"""Onglet Dashboard — version diagnostic checkpoints (TASK pré-render).

TEMPORAIRE — instrumenté pour identifier le bloc freeze pré-render.
Remplacer render() par la version complète une fois le blocage identifié.
"""
import sqlite3
import traceback
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

import database as _db_module
from database import (
    build_session_plan,
    classify_mastery,
    classify_skill_mastery,
    compute_and_save_learning_profile,
    get_attempts,
    get_attempts_count,
    get_chunk_stats,
    get_error_frequency,
    get_learning_profile,
    get_retention_metrics,
    get_score_evolution,
    get_topic_stats,
    get_user_skill_mastery,
)
from ui_helpers import (
    _ERROR_LABELS,
    _build_recommendations,
    _build_report,
    _kpi_card,
    _mastery_state,
    _truncate_label,
    explain_interval_decision,
    explain_priority_decision,
    explain_profile_detection,
)

_SCORE_GROUPS = [
    ("📐", "Analytique",  "logical_score",    "#0f172a"),
    ("⚙️",  "Procédural",  "procedural_score", "#0f172a"),
    ("📝", "Narratif",    "narrative_score",  "#0f172a"),
    ("🔀", "Analogique",  "analogy_score",    "#0f172a"),
]

_PEDAGOGY_FR = {
    "logical":    "Analytique",
    "procedural": "Procédural",
    "narrative":  "Narratif",
    "analogy":    "Analogique",
}

_BADGE = {
    "Fragile":          ("🔴", "FRAGILE"),
    "En consolidation": ("🟡", "EN CONSOLIDATION"),
    "Maîtrisé":         ("🟢", "MAÎTRISÉ"),
}


def render() -> None:
    # ── CP-0 : render() démarré ───────────────────────────────────────────
    st.write("🟢 **CP-0** — render() démarré")

    # ── CP-1 : session_state["user_id"] ──────────────────────────────────
    try:
        _uid = st.session_state["user_id"]
        st.write(f"🟢 **CP-1** — user_id OK : `{_uid}`")
    except KeyError as _e:
        st.error(f"**CP-1 FAIL** — session_state[user_id] absent : {_e}")
        return
    except Exception as _e:
        st.error(f"**CP-1 FAIL** — inattendu : {_e}")
        st.code(traceback.format_exc())
        return

    # ── CP-2 : connexion DB directe (timeout=5s) ──────────────────────────
    # Test brut avant d'appeler les fonctions engine — détecte DB lock.
    try:
        with sqlite3.connect(_db_module.DB_PATH, timeout=5) as _conn:
            _cnt_direct = _conn.execute(
                "SELECT COUNT(*) FROM attempts WHERE user_id = ?", (_uid,)
            ).fetchone()[0]
        st.write(f"🟢 **CP-2** — DB directe OK : {_cnt_direct} tentatives")
    except sqlite3.OperationalError as _e:
        st.error(f"**CP-2 FAIL** — DB LOCKED ou inaccessible : {_e}")
        st.caption(f"DB_PATH = `{_db_module.DB_PATH}`")
        return
    except Exception as _e:
        st.error(f"**CP-2 FAIL** — DB inattendu : {_e}")
        st.code(traceback.format_exc())
        return

    # ── CP-3 : get_attempts_count (fonction engine) ───────────────────────
    try:
        total_attempts = get_attempts_count(user_id=_uid)
        st.write(f"🟢 **CP-3** — get_attempts_count OK : {total_attempts}")
    except Exception as _e:
        st.error(f"**CP-3 FAIL** — get_attempts_count : {_e}")
        st.code(traceback.format_exc())
        return

    if total_attempts < 2:
        st.info("Effectuez au moins 2 tentatives pour afficher le dashboard.")
        return

    # ── CP-4 : selectbox fenêtre d'analyse ───────────────────────────────
    try:
        _WINDOW_OPTIONS = {
            "100 dernières": 100,
            "200 dernières": 200,
            "300 dernières": 300,
            "Tout l'historique": None,
        }
        _window_label = st.selectbox(
            "Fenêtre d'analyse",
            options=list(_WINDOW_OPTIONS.keys()),
            index=1,
            key="dashboard_window",
        )
        _window_limit = _WINDOW_OPTIONS[_window_label]
        st.write(f"🟢 **CP-4** — selectbox OK : limite = {_window_limit}")
    except Exception as _e:
        st.error(f"**CP-4 FAIL** — selectbox : {_e}")
        st.code(traceback.format_exc())
        return

    # ── CP-5 : expander diagnostic ────────────────────────────────────────
    try:
        with st.expander("Diagnostic d'isolation des blocs", expanded=True):
            st.write("🟢 **CP-5b** — INTÉRIEUR expander OK")
        st.write("🟢 **CP-5** — expander OK")
    except Exception as _e:
        st.error(f"**CP-5 FAIL** — expander : {_e}")
        st.code(traceback.format_exc())
        return

    # ── CP-6 : get_attempts ───────────────────────────────────────────────
    try:
        df_all = get_attempts(user_id=_uid, limit=_window_limit)
        st.write(f"🟢 **CP-6** — get_attempts OK : {len(df_all)} lignes, colonnes={list(df_all.columns)}")
    except Exception as _e:
        st.error(f"**CP-6 FAIL** — get_attempts : {_e}")
        st.code(traceback.format_exc())
        return

    # ── CP-7 : get_topic_stats ────────────────────────────────────────────
    try:
        df_topics = get_topic_stats(user_id=_uid)
        st.write(f"🟢 **CP-7** — get_topic_stats OK : {len(df_topics)} lignes")
    except Exception as _e:
        st.error(f"**CP-7 FAIL** — get_topic_stats : {_e}")
        st.code(traceback.format_exc())
        return

    # ── CP-8 : get_chunk_stats ────────────────────────────────────────────
    try:
        _raw_chunks = get_chunk_stats(user_id=_uid)
        st.write(f"🟢 **CP-8** — get_chunk_stats OK : {len(_raw_chunks)} lignes")
    except Exception as _e:
        st.error(f"**CP-8 FAIL** — get_chunk_stats : {_e}")
        st.code(traceback.format_exc())
        return

    # ── CP-9 : classify_mastery ───────────────────────────────────────────
    try:
        df_chunks = classify_mastery(_raw_chunks)
        st.write(f"🟢 **CP-9** — classify_mastery OK : {len(df_chunks)} lignes")
    except Exception as _e:
        st.error(f"**CP-9 FAIL** — classify_mastery : {_e}")
        st.code(traceback.format_exc())
        return

    # ── CP-10 : get_error_frequency ───────────────────────────────────────
    try:
        df_errors = get_error_frequency(user_id=_uid)
        st.write(f"🟢 **CP-10** — get_error_frequency OK : {len(df_errors)} lignes")
    except Exception as _e:
        st.error(f"**CP-10 FAIL** — get_error_frequency : {_e}")
        st.code(traceback.format_exc())
        return

    # ── CP-11 : get_score_evolution ───────────────────────────────────────
    try:
        df_evol = get_score_evolution(limit=20, user_id=_uid)
        st.write(f"🟢 **CP-11** — get_score_evolution OK : {len(df_evol)} lignes")
    except Exception as _e:
        st.error(f"**CP-11 FAIL** — get_score_evolution : {_e}")
        st.code(traceback.format_exc())
        return

    # ── CP-12 : get_retention_metrics ─────────────────────────────────────
    try:
        _ret = get_retention_metrics(_uid)
        st.write(f"🟢 **CP-12** — get_retention_metrics OK : {list(_ret.keys())}")
    except Exception as _e:
        st.error(f"**CP-12 FAIL** — get_retention_metrics : {_e}")
        st.code(traceback.format_exc())
        return

    # ── CP-13 : get_learning_profile ──────────────────────────────────────
    try:
        _profile = get_learning_profile(_uid)
        st.write(f"🟢 **CP-13** — get_learning_profile OK : {'profil trouvé' if _profile else 'None'}")
    except Exception as _e:
        st.error(f"**CP-13 FAIL** — get_learning_profile : {_e}")
        st.code(traceback.format_exc())
        return

    # ── CP-14 : get_user_skill_mastery ────────────────────────────────────
    try:
        _skill_mastery = get_user_skill_mastery(_uid)
        st.write(f"🟢 **CP-14** — get_user_skill_mastery OK : {len(_skill_mastery)} skills")
    except Exception as _e:
        st.error(f"**CP-14 FAIL** — get_user_skill_mastery : {_e}")
        st.code(traceback.format_exc())
        return

    # ── CP-15 : build_session_plan ────────────────────────────────────────
    try:
        _session_plan = build_session_plan(df_chunks, max_items=5) if not df_chunks.empty else []
        st.write(f"🟢 **CP-15** — build_session_plan OK : {len(_session_plan)} items")
    except Exception as _e:
        st.error(f"**CP-15 FAIL** — build_session_plan : {_e}")
        st.code(traceback.format_exc())
        return

    # ── CP-16 : KPIs calcul ───────────────────────────────────────────────
    try:
        scores_all = df_all["score"].dropna()
        n_sections = len(df_chunks)
        n_mastered = int((df_chunks["mastery_class"] == "Maîtrisé").sum()) if not df_chunks.empty else 0
        n_retard   = (
            int((df_chunks["review_status"] == "En retard").sum())
            if not df_chunks.empty and "review_status" in df_chunks.columns else 0
        )
        st.write(
            f"🟢 **CP-16** — KPIs OK : score_moy={round(scores_all.mean()*100) if len(scores_all) else '—'}% "
            f"· sections={n_sections} · maîtrisées={n_mastered} · retard={n_retard}"
        )
    except Exception as _e:
        st.error(f"**CP-16 FAIL** — calcul KPIs : {_e}")
        st.code(traceback.format_exc())
        return

    # ── CP-17 : _build_recommendations ───────────────────────────────────
    try:
        _recs = _build_recommendations(df_chunks, df_errors)
        st.write(f"🟢 **CP-17** — _build_recommendations OK : {len(_recs)} recs")
    except Exception as _e:
        st.error(f"**CP-17 FAIL** — _build_recommendations : {_e}")
        st.code(traceback.format_exc())
        return

    # ── CP-18 : plotly px.bar (topics) ────────────────────────────────────
    try:
        if not df_topics.empty:
            _df_plot = df_topics.copy()
            _df_plot["score_pct"] = (_df_plot["avg_score"] * 100).round().astype(int)
            _df_plot["label"]     = _df_plot["topic"].apply(_truncate_label)
            _fig_test = px.bar(
                _df_plot.sort_values("score_pct"),
                x="score_pct", y="label", orientation="h",
                height=max(200, len(_df_plot) * 44),
            )
            st.write(f"🟢 **CP-18** — px.bar topics OK : {len(_df_plot)} barres")
        else:
            st.write("🟢 **CP-18** — px.bar topics SKIPPED (df_topics vide)")
    except Exception as _e:
        st.error(f"**CP-18 FAIL** — px.bar topics : {_e}")
        st.code(traceback.format_exc())
        return

    # ── CP-19 : section cards HTML loop (20 cartes) ───────────────────────
    try:
        if not df_chunks.empty:
            _df_ord = pd.concat([
                df_chunks[df_chunks["mastery_class"] == "Fragile"].sort_values("avg_score"),
                df_chunks[df_chunks["mastery_class"] == "En consolidation"].sort_values("avg_score"),
                df_chunks[df_chunks["mastery_class"] == "Maîtrisé"],
            ]).head(20)
            _widget_count = 0
            for _, _r in _df_ord.iterrows():
                _icon, _badge = _BADGE.get(_r["mastery_class"], ("⚪", _r["mastery_class"].upper()))
                _ms_icon, _ms_label, _ms_color = _mastery_state(_r)
                _ivl = explain_interval_decision(
                    str(_r.get("mastery_class") or ""),
                    str(_r.get("trend") or "N/A"),
                )
                _widget_count += 1
            st.write(f"🟢 **CP-19** — section cards loop OK : {_widget_count} itérations")
        else:
            st.write("🟢 **CP-19** — section cards SKIPPED (df_chunks vide)")
    except Exception as _e:
        st.error(f"**CP-19 FAIL** — section cards loop : {_e}")
        st.code(traceback.format_exc())
        return

    # ── FINAL : toutes les fonctions OK ──────────────────────────────────
    st.divider()
    st.success(
        "**DIAGNOSTIC COMPLET — tous les checkpoints passés.**  \n"
        "Aucun blocage détecté. Le freeze était peut-être intermittent (DB lock transitoire) "
        "ou lié au volume de widgets Streamlit (reactiver le dashboard complet pour confirmer)."
    )
    st.caption(
        f"Résumé : {total_attempts} tentatives · {len(df_chunks)} chunks · "
        f"{len(df_topics)} topics · {len(_skill_mastery)} skills"
    )
