"""
tab_admin.py — Vue Admin (TASK-061)

Supervision utilisateurs, documents, stats globales et alertes système.
Visible uniquement pour le rôle 'admin'.
"""
import streamlit as st

from db.admin import (
    get_all_users,
    set_user_active,
    set_user_role,
    get_platform_stats,
    get_document_admin_stats,
    get_system_alerts,
)

_ROLES = ["apprenant", "formateur", "admin"]

_ROLE_BADGE = {
    "admin":     "🔴 admin",
    "formateur": "🟡 formateur",
    "apprenant": "🟢 apprenant",
}


def _kpi(label: str, value: str, color: str = "#4f46e5") -> str:
    return (
        f'<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;'
        f'padding:16px 20px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,.06)">'
        f'<div style="font-size:26px;font-weight:800;color:{color}">{value}</div>'
        f'<div style="font-size:11px;text-transform:uppercase;letter-spacing:.07em;'
        f'color:#64748b;margin-top:4px">{label}</div></div>'
    )


def render() -> None:
    role = st.session_state.get("role")
    if role != "admin":
        st.warning("Accès réservé aux administrateurs.")
        return

    current_username = st.session_state.get("username", "")

    st.markdown("### Administration ADDISCO OPS")

    # ── Zone 1 : KPIs globaux ────────────────────────────────────────────────
    stats = get_platform_stats()

    avg_str = f"{stats['avg_score']:.0%}" if stats["avg_score"] is not None else "—"
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            _kpi("Utilisateurs", str(stats["n_users"])),
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            _kpi("Comptes actifs", str(stats["n_active_users"]), "#16a34a"),
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            _kpi("Documents", str(stats["n_docs"]), "#0ea5e9"),
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            _kpi("Score moyen plateforme", avg_str, "#d97706"),
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Zone 2 : Alertes système ─────────────────────────────────────────────
    alerts = get_system_alerts()
    has_alert = (
        alerts["orphan_chunks"] > 0
        or alerts["bad_docs"] > 0
        or alerts["dead_skills"] > 0
    )

    with st.expander("⚠️ Alertes système", expanded=has_alert):
        a1, a2, a3, a4 = st.columns(4)
        with a1:
            color = "#dc2626" if alerts["orphan_chunks"] > 10 else "#d97706" if alerts["orphan_chunks"] > 0 else "#16a34a"
            st.markdown(
                _kpi("Chunks orphelins", str(alerts["orphan_chunks"]), color),
                unsafe_allow_html=True,
            )
        with a2:
            color = "#dc2626" if alerts["bad_docs"] > 0 else "#16a34a"
            st.markdown(
                _kpi("Docs problématiques", str(alerts["bad_docs"]), color),
                unsafe_allow_html=True,
            )
        with a3:
            color = "#d97706" if alerts["dead_skills"] > 0 else "#16a34a"
            st.markdown(
                _kpi("Skills inactifs", str(alerts["dead_skills"]), color),
                unsafe_allow_html=True,
            )
        with a4:
            color = "#6366f1" if alerts["disabled_users"] > 0 else "#16a34a"
            st.markdown(
                _kpi("Comptes désactivés", str(alerts["disabled_users"]), color),
                unsafe_allow_html=True,
            )
        if has_alert:
            st.caption(
                "Pour le détail complet : `python tools/maintenance/maintenance_report.py`"
            )

    st.divider()

    # ── Zone 3 : Gestion utilisateurs ────────────────────────────────────────
    st.markdown("#### Utilisateurs")

    users = get_all_users()
    if not users:
        st.info("Aucun utilisateur enregistré.")
    else:
        for u in users:
            is_self   = u["username"] == current_username
            is_active = bool(u.get("is_active", 1))
            badge     = _ROLE_BADGE.get(u["role"], u["role"])

            with st.container(border=True):
                col_info, col_role, col_toggle = st.columns([4, 2, 2])

                with col_info:
                    status_icon = "✅" if is_active else "🔒"
                    st.markdown(
                        f"**{status_icon} {u['username']}** &nbsp; {badge}",
                        unsafe_allow_html=True,
                    )
                    last_att = u.get("last_attempt") or "—"
                    if last_att != "—":
                        last_att = str(last_att)[:10]
                    st.caption(
                        f"{u['n_attempts']} tentative(s) · "
                        f"Dernière activité : {last_att} · "
                        f"Créé : {str(u['created_at'])[:10]}"
                    )

                with col_role:
                    if not is_self:
                        new_role = st.selectbox(
                            "Rôle",
                            options=_ROLES,
                            index=_ROLES.index(u["role"]) if u["role"] in _ROLES else 0,
                            key=f"role_{u['user_id']}",
                            label_visibility="collapsed",
                        )
                        if new_role != u["role"]:
                            if st.button(
                                "Appliquer",
                                key=f"apply_role_{u['user_id']}",
                                type="secondary",
                            ):
                                try:
                                    set_user_role(u["username"], new_role)
                                    st.success(f"Rôle mis à jour → {new_role}")
                                    st.rerun()
                                except Exception as exc:
                                    st.error(str(exc))
                    else:
                        st.caption("_(votre compte)_")

                with col_toggle:
                    if not is_self:
                        label   = "Désactiver" if is_active else "Activer"
                        btn_type = "secondary" if is_active else "primary"
                        if st.button(
                            label,
                            key=f"toggle_{u['user_id']}",
                            type=btn_type,
                        ):
                            set_user_active(u["username"], not is_active)
                            st.rerun()
                    else:
                        st.caption("")

    st.divider()

    # ── Zone 4 : Documents ───────────────────────────────────────────────────
    st.markdown("#### Documents")

    doc_stats = get_document_admin_stats()
    if not doc_stats:
        st.info("Aucun document en base.")
    else:
        for d in doc_stats:
            avg = d["avg_score"]
            avg_str = f"{avg:.0%}" if avg is not None else "—"

            if avg is not None and avg < 0.45 and d["n_attempts"] >= 3:
                border_color = "#dc2626"
                icon = "⚠️"
            elif d["n_attempts"] == 0:
                border_color = "#94a3b8"
                icon = "📄"
            else:
                border_color = "#16a34a"
                icon = "✅"

            with st.container(border=True):
                c_title, c_stats = st.columns([5, 3])
                with c_title:
                    st.markdown(f"**{icon} {d['title']}**")
                    st.caption(f"Créé : {str(d['created_at'])[:10]}")
                with c_stats:
                    st.caption(
                        f"**{d['n_chunks']}** chunks · "
                        f"**{d['n_attempts']}** tentatives · "
                        f"Score moyen : **{avg_str}**"
                    )
