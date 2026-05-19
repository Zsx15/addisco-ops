"""Composant LearnerCard — fiche compacte individuelle d'un apprenant.

Rendu entièrement en HTML dans un seul st.markdown() pour maximiser
la densité visuelle et éviter le surpadding Streamlit natif.
La classe CSS `.lc` est définie dans _COCKPIT_CSS (trainer_dashboard.py).
"""
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

_PILL = (
    '<span style="font-size:10.5px;color:#475569;background:#f8fafc;'
    'padding:2px 8px;border-radius:10px;border:1px solid #e2e8f0">{}</span>'
)


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

    # Pills row
    pills: list[str] = []
    if learner.get("profile"):
        pills.append(f'{learner.get("profile_icon", "📊")} {learner["profile"]}')
    if learner.get("attempts"):
        pills.append(f'{learner["attempts"]} tentatives')
    if learner.get("days_active"):
        pills.append(f'{learner["days_active"]}j d\'étude')
    if dom_err and dom_err not in ("—", ""):
        pills.append(f"🔍 {dom_err}")
    pills_html = " ".join(_PILL.format(p) for p in pills)

    mastery_html = (
        f'<div style="font-size:10px;color:#64748b;margin-top:4px">'
        f'🟢&nbsp;{mastered}&nbsp;·&nbsp;🔴&nbsp;{fragile}</div>'
        if (mastered or fragile) else ""
    )

    html = (
        f'<div class="lc">'
        # ── Top row ──────────────────────────────────────────
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start">'
        # Left block: name + progress + pills
        f'<div style="flex:1;min-width:0;margin-right:14px">'
        f'<div style="margin-bottom:7px">'
        f'<span style="font-size:13.5px;font-weight:700;color:#0f172a">'
        f'{learner["username"]}</span>'
        f'<span style="font-size:10.5px;color:#64748b;margin-left:8px">'
        f'{status["icon"]} {status["label"]}</span>'
        f'<span style="font-size:10px;color:#94a3b8;margin-left:6px">'
        f'· {learner.get("last_active", "—")}</span>'
        f'</div>'
        # Progress bar
        f'<div style="background:#f1f5f9;border-radius:3px;height:5px;'
        f'margin-bottom:8px;overflow:hidden">'
        f'<div style="width:{score_pct}%;background:{score_color};'
        f'height:100%;border-radius:3px"></div>'
        f'</div>'
        # Pills
        f'<div style="display:flex;flex-wrap:wrap;gap:5px">{pills_html}</div>'
        f'</div>'
        # Right block: score + trend
        f'<div style="text-align:right;flex-shrink:0;padding-top:2px">'
        f'<div style="font-size:26px;font-weight:800;color:{score_color};'
        f'letter-spacing:-0.03em;line-height:1">{score_pct}%</div>'
        f'<div style="font-size:14px;margin-top:4px">{trend}</div>'
        f'{mastery_html}'
        f'</div>'
        f'</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)
