"""Onglet Corpus — gestion des corpus personnalisés multi-documents (TASK-080)."""
from datetime import datetime

import streamlit as st

from database import get_documents
from db.corpus import (
    create_corpus,
    delete_corpus,
    get_corpus_documents,
    get_corpus_by_id,
    get_user_corpus,
)
from tabs.styles import DARK_DASHBOARD_CSS

_MONTHS_FR = [
    "jan", "fév", "mar", "avr", "mai", "juin",
    "juil", "août", "sep", "oct", "nov", "déc",
]


def _fmt_date(dt_str: str) -> str:
    try:
        dt = datetime.fromisoformat(str(dt_str))
        return f"{dt.day} {_MONTHS_FR[dt.month - 1]} {dt.year}"
    except Exception:
        return "—"


def _corpus_card(corpus: dict, is_active: bool, uid: str) -> None:
    accent = "#7C3AED" if is_active else "rgba(120,140,255,0.18)"
    border = f"2px solid {accent}" if is_active else f"1px solid {accent}"
    label  = corpus["corpus_name"]
    n_docs   = int(corpus.get("n_docs") or 0)
    n_chunks = int(corpus.get("n_chunks") or 0)
    created  = _fmt_date(corpus.get("created_at", ""))
    badge_bg  = "rgba(124,58,237,0.18)" if is_active else "rgba(37,99,235,0.1)"
    badge_col = "#A78BFA" if is_active else "#60A5FA"
    active_tag = (
        '<span style="background:rgba(124,58,237,0.22);border:1px solid #7C3AED;'
        'border-radius:10px;padding:2px 9px;font-size:10px;font-weight:700;'
        'color:#A78BFA;letter-spacing:.06em;text-transform:uppercase">ACTIF</span>'
        if is_active else ""
    )
    chunk_badge = (
        f'<span style="background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.25);'
        f'border-radius:8px;padding:2px 10px;font-size:11px;font-weight:600;color:#34D399">'
        f'{n_chunks} chunk{"s" if n_chunks != 1 else ""}</span>'
        if n_chunks else ""
    )

    st.markdown(
        f'<div style="background:#0B1530;border:{border};border-radius:14px;'
        f'padding:16px 18px;margin-bottom:10px">'
        f'<div style="display:flex;align-items:center;justify-content:space-between;'
        f'flex-wrap:wrap;gap:8px">'
        f'<div style="font-size:15px;font-weight:700;color:#F8FAFC">{label} {active_tag}</div>'
        f'<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">'
        f'<span style="background:{badge_bg};border:1px solid rgba(37,99,235,0.3);'
        f'border-radius:8px;padding:2px 10px;font-size:11px;font-weight:600;color:{badge_col}">'
        f'{n_docs} doc{"s" if n_docs != 1 else ""}</span>'
        f'{chunk_badge}'
        f'<span style="font-size:11px;color:#64748B">{created}</span>'
        f'</div></div></div>',
        unsafe_allow_html=True,
    )

    _c1, _c2, _c3 = st.columns([3, 1, 1])
    with _c2:
        if not is_active:
            if st.button("Activer", key=f"activate_{corpus['id']}", use_container_width=True):
                st.session_state["active_corpus_id"]   = corpus["id"]
                st.session_state["active_corpus_name"] = corpus["corpus_name"]
                # Réinitialiser le doc actif pour forcer le mode corpus dans l'entraînement
                st.session_state["active_document_id"]    = None
                st.session_state["active_document_title"] = None
                st.session_state["question"]              = None
                st.session_state["result"]                = None
                st.rerun()
        else:
            if st.button("Désactiver", key=f"deactivate_{corpus['id']}", use_container_width=True):
                st.session_state["active_corpus_id"]   = None
                st.session_state["active_corpus_name"] = None
                st.session_state["active_document_id"]    = None
                st.session_state["active_document_title"] = None
                st.rerun()
    with _c3:
        if st.button("Supprimer", key=f"delete_{corpus['id']}", use_container_width=True):
            if is_active:
                st.session_state["active_corpus_id"]   = None
                st.session_state["active_corpus_name"] = None
            delete_corpus(corpus["id"], uid)
            st.rerun()


def render() -> None:
    st.markdown(DARK_DASHBOARD_CSS, unsafe_allow_html=True)

    _uid  = st.session_state.get("user_id") or "default"
    _docs = get_documents()
    _corpora = get_user_corpus(_uid)
    _active_id   = st.session_state.get("active_corpus_id")
    _active_name = st.session_state.get("active_corpus_name", "")

    # ── Header ──────────────────────────────────────────────────────────────────
    st.markdown(
        '<div style="padding:18px 0 22px;border-bottom:1px solid rgba(120,140,255,0.13);'
        'margin-bottom:24px">'
        '<div style="display:flex;align-items:center;justify-content:space-between;'
        'flex-wrap:wrap;gap:10px">'
        '<div>'
        '<div style="font-size:26px;font-weight:800;color:#F8FAFC;letter-spacing:-0.02em">'
        'Corpus personnalisés</div>'
        '<div style="font-size:13px;color:#64748B;margin-top:5px">'
        'Créez des environnements d\'apprentissage ciblés à partir de vos documents.'
        '</div></div>'
        '<span style="background:rgba(124,58,237,0.13);border:1px solid rgba(124,58,237,0.35);'
        'border-radius:20px;padding:4px 14px;font-size:11px;font-weight:700;color:#A78BFA;'
        'text-transform:uppercase;letter-spacing:.08em">Multi-Doc</span>'
        '</div></div>',
        unsafe_allow_html=True,
    )

    # ── Section 1 — Corpus actif ─────────────────────────────────────────────
    st.markdown(
        '<div style="font-size:13px;font-weight:700;color:#94A3B8;text-transform:uppercase;'
        'letter-spacing:.08em;margin-bottom:10px">Corpus actif</div>',
        unsafe_allow_html=True,
    )

    if not _corpora:
        st.markdown(
            '<div style="background:#0B1530;border:1px dashed rgba(120,140,255,0.25);'
            'border-radius:14px;padding:40px 32px;text-align:center;margin-bottom:24px">'
            '<div style="font-size:32px;margin-bottom:12px">📚</div>'
            '<div style="font-size:16px;font-weight:700;color:#F8FAFC;margin-bottom:6px">'
            'Aucun corpus créé</div>'
            '<div style="font-size:13px;color:#64748B">'
            'Créez votre premier corpus pédagogique ci-dessous.'
            '</div></div>',
            unsafe_allow_html=True,
        )
    else:
        _options = [("— Aucun corpus (toutes les sources)", None)] + [
            (f"📚 {c['corpus_name']} ({c['n_docs']} doc{'s' if c['n_docs'] != 1 else ''})", c["id"])
            for c in _corpora
        ]
        _labels  = [o[0] for o in _options]
        _ids     = [o[1] for o in _options]
        _cur_idx = _ids.index(_active_id) if _active_id in _ids else 0

        _sel_label = st.selectbox(
            "Corpus de travail",
            options=_labels,
            index=_cur_idx,
            key="corpus_selector",
            label_visibility="collapsed",
        )
        _sel_id = _ids[_labels.index(_sel_label)]

        if _sel_id != _active_id:
            if _sel_id is None:
                st.session_state["active_corpus_id"]   = None
                st.session_state["active_corpus_name"] = None
            else:
                _meta = get_corpus_by_id(_sel_id, _uid)
                if _meta:
                    st.session_state["active_corpus_id"]   = _sel_id
                    st.session_state["active_corpus_name"] = _meta["corpus_name"]
            st.session_state["active_document_id"]    = None
            st.session_state["active_document_title"] = None
            st.session_state["question"] = None
            st.session_state["result"]   = None
            st.rerun()

        if _active_id:
            _meta = get_corpus_by_id(_active_id, _uid)
            if _meta:
                _doc_ids = get_corpus_documents(_active_id)
                st.markdown(
                    f'<div style="background:rgba(124,58,237,0.08);border:1px solid rgba(124,58,237,0.28);'
                    f'border-radius:10px;padding:12px 16px;margin-top:8px;margin-bottom:20px;'
                    f'display:flex;align-items:center;gap:12px">'
                    f'<span style="font-size:20px">🎯</span>'
                    f'<div>'
                    f'<div style="font-size:14px;font-weight:700;color:#A78BFA">{_meta["corpus_name"]}</div>'
                    f'<div style="font-size:12px;color:#64748B;margin-top:2px">'
                    f'{len(_doc_ids)} document{"s" if len(_doc_ids) != 1 else ""} · '
                    f'créé le {_fmt_date(_meta["created_at"])}'
                    f'</div></div></div>',
                    unsafe_allow_html=True,
                )

    st.markdown("<div style='margin:8px 0 20px'></div>", unsafe_allow_html=True)

    # ── Section 2 — Créer un corpus ──────────────────────────────────────────
    st.markdown(
        '<div style="font-size:13px;font-weight:700;color:#94A3B8;text-transform:uppercase;'
        'letter-spacing:.08em;margin-bottom:12px">Créer un corpus</div>',
        unsafe_allow_html=True,
    )

    if _docs.empty:
        st.markdown(
            '<div style="background:#0B1530;border:1px solid rgba(120,140,255,0.12);'
            'border-radius:10px;padding:16px 18px;color:#94A3B8;font-size:13px;'
            'margin-bottom:24px">'
            '⚠️ Aucun document disponible. Importez des documents dans l\'onglet Documents avant de créer un corpus.'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        _doc_options = {f"{r['title']}": int(r["id"]) for _, r in _docs.iterrows()}

        with st.form("form_create_corpus", clear_on_submit=True):
            _name = st.text_input(
                "Nom du corpus",
                placeholder="ex : Sécurité ferroviaire, VO583, Procédures ASCT…",
                max_chars=80,
            )
            _selected_titles = st.multiselect(
                "Documents à inclure",
                options=list(_doc_options.keys()),
                placeholder="Sélectionnez un ou plusieurs documents…",
            )
            _submit = st.form_submit_button("Créer le corpus", type="primary", use_container_width=True)

        if _submit:
            if not _name.strip():
                st.error("Le nom du corpus est requis.")
            elif not _selected_titles:
                st.error("Sélectionnez au moins un document.")
            else:
                _doc_ids = [_doc_options[t] for t in _selected_titles]
                try:
                    _new_id = create_corpus(_uid, _name.strip(), _doc_ids)
                    st.session_state["active_corpus_id"]   = _new_id
                    st.session_state["active_corpus_name"] = _name.strip()
                    st.session_state["active_document_id"]    = None
                    st.session_state["active_document_title"] = None
                    st.success(f'Corpus « {_name.strip()} » créé et activé ({len(_doc_ids)} document{"s" if len(_doc_ids) != 1 else ""}).')
                    st.rerun()
                except ValueError as _e:
                    st.error(str(_e))

    st.markdown("<div style='margin:8px 0 20px'></div>", unsafe_allow_html=True)

    # ── Section 3 — Corpus existants ─────────────────────────────────────────
    if _corpora:
        st.markdown(
            '<div style="font-size:13px;font-weight:700;color:#94A3B8;text-transform:uppercase;'
            'letter-spacing:.08em;margin-bottom:12px">Mes corpus</div>',
            unsafe_allow_html=True,
        )
        for _c in _corpora:
            _corpus_card(_c, is_active=(_c["id"] == _active_id), uid=_uid)
