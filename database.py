import sqlite3
import struct
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

DB_PATH = Path("database.db")

# Intervalles de répétition espacée par classe de maîtrise (en jours).
# Valeurs dupliquées dans get_revision_suggestion() ORDER BY (SQLite datetime inline).
# Toute modification ici doit être répercutée dans la requête SQL.
REVIEW_INTERVALS = {
    "Fragile":          1,
    "En consolidation": 3,
    "Maîtrisé":         7,
}


def _normalize_topic(topic: str | None) -> str | None:
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


def save_attempt(
    question: str,
    user_answer: str,
    expected_answer: str,
    correction: str,
    score: float,
    response_time_seconds: float = None,
    error_type: str = None,
    topic: str = None,
    pedagogy_type: str = None,
    document_id: int = None,
    chunk_id: int = None,
):
    topic = _normalize_topic(topic)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO attempts
                (question, user_answer, expected_answer, correction, score,
                 response_time_seconds, error_type, topic, pedagogy_type,
                 document_id, chunk_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (question, user_answer, expected_answer, correction, score,
             response_time_seconds, error_type, topic, pedagogy_type,
             document_id, chunk_id),
        )


def get_attempts() -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(
            "SELECT * FROM attempts ORDER BY created_at DESC", conn
        )
    return df


def get_score_evolution(limit: int = 20) -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(
            """
            SELECT id, score, created_at
            FROM attempts
            WHERE score IS NOT NULL
            ORDER BY created_at DESC
            LIMIT ?
            """,
            conn,
            params=(limit,),
        )
    return df.iloc[::-1].reset_index(drop=True)


def get_error_frequency() -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(
            """
            SELECT error_type, COUNT(*) as count
            FROM attempts
            WHERE error_type IS NOT NULL
              AND error_type != ''
              AND error_type != 'correct'
            GROUP BY error_type
            ORDER BY count DESC
            """,
            conn,
        )
    return df


def get_topic_stats() -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(
            """
            SELECT
                MIN(topic)           AS topic,
                ROUND(AVG(score), 2) AS avg_score,
                COUNT(*)             AS attempts
            FROM attempts
            WHERE topic IS NOT NULL AND topic != ''
            GROUP BY LOWER(TRIM(topic))
            ORDER BY avg_score ASC
            """,
            conn,
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
        return cur.lastrowid


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


def get_chunk_stats() -> pd.DataFrame:
    """
    Agrège les tentatives par chunk source (chunk_id IS NOT NULL = mode RAG uniquement).
    Retourne un DataFrame trié par avg_score ASC (chunks les plus fragiles en premier).
    """
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(
            """
            SELECT
                a.chunk_id,
                COALESCE(c.section_title, 'Chunk #' || c.chunk_index) AS section_label,
                d.title  AS document_title,
                ROUND(AVG(a.score), 2) AS avg_score,
                COUNT(*)               AS attempts_count,
                (
                    SELECT a2.error_type
                    FROM attempts a2
                    WHERE a2.chunk_id = a.chunk_id
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
            GROUP BY a.chunk_id
            ORDER BY avg_score ASC
            """,
            conn,
        )
    return df


def classify_mastery(df: pd.DataFrame) -> pd.DataFrame:
    """
    Enrichit un DataFrame issu de get_chunk_stats() avec deux colonnes :
    - mastery_class : 'Fragile' | 'En consolidation' | 'Maîtrisé'
    - trend         : 'Amélioration' | 'Stable' | 'Dégradation' | 'N/A'

    Règles de classification :
    - Maîtrisé       : avg_score >= 0.8 ET attempts_count >= 3
    - Fragile        : avg_score < 0.6  (quel que soit le nombre de tentatives)
    - En consolidation : tout le reste

    Règles de tendance (uniquement si attempts_count >= 2) :
    - Amélioration : last_score > avg_score + 0.1
    - Dégradation  : last_score < avg_score - 0.1
    - Stable       : écart <= 0.1
    - N/A          : une seule tentative ou last_score absent
    """
    def _class(row):
        if row["avg_score"] < 0.6:
            return "Fragile"
        if row["avg_score"] >= 0.8 and row["attempts_count"] >= 3:
            return "Maîtrisé"
        return "En consolidation"

    def _trend(row):
        if row["attempts_count"] < 2 or pd.isna(row["last_score"]):
            return "N/A"
        delta = float(row["last_score"]) - float(row["avg_score"])
        if delta > 0.1:
            return "Amélioration"
        if delta < -0.1:
            return "Dégradation"
        return "Stable"

    def _next_review(row):
        try:
            last_dt = datetime.fromisoformat(str(row["last_attempt_date"]))
            days    = REVIEW_INTERVALS.get(row["mastery_class"], 3)
            return last_dt + timedelta(days=days)
        except Exception:
            return None

    def _days_until(row):
        if row["next_review"] is None:
            return None
        return (row["next_review"].date() - datetime.now().date()).days

    def _review_status(row):
        d = row["days_until_review"]
        if d is None:
            return "—"
        if d < 0:
            return "En retard"
        if d == 0:
            return "Aujourd'hui"
        return f"Dans {d} jour{'s' if d > 1 else ''}"

    df = df.copy()
    df["mastery_class"]    = df.apply(_class, axis=1)
    df["trend"]            = df.apply(_trend, axis=1)
    df["next_review"]      = df.apply(_next_review, axis=1)
    df["days_until_review"] = df.apply(_days_until, axis=1)
    df["review_status"]    = df.apply(_review_status, axis=1)
    return df


def get_chunk_question_history(chunk_id: int, limit: int = 5) -> list[dict]:
    """
    Retourne les dernières tentatives pour un chunk donné.
    Lit pedagogy_type comme question_type (colonne réutilisée sans migration).
    Retourne [] si chunk inconnu ou aucun historique.
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT question, pedagogy_type AS question_type
            FROM attempts
            WHERE chunk_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (chunk_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def get_revision_suggestion() -> dict | None:
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
                COALESCE(c.section_title, 'Chunk #' || c.chunk_index) AS section_label,
                d.title                AS document_title,
                ROUND(AVG(a.score), 2) AS avg_score,
                COUNT(*)               AS attempts_count,
                MAX(a.created_at)      AS last_attempt_date
            FROM attempts a
            JOIN chunks    c ON a.chunk_id    = c.id
            JOIN documents d ON c.document_id = d.id
            WHERE a.chunk_id IS NOT NULL
              AND a.score    IS NOT NULL
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
            """
        ).fetchone()
    return dict(row) if row else None


def get_document_by_id(doc_id: int) -> dict | None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
    return dict(row) if row else None


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Similarité cosinus entre deux vecteurs — calcul pur Python, sans numpy."""
    dot   = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _blob_to_vector(blob: bytes) -> list[float]:
    """Désérialise un BLOB SQLite en vecteur de floats (float32, little-endian)."""
    n = len(blob) // 4  # chaque float32 = 4 octets
    return list(struct.unpack(f"<{n}f", blob))


def search_similar_chunks(
    query_embedding: list[float],
    document_id: int,
    top_k: int = 3,
) -> list[dict]:
    """
    Retourne les top_k chunks du document les plus proches de query_embedding.
    Ne renvoie que les chunks qui ont un embedding stocké.
    Résultats triés par similarité décroissante.
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, chunk_index, section_title, chunk_text, char_count, embedding
            FROM chunks
            WHERE document_id = ? AND embedding IS NOT NULL
            """,
            (document_id,),
        ).fetchall()

    if not rows:
        return []

    scored = []
    for row in rows:
        vec  = _blob_to_vector(row["embedding"])
        sim  = _cosine_similarity(query_embedding, vec)
        scored.append({
            "id":            row["id"],
            "chunk_index":   row["chunk_index"],
            "section_title": row["section_title"],
            "chunk_text":    row["chunk_text"],
            "char_count":    row["char_count"],
            "similarity":    sim,
        })

    scored.sort(key=lambda x: x["similarity"], reverse=True)
    return scored[:top_k]
