#!/usr/bin/env python3
"""Smoke test reword_commits on a tiny temp repo."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REWORD = Path(__file__).resolve().parents[1] / "skills/repo-ops/reword-branch-commits/scripts/reword_commits.py"


def run(cmd, cwd, env=None):
    r = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, env=env)
    return r


class RewordCommitsTest(unittest.TestCase):
    def test_reword_preserves_tree(self):
        with tempfile.TemporaryDirectory() as td:
            repo = td
            run(["git", "init", "-b", "main"], repo)
            run(["git", "config", "user.email", "t@example.com"], repo)
            run(["git", "config", "user.name", "Tester"], repo)
            Path(repo, "a.txt").write_text("1\n")
            run(["git", "add", "a.txt"], repo)
            run(["git", "commit", "-m", "feat(app): first"], repo)
            base = run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
            run(["git", "checkout", "-b", "feature/x"], repo)
            Path(repo, "a.txt").write_text("2\n")
            run(["git", "add", "a.txt"], repo)
            run(["git", "commit", "-m", "feat(app): second"], repo)
            old_tip = run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
            old_subj = run(["git", "log", "-1", "--format=%s", "HEAD"], repo).stdout.strip()
            sha2 = old_tip
            with tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False) as mf:
                mf.write(f"{sha2[:7]}\tfix(app): second renamed\n")
                map_path = mf.name
            try:
                py = os.environ.get("PYTHON", "python3")
                r = run(
                    [py, str(REWORD), "--repo", repo, "--branch", "feature/x", "--base", base, "--map", map_path, "--skip-remote-check"],
                    repo,
                )
            finally:
                os.unlink(map_path)
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            new_tip = run(["git", "rev-parse", "feature/x"], repo).stdout.strip()
            self.assertNotEqual(old_tip, new_tip)
            diff = run(["git", "diff", old_tip, new_tip], repo).stdout
            self.assertEqual(diff.strip(), "")
            new_subj = run(["git", "log", "-1", "--format=%s", "feature/x"], repo).stdout.strip()
            self.assertEqual(new_subj, "fix(app): second renamed")

    def test_reword_refuses_to_recreate_lineage_record(self):
        with tempfile.TemporaryDirectory() as td:
            repo = td
            run(["git", "init", "-b", "main"], repo)
            run(["git", "config", "user.email", "t@example.com"], repo)
            run(["git", "config", "user.name", "Tester"], repo)
            Path(repo, "a.txt").write_text("1\n")
            run(["git", "add", "a.txt"], repo)
            run(["git", "commit", "-m", "feat(app): first"], repo)
            base = run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
            run(["git", "checkout", "-b", "feature/x"], repo)
            message = "\n".join([
                "chore(repo): record branch lineage at branch start for feature/x",
                "",
                "Record-Type: branch-lineage",
                "Lineage-Type: branch-start",
            ])
            run(["git", "commit", "--allow-empty", "-m", message], repo)
            lineage_sha = run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
            with tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False) as mf:
                mf.write(f"{lineage_sha[:7]}\tchore(repo): unsafe reword\n")
                map_path = mf.name
            try:
                py = os.environ.get("PYTHON", "python3")
                result = run(
                    [py, str(REWORD), "--repo", repo, "--branch", "feature/x", "--base", base, "--map", map_path, "--skip-remote-check"],
                    repo,
                )
            finally:
                os.unlink(map_path)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("refusing to recreate branch-lineage record", result.stderr)
            self.assertEqual(run(["git", "rev-parse", "HEAD"], repo).stdout.strip(), lineage_sha)


if __name__ == "__main__":
    unittest.main()
