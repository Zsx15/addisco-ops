"""
Corpus service — corpus personnalisés multi-documents.
Utilise database.DB_PATH via import tardif pour respecter le monkey-patch des tests.
"""
import sqlite3
from typing import Optional

import database as _db


def create_corpus(user_id: str, corpus_name: str, document_ids: list[int]) -> int:
    """Crée un corpus nommé et associe les documents. Retourne l'id du corpus créé."""
    corpus_name = corpus_name.strip()
    if not corpus_name:
        raise ValueError("Le nom du corpus ne peut pas être vide.")
    if not document_ids:
        raise ValueError("Un corpus doit contenir au moins un document.")
    with sqlite3.connect(_db.DB_PATH) as conn:
        cur = conn.execute(
            "INSERT INTO corpus (user_id, corpus_name) VALUES (?, ?)",
            (user_id, corpus_name),
        )
        corpus_id = cur.lastrowid
        conn.executemany(
            "INSERT OR IGNORE INTO corpus_documents (corpus_id, document_id) VALUES (?, ?)",
            [(corpus_id, doc_id) for doc_id in document_ids],
        )
    conn.close()
    return corpus_id


def get_user_corpus(user_id: str) -> list[dict]:
    """Retourne tous les corpus de l'utilisateur avec le nombre de documents."""
    with sqlite3.connect(_db.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT c.id, c.corpus_name, c.created_at,
                   COUNT(DISTINCT cd.document_id) AS n_docs,
                   COUNT(ch.id) AS n_chunks
            FROM corpus c
            LEFT JOIN corpus_documents cd ON cd.corpus_id = c.id
            LEFT JOIN chunks ch ON ch.document_id = cd.document_id
            WHERE c.user_id = ?
            GROUP BY c.id
            ORDER BY c.created_at DESC
            """,
            (user_id,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_corpus_documents(corpus_id: int) -> list[int]:
    """Retourne la liste des document_ids du corpus."""
    with sqlite3.connect(_db.DB_PATH) as conn:
        rows = conn.execute(
            "SELECT document_id FROM corpus_documents WHERE corpus_id = ?",
            (corpus_id,),
        ).fetchall()
    conn.close()
    return [r[0] for r in rows]


def get_corpus_by_id(corpus_id: int, user_id: Optional[str] = None) -> Optional[dict]:
    """Retourne les métadonnées d'un corpus (avec n_docs). Vérifie user_id si fourni."""
    sql = """
        SELECT c.id, c.corpus_name, c.created_at, c.user_id,
               COUNT(DISTINCT cd.document_id) AS n_docs,
               COUNT(ch.id) AS n_chunks
        FROM corpus c
        LEFT JOIN corpus_documents cd ON cd.corpus_id = c.id
        LEFT JOIN chunks ch ON ch.document_id = cd.document_id
        WHERE c.id = ?
    """
    params: list = [corpus_id]
    if user_id is not None:
        sql += " AND c.user_id = ?"
        params.append(user_id)
    sql += " GROUP BY c.id"
    with sqlite3.connect(_db.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(sql, params).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_corpus(corpus_id: int, user_id: str) -> bool:
    """Supprime un corpus et ses liens documents. Vérifie l'ownership. Retourne True si supprimé."""
    with sqlite3.connect(_db.DB_PATH) as conn:
        n = conn.execute(
            "DELETE FROM corpus WHERE id = ? AND user_id = ?",
            (corpus_id, user_id),
        ).rowcount
        if n:
            conn.execute(
                "DELETE FROM corpus_documents WHERE corpus_id = ?",
                (corpus_id,),
            )
    conn.close()
    return bool(n)
