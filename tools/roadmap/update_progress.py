"""
Mise à jour de ROADMAP_PROGRESS.md pour une task donnée.

Usage :
    python tools/roadmap/update_progress.py --task TASK-052 --status DONE
    python tools/roadmap/update_progress.py --task TASK-052 --status DONE ^
        --snapshot snapshot_task052_ok --summary "Confidence scoring V1 livré"

Statuts valides : TODO  IN_PROGRESS  DONE  SKIP
"""
import argparse
import subprocess
from datetime import date
from pathlib import Path

ROOT          = Path(__file__).resolve().parents[2]
PROGRESS_FILE = ROOT / "docs" / "ROADMAP_PROGRESS.md"

_VALID_STATUSES = ("TODO", "IN_PROGRESS", "DONE", "SKIP")


def _git_last_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT, text=True, stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "unknown"


def _build_new_block(task_id: str, status: str, snapshot: str, summary: str) -> str:
    lines = [f"## {task_id}", ""]
    if status == "DONE":
        today  = date.today().isoformat()
        commit = _git_last_commit()
        lines += [
            f"STATUS   : {status}",
            f"DATE     : {today}",
            f"COMMIT   : {commit}",
        ]
        if snapshot:
            lines.append(f"SNAPSHOT : {snapshot}")
        if summary:
            lines += ["", f"Livré : {summary}"]
    else:
        lines.append(f"STATUS : {status}")
    lines.append("")
    return "\n".join(lines)


def _find_block_range(lines: list[str], task_id: str) -> tuple[int, int]:
    """Retourne (start, end) : de la ligne header jusqu'à la prochaine ## ou fin.
    Correspond aux lignes commençant par '## TASK-XXX' (titre long toléré).
    """
    prefix = f"## {task_id}"
    start  = -1
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == prefix or stripped.startswith(prefix + " "):
            start = i
            break
    if start == -1:
        return -1, -1
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break
    return start, end


def update_progress(task_id: str, status: str, snapshot: str, summary: str) -> int:
    if not PROGRESS_FILE.exists():
        print(f"[ERROR] Fichier introuvable : {PROGRESS_FILE}")
        return 1

    content = PROGRESS_FILE.read_text(encoding="utf-8")

    # Détection par préfixe pour accepter les titres longs (ex: "## TASK-052 — Score…")
    task_prefix = f"## {task_id}"
    task_present = any(
        line.strip() == task_prefix or line.strip().startswith(task_prefix + " ")
        for line in content.split("\n")
    )

    if not task_present:
        # Nouvelle entrée — ajout en fin de fichier
        new_block = _build_new_block(task_id, status, snapshot, summary)
        content   = content.rstrip() + "\n\n---\n\n" + new_block + "\n"
        PROGRESS_FILE.write_text(content, encoding="utf-8")
        print(f"[OK] Nouvelle entree ajoutee : {task_id} -- {status}")
        return 0

    # Mise à jour du bloc existant
    lines = content.split("\n")
    start, end = _find_block_range(lines, task_id)
    if start == -1:
        print(f"[ERROR] Bloc {task_id} introuvable malgre la presence du header.")
        return 1

    today  = date.today().isoformat()
    commit = _git_last_commit()
    status_updated   = False
    date_updated     = False
    commit_updated   = False
    snapshot_updated = False

    for i in range(start, end):
        ln = lines[i]
        if ln.startswith("STATUS"):
            lines[i]       = f"STATUS   : {status}" if status != "TODO" else f"STATUS : {status}"
            status_updated = True
        elif ln.startswith("DATE") and status == "DONE":
            lines[i]     = f"DATE     : {today}"
            date_updated = True
        elif ln.startswith("COMMIT") and status == "DONE":
            lines[i]       = f"COMMIT   : {commit}"
            commit_updated = True
        elif ln.startswith("SNAPSHOT") and snapshot:
            lines[i]         = f"SNAPSHOT : {snapshot}"
            snapshot_updated = True

    # Injecter DATE / COMMIT / SNAPSHOT s'ils sont absents et status=DONE
    if status == "DONE" and not date_updated:
        lines.insert(start + 2, f"DATE     : {today}")
        end += 1
    if status == "DONE" and not commit_updated:
        lines.insert(start + 3, f"COMMIT   : {commit}")
        end += 1
    if status == "DONE" and snapshot and not snapshot_updated:
        lines.insert(start + 4, f"SNAPSHOT : {snapshot}")

    if status_updated:
        PROGRESS_FILE.write_text("\n".join(lines), encoding="utf-8")
        print(f"[OK] {task_id} mis a jour -- STATUS : {status}")
        return 0

    print(f"[WARNING] STATUS non trouve dans le bloc {task_id} -- verifiez ROADMAP_PROGRESS.md")
    return 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mise a jour de ROADMAP_PROGRESS.md",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--task",     required=True, help="ID task (ex: TASK-052)")
    parser.add_argument("--status",   required=True, choices=_VALID_STATUSES)
    parser.add_argument("--snapshot", default="",    help="Nom du git tag snapshot")
    parser.add_argument("--summary",  default="",    help="Resume court du livre")
    args = parser.parse_args()

    task_id = args.task.upper()
    if not task_id.startswith("TASK-"):
        print(f"[ERROR] Format invalide : '{task_id}'. Attendu : TASK-XXX")
        raise SystemExit(1)

    raise SystemExit(update_progress(task_id, args.status, args.snapshot, args.summary))


if __name__ == "__main__":
    main()
