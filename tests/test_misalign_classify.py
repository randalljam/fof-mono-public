import os
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.misalign_classify import classify_misalignment_windows, render_window_prompt_content

### Fixtures
def _window():
    return {
        "window_id": 7,
        "anchor_before": [
            {"role": "anchor", "eval_index": 0, "timestamp": "00:00", "speaker": "A", "dialogue": "Intro.", "aligned_ref_index": 0}
        ],
        "anchor_after": [
            {"role": "anchor", "eval_index": 4, "timestamp": "00:20", "speaker": "B", "dialogue": "Next.", "aligned_ref_index": 4}
        ],
        "candidate_segments": [
            {
                "eval_index": 1,
                "timestamp": "00:05",
                "speaker": "A",
                "dialogue": "This belongs before.",
                "aligned_ref_index": 1,
                "is_delete": False,
                "is_boundary_error": True,
                "is_boundary_misplaced": True,
            },
            {
                "eval_index": 2,
                "timestamp": "00:09",
                "speaker": "B",
                "dialogue": "Extra turn.",
                "aligned_ref_index": None,
                "is_delete": True,
                "is_boundary_error": False,
                "is_boundary_misplaced": False,
            },
        ],
        "reference_segments": [
            {"ref_index": 1, "timestamp": "00:05", "speaker": "A", "dialogue": "This belongs before.", "is_missing": False},
            {"ref_index": 2, "timestamp": "00:11", "speaker": "B", "dialogue": "Missing turn.", "is_missing": True},
        ],
        "error_signature": {"missing": 1, "spurious": 1, "boundary_misplaced": 1, "boundary_error": 1},
        "window_kind_hint": "mixed_structural",
        "classification": None,
    }
def _classification(label="missing_turn", repairable=True, repair_family="insert_missing"):
    return {
        "label": label,
        "repairable": repairable,
        "repair_family": repair_family,
        "confidence": "high",
        "rationale": "The reference contains a dropped turn.",
        "suggested_fix": "Insert the missing turn boundary.",
    }

### Tests
class TestMisalignClassify(unittest.TestCase):
    def test_render_window_prompt_content_contains_markers(self):
        content = render_window_prompt_content(_window())
        self.assertIn("window_kind_hint: mixed_structural", content)
        self.assertIn("error_signature:", content)
        self.assertIn("## anchor before", content)
        self.assertIn("[00:00] A: Intro.", content)
        self.assertIn("## candidate", content)
        self.assertIn("<<spurious>>", content)
        self.assertIn("<<misplaced>>", content)
        self.assertIn("<<boundary_error>>", content)
        self.assertIn("## reference", content)
        self.assertIn("<<missing>>", content)
        self.assertIn("## anchor after", content)
    def test_classify_misalignment_windows_with_injected_mock(self):
        result = {"windows": [_window(), _window()]}
        summary = classify_misalignment_windows(result, classify_fn=lambda window: _classification())
        self.assertEqual(summary["classified"], 2)
        self.assertEqual(summary["unclassified"], 0)
        self.assertEqual(summary["label_counts"], {"missing_turn": 2})
        self.assertEqual(summary["repairable_count"], 2)
        self.assertEqual(summary["repair_family_counts"], {"insert_missing": 2})
        self.assertTrue(all(window["classification"] is not None for window in result["windows"]))
    def test_injected_out_of_taxonomy_label_counts_as_other(self):
        result = {"windows": [_window()]}
        summary = classify_misalignment_windows(
            result,
            classify_fn=lambda window: _classification(label="not_a_label", repairable=False, repair_family="none_artifact"),
        )
        self.assertEqual(result["windows"][0]["classification"]["label"], "not_a_label")
        self.assertEqual(summary["classified"], 1)
        self.assertEqual(summary["label_counts"], {"other": 1})
        self.assertEqual(sum(summary["label_counts"].values()), summary["classified"])
        self.assertEqual(summary["not_repairable_count"], 1)

if __name__ == "__main__":
    unittest.main()
