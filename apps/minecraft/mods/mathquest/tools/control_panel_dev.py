#!/usr/bin/env python3
"""Serve live MathQuest control-panel assets and proxy API calls to the running mod.

Run from repo root:
    .venv/bin/python3 apps/minecraft/mods/mathquest/tools/control_panel_dev.py

Open:
    http://127.0.0.1:8766/
"""
import http.server
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ASSET_ROOT = Path(__file__).resolve().parents[1] / "fabric/shared/src/main/resources/assets/mathquest"
BIND = os.environ.get("MATHQUEST_PANEL_DEV_BIND", "127.0.0.1")
PORT = int(os.environ.get("MATHQUEST_PANEL_DEV_PORT", "8766"))
TARGET = os.environ.get("MATHQUEST_PANEL_TARGET", "http://127.0.0.1:8765").rstrip("/")

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
}


def static_asset(url_path):
    path = urllib.parse.unquote(url_path.split("?", 1)[0])
    if ".." in path or "\\" in path or path.startswith("//"):
        return None
    if path in ("", "/", "/index.html"):
        return "control_panel/index.html"
    if path.startswith("/npc/") and path.endswith(".png"):
        npc_id = path[len("/npc/"):-len(".png")]
        if not npc_id.replace("_", "").replace("-", "").isalnum():
            return None
        return f"textures/entity/{npc_id}.png"
    if not path.startswith("/") or "/" in path[1:]:
        return None
    name = path[1:]
    if not all(ch.isalnum() or ch in "._-" for ch in name):
        return None
    if Path(name).suffix.lower() not in CONTENT_TYPES:
        return None
    return f"control_panel/{name}"


def safe_resolve(root, relative):
    base = root.resolve()
    target = (base / relative).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        return None
    return target


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/"):
            self.proxy()
            return
        asset = static_asset(self.path)
        if asset:
            path = safe_resolve(ASSET_ROOT, asset)
            if path and path.is_file():
                self.send_file(path)
                return
        self.send_error(404, "Not found")

    def do_POST(self):
        if self.path.startswith("/api/"):
            self.proxy()
            return
        self.send_error(404, "Not found")

    def send_file(self, path):
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream"))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def proxy(self):
        body = None
        headers = {}
        if self.command in ("POST", "PUT", "PATCH"):
            length = int(self.headers.get("Content-Length", "0") or "0")
            body = self.rfile.read(length) if length else b""
            content_type = self.headers.get("Content-Type")
            if content_type:
                headers["Content-Type"] = content_type
        url = TARGET + self.path
        req = urllib.request.Request(url, data=body, headers=headers, method=self.command)
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                payload = res.read()
                self.send_response(res.status)
                for key, value in res.headers.items():
                    if key.lower() in ("connection", "transfer-encoding"):
                        continue
                    self.send_header(key, value)
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(payload)
        except urllib.error.HTTPError as exc:
            payload = exc.read()
            self.send_response(exc.code)
            self.send_header("Content-Type", exc.headers.get("Content-Type", "text/plain; charset=utf-8"))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)
        except Exception as exc:
            payload = f"Proxy error: {exc}".encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} - {fmt % args}")


def main():
    if not ASSET_ROOT.is_dir():
        print(f"Asset root not found: {ASSET_ROOT}", file=sys.stderr)
        return 1
    server = http.server.ThreadingHTTPServer((BIND, PORT), Handler)
    print(f"MathQuest control panel dev server: http://{BIND}:{PORT}/")
    print(f"Static assets: {ASSET_ROOT}")
    print(f"Proxy target: {TARGET}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
