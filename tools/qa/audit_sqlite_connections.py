"""
tools/qa/audit_sqlite_connections.py

Audit statique read-only : détecte les utilisations de sqlite3.connect()
sans conn.close() explicite dans le code du projet.

Règles :
- Python 3.14 : with sqlite3.connect() as conn gère UNIQUEMENT la transaction,
  PAS la fermeture. conn.close() explicite obligatoire.
- Pour chaque sqlite3.connect(), vérifie qu'un conn.close() apparaît
  après la fin du bloc dans la même portée (fonction ou module).

Ignoré : .venv, backups, __pycache__, .git
Sortie  : OK / WARNING / UNKNOWN + verdict GO SAFE / WARNING
"""
import ast
import sys
from pathlib import Path

# Force UTF-8 sur Windows (cp1252 par défaut dans certains terminaux)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Configuration ──────────────────────────────────────────────────────────────

IGNORE_DIRS: frozenset[str] = frozenset({
    ".venv", "backups", "__pycache__", ".git", ".mypy_cache",
    "node_modules", ".pytest_cache",
})

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# ── AST Helpers ────────────────────────────────────────────────────────────────


def _is_sqlite3_connect(node: ast.expr) -> bool:
    """Vérifie si le nœud AST est un appel sqlite3.connect(...)."""
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "connect"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "sqlite3"
    )


def _iter_scope_nodes(node: ast.AST):
    """
    Parcourt récursivement le sous-arbre AST d'un nœud
    SANS descendre dans les définitions de fonctions imbriquées.
    """
    yield node
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        yield from _iter_scope_nodes(child)


# ── Collecte dans un scope ─────────────────────────────────────────────────────


def _collect_in_scope(
    stmts: list[ast.stmt],
) -> tuple[list[dict], dict[str, list[int]]]:
    """
    Collecte, dans une liste de statements d'un scope :
      - connects : [{line, end_line, varname, pattern}]
      - closes   : {varname: [lignes des .close()]}

    Ne descend PAS dans les définitions de fonctions imbriquées.
    """
    connects: list[dict] = []
    closes: dict[str, list[int]] = {}

    for stmt in stmts:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue  # analysé dans son propre scope

        for node in _iter_scope_nodes(stmt):

            # ── Pattern WITH : with sqlite3.connect(...) as conn: ──
            if isinstance(node, ast.With):
                for item in node.items:
                    if _is_sqlite3_connect(item.context_expr):
                        if isinstance(item.optional_vars, ast.Name):
                            varname: str | None = item.optional_vars.id
                        else:
                            varname = None
                        connects.append({
                            "line":     node.lineno,
                            "end_line": getattr(node, "end_lineno", node.lineno),
                            "varname":  varname,
                            "pattern":  "with",
                        })

            # ── Pattern ASSIGN : conn = sqlite3.connect(...) ──
            elif (
                isinstance(node, ast.Assign)
                and _is_sqlite3_connect(node.value)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
            ):
                varname = node.targets[0].id
                connects.append({
                    "line":     node.lineno,
                    "end_line": node.lineno,
                    "varname":  varname,
                    "pattern":  "assign",
                })

            # ── Close : varname.close() ──
            elif (
                isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Attribute)
                and node.value.func.attr == "close"
                and not node.value.args
                and isinstance(node.value.func.value, ast.Name)
            ):
                vn = node.value.func.value.id
                closes.setdefault(vn, []).append(node.lineno)

    return connects, closes


# ── Analyse fichier ────────────────────────────────────────────────────────────


def analyze_file(file_path: Path) -> list[dict]:
    """
    Parse un fichier Python et retourne la liste des findings
    (un finding par sqlite3.connect détecté).
    """
    try:
        source = file_path.read_text(encoding="utf-8", errors="replace")
        tree   = ast.parse(source, filename=str(file_path))
    except SyntaxError as exc:
        return [{
            "file":    file_path,
            "scope":   "?",
            "line":    0,
            "pattern": "?",
            "varname": None,
            "status":  "UNKNOWN",
            "detail":  f"SyntaxError: {exc}",
        }]

    # Scopes à analyser : module-level + toutes les fonctions/méthodes
    scopes: list[tuple[str, list[ast.stmt]]] = [("<module>", tree.body)]
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            scopes.append((node.name, node.body))

    findings: list[dict] = []

    for scope_name, body in scopes:
        connects, closes = _collect_in_scope(body)

        for c in connects:
            varname  = c["varname"]
            end_line = c["end_line"]

            if varname is None:
                status = "UNKNOWN"
                detail = "pas de 'as varname' — non vérifiable"
            else:
                close_lines = closes.get(varname, [])
                # conn.close() doit apparaître APRÈS la fin du bloc with/assign
                if any(ln > end_line for ln in close_lines):
                    status = "OK"
                    detail = f"{varname}.close() présent (L{min(ln for ln in close_lines if ln > end_line)})"
                else:
                    status = "WARNING"
                    detail = f"{varname}.close() MANQUANT après L{end_line}"

            findings.append({
                "file":    file_path,
                "scope":   scope_name,
                "line":    c["line"],
                "pattern": c["pattern"],
                "varname": varname,
                "status":  status,
                "detail":  detail,
            })

    return findings


# ── Collecte des fichiers ──────────────────────────────────────────────────────


def collect_python_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*.py"):
        rel_parts = path.relative_to(root).parts
        if any(p in IGNORE_DIRS for p in rel_parts):
            continue
        files.append(path)
    return sorted(files)


# ── Affichage ──────────────────────────────────────────────────────────────────


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def _print_findings(findings: list[dict], show_ok: bool = True) -> None:
    if not findings:
        return

    max_file_len = max(len(_rel(f["file"])) for f in findings)
    col_file  = min(max_file_len, 55)
    col_scope = 28

    for f in findings:
        if not show_ok and f["status"] == "OK":
            continue
        status   = f["status"]
        file_str = _rel(f["file"])[:col_file].ljust(col_file + 1)
        scope    = f["scope"][:col_scope].ljust(col_scope)
        line     = f"L{f['line']:<5}"
        badge = {"OK": " OK  ", "WARNING": "WARN ", "UNKNOWN": "UNK  "}.get(status, status)
        print(f"  [{badge}] {file_str} {line} {scope} {f['detail']}")


# ── Main ───────────────────────────────────────────────────────────────────────


def main() -> int:
    bar = "-" * 78

    print()
    print("=" * 78)
    print("  AUDIT SQLite Connections -- detection conn.close() manquant")
    print("=" * 78)
    print(f"  Racine  : {PROJECT_ROOT}")
    print(f"  Ignorés : {', '.join(sorted(IGNORE_DIRS))}")
    print()

    files = collect_python_files(PROJECT_ROOT)
    print(f"  Fichiers .py scannés : {len(files)}")
    print()

    all_findings: list[dict] = []
    for f in files:
        all_findings.extend(analyze_file(f))

    if not all_findings:
        print("  Aucune utilisation de sqlite3.connect trouvée.")
        print()
        print("  VERDICT : [OK] GO SAFE")
        print("=" * 78)
        return 0

    warnings = [f for f in all_findings if f["status"] == "WARNING"]
    oks       = [f for f in all_findings if f["status"] == "OK"]
    unknowns  = [f for f in all_findings if f["status"] == "UNKNOWN"]

    # ── Section WARNING (prioritaire) ──
    if warnings:
        print("  WARNINGS — connexions sans conn.close() :")
        print(bar)
        _print_findings(warnings, show_ok=True)
        print(bar)
        print()

    # ── Section OK ──
    print("  OK — connexions correctement fermées :")
    print(bar)
    _print_findings(oks, show_ok=True)
    if not oks:
        print("  (aucune)")
    print(bar)
    print()

    # ── Section UNKNOWN ──
    if unknowns:
        print("  UNKNOWN — non vérifiables (pas de 'as varname' ou SyntaxError) :")
        print(bar)
        _print_findings(unknowns, show_ok=True)
        print(bar)
        print()

    # ── Résumé ──
    print("  RÉSUMÉ")
    print(f"  {'Total sqlite3.connect':<30} : {len(all_findings)}")
    print(f"  {'OK':<30} : {len(oks)}")
    print(f"  {'WARNING':<30} : {len(warnings)}")
    print(f"  {'UNKNOWN':<30} : {len(unknowns)}")
    print()

    if warnings:
        print(f"  VERDICT : [!!] WARNING -- {len(warnings)} connexion(s) suspecte(s)")
        print()
        seen: set[str] = set()
        for f in warnings:
            fp = _rel(f["file"])
            key = f"{fp}:{f['line']}"
            if key not in seen:
                seen.add(key)
                print(f"    !!  {fp}  L{f['line']}  ({f['scope']})")
        print()
    else:
        print("  VERDICT : [OK] GO SAFE -- aucun WARNING dans le code projet")
        print()

    print("=" * 78)
    return 1 if warnings else 0


if __name__ == "__main__":
    sys.exit(main())
