#!/usr/bin/env python3
"""Tests for the canonical dragon-world on-disk save."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
import dragon_world_store as W  # noqa: E402


def rich_state():
    return {
        "version": 3,
        "learner": "Kid1",
        "gems": 208,
        "dragonName": "pipa",
        "totalBursts": 19,
        "maxPct": 80,
        "stations": {
            "signs": {"sign-welcome": "Pipa's valley", "sign-dragon": "tickle"},
            "levels": {"fountain": 2, "nest": 0, "trees": 1},
        },
        "volcano": {"intro": True, "cleared": 5, "summited": True},
    }


class DragonWorldStore(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.backup = self.tmp / "sqlite-snapshots"
        self.backup.mkdir()
        self._prev = os.environ.get("ANCHOR_DRAGON_BACKUP_DIR")
        os.environ["ANCHOR_DRAGON_BACKUP_DIR"] = str(self.tmp / "_dragon-backups")

    def tearDown(self):
        if self._prev is None:
            os.environ.pop("ANCHOR_DRAGON_BACKUP_DIR", None)
        else:
            os.environ["ANCHOR_DRAGON_BACKUP_DIR"] = self._prev
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_save_view_roundtrip(self):
        out = W.save_dragon_world(self.tmp, "tlkids", "Kid1", rich_state(), sqlite_backup_root=self.backup)
        self.assertTrue(out["ok"])
        view = W.dragon_world_view(self.tmp, "tlkids", "Kid1")
        self.assertTrue(view["found"])
        self.assertEqual(view["gameState"]["gems"], 208)
        self.assertEqual(view["gameState"]["dragonName"], "pipa")

    def test_wipe_shaped_save_is_preserved(self):
        W.save_dragon_world(self.tmp, "tlkids", "Kid1", rich_state(), sqlite_backup_root=self.backup)
        wiped = {
            "version": 3, "learner": "Kid1", "gems": 0, "dragonName": None,
            "totalBursts": 0, "maxPct": 80,
            "stations": {"signs": {"sign-welcome": ""}, "levels": {"fountain": 0}},
            "volcano": {"intro": True, "cleared": 0, "summited": False},
        }
        out = W.save_dragon_world(self.tmp, "tlkids", "Kid1", wiped, sqlite_backup_root=self.backup)
        self.assertTrue(out.get("preservedWorldProgress"))
        self.assertTrue(out.get("backup"))
        view = W.dragon_world_view(self.tmp, "tlkids", "Kid1")["gameState"]
        self.assertEqual(view["gems"], 208)
        self.assertEqual(view["stations"]["signs"]["sign-welcome"], "Pipa's valley")
        self.assertEqual(view["maxPct"], 80)

    def test_clone_rewrites_learner(self):
        W.save_dragon_world(self.tmp, "tlkids", "Kid1", rich_state(), sqlite_backup_root=self.backup)
        cloned = W.clone_dragon_world(self.tmp, "tlkids", "Kid1", "Randy", sqlite_backup_root=self.backup)
        self.assertTrue(cloned["copied"])
        view = W.dragon_world_view(self.tmp, "tlkids", "Randy")["gameState"]
        self.assertEqual(view["learner"], "Randy")
        self.assertEqual(view["gems"], 208)


if __name__ == "__main__":
    unittest.main()
