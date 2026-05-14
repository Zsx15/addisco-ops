"""
Fonctions utilitaires UI — rendu HTML, analyse pédagogique, rapport.
Aucune dépendance Streamlit : importable et testable indépendamment.
"""
from datetime import datetime

import pandas as pd

_ERROR_LABELS: dict[str, str] = {
    "oubli_etape":     "Oubli d'étape",
    "confusion_notion": "Confusion de notion",
    "reponse_vague":   "Réponse vague",
    "erreur_ordre":    "Erreur d'ordre",
    "hors_sujet":      "Hors sujet",
    "correct":         "Correct",
}


def _truncate_label(text: str, max_len: int = 25) -> str:
    return text if len(text) <= max_len else text[:max_len - 1] + "…"


def _kpi_card(icon: str, label: str, value: str, accent: str = "#0f172a") -> str:
    return (
        '<div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;'
        'padding:20px 14px;text-align:center;'
        'box-shadow:0 1px 3px rgba(15,23,42,.08),0 1px 2px rgba(15,23,42,.04);">'
        f'<div style="font-size:22px;line-height:1;margin-bottom:10px">{icon}</div>'
        f'<div style="font-size:30px;font-weight:800;color:{accent};line-height:1;'
        f'margin-bottom:8px;letter-spacing:-0.02em">{value}</div>'
        f'<div style="font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;'
        f'letter-spacing:.08em">{label}</div>'
        '</div>'
    )


def _mastery_state(row) -> tuple[str, str, str]:
    mc     = row.get("mastery_class", "")
    trend  = row.get("trend", "N/A")
    days   = row.get("days_until_review")
    overdue = isinstance(days, (int, float)) and days < 0

    if mc == "Maîtrisé":
        if overdue:
            return ("⚠️", "Oubli possible", "#9333ea")
        if trend == "Dégradation":
            return ("📉", "Maîtrise instable", "#d97706")
        return ("✅", "Maîtrisé", "#16a34a")

    if mc == "En consolidation":
        if trend == "Amélioration":
            return ("📈", "Forte progression", "#0891b2")
        if trend == "Dégradation":
            return ("📉", "Consolidation instable", "#d97706")
        if overdue:
            return ("⏰", "Révision en attente", "#7c3aed")
        return ("🔄", "Consolidation active", "#d97706")

    # Fragile
    if trend == "Amélioration":
        return ("📈", "En progression", "#0891b2")
    if trend == "Dégradation":
        return ("📉", "Régression active", "#dc2626")
    return ("⚡", "Fragilité confirmée", "#dc2626")


def _build_recommendations(
    df_chunks: pd.DataFrame, df_errors: pd.DataFrame
) -> list[tuple[str, str]]:
    recs: list[tuple[str, str]] = []
    if df_chunks.empty:
        return recs

    overdue = df_chunks[df_chunks["review_status"] == "En retard"]
    if len(overdue) == 1:
        recs.append(("urgent", f"Section \"{overdue.iloc[0]['section_label']}\" doit être revue aujourd'hui"))
    elif len(overdue) > 1:
        recs.append(("urgent", f"{len(overdue)} sections en retard de révision — priorité immédiate"))

    near = df_chunks[
        (df_chunks["avg_score"] >= 0.68) &
        (df_chunks["mastery_class"] == "En consolidation") &
        (df_chunks["trend"] == "Amélioration")
    ]
    for _, r in near.iterrows():
        recs.append(("success", f"\"{r['section_label']}\" proche de la maîtrise — {round(float(r['avg_score']) * 100)} %"))

    for _, r in df_chunks[df_chunks["trend"] == "Dégradation"].head(2).iterrows():
        recs.append(("warning", f"Régression détectée sur \"{r['section_label']}\" — révision recommandée"))

    if not df_errors.empty and int(df_errors.iloc[0]["count"]) >= 3:
        _te = df_errors.iloc[0]
        recs.append((
            "info",
            f"{int(_te['count'])} erreurs \"{_ERROR_LABELS.get(_te['error_type'], _te['error_type'])}\" — notion sensible identifiée",
        ))

    fragile_err = df_chunks[
        (df_chunks["mastery_class"] == "Fragile") &
        df_chunks["dominant_error_type"].notna() &
        (df_chunks["dominant_error_type"] != "")
    ]
    for _, r in fragile_err.head(1).iterrows():
        recs.append(("warning", f"\"{r['section_label']}\" : erreur répétée \"{_ERROR_LABELS.get(r['dominant_error_type'], r['dominant_error_type'])}\""))

    return recs[:5]


def _build_report(df_all: pd.DataFrame, df_topics: pd.DataFrame, df_chunks: pd.DataFrame) -> str:
    w     = 60
    lines: list[str] = []

    def _sep(c: str = "=") -> None:   lines.append(c * w)
    def _h(t: str) -> None:           lines.extend([t, "-" * len(t)])
    def _blank() -> None:             lines.append("")

    _sep()
    lines.append("RAPPORT DE PROGRESSION — IA REVISION METIER")
    lines.append(f"Genere le {datetime.now().strftime('%d/%m/%Y a %H:%M')}")
    _sep()
    _blank()

    _h("SYNTHESE GLOBALE")
    scores = df_all["score"].dropna()
    lines.append(f"  Tentatives totales  : {len(df_all)}")
    lines.append(
        f"  Score moyen global  : {round(scores.mean() * 100)} %"
        if len(scores) else "  Score moyen global  : —"
    )
    if not df_topics.empty:
        lines.append(f"  Meilleure notion    : {df_topics.iloc[-1]['topic']}")
        lines.append(f"  Notion a renforcer  : {df_topics.iloc[0]['topic']}")
    _blank()

    if not df_chunks.empty:
        _h("MAITRISE PAR SECTION")
        _TAG = {
            "Fragile":          "[FRAGILE]         ",
            "En consolidation": "[EN CONSOLIDATION]",
            "Maitrise":         "[MAITRISE]        ",
            "Maîtrisé":         "[MAITRISE]        ",
        }
        for _, r in df_chunks.iterrows():
            tag   = _TAG.get(r["mastery_class"], f"[{r['mastery_class']}]")
            pct   = round(float(r["avg_score"]) * 100)
            n     = int(r["attempts_count"])
            rv_st = r.get("review_status", "—")
            lines.append(f"  {tag}  {_truncate_label(r['section_label'], 30)}  —  {pct} %  ·  {n} tent.  ·  {rv_st}")
        _blank()

        _h("PROCHAINES REVISIONS PRIORITAIRES")
        for _, r in df_chunks[df_chunks["mastery_class"] == "Fragile"].sort_values("avg_score").iterrows():
            rv_st = r.get("review_status", "—")
            mk    = "  ! " if rv_st == "En retard" else "    "
            lines.append(f"{mk}{r['section_label']}  [{rv_st}]  (Fragile)")
        for _, r in df_chunks[df_chunks["mastery_class"] == "En consolidation"].sort_values("avg_score").iterrows():
            rv_st = r.get("review_status", "—")
            mk    = "  ! " if rv_st == "En retard" else "    "
            lines.append(f"{mk}{r['section_label']}  [{rv_st}]  (En consolidation)")
        for _, r in df_chunks[df_chunks["mastery_class"] == "Maîtrisé"].iterrows():
            rv_st = r.get("review_status", "—")
            lines.append(f"    {r['section_label']}  [{rv_st}]  (Maitrise)")
        _blank()

    _sep()
    lines.append("Rapport genere par IA Revision Metier")
    _sep()
    return "\n".join(lines)
