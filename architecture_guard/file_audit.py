from pathlib import Path
from typing import Optional

from architecture_guard.rules import CRITICAL_LINES, EXCLUDED_PREFIXES, WARN_LINES

_PROJECT_ROOT = Path(__file__).parent.parent


def audit_project(root: Optional[Path] = None) -> list[dict]:
    """
    Scanne les fichiers Python du projet et retourne les alertes de taille.

    Retourne une liste de dicts triés par nombre de lignes décroissant :
        [{"file": "database.py", "lines": 719, "level": "CRITICAL"}, ...]
    """
    scan_root = root or _PROJECT_ROOT
    results = []

    for path in sorted(scan_root.glob("*.py")):
        name = path.name
        if any(name.startswith(p) for p in EXCLUDED_PREFIXES):
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").count("\n")
        except OSError:
            continue

        if lines >= CRITICAL_LINES:
            level = "CRITICAL"
        elif lines >= WARN_LINES:
            level = "WARN"
        else:
            continue

        results.append({"file": name, "lines": lines, "level": level})

    return sorted(results, key=lambda r: r["lines"], reverse=True)


def print_audit_report(root: Optional[Path] = None) -> None:
    items = audit_project(root)
    if not items:
        print("Architecture Guard: aucun fichier au-dessus des seuils.")
        return
    print(f"\n{'=' * 52}")
    print("  ARCHITECTURE GUARD — Audit fichiers")
    print(f"{'=' * 52}")
    for item in items:
        tag = f"[{item['level']}]"
        print(f"  {tag:<12} {item['file']:<36} {item['lines']:>4} lignes")
    print(f"{'=' * 52}\n")
