#!/usr/bin/env python3
"""Tests for tools/ingest_drop_folder.py (drop-folder ingest into per-person files). Stdlib only."""
import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import ingest_drop_folder as I  # noqa: E402
from test_anchor_store import make_db  # noqa: E402

def drop(folder, filename, user, session_id, problems):
    """Write a single-session .sqlite into `folder` under `filename`; return its path."""
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, filename)
    make_db(path, user, session_id, problems)
    return path

class IdentityTests(unittest.TestCase):
    def test_identity_from_filename(self):
        d = tempfile.mkdtemp()
        p = drop(d, "math-quest_K1_2026-06-19_143000.sqlite", "Kid1", "s1", [(2, 3)])
        name, stamp = I.extract_identity(p, os.path.basename(p), "math-quest")
        self.assertEqual((name, stamp), ("Kid1", "2026-06-19_143000"))

    def test_identity_falls_back_to_db(self):
        # A non-conforming filename -> read user_name + start_time from the Sessions row.
        d = tempfile.mkdtemp()
        p = drop(d, "world_42_export.sqlite", "K2", "s9", [(1, 1)])
        name, stamp = I.extract_identity(p, os.path.basename(p), "math-quest")
        self.assertEqual(name, "K2")
        self.assertEqual(stamp, "2026-06-19_120000")  # make_db's start_time

    def test_normalize_stamp_handles_iso_and_space(self):
        self.assertEqual(I._normalize_stamp("2026-06-19T14:30:00", 0), "2026-06-19_143000")
        self.assertEqual(I._normalize_stamp("2026-06-19 14:30:00", 0), "2026-06-19_143000")
        self.assertEqual(I._normalize_stamp("2026-06-19_143000", 0), "2026-06-19_143000")

class IngestTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.data = os.path.join(self.root, "_data")
        self.drop = os.path.join(self.data, I.DROP_SUBDIR)
        os.makedirs(self.drop, exist_ok=True)

    def _ingest(self, **kw):
        kw.setdefault("data_dir", self.data)
        kw.setdefault("dest_folder", "test")
        kw.setdefault("source_prefix", "math-quest")
        kw.setdefault("output_prefix", "math-quest")
        return I.ingest_folder(**kw)

    def test_prefix_filters_out_other_apps(self):
        # The drop folder is shared: a math-flu (anchor) file must be ignored, math-quest ingested.
        drop(self.drop, "math-flu_K1_2026-06-19_120000.sqlite", "Kid1", "anchor", [(1, 1)])
        drop(self.drop, "math-quest_K1_2026-06-19_130000.sqlite", "Kid1", "mq1", [(2, 2)])
        s = self._ingest()
        self.assertEqual(s["ingested"], 1)
        files = sorted(os.listdir(os.path.join(self.data, "test")))
        self.assertEqual(files, ["math-quest_K1_2026-06-19_130000.sqlite"])

    def test_two_drops_accumulate_into_one_person_file(self):
        drop(self.drop, "math-quest_K1_2026-06-19_120000.sqlite", "Kid1", "mq1", [(2, 2)])
        drop(self.drop, "math-quest_K1_2026-06-20_120000.sqlite", "Kid1", "mq2", [(3, 3)])
        s = self._ingest()
        self.assertEqual(s["ingested"], 2)
        dest = os.path.join(self.data, "test")
        # Second drop continues the lineage -> single renamed to the multi (date-only) form.
        self.assertTrue(os.path.exists(os.path.join(dest, "math-quest_K1_2026-06-19.sqlite")))
        self.assertFalse(os.path.exists(os.path.join(dest, "math-quest_K1_2026-06-19_120000.sqlite")))
        c = sqlite3.connect(os.path.join(dest, "math-quest_K1_2026-06-19.sqlite"))
        self.assertEqual(c.execute("SELECT COUNT(*) FROM Sessions").fetchone()[0], 2)
        c.close()

    def test_separate_people_get_separate_files(self):
        drop(self.drop, "math-quest_K1_2026-06-19_120000.sqlite", "Kid1", "i1", [(2, 2)])
        drop(self.drop, "math-quest_Max_2026-06-19_120000.sqlite", "K2", "m1", [(3, 3)])
        self._ingest()
        files = sorted(os.listdir(os.path.join(self.data, "test")))
        self.assertEqual(files, ["math-quest_K1_2026-06-19_120000.sqlite",
                                 "math-quest_Max_2026-06-19_120000.sqlite"])

    def test_ledger_skips_unchanged_rerun(self):
        drop(self.drop, "math-quest_K1_2026-06-19_120000.sqlite", "Kid1", "mq1", [(2, 2)])
        first = self._ingest()
        self.assertEqual(first["ingested"], 1)
        second = self._ingest()                      # same file, no change
        self.assertEqual(second["ingested"], 0)
        self.assertEqual(second["skipped"], 1)
        self.assertTrue(os.path.exists(first["ledger"]))

    def test_force_reprocesses_but_stays_idempotent(self):
        drop(self.drop, "math-quest_K1_2026-06-19_120000.sqlite", "Kid1", "mq1", [(2, 2)])
        self._ingest()
        forced = self._ingest(force=True)            # reprocess, but append_session dedups
        self.assertEqual(forced["ingested"], 1)
        self.assertEqual(forced["results"][0]["added"], 0)

    def test_dest_switch_uses_independent_ledger(self):
        # The same drop ingests into both 'test' and 'tlkids' (ledgers are per-destination).
        drop(self.drop, "math-quest_K1_2026-06-19_120000.sqlite", "Kid1", "mq1", [(2, 2)])
        t = self._ingest(dest_folder="test")
        live = self._ingest(dest_folder="tlkids")
        self.assertEqual(t["ingested"], 1)
        self.assertEqual(live["ingested"], 1)         # not falsely skipped by test's ledger
        self.assertNotEqual(t["ledger"], live["ledger"])
        self.assertTrue(os.path.exists(os.path.join(self.data, "tlkids", "math-quest_K1_2026-06-19_120000.sqlite")))

    def test_dry_run_writes_nothing(self):
        drop(self.drop, "math-quest_K1_2026-06-19_120000.sqlite", "Kid1", "mq1", [(2, 2)])
        s = self._ingest(dry_run=True)
        self.assertEqual(s["results"][0]["action"], "would-ingest")
        self.assertFalse(os.path.exists(os.path.join(self.data, "test")))
        self.assertFalse(os.path.exists(s["ledger"]))

    def test_empty_prefix_matches_any_sqlite(self):
        drop(self.drop, "anything.sqlite", "TL", "t1", [(5, 5)])
        s = self._ingest(source_prefix="")
        self.assertEqual(s["ingested"], 1)
        self.assertTrue(os.path.exists(os.path.join(self.data, "test", "math-quest_TL_2026-06-19_120000.sqlite")))

    def test_source_files_left_in_place(self):
        src = drop(self.drop, "math-quest_K1_2026-06-19_120000.sqlite", "Kid1", "mq1", [(2, 2)])
        self._ingest()
        self.assertTrue(os.path.exists(src))          # ingest never moves/deletes the drop

if __name__ == "__main__":
    unittest.main()
