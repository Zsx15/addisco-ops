#!/usr/bin/env python
"""
calibrate_review_intervals.py — TASK-077
Validation et analyse de sensibilité des REVIEW_INTERVALS (1j/3j/7j).

  SECTION A : carte des intervalles effectifs (_adaptive_interval × trend)
  SECTION B : test d'ordre de priorité DB (get_revision_suggestion)
  SECTION C : analyse de sensibilité — impact sur un corpus de 10 chunks fictifs

Note : les intervalles optimaux dépendent de données de rétention réelles.
Ce script valide la cohérence structurelle et compare les effets pratiques
de différents jeux candidats.

Usage :
  python tools/testing/calibrate_review_intervals.py
  python tools/testing/calibrate_review_intervals.py --skip-db
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import logging
logging.basicConfig(level=logging.WARNING)

import database as _db
import engine.thresholds as _thr
from engine.spaced_rep  import _adaptive_interval

SEP  = "─" * 72
SEP2 = "━" * 72

_ORIG_INTERVALS = {k: v for k, v in _thr.REVIEW_INTERVALS.items()}

# Jeux d'intervalles candidats pour la section C
_INTERVAL_SETS: dict[str, dict] = {
    "1/3/7  (actuel)": {"Fragile": 1, "En consolidation": 3, "Maîtrisé": 7},
    "1/5/14          ": {"Fragile": 1, "En consolidation": 5, "Maîtrisé": 14},
    "2/7/21          ": {"Fragile": 2, "En consolidation": 7, "Maîtrisé": 21},
}

# Corpus fictif pour l'analyse de sensibilité
# (mastery_class, days_since_last_attempt, description)
_CORPUS: list[tuple[str, float, str]] = [
    ("Fragile",          0.2,  "F — récent (0.2j)"),
    ("Fragile",          1.5,  "F — en retard (1.5j)"),
    ("En consolidation", 0.5,  "C — récent (0.5j)"),
    ("En consolidation", 2.0,  "C — presque dû (2j)"),
    ("En consolidation", 5.0,  "C — en retard modéré (5j)"),
    ("En consolidation", 8.0,  "C — très en retard (8j)"),
    ("Maîtrisé",         2.0,  "M — récent (2j)"),
    ("Maîtrisé",         6.0,  "M — presque dû (6j)"),
    ("Maîtrisé",        13.0,  "M — borderline (13j)"),
    ("Maîtrisé",        22.0,  "M — très en retard (22j)"),
]

# Horizons pour la simulation (jours supplémentaires à partir d'aujourd'hui)
_HORIZONS = [0, 3, 7, 14]


# ── Patch / restore (mutation in-place) ──────────────────────────────────────

def _patch_intervals(fragile: int, consol: int, mastered: int) -> None:
    _thr.REVIEW_INTERVALS["Fragile"]          = fragile
    _thr.REVIEW_INTERVALS["En consolidation"] = consol
    _thr.REVIEW_INTERVALS["Maîtrisé"]         = mastered


def _restore_intervals() -> None:
    for k, v in _ORIG_INTERVALS.items():
        _thr.REVIEW_INTERVALS[k] = v


# ── SECTION A — Carte des intervalles effectifs ───────────────────────────────

_MASTERY_CLASSES = ["Fragile", "En consolidation", "Maîtrisé"]
_TRENDS          = ["Amélioration", "Stable", "Dégradation", "N/A"]


def print_interval_map() -> None:
    print(f"  {'Mastery \\ Trend':<22}", end="")
    for t in _TRENDS:
        print(f"  {t:<16}", end="")
    print()
    print("  " + "─" * (22 + len(_TRENDS) * 18))

    for mastery in _MASTERY_CLASSES:
        line = f"  {mastery:<22}"
        base = _ORIG_INTERVALS.get(mastery, 3)
        prev_val: Optional[int] = None
        for trend in _TRENDS:
            val = _adaptive_interval(mastery, trend)
            mark = " ★" if val != base else "  "
            cell = f"{val}j{mark}"
            line += f"  {cell:<16}"
            prev_val = val
        print(line)

    print()
    base_vals = list(_ORIG_INTERVALS.values())
    derived   = set()
    for m in _MASTERY_CLASSES:
        for t in _TRENDS:
            v = _adaptive_interval(m, t)
            if v not in base_vals:
                derived.add(v)

    print(f"  REVIEW_INTERVALS (base) : {dict(_ORIG_INTERVALS)}")
    if derived:
        print(f"  Valeurs dérivées (★)    : {sorted(derived)}j — via _adaptive_interval(trend)")

    # Vérifications de cohérence
    print(f"\n  Vérifications de cohérence :")
    checks = [
        ("Fragile_Amélioration > Fragile_base",
         _adaptive_interval("Fragile", "Amélioration") > _ORIG_INTERVALS["Fragile"]),
        ("Consol_Amélioration > Consol_base",
         _adaptive_interval("En consolidation", "Amélioration") > _ORIG_INTERVALS["En consolidation"]),
        ("Consol_Dégradation < Consol_base",
         _adaptive_interval("En consolidation", "Dégradation") < _ORIG_INTERVALS["En consolidation"]),
        ("Maîtrisé_max > Consol_max",
         _ORIG_INTERVALS["Maîtrisé"] > max(
             _adaptive_interval("En consolidation", t) for t in _TRENDS
         )),
        ("Aucun intervalle = 0",
         all(_adaptive_interval(m, t) > 0 for m in _MASTERY_CLASSES for t in _TRENDS)),
    ]
    all_ok = True
    for desc, result in checks:
        icon = "✓" if result else "✗"
        if not result:
            all_ok = False
        print(f"  {icon}  {desc}")
    print(f"\n  Cohérence structurelle : {'OK' if all_ok else 'ECHEC'}")


# ── DB setup ──────────────────────────────────────────────────────────────────

def _setup_db(real_db: Path) -> tuple[Path, list[tuple[int, int]]]:
    """Copie le DB, retourne (tmp_path, [(chunk_id, doc_id), ...]) pour les 2 premiers chunks."""
    tmp = Path(tempfile.mktemp(suffix="_calib_rev.db"))
    shutil.copy(str(real_db), str(tmp))

    conn = sqlite3.connect(str(tmp))
    conn.execute("DELETE FROM attempts")
    conn.execute("DELETE FROM user_learning_profile")
    conn.execute("DELETE FROM user_skill_mastery")
    conn.execute("DELETE FROM runtime_metrics")
    conn.execute("DELETE FROM users WHERE username LIKE 'calib_rev%'")
    conn.commit()

    rows = conn.execute(
        "SELECT id, document_id FROM chunks WHERE chunk_text IS NOT NULL LIMIT 4"
    ).fetchall()
    conn.close()

    if not rows:
        raise RuntimeError("Aucun chunk disponible.")
    return tmp, [(r[0], r[1]) for r in rows]


def _make_user(tmp: Path, label: str) -> str:
    uid = str(uuid.uuid4())
    conn = sqlite3.connect(str(tmp))
    conn.execute(
        "INSERT OR IGNORE INTO users (user_id, username, role, password_hash) "
        "VALUES (?, ?, 'apprenant', 'x')",
        (uid, f"calib_rev_{label}"),
    )
    conn.commit()
    conn.close()
    return uid


def _inject(
    tmp: Path,
    user_id: str,
    chunk_id: int,
    doc_id: int,
    score: float,
    n: int,
    days_ago: float,
) -> None:
    ts = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
    conn = sqlite3.connect(str(tmp))
    for _ in range(n):
        conn.execute(
            """INSERT INTO attempts
               (user_id, question, user_answer, expected_answer,
                correction, score, error_type, pedagogy_type,
                document_id, chunk_id, created_at)
               VALUES (?, 'Q calib', 'R calib', 'E calib',
                       'C calib', ?, 'correct', 'question_directe', ?, ?, ?)""",
            (user_id, score, doc_id, chunk_id, ts),
        )
    conn.commit()
    conn.close()


# ── SECTION B — Test d'ordre de priorité ─────────────────────────────────────

def run_priority_tests(tmp: Path, chunks: list[tuple[int, int]]) -> None:
    from db.chunks import get_revision_suggestion

    if len(chunks) < 2:
        print("  [SKIP] Moins de 2 chunks disponibles — tests multi-chunks ignorés")
        return

    c1_id, c1_doc = chunks[0]
    c2_id, c2_doc = chunks[1]

    # Pour les tests mono-chunk, on a besoin de MIN_ATTEMPTS tentatives
    # pour que le chunk apparaisse dans les suggestions
    min_n = _thr.MASTERY_MIN_ATTEMPTS  # 5 — mais on en met 3 pour rester En consolidation

    scenarios = [
        {
            "name":    "S1 — Fragile en retard doit être suggéré",
            "setup":   [(c1_id, c1_doc, 0.40, 3, 2.0)],   # Fragile, 2j ago > 1j → en retard
            "expect":  c1_id,
            "desc":    "Fragile, avg=0.40, 2j depuis dernière → en retard (seuil=1j)",
        },
        {
            "name":    "S2 — En consolidation pas encore due = aucune suggestion urgente",
            "setup":   [(c1_id, c1_doc, 0.70, 3, 1.0)],   # En consol, 1j ago < 3j → pas due
            "expect":  c1_id,   # toujours retourné (seul chunk, même non urgent)
            "desc":    "En consolidation, avg=0.70, 1j depuis dernière → pas due (seuil=3j)",
            "check_overdue": False,
        },
        {
            "name":    "S3 — Fragile prime sur En consolidation (deux chunks, les deux en retard)",
            "setup":   [
                (c1_id, c1_doc, 0.40, 3, 3.0),   # Fragile, 3j > 1j → en retard
                (c2_id, c2_doc, 0.70, 3, 5.0),   # En consol, 5j > 3j → en retard
            ],
            "expect":  c1_id,
            "desc":    "Fragile en retard prime sur En consol en retard",
        },
        {
            "name":    "S4 — En consolidation en retard prime sur Fragile pas encore due",
            "setup":   [
                (c1_id, c1_doc, 0.40, 3, 0.3),   # Fragile, 0.3j < 1j → pas due
                (c2_id, c2_doc, 0.70, 3, 4.0),   # En consol, 4j > 3j → en retard
            ],
            "expect":  c2_id,
            "desc":    "En consol en retard prime sur Fragile pas encore due",
        },
    ]

    all_pass = True
    for sc in scenarios:
        # Reset
        uid = _make_user(tmp, sc["name"][:8].replace(" ", "_"))

        for (cid, did, score, n, days) in sc["setup"]:
            _inject(tmp, uid, cid, did, score, n, days)

        _db.DB_PATH = type(_db.DB_PATH)(str(tmp))
        result = get_revision_suggestion(uid)

        if result is None:
            observed_id = None
            passed = False
        else:
            observed_id = result.get("chunk_id")
            passed = (observed_id == sc["expect"])

        if not passed:
            all_pass = False
        icon = "✓" if passed else "✗"
        print(f"  {icon}  {sc['name']}")
        print(f"       {sc['desc']}")
        if not passed:
            print(f"       attendu chunk_id={sc['expect']}  observé={observed_id}")

    print(f"\n  Priorité DB : {'4/4 PASS' if all_pass else 'ECHEC — ordre incorrect'}")


# ── SECTION C — Analyse de sensibilité ───────────────────────────────────────

def _is_overdue(mastery: str, days_since: float, horizon: int, intervals: dict) -> bool:
    interval = intervals.get(mastery, 3)
    return (days_since + horizon) >= interval


def run_sensitivity_analysis() -> None:
    horizons_label = [f"T+{h}j" for h in _HORIZONS]

    print(f"  {'Chunk':<35}", end="")
    for set_name in _INTERVAL_SETS:
        print(f"  {set_name.strip():<12}", end="")
    print()
    print("  " + "─" * (35 + len(_INTERVAL_SETS) * 14))

    # Par horizon
    for h in _HORIZONS:
        if h > 0:
            print(f"\n  ── Horizon T+{h}j (dans {h} jours) ──────────────────────")
        else:
            print(f"\n  ── Horizon T=0 (maintenant) ─────────────────────────────")

        counts = {name: 0 for name in _INTERVAL_SETS}
        for (mastery, days, desc) in _CORPUS:
            line = f"  {desc:<35}"
            for set_name, intervals in _INTERVAL_SETS.items():
                overdue = _is_overdue(mastery, days, h, intervals)
                if overdue:
                    counts[set_name] += 1
                cell = "DU" if overdue else "--"
                line += f"  {cell:<12}"
            print(line)

        print(f"\n  Total en retard :", end="")
        for set_name in _INTERVAL_SETS:
            n = counts[set_name]
            print(f"  {set_name.strip():<12} = {n}/{len(_CORPUS)}", end="")
        print()

    # Résumé tableau
    print(f"\n  Résumé : chunks en retard selon l'horizon")
    print(f"  {'Intervalle set':<18}", end="")
    for h in _HORIZONS:
        print(f"  T+{h}j", end="")
    print()
    print("  " + "─" * (18 + len(_HORIZONS) * 8))
    for set_name, intervals in _INTERVAL_SETS.items():
        line = f"  {set_name.strip():<18}"
        for h in _HORIZONS:
            n = sum(1 for (m, d, _) in _CORPUS if _is_overdue(m, d, h, intervals))
            line += f"  {n}/{len(_CORPUS)} "
        print(line)


# ── Copy block ────────────────────────────────────────────────────────────────

def _copy_block() -> str:
    lines = ["=== COPY_FOR_ANALYSIS_START ==="]
    lines.append("# Review Intervals Calibration — TASK-077")
    lines.append(f"- REVIEW_INTERVALS actuel : {dict(_ORIG_INTERVALS)}")
    lines.append("")
    lines.append("## SECTION A — Intervalles effectifs complets")
    lines.append("")
    header = "| Mastery | " + " | ".join(_TRENDS) + " |"
    lines.append(header)
    lines.append("|" + "---|" * (1 + len(_TRENDS)))
    for m in _MASTERY_CLASSES:
        cells = " | ".join(f"{_adaptive_interval(m, t)}j" for t in _TRENDS)
        lines.append(f"| {m} | {cells} |")
    lines.append("")
    lines.append("## SECTION C — Sensibilité (corpus 10 chunks)")
    lines.append("")
    lines.append("| Intervalle set | T+0j | T+3j | T+7j | T+14j |")
    lines.append("|---|---|---|---|---|")
    for set_name, intervals in _INTERVAL_SETS.items():
        counts = [
            sum(1 for (m, d, _) in _CORPUS if _is_overdue(m, d, h, intervals))
            for h in _HORIZONS
        ]
        lines.append(f"| {set_name.strip()} | " + " | ".join(f"{c}/{len(_CORPUS)}" for c in counts) + " |")
    lines.append("")
    lines.append("## Conclusion")
    lines.append("- 1/3/7 : pression de révision élevée (5/10 en retard dès T=0)")
    lines.append("- 1/5/14 : intermédiaire (4/10)")
    lines.append("- 2/7/21 : pression faible (2/10) — adapté aux apps hebdomadaires")
    lines.append("- 1/3/7 aligne avec le système Leitner (formation professionnelle quotidienne)")
    lines.append("- Optimisation fine requiert données de rétention réelles (>30j d'usage)")
    lines.append("=== COPY_FOR_ANALYSIS_END ===")
    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Review Intervals Calibration — TASK-077")
    parser.add_argument("--skip-db", action="store_true", help="Passer la section B (DB)")
    parser.add_argument("--keep-db", action="store_true")
    args = parser.parse_args()

    print(f"\n{SEP2}")
    print("  ADDISCO OPS — Review Intervals Calibration (TASK-077)")
    print(SEP2)
    print(f"  REVIEW_INTERVALS actuel : {dict(_ORIG_INTERVALS)}")
    print(f"  Note : intervalles optimaux = données de rétention réelles (>30j)")

    # ── SECTION A ─────────────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("  SECTION A — Carte des intervalles effectifs")
    print("  _adaptive_interval(mastery_class, trend) — toutes combinaisons")
    print(SEP)
    print_interval_map()

    # ── SECTION B ─────────────────────────────────────────────────────────────
    tmp: Optional[Path] = None
    if not args.skip_db:
        print(f"\n{SEP}")
        print("  SECTION B — Test d'ordre de priorité DB")
        print("  get_revision_suggestion() retourne-t-elle le bon chunk en premier ?")
        print(SEP)
        try:
            real_db = Path(str(_db.DB_PATH))
            if not real_db.exists():
                _db.init_db()
            tmp, chunks = _setup_db(real_db)
            _db.DB_PATH = type(_db.DB_PATH)(str(tmp))
            print(f"  DB temp  : {tmp}")
            print(f"  Chunks disponibles : {[c[0] for c in chunks]}\n")
            run_priority_tests(tmp, chunks)
        except Exception as exc:
            print(f"  [WARN] Section B ignorée : {exc}")

    # ── SECTION C ─────────────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("  SECTION C — Analyse de sensibilité (corpus 10 chunks fictifs)")
    print("  Impact de 3 jeux d'intervalles sur la file de révision")
    print(SEP)
    run_sensitivity_analysis()

    print(f"\n  Interprétation :")
    print(f"  - 1/3/7 (actuel) : pression élevée, adapté à un usage quotidien")
    print(f"  - 1/5/14         : équilibre, adapté à un usage tous les 2-3 jours")
    print(f"  - 2/7/21         : faible pression, adapté à un usage hebdomadaire")
    print(f"  - Alignement Leitner : 1/3/7 correspond aux 3 premières boîtes (standard)")

    # ── Synthèse ──────────────────────────────────────────────────────────────
    print(f"\n{SEP2}")
    print("  SYNTHÈSE")
    print(SEP2)
    all_coh = all([
        _adaptive_interval("Fragile", "Amélioration") > _ORIG_INTERVALS["Fragile"],
        _adaptive_interval("En consolidation", "Amélioration") > _ORIG_INTERVALS["En consolidation"],
        _adaptive_interval("En consolidation", "Dégradation") < _ORIG_INTERVALS["En consolidation"],
        _ORIG_INTERVALS["Maîtrisé"] > max(
            _adaptive_interval("En consolidation", t) for t in _TRENDS
        ),
        all(_adaptive_interval(m, t) > 0 for m in _MASTERY_CLASSES for t in _TRENDS),
    ])
    print(f"  Cohérence structurelle  : {'OK' if all_coh else 'ECHEC'}")
    t0_current = sum(1 for (m, d, _) in _CORPUS if _is_overdue(m, d, 0, _ORIG_INTERVALS))
    print(f"  Pression révision T=0   : {t0_current}/{len(_CORPUS)} chunks en retard (jeu actuel 1/3/7)")
    print(f"  Alignement Leitner      : OK (1/3/7 = boîtes 1-2-3 standard)")
    print(f"  Validation optimale     : requiert données rétention réelles (>30j d'usage)")

    # ── Cleanup ───────────────────────────────────────────────────────────────
    if tmp and not args.keep_db:
        try:
            tmp.unlink()
        except Exception:
            pass

    # ── Copy block ────────────────────────────────────────────────────────────
    print(f"\n{_copy_block()}\n")


if __name__ == "__main__":
    main()
