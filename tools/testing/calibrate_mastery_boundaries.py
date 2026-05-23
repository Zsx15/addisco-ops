#!/usr/bin/env python
"""
calibrate_mastery_boundaries.py — TASK-075
Calibration des seuils MASTERY_FRAGILE et MASTERY_MASTERED.

  SECTION A : MASTERY_FRAGILE  — pivot Fragile / En cours
  SECTION B : MASTERY_MASTERED — pivot En cours / Acquis
  SECTION C : validation DB pipeline (valeurs actuelles)

Ne modifie pas engine/thresholds.py : patch en mémoire, restauration garantie.
DB isolé : données réelles jamais touchées.

Usage :
  python tools/testing/calibrate_mastery_boundaries.py
  python tools/testing/calibrate_mastery_boundaries.py --fragile 0.50 0.55 0.60 0.65
  python tools/testing/calibrate_mastery_boundaries.py --mastered 0.75 0.80 0.85
  python tools/testing/calibrate_mastery_boundaries.py --skip-db
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import logging
logging.basicConfig(level=logging.WARNING)

import database as _db
import engine.thresholds  as _thr
import engine.skill_engine as _sk_eng

SEP  = "─" * 72
SEP2 = "━" * 72

_ORIG_FRAGILE      = _thr.MASTERY_FRAGILE
_ORIG_MASTERED     = _thr.MASTERY_MASTERED
_ORIG_MIN_ATTEMPTS = _thr.MASTERY_MIN_ATTEMPTS

# Candidats par défaut
_DEFAULT_FRAGILE_VALS  = [0.50, 0.55, 0.60, 0.65]
_DEFAULT_MASTERED_VALS = [0.75, 0.78, 0.80, 0.83, 0.85]

# Scores de test (couvrent la zone de transition pour chaque paramètre)
_FRAGILE_TEST_SCORES  = [0.45, 0.50, 0.55, 0.57, 0.60, 0.63, 0.67, 0.72]
_MASTERED_TEST_SCORES = [0.70, 0.74, 0.77, 0.79, 0.81, 0.83, 0.87, 0.92]

# Cas limites pour la validation DB (valeurs actuelles)
_DB_CASES = [
    (0.58, "Fragile"),   # juste sous MASTERY_FRAGILE=0.60
    (0.62, "En cours"),  # juste au-dessus de MASTERY_FRAGILE
    (0.79, "En cours"),  # juste sous MASTERY_MASTERED=0.80
    (0.82, "Acquis"),    # juste au-dessus, avec n >= MIN_ATTEMPTS
]

# ── Patch / restore ───────────────────────────────────────────────────────────

def _patch_fragile(v: float) -> None:
    _thr.MASTERY_FRAGILE    = v
    _sk_eng.MASTERY_FRAGILE = v


def _patch_mastered(v: float) -> None:
    _thr.MASTERY_MASTERED    = v
    _sk_eng.MASTERY_MASTERED = v


def _restore() -> None:
    _thr.MASTERY_FRAGILE     = _ORIG_FRAGILE
    _thr.MASTERY_MASTERED    = _ORIG_MASTERED
    _sk_eng.MASTERY_FRAGILE  = _ORIG_FRAGILE
    _sk_eng.MASTERY_MASTERED = _ORIG_MASTERED


# ── Analyse pure (sans DB) ────────────────────────────────────────────────────

def analyze_fragile(candidates: list[float], test_scores: list[float], n: int) -> dict:
    """Matrice {fragile_val: {score: label}}. Restauration garantie."""
    try:
        matrix: dict[float, dict[float, str]] = {}
        for fv in candidates:
            _patch_fragile(fv)
            matrix[fv] = {
                s: _sk_eng.classify_skill_mastery(s, n)
                for s in test_scores
            }
        return matrix
    finally:
        _restore()


def analyze_mastered(candidates: list[float], test_scores: list[float], n: int) -> dict:
    """Matrice {mastered_val: {score: label}}. Restauration garantie."""
    try:
        matrix: dict[float, dict[float, str]] = {}
        for mv in candidates:
            _patch_mastered(mv)
            matrix[mv] = {
                s: _sk_eng.classify_skill_mastery(s, n)
                for s in test_scores
            }
        return matrix
    finally:
        _restore()


# ── Affichage ─────────────────────────────────────────────────────────────────

_SHORT = {"Fragile": "F", "En cours": "C", "Acquis": "A"}


def _print_table(
    matrix: dict,
    test_scores: list[float],
    param_name: str,
    current_val: float,
) -> None:
    col = 8
    header = f"  {param_name:<20}"
    for s in test_scores:
        header += f"  {s:.2f} "
    print(header)
    print("  " + "─" * (20 + len(test_scores) * col))

    for pv, row in sorted(matrix.items()):
        tag = " ←" if abs(pv - current_val) < 0.001 else "  "
        line = f"  {pv:.2f}{tag:<18}"
        prev: Optional[str] = None
        for s in sorted(test_scores):
            label = row[s]
            sep = "│" if (prev is not None and prev != label) else " "
            line += f"  {sep}{_SHORT.get(label, label[:1])}      "
            prev = label
        print(line)

    print()
    print("  F=Fragile  C=En cours  A=Acquis  │=transition  ←=valeur actuelle")


# ── Recommandations ───────────────────────────────────────────────────────────

def _transition_score(row: dict[float, str], from_label: str, to_label: str) -> Optional[float]:
    """Premier score classifié to_label après une série de from_label."""
    sorted_scores = sorted(row.keys())
    prev: Optional[str] = None
    for s in sorted_scores:
        if row[s] == to_label and prev == from_label:
            return s
        prev = row[s]
    return None


def recommend_fragile(matrix: dict, current: float) -> str:
    lines: list[str] = []
    for fv, row in sorted(matrix.items()):
        t = _transition_score(row, "Fragile", "En cours")
        if t is None:
            all_labels = set(row.values())
            verdict = "TROP_STRICT (aucun score n'atteint En cours)" if "En cours" not in all_labels \
                      else "TROP_PERMISSIF (aucun score classifié Fragile)"
        elif t < 0.53:
            verdict = "TROP_PERMISSIF (transition trop basse)"
        elif t <= 0.65:
            verdict = "OK"
        else:
            verdict = "TROP_STRICT (transition trop haute)"
        mark = " ← actuel" if abs(fv - current) < 0.001 else ""
        lines.append(f"  FRAGILE={fv:.2f} : transition F→C à score {t or '—'} → {verdict}{mark}")
    return "\n".join(lines)


def recommend_mastered(matrix: dict, current: float, n: int) -> str:
    lines: list[str] = []
    for mv, row in sorted(matrix.items()):
        t = _transition_score(row, "En cours", "Acquis")
        if t is None:
            all_labels = set(row.values())
            verdict = "TROP_STRICT (aucun score n'atteint Acquis)" if "Acquis" not in all_labels \
                      else "TROP_PERMISSIF (tout Acquis)"
        elif t < 0.76:
            verdict = "TROP_PERMISSIF (maîtrise déclarée trop vite)"
        elif t <= 0.85:
            verdict = "OK"
        else:
            verdict = "TROP_STRICT (maîtrise presque inatteignable)"
        mark = " ← actuel" if abs(mv - current) < 0.001 else ""
        lines.append(f"  MASTERED={mv:.2f} : transition C→A à score {t or '—'} → {verdict}{mark}")
    return "\n".join(lines)


# ── DB validation ─────────────────────────────────────────────────────────────

def _setup_db(real_db: Path) -> tuple[Path, str, int, int, str]:
    tmp = Path(tempfile.mktemp(suffix="_calib_bnd.db"))
    shutil.copy(str(real_db), str(tmp))
    uid = str(uuid.uuid4())

    conn = sqlite3.connect(str(tmp))
    conn.execute("DELETE FROM attempts")
    conn.execute("DELETE FROM user_learning_profile")
    conn.execute("DELETE FROM user_skill_mastery")
    conn.execute("DELETE FROM runtime_metrics")
    conn.execute("DELETE FROM users WHERE username LIKE 'calibration%'")
    conn.execute(
        "INSERT OR IGNORE INTO users (user_id, username, role, password_hash) "
        "VALUES (?, 'calibration_boundary', 'apprenant', 'x')",
        (uid,),
    )
    conn.commit()

    row = conn.execute(
        """SELECT cs.chunk_id, c.document_id, s.slug
           FROM chunk_skills cs
           JOIN skills s ON cs.skill_id = s.id
           JOIN chunks  c ON cs.chunk_id = c.id
           WHERE cs.is_active = 1 AND c.chunk_text IS NOT NULL
             AND length(c.chunk_text) > 100
           LIMIT 1"""
    ).fetchone()
    conn.close()

    if not row:
        raise RuntimeError("Aucun chunk avec skill association.")
    return tmp, uid, row[0], row[1], row[2]


def _inject_n(conn: sqlite3.Connection, user_id: str,
              chunk_id: int, doc_id: int, score: float, n: int) -> None:
    for _ in range(n):
        conn.execute(
            """INSERT INTO attempts
               (user_id, question, user_answer, expected_answer,
                correction, score, error_type, pedagogy_type, document_id, chunk_id)
               VALUES (?, 'Q calib', 'R calib', 'E calib',
                       'C calib', ?, 'correct', 'question_directe', ?, ?)""",
            (user_id, score, doc_id, chunk_id),
        )
    conn.commit()


def run_db_validation(
    tmp: Path,
    user_id: str,
    chunk_id: int,
    doc_id: int,
    skill_slug: str,
    cases: list[tuple[float, str]],
    n: int,
) -> list[dict]:
    from db.skills import update_user_skill_mastery, get_user_skill_mastery

    results: list[dict] = []
    for (score, expected) in cases:
        conn = sqlite3.connect(str(tmp))
        conn.execute("DELETE FROM attempts WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM user_skill_mastery WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM user_learning_profile WHERE user_id = ?", (user_id,))
        conn.commit()
        _inject_n(conn, user_id, chunk_id, doc_id, score, n)
        conn.close()

        update_user_skill_mastery(user_id)

        skill_data = get_user_skill_mastery(user_id) or []
        observed = "Fragile"
        for s in skill_data:
            if s["slug"] == skill_slug:
                observed = _sk_eng.classify_skill_mastery(
                    s["mastery_score"], s["attempts_count"]
                )
                break

        results.append({
            "score":    score,
            "n":        n,
            "expected": expected,
            "observed": observed,
            "passed":   observed == expected,
        })
    return results


# ── Copy block ────────────────────────────────────────────────────────────────

def _copy_block(
    fragile_matrix: dict,
    mastered_matrix: dict,
    db_results: list[dict],
    fragile_scores: list[float],
    mastered_scores: list[float],
    n: int,
) -> str:
    lines = ["=== COPY_FOR_ANALYSIS_START ==="]
    lines.append("# Mastery Boundary Calibration — TASK-075")
    lines.append(f"- MIN_ATTEMPTS utilisé   : {n}")
    lines.append(f"- MASTERY_FRAGILE actuel : {_ORIG_FRAGILE}")
    lines.append(f"- MASTERY_MASTERED actuel: {_ORIG_MASTERED}")
    lines.append("")

    lines.append("## SECTION A — MASTERY_FRAGILE")
    header = "| MASTERY_FRAGILE | " + " | ".join(f"s={s:.2f}" for s in sorted(fragile_scores)) + " |"
    lines.append(header)
    lines.append("|" + "---|" * (1 + len(fragile_scores)))
    for fv, row in sorted(fragile_matrix.items()):
        mark = " ←" if abs(fv - _ORIG_FRAGILE) < 0.001 else ""
        cells = " | ".join(_SHORT.get(row[s], "?") for s in sorted(fragile_scores))
        lines.append(f"| {fv:.2f}{mark} | {cells} |")
    lines.append("")

    lines.append("## SECTION B — MASTERY_MASTERED")
    header = "| MASTERY_MASTERED | " + " | ".join(f"s={s:.2f}" for s in sorted(mastered_scores)) + " |"
    lines.append(header)
    lines.append("|" + "---|" * (1 + len(mastered_scores)))
    for mv, row in sorted(mastered_matrix.items()):
        mark = " ←" if abs(mv - _ORIG_MASTERED) < 0.001 else ""
        cells = " | ".join(_SHORT.get(row[s], "?") for s in sorted(mastered_scores))
        lines.append(f"| {mv:.2f}{mark} | {cells} |")
    lines.append("")

    if db_results:
        lines.append("## SECTION C — DB pipeline")
        lines.append("| Score | n | Attendu | Observé | Résultat |")
        lines.append("|---|---|---|---|---|")
        for r in db_results:
            lines.append(
                f"| {r['score']} | {r['n']} | {r['expected']} "
                f"| {r['observed']} | {'PASS' if r['passed'] else 'FAIL'} |"
            )
        n_pass = sum(1 for r in db_results if r["passed"])
        lines.append(f"\nDB pipeline : {n_pass}/{len(db_results)} PASS")
        lines.append("")

    lines.append("=== COPY_FOR_ANALYSIS_END ===")
    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Mastery Boundary Calibration — TASK-075")
    parser.add_argument("--fragile",  nargs="+", type=float, default=_DEFAULT_FRAGILE_VALS)
    parser.add_argument("--mastered", nargs="+", type=float, default=_DEFAULT_MASTERED_VALS)
    parser.add_argument("--n",        type=int,   default=_ORIG_MIN_ATTEMPTS,
                        help=f"Tentatives pour la validation DB (défaut: {_ORIG_MIN_ATTEMPTS})")
    parser.add_argument("--skip-db",  action="store_true", help="Passer la section C (DB)")
    parser.add_argument("--keep-db",  action="store_true")
    args = parser.parse_args()

    print(f"\n{SEP2}")
    print("  ADDISCO OPS — Mastery Boundary Calibration (TASK-075)")
    print(SEP2)
    print(f"  MASTERY_FRAGILE  candidats : {args.fragile}")
    print(f"  MASTERY_MASTERED candidats : {args.mastered}")
    print(f"  MIN_ATTEMPTS (référence)   : {_ORIG_MIN_ATTEMPTS}")
    print(f"  Valeurs actuelles          : FRAGILE={_ORIG_FRAGILE}  MASTERED={_ORIG_MASTERED}")

    # ── SECTION A ─────────────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("  SECTION A — MASTERY_FRAGILE : pivot Fragile / En cours")
    print("  Question : à quel score moyen l'apprenant sort-il de Fragile ?")
    print(SEP)

    fragile_matrix = analyze_fragile(args.fragile, _FRAGILE_TEST_SCORES, args.n)
    _print_table(fragile_matrix, _FRAGILE_TEST_SCORES, "MASTERY_FRAGILE", _ORIG_FRAGILE)

    print("  Recommandations :")
    print(recommend_fragile(fragile_matrix, _ORIG_FRAGILE))
    print("\n  Enjeu pédagogique :")
    print("  - Trop bas (0.50) : apprenants fragiles échappent au mode remédiation")
    print("  - Trop haut (0.65) : apprenants qui progressent bloqués en remédiation")

    # ── SECTION B ─────────────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("  SECTION B — MASTERY_MASTERED : pivot En cours / Acquis")
    print("  Question : à quel score moyen l'apprenant est-il déclaré Acquis ?")
    print(SEP)

    mastered_matrix = analyze_mastered(args.mastered, _MASTERED_TEST_SCORES, args.n)
    _print_table(mastered_matrix, _MASTERED_TEST_SCORES, "MASTERY_MASTERED", _ORIG_MASTERED)

    print("  Recommandations :")
    print(recommend_mastered(mastered_matrix, _ORIG_MASTERED, args.n))
    print(f"\n  Enjeu pédagogique (n >= {_ORIG_MIN_ATTEMPTS} requis) :")
    print("  - Trop bas (0.75) : maîtrise déclarée trop vite, risque de régression")
    print("  - Trop haut (0.85) : peu d'apprenants atteignent Acquis, démotivant")

    # ── SECTION C ─────────────────────────────────────────────────────────────
    db_results: list[dict] = []
    tmp: Optional[Path] = None

    if not args.skip_db:
        print(f"\n{SEP}")
        print("  SECTION C — Validation DB pipeline (valeurs actuelles)")
        print(f"  Injecte {args.n} attempts aux scores limites, vérifie le pipeline complet")
        print(SEP)
        try:
            real_db = Path(str(_db.DB_PATH))
            if not real_db.exists():
                _db.init_db()
            tmp, uid, chunk_id, doc_id, skill_slug = _setup_db(real_db)
            _db.DB_PATH = type(_db.DB_PATH)(str(tmp))
            print(f"  DB temp : {tmp}")
            print(f"  Skill   : {skill_slug}  (chunk_id={chunk_id})\n")

            db_results = run_db_validation(
                tmp, uid, chunk_id, doc_id, skill_slug, _DB_CASES, args.n
            )
            for r in db_results:
                icon = "✓" if r["passed"] else "✗"
                print(f"  {icon}  score={r['score']}  n={r['n']:<3}  "
                      f"attendu={r['expected']:<12}  observé={r['observed']}")
            n_pass = sum(1 for r in db_results if r["passed"])
            ok_str = "OK" if n_pass == len(db_results) else "FAIL — divergence pipeline"
            print(f"\n  DB pipeline : {n_pass}/{len(db_results)} PASS  [{ok_str}]")
        except Exception as exc:
            print(f"  [WARN] Section C ignorée : {exc}")

    # ── Synthèse ──────────────────────────────────────────────────────────────
    print(f"\n{SEP2}")
    print("  SYNTHÈSE")
    print(SEP2)

    if _ORIG_FRAGILE in fragile_matrix:
        row = fragile_matrix[_ORIG_FRAGILE]
        t = _transition_score(row, "Fragile", "En cours")
        print(f"  MASTERY_FRAGILE={_ORIG_FRAGILE}  : transition F→C à score {t or '—'}")
    if _ORIG_MASTERED in mastered_matrix:
        row = mastered_matrix[_ORIG_MASTERED]
        t = _transition_score(row, "En cours", "Acquis")
        print(f"  MASTERY_MASTERED={_ORIG_MASTERED} : transition C→A à score {t or '—'} (n>={_ORIG_MIN_ATTEMPTS})")
    if db_results:
        n_pass = sum(1 for r in db_results if r["passed"])
        print(f"  DB pipeline      : {n_pass}/{len(db_results)} cas limites validés")

    # ── Cleanup ───────────────────────────────────────────────────────────────
    if tmp and not args.keep_db:
        try:
            tmp.unlink()
        except Exception:
            pass

    # ── Copy block ────────────────────────────────────────────────────────────
    block = _copy_block(
        fragile_matrix, mastered_matrix, db_results,
        _FRAGILE_TEST_SCORES, _MASTERED_TEST_SCORES, args.n,
    )
    print(f"\n{block}\n")


if __name__ == "__main__":
    main()
