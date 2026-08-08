"""
Tests for the alignment defect-injection fixture and the segment-error metric.

Validates that evaluate_step_segments_align counts injected defects exactly:
the fixture generator injects a known defect set into a clean reference, and the
eval must report precisely the expected missing/spurious/boundary error counts.

Run from the repo root:
    .venv/bin/python3 -m pytest tests/test_stellar_alignment_fixture.py
"""
import importlib.util
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

FIXTURE_SCRIPT = os.path.join(REPO_ROOT, "apps", "transcription", "stellar-transcriber",
                              "scripts", "make_alignment_fixture.py")
spec = importlib.util.spec_from_file_location("make_alignment_fixture", FIXTURE_SCRIPT)
fixture_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture_mod)

from core.transcript_eval import evaluate_step_segments_align, extract_transcript_data

def _score_pair(eval_path, ref_path):
    eval_data = extract_transcript_data(eval_path)
    ref_data = extract_transcript_data(ref_path)
    _, metrics, _ = evaluate_step_segments_align(eval_data, ref_data, verbose=False)
    return metrics

class TestAlignmentFixtureMetric(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.TemporaryDirectory()
        cls.result = fixture_mod.build_fixture_set(cls.tmpdir.name, max_segments=30)
    @classmethod
    def tearDownClass(cls):
        cls.tmpdir.cleanup()
    def test_ref_vs_itself_has_zero_errors(self):
        metrics = _score_pair(self.result["ref"], self.result["ref"])
        self.assertEqual(metrics["seg_error_count"], 0)
        self.assertEqual(metrics["seg_missing_count"], 0)
        self.assertEqual(metrics["seg_spurious_count"], 0)
        self.assertEqual(metrics["seg_boundary_error_count"], 0)
    def test_raw_a_matches_expected_counts(self):
        metrics = _score_pair(self.result["raw_a"], self.result["ref"])
        expected = self.result["expected_a"]
        self.assertEqual(metrics["seg_missing_count"], expected["seg_missing_count"])
        self.assertEqual(metrics["seg_spurious_count"], expected["seg_spurious_count"])
        self.assertEqual(metrics["seg_boundary_error_count"], expected["seg_boundary_error_count"])
        self.assertEqual(metrics["seg_error_count"], expected["seg_error_count"])
    def test_raw_b_matches_expected_counts(self):
        metrics = _score_pair(self.result["raw_b"], self.result["ref"])
        expected = self.result["expected_b"]
        self.assertEqual(metrics["seg_missing_count"], expected["seg_missing_count"])
        self.assertEqual(metrics["seg_spurious_count"], expected["seg_spurious_count"])
        self.assertEqual(metrics["seg_boundary_error_count"], expected["seg_boundary_error_count"])
        self.assertEqual(metrics["seg_error_count"], expected["seg_error_count"])
    def test_injection_log_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp2:
            result2 = fixture_mod.build_fixture_set(tmp2, max_segments=30)
            self.assertEqual(result2["log_a"], self.result["log_a"])
            self.assertEqual(result2["log_b"], self.result["log_b"])

if __name__ == "__main__":
    unittest.main()
