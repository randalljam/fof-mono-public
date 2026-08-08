file: apps/minecraft/prism-sync/README.md
title: Prism Sync
last-updated: 2026-07-01_0545
ai: Cursor - Claude Opus 4.8
session: use/prism-sync M1 build

Local web app and CLI for pushing Prism Launcher instances from **host4** to the
family Macs. Master machine is the source of truth; targets receive instance folders via
`rsync` over SSH (saves, screenshots, logs, and local options are excluded).


## Quick start (web app)
From the repo root:

```bash
cd apps/minecraft/prism-sync
pip install -r requirements.txt
python -m server.main
```

Open **http://127.0.0.1:8770** in your browser.

Port is configured in [computers.toml](computers.toml). See [SPEC.md](SPEC.md) → **Local ports**
for the port map (Prism Sync **8770**; MathQuest control panel **8765**; math-quiz **8907**;
Minecraft **25565**) and how to change it if needed.


## Legacy CLI
The bash script remains available as a fallback:

```bash
apps/minecraft/prism-sync/prism-sync.sh
apps/minecraft/prism-sync/prism-sync.sh --computer 1 --include "MathQuest Cataclysm"
apps/minecraft/prism-sync/prism-sync.sh --update-existing --skip-prompt --log
```

Sync log (when `--log` or web-app sync with logging enabled):
[_data/prism-sync_log.md](_data/prism-sync_log.md) (local-files mount; shared across worktrees)


## Configuration
Canonical config: [computers.toml](computers.toml)

- Computers, SSH users, enabled flags, column order
- Instance include/exclude filters
- Rsync exclude paths (shown as short labels in the UI)
- Server port

Human reference for hostnames and accounts: [docs/personal/computer-info.md](../../../docs/personal/computer-info.md)


## Tests
```bash
cd apps/minecraft/prism-sync
../../../.venv/bin/pip install -r requirements.txt
../../../.venv/bin/python3 -m pytest tests -v
```

Covers config loading, instance discovery, icon resolution, rsync-output parsing, API smoke
tests, and mocked sync/status paths.


## Docs
- [SPEC.md](SPEC.md) — living design spec (M1 matrix UI; M2/M3 milestones)
- [2026-05-22_prism-sync-setup.md](2026-05-22_prism-sync-setup.md) — family Mac SSH setup
