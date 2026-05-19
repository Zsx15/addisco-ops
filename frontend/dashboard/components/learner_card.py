"""Composant LearnerCard — fiche individuelle d'un apprenant dans la cohorte."""
import streamlit as st

_STATUS_CFG: dict[str, dict] = {
    "active":   {"icon": "🟢", "label": "Actif"},
    "warning":  {"icon": "🟡", "label": "À suivre"},
    "critical": {"icon": "🔴", "label": "Critique"},
    "inactive": {"icon": "⚪", "label": "Inactif"},
}

_TREND_ICON: dict[str, str] = {
    "up": "📈", "down": "📉", "stable": "➡️",
}

_ERROR_FR: dict[str, str] = {
    "oubli_etape":      "Oubli d'étape",
    "confusion_notion": "Confusion de notion",
    "reponse_vague":    "Réponse vague",
    "erreur_ordre":     "Erreur d'ordre",
    "hors_sujet":       "Hors sujet",
}


def render_learner_card(learner: dict) -> None:
    status = _STATUS_CFG.get(learner.get("status", "active"), _STATUS_CFG["active"])
    score = float(learner.get("score", 0))
    score_pct = round(score * 100)
    score_color = "#15803d" if score >= 0.8 else ("#b45309" if score >= 0.6 else "#b91c1c")
    trend = _TREND_ICON.get(learner.get("trend", "stable"), "➡️")
    dom_err_raw = learner.get("dominant_error", "—")
    dom_err = _ERROR_FR.get(dom_err_raw, dom_err_raw)
    mastered = learner.get("mastered_sections", 0)
    fragile = learner.get("fragile_sections", 0)

    with st.container(border=True):
        col_info, col_score = st.columns([5, 1])
        with col_info:
            st.markdown(
                f"**{learner['username']}** &nbsp;"
                f'<span style="font-size:11px;color:#64748b">'
                f'{status["icon"]} {status["label"]} &nbsp;·&nbsp; {learner.get("last_active","—")}'
                f'</span>',
                unsafe_allow_html=True,
            )
            st.progress(min(score, 1.0), text=f"{score_pct} % de réussite")
            pills: list[str] = []
            if learner.get("profile"):
                pills.append(f'{learner.get("profile_icon","📊")} {learner["profile"]}')
            if learner.get("attempts"):
                pills.append(f'{learner["attempts"]} tentatives')
            if learner.get("days_active"):
                pills.append(f'{learner["days_active"]}j d\'étude')
            st.caption(" · ".join(pills) if pills else "Aucune donnée")
            if dom_err and dom_err != "—":
                st.caption(f"🔍 Difficulté dominante : **{dom_err}**")
        with col_score:
            mastery_line = f"🟢 {mastered} · 🔴 {fragile}" if (mastered or fragile) else ""
            st.markdown(
                f'<div style="text-align:center;padding:6px 0">'
                f'<div style="font-size:28px;font-weight:800;color:{score_color};'
                f'line-height:1;letter-spacing:-0.02em">{score_pct}%</div>'
                f'<div style="font-size:16px;margin-top:4px">{trend}</div>'
                f'<div style="font-size:10px;color:#64748b;margin-top:6px">{mastery_line}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
