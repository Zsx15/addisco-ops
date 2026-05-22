"""Seuils de maîtrise et paramètres adaptatifs — source unique de vérité.

Ces constantes sont importées par :
  engine/spaced_rep.py, engine/skill_engine.py, engine/skill_graph.py,
  engine/adaptive_difficulty.py, db/chunks.py.
Toute modification ici se propage automatiquement à l'ensemble du moteur.

Note SQL : db/chunks.get_revision_suggestion utilise ces valeurs via f-string.
           Les tripwires TestReviewIntervalsCoherence dans test_regression.py
           détectent toute divergence entre REVIEW_INTERVALS et la logique SQL.
"""

# ── Maîtrise par chunk / skill ────────────────────────────────────────────────
MASTERY_FRAGILE:      float = 0.60  # avg_score < seuil → Fragile
MASTERY_MASTERED:     float = 0.80  # avg_score ≥ seuil ET n ≥ MIN_ATTEMPTS → Maîtrisé / Acquis
MASTERY_MIN_ATTEMPTS: int   = 3     # nombre minimum de tentatives pour valider la maîtrise

# ── Difficulté adaptative (engine/adaptive_difficulty.py) ─────────────────────
ADAPTIVE_FORCE_EASY: float = 0.40  # avg récent < seuil → forcer easy quelle que soit mastery
ADAPTIVE_ALLOW_HARD: float = 0.65  # avg récent ≥ seuil → autoriser hard (si Maîtrisé)

# ── Intervalles de révision espacée (jours) ───────────────────────────────────
# Protégés par les tripwires TestReviewIntervalsCoherence dans test_regression.py.
REVIEW_INTERVALS: dict[str, int] = {
    "Fragile":          1,
    "En consolidation": 3,
    "Maîtrisé":         7,
}
