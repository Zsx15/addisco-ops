"""Composant RecommendationPanel — recommandations pédagogiques générées par le moteur IA.

La classe `.rec-card` et son hover sont définis dans _COCKPIT_CSS (trainer_dashboard.py).
"""
import streamlit as st

_PRIORITY_CFG: dict[str, dict] = {
    "high":   {"color": "#dc2626", "bg": "#fef2f2", "label": "Prioritaire", "border": "#dc2626"},
    "medium": {"color": "#d97706", "bg": "#fffbeb", "label": "Recommandé",  "border": "#d97706"},
    "low":    {"color": "#2563eb", "bg": "#eff6ff", "label": "Suggestion",  "border": "#93c5fd"},
}


def render_recommendations(recommendations: list[dict]) -> None:
    if not recommendations:
        st.caption("Aucune recommandation active.")
        return
    for rec in recommendations:
        pconf = _PRIORITY_CFG.get(rec.get("priority", "low"), _PRIORITY_CFG["low"])
        html = (
            f'<div class="rec-card" style="border-left:3px solid {pconf["border"]}">'
            f'<div style="display:flex;align-items:center;gap:7px;margin-bottom:4px">'
            f'<span style="font-size:16px">{rec["icon"]}</span>'
            f'<span style="font-size:12.5px;font-weight:700;color:#0f172a">{rec["title"]}</span>'
            f'<span style="font-size:9.5px;font-weight:600;padding:1px 6px;border-radius:9px;'
            f'background:{pconf["bg"]};color:{pconf["color"]};flex-shrink:0">'
            f'{pconf["label"]}</span>'
            f'</div>'
            f'<p style="font-size:11.5px;color:#475569;margin:0 0 4px;line-height:1.5">'
            f'{rec["description"]}</p>'
            f'<span style="font-size:10.5px;color:#94a3b8">👤 {rec.get("target","—")}</span>'
            f'</div>'
        )
        st.markdown(html, unsafe_allow_html=True)
