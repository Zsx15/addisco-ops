"""
Documents & Chunks — ingestion, indexation, retrieval, maîtrise.
Utilise database.DB_PATH via import tardif pour respecter le monkey-patch des tests.
"""
import logging
import sqlite3
from typing import Optional

import database as _db
import pandas as pd
from engine.thresholds import (
    MASTERY_FRAGILE,
    MASTERY_MASTERED,
    MASTERY_MIN_ATTEMPTS,
    REVIEW_INTERVALS,
)

logger = logging.getLogger(__name__)


def save_document(
    title: str,
    source_type: str,
    filename: str,
    raw_text: str,
    cleaned_text: str,
    category: Optional[str] = None,
) -> int:
    _cat = category.strip() if category and category.strip() else None
    with sqlite3.connect(_db.DB_PATH) as conn:
        cur = conn.execute(
            """
            INSERT INTO documents
                (title, source_type, filename, raw_text, cleaned_text, char_count, category)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (title, source_type, filename, raw_text, cleaned_text, len(cleaned_text), _cat),
        )
        doc_id = cur.lastrowid
    conn.close()
    logger.info("save_document: id=%d title=%r source=%s category=%r", doc_id, title, source_type, _cat)
    return doc_id


def save_chunks(document_id: int, chunks: list[dict]) -> None:
    rows = [
        (
            document_id,
            c["chunk_index"],
            c.get("section_title"),
            c["chunk_text"],
            c["char_count"],
            c.get("embedding_id"),
            c.get("embedding"),
        )
        for c in chunks
    ]
    with sqlite3.connect(_db.DB_PATH) as conn:
        conn.executemany(
            """
            INSERT INTO chunks
                (document_id, chunk_index, section_title, chunk_text, char_count, embedding_id, embedding)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
    conn.close()


def update_chunk_embedding(chunk_id: int, embedding: bytes) -> None:
    """UPDATE ciblé — la clé primaire chunk.id reste stable (invariant attempts.chunk_id)."""
    with sqlite3.connect(_db.DB_PATH) as conn:
        conn.execute(
            "UPDATE chunks SET embedding = ? WHERE id = ?",
            (embedding, chunk_id),
        )
    conn.close()


def get_chunks_for_reindex(document_id: int) -> list[dict]:
    """Retourne uniquement les chunks sans embedding (idempotence garantie)."""
    with sqlite3.connect(_db.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, chunk_index, chunk_text
            FROM chunks
            WHERE document_id = ? AND embedding IS NULL
            """,
            (document_id,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def has_documents() -> bool:
    with sqlite3.connect(_db.DB_PATH) as conn:
        count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    conn.close()
    return count > 0


def get_documents() -> pd.DataFrame:
    with sqlite3.connect(_db.DB_PATH) as conn:
        df = pd.read_sql_query(
            """
            SELECT
                d.id,
                d.title,
                d.source_type,
                d.filename,
                d.char_count,
                d.created_at,
                d.category,
                COUNT(c.id) AS chunk_count,
                SUM(CASE WHEN c.embedding IS NULL THEN 1 ELSE 0 END) AS chunks_missing_embedding
            FROM documents d
            LEFT JOIN chunks c ON c.document_id = d.id
            GROUP BY d.id
            ORDER BY d.created_at DESC
            """,
            conn,
        )
    conn.close()
    return df


def get_chunk_stats(user_id: str = "default") -> pd.DataFrame:
    """Agrège les tentatives par chunk source (mode RAG uniquement)."""
    with sqlite3.connect(_db.DB_PATH) as conn:
        df = pd.read_sql_query(
            """
            SELECT
                a.chunk_id,
                COALESCE(c.section_title, 'Section ' || (c.chunk_index + 1)) AS section_label,
                d.title  AS document_title,
                ROUND(AVG(a.score), 2) AS avg_score,
                COUNT(*)               AS attempts_count,
                (
                    SELECT a2.error_type
                    FROM attempts a2
                    WHERE a2.chunk_id = a.chunk_id
                      AND a2.user_id = a.user_id
                      AND a2.error_type IS NOT NULL
                      AND a2.error_type != ''
                      AND a2.error_type != 'correct'
                      AND a2.error_type != 'non_evaluable'
                    GROUP BY a2.error_type
                    ORDER BY COUNT(*) DESC
                    LIMIT 1
                ) AS dominant_error_type,
                (
                    SELECT a3.score
                    FROM attempts a3
                    WHERE a3.chunk_id = a.chunk_id
                      AND a3.user_id = a.user_id
                      AND a3.score IS NOT NULL
                    ORDER BY a3.created_at DESC
                    LIMIT 1
                ) AS last_score,
                MAX(a.created_at) AS last_attempt_date
            FROM attempts a
            JOIN chunks    c ON a.chunk_id     = c.id
            JOIN documents d ON c.document_id  = d.id
            WHERE a.chunk_id IS NOT NULL
              AND a.score    IS NOT NULL
              AND a.user_id  = ?
            GROUP BY a.chunk_id
            ORDER BY avg_score ASC
            """,
            conn,
            params=(user_id,),
        )
    conn.close()
    return df


def get_chunk_question_history(
    chunk_id: int, limit: int = 5, user_id: str = "default"
) -> list[dict]:
    """Lit pedagogy_type comme question_type (colonne réutilisée sans migration)."""
    with sqlite3.connect(_db.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT question, pedagogy_type AS question_type, score, error_type
            FROM attempts
            WHERE chunk_id = ? AND user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (chunk_id, user_id, limit),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_chunk_mastery(chunk_id: int, user_id: str = "default") -> Optional[str]:
    with sqlite3.connect(_db.DB_PATH) as conn:
        row = conn.execute(
            """
            SELECT ROUND(AVG(score), 2), COUNT(*)
            FROM attempts
            WHERE chunk_id = ? AND score IS NOT NULL AND user_id = ?
            """,
            (chunk_id, user_id),
        ).fetchone()
    conn.close()
    if not row or row[1] < 1:
        return None
    avg, n = row
    if avg < MASTERY_FRAGILE:
        return "Fragile"
    if avg >= MASTERY_MASTERED and n >= MASTERY_MIN_ATTEMPTS:
        return "Maîtrisé"
    return "En consolidation"


def get_revision_suggestion(user_id: str = "default") -> Optional[dict]:
    _frag        = MASTERY_FRAGILE
    _mast        = MASTERY_MASTERED
    _mast_n      = MASTERY_MIN_ATTEMPTS
    _frag_days   = REVIEW_INTERVALS["Fragile"]
    _consol_days = REVIEW_INTERVALS["En consolidation"]
    with sqlite3.connect(_db.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            f"""
            SELECT
                c.id       AS chunk_id,
                c.chunk_text,
                c.document_id,
                COALESCE(c.section_title, 'Section ' || (c.chunk_index + 1)) AS section_label,
                d.title                AS document_title,
                ROUND(AVG(a.score), 2) AS avg_score,
                COUNT(*)               AS attempts_count,
                MAX(a.created_at)      AS last_attempt_date
            FROM attempts a
            JOIN chunks    c ON a.chunk_id    = c.id
            JOIN documents d ON c.document_id = d.id
            WHERE a.chunk_id IS NOT NULL
              AND a.score    IS NOT NULL
              AND a.user_id  = ?
            GROUP BY a.chunk_id
            HAVING NOT (ROUND(AVG(a.score), 2) >= {_mast} AND COUNT(*) >= {_mast_n})
            ORDER BY
                CASE
                    WHEN ROUND(AVG(a.score), 2) < {_frag}
                         AND datetime(MAX(a.created_at), '+{_frag_days} days') <= datetime('now') THEN 0
                    WHEN ROUND(AVG(a.score), 2) >= {_frag}
                         AND datetime(MAX(a.created_at), '+{_consol_days} days') <= datetime('now') THEN 0
                    ELSE 1
                END ASC,
                CASE WHEN ROUND(AVG(a.score), 2) < {_frag} THEN 0 ELSE 1 END ASC,
                MAX(a.created_at) ASC,
                ROUND(AVG(a.score), 2) ASC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_document_by_id(doc_id: int) -> Optional[dict]:
    with sqlite3.connect(_db.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_chunk_by_id(chunk_id: int) -> Optional[dict]:
    """Retourne les métadonnées d'un chunk avec son document source.
    Utilisé par l'UI pour afficher le contexte RAG après génération.
    """
    with sqlite3.connect(_db.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT
                c.id,
                c.chunk_text,
                COALESCE(c.section_title, 'Section ' || (c.chunk_index + 1)) AS section_label,
                c.chunk_index,
                d.id    AS document_id,
                d.title AS document_title
            FROM chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE c.id = ?
            """,
            (chunk_id,),
        ).fetchone()
    conn.close()
    return dict(row) if row else None
