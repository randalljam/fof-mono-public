#!/usr/bin/env python3
"""Tests for tools/clone_user_file.py (clone one learner's file as another user).
Stdlib sqlite3 only."""
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(__file__))
import clone_user_file as C  # noqa: E402
from test_anchor_store import make_db  # noqa: E402


def add_per_user_tables(path, user):
    """Add per-user config tables (user_name primary keys) like a real file has."""
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE Profile (user_name TEXT PRIMARY KEY, green_ms INTEGER)")
    conn.execute("INSERT INTO Profile VALUES (?, 2000)", (user,))
    conn.execute("CREATE TABLE FluencyFeastConfig (user_name TEXT PRIMARY KEY, num_problems INTEGER)")
    conn.execute("INSERT INTO FluencyFeastConfig VALUES (?, 20)", (user,))
    conn.commit()
    conn.close()


def set_session_filename(path, session_id, filename):
    conn = sqlite3.connect(path)
    conn.execute("UPDATE Sessions SET session_filename = ? WHERE session_id = ?", (filename, session_id))
    conn.commit()
    conn.close()


def q1(path, sql, params=()):
    conn = sqlite3.connect(path)
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


class CloneUserFileTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.Kid1 = self.dir / "math-flu_K1_2026-06-17.sqlite"
        make_db(str(self.Kid1), "Kid1", "s1", [(2, 3), (7, 1)])
        add_per_user_tables(str(self.Kid1), "Kid1")
        set_session_filename(str(self.Kid1), "s1", "anchor_K1_2026-06-17_110141.sqlite")
        self.k1_bytes = self.Kid1.read_bytes()

    def test_force_clone_deletes_target_and_renames_everywhere(self):
        old_randy = self.dir / "math-flu_Randy_2026-06-10.sqlite"
        make_db(str(old_randy), "Randy", "r1", [(1, 1)])
        r = C.clone_user_file(self.dir, "Kid1", "Randy", force=True)
        self.assertTrue(r["ok"])
        self.assertEqual(r["deleted"], ["math-flu_Randy_2026-06-10.sqlite"])
        self.assertFalse(old_randy.exists())
        new = self.dir / "math-flu_Randy_2026-06-17.sqlite"
        self.assertEqual(r["new_file"], new.name)
        self.assertTrue(new.exists())
        # renamed in every table
        self.assertEqual(q1(str(new), "SELECT name FROM Users"), [("Randy",)])
        self.assertEqual(q1(str(new), "SELECT DISTINCT user_name FROM Sessions"), [("Randy",)])
        self.assertEqual(q1(str(new), "SELECT user_name FROM Profile"), [("Randy",)])
        self.assertEqual(q1(str(new), "SELECT user_name FROM FluencyFeastConfig"), [("Randy",)])
        # name embedded in session_filename swapped too
        self.assertEqual(q1(str(new), "SELECT session_filename FROM Sessions"),
                         [("anchor_Randy_2026-06-17_110141.sqlite",)])
        # attempts came along; source file untouched byte-for-byte
        self.assertEqual(q1(str(new), "SELECT COUNT(*) FROM ProblemAttempts"), [(2,)])
        self.assertEqual(self.Kid1.read_bytes(), self.k1_bytes)

    def test_prompt_declined_aborts_and_keeps_target(self):
        old_randy = self.dir / "math-flu_Randy_2026-06-10.sqlite"
        make_db(str(old_randy), "Randy", "r1", [(1, 1)])
        r = C.clone_user_file(self.dir, "Kid1", "Randy", force=False, prompt=lambda _msg: "n")
        self.assertFalse(r["ok"])
        self.assertTrue(old_randy.exists())
        self.assertFalse((self.dir / "math-flu_Randy_2026-06-17.sqlite").exists())

    def test_prompt_accepted_proceeds(self):
        old_randy = self.dir / "math-flu_Randy_2026-06-10.sqlite"
        make_db(str(old_randy), "Randy", "r1", [(1, 1)])
        r = C.clone_user_file(self.dir, "Kid1", "Randy", force=False, prompt=lambda _msg: "y")
        self.assertTrue(r["ok"])
        self.assertFalse(old_randy.exists())
    def test_failed_clone_keeps_existing_target_file(self):
        old_randy = self.dir / "math-flu_Randy_2026-06-10.sqlite"
        make_db(str(old_randy), "Randy", "r1", [(1, 1)])
        old_bytes = old_randy.read_bytes()
        with mock.patch.object(C, "rename_user_in_db", side_effect=RuntimeError("bad clone")):
            with self.assertRaisesRegex(RuntimeError, "bad clone"):
                C.clone_user_file(self.dir, "Kid1", "Randy", force=True)
        self.assertEqual(old_randy.read_bytes(), old_bytes)
        self.assertFalse((self.dir / "math-flu_Randy_2026-06-17.sqlite").exists())
        self.assertEqual(list(self.dir.glob("*.tmp")), [])

    def test_no_existing_target_needs_no_prompt(self):
        called = []
        r = C.clone_user_file(self.dir, "Kid1", "Randy", force=False,
                              prompt=lambda _msg: called.append(1) or "n")
        self.assertTrue(r["ok"])
        self.assertEqual(called, [])

    def test_missing_source_and_same_user_error(self):
        self.assertFalse(C.clone_user_file(self.dir, "Ghost", "Randy", force=True)["ok"])
        self.assertFalse(C.clone_user_file(self.dir, "Kid1", "Kid1", force=True)["ok"])
    def test_cli_data_folder_rejects_traversal(self):
        with mock.patch.object(C, "DATA_DIR", self.dir):
            self.assertEqual(C._data_folder("inside"), (self.dir / "inside").resolve())
            self.assertIsNone(C._data_folder("../outside"))
            self.assertIsNone(C._data_folder("."))

    def test_single_session_source_keeps_its_time_in_the_new_name(self):
        # Filename learner name must match source_user (pick_latest keys off the filename).
        single = self.dir / "math-flu_K2_2026-06-16_140533.sqlite"
        make_db(str(single), "K2", "m1", [(4, 4)])
        r = C.clone_user_file(self.dir, "K2", "Tester", force=True)
        self.assertTrue(r["ok"], r.get("error"))
        self.assertEqual(r["new_file"], "math-flu_Tester_2026-06-16_140533.sqlite")
    def test_explicit_source_filename_clones_that_lineage(self):
        newer = self.dir / "math-flu_K1_2026-07-01.sqlite"
        make_db(str(newer), "Kid1", "s2", [(9, 9)])
        os.utime(self.Kid1, (1000, 1000))
        os.utime(newer, (2000, 2000))
        r = C.clone_user_file(
            self.dir, "Kid1", "Randy", force=True, source_filename=self.Kid1.name)
        self.assertTrue(r["ok"], r.get("error"))
        self.assertEqual(r["source_file"], self.Kid1.name)
        self.assertEqual(r["new_file"], "math-flu_Randy_2026-06-17.sqlite")


if __name__ == "__main__":
    unittest.main()
