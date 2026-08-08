#!/usr/bin/env python3
"""Lightweight LAN-friendly static server for interactive HTML docs across the repo.

Run from anywhere in the repo:
    python3 docs/docs_server.py
    # http://127.0.0.1:8910/docs/          (laptop)
    # http://<lan-ip>:8910/docs/           (phone/iPad on same Wi-Fi)

Serves the whole repo root so links can reach docs/ and other HTML sites.

Config (env):
  DOCS_PORT          default 8910
  DOCS_BIND          default "0.0.0.0"  (use 127.0.0.1 to block LAN access)
  DOCS_PREVENT_SLEEP default "1" on macOS

On start, frees DOCS_PORT if something is already listening (same pattern as
apps/math-quiz/tools/dev_server.py), so a restart always serves this checkout.
"""
import http.server
import os
import signal
import socket
import socketserver
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

PORT = int(os.environ.get("DOCS_PORT", "8910"))
BIND = os.environ.get("DOCS_BIND", "0.0.0.0")
PREVENT_SLEEP = os.environ.get("DOCS_PREVENT_SLEEP", "1" if sys.platform == "darwin" else "0").lower() not in ("0", "false", "no")
_caffeinate_proc = None

def _repo_root():
    """Walk up from this script until we find the monorepo root."""
    here = Path(__file__).resolve().parent
    for parent in [here, *here.parents]:
        if (parent / "AGENTS.md").exists() and (parent / "docs").is_dir():
            return parent
    return here.parent

REPO_ROOT = _repo_root()
DOCS_INDEX = REPO_ROOT / "docs" / "index.html"

### Port takeover (same pattern as math-quiz tools/dev_server.py)
def _pids_listening_on(port):
    """Return PIDs listening on TCP port (excludes this process). Needs lsof."""
    try:
        out = subprocess.check_output(
            ["lsof", f"-tiTCP:{port}", "-sTCP:LISTEN"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    pids = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            pid = int(line)
        except ValueError:
            continue
        if pid != os.getpid():
            pids.append(pid)
    return pids
def _free_port(port):
    """Stop whatever is already listening on port so a plain restart just works."""
    pids = _pids_listening_on(port)
    if not pids:
        return
    for pid in pids:
        try:
            print(f"Port {port} in use by pid {pid} — stopping it.")
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        except PermissionError as exc:
            print(f"Could not stop pid {pid}: {exc}")
            raise SystemExit(1) from exc
    deadline = time.time() + 3.0
    while time.time() < deadline:
        if not _pids_listening_on(port):
            return
        time.sleep(0.1)
    for pid in _pids_listening_on(port):
        try:
            print(f"Port {port} still held by pid {pid} — force-killing.")
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    time.sleep(0.2)
    if _pids_listening_on(port):
        print(f"Port {port} is still in use after kill; exiting.")
        raise SystemExit(1)

def _start_sleep_guard():
    global _caffeinate_proc
    if not PREVENT_SLEEP or sys.platform != "darwin":
        return
    try:
        _caffeinate_proc = subprocess.Popen(
            ["caffeinate", "-i", "-w", str(os.getpid())],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print("Mac sleep disabled while server is running (caffeinate). Ctrl+C to stop both.")
    except Exception as exc:
        print(f"Note: could not disable sleep ({exc}) — keep the Mac awake manually.")

def _stop_sleep_guard():
    global _caffeinate_proc
    if _caffeinate_proc and _caffeinate_proc.poll() is None:
        _caffeinate_proc.terminate()
        _caffeinate_proc.wait(timeout=2)
    _caffeinate_proc = None

def _lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and ip != "127.0.0.1":
            return ip
    except Exception:
        pass
    return None

def _safe_repo_path(url_path):
    """Map a URL path to a file under REPO_ROOT; reject traversal."""
    clean = url_path.split("?", 1)[0].split("#", 1)[0]
    if clean in ("", "/"):
        return DOCS_INDEX
    rel = clean.lstrip("/")
    candidate = (REPO_ROOT / rel).resolve()
    try:
        candidate.relative_to(REPO_ROOT.resolve())
    except ValueError:
        return None
    if candidate.is_dir():
        index = candidate / "index.html"
        if index.is_file():
            return index
        return None
    if candidate.is_file():
        return candidate
    return None

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[docs] {self.address_string()} - {fmt % args}")
    def _send_file(self, path):
        suffix = path.suffix.lower()
        if suffix == ".html":
            content_type = "text/html; charset=utf-8"
        elif suffix == ".css":
            content_type = "text/css; charset=utf-8"
        elif suffix in (".js", ".mjs"):
            content_type = "text/javascript; charset=utf-8"
        elif suffix == ".json":
            content_type = "application/json; charset=utf-8"
        elif suffix in (".png",):
            content_type = "image/png"
        elif suffix in (".jpg", ".jpeg"):
            content_type = "image/jpeg"
        elif suffix == ".svg":
            content_type = "image/svg+xml"
        elif suffix == ".webp":
            content_type = "image/webp"
        elif suffix == ".woff2":
            content_type = "font/woff2"
        else:
            content_type = "application/octet-stream"
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        if suffix in (".html", ".js", ".mjs", ".css"):
            self.send_header("Cache-Control", "no-cache, must-revalidate")
        self.end_headers()
        self.wfile.write(data)
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/docs", "/docs/"):
            if DOCS_INDEX.is_file():
                return self._send_file(DOCS_INDEX)
            self.send_error(404, "docs/index.html not found")
            return
        target = _safe_repo_path(parsed.path)
        if not target:
            self.send_error(404, "Not found")
            return
        return self._send_file(target)

if __name__ == "__main__":
    _free_port(PORT)
    print(f"Docs server (bind {BIND}): http://127.0.0.1:{PORT}/docs/")
    lan = _lan_ip()
    if lan and BIND != "127.0.0.1":
        print(f"  On your phone (same Wi-Fi): http://{lan}:{PORT}/docs/")
    print(f"Serving repo root: {REPO_ROOT}")
    _start_sleep_guard()
    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer((BIND, PORT), Handler) as httpd:
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\nstopped")
    finally:
        _stop_sleep_guard()
