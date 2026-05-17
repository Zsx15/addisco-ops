"""Onglet Entraînement — génération de question, réponse, correction."""
import time
from datetime import datetime

import streamlit as st

from ai_service import correct_answer, explain_type_choice, generate_question
from database import (
    classify_mastery,
    compute_and_save_learning_profile,
    get_chunk_mastery,
    get_chunk_question_history,
    get_chunk_stats,
    get_document_by_id,
    get_documents,
    get_learning_profile,
    get_revision_suggestion,
    save_attempt,
)
from ui_helpers import explain_question_decision

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
        st.session_state["source_text_input"]     = cleaned_text
        st.session_state["active_document_id"]    = doc_id
        st.session_state["active_document_title"] = doc_title
        st.session_state["question"]              = None
        st.session_state["result"]                = None
        st.session_state["answer_input"]          = ""
    return _cb


def render() -> None:
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
                        st.session_state["question_mastery"] = get_chunk_mastery(
                            chunk_ids[0], user_id=st.session_state["user_id"]
                        )
                        _cs  = classify_mastery(get_chunk_stats(user_id=st.session_state["user_id"]))
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
                        st.session_state["question_mastery"]      = None
                        st.session_state["question_chunk_trend"]  = "N/A"
                        st.session_state["question_chunk_days"]   = None
                        st.session_state["question_chunk_error"]  = None
                        st.session_state["question_chunk_status"] = "—"
                    try:
                        _hist = get_chunk_question_history(
                            chunk_ids[0], user_id=st.session_state["user_id"]
                        )
                        _used = [h["question_type"] for h in _hist if h.get("question_type")]
                        _prof = get_learning_profile(st.session_state["user_id"])
                        _pped = _prof.get("preferred_pedagogy") if _prof else None
                        st.session_state["question_type_reason"] = explain_type_choice(
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
                _c_trend    = st.session_state.get("question_chunk_trend", "N/A")
                _c_status   = st.session_state.get("question_chunk_status", "—")
                _c_error    = st.session_state.get("question_chunk_error")
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
                    st.session_state["result"]        = result
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
            st.caption(
                f"🧠 Résultat enregistré · Notion : {_topic_res} · Score : {round(score * 100)} %"
            )

        def _reset_question():
            st.session_state["result"]       = None
            st.session_state["question"]     = None
            st.session_state["chunk_ids"]    = None
            st.session_state["answer_input"] = ""

        st.button("Nouvelle question sur ce texte", on_click=_reset_question)
