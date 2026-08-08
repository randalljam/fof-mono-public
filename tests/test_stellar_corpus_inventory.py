"""
Tests for the Stellar Transcriber corpus inventory script
(apps/transcription/stellar-transcriber/scripts/build_corpus_inventory.py).

Run from the repo root:
    .venv/bin/python3 -m pytest tests/test_stellar_corpus_inventory.py
or:
    .venv/bin/python3 -m unittest tests.test_stellar_corpus_inventory
"""
import importlib.util
import json
import os
import tempfile
import unittest

### Module loading (kebab-case app path, so importlib by file path)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_PATH = os.path.join(REPO_ROOT, "apps", "transcription", "stellar-transcriber",
                           "scripts", "build_corpus_inventory.py")
spec = importlib.util.spec_from_file_location("build_corpus_inventory", SCRIPT_PATH)
inv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inv)

### Helpers
def make_row(repo_path, corpus="deutsch"):
    """Minimal manifest row with the fields the script reads."""
    return {"repo_path": repo_path, "corpus": corpus, "s3_key": repo_path}

class TestSplitStemSuffix(unittest.TestCase):
    def test_raw_suffix(self):
        stem, suffix, ext = inv.split_stem_suffix("2024-03-06_PB_nova2gen.md")
        self.assertEqual((stem, suffix, ext), ("2024-03-06_PB", "_nova2gen", ".md"))
    def test_longest_suffix_wins_over_nova2(self):
        stem, suffix, ext = inv.split_stem_suffix("2023-01-05_PV-EPC_nova2meet.md")
        self.assertEqual(suffix, "_nova2meet")
        stem2, suffix2, _ = inv.split_stem_suffix("2023-01-05_PV-EPC_nova2.md")
        self.assertEqual(suffix2, "_nova2")
    def test_ref_suffix(self):
        _, suffix, _ = inv.split_stem_suffix("2011-08-01_KERA Think Radio_qafixed.md")
        self.assertEqual(suffix, "_qafixed")
    def test_no_suffix(self):
        stem, suffix, ext = inv.split_stem_suffix("INVENTORY_dd_post.md")
        self.assertEqual(suffix, "")
        self.assertEqual(stem, "INVENTORY_dd_post")
    def test_unknown_suffix(self):
        _, suffix, _ = inv.split_stem_suffix("2024-01-01_Title_qa-multi.md")
        self.assertEqual(suffix, "")
    def test_json_extension(self):
        stem, suffix, ext = inv.split_stem_suffix("2024-03-06_PB_dgwhspm.json")
        self.assertEqual((suffix, ext), ("_dgwhspm", ".json"))

class TestBuildCorpusCatalog(unittest.TestCase):
    def test_pairing_and_categories(self):
        rows = [
            make_row("data/deutsch/f9_raw/2024-03-06_PB_nova2gen.md"),
            make_row("data/deutsch/f9_raw/2024-03-06_PB_nova2gen.json"),
            make_row("data/deutsch/f9_raw/2024-03-06_PB_dgwhspm.md"),
            make_row("data/deutsch/f9_raw/2024-03-06_PB_yt.md"),
            make_row("data/deutsch/f8/2024-03-06_PB_qafixed.md"),
            make_row("data/deutsch/f8/2024-03-06_PB_vrb.md"),
        ]
        episodes = inv.build_corpus_catalog(rows, "deutsch")
        self.assertEqual(list(episodes.keys()), ["2024-03-06_PB"])
        ep = episodes["2024-03-06_PB"]
        self.assertEqual(ep["raw_suffixes"], {"_nova2gen", "_dgwhspm"})
        self.assertEqual(ep["ref_suffixes"], {"_qafixed", "_vrb"})
        self.assertEqual(ep["stage_suffixes"], {"_yt"})
        self.assertEqual(ep["json_suffixes"], {"_nova2gen"})
        self.assertEqual(len(ep["s3_keys"]), 5)  # md files only, json excluded
    def test_excludes_non_transcript_and_suffixless(self):
        rows = [
            make_row("data/deutsch/INVENTORY_dd_post.md"),
            make_row("data/deutsch/notes/2024-01-01_Title_qa-multi.md"),
            make_row("data/deutsch/audio/2024-01-01_Title_nova2gen.mp3"),
        ]
        episodes = inv.build_corpus_catalog(rows, "deutsch")
        self.assertEqual(episodes, {})
    def test_stage_only_stem_excluded(self):
        rows = [make_row("data/deutsch/f9_raw/2024-05-05_Solo_yt.md")]
        episodes = inv.build_corpus_catalog(rows, "deutsch")
        self.assertEqual(episodes, {})
    def test_ref_only_stem_included(self):
        rows = [make_row("data/deutsch/f7/2011-08-01_KERA_qafixed.md")]
        episodes = inv.build_corpus_catalog(rows, "deutsch")
        self.assertIn("2011-08-01_KERA", episodes)

class TestSummarize(unittest.TestCase):
    def test_summary_counts(self):
        rows = [
            make_row("data/x/2024-01-01_A_nova2gen.md"),
            make_row("data/x/2024-01-01_A_vrb.md"),
            make_row("data/x/2024-01-02_B_nova2gen.md"),
            make_row("data/x/2024-01-03_C_cemanual.md"),
        ]
        episodes = inv.build_corpus_catalog(rows, "x")
        summary = inv.summarize_corpus(episodes)
        self.assertEqual(summary, {"episodes": 3, "pairs": 1, "raw_only": 1, "ref_only": 1})

class TestCsvRows(unittest.TestCase):
    def test_csv_row_shape_and_sort(self):
        rows = [
            make_row("data/x/2024-01-02_B_nova2gen.md"),
            make_row("data/x/2024-01-01_A_nova2gen.md"),
            make_row("data/x/2024-01-01_A_vrb.md"),
        ]
        episodes = inv.build_corpus_catalog(rows, "x")
        csv_rows = inv.catalog_to_csv_rows(episodes)
        self.assertEqual([r["stem"] for r in csv_rows], ["2024-01-01_A", "2024-01-02_B"])
        self.assertEqual(csv_rows[0]["has_pair"], "yes")
        self.assertEqual(csv_rows[1]["has_pair"], "no")
        self.assertEqual(csv_rows[0]["raw_suffixes"], "_nova2gen")

class TestEndToEnd(unittest.TestCase):
    def test_load_manifest_and_catalog(self):
        rows = [
            make_row("data/t/2024-06-01_Ep1_nova2gen.md", corpus="t"),
            make_row("data/t/2024-06-01_Ep1_qafixed.md", corpus="t"),
            make_row("data/t/2024-06-02_Ep2_dgwhspm.md", corpus="t"),
        ]
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
            for row in rows:
                f.write(json.dumps(row) + "\n")
            manifest_path = f.name
        try:
            loaded = inv.load_manifest_rows(manifest_path)
            self.assertEqual(len(loaded), 3)
            episodes = inv.build_corpus_catalog(loaded, "t")
            summary = inv.summarize_corpus(episodes)
            self.assertEqual(summary["episodes"], 2)
            self.assertEqual(summary["pairs"], 1)
        finally:
            os.unlink(manifest_path)

if __name__ == "__main__":
    unittest.main()
