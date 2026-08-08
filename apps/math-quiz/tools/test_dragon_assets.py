#!/usr/bin/env python3
"""Regression: missing dragon/assets/models GLBs → procedural purple blob instead of Pipa."""
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
import dragon_assets as DA  # noqa: E402

APP_DIR = Path(__file__).resolve().parent.parent
DRAGON_JS = APP_DIR / "dragon" / "world" / "dragon.js"
EXPECTED_FORM_PATHS = {
    "baby": "assets/models/dragon.glb",
    "juvenile": "assets/models/dragon-juvenile.glb",
    "adult": "assets/models/dragon-adult.glb",
}


class DragonAssetPaths(unittest.TestCase):
    def test_dragon_js_form_paths_point_at_pipa_life_stages(self):
        """createDragon must load the rigged Pipa GLBs, not an old single placeholder."""
        text = DRAGON_JS.read_text(encoding="utf-8")
        match = re.search(r"const FORM_PATHS = \{([^}]+)\}", text, re.S)
        self.assertIsNotNone(match, "FORM_PATHS missing from dragon.js")
        found = dict(re.findall(r"(\w+):\s*'([^']+)'", match.group(1)))
        self.assertEqual(found, EXPECTED_FORM_PATHS)


class DragonAssetProvision(unittest.TestCase):
    def test_pipa_glb_life_stage_models_are_on_disk_for_the_game(self):
        """Regression for the purple-blob fallback.

        When approved Pipa GLBs exist under content_studio, the game-served
        copies under dragon/assets/models/ must be present. If they are missing,
        createDragon falls back to the procedural purple polygon dragon.
        """
        if not DA.approved_sources_available():
            self.skipTest("approved Pipa GLBs not available on this machine")
        # Before ensure_local_models / server startup, these paths are often empty
        # (gitignored) and createDragon falls back to the purple procedural blob.
        provisioned = DA.ensure_local_models()
        self.assertTrue(provisioned.get("ok"), provisioned)
        missing = [name for name, path in DA.runtime_model_paths().items() if not path.is_file()]
        self.assertEqual(
            missing, [],
            "missing runtime GLB(s) %s — game will use procedural purple blob instead of Pipa"
            % missing,
        )
        for name, path in DA.runtime_model_paths().items():
            self.assertGreater(
                path.stat().st_size, 100_000,
                "%s is too small to be the Pipa GLB: %s" % (name, path),
            )

    def test_ensure_local_models_copies_from_approved_when_missing(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        approved = tmp / "approved"
        runtime = tmp / "models"
        approved.mkdir()
        for name in DA.MODEL_FILES:
            (approved / name).write_bytes(b"glb-bytes-" + name.encode())
        prev_approved, prev_runtime = DA.APPROVED_DIR, DA.RUNTIME_MODELS_DIR
        DA.APPROVED_DIR = approved
        DA.RUNTIME_MODELS_DIR = runtime
        try:
            out = DA.ensure_local_models()
            self.assertTrue(out["ok"])
            self.assertEqual(sorted(out["copied"]), sorted(DA.MODEL_FILES))
            for name in DA.MODEL_FILES:
                dest = runtime / name
                self.assertTrue(dest.is_file())
                self.assertEqual(dest.read_bytes(), (approved / name).read_bytes())
            again = DA.ensure_local_models()
            self.assertEqual(again["copied"], [])
            self.assertEqual(sorted(again["present"]), sorted(DA.MODEL_FILES))
        finally:
            DA.APPROVED_DIR = prev_approved
            DA.RUNTIME_MODELS_DIR = prev_runtime


if __name__ == "__main__":
    unittest.main()
