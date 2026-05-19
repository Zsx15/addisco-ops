"""Mapping chunk_text → skills par correspondance de mots-clés — V1.0.

Déterministe, sans appel réseau, sans dépendance projet.
"""
from engine.skill_keywords import SKILL_KEYWORDS

# 3 mots-clés trouvés = weight 1.0 (plafonné)
_SCORE_DIVISOR: int = 3


def keyword_match_score(chunk_text: str, keywords: list[str]) -> float:
    """
    Score [0.0, 1.0] basé sur le nombre de mots-clés distincts trouvés.

    - 0 hit  → 0.0
    - 1 hit  → 0.333
    - 2 hits → 0.667
    - 3+ hits → 1.0 (plafonné)
    """
    if not chunk_text:
        return 0.0
    text_lower = chunk_text.lower()
    hits = sum(1 for kw in keywords if kw in text_lower)
    if hits == 0:
        return 0.0
    return round(min(hits / _SCORE_DIVISOR, 1.0), 3)


def classify_chunk_skills(chunk_text: str) -> list[dict]:
    """
    Retourne les skills détectés pour un chunk, triés par weight décroissant.

    Chaque entrée : {"slug": str, "weight": float}.
    Retourne [] si chunk_text est vide ou aucun keyword trouvé.
    """
    if not chunk_text or not chunk_text.strip():
        return []

    results = []
    for slug, keywords in SKILL_KEYWORDS.items():
        weight = keyword_match_score(chunk_text, keywords)
        if weight > 0.0:
            results.append({"slug": slug, "weight": weight})

    return sorted(results, key=lambda x: x["weight"], reverse=True)
