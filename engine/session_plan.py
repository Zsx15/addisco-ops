"""Plan de session adaptatif — priorités, objectifs pédagogiques, durées."""
from typing import Optional

import pandas as pd

from engine.question_type import _MASTERY_BIAS, QUESTION_TYPES

_OBJECTIVES: dict[tuple[str, str], str] = {
    ("Fragile",          "Dégradation"):  "Reprendre les fondamentaux — régression active détectée",
    ("Fragile",          "Amélioration"): "Ancrer les progrès récents — maintenir la dynamique fragile",
    ("Fragile",          "Stable"):       "Travail de fond — sortir de la zone fragile",
    ("Fragile",          "N/A"):          "Premier apprentissage structuré — 3 tentatives visées",
    ("En consolidation", "Dégradation"):  "Renforcement ciblé — risque de régression identifié",
    ("En consolidation", "Amélioration"): "Ancrage — progression à confirmer sur 2 séances",
    ("En consolidation", "Stable"):       "Révision de maintien — progression vers la maîtrise",
    ("En consolidation", "N/A"):          "Consolidation régulière — stabiliser les acquis",
    ("Maîtrisé",         "Dégradation"):  "Rappel urgent — érosion de maîtrise détectée",
    ("Maîtrisé",         "Amélioration"): "Rappel court — maîtrise solide, maintien long terme",
    ("Maîtrisé",         "Stable"):       "Rappel espacé — ancrage en mémoire long terme",
    ("Maîtrisé",         "N/A"):          "Vérification de maîtrise — rappel standard",
}

_DURATION_BY_MASTERY: dict[str, int] = {
    "Fragile":          8,
    "En consolidation": 6,
    "Maîtrisé":         3,
}


def _compute_priority_score(row: "pd.Series") -> float:
    """
    Score de priorité pour un chunk (usage interne à build_session_plan).

    Composantes (ordre décroissant) :
    1. Urgence révision  : +3.0 si retard (+ 0.1/j supplémentaire, cap 10j),
                           +2.5 si aujourd'hui, +1.5 si dans ≤ 2j
    2. Fragilité         : +2.0 Fragile, +1.0 En consolidation
    3. Tendance          : +1.0 Dégradation, −0.3 Amélioration
    4. Faible historique : +0.5 si attempts_count < 3
    """
    review_status  = str(row.get("review_status", "—"))
    mastery_class  = str(row.get("mastery_class", ""))
    trend          = str(row.get("trend", "N/A"))
    try:
        attempts_count = int(row.get("attempts_count", 0))
    except (TypeError, ValueError):
        attempts_count = 0

    days_raw = row.get("days_until_review")
    try:
        days_int: Optional[int] = None if (days_raw is None or pd.isna(days_raw)) else int(days_raw)
    except (TypeError, ValueError):
        days_int = None

    score: float = 0.0

    if review_status == "En retard":
        overdue = abs(days_int) if days_int is not None else 1
        score  += 3.0 + min(overdue, 10) * 0.1
    elif review_status == "Aujourd'hui":
        score  += 2.5
    elif days_int is not None and 0 < days_int <= 2:
        score  += 1.5

    if mastery_class == "Fragile":
        score += 2.0
    elif mastery_class == "En consolidation":
        score += 1.0

    if trend == "Dégradation":
        score += 1.0
    elif trend == "Amélioration":
        score -= 0.3

    if attempts_count < 3:
        score += 0.5

    return round(score, 3)


def build_session_plan(
    chunks_df: Optional["pd.DataFrame"],
    max_items: int = 5,
) -> list[dict]:
    """
    Construit le plan de session personnalisé depuis un DataFrame enrichi par classify_mastery().

    Colonnes requises dans chunks_df :
    chunk_id, mastery_class, trend, review_status, days_until_review,
    avg_score, attempts_count.

    Champs retournés par item :
    - chunk_id, section_label, document_title
    - mastery_class, trend, review_status, days_until_review, avg_score, attempts_count
    - priority_score    : score de tri interne (décroissant)
    - estimated_minutes : durée estimée en minutes (3–8)
    - objective         : texte de l'objectif pédagogique
    - question_bias     : types de questions recommandés pour cette section (biais mastery)
    """
    _required = {
        "chunk_id", "mastery_class", "trend", "review_status",
        "days_until_review", "avg_score", "attempts_count",
    }
    if chunks_df is None or chunks_df.empty:
        return []
    if not _required.issubset(chunks_df.columns):
        return []

    items: list[dict] = []
    for _, row in chunks_df.iterrows():
        mastery_class = str(row.get("mastery_class", ""))
        trend         = str(row.get("trend", "N/A"))
        review_status = str(row.get("review_status", "—"))

        objective = _OBJECTIVES.get((mastery_class, trend), "Révision adaptative")
        if review_status == "En retard":
            objective += " (révision en retard)"

        days_raw = row.get("days_until_review")
        try:
            days_out: Optional[int] = None if (days_raw is None or pd.isna(days_raw)) else int(days_raw)
        except (TypeError, ValueError):
            days_out = None

        items.append({
            "chunk_id":          int(row["chunk_id"]),
            "section_label":     str(row.get("section_label", "")),
            "document_title":    str(row.get("document_title", "")),
            "mastery_class":     mastery_class,
            "trend":             trend,
            "review_status":     review_status,
            "days_until_review": days_out,
            "avg_score":         float(row["avg_score"]),
            "attempts_count":    int(row["attempts_count"]),
            "priority_score":    _compute_priority_score(row),
            "estimated_minutes": _DURATION_BY_MASTERY.get(mastery_class, 5),
            "objective":         objective,
            "question_bias":     list(_MASTERY_BIAS.get(mastery_class, QUESTION_TYPES[:3])),
        })

    items.sort(key=lambda x: x["priority_score"], reverse=True)
    return items[:max_items]
