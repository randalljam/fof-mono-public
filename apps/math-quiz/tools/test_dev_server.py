#!/usr/bin/env python3
"""Integration tests for dev_server.save_run source->destination routing (S3 disabled).

Exercises destination 'source' (Start New create -> Continue append, incl. a custom source
folder) and destination 'test' (Continue seeds a multi-session trial from the source's
latest; Start New writes a fresh single-session trial). "Continue latest" with no existing
file is an error. S3 is stubbed to raise; only the local mirror runs. Stdlib sqlite3 only.
"""
import base64
import http.server
import os
import sqlite3
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(__file__))
import dev_server as D  # noqa: E402
import problem_list_store as P  # noqa: E402
from test_anchor_store import make_db  # noqa: E402


def session_bytes(user, session_id, problems):
    d = tempfile.mkdtemp()
    p = os.path.join(d, "s.sqlite")
    make_db(p, user, session_id, problems)
    return Path(p).read_bytes()


def add_internal_list(path, user, list_name, problems_text, retain=True):
    """Add an internal problem list to an on-disk source file; return its problem_list_id."""
    conn = P.connect(str(path))
    try:
        out = P.add_problem_list(conn, user_name=user, list_name=list_name, source="test",
                                 problems=P.parse_problem_list_text(problems_text), retain=retain)
    finally:
        conn.close()
    return out["problem_list_id"]


class DevServerRouting(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.backup_tmp = self.tmp.parent / f"{self.tmp.name}_backups"
        D.DATA_DIR = self.tmp                    # redirect the local mirror
        D.BACKUP_ROOT = self.backup_tmp          # redirect external append snapshots
        D._s3 = lambda: (_ for _ in ()).throw(RuntimeError("no s3 in test"))  # force local-only path
        # Isolate learner display-name aliases (local display_names.json may map Kid1→a display name).
        self._display_names_file = D.dragon_display_names.DISPLAY_NAMES_FILE
        self._display_names_cache = D.dragon_display_names._cache
        D.dragon_display_names.DISPLAY_NAMES_FILE = self.tmp / "display_names.json"
        D.dragon_display_names._cache = None
    def tearDown(self):
        D.dragon_display_names.DISPLAY_NAMES_FILE = self._display_names_file
        D.dragon_display_names._cache = self._display_names_cache

    def _count(self, path, table):
        c = sqlite3.connect(path)
        n = c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        c.close()
        return n

    def test_continue_with_no_source_file_errors(self):
        # The first file for a person must be Start New; a plain Continue with no file errors.
        r = D.save_run("real", "source", "Ghost", "2026-06-20_090000", "", session_bytes("Ghost", "g1", [(1, 1)]))
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"], "no-continue-file")
        self.assertFalse((self.tmp / "real").exists())   # nothing written

    def test_start_new_then_continue_append_renames_to_multi(self):
        r1 = D.save_run("real", "source", "Randy", "2026-06-19_120000", "",
                        session_bytes("Randy", "s1", [(3, 4), (5, 6)]), force_new=True)
        self.assertEqual(r1["action"], "create")
        self.assertEqual(r1["filename"], "math-flu_Randy_2026-06-19_120000.sqlite")
        self.assertTrue((self.tmp / "real" / r1["filename"]).exists())

        r2 = D.save_run("real", "source", "Randy", "2026-06-20_090000", "", session_bytes("Randy", "s2", [(7, 8)]))
        self.assertEqual(r2["action"], "append")
        self.assertEqual(r2["target"], "math-flu_Randy_2026-06-19_120000.sqlite")
        self.assertEqual(r2["filename"], "math-flu_Randy_2026-06-19.sqlite")  # time dropped
        multi = self.tmp / "real" / r2["filename"]
        self.assertEqual(self._count(multi, "Sessions"), 2)
        self.assertEqual(self._count(multi, "ProblemAttempts"), 3)
        self.assertFalse((self.tmp / "real" / "math-flu_Randy_2026-06-19_120000.sqlite").exists())

    def test_continue_append_backs_up_source_file_before_changing_it(self):
        # A Continue append to a source file first copies the existing (pre-change) file into
        # BACKUP_ROOT/<stem>_backup_<stamp><ext>, so a bad run can always be rolled back.
        D.save_run("real", "source", "Kid1", "2026-06-19_120000", "",
                   session_bytes("Kid1", "s1", [(1, 1), (2, 2)]), force_new=True)   # create (no backup)
        self.assertFalse(self.backup_tmp.exists())                                  # nothing backed up on create

        r = D.save_run("real", "source", "Kid1", "2026-06-20_093015", "", session_bytes("Kid1", "s2", [(3, 3)]))
        self.assertEqual(r["action"], "append")
        # The backup is reported and lands in BACKUP_ROOT with the run's stamp appended.
        self.assertIn("backup", r)
        backup = Path(r["backup"])
        self.assertTrue(backup.exists())
        self.assertEqual(backup.parent, self.backup_tmp)
        self.assertEqual(backup.name, "math-flu_K1_2026-06-19_120000_backup_2026-06-20_093015.sqlite")
        self.assertIn("backupS3Error", r)   # local backup still succeeds when S3 is unavailable
        # The backup is the PRE-change file (1 session); the live file now has 2.
        self.assertEqual(self._count(str(backup), "Sessions"), 1)
        self.assertEqual(self._count(str(self.tmp / "real" / r["filename"]), "Sessions"), 2)

    def test_create_does_not_write_a_backup(self):
        # Start New (create) has no pre-existing file to back up.
        r = D.save_run("real", "source", "Newbie", "2026-06-20_090000", "",
                       session_bytes("Newbie", "s1", [(1, 1)]), force_new=True)
        self.assertEqual(r["action"], "create")
        self.assertNotIn("backup", r)
        self.assertFalse(self.backup_tmp.exists())

    def test_destination_test_continue_seeds_multisession_from_source(self):
        # KEY BUG FIX: a Continue test run seeds from the source's latest file and APPENDS,
        # producing a multi-session file in the dated test subfolder — not a fresh single.
        D.save_run("real", "source", "Kid1", "2026-06-19_100000", "", session_bytes("Kid1", "r1", [(2, 2)]), force_new=True)
        D.save_run("real", "source", "Kid1", "2026-06-19_110000", "", session_bytes("Kid1", "r2", [(3, 3)]))  # -> multi (2)
        rt = D.save_run("real", "test", "Kid1", "2026-06-21_140000", "iPad keypad", session_bytes("Kid1", "t1", [(9, 9)]))
        self.assertEqual(rt["action"], "test-run")
        self.assertEqual(rt["subfolder"], "test_2026-06-21_140000_ipad-keypad")
        self.assertEqual(rt["seededFrom"], "math-flu_K1_2026-06-19.sqlite")    # source's latest (multi)
        self.assertEqual(rt["filename"], "math-flu_K1_2026-06-19.sqlite")      # multi name, not a timestamped single
        out = Path(rt["localPath"])
        self.assertEqual(self._count(out, "Sessions"), 3)                        # 2 from source + the trial
        # the source real file is untouched (still 2 sessions)
        self.assertEqual(self._count(self.tmp / "real" / "math-flu_K1_2026-06-19.sqlite", "Sessions"), 2)

    def test_destination_test_start_new_writes_single_session_trial(self):
        rt = D.save_run("real", "test", "Kid1", "2026-06-21_140000", "fresh",
                        session_bytes("Kid1", "t1", [(9, 9)]), force_new=True)
        self.assertEqual(rt["action"], "test-run")
        self.assertNotIn("seededFrom", rt)
        self.assertEqual(rt["filename"], "math-flu_K1_2026-06-21_140000.sqlite")  # individual (timestamped)
        self.assertEqual(self._count(Path(rt["localPath"]), "Sessions"), 1)

    def test_force_new_starts_a_second_lineage_not_appending(self):
        D.save_run("real", "source", "Kid", "2026-06-20_090000", "", session_bytes("Kid", "a1", [(1, 1)]), force_new=True)
        D.save_run("real", "source", "Kid", "2026-06-20_100000", "", session_bytes("Kid", "a2", [(2, 2)]))  # -> bare multi
        r = D.save_run("real", "source", "Kid", "2026-06-20_110000", "", session_bytes("Kid", "b1", [(3, 3)]), force_new=True)
        self.assertEqual(r["action"], "create")
        self.assertEqual(r["filename"], "math-flu_Kid_2026-06-20_110000.sqlite")
        self.assertTrue((self.tmp / "real" / "math-flu_Kid_2026-06-20.sqlite").exists())  # lineage #1 untouched

    def test_same_day_start_new_then_continue_suffixes_to_2(self):
        # Randy's walkthrough end-to-end: an accumulated lineage exists today; a later same-day
        # Start New makes a second lineage; the next Continue appends into the newer lineage and
        # the single->multi rename lands on _2 so it never overwrites the first.
        D.save_run("real", "source", "Kid", "2026-06-20_090000", "", session_bytes("Kid", "a1", [(1, 1)]), force_new=True)
        D.save_run("real", "source", "Kid", "2026-06-20_100000", "", session_bytes("Kid", "a2", [(2, 2)]))
        bare = self.tmp / "real" / "math-flu_Kid_2026-06-20.sqlite"
        D.save_run("real", "source", "Kid", "2026-06-20_110000", "", session_bytes("Kid", "b1", [(3, 3)]), force_new=True)
        single2 = self.tmp / "real" / "math-flu_Kid_2026-06-20_110000.sqlite"
        os.utime(bare, (1000, 1000))
        os.utime(single2, (2000, 2000))
        r = D.save_run("real", "source", "Kid", "2026-06-20_120000", "", session_bytes("Kid", "b2", [(4, 4)]))
        self.assertEqual(r["action"], "append")
        self.assertEqual(r["target"], "math-flu_Kid_2026-06-20_110000.sqlite")  # the newer lineage
        self.assertEqual(r["filename"], "math-flu_Kid_2026-06-20_2.sqlite")     # suffixed, no collision
        suffixed = self.tmp / "real" / "math-flu_Kid_2026-06-20_2.sqlite"
        self.assertEqual(self._count(suffixed, "Sessions"), 2)
        self.assertTrue(bare.exists())
        self.assertEqual(self._count(bare, "Sessions"), 2)

    def test_latest_user_db_returns_newest_with_count(self):
        D.save_run("real", "source", "Kid", "2026-06-19_120000", "", session_bytes("Kid", "s1", [(1, 1), (2, 2)]), force_new=True)
        D.save_run("real", "source", "Kid", "2026-06-20_120000", "", session_bytes("Kid", "s2", [(3, 3)]))  # -> bare multi
        res = D.latest_user_db("real", "Kid")
        self.assertTrue(res["found"])
        self.assertEqual(res["filename"], "math-flu_Kid_2026-06-19.sqlite")
        self.assertEqual(res["sessionCount"], 2)
        raw = base64.b64decode(res["base64"])
        self.assertTrue(raw.startswith(b"SQLite format 3"))
    def test_save_run_appends_to_explicit_source_lineage(self):
        old = D.save_run("real", "source", "Kid", "2026-06-19_120000", "",
                         session_bytes("Kid", "old", [(1, 1)]), force_new=True)
        newer = D.save_run("real", "source", "Kid", "2026-06-20_120000", "",
                           session_bytes("Kid", "newer", [(2, 2)]), force_new=True)
        nested = self.tmp / "real" / "old-trial" / old["filename"]
        nested.parent.mkdir(parents=True)
        nested.write_bytes(session_bytes("Kid", "nested", [(9, 9)]))
        os.utime(nested, (3000, 3000))
        result = D.save_run(
            "real", "source", "Kid", "2026-06-21_120000", "",
            session_bytes("Kid", "followup", [(3, 3)]), source_file=old["filename"])
        self.assertEqual(result["target"], old["filename"])
        self.assertEqual(result["filename"], "math-flu_Kid_2026-06-19.sqlite")
        self.assertEqual(self._count(self.tmp / "real" / result["filename"], "Sessions"), 2)
        self.assertEqual(self._count(self.tmp / "real" / newer["filename"], "Sessions"), 1)
        conn = sqlite3.connect(self.tmp / "real" / result["filename"])
        try:
            ids = {row[0] for row in conn.execute("SELECT session_id FROM Sessions")}
        finally:
            conn.close()
        self.assertEqual(ids, {"old", "followup"})

    def test_latest_user_db_none_for_unknown_user(self):
        D.save_run("real", "source", "Kid", "2026-06-19_120000", "", session_bytes("Kid", "s1", [(1, 1)]), force_new=True)
        self.assertFalse(D.latest_user_db("real", "Nobody")["found"])

    def test_latest_user_db_loads_explicit_filename(self):
        r1 = D.save_run("real", "source", "Kid", "2026-06-19_120000", "", session_bytes("Kid", "s1", [(1, 1)]), force_new=True)
        r2 = D.save_run("real", "source", "Kid", "2026-06-20_120000", "", session_bytes("Kid", "s2", [(3, 3)]))
        self.assertEqual(r2["filename"], "math-flu_Kid_2026-06-19.sqlite")
        res = D.latest_user_db("real", "Kid", filename=r2["filename"])
        self.assertTrue(res["found"])
        self.assertEqual(res["filename"], "math-flu_Kid_2026-06-19.sqlite")
        self.assertEqual(res["sessionCount"], 2)
    def test_explicit_top_level_filename_wins_over_newer_nested_copy(self):
        fn = "math-flu_Kid_2026-06-19_120000.sqlite"
        top = self.tmp / "real" / fn
        nested = self.tmp / "real" / "old-trial" / fn
        nested.parent.mkdir(parents=True)
        top.write_bytes(session_bytes("Kid", "top", [(1, 1)]))
        nested.write_bytes(session_bytes("Kid", "nested", [(9, 9)]))
        os.utime(top, (1000, 1000))
        os.utime(nested, (2000, 2000))
        self.assertEqual(D._resolve_user_db_path("real", "Kid", filename=fn), top)
        self.assertEqual(D._local_find("real", fn), top)

    def test_latest_user_db_loads_explicit_test_subfolder(self):
        rt = D.save_run("real", "test", "Kid1", "2026-06-21_140000", "ipad", session_bytes("Kid1", "t1", [(9, 9)]), force_new=True)
        res = D.latest_user_db("test", "Kid1", filename=rt["filename"], subfolder=rt["subfolder"])
        self.assertTrue(res["found"])
        self.assertEqual(res["filename"], rt["filename"])
        self.assertEqual(res["subfolder"], rt["subfolder"])
        self.assertEqual(res["sessionCount"], 1)
    def test_practice_config_edits_target_explicit_file(self):
        old = D.save_run("real", "source", "Kid", "2026-06-19_120000", "",
                         session_bytes("Kid", "old", [(1, 1)]), force_new=True)
        newer = D.save_run("real", "source", "Kid", "2026-06-20_120000", "",
                           session_bytes("Kid", "newer", [(2, 2)]), force_new=True)
        targeted = D.edit_targeted_config(
            "real", "Kid", {"file": old["filename"], "targets": ["3+4"]})
        visual = D.edit_visual_config(
            "real", "Kid", {"file": old["filename"], "targets": ["8+3"]})
        self.assertEqual(targeted["file"], old["filename"])
        self.assertEqual(visual["file"], old["filename"])
        self.assertEqual(
            D.targeted_config_view("real", "Kid", filename=old["filename"])["targetedConfig"]["targets"],
            ["3+4"])
        self.assertEqual(
            D.visual_config_view("real", "Kid", filename=old["filename"])["visualConfig"]["targets"],
            ["8+3"])
        self.assertIsNone(
            D.targeted_config_view("real", "Kid", filename=newer["filename"])["targetedConfig"])
        self.assertIsNone(
            D.visual_config_view("real", "Kid", filename=newer["filename"])["visualConfig"])

    def test_destination_source_uses_a_custom_source_folder(self):
        r1 = D.save_run("Kid1-practice", "source", "Kid1", "2026-06-20_090000", "",
                        session_bytes("Kid1", "p1", [(1, 1)]), force_new=True)
        self.assertEqual(r1["action"], "create")
        self.assertEqual(r1["sourceFolder"], "Kid1-practice")
        self.assertTrue((self.tmp / "Kid1-practice" / "math-flu_K1_2026-06-20_090000.sqlite").exists())
        r2 = D.save_run("Kid1-practice", "source", "Kid1", "2026-06-20_100000", "", session_bytes("Kid1", "p2", [(2, 2)]))
        self.assertEqual(r2["action"], "append")
        self.assertEqual(self._count(self.tmp / "Kid1-practice" / "math-flu_K1_2026-06-20.sqlite", "Sessions"), 2)
        self.assertFalse((self.tmp / "real").exists())   # real never created

    def test_source_folder_with_spaces_is_preserved(self):
        # 'TL kids' must resolve to _data/TL kids/ (the _safe_folder fix), not be stripped.
        self.assertEqual(D._safe_folder("TL kids"), "TL kids")
        self.assertEqual(D._safe_folder("../etc"), "")        # traversal rejected
        r = D.save_run("TL kids", "source", "Kid1", "2026-06-20_090000", "",
                       session_bytes("Kid1", "p1", [(1, 1)]), force_new=True)
        self.assertEqual(r["action"], "create")
        self.assertTrue((self.tmp / "TL kids" / "math-flu_K1_2026-06-20_090000.sqlite").exists())
        self.assertTrue(D.latest_user_db("TL kids", "Kid1")["found"])   # Continue/auto-load finds it

    def test_single_session_file_always_archived(self):
        r1 = D.save_run("real", "source", "Kid", "2026-06-20_090000", "",
                        session_bytes("Kid", "s1", [(1, 1)]), force_new=True)
        p1 = self.tmp / "_single-session-sqlite-files" / "math-flu_Kid_2026-06-20_090000.sqlite"
        self.assertTrue(p1.exists())
        self.assertEqual(r1["singleSessionPath"], str(p1))
        self.assertEqual(r1["singleSessionFile"], "math-flu_Kid_2026-06-20_090000.sqlite")
        self.assertIn("singleSessionS3Error", r1)   # local archive still succeeds when S3 is unavailable
        self.assertNotIn("_single-session-sqlite-files", D.data_folders())   # not a source-folder choice
        # also archived on a Continue append, and on a destination=test trial
        D.save_run("real", "source", "Kid", "2026-06-20_100000", "", session_bytes("Kid", "s2", [(2, 2)]))
        self.assertTrue((self.tmp / "_single-session-sqlite-files" / "math-flu_Kid_2026-06-20_100000.sqlite").exists())
        D.save_run("real", "test", "Kid", "2026-06-20_110000", "ipad", session_bytes("Kid", "t1", [(3, 3)]))
        self.assertTrue((self.tmp / "_single-session-sqlite-files" / "math-flu_Kid_2026-06-20_110000.sqlite").exists())

    def test_single_session_archived_even_on_no_continue_error(self):
        r = D.save_run("real", "source", "Ghost", "2026-06-20_090000", "", session_bytes("Ghost", "g1", [(1, 1)]))
        self.assertFalse(r["ok"])   # no file to continue
        self.assertTrue((self.tmp / "_single-session-sqlite-files" / "math-flu_Ghost_2026-06-20_090000.sqlite").exists())

    def test_data_folders_lists_real_test_and_custom(self):
        D.save_run("Kid1-practice", "source", "Kid1", "2026-06-20_090000", "",
                   session_bytes("Kid1", "p1", [(1, 1)]), force_new=True)
        folders = D.data_folders()
        self.assertIn("real", folders)
        self.assertIn("test", folders)
        self.assertIn("Kid1-practice", folders)
        self.assertNotIn("local-only", folders)   # internal backup folder excluded

    def test_default_save_makes_no_live_file_s3_upload_and_no_local_only(self):
        r = D.save_run("real", "source", "Kid", "2026-06-20_090000", "",
                       session_bytes("Kid", "s1", [(1, 1)]), force_new=True)
        self.assertNotIn("s3Uri", r)
        self.assertNotIn("s3Error", r)
        self.assertTrue((self.tmp / "real" / r["filename"]).exists())
        self.assertFalse((self.tmp / "local-only").exists())

    def test_latest_user_db_includes_problem_lists(self):
        D.save_run("real", "source", "K2", "2026-06-19_120000", "",
                   session_bytes("K2", "s1", [(1, 1)]), force_new=True)
        src = self.tmp / "real" / "math-flu_K2_2026-06-19_120000.sqlite"
        add_internal_list(src, "K2", "List A", "8 + 2\n3 + 4\n")
        add_internal_list(src, "K2", "List B", "5 + 5\n", retain=False)
        res = D.latest_user_db("real", "K2")
        lists = res["problemLists"]
        self.assertEqual([l["list_name"] for l in lists], ["List A", "List B"])
        self.assertEqual([l["list_order"] for l in lists], [1, 2])
        self.assertEqual((lists[0]["retain"], lists[1]["retain"]), (1, 0))
        self.assertEqual(lists[0]["items"][0]["num1"], 8)   # parsed nums travel to the browser

    def test_consume_nonretained_list_on_source_append(self):
        # "Use internal" ran a non-retained list: filing the run pops it off the source file.
        D.save_run("real", "source", "K2", "2026-06-19_120000", "",
                   session_bytes("K2", "s1", [(1, 1)]), force_new=True)
        single = self.tmp / "real" / "math-flu_K2_2026-06-19_120000.sqlite"
        lid = add_internal_list(single, "K2", "Run me", "8 + 2\n", retain=False)
        r = D.save_run("real", "source", "K2", "2026-06-20_090000", "",
                       session_bytes("K2", "s2", [(2, 2)]), consumed_problem_list_id=lid)
        self.assertEqual(r["action"], "append")
        self.assertEqual(r["consumedProblemList"]["action"], "deleted")
        multi = self.tmp / "real" / "math-flu_K2_2026-06-19.sqlite"
        self.assertEqual(D._problem_lists_for(multi, "K2"), [])     # list popped
        self.assertEqual(self._count(multi, "Sessions"), 2)          # session still filed

    def test_consume_retained_list_bumps_usage(self):
        D.save_run("real", "source", "K2", "2026-06-19_120000", "",
                   session_bytes("K2", "s1", [(1, 1)]), force_new=True)
        single = self.tmp / "real" / "math-flu_K2_2026-06-19_120000.sqlite"
        lid = add_internal_list(single, "K2", "Keep me", "8 + 2\n", retain=True)
        r = D.save_run("real", "source", "K2", "2026-06-20_090000", "",
                       session_bytes("K2", "s2", [(2, 2)]), consumed_problem_list_id=lid)
        self.assertEqual(r["consumedProblemList"]["action"], "retained")
        self.assertEqual(r["consumedProblemList"]["times_used"], 1)
        multi = self.tmp / "real" / "math-flu_K2_2026-06-19.sqlite"
        lists = D._problem_lists_for(multi, "K2")
        self.assertEqual((len(lists), lists[0]["times_used"]), (1, 1))   # kept + usage bumped

    def test_test_destination_does_not_consume_source_lists(self):
        D.save_run("real", "source", "K2", "2026-06-19_100000", "",
                   session_bytes("K2", "r1", [(2, 2)]), force_new=True)
        D.save_run("real", "source", "K2", "2026-06-19_110000", "", session_bytes("K2", "r2", [(3, 3)]))
        multi = self.tmp / "real" / "math-flu_K2_2026-06-19.sqlite"
        lid = add_internal_list(multi, "K2", "Run me", "8 + 2\n", retain=False)
        rt = D.save_run("real", "test", "K2", "2026-06-21_140000", "ipad",
                        session_bytes("K2", "t1", [(9, 9)]), consumed_problem_list_id=lid)
        self.assertEqual(rt["action"], "test-run")
        self.assertNotIn("consumedProblemList", rt)                 # test runs never touch source lists
        self.assertEqual(len(D._problem_lists_for(multi, "K2")), 1)

    def test_problem_lists_view_reads_the_latest_file(self):
        D.save_run("real", "source", "K2", "2026-06-19_120000", "",
                   session_bytes("K2", "s1", [(1, 1)]), force_new=True)
        src = self.tmp / "real" / "math-flu_K2_2026-06-19_120000.sqlite"
        add_internal_list(src, "K2", "List A", "8 + 2\n3 + 4\n")
        view = D.problem_lists_view("real", "K2")
        self.assertTrue(view["found"])
        self.assertEqual(view["file"], "math-flu_K2_2026-06-19_120000.sqlite")
        self.assertEqual(view["problemLists"][0]["list_name"], "List A")
        # No file yet -> found False, empty lists (not an error).
        self.assertEqual(D.problem_lists_view("real", "Ghost"), {
            "ok": True, "found": False, "folder": "real", "user": "Ghost", "problemLists": []})

    def test_edit_create_save_reorder_delete_roundtrip(self):
        D.save_run("real", "source", "K2", "2026-06-19_120000", "",
                   session_bytes("K2", "s1", [(1, 1)]), force_new=True)
        # create two empty lists
        r1 = D.edit_problem_lists("real", "K2", "create", {"listName": "First"})
        self.assertTrue(r1["ok"])
        self.assertEqual(r1["problemLists"][0]["list_name"], "First")
        D.edit_problem_lists("real", "K2", "create", {"listName": "Second"})
        ids = [l["problem_list_id"] for l in D.problem_lists_view("real", "K2")["problemLists"]]
        # fill the first via save-items
        save = D.edit_problem_lists("real", "K2", "save-items", {"problemListId": ids[0], "text": "8 + 2\n3 + 4\n"})
        self.assertEqual([it["problem_text"] for it in save["problemLists"][0]["items"]], ["8 + 2", "3 + 4"])
        # rename + set-retain
        D.edit_problem_lists("real", "K2", "rename", {"problemListId": ids[0], "listName": "Warm set"})
        D.edit_problem_lists("real", "K2", "set-retain", {"problemListId": ids[0], "retain": False})
        # reorder: put Second first
        rr = D.edit_problem_lists("real", "K2", "reorder", {"order": [ids[1], ids[0]]})
        self.assertEqual([l["list_name"] for l in rr["problemLists"]], ["Second", "Warm set"])
        self.assertEqual([l["list_order"] for l in rr["problemLists"]], [1, 2])
        self.assertEqual(rr["problemLists"][1]["retain"], 0)   # set-retain stuck
        # delete Second
        dl = D.edit_problem_lists("real", "K2", "delete", {"problemListId": ids[1]})
        self.assertEqual([l["list_name"] for l in dl["problemLists"]], ["Warm set"])
        self.assertEqual(dl["problemLists"][0]["list_order"], 1)

    def test_edit_persists_to_the_real_file(self):
        D.save_run("real", "source", "K2", "2026-06-19_120000", "",
                   session_bytes("K2", "s1", [(1, 1)]), force_new=True)
        D.edit_problem_lists("real", "K2", "create", {"listName": "Persisted", "text": "5 + 5\n"})
        # A fresh read of the on-disk file sees the new list (auto-saved, not just in memory).
        src = self.tmp / "real" / "math-flu_K2_2026-06-19_120000.sqlite"
        self.assertEqual(D._problem_lists_for(src, "K2")[0]["list_name"], "Persisted")

    def test_edit_targets_the_named_file_not_just_latest(self):
        # The analysis page loads a specific file and passes its name; the edit must land in THAT
        # file (the bug: it went to the folder's latest instead, so the loaded file stayed empty).
        D.save_run("real", "source", "Kid1", "2026-06-17_080000", "",
                   session_bytes("Kid1", "a1", [(1, 1)]), force_new=True)
        time.sleep(0.02)
        D.save_run("real", "source", "Kid1", "2026-06-20_080000", "",
                   session_bytes("Kid1", "b1", [(2, 2)]), force_new=True)   # newer => pick_latest
        old, latest = "math-flu_K1_2026-06-17_080000.sqlite", "math-flu_K1_2026-06-20_080000.sqlite"
        # Target the OLD file explicitly; retain=False (the Fluency-feast shape).
        r = D.edit_problem_lists("real", "Kid1", "create",
                                 {"listName": "Fluency", "text": "2 + 2\n3 + 3", "retain": False, "file": old})
        self.assertTrue(r["ok"])
        self.assertEqual(r["file"], old)
        self.assertEqual(len(D.problem_lists_view("real", "Kid1", filename=old)["problemLists"]), 1)
        self.assertEqual(len(D.problem_lists_view("real", "Kid1", filename=latest)["problemLists"]), 0)
        self.assertEqual(D.problem_lists_view("real", "Kid1", filename=old)["problemLists"][0]["retain"], 0)
        # No file arg -> the latest lineage (anchor's model), unchanged.
        r2 = D.edit_problem_lists("real", "Kid1", "create", {"listName": "Manual", "text": "4 + 4"})
        self.assertEqual(r2["file"], latest)

    def test_fluency_feast_preset_roundtrips_per_file(self):
        D.save_run("real", "source", "Kid1", "2026-06-19_120000", "",
                   session_bytes("Kid1", "s1", [(1, 1)]), force_new=True)
        # Save a preset, then read it back via the view + the latest-user-db field.
        r = D.edit_fluency_feast("real", "Kid1", {
            "count": 12, "session": {"mode": "recentN", "n": 3},
            "mix": {"missing": 40, "incorrect": 40, "almost": 20, "needs-practice": 0, "fluent": 0}})
        self.assertTrue(r["ok"])
        self.assertEqual(r["fluencyFeast"]["count"], 12)
        self.assertEqual(r["fluencyFeast"]["session"]["mode"], "recentN")
        self.assertEqual(r["fluencyFeast"]["mix"]["missing"], 40)
        view = D.fluency_feast_view("real", "Kid1")
        self.assertEqual(view["fluencyFeast"]["count"], 12)
        # The preset rides along on /api/latest-user-db so the kid pop-up can read it.
        latest = D.latest_user_db("real", "Kid1")
        self.assertEqual(latest["fluencyFeast"]["mix"]["incorrect"], 40)
        # Unset file -> None (the page falls back to its code defaults).
        D.save_run("real", "source", "Newbie", "2026-06-19_120000", "",
                   session_bytes("Newbie", "s1", [(1, 1)]), force_new=True)
        self.assertIsNone(D.fluency_feast_view("real", "Newbie")["fluencyFeast"])

    def test_profile_show_fluency_percent_roundtrips_per_file(self):
        D.save_run("real", "source", "Kid1", "2026-06-19_120000", "",
                   session_bytes("Kid1", "s1", [(1, 1)]), force_new=True)
        # Default (no row written yet): shown.
        self.assertTrue(D.profile_view("real", "Kid1")["profile"]["showFluencyPercent"])
        self.assertTrue(D.latest_user_db("real", "Kid1")["profile"]["showFluencyPercent"])
        # Uncheck -> persisted off; reads back off via the view + latest-user-db.
        r = D.edit_profile("real", "Kid1", {"showFluencyPercent": False})
        self.assertTrue(r["ok"])
        self.assertFalse(r["profile"]["showFluencyPercent"])
        self.assertFalse(D.profile_view("real", "Kid1")["profile"]["showFluencyPercent"])
        self.assertFalse(D.latest_user_db("real", "Kid1")["profile"]["showFluencyPercent"])
        # Re-check -> back on.
        self.assertTrue(D.edit_profile("real", "Kid1", {"showFluencyPercent": True})["profile"]["showFluencyPercent"])
        # Unknown user / no file -> default (shown), found=False.
        view = D.profile_view("real", "Newbie")
        self.assertFalse(view["found"])
        self.assertTrue(view["profile"]["showFluencyPercent"])

    def test_profile_edit_targets_the_named_file_not_just_latest(self):
        D.save_run("real", "source", "Kid1", "2026-06-17_080000", "",
                   session_bytes("Kid1", "a1", [(1, 1)]), force_new=True)
        time.sleep(0.02)
        D.save_run("real", "source", "Kid1", "2026-06-20_080000", "",
                   session_bytes("Kid1", "b1", [(2, 2)]), force_new=True)
        old, latest = "math-flu_K1_2026-06-17_080000.sqlite", "math-flu_K1_2026-06-20_080000.sqlite"
        r = D.edit_profile("real", "Kid1", {"showFluencyPercent": False, "file": old})
        self.assertEqual(r["file"], old)
        self.assertFalse(D.profile_view("real", "Kid1", filename=old)["profile"]["showFluencyPercent"])
        # The latest file was untouched (still default shown).
        self.assertTrue(D.profile_view("real", "Kid1", filename=latest)["profile"]["showFluencyPercent"])

    def test_profile_edit_with_no_file_returns_clear_error(self):
        r = D.edit_profile("real", "Ghost", {"showFluencyPercent": False})
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"], "no-file")

    def test_profile_rubric_thresholds_roundtrip_per_file(self):
        D.save_run("real", "source", "Kid1", "2026-06-19_120000", "",
                   session_bytes("Kid1", "s1", [(1, 1)]), force_new=True)
        # Default rubric mirrors the system defaults (minAccuracy as a 0-1 fraction).
        defs = D.profile_view("real", "Kid1")["profile"]["thresholds"]
        self.assertEqual(defs, {"greenMs": 2000, "redMs": 4000, "windowSize": 5, "minAccuracy": 0.8})
        # Save custom thresholds; minAccuracy sent as a percent is stored as a fraction.
        r = D.edit_profile("real", "Kid1", {"thresholds": {"greenMs": 1500, "redMs": 3500, "windowSize": 4, "minAccuracy": 90}})
        self.assertTrue(r["ok"])
        th = r["profile"]["thresholds"]
        self.assertEqual(th["greenMs"], 1500)
        self.assertEqual(th["redMs"], 3500)
        self.assertEqual(th["windowSize"], 4)
        self.assertAlmostEqual(th["minAccuracy"], 0.9)
        # Reads back via the view + latest-user-db; toggling another field keeps the thresholds.
        self.assertEqual(D.latest_user_db("real", "Kid1")["profile"]["thresholds"]["greenMs"], 1500)
        D.edit_profile("real", "Kid1", {"showFluencyPercent": False})
        keep = D.profile_view("real", "Kid1")["profile"]
        self.assertFalse(keep["showFluencyPercent"])
        self.assertEqual(keep["thresholds"]["greenMs"], 1500)

    def test_resolve_editor_target_prefers_source_over_test(self):
        fname = "math-flu_K2_2026-06-16.sqlite"
        (self.tmp / "tlkids").mkdir(parents=True)
        (self.tmp / "test" / "trial_a").mkdir(parents=True)
        make_db(str(self.tmp / "tlkids" / fname), "K2", "s1", [(1, 1), (2, 2), (3, 3)])
        make_db(str(self.tmp / "test" / "trial_a" / fname), "K2", "t1", [(4, 4)])
        r = D.resolve_editor_target("K2", fname)
        self.assertTrue(r["found"])
        self.assertEqual(r["folder"], "tlkids")
        self.assertIn("tlkids", r["relativePath"])

    def test_folder_users_lists_top_level_names_only(self):
        (self.tmp / "tlkids").mkdir(parents=True)
        (self.tmp / "tlkids" / "dragon-gm").mkdir(parents=True)
        make_db(str(self.tmp / "tlkids" / "math-flu_Kid1_2026-06-17.sqlite"), "Kid1", "s1", [(1, 1)])
        make_db(str(self.tmp / "tlkids" / "math-flu_Kid2_2026-06-16.sqlite"), "Kid2", "s2", [(2, 2)])
        # A sqlite inside a subfolder must not become a landing button.
        make_db(str(self.tmp / "tlkids" / "dragon-gm" / "math-flu_Hidden_2026-06-01.sqlite"), "Hidden", "s3", [(3, 3)])
        r = D.folder_users("tlkids")
        self.assertTrue(r["ok"])
        self.assertEqual([u["name"] for u in r["users"]], ["Kid1", "Kid2"])

    def test_local_find_picks_newest_when_duplicates_in_folder(self):
        (self.tmp / "test" / "old").mkdir(parents=True)
        (self.tmp / "test" / "new").mkdir(parents=True)
        fname = "dup.sqlite"
        old_p, new_p = self.tmp / "test" / "old" / fname, self.tmp / "test" / "new" / fname
        old_p.write_bytes(b"x")
        time.sleep(0.02)
        new_p.write_bytes(b"xy")
        found = D._local_find("test", fname)
        self.assertEqual(found, new_p)

    def test_edit_with_no_file_returns_clear_error(self):
        r = D.edit_problem_lists("real", "Ghost", "create", {"listName": "X"})
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"], "no-file")

    def test_save_items_rejects_unparseable_line(self):
        D.save_run("real", "source", "K2", "2026-06-19_120000", "",
                   session_bytes("K2", "s1", [(1, 1)]), force_new=True)
        out = D.edit_problem_lists("real", "K2", "create", {"listName": "L", "text": "1 + 1\n"})
        lid = out["problemLists"][0]["problem_list_id"]
        bad = D.edit_problem_lists("real", "K2", "save-items", {"problemListId": lid, "text": "8 plus 2"})
        self.assertFalse(bad["ok"])                               # parse error surfaced
        self.assertEqual(D._problem_lists_for(self.tmp / "real" / "math-flu_K2_2026-06-19_120000.sqlite",
                                              "K2")[0]["items"][0]["problem_text"], "1 + 1")  # unchanged
        # An empty text clears the list (allowed).
        cleared = D.edit_problem_lists("real", "K2", "save-items", {"problemListId": lid, "text": "  \n"})
        self.assertEqual(cleared["problemLists"][0]["item_count"], 0)

    def test_clone_user_snapshots_target_then_clones_and_renames(self):
        # /api/clone-user-file: Kid1's file is cloned as Randy; Randy's old file is
        # snapshotted to BACKUP_ROOT then deleted; Kid1's file is untouched.
        (self.tmp / "real").mkdir(parents=True)
        Kid1 = self.tmp / "real" / "math-flu_K1_2026-06-17.sqlite"
        make_db(str(Kid1), "Kid1", "s1", [(2, 3), (7, 1)])
        k1_bytes = Kid1.read_bytes()
        old_randy = self.tmp / "real" / "math-flu_Randy_2026-06-10.sqlite"
        make_db(str(old_randy), "Randy", "r1", [(1, 1)])

        r = D.clone_user("real", "Kid1", "Randy")
        self.assertTrue(r["ok"])
        self.assertEqual(r["new_file"], "math-flu_Randy_2026-06-17.sqlite")
        self.assertEqual(r["deleted"], ["math-flu_Randy_2026-06-10.sqlite"])
        self.assertFalse(old_randy.exists())
        new = self.tmp / "real" / "math-flu_Randy_2026-06-17.sqlite"
        conn = sqlite3.connect(str(new))
        self.assertEqual(conn.execute("SELECT name FROM Users").fetchall(), [("Randy",)])
        self.assertEqual(conn.execute("SELECT DISTINCT user_name FROM Sessions").fetchall(), [("Randy",)])
        conn.close()
        self.assertEqual(Kid1.read_bytes(), k1_bytes)
        # the deleted file was snapshotted first (reversible)
        self.assertEqual(len(r["backups"]), 1)
        backup = Path(r["backups"][0]["backup"])
        self.assertTrue(backup.exists())
        self.assertTrue(backup.name.startswith("math-flu_Randy_2026-06-10_backup_"))

    def test_clone_user_errors_on_missing_folder_or_source(self):
        self.assertFalse(D.clone_user("nope", "Kid1", "Randy")["ok"])
        (self.tmp / "real").mkdir(parents=True)
        self.assertFalse(D.clone_user("real", "Ghost", "Randy")["ok"])
        make_db(str(self.tmp / "real" / "math-flu_K1_2026-06-17.sqlite"), "Kid1", "s1", [(1, 1)])
        self.assertFalse(D.clone_user("real", "Kid1", "Kid1")["ok"])

    def test_list_folder_users_returns_distinct_names_from_filenames(self):
        (self.tmp / "real").mkdir(parents=True)
        make_db(str(self.tmp / "real" / "math-flu_K1_2026-06-17.sqlite"), "Kid1", "s1", [(1, 1)])
        make_db(str(self.tmp / "real" / "math-flu_K2_2026-06-16.sqlite"), "K2", "m1", [(2, 2)])
        make_db(str(self.tmp / "real" / "math-flu_Randy_2026-06-10.sqlite"), "Randy", "r1", [(3, 3)])
        self.assertEqual(D.list_folder_users("real"), ["Kid1", "K2", "Randy"])

    def test_append_uploads_snapshot_backup_to_s3(self):
        captured = []
        orig = D.s3_upload
        D.s3_upload = lambda local, key: (captured.append(key) or f"s3://bucket/{key}")
        try:
            D.save_run("real", "source", "Kid", "2026-06-20_090000", "",
                       session_bytes("Kid", "s1", [(1, 1)]), force_new=True)
            r = D.save_run("real", "source", "Kid", "2026-06-20_100000", "",
                           session_bytes("Kid", "s2", [(2, 2)]))
        finally:
            D.s3_upload = orig
        self.assertEqual(len(captured), 3)  # create single, append single, pre-append snapshot
        self.assertTrue(captured[0].startswith("math-quiz/single-sessions/"))
        self.assertTrue(captured[1].startswith("math-quiz/single-sessions/"))
        self.assertTrue(captured[2].startswith("math-quiz/_backup-s3/"))
        self.assertEqual(r.get("singleSessionS3Uri"), f"s3://bucket/{captured[1]}")
        self.assertEqual(r.get("backupS3Uri"), f"s3://bucket/{captured[2]}")
        self.assertTrue(captured[2].endswith("_backup_2026-06-20_100000.sqlite"))

    def test_clone_user_snapshots_target_then_clones_and_renames(self):
        # /api/clone-user-file: Kid1's file is cloned as Randy; Randy's old file is
        # snapshotted to BACKUP_ROOT then deleted; Kid1's file is untouched.
        (self.tmp / "real").mkdir(parents=True)
        Kid1 = self.tmp / "real" / "math-flu_K1_2026-06-17.sqlite"
        make_db(str(Kid1), "Kid1", "s1", [(2, 3), (7, 1)])
        k1_bytes = Kid1.read_bytes()
        old_randy = self.tmp / "real" / "math-flu_Randy_2026-06-10.sqlite"
        make_db(str(old_randy), "Randy", "r1", [(1, 1)])

        r = D.clone_user("real", "Kid1", "Randy")
        self.assertTrue(r["ok"])
        self.assertEqual(r["new_file"], "math-flu_Randy_2026-06-17.sqlite")
        self.assertEqual(r["deleted"], ["math-flu_Randy_2026-06-10.sqlite"])
        self.assertFalse(old_randy.exists())
        new = self.tmp / "real" / "math-flu_Randy_2026-06-17.sqlite"
        conn = sqlite3.connect(str(new))
        self.assertEqual(conn.execute("SELECT name FROM Users").fetchall(), [("Randy",)])
        self.assertEqual(conn.execute("SELECT DISTINCT user_name FROM Sessions").fetchall(), [("Randy",)])
        conn.close()
        self.assertEqual(Kid1.read_bytes(), k1_bytes)
        self.assertEqual(len(r["backups"]), 1)
        backup = Path(r["backups"][0]["backup"])
        self.assertTrue(backup.exists())
        self.assertTrue(backup.name.startswith("math-flu_Randy_2026-06-10_backup_"))

    def test_clone_user_errors_on_missing_folder_or_source(self):
        self.assertFalse(D.clone_user("nope", "Kid1", "Randy")["ok"])
        (self.tmp / "real").mkdir(parents=True)
        self.assertFalse(D.clone_user("real", "Ghost", "Randy")["ok"])
        make_db(str(self.tmp / "real" / "math-flu_K1_2026-06-17.sqlite"), "Kid1", "s1", [(1, 1)])
        self.assertFalse(D.clone_user("real", "Kid1", "Kid1")["ok"])
    def test_clone_user_stops_when_target_backup_fails(self):
        (self.tmp / "real").mkdir(parents=True)
        source = self.tmp / "real" / "math-flu_K1_2026-06-17.sqlite"
        target = self.tmp / "real" / "math-flu_Randy_2026-06-10.sqlite"
        make_db(str(source), "Kid1", "s1", [(1, 1)])
        make_db(str(target), "Randy", "r1", [(2, 2)])
        target_bytes = target.read_bytes()
        with mock.patch.object(D, "_backup_source_file", return_value={"backupError": "disk full"}):
            result = D.clone_user("real", "Kid1", "Randy")
        self.assertFalse(result["ok"])
        self.assertIn("backup failed", result["error"])
        self.assertEqual(target.read_bytes(), target_bytes)
        self.assertFalse((self.tmp / "real" / "math-flu_Randy_2026-06-17.sqlite").exists())

    def test_api_responses_send_cache_control_no_store(self):
        # Stale browser caching of /api/latest-user-db was able to wipe a just-saved
        # quiz from IndexedDB on Continue; API responses must opt out of caching.
        headers = []
        class Probe(D.Handler):
            def __init__(self):
                self.path = "/api/latest-user-db?folder=real&user=Kid"
            def send_header(self, k, v):
                headers.append((k, v))
        with mock.patch.object(http.server.SimpleHTTPRequestHandler, "end_headers", lambda self: None):
            Probe().end_headers()
        self.assertIn(("Cache-Control", "no-store"), headers)

if __name__ == "__main__":
    unittest.main()
