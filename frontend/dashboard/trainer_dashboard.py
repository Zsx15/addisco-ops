"""
Cockpit Pédagogique Formateur — TASK-056 / TASK-056B
Orchestrateur principal : données réelles (cohorte >= 2 apprenants)
ou mock data (démonstration) avec même interface.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from database import (
    classify_mastery,
    get_all_users,
    get_attempts,
    get_chunk_stats,
    get_documents,
    get_error_frequency,
    get_learning_profile,
    get_score_evolution,
)
from frontend.dashboard.components.adaptive_profile import render_adaptive_profiles
from frontend.dashboard.components.alerts_panel import render_alerts_panel
from frontend.dashboard.components.learner_card import render_learner_card
from frontend.dashboard.components.progress_chart import render_error_heatmap, render_score_chart
from frontend.dashboard.components.recommendation_panel import render_recommendations
from frontend.dashboard.components.stat_card import stat_card_html
from frontend.dashboard.mock_data.trainer_mock_data import (
    MOCK_ADAPTIVE_PROFILES,
    MOCK_ALERTS,
    MOCK_LEARNERS,
    MOCK_RECOMMENDATIONS,
)

_PEDAGOGY_LABELS: dict[str, tuple[str, str]] = {
    "logical":    ("Analytique",  "🔬"),
    "procedural": ("Procédural",  "⚙️"),
    "narrative":  ("Narratif",    "📖"),
    "analogy":    ("Analogique",  "🔗"),
}

# ── CSS global injecté une seule fois au démarrage du render() ─────────────
_COCKPIT_CSS = """
<style>
/* ── SYNPZ OPS — Cockpit Formateur ── */

/* Learner cards */
.lc {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 12px 16px;
  margin-bottom: 8px;
  box-shadow: 0 1px 3px rgba(15,23,42,.05);
  transition: box-shadow .15s ease, border-color .15s ease;
}
.lc:hover {
  box-shadow: 0 4px 14px rgba(79,70,229,.10);
  border-color: #c7d2fe;
}

/* Adaptive profile cards */
.ap-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 12px 14px;
  box-shadow: 0 1px 3px rgba(15,23,42,.04);
  transition: box-shadow .15s ease, border-color .15s ease;
}
.ap-card:hover {
  box-shadow: 0 3px 10px rgba(15,23,42,.08);
  border-color: #cbd5e1;
}

/* Recommendation cards */
.rec-card {
  padding: 10px 14px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  margin-bottom: 7px;
  transition: box-shadow .12s ease;
}
.rec-card:hover {
  box-shadow: 0 2px 8px rgba(15,23,42,.07);
  background: #f1f5f9;
}

/* Streamlit containers hover */
div[data-testid="stVerticalBlockBorderWrapper"] > div {
  transition: box-shadow .15s ease;
}
div[data-testid="stVerticalBlockBorderWrapper"] > div:hover {
  box-shadow: 0 3px 12px rgba(15,23,42,.08) !important;
}
</style>
"""

# ── Tendances mock pour le mode démonstration ──────────────────────────────
_MOCK_KPI_TRENDS: dict[str, str] = {
    "score":   "↗ +8 pts cette semaine",
    "active":  "→ stable",
    "docs":    "",
    "alerts":  "↘ −1 vs hier",
}


def _score_trend_str(df_evo: pd.DataFrame) -> str:
    """Calcule un indicateur de tendance depuis l'évolution de score."""
    if len(df_evo) < 6:
        return ""
    mid = len(df_evo) // 2
    old_avg = float(df_evo["score"].iloc[:mid].mean())
    new_avg = float(df_evo["score"].iloc[mid:].mean())
    delta = round((new_avg - old_avg) * 100)
    if delta >= 3:
        return f"↗ +{delta} pts"
    if delta <= -3:
        return f"↘ {delta} pts"
    return "→ stable"


def _build_real_learner(user: dict) -> dict:
    """Construit un profil apprenant normalisé depuis les données réelles."""
    uid = user["user_id"]
    uname = user.get("username", uid)

    df = get_attempts(user_id=uid)
    if df.empty:
        return {
            "username": uname, "user_id": uid, "score": 0.0, "attempts": 0,
            "days_active": 0, "mastered_sections": 0, "fragile_sections": 0,
            "dominant_error": "—", "profile": "Aucune donnée", "profile_icon": "❓",
            "status": "inactive", "trend": "stable", "momentum": 0.0,
            "last_active": "Jamais",
        }

    scores = df["score"].dropna()
    avg_score = float(scores.mean()) if len(scores) else 0.0
    days_active = df["created_at"].apply(lambda x: str(x)[:10]).nunique()

    dominant_error = "—"
    if "error_type" in df.columns:
        err_df = df[
            df["error_type"].notna()
            & (df["error_type"] != "correct")
            & (df["error_type"] != "")
        ]
        if not err_df.empty:
            dominant_error = str(err_df["error_type"].mode().iloc[0])

    df_chunks = get_chunk_stats(user_id=uid)
    df_mastery = classify_mastery(df_chunks) if not df_chunks.empty else pd.DataFrame()
    mastered_n = int((df_mastery["mastery_class"] == "Maîtrisé").sum()) if not df_mastery.empty else 0
    fragile_n  = int((df_mastery["mastery_class"] == "Fragile").sum())   if not df_mastery.empty else 0

    profile_name, profile_icon, momentum = "—", "📊", 0.0
    profile_data = get_learning_profile(uid)
    if profile_data:
        momentum = float(profile_data.get("momentum") or 0)
        p = profile_data.get("preferred_pedagogy")
        if p:
            profile_name, profile_icon = _PEDAGOGY_LABELS.get(p, (p, "📊"))

    trend = "up" if momentum > 0.05 else ("down" if momentum < -0.05 else "stable")

    if avg_score < 0.5 or fragile_n > mastered_n + 2:
        status = "critical"
    elif avg_score < 0.65 or (fragile_n > 0 and days_active < 3):
        status = "warning"
    else:
        status = "active"

    try:
        last_active = str(df["created_at"].max())[:10]
    except Exception:
        last_active = "—"

    return {
        "username": uname, "user_id": uid, "score": avg_score,
        "attempts": len(df), "days_active": days_active,
        "mastered_sections": mastered_n, "fragile_sections": fragile_n,
        "dominant_error": dominant_error, "profile": profile_name,
        "profile_icon": profile_icon, "status": status,
        "trend": trend, "momentum": momentum, "last_active": last_active,
    }


def _build_alerts(learners: list[dict]) -> list[dict]:
    alerts: list[dict] = []
    for l in learners:
        if l.get("status") == "critical":
            alerts.append({
                "severity": "critical", "icon": "🚨",
                "color": "#dc2626", "bg": "#fef2f2", "border": "#fecaca",
                "learner": l["username"],
                "message": (
                    f"Score moyen {round(l['score']*100)} % — "
                    f"{l['fragile_sections']} section(s) fragile(s) identifiée(s)."
                ),
                "recommendation": "Planifier une révision guidée des sections fragiles.",
            })
        elif l.get("status") == "warning":
            alerts.append({
                "severity": "warning", "icon": "⚠️",
                "color": "#b45309", "bg": "#fffbeb", "border": "#fde68a",
                "learner": l["username"],
                "message": f"Progression ralentie — score moyen {round(l['score']*100)} %.",
                "recommendation": "Varier les types de questions et injecter du rappel actif.",
            })
    return alerts


def _build_recommendations(learners: list[dict]) -> list[dict]:
    recs: list[dict] = []
    critical = [l["username"] for l in learners if l.get("status") == "critical"]
    if critical:
        recs.append({
            "icon": "🔄", "title": "Renforcer le rappel actif", "priority": "high",
            "description": "Apprenants en difficulté — révision immédiate des sections fragiles recommandée.",
            "target": ", ".join(critical),
        })
    low_score = [l["username"] for l in learners if float(l.get("score", 1)) < 0.65]
    if low_score:
        recs.append({
            "icon": "📏", "title": "Adapter la complexité des questions", "priority": "medium",
            "description": "Score moyen < 65 % — envisager des questions plus courtes et progressives.",
            "target": ", ".join(low_score),
        })
    recs.append({
        "icon": "🎯", "title": "Varier les formulations", "priority": "medium",
        "description": "Proposer des reformulations alternatives pour les notions à erreur récurrente.",
        "target": "Cohorte",
    })
    return recs


def _build_report(learners: list[dict], alerts: list[dict], recs: list[dict]) -> str:
    from frontend.dashboard.components.learner_card import _ERROR_FR
    sep = "─" * 60
    n = len(learners)
    avg = round(sum(l["score"] for l in learners) / n * 100) if n else 0
    n_active = sum(1 for l in learners if l.get("status") == "active")
    lines = [
        "SYNPZ OPS — Rapport Formateur",
        f"Généré le {pd.Timestamp.now().strftime('%d/%m/%Y à %H:%M')}",
        sep, "",
        "SYNTHÈSE COHORTE",
        f"  Apprenants suivis  : {n}",
        f"  Score moyen        : {avg} %",
        f"  Apprenants actifs  : {n_active}",
        f"  Alertes actives    : {len(alerts)}",
        "",
    ]
    if learners:
        lines += ["DÉTAIL PAR APPRENANT", sep]
        for l in learners:
            err_label = _ERROR_FR.get(l.get("dominant_error", ""), l.get("dominant_error", "—"))
            lines += [
                f"  {l['username']}",
                f"    Score moyen      : {round(l['score']*100)} %",
                f"    Tentatives       : {l.get('attempts','—')}",
                f"    Jours d'étude    : {l.get('days_active','—')}",
                f"    Profil IA        : {l.get('profile','—')}",
                f"    Difficulté dom.  : {err_label}",
                f"    Sections maît.   : {l.get('mastered_sections','—')}",
                f"    Sections fragiles: {l.get('fragile_sections','—')}",
                "",
            ]
    if alerts:
        lines += ["ALERTES PÉDAGOGIQUES", sep]
        for a in alerts:
            lines += [
                f"  [{a['severity'].upper()}] {a['learner']}",
                f"    {a['message']}",
                f"    → {a['recommendation']}", "",
            ]
    if recs:
        lines += ["RECOMMANDATIONS IA", sep]
        for r in recs:
            lines += [
                f"  {r['title']} [{r.get('priority','').upper()}]",
                f"    {r['description']}",
                f"    Cible : {r.get('target','—')}", "",
            ]
    return "\n".join(lines)


def _section_header(icon: str, title: str) -> None:
    st.markdown(
        f"<p style='font-size:11px;font-weight:700;color:#4f46e5;margin:0 0 10px;"
        f"text-transform:uppercase;letter-spacing:.09em'>{icon} {title}</p>",
        unsafe_allow_html=True,
    )


def render(current_user_id: str = "default") -> None:
    """Cockpit pédagogique formateur — point d'entrée principal."""

    # ── CSS global ────────────────────────────────────────────────────────────
    st.markdown(_COCKPIT_CSS, unsafe_allow_html=True)

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(
        "<div style='border-left:4px solid #4f46e5;padding-left:12px;margin-bottom:12px'>"
        "<h3 style='margin:0 0 2px;color:#0f172a;font-size:16px;font-weight:800;"
        "letter-spacing:-0.01em'>🎓 Cockpit Pédagogique Formateur</h3>"
        "<p style='color:#64748b;font-size:11.5px;margin:0'>"
        "Vue superviseur — cohorte · alertes IA · recommandations adaptatives</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    # ── Données ───────────────────────────────────────────────────────────────
    real_apprenants: list[dict] = []
    try:
        real_apprenants = [u for u in get_all_users() if u.get("role") == "apprenant"]
    except Exception:
        pass

    use_mock = len(real_apprenants) < 2
    if use_mock:
        learners = MOCK_LEARNERS
        alerts = MOCK_ALERTS
        recs = MOCK_RECOMMENDATIONS
        adaptive_profiles = MOCK_ADAPTIVE_PROFILES
    else:
        learners = [_build_real_learner(u) for u in real_apprenants]
        alerts = _build_alerts(learners)
        recs = _build_recommendations(learners)
        adaptive_profiles = MOCK_ADAPTIVE_PROFILES  # structure prête pour branchement réel

    if use_mock:
        st.info(
            "**Mode démonstration** — données simulées. "
            "Inscrivez des apprenants pour activer les données réelles.",
            icon="📊",
        )

    # ── Calcul tendances KPI ─────────────────────────────────────────────────
    if use_mock:
        trend_score  = _MOCK_KPI_TRENDS["score"]
        trend_active = _MOCK_KPI_TRENDS["active"]
        trend_alerts = _MOCK_KPI_TRENDS["alerts"]
    else:
        df_evo_ref   = get_score_evolution(limit=20, user_id=current_user_id)
        trend_score  = _score_trend_str(df_evo_ref)
        trend_active = ""
        trend_alerts = ""

    # ── KPI Header ────────────────────────────────────────────────────────────
    n_learners = len(learners)
    avg_score_raw = sum(l["score"] for l in learners) / n_learners if learners else 0.0
    avg_score = round(avg_score_raw * 100)
    n_active  = sum(1 for l in learners if l.get("status") == "active")
    n_alerts  = len(alerts)
    docs      = get_documents()
    n_docs    = len(docs) if not docs.empty else 0
    score_color = "#15803d" if avg_score >= 80 else ("#b45309" if avg_score >= 60 else "#dc2626")
    alerts_color = "#dc2626" if n_alerts > 0 else "#15803d"

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.markdown(stat_card_html("👥", "Apprenants",   str(n_learners)), unsafe_allow_html=True)
    k2.markdown(stat_card_html("📈", "Score moyen",  f"{avg_score} %",  score_color,  trend_str=trend_score),  unsafe_allow_html=True)
    k3.markdown(stat_card_html("⚡", "Actifs",       str(n_active),    "#334155",     trend_str=trend_active), unsafe_allow_html=True)
    k4.markdown(stat_card_html("📄", "Documents",    str(n_docs)),      unsafe_allow_html=True)
    k5.markdown(stat_card_html("⚠️", "Alertes",      str(n_alerts),    alerts_color,  trend_str=trend_alerts, alert=n_alerts > 0), unsafe_allow_html=True)

    st.divider()

    # ── Alertes pédagogiques ──────────────────────────────────────────────────
    if alerts:
        _section_header("⚠️", "Alertes pédagogiques")
        render_alerts_panel(alerts)
        st.divider()

    # ── Cartes apprenants — 2 colonnes ────────────────────────────────────────
    _section_header("👥", "Apprenants")
    _lc = st.columns(2)
    for _i, _learner in enumerate(learners):
        with _lc[_i % 2]:
            render_learner_card(_learner)
    st.divider()

    # ── Profils adaptatifs ───────────────────────────────────────────────────
    _section_header("🧠", "Profils détectés par l'IA")
    render_adaptive_profiles(adaptive_profiles)
    st.divider()

    # ── Analyse de performance ───────────────────────────────────────────────
    _section_header("📊", "Analyse de performance")
    col_chart, col_errors = st.columns([3, 2])
    with col_chart:
        with st.container(border=True):
            st.caption("📈 Évolution du score — session formateur")
            df_evo = get_score_evolution(limit=20, user_id=current_user_id)
            render_score_chart(df_evo)
    with col_errors:
        with st.container(border=True):
            st.caption("🔍 Distribution des erreurs")
            df_errors = get_error_frequency(user_id=current_user_id)
            render_error_heatmap(df_errors)
    st.divider()

    # ── Recommandations IA ───────────────────────────────────────────────────
    _section_header("💡", "Recommandations pédagogiques IA")
    render_recommendations(recs)
    st.divider()

    # ── Export rapport ───────────────────────────────────────────────────────
    report_txt = _build_report(learners, alerts, recs)
    st.download_button(
        "📥 Exporter le rapport formateur (.txt)",
        data=report_txt.encode("utf-8-sig"),
        file_name=f"rapport_formateur_{pd.Timestamp.now().strftime('%Y%m%d')}.txt",
        mime="text/plain",
        use_container_width=True,
    )
