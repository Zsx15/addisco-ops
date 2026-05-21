"""
Guardrails V1 — Moteur d'audit architectural déterministe.

Lecture seule. Ne modifie rien. Ne corrige rien.
Usage : python tools/guardrails/architecture_guardrails.py
"""

import ast
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, NamedTuple, Optional

# Ajoute la racine du projet au path pour l'exécution en script direct
_PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from tools.guardrails.rules import (
    EXCLUDED_DIRS,
    FILE_CRITICAL_LINES,
    FILE_WARN_LINES,
    FUNC_CRITICAL_LINES,
    FUNC_WARN_LINES,
    RUNTIME_CRITICAL,
    SECRET_PATTERNS,
    SECRETS_EXCLUDED_FILES,
)


class Finding(NamedTuple):
    level: str          # "WARNING" | "CRITICAL"
    rule: str
    file: str
    line: Optional[int]
    message: str


# ─── Utilitaires ──────────────────────────────────────────────────────────────

def _iter_py_files(root: Path) -> List[Path]:
    results = []
    for path in root.rglob("*.py"):
        parts = set(path.relative_to(root).parts)
        if parts & EXCLUDED_DIRS:
            continue
        results.append(path)
    return sorted(results)


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _read(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None


# ─── Règle 1 : Fichiers trop gros ─────────────────────────────────────────────

def check_file_sizes(root: Path) -> List[Finding]:
    findings = []
    for path in _iter_py_files(root):
        source = _read(path)
        if source is None:
            continue
        lines = source.count("\n")
        rel = _rel(path, root)
        if lines >= FILE_CRITICAL_LINES:
            findings.append(Finding("CRITICAL", "FILE_SIZE", rel, None, f"{lines} lignes"))
        elif lines >= FILE_WARN_LINES:
            findings.append(Finding("WARNING", "FILE_SIZE", rel, None, f"{lines} lignes"))
    return findings


# ─── Règle 2 : Fonctions trop longues ─────────────────────────────────────────

def check_function_lengths(root: Path) -> List[Finding]:
    findings = []
    for path in _iter_py_files(root):
        source = _read(path)
        if source is None:
            continue
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            continue
        rel = _rel(path, root)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            start = node.lineno
            end = getattr(node, "end_lineno", None) or start
            length = end - start + 1
            if length >= FUNC_CRITICAL_LINES:
                findings.append(Finding(
                    "CRITICAL", "FUNC_LENGTH", rel, start,
                    f"fonction {node.name}() = {length} lignes",
                ))
            elif length >= FUNC_WARN_LINES:
                findings.append(Finding(
                    "WARNING", "FUNC_LENGTH", rel, start,
                    f"fonction {node.name}() = {length} lignes",
                ))
    return findings


# ─── Règle 3 : Imports dangereux dans le runtime ──────────────────────────────

_IMPORT_TOOLS_RE = re.compile(r"\s*(?:import|from)\s+tools[.\s]")


def check_dangerous_imports(root: Path) -> List[Finding]:
    findings = []
    for path in _iter_py_files(root):
        if path.name not in RUNTIME_CRITICAL:
            continue
        source = _read(path)
        if source is None:
            continue
        rel = _rel(path, root)
        for i, line in enumerate(source.splitlines(), 1):
            if _IMPORT_TOOLS_RE.match(line):
                findings.append(Finding(
                    "CRITICAL", "DANGEROUS_IMPORT", rel, i,
                    f"import tools/ dans fichier runtime : {line.strip()}",
                ))
    return findings


# ─── Règle 4 : SQL sans LIMIT ─────────────────────────────────────────────────

_SELECT_STAR_RE = re.compile(r"SELECT\s+\*\s+FROM\s+(\w+)", re.IGNORECASE)
_LIMIT_RE = re.compile(r"\bLIMIT\b", re.IGNORECASE)
_WHERE_RE = re.compile(r"\bWHERE\b", re.IGNORECASE)


def check_sql_without_limit(root: Path) -> List[Finding]:
    findings = []
    for path in _iter_py_files(root):
        source = _read(path)
        if source is None:
            continue
        rel = _rel(path, root)
        for i, line in enumerate(source.splitlines(), 1):
            m = _SELECT_STAR_RE.search(line)
            if not m:
                continue
            if _LIMIT_RE.search(line):
                continue
            table = m.group(1)
            has_where = bool(_WHERE_RE.search(line))
            level = "WARNING" if has_where else "CRITICAL"
            findings.append(Finding(
                level, "SQL_NO_LIMIT", rel, i,
                f"SELECT * FROM {table} sans LIMIT",
            ))
    return findings


# ─── Règle 5 : Secrets potentiels ─────────────────────────────────────────────

_COMPILED_SECRETS = [re.compile(p, re.IGNORECASE) for p in SECRET_PATTERNS]
# Exemption : usages via os.getenv / os.environ (valeur lue, non hardcodée)
_SAFE_CONTEXT_RE = re.compile(r"os\.(?:getenv|environ)", re.IGNORECASE)


def check_secrets(root: Path) -> List[Finding]:
    findings = []
    for path in _iter_py_files(root):
        if path.name in SECRETS_EXCLUDED_FILES:
            continue
        source = _read(path)
        if source is None:
            continue
        rel = _rel(path, root)
        for i, line in enumerate(source.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if _SAFE_CONTEXT_RE.search(line):
                continue
            for pattern in _COMPILED_SECRETS:
                if pattern.search(line):
                    findings.append(Finding(
                        "WARNING", "SECRET", rel, i,
                        "valeur potentiellement sensible detectee",
                    ))
                    break
    return findings


# ─── Règle 6 : Streamlit lourd ────────────────────────────────────────────────

_ST_RENDER_RE = re.compile(r"\bst\.(dataframe|table)\s*\(")
_LOOP_RE = re.compile(r"^\s*(for |while )")
_LOOP_CONTEXT_WINDOW = 8  # lignes remontées pour détecter un bloc boucle


def check_streamlit_heavy(root: Path) -> List[Finding]:
    findings = []
    for path in _iter_py_files(root):
        source = _read(path)
        if source is None:
            continue
        rel = _rel(path, root)
        lines = source.splitlines()
        for i, line in enumerate(lines, 1):
            if not _ST_RENDER_RE.search(line):
                continue
            context_start = max(0, i - 1 - _LOOP_CONTEXT_WINDOW)
            context = lines[context_start: i - 1]
            if any(_LOOP_RE.match(l) for l in context):
                findings.append(Finding(
                    "WARNING", "STREAMLIT_HEAVY", rel, i,
                    "st.dataframe/table potentiellement dans une boucle",
                ))
    return findings


# ─── Rapport ──────────────────────────────────────────────────────────────────

_SEVERITY_ORDER = {"CRITICAL": 0, "WARNING": 1}

_RULE_LABELS = {
    "FILE_SIZE": "Fichier trop gros",
    "FUNC_LENGTH": "Fonction trop longue",
    "DANGEROUS_IMPORT": "Import dangereux",
    "SQL_NO_LIMIT": "SQL sans LIMIT",
    "SECRET": "Secret potentiel",
    "STREAMLIT_HEAVY": "Streamlit lourd",
}


def _print_report(findings: List[Finding]) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sep = "=" * 60
    print(f"\n{sep}")
    print(f"  GUARDRAILS REPORT -- {ts}")
    print(sep)

    if not findings:
        print("\n  Aucune anomalie detectee.\n")
        return

    current_level: Optional[str] = None
    for f in findings:
        if f.level != current_level:
            current_level = f.level
            print(f"\n[{f.level}]")
        rule_label = _RULE_LABELS.get(f.rule, f.rule)
        loc = f" ligne {f.line}" if f.line else ""
        print(f"  [{rule_label}] {f.file}{loc} -> {f.message}")


def run_audit(root: Optional[Path] = None) -> int:
    """
    Lance l'audit complet. Retourne :
      0 → GO SAFE
      1 → WARNING
      2 → FAILED (au moins un CRITICAL)
    """
    scan_root = root or _PROJECT_ROOT

    all_findings: List[Finding] = (
        check_file_sizes(scan_root)
        + check_function_lengths(scan_root)
        + check_dangerous_imports(scan_root)
        + check_sql_without_limit(scan_root)
        + check_secrets(scan_root)
        + check_streamlit_heavy(scan_root)
    )

    # Tri : CRITICAL en premier, puis par fichier
    all_findings.sort(key=lambda f: (_SEVERITY_ORDER.get(f.level, 9), f.file, f.line or 0))

    _print_report(all_findings)

    has_critical = any(f.level == "CRITICAL" for f in all_findings)
    has_warning = any(f.level == "WARNING" for f in all_findings)

    if has_critical:
        verdict, code = "FAILED", 2
    elif has_warning:
        verdict, code = "WARNING", 1
    else:
        verdict, code = "GO SAFE", 0

    sep = "=" * 60
    print(f"\n{sep}")
    print(f"  VERDICT : {verdict}")
    print(f"{sep}\n")

    return code


if __name__ == "__main__":
    sys.exit(run_audit())
