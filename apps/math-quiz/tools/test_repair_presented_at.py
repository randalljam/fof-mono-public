#!/usr/bin/env python3
"""Tests for tools/repair_presented_at.py (backfill presented_at from single-session captures)."""
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
import repair_presented_at as R  # noqa: E402

def _capture(path, rows):
    """A single-session capture WITH presented_at. rows = [(problem_id, presented_at), ...]."""
    c = sqlite3.connect(path)
    c.execute("CREATE TABLE ProblemAttempts (attempt_id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT,"
              " problem_id TEXT, problem_text TEXT, response_time_ms INTEGER, presented_at TEXT)")
    for pid, at in rows:
        c.execute("INSERT INTO ProblemAttempts(session_id, problem_id, problem_text, presented_at) VALUES(?,?,?,?)",
                  ("s1", pid, "3 + 7", at))
    c.commit(); c.close()
def _accum_old_schema(path, problem_ids):
    """An accumulated file with the OLD schema (no presented_at column)."""
    c = sqlite3.connect(path)
    c.execute("CREATE TABLE ProblemAttempts (attempt_id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT,"
              " problem_id TEXT, problem_text TEXT, response_time_ms INTEGER)")
    for pid in problem_ids:
        c.execute("INSERT INTO ProblemAttempts(session_id, problem_id, problem_text) VALUES(?,?,?)",
                  ("s1", pid, "3 + 7"))
    c.commit(); c.close()

class RepairTests(unittest.TestCase):
    def test_map_built_from_captures(self):
        d = tempfile.mkdtemp()
        _capture(os.path.join(d, "math-flu_K1_2026-06-21_103126.sqlite"),
                 [("p0", "2026-06-21T17:31:26Z"), ("p1", "2026-06-21T17:31:32Z")])
        m = R.build_presented_at_map(d)
        self.assertEqual(m, {"p0": "2026-06-21T17:31:26Z", "p1": "2026-06-21T17:31:32Z"})

    def test_backfill_adds_column_and_fills_missing(self):
        d = tempfile.mkdtemp()
        singles = os.path.join(d, "singles"); os.makedirs(singles)
        _capture(os.path.join(singles, "cap.sqlite"), [("p0", "2026-06-21T17:31:26Z"), ("p1", "2026-06-21T17:31:32Z")])
        accum = os.path.join(d, "accum.sqlite")
        _accum_old_schema(accum, ["p0", "p1", "pX"])     # pX has no capture
        pa = R.build_presented_at_map(singles)
        # dry run: reports fillable but writes nothing
        dry = R.backfill_file(accum, pa, execute=False)
        self.assertEqual((dry["total"], dry["already"], dry["filled"], dry["still_missing"]), (3, 0, 2, 1))
        self.assertNotIn("presented_at", [r[1] for r in sqlite3.connect(accum).execute("PRAGMA table_info(ProblemAttempts)")])
        # execute: adds the column, fills the two matched rows, leaves pX null, makes a .bak
        res = R.backfill_file(accum, pa, execute=True)
        self.assertEqual(res["filled"], 2)
        self.assertTrue(os.path.exists(accum + ".bak"))
        c = sqlite3.connect(accum)
        self.assertIn("presented_at", [r[1] for r in c.execute("PRAGMA table_info(ProblemAttempts)")])
        self.assertEqual(c.execute("SELECT presented_at FROM ProblemAttempts WHERE problem_id='p0'").fetchone()[0],
                         "2026-06-21T17:31:26Z")
        self.assertIsNone(c.execute("SELECT presented_at FROM ProblemAttempts WHERE problem_id='pX'").fetchone()[0])
        c.close()

    def test_backfill_does_not_overwrite_existing(self):
        d = tempfile.mkdtemp()
        singles = os.path.join(d, "singles"); os.makedirs(singles)
        _capture(os.path.join(singles, "cap.sqlite"), [("p0", "FROM-CAPTURE")])
        accum = os.path.join(d, "accum.sqlite")
        c = sqlite3.connect(accum)
        c.execute("CREATE TABLE ProblemAttempts (attempt_id INTEGER PRIMARY KEY AUTOINCREMENT, problem_id TEXT, presented_at TEXT)")
        c.execute("INSERT INTO ProblemAttempts(problem_id, presented_at) VALUES('p0','ALREADY-SET')")
        c.commit(); c.close()
        R.backfill_file(accum, R.build_presented_at_map(singles), execute=True)
        c = sqlite3.connect(accum)
        self.assertEqual(c.execute("SELECT presented_at FROM ProblemAttempts WHERE problem_id='p0'").fetchone()[0],
                         "ALREADY-SET")   # not overwritten
        c.close()

if __name__ == "__main__":
    unittest.main()
