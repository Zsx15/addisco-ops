import sqlite3
import struct
from pathlib import Path
import pandas as pd

DB_PATH = Path("database.db")


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
        # Migration douce : ajoute la colonne embedding sur les bases existantes
        # ALTER TABLE ADD COLUMN échoue si la colonne existe déjà → on ignore l'erreur
        try:
            conn.execute("ALTER TABLE chunks ADD COLUMN embedding BLOB")
        except sqlite3.OperationalError:
            pass  # colonne déjà présente


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
):
    topic = _normalize_topic(topic)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO attempts
                (question, user_answer, expected_answer, correction, score,
                 response_time_seconds, error_type, topic, pedagogy_type, document_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (question, user_answer, expected_answer, correction, score,
             response_time_seconds, error_type, topic, pedagogy_type, document_id),
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
