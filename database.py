import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
from adaptive_engine import (
    REVIEW_INTERVALS, _PEDAGOGY_GROUPS, _adaptive_interval, classify_mastery,
    compute_momentum, compute_learning_velocity, compute_consistency_score,
    build_session_plan, compute_retention_metrics,
)

logger = logging.getLogger(__name__)

DB_PATH = Path(os.getenv("DB_PATH", "database.db"))


def _normalize_topic(topic: Optional[str]) -> Optional[str]:
    if not topic or not topic.strip():
        return topic
    return topic.strip().capitalize()


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
    with sqlite3.connect(DB_PATH) as conn:
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


def get_attempts(user_id: str = "default") -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(
            "SELECT * FROM attempts WHERE user_id = ? ORDER BY created_at DESC",
            conn,
            params=(user_id,),
        )
    return df


def get_score_evolution(limit: int = 20, user_id: str = "default") -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
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
    with sqlite3.connect(DB_PATH) as conn:
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
    with sqlite3.connect(DB_PATH) as conn:
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


def save_document(
    title: str,
    source_type: str,
    filename: str,
    raw_text: str,
    cleaned_text: str,
) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            """
            INSERT INTO documents (title, source_type, filename, raw_text, cleaned_text, char_count)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (title, source_type, filename, raw_text, cleaned_text, len(cleaned_text)),
        )
        doc_id = cur.lastrowid
    logger.info("save_document: id=%d title=%r source=%s", doc_id, title, source_type)
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
            c.get("embedding"),   # BLOB sérialisé — None si embedding non calculé
        )
        for c in chunks
    ]
    with sqlite3.connect(DB_PATH) as conn:
        conn.executemany(
            """
            INSERT INTO chunks
                (document_id, chunk_index, section_title, chunk_text, char_count, embedding_id, embedding)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )


def update_chunk_embedding(chunk_id: int, embedding: bytes) -> None:
    """
    Met à jour uniquement la colonne embedding d'un chunk existant (UPDATE, jamais DELETE+INSERT).
    La clé primaire chunk.id reste stable — essentielle pour la future relation attempts.chunk_id.
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE chunks SET embedding = ? WHERE id = ?",
            (embedding, chunk_id),
        )


def get_chunks_for_reindex(document_id: int) -> list[dict]:
    """
    Retourne uniquement les chunks sans embedding pour un document donné.
    WHERE embedding IS NULL : garantit qu'aucun chunk déjà indexé n'est retouché,
    ce qui rend reindex_document() idempotente et évite tout retraitement inutile.
    Les IDs retournés sont stables — ils seront utilisés tels quels dans update_chunk_embedding().
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, chunk_index, chunk_text
            FROM chunks
            WHERE document_id = ? AND embedding IS NULL
            """,
            (document_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def has_documents() -> bool:
    """Retourne True si au moins un document existe en base."""
    with sqlite3.connect(DB_PATH) as conn:
        count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    return count > 0


def get_documents() -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(
            """
            SELECT
                d.id,
                d.title,
                d.source_type,
                d.filename,
                d.char_count,
                d.created_at,
                COUNT(c.id) AS chunk_count,
                SUM(CASE WHEN c.embedding IS NULL THEN 1 ELSE 0 END) AS chunks_missing_embedding
            FROM documents d
            LEFT JOIN chunks c ON c.document_id = d.id
            GROUP BY d.id
            ORDER BY d.created_at DESC
            """,
            conn,
        )
    return df


def get_chunk_stats(user_id: str = "default") -> pd.DataFrame:
    """
    Agrège les tentatives par chunk source (chunk_id IS NOT NULL = mode RAG uniquement).
    Retourne un DataFrame trié par avg_score ASC (chunks les plus fragiles en premier).
    """
    with sqlite3.connect(DB_PATH) as conn:
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
    return df


def get_chunk_question_history(
    chunk_id: int, limit: int = 5, user_id: str = "default"
) -> list[dict]:
    """
    Retourne les dernières tentatives pour un chunk donné, filtrées par user_id.
    Lit pedagogy_type comme question_type (colonne réutilisée sans migration).
    Retourne [] si chunk inconnu ou aucun historique.
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT question, pedagogy_type AS question_type
            FROM attempts
            WHERE chunk_id = ? AND user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (chunk_id, user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def get_chunk_mastery(chunk_id: int, user_id: str = "default") -> Optional[str]:
    """
    Retourne la classe de maîtrise d'un chunk (Fragile / En consolidation / Maîtrisé)
    ou None si pas assez de données. Même règles que classify_mastery().
    """
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            """
            SELECT ROUND(AVG(score), 2), COUNT(*)
            FROM attempts
            WHERE chunk_id = ? AND score IS NOT NULL AND user_id = ?
            """,
            (chunk_id, user_id),
        ).fetchone()
    if not row or row[1] < 1:
        return None
    avg, n = row
    if avg < 0.6:
        return "Fragile"
    if avg >= 0.8 and n >= 3:
        return "Maîtrisé"
    return "En consolidation"


def get_revision_suggestion(user_id: str = "default") -> Optional[dict]:
    """
    Retourne le chunk le plus prioritaire à réviser, ou None si aucun chunk éligible.

    Priorité :
    1. Fragile (avg_score < 0.6) avant En consolidation
    2. Tentative la plus ancienne (last_attempt_date ASC)
    3. Score le plus faible (avg_score ASC)

    Exclut les chunks Maîtrisés (avg_score >= 0.8 ET attempts_count >= 3).
    Mode RAG uniquement (chunk_id IS NOT NULL).
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
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
            HAVING NOT (ROUND(AVG(a.score), 2) >= 0.8 AND COUNT(*) >= 3)
            ORDER BY
                -- 1. Chunks en retard de révision d'abord
                --    Intervalles: Fragile=1j, En consolidation=3j (miroir de REVIEW_INTERVALS)
                CASE
                    WHEN ROUND(AVG(a.score), 2) < 0.6
                         AND datetime(MAX(a.created_at), '+1 day')  <= datetime('now') THEN 0
                    WHEN ROUND(AVG(a.score), 2) >= 0.6
                         AND datetime(MAX(a.created_at), '+3 days') <= datetime('now') THEN 0
                    ELSE 1
                END ASC,
                -- 2. Fragile avant En consolidation
                CASE WHEN ROUND(AVG(a.score), 2) < 0.6 THEN 0 ELSE 1 END ASC,
                -- 3. Tentative la plus ancienne
                MAX(a.created_at) ASC,
                -- 4. Score le plus faible
                ROUND(AVG(a.score), 2) ASC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
    return dict(row) if row else None


def get_document_by_id(doc_id: int) -> Optional[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
    return dict(row) if row else None


# ── Profil d'apprentissage utilisateur ───────────────────────────────────────


def get_learning_profile(user_id: str = "default") -> Optional[dict]:
    """Retourne le profil d'apprentissage d'un utilisateur, ou None s'il n'existe pas."""
    with sqlite3.connect(DB_PATH) as conn:
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
    Retourne le profil calculé.

    Scores par groupe pédagogique (voir _PEDAGOGY_GROUPS) :
    - logical     : question_directe
    - procedural  : cas_pratique, consequence
    - narrative   : reformulation
    - analogy     : vrai_faux, question_piege

    preferred_pedagogy : groupe avec le score moyen le plus élevé (min 1 tentative).
    fragile_topics     : notions avec avg_score < 0.6 (JSON array).

    Métriques adaptatives (TASK-049) :
    - momentum          : avg_score(7 derniers jours) − avg_score(7 jours précédents) ∈ [-1, 1]
    - learning_velocity : moyenne des deltas avg_score inter-sessions ∈ [-1, 1]
    - consistency_score : jours actifs / 30 sur les 30 derniers jours ∈ [0, 1]
    Toutes retournent 0.0 si les données sont insuffisantes.
    """
    with sqlite3.connect(DB_PATH) as conn:
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

        scored_groups = {
            g: _avg(v) for g, v in group_scores.items() if v
        }
        preferred_pedagogy = max(scored_groups, key=scored_groups.get) if scored_groups else None

        fragile_topics = sorted(
            t for t, s in topic_scores.items() if _avg(s) < 0.6
        )

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

    with sqlite3.connect(DB_PATH) as conn:
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

    return profile


# ── Plan de session adaptatif ─────────────────────────────────────────────────


def get_next_session_plan(user_id: str = "default", max_items: int = 5) -> list[dict]:
    """
    Retourne le plan de session personnalisé pour user_id :
    liste de max_items chunks ordonnés par priorité adaptative,
    avec durée estimée et objectif pédagogique par item.

    Retourne [] si aucun chunk n'a d'historique pour cet utilisateur.
    Délègue le scoring et le tri à adaptive_engine.build_session_plan().
    """
    df_stats = get_chunk_stats(user_id)
    if df_stats.empty:
        return []
    df_enriched = classify_mastery(df_stats)
    return build_session_plan(df_enriched, max_items=max_items)


# ── Métriques de rétention pédagogique ───────────────────────────────────────


def get_retention_metrics(user_id: str = "default") -> dict[str, Optional[float]]:
    """
    Retourne les métriques de rétention J+1/J+7/J+30 pour user_id.
    Calculées à la volée — non stockées en base.
    Délègue à adaptive_engine.compute_retention_metrics().
    """
    with sqlite3.connect(DB_PATH) as conn:
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


# ── Gestion des utilisateurs (admin) ─────────────────────────────────────────

def count_admins() -> int:
    """Retourne le nombre d'utilisateurs avec role='admin'."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM users WHERE role = 'admin'"
            ).fetchone()[0]
    except Exception:
        return 0


def get_all_users() -> list[dict]:
    """
    Retourne tous les utilisateurs sans password_hash.
    Tri : admin → formateur → apprenant, puis username ASC dans chaque groupe.
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT user_id, username, role, created_at
            FROM users
            ORDER BY
                CASE role
                    WHEN 'admin'     THEN 0
                    WHEN 'formateur' THEN 1
                    WHEN 'apprenant' THEN 2
                    ELSE 3
                END ASC,
                username ASC
            """
        ).fetchall()
    return [dict(r) for r in rows]


def set_user_role(username: str, new_role: str) -> None:
    """Modifie le rôle d'un utilisateur existant (UPDATE ciblé, jamais DELETE+INSERT)."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE users SET role = ? WHERE username = ?",
            (new_role, username),
        )
