"""Onglet Dashboard — Dark Premium UI (TASK-078)."""
from datetime import datetime
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
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
    _dark_kpi_card,
    _mastery_state,
    _truncate_label,
    build_recommendation_reason,
    explain_interval_decision,
    explain_priority_decision,
    explain_profile_detection,
)
from tabs.styles import DARK_DASHBOARD_CSS

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

_MONTHS_FR = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]


def render() -> None:
    st.markdown(DARK_DASHBOARD_CSS, unsafe_allow_html=True)

    _uid      = st.session_state["user_id"]
    _username = st.session_state.get("username") or "Apprenant"

    # ── Filtrage corpus actif ────────────────────────────────────────────────
    _corpus_doc_ids: Optional[list[int]] = None
    _active_corpus_name = st.session_state.get("active_corpus_name", "")
    _active_corpus_id   = st.session_state.get("active_corpus_id")
    if _active_corpus_id:
        from db.corpus import get_corpus_documents as _get_corpus_docs
        _corpus_doc_ids = _get_corpus_docs(_active_corpus_id) or None

    total_attempts = get_attempts_count(user_id=_uid, document_ids=_corpus_doc_ids)

    # ── Header ───────────────────────────────────────────────────────────────
    _now      = datetime.now()
    _date_str = f"{_now.day} {_MONTHS_FR[_now.month - 1]} {_now.year}"

    _corpus_badge = (
        f'<span style="background:rgba(124,58,237,0.13);border:1px solid rgba(124,58,237,0.35);'
        f'border-radius:20px;padding:4px 14px;font-size:11px;font-weight:700;color:#A78BFA;'
        f'text-transform:uppercase;letter-spacing:.08em">📚 {_active_corpus_name}</span>'
        if _active_corpus_name else
        '<span style="background:rgba(37,99,235,0.13);border:1px solid rgba(37,99,235,0.35);'
        'border-radius:20px;padding:4px 14px;font-size:11px;font-weight:700;color:#60A5FA;'
        'text-transform:uppercase;letter-spacing:.08em">Adaptive Learning</span>'
    )
    st.markdown(
        f'<div style="padding:18px 0 22px;border-bottom:1px solid rgba(120,140,255,0.13);margin-bottom:20px">'
        f'<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px">'
        f'<div>'
        f'<div style="font-size:26px;font-weight:800;color:#F8FAFC;letter-spacing:-0.02em;line-height:1.15">'
        f'Bonjour, {_username} 👋</div>'
        f'<div style="font-size:13px;color:#64748B;margin-top:5px">'
        f'{_date_str} &nbsp;·&nbsp; {total_attempts} tentative{"s" if total_attempts != 1 else ""} enregistrée{"s" if total_attempts != 1 else ""}'
        f'</div></div>'
        f'{_corpus_badge}'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    # ── Fallback : données insuffisantes ─────────────────────────────────────
    if total_attempts < 2:
        st.markdown(
            '<div style="background:#0B1530;border:1px solid rgba(120,140,255,0.18);border-radius:14px;'
            'padding:48px 32px;text-align:center;margin-top:16px">'
            '<div style="font-size:40px;margin-bottom:16px">📊</div>'
            '<div style="font-size:17px;font-weight:700;color:#F8FAFC;margin-bottom:8px">Données insuffisantes</div>'
            '<div style="font-size:13px;color:#94A3B8">'
            'Effectuez au moins 2 tentatives pour accéder au tableau de bord complet.'
            '</div></div>',
            unsafe_allow_html=True,
        )
        return

    # ── Fenêtre d'analyse ────────────────────────────────────────────────────
    _WINDOW_OPTIONS = {
        "20 dernières": 20,
        "50 dernières": 50,
        "100 dernières": 100,
        "Tout l'historique": None,
    }
    _w_left, _w_right = st.columns([5, 1])
    with _w_right:
        _window_label = st.selectbox(
            "Fenêtre",
            options=list(_WINDOW_OPTIONS.keys()),
            index=1,
            key="dashboard_window",
            label_visibility="collapsed",
        )
    _window_limit = _WINDOW_OPTIONS[_window_label]

    # ── Chargement des données ───────────────────────────────────────────────
    with st.spinner(""):
        df_all    = get_attempts(user_id=_uid, limit=_window_limit, document_ids=_corpus_doc_ids)
        df_topics = get_topic_stats(user_id=_uid, document_ids=_corpus_doc_ids)
        df_chunks = classify_mastery(get_chunk_stats(user_id=_uid, document_ids=_corpus_doc_ids))
        df_errors = get_error_frequency(user_id=_uid, document_ids=_corpus_doc_ids)

    scores_all = df_all["score"].dropna()
    n_sections = len(df_chunks)
    n_mastered = int((df_chunks["mastery_class"] == "Maîtrisé").sum()) if not df_chunks.empty else 0
    n_retard   = (
        int((df_chunks["review_status"] == "En retard").sum())
        if not df_chunks.empty and "review_status" in df_chunks.columns else 0
    )
    n_fragile  = int((df_chunks["mastery_class"] == "Fragile").sum())         if not df_chunks.empty else 0
    n_progress = int((df_chunks["trend"] == "Amélioration").sum())            if not df_chunks.empty else 0
    n_regress  = int((df_chunks["trend"] == "Dégradation").sum())             if not df_chunks.empty else 0

    _profile     = get_learning_profile(_uid)
    _momentum    = float(_profile.get("momentum")         or 0.0) if _profile else 0.0
    _consistency = float(_profile.get("consistency_score") or 0.0) if _profile else 0.0

    _mom_accent = "#10B981" if _momentum > 0 else ("#EF4444" if _momentum < 0 else "#94A3B8")
    _mom_icon   = "📈"      if _momentum > 0 else ("📉"      if _momentum < 0 else "➡️")
    _mom_str    = (
        f"+{round(_momentum * 100)}%"  if _momentum > 0
        else f"{round(_momentum * 100)}%" if _momentum < 0
        else "Stable"
    )

    # ── KPI Row ──────────────────────────────────────────────────────────────
    _avg_score = round(scores_all.mean() * 100) if len(scores_all) else None
    _kc1, _kc2, _kc3, _kc4, _kc5 = st.columns(5)
    _kc1.markdown(
        _dark_kpi_card("🎯", "Score moyen",
                       f"{_avg_score}%" if _avg_score is not None else "—",
                       "#2563EB", f"{len(scores_all)} réponses"),
        unsafe_allow_html=True,
    )
    _kc2.markdown(
        _dark_kpi_card("📊", "Tentatives", str(total_attempts), "#06B6D4", "total"),
        unsafe_allow_html=True,
    )
    _kc3.markdown(
        _dark_kpi_card(
            "✅", "Maîtrisées",
            f"{n_mastered}/{n_sections}" if n_sections else "—",
            "#10B981" if (n_mastered == n_sections and n_sections) else "#7C3AED",
            "sections",
        ),
        unsafe_allow_html=True,
    )
    _kc4.markdown(
        _dark_kpi_card("⚠️", "En retard",
                       str(n_retard) if n_sections else "—",
                       "#EF4444" if n_retard > 0 else "#94A3B8",
                       "révisions dues"),
        unsafe_allow_html=True,
    )
    _kc5.markdown(
        _dark_kpi_card(_mom_icon, "Momentum 7j", _mom_str, _mom_accent, "tendance récente"),
        unsafe_allow_html=True,
    )

    st.markdown("<div style='margin:22px 0 6px'></div>", unsafe_allow_html=True)

    # ── Mise en page principale : graphique + coach ───────────────────────────
    _col_main, _col_side = st.columns([7, 5])

    # ────────────────────────────────────────────────────────────────────────
    # COLONNE PRINCIPALE — Progression + Storytelling
    # ────────────────────────────────────────────────────────────────────────
    with _col_main:

        # Section header
        st.markdown(
            '<div style="font-size:11px;font-weight:700;color:#64748B;text-transform:uppercase;'
            'letter-spacing:.09em;margin-bottom:10px">Ma progression</div>',
            unsafe_allow_html=True,
        )

        df_evol = get_score_evolution(limit=50, user_id=_uid)

        if not df_evol.empty:
            _y = (df_evol["score"] * 100).round().tolist()
            _x = list(range(1, len(_y) + 1))

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=_x, y=_y,
                mode="lines+markers",
                line=dict(color="#2563EB", width=2.5, shape="spline"),
                fill="tozeroy",
                fillcolor="rgba(37,99,235,0.07)",
                marker=dict(size=5, color="#2563EB",
                            line=dict(width=1.5, color="#60A5FA")),
                hovertemplate="Tentative %{x} — <b>%{y}%</b><extra></extra>",
            ))
            fig.add_hline(
                y=60,
                line_dash="dot", line_color="rgba(239,68,68,0.35)",
                annotation_text="seuil fragile",
                annotation_font_color="#EF4444",
                annotation_font_size=10,
                annotation_position="bottom right",
            )
            fig.add_hline(
                y=80,
                line_dash="dot", line_color="rgba(16,185,129,0.35)",
                annotation_text="seuil maîtrise",
                annotation_font_color="#10B981",
                annotation_font_size=10,
                annotation_position="top right",
            )
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(11,21,48,0.45)",
                height=230,
                margin=dict(l=8, r=50, t=10, b=8),
                showlegend=False,
                xaxis=dict(
                    showgrid=True, gridcolor="rgba(120,140,255,0.07)",
                    tickfont=dict(size=10, color="#64748B"),
                    title=dict(text="Tentatives", font=dict(size=10, color="#64748B")),
                ),
                yaxis=dict(
                    range=[0, 105], showgrid=True, gridcolor="rgba(120,140,255,0.07)",
                    tickfont=dict(size=10, color="#64748B"),
                    ticksuffix="%",
                    title=dict(text="Score", font=dict(size=10, color="#64748B")),
                ),
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            st.markdown(
                f'<div style="font-size:10px;color:#475569;text-align:right;margin-top:-8px">'
                f'{len(df_evol)} tentatives affichées</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div style="color:#64748B;font-size:13px;padding:20px 0;text-align:center">'
                'Pas encore de données d\'évolution.</div>',
                unsafe_allow_html=True,
            )

        st.markdown("<div style='margin:18px 0 10px'></div>", unsafe_allow_html=True)

        # ── Storytelling moteur ───────────────────────────────────────────
        st.markdown(
            '<div style="font-size:11px;font-weight:700;color:#64748B;text-transform:uppercase;'
            'letter-spacing:.09em;margin-bottom:10px">Le moteur détecte…</div>',
            unsafe_allow_html=True,
        )

        _signals: list[tuple[str, str, str]] = []

        if n_fragile:
            _s = "s" if n_fragile > 1 else ""
            _signals.append(("#EF4444", "⚡",
                             f"{n_fragile} section{_s} fragile{_s} — révision prioritaire active"))
        if n_progress:
            _s = "s" if n_progress > 1 else ""
            _signals.append(("#10B981", "📈",
                             f"{n_progress} section{_s} en progression — consolidation détectée"))
        if n_regress:
            _s = "s" if n_regress > 1 else ""
            _signals.append(("#F59E0B", "📉",
                             f"{n_regress} régression{_s} — difficulté adaptée automatiquement"))
        if not df_errors.empty and int(df_errors.iloc[0]["count"]) >= 2:
            _te = df_errors.iloc[0]
            _signals.append(("#7C3AED", "🔍",
                             f"Erreur dominante : {_ERROR_LABELS.get(_te['error_type'], _te['error_type'])}"
                             f" ({int(_te['count'])} occ.)"))
        if _momentum > 0.05:
            _signals.append(("#2563EB", "🚀",
                             f"Momentum positif (+{round(_momentum * 100)}%) — score en hausse sur 7j"))
        elif _momentum < -0.05:
            _signals.append(("#F59E0B", "⚠️",
                             f"Momentum en baisse ({round(_momentum * 100):+d}%) — révision recommandée"))
        if not _signals:
            _signals.append(("#10B981", "✅", "Aucune anomalie détectée — profil stable"))

        _pills_html = ""
        for _color, _ico, _msg in _signals:
            _pills_html += (
                f'<div style="display:flex;align-items:center;gap:10px;padding:9px 14px;'
                f'background:rgba(11,21,48,0.65);border:1px solid {_color}2E;'
                f'border-left:3px solid {_color};border-radius:8px;margin-bottom:6px">'
                f'<span style="font-size:14px;flex-shrink:0">{_ico}</span>'
                f'<span style="font-size:12.5px;color:#CBD5E1">{_msg}</span>'
                f'</div>'
            )
        st.markdown(_pills_html, unsafe_allow_html=True)

    # ────────────────────────────────────────────────────────────────────────
    # COLONNE LATÉRALE — IA Coach + Révisions à venir
    # ────────────────────────────────────────────────────────────────────────
    with _col_side:

        # ── Recommandation IA Coach ───────────────────────────────────────
        _prio_fragile = (
            df_chunks[df_chunks["mastery_class"] == "Fragile"].sort_values("avg_score")
            if not df_chunks.empty else pd.DataFrame()
        )
        _prio_consol = (
            df_chunks[df_chunks["mastery_class"] == "En consolidation"].sort_values("avg_score")
            if not df_chunks.empty else pd.DataFrame()
        )
        _prio_row = (
            _prio_fragile.iloc[0] if not _prio_fragile.empty else
            (_prio_consol.iloc[0]  if not _prio_consol.empty  else None)
        )

        if _prio_row is not None:
            _p_pct    = round(float(_prio_row["avg_score"]) * 100)
            _p_n      = int(_prio_row["attempts_count"])
            _p_mc     = str(_prio_row.get("mastery_class")       or "")
            _p_err    = str(_prio_row.get("dominant_error_type") or "")
            _p_trend  = str(_prio_row.get("trend")               or "N/A")
            _p_due    = _prio_row.get("review_status") == "En retard"
            _p_label  = str(_prio_row.get("section_label")       or "—")
            _p_doc    = str(_prio_row.get("document_title")      or "—")

            _reasons = build_recommendation_reason(
                mastery_class  = _p_mc,
                dominant_error = _p_err if _p_err and _p_err not in ("", "correct") else None,
                momentum       = _momentum,
                review_due     = _p_due,
                avg_score      = float(_prio_row["avg_score"]),
            )

            # Carte Coach
            st.markdown(
                f'<div style="background:linear-gradient(135deg,#0B1530 0%,#10183A 100%);'
                f'border:1px solid rgba(124,58,237,0.32);border-radius:14px;padding:18px 16px;'
                f'margin-bottom:4px;box-shadow:0 4px 20px rgba(124,58,237,0.09)">'
                f'<div style="font-size:10px;color:#7C3AED;text-transform:uppercase;'
                f'letter-spacing:.1em;font-weight:700;margin-bottom:10px">🤖 Recommandation IA Coach</div>'
                f'<div style="font-size:14px;font-weight:700;color:#F8FAFC;margin-bottom:6px">'
                f'Focus recommandé aujourd\'hui</div>'
                f'<div style="font-size:13px;color:#06B6D4;font-weight:600;margin-bottom:2px">'
                f'{_p_label}</div>'
                f'<div style="font-size:11px;color:#64748B;margin-bottom:8px">'
                f'{_truncate_label(_p_doc, 32)} — {_p_pct}% · {_p_n} tent.</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Bouton Commencer
            _btn_start = st.button(
                "▶ Commencer la révision",
                key="btn_coach_start",
                type="primary",
                use_container_width=True,
            )
            if _btn_start:
                st.info("Rendez-vous dans l'onglet **Entraînement** pour réviser cette section.")

            # Expander Pourquoi ?
            with st.expander("🔎 Pourquoi cette recommandation ?", expanded=False):
                if _reasons:
                    _why_html = (
                        '<div style="font-size:10px;color:#64748B;text-transform:uppercase;'
                        'letter-spacing:.08em;font-weight:700;margin-bottom:8px">Signaux détectés :</div>'
                    )
                    for _r in _reasons:
                        _why_html += (
                            f'<div style="display:flex;align-items:flex-start;gap:8px;'
                            f'padding:6px 10px;background:rgba(124,58,237,0.07);'
                            f'border-left:2px solid rgba(124,58,237,0.45);'
                            f'border-radius:4px;margin-bottom:5px">'
                            f'<span style="color:#A78BFA;font-size:12px;flex-shrink:0;margin-top:1px">•</span>'
                            f'<span style="font-size:12px;color:#CBD5E1;line-height:1.4">{_r}</span>'
                            f'</div>'
                        )
                    st.markdown(_why_html, unsafe_allow_html=True)
                else:
                    st.markdown(
                        '<div style="font-size:12px;color:#64748B;font-style:italic;padding:4px 0">'
                        'Le moteur poursuit le renforcement progressif de cette compétence.</div>',
                        unsafe_allow_html=True,
                    )

                _ivl_expl = explain_interval_decision(_p_mc, _p_trend)
                if _ivl_expl:
                    st.markdown(
                        f'<div style="font-size:11px;color:#64748B;margin-top:10px;'
                        f'border-top:1px solid rgba(120,140,255,0.1);padding-top:8px">'
                        f'⏱ {_ivl_expl}</div>',
                        unsafe_allow_html=True,
                    )

        else:
            st.markdown(
                '<div style="background:#0B1530;border:1px solid rgba(120,140,255,0.18);'
                'border-radius:14px;padding:28px 20px;text-align:center;margin-bottom:12px">'
                '<div style="font-size:28px;margin-bottom:10px">🎯</div>'
                '<div style="font-size:13px;color:#94A3B8">'
                'Toutes les sections sont maîtrisées — aucune révision urgente.</div>'
                '</div>',
                unsafe_allow_html=True,
            )

        # ── Révisions à venir ─────────────────────────────────────────────
        if not df_chunks.empty:
            st.markdown(
                '<div style="font-size:11px;font-weight:700;color:#64748B;text-transform:uppercase;'
                'letter-spacing:.09em;margin:18px 0 10px">Révisions à venir</div>',
                unsafe_allow_html=True,
            )

            _urgency_order = {"En retard": 0, "Aujourd'hui": 1, "À venir": 2, "OK": 3}
            _rev_df = df_chunks[df_chunks["mastery_class"] != "Maîtrisé"].copy()
            if not _rev_df.empty and "review_status" in _rev_df.columns:
                _rev_df["_urg"] = _rev_df["review_status"].map(
                    lambda x: _urgency_order.get(x, 4)
                )
                _rev_df = _rev_df.sort_values(["_urg", "avg_score"]).head(6)

            _status_colors = {
                "En retard":   ("#EF4444", "🔴"),
                "Aujourd'hui": ("#F59E0B", "🟡"),
                "À venir":     ("#2563EB", "🔵"),
                "OK":          ("#10B981", "🟢"),
            }
            _rev_html = ""
            for _, _rv in _rev_df.iterrows():
                _rv_status = str(_rv.get("review_status") or "—")
                _rv_color, _rv_dot = _status_colors.get(_rv_status, ("#94A3B8", "⚪"))
                _rv_pct   = round(float(_rv["avg_score"]) * 100)
                _rv_short = _truncate_label(str(_rv["section_label"]), 22)
                _rv_mc    = str(_rv.get("mastery_class") or "")
                _rev_html += (
                    f'<div style="display:flex;align-items:center;justify-content:space-between;'
                    f'padding:7px 10px;background:rgba(11,21,48,0.55);'
                    f'border:1px solid rgba(120,140,255,0.1);border-radius:8px;margin-bottom:5px;gap:8px">'
                    f'<div style="display:flex;align-items:center;gap:8px;min-width:0">'
                    f'<span style="flex-shrink:0">{_rv_dot}</span>'
                    f'<div style="min-width:0">'
                    f'<div style="font-size:11.5px;font-weight:600;color:#E2E8F0;'
                    f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{_rv_short}</div>'
                    f'<div style="font-size:10px;color:#64748B">{_rv_mc} · {_rv_pct}%</div>'
                    f'</div></div>'
                    f'<div style="font-size:10px;color:{_rv_color};font-weight:700;'
                    f'flex-shrink:0;white-space:nowrap">{_rv_status}</div>'
                    f'</div>'
                )

            if _rev_html:
                st.markdown(_rev_html, unsafe_allow_html=True)
            else:
                st.markdown(
                    '<div style="font-size:12px;color:#64748B;padding:10px 0">'
                    'Aucune révision planifiée.</div>',
                    unsafe_allow_html=True,
                )

    # ── Compétences détectées ─────────────────────────────────────────────────
    st.divider()

    _skill_mastery = get_user_skill_mastery(_uid)
    if _skill_mastery:
        st.markdown(
            '<div style="font-size:11px;font-weight:700;color:#64748B;text-transform:uppercase;'
            'letter-spacing:.09em;margin-bottom:14px">Compétences détectées</div>',
            unsafe_allow_html=True,
        )

        _sk_names   = [sk.get("label_fr") or sk.get("slug", "") for sk in _skill_mastery]
        _sk_scores  = [round(float(sk.get("mastery_score") or 0) * 100) for sk in _skill_mastery]
        _sk_classes = [
            classify_skill_mastery(float(sk.get("mastery_score") or 0),
                                   int(sk.get("attempts_count") or 0))
            for sk in _skill_mastery
        ]
        _sk_color_map = {"Fragile": "#EF4444", "En cours": "#F59E0B", "Acquis": "#10B981"}
        _bar_colors   = [_sk_color_map.get(c, "#94A3B8") for c in _sk_classes]

        fig_sk = go.Figure(go.Bar(
            x=_sk_scores,
            y=_sk_names,
            orientation="h",
            marker=dict(color=_bar_colors, line=dict(width=0)),
            text=[f"{s}%" for s in _sk_scores],
            textposition="inside",
            textfont=dict(color="#F8FAFC", size=11),
            hovertemplate="%{y} — %{x}%<extra></extra>",
        ))
        fig_sk.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(11,21,48,0.4)",
            height=max(100, len(_skill_mastery) * 34),
            margin=dict(l=8, r=8, t=8, b=8),
            showlegend=False,
            xaxis=dict(
                range=[0, 100],
                showgrid=True, gridcolor="rgba(120,140,255,0.07)",
                tickfont=dict(size=10, color="#64748B"),
                ticksuffix="%",
            ),
            yaxis=dict(tickfont=dict(size=11, color="#CBD5E1")),
        )
        st.plotly_chart(fig_sk, use_container_width=True, config={"displayModeBar": False})

        # Badges compétences
        _sk_badge_icon = {"Fragile": "🔴", "En cours": "🟡", "Acquis": "🟢"}
        _badges_html = '<div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:4px">'
        for _sk, _sc in zip(_skill_mastery, _sk_classes):
            _lbl = _sk.get("label_fr") or _sk.get("slug", "")
            _ico = _sk_badge_icon.get(_sc, "⚪")
            _color = _sk_color_map.get(_sc, "#94A3B8")
            _badges_html += (
                f'<span style="background:rgba(11,21,48,0.7);border:1px solid {_color}55;'
                f'border-radius:20px;padding:3px 10px;font-size:11px;color:{_color};font-weight:600">'
                f'{_ico} {_lbl}</span>'
            )
        _badges_html += "</div>"
        st.markdown(_badges_html, unsafe_allow_html=True)

    # ── Profil d'apprentissage ────────────────────────────────────────────────
    st.divider()
    st.markdown(
        '<div style="font-size:11px;font-weight:700;color:#64748B;text-transform:uppercase;'
        'letter-spacing:.09em;margin-bottom:14px">Profil d\'apprentissage</div>',
        unsafe_allow_html=True,
    )

    if _profile is not None:
        _pg1, _pg2, _pg3, _pg4 = st.columns(4)
        for _gcol, (icon, label, key, _) in zip((_pg1, _pg2, _pg3, _pg4), _SCORE_GROUPS):
            _s       = float(_profile.get(key) or 0.0)
            _pct_str = f"{round(_s * 100)} %" if _s > 0 else "—"
            _acc     = ("#10B981" if _s >= 0.8
                        else "#F59E0B" if _s >= 0.6
                        else "#EF4444" if _s > 0
                        else "#94A3B8")
            _gcol.markdown(_dark_kpi_card(icon, label, _pct_str, _acc), unsafe_allow_html=True)

        st.markdown("<div style='margin:12px 0 6px'></div>", unsafe_allow_html=True)
        _dm1, _dm2, _dm3 = st.columns(3)
        _vel     = float(_profile.get("learning_velocity") or 0.0)
        _vel_str = f"+{round(_vel * 100)} %" if _vel > 0 else (f"{round(_vel * 100)} %" if _vel < 0 else "—")
        _vel_col = "#10B981" if _vel > 0 else ("#EF4444" if _vel < 0 else "#94A3B8")
        _con_str = f"{round(_consistency * 100)} %" if _consistency > 0 else "—"
        _con_col = ("#10B981" if _consistency >= 0.5
                    else "#F59E0B" if _consistency >= 0.3
                    else "#EF4444" if _consistency > 0
                    else "#94A3B8")
        _dm1.markdown(_dark_kpi_card(_mom_icon, "Momentum 7j",  _mom_str, _mom_accent), unsafe_allow_html=True)
        _dm2.markdown(_dark_kpi_card("⚡",        "Vélocité",    _vel_str, _vel_col),    unsafe_allow_html=True)
        _dm3.markdown(_dark_kpi_card("🔄",        "Régularité",  _con_str, _con_col),    unsafe_allow_html=True)

        _pref  = _profile.get("preferred_pedagogy")
        _pref_label = _PEDAGOGY_FR.get(_pref, _pref) if _pref else None
        _prof_expl  = explain_profile_detection(_profile)
        _meta_parts = []
        if _pref_label:
            _meta_parts.append(f"Style dominant : {_pref_label}")
        if _prof_expl:
            _meta_parts.append(_prof_expl)
        if _meta_parts:
            st.markdown(
                f'<div style="font-size:11.5px;color:#64748B;margin:8px 0 4px">'
                f'{"  ·  ".join(_meta_parts)}</div>',
                unsafe_allow_html=True,
            )

        if st.button("Recalculer le profil", key="btn_recompute_profile"):
            with st.spinner("Calcul…"):
                compute_and_save_learning_profile(_uid)
            st.rerun()

    else:
        st.markdown(
            '<div style="font-size:13px;color:#64748B;margin-bottom:10px">'
            'Profil non encore calculé.</div>',
            unsafe_allow_html=True,
        )
        if st.button("Calculer le profil d'apprentissage", key="btn_compute_profile_first"):
            with st.spinner("Calcul…"):
                compute_and_save_learning_profile(_uid)
            st.rerun()

    # ── Export ───────────────────────────────────────────────────────────────
    st.divider()
    _report_txt = _build_report(df_all, df_topics, df_chunks)
    _fname = f"rapport_progression_{datetime.now().strftime('%Y%m%d')}.txt"
    st.download_button(
        "📥 Télécharger le rapport de progression",
        data=_report_txt.encode("utf-8"),
        file_name=_fname,
        mime="text/plain",
    )
