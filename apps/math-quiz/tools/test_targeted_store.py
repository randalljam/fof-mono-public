#!/usr/bin/env python3
"""Tests for targeted_store (per-user targeted-practice config in the .sqlite) plus the
dev-server /api/targeted-config endpoints + save_run persistence. Stdlib sqlite3 only."""
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
import targeted_store as T  # noqa: E402
import dev_server as D  # noqa: E402
from test_anchor_store import make_db  # noqa: E402


class NormalizeTests(unittest.TestCase):
    def test_normalize_fact_whitespace_and_symbols(self):
        self.assertEqual(T.normalize_fact("3+6"), "3+6")
        self.assertEqual(T.normalize_fact("  3 + 6 "), "3+6")
        self.assertEqual(T.normalize_fact("8x7"), "8*7")
        self.assertEqual(T.normalize_fact("8×7"), "8*7")
        self.assertEqual(T.normalize_fact("6+0"), "6+0")     # orientation preserved
        self.assertEqual(T.normalize_fact("3+6", spaced=True), "3 + 6")   # filler form has spaces
        self.assertEqual(T.normalize_fact("  3+6 ", spaced=True), "3 + 6")
        self.assertIsNone(T.normalize_fact("hello"))
        self.assertIsNone(T.normalize_fact(""))

    def test_normalize_facts_list_and_text(self):
        self.assertEqual(T.normalize_facts(["3+6", "", " 8 + 7 ", "junk"]), ["3+6", "8+7"])
        self.assertEqual(T.normalize_facts("6+0\n0+6\n3+3", spaced=True), ["6 + 0", "0 + 6", "3 + 3"])  # filler keeps dupes/orientation


class StoreTests(unittest.TestCase):
    def _db(self):
        d = tempfile.mkdtemp()
        return os.path.join(d, "s.sqlite")

    def test_get_empty_is_none(self):
        conn = T.connect(self._db())
        try:
            self.assertIsNone(T.get_config(conn, "Kid1"))
        finally:
            conn.close()

    def test_set_then_get_roundtrip_caps_and_clamps(self):
        conn = T.connect(self._db())
        try:
            cfg = T.set_config(conn, "Kid1",
                               targets=["6+3", "6+8", "4+9", "3+7", "3+4", "1+1"],  # 6 -> capped to 5
                               filler=["0+1", "6+0", "0+6"],
                               graduation_streak=3, fast_ms=2000, percent_target=50)
            self.assertEqual(cfg["targets"], ["6+3", "6+8", "4+9", "3+7", "3+4"])   # compact
            self.assertEqual(cfg["filler"], ["0 + 1", "6 + 0", "0 + 6"])            # spaced
            self.assertEqual((cfg["graduationStreak"], cfg["fastMs"], cfg["percentTarget"]), (3, 2000, 50))
            # clamp out-of-range params
            cfg = T.set_config(conn, "Kid1", graduation_streak=99, percent_target=0, fast_ms=10)
            self.assertEqual(cfg["graduationStreak"], 9)     # clamped to [1,9]
            self.assertEqual(cfg["percentTarget"], 1)        # clamped to [1,100]
            self.assertEqual(cfg["fastMs"], 200)             # clamped to [200,60000]
        finally:
            conn.close()

    def test_partial_update_keeps_existing(self):
        conn = T.connect(self._db())
        try:
            T.set_config(conn, "K2", targets=["2+8", "2+7"], filler=["0+1"], percent_target=60)
            cfg = T.set_config(conn, "K2", filler=["1+1", "2+2"])   # only filler changes
            self.assertEqual(cfg["targets"], ["2+8", "2+7"])         # preserved
            self.assertEqual(cfg["filler"], ["1 + 1", "2 + 2"])      # spaced
            self.assertEqual(cfg["percentTarget"], 60)              # preserved
        finally:
            conn.close()

    def test_reward_images_default_none(self):
        conn = T.connect(self._db())
        try:
            cfg = T.set_config(conn, "Kid1", targets=["6+3"])
            self.assertIsNone(cfg["rewardImage"])        # unset -> None (page uses the fallback)
            self.assertIsNone(cfg["completionImage"])
        finally:
            conn.close()

    def test_reward_images_roundtrip_and_preserved(self):
        conn = T.connect(self._db())
        try:
            cfg = T.set_config(conn, "Kid1", targets=["6+3"],
                               reward_image="  _assets/pipa-dance.webp ",   # trimmed
                               completion_image="_assets/pipa_no_wand_clap_jump_fixed.webp")
            self.assertEqual(cfg["rewardImage"], "_assets/pipa-dance.webp")
            self.assertEqual(cfg["completionImage"], "_assets/pipa_no_wand_clap_jump_fixed.webp")
            # an auto-save that only touches targets/params must NOT wipe the images
            cfg = T.set_config(conn, "Kid1", targets=["6+3", "6+8"], percent_target=40)
            self.assertEqual(cfg["rewardImage"], "_assets/pipa-dance.webp")
            self.assertEqual(cfg["completionImage"], "_assets/pipa_no_wand_clap_jump_fixed.webp")
            # empty string clears a slot back to None
            cfg = T.set_config(conn, "Kid1", completion_image="")
            self.assertIsNone(cfg["completionImage"])
            self.assertEqual(cfg["rewardImage"], "_assets/pipa-dance.webp")   # other slot preserved
        finally:
            conn.close()

    def test_migrates_old_table_without_image_columns(self):
        path = self._db()
        # An older file: TargetedConfig exists but lacks the reward-image columns.
        conn = sqlite3.connect(path)
        conn.execute("""CREATE TABLE TargetedConfig (
            user_name TEXT PRIMARY KEY, graduation_streak INTEGER, fast_ms INTEGER,
            percent_target INTEGER, targets_json TEXT, filler_json TEXT, updated_at TEXT)""")
        conn.execute("INSERT INTO TargetedConfig VALUES ('Kid1',4,2000,30,'[\"6+3\"]','[]','2026-06-23_2145')")
        conn.commit(); conn.close()
        conn = T.connect(path)
        try:
            cfg = T.get_config(conn, "Kid1")               # triggers ensure_targeted_schema migration
            self.assertEqual(cfg["targets"], ["6+3"])
            self.assertIsNone(cfg["rewardImage"])
            cols = {r[1] for r in conn.execute("PRAGMA table_info(TargetedConfig)")}
            self.assertIn("reward_image", cols)
            self.assertIn("completion_image", cols)
            cfg = T.set_config(conn, "Kid1", completion_image="_assets/done.webp")
            self.assertEqual(cfg["completionImage"], "_assets/done.webp")
        finally:
            conn.close()


class DevServerTargetedConfig(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        D.DATA_DIR = self.tmp
        D._s3 = lambda: (_ for _ in ()).throw(RuntimeError("no s3 in test"))

    def _seed_source_file(self, user="Kid1"):
        # Create a per-person source file the way a finished run would.
        d = tempfile.mkdtemp()
        p = os.path.join(d, "s.sqlite")
        make_db(p, user, "s1", [(1, 1)])
        raw = Path(p).read_bytes()
        r = D.save_run("real", "source", user, "2026-06-20_090000", "", raw, force_new=True)
        self.assertTrue(r["ok"])
        return user

    def test_edit_then_view_and_latest_user_db_include_config(self):
        user = self._seed_source_file()
        res = D.edit_targeted_config("real", user, {
            "targets": ["6+3", "6+8", "4+9", "3+7", "3+4"],
            "filler": ["0+1", "1+1", "2+2"],
            "graduationStreak": 3, "fastMs": 2000, "percentTarget": 50})
        self.assertTrue(res["ok"])
        self.assertEqual(res["targetedConfig"]["targets"], ["6+3", "6+8", "4+9", "3+7", "3+4"])
        # view endpoint reads it back (filler stored in the spaced "a + b" form)
        view = D.targeted_config_view("real", user)
        self.assertEqual(view["targetedConfig"]["filler"], ["0 + 1", "1 + 1", "2 + 2"])
        # latest-user-db carries it for the page prefill
        latest = D.latest_user_db("real", user)
        self.assertEqual(latest["targetedConfig"]["percentTarget"], 50)

    def test_reward_images_through_endpoints_survive_autosave(self):
        user = self._seed_source_file("Kid1")
        # Coach sets both animation paths (e.g. the local agent writes Kid1's file).
        res = D.edit_targeted_config("real", user, {
            "targets": ["6+3"], "rewardImage": "_assets/pipa-dance.webp",
            "completionImage": "_assets/pipa_no_wand_clap_jump_fixed.webp"})
        self.assertEqual(res["targetedConfig"]["completionImage"], "_assets/pipa_no_wand_clap_jump_fixed.webp")
        # A later params-only auto-save (no image fields) must not clobber the paths.
        D.edit_targeted_config("real", user, {"targets": ["6+3", "6+8"], "percentTarget": 40})
        latest = D.latest_user_db("real", user)
        self.assertEqual(latest["targetedConfig"]["rewardImage"], "_assets/pipa-dance.webp")
        self.assertEqual(latest["targetedConfig"]["completionImage"], "_assets/pipa_no_wand_clap_jump_fixed.webp")

    def test_edit_with_no_file_errors(self):
        res = D.edit_targeted_config("real", "Nobody", {"targets": ["1+1"]})
        self.assertFalse(res["ok"])
        self.assertEqual(res["error"], "no-file")

    def test_save_run_persists_targeted_config(self):
        user = self._seed_source_file("K2")
        d = tempfile.mkdtemp()
        p = os.path.join(d, "s2.sqlite")
        make_db(p, user, "s2", [(2, 2)])
        raw = Path(p).read_bytes()
        r = D.save_run("real", "source", user, "2026-06-21_100000", "", raw, force_new=False,
                       targeted_config={"targets": ["2+8", "2+7", "2+5"], "filler": ["0+1"],
                                        "graduationStreak": 4, "fastMs": 1800, "percentTarget": 70})
        self.assertTrue(r["ok"])
        self.assertEqual(r["targetedConfig"]["targets"], ["2+8", "2+7", "2+5"])
        # and it's readable on the next load
        latest = D.latest_user_db("real", user)
        self.assertEqual(latest["targetedConfig"]["graduationStreak"], 4)
        self.assertEqual(latest["targetedConfig"]["percentTarget"], 70)


if __name__ == "__main__":
    unittest.main()
