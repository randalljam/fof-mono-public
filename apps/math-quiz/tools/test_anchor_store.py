#!/usr/bin/env python3
"""Tests for tools/anchor_store.py (naming + append). Stdlib sqlite3 only."""
import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import anchor_store as A  # noqa: E402

SCHEMA = """
CREATE TABLE Users (name TEXT PRIMARY KEY);
CREATE TABLE Sessions (session_id TEXT PRIMARY KEY, session_filename TEXT, user_name TEXT,
  start_time TEXT, end_time TEXT, num_problems INTEGER, number_range_start INTEGER,
  number_range_end INTEGER, numbers_include TEXT, numbers_exclude TEXT, num_numbers INTEGER,
  operations TEXT, total_problems INTEGER, correct_answers INTEGER, average_response_time_ms INTEGER);
CREATE TABLE ProblemAttempts (attempt_id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT,
  problem_id TEXT, problem_text TEXT, num1 INTEGER, num2 INTEGER, operation TEXT, correct_answer REAL,
  user_answer_string TEXT, user_answer REAL, is_correct INTEGER, response_time_ms INTEGER,
  flags_json TEXT, presented_at TEXT);
"""

def make_db(path, user, session_id, problems):
    c = sqlite3.connect(path)
    c.executescript(SCHEMA)
    c.execute("INSERT INTO Users(name) VALUES(?)", (user,))
    c.execute("INSERT INTO Sessions(session_id, user_name, start_time, total_problems) VALUES(?,?,?,?)",
              (session_id, user, "2026-06-19_120000", len(problems)))
    for i, (a, b) in enumerate(problems):
        c.execute("INSERT INTO ProblemAttempts(session_id, problem_id, problem_text, num1, num2, operation,"
                  " correct_answer, is_correct, response_time_ms) VALUES(?,?,?,?,?,?,?,?,?)",
                  (session_id, f"p{i}", f"{a} + {b}", a, b, "+", a + b, 1, 1500))
    c.commit()
    c.close()

class NamingTests(unittest.TestCase):
    def test_parse_single_vs_multi(self):
        s = A.parse_filename("math-flu_Randy_2026-06-19_143000.sqlite")
        self.assertEqual((s["name"], s["date"], s["time"], s["multi"]), ("Randy", "2026-06-19", "143000", False))
        m = A.parse_filename("math-flu_Randy_2026-06-19.sqlite")
        self.assertEqual((m["name"], m["date"], m["time"], m["multi"]), ("Randy", "2026-06-19", None, True))
        ms = A.parse_filename("math-flu_Randy_2026-06-19_ipad.sqlite")  # suffix provision
        self.assertEqual((ms["suffix"], ms["multi"]), ("ipad", True))
        self.assertIsNone(A.parse_filename("something_else.sqlite"))

    def test_to_multi_drops_time(self):
        self.assertEqual(A.to_multi_name("math-flu_Randy_2026-06-19_143000.sqlite"),
                         "math-flu_Randy_2026-06-19.sqlite")
        # already multi -> unchanged
        self.assertEqual(A.to_multi_name("math-flu_Randy_2026-06-19.sqlite"),
                         "math-flu_Randy_2026-06-19.sqlite")

    def test_pick_target_prefers_recent_and_multi(self):
        files = [
            "math-flu_Randy_2026-06-17_090000.sqlite",
            "math-flu_Randy_2026-06-19_080000.sqlite",  # single, same date as multi
            "math-flu_Randy_2026-06-19.sqlite",         # multi (accumulated) — should win
            "math-flu_K1_2026-06-20.sqlite",
        ]
        self.assertEqual(A.pick_target(files, "Randy"), "math-flu_Randy_2026-06-19.sqlite")
        self.assertIsNone(A.pick_target(files, "Nobody"))

    def test_resolve_save_create_then_append(self):
        # No existing files -> create a single-session file with the full stamp.
        r = A.resolve_save("real", "Randy", "2026-06-19_143000", [])
        self.assertEqual(r, {"action": "create", "target": None,
                             "filename": "math-flu_Randy_2026-06-19_143000.sqlite"})
        # A single-session file exists -> append, renaming it to the multi (date-only) form.
        r2 = A.resolve_save("real", "Randy", "2026-06-20_101010",
                            ["math-flu_Randy_2026-06-19_143000.sqlite"])
        self.assertEqual(r2, {"action": "append", "target": "math-flu_Randy_2026-06-19_143000.sqlite",
                              "filename": "math-flu_Randy_2026-06-19.sqlite"})
        # A multi file exists -> append, keep its name.
        r3 = A.resolve_save("real", "Randy", "2026-06-21_101010", ["math-flu_Randy_2026-06-19.sqlite"])
        self.assertEqual(r3["action"], "append")
        self.assertEqual(r3["filename"], "math-flu_Randy_2026-06-19.sqlite")

    def test_force_new_starts_fresh_lineage(self):
        # Even with an existing file, Start New (force_new) creates a brand-new single file.
        r = A.resolve_save("real", "Randy", "2026-06-19_150000",
                           ["math-flu_Randy_2026-06-19.sqlite"], force_new=True)
        self.assertEqual(r, {"action": "create", "target": None,
                             "filename": "math-flu_Randy_2026-06-19_150000.sqlite"})

    def test_pick_latest_follows_mtime_not_filename_date(self):
        # An older-dated file that was modified most recently wins (it's the one being
        # actively added to), which a filename-date-only pick (pick_target) would miss.
        entries = [
            ("math-flu_Randy_2026-06-19.sqlite", 100),       # older lineage, untouched
            ("math-flu_Randy_2026-06-17_090000.sqlite", 500),  # older date, just modified
        ]
        self.assertEqual(A.pick_latest(entries, "Randy"), "math-flu_Randy_2026-06-17_090000.sqlite")
        self.assertEqual(A.pick_target([f for f, _ in entries], "Randy"),
                         "math-flu_Randy_2026-06-19.sqlite")  # filename-only differs, as expected
        self.assertIsNone(A.pick_latest(entries, "Nobody"))

    def test_list_landing_users_unique_names(self):
        files = [
            "math-flu_G1_2026-06-15_multi-session.sqlite",
            "math-flu_Kid1_2026-06-17.sqlite",
            "math-flu_Kid2_2026-06-16.sqlite",
            "not-a-math-flu.sqlite",
        ]
        users = A.list_landing_users(files)
        self.assertEqual(
            [(u["name"], u["label"]) for u in users],
            [("G1", "G1"), ("Kid1", "Kid1"), ("Kid2", "Kid2")],
        )

    def test_list_landing_users_appends_date_when_name_repeats(self):
        files = [
            "math-flu_Kid1_2026-06-17.sqlite",
            "math-flu_Kid1_2026-07-01.sqlite",
            "math-flu_Kid2_2026-06-16.sqlite",
        ]
        users = A.list_landing_users(files)
        self.assertEqual(
            [(u["name"], u["label"], u["filename"]) for u in users],
            [
                ("Kid1", "Kid1 2026-06-17", "math-flu_Kid1_2026-06-17.sqlite"),
                ("Kid1", "Kid1 2026-07-01", "math-flu_Kid1_2026-07-01.sqlite"),
                ("Kid2", "Kid2", "math-flu_Kid2_2026-06-16.sqlite"),
            ],
        )

    def test_list_landing_users_same_day_collision_uses_time(self):
        files = [
            "math-flu_Kid1_2026-06-17_100000.sqlite",
            "math-flu_Kid1_2026-06-17_150000.sqlite",
        ]
        users = A.list_landing_users(files)
        labels = [u["label"] for u in users]
        self.assertEqual(labels, ["Kid1 2026-06-17 100000", "Kid1 2026-06-17 150000"])

    def test_next_multi_name_suffixes_on_collision(self):
        existing = ["math-flu_K1_2026-06-20.sqlite"]
        self.assertEqual(A.next_multi_name([], "Kid1", "2026-06-20"), "math-flu_K1_2026-06-20.sqlite")
        self.assertEqual(A.next_multi_name(existing, "Kid1", "2026-06-20"), "math-flu_K1_2026-06-20_2.sqlite")
        self.assertEqual(A.next_multi_name(existing + ["math-flu_K1_2026-06-20_2.sqlite"], "Kid1", "2026-06-20"),
                         "math-flu_K1_2026-06-20_3.sqlite")

    def test_same_day_start_new_then_append_suffixes_and_picks_latest(self):
        # Randy's walkthrough: one accumulated lineage exists today (bare multi), then a
        # fresh "Start New" single is created later the same day and is the newest. The
        # next plain run (Continue latest) must append into that newer single and, because
        # the bare multi name is taken, the rename lands on _2 — not overwrite the first.
        entries = [
            ("math-flu_Randy_2026-06-20.sqlite", 100),          # lineage #1 (accumulated), older
            ("math-flu_Randy_2026-06-20_130000.sqlite", 200),   # lineage #2 (Start New single), newest
        ]
        plan = A.resolve_save("real", "Randy", "2026-06-20_133000", entries)
        self.assertEqual(plan["action"], "append")
        self.assertEqual(plan["target"], "math-flu_Randy_2026-06-20_130000.sqlite")  # the newer single
        self.assertEqual(plan["filename"], "math-flu_Randy_2026-06-20_2.sqlite")     # suffixed, no collision

class PrefixTests(unittest.TestCase):
    def test_parse_respects_prefix(self):
        # A math-quest file parses under prefix="math-quest" but not under the default.
        fn = "math-quest_K1_2026-06-19_143000.sqlite"
        self.assertIsNone(A.parse_filename(fn))                       # default math-flu -> no match
        p = A.parse_filename(fn, prefix="math-quest")
        self.assertEqual((p["name"], p["date"], p["time"], p["multi"]), ("Kid1", "2026-06-19", "143000", False))

    def test_naming_helpers_use_prefix(self):
        self.assertEqual(A.single_session_name("Kid1", "2026-06-19_143000", prefix="math-quest"),
                         "math-quest_K1_2026-06-19_143000.sqlite")
        self.assertEqual(A.multi_session_name("Kid1", "2026-06-19", prefix="math-quest"),
                         "math-quest_K1_2026-06-19.sqlite")
        self.assertEqual(A.to_multi_name("math-quest_K1_2026-06-19_143000.sqlite", prefix="math-quest"),
                         "math-quest_K1_2026-06-19.sqlite")

    def test_pick_and_resolve_use_prefix(self):
        files = ["math-quest_K1_2026-06-19_080000.sqlite", "math-quest_K1_2026-06-19.sqlite"]
        self.assertEqual(A.pick_target(files, "Kid1", prefix="math-quest"), "math-quest_K1_2026-06-19.sqlite")
        r = A.resolve_save("test", "Kid1", "2026-06-20_101010",
                           ["math-quest_K1_2026-06-19_080000.sqlite"], prefix="math-quest")
        self.assertEqual(r, {"action": "append", "target": "math-quest_K1_2026-06-19_080000.sqlite",
                             "filename": "math-quest_K1_2026-06-19.sqlite"})

    def test_prefixes_do_not_collide(self):
        # math-flu and math-quest files for the same person are distinct lineages.
        files = ["math-flu_K1_2026-06-19.sqlite", "math-quest_K1_2026-06-19.sqlite"]
        self.assertEqual(A.pick_target(files, "Kid1"), "math-flu_K1_2026-06-19.sqlite")
        self.assertEqual(A.pick_target(files, "Kid1", prefix="math-quest"), "math-quest_K1_2026-06-19.sqlite")

class AccumulateTests(unittest.TestCase):
    def _drop(self, d, name, session_id, problems):
        path = os.path.join(d, f"src_{session_id}.sqlite")
        make_db(path, name, session_id, problems)
        return path

    def test_create_then_append_renames_single_to_multi(self):
        d = tempfile.mkdtemp()
        dest = os.path.join(d, "test")
        src1 = self._drop(d, "Kid1", "s1", [(2, 3)])
        r1 = A.accumulate(dest, "Kid1", "2026-06-19_120000", src1, prefix="math-quest")
        self.assertEqual(r1["action"], "create")
        self.assertEqual(r1["filename"], "math-quest_K1_2026-06-19_120000.sqlite")
        self.assertEqual(r1["added"], 1)
        self.assertTrue(os.path.exists(r1["path"]))
        # Second drop continues the lineage -> single renamed to the multi (date-only) form.
        src2 = self._drop(d, "Kid1", "s2", [(4, 5)])
        r2 = A.accumulate(dest, "Kid1", "2026-06-20_130000", src2, prefix="math-quest")
        self.assertEqual(r2["action"], "append")
        self.assertEqual(r2["filename"], "math-quest_K1_2026-06-19.sqlite")
        self.assertEqual(r2["added"], 1)
        # The accumulated multi exists with both sessions; the stale single is gone.
        self.assertTrue(os.path.exists(os.path.join(dest, "math-quest_K1_2026-06-19.sqlite")))
        self.assertFalse(os.path.exists(os.path.join(dest, "math-quest_K1_2026-06-19_120000.sqlite")))
        c = sqlite3.connect(os.path.join(dest, "math-quest_K1_2026-06-19.sqlite"))
        self.assertEqual(c.execute("SELECT COUNT(*) FROM Sessions").fetchone()[0], 2)
        c.close()

    def test_accumulate_is_idempotent(self):
        d = tempfile.mkdtemp()
        dest = os.path.join(d, "test")
        src = self._drop(d, "K2", "only", [(1, 1)])
        A.accumulate(dest, "K2", "2026-06-19_120000", src, prefix="math-quest")
        # Re-accumulating the SAME single-session file adds 0 (dedup by session_id).
        r = A.accumulate(dest, "K2", "2026-06-19_120000", src, prefix="math-quest")
        self.assertEqual(r["added"], 0)

    def test_force_new_starts_fresh_file(self):
        d = tempfile.mkdtemp()
        dest = os.path.join(d, "test")
        src1 = self._drop(d, "K2", "s1", [(1, 1)])
        A.accumulate(dest, "K2", "2026-06-19_120000", src1, prefix="math-quest")
        src2 = self._drop(d, "K2", "s2", [(2, 2)])
        r = A.accumulate(dest, "K2", "2026-06-19_150000", src2, prefix="math-quest", force_new=True)
        self.assertEqual(r["action"], "create")
        self.assertEqual(r["filename"], "math-quest_K2_2026-06-19_150000.sqlite")

    def test_local_entries_and_session_count(self):
        d = tempfile.mkdtemp()
        dest = os.path.join(d, "test")
        src = self._drop(d, "Kid1", "s1", [(2, 3)])
        out = A.accumulate(dest, "Kid1", "2026-06-19_120000", src, prefix="math-quest")
        entries = A.local_entries(dest)
        self.assertEqual([fn for fn, _ in entries], ["math-quest_K1_2026-06-19_120000.sqlite"])
        self.assertEqual(A.session_count(out["path"]), 1)

class AppendTests(unittest.TestCase):
    def test_append_merges_and_dedups(self):
        d = tempfile.mkdtemp()
        target = os.path.join(d, "target.sqlite")
        ind1 = os.path.join(d, "ind1.sqlite")
        ind2 = os.path.join(d, "ind2.sqlite")
        make_db(target, "Randy", "sess-1", [(3, 4), (5, 6)])
        make_db(ind2, "Randy", "sess-2", [(7, 8)])
        # append a new session
        added = A.append_session(target, ind2)
        self.assertEqual(added, 1)
        c = sqlite3.connect(target)
        self.assertEqual(c.execute("SELECT COUNT(*) FROM Sessions").fetchone()[0], 2)
        self.assertEqual(c.execute("SELECT COUNT(*) FROM ProblemAttempts").fetchone()[0], 3)
        self.assertEqual(c.execute("SELECT COUNT(*) FROM Users").fetchone()[0], 1)  # same user not duplicated
        # re-appending the same session is a no-op (idempotent)
        self.assertEqual(A.append_session(target, ind2), 0)
        self.assertEqual(c.execute("SELECT COUNT(*) FROM Sessions").fetchone()[0], 2)
        c.close()

    def test_append_carries_visual_practice_tables(self):
        # Regression: the append table list omitted the VisualPractice* trio, so a visual
        # session's metadata was dropped from the accumulated file (only Sessions/attempts
        # survived). The tables must be created in the destination and their rows copied.
        d = tempfile.mkdtemp()
        target = os.path.join(d, "target.sqlite")
        src = os.path.join(d, "single.sqlite")
        make_db(target, "Kid1", "sess-1", [(3, 4)])
        make_db(src, "Kid1", "sess-2", [(8, 3)])
        c = sqlite3.connect(src)
        c.executescript(
            "CREATE TABLE VisualPracticeSessions (session_id TEXT PRIMARY KEY, user_name TEXT,"
            " outcome TEXT, complete INTEGER, cleared_count INTEGER);"
            "CREATE TABLE VisualPracticeTargets (session_id TEXT, target_order INTEGER,"
            " target_key TEXT, cleared INTEGER, PRIMARY KEY (session_id, target_key));"
            "CREATE TABLE VisualPracticeAttemptRoles (session_id TEXT, problem_id TEXT,"
            " trial_role TEXT, passed INTEGER, PRIMARY KEY (session_id, problem_id));")
        c.execute("INSERT INTO VisualPracticeSessions VALUES('sess-2','Kid1','visual-complete',1,1)")
        c.execute("INSERT INTO VisualPracticeTargets VALUES('sess-2',1,'+|3|8',1)")
        c.execute("INSERT INTO VisualPracticeAttemptRoles VALUES('sess-2','p0','cold-probe',1)")
        c.commit(); c.close()
        self.assertEqual(A.append_session(target, src), 1)
        c = sqlite3.connect(target)
        self.assertEqual(c.execute("SELECT outcome FROM VisualPracticeSessions").fetchone()[0], "visual-complete")
        self.assertEqual(c.execute("SELECT COUNT(*) FROM VisualPracticeTargets").fetchone()[0], 1)
        self.assertEqual(c.execute("SELECT trial_role FROM VisualPracticeAttemptRoles").fetchone()[0], "cold-probe")
        # idempotent: re-append copies nothing
        self.assertEqual(A.append_session(target, src), 0)
        self.assertEqual(c.execute("SELECT COUNT(*) FROM VisualPracticeAttemptRoles").fetchone()[0], 1)
        c.close()

    def test_append_preserves_newer_columns_like_presented_at(self):
        # Regression: an accumulated file whose ProblemAttempts predates `presented_at` used to
        # DROP it on every append (intersection of columns). Now the column is added and kept.
        d = tempfile.mkdtemp()
        dst = os.path.join(d, "accum.sqlite")   # OLD schema — no presented_at column
        src = os.path.join(d, "single.sqlite")  # NEW capture — has presented_at + a value
        c = sqlite3.connect(dst)
        c.executescript(
            "CREATE TABLE Users (name TEXT PRIMARY KEY);"
            "CREATE TABLE Sessions (session_id TEXT PRIMARY KEY, user_name TEXT, start_time TEXT);"
            "CREATE TABLE ProblemAttempts (attempt_id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT,"
            " problem_text TEXT, response_time_ms INTEGER);")
        c.execute("INSERT INTO Users(name) VALUES('Kid1')")
        c.execute("INSERT INTO Sessions VALUES('s1','Kid1','2026-06-21_100000')")
        c.execute("INSERT INTO ProblemAttempts(session_id, problem_text, response_time_ms) VALUES('s1','3 + 7',2000)")
        c.commit(); c.close()
        c = sqlite3.connect(src)
        c.executescript(
            "CREATE TABLE Users (name TEXT PRIMARY KEY);"
            "CREATE TABLE Sessions (session_id TEXT PRIMARY KEY, user_name TEXT, start_time TEXT);"
            "CREATE TABLE ProblemAttempts (attempt_id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT,"
            " problem_text TEXT, response_time_ms INTEGER, presented_at TEXT);")
        c.execute("INSERT INTO Users(name) VALUES('Kid1')")
        c.execute("INSERT INTO Sessions VALUES('s2','Kid1','2026-06-21_103126')")
        c.execute("INSERT INTO ProblemAttempts(session_id, problem_text, response_time_ms, presented_at)"
                  " VALUES('s2','3 + 7',2847,'2026-06-21T17:32:34.067Z')")
        c.commit(); c.close()

        self.assertEqual(A.append_session(dst, src), 1)
        c = sqlite3.connect(dst)
        cols = [r[1] for r in c.execute("PRAGMA table_info(ProblemAttempts)")]
        self.assertIn("presented_at", cols)   # the fix adds the missing column
        self.assertEqual(c.execute("SELECT presented_at FROM ProblemAttempts WHERE session_id='s2'").fetchone()[0],
                         "2026-06-21T17:32:34.067Z")     # the new session's timestamp is preserved
        self.assertIsNone(c.execute("SELECT presented_at FROM ProblemAttempts WHERE session_id='s1'").fetchone()[0])
        c.close()

if __name__ == "__main__":
    unittest.main()
