import os

import streamlit as st

from logger import setup_logging

setup_logging()

from database import DB_PATH, get_documents, init_db
from document_service import seed_demo_document
from seed_demo_attempts import seed as _seed_demo_attempts
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

# ── Authentification (TASK-036) ───────────────────────────────────────────────
_APP_PASSWORD = os.getenv("APP_PASSWORD", "")
if _APP_PASSWORD:
    if not st.session_state.get("authenticated"):
        st.title("🧠 ADDISCO OPS")
        st.subheader("Accès protégé")
        _pwd_input = st.text_input("Mot de passe", type="password", key="login_password")
        if st.button("Connexion", type="primary"):
            if check_app_password(_pwd_input, _APP_PASSWORD):
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Mot de passe incorrect.")
        st.stop()

st.markdown(APP_CSS, unsafe_allow_html=True)
st.markdown(APP_HEADER, unsafe_allow_html=True)

for key in (
    "question", "source_text", "start_time", "result", "response_time",
    "active_document_id", "active_document_title", "chunk_ids", "question_type",
    "question_mastery", "question_chunk_trend", "question_chunk_days",
    "question_chunk_error", "question_chunk_status",
    "question_type_reason", "question_profile_pedagogy",
):
    if key not in st.session_state:
        st.session_state[key] = None
if "source_text_input" not in st.session_state:
    st.session_state["source_text_input"] = ""
if "user_id" not in st.session_state:
    st.session_state["user_id"] = "default"
st.session_state["user_id"] = sanitize_user_id(st.session_state["user_id"])

with st.sidebar:
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
