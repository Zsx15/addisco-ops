"""Onglet Dashboard — KPIs, maîtrise par section, profil d'apprentissage, export."""
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from database import (
    build_session_plan,
    classify_mastery,
    classify_skill_mastery,
    compute_and_save_learning_profile,
    get_attempts,
    get_attempts_count,
    get_chunk_stats,
    get_error_frequency,
    get_learning_profile,
    get_retention_metrics,
    get_score_evolution,
    get_topic_stats,
    get_user_skill_mastery,
)
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

_BADGE = {
    "Fragile":          ("🔴", "FRAGILE"),
    "En consolidation": ("🟡", "EN CONSOLIDATION"),
    "Maîtrisé":         ("🟢", "MAÎTRISÉ"),
}


def render() -> None:
    st.markdown(
        "<h4 style='margin:0 0 10px;color:#0f172a;font-size:15px;font-weight:700;"
        "letter-spacing:-0.01em'>Tableau de bord pédagogique</h4>",
        unsafe_allow_html=True,
    )

    _uid = st.session_state["user_id"]
    total_attempts = get_attempts_count(user_id=_uid)

    if total_attempts < 2:
        st.info("Effectuez au moins 2 tentatives pour afficher le dashboard.")
        return

    _WINDOW_OPTIONS = {
        "100 dernières": 100,
        "200 dernières": 200,
        "300 dernières": 300,
        "Tout l'historique": None,
    }
    _window_label = st.selectbox(
        "Fenêtre d'analyse",
        options=list(_WINDOW_OPTIONS.keys()),
        index=1,
        key="dashboard_window",
        help="Nombre de tentatives chargées. 'Tout l'historique' peut être lent sur les grands comptes.",
    )
    _window_limit = _WINDOW_OPTIONS[_window_label]

    # ── Diagnostic d'isolation — feature flags ────────────────────────────
    with st.expander("Diagnostic d'isolation des blocs", expanded=False):
        _diag_mode = st.checkbox(
            "Mode diagnostic — désactiver tous les blocs",
            key="dash_diag_mode",
            value=False,
            help="Désactive tous les blocs. Réactivez-les un par un pour isoler le bloc lent ou bugué.",
        )
        if _diag_mode:
            st.caption(
                "Réactivez les blocs un par un. "
                "Le bloc qui cause le bug ralentira ou plantera le dashboard lors de son activation."
            )
            _dc1, _dc2 = st.columns(2)
            with _dc1:
                _show_recs      = st.checkbox("Recommandations du moteur",             key="dash_recs",      value=False)
                _show_priority  = st.checkbox("Révision prioritaire",                   key="dash_priority",  value=False)
                _show_plan      = st.checkbox("Plan de session",                        key="dash_plan",      value=False)
                _show_sections  = st.checkbox("Progression par section (cartes)",       key="dash_sections",  value=False)
                _show_graphs    = st.checkbox("Graphiques (scores / topics / erreurs)", key="dash_graphs",    value=False)
                _show_timeline  = st.checkbox("Timeline récente (8 items)",             key="dash_timeline",  value=False)
            with _dc2:
                _show_retention        = st.checkbox("Rétention pédagogique",                 key="dash_retention",        value=False)
                _show_analysis         = st.checkbox("Analyse pédagogique",                   key="dash_analysis",         value=False)
                _show_profile          = st.checkbox("Profil d'apprentissage",                key="dash_profile",          value=False)
                _show_enriched_profile = st.checkbox("Profil pédagogique enrichi (V1)",       key="dash_enriched_profile", value=False)
                _show_skills           = st.checkbox("Compétences détectées",                 key="dash_skills",           value=False)
                _show_debug            = st.checkbox("Debug pédagogique V1.1",                key="dash_debug",            value=False)
                _show_export           = st.checkbox("Export rapport",                        key="dash_export",           value=False)
        else:
            (
                _show_recs, _show_priority, _show_plan, _show_sections,
                _show_graphs, _show_timeline, _show_retention, _show_analysis,
                _show_profile, _show_enriched_profile, _show_skills, _show_debug, _show_export,
            ) = (True,) * 13

    with st.spinner("Chargement du tableau de bord…"):
        df_all    = get_attempts(user_id=_uid, limit=_window_limit)
        df_topics = get_topic_stats(user_id=_uid)
        df_chunks = classify_mastery(get_chunk_stats(user_id=_uid))
        df_errors = get_error_frequency(user_id=_uid)

    # ── Zone 1 : KPIs enrichis ────────────────────────────────────────────
    scores_all = df_all["score"].dropna()
    n_sections = len(df_chunks)
    n_mastered = int((df_chunks["mastery_class"] == "Maîtrisé").sum()) if not df_chunks.empty else 0
    n_retard   = (
        int((df_chunks["review_status"] == "En retard").sum())
        if not df_chunks.empty and "review_status" in df_chunks.columns else 0
    )

    _kc1, _kc2, _kc3, _kc4 = st.columns(4)
    _kc1.markdown(_kpi_card("📊", "Tentatives", str(total_attempts)), unsafe_allow_html=True)
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
    if _show_recs:
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
    if _show_priority and not df_chunks.empty:
        _prio_fragile = df_chunks[df_chunks["mastery_class"] == "Fragile"].sort_values("avg_score")
        _prio_consol  = df_chunks[df_chunks["mastery_class"] == "En consolidation"].sort_values("avg_score")
        _prio_row     = (
            _prio_fragile.iloc[0] if not _prio_fragile.empty else
            (_prio_consol.iloc[0]  if not _prio_consol.empty  else None)
        )

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
                for _w in explain_priority_decision(_prio_row):
                    st.caption(f"· {_w}")
                _ivl_expl = explain_interval_decision(
                    str(_prio_row.get("mastery_class") or ""),
                    str(_prio_row.get("trend") or "N/A"),
                )
                if _ivl_expl:
                    st.caption(f"⏱ {_ivl_expl}")

    st.divider()

    # ── Zone 2b : Plan de session adaptatif ──────────────────────────────
    if _show_plan:
        _session_plan = build_session_plan(df_chunks, max_items=5) if not df_chunks.empty else []
        if _session_plan:
            st.markdown(
                "<p style='font-size:12px;font-weight:700;color:#475569;margin:0 0 6px;"
                "text-transform:uppercase;letter-spacing:.07em'>Plan de session</p>",
                unsafe_allow_html=True,
            )
            _total_min = sum(item["estimated_minutes"] for item in _session_plan)
            st.caption(
                f"{len(_session_plan)} section{'s' if len(_session_plan) > 1 else ''}"
                f" · ~{_total_min} min estimées"
            )
            for _rank, _item in enumerate(_session_plan, 1):
                _s_icon, _ = _BADGE.get(_item["mastery_class"], ("⚪", ""))
                _s_pct     = round(_item["avg_score"] * 100)
                _s_mins    = _item["estimated_minutes"]
                _s_status  = _item["review_status"]
                with st.container(border=True):
                    _sp_a, _sp_b = st.columns([3, 1])
                    with _sp_a:
                        st.markdown(
                            f"**{_rank}. {_item['section_label']}**"
                            f" · _{_item['document_title']}_"
                        )
                        st.caption(_item["objective"])
                    with _sp_b:
                        st.markdown(f"{_s_icon} **{_s_pct} %**")
                        st.caption(f"~{_s_mins} min · {_s_status}")

            st.divider()

    # ── Zone 3 : Cartes de section ────────────────────────────────────────
    if _show_sections:
        st.markdown(
            "<p style='font-size:12px;font-weight:700;color:#475569;margin:0 0 8px;"
            "text-transform:uppercase;letter-spacing:.07em'>Progression par section</p>",
            unsafe_allow_html=True,
        )
        _MAX_SECTIONS = 20
        if not df_chunks.empty:
            df_ordered = pd.concat([
                df_chunks[df_chunks["mastery_class"] == "Fragile"].sort_values("avg_score"),
                df_chunks[df_chunks["mastery_class"] == "En consolidation"].sort_values("avg_score"),
                df_chunks[df_chunks["mastery_class"] == "Maîtrisé"],
            ])
            _show_all_sec = st.session_state.get("dashboard_show_all_sections", False)
            _df_display   = df_ordered if _show_all_sec else df_ordered.head(_MAX_SECTIONS)
            _ncols     = min(len(_df_display), 3)
            _card_cols = st.columns(_ncols)
            for i, (_, r) in enumerate(_df_display.iterrows()):
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
                        _ivl = explain_interval_decision(
                            str(r.get("mastery_class") or ""),
                            str(r.get("trend") or "N/A"),
                        )
                        if _ivl:
                            st.caption(f"⏱ {_ivl}")

            _total_sec = len(df_ordered)
            if not _show_all_sec and _total_sec > _MAX_SECTIONS:
                _rem = _total_sec - _MAX_SECTIONS
                st.caption(f"Affichage des {_MAX_SECTIONS} sections prioritaires sur {_total_sec}.")
                if st.button(f"Charger les {_rem} sections restantes", key="btn_all_sections"):
                    st.session_state["dashboard_show_all_sections"] = True
                    st.rerun()
            elif _show_all_sec and _total_sec > _MAX_SECTIONS:
                if st.button("Réduire à l'affichage standard (20 sections)", key="btn_reduce_sections"):
                    st.session_state["dashboard_show_all_sections"] = False
                    st.rerun()
        else:
            st.info(
                "Aucune donnée par section disponible. "
                "Effectuez des tentatives en mode RAG (document importé avec embeddings)."
            )

    st.divider()

    # ── Zone 4a : Évolution des scores ────────────────────────────────────
    if _show_graphs:
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
        else:
            st.caption("Pas encore de données d'évolution.")

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
                df_plot["label"]     = df_plot["topic"].apply(_truncate_label)
                df_plot["niveau"]    = df_plot["avg_score"].apply(
                    lambda s: "Bon" if s >= 0.8 else ("Moyen" if s >= 0.5 else "Fragile")
                )
                fig = px.bar(
                    df_plot.sort_values("score_pct"),
                    x="score_pct", y="label", orientation="h",
                    color="niveau",
                    color_discrete_map={"Bon": "#16a34a", "Moyen": "#d97706", "Fragile": "#dc2626"},
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
                df_errors["label"]       = df_errors["error_type"].map(
                    lambda x: _ERROR_LABELS.get(x, x)
                )
                df_errors["label_short"] = df_errors["label"].apply(_truncate_label)
                fig = px.bar(
                    df_errors.sort_values("count"),
                    x="count", y="label_short", orientation="h",
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
                    xaxis=dict(title="Occurrences", nticks=5),
                    yaxis=dict(title=""),
                    margin=dict(l=10, r=10, t=10, b=10),
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Aucune erreur enregistrée.")

        st.divider()

    # ── Zone 4d : Mini-timeline ───────────────────────────────────────────
    if _show_timeline:
        st.markdown(
            "<p style='font-size:12px;font-weight:700;color:#475569;margin:8px 0 6px;"
            "text-transform:uppercase;letter-spacing:.07em'>Parcours récent</p>",
            unsafe_allow_html=True,
        )
        _recent   = df_all.head(8)
        _tl_items = []
        for _, _row in _recent.iterrows():
            try:
                _sv = float(_row["score"])
            except (TypeError, ValueError):
                _sv = 0.0
            _col         = "#16a34a" if _sv >= 0.8 else ("#d97706" if _sv >= 0.5 else "#dc2626")
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

    # ── Zone 4e : Rétention pédagogique ──────────────────────────────────
    if _show_retention:
        st.markdown(
            "<p style='font-size:12px;font-weight:700;color:#475569;margin:0 0 6px;"
            "text-transform:uppercase;letter-spacing:.07em'>Rétention pédagogique</p>",
            unsafe_allow_html=True,
        )
        _ret = get_retention_metrics(st.session_state["user_id"])
        _ret_windows = [
            ("retention_j1",  "🧠", "Rétention J+1",  "Révision lendemain (12h–2j)"),
            ("retention_j7",  "📅", "Rétention J+7",  "Révision hebdo (4–10j)"),
            ("retention_j30", "📆", "Rétention J+30", "Révision mensuelle (21–45j)"),
        ]
        _rc1, _rc2, _rc3 = st.columns(3)
        for _rcol, (_key, _ico, _lbl, _sub) in zip((_rc1, _rc2, _rc3), _ret_windows):
            _rval = _ret.get(_key)
            if _rval is not None:
                _rpct   = round(_rval * 100)
                _rcolor = "#15803d" if _rpct >= 70 else ("#b45309" if _rpct >= 50 else "#b91c1c")
                _rstr   = f"{_rpct} %"
            else:
                _rcolor = "#94a3b8"
                _rstr   = "—"
            _rcol.markdown(_kpi_card(_ico, _lbl, _rstr, _rcolor), unsafe_allow_html=True)
            _rcol.caption(_sub)
        if all(v is None for v in _ret.values()):
            st.caption(
                "Données insuffisantes — révisez le même concept à plusieurs jours d'intervalle "
                "pour que la rétention soit calculable."
            )

        st.divider()

    # ── Zone 5 : Analyse pédagogique dynamique ────────────────────────────
    if _show_analysis:
        _n_fragile  = int((df_chunks["mastery_class"] == "Fragile").sum()) if not df_chunks.empty else 0
        _n_maitrise = int((df_chunks["mastery_class"] == "Maîtrisé").sum()) if not df_chunks.empty else 0
        _n_progress = int((df_chunks["trend"] == "Amélioration").sum()) if not df_chunks.empty else 0
        _n_regress  = int((df_chunks["trend"] == "Dégradation").sum()) if not df_chunks.empty else 0

        _analyse = []
        if _n_fragile:
            _analyse.append(
                f"⚡ {_n_fragile} section{'s' if _n_fragile > 1 else ''} fragile{'s' if _n_fragile > 1 else ''} — révision prioritaire active, types reformulation/conséquence priorisés"
            )
        if _n_progress:
            _analyse.append(
                f"📈 {_n_progress} section{'s' if _n_progress > 1 else ''} en progression — consolidation détectée"
            )
        if _n_regress:
            _analyse.append(
                f"📉 {_n_regress} section{'s' if _n_regress > 1 else ''} en régression — adaptation du type de question en cours"
            )
        if _n_maitrise:
            _analyse.append(
                f"✅ {_n_maitrise} section{'s' if _n_maitrise > 1 else ''} maîtrisée{'s' if _n_maitrise > 1 else ''} — questions pièges et cas pratiques activés"
            )
        if not df_errors.empty:
            _te = df_errors.iloc[0]
            _analyse.append(
                f"🔍 Erreur dominante : \"{_ERROR_LABELS.get(_te['error_type'], _te['error_type'])}\" "
                f"({int(_te['count'])} occurrences) — notion sensible identifiée"
            )

        if _analyse:
            st.info("**Analyse pédagogique — Moteur adaptatif**  \n" + "  \n".join(_analyse))

    # ── Zone 7 : Profil d'apprentissage ──────────────────────────────────
    if _show_profile:
        st.markdown(
            "<p style='font-size:12px;font-weight:700;color:#475569;margin:0 0 8px;"
            "text-transform:uppercase;letter-spacing:.07em'>Profil d'apprentissage</p>",
            unsafe_allow_html=True,
        )

        _profile = get_learning_profile(st.session_state["user_id"])

        if _profile is not None:
            _pg1, _pg2, _pg3, _pg4 = st.columns(4)
            for _gcol, (icon, label, key, _) in zip(
                (_pg1, _pg2, _pg3, _pg4), _SCORE_GROUPS
            ):
                _s       = float(_profile.get(key) or 0.0)
                _pct_str = f"{round(_s * 100)} %" if _s > 0 else "—"
                _accent  = (
                    "#15803d" if _s >= 0.8
                    else "#b45309" if _s >= 0.6
                    else "#b91c1c" if _s > 0
                    else "#94a3b8"
                )
                _gcol.markdown(_kpi_card(icon, label, _pct_str, _accent), unsafe_allow_html=True)

            # ── Métriques dynamiques : momentum, vélocité, régularité ─────────
            st.markdown(
                "<p style='font-size:11px;font-weight:600;color:#94a3b8;margin:10px 0 6px;"
                "text-transform:uppercase;letter-spacing:.07em'>Dynamique d'apprentissage</p>",
                unsafe_allow_html=True,
            )
            _dm1, _dm2, _dm3 = st.columns(3)

            _mom = float(_profile.get("momentum") or 0.0)
            _vel = float(_profile.get("learning_velocity") or 0.0)
            _con = float(_profile.get("consistency_score") or 0.0)

            _mom_str = (
                f"+{round(_mom * 100)} %" if _mom > 0.0
                else (f"{round(_mom * 100)} %" if _mom < 0.0 else "Stable")
            )
            _mom_col = "#15803d" if _mom > 0.0 else ("#b91c1c" if _mom < 0.0 else "#94a3b8")
            _mom_ico = "📈" if _mom > 0.0 else ("📉" if _mom < 0.0 else "➡️")
            _dm1.markdown(_kpi_card(_mom_ico, "Momentum 7j", _mom_str, _mom_col), unsafe_allow_html=True)

            _vel_str = (
                f"+{round(_vel * 100)} %" if _vel > 0.0
                else (f"{round(_vel * 100)} %" if _vel < 0.0 else "—")
            )
            _vel_col = "#15803d" if _vel > 0.0 else ("#b91c1c" if _vel < 0.0 else "#94a3b8")
            _dm2.markdown(_kpi_card("⚡", "Vélocité", _vel_str, _vel_col), unsafe_allow_html=True)

            _con_str = f"{round(_con * 100)} %" if _con > 0.0 else "—"
            _con_col = (
                "#15803d" if _con >= 0.5
                else ("#b45309" if _con >= 0.3 else ("#b91c1c" if _con > 0.0 else "#94a3b8"))
            )
            _dm3.markdown(_kpi_card("🔄", "Régularité 30j", _con_str, _con_col), unsafe_allow_html=True)

            _pref       = _profile.get("preferred_pedagogy")
            _pref_label = _PEDAGOGY_FR.get(_pref, _pref) if _pref else None
            _fragile    = _profile.get("fragile_topics") or []
            _avg        = float(_profile.get("average_score") or 0.0)

            _profile_lines = []
            if _pref_label:
                _profile_lines.append(f"**Style dominant :** {_pref_label}")
            if _avg > 0:
                _profile_lines.append(f"**Score global :** {round(_avg * 100)} %")
            if _profile_lines:
                st.markdown("  ·  ".join(_profile_lines))
            if _fragile:
                st.caption("Notions fragiles : " + " · ".join(_fragile))
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
            with st.spinner("Calcul du profil…"):
                compute_and_save_learning_profile(st.session_state["user_id"])
            st.rerun()

        st.divider()

    # ── Zone 7b : Profil pédagogique enrichi V1 (TASK-049) ───────────────
    if _show_enriched_profile:
        from engine.user_profile_insights import compute_profile_insights

        st.markdown(
            "<p style='font-size:12px;font-weight:700;color:#475569;margin:0 0 8px;"
            "text-transform:uppercase;letter-spacing:.07em'>Profil pédagogique enrichi</p>",
            unsafe_allow_html=True,
        )

        _ep_profile = get_learning_profile(st.session_state["user_id"])

        if _ep_profile is None:
            st.info(
                "Calculez d'abord le profil d'apprentissage (section ci-dessus) "
                "pour afficher les insights enrichis."
            )
        else:
            _ep_err_counts: dict = {}
            if not df_errors.empty and "error_type" in df_errors.columns:
                for _, _er in df_errors.iterrows():
                    _etype = _er.get("error_type") or ""
                    if _etype and _etype != "correct":
                        _ep_err_counts[_etype] = int(_er.get("count") or 0)

            _ep_avg_rt = None
            if not df_all.empty and "response_time_seconds" in df_all.columns:
                _rt_series = df_all["response_time_seconds"].dropna()
                if len(_rt_series) > 0:
                    _ep_avg_rt = float(_rt_series.mean())

            _ep_data = {
                "total_attempts":    total_attempts,
                "avg_score":         float(_ep_profile.get("average_score") or 0.0),
                "preferred_pedagogy": _ep_profile.get("preferred_pedagogy"),
                "logical_score":     float(_ep_profile.get("logical_score") or 0.0),
                "procedural_score":  float(_ep_profile.get("procedural_score") or 0.0),
                "narrative_score":   float(_ep_profile.get("narrative_score") or 0.0),
                "analogy_score":     float(_ep_profile.get("analogy_score") or 0.0),
                "fragile_topics":    _ep_profile.get("fragile_topics") or [],
                "momentum":          float(_ep_profile.get("momentum") or 0.0),
                "consistency_score": float(_ep_profile.get("consistency_score") or 0.0),
                "error_type_counts": _ep_err_counts,
                "avg_response_time": _ep_avg_rt,
            }

            _ins = compute_profile_insights(_ep_data)

            _conf_color = {
                "high":   "#15803d",
                "medium": "#b45309",
                "low":    "#94a3b8",
            }.get(_ins["confidence"], "#94a3b8")

            st.markdown(
                f'<span style="font-size:11px;color:{_conf_color};font-weight:600">'
                f'Confiance : {_ins["confidence_label"]}</span>',
                unsafe_allow_html=True,
            )

            if _ins["dominant_style_label"]:
                st.caption(f"Style : {_ins['dominant_style_label']}")

            _ep_c1, _ep_c2 = st.columns(2)

            with _ep_c1:
                if _ins["strengths"]:
                    st.markdown("**Points forts observés**")
                    for _s in _ins["strengths"]:
                        st.markdown(
                            f'<div style="font-size:12.5px;padding:5px 10px;margin-bottom:4px;'
                            f'background:#f0fdf4;border-left:3px solid #16a34a;border-radius:4px">'
                            f'✅ {_s}</div>',
                            unsafe_allow_html=True,
                        )
                else:
                    st.caption("Pas encore de points forts identifiés.")

            with _ep_c2:
                if _ins["weaknesses"]:
                    st.markdown("**Fragilités observées**")
                    for _w in _ins["weaknesses"]:
                        st.markdown(
                            f'<div style="font-size:12.5px;padding:5px 10px;margin-bottom:4px;'
                            f'background:#fff7ed;border-left:3px solid #d97706;border-radius:4px">'
                            f'⚠️ {_w}</div>',
                            unsafe_allow_html=True,
                        )
                else:
                    st.caption("Aucune fragilité significative détectée.")

            if _ins["recommendations"]:
                st.markdown("**Recommandations pédagogiques**")
                for _r in _ins["recommendations"]:
                    st.markdown(
                        f'<div style="font-size:12.5px;padding:5px 10px;margin-bottom:4px;'
                        f'background:#eff6ff;border-left:3px solid #3b82f6;border-radius:4px">'
                        f'💡 {_r}</div>',
                        unsafe_allow_html=True,
                    )

            with st.expander("Signaux utilisés", expanded=False):
                st.json(_ins["signals_used"])

        st.divider()

    # ── Zone 8 : Compétences détectées (Skills Engine V1.0) ───────────────
    if _show_skills:
        st.markdown(
            "<p style='font-size:12px;font-weight:700;color:#475569;margin:0 0 4px;"
            "text-transform:uppercase;letter-spacing:.07em'>Compétences détectées</p>",
            unsafe_allow_html=True,
        )
        st.caption("Score estimé V1 — mapping automatique par mots-clés, non validé")

        _skill_mastery = get_user_skill_mastery(st.session_state["user_id"])
        if _skill_mastery:
            _sk_cols = st.columns(3)
            _sk_state_color = {
                "Fragile":  "#dc2626",
                "En cours": "#d97706",
                "Acquis":   "#16a34a",
            }
            _sk_state_icon = {
                "Fragile":  "🔴",
                "En cours": "🟡",
                "Acquis":   "🟢",
            }
            for _i, _sk in enumerate(_skill_mastery):
                _sk_score = float(_sk.get("mastery_score") or 0.0)
                _sk_count = int(_sk.get("attempts_count") or 0)
                _sk_label = _sk.get("label_fr") or _sk.get("slug", "")
                _sk_class = classify_skill_mastery(_sk_score, _sk_count)
                _sk_color = _sk_state_color.get(_sk_class, "#94a3b8")
                _sk_icon  = _sk_state_icon.get(_sk_class, "⚪")
                with _sk_cols[_i % 3]:
                    with st.container(border=True):
                        st.markdown(
                            f'<span style="font-size:12px;font-weight:700;color:{_sk_color}">'
                            f'{_sk_icon} {_sk_class}</span>',
                            unsafe_allow_html=True,
                        )
                        st.markdown(f"**{_sk_label}**")
                        st.progress(min(_sk_score, 1.0), text=f"{round(_sk_score * 100)} %")
                        st.caption(f"{_sk_count} tentative{'s' if _sk_count > 1 else ''}")
        else:
            st.info(
                "Aucune compétence détectée. "
                "Effectuez des tentatives sur un document importé pour activer l'analyse."
            )

    # ── Zone 8b : Debug pédagogique V1.1 (lecture seule) ─────────────────
    if _show_debug:
        with st.expander("Debug pédagogique V1.1 — Analytics skills (lecture seule)"):
            try:
                from engine.skill_analytics import (
                    get_skill_frequency,
                    get_skill_collisions,
                    get_unused_skills,
                    get_overrepresented_skills,
                    get_chunks_without_skills,
                )
                from engine.skill_debug import explain_chunk_skills

                _tab_freq, _tab_coll, _tab_diag = st.tabs(
                    ["Fréquence skills", "Collisions", "Diagnostic chunk"]
                )

                with _tab_freq:
                    _freq = get_skill_frequency()
                    _unused = get_unused_skills()
                    _over = get_overrepresented_skills(threshold_pct=0.7)

                    if _freq:
                        st.markdown("**Fréquence par skill (chunks actifs)**")
                        _fdf = pd.DataFrame(_freq)
                        _fdf["coverage %"] = (_fdf["chunk_count"] / max(_fdf["chunk_count"].max(), 1) * 100).round(1)
                        st.dataframe(
                            _fdf[["slug", "label_fr", "chunk_count", "avg_weight"]],
                            use_container_width=True, hide_index=True,
                        )
                    else:
                        st.caption("Aucun mapping actif en base.")

                    if _over:
                        st.markdown("**Skills sur-représentés (≥ 70 % des chunks)**")
                        st.dataframe(
                            pd.DataFrame(_over)[["slug", "chunk_count", "total_chunks", "coverage_pct"]],
                            use_container_width=True, hide_index=True,
                        )
                        st.caption("Ces skills couvrent trop de chunks — indicateur de keywords trop génériques.")

                    if _unused:
                        st.markdown("**Skills sans aucun mapping**")
                        st.dataframe(
                            pd.DataFrame(_unused)[["slug", "label_fr"]],
                            use_container_width=True, hide_index=True,
                        )

                with _tab_coll:
                    _coll = get_skill_collisions()
                    if _coll:
                        st.markdown("**Co-occurrences les plus fréquentes (même chunk)**")
                        st.dataframe(
                            pd.DataFrame(_coll),
                            use_container_width=True, hide_index=True,
                        )
                        st.caption(
                            "Une co-occurrence élevée indique que deux skills sont difficiles à discriminer "
                            "avec les keywords V1.1 actuels."
                        )
                    else:
                        st.caption("Aucune collision détectée (ou mapping vide).")

                    _no_skill_chunks = get_chunks_without_skills()
                    if _no_skill_chunks:
                        st.markdown(f"**Chunks sans skill ({len(_no_skill_chunks)})**")
                        st.dataframe(
                            pd.DataFrame(_no_skill_chunks)[
                                ["chunk_id", "chunk_index", "section_title", "document_title", "text_preview"]
                            ],
                            use_container_width=True, hide_index=True,
                        )
                    else:
                        st.caption("Tous les chunks ont au moins un skill mappé.")

                with _tab_diag:
                    st.caption(
                        "Saisissez un chunk_id pour comparer le mapping stocké en base "
                        "avec la détection live des keywords V1.1."
                    )
                    _diag_id = st.number_input(
                        "Chunk ID", min_value=1, step=1, key="debug_chunk_id"
                    )
                    if st.button("Analyser ce chunk", key="btn_debug_chunk"):
                        _diag = explain_chunk_skills(int(_diag_id))
                        if "error" in _diag:
                            st.warning(_diag["error"])
                        else:
                            st.markdown(
                                f"**Chunk #{_diag['chunk_id']}** — "
                                f"{_diag.get('document_title', '—')} › "
                                f"{_diag.get('section_title') or '(sans titre)'}"
                            )
                            st.caption(_diag.get("text_preview", ""))

                            _dcol1, _dcol2 = st.columns(2)
                            with _dcol1:
                                st.markdown("**Mappings en base**")
                                if _diag["stored_mappings"]:
                                    st.dataframe(
                                        pd.DataFrame(_diag["stored_mappings"])[
                                            ["slug", "weight", "source", "is_validated", "is_active"]
                                        ],
                                        use_container_width=True, hide_index=True,
                                    )
                                else:
                                    st.caption("Aucun mapping stocké.")

                            with _dcol2:
                                st.markdown("**Détection live (keywords V1.1)**")
                                if _diag["live_detection"]:
                                    st.dataframe(
                                        pd.DataFrame(_diag["live_detection"])[
                                            ["slug", "weight", "keywords_matched"]
                                        ],
                                        use_container_width=True, hide_index=True,
                                    )
                                else:
                                    st.caption("Aucun skill détecté avec les keywords actuels.")

                            if _diag["discrepancies"]:
                                st.markdown("**Écarts détectés**")
                                st.dataframe(
                                    pd.DataFrame(_diag["discrepancies"]),
                                    use_container_width=True, hide_index=True,
                                )
                            else:
                                st.success("Aucun écart — mapping cohérent avec les keywords V1.1.")

            except Exception as _dbg_exc:
                st.caption(f"Debug indisponible : {_dbg_exc}")

    st.divider()

    # ── Zone 6 : Export ───────────────────────────────────────────────────
    if _show_export:
        _report_txt = _build_report(df_all, df_topics, df_chunks)
        _fname      = f"rapport_progression_{datetime.now().strftime('%Y%m%d')}.txt"
        st.download_button(
            "Télécharger le rapport de progression",
            data=_report_txt.encode("utf-8"),
            file_name=_fname,
            mime="text/plain",
        )
