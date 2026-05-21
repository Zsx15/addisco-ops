#!/usr/bin/env python
"""
skill_graph_observer.py — Observabilité du Skill Graph Engine V1 (TASK-055)

Visualise la structure du graphe et l'état de maîtrise d'un utilisateur.

Usage (depuis la racine du projet) :
    python tools/observability/skill_graph_observer.py
    python tools/observability/skill_graph_observer.py --username test

Read-only strict : aucune écriture SQL, aucun appel API, aucun fix automatique.
"""
import argparse
import os
import sqlite3
import sys
from pathlib import Path
from typing import Optional

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

# Ajout de la racine au path pour importer engine/
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from engine.skill_graph import (
    SKILL_GRAPH,
    MASTERY_THRESHOLD,
    get_level,
    get_prerequisites,
    get_dependents,
    get_blocking,
    get_full_blocking_chain,
    get_session_order,
    topological_order,
    validate_graph,
    levels,
)

DB_PATH = Path(os.getenv("DB_PATH", "database.db"))
SEP  = "-" * 76
SEP2 = "=" * 76


# ── DB helpers ────────────────────────────────────────────────────────────────

def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(DB_PATH))
    c.row_factory = sqlite3.Row
    return c


def _load_skill_labels(conn: sqlite3.Connection) -> dict[str, str]:
    rows = conn.execute("SELECT slug, label_fr FROM skills").fetchall()
    return {r["slug"]: r["label_fr"] for r in rows}


def _load_db_skills(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT slug FROM skills WHERE is_active = 1").fetchall()
    return [r["slug"] for r in rows]


def _load_user_mastery(conn: sqlite3.Connection,
                        user_id: str) -> dict[str, float]:
    rows = conn.execute("""
        SELECT s.slug, usm.mastery_score
        FROM   user_skill_mastery usm
        JOIN   skills s ON s.id = usm.skill_id
        WHERE  usm.user_id = ?
    """, (user_id,)).fetchall()
    return {r["slug"]: round(r["mastery_score"], 3) for r in rows}


def _load_user_attempts_per_skill(conn: sqlite3.Connection,
                                   user_id: str) -> dict[str, int]:
    rows = conn.execute("""
        SELECT s.slug, COUNT(*) AS n
        FROM   attempts a
        JOIN   chunks c       ON c.id = a.chunk_id
        JOIN   chunk_skills cs ON cs.chunk_id = c.id AND cs.is_active = 1
        JOIN   skills s       ON s.id = cs.skill_id
        WHERE  a.user_id = ?
        GROUP  BY s.slug
    """, (user_id,)).fetchall()
    return {r["slug"]: r["n"] for r in rows}


# ── Affichage ─────────────────────────────────────────────────────────────────

def _section(title: str) -> None:
    print(f"\n{SEP2}")
    print(f"  {title}")
    print(SEP2)


def _score_bar(score: Optional[float], width: int = 12) -> str:
    if score is None:
        return "░" * width + "  —  "
    filled = round(score * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"{bar}  {score:.2f}"


def _status_icon(slug: str,
                  mastery: dict[str, float],
                  threshold: float) -> str:
    score = mastery.get(slug, 0.0)
    ready = all(mastery.get(p, 0.0) >= threshold for p in get_prerequisites(slug))
    if score >= threshold:
        return "[ACQUIS]"
    if ready:
        return "[PRET]  "
    return "[BLOQUE]"


# ── Sections du rapport ───────────────────────────────────────────────────────

def _print_graph_structure(labels: dict[str, str]) -> None:
    _section("1. STRUCTURE DU GRAPHE")

    lvls = levels()
    max_level = max(lvls.values()) if lvls else 0
    topo = topological_order()

    print()
    for level in range(max_level + 1):
        skills_at_level = [s for s in topo if lvls.get(s) == level]
        label_level = {
            0: "Fondations",
            1: "Compréhension",
            2: "Application",
            3: "Maîtrise",
            4: "Expertise",
        }.get(level, f"Level {level}")
        print(f"  Level {level} — {label_level}")
        print(f"  {'-' * 60}")
        for slug in skills_at_level:
            label = labels.get(slug, slug)
            prereqs = get_prerequisites(slug)
            deps    = get_dependents(slug)
            prereq_str = ", ".join(prereqs) if prereqs else "—"
            dep_str    = ", ".join(deps) if deps else "—"
            print(f"    {slug:<35}  [{label}]")
            print(f"      ← prérequis : {prereq_str}")
            print(f"      → débloq.   : {dep_str}")
        print()


def _print_orphan_check(db_skills: list[str], labels: dict[str, str]) -> None:
    _section("2. COHÉRENCE GRAPHE ↔ BASE DE DONNÉES")

    graph_slugs = set(SKILL_GRAPH.keys())
    db_slugs    = set(db_skills)

    in_graph_not_db = graph_slugs - db_slugs
    in_db_not_graph = db_slugs - graph_slugs

    errors = validate_graph()

    if errors:
        print(f"\n  [ERREURS GRAPHE]")
        for e in errors:
            print(f"    ❌  {e}")
    else:
        print(f"\n  ✅  Graphe valide — aucun cycle, tous les prérequis connus.")

    print(f"\n  Skills en base (actifs)   : {len(db_slugs)}")
    print(f"  Skills dans le graphe     : {len(graph_slugs)}")

    if in_graph_not_db:
        print(f"\n  [FANTÔMES] Dans le graphe mais absents de la base :")
        for s in sorted(in_graph_not_db):
            print(f"    ⚠  {s}")
    else:
        print(f"\n  ✅  Tous les skills du graphe sont en base.")

    if in_db_not_graph:
        print(f"\n  [ORPHELINS] En base mais absents du graphe :")
        for s in sorted(in_db_not_graph):
            label = labels.get(s, s)
            print(f"    ⚠  {s:<35}  [{label}]")
        print(f"       → Ces skills ne participent pas au graphe de progression.")
    else:
        print(f"  ✅  Tous les skills de la base sont dans le graphe.")


def _print_user_readiness(username: str,
                           user_id: str,
                           mastery: dict[str, float],
                           attempts: dict[str, int],
                           labels: dict[str, str]) -> None:
    _section(f"3. ÉTAT UTILISATEUR : {username}")

    topo = topological_order()
    lvls = levels()

    print(f"\n  {'SKILL':<35}  {'ÉTAT':>8}  {'SCORE':>18}  {'ATT':>5}  LABEL")
    print(f"  {SEP}")

    n_acquis  = 0
    n_pret    = 0
    n_bloque  = 0

    for slug in topo:
        label  = labels.get(slug, slug)[:30]
        score  = mastery.get(slug)
        att    = attempts.get(slug, 0)
        icon   = _status_icon(slug, mastery, MASTERY_THRESHOLD)
        bar    = _score_bar(score)
        level  = lvls.get(slug, 0)
        indent = "  " * level

        print(f"  {indent}{slug:<{35 - len(indent)}}  {icon}  {bar}  {att:>5}  {label}")

        if icon == "[ACQUIS]":
            n_acquis += 1
        elif icon == "[PRET]  ":
            n_pret += 1
        else:
            n_bloque += 1

    print(f"\n  Acquis : {n_acquis}  |  Prêts à apprendre : {n_pret}  |  Bloqués : {n_bloque}")


def _print_blocking_chains(mastery: dict[str, float],
                            labels: dict[str, str]) -> None:
    _section("4. CHAÎNES DE BLOCAGE")

    blocked = [
        s for s in SKILL_GRAPH
        if mastery.get(s, 0.0) < MASTERY_THRESHOLD
           and get_prerequisites(s)
           and not all(mastery.get(p, 0.0) >= MASTERY_THRESHOLD for p in get_prerequisites(s))
    ]

    if not blocked:
        print(f"\n  ✅  Aucun skill bloqué pour cet utilisateur.")
        return

    for slug in blocked:
        chain = get_full_blocking_chain(slug, mastery, MASTERY_THRESHOLD)
        label = labels.get(slug, slug)
        print(f"\n  {slug} [{label}]")
        print(f"    bloqué par :")
        for blocker in chain:
            b_score = mastery.get(blocker, 0.0)
            b_label = labels.get(blocker, blocker)
            print(f"      └── {blocker:<35}  score={b_score:.2f}  [{b_label}]")


def _print_session_order(mastery: dict[str, float],
                          labels: dict[str, str]) -> None:
    _section("5. ORDRE DE SESSION RECOMMANDÉ")

    order = get_session_order(mastery, MASTERY_THRESHOLD)
    lvls  = levels()

    print(f"\n  Ordre optimal (prérequis d'abord, puis skills prêts, puis révision) :\n")
    for i, slug in enumerate(order, 1):
        label   = labels.get(slug, slug)
        score   = mastery.get(slug, 0.0)
        ready   = all(mastery.get(p, 0.0) >= MASTERY_THRESHOLD for p in get_prerequisites(slug))
        mastered = score >= MASTERY_THRESHOLD
        level   = lvls.get(slug, 0)

        tag = "REVISER" if mastered else ("APPRENDRE" if ready else "BLOQUE  ")
        print(f"  {i:>3}. Lv{level}  {slug:<35}  [{tag}]  score={score:.2f}  {label}")


# ── Verdict ───────────────────────────────────────────────────────────────────

def _verdict(db_skills: list[str], mastery: dict[str, float]) -> str:
    errors = validate_graph()
    if errors:
        return "FAILED"

    graph_slugs = set(SKILL_GRAPH.keys())
    in_db_not_graph = set(db_skills) - graph_slugs

    blocked = [
        s for s in SKILL_GRAPH
        if mastery and mastery.get(s, 0.0) < MASTERY_THRESHOLD
           and not all(mastery.get(p, 0.0) >= MASTERY_THRESHOLD for p in get_prerequisites(s))
    ]

    if in_db_not_graph:
        return "GO WITH WARNING"

    if mastery and len(blocked) > len(SKILL_GRAPH) * 0.6:
        return "GO WITH WARNING"

    return "GO SAFE"


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Skill Graph Observer V1 — read-only."
    )
    parser.add_argument(
        "--username", default=None,
        help="Afficher l'état de maîtrise d'un utilisateur (ex: test)"
    )
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"[ERREUR] Base introuvable : {DB_PATH}")
        sys.exit(1)

    conn      = _conn()
    labels    = _load_skill_labels(conn)
    db_skills = _load_db_skills(conn)

    mastery:  dict[str, float] = {}
    attempts: dict[str, int]   = {}
    user_id:  Optional[str]    = None
    username: str               = args.username or "(aucun)"

    if args.username:
        row = conn.execute(
            "SELECT user_id FROM users WHERE username = ?", (args.username,)
        ).fetchone()
        if row:
            user_id  = row["user_id"]
            mastery  = _load_user_mastery(conn, user_id)
            attempts = _load_user_attempts_per_skill(conn, user_id)
        else:
            print(f"[ERREUR] Utilisateur '{args.username}' introuvable.")
            conn.close()
            sys.exit(1)

    conn.close()

    # ── En-tête ───────────────────────────────────────────────────────────────
    print(f"\n{SEP2}")
    print(f"  SKILL GRAPH OBSERVER V1  —  TASK-055")
    print(f"  Utilisateur : {username}")
    print(f"  Base        : {DB_PATH}")
    print(f"  Skills DB   : {len(db_skills)}  |  Skills graphe : {len(SKILL_GRAPH)}")
    print(f"  Seuil maîtrise : {MASTERY_THRESHOLD}")
    print(SEP2)

    _print_graph_structure(labels)
    _print_orphan_check(db_skills, labels)

    if user_id:
        _print_user_readiness(username, user_id, mastery, attempts, labels)
        _print_blocking_chains(mastery, labels)
        _print_session_order(mastery, labels)

    # ── Verdict ───────────────────────────────────────────────────────────────
    _section("VERDICT GLOBAL")
    v    = _verdict(db_skills, mastery)
    icon = {"GO SAFE": "✅", "GO WITH WARNING": "⚠️ ", "FAILED": "❌"}.get(v, "")
    print(f"\n  {icon}  {v}\n")
    print(SEP2 + "\n")


if __name__ == "__main__":
    main()
