import logging
import re
import unicodedata

from ai_service import generate_embedding
from database import get_chunks_for_reindex, save_chunks, save_document, update_chunk_embedding

logger = logging.getLogger(__name__)

CHUNK_SIZE     = 1000
CHUNK_OVERLAP  = 150
MAX_FILE_BYTES = 10 * 1024 * 1024   # 10 Mo
WARN_TEXT_CHARS = 150_000


# ── Public API ────────────────────────────────────────────────────────────────

def ingest_document(
    title: str,
    source_type: str,
    filename: str,
    file_bytes: bytes,
) -> int:
    """
    Full ingestion pipeline. Returns the new document_id.
    Raises ValueError with a user-readable message on failure.
    """
    if len(file_bytes) > MAX_FILE_BYTES:
        raise ValueError(
            f"Fichier trop volumineux "
            f"({len(file_bytes) // 1024 // 1024} Mo). "
            f"Limite : {MAX_FILE_BYTES // 1024 // 1024} Mo."
        )
    if len(file_bytes) == 0:
        raise ValueError("Le fichier est vide.")

    raw_text = _extract_text(file_bytes, source_type)
    cleaned  = _clean_text(raw_text)

    if not cleaned.strip():
        raise ValueError("Le texte extrait est vide après nettoyage.")

    if len(cleaned) > WARN_TEXT_CHARS:
        logger.warning(
            "Document long : %d chars (document_id non encore attribué). "
            "Le texte complet est conservé ; la génération de questions "
            "utilisera une sélection.",
            len(cleaned),
        )

    doc_id = save_document(
        title=title,
        source_type=source_type,
        filename=filename,
        raw_text=raw_text,
        cleaned_text=cleaned,
    )
    logger.info("Document saved: id=%d  chars=%d", doc_id, len(cleaned))

    chunks = _create_chunks(cleaned)

    # Calcul des embeddings — mode dégradé : un échec n'interrompt pas l'import
    embedded = 0
    for chunk in chunks:
        try:
            chunk["embedding"] = generate_embedding(chunk["chunk_text"])
            embedded += 1
        except Exception as exc:
            logger.warning(
                "Embedding échoué pour chunk %d (doc %d) : %s",
                chunk["chunk_index"], doc_id, exc,
            )
            chunk["embedding"] = None  # sera stocké NULL dans SQLite

    logger.info(
        "Embeddings calculés : %d/%d pour document %d",
        embedded, len(chunks), doc_id,
    )

    save_chunks(doc_id, chunks)
    logger.info("Chunks created: %d segments for document %d", len(chunks), doc_id)

    return doc_id


def reindex_document(document_id: int) -> dict:
    """
    Calcule et stocke les embeddings manquants pour un document déjà importé.

    Garanties :
    - UPDATE uniquement — jamais DELETE + INSERT. Les chunk IDs restent stables,
      ce qui préserve la cohérence des futures relations attempts.chunk_id → chunks.id.
    - Idempotence : WHERE embedding IS NULL dans get_chunks_for_reindex() assure
      qu'un chunk déjà indexé n'est jamais retouché, même si la fonction est appelée
      plusieurs fois de suite sur le même document.
    - Fallback gracieux : une erreur API sur un chunk est loggée mais n'interrompt
      pas le traitement des chunks suivants.

    Retourne un rapport {"total", "updated", "already_indexed", "failed"}.
    """
    pending = get_chunks_for_reindex(document_id)

    # Nombre de chunks déjà indexés = total chunks - chunks manquants
    # (get_chunks_for_reindex ne charge que les NULL, donc on ne connaît pas le total ici)
    # Le rapport "already_indexed" est calculé côté appelant via get_documents() si besoin.
    # Ici on rapporte uniquement ce qui a été traité dans cette session.
    updated = 0
    failed  = 0

    for chunk in pending:
        try:
            blob = generate_embedding(chunk["chunk_text"])
            # UPDATE ciblé par clé primaire — chunk.id jamais modifié
            update_chunk_embedding(chunk["id"], blob)
            updated += 1
        except Exception as exc:
            logger.warning(
                "Reindex échoué pour chunk id=%d (doc %d) : %s",
                chunk["id"], document_id, exc,
            )
            failed += 1

    logger.info(
        "Reindex doc %d : %d mis à jour, %d échoués sur %d chunks manquants",
        document_id, updated, failed, len(pending),
    )
    return {
        "total_missing": len(pending),
        "updated":       updated,
        "failed":        failed,
    }


def get_text_preview(cleaned_text: str, chars: int = 500) -> str:
    preview = cleaned_text[:chars]
    return preview + ("…" if len(cleaned_text) > chars else "")


# ── Extraction ────────────────────────────────────────────────────────────────

def _extract_text(file_bytes: bytes, source_type: str) -> str:
    if source_type == "txt":
        return _extract_text_txt(file_bytes)
    if source_type == "pdf":
        return _extract_text_pdf(file_bytes)
    raise ValueError(f"Type de fichier non supporté : {source_type}")


def _extract_text_txt(file_bytes: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            return file_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError(
        "Impossible de décoder le fichier texte. "
        "Vérifiez l'encodage (UTF-8 recommandé)."
    )


def _extract_text_pdf(file_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ValueError(
            "La librairie pypdf n'est pas installée. "
            "Exécutez : pip install pypdf"
        )

    import io
    reader      = PdfReader(io.BytesIO(file_bytes))
    total_pages = len(reader.pages)
    pages_text: list[str] = []
    failed:     list[int] = []

    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
            pages_text.append(text)
        except Exception as exc:
            failed.append(i + 1)
            logger.warning("PDF page %d/%d — extraction failed: %s", i + 1, total_pages, exc)

    if failed:
        logger.warning(
            "PDF: %d/%d page(s) failed — pages: %s",
            len(failed), total_pages, failed,
        )

    full_text = "\n\n".join(p for p in pages_text if p.strip())

    if not full_text.strip():
        logger.error("PDF: aucun texte extractible sur %d pages", total_pages)
        raise ValueError(
            "Aucun texte lisible dans ce PDF. "
            "Il est peut-être constitué d'images scannées (OCR requis)."
        )

    logger.info(
        "PDF extracted: %d chars — %d/%d pages OK",
        len(full_text), total_pages - len(failed), total_pages,
    )
    return full_text


# ── Nettoyage ─────────────────────────────────────────────────────────────────

def _clean_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = "".join(c for c in text if c.isprintable() or c in "\n\t")
    text = text.replace("\t", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r" {2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ── Découpage ─────────────────────────────────────────────────────────────────

def _create_chunks(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[dict]:
    """
    Splits text into chunks at paragraph boundaries.
    Consecutive chunks share chunk_overlap trailing chars as context prefix.
    Designed to be replaced by embedding-aware chunking in Phase 6.
    """
    paragraphs   = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    result:      list[dict] = []
    buffer:      list[str]  = []
    buffer_len:  int        = 0
    overlap_prefix: str     = ""

    def flush() -> None:
        if not buffer:
            return
        body       = "\n\n".join(buffer)
        chunk_text = (overlap_prefix.rstrip() + "\n\n" + body).strip() \
                     if overlap_prefix else body
        result.append({
            "chunk_index":   len(result),
            "section_title": None,
            "chunk_text":    chunk_text,
            "char_count":    len(chunk_text),
            "embedding_id":  None,
        })

    for para in paragraphs:
        # Paragraph alone exceeds chunk_size → hard-split at word boundary
        if len(para) > chunk_size:
            flush()
            buffer, buffer_len, overlap_prefix = [], 0, ""
            start = 0
            while start < len(para):
                end = min(start + chunk_size, len(para))
                if end < len(para):
                    space = para.rfind(" ", start, end)
                    end   = space if space > start else end
                piece = para[start:end].strip()
                if piece:
                    result.append({
                        "chunk_index":   len(result),
                        "section_title": None,
                        "chunk_text":    piece,
                        "char_count":    len(piece),
                        "embedding_id":  None,
                    })
                    overlap_prefix = piece[-chunk_overlap:] if chunk_overlap else ""
                start = end + 1 if end < len(para) else end
            continue

        addition = len(para) + (2 if buffer else 0)
        if buffer_len + addition > chunk_size and buffer:
            flush()
            overlap_prefix = (
                result[-1]["chunk_text"][-chunk_overlap:]
                if chunk_overlap and result else ""
            )
            buffer     = [para]
            buffer_len = len(para)
        else:
            buffer.append(para)
            buffer_len += addition

    flush()
    return result
