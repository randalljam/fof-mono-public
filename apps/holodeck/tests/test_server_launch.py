import socket

import pytest

from apps.holodeck import server as holodeck_server


def test_is_holodeck_process_matches_known_commands():
    assert holodeck_server.is_holodeck_process(".venv/bin/uvicorn apps.holodeck.server:app --port 8790")
    assert holodeck_server.is_holodeck_process(".venv/bin/python3 apps/holodeck/server.py")
    assert not holodeck_server.is_holodeck_process(".venv/bin/uvicorn other.app:app --port 8790")
def test_listeners_on_port_parses_lsof_output(monkeypatch):
    class Result:
        returncode = 0
        stdout = "12345\n67890\n"
    monkeypatch.setattr(holodeck_server.subprocess, "run", lambda *args, **kwargs: Result())
    assert holodeck_server.listeners_on_port(8790) == [12345, 67890]
def test_confirm_restart_accepts_yes(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "y")
    assert holodeck_server.confirm_restart() is True
def test_confirm_restart_rejects_blank(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    assert holodeck_server.confirm_restart() is False
def test_run_server_leaves_running_server_when_declined(monkeypatch):
    calls = []
    monkeypatch.setattr(holodeck_server, "port_is_open", lambda host, port: True)
    monkeypatch.setattr(holodeck_server, "confirm_restart", lambda: False)
    monkeypatch.setattr(holodeck_server, "kill_holodeck_listeners", lambda port=8790: calls.append("kill"))
    monkeypatch.setattr(holodeck_server.uvicorn, "run", lambda *args, **kwargs: calls.append("run"))
    holodeck_server.run_server()
    assert calls == []
def test_run_server_restarts_when_confirmed(monkeypatch):
    calls = []
    monkeypatch.setattr(holodeck_server, "port_is_open", lambda host, port: True)
    monkeypatch.setattr(holodeck_server, "confirm_restart", lambda: True)
    monkeypatch.setattr(holodeck_server, "kill_holodeck_listeners", lambda port=8790: calls.append("kill"))
    monkeypatch.setattr(holodeck_server, "wait_for_port_free", lambda host, port, timeout=5.0: True)
    monkeypatch.setattr(
        holodeck_server.uvicorn,
        "run",
        lambda app, host, port: calls.append(("run", host, port)),
    )
    holodeck_server.run_server()
    assert calls == ["kill", ("run", holodeck_server.HOLODECK_HOST, holodeck_server.HOLODECK_PORT)]
def test_port_is_open_uses_connect_ex(monkeypatch):
    class FakeSocket:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False
        def settimeout(self, value):
            pass
        def connect_ex(self, address):
            return 0
    monkeypatch.setattr(holodeck_server.socket, "socket", lambda *args, **kwargs: FakeSocket())
    assert holodeck_server.port_is_open("127.0.0.1", 8790) is True
