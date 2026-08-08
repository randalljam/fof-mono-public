"""Tests for Prism Sync config loading."""
import os
import sys

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from server import config as app_config


def test_load_config_computers_order():
    cfg = app_config.load_config(force_reload=True)
    computers = cfg["computers"]
    assert computers[0]["role"] == "master"
    assert computers[0]["id"] == "master"
    labels = [row["label"] for row in computers]
    assert labels == ["host4", "host1", "host3", "host2", "host5"]


def test_rsync_exclude_labels():
    labels = app_config.rsync_exclude_labels()
    assert "saves" in labels
    assert "options.txt" in labels


def test_instance_name_filters():
    assert app_config.instance_name_matches_filters("26.1.2 MathQuest")
    assert not app_config.instance_name_matches_filters("26.1.2 _Base Template")
    assert app_config.instance_name_matches_filters("MathQuest Cataclysm", includes=["MathQuest"])
    assert not app_config.instance_name_matches_filters("Skyhanni", includes=["MathQuest"])


def test_public_config_port():
    public = app_config.public_config()
    assert public["port"] == 8770
    assert any(row["role"] == "master" for row in public["computers"])
