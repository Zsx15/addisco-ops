"""Service d'authentification — hash/verify password, gestion table users."""
import sqlite3
import uuid
from typing import Optional

import bcrypt

import database


def register_user(
    username: str,
    password: str,
    role: str = "apprenant",
) -> str:
    """Crée un nouvel utilisateur. Retourne user_id (UUID). Lève ValueError si username déjà pris."""
    user_id = str(uuid.uuid4())
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    with sqlite3.connect(str(database.DB_PATH)) as conn:
        try:
            conn.execute(
                "INSERT INTO users (user_id, username, password_hash, role) VALUES (?, ?, ?, ?)",
                (user_id, username, password_hash, role),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"Nom d'utilisateur déjà pris : {username}") from exc
    return user_id


def get_user_by_username(username: str) -> Optional[dict]:
    """Retourne le dict utilisateur complet ou None si introuvable."""
    with sqlite3.connect(str(database.DB_PATH)) as conn:
        row = conn.execute(
            "SELECT user_id, username, password_hash, role, created_at "
            "FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    if row is None:
        return None
    return {
        "user_id":       row[0],
        "username":      row[1],
        "password_hash": row[2],
        "role":          row[3],
        "created_at":    row[4],
    }


def verify_password(username: str, password: str) -> Optional[dict]:
    """Vérifie identifiants. Retourne {user_id, username, role} ou None (sans exposer le hash)."""
    user = get_user_by_username(username)
    if user is None:
        return None
    if user["password_hash"] is None:
        return None
    if not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        return None
    return {
        "user_id":  user["user_id"],
        "username": user["username"],
        "role":     user["role"],
    }
