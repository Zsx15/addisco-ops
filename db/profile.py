"""
Profil d'apprentissage, plan de session adaptatif, métriques de rétention.
Utilise database.DB_PATH via import tardif pour respecter le monkey-patch des tests.
"""
import json
import logging
import sqlite3
from typing import Optional

import database as _db
from adaptive_engine import (
    _PEDAGOGY_GROUPS,
    build_session_plan,
    classify_mastery,
    compute_learning_velocity,
    compute_momentum,
    compute_consistency_score,
    compute_retention_metrics,
)
from db.chunks import get_chunk_stats

logger = logging.getLogger(__name__)


def get_learning_profile(user_id: str = "default") -> Optional[dict]:
    with sqlite3.connect(_db.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM user_learning_profile WHERE user_id = ?", (user_id,)
        ).fetchone()
    if row is None:
        return None
    d = dict(row)
    if d.get("fragile_topics"):
        try:
            d["fragile_topics"] = json.loads(d["fragile_topics"])
        except (json.JSONDecodeError, TypeError):
            d["fragile_topics"] = []
    return d


def compute_and_save_learning_profile(user_id: str = "default") -> dict:
    """
    Calcule le profil pédagogique depuis les tentatives et le sauvegarde (INSERT OR REPLACE).

    Scores par groupe pédagogique (_PEDAGOGY_GROUPS) :
      logical: question_directe | procedural: cas_pratique, consequence
      narrative: reformulation  | analogy: vrai_faux, question_piege

    Métriques adaptatives : momentum, learning_velocity, consistency_score.
    """
    with sqlite3.connect(_db.DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT pedagogy_type, topic, score, created_at
            FROM attempts
            WHERE user_id = ? AND score IS NOT NULL
            ORDER BY created_at ASC
            """,
            (user_id,),
        ).fetchall()

    score_time_rows       = [(r[3], r[2]) for r in rows]
    momentum_val          = compute_momentum(score_time_rows)
    learning_velocity_val = compute_learning_velocity(score_time_rows)
    consistency_val       = compute_consistency_score(score_time_rows)

    if not rows:
        profile = {
            "user_id": user_id,
            "preferred_pedagogy": None,
            "logical_score": 0.0,
            "procedural_score": 0.0,
            "narrative_score": 0.0,
            "analogy_score": 0.0,
            "average_score": 0.0,
            "fragile_topics": [],
            "momentum":          momentum_val,
            "learning_velocity": learning_velocity_val,
            "consistency_score": consistency_val,
        }
    else:
        all_scores = [r[2] for r in rows]
        average_score = round(sum(all_scores) / len(all_scores), 3)

        group_scores: dict[str, list[float]] = {g: [] for g in _PEDAGOGY_GROUPS}
        topic_scores: dict[str, list[float]] = {}

        for ptype, topic, score, _created_at in rows:
            for group, types in _PEDAGOGY_GROUPS.items():
                if ptype in types:
                    group_scores[group].append(score)
            if topic:
                topic_scores.setdefault(topic, []).append(score)

        def _avg(lst: list[float]) -> float:
            return round(sum(lst) / len(lst), 3) if lst else 0.0

        logical_score    = _avg(group_scores["logical"])
        procedural_score = _avg(group_scores["procedural"])
        narrative_score  = _avg(group_scores["narrative"])
        analogy_score    = _avg(group_scores["analogy"])

        scored_groups = {g: _avg(v) for g, v in group_scores.items() if v}
        preferred_pedagogy = max(scored_groups, key=scored_groups.get) if scored_groups else None
        fragile_topics = sorted(t for t, s in topic_scores.items() if _avg(s) < 0.6)

        profile = {
            "user_id": user_id,
            "preferred_pedagogy": preferred_pedagogy,
            "logical_score": logical_score,
            "procedural_score": procedural_score,
            "narrative_score": narrative_score,
            "analogy_score": analogy_score,
            "average_score": average_score,
            "fragile_topics": fragile_topics,
            "momentum":          momentum_val,
            "learning_velocity": learning_velocity_val,
            "consistency_score": consistency_val,
        }

    with sqlite3.connect(_db.DB_PATH) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO user_learning_profile
                (user_id, preferred_pedagogy, logical_score, procedural_score,
                 narrative_score, analogy_score, average_score, fragile_topics,
                 momentum, learning_velocity, consistency_score, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                profile["user_id"],
                profile["preferred_pedagogy"],
                profile["logical_score"],
                profile["procedural_score"],
                profile["narrative_score"],
                profile["analogy_score"],
                profile["average_score"],
                json.dumps(profile["fragile_topics"], ensure_ascii=False),
                profile["momentum"],
                profile["learning_velocity"],
                profile["consistency_score"],
            ),
        )

    # Mise à jour skill mastery — non bloquante
    try:
        from db.skills import update_user_skill_mastery
        update_user_skill_mastery(user_id)
    except Exception as exc:
        logger.warning(
            "update_user_skill_mastery échoué pour user %s (non bloquant) : %s", user_id, exc
        )

    return profile


def get_next_session_plan(user_id: str = "default", max_items: int = 5) -> list[dict]:
    """Plan de session personnalisé — délègue le scoring à adaptive_engine.build_session_plan."""
    df_stats = get_chunk_stats(user_id)
    if df_stats.empty:
        return []
    df_enriched = classify_mastery(df_stats)
    return build_session_plan(df_enriched, max_items=max_items)


def get_retention_metrics(user_id: str = "default") -> dict[str, Optional[float]]:
    """Métriques de rétention J+1/J+7/J+30 — calculées à la volée."""
    with sqlite3.connect(_db.DB_PATH) as conn:
        rows_raw = conn.execute(
            """
            SELECT chunk_id, created_at, score
            FROM attempts
            WHERE user_id = ?
              AND score IS NOT NULL
              AND chunk_id IS NOT NULL
            ORDER BY chunk_id, created_at ASC
            """,
            (user_id,),
        ).fetchall()
    return compute_retention_metrics([(r[0], r[1], r[2]) for r in rows_raw])
