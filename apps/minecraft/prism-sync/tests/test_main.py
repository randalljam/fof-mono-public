"""FastAPI endpoint smoke tests with mocked remote/sync operations."""
import os
import sys
from unittest.mock import patch

from fastapi.testclient import TestClient

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from server.main import app

client = TestClient(app)


def test_get_config():
    response = client.get("/api/config")
    assert response.status_code == 200
    payload = response.json()
    assert payload["port"] == 8770
    assert payload["computers"][0]["role"] == "master"


def test_get_status_health():
    response = client.get("/api/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["service"] == "prism-sync"


@patch("server.remote.check_all_reachability", return_value={"master": "online", "1": "offline"})
def test_post_reachability(mock_check):
    response = client.post("/api/reachability", json={"computer_ids": ["master", "1"]})
    assert response.status_code == 200
    assert response.json()["reachability"]["1"] == "offline"


@patch("server.sync.preview_sync", return_value="dry-run output")
@patch("server.sync.apply_sync", return_value="real output")
@patch("server.sync.append_sync_log")
def test_post_sync_apply(mock_log, mock_apply, mock_preview):
    response = client.post("/api/sync/apply", json={
        "instance_names": ["Test Pack"],
        "computer_ids": ["1"],
        "update_existing": False,
        "sync_icons": True,
        "write_log": True,
    })
    assert response.status_code == 200
    payload = response.json()
    assert "dry-run output" in payload["preview"]
    assert payload["apply"] == "real output"
    mock_log.assert_called_once()
