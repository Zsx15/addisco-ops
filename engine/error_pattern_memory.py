"""
error_pattern_memory.py — Error Pattern Memory V1 (TASK-057)

Module pur : aucune UI, aucune dépendance Streamlit, logique déterministe.
Fournit une mémoire comportementale persistante des erreurs pédagogiques.

Tendances possibles :
  - critique       : erreur fréquente, score bas, installée depuis longtemps, active
  - chronique      : erreur récurrente ancienne, toujours active
  - récent         : erreur récente, pattern encore faible
  - en_amelioration: score récent nettement supérieur au score ancien
  - stabilisé      : pattern inactif depuis STALE_DAYS jours
"""

import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

# ── Paramètres ────────────────────────────────────────────────────────────────
MIN_COUNT_PATTERN   = 2    # occurrences min pour constituer un pattern
MIN_COUNT_CRITICAL  = 5    # occurrences min pour "critique"
CHRONIC_MIN_AGE     = 14   # jours depuis la 1re occurrence → "chronique" / "critique"
RECENT_WINDOW_DAYS  = 7    # fenêtre "récent"
STALE_DAYS          = 21   # inactivité → "stabilisé"
IMPROVEMENT_DELTA   = 0.15 # delta score moyen (récent - ancien) → "en_amelioration"

_EXCLUDED_ERRORS = frozenset({"non_evaluable", "correct", ""})


# ── Logique de classification ─────────────────────────────────────────────────

def _classify_pattern(
    count:           int,
    avg_score:       float,
    first_seen_days: float,
    last_seen_days:  float,
    recent_count:    int,
    early_avg:       Optional[float],
    recent_avg:      Optional[float],
) -> str:
    """
    Retourne la tendance d'un pattern d'erreur.
    Priorité décroissante : stabilisé → en_amelioration → critique → chronique → récent → stabilisé
    """
    # Inactif depuis longtemps → stabilisé
    if last_seen_days > STALE_DAYS:
        return "stabilisé"

    # Amélioration significative du score
    if (
        early_avg is not None
        and recent_avg is not None
        and (recent_avg - early_avg) >= IMPROVEMENT_DELTA
    ):
        return "en_amelioration"

    # Critique : fréquent, score bas, installé depuis longtemps, toujours actif
    if (
        count >= MIN_COUNT_CRITICAL
        and avg_score < 0.60
        and recent_count >= 2
        and first_seen_days >= CHRONIC_MIN_AGE
    ):
        return "critique"

    # Chronique : installé depuis longtemps, toujours actif
    if first_seen_days >= CHRONIC_MIN_AGE and last_seen_days <= STALE_DAYS:
        return "chronique"

    # Récent : apparu récemment
    if last_seen_days <= RECENT_WINDOW_DAYS and count >= MIN_COUNT_PATTERN:
        return "récent"

    return "stabilisé"


# ── Fonction pure ─────────────────────────────────────────────────────────────

def compute_error_patterns(
    rows: list[tuple],
    now:  Optional[datetime] = None,
) -> list[dict]:
    """
    Calcule les patterns d'erreur à partir d'une liste brute de tentatives.

    rows : liste de tuples (error_type, score, created_at_iso, pedagogy_type)
           créés par la requête DB (created_at = ISO 8601 string).

    Retourne une liste de dicts triés par sévérité décroissante :
    {
        "error_type":       str,
        "count":            int,
        "avg_score":        float,
        "trend":            str,   # critique|chronique|récent|en_amelioration|stabilisé
        "last_seen_days":   float,
        "first_seen_days":  float,
        "recent_count":     int,
    }
    """
    if now is None:
        now = datetime.now(timezone.utc)

    # Agrégation par error_type
    buckets: dict[str, dict] = defaultdict(lambda: {
        "scores":     [],
        "dates":      [],
        "recent":     [],
        "early":      [],
    })

    for error_type, score, created_at_iso, _pedagogy in rows:
        if not error_type or error_type in _EXCLUDED_ERRORS:
            continue
        if score is None:
            continue

        try:
            dt = datetime.fromisoformat(created_at_iso.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except (ValueError, AttributeError):
            continue

        age_days = (now - dt).total_seconds() / 86400
        b = buckets[error_type]
        b["scores"].append(float(score))
        b["dates"].append(age_days)

        if age_days <= RECENT_WINDOW_DAYS:
            b["recent"].append(float(score))
        else:
            b["early"].append(float(score))

    patterns = []
    for error_type, b in buckets.items():
        if len(b["scores"]) < MIN_COUNT_PATTERN:
            continue

        count          = len(b["scores"])
        avg_score      = sum(b["scores"]) / count
        last_seen_days = min(b["dates"])
        first_seen_days = max(b["dates"])
        recent_count   = len(b["recent"])
        recent_avg     = sum(b["recent"]) / recent_count if b["recent"] else None
        early_avg      = sum(b["early"])  / len(b["early"]) if b["early"] else None

        trend = _classify_pattern(
            count, avg_score, first_seen_days, last_seen_days,
            recent_count, early_avg, recent_avg,
        )

        patterns.append({
            "error_type":      error_type,
            "count":           count,
            "avg_score":       round(avg_score, 3),
            "trend":           trend,
            "last_seen_days":  round(last_seen_days, 1),
            "first_seen_days": round(first_seen_days, 1),
            "recent_count":    recent_count,
        })

    # Tri sévérité : critique → chronique → récent → en_amelioration → stabilisé
    _SEVERITY = {"critique": 0, "chronique": 1, "récent": 2, "en_amelioration": 3, "stabilisé": 4}
    patterns.sort(key=lambda p: (_SEVERITY.get(p["trend"], 9), -p["count"]))
    return patterns


def get_persistent_error_types(
    patterns:        list[dict],
    include_trends:  Optional[list[str]] = None,
) -> list[str]:
    """
    Retourne la liste des error_type persistants selon les tendances demandées.
    Par défaut : critique + chronique + récent.
    """
    if include_trends is None:
        include_trends = ["critique", "chronique", "récent"]
    return [p["error_type"] for p in patterns if p["trend"] in include_trends]


# ── Fonction avec accès DB ────────────────────────────────────────────────────

def detect_persistent_error_patterns(user_id: str = "default") -> dict:
    """
    Charge les tentatives depuis SQLite et calcule les patterns persistants.

    Retourne :
    {
        "user_id":  str,
        "patterns": list[dict],   # voir compute_error_patterns()
        "persistent_types": list[str],  # error_types actifs (critique/chronique/récent)
        "has_critical": bool,
        "has_chronic":  bool,
    }
    """
    import database as _db

    with sqlite3.connect(_db.DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT error_type, score, created_at, pedagogy_type
            FROM attempts
            WHERE user_id = ?
              AND error_type IS NOT NULL
              AND error_type != ''
              AND score IS NOT NULL
            ORDER BY created_at ASC
            """,
            (user_id,),
        ).fetchall()
    conn.close()

    patterns        = compute_error_patterns(rows)
    persistent_types = get_persistent_error_types(patterns)

    return {
        "user_id":          user_id,
        "patterns":         patterns,
        "persistent_types": persistent_types,
        "has_critical":     any(p["trend"] == "critique"  for p in patterns),
        "has_chronic":      any(p["trend"] == "chronique" for p in patterns),
    }
