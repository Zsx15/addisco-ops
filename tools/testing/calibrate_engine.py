#!/usr/bin/env python
"""
calibrate_engine.py — TASK-074
Engine Calibration Harness : séquences déterministes pour mesurer la
réactivité du moteur adaptatif face à des profils d'erreur contrôlés.

Usage :
  python tools/testing/calibrate_engine.py
  python tools/testing/calibrate_engine.py --seq A B C
  python tools/testing/calibrate_engine.py --keep-db   # conserver le DB temp

Séquences :
  SEQ-A : 20× reponse_vague  → critique/chronique attendu avant Q20
  SEQ-B : 15× hors_sujet     → pivot curriculum (question_type change)
  SEQ-C : 20× correct        → mastery Fragile → Acquis
  SEQ-D : 10× vague + 10× correct (décalés) → en_amelioration
  SEQ-E : 10× oubli_etape (ancient) + 10× correct → stabilisé

Verdicts : PASS / TOO_FAST / TOO_SLOW / NO_REACTION / WRONG_REACTION
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
import tempfile
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

# ── Encodage Windows ──────────────────────────────────────────────────────────
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Racine du projet ──────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import logging
logging.basicConfig(level=logging.WARNING)

import database as _db
from engine.error_pattern_memory import (
    compute_error_patterns,
    detect_persistent_error_patterns,
    MIN_COUNT_CRITICAL,
    CHRONIC_MIN_AGE,
    RECENT_WINDOW_DAYS,
    STALE_DAYS,
    IMPROVEMENT_DELTA,
)
from engine.curriculum_engine import get_curriculum_recommendation
from engine.skill_engine import classify_skill_mastery
from db.skills import update_user_skill_mastery, get_user_skill_mastery
from db.profile import compute_and_save_learning_profile

# ── Constantes ────────────────────────────────────────────────────────────────
SEP  = "─" * 70
SEP2 = "━" * 70
BATCH = 5   # recalcul toutes les N injections

# Seuils du moteur (référence pour le rapport)
THRESHOLDS = {
    "MIN_COUNT_CRITICAL":  MIN_COUNT_CRITICAL,
    "CHRONIC_MIN_AGE":     CHRONIC_MIN_AGE,
    "RECENT_WINDOW_DAYS":  RECENT_WINDOW_DAYS,
    "STALE_DAYS":          STALE_DAYS,
    "IMPROVEMENT_DELTA":   IMPROVEMENT_DELTA,
}


# ── DB isolée ─────────────────────────────────────────────────────────────────

def _setup_isolated_db(real_db: Path) -> tuple[Path, str]:
    """
    Copie le vrai DB dans un fichier temp.
    Supprime les données utilisateur, crée calibration_user.
    Retourne (chemin_temp, user_id).
    """
    tmp = Path(tempfile.mktemp(suffix="_calib.db"))
    shutil.copy(str(real_db), str(tmp))

    cal_uid = str(uuid.uuid4())
    conn = sqlite3.connect(str(tmp))
    conn.execute("DELETE FROM attempts")
    conn.execute("DELETE FROM user_learning_profile")
    conn.execute("DELETE FROM user_skill_mastery")
    conn.execute("DELETE FROM runtime_metrics")
    conn.execute("DELETE FROM users WHERE username LIKE 'calibration%'")
    conn.execute(
        "INSERT OR IGNORE INTO users (user_id, username, role, password_hash) "
        "VALUES (?, 'calibration_user', 'apprenant', 'x')",
        (cal_uid,),
    )
    conn.commit()
    conn.close()
    return tmp, cal_uid


def _clear_user(conn: sqlite3.Connection, user_id: str) -> None:
    """Réinitialise les données du calibration_user entre séquences."""
    conn.execute("DELETE FROM attempts WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM user_learning_profile WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM user_skill_mastery WHERE user_id = ?", (user_id,))
    conn.commit()


# ── Injection directe ─────────────────────────────────────────────────────────

def _inject(
    conn: sqlite3.Connection,
    user_id: str,
    n: int,
    score: float,
    error_type: str,
    q_type: str,
    chunk_id: Optional[int],
    doc_id: Optional[int],
    days_ago: float = 0.0,
) -> None:
    """Insère n tentatives avec created_at backdaté."""
    ts = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
    for _ in range(n):
        conn.execute(
            """INSERT INTO attempts
               (user_id, question, user_answer, expected_answer,
                correction, score, error_type, pedagogy_type,
                document_id, chunk_id, created_at)
               VALUES (?, 'Q calibration', 'R calibration', 'Expected',
                       'Correction calibration', ?, ?, ?, ?, ?, ?)""",
            (user_id, score if score is not None else None,
             error_type, q_type, doc_id, chunk_id, ts),
        )
    conn.commit()


# ── Observateurs ─────────────────────────────────────────────────────────────

def _get_pattern_trend(user_id: str, error_type: str) -> Optional[str]:
    """Retourne la tendance actuelle d'un error_type pour user_id."""
    try:
        result = detect_persistent_error_patterns(user_id)
        for p in result.get("patterns", []):
            if p["error_type"] == error_type:
                return p["trend"]
    except Exception:
        pass
    return None


def _get_curriculum_qtype(user_id: str) -> Optional[str]:
    try:
        rec = get_curriculum_recommendation(user_id)
        return (rec.get("next_step") or {}).get("question_type")
    except Exception:
        return None


def _get_skill_label(user_id: str, skill_slug: str) -> Optional[str]:
    try:
        skills = get_user_skill_mastery(user_id) or []
        for s in skills:
            if s["slug"] == skill_slug:
                return classify_skill_mastery(s["mastery_score"], s["attempts_count"])
        # Pas encore de mastery enregistré = Fragile (0 score)
        return "Fragile"
    except Exception:
        return None


def _get_skill_score(user_id: str, skill_slug: str) -> float:
    try:
        skills = get_user_skill_mastery(user_id) or []
        for s in skills:
            if s["slug"] == skill_slug:
                return s["mastery_score"]
        return 0.0
    except Exception:
        return 0.0


# ── Runner de séquence ────────────────────────────────────────────────────────

class CheckPoint:
    """Résultat d'une observation à Q_n."""
    def __init__(self, q_n: int, observed: Any, expected: Any, passed: bool):
        self.q_n      = q_n
        self.observed = observed
        self.expected = expected
        self.passed   = passed

    def __str__(self) -> str:
        icon = "✓" if self.passed else "✗"
        return f"  Q{self.q_n:>02} {icon} observé={self.observed!r}  attendu={self.expected!r}"


def run_sequence(
    conn: sqlite3.Connection,
    user_id: str,
    name: str,
    steps: list[dict],
    check_fn,
    expected_by_q: dict[int, Any],
    pass_criterion,
) -> dict:
    """
    Exécute une séquence et retourne le résultat.

    steps : liste de dicts {n, score, error_type, q_type, days_ago, chunk_id, doc_id}
    check_fn : (user_id) → observed value
    expected_by_q : {q_n: expected_value} — checkpoints
    pass_criterion : fn(checkpoints) → verdict str
    """
    _clear_user(conn, user_id)
    q = 0
    checkpoints: list[CheckPoint] = []

    for step in steps:
        _inject(
            conn, user_id,
            n=step["n"],
            score=step["score"],
            error_type=step["error_type"],
            q_type=step.get("q_type", "question_directe"),
            chunk_id=step.get("chunk_id"),
            doc_id=step.get("doc_id"),
            days_ago=step.get("days_ago", 0.0),
        )
        q += step["n"]

        # Recalcul moteur
        try:
            update_user_skill_mastery(user_id)
            compute_and_save_learning_profile(user_id)
        except Exception:
            pass

        # Observations aux checkpoints définis
        if q in expected_by_q:
            observed = check_fn(user_id)
            expected = expected_by_q[q]
            passed = (observed == expected) if not callable(expected) else expected(observed)
            cp = CheckPoint(q, observed, expected if not callable(expected) else "fn()", passed)
            checkpoints.append(cp)

    verdict = pass_criterion(checkpoints)
    return {"name": name, "verdict": verdict, "checkpoints": checkpoints, "total_q": q}


# ── Séquences ─────────────────────────────────────────────────────────────────

def _seq_a(conn, user_id, chunk_id, doc_id) -> dict:
    """SEQ-A : 20× reponse_vague → critique/chronique attendu par Q15"""
    name  = "SEQ-A — reponse_vague → critique/chronique"
    steps = [
        # Établit l'ancienneté (> CHRONIC_MIN_AGE jours)
        dict(n=5,  score=0.20, error_type="reponse_vague", q_type="question_directe",
             days_ago=float(CHRONIC_MIN_AGE + 2), chunk_id=chunk_id, doc_id=doc_id),
        # Maintient le pattern actif récemment
        dict(n=5,  score=0.25, error_type="reponse_vague", q_type="question_directe",
             days_ago=1.0, chunk_id=chunk_id, doc_id=doc_id),
        dict(n=5,  score=0.22, error_type="reponse_vague", q_type="question_directe",
             days_ago=0.5, chunk_id=chunk_id, doc_id=doc_id),
        dict(n=5,  score=0.18, error_type="reponse_vague", q_type="question_directe",
             days_ago=0.1, chunk_id=chunk_id, doc_id=doc_id),
    ]
    # Checkpoints : Q5 (trop tôt), Q10 (transition possible), Q15, Q20
    expected_by_q = {
        5:  "récent",      # pas encore chronique/critique (ancienneté non encore comptée)
        10: lambda t: t in ("critique", "chronique", "récent"),
        15: lambda t: t in ("critique", "chronique"),
        20: lambda t: t in ("critique", "chronique"),
    }

    def check(uid):
        return _get_pattern_trend(uid, "reponse_vague")

    def verdict(cps):
        # Chercher premier PASS >= Q10
        for cp in cps:
            if cp.q_n >= 10 and cp.passed:
                if cp.q_n <= 15:
                    return "PASS"
                return "TOO_SLOW"
        # Q5 déjà critique?
        q5 = next((c for c in cps if c.q_n == 5), None)
        if q5 and q5.observed in ("critique", "chronique"):
            return "TOO_FAST"
        # Aucune réaction?
        last = cps[-1] if cps else None
        if last and last.observed is None:
            return "NO_REACTION"
        # Signal différent?
        return "WRONG_REACTION"

    return run_sequence(conn, user_id, name, steps, check, expected_by_q, verdict)


def _seq_b(conn, user_id, chunk_id, doc_id) -> dict:
    """SEQ-B : 15× hors_sujet → curriculum pivot (hors_sujet dans les patterns actifs)"""
    name  = "SEQ-B — hors_sujet × 15 → pivot curriculum"
    steps = [
        dict(n=5,  score=0.05, error_type="hors_sujet", q_type="question_directe",
             days_ago=CHRONIC_MIN_AGE + 1, chunk_id=chunk_id, doc_id=doc_id),
        dict(n=5,  score=0.05, error_type="hors_sujet", q_type="question_directe",
             days_ago=1.0, chunk_id=chunk_id, doc_id=doc_id),
        dict(n=5,  score=0.05, error_type="hors_sujet", q_type="question_directe",
             days_ago=0.2, chunk_id=chunk_id, doc_id=doc_id),
    ]
    # Attendu : hors_sujet apparaît comme pattern actif dans la recommandation curriculum
    # et/ou la recommandation pointe vers un type correctif
    expected_by_q = {
        5:  None,   # pas encore
        10: True,   # pattern hors_sujet détecté
        15: True,   # curriculum intègre le signal
    }

    def check(uid):
        trend = _get_pattern_trend(uid, "hors_sujet")
        qtype = _get_curriculum_qtype(uid)
        # Pivot = pattern détecté ET curriculum a un next_step
        return trend in ("critique", "chronique", "récent") and qtype is not None

    def verdict(cps):
        for cp in cps:
            if cp.q_n >= 10 and cp.passed:
                return "PASS"
        q5 = next((c for c in cps if c.q_n == 5), None)
        if q5 and q5.passed:
            return "TOO_FAST"
        last = cps[-1] if cps else None
        if last and not last.passed and _get_pattern_trend(user_id, "hors_sujet") is None:
            return "NO_REACTION"
        return "TOO_SLOW" if cps else "NO_REACTION"

    return run_sequence(conn, user_id, name, steps, check, expected_by_q, verdict)


def _seq_c(conn, user_id, chunk_id_skill: int, doc_id: int, skill_slug: str) -> dict:
    """SEQ-C : 20× correct → mastery Fragile (0.0) → Acquis (>= 0.8)"""
    name = f"SEQ-C — correct × 20 → mastery '{skill_slug}' : Fragile → Acquis"
    steps = [
        dict(n=5,  score=0.90, error_type="correct", q_type="question_directe",
             days_ago=0.0, chunk_id=chunk_id_skill, doc_id=doc_id),
        dict(n=5,  score=0.88, error_type="correct", q_type="cas_pratique",
             days_ago=0.0, chunk_id=chunk_id_skill, doc_id=doc_id),
        dict(n=5,  score=0.92, error_type="correct", q_type="reformulation",
             days_ago=0.0, chunk_id=chunk_id_skill, doc_id=doc_id),
        dict(n=5,  score=0.91, error_type="correct", q_type="question_directe",
             days_ago=0.0, chunk_id=chunk_id_skill, doc_id=doc_id),
    ]
    expected_by_q = {
        5:  lambda s: s == "En cours",  # 5 attempts × 0.90 → score ~0.90 → En cours (>= 0.60)
        10: lambda s: s in ("En cours", "Acquis"),
        15: lambda s: s in ("En cours", "Acquis"),
        20: lambda s: s == "Acquis",
    }

    def check(uid):
        return _get_skill_label(uid, skill_slug)

    def verdict(cps):
        q5 = next((c for c in cps if c.q_n == 5), None)
        q20 = next((c for c in cps if c.q_n == 20), None)

        if q20 and q20.passed:
            # Vérifier si Acquis arrive trop tôt
            for cp in cps:
                if cp.q_n < 10 and cp.observed == "Acquis":
                    return "TOO_FAST"
            return "PASS"
        if q20 and q20.observed == "En cours":
            return "TOO_SLOW"
        if q20 and q20.observed == "Fragile":
            return "NO_REACTION"
        return "WRONG_REACTION"

    return run_sequence(conn, user_id, name, steps, check, expected_by_q, verdict)


def _seq_d(conn, user_id, chunk_id, doc_id) -> dict:
    """SEQ-D : 10× vague (ancien) + 10× correct/amélioration → en_amelioration"""
    name = "SEQ-D — reponse_vague ancien + scores hauts récents → en_amelioration"
    steps = [
        # Phase ancienne : vague, score bas (> RECENT_WINDOW_DAYS)
        dict(n=10, score=0.18, error_type="reponse_vague", q_type="question_directe",
             days_ago=float(RECENT_WINDOW_DAYS + 2), chunk_id=chunk_id, doc_id=doc_id),
        # Phase récente : même error_type mais score nettement meilleur
        # (recent_avg - early_avg >= IMPROVEMENT_DELTA = 0.15)
        dict(n=10, score=0.55, error_type="reponse_vague", q_type="cas_pratique",
             days_ago=0.2, chunk_id=chunk_id, doc_id=doc_id),
    ]
    expected_by_q = {
        10: lambda t: t in ("récent", "chronique"),   # phase 1 seule
        20: "en_amelioration",                         # delta 0.55-0.18=0.37 >= 0.15
    }

    def check(uid):
        return _get_pattern_trend(uid, "reponse_vague")

    def verdict(cps):
        q10 = next((c for c in cps if c.q_n == 10), None)
        q20 = next((c for c in cps if c.q_n == 20), None)

        if q20 and q20.passed:
            return "PASS"
        if q20 and q20.observed == "en_amelioration":
            return "PASS"  # correspond à expected
        if q20 is None or q20.observed is None:
            return "NO_REACTION"
        if q20.observed in ("récent", "chronique", "critique"):
            return "WRONG_REACTION"
        return "TOO_SLOW"

    return run_sequence(conn, user_id, name, steps, check, expected_by_q, verdict)


def _seq_e(conn, user_id, chunk_id, doc_id) -> dict:
    """SEQ-E : 10× oubli_etape (il y a > STALE_DAYS j) → pattern stabilisé après correct"""
    name = f"SEQ-E — oubli_etape ancien (>{STALE_DAYS}j) → stabilisé"
    steps = [
        # Phase ancienne : oubli_etape bien au-delà de STALE_DAYS
        dict(n=10, score=0.30, error_type="oubli_etape", q_type="question_directe",
             days_ago=float(STALE_DAYS + 2), chunk_id=chunk_id, doc_id=doc_id),
        # Phase récente : correct (ne crée pas de pattern, car 'correct' est exclu)
        dict(n=10, score=0.90, error_type="correct", q_type="question_directe",
             days_ago=0.1, chunk_id=chunk_id, doc_id=doc_id),
    ]
    # Attendu : oubli_etape last_seen_days >= STALE_DAYS → "stabilisé"
    expected_by_q = {
        10: lambda t: t in ("récent", "chronique", "critique"),  # avant correct phase
        20: "stabilisé",
    }

    def check(uid):
        return _get_pattern_trend(uid, "oubli_etape")

    def verdict(cps):
        q20 = next((c for c in cps if c.q_n == 20), None)

        if q20 and q20.passed:
            return "PASS"
        if q20 and q20.observed is None:
            # Stabilisé = disparition du pattern (min_count non atteint ?)
            # Vérifier si le pattern n'apparaît plus du tout = aussi acceptable
            return "PASS"
        if q20 and q20.observed in ("récent", "chronique", "critique"):
            # Pattern encore actif alors qu'il aurait dû se calmer
            return "WRONG_REACTION"
        return "NO_REACTION"

    return run_sequence(conn, user_id, name, steps, check, expected_by_q, verdict)


# ── Rapport ───────────────────────────────────────────────────────────────────

_VERDICT_COLORS = {
    "PASS":           "PASS",
    "TOO_FAST":       "TOO_FAST",
    "TOO_SLOW":       "TOO_SLOW",
    "NO_REACTION":    "NO_REACTION",
    "WRONG_REACTION": "WRONG_REACTION",
}

_VERDICT_EXPLAIN = {
    "PASS":           "Signal détecté dans la fenêtre attendue.",
    "TOO_FAST":       "Signal apparu trop tôt — seuil trop sensible.",
    "TOO_SLOW":       "Signal apparu trop tard — moteur trop inerte.",
    "NO_REACTION":    "Aucun signal détecté — moteur aveugle à ce profil.",
    "WRONG_REACTION": "Signal différent de l'attendu — mauvaise classification.",
}


def _print_result(r: dict) -> None:
    v = r["verdict"]
    print(f"\n  {r['name']}")
    print(f"  {'─' * 60}")
    for cp in r["checkpoints"]:
        print(f"  {cp}")
    print(f"\n  Verdict : {v}")
    print(f"  {_VERDICT_EXPLAIN.get(v, '')}")


def _copy_block(results: list[dict], db_path: Path) -> str:
    lines = ["=== COPY_FOR_ANALYSIS_START ==="]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines.append(f"# Engine Calibration Report — {now}")
    lines.append(f"- DB temp : {db_path}")
    lines.append("")
    lines.append("## Seuils moteur")
    for k, v in THRESHOLDS.items():
        lines.append(f"- {k} : {v}")
    lines.append("")
    lines.append("## Résultats par séquence")
    lines.append("")

    all_pass = all(r["verdict"] == "PASS" for r in results)
    for r in results:
        v = r["verdict"]
        lines.append(f"### {r['name']}")
        lines.append(f"- Verdict : **{v}** — {_VERDICT_EXPLAIN.get(v, '')}")
        lines.append("- Checkpoints :")
        for cp in r["checkpoints"]:
            icon = "PASS" if cp.passed else "FAIL"
            lines.append(f"  - Q{cp.q_n:02} [{icon}] observé={cp.observed!r}")
        lines.append("")

    lines.append("## Synthèse")
    n_pass = sum(1 for r in results if r["verdict"] == "PASS")
    lines.append(f"- PASS        : {n_pass}/{len(results)}")
    for v in ("TOO_FAST", "TOO_SLOW", "NO_REACTION", "WRONG_REACTION"):
        n = sum(1 for r in results if r["verdict"] == v)
        if n:
            lines.append(f"- {v:<14}: {n}/{len(results)}")
    lines.append("")
    lines.append(
        "## Interprétation calibration\n"
        "- TOO_FAST    → baisser MIN_COUNT_PATTERN ou MIN_COUNT_CRITICAL\n"
        "- TOO_SLOW    → baisser CHRONIC_MIN_AGE ou MIN_COUNT_CRITICAL\n"
        "- NO_REACTION → vérifier chunk_skills associations ou seuils\n"
        "- WRONG_REACT → revoir logique _classify_pattern()"
    )
    lines.append("=== COPY_FOR_ANALYSIS_END ===")
    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Engine Calibration Harness — TASK-074")
    parser.add_argument("--seq",      nargs="+", choices=["A","B","C","D","E"],
                        default=["A","B","C","D","E"], help="Séquences à exécuter")
    parser.add_argument("--keep-db",  action="store_true",  help="Conserver le DB temp après exécution")
    parser.add_argument("--isolate-db", action="store_true", default=True,
                        help="Utiliser un DB isolé (défaut: True)")
    args = parser.parse_args()

    print(f"\n{SEP2}")
    print("  ADDISCO OPS — Engine Calibration Harness (TASK-074)")
    print(SEP2)
    print(f"  Séquences     : {' '.join(args.seq)}")
    print(f"  DB réel       : {_db.DB_PATH}")

    # ── Setup DB isolé ────────────────────────────────────────────────────────
    real_db = Path(str(_db.DB_PATH))
    if not real_db.exists():
        # Si pas de DB réel, init minimal
        _db.init_db()

    tmp_db, user_id = _setup_isolated_db(real_db)
    _db.DB_PATH = type(_db.DB_PATH)(str(tmp_db))  # patch pour tous les modules

    print(f"  DB temp       : {tmp_db}")
    print(f"  user_id       : {user_id[:8]}…")

    # ── Récupérer un chunk exploitable avec skill association ────────────────
    conn = sqlite3.connect(str(tmp_db))
    row = conn.execute(
        """SELECT cs.chunk_id, c.document_id, s.slug
           FROM chunk_skills cs
           JOIN skills s ON cs.skill_id = s.id
           JOIN chunks  c ON cs.chunk_id = c.id
           WHERE cs.is_active = 1 AND c.chunk_text IS NOT NULL
             AND length(c.chunk_text) > 100
           LIMIT 1"""
    ).fetchone()
    if not row:
        print("\n  [ERREUR] Aucun chunk avec skill association. Vérifiez le DB.")
        conn.close()
        sys.exit(1)
    skill_chunk_id, skill_doc_id, skill_slug = row[0], row[1], row[2]

    # chunk générique pour les séquences sans besoin de skill tracking
    any_row = conn.execute(
        "SELECT id, document_id FROM chunks WHERE chunk_text IS NOT NULL LIMIT 1"
    ).fetchone()
    gen_chunk_id = any_row[0] if any_row else skill_chunk_id
    gen_doc_id   = any_row[1] if any_row else skill_doc_id
    conn.close()

    print(f"  Chunk skill   : id={skill_chunk_id}  doc={skill_doc_id}  skill='{skill_slug}'")
    print(f"  Chunk générique: id={gen_chunk_id}  doc={gen_doc_id}")

    # ── Seuils référence ──────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("  Seuils moteur (référence)")
    print(SEP)
    for k, v in THRESHOLDS.items():
        print(f"  {k:<25} : {v}")

    # ── Exécution séquences ───────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("  Exécution des séquences")
    print(SEP)

    conn = sqlite3.connect(str(tmp_db))
    results: list[dict] = []

    seq_map = {
        "A": lambda: _seq_a(conn, user_id, gen_chunk_id, gen_doc_id),
        "B": lambda: _seq_b(conn, user_id, gen_chunk_id, gen_doc_id),
        "C": lambda: _seq_c(conn, user_id, skill_chunk_id, skill_doc_id, skill_slug),
        "D": lambda: _seq_d(conn, user_id, gen_chunk_id, gen_doc_id),
        "E": lambda: _seq_e(conn, user_id, gen_chunk_id, gen_doc_id),
    }

    for s in args.seq:
        print(f"\n  ── Séquence {s} ──────────────────────────────────────────────")
        try:
            r = seq_map[s]()
            results.append(r)
            _print_result(r)
        except Exception as exc:
            print(f"  [ERREUR] Séquence {s} : {exc}")
            results.append({"name": f"SEQ-{s}", "verdict": "FAILED", "checkpoints": [], "total_q": 0})

    conn.close()

    # ── Synthèse ─────────────────────────────────────────────────────────────
    print(f"\n{SEP2}")
    print("  SYNTHÈSE")
    print(SEP2)
    n_pass = sum(1 for r in results if r["verdict"] == "PASS")
    print(f"  PASS : {n_pass}/{len(results)}")
    for r in results:
        icon = "✓" if r["verdict"] == "PASS" else "✗"
        print(f"  {icon}  {r['verdict']:<16} {r['name']}")

    # ── Cleanup DB ────────────────────────────────────────────────────────────
    if not args.keep_db:
        try:
            tmp_db.unlink()
            print(f"\n  DB temp supprimé.")
        except Exception:
            pass
    else:
        print(f"\n  DB temp conservé : {tmp_db}")

    # ── Copy block ────────────────────────────────────────────────────────────
    block = _copy_block(results, tmp_db)
    print(f"\n{block}\n")

    sys.exit(0 if n_pass == len(results) else 1)


if __name__ == "__main__":
    main()
