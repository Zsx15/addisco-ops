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
):
    topic = _normalize_topic(topic)
    with sqlite3.connect(_db.DB_PATH) as conn:
        conn.execute(
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


def get_attempts_count(user_id: str = "default") -> int:
    with sqlite3.connect(_db.DB_PATH) as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM attempts WHERE user_id = ?", (user_id,)
        ).fetchone()
    return int(row[0]) if row else 0


def get_attempts(user_id: str = "default", limit: Optional[int] = None) -> pd.DataFrame:
    sql = "SELECT * FROM attempts WHERE user_id = ? ORDER BY created_at DESC"
    params: tuple = (user_id,)
    if limit is not None:
        sql += " LIMIT ?"
        params = (user_id, limit)
    with sqlite3.connect(_db.DB_PATH) as conn:
        df = pd.read_sql_query(sql, conn, params=params)
    return df


def get_score_evolution(limit: int = 20, user_id: str = "default") -> pd.DataFrame:
    with sqlite3.connect(_db.DB_PATH) as conn:
        df = pd.read_sql_query(
            """
            SELECT id, score, created_at
            FROM attempts
            WHERE score IS NOT NULL
              AND user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            conn,
            params=(user_id, limit),
        )
    return df.iloc[::-1].reset_index(drop=True)


def get_error_frequency(user_id: str = "default") -> pd.DataFrame:
    with sqlite3.connect(_db.DB_PATH) as conn:
        df = pd.read_sql_query(
            """
            SELECT error_type, COUNT(*) as count
            FROM attempts
            WHERE error_type IS NOT NULL
              AND error_type != ''
              AND error_type != 'correct'
              AND user_id = ?
            GROUP BY error_type
            ORDER BY count DESC
            """,
            conn,
            params=(user_id,),
        )
    return df


def get_topic_stats(user_id: str = "default") -> pd.DataFrame:
    with sqlite3.connect(_db.DB_PATH) as conn:
        df = pd.read_sql_query(
            """
            SELECT
                MIN(topic)           AS topic,
                ROUND(AVG(score), 2) AS avg_score,
                COUNT(*)             AS attempts
            FROM attempts
            WHERE topic IS NOT NULL AND topic != ''
              AND score IS NOT NULL
              AND user_id = ?
            GROUP BY LOWER(TRIM(topic))
            ORDER BY avg_score ASC
            """,
            conn,
            params=(user_id,),
        )
    return df
