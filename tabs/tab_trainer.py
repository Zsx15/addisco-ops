"""Onglet Formateur — synthèse pédagogique superviseur."""
import pandas as pd
import streamlit as st

from database import classify_mastery, get_attempts, get_all_users, get_chunk_stats, get_documents
from auth_service import promote_user
from ui_helpers import _kpi_card, _truncate_label

_TYPE_FR_FORM = {
    "question_directe": "questions directes",
    "cas_pratique":     "cas pratiques",
    "vrai_faux":        "vrai / faux",
    "question_piege":   "questions pièges",
    "reformulation":    "reformulations",
    "consequence":      "conséquences",
}

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


_ROLE_LABELS_ADM = {"admin": "Administrateur", "formateur": "Formateur", "apprenant": "Apprenant"}
_PROMO_OPTS      = {"apprenant": ["formateur", "admin"], "formateur": ["admin"], "admin": []}


def _render_admin_section() -> None:
    if st.session_state.get("role") != "admin":
        return
    st.divider()
    st.markdown(
        "<p style='font-size:12px;font-weight:700;color:#475569;margin:0 0 8px;"
        "text-transform:uppercase;letter-spacing:.07em'>Administration — Gestion des rôles</p>",
        unsafe_allow_html=True,
    )
    try:
        _users = get_all_users()
    except Exception:
        st.warning("Impossible de charger la liste des utilisateurs.")
        return
    _me = st.session_state.get("username", "")
    for _u in _users:
        _uname = _u["username"]
        _urole = _u["role"]
        _opts  = _PROMO_OPTS.get(_urole, [])
        with st.container(border=True):
            _col1, _col2, _col3 = st.columns([2, 1, 2])
            _col1.markdown(f"**{_uname}**")
            _col2.caption(_ROLE_LABELS_ADM.get(_urole, _urole))
            with _col3:
                if _uname == _me:
                    st.caption("*(vous)*")
                elif not _opts:
                    st.caption("—")
                else:
                    _sel = st.selectbox(
                        "Rôle cible",
                        options=_opts,
                        key=f"promo_sel_{_uname}",
                        label_visibility="collapsed",
                        format_func=lambda r: _ROLE_LABELS_ADM.get(r, r),
                    )
                    if st.button("Promouvoir", key=f"promo_btn_{_uname}", type="primary"):
                        try:
                            promote_user(_me, _uname, _sel)
                            st.success(f"{_uname} promu {_ROLE_LABELS_ADM.get(_sel, _sel)}.")
                            st.rerun()
                        except ValueError as _ve:
                            st.error(str(_ve))


def render() -> None:
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
        _render_admin_section()
        return

    _f_chunks = classify_mastery(get_chunk_stats(user_id=st.session_state["user_id"]))
    _f_docs   = get_documents()

    # ── Zone F1 : KPIs formateur ─────────────────────────────────────────
    _f_scores    = _f_all["score"].dropna()
    _f_times     = _f_all["response_time_seconds"].dropna()
    _days_active = _f_all["created_at"].apply(lambda x: str(x)[:10]).nunique()
    _total_chunks  = int(_f_docs["chunk_count"].sum()) if not _f_docs.empty else 0
    _tested_chunks = len(_f_chunks)
    _avg_score     = float(_f_scores.mean()) if len(_f_scores) else 0.0
    _score_color   = "#15803d" if _avg_score >= 0.8 else ("#b45309" if _avg_score >= 0.6 else "#b91c1c")

    _fc1, _fc2, _fc3, _fc4 = st.columns(4)
    _fc1.markdown(_kpi_card("📋", "Tentatives", str(len(_f_all))), unsafe_allow_html=True)
    _fc2.markdown(
        _kpi_card("🎯", "Score moyen",
                  f"{round(_avg_score * 100)} %" if len(_f_scores) else "—",
                  _score_color),
        unsafe_allow_html=True,
    )
    _fc3.markdown(_kpi_card("📅", "Jours d'étude", str(_days_active)), unsafe_allow_html=True)
    if len(_f_times) >= 3:
        _fc4.markdown(
            _kpi_card("⏱", "Temps moyen / réponse", f"{round(float(_f_times.mean()))} s"),
            unsafe_allow_html=True,
        )
    else:
        _cov_str = f"{_tested_chunks} / {_total_chunks}" if _total_chunks else "—"
        _fc4.markdown(_kpi_card("📐", "Sections testées", _cov_str), unsafe_allow_html=True)

    st.divider()

    # ── Zone F2 : Synthèse narrative ─────────────────────────────────────
    st.markdown(
        "<p style='font-size:12px;font-weight:700;color:#475569;margin:0 0 8px;"
        "text-transform:uppercase;letter-spacing:.07em'>Synthèse pédagogique</p>",
        unsafe_allow_html=True,
    )

    _f_lines: list[tuple[str, str]] = []

    if _days_active >= 5:
        _f_lines.append(("🟢", f"Révision régulière : <b>{_days_active} jours d'étude</b> enregistrés."))
    elif _days_active >= 2:
        _f_lines.append(("🟡", f"<b>{_days_active} jours d'étude</b> enregistrés — effort en cours."))
    else:
        _f_lines.append(("🔵", "Démarrage récent — première journée d'étude enregistrée."))

    if len(_f_scores):
        if _avg_score >= 0.8:
            _f_lines.append(("🟢", f"Niveau global <b>excellent</b> — score moyen de {round(_avg_score * 100)} %."))
        elif _avg_score >= 0.6:
            _f_lines.append(("🟡", f"Niveau global <b>correct</b> — score moyen de {round(_avg_score * 100)} %, marge de progression identifiée."))
        else:
            _f_lines.append(("🔴", f"Niveau global <b>fragile</b> — score moyen de {round(_avg_score * 100)} %, accompagnement recommandé."))

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

    if not _f_chunks.empty:
        _frag_rows = _f_chunks[_f_chunks["mastery_class"] == "Fragile"].sort_values("avg_score")
        if not _frag_rows.empty:
            _top_f = _frag_rows.iloc[0]
            _f_lines.append(("🔴", f"Section prioritaire : <b>{_top_f['section_label']}</b> — {round(float(_top_f['avg_score']) * 100)} % de score moyen, révision immédiate recommandée."))
        else:
            _n_ok = int((_f_chunks["mastery_class"] == "Maîtrisé").sum())
            if _n_ok:
                _f_lines.append(("🟢", f"<b>{_n_ok} section{'s' if _n_ok > 1 else ''} maîtrisée{'s' if _n_ok > 1 else ''}</b> — bon niveau général."))

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

    _render_admin_section()
