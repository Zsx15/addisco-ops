"""
Tests de non-régression — SYNPZ OPS
Couvre : database.py (invariants critiques) + ui_helpers.py (fonctions pures)
         + ai_service._choose_question_type (logique biais profil).

Exécution : python test_regression.py
Chaque test database utilise une base SQLite temporaire isolée (tempfile).
Aucun accès à database.db ni à l'API OpenAI.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd


# ─────────────────────────────────────────────────────────────────────────────
# Helpers de setup DB
# ─────────────────────────────────────────────────────────────────────────────

def _make_temp_db():
    """Crée une base SQLite temporaire et renvoie son chemin."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    return Path(tmp.name)


class _DbTestCase(unittest.TestCase):
    """Base : monte une DB temporaire avant chaque test, la détruit après."""

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

    # ── helpers ──────────────────────────────────────────────────────────────

    def _add_attempt(self, score=0.8, user_id="default", topic="T1",
                     error_type=None, pedagogy_type="question_directe",
                     chunk_id=None, question="Q?"):
        self.db.save_attempt(
            question=question, user_answer="A", expected_answer="EA",
            correction="C", score=score,
            error_type=error_type, topic=topic,
            pedagogy_type=pedagogy_type, user_id=user_id,
            chunk_id=chunk_id,
        )

    def _add_doc_and_chunk(self):
        """Insère un document + un chunk, retourne (doc_id, chunk_id)."""
        import sqlite3
        with sqlite3.connect(self.db.DB_PATH) as conn:
            cur = conn.execute(
                "INSERT INTO documents (title, source_type, filename, raw_text, cleaned_text, char_count) "
                "VALUES ('Doc test', 'txt', 'f.txt', 'raw', 'cleaned', 7)"
            )
            doc_id = cur.lastrowid
            cur2 = conn.execute(
                "INSERT INTO chunks (document_id, chunk_index, section_title, chunk_text, char_count) "
                "VALUES (?, 0, 'Section Test', 'Texte du chunk test.', 20)",
                (doc_id,),
            )
            chunk_id = cur2.lastrowid
        return doc_id, chunk_id


# ─────────────────────────────────────────────────────────────────────────────
# Tests ui_helpers
# ─────────────────────────────────────────────────────────────────────────────

class TestUiHelpers(unittest.TestCase):

    def setUp(self):
        from ui_helpers import (
            _ERROR_LABELS, _build_recommendations, _build_report,
            _kpi_card, _mastery_state, _truncate_label,
        )
        self.el  = _ERROR_LABELS
        self.tl  = _truncate_label
        self.kpi = _kpi_card
        self.ms  = _mastery_state
        self.br  = _build_recommendations
        self.rep = _build_report

    # _truncate_label
    def test_truncate_short(self):
        self.assertEqual(self.tl("abc", 10), "abc")

    def test_truncate_long(self):
        result = self.tl("abcdefghijklmnop", 5)
        self.assertEqual(len(result), 5)
        self.assertTrue(result.endswith("…"))

    # _kpi_card
    def test_kpi_card_contains_value(self):
        html = self.kpi("X", "LABEL", "42 %", "#ff0000")
        self.assertIn("42 %", html)
        self.assertIn("LABEL", html)
        self.assertIn("#ff0000", html)

    def test_kpi_card_returns_string(self):
        self.assertIsInstance(self.kpi("🎯", "Score", "80 %"), str)

    # _mastery_state
    def test_mastery_fragile_degradation(self):
        row = {"mastery_class": "Fragile", "trend": "Dégradation", "days_until_review": -1}
        icon, label, color = self.ms(row)
        self.assertEqual(label, "Régression active")
        self.assertEqual(color, "#dc2626")

    def test_mastery_maitrise_overdue(self):
        row = {"mastery_class": "Maîtrisé", "trend": "Stable", "days_until_review": -2}
        _, label, _ = self.ms(row)
        self.assertEqual(label, "Oubli possible")

    def test_mastery_consolidation_progression(self):
        row = {"mastery_class": "En consolidation", "trend": "Amélioration", "days_until_review": 3}
        _, label, _ = self.ms(row)
        self.assertEqual(label, "Forte progression")

    # _build_recommendations
    def test_recommendations_empty_df(self):
        recs = self.br(pd.DataFrame(), pd.DataFrame())
        self.assertEqual(recs, [])

    def test_recommendations_max_5(self):
        df = pd.DataFrame([
            {"section_label": f"S{i}", "mastery_class": "Fragile",
             "avg_score": 0.3, "attempts_count": 2,
             "review_status": "En retard", "trend": "Dégradation",
             "dominant_error_type": "oubli_etape"}
            for i in range(10)
        ])
        recs = self.br(df, pd.DataFrame())
        self.assertLessEqual(len(recs), 5)

    # _build_report
    def test_report_contains_header(self):
        df_all    = pd.DataFrame({"score": [0.8, 0.6]})
        df_topics = pd.DataFrame({"topic": ["T1"], "avg_score": [0.7], "attempts": [2]})
        report    = self.rep(df_all, df_topics, pd.DataFrame())
        self.assertIn("RAPPORT DE PROGRESSION", report)
        self.assertIn("2", report)  # 2 tentatives

    # _ERROR_LABELS — régression bug dict dupliqué
    def test_error_labels_correct_keys(self):
        self.assertIn("oubli_etape",     self.el)
        self.assertIn("confusion_notion", self.el)
        self.assertNotIn("memory",        self.el)   # clé morte supprimée
        self.assertNotIn("attention",     self.el)   # clé morte supprimée


# ─────────────────────────────────────────────────────────────────────────────
# Tests database.py
# ─────────────────────────────────────────────────────────────────────────────

class TestDatabaseInit(_DbTestCase):

    def test_all_tables_created(self):
        import sqlite3
        with sqlite3.connect(self.db.DB_PATH) as conn:
            tables = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}
        expected = {"attempts", "documents", "chunks", "user_learning_profile"}
        self.assertTrue(expected.issubset(tables), f"Tables manquantes : {expected - tables}")


class TestDatabaseAttempts(_DbTestCase):

    def test_save_and_get_attempts(self):
        self._add_attempt(score=0.75)
        df = self.db.get_attempts("default")
        self.assertEqual(len(df), 1)
        self.assertAlmostEqual(float(df.iloc[0]["score"]), 0.75)

    def test_user_isolation(self):
        """Invariant TASK-019 : user A ne voit pas les données de user B."""
        self._add_attempt(score=0.9, user_id="alice")
        self._add_attempt(score=0.5, user_id="bob")

        df_alice = self.db.get_attempts("alice")
        df_bob   = self.db.get_attempts("bob")

        self.assertEqual(len(df_alice), 1)
        self.assertEqual(len(df_bob),   1)
        self.assertAlmostEqual(float(df_alice.iloc[0]["score"]), 0.9)
        self.assertAlmostEqual(float(df_bob.iloc[0]["score"]),   0.5)

    def test_get_attempts_empty_for_unknown_user(self):
        self._add_attempt(user_id="alice")
        df = self.db.get_attempts("nobody")
        self.assertTrue(df.empty)

    def test_score_evolution_chronological(self):
        """get_score_evolution retourne les scores en ordre chronologique (ASC)."""
        import sqlite3
        # Inserts avec created_at distincts pour garantir l'ordre
        timestamps = ["2026-05-01 10:00:00", "2026-05-01 11:00:00", "2026-05-01 12:00:00"]
        scores_in  = [0.4, 0.6, 0.8]
        with sqlite3.connect(self.db.DB_PATH) as conn:
            for ts, sc in zip(timestamps, scores_in):
                conn.execute(
                    "INSERT INTO attempts (user_id, question, user_answer, expected_answer, "
                    "correction, score, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    ("default", "Q", "A", "E", "C", sc, ts),
                )
        df = self.db.get_score_evolution(limit=10, user_id="default")
        scores = list(df["score"])
        self.assertEqual(scores, sorted(scores))

    def test_error_frequency_user_filtered(self):
        self._add_attempt(error_type="oubli_etape",     user_id="alice")
        self._add_attempt(error_type="confusion_notion", user_id="bob")

        df_alice = self.db.get_error_frequency("alice")
        self.assertEqual(len(df_alice), 1)
        self.assertEqual(df_alice.iloc[0]["error_type"], "oubli_etape")

    def test_topic_stats_user_filtered(self):
        self._add_attempt(score=0.8, topic="Procédure A", user_id="alice")
        self._add_attempt(score=0.4, topic="Procédure B", user_id="bob")

        df = self.db.get_topic_stats("alice")
        self.assertEqual(len(df), 1)
        # _normalize_topic applique .capitalize() → "Procédure A" devient "Procédure a"
        self.assertEqual(df.iloc[0]["topic"], "Procédure a")


class TestDatabaseChunkMastery(_DbTestCase):

    def _attempts_for_chunk(self, chunk_id, scores, user_id="default"):
        for s in scores:
            self._add_attempt(score=s, user_id=user_id, chunk_id=chunk_id)

    def test_chunk_mastery_fragile(self):
        _, chunk_id = self._add_doc_and_chunk()
        self._attempts_for_chunk(chunk_id, [0.3, 0.5, 0.4])
        result = self.db.get_chunk_mastery(chunk_id, "default")
        self.assertEqual(result, "Fragile")

    def test_chunk_mastery_maitrise(self):
        _, chunk_id = self._add_doc_and_chunk()
        self._attempts_for_chunk(chunk_id, [0.9, 0.85, 0.88])
        result = self.db.get_chunk_mastery(chunk_id, "default")
        self.assertEqual(result, "Maîtrisé")

    def test_chunk_mastery_consolidation(self):
        _, chunk_id = self._add_doc_and_chunk()
        self._attempts_for_chunk(chunk_id, [0.7, 0.65])
        result = self.db.get_chunk_mastery(chunk_id, "default")
        self.assertEqual(result, "En consolidation")

    def test_chunk_mastery_user_isolation(self):
        _, chunk_id = self._add_doc_and_chunk()
        self._attempts_for_chunk(chunk_id, [0.9, 0.9, 0.9], "alice")   # Maîtrisé pour alice
        self._attempts_for_chunk(chunk_id, [0.2, 0.3, 0.2], "bob")     # Fragile pour bob
        self.assertEqual(self.db.get_chunk_mastery(chunk_id, "alice"), "Maîtrisé")
        self.assertEqual(self.db.get_chunk_mastery(chunk_id, "bob"),   "Fragile")

    def test_chunk_mastery_no_data(self):
        self.assertIsNone(self.db.get_chunk_mastery(9999, "default"))

    def test_chunk_history_user_isolation(self):
        """Invariant TASK-026 : l'historique de questions d'un chunk est per-user."""
        _, chunk_id = self._add_doc_and_chunk()
        self._add_attempt(score=0.8, user_id="alice", chunk_id=chunk_id,
                          question="Question alice")
        self._add_attempt(score=0.5, user_id="bob",   chunk_id=chunk_id,
                          question="Question bob")
        alice_history = self.db.get_chunk_question_history(chunk_id, user_id="alice")
        bob_history   = self.db.get_chunk_question_history(chunk_id, user_id="bob")
        alice_qs = [h["question"] for h in alice_history]
        bob_qs   = [h["question"] for h in bob_history]
        self.assertIn("Question alice", alice_qs)
        self.assertNotIn("Question bob", alice_qs)
        self.assertIn("Question bob", bob_qs)
        self.assertNotIn("Question alice", bob_qs)


class TestClassifyMastery(unittest.TestCase):
    """classify_mastery est une fonction pure DataFrame → pas besoin de DB."""

    def setUp(self):
        from database import classify_mastery
        self.fn = classify_mastery

    def _row(self, avg_score, attempts_count, last_score=None, last_attempt_date="2026-05-01 10:00:00"):
        return {
            "chunk_id": 1, "section_label": "S1", "document_title": "D",
            "avg_score": avg_score, "attempts_count": attempts_count,
            "last_score": last_score if last_score is not None else avg_score,
            "dominant_error_type": None, "last_attempt_date": last_attempt_date,
        }

    def test_fragile_classification(self):
        df = pd.DataFrame([self._row(0.45, 3)])
        result = self.fn(df)
        self.assertEqual(result.iloc[0]["mastery_class"], "Fragile")

    def test_maitrise_classification(self):
        df = pd.DataFrame([self._row(0.85, 4)])
        result = self.fn(df)
        self.assertEqual(result.iloc[0]["mastery_class"], "Maîtrisé")

    def test_consolidation_classification(self):
        df = pd.DataFrame([self._row(0.70, 2)])
        result = self.fn(df)
        self.assertEqual(result.iloc[0]["mastery_class"], "En consolidation")

    def test_trend_amelioration(self):
        df = pd.DataFrame([self._row(avg_score=0.6, attempts_count=3, last_score=0.8)])
        result = self.fn(df)
        self.assertEqual(result.iloc[0]["trend"], "Amélioration")

    def test_trend_degradation(self):
        df = pd.DataFrame([self._row(avg_score=0.7, attempts_count=3, last_score=0.5)])
        result = self.fn(df)
        self.assertEqual(result.iloc[0]["trend"], "Dégradation")

    def test_next_review_column_present(self):
        df = pd.DataFrame([self._row(0.5, 2)])
        result = self.fn(df)
        self.assertIn("next_review",       result.columns)
        self.assertIn("days_until_review", result.columns)
        self.assertIn("review_status",     result.columns)


class TestLearningProfile(_DbTestCase):

    def test_get_profile_unknown_user(self):
        self.assertIsNone(self.db.get_learning_profile("nobody"))

    def test_compute_and_get_profile(self):
        for pedagogy, score in [
            ("question_directe", 0.7),
            ("cas_pratique",     0.8),
            ("reformulation",    0.6),
            ("vrai_faux",        0.4),
        ]:
            self.db.save_attempt(
                question="Q", user_answer="A", expected_answer="E",
                correction="C", score=score, pedagogy_type=pedagogy,
                topic="T1", user_id="default",
            )
        profile = self.db.compute_and_save_learning_profile("default")
        self.assertEqual(profile["user_id"], "default")
        self.assertIsNotNone(profile["preferred_pedagogy"])
        self.assertGreater(profile["average_score"], 0)
        self.assertIsInstance(profile["fragile_topics"], list)

        loaded = self.db.get_learning_profile("default")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["user_id"], "default")
        self.assertIsInstance(loaded["fragile_topics"], list)

    def test_profile_user_isolation(self):
        self.db.save_attempt(
            question="Q", user_answer="A", expected_answer="E",
            correction="C", score=0.9, pedagogy_type="cas_pratique",
            topic="T", user_id="alice",
        )
        self.db.save_attempt(
            question="Q", user_answer="A", expected_answer="E",
            correction="C", score=0.3, pedagogy_type="cas_pratique",
            topic="T", user_id="bob",
        )
        p_alice = self.db.compute_and_save_learning_profile("alice")
        p_bob   = self.db.compute_and_save_learning_profile("bob")
        self.assertGreater(p_alice["average_score"], p_bob["average_score"])

    def test_fragile_topics_populated(self):
        for _ in range(3):
            self.db.save_attempt(
                question="Q", user_answer="A", expected_answer="E",
                correction="C", score=0.3, topic="Notion fragile",
                pedagogy_type="reformulation", user_id="default",
            )
        profile = self.db.compute_and_save_learning_profile("default")
        self.assertIn("Notion fragile", profile["fragile_topics"])


# ─────────────────────────────────────────────────────────────────────────────
# Tests ai_service._choose_question_type
# ─────────────────────────────────────────────────────────────────────────────

class TestChooseQuestionType(unittest.TestCase):
    """
    Teste la logique de sélection du type de question sans appel API.
    Vérifie les trois niveaux de priorité : rotation → mastery → profil.
    """

    def setUp(self):
        from ai_service import _choose_question_type, QUESTION_TYPES
        self.fn    = _choose_question_type
        self.types = QUESTION_TYPES

    def test_no_history_no_bias_returns_valid_type(self):
        result = self.fn([])
        self.assertIn(result, self.types)

    def test_mastery_bias_applied_over_rotation(self):
        # Tous les types sont équitables (1 occurrence chacun sauf reformulation)
        # mastery Fragile → favorise reformulation/consequence/cas_pratique
        used = ["question_directe", "vrai_faux", "question_piege",
                "cas_pratique", "consequence"]  # reformulation = 0 occurrences
        result = self.fn(used, mastery_class="Fragile")
        # reformulation est le seul candidat équitable ET dans le biais Fragile
        self.assertEqual(result, "reformulation")

    def test_profile_bias_as_tiebreaker(self):
        # 2 types equitables : question_directe et vrai_faux (0 occurrences chacun)
        # mastery None → pas de biais mastery → les deux sont candidats
        # profil logical → question_directe doit être choisi
        used = ["cas_pratique", "reformulation", "consequence", "question_piege"]
        result = self.fn(used, mastery_class=None, profile_types=["question_directe"])
        self.assertEqual(result, "question_directe")

    def test_profile_bias_no_match_falls_back(self):
        # profile_types ne correspond à aucun candidat équitable → rotation normale
        # Tous types à 1 occurrence sauf question_directe (0) → seul candidat
        used = ["cas_pratique", "vrai_faux", "question_piege", "reformulation", "consequence"]
        result = self.fn(used, mastery_class=None, profile_types=["reformulation"])
        # reformulation est épuisé dans used, question_directe est le seul à 0
        self.assertEqual(result, "question_directe")

    def test_mastery_priority_over_profile(self):
        # mastery Maîtrisé → biais vers question_piege/cas_pratique/consequence
        # profile → narrative → reformulation
        # Le biais mastery doit l'emporter sur le biais profil
        used = ["question_directe", "vrai_faux"]  # question_piege, cas_pratique, consequence, reformulation à 0
        result = self.fn(used, mastery_class="Maîtrisé", profile_types=["reformulation"])
        # reformulation n'est PAS dans le biais Maîtrisé → mastery l'exclut
        self.assertIn(result, ["question_piege", "cas_pratique", "consequence"])

    def test_no_profile_unchanged_behavior(self):
        # Sans profile_types, comportement identique à avant TASK-024
        result = self.fn([], mastery_class="Fragile", profile_types=None)
        self.assertIn(result, ["reformulation", "consequence", "cas_pratique"])


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    loader  = unittest.TestLoader()
    suite   = unittest.TestSuite()
    for cls in (
        TestUiHelpers,
        TestDatabaseInit,
        TestDatabaseAttempts,
        TestDatabaseChunkMastery,
        TestClassifyMastery,
        TestLearningProfile,
        TestChooseQuestionType,
    ):
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
