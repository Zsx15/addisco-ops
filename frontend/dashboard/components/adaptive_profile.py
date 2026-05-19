"""Composant AdaptiveProfile — profils d'apprentissage détectés par le moteur IA."""
import streamlit as st


def render_adaptive_profiles(profiles: list[dict]) -> None:
    if not profiles:
        st.caption("Aucun profil détecté — données insuffisantes.")
        return
    cols = st.columns(2)
    for i, profile in enumerate(profiles):
        with cols[i % 2]:
            with st.container(border=True):
                st.markdown(
                    f'<span style="background:{profile["badge_bg"]};'
                    f'color:{profile["badge_text"]};'
                    f'font-size:11px;font-weight:700;padding:3px 10px;'
                    f'border-radius:12px;display:inline-block;margin-bottom:8px">'
                    f'{profile["icon"]} {profile["name"]}</span>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<p style="font-size:12px;color:#334155;margin:0 0 6px;'
                    f'line-height:1.5">{profile["description"]}</p>',
                    unsafe_allow_html=True,
                )
                st.caption(f"💡 {profile['impact']}")
                if profile.get("learners"):
                    st.caption("👤 " + " · ".join(profile["learners"]))
