#!/usr/bin/env python3
"""Tests for dragon/data/display_names.json alias resolution."""
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
import dragon_display_names as DDN  # noqa: E402
import dev_server as D  # noqa: E402
from test_anchor_store import make_db  # noqa: E402


class DragonDisplayNamesModule(unittest.TestCase):
    def setUp(self):
        self._path = DDN.DISPLAY_NAMES_FILE
        self._cache = DDN._cache
        self.tmp = Path(tempfile.mkdtemp())
        DDN.DISPLAY_NAMES_FILE = self.tmp / "display_names.json"
        DDN._cache = None

    def tearDown(self):
        DDN.DISPLAY_NAMES_FILE = self._path
        DDN._cache = self._cache
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_missing_file_returns_empty_map(self):
        self.assertEqual(DDN.load_names(), {})
        self.assertEqual(DDN.resolve_data_user("Kid1"), "Kid1")

    def test_resolve_maps_code_id_to_local_name(self):
        DDN.DISPLAY_NAMES_FILE.write_text('{"Kid1": "Kid1"}', encoding="utf-8")
        DDN._cache = None
        self.assertEqual(DDN.resolve_data_user("Kid1"), "Kid1")
        self.assertEqual(DDN.resolve_data_user("Randy"), "Randy")


class CloneWithDisplayAlias(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self._data_dir = D.DATA_DIR
        self._names_path = DDN.DISPLAY_NAMES_FILE
        self._names_cache = DDN._cache
        D.DATA_DIR = self.tmp
        DDN.DISPLAY_NAMES_FILE = self.tmp / "display_names.json"
        DDN.DISPLAY_NAMES_FILE.write_text('{"Kid1": "Kid1"}', encoding="utf-8")
        DDN._cache = None
        folder = self.tmp / "tlkids"
        folder.mkdir()
        Kid1 = folder / "math-flu_Izzy_2026-06-17.sqlite"
        make_db(str(Kid1), "Kid1", "s1", [(2, 3)])

    def tearDown(self):
        D.DATA_DIR = self._data_dir
        DDN.DISPLAY_NAMES_FILE = self._names_path
        DDN._cache = self._names_cache
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_clone_user_resolves_k1_to_izzy_file(self):
        r = D.clone_user("tlkids", "Kid1", "Tester")
        self.assertTrue(r["ok"], r.get("error"))
        self.assertEqual(r["source_file"], "math-flu_Izzy_2026-06-17.sqlite")
        self.assertTrue(r["new_file"].startswith("math-flu_Tester_"))


if __name__ == "__main__":
    unittest.main()
