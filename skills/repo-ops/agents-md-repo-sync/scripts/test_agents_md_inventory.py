#!/usr/bin/env python3
"""Unit tests for agents_md_inventory pure helpers."""
import unittest

from agents_md_inventory import (
    classify_agents_presence,
    default_candidate_branches,
    refine_classification,
    short_sha256,
)

class TestAgentsMdInventory(unittest.TestCase):
    def test_short_sha256_stable(self):
        self.assertEqual(short_sha256("hello"), short_sha256("hello"))
        self.assertNotEqual(short_sha256("hello"), short_sha256("world"))
        self.assertEqual(len(short_sha256("hello")), 12)
    def test_classify_match_and_missing(self):
        self.assertEqual(classify_agents_presence("a", "a"), "match")
        self.assertEqual(classify_agents_presence(None, None), "missing-both")
        self.assertEqual(classify_agents_presence(None, "a"), "missing-on-main")
        self.assertEqual(classify_agents_presence("a", None), "missing-on-branch")
        self.assertEqual(classify_agents_presence("a", "b"), "diverged")
    def test_refine_classification(self):
        self.assertEqual(refine_classification("match", True, False), "match")
        self.assertEqual(refine_classification("diverged", True, False), "branch-only")
        self.assertEqual(refine_classification("diverged", False, True), "main-only")
        self.assertEqual(refine_classification("diverged", True, True), "diverged")
        self.assertEqual(refine_classification("diverged", None, False), "diverged")
    def test_default_candidate_branches(self):
        names = [
            "main",
            "HEAD",
            "origin",
            "claude/foo-bar-baz",
            "feature/math-quiz",
            "fix/hooks",
            "holodeck/swing-v2",
            "stellar-transcriber-start",
        ]
        out = default_candidate_branches(names)
        self.assertIn("feature/math-quiz", out)
        self.assertIn("fix/hooks", out)
        self.assertIn("holodeck/swing-v2", out)
        self.assertIn("stellar-transcriber-start", out)
        self.assertNotIn("main", out)
        self.assertNotIn("origin", out)
        self.assertNotIn("claude/foo-bar-baz", out)

if __name__ == "__main__":
    unittest.main()
