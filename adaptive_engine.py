"""Façade de compatibilité — logique migrée dans engine/.

Tous les imports existants (database.py, ai_service.py, db/profile.py, app.py)
continuent de fonctionner sans modification.
"""
from engine.spaced_rep import (
    REVIEW_INTERVALS,
    _adaptive_interval,
    classify_mastery,
)
from engine.question_type import (
    QUESTION_TYPES,
    _MASTERY_BIAS,
    _PEDAGOGY_GROUPS,
    _choose_question_type,
    explain_type_choice,
)
from engine.profile_metrics import (
    compute_momentum,
    compute_learning_velocity,
    compute_consistency_score,
)
from engine.session_plan import (
    _OBJECTIVES,
    _DURATION_BY_MASTERY,
    _compute_priority_score,
    build_session_plan,
)
from engine.retention import (
    _RETENTION_WINDOWS,
    compute_retention_metrics,
)

__all__ = [
    # spaced_rep
    "REVIEW_INTERVALS",
    "_adaptive_interval",
    "classify_mastery",
    # question_type
    "QUESTION_TYPES",
    "_MASTERY_BIAS",
    "_PEDAGOGY_GROUPS",
    "_choose_question_type",
    "explain_type_choice",
    # profile_metrics
    "compute_momentum",
    "compute_learning_velocity",
    "compute_consistency_score",
    # session_plan
    "_OBJECTIVES",
    "_DURATION_BY_MASTERY",
    "_compute_priority_score",
    "build_session_plan",
    # retention
    "_RETENTION_WINDOWS",
    "compute_retention_metrics",
]
