"""
rag_service.py — Recherche vectorielle et retrieval sémantique.

Responsabilités :
- désérialisation des embeddings BLOB SQLite ;
- calcul de similarité cosinus (pur Python) ;
- recherche des top-k chunks les plus proches d'un vecteur requête.

Ce module sera le point d'extension naturel pour la migration
vers pgvector (Phase 13) ou une base vectorielle dédiée (Phase 15+).
"""
import sqlite3
import struct
from typing import Optional

import numpy as np

import database


_FR_STOPWORDS = frozenset({
    "le", "la", "les", "un", "une", "des", "de", "du", "au", "aux",
    "et", "ou", "en", "dans", "par", "sur", "sous", "avec", "que",
    "qui", "est", "sont", "pas", "ne", "se", "ce", "sa", "son", "ses",
    "il", "elle", "ils", "elles", "je", "tu", "nous", "vous", "si",
    "car", "mais", "donc", "or", "puis", "bien", "tout", "plus",
})


def compute_retrieval_overlap(question: str, chunk_texts: list[str]) -> float:
    """
    Score de recouvrement lexical entre la question générée et les chunks retrieval.
    Retourne 0.0–1.0 : proportion des mots significatifs de la question
    présents dans le texte des chunks.
    0.0 si aucun mot significatif ou aucun chunk.
    """
    if not question or not chunk_texts:
        return 0.0
    combined = " ".join(chunk_texts).lower()
    words = [
        w.lower()
        for w in question.replace("'", " ").replace("-", " ").split()
        if len(w) > 2 and w.lower() not in _FR_STOPWORDS and w.isalpha()
    ]
    if not words:
        return 0.0
    matched = sum(1 for w in words if w in combined)
    return round(matched / len(words), 3)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Similarité cosinus entre deux vecteurs via numpy (float32, ~100x plus rapide)."""
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    norm_a = float(np.linalg.norm(va))
    norm_b = float(np.linalg.norm(vb))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(va, vb) / (norm_a * norm_b))


def _blob_to_vector(blob: bytes) -> list[float]:
    """Désérialise un BLOB SQLite en vecteur de floats (float32, little-endian)."""
    n = len(blob) // 4  # chaque float32 = 4 octets
    return list(struct.unpack(f"<{n}f", blob))


def search_similar_chunks(
    query_embedding: list[float],
    document_id: int,
    top_k: int = 3,
) -> list[dict]:
    """
    Retourne les top_k chunks du document les plus proches de query_embedding.
    Ne renvoie que les chunks qui ont un embedding stocké.
    Résultats triés par similarité décroissante.
    """
    with sqlite3.connect(database.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, document_id, chunk_index, section_title, chunk_text, char_count, embedding
            FROM chunks
            WHERE document_id = ? AND embedding IS NOT NULL AND char_count >= 150
            """,
            (document_id,),
        ).fetchall()
    conn.close()

    if not rows:
        return []

    scored = []
    for row in rows:
        vec = _blob_to_vector(row["embedding"])
        sim = _cosine_similarity(query_embedding, vec)
        scored.append({
            "id":            row["id"],
            "document_id":   row["document_id"],
            "chunk_index":   row["chunk_index"],
            "section_title": row["section_title"],
            "chunk_text":    row["chunk_text"],
            "char_count":    row["char_count"],
            "similarity":    sim,
        })

    scored.sort(key=lambda x: x["similarity"], reverse=True)
    return scored[:top_k]


def search_similar_chunks_multi(
    query_embedding: list[float],
    document_ids: Optional[list[int]],
    top_k: int = 3,
) -> list[dict]:
    """
    Retourne les top_k chunks les plus proches de query_embedding.

    document_ids=[1,2,...] → recherche sur ces documents uniquement.
    document_ids=None      → recherche sur tout le corpus (sans filtre document_id).
    document_ids=[]        → retourne [] immédiatement.

    Note : le mode corpus complet (None) est acceptable pour un MVP jusqu'à ~50 documents.
    Au-delà, envisager un index ANN ou pgvector (Phase 13).
    """
    if document_ids is not None and len(document_ids) == 0:
        return []

    with sqlite3.connect(database.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        if document_ids is None:
            rows = conn.execute(
                """
                SELECT id, document_id, chunk_index, section_title, chunk_text, char_count, embedding
                FROM chunks
                WHERE embedding IS NOT NULL
                  AND char_count >= 150
                """
            ).fetchall()
        else:
            placeholders = ",".join("?" * len(document_ids))
            rows = conn.execute(
                f"""
                SELECT id, document_id, chunk_index, section_title, chunk_text, char_count, embedding
                FROM chunks
                WHERE document_id IN ({placeholders})
                  AND embedding IS NOT NULL
                  AND char_count >= 150
                """,
                document_ids,
            ).fetchall()
    conn.close()

    if not rows:
        return []

    scored = []
    for row in rows:
        vec = _blob_to_vector(row["embedding"])
        sim = _cosine_similarity(query_embedding, vec)
        scored.append({
            "id":            row["id"],
            "document_id":   row["document_id"],
            "chunk_index":   row["chunk_index"],
            "section_title": row["section_title"],
            "chunk_text":    row["chunk_text"],
            "char_count":    row["char_count"],
            "similarity":    sim,
        })

    scored.sort(key=lambda x: x["similarity"], reverse=True)
    return scored[:top_k]
