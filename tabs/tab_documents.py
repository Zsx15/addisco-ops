"""Onglet Documents — import, bibliothèque, reindexation des embeddings."""
import streamlit as st

from database import get_document_by_id, get_documents
from document_service import get_text_preview, ingest_document, reindex_document
from ui_helpers import validate_doc_title, validate_file_size


def _make_use_callback(cleaned_text: str, doc_id: int, doc_title: str = ""):
    def _cb():
        st.session_state["source_text_input"]     = cleaned_text
        st.session_state["active_document_id"]    = doc_id
        st.session_state["active_document_title"] = doc_title
        st.session_state["question"]              = None
        st.session_state["result"]                = None
        st.session_state["answer_input"]          = ""
    return _cb


def render() -> None:
    st.subheader("Importer un document")

    with st.form("upload_form", clear_on_submit=True):
        doc_title     = st.text_input("Titre du document", placeholder="Ex : Procédure accueil client")
        uploaded_file = st.file_uploader("Fichier (TXT, PDF ou DOCX)", type=["txt", "pdf", "docx"])
        submitted     = st.form_submit_button("Importer")

    if submitted:
        _title_err = validate_doc_title(doc_title)
        if _title_err:
            st.error(_title_err)
        elif uploaded_file is None:
            st.error("Veuillez sélectionner un fichier.")
        else:
            file_bytes = uploaded_file.read()
            _size_err  = validate_file_size(len(file_bytes))
            if _size_err:
                st.error(_size_err)
            else:
                source_type = uploaded_file.name.rsplit(".", 1)[-1].lower()
                with st.spinner("Extraction et découpage en cours…"):
                    try:
                        doc_id = ingest_document(
                            title=doc_title.strip(),
                            source_type=source_type,
                            filename=uploaded_file.name,
                            file_bytes=file_bytes,
                        )
                        st.success(f"Document importé avec succès (ID {doc_id}).")
                    except ValueError as exc:
                        st.error(str(exc))
                    except Exception as exc:
                        st.error(f"Erreur inattendue : {exc}")

    st.divider()
    st.subheader("Bibliothèque")

    df_docs = get_documents()

    if df_docs.empty:
        st.info("Aucun document importé pour l'instant.")
        return

    st.caption(f"{len(df_docs)} document{'s' if len(df_docs) > 1 else ''} dans la bibliothèque")
    for _, doc in df_docs.iterrows():
        doc_id = int(doc["id"])
        label  = (
            f"📄 {doc['title']}  ·  {doc['source_type'].upper()}"
            f"  ·  {int(doc['chunk_count'])} section{'s' if doc['chunk_count'] != 1 else ''}"
            f"  ·  {str(doc['created_at'])[:16]}"
        )
        with st.expander(label):
            c1, c2, c3 = st.columns(3)
            c1.metric("Caractères", f"{int(doc['char_count']):,}".replace(",", " "))
            c2.metric("Sections", int(doc["chunk_count"]))
            c3.metric("Fichier", doc["filename"] or "—")

            full_doc = get_document_by_id(doc_id)
            if full_doc and full_doc.get("cleaned_text"):
                st.markdown("**Aperçu**")
                st.text(get_text_preview(full_doc["cleaned_text"], chars=400))

            st.button(
                "Utiliser ce document pour l'entraînement",
                key=f"use_doc_{doc_id}",
                on_click=_make_use_callback(
                    full_doc["cleaned_text"] if full_doc else "",
                    doc_id,
                    doc["title"],
                ),
            )

            missing = int(doc.get("chunks_missing_embedding") or 0)
            if missing == 0:
                st.button(
                    "✓ Embeddings complets",
                    key=f"reindex_{doc_id}",
                    disabled=True,
                )
            else:
                if st.button(
                    f"Indexer les embeddings ({missing} section{'s' if missing > 1 else ''} manquante{'s' if missing > 1 else ''})",
                    key=f"reindex_{doc_id}",
                ):
                    with st.spinner("Calcul des embeddings en cours…"):
                        report = reindex_document(doc_id)
                    if report["failed"] == 0:
                        st.success(
                            f"{report['updated']} embedding{'s' if report['updated'] > 1 else ''} "
                            f"calculé{'s' if report['updated'] > 1 else ''}."
                        )
                    else:
                        st.warning(
                            f"{report['updated']} réussi(s), {report['failed']} échoué(s). "
                            "Rechargez la page pour relancer les manquants."
                        )
                    st.rerun()
