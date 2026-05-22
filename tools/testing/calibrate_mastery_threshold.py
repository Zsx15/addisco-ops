#!/usr/bin/env python
"""
calibrate_mastery_threshold.py — TASK-074B
Impact de MASTERY_MIN_ATTEMPTS (3, 5, 8) sur la progression mastery SEQ-C.

Ne modifie pas engine/thresholds.py : patch en mémoire, restauration garantie.

Usage :
  python tools/testing/calibrate_mastery_threshold.py
  python tools/testing/calibrate_mastery_threshold.py --values 3 5 8 10
  python tools/testing/calibrate_mastery_threshold.py --n 30 --score 0.85
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

# ── Encodage Windows ──────────────────────────────────────────────────────────
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Racine du projet ──────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import logging
logging.basicConfig(level=logging.WARNING)

import database as _db
import engine.thresholds  as _thr
import engine.skill_engine as _sk_eng
import engine.spaced_rep   as _sp_rep

SEP  = "─" * 72
SEP2 = "━" * 72

# Valeurs actuelles (référence)
_ORIG_MIN_ATTEMPTS = _thr.MASTERY_MIN_ATTEMPTS
_ORIG_FRAGILE      = _thr.MASTERY_FRAGILE
_ORIG_MASTERED     = _thr.MASTERY_MASTERED


# ── Patch / restore ───────────────────────────────────────────────────────────

def _patch(min_attempts: int) -> None:
    _thr.MASTERY_MIN_ATTEMPTS     = min_attempts
    _sk_eng.MASTERY_MIN_ATTEMPTS  = min_attempts
    _sp_rep.MASTERY_MIN_ATTEMPTS  = min_attempts


def _restore() -> None:
    _thr.MASTERY_MIN_ATTEMPTS     = _ORIG_MIN_ATTEMPTS
    _sk_eng.MASTERY_MIN_ATTEMPTS  = _ORIG_MIN_ATTEMPTS
    _sp_rep.MASTERY_MIN_ATTEMPTS  = _ORIG_MIN_ATTEMPTS


# ── DB isolé ─────────────────────────────────────────────────────────────────

def _setup_db(real_db: Path) -> tuple[Path, str, int, int, str]:
    """
    Copie le vrai DB, nettoie les données user, crée calibration_user.
    Retourne (tmp_path, user_id, chunk_id, doc_id, skill_slug).
    """
    tmp = Path(tempfile.mktemp(suffix="_calib_mastery.db"))
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
        "VALUES (?, 'calibration_mastery', 'apprenant', 'x')",
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


def _reset_user(tmp: Path, user_id: str) -> None:
    conn = sqlite3.connect(str(tmp))
    conn.execute("DELETE FROM attempts WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM user_skill_mastery WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM user_learning_profile WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def _inject_one(conn: sqlite3.Connection, user_id: str,
                chunk_id: int, doc_id: int, score: float) -> None:
    conn.execute(
        """INSERT INTO attempts
           (user_id, question, user_answer, expected_answer,
            correction, score, error_type, pedagogy_type, document_id, chunk_id)
           VALUES (?, 'Q calib', 'R calib', 'E calib',
                   'C calib', ?, 'correct', 'question_directe', ?, ?)""",
        (user_id, score, doc_id, chunk_id),
    )
    conn.commit()


def _get_mastery(user_id: str, skill_slug: str) -> tuple[float, int, str]:
    """Retourne (mastery_score, attempts_count, label)."""
    from db.skills import get_user_skill_mastery
    from engine.skill_engine import classify_skill_mastery
    try:
        skills = get_user_skill_mastery(user_id) or []
        for s in skills:
            if s["slug"] == skill_slug:
                label = classify_skill_mastery(s["mastery_score"], s["attempts_count"])
                return s["mastery_score"], s["attempts_count"], label
    except Exception:
        pass
    return 0.0, 0, "Fragile"


# ── Séquence SEQ-C pour un seuil donné ───────────────────────────────────────

def run_seq_c(
    tmp: Path,
    user_id: str,
    chunk_id: int,
    doc_id: int,
    skill_slug: str,
    n: int,
    score: float,
    min_attempts: int,
) -> dict:
    """
    Injecte n tentatives correctes une par une.
    Retourne l'historique de transition + Q# de chaque changement d'état.
    """
    from db.skills import update_user_skill_mastery

    _reset_user(tmp, user_id)
    _patch(min_attempts)

    conn = sqlite3.connect(str(tmp))

    history: list[dict] = []
    prev_label  = "Fragile"
    q_fragile_to_encours: Optional[int] = None
    q_encours_to_acquis:  Optional[int] = None

    try:
        for q in range(1, n + 1):
            _inject_one(conn, user_id, chunk_id, doc_id, score)
            update_user_skill_mastery(user_id)

            m_score, m_count, label = _get_mastery(user_id, skill_slug)

            if prev_label == "Fragile" and label in ("En cours", "Acquis"):
                q_fragile_to_encours = q
            if prev_label in ("Fragile", "En cours") and label == "Acquis":
                q_encours_to_acquis = q

            history.append({
                "q":      q,
                "score":  round(m_score, 3),
                "n":      m_count,
                "label":  label,
            })
            prev_label = label

            # Arrêt anticipé une fois Acquis stable
            if label == "Acquis" and q >= min_attempts:
                # Poursuivre jusqu'à n pour mesurer la stabilité
                pass

    finally:
        conn.close()
        _restore()

    return {
        "min_attempts":          min_attempts,
        "skill":                 skill_slug,
        "history":               history,
        "q_fragile_to_encours":  q_fragile_to_encours,
        "q_encours_to_acquis":   q_encours_to_acquis,
        "final_label":           history[-1]["label"] if history else "Fragile",
        "final_score":           history[-1]["score"] if history else 0.0,
    }


# ── Rapport ───────────────────────────────────────────────────────────────────

def _verdict(r: dict) -> str:
    q_acquis = r["q_encours_to_acquis"] or r["q_fragile_to_encours"]
    if q_acquis is None:
        return "NO_REACTION"
    if q_acquis <= 3:
        return "TOO_FAST"
    if q_acquis <= 8:
        return "OK"
    return "TOO_SLOW"


def _recommend(results: list[dict]) -> str:
    """Recommandation basée sur les résultats comparatifs."""
    ok = [r for r in results if _verdict(r) == "OK"]
    if not ok:
        fast = [r for r in results if _verdict(r) == "TOO_FAST"]
        slow = [r for r in results if _verdict(r) == "TOO_SLOW"]
        if fast and not slow:
            return f"Tous les seuils testés sont TOO_FAST. Augmenter au-delà de {max(r['min_attempts'] for r in fast)}."
        if slow and not fast:
            return f"Tous les seuils testés sont TOO_SLOW. Diminuer en-dessous de {min(r['min_attempts'] for r in slow)}."
        return "Résultats mixtes — affiner la plage testée."

    # Parmi les OK, préférer le seuil le plus élevé (plus conservateur)
    best = max(ok, key=lambda r: r["min_attempts"])
    q = best["q_encours_to_acquis"] or best["q_fragile_to_encours"]
    return (
        f"MASTERY_MIN_ATTEMPTS = {best['min_attempts']} recommandé : "
        f"'Acquis' atteint à Q{q} — équilibre réactivité / robustesse."
    )


def _print_table(results: list[dict], n: int) -> None:
    print(f"\n{'Q':>4}", end="")
    for r in results:
        h = f"MIN={r['min_attempts']}"
        print(f"  {h:^16}", end="")
    print()
    print("  " + "─" * (4 + len(results) * 18))

    for q in range(1, n + 1):
        print(f"  Q{q:>02}", end="")
        for r in results:
            entry = next((e for e in r["history"] if e["q"] == q), None)
            if entry:
                label = entry["label"]
                score = entry["score"]
                cell  = f"{label} ({score:.2f})"
            else:
                cell = "—"
            # Highlight transitions
            transitions = []
            if r["q_fragile_to_encours"] == q:
                transitions.append("←")
            if r["q_encours_to_acquis"] == q:
                transitions.append("★")
            marker = "".join(transitions)
            print(f"  {cell:<14}{marker:>2}", end="")
        print()

    print()
    print(f"  {'':4}", end="")
    for r in results:
        v = _verdict(r)
        q_t = r["q_encours_to_acquis"] or r["q_fragile_to_encours"] or "—"
        cell = f"[{v}] Q{q_t}"
        print(f"  {cell:^16}", end="")
    print()


def _copy_block(results: list[dict], score: float, n: int) -> str:
    lines = ["=== COPY_FOR_ANALYSIS_START ==="]
    lines.append("# Mastery Threshold Calibration — TASK-074B")
    lines.append(f"- Score injecté      : {score}")
    lines.append(f"- Tentatives max     : {n}")
    lines.append(f"- MASTERY_FRAGILE    : {_ORIG_FRAGILE}")
    lines.append(f"- MASTERY_MASTERED   : {_ORIG_MASTERED}")
    lines.append("")
    lines.append("## Résultats comparatifs")
    lines.append("")
    lines.append("| MIN_ATTEMPTS | Fragile→En cours | En cours→Acquis | Verdict |")
    lines.append("|---|---|---|---|")
    for r in results:
        q_f = r["q_fragile_to_encours"] or "—"
        q_a = r["q_encours_to_acquis"]  or "—"
        v   = _verdict(r)
        current = " ← actuel" if r["min_attempts"] == _ORIG_MIN_ATTEMPTS else ""
        lines.append(f"| {r['min_attempts']}{current} | Q{q_f} | Q{q_a} | {v} |")
    lines.append("")
    lines.append("## Interprétation")
    lines.append(f"- ← (Fragile→En cours) : première tentative avec score >= {_ORIG_FRAGILE}")
    lines.append(f"- ★ (En cours→Acquis)  : score >= {_ORIG_MASTERED} ET n >= MIN_ATTEMPTS")
    lines.append("")
    lines.append("## Recommandation")
    lines.append(_recommend(results))
    lines.append("")
    lines.append("## Risques")
    lines.append("- TOO_FAST : l'apprenant est déclaré 'Acquis' après trop peu de tentatives")
    lines.append("  → risque de sous-entraînement, révision espacée trop rare")
    lines.append("- TOO_SLOW : l'apprenant reste 'En cours' longtemps malgré de bons scores")
    lines.append("  → risque de démotivation, curriculum trop conservateur")
    lines.append("=== COPY_FOR_ANALYSIS_END ===")
    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Mastery Threshold Calibration — TASK-074B")
    parser.add_argument("--values", nargs="+", type=int, default=[3, 5, 8],
                        help="Valeurs de MASTERY_MIN_ATTEMPTS à tester")
    parser.add_argument("--n",     type=int,   default=20,
                        help="Nombre de tentatives par séquence (défaut: 20)")
    parser.add_argument("--score", type=float, default=0.90,
                        help="Score injecté (défaut: 0.90)")
    parser.add_argument("--keep-db", action="store_true")
    args = parser.parse_args()

    print(f"\n{SEP2}")
    print("  ADDISCO OPS — Mastery Threshold Calibration (TASK-074B)")
    print(SEP2)
    print(f"  MASTERY_MIN_ATTEMPTS testés : {args.values}")
    print(f"  Score injecté               : {args.score}")
    print(f"  Tentatives max              : {args.n}")
    print(f"  Seuil actuel                : MIN_ATTEMPTS={_ORIG_MIN_ATTEMPTS}  "
          f"FRAGILE={_ORIG_FRAGILE}  MASTERED={_ORIG_MASTERED}")

    # DB isolé
    real_db = Path(str(_db.DB_PATH))
    tmp, user_id, chunk_id, doc_id, skill_slug = _setup_db(real_db)
    _db.DB_PATH = type(_db.DB_PATH)(str(tmp))

    print(f"  DB temp     : {tmp}")
    print(f"  Skill testé : {skill_slug}  (chunk_id={chunk_id})")

    # Exécution
    results: list[dict] = []
    for val in args.values:
        print(f"\n  ── MIN_ATTEMPTS={val} ────────────────────────────────")
        r = run_seq_c(tmp, user_id, chunk_id, doc_id, skill_slug,
                      n=args.n, score=args.score, min_attempts=val)
        results.append(r)
        q_f = r["q_fragile_to_encours"] or "—"
        q_a = r["q_encours_to_acquis"]  or "—"
        print(f"  Fragile → En cours : Q{q_f}")
        print(f"  En cours → Acquis  : Q{q_a}")
        print(f"  État final         : {r['final_label']} (score={r['final_score']:.3f})")
        print(f"  Verdict            : {_verdict(r)}")

    # Tableau comparatif
    print(f"\n{SEP}")
    print("  Tableau comparatif (← = Fragile→En cours, ★ = En cours→Acquis)")
    print(SEP)
    _print_table(results, args.n)

    # Recommandation
    print(f"{SEP}")
    print("  Recommandation")
    print(SEP)
    print(f"  {_recommend(results)}")

    # Risques
    print(f"\n{SEP}")
    print("  Analyse des risques")
    print(SEP)
    print(f"  TOO_FAST : apprenant déclaré 'Acquis' après ≤ 3 tentatives")
    print(f"             → révision espacée sous-utilisée, sur-confiance")
    print(f"  OK       : 'Acquis' entre Q4 et Q8 — équilibre réactivité/robustesse")
    print(f"  TOO_SLOW : 'Acquis' après Q8 — curriculum trop conservateur")

    # Cleanup
    if not args.keep_db:
        try:
            tmp.unlink()
        except Exception:
            pass

    # Copy block
    block = _copy_block(results, args.score, args.n)
    print(f"\n{block}\n")


if __name__ == "__main__":
    main()
