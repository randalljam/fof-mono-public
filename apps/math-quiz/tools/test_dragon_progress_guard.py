#!/usr/bin/env python3
"""Tests for dragon world-progress guard + JSON snapshot backups."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
import dragon_progress_guard as dpg  # noqa: E402


class WorldProgressScore(unittest.TestCase):
    def test_richer_nest_scores_higher(self):
        empty = {"gems": 0, "stations": {"signs": {"sign-welcome": ""}, "levels": {"fountain": 0}}}
        rich = {
            "gems": 208,
            "dragonName": "pipa",
            "totalBursts": 19,
            "stations": {
                "signs": {"sign-welcome": "Pipa's Dragon Valley", "sign-dragon": "Beware"},
                "levels": {"fountain": 2, "nest": 0, "trees": 1},
            },
            "volcano": {"intro": True, "cleared": 5, "summited": True},
        }
        self.assertGreater(dpg.world_progress_score(rich), dpg.world_progress_score(empty))
        self.assertGreater(dpg.world_progress_score(rich), 30)


class PreserveWorldProgress(unittest.TestCase):
    def test_wiped_incoming_keeps_signs_gems_and_stations(self):
        existing = {
            "gems": 208,
            "dragonName": "pipa",
            "totalBursts": 19,
            "maxPct": 69,
            "stations": {
                "signs": {"sign-welcome": "Pipa's Dragon Valley don't go in lava.",
                          "sign-dragon": "Beware: tickle dragon!"},
                "levels": {"fountain": 2, "nest": 0, "trees": 1},
            },
            "volcano": {"intro": True, "cleared": 5, "summited": True},
            "lava": {"intro": True, "startPct": 80, "stopped": [3, 1], "won": False},
            "celebratedIds": ["egg-found", "hatch"],
        }
        incoming = {
            "gems": 5,
            "dragonName": None,
            "totalBursts": 0,
            "maxPct": 80,
            "stations": {
                "signs": {"sign-welcome": "", "sign-dragon": ""},
                "levels": {"fountain": 0, "nest": 0, "trees": 0},
            },
            "volcano": {"intro": True, "cleared": 0, "summited": False},
            "lava": {"intro": True, "startPct": 80, "stopped": [], "won": False},
            "celebratedIds": ["egg-found", "hatch", "wings", "jump"],
        }
        merged, preserved = dpg.preserve_world_progress(existing, incoming)
        self.assertTrue(preserved)
        self.assertEqual(merged["gems"], 208)
        self.assertEqual(merged["dragonName"], "pipa")
        self.assertEqual(merged["stations"]["signs"]["sign-dragon"], "Beware: tickle dragon!")
        self.assertEqual(merged["stations"]["levels"]["fountain"], 2)
        self.assertEqual(merged["volcano"]["cleared"], 5)
        self.assertTrue(merged["volcano"]["summited"])
        self.assertEqual(merged["lava"]["stopped"], [3, 1])
        self.assertEqual(merged["maxPct"], 80)  # fluency high-water still advances
        self.assertIn("wings", merged["celebratedIds"])
        self.assertIn("hatch", merged["celebratedIds"])

    def test_richer_incoming_is_kept(self):
        existing = {"gems": 10, "stations": {"signs": {}, "levels": {}}}
        incoming = {
            "gems": 50,
            "dragonName": "pipa",
            "stations": {"signs": {"sign-welcome": "Hi"}, "levels": {"fountain": 1}},
        }
        merged, preserved = dpg.preserve_world_progress(existing, incoming)
        self.assertFalse(preserved)
        self.assertEqual(merged["gems"], 50)
        self.assertEqual(merged["stations"]["levels"]["fountain"], 1)

    def test_preserve_checkpoint_keeps_pending_quiz(self):
        existing = {
            "gameState": {"gems": 208, "dragonName": "pipa", "stations": {
                "signs": {"sign-welcome": "Hi"}, "levels": {"fountain": 2}}},
            "pendingQuiz": {"atGoGate": True, "items": [1]},
            "pose": {"x": 1},
        }
        incoming = {
            "gameState": {"gems": 0, "dragonName": None, "stations": {
                "signs": {"sign-welcome": ""}, "levels": {"fountain": 0}}},
            "pendingQuiz": None,
            "pose": {"x": 2},
        }
        merged, preserved = dpg.preserve_checkpoint(existing, incoming)
        self.assertTrue(preserved)
        self.assertEqual(merged["gameState"]["gems"], 208)
        self.assertEqual(merged["pendingQuiz"]["atGoGate"], True)
        self.assertEqual(merged["pose"]["x"], 2)


class BackupJsonFile(unittest.TestCase):
    def test_backup_writes_snapshot_and_prunes(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src_dir = tmp / "live"
            src_dir.mkdir()
            src = src_dir / "K1_state.json"
            src.write_text(json.dumps({"state": {"gems": 1}}))
            sqlite_root = tmp / "sqlite-snapshots"
            sqlite_root.mkdir()
            out = dpg.backup_json_file(src, "dragon-gm", sqlite_backup_root=sqlite_root, stamp="2026-07-21_120000")
            self.assertIsInstance(out, str)
            backup = Path(out)
            self.assertTrue(backup.is_file())
            self.assertEqual(backup.parent.resolve(), (tmp / "dragon-gm-snapshots").resolve())
            self.assertEqual(backup.name, "K1_state_backup_2026-07-21_120000.json")
            self.assertEqual(json.loads(backup.read_text())["state"]["gems"], 1)


if __name__ == "__main__":
    unittest.main()
