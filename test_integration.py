"""
Tests d'intégration — ADDISCO OPS — TASK-064
Pipeline complet : ingest → generate_question → correct_answer → save_attempt → analytics
Aucun appel API réel. LLM et embeddings sont mockés.
Base SQLite temporaire isolée par test.

Exécution : python test_integration.py
"""
import json
import os
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


# ── Constantes de test ────────────────────────────────────────────────────────

FAKE_DIM = 1536
FAKE_EMBEDDING = [0.1] * FAKE_DIM
FAKE_EMBEDDING_BYTES = struct.pack(f"<{FAKE_DIM}f", *FAKE_EMBEDDING)

FAKE_QUESTION = "Quelles sont les conditions requises pour appliquer cette règle ?"

FAKE_CORRECTION_JSON = json.dumps({
    "score": 0.85,
    "expected_answer": "Il faut remplir les conditions A, B et C.",
    "correction": "Bonne réponse. Les conditions sont bien identifiées dans le texte.",
    "error_type": "correct",
    "topic": "conditions d'application",
})


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_temp_db() -> Path:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    return Path(tmp.name)


class _IntegrationTestCase(unittest.TestCase):
    """Base : DB temporaire isolée + mocks LLM et embeddings actifs."""

    def setUp(self):
        import database as db
        self._orig_path = db.DB_PATH
        self._tmp_path = _make_temp_db()
        db.DB_PATH = self._tmp_path
        db.init_db()
        self.db = db

        self._patch_embed = patch("ai_service.call_embedding_api", return_value=FAKE_EMBEDDING)
        self._patch_chat = patch("ai_service.call_chat_completion", return_value=FAKE_QUESTION)
        self.mock_embed = self._patch_embed.start()
        self.mock_chat = self._patch_chat.start()

    def tearDown(self):
        self._patch_embed.stop()
        self._patch_chat.stop()
        import database as db
        db.DB_PATH = self._orig_path
        try:
            os.unlink(self._tmp_path)
        except OSError:
            pass


# ── Ingestion document ────────────────────────────────────────────────────────

class TestIngestionPipeline(_IntegrationTestCase):

    _SAMPLE_CONTENT = (
        b"Les conditions d'application de la regle principale sont les suivantes : "
        b"A, B et C doivent etre remplies simultanement par l'operateur. "
        b"En cas de doute, consulter le responsable hierarchique direct. " * 10
    )

    def test_ingest_creates_document_and_chunks(self):
        from document_service import ingest_document
        import sqlite3

        doc_id = ingest_document(
            title="Doc intégration",
            source_type="txt",
            filename="test.txt",
            file_bytes=self._SAMPLE_CONTENT,
        )
        self.assertIsInstance(doc_id, int)
        self.assertGreater(doc_id, 0)

        with sqlite3.connect(self.db.DB_PATH) as conn:
            n_docs = conn.execute(
                "SELECT COUNT(*) FROM documents WHERE id = ?", (doc_id,)
            ).fetchone()[0]
            n_chunks = conn.execute(
                "SELECT COUNT(*) FROM chunks WHERE document_id = ?", (doc_id,)
            ).fetchone()[0]
        conn.close()

        self.assertEqual(n_docs, 1)
        self.assertGreater(n_chunks, 0)

    def test_ingest_stores_embeddings(self):
        from document_service import ingest_document
        import sqlite3

        doc_id = ingest_document(
            title="Doc embeddings",
            source_type="txt",
            filename="embed.txt",
            file_bytes=self._SAMPLE_CONTENT,
        )
        with sqlite3.connect(self.db.DB_PATH) as conn:
            n_with_emb = conn.execute(
                "SELECT COUNT(*) FROM chunks WHERE document_id = ? AND embedding IS NOT NULL",
                (doc_id,),
            ).fetchone()[0]
        conn.close()

        self.assertGreater(n_with_emb, 0)
        self.assertGreater(self.mock_embed.call_count, 0)

    def test_ingest_empty_raises(self):
        from document_service import ingest_document
        with self.assertRaises(ValueError):
            ingest_document(
                title="Vide", source_type="txt", filename="vide.txt", file_bytes=b""
            )

    def test_ingest_too_large_raises(self):
        from document_service import ingest_document
        with self.assertRaises(ValueError):
            ingest_document(
                title="Gros",
                source_type="txt",
                filename="gros.txt",
                file_bytes=b"x" * (11 * 1024 * 1024),
            )


# ── Génération de question ────────────────────────────────────────────────────

VALID_QUESTION_TYPES = {
    "question_directe", "cas_pratique", "vrai_faux",
    "question_piege", "reformulation", "consequence",
}


class TestQuestionGenerationPipeline(_IntegrationTestCase):

    def _seed_doc_with_chunk(self) -> tuple[int, int]:
        """Insère un document + chunk avec embedding, retourne (doc_id, chunk_id)."""
        import sqlite3
        with sqlite3.connect(self.db.DB_PATH) as conn:
            cur = conn.execute(
                "INSERT INTO documents "
                "(title, source_type, filename, raw_text, cleaned_text, char_count) "
                "VALUES ('Doc test', 'txt', 't.txt', 'raw', 'contenu pédagogique test', 25)"
            )
            doc_id = cur.lastrowid
            cur2 = conn.execute(
                "INSERT INTO chunks "
                "(document_id, chunk_index, section_title, chunk_text, char_count, embedding) "
                "VALUES (?, 0, 'Section', 'Contenu pédagogique du chunk intégration.', 41, ?)",
                (doc_id, FAKE_EMBEDDING_BYTES),
            )
            chunk_id = cur2.lastrowid
        conn.close()
        return doc_id, chunk_id

    def test_generate_returns_four_tuple(self):
        from ai_service import generate_question
        result = generate_question(source_text="Texte source test.", user_id="tuser")
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 4)

    def test_generate_question_string(self):
        from ai_service import generate_question
        question, _, _, _ = generate_question(
            source_text="Texte source test.", user_id="tuser"
        )
        self.assertIsInstance(question, str)
        self.assertGreater(len(question), 0)

    def test_generate_question_type_valid(self):
        from ai_service import generate_question
        _, _, question_type, _ = generate_question(
            source_text="Texte source.", user_id="tuser"
        )
        self.assertIn(question_type, VALID_QUESTION_TYPES)

    def test_generate_with_document_id(self):
        from ai_service import generate_question
        doc_id, _ = self._seed_doc_with_chunk()
        question, chunk_ids, question_type, rag_chunks = generate_question(
            source_text="contenu pédagogique",
            document_id=doc_id,
            user_id="tuser",
        )
        self.assertEqual(question, FAKE_QUESTION)
        self.assertIn(question_type, VALID_QUESTION_TYPES)
        self.assertIsInstance(chunk_ids, list)

    def test_generate_fallback_no_document(self):
        """Sans document_id, le fallback texte brut fonctionne."""
        from ai_service import generate_question
        question, chunk_ids, question_type, _ = generate_question(
            source_text="Texte brut sans document.", user_id="tuser"
        )
        self.assertEqual(question, FAKE_QUESTION)
        self.assertIsInstance(chunk_ids, list)

    def test_generate_raises_on_llm_failure(self):
        """Si le LLM renvoie None, generate_question lève RuntimeError."""
        from ai_service import generate_question
        self.mock_chat.return_value = None
        with self.assertRaises(RuntimeError):
            generate_question(source_text="Texte test panne LLM.", user_id="tuser")


# ── Correction de réponse ─────────────────────────────────────────────────────

class TestCorrectionPipeline(_IntegrationTestCase):

    def setUp(self):
        super().setUp()
        self.mock_chat.return_value = FAKE_CORRECTION_JSON

    def test_correct_returns_dict(self):
        from ai_service import correct_answer
        result = correct_answer(
            question=FAKE_QUESTION,
            user_answer="Il faut remplir les conditions A, B et C simultanément.",
            source_text="Texte source pédagogique.",
        )
        self.assertIsInstance(result, dict)
        for key in ("score", "expected_answer", "correction", "error_type", "topic"):
            self.assertIn(key, result)

    def test_correct_score_in_range(self):
        from ai_service import correct_answer
        result = correct_answer(
            question=FAKE_QUESTION,
            user_answer="Les conditions requises sont bien identifiées dans ce texte.",
            source_text="Texte source.",
        )
        self.assertGreaterEqual(result["score"], 0.0)
        self.assertLessEqual(result["score"], 1.0)

    def test_correct_parses_fake_json(self):
        from ai_service import correct_answer
        result = correct_answer(
            question=FAKE_QUESTION,
            user_answer="Il faut respecter les conditions A, B et C décrites.",
            source_text="Texte source.",
        )
        self.assertAlmostEqual(result["score"], 0.85)
        self.assertEqual(result["error_type"], "correct")

    def test_correct_rejects_empty_answer(self):
        from ai_service import correct_answer
        result = correct_answer(
            question=FAKE_QUESTION,
            user_answer="",
            source_text="Texte source.",
        )
        self.assertEqual(result["score"], 0.0)
        self.assertEqual(result["error_type"], "non_evaluable")
        self.mock_chat.assert_not_called()

    def test_correct_rejects_too_short(self):
        from ai_service import correct_answer
        result = correct_answer(
            question=FAKE_QUESTION,
            user_answer="oui",
            source_text="Texte source.",
        )
        self.assertEqual(result["error_type"], "non_evaluable")
        self.mock_chat.assert_not_called()

    def test_correct_fallback_on_llm_none(self):
        from ai_service import correct_answer
        self.mock_chat.return_value = None
        result = correct_answer(
            question=FAKE_QUESTION,
            user_answer="Il faut respecter les conditions requises dans le document.",
            source_text="Texte source.",
        )
        self.assertEqual(result["score"], 0.0)
        self.assertIn("indisponible", result["correction"])

    def test_correct_fallback_on_invalid_json(self):
        from ai_service import correct_answer
        self.mock_chat.return_value = "ce n'est pas du JSON valide"
        result = correct_answer(
            question=FAKE_QUESTION,
            user_answer="Il faut respecter les conditions requises dans le document.",
            source_text="Texte source.",
        )
        self.assertEqual(result["score"], 0.0)


# ── Save attempt + analytics ──────────────────────────────────────────────────

class TestAnalyticsPipeline(_IntegrationTestCase):

    def test_save_and_retrieve(self):
        self.db.save_attempt(
            question="Quelle est la règle principale ?",
            user_answer="La règle principale est l'application des conditions.",
            expected_answer="Conditions A, B, C.",
            correction="Réponse correcte mais incomplète.",
            score=0.7,
            error_type="oubli_etape",
            topic="Règle principale",
            pedagogy_type="question_directe",
            user_id="t_user",
        )
        df = self.db.get_attempts(user_id="t_user")
        self.assertEqual(len(df), 1)
        self.assertAlmostEqual(float(df.iloc[0]["score"]), 0.7)

    def test_attempts_count(self):
        for i in range(4):
            self.db.save_attempt(
                question=f"Q{i}",
                user_answer="Réponse suffisamment longue pour être valide.",
                expected_answer="EA",
                correction="C",
                score=0.5,
                user_id="t_count",
            )
        self.assertEqual(self.db.get_attempts_count(user_id="t_count"), 4)

    def test_score_evolution_returns_data(self):
        for score in (0.4, 0.6, 0.8):
            self.db.save_attempt(
                question="Q",
                user_answer="R",
                expected_answer="E",
                correction="C",
                score=score,
                user_id="t_evo",
            )
        df = self.db.get_score_evolution(user_id="t_evo")
        self.assertGreater(len(df), 0)

    def test_chunk_stats_with_chunk_id(self):
        """save_attempt avec chunk_id → get_chunk_stats retourne des données."""
        import sqlite3
        with sqlite3.connect(self.db.DB_PATH) as conn:
            cur = conn.execute(
                "INSERT INTO documents (title, source_type, filename, raw_text, cleaned_text, char_count) "
                "VALUES ('D', 'txt', 'f.txt', 'r', 'c', 1)"
            )
            doc_id = cur.lastrowid
            cur2 = conn.execute(
                "INSERT INTO chunks (document_id, chunk_index, chunk_text, char_count) "
                "VALUES (?, 0, 'chunk text', 10)", (doc_id,)
            )
            chunk_id = cur2.lastrowid
        conn.close()

        self.db.save_attempt(
            question="Q chunk",
            user_answer="R",
            expected_answer="E",
            correction="C",
            score=0.9,
            user_id="t_chunk",
            chunk_id=chunk_id,
        )
        df = self.db.get_chunk_stats(user_id="t_chunk")
        self.assertGreater(len(df), 0)

    def test_isolation_between_users(self):
        """Les données d'un user ne contaminent pas un autre."""
        self.db.save_attempt(
            question="Q", user_answer="R", expected_answer="E",
            correction="C", score=1.0, user_id="user_a",
        )
        self.db.save_attempt(
            question="Q", user_answer="R", expected_answer="E",
            correction="C", score=0.0, user_id="user_b",
        )
        self.assertEqual(self.db.get_attempts_count(user_id="user_a"), 1)
        self.assertEqual(self.db.get_attempts_count(user_id="user_b"), 1)
        df_a = self.db.get_attempts(user_id="user_a")
        self.assertAlmostEqual(float(df_a.iloc[0]["score"]), 1.0)


# ── Pipeline bout-en-bout ─────────────────────────────────────────────────────

class TestFullSessionPipeline(_IntegrationTestCase):
    """Simule une session complète : ingest → generate → correct → save → analytics."""

    _SAMPLE = (
        b"Les conditions d'application de la regle principale sont A, B et C. "
        b"Elles doivent etre remplies simultanement par tout operateur. " * 12
    )

    def test_full_pipeline_end_to_end(self):
        from document_service import ingest_document
        from ai_service import generate_question, correct_answer

        # 1. Ingestion
        doc_id = ingest_document(
            title="Session test",
            source_type="txt",
            filename="session.txt",
            file_bytes=self._SAMPLE,
        )
        self.assertIsInstance(doc_id, int)

        # 2. Génération (mock retourne FAKE_QUESTION)
        question, chunk_ids, question_type, rag_chunks = generate_question(
            source_text="conditions application règle",
            document_id=doc_id,
            user_id="session_user",
        )
        self.assertEqual(question, FAKE_QUESTION)
        self.assertIn(question_type, VALID_QUESTION_TYPES)

        # 3. Correction — switch mock vers JSON
        self.mock_chat.return_value = FAKE_CORRECTION_JSON
        user_answer = "Il faut remplir les conditions A, B et C simultanément."
        result = correct_answer(
            question=question,
            user_answer=user_answer,
            source_text="conditions application règle",
        )
        self.assertGreater(result["score"], 0.0)
        self.assertIn("error_type", result)

        # 4. Sauvegarde
        self.db.save_attempt(
            question=question,
            user_answer=user_answer,
            expected_answer=result["expected_answer"],
            correction=result["correction"],
            score=result["score"],
            error_type=result["error_type"],
            topic=result["topic"],
            pedagogy_type=question_type,
            document_id=doc_id,
            chunk_id=chunk_ids[0] if chunk_ids else None,
            user_id="session_user",
        )

        # 5. Analytics
        count = self.db.get_attempts_count(user_id="session_user")
        self.assertEqual(count, 1)
        df = self.db.get_attempts(user_id="session_user")
        self.assertAlmostEqual(float(df.iloc[0]["score"]), result["score"])

    def test_pipeline_multiple_sessions(self):
        """Trois sessions successives → compteur correct, évolution de score."""
        from ai_service import correct_answer
        scores = [0.5, 0.75, 0.9]
        for score_val in scores:
            self.mock_chat.return_value = json.dumps({
                "score": score_val,
                "expected_answer": "EA",
                "correction": "Correction.",
                "error_type": "correct" if score_val >= 0.8 else "oubli_etape",
                "topic": "règle",
            })
            result = correct_answer(
                question=FAKE_QUESTION,
                user_answer="Il faut respecter les conditions requises décrites dans le texte.",
                source_text="Texte source.",
            )
            self.db.save_attempt(
                question=FAKE_QUESTION,
                user_answer="Il faut respecter les conditions requises décrites dans le texte.",
                expected_answer=result["expected_answer"],
                correction=result["correction"],
                score=result["score"],
                user_id="multi_session_user",
            )

        self.assertEqual(self.db.get_attempts_count(user_id="multi_session_user"), 3)
        df = self.db.get_score_evolution(user_id="multi_session_user")
        self.assertGreater(len(df), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
