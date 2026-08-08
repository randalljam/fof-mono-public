file: apps/minecraft/prism-sync/SPEC.md
title: Prism Sync Web App — Spec
last-updated: 2026-07-01_1104
ai: Cursor - Claude Opus 4.8
session: use/prism-sync M1 build

Living design spec for the Prism Sync local web app. M1 is implemented; see
[README.md](README.md) for run instructions.


## Goal
Replace the manual `prism-sync.sh` CLI workflow with a **local web app** on **host4**
that shows a computers-by-instances **matrix**: reachability, sync status, and one-click push
of selected Prism Launcher instances to family Macs.


## Locked decisions
- **App folder:** `apps/minecraft/prism-sync/` (script, log, and setup docs moved here;
  `mac-scripts/` retired).
- **Config source of truth:** [computers.toml](computers.toml) — computers, filters, rsync
  excludes, server port. Human reference: [docs/personal/computer-info.md](../../../docs/personal/computer-info.md).
- **Port:** `8770` (configurable in `computers.toml`). **Not** `8765` — that port is used by
  the MathQuest control panel web app when the Fabric/Forge dev server is running.
- **Computers / column order:** `host4` (master), `host1`/`Kid1`, `host3`/`carer`,
  `host2`/`tl-user`, `host5` (disabled placeholder — hostname/user TBD).
- **Stack:** Python + FastAPI + uvicorn; vanilla HTML/CSS/JS frontend; `ssh`/`rsync` shell-out.
- **Refresh:** manual only (no auto-timer). **Check Status:** manual; matrix starts unknown.


## Local ports
Each local app binds its **own** port so they can run at the same time. Only one process can
listen on a given port; if two apps share a port, whichever starts second fails — or, if you
stop one and start another, an old browser tab on that URL will show the **wrong** app after
refresh (what happened when Prism Sync briefly used `8765`).

| Service | Port | URL / notes |
|---------|------|-------------|
| **MathQuest control panel** | **8765** | Web UI when running the MathQuest Fabric/Forge dev server — **reserved** |
| **Prism Sync** (this app) | **8770** | `http://127.0.0.1:8770` — set in [computers.toml](computers.toml) |
| **Math quiz** dev server | **8907** | `http://127.0.0.1:8907/math_quiz.html` |
| **Minecraft** (Fabric/Forge) | **25565** | Game protocol, not HTTP |

**Why 8770?** Chosen after discovering `8765` was already in use by the MathQuest control
panel. `8770` stays in the same “local dev” range but does not collide with 8765, 8907, or
25565.

**To change Prism Sync’s port:** edit `[server] port` in `computers.toml` and restart the
server. Pick a port nothing else on your machine uses.


## Background — shared sync semantics
One-directional push from `~/Library/Application Support/PrismLauncher/instances` (+ icons).
Rsync excludes per-person data: saves, screenshots, logs, crash-reports, options.txt.
Dry-run preview before real sync; skip existing targets unless update-existing is on.
Legacy CLI: [prism-sync.sh](prism-sync.sh).


## Milestone 1 (M1) — matrix web app — **implemented**

### UI
- Top panel: update-existing, icon sync, write-log, include/exclude filters, exclude chips,
  Refresh, Check Status, Sync Selected.
- Per-computer ON/OFF toggles above columns; disabled columns gray out.
- Matrix: local instances (icon + name, A→Z), then remote-only instances below.
- Reachability in column headers (online/offline/unconfigured/checking).
- Cell states: in_sync ✓, differs ≠, missing —, unreachable ?, unknown …
- Row click → status for that instance; multi-select + Sync → preview dialog → apply.


## Architecture

```
apps/minecraft/prism-sync/
  computers.toml
  prism-sync.sh
  _data/prism-sync_log.md
  server/{main,config,prism,remote,sync}.py
  web/{index.html,app.js,styles.css}
  tests/
```

### API
- `GET /api/config`, `/api/instances`, `/api/icon/{instance}`
- `POST /api/reachability`, `/api/status`, `/api/status/instance`
- `POST /api/sync/preview`, `/api/sync/apply`


## Milestone 2 (M2) — mods & saves detail per instance
**Next.** Foldable columns (provisional) to inspect mods and saves per instance. Read-only.


## Milestone 3 (M3) — per-mod view & sync (separate plan)
Select a mod; see which instances have it and latest version; update instances on host4.
Framework-aware (Fabric/Forge). MathQuest is the driving example; code works for any mod.
Warrants a dedicated plan.
