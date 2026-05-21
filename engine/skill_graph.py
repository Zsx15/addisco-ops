"""
skill_graph.py — Skill Graph Engine V1 (TASK-055)

Graphe déclaratif des dépendances pédagogiques entre skills.
Module pur : zéro import projet, zéro accès DB.

Hiérarchie (inspirée taxonomie de Bloom adaptée au domaine) :
  Level 0 — fondations  : memorisation_faits, identification_concepts
  Level 1 — compréhension: comprehension_procedure
  Level 2 — application  : application_regles, analyse_causale, synthese_reformulation
  Level 3 — maîtrise     : conformite_reglementaire, resolution_problemes
  Level 4 — expertise    : prise_decision, evaluation_critique
"""

from collections import deque
from typing import Optional

# ── Seuil de maîtrise ─────────────────────────────────────────────────────────
# Score minimum pour considérer un prérequis comme "acquis"
MASTERY_THRESHOLD: float = 0.70

# ── Graphe déclaratif ─────────────────────────────────────────────────────────
# Format : "slug" -> [liste des slugs prérequis]
# Un skill sans prérequis est une fondation (level 0).
SKILL_GRAPH: dict[str, list[str]] = {
    # Fondations — aucun prérequis
    "memorisation_faits":       [],
    "identification_concepts":  [],

    # Compréhension — nécessite mémorisation
    "comprehension_procedure":  ["memorisation_faits"],

    # Application — nécessite compréhension + identification
    "application_regles":       ["identification_concepts", "comprehension_procedure"],
    "analyse_causale":          ["identification_concepts", "comprehension_procedure"],
    "synthese_reformulation":   ["identification_concepts", "comprehension_procedure"],

    # Maîtrise — nécessite application
    "conformite_reglementaire": ["application_regles", "identification_concepts"],
    "resolution_problemes":     ["application_regles", "analyse_causale"],

    # Expertise — nécessite maîtrise
    "prise_decision":           ["resolution_problemes", "analyse_causale"],
    "evaluation_critique":      ["synthese_reformulation", "analyse_causale"],
}

# ── Traversal ─────────────────────────────────────────────────────────────────

def get_prerequisites(slug: str) -> list[str]:
    """Prérequis directs d'un skill (liste vide si fondation ou inconnu)."""
    return list(SKILL_GRAPH.get(slug, []))


def get_all_prerequisites(slug: str) -> list[str]:
    """Tous les prérequis transitifs d'un skill (DFS)."""
    visited: set[str] = set()
    stack = list(SKILL_GRAPH.get(slug, []))
    while stack:
        current = stack.pop()
        if current in visited:
            continue
        visited.add(current)
        stack.extend(SKILL_GRAPH.get(current, []))
    return list(visited)


def get_dependents(slug: str) -> list[str]:
    """Skills qui dépendent directement de ce skill."""
    return [s for s, prereqs in SKILL_GRAPH.items() if slug in prereqs]


def get_all_dependents(slug: str) -> list[str]:
    """Tous les skills qui dépendent transitivement de ce skill."""
    visited: set[str] = set()
    stack = get_dependents(slug)
    while stack:
        current = stack.pop()
        if current in visited:
            continue
        visited.add(current)
        stack.extend(get_dependents(current))
    return list(visited)


def topological_order() -> list[str]:
    """
    Ordre d'apprentissage optimal via tri topologique (algorithme de Kahn).
    Retourne une liste vide si le graphe contient un cycle (invalide).
    """
    in_degree: dict[str, int] = {slug: 0 for slug in SKILL_GRAPH}
    dependents_map: dict[str, list[str]] = {slug: [] for slug in SKILL_GRAPH}

    for slug, prereqs in SKILL_GRAPH.items():
        for prereq in prereqs:
            if prereq in SKILL_GRAPH:
                in_degree[slug] += 1
                dependents_map[prereq].append(slug)

    queue: deque[str] = deque(
        slug for slug, deg in sorted(in_degree.items()) if deg == 0
    )
    result: list[str] = []
    while queue:
        slug = queue.popleft()
        result.append(slug)
        for dep in sorted(dependents_map.get(slug, [])):
            in_degree[dep] -= 1
            if in_degree[dep] == 0:
                queue.append(dep)

    return result if len(result) == len(SKILL_GRAPH) else []


def has_cycle() -> bool:
    """Retourne True si le graphe contient un cycle (invalide)."""
    return len(topological_order()) != len(SKILL_GRAPH)


def get_level(slug: str) -> int:
    """
    Niveau topologique du skill (0 = fondation).
    Calculé comme le plus long chemin depuis une fondation.
    """
    prereqs = SKILL_GRAPH.get(slug, [])
    if not prereqs:
        return 0
    return 1 + max(
        get_level(p) for p in prereqs if p in SKILL_GRAPH
    )


def levels() -> dict[str, int]:
    """Dictionnaire slug → niveau pour tous les skills du graphe."""
    return {slug: get_level(slug) for slug in SKILL_GRAPH}


# ── Propagation déterministe ──────────────────────────────────────────────────

def is_ready(slug: str,
             mastery: dict[str, float],
             threshold: float = MASTERY_THRESHOLD) -> bool:
    """
    Un skill est "prêt à apprendre" si tous ses prérequis directs
    ont un score >= threshold dans le dict mastery.
    Un skill sans prérequis est toujours prêt.
    """
    for prereq in SKILL_GRAPH.get(slug, []):
        if mastery.get(prereq, 0.0) < threshold:
            return False
    return True


def get_blocking(slug: str,
                 mastery: dict[str, float],
                 threshold: float = MASTERY_THRESHOLD) -> list[str]:
    """
    Retourne la liste des prérequis directs non maîtrisés qui bloquent ce skill.
    Vide si le skill est prêt ou sans prérequis.
    """
    return [
        prereq
        for prereq in SKILL_GRAPH.get(slug, [])
        if mastery.get(prereq, 0.0) < threshold
    ]


def get_full_blocking_chain(slug: str,
                             mastery: dict[str, float],
                             threshold: float = MASTERY_THRESHOLD) -> list[str]:
    """
    Tous les prérequis transitifs non maîtrisés qui bloquent ce skill.
    """
    visited: set[str] = set()
    stack = list(SKILL_GRAPH.get(slug, []))
    blocking: list[str] = []
    while stack:
        current = stack.pop()
        if current in visited:
            continue
        visited.add(current)
        score = mastery.get(current, 0.0)
        if score < threshold:
            blocking.append(current)
            stack.extend(SKILL_GRAPH.get(current, []))
    return blocking


def get_session_order(mastery: dict[str, float],
                      threshold: float = MASTERY_THRESHOLD) -> list[str]:
    """
    Ordre de session optimal :
    1. prioriser les fondations non maîtrisées ;
    2. puis les skills prêts (prérequis maîtrisés) non maîtrisés ;
    3. puis les skills déjà maîtrisés (révision) ;
    4. les skills bloqués en dernier.

    Retourne la liste complète des skills du graphe dans cet ordre.
    """
    topo = topological_order()
    if not topo:
        return list(SKILL_GRAPH.keys())

    def _priority(slug: str) -> tuple[int, int]:
        score = mastery.get(slug, 0.0)
        level = get_level(slug)
        mastered = score >= threshold
        ready = is_ready(slug, mastery, threshold)

        if not mastered and ready:
            return (0, level)   # à apprendre maintenant
        if mastered:
            return (1, level)   # révisable
        return (2, level)       # bloqué

    return sorted(topo, key=_priority)


# ── Cohérence du graphe ───────────────────────────────────────────────────────

def validate_graph() -> list[str]:
    """
    Vérifie la cohérence interne du graphe.
    Retourne une liste d'erreurs (vide si tout est OK).
    """
    errors: list[str] = []

    # Cycles
    if has_cycle():
        errors.append("Cycle détecté dans le graphe — tri topologique impossible.")

    # Prérequis inconnus
    for slug, prereqs in SKILL_GRAPH.items():
        for prereq in prereqs:
            if prereq not in SKILL_GRAPH:
                errors.append(
                    f"Prérequis inconnu : '{prereq}' référencé par '{slug}'."
                )

    # Auto-référence
    for slug, prereqs in SKILL_GRAPH.items():
        if slug in prereqs:
            errors.append(f"Auto-référence détectée : '{slug}' est son propre prérequis.")

    return errors
