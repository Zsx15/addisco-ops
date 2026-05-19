"""Composant AdaptiveProfile — profils d'apprentissage détectés par le moteur IA.

Rendu en CSS grid HTML pour une densité maximale et sans overhead Streamlit columns.
La classe `.ap-card` et son effet hover sont définis dans _COCKPIT_CSS.
"""
import streamlit as st


def render_adaptive_profiles(profiles: list[dict]) -> None:
    if not profiles:
        st.caption("Aucun profil détecté — données insuffisantes.")
        return

    cards_html = ""
    for profile in profiles:
        learner_str = " · ".join(profile.get("learners", []))
        learners_html = (
            f'<div style="font-size:10.5px;color:#94a3b8;margin-top:3px">'
            f'👤 {learner_str}</div>'
            if learner_str else ""
        )
        cards_html += (
            f'<div class="ap-card">'
            f'<div style="margin-bottom:7px">'
            f'<span style="background:{profile["badge_bg"]};color:{profile["badge_text"]};'
            f'font-size:10.5px;font-weight:700;padding:2px 9px;border-radius:10px;'
            f'display:inline-block">{profile["icon"]} {profile["name"]}</span>'
            f'</div>'
            f'<p style="font-size:11.5px;color:#334155;margin:0 0 5px;line-height:1.5">'
            f'{profile["description"]}</p>'
            f'<p style="font-size:11px;color:#475569;margin:0 0 2px">'
            f'💡 {profile["impact"]}</p>'
            f'{learners_html}'
            f'</div>'
        )

    st.markdown(
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">'
        f'{cards_html}</div>',
        unsafe_allow_html=True,
    )
