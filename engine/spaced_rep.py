"""Répétition espacée — intervalles adaptatifs et classification de maîtrise."""
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

from engine.thresholds import (
    MASTERY_FRAGILE,
    MASTERY_MASTERED,
    MASTERY_MIN_ATTEMPTS,
    REVIEW_INTERVALS,
)


def _adaptive_interval(mastery_class: str, trend: str) -> int:
    """
    Intervalle de révision (jours) modulé par la tendance récente.

    - Fragile + Amélioration           → 2j
    - Fragile + autre                  → 1j
    - En consolidation + Amélioration  → 5j
    - En consolidation + Dégradation   → 2j
    - En consolidation + autre         → 3j
    - Maîtrisé                         → 7j
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
    Enrichit un DataFrame issu de get_chunk_stats() avec :
    - mastery_class : 'Fragile' | 'En consolidation' | 'Maîtrisé'
    - trend         : 'Amélioration' | 'Stable' | 'Dégradation' | 'N/A'
    - next_review, days_until_review, review_status

    Règles :
    - Maîtrisé       : avg_score >= 0.8 ET attempts_count >= MASTERY_MIN_ATTEMPTS (5)
    - Fragile        : avg_score < 0.6
    - En consolidation : reste
    """
    def _class(row):
        if row["avg_score"] < MASTERY_FRAGILE:
            return "Fragile"
        if row["avg_score"] >= MASTERY_MASTERED and row["attempts_count"] >= MASTERY_MIN_ATTEMPTS:
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
        # pd.isna() requis : pandas 2.x peut convertir None → NaT (datetime64[us])
        nxt = row["next_review"]
        try:
            if nxt is None or pd.isna(nxt):
                return None
            return int((nxt.date() - datetime.now().date()).days)
        except Exception:
            return None

    def _review_status(row):
        d = row["days_until_review"]
        if d is None or pd.isna(d):
            return "—"
        if d < 0:
            return "En retard"
        if d == 0:
            return "Aujourd'hui"
        return f"Dans {d} jour{'s' if d > 1 else ''}"

    df = df.copy()
    if df.empty:
        return df
    df["mastery_class"]     = df.apply(_class, axis=1)
    df["trend"]             = df.apply(_trend, axis=1)
    df["next_review"]       = df.apply(_next_review, axis=1)
    df["days_until_review"] = df.apply(_days_until, axis=1)
    df["review_status"]     = df.apply(_review_status, axis=1)
    return df
