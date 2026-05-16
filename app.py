import os
import sqlite3

import streamlit as st

from logger import setup_logging

setup_logging()

from database import DB_PATH, get_documents, init_db
from document_service import seed_demo_document
from seed_demo_attempts import seed as _seed_demo_attempts
from auth_service import register_user, verify_password
from ui_helpers import check_app_password, sanitize_user_id
from tabs.styles import APP_CSS, APP_HEADER
from tabs.tab_training import render as render_training
from tabs.tab_history import render as render_history
from tabs.tab_dashboard import render as render_dashboard
from tabs.tab_documents import render as render_documents
from tabs.tab_engine import render as render_engine
from tabs.tab_trainer import render as render_trainer

init_db()
seed_demo_document()
try:
    _seed_demo_attempts()
except Exception:
    pass

st.set_page_config(page_title="ADDISCO OPS", page_icon="🧠", layout="wide")


# ── Gate APP_PASSWORD (clé "app_gated" — indépendante du login users) ─────────
_APP_PASSWORD = os.getenv("APP_PASSWORD", "")
if _APP_PASSWORD and not st.session_state.get("app_gated"):
    st.title("🧠 ADDISCO OPS")
    st.subheader("Accès protégé")
    _pwd_input = st.text_input("Mot de passe", type="password", key="login_password")
    if st.button("Connexion", type="primary"):
        if check_app_password(_pwd_input, _APP_PASSWORD):
            st.session_state["app_gated"] = True
            st.rerun()
        else:
            st.error("Mot de passe incorrect.")
    st.stop()


# ── Authentification utilisateur (TASK-043) ───────────────────────────────────
def _count_users() -> int:
    try:
        with sqlite3.connect(str(DB_PATH)) as conn:
            return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    except Exception:
        return 0


_demo_mode = _count_users() == 0
_is_authed = (
    st.session_state.get("authenticated")
    or st.session_state.get("demo_active")
)

if not _is_authed:
    st.title("🧠 ADDISCO OPS")

    if _demo_mode:
        # ── Bootstrap : aucun user en base ────────────────────────────────
        _tb_reg, _tb_demo = st.tabs(["Créer un compte", "Mode démo"])

        with _tb_reg:
            with st.form("form_register_boot"):
                _r_user    = st.text_input("Nom d'utilisateur")
                _r_pass    = st.text_input("Mot de passe", type="password")
                _r_confirm = st.text_input("Confirmer le mot de passe", type="password")
                _r_submit  = st.form_submit_button("Créer le compte", type="primary")
            if _r_submit:
                if not _r_user.strip():
                    st.error("Le nom d'utilisateur ne peut pas être vide.")
                elif len(_r_pass) < 6:
                    st.error("Le mot de passe doit contenir au moins 6 caractères.")
                elif _r_pass != _r_confirm:
                    st.error("Les mots de passe ne correspondent pas.")
                else:
                    try:
                        _new_id = register_user(_r_user.strip(), _r_pass)
                        st.session_state["authenticated"] = True
                        st.session_state["user_id"]       = _new_id
                        st.session_state["username"]      = _r_user.strip()
                        st.session_state["role"]          = "apprenant"
                        st.rerun()
                    except ValueError as _e:
                        st.error(str(_e))

        with _tb_demo:
            st.info(
                "Aucun utilisateur enregistré.  \n"
                "Créez un compte pour une session personnalisée, "
                "ou continuez en mode démo (session partagée, user_id = default)."
            )
            if st.button("Continuer en mode démo", type="primary"):
                st.session_state["demo_active"] = True
                st.session_state["user_id"]     = "default"
                st.rerun()

    else:
        # ── Users présents : login ou inscription ─────────────────────────
        _tb_login, _tb_reg = st.tabs(["Connexion", "Créer un compte"])

        with _tb_login:
            with st.form("form_login"):
                _l_user   = st.text_input("Nom d'utilisateur")
                _l_pass   = st.text_input("Mot de passe", type="password")
                _l_submit = st.form_submit_button("Se connecter", type="primary")
            if _l_submit:
                _result = verify_password(_l_user.strip(), _l_pass)
                if _result:
                    st.session_state["authenticated"] = True
                    st.session_state["user_id"]       = _result["user_id"]
                    st.session_state["username"]      = _result["username"]
                    st.session_state["role"]          = _result["role"]
                    st.rerun()
                else:
                    st.error("Identifiants incorrects.")

        with _tb_reg:
            with st.form("form_register"):
                _r_user    = st.text_input("Nom d'utilisateur")
                _r_pass    = st.text_input("Mot de passe", type="password")
                _r_confirm = st.text_input("Confirmer le mot de passe", type="password")
                _r_submit  = st.form_submit_button("Créer le compte", type="primary")
            if _r_submit:
                if not _r_user.strip():
                    st.error("Le nom d'utilisateur ne peut pas être vide.")
                elif len(_r_pass) < 6:
                    st.error("Le mot de passe doit contenir au moins 6 caractères.")
                elif _r_pass != _r_confirm:
                    st.error("Les mots de passe ne correspondent pas.")
                else:
                    try:
                        _new_id = register_user(_r_user.strip(), _r_pass)
                        st.session_state["authenticated"] = True
                        st.session_state["user_id"]       = _new_id
                        st.session_state["username"]      = _r_user.strip()
                        st.session_state["role"]          = "apprenant"
                        st.rerun()
                    except ValueError as _e:
                        st.error(str(_e))

    st.stop()


# ── App ───────────────────────────────────────────────────────────────────────
st.markdown(APP_CSS, unsafe_allow_html=True)
st.markdown(APP_HEADER, unsafe_allow_html=True)

for key in (
    "question", "source_text", "start_time", "result", "response_time",
    "active_document_id", "active_document_title", "chunk_ids", "question_type",
    "question_mastery", "question_chunk_trend", "question_chunk_days",
    "question_chunk_error", "question_chunk_status",
    "question_type_reason", "question_profile_pedagogy",
    "username", "role",
):
    if key not in st.session_state:
        st.session_state[key] = None
if "source_text_input" not in st.session_state:
    st.session_state["source_text_input"] = ""
if "user_id" not in st.session_state:
    st.session_state["user_id"] = "default"
st.session_state["user_id"] = sanitize_user_id(st.session_state["user_id"])

with st.sidebar:
    if st.session_state.get("authenticated") and st.session_state.get("username"):
        st.markdown(f"**👤 {st.session_state['username']}**")
        st.caption(f"Rôle : {st.session_state.get('role', 'apprenant')}")
        if st.button("Déconnexion"):
            st.session_state["authenticated"] = False
            st.session_state["demo_active"]   = False
            st.session_state["user_id"]       = "default"
            st.session_state["username"]      = None
            st.session_state["role"]          = None
            st.rerun()
    else:
        st.markdown("**Session utilisateur**")
        st.text_input("Identifiant", key="user_id", placeholder="ex : alice, bob…")

    st.divider()
    st.caption("**Statut système**")
    _db_ok = DB_PATH.exists()
    st.caption(f"{'✅' if _db_ok else '❌'} Base · {'opérationnelle' if _db_ok else 'introuvable'}")
    _api_ok = bool(os.getenv("OPENAI_API_KEY"))
    st.caption(f"{'✅' if _api_ok else '⚠️'} OpenAI · {'connecté' if _api_ok else 'mode fallback'}")
    _n_docs = len(get_documents())
    st.caption(f"📄 {_n_docs} document{'s' if _n_docs > 1 else ''} chargé{'s' if _n_docs > 1 else ''}")

tab_train, tab_history, tab_dashboard, tab_docs, tab_engine, tab_formateur = st.tabs(
    ["Entraînement", "Historique", "Dashboard", "Documents", "Moteur IA", "Formateur"]
)

with tab_train:
    render_training()

with tab_history:
    render_history()

with tab_dashboard:
    render_dashboard()

with tab_docs:
    render_documents()

with tab_engine:
    render_engine()

with tab_formateur:
    render_trainer()
