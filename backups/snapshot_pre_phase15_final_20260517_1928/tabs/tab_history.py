"""Onglet Historique — liste des tentatives avec détail et export CSV."""
import streamlit as st

from database import get_attempts
from ui_helpers import _ERROR_LABELS


def render() -> None:
    st.subheader("Historique des tentatives")

    df = get_attempts(user_id=st.session_state["user_id"])

    if df.empty:
        st.info("Aucune tentative enregistrée pour l'instant.")
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("Tentatives", len(df))
    scores = df["score"].dropna()
    mean_score_str = f"{round(scores.mean() * 100)} %" if len(scores) > 0 else "—"
    col2.metric("Score moyen", mean_score_str)
    col3.metric(
        "Dernière tentative",
        str(df["created_at"].iloc[0])[:16] if not df.empty else "—",
    )

    _EXPORT_COLS = [
        "created_at", "question", "user_answer", "expected_answer",
        "score", "error_type", "topic", "pedagogy_type", "response_time_seconds",
    ]
    _export_cols = [c for c in _EXPORT_COLS if c in df.columns]
    _csv_bytes = df[_export_cols].to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="⬇ Exporter l'historique (.csv)",
        data=_csv_bytes,
        file_name="addisco_historique.csv",
        mime="text/csv",
    )

    st.divider()

    for _, row in df.iterrows():
        try:
            score_val = float(row["score"])
            if score_val != score_val:  # NaN
                score_val = 0.0
        except (TypeError, ValueError):
            score_val = 0.0

        score_pct   = round(score_val * 100)
        icon        = "✅" if score_val >= 0.8 else ("⚠️" if score_val >= 0.5 else "❌")
        notion      = row["topic"] or "—"
        date_str    = str(row["created_at"])[:16] if row["created_at"] else "—"
        error_label = _ERROR_LABELS.get(row["error_type"] or "", row["error_type"] or "—")

        with st.expander(f"{icon} {score_pct} % · {notion} · {date_str}"):
            c1, c2, c3 = st.columns(3)
            c1.metric("Score", f"{score_pct} %")
            c2.metric("Notion", notion)
            c3.metric("Type d'erreur", error_label)

            st.markdown("**Question**")
            st.write(row["question"] or "—")

            st.markdown("**Votre réponse**")
            st.write(row["user_answer"] or "—")

            if row["expected_answer"]:
                st.markdown("**Réponse attendue**")
                st.write(row["expected_answer"])

            st.markdown("**Correction**")
            correction = row["correction"] or "—"
            if score_val >= 0.8:
                st.success(correction)
            elif score_val >= 0.5:
                st.warning(correction)
            else:
                st.error(correction)
