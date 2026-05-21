#!/usr/bin/env python
"""
correction_map.py — Correction Map / Imagerie des corrections moteur (TASK-057A)

Vision consolidée des corrections apportées et restantes sur ADDISCO OPS.
Sources : ROADMAP_PROGRESS.md, DEVLOG.md, guardrails, DB (read-only).

Usage (depuis la racine du projet) :
    python tools/observability/correction_map.py
    python tools/observability/correction_map.py --no-guardrails

Read-only strict : aucune écriture SQL, aucun appel API, aucune modification runtime.
"""
import argparse
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Optional

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

ROOT    = Path(__file__).resolve().parents[2]
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "database.db"))
SEP     = "-" * 74
SEP2    = "=" * 74

# ── Catalogue des corrections ─────────────────────────────────────────────────
# Base de connaissance statique — issues identifiées, solutions livrées.

CORRECTIONS_DONE = [
    {
        "task":     "TASK-050",
        "titre":    "Guardrails Architecture V1",
        "probleme": "Aucun audit automatique des derives architecturales",
        "solution": "Moteur d'audit read-only : 6 regles (taille, imports, SQL, secrets). Verdict GO/WARNING/FAILED.",
        "impact":   "Detection proactive — 11 CRITICALs identifies des le lancement",
        "snapshot": "snapshot_pre_docker_readme_visual_v1",
        "commit":   "e5c3690",
        "fichiers": ["tools/guardrails/architecture_guardrails.py"],
    },
    {
        "task":     "TASK-051",
        "titre":    "Sources RAG visibles",
        "probleme": "Chunks RAG utilises invisibles pour l'apprenant — moteur boite noire",
        "solution": "Expander top-k chunks avec rang, document, section, extrait, score RAG (%)",
        "impact":   "Explicabilite RAG — confiance apprenant augmentee, chunks bruites identifies",
        "snapshot": "snapshot_task051_ok",
        "commit":   "8aebae7",
        "fichiers": ["tabs/tab_training.py", "ai_service.py", "rag_service.py"],
    },
    {
        "task":     "TASK-051B",
        "titre":    "Separation confiance / signal pedagogique",
        "probleme": "Confusion entre volume de donnees et qualite du signal dans le profil",
        "solution": "Deux metriques distinctes : confiance_statistique (volume) / signal_pedagogique (gap modes)",
        "impact":   "Dashboard profil plus honnete — signal faible correctement identifie",
        "snapshot": "snapshot_task051b_ok",
        "commit":   "f31f117",
        "fichiers": ["engine/user_profile_insights.py", "tabs/tab_dashboard.py"],
    },
    {
        "task":     "TASK-052",
        "titre":    "Score de confiance correction V1",
        "probleme": "Toutes les corrections presentees avec la meme autorite, quelle que soit la qualite",
        "solution": "Score deterministique : score RAG + overlap lexical + longueur reponse -> faible/moyen/eleve",
        "impact":   "Apprenant averti si correction peu fiable — zero appel API supplementaire",
        "snapshot": "snapshot_task052_ok",
        "commit":   "d56a087",
        "fichiers": ["ai_service.py", "tabs/tab_training.py"],
    },
    {
        "task":     "TASK-053",
        "titre":    "Rejet hors sujet / non evaluable",
        "probleme": "Reponses vides, trop courtes ou hors sujet envoyees au LLM inutilement",
        "solution": "Pre-validation deterministe avant appel API : empty / too_short / non_knowledge",
        "impact":   "Zero appel API superflu, analytics propres, UX claire (warning vs error)",
        "snapshot": "snapshot_task053_ok",
        "commit":   "e0ae2a1",
        "fichiers": ["ai_service.py", "tabs/tab_training.py"],
    },
    {
        "task":     "TASK-054",
        "titre":    "Chunk Quality Analyzer V1",
        "probleme": "Qualite documentaire non mesuree — chunks bruites, orphelins, weak invisibles",
        "solution": "Script read-only : 7 verdicts (WEAK/NOISY/ORPHAN/OVERSIZED/UNDERSIZED/WATCH/OK)",
        "impact":   "10 chunks WEAK, 2 NOISY, 80 ORPHAN detectes — base de priorisation TASK-055+",
        "snapshot": "snapshot_task054_ok",
        "commit":   "b39bc6e",
        "fichiers": ["tools/observability/chunk_quality_analyzer.py"],
    },
    {
        "task":     "TASK-055",
        "titre":    "Skill Graph Engine V1",
        "probleme": "Skills plats — aucune dependance pedagogique, pas d'ordre d'apprentissage",
        "solution": "Graphe declaratif Bloom (5 niveaux), topological_sort, is_ready/get_blocking/get_session_order",
        "impact":   "Ordre de session oriente, skills bloques visibles — base pour TASK-056/058",
        "snapshot": "snapshot_task055_ok",
        "commit":   "3eaf9b4",
        "fichiers": ["engine/skill_graph.py", "tools/observability/skill_graph_observer.py"],
    },
    {
        "task":     "TASK-056",
        "titre":    "Adaptive Difficulty Engine V2",
        "probleme": "consequence (Lv4) genere 8/20 fois pour profil Fragile — biais MASTERY_BIAS['Fragile'] errone",
        "solution": "Fix _MASTERY_BIAS + module adaptatif : recent_scores, graph_level, error patterns",
        "impact":   "consequence absent de 300 appels Fragile. Distribution : vrai_faux/question_directe uniquement",
        "snapshot": "snapshot_task056_ok",
        "commit":   "412101e",
        "fichiers": ["engine/question_type.py", "engine/adaptive_difficulty.py", "ai_service.py", "db/chunks.py"],
    },
    {
        "task":     "TASK-056A",
        "titre":    "Simulateur session pedagogique reelle",
        "probleme": "Comportement moteur non observable sans simulation reelle",
        "solution": "Script 20 questions / vraies APIs / 5 types reponses / rapport progression + skill graph",
        "impact":   "Revele biais consequence + 8 skills bloques + score moyen 0.20 pour Guilhem",
        "snapshot": "snapshot_task056a_ok",
        "commit":   "2909343",
        "fichiers": ["tools/testing/simulate_learning_session.py"],
    },
]

CORRECTIONS_TODO = [
    {
        "task":      "TASK-057",
        "titre":     "Error Pattern Memory",
        "priorite":  "HIGH",
        "probleme":  "Patterns erreurs (reponse_vague x9 dans sim) memorises 5 tentatives seulement",
        "risque":    "Moteur ne corrige pas les patterns persistants inter-sessions",
        "prereqs":   ["TASK-056 OK"],
    },
    {
        "task":      "TASK-058",
        "titre":     "Curriculum Engine V1",
        "priorite":  "HIGH",
        "probleme":  "Aucune progression logique fondation->entrainement->validation->revision",
        "risque":    "Sessions non ordonnees — apprenant attaque des notions sans base acquise",
        "prereqs":   ["TASK-055 OK (Skill Graph)", "TASK-057 recommande"],
    },
    {
        "task":      "TASK-059",
        "titre":     "Calibration Engine V1",
        "priorite":  "HIGH",
        "probleme":  "Moteur non calibre — profils produits non verifies vs profils attendus",
        "risque":    "Derive silencieuse du moteur adaptatif non detectee",
        "prereqs":   ["TASK-058 recommande"],
    },
    {
        "task":      "TASK-060",
        "titre":     "Maintenance Assistee V1",
        "priorite":  "MEDIUM",
        "probleme":  "Dettes RAG (chunks ORPHAN/WEAK) non traitees automatiquement",
        "risque":    "Degradation progressive qualite RAG sans alerte",
        "prereqs":   ["TASK-054 OK (Chunk Quality)"],
    },
    {
        "task":      "TASK-061",
        "titre":     "Vue Admin",
        "priorite":  "MEDIUM",
        "probleme":  "Supervision utilisateurs/documents impossible sans acces technique",
        "risque":    "Impossible a operer en production sans dashboard admin",
        "prereqs":   ["Phase 16 UX en cours"],
    },
    {
        "task":      "TASK-062",
        "titre":     "Rapports HTML/PDF",
        "priorite":  "MEDIUM",
        "probleme":  "Aucun bilan exportable par apprenant ou cohorte",
        "risque":    "Valeur SaaS non demontrable aux formateurs",
        "prereqs":   ["TASK-061 recommande"],
    },
    {
        "task":      "TASK-063",
        "titre":     "UX Responsive Tablette",
        "priorite":  "LOW",
        "probleme":  "Layout non optimise tablette / mode presentation",
        "risque":    "Experience demonstration degradee sur tablette",
        "prereqs":   ["TASK-062 recommande"],
    },
]

PRIORITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
PRIORITY_ICON  = {"CRITICAL": "[!!!]", "HIGH": "[HI] ", "MEDIUM": "[MED]", "LOW": "[LOW]"}


# ── Parsers ───────────────────────────────────────────────────────────────────

def _parse_roadmap_progress(path: Path) -> dict[str, str]:
    """Retourne {task_id: status} depuis ROADMAP_PROGRESS.md."""
    result: dict[str, str] = {}
    if not path.exists():
        return result
    task: Optional[str] = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^## (TASK-\w+)", line)
        if m:
            task = m.group(1)
        if task and re.match(r"^STATUS\s*:\s*(.+)", line):
            result[task] = re.match(r"^STATUS\s*:\s*(.+)", line).group(1).strip()
    return result


def _parse_devlog_tasks(path: Path) -> dict[str, str]:
    """Retourne {task_id: premiere_ligne_resume} depuis DEVLOG.md."""
    result: dict[str, str] = {}
    if not path.exists():
        return result
    current: Optional[str] = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.search(r"(TASK-\d+\w*)", line)
        if m and line.startswith("##"):
            current = m.group(1)
        elif current and line.startswith("**Fichiers"):
            result[current] = line.strip()
    return result


def _run_guardrails(root: Path) -> tuple[int, int, int]:
    """Lance les guardrails et retourne (n_critical, n_warning, returncode)."""
    script = root / "tools" / "guardrails" / "architecture_guardrails.py"
    if not script.exists():
        return 0, 0, -1
    try:
        r = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=30,
            encoding="utf-8",
            errors="replace",
        )
        out = r.stdout + r.stderr
        n_crit = out.count("[CRITICAL]")
        n_warn = out.count("[WARNING]")
        return n_crit, n_warn, r.returncode
    except Exception:
        return 0, 0, -1


def _db_chunk_stats() -> dict:
    """Stats chunks depuis la DB (read-only)."""
    stats = {
        "total": 0, "orphan": 0, "n_docs": 0,
        "low_score_chunks": 0, "avg_score": None,
    }
    if not DB_PATH.exists():
        return stats
    try:
        with sqlite3.connect(str(DB_PATH)) as conn:
            stats["total"]  = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
            stats["n_docs"] = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
            stats["orphan"] = conn.execute("""
                SELECT COUNT(*) FROM chunks c
                WHERE NOT EXISTS (
                    SELECT 1 FROM chunk_skills cs
                    WHERE cs.chunk_id = c.id AND cs.is_active = 1
                )
            """).fetchone()[0]
            row = conn.execute("""
                SELECT COUNT(*), AVG(score) FROM attempts
                WHERE score IS NOT NULL AND chunk_id IS NOT NULL
            """).fetchone()
            if row and row[0] > 0:
                stats["avg_score"] = round(row[1], 3) if row[1] else None
                stats["low_score_chunks"] = conn.execute("""
                    SELECT COUNT(DISTINCT chunk_id) FROM attempts
                    WHERE chunk_id IS NOT NULL
                    GROUP BY chunk_id
                    HAVING AVG(score) < 0.45
                """).fetchone()[0] if conn.execute("""
                    SELECT COUNT(DISTINCT chunk_id) FROM attempts
                    WHERE chunk_id IS NOT NULL
                    GROUP BY chunk_id
                    HAVING AVG(score) < 0.45
                """).fetchone() else 0
    except Exception:
        pass
    return stats


def _count_git_commits_since(root: Path, ref: str) -> int:
    try:
        r = subprocess.run(
            ["git", "rev-list", "--count", f"{ref}..HEAD"],
            cwd=str(root), capture_output=True, text=True, timeout=10
        )
        return int(r.stdout.strip()) if r.returncode == 0 else 0
    except Exception:
        return 0


# ── Calcul des scores ─────────────────────────────────────────────────────────

def _compute_scores(
    n_done:   int,
    n_todo:   int,
    n_crit:   int,
    n_warn:   int,
    db_stats: dict,
) -> dict[str, int]:
    total = n_done + n_todo
    done_pct = n_done / total * 100 if total else 0

    # Robustesse moteur : taches engine done + penalites guardrails critiques
    robustesse = min(100, max(0, int(
        55
        + (n_done * 3)
        - (n_crit * 2)
        - (1 if n_todo >= 5 else 0) * 5
    )))

    # Qualite RAG : chunks orphelins et faibles
    orphan_pct = db_stats["orphan"] / db_stats["total"] * 100 if db_stats["total"] else 0
    qualite_rag = min(100, max(0, int(
        80
        - (orphan_pct * 0.3)
        - (db_stats["low_score_chunks"] * 2)
    )))

    # Observabilite : outils disponibles
    tools_obs = ROOT / "tools" / "observability"
    n_obs_tools = len(list(tools_obs.glob("*.py"))) if tools_obs.exists() else 0
    observabilite = min(100, max(0, 30 + (n_obs_tools * 12)))

    # Adaptativite : taches adaptatives completees
    adaptative_done = sum(
        1 for c in CORRECTIONS_DONE
        if any(k in c["task"] for k in ["055", "056"])
    )
    adaptative_todo = sum(
        1 for c in CORRECTIONS_TODO
        if any(k in c["task"] for k in ["057", "058", "059"])
    )
    adaptativite = min(100, max(0, int(
        40 + (adaptative_done * 12) - (adaptative_todo * 8)
    )))

    # Securite : secrets/imports guardrails
    securite = min(100, max(0, int(
        90 - (n_crit * 3) - (n_warn * 1)
    )))

    # Dette technique : basee sur guardrails totaux
    total_findings = n_crit + n_warn
    dette = min(100, max(0, int(
        100 - (n_crit * 4) - (n_warn * 2)
    )))

    return {
        "robustesse_moteur": robustesse,
        "qualite_rag":       qualite_rag,
        "observabilite":     observabilite,
        "adaptativite":      adaptativite,
        "securite":          securite,
        "dette_technique":   dette,
    }


# ── Helpers affichage ─────────────────────────────────────────────────────────

def _section(title: str) -> None:
    print(f"\n{SEP2}")
    print(f"  {title}")
    print(SEP2)


def _score_bar(score: int, width: int = 20) -> str:
    filled  = round(score / 100 * width)
    empty   = width - filled
    bar     = "#" * filled + "." * empty
    return f"[{bar}]"


def _score_label(score: int) -> str:
    if score >= 80:
        return "BON  "
    if score >= 60:
        return "MOYEN"
    if score >= 40:
        return "FAIBLE"
    return "CRITIQUE"


def _status_icon(done: bool) -> str:
    return "[OK]     " if done else "[TODO]   "


# ── Sections du rapport ───────────────────────────────────────────────────────

def _print_corrections_done() -> None:
    _section("1. CORRECTIONS APPORTEES")
    for c in CORRECTIONS_DONE:
        print(f"\n  {c['task']} — {c['titre']}")
        print(f"  {'-' * 60}")
        print(f"  Probleme : {c['probleme']}")
        print(f"  Solution : {c['solution']}")
        print(f"  Impact   : {c['impact']}")
        print(f"  Snapshot : {c['snapshot']}  (commit {c['commit']})")
        print(f"  Fichiers : {', '.join(c['fichiers'])}")


def _print_corrections_todo() -> None:
    _section("2. CORRECTIONS A APPORTER")

    # Tri par priorite
    by_priority: dict[str, list] = {"CRITICAL": [], "HIGH": [], "MEDIUM": [], "LOW": []}
    for c in CORRECTIONS_TODO:
        by_priority[c["priorite"]].append(c)

    for prio, group in by_priority.items():
        if not group:
            continue
        icon = PRIORITY_ICON[prio]
        print(f"\n  {icon}  {prio}")
        print(f"  {'-' * 60}")
        for c in group:
            print(f"\n    {c['task']} — {c['titre']}")
            print(f"    Probleme : {c['probleme']}")
            print(f"    Risque   : {c['risque']}")
            print(f"    Prereqs  : {', '.join(c['prereqs'])}")


def _print_matrix(roadmap_statuses: dict[str, str]) -> None:
    _section("3. MATRICE VISUELLE")

    all_items = [
        ("TASK-050", "Guardrails Architecture V1"),
        ("TASK-051", "Sources RAG visibles"),
        ("TASK-051B", "Separation confiance / signal pedagogique"),
        ("TASK-052", "Score de confiance correction V1"),
        ("TASK-053", "Rejet non-evaluable"),
        ("TASK-054", "Chunk Quality Analyzer V1"),
        ("TASK-055", "Skill Graph Engine V1"),
        ("TASK-056", "Adaptive Difficulty Engine V2"),
        ("TASK-056A", "Simulateur session pedagogique"),
        ("TASK-057", "Error Pattern Memory"),
        ("TASK-058", "Curriculum Engine V1"),
        ("TASK-059", "Calibration Engine V1"),
        ("TASK-060", "Maintenance Assistee V1"),
        ("TASK-061", "Vue Admin"),
        ("TASK-062", "Rapports HTML/PDF"),
        ("TASK-063", "UX Responsive Tablette"),
    ]

    # Issues connues
    known_issues = {
        "TASK-054": "WARNING",  # 80 chunks orphelins encore presents
    }

    print()
    for task_id, titre in all_items:
        status = roadmap_statuses.get(task_id, "")
        is_done = "DONE" in status.upper()

        # Override avec etat connu
        if is_done and task_id in known_issues:
            icon = "[WARNING]"
        elif is_done:
            icon = "[OK]     "
        else:
            icon = "[TODO]   "

        print(f"  {icon}  {task_id:<10}  {titre}")


def _print_scores(scores: dict[str, int], n_crit: int, n_warn: int,
                  db_stats: dict) -> None:
    _section("4. SCORE GLOBAL")

    print(f"\n  {'DIMENSION':<25}  {'SCORE':>5}  {'BAR':>22}  ETAT")
    print(f"  {SEP}")

    total = 0
    for dim, score in scores.items():
        bar   = _score_bar(score)
        label = _score_label(score)
        dim_fr = {
            "robustesse_moteur": "Robustesse moteur",
            "qualite_rag":       "Qualite RAG",
            "observabilite":     "Observabilite",
            "adaptativite":      "Adaptativite",
            "securite":          "Securite",
            "dette_technique":   "Dette technique",
        }.get(dim, dim)
        print(f"  {dim_fr:<25}  {score:>5}  {bar}  {label}")
        total += score

    avg = total // len(scores)
    print(f"\n  {SEP}")
    print(f"  {'SCORE GLOBAL':<25}  {avg:>5}  {_score_bar(avg)}  {_score_label(avg)}")

    print(f"\n  Guardrails : {n_crit} CRITICAL  {n_warn} WARNING")
    print(f"  DB         : {db_stats['total']} chunks  {db_stats['orphan']} orphelins"
          f"  {db_stats['n_docs']} documents")
    if db_stats["avg_score"] is not None:
        print(f"             score moyen attempts : {db_stats['avg_score']:.2f}")


def _print_next_action(scores: dict[str, int]) -> None:
    _section("5. PROCHAINE ACTION RECOMMANDEE")

    # Identifier la correction la plus urgente non faite
    todo_critical = [c for c in CORRECTIONS_TODO if c["priorite"] == "CRITICAL"]
    todo_high     = [c for c in CORRECTIONS_TODO if c["priorite"] == "HIGH"]

    if todo_critical:
        next_c = todo_critical[0]
    elif todo_high:
        next_c = todo_high[0]
    else:
        next_c = CORRECTIONS_TODO[0] if CORRECTIONS_TODO else None

    if not next_c:
        print("\n  Toutes les corrections planifiees sont realisees.")
        return

    print(f"\n  Prochaine correction : {next_c['task']} — {next_c['titre']}")
    print(f"\n  Pourquoi :")
    print(f"    {next_c['probleme']}")
    print(f"\n  Risque si non traite :")
    print(f"    {next_c['risque']}")
    print(f"\n  Prerequis satisfaits : {', '.join(next_c['prereqs'])}")

    # Context supplementaire selon score
    if scores.get("adaptativite", 100) < 70:
        print(f"\n  Note : score adaptativite = {scores['adaptativite']}/100 — moteur")
        print(f"         adaptatif incomplet. {next_c['task']} est la prochaine brique critique.")


def _verdict(scores: dict[str, int], n_crit: int) -> str:
    avg = sum(scores.values()) // len(scores)
    if n_crit > 15 or avg < 40:
        return "FAILED"
    if n_crit > 5 or avg < 60:
        return "GO WITH WARNING"
    return "GO SAFE"


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Correction Map — imagerie des corrections ADDISCO OPS."
    )
    parser.add_argument(
        "--no-guardrails", action="store_true",
        help="Ignorer les guardrails (plus rapide, moins precis)"
    )
    args = parser.parse_args()

    # ── Collecte donnees ──────────────────────────────────────────────────────
    roadmap_path = ROOT / "docs" / "ROADMAP_PROGRESS.md"
    devlog_path  = ROOT / "DEVLOG.md"

    roadmap_statuses = _parse_roadmap_progress(roadmap_path)
    db_stats         = _db_chunk_stats()

    n_crit, n_warn, guardrails_rc = (0, 0, -1)
    if not args.no_guardrails:
        print("  [Guardrails en cours...]", end="", flush=True)
        n_crit, n_warn, guardrails_rc = _run_guardrails(ROOT)
        print(f" {n_crit} CRITICAL  {n_warn} WARNING")

    n_done = sum(1 for s in roadmap_statuses.values() if "DONE" in s.upper())
    n_todo = sum(1 for s in roadmap_statuses.values() if "TODO" in s.upper())
    scores = _compute_scores(n_done, n_todo, n_crit, n_warn, db_stats)

    # ── En-tete ───────────────────────────────────────────────────────────────
    print(f"\n{SEP2}")
    print(f"  CORRECTION MAP — ADDISCO OPS")
    print(f"  Base : {DB_PATH.name}  |  Guardrails : {'actifs' if not args.no_guardrails else 'ignores'}")
    print(f"  Tasks done : {n_done}  |  Tasks todo : {len(CORRECTIONS_TODO)}")
    print(SEP2)

    # ── Sections ──────────────────────────────────────────────────────────────
    _print_corrections_done()
    _print_corrections_todo()
    _print_matrix(roadmap_statuses)
    _print_scores(scores, n_crit, n_warn, db_stats)
    _print_next_action(scores)

    # ── Verdict ───────────────────────────────────────────────────────────────
    _section("VERDICT GLOBAL")
    v    = _verdict(scores, n_crit)
    icon = {"GO SAFE": "OK", "GO WITH WARNING": "WARNING", "FAILED": "FAILED"}.get(v, v)
    avg  = sum(scores.values()) // len(scores)
    print(f"\n  [{icon}]  {v}")
    print(f"          Score moyen : {avg}/100  |  {n_crit} CRITICAL guardrails  "
          f"|  {len(CORRECTIONS_TODO)} corrections restantes\n")
    print(SEP2 + "\n")


if __name__ == "__main__":
    main()
