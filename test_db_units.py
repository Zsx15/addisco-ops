"""
Tests unitaires — db/skills.py et db/sessions.py
Base SQLite temporaire isolée — zéro API OpenAI, zéro database.db de prod.

Exécution : python test_db_units.py
"""
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


# ─────────────────────────────────────────────────────────────────────────────
# Infrastructure partagée
# ─────────────────────────────────────────────────────────────────────────────

def _make_temp_db() -> Path:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    return Path(tmp.name)


class _DbTestCase(unittest.TestCase):
    """Base : monte une DB temporaire avant chaque test, la nettoie après."""

    def setUp(self):
        import database as db
        self._orig_path = db.DB_PATH
        self._tmp_path  = _make_temp_db()
        db.DB_PATH      = self._tmp_path
        db.init_db()
        self.db = db

    def tearDown(self):
        import database as db
        db.DB_PATH = self._orig_path
        try:
            os.unlink(self._tmp_path)
        except OSError:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# db/skills.py — seed et CRUD
# ─────────────────────────────────────────────────────────────────────────────

class TestDbSkillsSeed(_DbTestCase):

    def test_seed_creates_10_skills(self):
        from db.skills import seed_skills, get_all_skills
        seed_skills()
        self.assertEqual(len(get_all_skills()), 10)

    def test_seed_idempotent(self):
        from db.skills import seed_skills, get_all_skills
        seed_skills()
        seed_skills()
        self.assertEqual(len(get_all_skills()), 10)

    def test_all_skills_have_slug_and_label(self):
        from db.skills import seed_skills, get_all_skills
        seed_skills()
        for skill in get_all_skills():
            self.assertTrue(skill["slug"], "slug vide")
            self.assertTrue(skill["label_fr"], "label_fr vide")

    def test_get_skill_by_slug_found(self):
        from db.skills import seed_skills, get_skill_by_slug
        seed_skills()
        skill = get_skill_by_slug("prise_decision")
        self.assertIsNotNone(skill)
        self.assertEqual(skill["slug"], "prise_decision")

    def test_get_skill_by_slug_not_found(self):
        from db.skills import seed_skills, get_skill_by_slug
        seed_skills()
        self.assertIsNone(get_skill_by_slug("slug_inexistant_xyz"))

    def test_all_10_expected_slugs_present(self):
        from db.skills import seed_skills, get_all_skills
        seed_skills()
        expected = {
            "memorisation_faits", "comprehension_procedure", "identification_concepts",
            "application_regles", "analyse_causale", "resolution_problemes",
            "prise_decision", "evaluation_critique", "synthese_reformulation",
            "conformite_reglementaire",
        }
        actual = {s["slug"] for s in get_all_skills()}
        self.assertEqual(actual, expected)


class TestDbSkillsMastery(_DbTestCase):

    def _seed_attempt_with_skill(self, user_id: str, skill_slug: str, scores: list):
        """Helper : crée doc + chunk + chunk_skill + attempts pour un user."""
        from db.skills import seed_skills

        seed_skills()
        with sqlite3.connect(str(self.db.DB_PATH)) as conn:
            skill_row = conn.execute(
                "SELECT id FROM skills WHERE slug = ?", (skill_slug,)
            ).fetchone()
            self.assertIsNotNone(skill_row, f"Skill '{skill_slug}' introuvable après seed")
            skill_id = skill_row[0]

            conn.execute(
                "INSERT INTO documents (title, source_type, raw_text, cleaned_text) "
                "VALUES ('doc', 'text', 'c', 'c')"
            )
            doc_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

            conn.execute(
                "INSERT INTO chunks (document_id, chunk_text, chunk_index, char_count) "
                "VALUES (?, 'txt', 0, 50)",
                (doc_id,),
            )
            chunk_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

            conn.execute(
                "INSERT OR IGNORE INTO chunk_skills (chunk_id, skill_id, weight, source) "
                "VALUES (?, ?, 1.0, 'keyword')",
                (chunk_id, skill_id),
            )
            for score in scores:
                conn.execute(
                    "INSERT INTO attempts "
                    "(user_id, chunk_id, document_id, score, pedagogy_type, question, user_answer, correction) "
                    "VALUES (?, ?, ?, ?, 'question_directe', 'q', 'a', 'c')",
                    (user_id, chunk_id, doc_id, score),
                )
        return chunk_id

    def test_mastery_empty_before_attempts(self):
        from db.skills import seed_skills, get_user_skill_mastery
        seed_skills()
        self.assertEqual(get_user_skill_mastery("ghost_user"), [])

    def test_update_persists_correct_mastery_score(self):
        from db.skills import update_user_skill_mastery, get_user_skill_mastery
        scores  = [0.9, 0.85, 0.95]
        user_id = "test_mastery_user"
        self._seed_attempt_with_skill(user_id, "prise_decision", scores)
        update_user_skill_mastery(user_id)
        rows = get_user_skill_mastery(user_id)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["slug"], "prise_decision")
        expected = round(sum(scores) / len(scores), 3)
        self.assertAlmostEqual(rows[0]["mastery_score"], expected, places=2)

    def test_update_user_isolation(self):
        from db.skills import update_user_skill_mastery, get_user_skill_mastery
        self._seed_attempt_with_skill("userA", "prise_decision", [0.9, 0.9, 0.9])
        update_user_skill_mastery("userA")
        # userB n'a pas de tentatives → mastery vide
        self.assertEqual(get_user_skill_mastery("userB"), [])

    def test_update_idempotent(self):
        from db.skills import update_user_skill_mastery, get_user_skill_mastery
        user_id = "idem_user"
        self._seed_attempt_with_skill(user_id, "analyse_causale", [0.8, 0.7])
        update_user_skill_mastery(user_id)
        update_user_skill_mastery(user_id)
        rows = get_user_skill_mastery(user_id)
        self.assertEqual(len(rows), 1)


# ─────────────────────────────────────────────────────────────────────────────
# db/sessions.py — start, close, analytics
# ─────────────────────────────────────────────────────────────────────────────

class TestDbSessions(_DbTestCase):

    def test_start_session_returns_positive_int(self):
        from db.sessions import start_session
        sid = start_session("user1")
        self.assertIsInstance(sid, int)
        self.assertGreater(sid, 0)

    def test_multiple_sessions_get_distinct_ids(self):
        from db.sessions import start_session
        ids = [start_session("user1") for _ in range(3)]
        self.assertEqual(len(set(ids)), 3)

    def test_close_session_stores_avg_score(self):
        from db.sessions import start_session, close_session
        sid = start_session("user2")
        close_session(sid, completed_questions=5, avg_score=0.75)
        with sqlite3.connect(str(self.db.DB_PATH)) as conn:
            row = conn.execute(
                "SELECT avg_score, completed_questions FROM learning_sessions WHERE id = ?",
                (sid,),
            ).fetchone()
        self.assertAlmostEqual(row[0], 0.75, places=2)
        self.assertEqual(row[1], 5)

    def test_close_session_sets_ended_at(self):
        from db.sessions import start_session, close_session
        sid = start_session("user2")
        close_session(sid, avg_score=0.6)
        with sqlite3.connect(str(self.db.DB_PATH)) as conn:
            row = conn.execute(
                "SELECT ended_at FROM learning_sessions WHERE id = ?", (sid,)
            ).fetchone()
        self.assertIsNotNone(row[0])

    def test_get_user_sessions_returns_list(self):
        from db.sessions import start_session, close_session, get_user_sessions
        sid = start_session("user3")
        close_session(sid, avg_score=0.6, completed_questions=3)
        sessions = get_user_sessions("user3")
        self.assertIsInstance(sessions, list)
        self.assertGreaterEqual(len(sessions), 1)

    def test_user_session_isolation(self):
        from db.sessions import start_session, close_session, get_user_sessions
        sidA = start_session("userA")
        sidB = start_session("userB")
        close_session(sidA, avg_score=0.7, completed_questions=2)
        close_session(sidB, avg_score=0.8, completed_questions=3)
        ids_a = {s["id"] for s in get_user_sessions("userA")}
        ids_b = {s["id"] for s in get_user_sessions("userB")}
        self.assertEqual(ids_a & ids_b, set(), "Les sessions de A et B se croisent")

    def test_get_session_analytics_structure(self):
        from db.sessions import start_session, close_session, get_session_analytics
        sid = start_session("user4")
        close_session(sid, avg_score=0.8, completed_questions=10)
        analytics = get_session_analytics("user4")
        self.assertIn("total_sessions", analytics)
        self.assertIn("avg_score_this_week", analytics)

    def test_session_analytics_empty_user(self):
        from db.sessions import get_session_analytics
        analytics = get_session_analytics("ghost_user_xyz")
        self.assertEqual(analytics.get("total_sessions", 0), 0)

    def test_session_analytics_counts_correctly(self):
        from db.sessions import start_session, close_session, get_session_analytics
        for _ in range(3):
            sid = start_session("user5")
            close_session(sid, avg_score=0.7, completed_questions=5)
        analytics = get_session_analytics("user5")
        self.assertGreaterEqual(analytics.get("total_sessions", 0), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
