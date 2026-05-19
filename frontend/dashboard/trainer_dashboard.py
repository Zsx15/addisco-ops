"""
Cockpit Pédagogique Formateur — TASK-056
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


def render(current_user_id: str = "default") -> None:
    """Cockpit pédagogique formateur — point d'entrée principal."""

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(
        "<h3 style='margin:0 0 4px;color:#0f172a;font-size:16px;font-weight:800;"
        "letter-spacing:-0.01em'>🎓 Cockpit Pédagogique Formateur</h3>"
        "<p style='color:#64748b;font-size:12px;margin:0 0 16px'>"
        "Vue superviseur — suivi de cohorte, alertes IA, recommandations adaptatives.</p>",
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

    # ── KPI Header ────────────────────────────────────────────────────────────
    n_learners = len(learners)
    avg_score_raw = sum(l["score"] for l in learners) / n_learners if learners else 0.0
    avg_score = round(avg_score_raw * 100)
    n_active = sum(1 for l in learners if l.get("status") == "active")
    n_alerts = len(alerts)
    docs = get_documents()
    n_docs = len(docs) if not docs.empty else 0
    score_color = "#15803d" if avg_score >= 80 else ("#b45309" if avg_score >= 60 else "#dc2626")

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.markdown(stat_card_html("👥", "Apprenants", str(n_learners)), unsafe_allow_html=True)
    k2.markdown(stat_card_html("📈", "Score moyen", f"{avg_score} %", score_color), unsafe_allow_html=True)
    k3.markdown(stat_card_html("⚡", "Actifs", str(n_active)), unsafe_allow_html=True)
    k4.markdown(stat_card_html("📄", "Documents", str(n_docs)), unsafe_allow_html=True)
    k5.markdown(
        stat_card_html("⚠️", "Alertes", str(n_alerts),
                       "#dc2626" if n_alerts > 0 else "#15803d",
                       alert=n_alerts > 0),
        unsafe_allow_html=True,
    )

    st.divider()

    # ── Alertes pédagogiques ──────────────────────────────────────────────────
    if alerts:
        st.markdown(
            "<p style='font-size:12px;font-weight:700;color:#475569;margin:0 0 8px;"
            "text-transform:uppercase;letter-spacing:.07em'>⚠️ Alertes pédagogiques</p>",
            unsafe_allow_html=True,
        )
        render_alerts_panel(alerts)
        st.divider()

    # ── Cartes apprenants ────────────────────────────────────────────────────
    st.markdown(
        "<p style='font-size:12px;font-weight:700;color:#475569;margin:0 0 10px;"
        "text-transform:uppercase;letter-spacing:.07em'>👥 Apprenants</p>",
        unsafe_allow_html=True,
    )
    for learner in learners:
        render_learner_card(learner)
    st.divider()

    # ── Profils adaptatifs ───────────────────────────────────────────────────
    st.markdown(
        "<p style='font-size:12px;font-weight:700;color:#475569;margin:0 0 10px;"
        "text-transform:uppercase;letter-spacing:.07em'>🧠 Profils détectés par l'IA</p>",
        unsafe_allow_html=True,
    )
    render_adaptive_profiles(adaptive_profiles)
    st.divider()

    # ── Analyse de performance ───────────────────────────────────────────────
    st.markdown(
        "<p style='font-size:12px;font-weight:700;color:#475569;margin:0 0 10px;"
        "text-transform:uppercase;letter-spacing:.07em'>📊 Analyse de performance</p>",
        unsafe_allow_html=True,
    )
    col_chart, col_errors = st.columns([3, 2])
    with col_chart:
        st.caption("Évolution du score — session formateur")
        df_evo = get_score_evolution(limit=20, user_id=current_user_id)
        render_score_chart(df_evo)
    with col_errors:
        st.caption("Distribution des erreurs")
        df_errors = get_error_frequency(user_id=current_user_id)
        render_error_heatmap(df_errors)
    st.divider()

    # ── Recommandations IA ───────────────────────────────────────────────────
    st.markdown(
        "<p style='font-size:12px;font-weight:700;color:#475569;margin:0 0 10px;"
        "text-transform:uppercase;letter-spacing:.07em'>💡 Recommandations pédagogiques IA</p>",
        unsafe_allow_html=True,
    )
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
