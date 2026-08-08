#!/usr/bin/env python3
"""Tests for tools/session_ingest.py reusable single-session intake."""
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
import session_ingest as I  # noqa: E402
from test_anchor_store import make_db  # noqa: E402


def make_session_file(directory, filename, user, session_id, problems):
    path = Path(directory) / filename
    make_db(str(path), user, session_id, problems)
    return path


class SessionIngestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def _count(self, path, table):
        conn = sqlite3.connect(path)
        try:
            return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        finally:
            conn.close()

    def test_ingests_mathquest_single_session_into_tl_kids_folder(self):
        src = make_session_file(
            self.tmp,
            "mathquest_K1_2026-06-26_101500.sqlite",
            "Kid1",
            "sess-1",
            [(1, 2)],
        )
        result = I.ingest_single_session(
            src,
            "Kid1",
            self.tmp / "tl-kids",
            archive_dir=self.tmp / "_single-session-sqlite-files",
            prefix="mathquest",
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["action"], "create")
        self.assertEqual(result["filename"], "mathquest_K1_2026-06-26_101500.sqlite")
        self.assertTrue((self.tmp / "_single-session-sqlite-files" / src.name).exists())
        self.assertTrue((self.tmp / "tl-kids" / result["filename"]).exists())

    def test_second_mathquest_session_appends_and_renames_to_multi(self):
        first = make_session_file(
            self.tmp,
            "mathquest_K2_2026-06-26_101500.sqlite",
            "K2",
            "sess-1",
            [(1, 2)],
        )
        second = make_session_file(
            self.tmp,
            "mathquest_K2_2026-06-26_102000.sqlite",
            "K2",
            "sess-2",
            [(3, 4)],
        )
        I.ingest_single_session(first, "K2", self.tmp / "tl-kids",
                                archive_dir=self.tmp / "_single-session-sqlite-files",
                                prefix="mathquest")
        result = I.ingest_single_session(second, "K2", self.tmp / "tl-kids",
                                         archive_dir=self.tmp / "_single-session-sqlite-files",
                                         prefix="mathquest")
        self.assertTrue(result["ok"])
        self.assertEqual(result["action"], "append")
        self.assertEqual(result["filename"], "mathquest_K2_2026-06-26.sqlite")
        multi = self.tmp / "tl-kids" / result["filename"]
        self.assertEqual(self._count(multi, "Sessions"), 2)
        self.assertEqual(self._count(multi, "ProblemAttempts"), 2)
        self.assertFalse((self.tmp / "tl-kids" / first.name).exists())

    def test_mathquest_session_appends_to_latest_named_file_with_any_prefix(self):
        active = self.tmp / "tlkids"
        active.mkdir()
        older = make_session_file(
            active,
            "math-flu_Randy_2026-06-10.sqlite",
            "Randy",
            "sess-old",
            [(1, 1)],
        )
        newer = make_session_file(
            active,
            "math-flu_Randy_2026-06-16.sqlite",
            "Randy",
            "sess-new",
            [(2, 2)],
        )
        src = make_session_file(
            self.tmp,
            "mathquest_Randy_2026-06-26_152500.sqlite",
            "Randy",
            "sess-mathquest",
            [(3, 3)],
        )
        result = I.ingest_single_session(
            src,
            "Randy",
            active,
            archive_dir=self.tmp / "_single-session-sqlite-files",
            prefix="mathquest",
            match_any_prefix=True,
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["action"], "append")
        self.assertEqual(result["filename"], newer.name)
        self.assertEqual(result["target"], newer.name)
        self.assertEqual(result["matchedBy"], "name-date-any-prefix")
        self.assertEqual(self._count(newer, "Sessions"), 2)
        self.assertEqual(self._count(older, "Sessions"), 1)

    def test_exact_active_file_overrides_latest_named_file_matching(self):
        active = self.tmp / "tlkids"
        active.mkdir()
        regular = make_session_file(
            active,
            "math-flu_K1_2026-06-27.sqlite",
            "Kid1",
            "sess-regular",
            [(1, 1)],
        )
        quest_active = active / "quest1_try1_K1_2026-06-27.sqlite"
        first = make_session_file(
            self.tmp,
            "mathquest_K1_2026-06-27_101500.sqlite",
            "Kid1",
            "sess-quest-1",
            [(2, 2)],
        )
        second = make_session_file(
            self.tmp,
            "mathquest_K1_2026-06-27_102000.sqlite",
            "Kid1",
            "sess-quest-2",
            [(3, 3)],
        )
        created = I.ingest_single_session(
            first,
            "Kid1",
            None,
            active_file=quest_active,
            archive_dir=self.tmp / "_single-session-sqlite-files",
            prefix="mathquest",
            match_any_prefix=True,
        )
        appended = I.ingest_single_session(
            second,
            "Kid1",
            None,
            active_file=quest_active,
            archive_dir=self.tmp / "_single-session-sqlite-files",
            prefix="mathquest",
            match_any_prefix=True,
        )
        self.assertTrue(created["ok"])
        self.assertEqual(created["action"], "create")
        self.assertEqual(created["matchedBy"], "exact-active-file")
        self.assertTrue(appended["ok"])
        self.assertEqual(appended["action"], "append")
        self.assertEqual(appended["filename"], quest_active.name)
        self.assertEqual(self._count(quest_active, "Sessions"), 2)
        self.assertEqual(self._count(regular, "Sessions"), 1)

    def test_require_existing_errors_after_archive_without_active_write(self):
        src = make_session_file(
            self.tmp,
            "math-flu_Ghost_2026-06-26_101500.sqlite",
            "Ghost",
            "sess-1",
            [(1, 1)],
        )
        result = I.ingest_single_session(
            src,
            "Ghost",
            self.tmp / "real",
            archive_dir=self.tmp / "_single-session-sqlite-files",
            require_existing=True,
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "no-continue-file")
        self.assertTrue((self.tmp / "_single-session-sqlite-files" / src.name).exists())
        self.assertFalse((self.tmp / "real").exists())


if __name__ == "__main__":
    unittest.main()
