"""Composant AlertsPanel — panneau d'alertes pédagogiques du cockpit formateur."""
import streamlit as st


def render_alerts_panel(alerts: list[dict]) -> None:
    if not alerts:
        st.success("Aucune alerte pédagogique active.", icon="✅")
        return
    for alert in alerts:
        html = (
            f'<div style="display:flex;align-items:flex-start;gap:11px;'
            f'padding:10px 14px;background:{alert["bg"]};'
            f'border:1px solid {alert["border"]};'
            f'border-left:4px solid {alert["color"]};'
            f'border-radius:8px;margin-bottom:5px;'
            f'transition:opacity .15s ease">'
            f'<span style="font-size:17px;flex-shrink:0;margin-top:1px">{alert["icon"]}</span>'
            f'<div style="flex:1">'
            f'<div style="font-size:11.5px;font-weight:700;color:{alert["color"]};margin-bottom:2px">'
            f'{alert["learner"]}</div>'
            f'<div style="font-size:12px;color:#1e293b;margin-bottom:4px">'
            f'{alert["message"]}</div>'
            f'<div style="font-size:11px;color:#475569">'
            f'💬 <em>{alert["recommendation"]}</em></div>'
            f'</div></div>'
        )
        st.markdown(html, unsafe_allow_html=True)
