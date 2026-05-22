"""
test_error_pattern_memory.py -- Simulation & validation TASK-057

Tests de simulation (non-regression supplémentaires) pour engine/error_pattern_memory.py.
Exécution standalone : python tools/testing/test_error_pattern_memory.py
"""

import sys
import os
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from engine.error_pattern_memory import (
    compute_error_patterns,
    get_persistent_error_types,
    detect_persistent_error_patterns,
    MIN_COUNT_PATTERN,
    CHRONIC_MIN_AGE,
    RECENT_WINDOW_DAYS,
    STALE_DAYS,
    IMPROVEMENT_DELTA,
)

_NOW = datetime.now(timezone.utc)


def _iso(days_ago: float) -> str:
    return (_NOW - timedelta(days=days_ago)).isoformat()


def _make_rows(*specs) -> list[tuple]:
    """specs : (error_type, score, days_ago) -- pedagogy_type vide."""
    return [(e, s, _iso(d), None) for e, s, d in specs]


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_empty_data():
    patterns = compute_error_patterns([])
    assert patterns == [], f"Attendu [], obtenu {patterns}"
    print("  [OK]  T1 -- donnees vides -> liste vide")


def test_non_evaluable_excluded():
    rows = _make_rows(
        ("non_evaluable", 0.0, 1),
        ("non_evaluable", 0.0, 2),
        ("non_evaluable", 0.0, 3),
        ("correct",       1.0, 1),
    )
    patterns = compute_error_patterns(rows)
    types = [p["error_type"] for p in patterns]
    assert "non_evaluable" not in types, "non_evaluable ne doit pas apparaître"
    assert "correct" not in types, "correct ne doit pas apparaître"
    print("  [OK]  T2 -- non_evaluable et correct exclus")


def test_chronic_pattern():
    rows = _make_rows(
        ("reponse_vague", 0.30, 30),
        ("reponse_vague", 0.35, 25),
        ("reponse_vague", 0.28, 18),
        ("reponse_vague", 0.40, 3),
    )
    patterns = compute_error_patterns(rows)
    assert patterns, "Des patterns doivent être détectés"
    p = next((x for x in patterns if x["error_type"] == "reponse_vague"), None)
    assert p is not None
    assert p["trend"] in ("chronique", "critique"), f"Tendance attendue chronique/critique, obtenu {p['trend']}"
    print(f"  [OK]  T3 -- pattern chronique détecté (trend={p['trend']})")


def test_critical_pattern():
    rows = _make_rows(
        ("oubli_etape", 0.20, 60),
        ("oubli_etape", 0.22, 50),
        ("oubli_etape", 0.18, 40),
        ("oubli_etape", 0.25, 30),
        ("oubli_etape", 0.22, 20),
        ("oubli_etape", 0.19, 5),
        ("oubli_etape", 0.21, 2),
    )
    patterns = compute_error_patterns(rows)
    p = next((x for x in patterns if x["error_type"] == "oubli_etape"), None)
    assert p is not None
    assert p["trend"] == "critique", f"Attendu critique, obtenu {p['trend']}"
    assert p["count"] == 7
    print(f"  [OK]  T4 -- pattern critique (count={p['count']}, score={p['avg_score']:.0%})")


def test_improvement_pattern():
    rows = _make_rows(
        ("confusion_notion", 0.20, 40),
        ("confusion_notion", 0.25, 35),
        ("confusion_notion", 0.60, 5),
        ("confusion_notion", 0.70, 3),
        ("confusion_notion", 0.72, 1),
    )
    patterns = compute_error_patterns(rows)
    p = next((x for x in patterns if x["error_type"] == "confusion_notion"), None)
    assert p is not None
    assert p["trend"] == "en_amelioration", f"Attendu en_amelioration, obtenu {p['trend']}"
    print(f"  [OK]  T5 -- pattern en amelioration détecté (delta suffisant)")


def test_recent_pattern():
    rows = _make_rows(
        ("hors_sujet", 0.40, 4),
        ("hors_sujet", 0.35, 3),
    )
    patterns = compute_error_patterns(rows)
    p = next((x for x in patterns if x["error_type"] == "hors_sujet"), None)
    assert p is not None
    assert p["trend"] == "récent", f"Attendu récent, obtenu {p['trend']}"
    print(f"  [OK]  T6 -- pattern récent (last_seen={p['last_seen_days']:.0f}j)")


def test_stale_pattern():
    rows = _make_rows(
        ("erreur_ordre", 0.30, 40),
        ("erreur_ordre", 0.35, 35),
        ("erreur_ordre", 0.28, 30),
    )
    patterns = compute_error_patterns(rows)
    p = next((x for x in patterns if x["error_type"] == "erreur_ordre"), None)
    assert p is not None
    assert p["trend"] == "stabilisé", f"Attendu stabilisé, obtenu {p['trend']}"
    print(f"  [OK]  T7 -- pattern stabilisé (inactif depuis {p['last_seen_days']:.0f}j)")


def test_get_persistent_error_types():
    patterns = [
        {"error_type": "reponse_vague",    "trend": "critique",       "count": 6, "avg_score": 0.2},
        {"error_type": "oubli_etape",      "trend": "chronique",      "count": 3, "avg_score": 0.4},
        {"error_type": "hors_sujet",       "trend": "récent",         "count": 2, "avg_score": 0.5},
        {"error_type": "confusion_notion", "trend": "en_amelioration","count": 4, "avg_score": 0.7},
        {"error_type": "erreur_ordre",     "trend": "stabilisé",      "count": 2, "avg_score": 0.3},
    ]
    types = get_persistent_error_types(patterns)
    assert "reponse_vague" in types
    assert "oubli_etape" in types
    assert "hors_sujet" in types
    assert "confusion_notion" not in types
    assert "erreur_ordre" not in types
    print(f"  [OK]  T8 -- get_persistent_error_types filtre correctement ({types})")


def test_db_integration():
    """Vérifie l'appel DB complet via monkey-patch."""
    import database as _db

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = tmp.name

    original_path = _db.DB_PATH
    try:
        _db.DB_PATH = tmp_path
        with sqlite3.connect(tmp_path) as conn:
            conn.execute(
                """CREATE TABLE attempts (
                    id INTEGER PRIMARY KEY,
                    user_id TEXT, question TEXT, user_answer TEXT,
                    expected_answer TEXT, correction TEXT,
                    score REAL, response_time_seconds REAL,
                    error_type TEXT, topic TEXT, pedagogy_type TEXT,
                    document_id INTEGER, chunk_id INTEGER,
                    created_at TEXT DEFAULT (datetime('now'))
                )"""
            )
            # Insert test data
            for i, (et, sc, days) in enumerate([
                ("reponse_vague", 0.30, 20),
                ("reponse_vague", 0.28, 15),
                ("reponse_vague", 0.32, 5),
                ("non_evaluable", 0.0,  2),
            ]):
                ts = (_NOW - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
                conn.execute(
                    "INSERT INTO attempts (user_id, question, user_answer, expected_answer, "
                    "correction, score, error_type, created_at) VALUES (?,?,?,?,?,?,?,?)",
                    ("default", f"Q{i}", "rep", "exp", "corr", sc, et, ts),
                )

        result = detect_persistent_error_patterns("default")
        assert "patterns" in result
        assert "persistent_types" in result
        types = [p["error_type"] for p in result["patterns"]]
        assert "non_evaluable" not in types
        assert "reponse_vague" in types
        print(f"  [OK]  T9 -- intégration DB (patterns={types})")

    finally:
        _db.DB_PATH = original_path
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def test_adaptive_difficulty_integration():
    """Vérifie que les patterns critique/chronique influencent choose_adaptive_question_type."""
    from engine.adaptive_difficulty import choose_adaptive_question_type

    # Simule une injection : reponse_vague avec poids 2 (comme dans ai_service.py)
    injected = ["reponse_vague", "reponse_vague"]
    result = choose_adaptive_question_type(
        used_types      = [],
        mastery_class   = "Fragile",
        repeated_errors = injected,
    )
    assert result in ("reformulation", "question_directe", "vrai_faux",
                      "cas_pratique", "consequence", "question_piege"), \
        f"Type invalide : {result}"
    # Avec reponse_vague dominant (count=2) et mastery Fragile -> reformulation attendu
    assert result == "reformulation", \
        f"Attendu reformulation pour reponse_vague Fragile, obtenu {result}"
    print(f"  [OK]  T10 -- injection adaptive difficulty (type={result})")


# ── Runner ────────────────────────────────────────────────────────────────────

def main():
    tests = [
        test_empty_data,
        test_non_evaluable_excluded,
        test_chronic_pattern,
        test_critical_pattern,
        test_improvement_pattern,
        test_recent_pattern,
        test_stale_pattern,
        test_get_persistent_error_types,
        test_db_integration,
        test_adaptive_difficulty_integration,
    ]

    print(f"\n{'=' * 60}")
    print("  TASK-057 - Error Pattern Memory - Tests de simulation")
    print(f"{'=' * 60}\n")

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as exc:
            print(f"  [FAIL]  {t.__name__} -- ERREUR : {exc}")
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"  Resultat : {passed}/{len(tests)} tests passes", end="")
    if failed:
        print(f"  --  {failed} ECHEC(S)")
    else:
        print("  -- OK TOUS PASSES")
    print(f"{'=' * 60}\n")

    return failed


if __name__ == "__main__":
    sys.exit(main())

