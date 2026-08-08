"""Tests for rsync output parsing and mocked sync/status paths."""
import os
import sys
from unittest.mock import patch

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from server import remote as remote_ops
from server import sync as sync_ops


def test_rsync_remote_dest_quotes_spaces():
    computer = {"id": "2", "role": "target", "host": "host3.local", "user": "carer"}
    dest = remote_ops.rsync_remote_dest(
        computer,
        "Library/Application Support/PrismLauncher/instances/Fabric 26.1.2 MathQuest/",
    )
    assert dest == 'carer@host3.local:"$HOME/Library/Application Support/PrismLauncher/instances/Fabric 26.1.2 MathQuest/"'


def test_parse_rsync_dry_run_no_changes():
    output = "sending incremental file list\n\nsent 100 bytes  received 20 bytes\n"
    assert sync_ops.parse_rsync_dry_run_output(output) is False


def test_parse_rsync_dry_run_with_changes():
    output = "sending incremental file list\n>f+++++++++ mods/foo.jar\n"
    assert sync_ops.parse_rsync_dry_run_output(output) is True


def test_filter_rsync_preview_hides_timestamp_only():
    raw = "\n".join([
        "Replacing older mod versions:",
        "  old.jar → new.jar",
        ".d..t.... ./",
        "<f..t.... jei-1.20.1-forge-15.20.0.130.jar",
        "<f+++++++ coordinatesdisplay-3.1.0-all.jar",
        "*deleting minecraft/config/jei/jei-client.ini",
    ])
    filtered = sync_ops.filter_rsync_preview_output(raw)
    assert "Replacing older mod versions:" in filtered
    assert "old.jar → new.jar" in filtered
    assert "jei-1.20.1-forge-15.20.0.130.jar" not in filtered
    assert ".d..t...." not in filtered
    assert "coordinatesdisplay-3.1.0-all.jar" in filtered
    assert "*deleting minecraft/config/jei/jei-client.ini" in filtered


def test_filter_rsync_preview_empty_after_filter():
    raw = ".d..t.... ./\n<f..t.... jei-1.20.1-forge-15.20.0.130.jar\n"
    filtered = sync_ops.filter_rsync_preview_output(raw)
    assert filtered == "(no file adds, deletes, or content changes)"


def test_build_matrix_local_instances_only():
    local = [{"name": "Local A", "display_name": "Local A", "section": "local"}]
    payload = sync_ops.build_matrix(local, {
        "status": {"Local A": {"1": "same_mods"}},
        "mods_detail": {},
    })
    assert [row["name"] for row in payload["rows"]] == ["Local A"]
    assert payload["status"]["Local A"]["1"] == "same_mods"
    assert payload["local_mods"]["Local A"] == []


@patch("server.mods.remote_mod_jars", return_value=["fabric-api.jar"])
@patch("server.mods.local_mod_jars", return_value=["fabric-api.jar"])
@patch("server.remote.remote_has_instance", return_value=True)
@patch("server.sync.os.path.isdir", return_value=True)
def test_instance_status_same_mods(mock_isdir, mock_has, mock_local, mock_remote):
    computer = {"id": "1", "role": "target", "host": "host1.local", "user": "Kid1"}
    detail = sync_ops.instance_status_detail(computer, "Test Pack", {"1": "online"})
    assert detail["state"] == "same_mods"
    assert "mods_diff" not in detail


@patch("server.mods.remote_mod_jars", return_value=["old-api.jar"])
@patch("server.mods.local_mod_jars", return_value=["new-api.jar"])
@patch("server.remote.remote_has_instance", return_value=True)
@patch("server.sync.os.path.isdir", return_value=True)
def test_instance_status_different_mods(mock_isdir, mock_has, mock_local, mock_remote):
    computer = {"id": "1", "role": "target", "host": "host1.local", "user": "Kid1"}
    detail = sync_ops.instance_status_detail(computer, "Test Pack", {"1": "online"})
    assert detail["state"] == "different_mods"
    assert detail["mods_diff"]["local_only"] == ["new-api.jar"]
    assert detail["mods_diff"]["remote_only"] == ["old-api.jar"]


@patch("server.remote.remote_has_instance", return_value=False)
@patch("server.sync.os.path.isdir", return_value=False)
def test_instance_status_missing_when_not_on_master(mock_isdir, mock_has):
    computer = {"id": "1", "role": "target", "host": "host1.local", "user": "Kid1"}
    status = sync_ops.instance_status(computer, "Remote Only Pack", {"1": "online"})
    assert status == "missing"


@patch("server.sync._pull_mod_jar", return_value=(True, "Pulled: extra.jar"))
@patch("server.remote.remote_has_instance", return_value=True)
@patch("server.remote.check_reachability", return_value="online")
@patch("server.mods.remote_mod_jars", return_value=["extra.jar"])
@patch("server.mods.local_mod_jars", return_value=[])
@patch("server.sync.os.path.isdir", return_value=True)
def test_apply_pull_remote_only_jars(mock_isdir, mock_local, mock_remote, mock_reach, mock_has, mock_pull):
    computer = {"id": "2", "role": "target", "host": "host3.local", "user": "carer", "label": "host3", "name": "host3"}
    with patch("server.sync._targets_for_ids", return_value=[computer]):
        result = sync_ops.apply_pull(["Test Pack"], ["2"])
    assert "Pulled: extra.jar" in result
    mock_pull.assert_called_once()


def test_instance_sync_mode():
    assert sync_ops._instance_sync_mode(True, True) == "mods_jars"
    assert sync_ops._instance_sync_mode(True, False) == "full_instance"
    assert sync_ops._instance_sync_mode(False, True) == "full_instance"


@patch("server.sync._sync_mods_jars", return_value=(True, "mods", ""))
@patch("server.sync._rsync_instance", return_value=(True, "full", ""))
@patch("server.remote.remote_has_instance")
@patch("server.sync.app_config.load_config")
def test_preview_sync_mods_only_per_target(mock_cfg, mock_has, mock_full, mock_mods):
    computer = {"id": "1", "role": "target", "host": "host1.local", "user": "Kid1", "name": "host1", "order": 1}
    mock_cfg.return_value = {
        "computers": [computer],
        "paths": {"remote_instances_dir": "instances", "remote_icons_dir": "icons"},
    }
    mock_has.side_effect = lambda _computer, name: name == "Existing Pack"
    with patch("server.sync._rsync_icons", return_value=(True, "", "")):
        preview = sync_ops.preview_sync(
            ["Existing Pack", "New Pack"],
            ["1"],
            mods_only=True,
            update_existing=True,
            sync_icons=False,
        )
    assert "Mod jars only (instance exists on target): Existing Pack" in preview
    assert "Full instance sync: New Pack" in preview
    mock_mods.assert_called_once()
    mock_full.assert_called_once()


@patch("server.sync._rsync_mods_jars", return_value=(True, "", ""))
@patch("server.remote.delete_remote_mod_jar", return_value=(True, "Deleted and verified: jei-old.jar"))
@patch("server.mods.remote_mod_jars", return_value=["jei-1.20.1-forge-15.19.0.120.jar"])
@patch("server.mods.local_mod_jars", return_value=["jei-1.20.1-forge-15.20.0.130.jar"])
def test_replace_superseded_mod_jars_apply(mock_local, mock_remote, mock_delete, mock_rsync):
    computer = {"id": "1", "role": "target", "host": "host1.local", "user": "Kid1"}
    ok, stdout, stderr = sync_ops._replace_superseded_mod_jars(computer, "Test Pack", dry_run=False)
    assert ok is True
    assert "Replacing older mod versions:" in stdout
    assert "jei-1.20.1-forge-15.19.0.120.jar" in stdout
    mock_delete.assert_called_once()
    mock_rsync.assert_not_called()


@patch("server.mods.remote_mod_jars", return_value=["jei-1.20.1-forge-15.19.0.120.jar"])
@patch("server.mods.local_mod_jars", return_value=["jei-1.20.1-forge-15.20.0.130.jar"])
def test_replace_superseded_mod_jars_dry_run(mock_local, mock_remote):
    computer = {"id": "1", "role": "target", "host": "host1.local", "user": "Kid1"}
    ok, stdout, stderr = sync_ops._replace_superseded_mod_jars(computer, "Test Pack", dry_run=True)
    assert ok is True
    assert "dry-run: old jars would be deleted and verified before sync" in stdout


@patch("server.sync.subprocess.run")
def test_rsync_mods_jars_includes_only_jars(mock_run):
    mock_run.return_value = type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()
    computer = {"id": "1", "role": "target", "host": "host1.local", "user": "Kid1"}
    with patch("server.sync.os.path.isdir", return_value=True):
        sync_ops._rsync_mods_jars(computer, "Test Pack", dry_run=True)
    args = mock_run.call_args[0][0]
    assert "--include=*.jar" in args
    assert "--exclude=*" in args
    assert args[-2].endswith("/mods/" + os.sep) or args[-2].endswith("/mods" + os.sep)


@patch("server.sync.preview_sync", return_value="preview text")
@patch("server.sync.apply_sync", return_value="apply text")
@patch("server.sync.append_sync_log")
def test_end_to_end_sync_apply(mock_log, mock_apply, mock_preview):
    apply_text = sync_ops.apply_sync(["Test Pack"], ["1"], sync_icons=False, update_existing=False)
    assert apply_text == "apply text"
    preview = sync_ops.preview_sync(["Test Pack"], ["1"], sync_icons=False, update_existing=False)
    assert preview == "preview text"
