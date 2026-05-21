"""
Clôture guidée d'une task — vérification git + mise à jour ROADMAP_PROGRESS.md.

Usage :
    python tools/roadmap/close_task.py TASK-052

Ce script :
  1. Verifie git status (working tree clean ?)
  2. Recupere le dernier commit
  3. Propose un nom de snapshot git tag
  4. Appelle update_progress.py avec status=DONE
  5. Affiche GO SAFE / WARNING / FAILED

Aucun auto-commit. Aucun git push. Lecture/ecriture ROADMAP_PROGRESS.md uniquement.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _run(cmd: list[str]) -> tuple[int, str]:
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return result.returncode, (result.stdout + result.stderr).strip()


def _git_is_clean() -> bool:
    rc, out = _run(["git", "status", "--porcelain"])
    return rc == 0 and out == ""


def _git_last_commit() -> str:
    rc, out = _run(["git", "rev-parse", "--short", "HEAD"])
    return out if rc == 0 else "unknown"


def _git_last_message() -> str:
    rc, out = _run(["git", "log", "-1", "--format=%s"])
    return out if rc == 0 else ""


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage : python tools/roadmap/close_task.py TASK-XXX")
        sys.exit(1)

    task_id = sys.argv[1].upper()
    if not task_id.startswith("TASK-"):
        print(f"[ERROR] Format invalide : '{task_id}'. Attendu : TASK-XXX")
        sys.exit(1)

    sep = "=" * 44
    print(f"\n{sep}")
    print(f"  CLOSE TASK -- {task_id}")
    print(f"{sep}\n")

    # ── 1. Git status ─────────────────────────────────────────────────────────
    clean  = _git_is_clean()
    commit = _git_last_commit()
    msg    = _git_last_message()

    if clean:
        print("[OK] Working tree clean")
    else:
        print("[WARNING] Working tree non clean -- commitez vos changements avant de clore")
    print(f"   Dernier commit : {commit} -- {msg}\n")

    # ── 2. Snapshot suggere ───────────────────────────────────────────────────
    task_slug           = task_id.lower().replace("-", "")   # "task052"
    snapshot_suggestion = f"snapshot_{task_slug}_ok"
    print(f"   Snapshot suggere  : {snapshot_suggestion}")
    print(f"   Pour creer le tag : git tag {snapshot_suggestion}\n")

    # ── 3. Resume optionnel ───────────────────────────────────────────────────
    print("   Resume court du livre (Entree pour ignorer) :")
    try:
        summary = input("   > ").strip()
    except (EOFError, KeyboardInterrupt):
        summary = ""
        print()

    # ── 4. Mise a jour ROADMAP_PROGRESS.md ────────────────────────────────────
    print()
    update_script = ROOT / "tools" / "roadmap" / "update_progress.py"
    cmd = [
        sys.executable, str(update_script),
        "--task",     task_id,
        "--status",   "DONE",
        "--snapshot", snapshot_suggestion,
    ]
    if summary:
        cmd += ["--summary", summary]

    rc, out = _run(cmd)
    if out:
        print(out)

    # ── 5. Verdict ────────────────────────────────────────────────────────────
    print(f"\n{sep}")
    if rc != 0:
        print("  VERDICT : FAILED -- erreur lors de la mise a jour ROADMAP_PROGRESS.md")
    elif not clean:
        print("  VERDICT : WARNING -- working tree non clean au moment de la cloture")
        print("  (ROADMAP_PROGRESS.md mis a jour, commitez vos changements)")
    else:
        print("  VERDICT : GO SAFE")
    print(f"{sep}\n")

    sys.exit(0 if rc == 0 else 1)


if __name__ == "__main__":
    main()
