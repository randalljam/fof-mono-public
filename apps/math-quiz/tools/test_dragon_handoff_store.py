#!/usr/bin/env python3
"""Tests for dragon cross-device handoff store (dragon-sync/). Stdlib only."""
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
import dragon_handoff_store as H  # noqa: E402


def sample_checkpoint(user="Kid1", bursts=3):
    return {
        "gameState": {"learner": user, "totalBursts": bursts, "dragonName": "Pipa", "gems": 12},
        "pose": {"x": 1.2, "y": 1.6, "z": 4.0, "yaw": 0.5, "pitch": -0.1},
        "pendingQuiz": {
            "items": [{"key": "5+3", "operation": "+", "num1": 5, "num2": 3, "problemText": "5 + 3"}],
            "atGoGate": True,
            "pendingBoulder": False,
            "pendingLava": None,
            "pendingStation": None,
        },
    }


class DragonHandoffStore(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.folder = "tlkids"
        self.user = "Kid1"
        self.desktop = "desktop-aaa"
        self.touch = "touch-bbb"
        self._prev_backup_dir = os.environ.get("ANCHOR_DRAGON_BACKUP_DIR")
        os.environ["ANCHOR_DRAGON_BACKUP_DIR"] = str(self.tmp / "_dragon-backups")

    def tearDown(self):
        if self._prev_backup_dir is None:
            os.environ.pop("ANCHOR_DRAGON_BACKUP_DIR", None)
        else:
            os.environ["ANCHOR_DRAGON_BACKUP_DIR"] = self._prev_backup_dir
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_initialize_then_status_owner(self):
        cp = sample_checkpoint()
        out = H.dragon_handoff_action(self.tmp, self.folder, self.user, "initialize", {
            "deviceId": self.desktop, "deviceType": "desktop", "checkpoint": cp,
        })
        self.assertTrue(out["ok"])
        self.assertEqual(out["revision"], 1)
        self.assertTrue(out["ownerToken"])
        st = H.dragon_handoff_view(self.tmp, self.folder, self.user, self.desktop, "desktop")
        self.assertTrue(st["found"])
        self.assertTrue(st["isOwner"])
        self.assertEqual(st["revision"], 1)

    def test_checkpoint_requires_owner_token_and_revision(self):
        init = H.dragon_handoff_action(self.tmp, self.folder, self.user, "initialize", {
            "deviceId": self.desktop, "deviceType": "desktop", "checkpoint": sample_checkpoint(),
        })
        bad = H.dragon_handoff_action(self.tmp, self.folder, self.user, "checkpoint", {
            "deviceId": self.desktop, "deviceType": "desktop",
            "ownerToken": "wrong", "revision": init["revision"],
            "checkpoint": sample_checkpoint(bursts=4),
        })
        self.assertFalse(bad["ok"])
        ok = H.dragon_handoff_action(self.tmp, self.folder, self.user, "checkpoint", {
            "deviceId": self.desktop, "deviceType": "desktop",
            "ownerToken": init["ownerToken"], "revision": init["revision"],
            "checkpoint": sample_checkpoint(bursts=4),
        })
        self.assertTrue(ok["ok"])
        self.assertEqual(ok["revision"], 2)

    def test_transfer_claim_roundtrip(self):
        init = H.dragon_handoff_action(self.tmp, self.folder, self.user, "initialize", {
            "deviceId": self.desktop, "deviceType": "desktop", "checkpoint": sample_checkpoint(),
        })
        cp = sample_checkpoint(bursts=5)
        xfer = H.dragon_handoff_action(self.tmp, self.folder, self.user, "transfer", {
            "deviceId": self.desktop, "deviceType": "desktop",
            "ownerToken": init["ownerToken"], "revision": init["revision"],
            "checkpoint": cp, "targetDeviceType": "touch",
        })
        self.assertTrue(xfer["ok"])
        st_desktop = H.dragon_handoff_view(self.tmp, self.folder, self.user, self.desktop, "desktop")
        self.assertFalse(st_desktop["isOwner"])
        self.assertEqual(st_desktop["inactiveReason"], "transferred")
        st_touch = H.dragon_handoff_view(self.tmp, self.folder, self.user, self.touch, "touch")
        self.assertTrue(st_touch["canClaim"])
        self.assertTrue(st_touch["checkpoint"]["pendingQuiz"]["atGoGate"])
        claim = H.dragon_handoff_action(self.tmp, self.folder, self.user, "claim", {
            "deviceId": self.touch, "deviceType": "touch",
        })
        self.assertTrue(claim["ok"])
        self.assertEqual(claim["checkpoint"]["gameState"]["totalBursts"], 5)
        self.assertEqual(len(claim["checkpoint"]["pendingQuiz"]["items"]), 1)
        self.assertTrue(claim["isOwner"])
        # Owner status also returns the full checkpoint (quiz survives reload).
        st_owner = H.dragon_handoff_view(self.tmp, self.folder, self.user, self.touch, "touch")
        self.assertTrue(st_owner["isOwner"])
        self.assertTrue(st_owner["checkpoint"]["pendingQuiz"]["items"])

    def test_claim_rejects_wrong_device_type(self):
        init = H.dragon_handoff_action(self.tmp, self.folder, self.user, "initialize", {
            "deviceId": self.desktop, "deviceType": "desktop", "checkpoint": sample_checkpoint(),
        })
        H.dragon_handoff_action(self.tmp, self.folder, self.user, "transfer", {
            "deviceId": self.desktop, "deviceType": "desktop",
            "ownerToken": init["ownerToken"], "revision": init["revision"],
            "checkpoint": sample_checkpoint(), "targetDeviceType": "touch",
        })
        bad = H.dragon_handoff_action(self.tmp, self.folder, self.user, "claim", {
            "deviceId": self.desktop, "deviceType": "desktop",
        })
        self.assertFalse(bad["ok"])

    def test_per_user_folder_isolation(self):
        H.dragon_handoff_action(self.tmp, self.folder, self.user, "initialize", {
            "deviceId": self.desktop, "deviceType": "desktop", "checkpoint": sample_checkpoint(),
        })
        other = H.dragon_handoff_view(self.tmp, self.folder, "Randy", self.desktop, "desktop")
        self.assertFalse(other["found"])

    def test_takeover_recovery(self):
        init = H.dragon_handoff_action(self.tmp, self.folder, self.user, "initialize", {
            "deviceId": self.desktop, "deviceType": "desktop", "checkpoint": sample_checkpoint(),
        })
        H.dragon_handoff_action(self.tmp, self.folder, self.user, "transfer", {
            "deviceId": self.desktop, "deviceType": "desktop",
            "ownerToken": init["ownerToken"], "revision": init["revision"],
            "checkpoint": sample_checkpoint(), "targetDeviceType": "touch",
        })
        take = H.dragon_handoff_action(self.tmp, self.folder, self.user, "takeover", {
            "deviceId": self.desktop, "deviceType": "desktop", "confirm": True,
        })
        self.assertTrue(take["ok"])
        self.assertTrue(take["isOwner"])
        self.assertTrue(take["checkpoint"]["pendingQuiz"]["atGoGate"])

    def test_takeover_does_not_wipe_pending_quiz_when_client_omits_it(self):
        init = H.dragon_handoff_action(self.tmp, self.folder, self.user, "initialize", {
            "deviceId": self.desktop, "deviceType": "desktop", "checkpoint": sample_checkpoint(),
        })
        H.dragon_handoff_action(self.tmp, self.folder, self.user, "transfer", {
            "deviceId": self.desktop, "deviceType": "desktop",
            "ownerToken": init["ownerToken"], "revision": init["revision"],
            "checkpoint": sample_checkpoint(bursts=9), "targetDeviceType": "touch",
        })
        # Bug that bit playtesting: iPad "Take over" uploaded a world-only blob
        # and erased the desktop's pending Go quiz.
        wiped = {
            "gameState": {"learner": "Kid1", "totalBursts": 1, "dragonName": "Pipa"},
            "pose": None,
            "pendingQuiz": None,
        }
        take = H.dragon_handoff_action(self.tmp, self.folder, self.user, "takeover", {
            "deviceId": self.touch, "deviceType": "touch", "confirm": True,
            "checkpoint": wiped,
        })
        self.assertTrue(take["ok"])
        self.assertEqual(take["checkpoint"]["gameState"]["totalBursts"], 1)
        self.assertTrue(take["checkpoint"]["pendingQuiz"]["atGoGate"])
        self.assertEqual(take["checkpoint"]["pendingQuiz"]["items"][0]["problemText"], "5 + 3")

    def test_checkpoint_preserves_rich_world_against_blank_localstorage(self):
        rich = {
            "gameState": {
                "learner": "Kid1", "totalBursts": 19, "dragonName": "pipa", "gems": 208,
                "stations": {
                    "signs": {"sign-welcome": "Pipa's valley", "sign-dragon": "tickle"},
                    "levels": {"fountain": 2, "nest": 0, "trees": 1},
                },
                "volcano": {"intro": True, "cleared": 5, "summited": True},
            },
            "pose": {"x": 0, "y": 1.6, "z": -8, "yaw": 0, "pitch": 0},
            "pendingQuiz": None,
        }
        init = H.dragon_handoff_action(self.tmp, self.folder, self.user, "initialize", {
            "deviceId": self.desktop, "deviceType": "desktop", "checkpoint": rich,
        })
        blank = {
            "gameState": {
                "learner": "Kid1", "totalBursts": 0, "dragonName": None, "gems": 5,
                "stations": {
                    "signs": {"sign-welcome": "", "sign-dragon": ""},
                    "levels": {"fountain": 0, "nest": 0, "trees": 0},
                },
                "volcano": {"intro": True, "cleared": 0, "summited": False},
            },
            "pose": {"x": 1, "y": 1.6, "z": 0, "yaw": 0, "pitch": 0},
            "pendingQuiz": None,
        }
        out = H.dragon_handoff_action(self.tmp, self.folder, self.user, "checkpoint", {
            "deviceId": self.desktop, "deviceType": "desktop",
            "ownerToken": init["ownerToken"], "revision": init["revision"],
            "checkpoint": blank,
        })
        self.assertTrue(out["ok"])
        self.assertTrue(out.get("preservedWorldProgress"))
        st = H.dragon_handoff_view(self.tmp, self.folder, self.user, self.desktop, "desktop")
        gs = st["checkpoint"]["gameState"]
        self.assertEqual(gs["gems"], 208)
        self.assertEqual(gs["dragonName"], "pipa")
        self.assertEqual(gs["stations"]["signs"]["sign-welcome"], "Pipa's valley")
        self.assertGreaterEqual(gs["volcano"]["cleared"], 5)
        snaps = list((self.tmp / "_dragon-backups" / "dragon-sync-snapshots").glob("K1_handoff_backup_*.json"))
        self.assertTrue(snaps)


if __name__ == "__main__":
    unittest.main()
