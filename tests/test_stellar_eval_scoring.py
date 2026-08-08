"""
Tests for Stellar Transcriber eval scoring: normalization policies, subscores,
composite score, config loader, and rescore helper.

Run from the repo root:
    .venv/bin/python3 -m pytest tests/test_stellar_eval_scoring.py tests/test_stellar_corpus_inventory.py
"""
import csv
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
os.environ.setdefault("ELEVENLABS_API_KEY", "test-key-for-unit-tests")
sys.modules.setdefault("elevenlabs", MagicMock())
sys.modules.setdefault("elevenlabs.client", MagicMock())

from core.conversion import normalize_text
from core.transcript_eval import (
    EVAL_CODE_VERSION,
    compute_composite_scores,
    compute_subscore_alignment,
    compute_subscore_alignment_loose,
    compute_subscore_alignment_strict,
    compute_subscore_proper_names,
    compute_subscore_quotations,
    compute_subscore_speaker,
    compute_subscore_word_accuracy,
    get_normalization_policy,
    load_eval_corpus_config,
    normalize_dialogue,
    rescore_metrics_csv,
    resolve_proper_names_method,
)

class TestNormalizationPolicy(unittest.TestCase):
    def test_keep_all_matches_normalize_text(self):
        policy = get_normalization_policy("keep-all")
        samples = [
            "Hello, World!",
            "Speaker said: **bold** and __underline__",
            "Um, I think that's right.",
            "We were- we went home.",
        ]
        for sample in samples:
            self.assertEqual(normalize_dialogue(sample, policy), normalize_text(sample))
    def test_strip_fillers(self):
        policy = get_normalization_policy("deutsch-v1")
        result = normalize_dialogue("Um, I think, you know, that's fine.", policy)
        self.assertNotIn("um", result.split())
        self.assertNotIn("you", result.split())  # 'you know' stripped
    def test_collapse_repeats(self):
        policy = get_normalization_policy("deutsch-v1")
        result = normalize_dialogue("I I I went there", policy)
        self.assertEqual(result.count("i"), 1)
    def test_strip_partial_words(self):
        policy = get_normalization_policy("deutsch-v1")
        result = normalize_dialogue("We were- we went", policy)
        self.assertNotIn("were-", result)

class TestConfigLoader(unittest.TestCase):
    def test_load_eval_corpus_config(self):
        config = load_eval_corpus_config(repo_root=REPO_ROOT)
        self.assertIn("deutsch", config)
        self.assertIn("policies", config)
        self.assertEqual(config["deutsch"]["policy_id"], "deutsch-v1")
    def test_resolve_proper_names_method_caprules(self):
        self.assertEqual(resolve_proper_names_method("caprules"), "caprules")

class TestSubscores(unittest.TestCase):
    def test_word_accuracy_subscore_scales_fraction(self):
        # word_accuracy is stored as a 0-1 fraction by evaluate_step_word_error_rate
        self.assertEqual(compute_subscore_word_accuracy({"word_accuracy": 0.875}), 87.5)
    def test_word_accuracy_subscore_accepts_percentage(self):
        self.assertEqual(compute_subscore_word_accuracy({"word_accuracy": 87.5}), 87.5)
    def test_alignment_subscore_loose_from_error_counts(self):
        # 100 ref segments, 10 loose segment errors -> 90.0
        metrics = {"total_ref_segments": 100, "seg_error_count": 10}
        self.assertEqual(compute_subscore_alignment_loose(metrics), 90.0)
    def test_alignment_subscore_strict_from_error_counts(self):
        # 100 ref segments, 10 strict segment errors -> 90.0
        metrics = {"total_ref_segments": 100, "seg_error_count_strict": 10}
        self.assertEqual(compute_subscore_alignment_strict(metrics), 90.0)
    def test_alignment_subscore_active_is_strict(self):
        # Active compute_subscore_alignment uses strict counts, not loose
        metrics = {
            "total_ref_segments": 100,
            "seg_error_count": 40,
            "seg_error_count_strict": 10,
        }
        self.assertEqual(compute_subscore_alignment(metrics), 90.0)
        self.assertEqual(compute_subscore_alignment_strict(metrics), 90.0)
        self.assertEqual(compute_subscore_alignment_loose(metrics), 60.0)
    def test_alignment_subscore_zero_errors_is_100(self):
        metrics = {"total_ref_segments": 50, "seg_error_count_strict": 0}
        self.assertEqual(compute_subscore_alignment(metrics), 100.0)
    def test_alignment_subscore_error_count_exceeding_ref_clamps_to_0(self):
        metrics = {"total_ref_segments": 10, "seg_error_count_strict": 25}
        self.assertEqual(compute_subscore_alignment(metrics), 0.0)
    def test_alignment_subscore_legacy_fraction_fallback(self):
        # Legacy rows store 'is_aligned == True' etc. as 0-1 fractions of eval segments
        metrics = {
            "total_eval_segments": 100,
            "is_aligned == True": 0.90,
            "is_delete == True": 0.05,
            "ref_indices_to_add": 0.02,
            "total_ref_segments": 100,
        }
        score = compute_subscore_alignment(metrics)
        self.assertAlmostEqual(score, 90.0 - 1.0 - 0.4, places=6)
        self.assertEqual(compute_subscore_alignment_loose(metrics), score)
        self.assertEqual(compute_subscore_alignment_strict(metrics), score)
    def test_alignment_subscore_independent_of_segment_count(self):
        # Same aligned fraction must give the same score for a short and a long episode
        short = {"total_eval_segments": 25, "is_aligned == True": 0.8,
                 "is_delete == True": 0, "ref_indices_to_add": 0, "total_ref_segments": 25}
        long = {"total_eval_segments": 250, "is_aligned == True": 0.8,
                "is_delete == True": 0, "ref_indices_to_add": 0, "total_ref_segments": 250}
        self.assertEqual(compute_subscore_alignment(short), compute_subscore_alignment(long))
    def test_quotations_no_ref_quotes(self):
        self.assertEqual(compute_subscore_quotations({"quotes_ref": 0}), 100.0)
    def test_proper_names_f1(self):
        metrics = {"pn_total_ref_names": 10, "pn_exact_matches": 8, "pn_extra_names": 2}
        score = compute_subscore_proper_names(metrics)
        self.assertGreater(score, 0)
        self.assertLessEqual(score, 100)
    def test_speaker_subscore(self):
        metrics = {"sc_aligned": 0.8}
        self.assertEqual(compute_subscore_speaker(metrics), 80.0)

class TestCompositeScore(unittest.TestCase):
    def test_composite_weighted_sum(self):
        metrics = {
            "total_eval_segments": 10, "seg_error_count": 0, "seg_error_count_strict": 0,
            "total_ref_segments": 10,
            "word_accuracy": 0.80,
            "quotes_ref": 0,
            "pn_total_ref_names": 0,
            "sc_aligned": 0.8, "sc_consistent": 0.7,
        }
        weights = {"word_accuracy": 0.35, "speaker": 0.25, "alignment": 0.20, "proper_names": 0.12, "quotations": 0.08}
        result = compute_composite_scores(metrics, weights)
        self.assertIn("overall_score", result)
        self.assertEqual(result["subscore_word_accuracy"], 80.0)
        self.assertEqual(result["subscore_alignment"], 100.0)
        self.assertEqual(result["subscore_alignment_strict"], 100.0)
        self.assertEqual(result["subscore_alignment_loose"], 100.0)
        # 0.35*80 + 0.25*80 + 0.20*100 + 0.12*100 + 0.08*100 = 88.0
        self.assertEqual(result["overall_score"], 88.0)
    def test_composite_uses_strict_alignment_not_loose(self):
        metrics = {
            "total_ref_segments": 100,
            "seg_error_count": 50,
            "seg_error_count_strict": 10,
            "word_accuracy": 1.0,
            "quotes_ref": 0,
            "pn_total_ref_names": 0,
            "sc_aligned": 1.0,
        }
        result = compute_composite_scores(metrics)
        self.assertEqual(result["subscore_alignment_loose"], 50.0)
        self.assertEqual(result["subscore_alignment_strict"], 90.0)
        self.assertEqual(result["subscore_alignment"], 90.0)

class TestRescoreMetricsCsv(unittest.TestCase):
    def test_rescore_adds_columns(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="") as f:
            path = f.name
            writer = csv.DictWriter(f, fieldnames=["word_accuracy", "quotes_ref", "policy_id",
                "total_eval_segments", "is_aligned == True", "is_delete == True", "ref_indices_to_add",
                "total_ref_segments", "pn_total_ref_names", "pn_exact_matches", "pn_extra_names",
                "sc_aligned", "sc_consistent"])
            writer.writeheader()
            writer.writerow({
                "word_accuracy": 90, "quotes_ref": 0, "policy_id": "deutsch-v1",
                "total_eval_segments": 10, "is_aligned == True": 9, "is_delete == True": 0,
                "ref_indices_to_add": 0, "total_ref_segments": 10,
                "pn_total_ref_names": 5, "pn_exact_matches": 4, "pn_extra_names": 1,
                "sc_aligned": 0.9, "sc_consistent": 0.8,
            })
        try:
            rows = rescore_metrics_csv(path, load_eval_corpus_config(repo_root=REPO_ROOT))
            self.assertEqual(len(rows), 1)
            self.assertIn("overall_score", rows[0])
            self.assertIsNotNone(rows[0]["overall_score"])
        finally:
            os.unlink(path)

class TestRunnerHelpers(unittest.TestCase):
    def test_suffix_from_filename(self):
        import importlib.util
        runner_path = os.path.join(REPO_ROOT, "apps", "transcription", "stellar-transcriber",
                                   "scripts", "run_baseline_eval.py")
        spec = importlib.util.spec_from_file_location("run_baseline_eval", runner_path)
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        self.assertEqual(runner.suffix_from_filename("2024-03-06_PB_nova2gen.md"), "_nova2gen.md")
        keys = ["data/x/2024-03-06_PB_nova2gen.md", "data/x/2024-03-06_PB_vrb.md"]
        # pick_ref_path needs files on disk; test suffix logic via keys_by_suffix pattern
        suffixes = {}
        for key in keys:
            s = runner.suffix_from_filename(os.path.basename(key))
            suffixes[s] = key
        self.assertEqual(suffixes["_vrb.md"], "data/x/2024-03-06_PB_vrb.md")
        eval_map = runner.pick_eval_keys(keys, ["_nova2gen.md", "_dgwhspm.md"])
        self.assertIn("_nova2gen.md", eval_map)
    def test_version_is_set(self):
        self.assertTrue(EVAL_CODE_VERSION.startswith("0."))

if __name__ == "__main__":
    unittest.main()
