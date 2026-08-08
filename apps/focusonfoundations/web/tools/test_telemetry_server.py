#!/usr/bin/env python3
import json
import os
import sqlite3
import tempfile
import unittest

import telemetry_server

def sample_payload(events=None):
    return {
        "applet": "logic-gates",
        "user": "Kid1",
        "session_id": "logic-gates_K1_2026-07-11_103814",
        "start_stamp": "2026-07-11_103814",
        "start_wall_time": "2026-07-11 10:38:14",
        "user_agent": "test-agent",
        "events": events or [],
    }
class TelemetryServerTest(unittest.TestCase):
    def test_filename_validation_accepts_good_and_rejects_bad_inputs(self):
        self.assertEqual(
            telemetry_server.safe_session_filename(sample_payload()),
            "logic-gates_K1_2026-07-11_103814.sqlite",
        )
        payload = sample_payload()
        payload["applet"] = "../evil"
        with self.assertRaises(ValueError):
            telemetry_server.safe_session_filename(payload)
        payload = sample_payload()
        payload["start_stamp"] = "2026-07-11_999999"
        payload["session_id"] = "logic-gates_K1_2026-07-11_999999"
        with self.assertRaises(ValueError):
            telemetry_server.safe_session_filename(payload)
    def test_step_visits_include_closed_and_unclosed_visits(self):
        events = telemetry_server.normalize_events([
            {"t_ms": 10, "kind": "step-enter", "step": 0},
            {"t_ms": 60, "kind": "step-leave", "step": 0},
            {"t_ms": 70, "kind": "step-enter", "step": 1},
        ])
        self.assertEqual(telemetry_server.derive_step_visits(events), [
            {"step": 0, "enter_t_ms": 10, "leave_t_ms": 60, "duration_ms": 50},
            {"step": 1, "enter_t_ms": 70, "leave_t_ms": None, "duration_ms": None},
        ])
    def test_quiz_attempts_count_retries_boundaries_and_missing_rounds(self):
        events = telemetry_server.normalize_events([
            {"t_ms": 100, "kind": "quiz-round", "detail": {"quiz": "AND", "round": 0, "prompt": "10"}},
            {"t_ms": 150, "kind": "quiz-attempt", "detail": {"quiz": "AND", "round": 0, "prompt": "10", "given": "0", "isCorrect": False}},
            {"t_ms": 180, "kind": "quiz-attempt", "detail": {"quiz": "AND", "round": 0, "prompt": "10", "given": "1", "isCorrect": True}},
            {"t_ms": 300, "kind": "quiz-round", "detail": {"quiz": "AND", "round": 0, "prompt": "10"}},
            {"t_ms": 350, "kind": "quiz-attempt", "detail": {"quiz": "AND", "round": 0, "prompt": "10", "given": "1", "isCorrect": True}},
            {"t_ms": 500, "kind": "quiz-attempt", "detail": {"quiz": "OR", "round": 1, "prompt": "11", "given": "0", "isCorrect": False}},
        ])
        attempts = telemetry_server.derive_quiz_attempts(events)
        self.assertEqual([attempt["attempt_index"] for attempt in attempts], [1, 2, 1, 1])
        self.assertEqual([attempt["response_time_ms"] for attempt in attempts], [50, 80, 50, None])
        self.assertEqual([attempt["is_correct"] for attempt in attempts], [0, 1, 1, 0])
    def test_full_save_rebuilds_sqlite_file(self):
        events = [
            {"t_ms": 0, "kind": "start", "detail": {"applet": "logic-gates"}},
            {"t_ms": 5, "kind": "step-enter", "step": 0},
            {"t_ms": 20, "kind": "click", "step": 0, "target": "start"},
            {"t_ms": 40, "kind": "quiz-round", "step": 3, "detail": {"quiz": "NOT", "round": 0, "prompt": "1"}},
            {"t_ms": 90, "kind": "quiz-attempt", "step": 3, "detail": {"quiz": "NOT", "round": 0, "prompt": "1", "given": "0", "isCorrect": True}},
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            result = telemetry_server.save_payload(sample_payload(events), data_dir=tmpdir)
            self.assertTrue(os.path.exists(result["path"]))
            conn = sqlite3.connect(result["path"])
            try:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM Users").fetchone()[0], 1)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM Sessions").fetchone()[0], 1)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM Events").fetchone()[0], 5)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM StepVisits").fetchone()[0], 1)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM QuizAttempts").fetchone()[0], 1)
                session = conn.execute("SELECT total_clicks, total_quiz_attempts, duration_ms, end_time FROM Sessions").fetchone()
                self.assertEqual(session, (1, 1, 90, "2026-07-11 10:38:14"))
                detail = json.loads(conn.execute("SELECT detail_json FROM Events WHERE kind = 'quiz-attempt'").fetchone()[0])
                self.assertEqual(detail["given"], "0")
            finally:
                conn.close()
            next_events = events + [
                {"t_ms": 120, "kind": "click", "step": 3, "target": "Finish"},
            ]
            result = telemetry_server.save_payload(sample_payload(next_events), data_dir=tmpdir)
            conn = sqlite3.connect(result["path"])
            try:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM Events").fetchone()[0], 6)
                self.assertEqual(conn.execute("SELECT total_clicks FROM Sessions").fetchone()[0], 2)
            finally:
                conn.close()
if __name__ == "__main__":
    unittest.main()
