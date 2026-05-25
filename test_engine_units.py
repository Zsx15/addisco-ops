"""
Tests unitaires — engine/ (fonctions pures, zéro DB, zéro API)

Couvre :
  - engine/skill_engine.py      : compute_skill_mastery, classify_skill_mastery
  - engine/question_type.py     : _choose_question_type, explain_type_choice
  - engine/profile_metrics.py   : compute_momentum, compute_learning_velocity,
                                  compute_consistency_score
  - engine/adaptive_difficulty.py : get_difficulty_target, get_error_correction_type,
                                    filter_by_difficulty, choose_adaptive_question_type
  - engine/retention.py         : compute_retention_metrics

Exécution : python test_engine_units.py
"""
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


# ─────────────────────────────────────────────────────────────────────────────
# engine/skill_engine.py
# ─────────────────────────────────────────────────────────────────────────────

class TestSkillEngine(unittest.TestCase):

    def setUp(self):
        from engine.skill_engine import compute_skill_mastery, classify_skill_mastery
        self.compute  = compute_skill_mastery
        self.classify = classify_skill_mastery

    def test_compute_empty_returns_zero(self):
        self.assertEqual(self.compute([]), 0.0)

    def test_compute_perfect(self):
        self.assertEqual(self.compute([1.0, 1.0, 1.0]), 1.0)

    def test_compute_average(self):
        self.assertAlmostEqual(self.compute([0.6, 0.8, 1.0]), 0.8, places=2)

    def test_compute_single_value(self):
        self.assertEqual(self.compute([0.75]), 0.75)

    def test_classify_fragile_below_threshold(self):
        self.assertEqual(self.classify(0.5, 5), "Fragile")

    def test_classify_acquis_above_threshold_enough_attempts(self):
        self.assertEqual(self.classify(0.85, 5), "Acquis")

    def test_classify_acquis_requires_min_attempts(self):
        # score suffisant mais pas assez de tentatives → En cours
        self.assertEqual(self.classify(0.85, 2), "En cours")

    def test_classify_en_cours_mid_range(self):
        self.assertEqual(self.classify(0.70, 5), "En cours")

    def test_classify_boundary_fragile_is_en_cours(self):
        # exactement 0.60 → pas Fragile (< 0.60 requis)
        self.assertEqual(self.classify(0.60, 5), "En cours")

    def test_classify_boundary_acquis_at_threshold(self):
        self.assertEqual(self.classify(0.80, 5), "Acquis")


# ─────────────────────────────────────────────────────────────────────────────
# engine/question_type.py
# ─────────────────────────────────────────────────────────────────────────────

class TestQuestionType(unittest.TestCase):

    def setUp(self):
        from engine.question_type import _choose_question_type, QUESTION_TYPES, _MASTERY_BIAS
        self.choose      = _choose_question_type
        self.all_types   = QUESTION_TYPES
        self.mastery_bias = _MASTERY_BIAS

    def test_empty_history_returns_valid_type(self):
        t = self.choose([], None, None)
        self.assertIn(t, self.all_types)

    def test_rotation_picks_least_used(self):
        # 5 types utilisés une fois, vrai_faux absent → rotation choisit vrai_faux
        used = ["question_directe", "cas_pratique", "reformulation",
                "consequence", "question_piege"]
        self.assertEqual(self.choose(used, None, None), "vrai_faux")

    def test_all_types_reachable_without_history(self):
        results = {self.choose([], None, None) for _ in range(100)}
        self.assertEqual(results, set(self.all_types))

    def test_mastery_bias_fragile(self):
        # Fragile → la majorité des sélections doit provenir du biais
        biased  = set(self.mastery_bias["Fragile"])
        results = {self.choose([], "Fragile", None) for _ in range(30)}
        self.assertTrue(results & biased, "Aucun type du biais Fragile sélectionné")

    def test_mastery_bias_maitrise(self):
        biased  = set(self.mastery_bias["Maîtrisé"])
        results = {self.choose([], "Maîtrisé", None) for _ in range(30)}
        self.assertTrue(results & biased, "Aucun type du biais Maîtrisé sélectionné")

    def test_profile_bias_as_tiebreaker(self):
        # Équité parfaite → profile_type devrait apparaître
        used    = self.all_types * 3  # chacun 3×
        results = {self.choose(used, None, ["reformulation"]) for _ in range(30)}
        self.assertIn("reformulation", results)

    def test_explain_type_choice_returns_string(self):
        from engine.question_type import explain_type_choice
        for t in self.all_types:
            msg = explain_type_choice(
                used_types=[], mastery_class="Fragile",
                profile_pedagogy=None, chosen_type=t,
            )
            self.assertIsInstance(msg, str)
            self.assertGreater(len(msg), 0)


# ─────────────────────────────────────────────────────────────────────────────
# engine/profile_metrics.py
# ─────────────────────────────────────────────────────────────────────────────

class TestProfileMetrics(unittest.TestCase):

    def _rows(self, days_back: list[int], scores: list[float]):
        now = datetime.now()
        return [
            ((now - timedelta(days=d)).isoformat(), s)
            for d, s in zip(days_back, scores)
        ]

    # ── compute_momentum ──────────────────────────────────────────────────────

    def test_momentum_empty(self):
        from engine.profile_metrics import compute_momentum
        self.assertEqual(compute_momentum([]), 0.0)

    def test_momentum_single_window_empty(self):
        from engine.profile_metrics import compute_momentum
        # Seulement des données récentes, fenêtre précédente vide → 0.0
        rows = self._rows([1, 2], [0.8, 0.9])
        self.assertEqual(compute_momentum(rows), 0.0)

    def test_momentum_improvement(self):
        from engine.profile_metrics import compute_momentum
        recent = self._rows([1, 2, 3], [0.9, 0.85, 0.88])
        prev   = self._rows([8, 9, 10], [0.4, 0.35, 0.45])
        self.assertGreater(compute_momentum(recent + prev), 0)

    def test_momentum_degradation(self):
        from engine.profile_metrics import compute_momentum
        recent = self._rows([1, 2, 3], [0.3, 0.35, 0.4])
        prev   = self._rows([8, 9, 10], [0.85, 0.9, 0.88])
        self.assertLess(compute_momentum(recent + prev), 0)

    def test_momentum_bounded(self):
        from engine.profile_metrics import compute_momentum
        rows = self._rows([1, 8], [1.0, 0.0])
        r = compute_momentum(rows)
        self.assertLessEqual(r, 1.0)
        self.assertGreaterEqual(r, -1.0)

    # ── compute_learning_velocity ─────────────────────────────────────────────

    def test_velocity_empty(self):
        from engine.profile_metrics import compute_learning_velocity
        self.assertEqual(compute_learning_velocity([]), 0.0)

    def test_velocity_single_day(self):
        from engine.profile_metrics import compute_learning_velocity
        rows = self._rows([1, 1, 1], [0.5, 0.6, 0.7])
        self.assertEqual(compute_learning_velocity(rows), 0.0)

    def test_velocity_improving(self):
        from engine.profile_metrics import compute_learning_velocity
        rows = self._rows([3, 2, 1], [0.4, 0.6, 0.8])
        self.assertGreater(compute_learning_velocity(rows), 0)

    def test_velocity_degrading(self):
        from engine.profile_metrics import compute_learning_velocity
        rows = self._rows([3, 2, 1], [0.9, 0.6, 0.3])
        self.assertLess(compute_learning_velocity(rows), 0)

    # ── compute_consistency_score ─────────────────────────────────────────────

    def test_consistency_empty(self):
        from engine.profile_metrics import compute_consistency_score
        self.assertEqual(compute_consistency_score([]), 0.0)

    def test_consistency_zero_window(self):
        from engine.profile_metrics import compute_consistency_score
        rows = self._rows([1], [0.7])
        self.assertEqual(compute_consistency_score(rows, window_days=0), 0.0)

    def test_consistency_7_active_days_out_of_30(self):
        from engine.profile_metrics import compute_consistency_score
        rows = self._rows(list(range(1, 8)), [0.7] * 7)
        result = compute_consistency_score(rows, window_days=30)
        self.assertAlmostEqual(result, round(7 / 30, 3), places=2)

    def test_consistency_old_rows_ignored(self):
        from engine.profile_metrics import compute_consistency_score
        rows = self._rows([60, 90], [0.7, 0.8])
        self.assertEqual(compute_consistency_score(rows, window_days=30), 0.0)

    def test_consistency_bounded_to_1(self):
        from engine.profile_metrics import compute_consistency_score
        # 40 jours actifs dans une fenêtre de 30 → plafonné à ~1.0
        rows = self._rows(list(range(1, 31)), [0.7] * 30)
        result = compute_consistency_score(rows, window_days=30)
        self.assertLessEqual(result, 1.0)


# ─────────────────────────────────────────────────────────────────────────────
# engine/adaptive_difficulty.py
# ─────────────────────────────────────────────────────────────────────────────

class TestAdaptiveDifficulty(unittest.TestCase):

    def setUp(self):
        from engine.adaptive_difficulty import (
            get_difficulty_target,
            get_error_correction_type,
            filter_by_difficulty,
            choose_adaptive_question_type,
            DIFFICULTY_EASY,
            DIFFICULTY_HARD,
        )
        self.target    = get_difficulty_target
        self.error_cor = get_error_correction_type
        self.filter    = filter_by_difficulty
        self.choose    = choose_adaptive_question_type
        self.EASY      = DIFFICULTY_EASY
        self.HARD      = DIFFICULTY_HARD

    # ── get_difficulty_target ─────────────────────────────────────────────────

    def test_fragile_returns_easy(self):
        self.assertEqual(self.target("Fragile"), "easy")

    def test_consolidation_returns_medium(self):
        self.assertEqual(self.target("En consolidation"), "medium")

    def test_maitrise_returns_hard(self):
        self.assertEqual(self.target("Maîtrisé"), "hard")

    def test_recent_low_scores_force_easy_even_if_maitrise(self):
        self.assertEqual(self.target("Maîtrisé", recent_scores=[0.2, 0.3, 0.3]), "easy")

    def test_maitrise_mid_scores_returns_medium(self):
        # avg récent entre FORCE_EASY et ALLOW_HARD → medium
        self.assertEqual(self.target("Maîtrisé", recent_scores=[0.5, 0.55, 0.6]), "medium")

    def test_bloom_level_0_blocks_hard(self):
        result = self.target("Maîtrisé", recent_scores=[0.9, 0.9], graph_level=0)
        self.assertNotEqual(result, "hard")

    def test_bloom_level_1_blocks_hard(self):
        result = self.target("Maîtrisé", recent_scores=[0.9, 0.9], graph_level=1)
        self.assertNotEqual(result, "hard")

    def test_unknown_mastery_returns_medium(self):
        self.assertEqual(self.target(None), "medium")

    # ── get_error_correction_type ─────────────────────────────────────────────

    def test_error_correction_none_when_empty(self):
        self.assertIsNone(self.error_cor(None))
        self.assertIsNone(self.error_cor([]))

    def test_error_correction_needs_min_2_occurrences(self):
        self.assertIsNone(self.error_cor(["reponse_vague"]))

    def test_error_correction_dominant_reponse_vague(self):
        result = self.error_cor(["reponse_vague"] * 3)
        self.assertEqual(result, "reformulation")

    def test_error_correction_dominant_oubli_etape(self):
        result = self.error_cor(["oubli_etape"] * 3)
        self.assertEqual(result, "cas_pratique")

    def test_error_correction_fragile_uses_safe_types(self):
        # Fragile + oubli_etape → reformulation (pas cas_pratique trop complexe)
        result = self.error_cor(["oubli_etape"] * 3, mastery_class="Fragile")
        self.assertEqual(result, "reformulation")

    # ── filter_by_difficulty ──────────────────────────────────────────────────

    def test_filter_easy_keeps_only_easy(self):
        candidates = ["vrai_faux", "question_directe", "question_piege"]
        result = self.filter(candidates, "easy")
        self.assertTrue(all(t in self.EASY for t in result))

    def test_filter_hard_keeps_only_hard(self):
        candidates = ["question_piege", "consequence", "vrai_faux"]
        result = self.filter(candidates, "hard")
        self.assertTrue(all(t in self.HARD for t in result))

    def test_filter_fallback_when_no_match(self):
        # Aucun candidat dans hard → retourne la liste entière (fallback garanti)
        candidates = ["vrai_faux", "question_directe"]
        result = self.filter(candidates, "hard")
        self.assertEqual(result, candidates)

    # ── choose_adaptive_question_type ─────────────────────────────────────────

    def test_choose_returns_valid_type(self):
        from engine.question_type import QUESTION_TYPES
        t = self.choose([], "Fragile")
        self.assertIn(t, QUESTION_TYPES)

    def test_choose_error_correction_takes_priority(self):
        # 3× oubli_etape + mastery normale → cas_pratique (correction ciblée)
        result = self.choose(
            used_types=[],
            mastery_class="En consolidation",
            repeated_errors=["oubli_etape", "oubli_etape", "oubli_etape"],
        )
        self.assertEqual(result, "cas_pratique")

    def test_choose_fragile_never_returns_hard_type(self):
        for _ in range(30):
            t = self.choose([], "Fragile", recent_scores=[0.3, 0.2])
            self.assertNotIn(t, ["question_piege", "consequence"])


# ─────────────────────────────────────────────────────────────────────────────
# engine/retention.py
# ─────────────────────────────────────────────────────────────────────────────

class TestRetentionMetrics(unittest.TestCase):

    def setUp(self):
        from engine.retention import compute_retention_metrics
        self.compute = compute_retention_metrics

    def _row(self, chunk_id: int, days_ago: float, score: float):
        dt = (datetime.now() - timedelta(days=days_ago)).isoformat()
        return (chunk_id, dt, score)

    def test_empty_returns_all_none(self):
        r = self.compute([])
        self.assertIsNone(r["retention_j1"])
        self.assertIsNone(r["retention_j7"])
        self.assertIsNone(r["retention_j30"])

    def test_single_attempt_no_pairs(self):
        r = self.compute([self._row(1, 1, 0.8)])
        self.assertIsNone(r["retention_j1"])

    def test_j1_window_captured(self):
        # Deux tentatives même chunk, ~1 jour d'écart → tombe dans j1 (0.5–2.5j)
        rows = [self._row(1, 2.0, 0.5), self._row(1, 1.0, 0.9)]
        r = self.compute(rows)
        self.assertIsNotNone(r["retention_j1"])
        self.assertAlmostEqual(r["retention_j1"], 0.9, places=2)

    def test_j7_window_captured(self):
        # ~6j d'écart → j7 (4–10j)
        rows = [self._row(1, 9.0, 0.5), self._row(1, 3.0, 0.8)]
        r = self.compute(rows)
        self.assertIsNotNone(r["retention_j7"])

    def test_different_chunks_do_not_form_pairs(self):
        rows = [self._row(1, 2.0, 0.5), self._row(2, 1.0, 0.9)]
        r = self.compute(rows)
        self.assertIsNone(r["retention_j1"])

    def test_score_clamped_to_0_1(self):
        rows = [self._row(1, 2.0, 1.5), self._row(1, 1.0, 0.9)]
        r = self.compute(rows)
        if r["retention_j1"] is not None:
            self.assertLessEqual(r["retention_j1"], 1.0)
            self.assertGreaterEqual(r["retention_j1"], 0.0)

    def test_none_score_ignored(self):
        rows = [(1, datetime.now().isoformat(), None), self._row(1, 1.0, 0.8)]
        r = self.compute(rows)
        self.assertIsNone(r["retention_j1"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
