import os
import time
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from logger import setup_logging

setup_logging()

from ai_service import correct_answer, explain_type_choice, generate_question
from database import (
    DB_PATH,
    classify_mastery,
    compute_and_save_learning_profile,
    get_attempts,
    get_chunk_mastery,
    get_chunk_question_history,
    get_chunk_stats,
    get_document_by_id,
    get_documents,
    get_error_frequency,
    get_learning_profile,
    get_revision_suggestion,
    get_score_evolution,
    get_topic_stats,
    init_db,
    save_attempt,
)
from document_service import get_text_preview, ingest_document, reindex_document, seed_demo_document
from seed_demo_attempts import seed as _seed_demo_attempts
from ui_helpers import (
    _ERROR_LABELS,
    _build_recommendations,
    _build_report,
    _kpi_card,
    _mastery_state,
    _truncate_label,
    explain_interval_decision,
    explain_priority_decision,
    explain_profile_detection,
    explain_question_decision,
)

init_db()
seed_demo_document()
try:
    _seed_demo_attempts()
except Exception:
    pass

st.set_page_config(page_title="SYNPZ OPS", page_icon="🧠", layout="wide")

st.markdown("""
<style>
/* ── App background ── */
.stApp {
    background-color: #f5f6fa;
}
/* ── Main content ── */
.main .block-container {
    padding-top: 1rem !important;
    padding-bottom: 1rem !important;
    background-color: #f5f6fa;
}
/* ── Tabs background ── */
.stTabs [data-baseweb="tab-panel"] {
    background-color: #f5f6fa;
    padding-top: 10px !important;
}
/* ── Dividers ── */
hr {
    margin-top: 0.5rem !important;
    margin-bottom: 0.5rem !important;
    border-color: #e2e8f0 !important;
}
/* ── Alerts ── */
[data-testid="stAlert"] {
    padding: 0.6rem 1rem !important;
    border-radius: 8px !important;
}
/* ── Tabs ── */
.stTabs [data-baseweb="tab"] {
    font-weight: 600 !important;
    padding: 6px 16px !important;
    font-size: 13px !important;
}
.stTabs [data-baseweb="tab-list"] {
    gap: 2px !important;
    border-bottom: 2px solid #e2e8f0 !important;
    background-color: transparent !important;
}
/* ── Metric labels ── */
[data-testid="stMetricLabel"] > div {
    font-size: 0.68rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    color: #94a3b8 !important;
}
[data-testid="stMetricValue"] > div {
    font-size: 1.8rem !important;
    font-weight: 700 !important;
    color: #0f172a !important;
}
/* ── Bordered containers — card with shadow ── */
[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 10px !important;
    box-shadow: 0 1px 3px rgba(15,23,42,.08), 0 1px 2px rgba(15,23,42,.04) !important;
    background: #ffffff !important;
    border-color: #e2e8f0 !important;
}
/* ── Caption ── */
[data-testid="stCaptionContainer"] {
    margin-bottom: 0 !important;
}
/* ── Progress bar ── */
[data-testid="stProgress"] {
    margin-bottom: 2px !important;
}
/* ── Info box border ── */
[data-testid="stAlert"][kind="info"] {
    background-color: #f0f4ff !important;
    border-left-color: #4f46e5 !important;
}
/* ── Expander ── */
[data-testid="stExpander"] {
    border-radius: 8px !important;
    border-color: #e2e8f0 !important;
    background: #ffffff !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div style="padding:6px 0 16px;border-bottom:2px solid #e2e8f0;margin-bottom:8px;background:#f5f6fa">
  <div style="display:flex;align-items:flex-start;gap:14px;margin-bottom:9px">
    <div style="width:4px;min-height:40px;background:#4f46e5;border-radius:3px;flex-shrink:0;margin-top:2px"></div>
    <div>
      <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:3px">
        <span style="font-size:22px;font-weight:800;color:#0f172a;letter-spacing:-0.03em;line-height:1">SYNPZ OPS</span>
        <span style="font-size:10px;font-weight:700;color:#4f46e5;text-transform:uppercase;letter-spacing:.1em;background:#eef2ff;padding:2px 9px;border-radius:20px;border:1px solid #c7d2fe;white-space:nowrap">Adaptive Learning Intelligence</span>
      </div>
      <div style="font-size:11.5px;color:#94a3b8;font-weight:500;margin-top:2px">
        RAG documentaire &middot; Répétition espacée &middot; Adaptation cognitive
      </div>
    </div>
  </div>
  <div style="display:flex;align-items:center;gap:4px;flex-wrap:wrap;margin-left:18px">
    <span style="background:#ffffff;border:1px solid #e2e8f0;border-radius:20px;padding:2px 10px;font-size:11px;color:#475569;white-space:nowrap;box-shadow:0 1px 2px rgba(0,0,0,.04)">📄 Document</span>
    <span style="color:#c7d2fe;font-size:12px;font-weight:700">&rarr;</span>
    <span style="background:#ffffff;border:1px solid #e2e8f0;border-radius:20px;padding:2px 10px;font-size:11px;color:#475569;white-space:nowrap;box-shadow:0 1px 2px rgba(0,0,0,.04)">🔍 RAG</span>
    <span style="color:#c7d2fe;font-size:12px;font-weight:700">&rarr;</span>
    <span style="background:#ffffff;border:1px solid #e2e8f0;border-radius:20px;padding:2px 10px;font-size:11px;color:#475569;white-space:nowrap;box-shadow:0 1px 2px rgba(0,0,0,.04)">❓ Question</span>
    <span style="color:#c7d2fe;font-size:12px;font-weight:700">&rarr;</span>
    <span style="background:#ffffff;border:1px solid #e2e8f0;border-radius:20px;padding:2px 10px;font-size:11px;color:#475569;white-space:nowrap;box-shadow:0 1px 2px rgba(0,0,0,.04)">✍️ Réponse</span>
    <span style="color:#c7d2fe;font-size:12px;font-weight:700">&rarr;</span>
    <span style="background:#ffffff;border:1px solid #e2e8f0;border-radius:20px;padding:2px 10px;font-size:11px;color:#475569;white-space:nowrap;box-shadow:0 1px 2px rgba(0,0,0,.04)">✅ Correction</span>
    <span style="color:#c7d2fe;font-size:12px;font-weight:700">&rarr;</span>
    <span style="background:#ffffff;border:1px solid #e2e8f0;border-radius:20px;padding:2px 10px;font-size:11px;color:#475569;white-space:nowrap;box-shadow:0 1px 2px rgba(0,0,0,.04)">🧠 Mémoire</span>
    <span style="color:#c7d2fe;font-size:12px;font-weight:700">&rarr;</span>
    <span style="background:#eef2ff;border:1px solid #c7d2fe;border-radius:20px;padding:2px 10px;font-size:11px;color:#4f46e5;white-space:nowrap;font-weight:600;box-shadow:0 1px 2px rgba(0,0,0,.04)">🔄 Révision</span>
  </div>
</div>
""", unsafe_allow_html=True)

for key in (
    "question", "source_text", "start_time", "result", "response_time",
    "active_document_id", "active_document_title", "chunk_ids", "question_type",
    "question_mastery", "question_chunk_trend", "question_chunk_days",
    "question_chunk_error", "question_chunk_status",
    "question_type_reason", "question_profile_pedagogy",
):
    if key not in st.session_state:
        st.session_state[key] = None
if "source_text_input" not in st.session_state:
    st.session_state["source_text_input"] = ""
if "user_id" not in st.session_state:
    st.session_state["user_id"] = "default"

with st.sidebar:
    st.markdown("**Session utilisateur**")
    st.text_input("Identifiant", key="user_id", placeholder="ex : alice, bob…")

    st.divider()
    st.caption("**Statut système**")
    _db_ok = DB_PATH.exists()
    st.caption(f"{'✅' if _db_ok else '❌'} Base · {'opérationnelle' if _db_ok else 'introuvable'}")
    _api_ok = bool(os.getenv("OPENAI_API_KEY"))
    st.caption(f"{'✅' if _api_ok else '⚠️'} OpenAI · {'connecté' if _api_ok else 'mode fallback'}")
    _n_docs = len(get_documents())
    st.caption(f"📄 {_n_docs} document{'s' if _n_docs > 1 else ''} chargé{'s' if _n_docs > 1 else ''}")

tab_train, tab_history, tab_dashboard, tab_docs, tab_engine, tab_formateur = st.tabs(
    ["Entraînement", "Historique", "Dashboard", "Documents", "Moteur IA", "Formateur"]
)


_TYPE_LABELS = {
    "question_directe": "Question directe",
    "cas_pratique":     "Cas pratique",
    "vrai_faux":        "Vrai / Faux",
    "question_piege":   "Question piège",
    "reformulation":    "Reformulation",
    "consequence":      "Conséquence / condition",
}

_TYPE_EXPLANATIONS = {
    "question_directe": "Vérifie la restitution directe d'une information clé du document.",
    "cas_pratique":     "Met en situation concrète pour tester l'application des règles métier.",
    "vrai_faux":        "Teste la capacité à distinguer les affirmations correctes des erreurs.",
    "question_piege":   "Éprouve la solidité de la maîtrise face à des formulations trompeuses.",
    "reformulation":    "Demande d'expliquer avec ses propres mots pour consolider la compréhension.",
    "consequence":      "Teste la compréhension des enchaînements logiques et des conditions d'application.",
}

_MASTERY_BIAS_LABELS = {
    "Fragile":          "Section fragile — reformulation et conséquence prioritaires pour consolider les bases.",
    "En consolidation": "Section en progression — types variés pour ancrer les acquis.",
    "Maîtrisé":         "Section maîtrisée — questions pièges et cas pratiques pour challenger la maîtrise.",
}


def _make_use_callback(cleaned_text: str, doc_id: int, doc_title: str = ""):
    def _cb():
        st.session_state["source_text_input"] = cleaned_text
        st.session_state["active_document_id"] = doc_id
        st.session_state["active_document_title"] = doc_title
        st.session_state["question"] = None
        st.session_state["result"] = None
        st.session_state["answer_input"] = ""
    return _cb


# ── Onglet Entraînement ──────────────────────────────────────────────────────

with tab_train:
    # ── Suggestion de révision ───────────────────────────────────────────
    suggestion = get_revision_suggestion(user_id=st.session_state["user_id"])
    if suggestion:
        try:
            last_dt   = datetime.fromisoformat(str(suggestion["last_attempt_date"]))
            days_ago  = (datetime.now() - last_dt).days
            age_label = (
                f"il y a {days_ago} jour{'s' if days_ago > 1 else ''}"
                if days_ago > 0 else "aujourd'hui"
            )
        except Exception:
            age_label = "—"

        st.markdown("##### Révision suggérée")
        c1, c2, c3, c4 = st.columns([4, 1, 1, 2])
        c1.markdown(
            f"**{suggestion['section_label']}**  \n"
            f"_{suggestion['document_title']}_ · {age_label}"
        )
        c2.metric("Score", f"{round(float(suggestion['avg_score']) * 100)} %")
        c3.metric("Tentatives", int(suggestion["attempts_count"]))
        c4.button(
            "Réviser cette section →",
            key="btn_revision_suggestion",
            on_click=_make_use_callback(
                suggestion["chunk_text"], suggestion["document_id"],
                suggestion["document_title"],
            ),
        )
        st.divider()

    # ── Sélecteur de document ────────────────────────────────────────────
    _df_docs = get_documents()
    if not _df_docs.empty:
        _doc_ids    = [None] + [int(r["id"]) for _, r in _df_docs.iterrows()]
        _doc_titles = {None: "— Texte libre (sans RAG)"}
        for _, _r in _df_docs.iterrows():
            _doc_titles[int(_r["id"])] = _r["title"]
        _active_id = st.session_state.get("active_document_id")
        _sel_idx   = _doc_ids.index(_active_id) if _active_id in _doc_ids else 0
        _selected  = st.selectbox(
            "Document de travail",
            options=_doc_ids,
            format_func=lambda x: _doc_titles.get(x, "—"),
            index=_sel_idx,
        )
        if _selected != _active_id:
            if _selected is None:
                st.session_state["active_document_id"]    = None
                st.session_state["active_document_title"] = ""
                st.session_state["source_text_input"]     = ""
            else:
                _full = get_document_by_id(_selected)
                if _full:
                    st.session_state["active_document_id"]    = _selected
                    st.session_state["active_document_title"] = _full["title"]
                    st.session_state["source_text_input"]     = _full.get("cleaned_text", "")
            st.session_state["question"] = None
            st.session_state["result"]   = None
            st.rerun()

    st.subheader("Texte source")
    source_text = st.text_area(
        "Collez votre texte métier ici",
        height=200,
        placeholder="Procédure, règle, documentation…",
        key="source_text_input",
    )

    if st.session_state.get("active_document_id"):
        _doc_title = st.session_state.get("active_document_title") or "Document importé"
        st.caption(f"Source : {_doc_title}")

    if len(source_text) > 6000:
        st.warning("Texte trop long — seuls les 6 000 premiers caractères seront utilisés.")

    if st.button("Générer une question", disabled=not source_text.strip()):
        with st.spinner("Génération en cours…"):
            try:
                question, chunk_ids, question_type = generate_question(
                    source_text,
                    document_id=st.session_state.get("active_document_id"),
                    user_id=st.session_state["user_id"],
                )
                st.session_state["question"]      = question
                st.session_state["chunk_ids"]     = chunk_ids
                st.session_state["question_type"] = question_type
                st.session_state["source_text"]   = source_text
                st.session_state["start_time"]    = time.time()
                st.session_state["result"]        = None
                if chunk_ids:
                    try:
                        st.session_state["question_mastery"] = get_chunk_mastery(chunk_ids[0], user_id=st.session_state["user_id"])
                        _cs = classify_mastery(get_chunk_stats(user_id=st.session_state["user_id"]))
                        _csr = _cs[_cs["chunk_id"] == chunk_ids[0]]
                        if not _csr.empty:
                            _cr = _csr.iloc[0]
                            st.session_state["question_chunk_trend"]  = _cr.get("trend", "N/A")
                            st.session_state["question_chunk_days"]   = _cr.get("days_until_review")
                            st.session_state["question_chunk_error"]  = _cr.get("dominant_error_type")
                            st.session_state["question_chunk_status"] = _cr.get("review_status", "—")
                        else:
                            st.session_state["question_chunk_trend"]  = "N/A"
                            st.session_state["question_chunk_days"]   = None
                            st.session_state["question_chunk_error"]  = None
                            st.session_state["question_chunk_status"] = "—"
                    except Exception:
                        st.session_state["question_mastery"]          = None
                        st.session_state["question_chunk_trend"]      = "N/A"
                        st.session_state["question_chunk_days"]       = None
                        st.session_state["question_chunk_error"]      = None
                        st.session_state["question_chunk_status"]     = "—"
                    # TASK-028e — trace de décision (bloc indépendant, non bloquant)
                    try:
                        _hist  = get_chunk_question_history(chunk_ids[0], user_id=st.session_state["user_id"])
                        _used  = [h["question_type"] for h in _hist if h.get("question_type")]
                        _prof  = get_learning_profile(st.session_state["user_id"])
                        _pped  = _prof.get("preferred_pedagogy") if _prof else None
                        st.session_state["question_type_reason"]      = explain_type_choice(
                            _used, st.session_state.get("question_mastery"), _pped, question_type
                        )
                        st.session_state["question_profile_pedagogy"] = _pped
                    except Exception:
                        st.session_state["question_type_reason"]      = None
                        st.session_state["question_profile_pedagogy"] = None
                else:
                    st.session_state["question_mastery"]          = None
                    st.session_state["question_chunk_trend"]      = "N/A"
                    st.session_state["question_chunk_days"]       = None
                    st.session_state["question_chunk_error"]      = None
                    st.session_state["question_chunk_status"]     = "—"
                    st.session_state["question_type_reason"]      = None
                    st.session_state["question_profile_pedagogy"] = None
            except Exception as exc:
                st.error(f"Erreur lors de la génération : {exc}")

    if st.session_state["question"]:
        st.divider()
        st.subheader("Question")
        st.info(st.session_state["question"])
        _q_type = st.session_state.get("question_type")
        _mode   = "RAG actif" if st.session_state.get("chunk_ids") else "Texte brut"
        _tlabel = _TYPE_LABELS.get(_q_type, _q_type) if _q_type else "—"
        st.caption(f"Type : {_tlabel} · {_mode}")

        with st.expander("Pourquoi cette question ?"):
            _expl = _TYPE_EXPLANATIONS.get(_q_type, "")
            st.markdown(f"**Type · {_tlabel}**  \n{_expl}" if _expl else f"**Type · {_tlabel}**")
            # TASK-028e — trace de décision moteur
            _type_reason = st.session_state.get("question_type_reason")
            if _type_reason:
                st.caption(f"🧩 Décision moteur : {_type_reason}")
            _mastery = st.session_state.get("question_mastery")
            if _mastery and st.session_state.get("chunk_ids"):
                _bias_text = _MASTERY_BIAS_LABELS.get(_mastery, "")
                st.markdown(
                    f"**Maîtrise détectée · {_mastery}**  \n{_bias_text}"
                    if _bias_text else f"**Maîtrise détectée · {_mastery}**"
                )
                # TASK-028a — signaux cognitifs structurés
                _c_trend   = st.session_state.get("question_chunk_trend", "N/A")
                _c_status  = st.session_state.get("question_chunk_status", "—")
                _c_error   = st.session_state.get("question_chunk_error")
                _c_pedagogy = st.session_state.get("question_profile_pedagogy")
                _signals = explain_question_decision(
                    _q_type or "", _mastery, _c_trend or "N/A",
                    _c_status or "—", _c_error, _c_pedagogy,
                )
                if _signals:
                    _sig_html = "".join(
                        f'<div style="font-size:12px;color:#475569;padding:2px 0">'
                        f'<span style="margin-right:6px">{icon}</span>{text}</div>'
                        for icon, text in _signals
                    )
                    st.markdown(_sig_html, unsafe_allow_html=True)
            elif not st.session_state.get("chunk_ids"):
                st.caption(
                    "Mode texte brut — RAG non actif. "
                    "Sélectionnez un document pour activer la trace RAG et l'adaptation cognitive."
                )

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
                        pedagogy_type=st.session_state.get("question_type"),
                        document_id=st.session_state.get("active_document_id"),
                        chunk_id=_chunk_ids[0] if _chunk_ids else None,
                        user_id=st.session_state["user_id"],
                    )
                    try:
                        compute_and_save_learning_profile(st.session_state["user_id"])
                    except Exception:
                        pass
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

        _chunk_ids_res = st.session_state.get("chunk_ids") or []
        _topic_res     = result.get("topic") or "—"
        if _chunk_ids_res:
            st.caption(
                f"🧠 Résultat enregistré · Notion : {_topic_res} · "
                f"Score : {round(score * 100)} % · Mémoire pédagogique mise à jour"
            )
        else:
            st.caption(f"🧠 Résultat enregistré · Notion : {_topic_res} · Score : {round(score * 100)} %")

        def _reset_question():
            st.session_state["result"] = None
            st.session_state["question"] = None
            st.session_state["chunk_ids"] = None
            st.session_state["answer_input"] = ""

        st.button("Nouvelle question sur ce texte", on_click=_reset_question)


# ── Onglet Historique ────────────────────────────────────────────────────────

with tab_history:
    st.subheader("Historique des tentatives")

    df = get_attempts(user_id=st.session_state["user_id"])

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

        _EXPORT_COLS = [
            "created_at", "question", "user_answer", "expected_answer",
            "score", "error_type", "topic", "pedagogy_type", "response_time_seconds",
        ]
        _export_cols = [c for c in _EXPORT_COLS if c in df.columns]
        _csv_bytes = df[_export_cols].to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="⬇ Exporter l'historique (.csv)",
            data=_csv_bytes,
            file_name="synpz_historique.csv",
            mime="text/csv",
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
    st.markdown(
        "<h4 style='margin:0 0 10px;color:#0f172a;font-size:15px;font-weight:700;"
        "letter-spacing:-0.01em'>Tableau de bord pédagogique</h4>",
        unsafe_allow_html=True,
    )

    df_all = get_attempts(user_id=st.session_state["user_id"])

    if len(df_all) < 2:
        st.info("Effectuez au moins 2 tentatives pour afficher le dashboard.")
    else:
        df_topics = get_topic_stats(user_id=st.session_state["user_id"])
        df_chunks = classify_mastery(get_chunk_stats(user_id=st.session_state["user_id"]))
        df_errors = get_error_frequency(user_id=st.session_state["user_id"])

        # ── Zone 1 : KPIs enrichis ────────────────────────────────────────────
        scores_all = df_all["score"].dropna()
        n_sections = len(df_chunks)
        n_mastered = int((df_chunks["mastery_class"] == "Maîtrisé").sum()) if not df_chunks.empty else 0
        n_retard   = int((df_chunks["review_status"] == "En retard").sum()) if not df_chunks.empty and "review_status" in df_chunks.columns else 0

        _kc1, _kc2, _kc3, _kc4 = st.columns(4)
        _kc1.markdown(
            _kpi_card("📊", "Tentatives", str(len(df_all))),
            unsafe_allow_html=True,
        )
        _kc2.markdown(
            _kpi_card("🎯", "Score moyen",
                      f"{round(scores_all.mean() * 100)} %" if len(scores_all) else "—"),
            unsafe_allow_html=True,
        )
        _kc3.markdown(
            _kpi_card("✅", "Sections maîtrisées",
                      f"{n_mastered} / {n_sections}" if n_sections else "—",
                      "#15803d" if n_mastered == n_sections and n_sections else "#1e293b"),
            unsafe_allow_html=True,
        )
        _kc4.markdown(
            _kpi_card("⚠️", "Révisions en retard",
                      str(n_retard) if n_sections else "—",
                      "#c2410c" if n_retard > 0 else "#1e293b"),
            unsafe_allow_html=True,
        )

        # ── Zone 1b : Recommandations intelligentes ───────────────────────────
        _recs = _build_recommendations(df_chunks, df_errors)
        if _recs:
            st.divider()
            st.markdown(
                "<p style='font-size:12px;font-weight:700;color:#475569;margin:0 0 6px;"
                "text-transform:uppercase;letter-spacing:.07em'>Recommandations du moteur</p>",
                unsafe_allow_html=True,
            )
            _rec_icons = {"urgent": "🔴", "warning": "🟡", "success": "🟢", "info": "🔵"}
            _rec_html = "".join(
                f'<div style="display:flex;align-items:center;gap:8px;padding:6px 12px;'
                f'background:#ffffff;border:1px solid #e2e8f0;border-radius:8px;margin-bottom:4px;'
                f'box-shadow:0 1px 2px rgba(0,0,0,.04)">'
                f'<span style="font-size:14px;flex-shrink:0">{_rec_icons.get(rt, "⚪")}</span>'
                f'<span style="font-size:12.5px;color:#1e293b">{txt}</span>'
                f'</div>'
                for rt, txt in _recs
            )
            st.markdown(_rec_html, unsafe_allow_html=True)

        # ── Zone 2 : Révision prioritaire ────────────────────────────────────
        if not df_chunks.empty:
            _prio_fragile = df_chunks[df_chunks["mastery_class"] == "Fragile"].sort_values("avg_score")
            _prio_consol  = df_chunks[df_chunks["mastery_class"] == "En consolidation"].sort_values("avg_score")
            _prio_row     = _prio_fragile.iloc[0] if not _prio_fragile.empty else (
                            _prio_consol.iloc[0]  if not _prio_consol.empty  else None)

            if _prio_row is not None:
                st.divider()
                _pct    = round(float(_prio_row["avg_score"]) * 100)
                _n      = int(_prio_row["attempts_count"])
                _status = _prio_row.get("review_status", "—")
                _retard = "⚠ En retard" if _status == "En retard" else _status
                with st.container(border=True):
                    st.markdown("🔴 **Révision prioritaire**")
                    st.markdown(
                        f"**{_prio_row['section_label']}** · _{_prio_row['document_title']}_  \n"
                        f"Score : **{_pct} %** · {_n} tentative{'s' if _n > 1 else ''} · {_retard}"
                    )
                    # TASK-028c — raisons algorithmiques
                    for _w in explain_priority_decision(_prio_row):
                        st.caption(f"· {_w}")
                    # TASK-028b — explication de l'intervalle adaptatif
                    _ivl_expl = explain_interval_decision(
                        str(_prio_row.get("mastery_class") or ""),
                        str(_prio_row.get("trend") or "N/A"),
                    )
                    if _ivl_expl:
                        st.caption(f"⏱ {_ivl_expl}")

        st.divider()

        # ── Zone 3 : Cartes de section ────────────────────────────────────────
        st.markdown(
            "<p style='font-size:12px;font-weight:700;color:#475569;margin:0 0 8px;"
            "text-transform:uppercase;letter-spacing:.07em'>Progression par section</p>",
            unsafe_allow_html=True,
        )
        if not df_chunks.empty:
            _BADGE = {
                "Fragile":          ("🔴", "FRAGILE"),
                "En consolidation": ("🟡", "EN CONSOLIDATION"),
                "Maîtrisé":         ("🟢", "MAÎTRISÉ"),
            }
            df_ordered = pd.concat([
                df_chunks[df_chunks["mastery_class"] == "Fragile"].sort_values("avg_score"),
                df_chunks[df_chunks["mastery_class"] == "En consolidation"].sort_values("avg_score"),
                df_chunks[df_chunks["mastery_class"] == "Maîtrisé"],
            ])
            _ncols = min(len(df_ordered), 3)
            _card_cols = st.columns(_ncols)
            for i, (_, r) in enumerate(df_ordered.iterrows()):
                _icon, _badge = _BADGE.get(r["mastery_class"], ("⚪", r["mastery_class"].upper()))
                _pct  = round(float(r["avg_score"]) * 100)
                _n    = int(r["attempts_count"])
                _st   = r.get("review_status", "—")
                _ms_icon, _ms_label, _ms_color = _mastery_state(r)
                _dom_err = r.get("dominant_error_type") or ""
                with _card_cols[i % _ncols]:
                    with st.container(border=True):
                        st.markdown(f"{_icon} **{_badge}**")
                        st.markdown(f"**{r['section_label']}**")
                        st.progress(min(float(r["avg_score"]), 1.0), text=f"{_pct} %")
                        st.markdown(
                            f'<span style="font-size:11px;font-weight:600;color:{_ms_color}">'
                            f'{_ms_icon} {_ms_label}</span>',
                            unsafe_allow_html=True,
                        )
                        if _dom_err and _dom_err != "correct":
                            st.caption(
                                f"Erreur : {_ERROR_LABELS.get(_dom_err, _dom_err)}"
                                f" · {_n} tent. · {_st}"
                            )
                        else:
                            st.caption(f"{_n} tentative{'s' if _n > 1 else ''} · {_st}")
                        # TASK-028b — explication de l'intervalle adaptatif
                        _ivl = explain_interval_decision(
                            str(r.get("mastery_class") or ""),
                            str(r.get("trend") or "N/A"),
                        )
                        if _ivl:
                            st.caption(f"⏱ {_ivl}")
        else:
            st.info(
                "Aucune donnée par section disponible. "
                "Effectuez des tentatives en mode RAG (document importé avec embeddings)."
            )

        st.divider()

        # ── Zone 4a : Évolution des scores ────────────────────────────────────
        st.markdown(
            "<p style='font-size:12px;font-weight:700;color:#475569;margin:0 0 6px;"
            "text-transform:uppercase;letter-spacing:.07em'>Évolution des scores</p>",
            unsafe_allow_html=True,
        )
        df_evol = get_score_evolution(limit=20, user_id=st.session_state["user_id"])
        if not df_evol.empty:
            df_line = df_evol[["score"]].copy()
            df_line["Score (%)"] = (df_line["score"] * 100).round().astype(int)
            df_line["Tentative"] = range(1, len(df_line) + 1)
            st.line_chart(df_line, x="Tentative", y="Score (%)", height=210)
            st.caption(f"{len(df_evol)} dernières tentatives — ordre chronologique")

        st.divider()

        col_left, col_right = st.columns(2)

        # ── Zone 4b : Score moyen par notion ──────────────────────────────────
        with col_left:
            st.markdown(
                "<p style='font-size:12px;font-weight:700;color:#475569;margin:0 0 6px;"
                "text-transform:uppercase;letter-spacing:.07em'>Score moyen par notion</p>",
                unsafe_allow_html=True,
            )
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
                        "Bon":     "#16a34a",
                        "Moyen":   "#d97706",
                        "Fragile": "#dc2626",
                    },
                    custom_data=["topic", "attempts"],
                    height=max(200, len(df_plot) * 44),
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

        # ── Zone 4c : Types d'erreurs ─────────────────────────────────────────
        with col_right:
            st.markdown(
                "<p style='font-size:12px;font-weight:700;color:#475569;margin:0 0 6px;"
                "text-transform:uppercase;letter-spacing:.07em'>Types d'erreurs fréquents</p>",
                unsafe_allow_html=True,
            )
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
                    color_discrete_sequence=["#6366f1"],
                    custom_data=["label"],
                    height=max(200, len(df_errors) * 44),
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

        # ── Zone 4d : Mini-timeline ───────────────────────────────────────────
        st.markdown(
            "<p style='font-size:12px;font-weight:700;color:#475569;margin:8px 0 6px;"
            "text-transform:uppercase;letter-spacing:.07em'>Parcours récent</p>",
            unsafe_allow_html=True,
        )
        _recent = df_all.head(8)
        _tl_items = []
        for _, _row in _recent.iterrows():
            try:
                _sv = float(_row["score"])
            except (TypeError, ValueError):
                _sv = 0.0
            _col = "#16a34a" if _sv >= 0.8 else ("#d97706" if _sv >= 0.5 else "#dc2626")
            _topic_short = (_row["topic"] or "—")[:18]
            _date_short  = str(_row["created_at"])[:10] if _row["created_at"] else "—"
            _tl_items.append(
                f'<div style="border:1px solid {_col};border-radius:8px;padding:5px 10px;'
                f'background:{_col}12;text-align:center;min-width:58px;flex-shrink:0">'
                f'<div style="font-size:13px;font-weight:700;color:{_col}">{round(_sv*100)}%</div>'
                f'<div style="font-size:10px;color:#64748b;margin-top:1px">{_topic_short}</div>'
                f'<div style="font-size:9px;color:#94a3b8">{_date_short}</div>'
                f'</div>'
            )
        st.markdown(
            '<div style="display:flex;gap:5px;flex-wrap:wrap;align-items:flex-start">'
            + "".join(_tl_items)
            + "</div>",
            unsafe_allow_html=True,
        )

        st.divider()

        # ── Zone 5 : Analyse pédagogique dynamique ────────────────────────────
        _n_fragile  = int((df_chunks["mastery_class"] == "Fragile").sum()) if not df_chunks.empty else 0
        _n_maitrise = int((df_chunks["mastery_class"] == "Maîtrisé").sum()) if not df_chunks.empty else 0
        _n_progress = int((df_chunks["trend"] == "Amélioration").sum()) if not df_chunks.empty else 0
        _n_regress  = int((df_chunks["trend"] == "Dégradation").sum()) if not df_chunks.empty else 0

        _analyse = []
        if _n_fragile:
            _analyse.append(f"⚡ {_n_fragile} section{'s' if _n_fragile > 1 else ''} fragile{'s' if _n_fragile > 1 else ''} — révision prioritaire active, types reformulation/conséquence priorisés")
        if _n_progress:
            _analyse.append(f"📈 {_n_progress} section{'s' if _n_progress > 1 else ''} en progression — consolidation détectée")
        if _n_regress:
            _analyse.append(f"📉 {_n_regress} section{'s' if _n_regress > 1 else ''} en régression — adaptation du type de question en cours")
        if _n_maitrise:
            _analyse.append(f"✅ {_n_maitrise} section{'s' if _n_maitrise > 1 else ''} maîtrisée{'s' if _n_maitrise > 1 else ''} — questions pièges et cas pratiques activés")
        if not df_errors.empty:
            _te = df_errors.iloc[0]
            _analyse.append(f"🔍 Erreur dominante : \"{_ERROR_LABELS.get(_te['error_type'], _te['error_type'])}\" ({int(_te['count'])} occurrences) — notion sensible identifiée")

        if _analyse:
            st.info("**Analyse pédagogique — Moteur adaptatif**  \n" + "  \n".join(_analyse))

        # ── Zone 7 : Profil d'apprentissage ──────────────────────────────────
        st.markdown(
            "<p style='font-size:12px;font-weight:700;color:#475569;margin:0 0 8px;"
            "text-transform:uppercase;letter-spacing:.07em'>Profil d'apprentissage</p>",
            unsafe_allow_html=True,
        )

        _SCORE_GROUPS = [
            ("📐", "Analytique",  "logical_score",    "#0f172a"),
            ("⚙️",  "Procédural",  "procedural_score", "#0f172a"),
            ("📝", "Narratif",    "narrative_score",  "#0f172a"),
            ("🔀", "Analogique",  "analogy_score",    "#0f172a"),
        ]
        _PEDAGOGY_FR = {
            "logical":    "Analytique",
            "procedural": "Procédural",
            "narrative":  "Narratif",
            "analogy":    "Analogique",
        }

        _profile = get_learning_profile(st.session_state["user_id"])

        if _profile is not None:
            _pg1, _pg2, _pg3, _pg4 = st.columns(4)
            for _gcol, (icon, label, key, _) in zip(
                (_pg1, _pg2, _pg3, _pg4), _SCORE_GROUPS
            ):
                _s = float(_profile.get(key) or 0.0)
                _pct_str = f"{round(_s * 100)} %" if _s > 0 else "—"
                _accent = (
                    "#15803d" if _s >= 0.8
                    else "#b45309" if _s >= 0.6
                    else "#b91c1c" if _s > 0
                    else "#94a3b8"
                )
                _gcol.markdown(
                    _kpi_card(icon, label, _pct_str, _accent),
                    unsafe_allow_html=True,
                )

            _pref = _profile.get("preferred_pedagogy")
            _pref_label = _PEDAGOGY_FR.get(_pref, _pref) if _pref else None
            _fragile = _profile.get("fragile_topics") or []
            _avg = float(_profile.get("average_score") or 0.0)

            _profile_lines = []
            if _pref_label:
                _profile_lines.append(f"**Style dominant :** {_pref_label}")
            if _avg > 0:
                _profile_lines.append(f"**Score global :** {round(_avg * 100)} %")
            if _profile_lines:
                st.markdown("  ·  ".join(_profile_lines))
            if _fragile:
                st.caption("Notions fragiles : " + " · ".join(_fragile))
            # TASK-028d — explication du profil détecté
            _prof_expl = explain_profile_detection(_profile)
            if _prof_expl:
                st.caption(_prof_expl)
        else:
            st.info(
                "Profil non encore calculé. "
                "Cliquez sur **Calculer le profil** pour générer votre analyse."
            )

        if st.button(
            "Recalculer le profil" if _profile is not None else "Calculer le profil",
            key="btn_recompute_profile",
        ):
            compute_and_save_learning_profile(st.session_state["user_id"])
            st.rerun()

        st.divider()

        # ── Zone 6 : Export ───────────────────────────────────────────────────
        _report_txt = _build_report(df_all, df_topics, df_chunks)
        _fname = f"rapport_progression_{datetime.now().strftime('%Y%m%d')}.txt"
        st.download_button(
            "Télécharger le rapport de progression",
            data=_report_txt.encode("utf-8"),
            file_name=_fname,
            mime="text/plain",
        )


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
            label    = f"📄 {doc['title']}  ·  {doc['source_type'].upper()}  ·  {int(doc['chunk_count'])} section{'s' if doc['chunk_count'] != 1 else ''}  ·  {str(doc['created_at'])[:16]}"
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
                        f"Indexer les embeddings ({missing} section{'s' if missing > 1 else ''} manquante{'s' if missing > 1 else ''})",
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


# ── Onglet Moteur IA ─────────────────────────────────────────────────────────

with tab_engine:
    st.markdown(
        "<h3 style='margin:0 0 2px;color:#1e293b;font-size:18px'>Comment fonctionne ce moteur ?</h3>"
        "<p style='color:#64748b;font-size:13px;margin:0 0 10px'>"
        "Un pipeline en 7 étapes transforme vos documents métier en révision adaptative et personnalisée."
        "</p>",
        unsafe_allow_html=True,
    )

    # ── Pipeline 7 étapes — grille 2 colonnes ────────────────────────────────
    st.markdown(
        "<p style='font-size:13px;font-weight:700;color:#1e293b;margin:0 0 6px;text-transform:uppercase;"
        "letter-spacing:.05em'>Pipeline pédagogique</p>",
        unsafe_allow_html=True,
    )
    _pipe_data = [
        ("📄", "Document",         "Importez un PDF ou TXT. Extraction, nettoyage et découpage en sections logiques."),
        ("🔍", "RAG",              "Embeddings sémantiques par section. Retrieval par similarité cosinus lors de chaque session."),
        ("❓", "Question",         "Générée depuis la section pertinente, avec un type adapté à votre maîtrise actuelle."),
        ("✍️", "Réponse libre",    "Réponse en langage naturel. Temps de réponse mesuré, historique complet conservé."),
        ("✅", "Correction IA",    "Score, diagnostic d'erreur et explication ancrés dans le contenu source du document."),
        ("🧠", "Mémoire",          "Résultats enregistrés : score, notion, type d'erreur, section source, date."),
        ("🔄", "Révision prioritaire", "Prochaine révision calculée selon la maîtrise et l'algorithme de répétition espacée."),
    ]
    _pipe_html = "".join(
        f'<div style="border:1px solid #e2e8f0;border-radius:8px;padding:10px 13px;background:#fafbfc">'
        f'<div style="font-size:17px;margin-bottom:3px">{ic}</div>'
        f'<div style="font-size:12px;font-weight:600;color:#1e293b;margin-bottom:2px">{ti}</div>'
        f'<div style="font-size:11.5px;color:#64748b;line-height:1.4">{de}</div>'
        f'</div>'
        for ic, ti, de in _pipe_data
    )
    st.markdown(
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-bottom:14px">'
        f'{_pipe_html}</div>',
        unsafe_allow_html=True,
    )

    st.divider()

    # ── 6 types de questions — grille 3 colonnes ─────────────────────────────
    st.markdown(
        "<p style='font-size:13px;font-weight:700;color:#1e293b;margin:0 0 2px;text-transform:uppercase;"
        "letter-spacing:.05em'>6 types de questions adaptatives</p>"
        "<p style='font-size:12px;color:#64748b;margin:0 0 7px'>"
        "Le type est sélectionné automatiquement selon la maîtrise détectée pour chaque section.</p>",
        unsafe_allow_html=True,
    )
    _qt_data = [
        ("❶", "Question directe",  "Restitution directe d'une information clé.",                             "#f0f9ff", "#0369a1"),
        ("❷", "Reformulation",     "Expliquer avec ses mots — prioritaire pour les sections fragiles.",      "#fdf4ff", "#7e22ce"),
        ("❸", "Conséquence",       "Enchaînements logiques et conditions d'application.",                    "#fff7ed", "#c2410c"),
        ("❹", "Cas pratique",      "Application des règles en situation concrète.",                          "#f0fdf4", "#15803d"),
        ("❺", "Vrai / Faux",       "Distinguer vrai et faux — précision des connaissances.",                 "#f8fafc", "#475569"),
        ("❻", "Question piège",    "Formulations trompeuses — réservé aux sections maîtrisées.",             "#fef2f2", "#991b1b"),
    ]
    _qt_html = "".join(
        f'<div style="border:1px solid #e2e8f0;border-radius:8px;padding:10px 12px;background:{bg}">'
        f'<div style="font-size:11px;font-weight:700;color:{ac};text-transform:uppercase;'
        f'letter-spacing:.04em;margin-bottom:3px">{num} {lbl}</div>'
        f'<div style="font-size:11.5px;color:#475569;line-height:1.35">{dsc}</div>'
        f'</div>'
        for num, lbl, dsc, bg, ac in _qt_data
    )
    st.markdown(
        f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:7px;margin-bottom:14px">'
        f'{_qt_html}</div>',
        unsafe_allow_html=True,
    )

    st.divider()

    # ── Répétition espacée + Adaptation cognitive — 2 colonnes ───────────────
    _col_rep, _col_adp = st.columns(2)

    with _col_rep:
        st.markdown(
            "<p style='font-size:13px;font-weight:700;color:#1e293b;margin:0 0 7px;"
            "text-transform:uppercase;letter-spacing:.05em'>Répétition espacée</p>",
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:7px">'
            '<div style="border:1px solid #fca5a5;border-radius:8px;padding:10px 8px;'
            'background:#fef2f2;text-align:center">'
            '<div style="font-size:18px">🔴</div>'
            '<div style="font-size:12px;font-weight:700;color:#991b1b;margin:3px 0">Fragile</div>'
            '<div style="font-size:11px;color:#b91c1c">Rappel · 1 j</div></div>'
            '<div style="border:1px solid #fde68a;border-radius:8px;padding:10px 8px;'
            'background:#fffbeb;text-align:center">'
            '<div style="font-size:18px">🟡</div>'
            '<div style="font-size:12px;font-weight:700;color:#92400e;margin:3px 0">Consolidation</div>'
            '<div style="font-size:11px;color:#b45309">Rappel · 3 j</div></div>'
            '<div style="border:1px solid #86efac;border-radius:8px;padding:10px 8px;'
            'background:#f0fdf4;text-align:center">'
            '<div style="font-size:18px">🟢</div>'
            '<div style="font-size:12px;font-weight:700;color:#166534;margin:3px 0">Maîtrisé</div>'
            '<div style="font-size:11px;color:#15803d">Rappel · 7 j</div></div>'
            '</div>',
            unsafe_allow_html=True,
        )

    with _col_adp:
        st.markdown(
            "<p style='font-size:13px;font-weight:700;color:#1e293b;margin:0 0 7px;"
            "text-transform:uppercase;letter-spacing:.05em'>Adaptation cognitive</p>",
            unsafe_allow_html=True,
        )
        st.info(
            "🔴 **Fragile** → reformulation, conséquence  \n"
            "🟡 **En consolidation** → types variés  \n"
            "🟢 **Maîtrisé** → questions pièges, cas pratiques"
        )


# ── Onglet Formateur ─────────────────────────────────────────────────────────

with tab_formateur:
    st.markdown(
        "<h4 style='margin:0 0 4px;color:#0f172a;font-size:15px;font-weight:700;"
        "letter-spacing:-0.01em'>Vue formateur</h4>"
        "<p style='color:#64748b;font-size:12px;margin:0 0 12px'>"
        "Synthèse pédagogique de la progression — lecture superviseur.</p>",
        unsafe_allow_html=True,
    )

    _f_all = get_attempts(user_id=st.session_state["user_id"])

    if len(_f_all) < 2:
        st.info("Effectuez au moins 2 tentatives pour afficher la vue formateur.")
    else:
        _f_chunks  = classify_mastery(get_chunk_stats(user_id=st.session_state["user_id"]))
        _f_docs    = get_documents()

        # ── Zone F1 : KPIs formateur ─────────────────────────────────────────
        _f_scores    = _f_all["score"].dropna()
        _f_times     = _f_all["response_time_seconds"].dropna()
        _days_active = _f_all["created_at"].apply(lambda x: str(x)[:10]).nunique()
        _total_chunks  = int(_f_docs["chunk_count"].sum()) if not _f_docs.empty else 0
        _tested_chunks = len(_f_chunks)
        _avg_score     = float(_f_scores.mean()) if len(_f_scores) else 0.0
        _score_color   = "#15803d" if _avg_score >= 0.8 else ("#b45309" if _avg_score >= 0.6 else "#b91c1c")

        _fc1, _fc2, _fc3, _fc4 = st.columns(4)
        _fc1.markdown(
            _kpi_card("📋", "Tentatives", str(len(_f_all))),
            unsafe_allow_html=True,
        )
        _fc2.markdown(
            _kpi_card("🎯", "Score moyen",
                      f"{round(_avg_score * 100)} %" if len(_f_scores) else "—",
                      _score_color),
            unsafe_allow_html=True,
        )
        _fc3.markdown(
            _kpi_card("📅", "Jours d'étude", str(_days_active)),
            unsafe_allow_html=True,
        )
        if len(_f_times) >= 3:
            _fc4.markdown(
                _kpi_card("⏱", "Temps moyen / réponse", f"{round(float(_f_times.mean()))} s"),
                unsafe_allow_html=True,
            )
        else:
            _cov_str = f"{_tested_chunks} / {_total_chunks}" if _total_chunks else "—"
            _fc4.markdown(
                _kpi_card("📐", "Sections testées", _cov_str),
                unsafe_allow_html=True,
            )

        st.divider()

        # ── Zone F2 : Synthèse narrative ─────────────────────────────────────
        st.markdown(
            "<p style='font-size:12px;font-weight:700;color:#475569;margin:0 0 8px;"
            "text-transform:uppercase;letter-spacing:.07em'>Synthèse pédagogique</p>",
            unsafe_allow_html=True,
        )

        _TYPE_FR_FORM = {
            "question_directe": "questions directes",
            "cas_pratique":     "cas pratiques",
            "vrai_faux":        "vrai / faux",
            "question_piege":   "questions pièges",
            "reformulation":    "reformulations",
            "consequence":      "conséquences",
        }

        _f_lines: list[tuple[str, str]] = []

        # Régularité
        if _days_active >= 5:
            _f_lines.append(("🟢", f"Révision régulière : <b>{_days_active} jours d'étude</b> enregistrés."))
        elif _days_active >= 2:
            _f_lines.append(("🟡", f"<b>{_days_active} jours d'étude</b> enregistrés — effort en cours."))
        else:
            _f_lines.append(("🔵", "Démarrage récent — première journée d'étude enregistrée."))

        # Niveau global
        if len(_f_scores):
            if _avg_score >= 0.8:
                _f_lines.append(("🟢", f"Niveau global <b>excellent</b> — score moyen de {round(_avg_score * 100)} %."))
            elif _avg_score >= 0.6:
                _f_lines.append(("🟡", f"Niveau global <b>correct</b> — score moyen de {round(_avg_score * 100)} %, marge de progression identifiée."))
            else:
                _f_lines.append(("🔴", f"Niveau global <b>fragile</b> — score moyen de {round(_avg_score * 100)} %, accompagnement recommandé."))

        # Format le plus efficace
        if "pedagogy_type" in _f_all.columns:
            _type_avgs = (
                _f_all.dropna(subset=["pedagogy_type", "score"])
                .groupby("pedagogy_type")["score"]
                .mean()
            )
            if not _type_avgs.empty:
                _best_t = _type_avgs.idxmax()
                _best_s = round(_type_avgs.max() * 100)
                _f_lines.append(("🔵", f"Format le plus réussi : <b>{_TYPE_FR_FORM.get(_best_t, _best_t)}</b> ({_best_s} % de score moyen)."))

        # Section prioritaire
        if not _f_chunks.empty:
            _frag_rows = _f_chunks[_f_chunks["mastery_class"] == "Fragile"].sort_values("avg_score")
            if not _frag_rows.empty:
                _top_f = _frag_rows.iloc[0]
                _f_lines.append(("🔴", f"Section prioritaire : <b>{_top_f['section_label']}</b> — {round(float(_top_f['avg_score']) * 100)} % de score moyen, révision immédiate recommandée."))
            else:
                _n_ok = int((_f_chunks["mastery_class"] == "Maîtrisé").sum())
                if _n_ok:
                    _f_lines.append(("🟢", f"<b>{_n_ok} section{'s' if _n_ok > 1 else ''} maîtrisée{'s' if _n_ok > 1 else ''}</b> — bon niveau général."))

        # Temps de réponse
        if len(_f_times) >= 3:
            _at = float(_f_times.mean())
            if _at < 30:
                _f_lines.append(("🔵", f"Temps de réponse moyen : <b>{round(_at)} s</b> — réactivité élevée."))
            elif _at < 90:
                _f_lines.append(("🔵", f"Temps de réponse moyen : <b>{round(_at)} s</b> — réflexion approfondie."))
            else:
                _f_lines.append(("🟡", f"Temps de réponse moyen : <b>{round(_at)} s</b> — difficulté de formulation possible."))

        _synth_html = "".join(
            f'<div style="display:flex;align-items:flex-start;gap:10px;padding:8px 14px;'
            f'background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;margin-bottom:5px">'
            f'<span style="font-size:14px;flex-shrink:0;margin-top:1px">{dot}</span>'
            f'<span style="font-size:12.5px;color:#1e293b;line-height:1.5">{txt}</span>'
            f'</div>'
            for dot, txt in _f_lines
        )
        st.markdown(_synth_html, unsafe_allow_html=True)

        st.divider()

        # ── Zone F3 : Efficacité par type de question ─────────────────────────
        if "pedagogy_type" in _f_all.columns:
            _ftype_df = (
                _f_all.dropna(subset=["pedagogy_type", "score"])
                .groupby("pedagogy_type")
                .agg(avg_score=("score", "mean"), count=("score", "count"))
                .reset_index()
                .sort_values("avg_score", ascending=False)
            )
            if not _ftype_df.empty:
                st.markdown(
                    "<p style='font-size:12px;font-weight:700;color:#475569;margin:0 0 8px;"
                    "text-transform:uppercase;letter-spacing:.07em'>Efficacité par type de question</p>",
                    unsafe_allow_html=True,
                )
                _TYPE_ICONS_F = {
                    "question_directe": "📖",
                    "cas_pratique":     "⚙️",
                    "vrai_faux":        "✅",
                    "question_piege":   "🎯",
                    "reformulation":    "📝",
                    "consequence":      "🔗",
                }
                _TYPE_LABELS_F = {
                    "question_directe": "Question directe",
                    "cas_pratique":     "Cas pratique",
                    "vrai_faux":        "Vrai / Faux",
                    "question_piege":   "Question piège",
                    "reformulation":    "Reformulation",
                    "consequence":      "Conséquence",
                }
                _ncols_f = min(len(_ftype_df), 3)
                _ft_cols = st.columns(_ncols_f)
                for _fi, (_, _frow) in enumerate(_ftype_df.iterrows()):
                    _ficon  = _TYPE_ICONS_F.get(_frow["pedagogy_type"], "📌")
                    _flabel = _TYPE_LABELS_F.get(_frow["pedagogy_type"], _frow["pedagogy_type"])
                    _fpct   = round(float(_frow["avg_score"]) * 100)
                    with _ft_cols[_fi % _ncols_f]:
                        with st.container(border=True):
                            st.markdown(f"{_ficon} **{_flabel}**")
                            st.progress(min(float(_frow["avg_score"]), 1.0), text=f"{_fpct} %")
                            st.caption(f"{int(_frow['count'])} tentative{'s' if _frow['count'] > 1 else ''}")

                st.divider()

        # ── Zone F4 : Couverture du corpus ────────────────────────────────────
        if not _f_docs.empty:
            st.markdown(
                "<p style='font-size:12px;font-weight:700;color:#475569;margin:0 0 8px;"
                "text-transform:uppercase;letter-spacing:.07em'>Couverture du corpus</p>",
                unsafe_allow_html=True,
            )
            for _, _fdoc in _f_docs.iterrows():
                _dc     = _f_chunks[_f_chunks["document_title"] == _fdoc["title"]] if not _f_chunks.empty else pd.DataFrame()
                _total  = int(_fdoc["chunk_count"]) if _fdoc["chunk_count"] else 0
                _tested = len(_dc)
                _frag_n = int((_dc["mastery_class"] == "Fragile").sum())          if not _dc.empty else 0
                _cons_n = int((_dc["mastery_class"] == "En consolidation").sum()) if not _dc.empty else 0
                _mait_n = int((_dc["mastery_class"] == "Maîtrisé").sum())         if not _dc.empty else 0
                _cov    = _tested / _total if _total > 0 else 0.0

                with st.container(border=True):
                    _dc1, _dc2 = st.columns([3, 1])
                    with _dc1:
                        st.markdown(f"**{_fdoc['title']}**")
                        _prog_text = (
                            f"{_tested} section{'s' if _tested != 1 else ''} testée{'s' if _tested != 1 else ''} / {_total}"
                            if _total else "Aucune section indexée"
                        )
                        st.progress(_cov, text=_prog_text)
                    with _dc2:
                        if _tested == 0:
                            st.caption("⚪ Non démarré")
                        else:
                            if _frag_n:
                                st.caption(f"🔴 {_frag_n} fragile{'s' if _frag_n > 1 else ''}")
                            if _cons_n:
                                st.caption(f"🟡 {_cons_n} en consolidation")
                            if _mait_n:
                                st.caption(f"🟢 {_mait_n} maîtrisée{'s' if _mait_n > 1 else ''}")
