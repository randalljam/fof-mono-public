import os
import sys
from unittest.mock import MagicMock

os.environ.setdefault("ELEVENLABS_API_KEY", "unused")
sys.modules.setdefault("elevenlabs", MagicMock())
sys.modules.setdefault("elevenlabs.client", MagicMock())

import copy
import importlib.util
import json
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

FIXTURE_SCRIPT = os.path.join(REPO_ROOT, "apps", "transcription", "stellar-transcriber",
                              "scripts", "make_alignment_fixture.py")
spec = importlib.util.spec_from_file_location("make_alignment_fixture", FIXTURE_SCRIPT)
fixture_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture_mod)

from core.transcript_eval import extract_transcript_data
from core.transcript_misalign import (
    extract_misalignment_windows,
    misalignment_windows_from_paths,
    write_misalignment_windows_json,
)

### Helpers
def _anchor_ref(anchor):
    if anchor is None:
        return None
    return anchor[0]["aligned_ref_index"]
def _last_anchor_ref(anchor):
    if anchor is None:
        return None
    return anchor[-1]["aligned_ref_index"]

### Tests
class TestTranscriptMisalign(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.TemporaryDirectory()
        cls.result = fixture_mod.build_fixture_set(cls.tmpdir.name, max_segments=30)
    @classmethod
    def tearDownClass(cls):
        cls.tmpdir.cleanup()
    def test_ref_vs_itself_has_zero_windows(self):
        result = misalignment_windows_from_paths(self.result["ref"], self.result["ref"])
        self.assertEqual(result["windows"], [])
        self.assertEqual(result["metrics"]["seg_error_count_strict"], 0)
    def test_raw_a_has_valid_nonempty_windows(self):
        result = misalignment_windows_from_paths(self.result["raw_a"], self.result["ref"])
        self.assertGreaterEqual(len(result["windows"]), 1)
        self.assertEqual([w["window_id"] for w in result["windows"]], list(range(len(result["windows"]))))
        for window in result["windows"]:
            missing_refs = [seg for seg in window["reference_segments"] if seg["is_missing"]]
            self.assertTrue(window["candidate_segments"] or missing_refs)
    def test_raw_a_windows_partition_strict_errors(self):
        result = misalignment_windows_from_paths(self.result["raw_a"], self.result["ref"])
        windows = result["windows"]
        metrics = result["metrics"]
        self.assertEqual(sum(w["error_signature"]["spurious"] for w in windows), metrics["seg_spurious_count"])
        self.assertEqual(sum(w["error_signature"]["boundary_misplaced"] for w in windows), metrics["seg_boundary_misplaced_count"])
        missing_count = sum(1 for w in windows for seg in w["reference_segments"] if seg["is_missing"])
        self.assertEqual(missing_count, metrics["seg_missing_count"])
    def test_reference_indices_are_contiguous_between_flanking_anchors(self):
        result = misalignment_windows_from_paths(self.result["raw_a"], self.result["ref"])
        total_ref = result["total_ref_segments"]
        for window in result["windows"]:
            ref_indices = [seg["ref_index"] for seg in window["reference_segments"]]
            if ref_indices:
                self.assertEqual(ref_indices, list(range(ref_indices[0], ref_indices[-1] + 1)))
            before_ref = _last_anchor_ref(window["anchor_before"])
            after_ref = _anchor_ref(window["anchor_after"])
            lower = -1 if before_ref is None else before_ref
            upper = total_ref if after_ref is None else after_ref
            for ref_index in ref_indices:
                self.assertGreater(ref_index, lower)
                self.assertLess(ref_index, upper)
    def test_ref_indices_are_globally_disjoint_across_windows(self):
        # No reference index may appear in two windows: the anchor-bounded spans must
        # partition the reference, never overlap (guards candidate-vs-candidate double-count).
        for arm in ("raw_a", "raw_b"):
            result = misalignment_windows_from_paths(self.result[arm], self.result["ref"])
            seen = set()
            for window in result["windows"]:
                for seg in window["reference_segments"]:
                    self.assertNotIn(seg["ref_index"], seen)
                    seen.add(seg["ref_index"])
    def test_trailing_missing_refs_are_captured(self):
        # A reference tail with no candidate counterpart (dropped after the last aligned
        # segment) must still surface as missing in a window — the head/tail coverage the
        # region walk adds. Pre-fix these trailing segments were silently lost.
        ref_data = extract_transcript_data(self.result["ref"])
        eval_data = copy.deepcopy(ref_data[:-2])
        result = extract_misalignment_windows(eval_data, copy.deepcopy(ref_data))
        missing = {seg["ref_index"] for w in result["windows"] for seg in w["reference_segments"] if seg["is_missing"]}
        self.assertIn(len(ref_data) - 1, missing)
        self.assertIn(len(ref_data) - 2, missing)
        self.assertEqual(len(missing), result["metrics"]["seg_missing_count"])
    def test_leading_missing_refs_are_captured(self):
        # Symmetric guard for the head region: reference turns before the first aligned
        # segment must surface as missing.
        ref_data = extract_transcript_data(self.result["ref"])
        eval_data = copy.deepcopy(ref_data[2:])
        result = extract_misalignment_windows(eval_data, copy.deepcopy(ref_data))
        missing = {seg["ref_index"] for w in result["windows"] for seg in w["reference_segments"] if seg["is_missing"]}
        self.assertIn(0, missing)
        self.assertIn(1, missing)
        self.assertEqual(len(missing), result["metrics"]["seg_missing_count"])
    def test_write_misalignment_windows_json_round_trips(self):
        result = misalignment_windows_from_paths(self.result["raw_a"], self.result["ref"])
        out_path = os.path.join(self.tmpdir.name, "nested", "windows.json")
        write_misalignment_windows_json(result, out_path)
        with open(out_path, encoding="utf-8") as f:
            loaded = json.load(f)
        self.assertEqual(loaded, result)

if __name__ == "__main__":
    unittest.main()
