"""Calcul de maîtrise par skill — logique pure, sans accès base de données."""
from engine.thresholds import MASTERY_FRAGILE, MASTERY_MASTERED, MASTERY_MIN_ATTEMPTS


def compute_skill_mastery(scores: list[float]) -> float:
    """Moyenne des scores [0.0, 1.0]. Retourne 0.0 si liste vide."""
    if not scores:
        return 0.0
    return round(sum(scores) / len(scores), 3)


def classify_skill_mastery(mastery_score: float, attempts_count: int = 0) -> str:
    """
    Classe un skill en trois états.

    - Acquis  : score >= 0.8 ET au moins 3 tentatives
    - Fragile : score < 0.6
    - En cours : reste
    """
    if mastery_score < MASTERY_FRAGILE:
        return "Fragile"
    if mastery_score >= MASTERY_MASTERED and attempts_count >= MASTERY_MIN_ATTEMPTS:
        return "Acquis"
    return "En cours"
