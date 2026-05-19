"""Composant RecommendationPanel — recommandations pédagogiques générées par le moteur IA."""
import streamlit as st

_PRIORITY_CFG: dict[str, dict] = {
    "high":   {"color": "#dc2626", "bg": "#fef2f2", "label": "Prioritaire"},
    "medium": {"color": "#d97706", "bg": "#fffbeb", "label": "Recommandé"},
    "low":    {"color": "#2563eb", "bg": "#eff6ff", "label": "Suggestion"},
}


def render_recommendations(recommendations: list[dict]) -> None:
    if not recommendations:
        st.caption("Aucune recommandation active.")
        return
    for rec in recommendations:
        pconf = _PRIORITY_CFG.get(rec.get("priority", "low"), _PRIORITY_CFG["low"])
        html = (
            f'<div style="padding:12px 16px;background:#f8fafc;border:1px solid #e2e8f0;'
            f'border-left:3px solid {pconf["color"]};border-radius:8px;margin-bottom:8px">'
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:5px">'
            f'<span style="font-size:17px">{rec["icon"]}</span>'
            f'<span style="font-size:13px;font-weight:700;color:#0f172a">{rec["title"]}</span>'
            f'<span style="font-size:10px;font-weight:600;padding:1px 7px;border-radius:10px;'
            f'background:{pconf["bg"]};color:{pconf["color"]}">{pconf["label"]}</span>'
            f'</div>'
            f'<p style="font-size:12px;color:#475569;margin:0 0 5px;line-height:1.5">'
            f'{rec["description"]}</p>'
            f'<span style="font-size:11px;color:#94a3b8">👤 {rec.get("target","—")}</span>'
            f'</div>'
        )
        st.markdown(html, unsafe_allow_html=True)
