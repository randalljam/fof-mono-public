file: docs/README.md
title: Docs hub — local server
last-updated: 2026-07-09_0735
ai: Cursor - Composer 2.5 Fast
session: `Docs server setup`

# Docs hub — local server

Lightweight static server for browsing interactive HTML documentation and research sites from your laptop, phone, or iPad on the same Wi-Fi network.


## Quick start

From the repo root:

```bash
python3 docs/docs_server.py
```

Then open:

- **This machine:** [http://127.0.0.1:8910/docs/](http://127.0.0.1:8910/docs/)
- **Phone / iPad (same Wi-Fi):** `http://<your-mac-lan-ip>:8910/docs/` — the server prints the LAN URL on startup.

The hub page is `docs/index.html`. It links to other `index.html` sites anywhere in the repo (under `docs/`, app folders, etc.).


## Configuration

Environment variables (all optional):

| Variable | Default | Purpose |
|----------|---------|---------|
| `DOCS_PORT` | `8910` | TCP port |
| `DOCS_BIND` | `0.0.0.0` | Bind address; use `127.0.0.1` to block LAN access |
| `DOCS_PREVENT_SLEEP` | `1` on macOS | Runs `caffeinate` so the Mac stays awake while serving |

Example — laptop only, different port:

```bash
DOCS_BIND=127.0.0.1 DOCS_PORT=9000 python3 docs/docs_server.py
```


## Adding or updating hub links

Edit **`docs/index.html`**. Each doc is a large button in the `.grid` section.

Copy this block for each new site:

```html
<a class="doc-btn" href="/path/from/repo/root/index.html">
  Short label
  <span>Optional subtitle</span>
</a>
```

Rules:

- **`href`** must be a repo-root path starting with `/` (e.g. `/docs/2026-07-01_repo-snapshot-oss-discovery/index.html`, `/docs/research/graphs/index.html`).
- **`Short label`** is the main button text (what you tap on a phone).
- **`span`** subtitle is optional; keep it brief.

Current entries:

| Label | Path |
|-------|------|
| Snapshot 07-01 | `/docs/2026-07-01_repo-snapshot-oss-discovery/index.html` |
| Web Stacks | `/docs/2026-07-01_repo-snapshot-oss-discovery/webstacks.html` |
| Graphs | `/docs/research/graphs/index.html` |

### Instructions for an agent

When asked to add a hub link:

1. Confirm the target `index.html` exists (or create it first if that was requested).
2. Open `docs/index.html` and add a new `<a class="doc-btn" …>` inside `<div class="grid">`.
3. Use a repo-root `href` (not a relative path from `docs/`).
4. Update the table in this README if you are already editing it.
5. Do not change `docs/docs_server.py` unless the new site needs a non-standard URL layout.


## What gets served

The server exposes the **entire repo root** as static files. Only paths that resolve to real files (or `index.html` inside a directory) are returned. Path traversal outside the repo is rejected.

Entry routes:

- `/`, `/docs`, `/docs/` → `docs/index.html`

Local dev only — do not deploy this script to production infrastructure.
