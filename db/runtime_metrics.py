"""
Runtime Metrics Engine — TASK-068
Persistance SQLite des événements runtime LLM et pédagogiques.

Principe :
- record_metric() est non-bloquant : toute exception est catchée et loggée.
- Aucune erreur de métrique ne doit jamais interrompre le moteur métier.
- get_metrics() / get_metrics_summary() : lecture seule pour analytics.
"""
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Optional

import database as _db

logger = logging.getLogger(__name__)


def record_metric(
    *,
    metric_type: str,
    endpoint: Optional[str] = None,
    latency_ms: Optional[int] = None,
    estimated_cost: Optional[float] = None,
    tokens_input: Optional[int] = None,
    tokens_output: Optional[int] = None,
    success: bool = True,
    fallback_used: bool = False,
    error_type: Optional[str] = None,
    question_type: Optional[str] = None,
    score: Optional[float] = None,
    document_id: Optional[int] = None,
    user_id: str = "default",
) -> None:
    """Insère une métrique runtime. Non-bloquant — jamais d'exception propagée."""
    try:
        ts = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(_db.DB_PATH) as conn:
            conn.execute(
                """
                INSERT INTO runtime_metrics (
                    timestamp, user_id, metric_type, endpoint,
                    latency_ms, estimated_cost,
                    tokens_input, tokens_output,
                    success, fallback_used, error_type,
                    question_type, score, document_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ts, user_id, metric_type, endpoint,
                    latency_ms, estimated_cost,
                    tokens_input, tokens_output,
                    1 if success else 0,
                    1 if fallback_used else 0,
                    error_type,
                    question_type, score, document_id,
                ),
            )
        conn.close()
    except Exception as exc:
        logger.warning("runtime_metrics.record_metric: échec non-bloquant (%s)", exc)


def get_metrics(
    hours: int = 24,
    user_id: Optional[str] = None,
    metric_type: Optional[str] = None,
    limit: int = 1000,
) -> list[dict]:
    """Retourne les métriques récentes. Lecture seule."""
    try:
        clauses = ["timestamp >= datetime('now', ?  )"]
        params: list = [f"-{hours} hours"]
        if user_id:
            clauses.append("user_id = ?")
            params.append(user_id)
        if metric_type:
            clauses.append("metric_type = ?")
            params.append(metric_type)
        where = " AND ".join(clauses)

        with sqlite3.connect(_db.DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"SELECT * FROM runtime_metrics WHERE {where} ORDER BY timestamp DESC LIMIT ?",
                params + [limit],
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as exc:
        logger.warning("runtime_metrics.get_metrics: %s", exc)
        return []


def get_metrics_summary(hours: int = 24) -> dict:
    """
    Agrégats SQL pour le dashboard admin.
    Retourne un dict avec toutes les métriques consolidées.
    """
    empty: dict = {
        "total_calls": 0,
        "success_rate": 0.0,
        "fallback_rate": 0.0,
        "avg_latency_ms": 0.0,
        "p95_latency_ms": 0.0,
        "estimated_cost_total": 0.0,
        "total_tokens": 0,
        "error_types": {},
        "by_endpoint": {},
        "by_user": {},
        "slow_calls": 0,
        "hours": hours,
    }
    try:
        interval = f"-{hours} hours"
        with sqlite3.connect(_db.DB_PATH) as conn:
            conn.row_factory = sqlite3.Row

            # Agrégats globaux
            row = conn.execute(
                """
                SELECT
                    COUNT(*)                                    AS total_calls,
                    ROUND(AVG(success) * 100, 1)               AS success_rate,
                    ROUND(AVG(fallback_used) * 100, 1)         AS fallback_rate,
                    ROUND(AVG(latency_ms), 0)                  AS avg_latency_ms,
                    ROUND(SUM(COALESCE(estimated_cost, 0)), 6) AS estimated_cost_total,
                    SUM(COALESCE(tokens_input, 0) + COALESCE(tokens_output, 0)) AS total_tokens,
                    SUM(CASE WHEN latency_ms > 3000 THEN 1 ELSE 0 END) AS slow_calls
                FROM runtime_metrics
                WHERE timestamp >= datetime('now', ?)
                """,
                (interval,),
            ).fetchone()
            if row:
                empty.update({k: (row[k] or 0) for k in row.keys()})

            # P95 latence (approximation percentile SQLite)
            p95_row = conn.execute(
                """
                SELECT latency_ms FROM runtime_metrics
                WHERE timestamp >= datetime('now', ?) AND latency_ms IS NOT NULL
                ORDER BY latency_ms
                LIMIT 1
                OFFSET MAX(0, CAST(
                    (SELECT COUNT(*) FROM runtime_metrics
                     WHERE timestamp >= datetime('now', ?) AND latency_ms IS NOT NULL)
                    * 0.95 AS INTEGER
                ) - 1)
                """,
                (interval, interval),
            ).fetchone()
            empty["p95_latency_ms"] = p95_row[0] if p95_row else 0

            # Répartition par endpoint
            by_ep = conn.execute(
                """
                SELECT endpoint,
                       COUNT(*) AS calls,
                       ROUND(AVG(latency_ms), 0) AS avg_ms,
                       ROUND(AVG(success) * 100, 1) AS ok_pct
                FROM runtime_metrics
                WHERE timestamp >= datetime('now', ?) AND endpoint IS NOT NULL
                GROUP BY endpoint ORDER BY calls DESC
                """,
                (interval,),
            ).fetchall()
            empty["by_endpoint"] = {r["endpoint"]: dict(r) for r in by_ep}

            # Top erreurs
            errs = conn.execute(
                """
                SELECT error_type, COUNT(*) AS n
                FROM runtime_metrics
                WHERE timestamp >= datetime('now', ?) AND error_type IS NOT NULL
                GROUP BY error_type ORDER BY n DESC LIMIT 10
                """,
                (interval,),
            ).fetchall()
            empty["error_types"] = {r["error_type"]: r["n"] for r in errs}

            # Top users par volume d'appels
            by_user = conn.execute(
                """
                SELECT user_id,
                       COUNT(*) AS calls,
                       ROUND(SUM(COALESCE(estimated_cost, 0)), 6) AS cost
                FROM runtime_metrics
                WHERE timestamp >= datetime('now', ?)
                GROUP BY user_id ORDER BY calls DESC LIMIT 10
                """,
                (interval,),
            ).fetchall()
            empty["by_user"] = {r["user_id"]: dict(r) for r in by_user}

        conn.close()
    except Exception as exc:
        logger.warning("runtime_metrics.get_metrics_summary: %s", exc)
    return empty
