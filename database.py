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
        try:
            conn.execute("ALTER TABLE documents ADD COLUMN category TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute(
                "ALTER TABLE users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1"
            )
        except sqlite3.OperationalError:
            pass
        # ── Skills Engine V1.0 — tables additives ────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS skills (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                slug        TEXT    NOT NULL UNIQUE,
                label_fr    TEXT    NOT NULL,
                description TEXT,
                is_active   INTEGER NOT NULL DEFAULT 1,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chunk_skills (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                chunk_id     INTEGER NOT NULL REFERENCES chunks(id),
                skill_id     INTEGER NOT NULL REFERENCES skills(id),
                weight       REAL    NOT NULL DEFAULT 1.0,
                source       TEXT    NOT NULL DEFAULT 'keyword',
                is_validated INTEGER NOT NULL DEFAULT 0,
                is_active    INTEGER NOT NULL DEFAULT 1,
                validated_by TEXT,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(chunk_id, skill_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_skill_mastery (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id          TEXT    NOT NULL,
                skill_id         INTEGER NOT NULL REFERENCES skills(id),
                mastery_score    REAL    NOT NULL DEFAULT 0.0,
                attempts_count   INTEGER NOT NULL DEFAULT 0,
                last_reviewed_at TIMESTAMP,
                updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, skill_id)
            )
        """)
    conn.close()
    # Seed des 10 skills V1.0 — idempotent
    from db.skills import seed_skills as _seed_skills
    _seed_skills()
    logger.info("init_db: ready (%s)", DB_PATH)


# ── Re-exports — backward compatibility totale ────────────────────────────────
# Tous les callers existants (`from database import X`) continuent à fonctionner.
# Les nouveaux callers peuvent importer directement depuis db/analytics, db/chunks, etc.

from db.analytics import (                                          # noqa: E402
    save_attempt,
    get_attempts,
    get_attempts_count,
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
    get_chunk_by_id,
)
from db.profile import (                                            # noqa: E402
    get_learning_profile,
    compute_and_save_learning_profile,
    get_next_session_plan,
    get_retention_metrics,
)
from db.admin import (                                              # noqa: E402
    count_admins, get_all_users, set_user_role, set_user_active,
    get_platform_stats, get_document_admin_stats, get_system_alerts,
)
from db.skills import (                                             # noqa: E402
    seed_skills,
    get_all_skills,
    get_skill_by_slug,
    get_chunk_skills,
    classify_and_save_document_skills,
    remap_document_skills,
    remap_all_documents,
    get_user_skill_mastery,
    update_user_skill_mastery,
)
from engine.skill_engine import classify_skill_mastery             # noqa: E402

__all__ = [
    # Infrastructure
    "DB_PATH", "init_db",
    # Adaptive engine re-exports (backward compat)
    "REVIEW_INTERVALS", "_PEDAGOGY_GROUPS", "_adaptive_interval", "classify_mastery",
    "compute_momentum", "compute_learning_velocity", "compute_consistency_score",
    "build_session_plan", "compute_retention_metrics",
    # Analytics
    "save_attempt", "get_attempts", "get_attempts_count", "get_score_evolution",
    "get_error_frequency", "get_topic_stats",
    # Documents & Chunks
    "save_document", "save_chunks", "update_chunk_embedding", "get_chunks_for_reindex",
    "has_documents", "get_documents", "get_chunk_stats", "get_chunk_question_history",
    "get_chunk_mastery", "get_revision_suggestion", "get_document_by_id", "get_chunk_by_id",
    # Profil
    "get_learning_profile", "compute_and_save_learning_profile",
    "get_next_session_plan", "get_retention_metrics",
    # Admin
    "count_admins", "get_all_users", "set_user_role", "set_user_active",
    "get_platform_stats", "get_document_admin_stats", "get_system_alerts",
    # Skills Engine V1.0
    "seed_skills", "get_all_skills", "get_skill_by_slug",
    "get_chunk_skills", "classify_and_save_document_skills",
    "get_user_skill_mastery", "update_user_skill_mastery",
    "classify_skill_mastery",
    # Skills Engine V1.1
    "remap_document_skills", "remap_all_documents",
]
