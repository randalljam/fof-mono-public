import os
import sys
import unittest
from unittest.mock import MagicMock

os.environ.setdefault("ELEVENLABS_API_KEY", "unused")
sys.modules.setdefault("elevenlabs", MagicMock())
sys.modules.setdefault("elevenlabs.client", MagicMock())

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.dual_missing_recovery import analyze_missing_recovery, locate_turn_in_transcript

def _seg(timestamp, speaker, dialogue):
    return {
        "timestamp": timestamp,
        "speaker_name": speaker,
        "dialogue": dialogue,
    }

class TestDualMissingRecovery(unittest.TestCase):
    def test_locate_turn_in_transcript_exact_near_match(self):
        sibling = [
            _seg("0:09", "Alice", "We found the missing turn exactly."),
        ]
        result = locate_turn_in_transcript("We found the missing turn exactly.", 10, sibling)
        self.assertTrue(result["found"])
        self.assertGreaterEqual(result["sim"], 0.99)
        self.assertEqual(result["matched_index"], 0)
        self.assertEqual(result["matched_timestamp"], "0:09")
    def test_locate_turn_in_transcript_contained_run(self):
        sibling = [
            _seg("0:20", "Bob", "Before that, we found the missing turn exactly, and then moved on."),
        ]
        result = locate_turn_in_transcript(
            "we found the missing turn exactly",
            20,
            sibling,
            sim_threshold=0.95,
        )
        self.assertTrue(result["found"])
        self.assertTrue(result["contained"])
        self.assertEqual(result["matched_index"], 0)
    def test_locate_turn_in_transcript_unrelated_near_text(self):
        sibling = [
            _seg("0:21", "Bob", "This is a completely unrelated sibling segment."),
        ]
        result = locate_turn_in_transcript("we found the missing turn exactly", 20, sibling)
        self.assertFalse(result["found"])
        self.assertFalse(result["contained"])
        self.assertIsNone(result["matched_index"])
    def test_locate_turn_in_transcript_match_outside_time_window(self):
        sibling = [
            _seg("1:20", "Bob", "we found the missing turn exactly"),
        ]
        result = locate_turn_in_transcript(
            "we found the missing turn exactly",
            20,
            sibling,
            window_secs=10,
        )
        self.assertFalse(result["found"])
        self.assertEqual(result["sim"], 0.0)
        self.assertIsNone(result["matched_index"])
    def test_analyze_missing_recovery_counts_sibling_opportunity(self):
        ref = [
            _seg("0:10", "Alice", "Opening anchor words."),
            _seg("0:20", "Bob", "Recover this dropped reference turn."),
            _seg("0:30", "Alice", "This dropped turn is absent from the sibling."),
        ]
        arm = [
            _seg("0:10", "Alice", "Opening anchor words."),
        ]
        sibling = [
            _seg("0:20", "Bob", "Recover this dropped reference turn."),
        ]
        result = analyze_missing_recovery(ref, arm, sibling, window_secs=5)
        self.assertEqual(result["arm_missing_count"], 2)
        self.assertEqual(result["recoverable_from_sibling"], 1)
        self.assertEqual(result["not_in_sibling"], 1)
        self.assertEqual(result["recovery_rate"], 0.5)
        self.assertEqual([item["ref_index"] for item in result["missing_details"]], [1, 2])
        self.assertTrue(result["missing_details"][0]["recovered"])
        self.assertEqual(result["missing_details"][0]["sibling_timestamp"], "0:20")
        self.assertFalse(result["missing_details"][1]["recovered"])
        self.assertIsNone(result["missing_details"][1]["sibling_timestamp"])

if __name__ == "__main__":
    unittest.main()
