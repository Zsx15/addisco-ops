"""Moteur adaptatif — constantes et logique pédagogique pure.

Sans import projet : zéro risque de circular dependency.
database.py et ai_service.py importent depuis ici.
"""
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

# ── Répétition espacée ────────────────────────────────────────────────────────
# Intervalles de base par classe de maîtrise (en jours).
# Utilisés par _adaptive_interval() comme point de départ avant modulation par trend.
# Les valeurs brutes (1j/3j) sont dupliquées dans get_revision_suggestion() ORDER BY.
REVIEW_INTERVALS: dict[str, int] = {
    "Fragile":          1,
    "En consolidation": 3,
    "Maîtrisé":         7,
}

# ── Profil pédagogique utilisateur ────────────────────────────────────────────
# Mappage question_type → dimension du profil.
_PEDAGOGY_GROUPS: dict[str, list[str]] = {
    "logical":    ["question_directe"],
    "procedural": ["cas_pratique", "consequence"],
    "narrative":  ["reformulation"],
    "analogy":    ["vrai_faux", "question_piege"],
}

# ── Types de questions pédagogiques disponibles ───────────────────────────────
QUESTION_TYPES: list[str] = [
    "question_directe",
    "cas_pratique",
    "vrai_faux",
    "question_piege",
    "reformulation",
    "consequence",
]

# ── Intervalle adaptatif de révision ─────────────────────────────────────────

def _adaptive_interval(mastery_class: str, trend: str) -> int:
    """
    Retourne l'intervalle de révision (en jours) adapté à la tendance récente.

    Modulation par rapport à REVIEW_INTERVALS :
    - Fragile + Amélioration    → 2j  (progrès visible, délai légèrement allongé)
    - Fragile + autre           → 1j  (inchangé — situation critique)
    - En consolidation + Amélioration → 5j  (bonne trajectoire, espacer davantage)
    - En consolidation + Dégradation  → 2j  (surveillance renforcée)
    - En consolidation + autre        → 3j  (inchangé)
    - Maîtrisé                  → 7j  (inchangé — déjà maîtrisé)
    """
    base = REVIEW_INTERVALS.get(mastery_class, 3)
    if mastery_class == "Fragile":
        return 2 if trend == "Amélioration" else base
    if mastery_class == "En consolidation":
        if trend == "Amélioration":
            return 5
        if trend == "Dégradation":
            return 2
    return base


def classify_mastery(df: pd.DataFrame) -> pd.DataFrame:
    """
    Enrichit un DataFrame issu de get_chunk_stats() avec deux colonnes :
    - mastery_class : 'Fragile' | 'En consolidation' | 'Maîtrisé'
    - trend         : 'Amélioration' | 'Stable' | 'Dégradation' | 'N/A'

    Règles de classification :
    - Maîtrisé       : avg_score >= 0.8 ET attempts_count >= 3
    - Fragile        : avg_score < 0.6  (quel que soit le nombre de tentatives)
    - En consolidation : tout le reste

    Règles de tendance (uniquement si attempts_count >= 2) :
    - Amélioration : last_score > avg_score + 0.1
    - Dégradation  : last_score < avg_score - 0.1
    - Stable       : écart <= 0.1
    - N/A          : une seule tentative ou last_score absent
    """
    def _class(row):
        if row["avg_score"] < 0.6:
            return "Fragile"
        if row["avg_score"] >= 0.8 and row["attempts_count"] >= 3:
            return "Maîtrisé"
        return "En consolidation"

    def _trend(row):
        if row["attempts_count"] < 2 or pd.isna(row["last_score"]):
            return "N/A"
        delta = float(row["last_score"]) - float(row["avg_score"])
        if delta > 0.1:
            return "Amélioration"
        if delta < -0.1:
            return "Dégradation"
        return "Stable"

    def _next_review(row):
        try:
            last_dt = datetime.fromisoformat(str(row["last_attempt_date"]))
            days    = _adaptive_interval(row["mastery_class"], row["trend"])
            return last_dt + timedelta(days=days)
        except Exception:
            return None

    def _days_until(row):
        if row["next_review"] is None:
            return None
        return (row["next_review"].date() - datetime.now().date()).days

    def _review_status(row):
        d = row["days_until_review"]
        if d is None:
            return "—"
        if d < 0:
            return "En retard"
        if d == 0:
            return "Aujourd'hui"
        return f"Dans {d} jour{'s' if d > 1 else ''}"

    df = df.copy()
    df["mastery_class"]     = df.apply(_class, axis=1)
    df["trend"]             = df.apply(_trend, axis=1)
    df["next_review"]       = df.apply(_next_review, axis=1)
    df["days_until_review"] = df.apply(_days_until, axis=1)
    df["review_status"]     = df.apply(_review_status, axis=1)
    return df


# ── Biais mastery sur la sélection des types de questions ─────────────────────
# Fragile  → compréhension et reformulation avant tout.
# Maîtrisé → challenge et application en situation complexe.
_MASTERY_BIAS: dict[str, list[str]] = {
    "Fragile":  ["reformulation", "consequence", "cas_pratique"],
    "Maîtrisé": ["question_piege", "cas_pratique", "consequence"],
}
