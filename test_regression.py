"""
Tests de non-régression — ADDISCO OPS
Couvre : database.py (invariants critiques) + ui_helpers.py (fonctions pures)
         + ai_service._choose_question_type / explain_type_choice
         + adaptive_engine.REVIEW_INTERVALS (tripwires de cohérence)
         + rag_service._cosine_similarity (comportement post-numpy)

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

    # ── TASK-035 : validation des entrées ────────────────────────────────────
    def test_sanitize_user_id(self):
        from ui_helpers import sanitize_user_id
        self.assertEqual(sanitize_user_id(""),           "default")
        self.assertEqual(sanitize_user_id("   "),        "default")
        self.assertEqual(sanitize_user_id("  alice  "),  "alice")
        self.assertEqual(sanitize_user_id("a" * 60),     "a" * 50)
        self.assertEqual(sanitize_user_id("bob"),        "bob")

    def test_validate_doc_title(self):
        from ui_helpers import validate_doc_title
        self.assertIsNone(validate_doc_title("Procédure accueil"))
        self.assertIsNotNone(validate_doc_title(""))
        self.assertIsNotNone(validate_doc_title("   "))
        self.assertIsNotNone(validate_doc_title("x" * 201))
        self.assertIsNone(validate_doc_title("x" * 200))

    def test_validate_file_size(self):
        from ui_helpers import validate_file_size, _FILE_MAX_BYTES
        self.assertIsNone(validate_file_size(0))
        self.assertIsNone(validate_file_size(_FILE_MAX_BYTES))
        self.assertIsNotNone(validate_file_size(_FILE_MAX_BYTES + 1))
        err = validate_file_size(25 * 1024 * 1024)
        self.assertIsNotNone(err)
        self.assertIn("25", err)

    def test_check_app_password(self):
        from ui_helpers import check_app_password
        self.assertTrue(check_app_password("secret", "secret"))
        self.assertFalse(check_app_password("wrong", "secret"))
        self.assertFalse(check_app_password("", "secret"))
        self.assertTrue(check_app_password("", ""))


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

    def test_export_columns_present(self):
        """TASK-031 : les colonnes nécessaires à l'export CSV sont toutes présentes."""
        self._add_attempt(score=0.6)
        df = self.db.get_attempts("default")
        required = [
            "created_at", "question", "user_answer", "expected_answer",
            "score", "error_type", "topic", "pedagogy_type", "response_time_seconds",
        ]
        for col in required:
            self.assertIn(col, df.columns, f"colonne manquante pour export : {col}")

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

    def test_adaptive_interval_amelioration_allonge(self):
        """Invariant TASK-027 : Fragile+Amélioration → interval > Fragile+Stable."""
        from database import _adaptive_interval
        fragile_stable     = _adaptive_interval("Fragile", "Stable")
        fragile_amelio     = _adaptive_interval("Fragile", "Amélioration")
        consol_stable      = _adaptive_interval("En consolidation", "Stable")
        consol_amelio      = _adaptive_interval("En consolidation", "Amélioration")
        self.assertGreater(fragile_amelio, fragile_stable)
        self.assertGreater(consol_amelio,  consol_stable)

    def test_adaptive_interval_degradation_reduit(self):
        """Invariant TASK-027 : En consolidation+Dégradation → interval < Stable."""
        from database import _adaptive_interval
        consol_stable = _adaptive_interval("En consolidation", "Stable")
        consol_degrad = _adaptive_interval("En consolidation", "Dégradation")
        self.assertLess(consol_degrad, consol_stable)

    def test_adaptive_interval_maitrise_inchange(self):
        """Invariant TASK-027 : Maîtrisé n'est pas modulé."""
        from database import _adaptive_interval, REVIEW_INTERVALS
        for trend in ("Amélioration", "Stable", "Dégradation", "N/A"):
            self.assertEqual(_adaptive_interval("Maîtrisé", trend), REVIEW_INTERVALS["Maîtrisé"])

    def test_classify_mastery_uses_adaptive_interval(self):
        """next_review d'un chunk Fragile+Amélioration > Fragile+Stable (même date)."""
        date = "2026-05-01 10:00:00"
        df_amelio = pd.DataFrame([self._row(avg_score=0.45, attempts_count=3,
                                            last_score=0.75, last_attempt_date=date)])
        df_stable = pd.DataFrame([self._row(avg_score=0.45, attempts_count=3,
                                            last_score=0.45, last_attempt_date=date)])
        r_amelio = self.fn(df_amelio).iloc[0]
        r_stable = self.fn(df_stable).iloc[0]
        self.assertGreater(r_amelio["next_review"], r_stable["next_review"])


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
# Tests Phase 9.5 — Decision Explainability Layer
# ─────────────────────────────────────────────────────────────────────────────

class TestExplainFunctions(unittest.TestCase):
    """
    Teste les 4 fonctions d'explainability dans ui_helpers.py.
    Fonctions pures — aucune base de données, aucun appel API.
    """

    def setUp(self):
        from ui_helpers import (
            explain_interval_decision,
            explain_priority_decision,
            explain_profile_detection,
            explain_question_decision,
        )
        self.eqd  = explain_question_decision
        self.eid  = explain_interval_decision
        self.eprd = explain_priority_decision
        self.epfd = explain_profile_detection

    # ── explain_question_decision ────────────────────────────────────────────

    def test_eqd_fragile_returns_bias_signal(self):
        signals = self.eqd("reformulation", "Fragile", "N/A", "—", None, None)
        icons   = [s[0] for s in signals]
        texts   = [s[1] for s in signals]
        self.assertIn("⚡", icons)
        self.assertTrue(any("fragile" in t.lower() for t in texts))

    def test_eqd_degradation_adds_signal(self):
        signals = self.eqd("cas_pratique", None, "Dégradation", "—", None, None)
        texts   = [s[1] for s in signals]
        self.assertTrue(any("régression" in t.lower() for t in texts))

    def test_eqd_en_retard_adds_signal(self):
        signals = self.eqd("question_directe", None, "N/A", "En retard", None, None)
        texts   = [s[1] for s in signals]
        self.assertTrue(any("retard" in t.lower() for t in texts))

    def test_eqd_dominant_error_adds_signal(self):
        signals = self.eqd("vrai_faux", None, "N/A", "—", "oubli_etape", None)
        texts   = [s[1] for s in signals]
        self.assertTrue(any("Oubli" in t for t in texts))

    def test_eqd_profile_adds_signal(self):
        signals = self.eqd("cas_pratique", None, "N/A", "—", None, "procedural")
        texts   = [s[1] for s in signals]
        self.assertTrue(any("procédural" in t.lower() for t in texts))

    def test_eqd_no_signals_when_empty(self):
        signals = self.eqd("question_directe", None, "N/A", "—", None, None)
        self.assertEqual(signals, [])

    def test_eqd_maitrise_returns_correct_bias(self):
        signals = self.eqd("question_piege", "Maîtrisé", "Stable", "—", None, None)
        texts   = [s[1] for s in signals]
        self.assertTrue(any("maîtrisée" in t.lower() for t in texts))

    # ── explain_interval_decision ─────────────────────────────────────────────

    def test_eid_fragile_stable(self):
        result = self.eid("Fragile", "Stable")
        self.assertIn("1j", result)
        self.assertIn("prioritaire", result.lower())

    def test_eid_fragile_amelioration(self):
        result = self.eid("Fragile", "Amélioration")
        self.assertIn("2j", result)
        self.assertIn("progression", result.lower())

    def test_eid_consolidation_amelioration(self):
        result = self.eid("En consolidation", "Amélioration")
        self.assertIn("5j", result)
        self.assertIn("espacement", result.lower())

    def test_eid_consolidation_degradation(self):
        result = self.eid("En consolidation", "Dégradation")
        self.assertIn("2j", result)
        self.assertIn("surveillance", result.lower())

    def test_eid_consolidation_stable(self):
        result = self.eid("En consolidation", "Stable")
        self.assertIn("3j", result)

    def test_eid_maitrise(self):
        result = self.eid("Maîtrisé", "Stable")
        self.assertIn("7j", result)
        self.assertIn("maximal", result.lower())

    def test_eid_unknown_returns_empty(self):
        result = self.eid("Inconnu", "N/A")
        self.assertEqual(result, "")

    # ── explain_priority_decision ─────────────────────────────────────────────

    def test_eprd_fragile_score_in_reasons(self):
        row = {"avg_score": 0.42, "mastery_class": "Fragile",
               "review_status": "—", "trend": "N/A",
               "dominant_error_type": None, "attempts_count": 5}
        reasons = self.eprd(row)
        self.assertTrue(any("42 %" in r for r in reasons))
        self.assertTrue(any("fragilité" in r or "Fragile" in r for r in reasons))

    def test_eprd_en_retard_in_reasons(self):
        row = {"avg_score": 0.55, "mastery_class": "En consolidation",
               "review_status": "En retard", "trend": "N/A",
               "dominant_error_type": None, "attempts_count": 5}
        reasons = self.eprd(row)
        self.assertTrue(any("retard" in r.lower() for r in reasons))

    def test_eprd_dominant_error_in_reasons(self):
        row = {"avg_score": 0.4, "mastery_class": "Fragile",
               "review_status": "—", "trend": "N/A",
               "dominant_error_type": "confusion_notion", "attempts_count": 4}
        reasons = self.eprd(row)
        self.assertTrue(any("Confusion" in r for r in reasons))

    def test_eprd_few_attempts_in_reasons(self):
        row = {"avg_score": 0.5, "mastery_class": "En consolidation",
               "review_status": "—", "trend": "N/A",
               "dominant_error_type": None, "attempts_count": 1}
        reasons = self.eprd(row)
        self.assertTrue(any("tentative" in r.lower() for r in reasons))

    def test_eprd_empty_row_no_crash(self):
        reasons = self.eprd({})
        self.assertIsInstance(reasons, list)

    # ── explain_profile_detection ─────────────────────────────────────────────

    def test_epfd_none_profile(self):
        result = self.epfd(None)
        self.assertIn("établi", result.lower())

    def test_epfd_logical_dominant(self):
        profile = {"preferred_pedagogy": "logical", "logical_score": 0.82,
                   "average_score": 0.65}
        result = self.epfd(profile)
        self.assertIn("Analytique", result)
        self.assertIn("82 %", result)

    def test_epfd_procedural_dominant(self):
        profile = {"preferred_pedagogy": "procedural", "procedural_score": 0.74,
                   "average_score": 0.60}
        result = self.epfd(profile)
        self.assertIn("Procédural", result)

    def test_epfd_missing_preferred_returns_fallback(self):
        profile = {"preferred_pedagogy": None, "average_score": 0.5}
        result = self.epfd(profile)
        self.assertIn("insuffisant", result.lower())


# ─────────────────────────────────────────────────────────────────────────────
# Tests ai_service.explain_type_choice
# ─────────────────────────────────────────────────────────────────────────────

class TestExplainTypeChoice(unittest.TestCase):
    """
    Teste explain_type_choice() dans ai_service.py.
    Aucun appel API — logique pure de décision.
    """

    def setUp(self):
        from ai_service import explain_type_choice
        self.fn = explain_type_choice

    def test_no_history_mastery_bias_mentioned(self):
        result = self.fn([], "Fragile", None, "reformulation")
        self.assertIn("Fragile", result)
        self.assertIn("reformulation", result)

    def test_rotation_tier_mentioned(self):
        used   = ["question_directe", "cas_pratique", "vrai_faux", "question_piege", "consequence"]
        result = self.fn(used, None, None, "reformulation")
        self.assertIn("rotation", result.lower())
        self.assertIn("reformulation", result)

    def test_mastery_bias_tier_mentioned(self):
        used   = ["question_directe", "vrai_faux"]
        result = self.fn(used, "Fragile", None, "reformulation")
        self.assertIn("biais", result.lower())
        self.assertIn("Fragile", result)

    def test_profile_tier_mentioned(self):
        used   = ["cas_pratique", "vrai_faux", "question_piege", "reformulation", "consequence"]
        result = self.fn(used, None, "logical", "question_directe")
        self.assertIn("profil", result.lower())

    def test_no_history_no_bias_returns_string(self):
        result = self.fn([], None, None, "cas_pratique")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 5)


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
# Tests Phase 15A — Tripwires cohérence REVIEW_INTERVALS
# ─────────────────────────────────────────────────────────────────────────────

class TestReviewIntervalsCoherence(unittest.TestCase):
    """
    Tripwires : vérifient que REVIEW_INTERVALS reste cohérent avec les valeurs
    hardcodées dans database.get_revision_suggestion (SQL) et dans
    ui_helpers.explain_interval_decision.

    Si REVIEW_INTERVALS change dans adaptive_engine, ces tests tombent et
    signalent explicitement les deux endroits à mettre à jour manuellement :
    - database.py  get_revision_suggestion  lignes '+1 day' / '+3 days'
    - ui_helpers.py explain_interval_decision  dict _special / _default
    """

    def setUp(self):
        from adaptive_engine import REVIEW_INTERVALS, _adaptive_interval
        self.rv = REVIEW_INTERVALS
        self.ai = _adaptive_interval

    # ── Valeurs de base — miroir des constantes SQL ───────────────────────────

    def test_fragile_base_equals_1(self):
        """SQL get_revision_suggestion : '+1 day' correspond à REVIEW_INTERVALS['Fragile']."""
        self.assertEqual(self.rv["Fragile"], 1,
            "Mettre à jour la chaîne SQL '+1 day' dans database.get_revision_suggestion")

    def test_consolidation_base_equals_3(self):
        """SQL get_revision_suggestion : '+3 days' correspond à REVIEW_INTERVALS['En consolidation']."""
        self.assertEqual(self.rv["En consolidation"], 3,
            "Mettre à jour la chaîne SQL '+3 days' dans database.get_revision_suggestion")

    def test_maitrise_base_equals_7(self):
        """ui_helpers._default : (7, ...) correspond à REVIEW_INTERVALS['Maîtrisé']."""
        self.assertEqual(self.rv["Maîtrisé"], 7,
            "Mettre à jour _default['Maîtrisé'] dans ui_helpers.explain_interval_decision")

    # ── Valeurs modulées — miroir de ui_helpers.explain_interval_decision ─────

    def test_fragile_amelioration_equals_2(self):
        """ui_helpers._special : ('Fragile', 'Amélioration') → 2."""
        self.assertEqual(self.ai("Fragile", "Amélioration"), 2,
            "Mettre à jour _special[('Fragile','Amélioration')] dans ui_helpers.explain_interval_decision")

    def test_consolidation_amelioration_equals_5(self):
        """ui_helpers._special : ('En consolidation', 'Amélioration') → 5."""
        self.assertEqual(self.ai("En consolidation", "Amélioration"), 5,
            "Mettre à jour _special[('En consolidation','Amélioration')] dans ui_helpers")

    def test_consolidation_degradation_equals_2(self):
        """ui_helpers._special : ('En consolidation', 'Dégradation') → 2."""
        self.assertEqual(self.ai("En consolidation", "Dégradation"), 2,
            "Mettre à jour _special[('En consolidation','Dégradation')] dans ui_helpers")

    def test_fragile_stable_equals_base(self):
        """Fragile+Stable = REVIEW_INTERVALS['Fragile'] sans modulation."""
        self.assertEqual(self.ai("Fragile", "Stable"), self.rv["Fragile"])

    def test_consolidation_stable_equals_base(self):
        """En consolidation+Stable = REVIEW_INTERVALS['En consolidation'] sans modulation."""
        self.assertEqual(self.ai("En consolidation", "Stable"), self.rv["En consolidation"])

    def test_maitrise_never_modulated(self):
        """Maîtrisé retourne toujours REVIEW_INTERVALS['Maîtrisé'] quelle que soit la tendance."""
        for trend in ("Amélioration", "Stable", "Dégradation", "N/A"):
            with self.subTest(trend=trend):
                self.assertEqual(self.ai("Maîtrisé", trend), self.rv["Maîtrisé"])


# ─────────────────────────────────────────────────────────────────────────────
# Tests Phase 15A — Cosine similarity post-numpy
# ─────────────────────────────────────────────────────────────────────────────

class TestCosineSimilarity(unittest.TestCase):
    """Tests minimaux pour rag_service._cosine_similarity (implémentation numpy)."""

    def setUp(self):
        from rag_service import _cosine_similarity
        self.fn = _cosine_similarity

    def test_identical_vectors_approx_1(self):
        v = [1.0, 0.5, 0.3]
        self.assertAlmostEqual(self.fn(v, v), 1.0, places=5)

    def test_orthogonal_vectors_approx_0(self):
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        self.assertAlmostEqual(self.fn(a, b), 0.0, places=5)

    def test_null_vector_a_returns_0(self):
        self.assertEqual(self.fn([0.0, 0.0, 0.0], [1.0, 0.5, 0.3]), 0.0)

    def test_null_vector_b_returns_0(self):
        self.assertEqual(self.fn([1.0, 0.5, 0.3], [0.0, 0.0, 0.0]), 0.0)


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    loader  = unittest.TestLoader()
    suite   = unittest.TestSuite()
    for cls in (
        TestUiHelpers,
        TestExplainFunctions,
        TestExplainTypeChoice,
        TestDatabaseInit,
        TestDatabaseAttempts,
        TestDatabaseChunkMastery,
        TestClassifyMastery,
        TestLearningProfile,
        TestChooseQuestionType,
        TestReviewIntervalsCoherence,
        TestCosineSimilarity,
    ):
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
