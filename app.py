import time

import plotly.express as px
import streamlit as st

from ai_service import correct_answer, generate_question
from database import (
    get_attempts,
    get_document_by_id,
    get_documents,
    get_error_frequency,
    get_score_evolution,
    get_topic_stats,
    init_db,
    save_attempt,
)
from document_service import get_text_preview, ingest_document, reindex_document

init_db()

st.set_page_config(page_title="IA Révision Métier", page_icon="📚", layout="wide")
st.title("📚 IA Révision Métier")

for key in ("question", "source_text", "start_time", "result", "response_time", "active_document_id", "chunk_ids"):
    if key not in st.session_state:
        st.session_state[key] = None
if "source_text_input" not in st.session_state:
    st.session_state["source_text_input"] = ""

tab_train, tab_history, tab_dashboard, tab_docs = st.tabs(
    ["Entraînement", "Historique", "Dashboard", "Documents"]
)


def _make_use_callback(cleaned_text: str, doc_id: int):
    def _cb():
        st.session_state["source_text_input"] = cleaned_text
        st.session_state["active_document_id"] = doc_id
        st.session_state["question"] = None
        st.session_state["result"] = None
        st.session_state["answer_input"] = ""
    return _cb


# ── Onglet Entraînement ──────────────────────────────────────────────────────

with tab_train:
    st.subheader("Texte source")
    source_text = st.text_area(
        "Collez votre texte métier ici",
        height=200,
        placeholder="Procédure, règle, documentation…",
        key="source_text_input",
    )

    if st.session_state.get("active_document_id"):
        st.caption(f"Source : document importé (ID {st.session_state['active_document_id']})")

    if len(source_text) > 6000:
        st.warning("Texte trop long — seuls les 6 000 premiers caractères seront utilisés.")

    if st.button("Générer une question", disabled=not source_text.strip()):
        with st.spinner("Génération en cours…"):
            try:
                question, chunk_ids = generate_question(
                    source_text,
                    document_id=st.session_state.get("active_document_id"),
                )
                st.session_state["question"] = question
                st.session_state["chunk_ids"] = chunk_ids
                st.session_state["source_text"] = source_text
                st.session_state["start_time"] = time.time()
                st.session_state["result"] = None
            except Exception as exc:
                st.error(f"Erreur lors de la génération : {exc}")

    if st.session_state["question"]:
        st.divider()
        st.subheader("Question")
        st.info(st.session_state["question"])

        user_answer = st.text_area("Votre réponse", height=120, key="answer_input")

        if st.button("Valider ma réponse", disabled=not (user_answer or "").strip()):
            elapsed = time.time() - (st.session_state["start_time"] or time.time())
            with st.spinner("Correction en cours…"):
                try:
                    result = correct_answer(
                        st.session_state["question"],
                        user_answer,
                        st.session_state["source_text"],
                    )
                    st.session_state["result"] = result
                    st.session_state["response_time"] = elapsed

                    _chunk_ids = st.session_state.get("chunk_ids") or []
                    save_attempt(
                        question=st.session_state["question"],
                        user_answer=user_answer,
                        expected_answer=result.get("expected_answer", ""),
                        correction=result.get("correction", ""),
                        score=result.get("score", 0.0),
                        response_time_seconds=round(elapsed, 1),
                        error_type=result.get("error_type", ""),
                        topic=result.get("topic", ""),
                        document_id=st.session_state.get("active_document_id"),
                        chunk_id=_chunk_ids[0] if _chunk_ids else None,
                    )
                except Exception as exc:
                    st.error(f"Erreur lors de la correction : {exc}")

    if st.session_state["result"]:
        result = st.session_state["result"]
        try:
            score = float(result.get("score", 0))
        except (TypeError, ValueError):
            score = 0.0
        response_time = st.session_state.get("response_time") or 0

        st.divider()
        st.subheader("Correction")

        col1, col2, col3 = st.columns(3)
        col1.metric("Score", f"{round(score * 100)} %")
        col2.metric("Notion", result.get("topic") or "—")
        col3.metric("Temps de réponse", f"{round(response_time)} s")

        correction_text = result.get("correction", "")
        if score >= 0.8:
            st.success(correction_text)
        elif score >= 0.5:
            st.warning(correction_text)
        else:
            st.error(correction_text)

        if result.get("expected_answer"):
            with st.expander("Voir la réponse attendue"):
                st.write(result["expected_answer"])

        def _reset_question():
            st.session_state["result"] = None
            st.session_state["question"] = None
            st.session_state["chunk_ids"] = None
            st.session_state["answer_input"] = ""

        st.button("Nouvelle question sur ce texte", on_click=_reset_question)


# ── Onglet Historique ────────────────────────────────────────────────────────

_ERROR_LABELS = {
    "oubli_etape": "Oubli d'étape",
    "confusion_notion": "Confusion de notion",
    "reponse_vague": "Réponse vague",
    "erreur_ordre": "Erreur d'ordre",
    "hors_sujet": "Hors sujet",
    "correct": "Correct",
}


def _truncate_label(text: str, max_len: int = 25) -> str:
    return text if len(text) <= max_len else text[:max_len - 1] + "…"

with tab_history:
    st.subheader("Historique des tentatives")

    df = get_attempts()

    if df.empty:
        st.info("Aucune tentative enregistrée pour l'instant.")
    else:
        col1, col2, col3 = st.columns(3)
        col1.metric("Tentatives", len(df))
        scores = df["score"].dropna()
        mean_score_str = f"{round(scores.mean() * 100)} %" if len(scores) > 0 else "—"
        col2.metric("Score moyen", mean_score_str)
        col3.metric(
            "Dernière tentative",
            str(df["created_at"].iloc[0])[:16] if not df.empty else "—",
        )

        st.divider()

        for _, row in df.iterrows():
            try:
                score_val = float(row["score"])
                if score_val != score_val:  # NaN
                    score_val = 0.0
            except (TypeError, ValueError):
                score_val = 0.0

            score_pct = round(score_val * 100)
            icon = "✅" if score_val >= 0.8 else ("⚠️" if score_val >= 0.5 else "❌")
            notion = row["topic"] or "—"
            date_str = str(row["created_at"])[:16] if row["created_at"] else "—"
            error_label = _ERROR_LABELS.get(row["error_type"] or "", row["error_type"] or "—")

            with st.expander(f"{icon} {score_pct} % · {notion} · {date_str}"):
                c1, c2, c3 = st.columns(3)
                c1.metric("Score", f"{score_pct} %")
                c2.metric("Notion", notion)
                c3.metric("Type d'erreur", error_label)

                st.markdown("**Question**")
                st.write(row["question"] or "—")

                st.markdown("**Votre réponse**")
                st.write(row["user_answer"] or "—")

                if row["expected_answer"]:
                    st.markdown("**Réponse attendue**")
                    st.write(row["expected_answer"])

                st.markdown("**Correction**")
                correction = row["correction"] or "—"
                if score_val >= 0.8:
                    st.success(correction)
                elif score_val >= 0.5:
                    st.warning(correction)
                else:
                    st.error(correction)


# ── Onglet Dashboard ─────────────────────────────────────────────────────────

with tab_dashboard:
    st.subheader("Dashboard — Axes de progression")

    df_all = get_attempts()

    if len(df_all) < 2:
        st.info("Effectuez au moins 2 tentatives pour afficher le dashboard.")
    else:
        df_topics = get_topic_stats()

        # ── Métriques globales ────────────────────────────────────────────────
        scores_all = df_all["score"].dropna()
        worst_topic = df_topics.iloc[0]["topic"] if not df_topics.empty else "—"
        best_topic  = df_topics.iloc[-1]["topic"] if not df_topics.empty else "—"

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Tentatives totales", len(df_all))
        c2.metric("Score moyen global", f"{round(scores_all.mean() * 100)} %" if len(scores_all) else "—")
        c3.metric("Meilleure notion", best_topic)
        c4.metric("Notion la plus fragile", worst_topic)

        st.divider()

        # ── Évolution des scores ──────────────────────────────────────────────
        st.markdown("#### Évolution des scores")
        df_evol = get_score_evolution(limit=20)
        if not df_evol.empty:
            df_line = df_evol[["score"]].copy()
            df_line["Score (%)"] = (df_line["score"] * 100).round().astype(int)
            df_line["Tentative"] = range(1, len(df_line) + 1)
            st.line_chart(df_line, x="Tentative", y="Score (%)", height=300)
            st.caption(f"{len(df_evol)} dernières tentatives — ordre chronologique, de gauche à droite")

        st.divider()

        col_left, col_right = st.columns(2)

        # ── Score moyen par notion ────────────────────────────────────────────
        with col_left:
            st.markdown("#### Score moyen par notion")
            if not df_topics.empty:
                df_plot = df_topics.copy()
                df_plot["score_pct"] = (df_plot["avg_score"] * 100).round().astype(int)
                df_plot["label"] = df_plot["topic"].apply(_truncate_label)
                df_plot["niveau"] = df_plot["avg_score"].apply(
                    lambda s: "Bon" if s >= 0.8 else ("Moyen" if s >= 0.5 else "Fragile")
                )
                fig = px.bar(
                    df_plot.sort_values("score_pct"),
                    x="score_pct",
                    y="label",
                    orientation="h",
                    color="niveau",
                    color_discrete_map={
                        "Bon":     "#27ae60",
                        "Moyen":   "#e67e22",
                        "Fragile": "#e74c3c",
                    },
                    custom_data=["topic", "attempts"],
                    height=max(260, len(df_plot) * 52),
                )
                fig.update_traces(
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>"
                        "Score moyen : %{x} %<br>"
                        "Tentatives : %{customdata[1]:.0f}"
                        "<extra></extra>"
                    )
                )
                fig.update_layout(
                    legend_title_text="Niveau",
                    xaxis=dict(range=[0, 100], title="Score moyen (%)"),
                    yaxis=dict(title=""),
                    margin=dict(l=10, r=10, t=10, b=10),
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Pas encore de données par notion.")

        # ── Types d'erreurs ───────────────────────────────────────────────────
        with col_right:
            st.markdown("#### Types d'erreurs fréquents")
            df_errors = get_error_frequency()
            if not df_errors.empty:
                df_errors["label"] = df_errors["error_type"].map(
                    lambda x: _ERROR_LABELS.get(x, x)
                )
                df_errors["label_short"] = df_errors["label"].apply(_truncate_label)
                fig = px.bar(
                    df_errors.sort_values("count"),
                    x="count",
                    y="label_short",
                    orientation="h",
                    color_discrete_sequence=["#3498db"],
                    custom_data=["label"],
                    height=max(260, len(df_errors) * 52),
                )
                fig.update_traces(
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>"
                        "Occurrences : %{x}"
                        "<extra></extra>"
                    )
                )
                fig.update_layout(
                    showlegend=False,
                    xaxis=dict(title="Occurrences", dtick=1),
                    yaxis=dict(title=""),
                    margin=dict(l=10, r=10, t=10, b=10),
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Aucune erreur enregistrée.")

        st.divider()

        # ── Notions fragiles ──────────────────────────────────────────────────
        st.markdown("#### Notions fragiles — score moyen < 60 %")
        if not df_topics.empty:
            fragile = df_topics[df_topics["avg_score"] < 0.6]
            if fragile.empty:
                st.success("Aucune notion fragile détectée — bon travail !")
            else:
                for _, r in fragile.iterrows():
                    pct = round(float(r["avg_score"]) * 100)
                    n = int(r["attempts"])
                    st.error(
                        f"**{r['topic']}** — Score moyen : {pct} %  "
                        f"({n} tentative{'s' if n > 1 else ''})"
                    )
        else:
            st.info("Pas encore assez de données par notion.")

        st.divider()

        # ── Nombre de tentatives par notion ──────────────────────────────────
        st.markdown("#### Tentatives par notion")
        if not df_topics.empty:
            df_tc = df_topics.copy()
            df_tc["label"] = df_tc["topic"].apply(_truncate_label)
            fig = px.bar(
                df_tc.sort_values("attempts"),
                x="attempts",
                y="label",
                orientation="h",
                color_discrete_sequence=["#9b59b6"],
                custom_data=["topic"],
                height=max(260, len(df_tc) * 52),
            )
            fig.update_traces(
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Tentatives : %{x:.0f}"
                    "<extra></extra>"
                )
            )
            fig.update_layout(
                showlegend=False,
                xaxis=dict(title="Tentatives", dtick=1),
                yaxis=dict(title=""),
                margin=dict(l=10, r=10, t=10, b=10),
            )
            st.plotly_chart(fig, use_container_width=True)


# ── Onglet Documents ─────────────────────────────────────────────────────────

with tab_docs:
    st.subheader("Importer un document")

    with st.form("upload_form", clear_on_submit=True):
        doc_title = st.text_input("Titre du document", placeholder="Ex : Procédure accueil client")
        uploaded_file = st.file_uploader("Fichier (TXT ou PDF)", type=["txt", "pdf"])
        submitted = st.form_submit_button("Importer")

    if submitted:
        if not doc_title.strip():
            st.error("Veuillez saisir un titre.")
        elif uploaded_file is None:
            st.error("Veuillez sélectionner un fichier.")
        else:
            file_bytes = uploaded_file.read()
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
    else:
        st.caption(f"{len(df_docs)} document{'s' if len(df_docs) > 1 else ''} dans la bibliothèque")
        for _, doc in df_docs.iterrows():
            doc_id   = int(doc["id"])
            label    = f"📄 {doc['title']}  ·  {doc['source_type'].upper()}  ·  {int(doc['chunk_count'])} chunk{'s' if doc['chunk_count'] != 1 else ''}  ·  {str(doc['created_at'])[:16]}"
            with st.expander(label):
                c1, c2, c3 = st.columns(3)
                c1.metric("Caractères", f"{int(doc['char_count']):,}".replace(",", " "))
                c2.metric("Chunks", int(doc["chunk_count"]))
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
                    ),
                )

                # Bouton reindex — visible uniquement si des embeddings manquent.
                # chunks_missing_embedding provient de get_documents() (colonne ajoutée).
                # Désactivé si tout est déjà indexé : garantit aucun retraitement inutile.
                missing = int(doc.get("chunks_missing_embedding") or 0)
                if missing == 0:
                    st.button(
                        "✓ Embeddings complets",
                        key=f"reindex_{doc_id}",
                        disabled=True,
                    )
                else:
                    if st.button(
                        f"Indexer les embeddings ({missing} chunk{'s' if missing > 1 else ''} manquant{'s' if missing > 1 else ''})",
                        key=f"reindex_{doc_id}",
                    ):
                        with st.spinner("Calcul des embeddings en cours…"):
                            report = reindex_document(doc_id)
                        if report["failed"] == 0:
                            st.success(
                                f"{report['updated']} embedding{'s' if report['updated'] > 1 else ''} calculé{'s' if report['updated'] > 1 else ''}."
                            )
                        else:
                            st.warning(
                                f"{report['updated']} réussi(s), {report['failed']} échoué(s). "
                                "Rechargez la page pour relancer les manquants."
                            )
                        st.rerun()
