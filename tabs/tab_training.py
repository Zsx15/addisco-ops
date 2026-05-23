"""Onglet Entraînement — génération de question, réponse, correction."""
import time
from datetime import datetime
from typing import Optional

import streamlit as st

from ai_service import correct_answer, explain_type_choice, generate_question
from database import (
    classify_mastery,
    compute_and_save_learning_profile,
    get_chunk_by_id,
    get_chunk_mastery,
    get_chunk_question_history,
    get_chunk_stats,
    get_document_by_id,
    get_documents,
    get_last_attempt_id,
    get_learning_profile,
    get_revision_suggestion,
    save_attempt,
    save_attempt_feedback,
    save_recommendation_feedback,
)
from db.sessions import start_session, close_session, log_event as _log_event
from db.corpus import get_corpus_documents
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

# Sentinels : jamais des AUTOINCREMENT SQLite valides
_CORPUS       = -1   # tous les documents
_NAMED_CORPUS = -2   # corpus personnalisé actif


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
    # ── Corpus actif ─────────────────────────────────────────────────────
    _active_corpus_id   = st.session_state.get("active_corpus_id")
    _active_corpus_name = st.session_state.get("active_corpus_name", "")
    _corpus_doc_ids: Optional[list[int]] = None
    if _active_corpus_id:
        _corpus_doc_ids = get_corpus_documents(_active_corpus_id) or None
        if _corpus_doc_ids:
            st.markdown(
                f'<div style="background:rgba(124,58,237,0.08);border:1px solid rgba(124,58,237,0.28);'
                f'border-radius:10px;padding:8px 14px;margin-bottom:12px;font-size:13px;'
                f'color:#A78BFA;display:flex;align-items:center;gap:8px">'
                f'<span>📚</span>'
                f'<span><b>{_active_corpus_name}</b> — {len(_corpus_doc_ids)} document{"s" if len(_corpus_doc_ids) != 1 else ""} actifs</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── Suggestion de révision ───────────────────────────────────────────
    suggestion = get_revision_suggestion(
        user_id=st.session_state["user_id"],
        document_ids=_corpus_doc_ids,
    )
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
    _cat_sel: Optional[str] = None
    if not _df_docs.empty:
        # Filtre catégorie (masqué si aucune catégorie définie)
        _cats = sorted(c for c in _df_docs["category"].dropna().unique() if str(c).strip())
        if _cats:
            _cat_opts = ["Toutes les catégories"] + _cats
            _cat_sel  = st.selectbox("Catégorie", _cat_opts, key="train_filter_category")
            if _cat_sel != "Toutes les catégories":
                _df_docs = _df_docs[_df_docs["category"] == _cat_sel]

        # Corpus label selon le filtre actif
        _n_docs = len(_df_docs)
        if _cat_sel and _cat_sel != "Toutes les catégories":
            _corpus_label = f"📚 Corpus catégorie : {_cat_sel} ({_n_docs} docs)"
        else:
            _corpus_label = f"📚 Corpus complet ({_n_docs} docs)"

        # Option corpus nommé actif
        _named_corpus_label = (
            f"🎯 {_active_corpus_name} ({len(_corpus_doc_ids)} docs)"
            if _corpus_doc_ids else None
        )

        _doc_ids = [None]
        if _named_corpus_label:
            _doc_ids.append(_NAMED_CORPUS)
        _doc_ids.append(_CORPUS)
        _doc_ids += [int(r["id"]) for _, r in _df_docs.iterrows()]

        _doc_titles: dict = {None: "— Texte libre (sans RAG)", _CORPUS: _corpus_label}
        if _named_corpus_label:
            _doc_titles[_NAMED_CORPUS] = _named_corpus_label
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
        # Sync active_document_ids selon la sélection
        if _selected == _CORPUS:
            st.session_state["active_document_ids"] = [int(r["id"]) for _, r in _df_docs.iterrows()]
        elif _selected == _NAMED_CORPUS and _corpus_doc_ids:
            st.session_state["active_document_ids"] = _corpus_doc_ids
        else:
            st.session_state.pop("active_document_ids", None)

        if _selected != _active_id:
            if _selected is None:
                st.session_state["active_document_id"]    = None
                st.session_state["active_document_title"] = ""
                st.session_state["source_text_input"]     = ""
            elif _selected == _CORPUS:
                st.session_state["active_document_id"]    = _CORPUS
                st.session_state["active_document_title"] = _corpus_label
                st.session_state["source_text_input"]     = ""
            elif _selected == _NAMED_CORPUS:
                st.session_state["active_document_id"]    = _NAMED_CORPUS
                st.session_state["active_document_title"] = _named_corpus_label or _active_corpus_name
                st.session_state["active_document_ids"]   = _corpus_doc_ids or []
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

    _active_doc_id = st.session_state.get("active_document_id")
    if _active_doc_id in (_CORPUS, _NAMED_CORPUS):
        _corpus_ids = st.session_state.get("active_document_ids") or []
        _corpus_tag = f"🎯 {_active_corpus_name} —" if _active_doc_id == _NAMED_CORPUS and _active_corpus_name else "📚 Corpus —"
        st.caption(f"{_corpus_tag} {len(_corpus_ids)} document(s) · RAG multi-documents")
    elif _active_doc_id:
        _doc_title = st.session_state.get("active_document_title") or "Document importé"
        st.caption(f"Source : {_doc_title}")

    if len(source_text) > 6000:
        st.warning("Texte trop long — seuls les 6 000 premiers caractères seront utilisés.")

    # En mode corpus (nommé ou complet), le texte source vient du RAG — bouton autorisé même si vide
    _is_corpus = _active_doc_id in (_CORPUS, _NAMED_CORPUS)
    _btn_disabled = not (source_text.strip() or _is_corpus)
    if st.button("Générer une question", disabled=_btn_disabled):
        with st.spinner("Génération en cours…"):
            try:
                _gen_doc_ids = st.session_state.get("active_document_ids") if _is_corpus else None
                _gen_doc_id  = None if _is_corpus else st.session_state.get("active_document_id")
                question, chunk_ids, question_type, rag_chunks = generate_question(
                    source_text or " ",
                    document_id=_gen_doc_id,
                    document_ids=_gen_doc_ids,
                    user_id=st.session_state["user_id"],
                )
                st.session_state["question"]      = question
                st.session_state["chunk_ids"]     = chunk_ids
                st.session_state["question_type"] = question_type
                st.session_state["source_text"]   = source_text
                st.session_state["start_time"]    = time.time()
                st.session_state["result"]        = None
                st.session_state["answer_input"]  = ""
                # ── Session tracking ─────────────────────────────────────
                try:
                    if st.session_state.get("current_session_id") is None:
                        _corpus_id = st.session_state.get("active_corpus_id")
                        _sid = start_session(st.session_state["user_id"], corpus_id=_corpus_id)
                        st.session_state["current_session_id"] = _sid
                        st.session_state["session_scores"]      = []
                        st.session_state["session_error_types"] = []
                    _sid = st.session_state.get("current_session_id")
                    if _sid:
                        _log_event(_sid, "question_generated")
                except Exception:
                    pass
                if chunk_ids:
                    # Contexte RAG — enrichissement document_title via get_chunk_by_id
                    try:
                        _enriched = []
                        for _rc in rag_chunks:
                            _meta = get_chunk_by_id(_rc["id"])
                            if _meta:
                                _rc = {
                                    **_rc,
                                    "document_title": _meta.get("document_title") or "—",
                                    "section_title":  _meta.get("section_label") or _rc.get("section_title") or "—",
                                }
                            _enriched.append(_rc)
                        st.session_state["rag_chunks"] = _enriched
                        # Compat backward — clés individuelles du chunk primaire
                        _primary = _enriched[0] if _enriched else {}
                        _raw = _primary.get("chunk_text") or ""
                        st.session_state["source_chunk_text"]  = _raw[:300] + ("…" if len(_raw) > 300 else "")
                        st.session_state["source_chunk_title"] = _primary.get("section_title") or ""
                        st.session_state["source_doc_title"]   = _primary.get("document_title") or ""
                    except Exception:
                        st.session_state["rag_chunks"]         = []
                        st.session_state["source_chunk_text"]  = None
                        st.session_state["source_chunk_title"] = None
                        st.session_state["source_doc_title"]   = None
                    st.session_state["source_chunk_count"] = len(chunk_ids)
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
                    st.session_state["rag_chunks"]                = []
                    st.session_state["source_chunk_text"]         = None
                    st.session_state["source_chunk_title"]        = None
                    st.session_state["source_doc_title"]          = None
                    st.session_state["source_chunk_count"]        = 0
            except Exception as exc:
                st.error(f"Erreur lors de la génération : {exc}")

    if st.session_state["question"]:
        st.divider()

        _rag_chunks = st.session_state.get("rag_chunks") or []
        if _rag_chunks:
            _n = len(_rag_chunks)
            with st.expander("📄 Contexte RAG utilisé", expanded=False):
                st.caption(
                    f"📚 {_n} chunk{'s' if _n > 1 else ''} utilisé{'s' if _n > 1 else ''}"
                    " — similarité cosinus"
                )
                for _i, _rc in enumerate(_rag_chunks):
                    if _i > 0:
                        st.divider()
                    _score   = round((_rc.get("similarity") or 0) * 100)
                    _doc     = _rc.get("document_title") or "—"
                    _section = _rc.get("section_title") or ""
                    _full    = _rc.get("chunk_text") or ""
                    _excerpt = _full[:200] + ("…" if len(_full) > 200 else "")
                    _label   = "Source principale" if _i == 0 else f"Source {_i + 1}"
                    _c1, _c2 = st.columns([4, 1])
                    _c1.markdown(f"**{_label}** · {_doc}")
                    _c2.metric("Score RAG", f"{_score} %")
                    if _section:
                        st.caption(f"Section : {_section}")
                    if _excerpt:
                        st.markdown(f'> "{_excerpt}"')

        st.subheader("Question")
        st.info(st.session_state["question"])
        _q_type = st.session_state.get("question_type")
        _chunk_ids_q = st.session_state.get("chunk_ids") or []
        if st.session_state.get("active_document_id") == _CORPUS and _chunk_ids_q:
            _n_corpus = len(st.session_state.get("active_document_ids") or [])
            _mode = f"📚 Corpus ({_n_corpus} docs)"
        elif _chunk_ids_q:
            _mode = "RAG actif"
        else:
            _mode = "Texte brut"
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

                    _chunk_ids  = st.session_state.get("chunk_ids") or []
                    _save_doc_id = (
                        None
                        if st.session_state.get("active_document_id") == _CORPUS
                        else st.session_state.get("active_document_id")
                    )
                    _attempt_id = save_attempt(
                        question=st.session_state["question"],
                        user_answer=user_answer,
                        expected_answer=result.get("expected_answer", ""),
                        correction=result.get("correction", ""),
                        score=result.get("score", 0.0),
                        response_time_seconds=round(elapsed, 1),
                        error_type=result.get("error_type", ""),
                        topic=result.get("topic", ""),
                        pedagogy_type=st.session_state.get("question_type"),
                        document_id=_save_doc_id,
                        chunk_id=_chunk_ids[0] if _chunk_ids else None,
                        user_id=st.session_state["user_id"],
                    )
                    st.session_state["last_attempt_id"]      = _attempt_id
                    st.session_state["feedback_given"]       = False
                    st.session_state["session_answers_count"] = (
                        st.session_state.get("session_answers_count", 0) + 1
                    )
                    try:
                        _sid = st.session_state.get("current_session_id")
                        if _sid:
                            _s_val = float(result.get("score", 0) or 0)
                            _e_val = result.get("error_type") or ""
                            st.session_state.setdefault("session_scores", []).append(_s_val)
                            if _e_val:
                                st.session_state.setdefault("session_error_types", []).append(_e_val)
                            _log_event(_sid, "answer_submitted", {"score": round(_s_val, 2)})
                    except Exception:
                        pass
                    try:
                        compute_and_save_learning_profile(st.session_state["user_id"])
                    except Exception:
                        pass
                except Exception as exc:
                    st.error(f"Erreur lors de la correction : {exc}")
                else:
                    st.rerun()

    if st.session_state["result"]:
        result = st.session_state["result"]
        try:
            score = float(result.get("score", 0))
        except (TypeError, ValueError):
            score = 0.0
        response_time = st.session_state.get("response_time") or 0

        st.divider()
        st.subheader("Correction")

        _rejection_reason = result.get("rejection_reason")
        if _rejection_reason:
            _REJECTION_LABELS = {
                "empty":         "Réponse vide",
                "too_short":     "Réponse trop courte",
                "non_knowledge": "Réponse de non-savoir",
            }
            st.warning(result.get("correction", "Réponse non évaluable."))
            st.caption(
                f"Non évaluable · {_REJECTION_LABELS.get(_rejection_reason, _rejection_reason)}"
                " · Score 0 enregistré."
            )
        else:
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

        # ── Feedback qualitatif ───────────────────────────────────────────
        _fb_given = st.session_state.get("feedback_given", False)
        if not _fb_given:
            st.markdown(
                '<p style="font-size:13px;color:#64748B;margin:12px 0 6px">'
                "Cette question était-elle pertinente ?</p>",
                unsafe_allow_html=True,
            )
            _fc1, _fc2, _fc3 = st.columns([1, 1, 6])
            if _fc1.button("👍 Oui", key="fb_yes"):
                _aid = st.session_state.get("last_attempt_id") or get_last_attempt_id(st.session_state["user_id"])
                if _aid:
                    try:
                        save_attempt_feedback(_aid, 1)
                    except Exception:
                        pass
                st.session_state["feedback_given"] = True
                st.rerun()
            if _fc2.button("👎 Non", key="fb_no"):
                _aid = st.session_state.get("last_attempt_id") or get_last_attempt_id(st.session_state["user_id"])
                if _aid:
                    try:
                        save_attempt_feedback(_aid, 0)
                    except Exception:
                        pass
                st.session_state["feedback_given"] = True
                st.rerun()
        else:
            st.caption("Merci pour votre retour.")

        # ── Feedback session ─────────────────────────────────────────────
        _session_count   = st.session_state.get("session_answers_count", 0)
        _sess_fb_given   = st.session_state.get("session_feedback_given", False)
        _sess_fb_pending = st.session_state.get("session_fb_pending_score")

        if _session_count >= 3 and not _sess_fb_given:
            st.markdown(
                '<div style="background:rgba(30,30,50,0.6);border:1px solid rgba(124,58,237,0.25);'
                'border-radius:12px;padding:16px 18px;margin:16px 0 8px">'
                '<p style="font-size:14px;font-weight:600;color:#C4B5FD;margin:0 0 12px">'
                'Cette session vous a-t-elle aidé ?</p>',
                unsafe_allow_html=True,
            )
            if _sess_fb_pending is None:
                _sb1, _sb2, _sb3, _sb4 = st.columns([1, 1, 1, 5])
                if _sb1.button("👍 Oui", key="sfb_yes"):
                    st.session_state["session_fb_pending_score"] = 1.0
                    st.rerun()
                if _sb2.button("😐 Partiellement", key="sfb_partial"):
                    st.session_state["session_fb_pending_score"] = 0.5
                    st.rerun()
                if _sb3.button("👎 Non", key="sfb_no"):
                    st.session_state["session_fb_pending_score"] = 0.0
                    st.rerun()
            else:
                _SCORE_LABELS = {1.0: "👍 Oui", 0.5: "😐 Partiellement", 0.0: "👎 Non"}
                st.caption(f"Réponse : {_SCORE_LABELS.get(_sess_fb_pending, '—')}")
                _REASONS = [
                    "utile", "trop difficile", "trop facile",
                    "confus", "répétitif", "bonne progression", "fatigue", "autre",
                ]
                _reason_sel = st.radio(
                    "Pourquoi ? (facultatif)",
                    options=["—"] + _REASONS,
                    horizontal=True,
                    key="sfb_reason",
                    label_visibility="visible",
                )
                _rc1, _rc2 = st.columns([1, 4])
                if _rc1.button("Enregistrer", key="sfb_submit"):
                    _reason = _reason_sel if _reason_sel != "—" else None
                    try:
                        save_recommendation_feedback(
                            user_id=st.session_state["user_id"],
                            recommendation_type="session",
                            feedback_score=_sess_fb_pending,
                            feedback_reason=_reason,
                        )
                    except Exception:
                        pass
                    try:
                        _sid = st.session_state.get("current_session_id")
                        if _sid:
                            _sc = st.session_state.get("session_scores") or []
                            _er = st.session_state.get("session_error_types") or []
                            close_session(
                                _sid,
                                total_questions=st.session_state.get("session_answers_count", 0),
                                completed_questions=st.session_state.get("session_answers_count", 0),
                                avg_score=round(sum(_sc) / len(_sc), 2) if _sc else None,
                                dominant_error=max(set(_er), key=_er.count) if _er else None,
                                feedback_score=_sess_fb_pending,
                            )
                            _log_event(_sid, "feedback_submitted", {"score": _sess_fb_pending, "reason": _reason})
                            st.session_state["current_session_id"] = None
                    except Exception:
                        pass
                    st.session_state["session_feedback_given"]   = True
                    st.session_state["session_fb_pending_score"] = None
                    st.rerun()
                if _rc2.button("Passer", key="sfb_skip"):
                    try:
                        _sid = st.session_state.get("current_session_id")
                        if _sid:
                            _sc = st.session_state.get("session_scores") or []
                            _er = st.session_state.get("session_error_types") or []
                            close_session(
                                _sid,
                                total_questions=st.session_state.get("session_answers_count", 0),
                                completed_questions=st.session_state.get("session_answers_count", 0),
                                avg_score=round(sum(_sc) / len(_sc), 2) if _sc else None,
                                dominant_error=max(set(_er), key=_er.count) if _er else None,
                                feedback_score=_sess_fb_pending,
                            )
                            _log_event(_sid, "session_completed")
                            st.session_state["current_session_id"] = None
                    except Exception:
                        pass
                    st.session_state["session_feedback_given"]   = True
                    st.session_state["session_fb_pending_score"] = None
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        elif _sess_fb_given and _session_count >= 3:
            st.caption("Merci pour votre retour sur cette session.")

        def _reset_question():
            st.session_state["result"]          = None
            st.session_state["question"]        = None
            st.session_state["chunk_ids"]       = None
            st.session_state["rag_chunks"]      = []
            st.session_state["answer_input"]    = ""
            st.session_state["last_attempt_id"] = None
            st.session_state["feedback_given"]  = False

        st.button("Nouvelle question sur ce texte", on_click=_reset_question)
