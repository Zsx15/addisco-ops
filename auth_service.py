"""Service d'authentification — hash/verify password, gestion table users."""
import logging
import sqlite3
import uuid
from typing import Optional

import bcrypt

import database

logger = logging.getLogger(__name__)

# Transitions de rôle autorisées — pas de rétrogradation possible.
_VALID_PROMOTIONS: frozenset[tuple[str, str]] = frozenset({
    ("apprenant", "formateur"),
    ("apprenant", "admin"),
    ("formateur", "admin"),
})


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


def promote_user(admin_username: str, target_username: str, new_role: str) -> None:
    """
    Promeut target_username vers new_role.

    Valide (dans l'ordre) :
    - auto-promotion interdite ;
    - admin_username a role='admin' en base (re-vérification DB, pas session_state) ;
    - target_username existe ;
    - la transition (role_actuel → new_role) est dans _VALID_PROMOTIONS.

    Lève ValueError avec message utilisateur si une validation échoue.
    """
    if admin_username == target_username:
        raise ValueError("Auto-promotion interdite.")

    admin = get_user_by_username(admin_username)
    if not admin or admin["role"] != "admin":
        raise ValueError("Droits insuffisants — seul un administrateur peut promouvoir.")

    target = get_user_by_username(target_username)
    if not target:
        raise ValueError(f"Utilisateur introuvable : {target_username}")

    current_role = target["role"]
    if (current_role, new_role) not in _VALID_PROMOTIONS:
        raise ValueError(
            f"Transition {current_role} → {new_role} non autorisée."
        )

    database.set_user_role(target_username, new_role)


def seed_demo_accounts() -> None:
    """Crée les comptes de démonstration si aucun administrateur n'existe.
    Idempotente — sans effet si un admin est déjà présent en base.
    """
    if database.count_admins() > 0:
        return
    _accounts = [
        ("admin",      "admin123",      "admin"),
        ("formateur",  "formateur123",  "formateur"),
    ]
    for _username, _password, _role in _accounts:
        try:
            register_user(_username, _password, role=_role)
            logger.info("Compte démo créé : %s (%s)", _username, _role)
        except ValueError:
            pass  # compte déjà présent


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
