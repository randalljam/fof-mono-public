#!/usr/bin/env python3
"""Unit tests for agents_md_report pure helpers."""
import os
import tempfile
import unittest

from agents_md_report import format_run_report, format_verify_section, prepend_log, LOG_REL


class TestAgentsMdReport(unittest.TestCase):
    def test_format_verify_pass(self):
        rows = [
            {"name": "main", "sha12": "abc", "class": "baseline"},
            {"name": "feature/a", "sha12": "abc", "class": "match"},
        ]
        lines = format_verify_section(True, rows, [])
        self.assertTrue(any("PASS" in line for line in lines))
        self.assertTrue(any("1" in line and "matching" in line for line in lines))
    def test_format_verify_fail(self):
        rows = [
            {"name": "main", "sha12": "abc", "class": "baseline"},
            {"name": "feature/a", "sha12": "def", "class": "main-only"},
        ]
        mismatches = [rows[1]]
        lines = format_verify_section(False, rows, mismatches)
        self.assertTrue(any("FAIL" in line for line in lines))
        self.assertTrue(any("feature/a" in line for line in lines))
    def test_format_run_report_categories(self):
        md = format_run_report({
            "stamp": "2026-07-28_0941",
            "runner": "Randy (test)",
            "phase_a_note": "none (fan-out only)",
            "canonical_sha12": "abc123abc123",
            "verify_lines": ["- **Verification: PASS**"],
            "fanout_main_only": [
                {"branch": "feature/a", "action": "updated from main", "commit": "deadbeef"},
                {"branch": "feature/b", "action": "already matched"},
            ],
            "non_root_agents_md": ["apps/foo/AGENTS.md", "apps/bar/AGENTS.md"],
            "demoted": [{
                "branch": "feature/c",
                "topic": "app run notes",
                "scoped_path": "apps/foo/AGENTS.md",
                "created": True,
                "commit": "cafebabe",
                "pushed": True,
            }],
        })
        self.assertIn("## 2026-07-28_0941 — agents-md-repo-sync", md)
        self.assertIn("Fan-out only", md)
        self.assertIn("`feature/a`", md)
        self.assertIn("Demoted to scoped", md)
        self.assertIn("apps/foo/AGENTS.md", md)
        self.assertIn("(created)", md)
        self.assertIn("Inventory — non-root", md)
        self.assertIn("`apps/bar/AGENTS.md`", md)
        # inventory section should follow fan-out section
        self.assertLess(md.find("Fan-out only"), md.find("Inventory — non-root"))
    def test_log_rel_is_skill_tracked(self):
        self.assertEqual(LOG_REL, "skills/repo-ops/agents-md-repo-sync/run-log.md")
    def test_prepend_log_newest_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "agents-md-repo-sync.md")
            prepend_log(path, "## 2026-07-28_0900 — agents-md-repo-sync\n\nold\n")
            prepend_log(path, "## 2026-07-28_1000 — agents-md-repo-sync\n\nnew\n")
            with open(path, encoding="utf-8") as f:
                text = f.read()
            self.assertTrue(text.startswith("# agents-md-repo-sync run log"))
            pos_new = text.find("## 2026-07-28_1000")
            pos_old = text.find("## 2026-07-28_0900")
            self.assertGreater(pos_new, 0)
            self.assertGreater(pos_old, pos_new)

if __name__ == "__main__":
    unittest.main()
