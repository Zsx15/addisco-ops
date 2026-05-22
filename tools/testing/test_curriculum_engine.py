"""
test_curriculum_engine.py -- Simulation & validation TASK-058

Tests de simulation pour engine/curriculum_engine.py.
Execution standalone : python tools/testing/test_curriculum_engine.py
"""

import sys
import os
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from engine.curriculum_engine import (
    compute_learning_priority,
    build_learning_queue,
    select_next_learning_step,
    recommend_revision_focus,
    _pick_question_type,
    _classify_difficulty,
    _TREND_WEIGHT,
    _MASTERY_WEIGHT,
)
from engine.question_type import QUESTION_TYPES

_NOW = datetime.now(timezone.utc)


def _iso(days_ago: float) -> str:
    return (_NOW - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")


# ── DB helpers ────────────────────────────────────────────────────────────────

_SKILL_SLUGS = [
    "memorisation_faits", "identification_concepts",
    "comprehension_procedure", "application_regles",
    "analyse_causale", "resolution_problemes",
    "prise_decision", "evaluation_critique",
    "synthese_reformulation", "conformite_reglementaire",
]


def _make_db(tmp_path: str, attempts: list = None, skill_overrides: dict = None) -> None:
    """Cree une DB de test avec schema complet (compatible get_user_skill_mastery JOIN)."""
    with sqlite3.connect(tmp_path) as conn:
        conn.execute("""CREATE TABLE users (
            id TEXT PRIMARY KEY, username TEXT, email TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )""")
        conn.execute("""CREATE TABLE documents (
            id INTEGER PRIMARY KEY, title TEXT, content TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )""")
        conn.execute("""CREATE TABLE chunks (
            id INTEGER PRIMARY KEY, document_id INTEGER,
            section_label TEXT, content TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )""")
        conn.execute("""CREATE TABLE chunk_attempts (
            id INTEGER PRIMARY KEY, user_id TEXT, chunk_id INTEGER,
            score REAL, created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(chunk_id) REFERENCES chunks(id)
        )""")
        conn.execute("""CREATE TABLE attempts (
            id INTEGER PRIMARY KEY,
            user_id TEXT, question TEXT, user_answer TEXT,
            expected_answer TEXT, correction TEXT,
            score REAL, response_time_seconds REAL,
            error_type TEXT, topic TEXT, pedagogy_type TEXT,
            document_id INTEGER, chunk_id INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        )""")
        # Schema complet skills + user_skill_mastery pour JOIN
        conn.execute("""CREATE TABLE skills (
            id INTEGER PRIMARY KEY,
            slug TEXT UNIQUE,
            label_fr TEXT,
            description TEXT,
            is_active INTEGER DEFAULT 1
        )""")
        conn.execute("""CREATE TABLE user_skill_mastery (
            id INTEGER PRIMARY KEY,
            user_id TEXT,
            skill_id INTEGER,
            mastery_score REAL DEFAULT 0.0,
            attempts_count INTEGER DEFAULT 0,
            last_reviewed_at TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, skill_id),
            FOREIGN KEY(skill_id) REFERENCES skills(id)
        )""")
        conn.execute("""CREATE TABLE user_learning_profile (
            user_id TEXT PRIMARY KEY,
            avg_score REAL DEFAULT 0.0,
            total_attempts INTEGER DEFAULT 0,
            preferred_pedagogy TEXT,
            strong_topics TEXT,
            weak_topics TEXT,
            last_updated TEXT DEFAULT (datetime('now'))
        )""")

        conn.execute(
            "INSERT INTO users VALUES (?,?,?,?)",
            ("test_user", "TestUser", "test@test.com", _iso(10)),
        )
        conn.execute(
            "INSERT INTO documents VALUES (?,?,?,?)",
            (1, "Doc Test", "Contenu test.", _iso(10)),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?)",
            (1, 1, "Section A", "Contenu section A.", _iso(10)),
        )

        # Skill seeds avec IDs sequentiels (necessaire pour le JOIN)
        for i, slug in enumerate(_SKILL_SLUGS, 1):
            conn.execute(
                "INSERT INTO skills (id, slug, label_fr, description, is_active) VALUES (?,?,?,?,1)",
                (i, slug, slug.replace("_", " "), f"Description {slug}"),
            )
            score = skill_overrides.get(slug, 0.0) if skill_overrides else 0.0
            conn.execute(
                "INSERT INTO user_skill_mastery "
                "(user_id, skill_id, mastery_score, attempts_count) "
                "VALUES (?,?,?,?)",
                ("test_user", i, score, 3 if score > 0 else 0),
            )

        if attempts:
            for et, sc, days, pt in attempts:
                conn.execute(
                    "INSERT INTO attempts (user_id, question, user_answer, expected_answer, "
                    "correction, score, error_type, pedagogy_type, created_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?)",
                    ("test_user", "Q?", "rep", "exp", "corr", sc, et, pt, _iso(days)),
                )


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_compute_priority_baseline():
    """Score de base sans facteurs = 0.50."""
    p = compute_learning_priority()
    assert p == 0.50, f"Attendu 0.50, obtenu {p}"
    print("  [OK]  T1 -- priorite de base = 0.50")


def test_compute_priority_fragile_critique():
    """Fragile + critique = priorite haute."""
    p = compute_learning_priority(
        mastery_class="Fragile",
        error_trend="critique",
        recent_avg=0.30,
        is_blocking=True,
    )
    expected = round(0.50 + 0.22 + 0.25 + 0.12 + 0.20, 3)
    assert p == min(1.0, expected), f"Attendu {min(1.0,expected)}, obtenu {p}"
    print(f"  [OK]  T2 -- Fragile+critique+blocking = {p:.3f}")


def test_compute_priority_acquis():
    """Acquis + score eleve = priorite basse."""
    p = compute_learning_priority(
        mastery_class="Acquis",
        error_trend=None,
        recent_avg=0.85,
    )
    expected = round(0.50 - 0.18 - 0.10, 3)
    assert p == max(0.0, expected), f"Attendu {max(0.0,expected)}, obtenu {p}"
    print(f"  [OK]  T3 -- Acquis+score eleve = {p:.3f}")


def test_compute_priority_clamped():
    """Le score est toujours clamp entre 0.0 et 1.0."""
    p_high = compute_learning_priority("Fragile", "critique", 0.10, True, True)
    p_low  = compute_learning_priority("Acquis",  "stabilisé", 0.90)
    assert 0.0 <= p_high <= 1.0, f"Score > 1.0 : {p_high}"
    assert 0.0 <= p_low  <= 1.0, f"Score < 0.0 : {p_low}"
    print(f"  [OK]  T4 -- clamp [0,1] respecte (max={p_high:.3f}, min={p_low:.3f})")


def test_pick_question_type_error_normal():
    """reponse_vague + mastery normale -> reformulation."""
    qt = _pick_question_type("reponse_vague", None, "En cours", [])
    assert qt == "reformulation", f"Attendu reformulation, obtenu {qt}"
    print(f"  [OK]  T5 -- erreur reponse_vague normal -> reformulation")


def test_pick_question_type_error_fragile():
    """reponse_vague + Fragile -> question_directe (version accessible)."""
    qt = _pick_question_type("reponse_vague", None, "Fragile", [])
    assert qt == "question_directe", f"Attendu question_directe, obtenu {qt}"
    print(f"  [OK]  T6 -- erreur reponse_vague Fragile -> question_directe")


def test_pick_question_type_rotation():
    """Saturation : si les 2 derniers types sont identiques, ce type est evite."""
    used = ["reformulation", "reformulation", "cas_pratique"]
    qt = _pick_question_type("reponse_vague", None, "En cours", used)
    assert qt != "reformulation", f"reformulation sature, ne devrait pas etre selectionne"
    assert qt in QUESTION_TYPES, f"Type invalide : {qt}"
    print(f"  [OK]  T7 -- rotation saturation reformulation -> {qt}")


def test_classify_difficulty_fragile():
    """Fragile -> easy."""
    d = _classify_difficulty("Fragile", recent_avg=0.50)
    assert d == "easy", f"Attendu easy, obtenu {d}"
    print("  [OK]  T8 -- Fragile -> easy")


def test_classify_difficulty_acquis_high():
    """Acquis + score eleve -> hard."""
    d = _classify_difficulty("Acquis", recent_avg=0.80)
    assert d == "hard", f"Attendu hard, obtenu {d}"
    print("  [OK]  T9 -- Acquis + score >= 0.65 -> hard")


def test_build_queue_no_history():
    """Sans historique : fallback item retourne."""
    import database as _db
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = tmp.name
    original = _db.DB_PATH
    try:
        _db.DB_PATH = tmp_path
        _make_db(tmp_path)
        queue = build_learning_queue("test_user")
        assert len(queue) >= 1, "Queue doit avoir au moins 1 item"
        sources = {it["source"] for it in queue}
        # Sans historique de tentatives : fallback ou skill_mastery attendu
        assert sources & {"fallback", "skill_mastery"}, f"Sources inattendues : {sources}"
        for it in queue:
            assert it["question_type"] in QUESTION_TYPES, f"Type invalide : {it['question_type']}"
            assert 0.0 <= it["priority"] <= 1.0, f"Priorite hors bornes : {it['priority']}"
        print(f"  [OK]  T10 -- sans historique queue={len(queue)} items, sources={sources}")
    finally:
        _db.DB_PATH = original
        try: os.unlink(tmp_path)
        except OSError: pass


def test_build_queue_fragile_pattern():
    """Pattern chronique reponse_vague -> error_pattern en source."""
    import database as _db
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = tmp.name
    original = _db.DB_PATH
    try:
        _db.DB_PATH = tmp_path
        attempts = [
            ("reponse_vague", 0.30, 30, "reformulation"),
            ("reponse_vague", 0.28, 20, "reformulation"),
            ("reponse_vague", 0.35, 10, "reformulation"),
        ]
        _make_db(tmp_path, attempts=attempts, skill_overrides={"synthese_reformulation": 0.30})
        queue = build_learning_queue("test_user")
        ep_items = [it for it in queue if it["source"] == "error_pattern"]
        assert ep_items, "Aucun item error_pattern dans la queue"
        rv_item = next((it for it in ep_items if it["context"]["error_type"] == "reponse_vague"), None)
        assert rv_item is not None, "Item reponse_vague attendu dans error_pattern"
        print(f"  [OK]  T11 -- pattern chronique reponse_vague -> priority={rv_item['priority']:.3f}")
    finally:
        _db.DB_PATH = original
        try: os.unlink(tmp_path)
        except OSError: pass


def test_build_queue_mastered_skill_excluded():
    """Skill Acquis (score 0.90) ne doit pas apparaitre comme priorite."""
    import database as _db
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = tmp.name
    original = _db.DB_PATH
    try:
        _db.DB_PATH = tmp_path
        _make_db(tmp_path, skill_overrides={"memorisation_faits": 0.90})
        queue = build_learning_queue("test_user")
        mastered = [it for it in queue
                    if it["target_skill"] == "memorisation_faits"
                    and it["source"] == "skill_mastery"]
        assert not mastered, "Skill Acquis ne doit pas etre dans la queue skill_mastery"
        print(f"  [OK]  T12 -- skill Acquis exclu de la queue skill_mastery")
    finally:
        _db.DB_PATH = original
        try: os.unlink(tmp_path)
        except OSError: pass


def test_queue_deduplication():
    """Pas de doublon (meme type + meme skill) dans la queue."""
    import database as _db
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = tmp.name
    original = _db.DB_PATH
    try:
        _db.DB_PATH = tmp_path
        attempts = [
            ("hors_sujet",   0.25, 20, "question_directe"),
            ("hors_sujet",   0.22, 15, "question_directe"),
            ("hors_sujet",   0.28, 8,  "question_directe"),
        ]
        _make_db(tmp_path, attempts=attempts)
        queue = build_learning_queue("test_user")
        keys = [(it["question_type"], it["target_skill"]) for it in queue]
        assert len(keys) == len(set(keys)), f"Doublons detectes dans la queue : {keys}"
        print(f"  [OK]  T13 -- deduplication queue ({len(queue)} items uniques)")
    finally:
        _db.DB_PATH = original
        try: os.unlink(tmp_path)
        except OSError: pass


def test_recommend_revision_focus_structure():
    """recommend_revision_focus retourne la structure attendue."""
    import database as _db
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = tmp.name
    original = _db.DB_PATH
    try:
        _db.DB_PATH = tmp_path
        _make_db(tmp_path)
        focus = recommend_revision_focus("test_user")
        for key in ("fragile_skills", "active_patterns", "revision_due", "avg_score", "confidence"):
            assert key in focus, f"Cle manquante : {key}"
        assert focus["confidence"] in ("low", "medium", "high"), f"Confiance invalide : {focus['confidence']}"
        print(f"  [OK]  T14 -- structure recommend_revision_focus valide (conf={focus['confidence']})")
    finally:
        _db.DB_PATH = original
        try: os.unlink(tmp_path)
        except OSError: pass


# ── Runner ────────────────────────────────────────────────────────────────────

def main():
    tests = [
        test_compute_priority_baseline,
        test_compute_priority_fragile_critique,
        test_compute_priority_acquis,
        test_compute_priority_clamped,
        test_pick_question_type_error_normal,
        test_pick_question_type_error_fragile,
        test_pick_question_type_rotation,
        test_classify_difficulty_fragile,
        test_classify_difficulty_acquis_high,
        test_build_queue_no_history,
        test_build_queue_fragile_pattern,
        test_build_queue_mastered_skill_excluded,
        test_queue_deduplication,
        test_recommend_revision_focus_structure,
    ]

    print(f"\n{'=' * 64}")
    print("  TASK-058 - Curriculum Engine V1 - Tests de simulation")
    print(f"{'=' * 64}\n")

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as exc:
            print(f"  [FAIL]  {t.__name__} -- {exc}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'=' * 64}")
    print(f"  Resultat : {passed}/{len(tests)} tests passes", end="")
    if failed:
        print(f"  --  {failed} ECHEC(S)")
    else:
        print("  -- OK TOUS PASSES")
    print(f"{'=' * 64}\n")
    return failed


if __name__ == "__main__":
    sys.exit(main())
