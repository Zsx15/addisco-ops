"""
Gestion des utilisateurs — fonctions réservées aux administrateurs.
Utilise database.DB_PATH via import tardif pour respecter le monkey-patch des tests.
"""
import logging
import sqlite3

import database as _db

logger = logging.getLogger(__name__)


def count_admins() -> int:
    try:
        with sqlite3.connect(_db.DB_PATH) as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM users WHERE role = 'admin'"
            ).fetchone()[0]
    except Exception:
        return 0


def admin_exists() -> bool:
    """Vérifie qu'au moins un admin est enregistré en base. Read-only."""
    return count_admins() > 0


def get_all_users() -> list[dict]:
    """Retourne tous les utilisateurs (sans password_hash), triés par rôle puis username."""
    with sqlite3.connect(_db.DB_PATH) as conn:
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
    """UPDATE ciblé — jamais DELETE+INSERT."""
    with sqlite3.connect(_db.DB_PATH) as conn:
        conn.execute(
            "UPDATE users SET role = ? WHERE username = ?",
            (new_role, username),
        )
