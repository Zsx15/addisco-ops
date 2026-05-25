"""
CLI — Créer ou promouvoir un utilisateur (admin, formateur, apprenant).

Usage (depuis la racine du projet) :
    python tools/admin/create_or_promote_user.py --username <nom> --role <rôle> [--password <mdp>]

Comportement :
- Utilisateur absent  → le crée avec le rôle et le mot de passe fournis.
- Utilisateur présent → met à jour le rôle ET le mot de passe si --password fourni.
- Le mot de passe n'est jamais affiché en clair dans les logs.
- Vérification bcrypt immédiate après chaque modification.
- UPDATE ciblé — jamais DELETE+INSERT (préserve user_id, created_at, données liées).

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

_VALID_ROLES = frozenset({"admin", "formateur", "apprenant"})


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Créer ou promouvoir un utilisateur (outil CLI interne).",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--username", required=True, help="Nom d'utilisateur cible")
    parser.add_argument(
        "--role",
        required=True,
        choices=sorted(_VALID_ROLES),
        metavar="ROLE",
        help=f"Rôle cible : {', '.join(sorted(_VALID_ROLES))}",
    )
    parser.add_argument(
        "--password",
        default=None,
        help="Mot de passe (obligatoire à la création, optionnel pour mise à jour)",
    )
    parser.add_argument(
        "--db",
        default=None,
        help="Chemin vers database.db (défaut : DB_PATH env ou ./database.db)",
    )
    return parser.parse_args()


def _update_role(username: str, new_role: str) -> None:
    """UPDATE ciblé du rôle — préserve user_id, password_hash, created_at."""
    with sqlite3.connect(str(database.DB_PATH)) as conn:
        cur = conn.execute(
            "UPDATE users SET role = ? WHERE username = ?",
            (new_role, username),
        )
    if cur.rowcount == 0:
        raise ValueError(f"Utilisateur introuvable : {username}")


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

    existing = auth_service.get_user_by_username(args.username)

    if existing is None:
        # ── Création ──────────────────────────────────────────────────────────
        if not args.password:
            print(f"[ERREUR] --password obligatoire pour créer '{args.username}'.")
            sys.exit(1)

        try:
            user_id = auth_service.register_user(args.username, args.password, role=args.role)
        except ValueError as exc:
            print(f"[ERREUR] {exc}")
            sys.exit(1)

        verified = auth_service.verify_password(args.username, args.password)
        if verified is None:
            print("[ERREUR] Création échouée — vérification bcrypt post-création invalide.")
            sys.exit(1)

        print(f"[OK] Utilisateur '{args.username}' créé.")
        print(f"     id       : {user_id[:8]}...")
        print(f"     rôle     : {args.role}")
        print(f"     bcrypt   : OK")

    else:
        # ── Mise à jour ────────────────────────────────────────────────────────
        actions: list[str] = []

        if existing["role"] != args.role:
            try:
                _update_role(args.username, args.role)
                actions.append(f"role : {existing['role']} -> {args.role}")
            except ValueError as exc:
                print(f"[ERREUR] {exc}")
                sys.exit(1)

        if args.password:
            try:
                _update_password(args.username, args.password)
                actions.append("mot de passe : mis à jour")
            except ValueError as exc:
                print(f"[ERREUR] {exc}")
                sys.exit(1)

            verified = auth_service.verify_password(args.username, args.password)
            if verified is None:
                print("[ERREUR] Mise à jour échouée — vérification bcrypt post-update invalide.")
                sys.exit(1)
            print(f"     bcrypt   : OK")

        if not actions:
            print(
                f"[INFO] '{args.username}' est déjà {existing['role']} "
                f"— aucun changement appliqué."
            )
        else:
            print(f"[OK] Utilisateur '{args.username}' mis à jour.")
            for a in actions:
                print(f"     - {a}")


if __name__ == "__main__":
    main()
