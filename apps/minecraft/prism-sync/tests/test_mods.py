"""Tests for mod jar filename comparison."""
import os
import sys

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from server import mods as mods_ops


def test_mod_jar_slug():
    assert mods_ops.mod_jar_slug("jei-1.20.1-forge-15.20.0.130.jar") == "jei"
    assert mods_ops.mod_jar_slug("fabric-api-0.138.4+1.21.10.jar") == "fabric-api"


def test_superseded_replacements():
    local = ["jei-1.20.1-forge-15.20.0.130.jar", "sodium-fabric-0.7.3+mc1.21.10.jar"]
    remote = [
        "jei-1.20.1-forge-15.19.0.120.jar",
        "sodium-fabric-0.7.3+mc1.21.10.jar",
        "alexsmobs-1.22.9.jar",
    ]
    rows = mods_ops.superseded_replacements(local, remote)
    assert len(rows) == 1
    assert rows[0]["remote_jar"] == "jei-1.20.1-forge-15.19.0.120.jar"
    assert rows[0]["local_jar"] == "jei-1.20.1-forge-15.20.0.130.jar"


def test_compare_mod_jars_same():
    jars = ["fabric-api-0.92.0.jar", "sodium-0.5.0.jar"]
    state, diff = mods_ops.compare_mod_jars(jars, list(jars))
    assert state == "same_mods"
    assert diff is None


def test_compare_mod_jars_different():
    local = ["fabric-api-0.92.0.jar", "sodium-0.5.0.jar"]
    remote = ["fabric-api-0.91.0.jar", "sodium-0.5.0.jar"]
    state, diff = mods_ops.compare_mod_jars(local, remote)
    assert state == "different_mods"
    assert diff["local_only"] == ["fabric-api-0.92.0.jar"]
    assert diff["remote_only"] == ["fabric-api-0.91.0.jar"]


def test_local_mods_tooltip_text():
    assert "  (none)" in mods_ops.local_mods_tooltip_text([])
    text = mods_ops.local_mods_tooltip_text(["alpha.jar", "beta.jar"])
    assert "mods/ on host4:" in text
    assert "  alpha.jar" in text


def test_mods_push_diff_lines_removed_and_added():
    lines = mods_ops.mods_push_diff_lines(
        ["old-mod-1.23.jar"],
        ["new-mod-1.24.jar"],
        ["new-mod-1.24.jar"],
        True,
    )
    text = "\n".join(lines)
    assert "Target mods/ before: old-mod-1.23.jar" in text
    assert "Target mods/ after: new-mod-1.24.jar" in text
    assert "Removed from target (rsync --delete):" in text
    assert "  - old-mod-1.23.jar" in text
    assert "  + new-mod-1.24.jar" in text


def test_mods_diff_tooltip():
    text = mods_ops.mods_diff_tooltip({
        "local_only": ["a.jar"],
        "remote_only": ["b.jar"],
    })
    assert "Only on host4:" in text
    assert "  a.jar" in text
    assert "Only on target:" in text
    assert "  b.jar" in text
