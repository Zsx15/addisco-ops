"""
adaptive_difficulty.py — Adaptive Difficulty Engine V2 (TASK-056)

Module pur : aucun accès DB, aucun import Streamlit.

Wrapper adaptatif autour de la sélection de type de question.
Signaux supplémentaires par rapport à _choose_question_type :
  - recent_scores  : trend récent — dilue mastery_class si divergent
  - graph_level    : niveau Bloom (0-4) — bloque les hard aux fondations
  - repeated_errors: pattern d'erreurs dominant → type correctif ciblé
"""

import random
from collections import Counter
from typing import Optional

from engine.question_type import QUESTION_TYPES, _MASTERY_BIAS
from engine.thresholds import ADAPTIVE_FORCE_EASY, ADAPTIVE_ALLOW_HARD

# ── Buckets de difficulté ─────────────────────────────────────────────────────
DIFFICULTY_EASY   = frozenset(["vrai_faux", "question_directe"])
DIFFICULTY_MEDIUM = frozenset(["reformulation", "question_directe", "cas_pratique"])
DIFFICULTY_HARD   = frozenset(["cas_pratique", "consequence", "question_piege"])

# ── Paramètres ────────────────────────────────────────────────────────────────
RECENT_N         = 5                  # fenêtre de scores récents
SCORE_FORCE_EASY = ADAPTIVE_FORCE_EASY  # avg récent < seuil → forcer easy quelle que soit mastery
SCORE_ALLOW_HARD = ADAPTIVE_ALLOW_HARD  # avg récent ≥ seuil → autoriser hard (si Maîtrisé)

# ── Correction par type d'erreur dominant ─────────────────────────────────────
# Type de question recommandé selon le pattern d'erreur le plus fréquent.
_ERROR_CORRECTION: dict[str, str] = {
    "reponse_vague":    "reformulation",    # préciser sa réponse
    "oubli_etape":      "cas_pratique",     # pratiquer les étapes
    "confusion_notion": "vrai_faux",        # clarifier les concepts
    "hors_sujet":       "question_directe", # recentrer sur le sujet
    "erreur_ordre":     "consequence",      # pratiquer la séquence
}
_ERROR_CORRECTION_FRAGILE: dict[str, str] = {
    "reponse_vague":    "reformulation",
    "oubli_etape":      "reformulation",    # Fragile : pas de cas_pratique complexe
    "confusion_notion": "vrai_faux",
    "hors_sujet":       "question_directe",
    "erreur_ordre":     "question_directe", # Fragile : pas de consequence
}


# ── Fonctions publiques ───────────────────────────────────────────────────────

def get_difficulty_target(
    mastery_class: Optional[str],
    recent_scores: Optional[list[float]] = None,
    graph_level:   int = 2,
) -> str:
    """
    Retourne le bucket de difficulté cible : "easy" | "medium" | "hard".

    Priorité des signaux (décroissante) :
    1. Trend récent — si avg < SCORE_FORCE_EASY, forcer easy
    2. Niveau graphe — fondations (0-1) ne vont jamais en hard
    3. Classe de maîtrise du chunk
    """
    avg_recent: Optional[float] = None
    if recent_scores:
        window     = recent_scores[-RECENT_N:]
        avg_recent = sum(window) / len(window)

    # Signal 1 : trend récent trop bas → forcer easy
    if avg_recent is not None and avg_recent < SCORE_FORCE_EASY:
        return "easy"

    # Signal 2 : fondations Bloom (Lv0-1) → jamais hard
    if graph_level <= 1:
        return "easy" if mastery_class == "Fragile" else "medium"

    # Signal 3 : mastery_class
    if mastery_class == "Fragile":
        return "easy"
    if mastery_class == "En consolidation":
        return "medium"
    if mastery_class == "Maîtrisé":
        if avg_recent is None or avg_recent >= SCORE_ALLOW_HARD:
            return "hard"
        return "medium"

    return "medium"


def get_error_correction_type(
    repeated_errors: Optional[list[str]],
    mastery_class:   Optional[str] = None,
) -> Optional[str]:
    """
    Retourne le type de question correctif si un pattern d'erreur domine (≥ 2 occ.).
    Retourne None si le pattern n'est pas assez fort.
    """
    if not repeated_errors:
        return None
    top_error, top_count = Counter(repeated_errors).most_common(1)[0]
    if top_count < 2:
        return None
    table = _ERROR_CORRECTION_FRAGILE if mastery_class == "Fragile" else _ERROR_CORRECTION
    return table.get(top_error)


def filter_by_difficulty(candidates: list[str], target: str) -> list[str]:
    """
    Filtre la liste de candidats par bucket de difficulté.
    Retourne la liste complète si aucune intersection (fallback garanti).
    """
    bucket = {"easy": DIFFICULTY_EASY, "hard": DIFFICULTY_HARD}.get(target, DIFFICULTY_MEDIUM)
    filtered = [t for t in candidates if t in bucket]
    return filtered if filtered else candidates


def choose_adaptive_question_type(
    used_types:      list[str],
    mastery_class:   Optional[str]        = None,
    profile_types:   Optional[list[str]]  = None,
    recent_scores:   Optional[list[float]] = None,
    graph_level:     int                   = 2,
    repeated_errors: Optional[list[str]]  = None,
) -> str:
    """
    Sélection adaptative du type de question (V2).

    Étapes (priorité décroissante) :
    1. Correction d'erreur dominante — si pattern clair et type sous-utilisé
    2. Cible de difficulté — recent_scores + graph_level + mastery_class
    3. Rotation équitable — type le moins utilisé sur ce chunk
    4. Filtre difficulté — intersection candidats × bucket cible
    5. Tie-breaker profil — preferred_pedagogy comme départage final
    """
    # ── 1. Correction d'erreur dominante ─────────────────────────────────────
    correction = get_error_correction_type(repeated_errors, mastery_class)
    if correction and correction in QUESTION_TYPES:
        counts = {t: used_types.count(t) for t in QUESTION_TYPES}
        min_c  = min(counts.values()) if counts else 0
        if counts.get(correction, 0) <= min_c + 1:
            return correction

    # ── 2. Cible de difficulté ────────────────────────────────────────────────
    target = get_difficulty_target(mastery_class, recent_scores, graph_level)

    # ── 3. Rotation équitable ─────────────────────────────────────────────────
    if not used_types:
        base_bias  = _MASTERY_BIAS.get(mastery_class or "", [])
        candidates = list(base_bias) if base_bias else list(QUESTION_TYPES)
    else:
        counts     = {t: used_types.count(t) for t in QUESTION_TYPES}
        min_c      = min(counts.values())
        candidates = [t for t, c in counts.items() if c == min_c]

    # ── 4. Filtre difficulté ──────────────────────────────────────────────────
    candidates = filter_by_difficulty(candidates, target)

    # ── 5. Tie-breaker profil ─────────────────────────────────────────────────
    if profile_types:
        matched = [t for t in profile_types if t in candidates]
        if matched:
            return random.choice(matched)

    return random.choice(candidates) if candidates else random.choice(QUESTION_TYPES)
