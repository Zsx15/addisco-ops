import logging
import os
import sqlite3
from pathlib import Path
from typing import Optional

from adaptive_engine import (
    REVIEW_INTERVALS, _PEDAGOGY_GROUPS, _adaptive_interval, classify_mastery,
    compute_momentum, compute_learning_velocity, compute_consistency_score,
    build_session_plan, compute_retention_metrics,
)

logger = logging.getLogger(__name__)

# DB_PATH doit être défini ICI — les tests le patchent via `database.DB_PATH = tmp`.
# Les sous-modules (db/) accèdent à cette valeur via `import database; database.DB_PATH`.
DB_PATH = Path(os.getenv("DB_PATH", "database.db"))


# ── Infrastructure & initialisation ──────────────────────────────────────────


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT DEFAULT 'default',
                document_id INTEGER,
                question TEXT NOT NULL,
                user_answer TEXT,
                expected_answer TEXT,
                correction TEXT,
                score REAL,
                error_type TEXT,
                topic TEXT,
                pedagogy_type TEXT,
                response_time_seconds REAL,
                success_after_retry INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                source_type TEXT NOT NULL,
                filename TEXT,
                raw_text TEXT,
                cleaned_text TEXT,
                char_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL REFERENCES documents(id),
                chunk_index INTEGER NOT NULL,
                section_title TEXT,
                chunk_text TEXT NOT NULL,
                char_count INTEGER,
                embedding_id TEXT,
                embedding BLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_learning_profile (
                user_id            TEXT PRIMARY KEY,
                preferred_pedagogy TEXT,
                logical_score      REAL DEFAULT 0.0,
                procedural_score   REAL DEFAULT 0.0,
                narrative_score    REAL DEFAULT 0.0,
                analogy_score      REAL DEFAULT 0.0,
                average_score      REAL DEFAULT 0.0,
                fragile_topics     TEXT,
                updated_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id       TEXT PRIMARY KEY,
                username      TEXT NOT NULL UNIQUE,
                password_hash TEXT,
                role          TEXT NOT NULL DEFAULT 'apprenant',
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Migrations douces : ALTER TABLE ADD COLUMN échoue si la colonne existe → ignoré
        try:
            conn.execute("ALTER TABLE chunks ADD COLUMN embedding BLOB")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute(
                "ALTER TABLE attempts ADD COLUMN chunk_id INTEGER REFERENCES chunks(id)"
            )
        except sqlite3.OperationalError:
            pass
        for _col in ("momentum", "learning_velocity", "consistency_score"):
            try:
                conn.execute(
                    f"ALTER TABLE user_learning_profile ADD COLUMN {_col} REAL DEFAULT 0"
                )
            except sqlite3.OperationalError:
                pass
    logger.info("init_db: ready (%s)", DB_PATH)


# ── Re-exports — backward compatibility totale ────────────────────────────────
# Tous les callers existants (`from database import X`) continuent à fonctionner.
# Les nouveaux callers peuvent importer directement depuis db/analytics, db/chunks, etc.

from db.analytics import (                                          # noqa: E402
    save_attempt,
    get_attempts,
    get_score_evolution,
    get_error_frequency,
    get_topic_stats,
)
from db.chunks import (                                             # noqa: E402
    save_document,
    save_chunks,
    update_chunk_embedding,
    get_chunks_for_reindex,
    has_documents,
    get_documents,
    get_chunk_stats,
    get_chunk_question_history,
    get_chunk_mastery,
    get_revision_suggestion,
    get_document_by_id,
)
from db.profile import (                                            # noqa: E402
    get_learning_profile,
    compute_and_save_learning_profile,
    get_next_session_plan,
    get_retention_metrics,
)
from db.admin import count_admins, get_all_users, set_user_role    # noqa: E402

__all__ = [
    # Infrastructure
    "DB_PATH", "init_db",
    # Adaptive engine re-exports (backward compat)
    "REVIEW_INTERVALS", "_PEDAGOGY_GROUPS", "_adaptive_interval", "classify_mastery",
    "compute_momentum", "compute_learning_velocity", "compute_consistency_score",
    "build_session_plan", "compute_retention_metrics",
    # Analytics
    "save_attempt", "get_attempts", "get_score_evolution",
    "get_error_frequency", "get_topic_stats",
    # Documents & Chunks
    "save_document", "save_chunks", "update_chunk_embedding", "get_chunks_for_reindex",
    "has_documents", "get_documents", "get_chunk_stats", "get_chunk_question_history",
    "get_chunk_mastery", "get_revision_suggestion", "get_document_by_id",
    # Profil
    "get_learning_profile", "compute_and_save_learning_profile",
    "get_next_session_plan", "get_retention_metrics",
    # Admin
    "count_admins", "get_all_users", "set_user_role",
]
