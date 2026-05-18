"""Types de questions — constantes, sélection adaptative et explicabilité."""
import random
from typing import Optional

# Mappage question_type → dimension du profil pédagogique.
_PEDAGOGY_GROUPS: dict[str, list[str]] = {
    "logical":    ["question_directe"],
    "procedural": ["cas_pratique", "consequence"],
    "narrative":  ["reformulation"],
    "analogy":    ["vrai_faux", "question_piege"],
}

QUESTION_TYPES: list[str] = [
    "question_directe",
    "cas_pratique",
    "vrai_faux",
    "question_piege",
    "reformulation",
    "consequence",
]

# Biais mastery sur la sélection des types.
# Fragile  → compréhension et reformulation avant tout.
# Maîtrisé → challenge et application en situation complexe.
_MASTERY_BIAS: dict[str, list[str]] = {
    "Fragile":  ["reformulation", "consequence", "cas_pratique"],
    "Maîtrisé": ["question_piege", "cas_pratique", "consequence"],
}


def _choose_question_type(
    used_types: list[str],
    mastery_class: Optional[str] = None,
    profile_types: Optional[list[str]] = None,
) -> str:
    """
    Choisit le type de question le moins utilisé pour ce chunk.

    Priorités décroissantes :
    1. Rotation équitable (type le moins posé sur ce chunk).
    2. Biais mastery (Fragile/Maîtrisé) parmi les candidats équitables.
    3. Biais profil utilisateur (preferred_pedagogy) comme tie-breaker final.
    """
    if not used_types:
        bias = _MASTERY_BIAS.get(mastery_class or "", [])
        pool = bias if bias else QUESTION_TYPES
        if profile_types:
            matched = [t for t in profile_types if t in pool]
            if matched:
                return random.choice(matched)
        return random.choice(pool)

    counts     = {t: used_types.count(t) for t in QUESTION_TYPES}
    min_count  = min(counts.values())
    candidates = [t for t, c in counts.items() if c == min_count]
    bias       = _MASTERY_BIAS.get(mastery_class or "", [])
    biased     = [t for t in bias if t in candidates]
    pool       = biased if biased else candidates
    if profile_types:
        matched = [t for t in profile_types if t in pool]
        if matched:
            return random.choice(matched)
    return random.choice(pool)


def explain_type_choice(
    used_types: list[str],
    mastery_class: Optional[str],
    profile_pedagogy: Optional[str],
    chosen_type: str,
) -> str:
    """
    Explication textuelle de la décision de sélection du type de question.
    Miroir narratif de _choose_question_type() — aucun appel API.
    """
    _type_fr: dict[str, str] = {
        "question_directe": "question directe",
        "cas_pratique":     "cas pratique",
        "vrai_faux":        "vrai / faux",
        "question_piege":   "question piège",
        "reformulation":    "reformulation",
        "consequence":      "conséquence",
    }
    _mastery_fr: dict[str, str] = {
        "Fragile":          "Fragile",
        "En consolidation": "En consolidation",
        "Maîtrisé":         "Maîtrisé",
    }
    _profile_fr: dict[str, str] = {
        "logical":    "analytique",
        "procedural": "procédural",
        "narrative":  "narratif",
        "analogy":    "analogique",
    }

    chosen_fr = _type_fr.get(chosen_type, chosen_type)

    if not used_types:
        if mastery_class and mastery_class in _MASTERY_BIAS:
            mc_fr = _mastery_fr.get(mastery_class, mastery_class)
            return f"Premier type sur cette section — biais {mc_fr} appliqué ({chosen_fr})"
        return f"Premier type sur cette section — sélection initiale ({chosen_fr})"

    counts     = {t: used_types.count(t) for t in QUESTION_TYPES}
    min_count  = min(counts.values())
    candidates = [t for t, c in counts.items() if c == min_count]
    bias       = _MASTERY_BIAS.get(mastery_class or "", [])
    biased     = [t for t in bias if t in candidates]

    profile_types = _PEDAGOGY_GROUPS.get(profile_pedagogy or "", []) if profile_pedagogy else []

    if biased and chosen_type in biased:
        mc_fr = _mastery_fr.get(mastery_class or "", mastery_class or "")
        if profile_types and chosen_type in profile_types:
            pf_fr = _profile_fr.get(profile_pedagogy or "", profile_pedagogy or "")
            return f"Sélectionné par biais maîtrise ({mc_fr}) et profil {pf_fr} ({chosen_fr})"
        return f"Sélectionné par biais maîtrise ({mc_fr} → {chosen_fr} priorisé)"

    if profile_types and chosen_type in profile_types and chosen_type in candidates:
        pf_fr = _profile_fr.get(profile_pedagogy or "", profile_pedagogy or "")
        return f"Sélectionné par profil pédagogique ({pf_fr} → {chosen_fr} favorisé)"

    return f"Sélectionné par rotation équitable ({chosen_fr} le moins utilisé sur cette section)"
