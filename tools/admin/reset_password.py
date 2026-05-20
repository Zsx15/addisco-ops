"""
CLI — Réinitialiser le mot de passe d'un utilisateur existant.

Usage (depuis la racine du projet) :
    python tools/admin/reset_password.py --username <nom> --new-password <mdp>

Comportement :
- Vérifie que l'utilisateur existe.
- Met à jour uniquement le champ password_hash (UPDATE ciblé — jamais DELETE+INSERT).
- N'affecte pas le rôle, user_id, ni aucune donnée liée.
- Fonctionne pour tout rôle (admin, formateur, apprenant).

Ce script n'est JAMAIS exposé dans l'UI publique.
"""

import argparse
import sqlite3
import sys
from pathlib import Path

import bcrypt

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import database
import auth_service


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Réinitialiser le mot de passe d'un utilisateur (outil CLI interne)."
    )
    parser.add_argument("--username", required=True, help="Nom d'utilisateur cible")
    parser.add_argument("--new-password", required=True, dest="new_password", help="Nouveau mot de passe")
    parser.add_argument(
        "--db",
        default=None,
        help="Chemin vers database.db (défaut : variable d'env DB_PATH ou ./database.db)",
    )
    return parser.parse_args()


def _update_password(username: str, new_password: str) -> None:
    """UPDATE ciblé du hash — préserve user_id, rôle, created_at."""
    new_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    with sqlite3.connect(str(database.DB_PATH)) as conn:
        cur = conn.execute(
            "UPDATE users SET password_hash = ? WHERE username = ?",
            (new_hash, username),
        )
    if cur.rowcount == 0:
        raise ValueError(f"Utilisateur introuvable : {username}")


def main() -> None:
    args = _parse_args()

    if args.db:
        database.DB_PATH = Path(args.db)

    database.init_db()

    user = auth_service.get_user_by_username(args.username)
    if user is None:
        print(f"[ERREUR] Utilisateur '{args.username}' introuvable en base.")
        sys.exit(1)

    try:
        _update_password(args.username, args.new_password)
    except ValueError as exc:
        print(f"[ERREUR] {exc}")
        sys.exit(1)

    # Vérification immédiate — le hash doit matcher.
    verified = auth_service.verify_password(args.username, args.new_password)
    if verified is None:
        print("[ERREUR] Réinitialisation échouée — vérification post-update invalide.")
        sys.exit(1)

    print(f"[OK] Mot de passe réinitialisé pour '{args.username}' (rôle={user['role']}).")
    print(f"     Vérification bcrypt : OK")


if __name__ == "__main__":
    main()
