"""
Session tracking — learning_sessions + session_events.
TASK-084 — Human Testing Analytics & Session Tracking.
Utilise database.DB_PATH via import tardif pour respecter le monkey-patch des tests.
"""
import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Optional

import database as _db
import pandas as pd

logger = logging.getLogger(__name__)


def start_session(user_id: str, corpus_id: Optional[int] = None) -> int:
    """Ouvre une nouvelle session d'apprentissage. Retourne le session_id."""
    with sqlite3.connect(_db.DB_PATH) as conn:
        cur = conn.execute(
            "INSERT INTO learning_sessions (user_id, corpus_id) VALUES (?, ?)",
            (user_id, corpus_id),
        )
        session_id = cur.lastrowid
    conn.close()
    return session_id


def close_session(
    session_id: int,
    total_questions: int = 0,
    completed_questions: int = 0,
    avg_score: Optional[float] = None,
    dominant_error: Optional[str] = None,
    recommendation_followed: Optional[bool] = None,
    feedback_score: Optional[float] = None,
) -> None:
    """Ferme une session : calcule la durée et enregistre les stats finales."""
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(_db.DB_PATH) as conn:
        row = conn.execute(
            "SELECT started_at FROM learning_sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        duration = None
        if row and row[0]:
            try:
                started = datetime.fromisoformat(str(row[0]))
                duration = int((datetime.now(timezone.utc) - started.replace(tzinfo=timezone.utc)).total_seconds())
            except Exception:
                pass
        rec_followed = None
        if recommendation_followed is not None:
            rec_followed = 1 if recommendation_followed else 0
        conn.execute(
            """
            UPDATE learning_sessions
            SET ended_at = ?, duration_seconds = ?,
                total_questions = ?, completed_questions = ?,
                avg_score = ?, dominant_error = ?,
                recommendation_followed = ?, feedback_score = ?
            WHERE id = ?
            """,
            (now, duration, total_questions, completed_questions,
             avg_score, dominant_error, rec_followed, feedback_score,
             session_id),
        )
    conn.close()


def log_event(
    session_id: int,
    event_type: str,
    event_data: Optional[dict] = None,
) -> None:
    """Enregistre un événement dans la session (silencieux en cas d'erreur)."""
    data_str = json.dumps(event_data, ensure_ascii=False) if event_data else None
    try:
        with sqlite3.connect(_db.DB_PATH) as conn:
            conn.execute(
                "INSERT INTO session_events (session_id, event_type, event_data) VALUES (?, ?, ?)",
                (session_id, event_type, data_str),
            )
        conn.close()
    except Exception as exc:
        logger.debug("log_event silent fail: %s", exc)


def get_user_sessions(user_id: str, limit: int = 20) -> list[dict]:
    """Retourne les sessions récentes avec corpus_name si disponible."""
    with sqlite3.connect(_db.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT ls.*, c.corpus_name
            FROM learning_sessions ls
            LEFT JOIN corpus c ON c.id = ls.corpus_id
            WHERE ls.user_id = ?
            ORDER BY ls.started_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_session_analytics(user_id: str) -> dict:
    """Agrégats sessions pour les KPIs analytics."""
    with sqlite3.connect(_db.DB_PATH) as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM learning_sessions WHERE user_id = ?",
            (user_id,),
        ).fetchone()[0]

        sessions_week = conn.execute(
            "SELECT COUNT(*) FROM learning_sessions WHERE user_id = ? "
            "AND started_at >= datetime('now', '-7 days')",
            (user_id,),
        ).fetchone()[0]

        sessions_prev = conn.execute(
            "SELECT COUNT(*) FROM learning_sessions WHERE user_id = ? "
            "AND started_at >= datetime('now', '-14 days') "
            "AND started_at < datetime('now', '-7 days')",
            (user_id,),
        ).fetchone()[0]

        avg_dur = conn.execute(
            "SELECT AVG(duration_seconds) FROM learning_sessions "
            "WHERE user_id = ? AND duration_seconds IS NOT NULL",
            (user_id,),
        ).fetchone()[0]

        completed = conn.execute(
            "SELECT COUNT(*) FROM learning_sessions "
            "WHERE user_id = ? AND completed_questions >= 3",
            (user_id,),
        ).fetchone()[0]

        top_corpus = conn.execute(
            """
            SELECT c.corpus_name, COUNT(*) AS n
            FROM learning_sessions ls
            JOIN corpus c ON c.id = ls.corpus_id
            WHERE ls.user_id = ? AND ls.corpus_id IS NOT NULL
            GROUP BY ls.corpus_id ORDER BY n DESC LIMIT 1
            """,
            (user_id,),
        ).fetchone()

        avg_score_week = conn.execute(
            "SELECT AVG(score) FROM attempts WHERE user_id = ? "
            "AND created_at >= datetime('now', '-7 days')",
            (user_id,),
        ).fetchone()[0]

        avg_score_prev = conn.execute(
            "SELECT AVG(score) FROM attempts WHERE user_id = ? "
            "AND created_at >= datetime('now', '-14 days') "
            "AND created_at < datetime('now', '-7 days')",
            (user_id,),
        ).fetchone()[0]

    conn.close()
    return {
        "total_sessions":       total,
        "sessions_this_week":   sessions_week,
        "sessions_prev_week":   sessions_prev,
        "avg_duration_seconds": avg_dur,
        "completed_sessions":   completed,
        "completion_rate":      round(completed / total, 2) if total > 0 else 0.0,
        "top_corpus_name":      top_corpus[0] if top_corpus else None,
        "avg_score_this_week":  round(float(avg_score_week), 3) if avg_score_week else None,
        "avg_score_prev_week":  round(float(avg_score_prev), 3) if avg_score_prev else None,
    }


def get_activity_data(user_id: str, days: int = 56) -> pd.DataFrame:
    """Tentatives groupées par jour pour heatmap et courbe de score."""
    with sqlite3.connect(_db.DB_PATH) as conn:
        df = pd.read_sql_query(
            """
            SELECT DATE(created_at) AS day,
                   COUNT(*) AS n_attempts,
                   AVG(score) AS avg_score
            FROM attempts
            WHERE user_id = ? AND created_at >= datetime('now', ?)
            GROUP BY DATE(created_at)
            ORDER BY day
            """,
            conn,
            params=(user_id, f"-{days} days"),
        )
    conn.close()
    return df
