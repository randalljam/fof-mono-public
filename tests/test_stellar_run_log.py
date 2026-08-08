import os
import sys
from unittest.mock import MagicMock

os.environ.setdefault("ELEVENLABS_API_KEY", "unused")
sys.modules.setdefault("elevenlabs", MagicMock())
sys.modules.setdefault("elevenlabs.client", MagicMock())

import json
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.stellar_run_log import append_run_record, build_episode_record, build_run_record, load_run_log, render_run_log_md

### Fixtures
def _windows_result(total_ref, strict_errors, loose_errors, missing, spurious, boundary_error, misplaced, n_windows):
    return {
        "total_ref_segments": total_ref,
        "total_eval_segments": total_ref,
        "metrics": {
            "seg_error_count": loose_errors,
            "seg_error_count_strict": strict_errors,
            "seg_missing_count": missing,
            "seg_spurious_count": spurious,
            "seg_boundary_error_count": boundary_error,
            "seg_boundary_misplaced_count": misplaced,
        },
        "windows": [{"window_id": idx} for idx in range(n_windows)],
    }
def _summary(label, count, repairable):
    return {
        "classified": count,
        "unclassified": 0,
        "label_counts": {label: count},
        "repairable_count": repairable,
        "not_repairable_count": count - repairable,
        "repair_family_counts": {"insert_missing": repairable},
        "usage": None,
    }

### Tests
class TestStellarRunLog(unittest.TestCase):
    def test_run_log_jsonl_and_markdown_round_trip(self):
        episode_a = build_episode_record(
            "episode-a", "nova2gen", "strict",
            _windows_result(13, 2, 3, 1, 1, 1, 0, 2),
            classify_summary=_summary("missing_turn", 2, 1),
        )
        episode_b = build_episode_record(
            "episode-b", "dgwhspm", "strict",
            _windows_result(10, 1, 2, 0, 1, 1, 1, 1),
            classify_summary=_summary("spurious_turn", 1, 1),
        )
        self.assertEqual(episode_a["strict"], 84.6)
        self.assertEqual(episode_a["loose"], 76.9)
        self.assertEqual(episode_a["strict"], round(episode_a["strict"], 1))
        record = build_run_record(
            "run-test", "2026-07-21_120000", "strict", "deutsch", "deutsch",
            "gpt-5-mini", "deutsch-v1", [episode_a, episode_b], "/tmp/out", notes="unit test",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            jsonl_path = os.path.join(tmpdir, "stellar-run-log.jsonl")
            md_path = os.path.join(tmpdir, "stellar-run-log.md")
            append_run_record(record, jsonl_path)
            append_run_record(record, jsonl_path)
            records = load_run_log(jsonl_path)
            self.assertEqual(len(records), 2)
            self.assertEqual(records[0]["run_id"], "run-test")
            render_run_log_md(jsonl_path, md_path)
            with open(md_path, encoding="utf-8") as f:
                md = f.read()
            self.assertIn("run-test", md)
            self.assertIn("episode-a", md)
            self.assertIn("episode-b", md)
            self.assertIn("| Episode | ASR | strict | loose |", md)
            with open(jsonl_path, encoding="utf-8") as f:
                self.assertEqual(len([json.loads(line) for line in f if line.strip()]), 2)

if __name__ == "__main__":
    unittest.main()
