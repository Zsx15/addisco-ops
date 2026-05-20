"""
CLI — Créer ou promouvoir un compte administrateur.

Usage (depuis la racine du projet) :
    python tools/admin/create_admin.py --username <nom> --password <mdp>

Comportement :
- Si le compte n'existe pas → le crée avec role='admin'.
- Si le compte existe déjà avec role='admin' → erreur (pas de double création).
- Si le compte existe avec un autre rôle → refuse (utiliser reset_password ou promote_user).

Ce script n'est JAMAIS exposé dans l'UI publique.
"""

import argparse
import sys
from pathlib import Path

# Ajoute la racine du projet au path pour permettre les imports locaux.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import database
import auth_service
from db.admin import count_admins


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Créer un compte administrateur (outil CLI interne)."
    )
    parser.add_argument("--username", required=True, help="Nom d'utilisateur admin")
    parser.add_argument("--password", required=True, help="Mot de passe admin")
    parser.add_argument(
        "--db",
        default=None,
        help="Chemin vers database.db (défaut : variable d'env DB_PATH ou ./database.db)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    if args.db:
        database.DB_PATH = Path(args.db)

    database.init_db()

    existing = auth_service.get_user_by_username(args.username)
    if existing is not None:
        if existing["role"] == "admin":
            print(f"[ERREUR] Le compte '{args.username}' est déjà administrateur.")
            sys.exit(1)
        else:
            print(
                f"[ERREUR] Le compte '{args.username}' existe avec le rôle '{existing['role']}'.\n"
                "Utilisez promote_user() pour le promouvoir, ou reset_password.py pour changer son mot de passe."
            )
            sys.exit(1)

    try:
        user_id = auth_service.register_user(args.username, args.password, role="admin")
    except ValueError as exc:
        print(f"[ERREUR] {exc}")
        sys.exit(1)

    total = count_admins()
    print(f"[OK] Compte admin '{args.username}' créé (id={user_id[:8]}...).")
    print(f"     Nombre total d'admins en base : {total}")


if __name__ == "__main__":
    main()
