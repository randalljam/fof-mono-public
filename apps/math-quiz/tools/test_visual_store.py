#!/usr/bin/env python3
"""Tests for visual_store (per-user visual-practice config in the .sqlite) plus the
dev-server /api/visual-config endpoints + save_run persistence. Stdlib sqlite3 only."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(__file__))
import visual_store as V  # noqa: E402
import dev_server as D  # noqa: E402
from test_anchor_store import make_db  # noqa: E402


class NormalizeTests(unittest.TestCase):
    def test_normalize_fact_whitespace_and_symbols(self):
        self.assertEqual(V.normalize_fact("3+6"), "3+6")
        self.assertEqual(V.normalize_fact("  3 + 6 "), "3+6")
        self.assertEqual(V.normalize_fact("8x7"), "8*7")
        self.assertEqual(V.normalize_fact("8×7"), "8*7")
        self.assertEqual(V.normalize_fact("6+0"), "6+0")     # orientation preserved
        self.assertEqual(V.normalize_fact("3+6", spaced=True), "3 + 6")   # filler form has spaces
        self.assertEqual(V.normalize_fact("  3+6 ", spaced=True), "3 + 6")
        self.assertIsNone(V.normalize_fact("hello"))
        self.assertIsNone(V.normalize_fact(""))

    def test_normalize_facts_list_and_text(self):
        self.assertEqual(V.normalize_facts(["3+6", "", " 8 + 7 ", "junk"]), ["3+6", "8+7"])
        self.assertEqual(V.normalize_facts("6+0\n0+6\n3+3", spaced=True), ["6 + 0", "0 + 6", "3 + 3"])  # filler keeps dupes/orientation


class StoreTests(unittest.TestCase):
    def _db(self):
        d = tempfile.mkdtemp()
        return os.path.join(d, "s.sqlite")

    def test_get_empty_is_none(self):
        conn = V.connect(self._db())
        try:
            self.assertIsNone(V.get_config(conn, "Kid1"))
        finally:
            conn.close()
    def test_get_corrupt_json_degrades_to_empty_lists(self):
        conn = V.connect(self._db())
        try:
            V.ensure_visual_schema(conn)
            conn.execute(
                "INSERT INTO VisualPracticeConfig(user_name, targets_json, filler_json) "
                "VALUES (?, ?, ?)", ("Kid1", "{bad", '"not-a-list"'))
            conn.commit()
            cfg = V.get_config(conn, "Kid1")
            self.assertEqual(cfg["targets"], [])
            self.assertEqual(cfg["filler"], [])
        finally:
            conn.close()

    def test_set_then_get_roundtrip_caps_and_clamps(self):
        conn = V.connect(self._db())
        try:
            cfg = V.set_config(conn, "Kid1",
                               targets=["8+3", "4+9", "6+8", "3+7", "3+4", "1+1"],  # 6 -> capped to 5
                               filler=["0+1", "6+0", "0+6"],
                               fast_ms=2000, retrievals_to_clear=2, hesitation_ms=6000)
            self.assertEqual(cfg["targets"], ["8+3", "4+9", "6+8", "3+7", "3+4"])   # compact
            self.assertEqual(cfg["filler"], ["0 + 1", "6 + 0", "0 + 6"])            # spaced
            self.assertEqual((cfg["fastMs"], cfg["retrievalsToClear"], cfg["hesitationMs"]), (2000, 2, 6000))
            # clamp out-of-range params
            cfg = V.set_config(conn, "Kid1", fast_ms=10, retrievals_to_clear=99, hesitation_ms=-5)
            self.assertEqual(cfg["fastMs"], 200)              # clamped to [200,60000]
            self.assertEqual(cfg["retrievalsToClear"], 9)     # clamped to [1,9]
            self.assertEqual(cfg["hesitationMs"], 0)          # clamped to [0,60000]
        finally:
            conn.close()

    def test_partial_update_keeps_existing(self):
        conn = V.connect(self._db())
        try:
            V.set_config(conn, "K2", targets=["2+8", "2+7"], filler=["0+1"], retrievals_to_clear=3)
            cfg = V.set_config(conn, "K2", filler=["1+1", "2+2"])   # only filler changes
            self.assertEqual(cfg["targets"], ["2+8", "2+7"])         # preserved
            self.assertEqual(cfg["filler"], ["1 + 1", "2 + 2"])      # spaced
            self.assertEqual(cfg["retrievalsToClear"], 3)             # preserved
        finally:
            conn.close()

    def test_defaults_on_first_write(self):
        conn = V.connect(self._db())
        try:
            cfg = V.set_config(conn, "Kid1", targets=["8+3"])
            self.assertEqual(cfg["targets"], ["8+3"])
            self.assertEqual(cfg["fastMs"], V.DEFAULT_FAST_MS)
            self.assertEqual(cfg["retrievalsToClear"], V.DEFAULT_RETRIEVALS_TO_CLEAR)
            self.assertEqual(cfg["hesitationMs"], V.DEFAULT_HESITATION_MS)
        finally:
            conn.close()


class DevServerVisualConfig(unittest.TestCase):
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
        res = D.edit_visual_config("real", user, {
            "targets": ["8+3", "4+9", "6+8", "3+7", "3+4"],
            "filler": ["0+1", "1+1", "2+2"],
            "fastMs": 2000, "retrievalsToClear": 2, "hesitationMs": 6000})
        self.assertTrue(res["ok"])
        self.assertEqual(res["visualConfig"]["targets"], ["8+3", "4+9", "6+8", "3+7", "3+4"])
        # view endpoint reads it back (filler stored in the spaced "a + b" form)
        view = D.visual_config_view("real", user)
        self.assertEqual(view["visualConfig"]["filler"], ["0 + 1", "1 + 1", "2 + 2"])
        # latest-user-db carries it for the page prefill
        latest = D.latest_user_db("real", user)
        self.assertEqual(latest["visualConfig"]["retrievalsToClear"], 2)
        self.assertEqual(latest["targetedConfig"], None)

    def test_edit_with_no_file_errors(self):
        res = D.edit_visual_config("real", "Nobody", {"targets": ["1+1"]})
        self.assertFalse(res["ok"])
        self.assertEqual(res["error"], "no-file")

    def test_save_run_persists_visual_config(self):
        user = self._seed_source_file("K2")
        d = tempfile.mkdtemp()
        p = os.path.join(d, "s2.sqlite")
        make_db(p, user, "s2", [(2, 2)])
        raw = Path(p).read_bytes()
        r = D.save_run("real", "source", user, "2026-06-21_100000", "", raw, force_new=False,
                       visual_config={"targets": ["2+8", "2+7", "2+5"], "filler": ["0+1"],
                                      "fastMs": 1800, "retrievalsToClear": 3, "hesitationMs": 5000})
        self.assertTrue(r["ok"])
        self.assertEqual(r["visualConfig"]["targets"], ["2+8", "2+7", "2+5"])
        # and it's readable on the next load
        latest = D.latest_user_db("real", user)
        self.assertEqual(latest["visualConfig"]["fastMs"], 1800)
        self.assertEqual(latest["visualConfig"]["retrievalsToClear"], 3)
        self.assertEqual(latest["visualConfig"]["hesitationMs"], 5000)
    def test_save_run_reports_visual_config_write_failure(self):
        user = self._seed_source_file("K2")
        d = tempfile.mkdtemp()
        p = os.path.join(d, "s2.sqlite")
        make_db(p, user, "s2", [(2, 2)])
        raw = Path(p).read_bytes()
        with mock.patch.object(D.visual_store, "set_config", side_effect=RuntimeError("disk full")):
            result = D.save_run(
                "real", "source", user, "2026-06-21_100000", "", raw,
                force_new=False, visual_config={"targets": ["2+8"]})
        self.assertTrue(result["ok"])
        self.assertEqual(result["visualConfig"]["error"], "disk full")


if __name__ == "__main__":
    unittest.main()
