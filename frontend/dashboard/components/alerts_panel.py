"""Composant AlertsPanel — panneau d'alertes pédagogiques du cockpit formateur."""
import streamlit as st


def render_alerts_panel(alerts: list[dict]) -> None:
    if not alerts:
        st.success("Aucune alerte pédagogique active.", icon="✅")
        return
    for alert in alerts:
        html = (
            f'<div style="display:flex;align-items:flex-start;gap:12px;'
            f'padding:12px 16px;background:{alert["bg"]};'
            f'border:1px solid {alert["border"]};'
            f'border-left:4px solid {alert["color"]};'
            f'border-radius:8px;margin-bottom:6px">'
            f'<span style="font-size:18px;flex-shrink:0;margin-top:1px">{alert["icon"]}</span>'
            f'<div style="flex:1">'
            f'<div style="font-size:12px;font-weight:700;color:{alert["color"]};margin-bottom:3px">'
            f'{alert["learner"]}</div>'
            f'<div style="font-size:12.5px;color:#1e293b;margin-bottom:5px">'
            f'{alert["message"]}</div>'
            f'<div style="font-size:11.5px;color:#475569">'
            f'💬 <em>{alert["recommendation"]}</em></div>'
            f'</div></div>'
        )
        st.markdown(html, unsafe_allow_html=True)
