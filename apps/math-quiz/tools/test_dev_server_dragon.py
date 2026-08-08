#!/usr/bin/env python3
"""Tests for the dragon Game Master sync store in dev_server: state snapshot
save/view and the GM message send -> unread poll -> mark-read cycle. Stdlib only."""
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
import dev_server as D  # noqa: E402


class DragonStaticPaths(unittest.TestCase):
    def test_normalize_dragon_index_aliases(self):
        self.assertEqual(D._normalize_static_path("/dragon/index"), "/dragon/index.html")
        self.assertEqual(D._normalize_static_path("/dragon"), "/dragon/index.html")
        self.assertEqual(D._normalize_static_path("/dragon/"), "/dragon/index.html")
        self.assertEqual(D._normalize_static_path("/Dragon/Index"), "/dragon/index.html")
        self.assertEqual(D._normalize_static_path("/dragon/gm"), "/dragon/gm.html")
        self.assertEqual(D._normalize_static_path("/anchor.html"), "/anchor.html")


class DragonGmStore(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self._data_dir = D.DATA_DIR
        self._backup_root = D.BACKUP_ROOT
        self._display_names_file = D.dragon_display_names.DISPLAY_NAMES_FILE
        self._display_names_cache = D.dragon_display_names._cache
        self._prev_backup_dir = os.environ.get("ANCHOR_DRAGON_BACKUP_DIR")
        D.DATA_DIR = self.tmp
        D.BACKUP_ROOT = self.tmp / "sqlite-snapshots"
        D.BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
        D.dragon_display_names.DISPLAY_NAMES_FILE = self.tmp / "display_names.json"
        D.dragon_display_names._cache = None
        os.environ["ANCHOR_DRAGON_BACKUP_DIR"] = str(self.tmp / "_dragon-backups")
    def tearDown(self):
        D.DATA_DIR = self._data_dir
        D.BACKUP_ROOT = self._backup_root
        D.dragon_display_names.DISPLAY_NAMES_FILE = self._display_names_file
        D.dragon_display_names._cache = self._display_names_cache
        if self._prev_backup_dir is None:
            os.environ.pop("ANCHOR_DRAGON_BACKUP_DIR", None)
        else:
            os.environ["ANCHOR_DRAGON_BACKUP_DIR"] = self._prev_backup_dir
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_state_view_before_first_post(self):
        out = D.dragon_state_view("tlkids", "Kid1")
        self.assertTrue(out["ok"])
        self.assertFalse(out["found"])

    def test_state_save_then_view_roundtrip(self):
        snapshot = {"dragonName": "Sparkle", "pct": 62.5, "maxPct": 64,
                    "phase": "hatchling", "totalBursts": 9, "gems": 40,
                    "stations": {"signs": {"sign-welcome": "Hi"}, "levels": {"fountain": 1}}}
        saved = D.save_dragon_state("tlkids", "Kid1", snapshot)
        self.assertTrue(saved["ok"])
        self.assertTrue(saved["updatedAt"])
        out = D.dragon_state_view("tlkids", "Kid1")
        self.assertTrue(out["found"])
        self.assertEqual(out["state"], snapshot)
        self.assertEqual(out["updatedAt"], saved["updatedAt"])
        newer = dict(snapshot, totalBursts=10)
        D.save_dragon_state("tlkids", "Kid1", newer)
        self.assertEqual(D.dragon_state_view("tlkids", "Kid1")["state"]["totalBursts"], 10)

    def test_state_save_backups_and_rejects_wipe(self):
        rich = {
            "dragonName": "pipa", "gems": 208, "totalBursts": 19, "maxPct": 69,
            "stations": {
                "signs": {"sign-welcome": "Pipa's valley", "sign-dragon": "tickle"},
                "levels": {"fountain": 2, "nest": 0, "trees": 1},
            },
            "volcano": {"intro": True, "cleared": 5, "summited": True},
        }
        D.save_dragon_state("tlkids", "Kid1", rich)
        wiped = {
            "dragonName": None, "gems": 0, "totalBursts": 0, "maxPct": 80,
            "stations": {
                "signs": {"sign-welcome": "", "sign-dragon": ""},
                "levels": {"fountain": 0, "nest": 0, "trees": 0},
            },
            "volcano": {"intro": True, "cleared": 0, "summited": False},
        }
        saved = D.save_dragon_state("tlkids", "Kid1", wiped)
        self.assertTrue(saved.get("preservedWorldProgress"))
        self.assertTrue(saved.get("backup"))
        self.assertTrue(Path(saved["backup"]).is_file())
        out = D.dragon_state_view("tlkids", "Kid1")["state"]
        self.assertEqual(out["gems"], 208)
        self.assertEqual(out["dragonName"], "pipa")
        self.assertEqual(out["stations"]["signs"]["sign-welcome"], "Pipa's valley")
        self.assertEqual(out["maxPct"], 80)

    def test_state_is_per_user_and_folder(self):
        D.save_dragon_state("tlkids", "Kid1", {"pct": 50})
        self.assertFalse(D.dragon_state_view("tlkids", "Randy")["found"])
        self.assertFalse(D.dragon_state_view("playtest", "Kid1")["found"])

    def test_message_cycle_send_unread_mark_read(self):
        sent = D.post_dragon_message("tlkids", "Kid1", "So proud of you!", "Baba")
        self.assertTrue(sent["ok"])
        self.assertEqual(sent["message"]["from"], "Baba")
        self.assertFalse(sent["message"]["read"])
        D.post_dragon_message("tlkids", "Kid1", "Keep going!", None)
        unread = D.dragon_messages_view("tlkids", "Kid1", unread_only=True)["messages"]
        self.assertEqual(len(unread), 2)
        self.assertEqual(unread[1]["from"], "The Dragon Keeper")   # default sender
        marked = D.mark_dragon_messages_read("tlkids", "Kid1", [m["id"] for m in unread])
        self.assertEqual(marked["marked"], 2)
        self.assertEqual(D.dragon_messages_view("tlkids", "Kid1", unread_only=True)["messages"], [])
        full = D.dragon_messages_view("tlkids", "Kid1")["messages"]
        self.assertEqual(len(full), 2)
        self.assertTrue(all(m["read"] for m in full))

    def test_message_validation_and_caps(self):
        self.assertFalse(D.post_dragon_message("tlkids", "Kid1", "   ", "Baba")["ok"])
        long_text = "x" * 900
        msg = D.post_dragon_message("tlkids", "Kid1", long_text, "Baba")["message"]
        self.assertEqual(len(msg["text"]), 500)
        for i in range(105):
            D.post_dragon_message("tlkids", "Kid1", f"m{i}", "Baba")
        msgs = D.dragon_messages_view("tlkids", "Kid1")["messages"]
        self.assertEqual(len(msgs), 100)   # history capped
        self.assertEqual(msgs[-1]["text"], "m104")
        ids = [m["id"] for m in msgs]
        self.assertEqual(ids, sorted(ids))   # ids stay monotonic across the cap

    def test_mark_read_ignores_unknown_ids(self):
        D.post_dragon_message("tlkids", "Kid1", "hello", "Baba")
        out = D.mark_dragon_messages_read("tlkids", "Kid1", [999])
        self.assertTrue(out["ok"])
        self.assertEqual(out["marked"], 0)

    def test_zoomie_lines_save_then_view_roundtrip(self):
        saved = D.save_dragon_zoomie_lines("tlkids", "Kid1", {
            "81": ["Nice work", "Breathe in"],
            82: ["Almost steady"],
        })
        self.assertTrue(saved["ok"])
        self.assertTrue(saved["updatedAt"])
        self.assertEqual(saved["bands"], {"81": ["Nice work", "Breathe in"], "82": ["Almost steady"]})
        out = D.dragon_zoomie_lines_view("tlkids", "Kid1")
        self.assertTrue(out["ok"])
        self.assertEqual(out["bands"], saved["bands"])
        self.assertEqual(out["updatedAt"], saved["updatedAt"])

    def test_zoomie_lines_reject_bad_band_key(self):
        out = D.save_dragon_zoomie_lines("tlkids", "Kid1", {"42": ["Nope"]})
        self.assertFalse(out["ok"])
        self.assertIn("42", out["error"])

    def test_zoomie_lines_trim_drop_empty_and_remove_empty_bands(self):
        saved = D.save_dragon_zoomie_lines("tlkids", "Kid1", {
            "81": ["  first line  ", "", "   ", "\nsecond line\n"],
            "82": [" ", "\n"],
        })
        self.assertTrue(saved["ok"])
        self.assertEqual(saved["bands"], {"81": ["first line", "second line"]})
        self.assertNotIn("82", D.dragon_zoomie_lines_view("tlkids", "Kid1")["bands"])

    def test_zoomie_lines_caps_lines_and_band_size(self):
        saved = D.save_dragon_zoomie_lines("tlkids", "Kid1", {
            "89": ["x" * 450] + [f"line {i}" for i in range(20)],
        })
        self.assertTrue(saved["ok"])
        lines = saved["bands"]["89"]
        self.assertEqual(len(lines), 8)
        self.assertEqual(len(lines[0]), 400)
        self.assertEqual(lines[-1], "line 6")

    def test_growth_spurt_lines_save_then_view_roundtrip(self):
        saved = D.save_dragon_growth_spurt_lines("tlkids", "Kid1", {
            "91": ["Whoa, big!", "Even bigger"],
            92: ["Tall tail"],
        })
        self.assertTrue(saved["ok"])
        self.assertTrue(saved["updatedAt"])
        self.assertEqual(saved["bands"], {"91": ["Whoa, big!", "Even bigger"], "92": ["Tall tail"]})
        out = D.dragon_growth_spurt_lines_view("tlkids", "Kid1")
        self.assertTrue(out["ok"])
        self.assertEqual(out["bands"], saved["bands"])
        self.assertEqual(out["updatedAt"], saved["updatedAt"])

    def test_growth_spurt_lines_reject_bad_band_key(self):
        out = D.save_dragon_growth_spurt_lines("tlkids", "Kid1", {"90": ["Too early"]})
        self.assertFalse(out["ok"])
        self.assertIn("90", out["error"])

    def test_growth_spurt_lines_trim_drop_empty_and_remove_empty_bands(self):
        saved = D.save_dragon_growth_spurt_lines("tlkids", "Kid1", {
            "91": ["  first line  ", "", "   "],
            "92": [" ", "\n"],
        })
        self.assertTrue(saved["ok"])
        self.assertEqual(saved["bands"], {"91": ["first line"]})
        self.assertNotIn("92", D.dragon_growth_spurt_lines_view("tlkids", "Kid1")["bands"])

    def test_growth_spurt_lines_caps_lines_and_band_size(self):
        saved = D.save_dragon_growth_spurt_lines("tlkids", "Kid1", {
            "100": ["x" * 450] + [f"line {i}" for i in range(20)],
        })
        self.assertTrue(saved["ok"])
        lines = saved["bands"]["100"]
        self.assertEqual(len(lines), 8)
        self.assertEqual(len(lines[0]), 400)
        self.assertEqual(lines[-1], "line 6")

    def test_clone_dragon_gm_state_copies_snapshot_and_renames_user(self):
        D.save_dragon_state("tlkids", "Kid1", {
            "user": "Kid1", "pct": 70, "volcano": {"cleared": 4},
            "stations": {"signs": {"sign-welcome": "HI"}},
        })
        D.save_dragon_state("tlkids", "Randy", {"user": "Randy", "pct": 10})
        out = D.clone_dragon_gm_state("tlkids", "Kid1", "Randy")
        self.assertTrue(out["copied"])
        randy = D.dragon_state_view("tlkids", "Randy")
        self.assertTrue(randy["found"])
        self.assertEqual(randy["state"]["user"], "Randy")
        self.assertEqual(randy["state"]["volcano"]["cleared"], 4)
        self.assertEqual(randy["state"]["stations"]["signs"]["sign-welcome"], "HI")
        # Source untouched
        self.assertEqual(D.dragon_state_view("tlkids", "Kid1")["state"]["user"], "Kid1")

    def test_clone_dragon_gm_state_clears_target_when_source_missing(self):
        D.save_dragon_state("tlkids", "Randy", {"pct": 10})
        out = D.clone_dragon_gm_state("tlkids", "Kid1", "Randy")
        self.assertFalse(out["copied"])
        self.assertFalse(D.dragon_state_view("tlkids", "Randy")["found"])


class DragonDisplayNames(unittest.TestCase):
    def setUp(self):
        import dragon_display_names as ddn
        self._mod = ddn
        self._path = ddn.DISPLAY_NAMES_FILE
        self._cache = ddn._cache
        self.tmp = Path(tempfile.mkdtemp())
        ddn.DISPLAY_NAMES_FILE = self.tmp / "display_names.json"
        ddn._cache = None

    def tearDown(self):
        self._mod.DISPLAY_NAMES_FILE = self._path
        self._mod._cache = self._cache
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_missing_file_returns_empty_map(self):
        out = D.dragon_display_names_view()
        self.assertTrue(out["ok"])
        self.assertEqual(out["names"], {})

    def test_reads_user_id_to_friendly_name(self):
        self._mod.DISPLAY_NAMES_FILE.write_text('{"Kid1": "Kid1", "Randy": "Dad"}', encoding="utf-8")
        self._mod._cache = None
        out = D.dragon_display_names_view()
        self.assertEqual(out["names"], {"Kid1": "Kid1", "Randy": "Dad"})


if __name__ == "__main__":
    unittest.main()
