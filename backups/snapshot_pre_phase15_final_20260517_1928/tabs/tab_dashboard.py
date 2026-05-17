"""Onglet Dashboard — KPIs, maîtrise par section, profil d'apprentissage, export."""
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from database import (
    classify_mastery,
    compute_and_save_learning_profile,
    get_attempts,
    get_chunk_stats,
    get_error_frequency,
    get_learning_profile,
    get_score_evolution,
    get_topic_stats,
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

    df_all = get_attempts(user_id=st.session_state["user_id"])

    if len(df_all) < 2:
        st.info("Effectuez au moins 2 tentatives pour afficher le dashboard.")
        return

    df_topics = get_topic_stats(user_id=st.session_state["user_id"])
    df_chunks = classify_mastery(get_chunk_stats(user_id=st.session_state["user_id"]))
    df_errors = get_error_frequency(user_id=st.session_state["user_id"])

    # ── Zone 1 : KPIs enrichis ────────────────────────────────────────────
    scores_all = df_all["score"].dropna()
    n_sections = len(df_chunks)
    n_mastered = int((df_chunks["mastery_class"] == "Maîtrisé").sum()) if not df_chunks.empty else 0
    n_retard   = (
        int((df_chunks["review_status"] == "En retard").sum())
        if not df_chunks.empty and "review_status" in df_chunks.columns else 0
    )

    _kc1, _kc2, _kc3, _kc4 = st.columns(4)
    _kc1.markdown(_kpi_card("📊", "Tentatives", str(len(df_all))), unsafe_allow_html=True)
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

    # ── Zone 3 : Cartes de section ────────────────────────────────────────
    st.markdown(
        "<p style='font-size:12px;font-weight:700;color:#475569;margin:0 0 8px;"
        "text-transform:uppercase;letter-spacing:.07em'>Progression par section</p>",
        unsafe_allow_html=True,
    )
    if not df_chunks.empty:
        df_ordered = pd.concat([
            df_chunks[df_chunks["mastery_class"] == "Fragile"].sort_values("avg_score"),
            df_chunks[df_chunks["mastery_class"] == "En consolidation"].sort_values("avg_score"),
            df_chunks[df_chunks["mastery_class"] == "Maîtrisé"],
        ])
        _ncols     = min(len(df_ordered), 3)
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

    # ── Zone 5 : Analyse pédagogique dynamique ────────────────────────────
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

    # ── Zone 6 : Export ───────────────────────────────────────────────────
    _report_txt = _build_report(df_all, df_topics, df_chunks)
    _fname      = f"rapport_progression_{datetime.now().strftime('%Y%m%d')}.txt"
    st.download_button(
        "Télécharger le rapport de progression",
        data=_report_txt.encode("utf-8"),
        file_name=_fname,
        mime="text/plain",
    )
