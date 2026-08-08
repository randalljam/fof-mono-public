"""Tests for the Stellar Transcriber diarization benchmark runner."""
import importlib.util
import os
import sys
import unittest

### Module loading
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_DIR = os.path.join(REPO_ROOT, "apps", "transcription", "stellar-transcriber", "scripts")
SCRIPT_PATH = os.path.join(SCRIPT_DIR, "run_diar_bench.py")
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
spec = importlib.util.spec_from_file_location("run_diar_bench", SCRIPT_PATH)
bench = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench)

class TestFilterSessions(unittest.TestCase):
    def setUp(self):
        self.sessions = [
            {"session_id": "deutsch-alpha", "stem": "2024-01-01_First"},
            {"session_id": "deutsch-beta", "stem": "2024-02-02_Second"},
            {"session_id": "pv-gamma", "stem": "2025-03-03_PV-EPC"},
        ]
    def test_matches_session_ids_and_stems(self):
        filtered = bench.filter_sessions(
            self.sessions,
            "deutsch-alpha,PV-EPC",
            include_stem=True,
        )
        self.assertEqual(
            [session["session_id"] for session in filtered],
            ["deutsch-alpha", "pv-gamma"],
        )
    def test_ignores_empty_comma_separated_values(self):
        filtered = bench.filter_sessions(self.sessions, "deutsch-beta,")
        self.assertEqual(
            [session["session_id"] for session in filtered],
            ["deutsch-beta"],
        )
    def test_rejects_empty_filter(self):
        with self.assertRaisesRegex(SystemExit, "no non-empty session filters"):
            bench.filter_sessions(self.sessions, " , ")
    def test_reports_no_matches(self):
        with self.assertRaisesRegex(SystemExit, "no sessions matched"):
            bench.filter_sessions(self.sessions, "missing")

if __name__ == "__main__":
    unittest.main()
