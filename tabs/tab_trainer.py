"""Onglet Formateur — cockpit pédagogique superviseur (TASK-056)."""
import streamlit as st

from auth_service import promote_user
from database import get_all_users
from frontend.dashboard.trainer_dashboard import render as _render_cockpit

_ROLE_LABELS_ADM = {"admin": "Administrateur", "formateur": "Formateur", "apprenant": "Apprenant"}
_PROMO_OPTS = {"apprenant": ["formateur", "admin"], "formateur": ["admin"], "admin": []}


def _render_admin_section() -> None:
    if st.session_state.get("role") != "admin":
        return
    st.divider()
    st.markdown(
        "<p style='font-size:12px;font-weight:700;color:#475569;margin:0 0 8px;"
        "text-transform:uppercase;letter-spacing:.07em'>Administration — Gestion des rôles</p>",
        unsafe_allow_html=True,
    )
    try:
        _users = get_all_users()
    except Exception:
        st.warning("Impossible de charger la liste des utilisateurs.")
        return
    _me = st.session_state.get("username", "")
    for _u in _users:
        _uname = _u["username"]
        _urole = _u["role"]
        _opts  = _PROMO_OPTS.get(_urole, [])
        with st.container(border=True):
            _col1, _col2, _col3 = st.columns([2, 1, 2])
            _col1.markdown(f"**{_uname}**")
            _col2.caption(_ROLE_LABELS_ADM.get(_urole, _urole))
            with _col3:
                if _uname == _me:
                    st.caption("*(vous)*")
                elif not _opts:
                    st.caption("—")
                else:
                    _sel = st.selectbox(
                        "Rôle cible",
                        options=_opts,
                        key=f"promo_sel_{_uname}",
                        label_visibility="collapsed",
                        format_func=lambda r: _ROLE_LABELS_ADM.get(r, r),
                    )
                    if st.button("Promouvoir", key=f"promo_btn_{_uname}", type="primary"):
                        try:
                            promote_user(_me, _uname, _sel)
                            st.success(f"{_uname} promu {_ROLE_LABELS_ADM.get(_sel, _sel)}.")
                            st.rerun()
                        except ValueError as _ve:
                            st.error(str(_ve))


def render() -> None:
    _render_cockpit(current_user_id=st.session_state.get("user_id", "default"))
    _render_admin_section()
