"""
Tentatives & Analytics — lecture/écriture des tentatives utilisateur.
Utilise database.DB_PATH via import tardif pour respecter le monkey-patch des tests.
"""
import logging
import sqlite3
from typing import Optional

import database as _db
import pandas as pd

logger = logging.getLogger(__name__)


def _normalize_topic(topic: Optional[str]) -> Optional[str]:
    if not topic or not topic.strip():
        return topic
    return topic.strip().capitalize()


def _doc_filter(document_ids: Optional[list[int]]) -> tuple[str, list]:
    """Retourne (clause SQL, params) pour filtrer par document_ids. Vide si None."""
    if not document_ids:
        return "", []
    ph = ",".join("?" * len(document_ids))
    return f" AND document_id IN ({ph})", list(document_ids)


def save_attempt(
    question: str,
    user_answer: str,
    expected_answer: str,
    correction: str,
    score: float,
    response_time_seconds: Optional[float] = None,
    error_type: Optional[str] = None,
    topic: Optional[str] = None,
    pedagogy_type: Optional[str] = None,
    document_id: Optional[int] = None,
    chunk_id: Optional[int] = None,
    user_id: str = "default",
) -> Optional[int]:
    """Enregistre une tentative et retourne son ID (lastrowid)."""
    topic = _normalize_topic(topic)
    with sqlite3.connect(_db.DB_PATH) as conn:
        cur = conn.execute(
            """
            INSERT INTO attempts
                (user_id, question, user_answer, expected_answer, correction, score,
                 response_time_seconds, error_type, topic, pedagogy_type,
                 document_id, chunk_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, question, user_answer, expected_answer, correction, score,
             response_time_seconds, error_type, topic, pedagogy_type,
             document_id, chunk_id),
        )
        attempt_id = cur.lastrowid
    conn.close()
    return attempt_id


def save_attempt_feedback(attempt_id: int, feedback: int) -> None:
    """Enregistre le feedback qualitatif (1=pertinent, 0=non_pertinent) sur une tentative."""
    with sqlite3.connect(_db.DB_PATH) as conn:
        conn.execute(
            "UPDATE attempts SET question_feedback = ? WHERE id = ?",
            (feedback, attempt_id),
        )
    conn.close()


def get_last_attempt_id(user_id: str) -> Optional[int]:
    """Retourne l'ID de la dernière tentative de l'utilisateur, ou None."""
    with sqlite3.connect(_db.DB_PATH) as conn:
        row = conn.execute(
            "SELECT id FROM attempts WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,),
        ).fetchone()
    conn.close()
    return int(row[0]) if row else None


def get_attempts_count(user_id: str = "default", document_ids: Optional[list[int]] = None) -> int:
    _clause, _params = _doc_filter(document_ids)
    sql = f"SELECT COUNT(*) FROM attempts WHERE user_id = ?{_clause}"
    with sqlite3.connect(_db.DB_PATH) as conn:
        row = conn.execute(sql, (user_id, *_params)).fetchone()
    conn.close()
    return int(row[0]) if row else 0


def get_attempts(
    user_id: str = "default",
    limit: Optional[int] = None,
    document_ids: Optional[list[int]] = None,
) -> pd.DataFrame:
    _clause, _params = _doc_filter(document_ids)
    sql = f"SELECT * FROM attempts WHERE user_id = ?{_clause} ORDER BY created_at DESC"
    params: list = [user_id, *_params]
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)
    with sqlite3.connect(_db.DB_PATH) as conn:
        df = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df


def get_score_evolution(
    limit: int = 20,
    user_id: str = "default",
    document_ids: Optional[list[int]] = None,
) -> pd.DataFrame:
    _clause, _params = _doc_filter(document_ids)
    with sqlite3.connect(_db.DB_PATH) as conn:
        df = pd.read_sql_query(
            f"""
            SELECT id, score, created_at
            FROM attempts
            WHERE score IS NOT NULL
              AND user_id = ?{_clause}
            ORDER BY created_at DESC
            LIMIT ?
            """,
            conn,
            params=(user_id, *_params, limit),
        )
    conn.close()
    return df.iloc[::-1].reset_index(drop=True)


def get_error_frequency(
    user_id: str = "default",
    document_ids: Optional[list[int]] = None,
) -> pd.DataFrame:
    _clause, _params = _doc_filter(document_ids)
    with sqlite3.connect(_db.DB_PATH) as conn:
        df = pd.read_sql_query(
            f"""
            SELECT error_type, COUNT(*) as count
            FROM attempts
            WHERE error_type IS NOT NULL
              AND error_type != ''
              AND error_type != 'correct'
              AND error_type != 'non_evaluable'
              AND user_id = ?{_clause}
            GROUP BY error_type
            ORDER BY count DESC
            """,
            conn,
            params=(user_id, *_params),
        )
    conn.close()
    return df


def get_topic_stats(
    user_id: str = "default",
    document_ids: Optional[list[int]] = None,
) -> pd.DataFrame:
    _clause, _params = _doc_filter(document_ids)
    with sqlite3.connect(_db.DB_PATH) as conn:
        df = pd.read_sql_query(
            f"""
            SELECT
                MIN(topic)           AS topic,
                ROUND(AVG(score), 2) AS avg_score,
                COUNT(*)             AS attempts
            FROM attempts
            WHERE topic IS NOT NULL AND topic != ''
              AND score IS NOT NULL
              AND user_id = ?{_clause}
            GROUP BY LOWER(TRIM(topic))
            ORDER BY avg_score ASC
            """,
            conn,
            params=(user_id, *_params),
        )
    conn.close()
    return df
