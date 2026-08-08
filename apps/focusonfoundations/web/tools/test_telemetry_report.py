#!/usr/bin/env python3
import tempfile
import unittest

import telemetry_report
import telemetry_server

def sample_payload(stamp, events=None):
    return {
        "applet": "logic-gates",
        "user": "Dev",
        "session_id": "logic-gates_Dev_" + stamp,
        "start_stamp": stamp,
        "start_wall_time": stamp[:10] + " " + stamp[11:13] + ":" + stamp[13:15] + ":" + stamp[15:17],
        "user_agent": "test-agent",
        "events": events or [],
    }
def save_fixture(tmpdir, stamp, events):
    return telemetry_server.save_payload(sample_payload(stamp, events), data_dir=tmpdir)["path"]
class TelemetryReportTest(unittest.TestCase):
    def test_title_resolution_uses_enter_then_start_steps_then_fallback(self):
        events = [
            {"t_ms": 0, "kind": "applet-start", "detail": {"steps": ["Start title", {"title": "Array title"}]}},
            {"t_ms": 1000, "kind": "step-enter", "step": 0, "detail": {"title": "Enter title"}},
            {"t_ms": 2000, "kind": "step-leave", "step": 0},
            {"t_ms": 3000, "kind": "step-enter", "step": 1},
            {"t_ms": 4000, "kind": "step-leave", "step": 1},
            {"t_ms": 5000, "kind": "step-enter", "step": 2},
            {"t_ms": 6000, "kind": "step-leave", "step": 2},
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            report = telemetry_report.load_report(save_fixture(tmpdir, "2026-07-11_103814", events))
        self.assertEqual(telemetry_report.resolve_step_title(report["step_titles"], 0), "Enter title")
        self.assertEqual(telemetry_report.resolve_step_title(report["step_titles"], 1), "Array title")
        self.assertEqual(telemetry_report.resolve_step_title(report["step_titles"], 2), "step 2")
        output = telemetry_report.format_report(report)
        self.assertIn("Enter title", output)
        self.assertIn("Array title", output)
        self.assertIn("step 2", output)
    def test_quiz_aggregation_counts_rounds_tries_outcomes_and_response_times(self):
        events = [
            {"t_ms": 0, "kind": "applet-start"},
            {"t_ms": 100, "kind": "quiz-round", "step": 4, "detail": {"quiz": "AND", "round": 0, "prompt": "1 & 1"}},
            {"t_ms": 150, "kind": "quiz-attempt", "step": 4, "detail": {"quiz": "AND", "round": 0, "prompt": "1 & 1", "given": "0", "isCorrect": False}},
            {"t_ms": 180, "kind": "quiz-attempt", "step": 4, "detail": {"quiz": "AND", "round": 0, "prompt": "1 & 1", "given": "0", "isCorrect": False}},
            {"t_ms": 220, "kind": "quiz-attempt", "step": 4, "detail": {"quiz": "AND", "round": 0, "prompt": "1 & 1", "given": "1", "isCorrect": True}},
            {"t_ms": 300, "kind": "quiz-round", "step": 4, "detail": {"quiz": "AND", "round": 1, "prompt": "1 & 0"}},
            {"t_ms": 340, "kind": "quiz-attempt", "step": 4, "detail": {"quiz": "AND", "round": 1, "prompt": "1 & 0", "given": "0", "isCorrect": True}},
            {"t_ms": 500, "kind": "quiz-attempt", "step": 4, "detail": {"quiz": "AND", "round": 2, "prompt": "0 & 0", "given": "1", "isCorrect": False}},
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            report = telemetry_report.load_report(save_fixture(tmpdir, "2026-07-11_103814", events))
        quizzes = telemetry_report.aggregate_quizzes(report["quiz_attempts"])
        self.assertEqual(len(quizzes), 1)
        quiz = quizzes[0]
        self.assertEqual(quiz["round_count"], 3)
        self.assertEqual(quiz["total_attempts"], 5)
        self.assertEqual(quiz["correct"], 2)
        self.assertEqual(quiz["wrong"], 3)
        self.assertEqual(quiz["avg_response_time_ms"], 72.5)
        self.assertEqual(quiz["max_response_time_ms"], 120)
        self.assertEqual(quiz["rounds"][0]["tries"], 3)
        self.assertEqual(quiz["rounds"][0]["outcome_sequence"], "x x ok")
        self.assertEqual(quiz["rounds"][0]["response_time_sequence"], "50 80 120")
        self.assertEqual(quiz["rounds"][2]["response_time_sequence"], "-")
    def test_directory_input_picks_newest_sqlite_by_filename_sort(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            save_fixture(tmpdir, "2026-07-11_103814", [])
            newest = save_fixture(tmpdir, "2026-07-12_103814", [])
            self.assertEqual(telemetry_report.select_session_path(tmpdir), newest)
    def test_events_timeline_includes_formatted_row(self):
        events = [
            {"t_ms": 0, "kind": "applet-start"},
            {"t_ms": 1234, "kind": "click", "step": 0, "target": "next", "detail": {"foo": "bar", "empty": None}},
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            report = telemetry_report.load_report(save_fixture(tmpdir, "2026-07-11_103814", events))
        output = telemetry_report.format_report(report, include_events=True)
        self.assertIn("0:01.234", output)
        self.assertIn("click", output)
        self.assertIn("next", output)
        self.assertIn('{"foo":"bar"}', output)
    def test_zero_duration_does_not_crash_duration_or_percent_formatting(self):
        events = [
            {"t_ms": 0, "kind": "step-enter", "step": 0, "detail": {"title": "Zero"}},
            {"t_ms": 0, "kind": "step-leave", "step": 0},
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            report = telemetry_report.load_report(save_fixture(tmpdir, "2026-07-11_103814", events))
        output = telemetry_report.format_report(report)
        self.assertIn("duration", output)
        self.assertIn("0:00", output)
        self.assertIn("0.0%", output)
if __name__ == "__main__":
    unittest.main()
