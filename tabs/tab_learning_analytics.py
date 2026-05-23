"""Onglet Analytics d'apprentissage — TASK-084."""
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from db.sessions import get_activity_data, get_session_analytics, get_user_sessions
from tabs.styles import DARK_DASHBOARD_CSS


def _fmt_duration(seconds: Optional[float]) -> str:
    if seconds is None:
        return "—"
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m}m {s:02d}s" if m > 0 else f"{s}s"


def _score_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["day"],
        y=(df["avg_score"] * 100).round(1),
        mode="lines+markers",
        line=dict(color="#7C3AED", width=2.5),
        marker=dict(size=5, color="#A78BFA"),
        fill="tozeroy",
        fillcolor="rgba(124,58,237,0.07)",
        name="Score",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=8, b=0),
        height=180,
        xaxis=dict(showgrid=False, tickfont=dict(size=10, color="#64748B"), color="#64748B"),
        yaxis=dict(
            showgrid=True, gridcolor="rgba(100,116,139,0.1)",
            ticksuffix="%", range=[0, 105],
            tickfont=dict(size=10, color="#64748B"), color="#64748B",
        ),
        showlegend=False,
    )
    return fig


def _heatmap_chart(df: pd.DataFrame) -> go.Figure:
    today = datetime.now().date()
    start = today - timedelta(days=today.weekday()) - timedelta(weeks=7)
    date_counts: dict = {}
    if not df.empty:
        for _, row in df.iterrows():
            date_counts[str(row["day"])] = int(row["n_attempts"])

    weeks = 8
    days_fr = ["L", "M", "M", "J", "V", "S", "D"]
    z = np.zeros((7, weeks), dtype=int)
    week_labels = []
    text_matrix = [["" for _ in range(weeks)] for _ in range(7)]

    for w in range(weeks):
        week_start = start + timedelta(weeks=w)
        week_labels.append(week_start.strftime("%d/%m"))
        for d in range(7):
            day = week_start + timedelta(days=d)
            count = date_counts.get(str(day), 0)
            z[d][w] = count
            text_matrix[d][w] = f"{day.strftime('%d/%m')}<br>{count} réponse{'s' if count != 1 else ''}"

    fig = go.Figure(go.Heatmap(
        z=z,
        x=week_labels,
        y=days_fr,
        text=text_matrix,
        hovertemplate="%{text}<extra></extra>",
        colorscale=[
            [0.0,   "rgba(11,21,48,1)"],
            [0.001, "rgba(30,27,75,1)"],
            [0.3,   "rgba(76,29,149,0.7)"],
            [1.0,   "rgba(139,92,246,1)"],
        ],
        showscale=False,
        xgap=3,
        ygap=3,
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=28, r=0, t=8, b=28),
        height=145,
        xaxis=dict(tickfont=dict(size=10, color="#64748B"), side="bottom"),
        yaxis=dict(tickfont=dict(size=11, color="#64748B"), autorange="reversed"),
    )
    return fig


def _gen_insights(analytics: dict, df: pd.DataFrame) -> list:
    out = []
    this_w = analytics.get("sessions_this_week", 0)
    prev_w = analytics.get("sessions_prev_week", 0)
    if this_w > prev_w and prev_w > 0:
        out.append(f"Votre activité augmente — {this_w} session{'s' if this_w > 1 else ''} cette semaine vs {prev_w} la semaine dernière.")
    elif this_w < prev_w and prev_w > 0:
        out.append(f"Baisse d'activité détectée — {this_w} session{'s' if this_w != 1 else ''} cette semaine vs {prev_w} la semaine précédente.")
    elif this_w == 0 and analytics.get("total_sessions", 0) > 0:
        out.append("Aucune session cette semaine — reprenez votre rythme de révision.")

    s_this = analytics.get("avg_score_this_week")
    s_prev = analytics.get("avg_score_prev_week")
    if s_this and s_prev and abs(s_this - s_prev) > 0.04:
        if s_this > s_prev:
            out.append(f"Votre score progresse — {round(s_this * 100)}% cette semaine vs {round(s_prev * 100)}% la semaine précédente.")
        else:
            out.append(f"Votre score recule — {round(s_this * 100)}% cette semaine. Revoyez les notions fragiles.")
    elif s_this and not s_prev:
        out.append(f"Score moyen cette semaine : {round(s_this * 100)}%.")

    rate = analytics.get("completion_rate", 0)
    total = analytics.get("total_sessions", 0)
    if total >= 3:
        if rate >= 0.7:
            out.append("Vous terminez vos sessions régulièrement — bonne discipline d'apprentissage.")
        elif rate < 0.35:
            out.append("Beaucoup de sessions courtes — essayez de maintenir au moins 3 questions par session.")

    corpus = analytics.get("top_corpus_name")
    if corpus:
        out.append(f"Le corpus « {corpus} » est votre environnement le plus utilisé.")

    if not df.empty and len(df) >= 7:
        mean_ = df["n_attempts"].mean()
        std_  = df["n_attempts"].std()
        if mean_ > 0 and std_ / mean_ < 0.5:
            out.append("Votre régularité est bonne — des sessions fréquentes et stables.")

    return out


def _kpi_card(col, label: str, value: str, sub: str) -> None:
    col.markdown(
        f'<div style="background:#0B1530;border:1px solid rgba(120,140,255,0.15);'
        f'border-radius:12px;padding:14px 16px;margin-bottom:16px">'
        f'<div style="font-size:11px;color:#64748B;text-transform:uppercase;'
        f'letter-spacing:.07em;margin-bottom:6px">{label}</div>'
        f'<div style="font-size:24px;font-weight:800;color:#F8FAFC">{value}</div>'
        f'<div style="font-size:11px;color:#475569;margin-top:3px">{sub}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render() -> None:
    st.markdown(DARK_DASHBOARD_CSS, unsafe_allow_html=True)
    _uid = st.session_state.get("user_id") or "default"

    analytics   = get_session_analytics(_uid)
    df_activity = get_activity_data(_uid, days=56)
    sessions    = get_user_sessions(_uid, limit=10)

    # ── Header ──────────────────────────────────────────────────────────────
    st.markdown(
        '<div style="padding:18px 0 22px;border-bottom:1px solid rgba(120,140,255,0.13);'
        'margin-bottom:24px">'
        '<div style="display:flex;align-items:center;justify-content:space-between;'
        'flex-wrap:wrap;gap:10px">'
        '<div>'
        '<div style="font-size:26px;font-weight:800;color:#F8FAFC;letter-spacing:-0.02em">'
        "Analytics d'apprentissage</div>"
        '<div style="font-size:13px;color:#64748B;margin-top:5px">'
        'Observez comment vous apprenez et progressez.'
        '</div></div>'
        '<span style="background:rgba(124,58,237,0.13);border:1px solid rgba(124,58,237,0.35);'
        'border-radius:20px;padding:4px 14px;font-size:11px;font-weight:700;color:#A78BFA;'
        'text-transform:uppercase;letter-spacing:.08em">Beta</span>'
        '</div></div>',
        unsafe_allow_html=True,
    )

    total_sessions = analytics.get("total_sessions", 0)

    if total_sessions == 0:
        st.markdown(
            '<div style="background:#0B1530;border:1px dashed rgba(120,140,255,0.25);'
            'border-radius:14px;padding:48px 32px;text-align:center">'
            '<div style="font-size:36px;margin-bottom:12px">📊</div>'
            '<div style="font-size:16px;font-weight:700;color:#F8FAFC;margin-bottom:8px">'
            'Données insuffisantes</div>'
            '<div style="font-size:13px;color:#64748B">'
            "Commencez une session d'entraînement pour voir vos analytics."
            '</div></div>',
            unsafe_allow_html=True,
        )
        return

    # ── KPIs ────────────────────────────────────────────────────────────────
    _k1, _k2, _k3, _k4 = st.columns(4)
    _avg_dur   = analytics.get("avg_duration_seconds")
    _score_w   = analytics.get("avg_score_this_week")
    _compl     = analytics.get("completion_rate", 0)
    _sessions_w = analytics.get("sessions_this_week", 0)

    _kpi_card(_k1, "Sessions cette semaine", str(_sessions_w), f"{total_sessions} au total")
    _kpi_card(_k2, "Durée moy. session",     _fmt_duration(_avg_dur), "par session complète")
    _kpi_card(_k3, "Score moyen 7j",         f"{round(_score_w * 100)}%" if _score_w else "—", "derniers 7 jours")
    _kpi_card(_k4, "Taux de complétion",     f"{round(_compl * 100)}%", "sessions ≥ 3 questions")

    # ── Graphiques ───────────────────────────────────────────────────────────
    _g1, _g2 = st.columns([3, 2])

    with _g1:
        st.markdown(
            '<div style="font-size:12px;font-weight:700;color:#94A3B8;text-transform:uppercase;'
            'letter-spacing:.07em;margin-bottom:6px">Évolution du score (30 jours)</div>',
            unsafe_allow_html=True,
        )
        df_30 = get_activity_data(_uid, days=30)
        if not df_30.empty and len(df_30) >= 2:
            st.plotly_chart(_score_chart(df_30), use_container_width=True, config={"displayModeBar": False})
        else:
            st.caption("Pas assez de données pour ce graphique.")

    with _g2:
        st.markdown(
            '<div style="font-size:12px;font-weight:700;color:#94A3B8;text-transform:uppercase;'
            'letter-spacing:.07em;margin-bottom:6px">Activité (8 semaines)</div>',
            unsafe_allow_html=True,
        )
        if not df_activity.empty:
            st.plotly_chart(_heatmap_chart(df_activity), use_container_width=True, config={"displayModeBar": False})
        else:
            st.caption("Aucune activité récente.")

    # ── Insights ────────────────────────────────────────────────────────────
    insights = _gen_insights(analytics, df_activity)
    if insights:
        st.markdown(
            '<div style="font-size:12px;font-weight:700;color:#94A3B8;text-transform:uppercase;'
            'letter-spacing:.07em;margin:18px 0 10px">Insights</div>',
            unsafe_allow_html=True,
        )
        for insight in insights:
            st.markdown(
                f'<div style="background:rgba(124,58,237,0.07);border:1px solid '
                f'rgba(124,58,237,0.18);border-radius:8px;padding:9px 14px;'
                f'margin-bottom:6px;font-size:13px;color:#C4B5FD">'
                f'<span style="margin-right:8px">💡</span>{insight}</div>',
                unsafe_allow_html=True,
            )

    # ── Sessions récentes ────────────────────────────────────────────────────
    if sessions:
        st.markdown(
            '<div style="font-size:12px;font-weight:700;color:#94A3B8;text-transform:uppercase;'
            'letter-spacing:.07em;margin:20px 0 10px">Sessions récentes</div>',
            unsafe_allow_html=True,
        )
        for s in sessions[:8]:
            try:
                _dt = datetime.fromisoformat(str(s.get("started_at", "")))
                _date_str = _dt.strftime("%d/%m %H:%M")
            except Exception:
                _date_str = "—"
            _dur     = _fmt_duration(s.get("duration_seconds"))
            _q       = int(s.get("completed_questions") or 0)
            _sc      = s.get("avg_score")
            _sc_str  = f"{round(_sc * 100)}%" if _sc is not None else "—"
            _corpus_n = s.get("corpus_name") or "Toutes les sources"
            _closed  = s.get("ended_at") is not None
            _col_s   = "#34D399" if _closed else "#F59E0B"
            _status  = "Terminée" if _closed else "En cours"

            st.markdown(
                f'<div style="background:#0B1530;border:1px solid rgba(120,140,255,0.1);'
                f'border-radius:10px;padding:10px 14px;margin-bottom:6px;'
                f'display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px">'
                f'<div>'
                f'<span style="font-size:12px;color:#94A3B8">{_date_str}</span>'
                f'<span style="font-size:11px;color:#475569;margin-left:10px">{_corpus_n}</span>'
                f'</div>'
                f'<div style="display:flex;gap:12px;align-items:center;font-size:12px">'
                f'<span style="color:#64748B">{_q} question{"s" if _q != 1 else ""}</span>'
                f'<span style="color:#A78BFA;font-weight:600">{_sc_str}</span>'
                f'<span style="color:#64748B">{_dur}</span>'
                f'<span style="color:{_col_s};font-size:10px;font-weight:700">{_status}</span>'
                f'</div></div>',
                unsafe_allow_html=True,
            )
