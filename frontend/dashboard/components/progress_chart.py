"""Composant ProgressChart — graphiques de progression et distribution des erreurs."""
import pandas as pd
import streamlit as st

_ERROR_FR: dict[str, str] = {
    "oubli_etape":      "Oubli d'étape",
    "confusion_notion": "Confusion de notion",
    "reponse_vague":    "Réponse vague",
    "erreur_ordre":     "Erreur d'ordre",
    "hors_sujet":       "Hors sujet",
}

_ERROR_COLORS = ["#6366f1", "#b45309", "#dc2626", "#0369a1", "#7c3aed"]


def render_score_chart(df_evo: pd.DataFrame) -> None:
    if df_evo.empty or "score" not in df_evo.columns:
        st.markdown(
            '<p style="font-size:11.5px;color:#94a3b8;padding:8px 0 4px">Données insuffisantes.</p>',
            unsafe_allow_html=True,
        )
        return
    df_plot = df_evo[["score"]].rename(columns={"score": "Score"})
    st.line_chart(df_plot, height=145, use_container_width=True)


def render_error_heatmap(df_errors: pd.DataFrame) -> None:
    """Distribution des erreurs — barres colorées avec intensité proportionnelle."""
    if df_errors.empty or "error_type" not in df_errors.columns:
        st.markdown(
            '<p style="font-size:11.5px;color:#94a3b8;padding:8px 0 4px">Aucune erreur enregistrée.</p>',
            unsafe_allow_html=True,
        )
        return

    total = int(df_errors["count"].sum()) if "count" in df_errors.columns else len(df_errors)
    if total == 0:
        st.markdown(
            '<p style="font-size:11.5px;color:#94a3b8;padding:8px 0 4px">Aucune erreur enregistrée.</p>',
            unsafe_allow_html=True,
        )
        return

    rows_html = ""
    for i, (_, row) in enumerate(df_errors.iterrows()):
        err_type = str(row.get("error_type", ""))
        label = _ERROR_FR.get(err_type, err_type)
        count = int(row.get("count", 1))
        pct = round(count / total * 100)
        color = _ERROR_COLORS[i % len(_ERROR_COLORS)]
        rows_html += (
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:5px">'
            f'<div style="font-size:11px;color:#475569;min-width:128px;flex-shrink:0;'
            f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{label}</div>'
            f'<div style="flex:1;background:#f1f5f9;border-radius:3px;height:12px;overflow:hidden">'
            f'<div style="width:{pct}%;background:{color};height:100%;border-radius:3px;'
            f'opacity:.85"></div>'
            f'</div>'
            f'<div style="font-size:11px;color:{color};font-weight:700;min-width:22px;'
            f'text-align:right">{count}</div>'
            f'</div>'
        )

    st.markdown(
        f'<div style="padding:10px 12px;background:#f8fafc;border:1px solid #e2e8f0;'
        f'border-radius:8px">{rows_html}</div>',
        unsafe_allow_html=True,
    )
