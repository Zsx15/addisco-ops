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
            SELECT u.user_id, u.username, u.role,
                   COALESCE(u.is_active, 1) AS is_active,
                   u.created_at,
                   COUNT(a.id)       AS n_attempts,
                   MAX(a.created_at) AS last_attempt
            FROM users u
            LEFT JOIN attempts a ON a.user_id = u.user_id
            GROUP BY u.user_id, u.username, u.role, u.is_active, u.created_at
            ORDER BY
                CASE u.role
                    WHEN 'admin'     THEN 0
                    WHEN 'formateur' THEN 1
                    WHEN 'apprenant' THEN 2
                    ELSE 3
                END ASC,
                u.username ASC
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


def set_user_active(username: str, is_active: bool) -> None:
    """Active ou désactive un compte. UPDATE ciblé — jamais DELETE+INSERT."""
    with sqlite3.connect(_db.DB_PATH) as conn:
        conn.execute(
            "UPDATE users SET is_active = ? WHERE username = ?",
            (1 if is_active else 0, username),
        )
    logger.info("set_user_active: %s → is_active=%s", username, is_active)


def get_platform_stats() -> dict:
    """Stats globales de la plateforme — read-only."""
    with sqlite3.connect(_db.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        n_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        n_active_users = conn.execute(
            "SELECT COUNT(*) FROM users WHERE COALESCE(is_active, 1) = 1"
        ).fetchone()[0]
        n_docs = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        n_attempts = conn.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
        avg_score = conn.execute(
            "SELECT AVG(score) FROM attempts WHERE score IS NOT NULL"
        ).fetchone()[0]
    return {
        "n_users":        n_users,
        "n_active_users": n_active_users,
        "n_docs":         n_docs,
        "n_attempts":     n_attempts,
        "avg_score":      avg_score,
    }


def get_document_admin_stats() -> list[dict]:
    """Liste des documents avec nb chunks, nb attempts et score moyen — read-only."""
    with sqlite3.connect(_db.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT d.id, d.title, d.created_at,
                   COUNT(DISTINCT c.id)   AS n_chunks,
                   COUNT(a.id)            AS n_attempts,
                   AVG(a.score)           AS avg_score
            FROM   documents d
            LEFT   JOIN chunks  c ON c.document_id = d.id
            LEFT   JOIN attempts a ON a.chunk_id   = c.id
            GROUP  BY d.id, d.title, d.created_at
            ORDER  BY d.created_at DESC
            """
        ).fetchall()
    return [dict(r) for r in rows]


def get_system_alerts() -> dict:
    """
    Comptage rapide des anomalies système — read-only, sans appel API.
    Utilisé dans la vue admin pour afficher les alertes en temps réel.
    """
    with sqlite3.connect(_db.DB_PATH) as conn:
        # Chunks orphelins (aucun skill actif associé)
        orphan_chunks = conn.execute(
            """
            SELECT COUNT(*) FROM chunks c
            WHERE NOT EXISTS (
                SELECT 1 FROM chunk_skills cs
                WHERE cs.chunk_id = c.id AND cs.is_active = 1
            )
            """
        ).fetchone()[0]

        # Documents problématiques (avg_score < 0.45 avec >= 3 attempts)
        bad_docs = conn.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT d.id
                FROM   documents d
                JOIN   chunks  c ON c.document_id = d.id
                JOIN   attempts a ON a.chunk_id   = c.id
                GROUP  BY d.id
                HAVING COUNT(a.id) >= 3 AND AVG(a.score) < 0.45
            )
            """
        ).fetchone()[0]

        # Skills actifs mais sans aucun chunk associé
        dead_skills = conn.execute(
            """
            SELECT COUNT(*) FROM skills s
            WHERE s.is_active = 1
              AND NOT EXISTS (
                SELECT 1 FROM chunk_skills cs
                WHERE cs.skill_id = s.id AND cs.is_active = 1
              )
              AND NOT EXISTS (
                SELECT 1 FROM user_skill_mastery usm
                WHERE usm.skill_id = s.id
              )
            """
        ).fetchone()[0]

        # Comptes désactivés
        disabled_users = conn.execute(
            "SELECT COUNT(*) FROM users WHERE is_active = 0"
        ).fetchone()[0]

    return {
        "orphan_chunks":   orphan_chunks,
        "bad_docs":        bad_docs,
        "dead_skills":     dead_skills,
        "disabled_users":  disabled_users,
    }
