"""Unit tests for push_to_computer (config, paths, argv). No network."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import push_to_computer as ptc


SAMPLE_TOML = """
[[computers]]
id = "target-laptop"
aliases = ["target-laptop", "tl"]
ssh = "user@host1.local"
primary_checkout = "/Users/your-user/Code/fof-mono"
local_files_root = "/Users/your-user/Code/_LOCAL_FILES/fof-mono"

[[computers]]
id = "other-mac"
aliases = ["other-mac"]
ssh = "user@host3.local"
"""

class PushToComputerTests(unittest.TestCase):
    def _write_config(self, text=SAMPLE_TOML):
        handle = tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False)
        handle.write(text)
        handle.close()
        self.addCleanup(lambda: os.path.exists(handle.name) and os.unlink(handle.name))
        return handle.name
    def test_load_computers_and_alias_lookup(self):
        path = self._write_config()
        computers = ptc.load_computers(path)
        self.assertIn("target-laptop", computers)
        cid, info = ptc.resolve_computer("tl", computers)
        self.assertEqual(cid, "target-laptop")
        self.assertEqual(info["ssh"], "user@host1.local")
        self.assertEqual(
            info["local_files_root"],
            "/Users/your-user/Code/_LOCAL_FILES/fof-mono",
        )
    def test_missing_config_message(self):
        missing = os.path.join(tempfile.gettempdir(), "no-such-push-computers.toml")
        with self.assertRaises(SystemExit) as ctx:
            ptc.load_computers(missing)
        self.assertIn("computer registry not found", str(ctx.exception))
        self.assertIn("computers.example.toml", str(ctx.exception))
    def test_malformed_toml(self):
        path = self._write_config("[[computers]\nid = 'broken'\n")
        with self.assertRaises(SystemExit) as ctx:
            ptc.load_computers(path)
        self.assertIn("invalid TOML", str(ctx.exception))
    def test_config_path_precedence(self):
        with mock.patch.dict(os.environ, {ptc.ENV_CONFIG: "/tmp/from-env.toml"}, clear=False):
            self.assertEqual(
                ptc.resolve_config_path("/explicit/path.toml"),
                os.path.abspath("/explicit/path.toml"),
            )
            self.assertEqual(
                ptc.resolve_config_path(None),
                os.path.abspath("/tmp/from-env.toml"),
            )
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(ptc.ENV_CONFIG, None)
            with mock.patch.object(ptc, "find_repo_root", return_value="/repo"):
                self.assertEqual(
                    ptc.resolve_config_path(None),
                    os.path.join("/repo", ptc.DEFAULT_CONFIG_REL),
                )
    def test_resolve_dest_modes(self):
        computers = ptc.load_computers(self._write_config())
        _, target = ptc.resolve_computer("target-laptop", computers)
        self.assertEqual(
            ptc.resolve_dest_dir(target, "local-files", "data/ai-coding/notes"),
            "/Users/your-user/Code/_LOCAL_FILES/fof-mono/data/ai-coding/notes",
        )
        self.assertEqual(
            ptc.resolve_dest_dir(target, "primary-checkout", ""),
            "/Users/your-user/Code/fof-mono",
        )
        _, other = ptc.resolve_computer("other-mac", computers)
        with self.assertRaises(SystemExit):
            ptc.resolve_dest_dir(other, "local-files", "x")
    def test_reject_rel_traversal_and_absolute(self):
        with self.assertRaises(SystemExit):
            ptc.sanitize_rel("../escape")
        with self.assertRaises(SystemExit):
            ptc.sanitize_rel("/absolute")
        with self.assertRaises(SystemExit):
            ptc.sanitize_rel("ok/\x00bad")
        self.assertEqual(ptc.sanitize_rel("./data/notes"), "data/notes")
    def test_reject_non_absolute_configured_roots(self):
        path = self._write_config(
            """
[[computers]]
id = "bad"
aliases = ["bad"]
ssh = "user@host1.local"
local_files_root = "relative/path"
"""
        )
        with self.assertRaises(SystemExit) as ctx:
            ptc.load_computers(path)
        self.assertIn("absolute remote path", str(ctx.exception))
    def test_build_rsync_args_dry_run_and_execute(self):
        dry = ptc.build_rsync_args(
            "user@host1.local",
            ["/tmp/src.md"],
            "/Users/your-user/Code/_LOCAL_FILES/fof-mono/notes",
            execute=False,
        )
        self.assertIn("--dry-run", dry)
        self.assertIn("--", dry)
        self.assertEqual(dry[dry.index("--") + 1], "/tmp/src.md")
        self.assertTrue(dry[-1].startswith("user@host1.local:"))
        live = ptc.build_rsync_args(
            "user@host1.local",
            ["/tmp/src.md"],
            "/Users/your-user/Code/_LOCAL_FILES/fof-mono/notes",
            execute=True,
        )
        self.assertNotIn("--dry-run", live)
        self.assertIn("--", live)
    def test_main_list_computers(self):
        path = self._write_config()
        with mock.patch("sys.stdout") as _:
            code = ptc.main(["--config", path, "--list-computers"])
        self.assertEqual(code, 0)
    def test_main_dry_run_uses_mocked_ssh_rsync(self):
        path = self._write_config()
        src = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False)
        src.write("hello\n")
        src.close()
        self.addCleanup(lambda: os.path.exists(src.name) and os.unlink(src.name))
        with mock.patch.object(ptc, "ssh_reachable", return_value=True), mock.patch.object(
            ptc, "ensure_remote_dir", return_value=True
        ) as ensure, mock.patch.object(ptc, "rsync_push", return_value=True) as rsync:
            code = ptc.main(
                [
                    "--config",
                    path,
                    "--computer",
                    "tl",
                    "--local-files",
                    "--rel",
                    "data/notes",
                    src.name,
                ]
            )
        self.assertEqual(code, 0)
        ensure.assert_called_once()
        self.assertFalse(ensure.call_args.args[2])
        rsync.assert_called_once()
        self.assertFalse(rsync.call_args.kwargs.get("execute", rsync.call_args.args[3]))

if __name__ == "__main__":
    unittest.main()
