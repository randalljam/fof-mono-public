file: 2026-06-04_bring-over_kid-games.md
title: Bring-over plan — kid-games repo into fof-mono
last-updated: 2026-06-05_1430
ai: Claude Code (Opus)
session: `kid-games bring-over`

## Purpose
Bring the `kid-games` repo (multi-project workspace: Minecraft mods, Three.js experiments, small games) into `fof-mono`. This is a catch-all repo that gets split per project on import: Minecraft content into `apps/minecraft/`, Robopoli content into the existing `apps/games/robopoli/`, and other small games into `apps/games/`.


## Branch strategy
- **SOURCE** (`kid-games`): branch `export/to-fof-mono` off `main`. Gitignore updated and bulk items untracked. Leave FROZEN after plan approval. Never PR or merge back into source main.
- **TARGET** (`fof-mono`): branch `import/from-kid-games` off `main`. All copying, gitignore changes, doc updates happen here. Never push to main. PR only with explicit approval.


## Current state

### Source repo (kid-games)

- Multi-project workspace. Headline project: **MathQuest** Minecraft Fabric mod. Also contains: Robopoli (Python + web), Three.js dancing/viewer experiments, milestone-web tracker, Skyblock reference materials, Prism Sync scripts.
- On the `export/to-fof-mono` branch: gitignore expanded and bulk items untracked. **242 tracked files, 2.2 MB** (down from ~3000 files / hundreds of MB on main).
- No secrets or API keys found.
- No PII detected.

### Target repo (fof-mono) — existing content that overlaps

- `apps/minecraft/` exists with two files: `enchanments.md` and `rail.md` (Randy's notes — leave untouched per instructions)
- `apps/games/robopoli/` exists with three Python files: `tv_robopoli_code.py`, `tv_robopoli_power-up.py`, `tv_robopoli_power-up-2.py` — **identical** to the root-level Python files in kid-games. No need to re-copy them.
- `apps/games/wingspan/` exists (separate game, unrelated)


## Repo size report — export branch after cleanup

Overall (kid-games export branch, tracked files only):

- **Total tracked**: 242 files, 2.2 MB
- **minecraft/**: 197 files, 1.4 MB (the bulk of the repo)
  - **minecraft/mods/**: 166 files, 0.9 MB
    - **mathquest/**: 129 files, 0.8 MB (excluding _deprecated which is 200 MB of old JARs, now gitignored)
    - **remove-singleplayer/**: 34 files, 0.1 MB
    - **build-and-deploy.py + CLAUDE.md + .gitignore**: 3 files
  - **minecraft/skyblock/**: 26 files, 0.4 MB (excluding 35 MB SkyHanni JAR, now gitignored)
  - **minecraft/ root**: 5 files, 0.1 MB (great railway docs, make_dragon_skin.py, PNG outputs)
- **tv_robopoli/**: 7 files, 0.1 MB (web/3D version — JS + HTML)
- **mac-scripts/**: 3 files, 0.2 MB (Prism Sync for Minecraft)
- **milestone-web/**: 5 files, 0.0 MB
- **dancing-1/2/3/**: 7 files, 0.1 MB total (Three.js experiments)
- **sounds/**: 2 files, 0.2 MB (WAV files for Robopoli)
- **prompts/**: 3 files, 0.0 MB
- **Root files**: 14 files, 0.2 MB (includes items being discarded)

Items removed from tracking (still on disk, not in the export):
- `minecraft/mods/mathquest/_deprecated/` — 200 MB of old build artifacts (JARs, loom-cache)
- `minecraft/skyblock/skyhanni/SkyHanni-7.13.0-mc1.21.11.jar` — 35 MB third-party mod
- `node_modules/` — 34 MB (three.js + live-server)
- `poly-files/` — 12 MB (3D model assets from Three.js era)
- `arnis-tile-cache/` — 11 MB (map tile images)
- `.cursor/`, `.vscode/` — IDE settings


## Flags

- **Secrets/API keys**: NONE detected. No rotation needed.
- **PII**: NONE detected.
- **Large/bulk data**: All large items (deprecated build artifacts, SkyHanni JAR, poly-files, arnis-tile-cache, node_modules) are gitignored and excluded from the bring-over. The 35 MB SkyHanni JAR is a downloadable third-party mod — no need to archive to S3.
- **Vendored deps**: `node_modules/` (three.js + live-server) — DISCARD. No JS apps in the bring-over need them; fof-mono does not ship Three.js content.
- **Build artifacts**: `mathquest/_deprecated/` (201 MB old JARs) — DISCARD. Gradle wrapper JARs (< 100 KB each) are intentionally kept (needed for `./gradlew` bootstrap).
- **Existing duplicates**: The three root-level `tv_robopoli_*.py` files are byte-identical to what's already in `apps/games/robopoli/`. Skip re-copying.


## Per-item disposition

### REPO — Minecraft mods → `apps/minecraft/mods/`

The entire `minecraft/mods/` tree (minus _deprecated and build output) comes over preserving its internal structure. This is the most important content.

- `minecraft/mods/.gitignore` → `apps/minecraft/mods/.gitignore`
- `minecraft/mods/CLAUDE.md` → Becomes `apps/minecraft/mods/AGENTS.md` + `apps/minecraft/mods/CLAUDE.md` (thin reference). See "CLAUDE.md / AGENTS.md migration" section below.
- `minecraft/mods/build-and-deploy.py` → `apps/minecraft/mods/build-and-deploy.py`
- `minecraft/mods/mathquest/` (129 tracked files, 0.8 MB) → `apps/minecraft/mods/mathquest/`
  - Includes: Java source, Gradle build files, wrapper, stubs, targets, tools, docs, CHANGELOG, versions, .mod-build.toml
  - Excludes: `_deprecated/` (gitignored), `logs/` (gitignored), any `build/` or `.gradle/` dirs
- `minecraft/mods/remove-singleplayer/` (34 files, 0.1 MB) → `apps/minecraft/mods/remove-singleplayer/`

### REPO — Minecraft Skyblock → `apps/minecraft/skyblock/`

Reference materials for Hypixel Skyblock gameplay. Small files, useful context.

- `minecraft/skyblock/Skyblock Cooperation and Rules.md` → `apps/minecraft/skyblock/`
- `minecraft/skyblock/tarantula-quest.md` → `apps/minecraft/skyblock/`
- `minecraft/skyblock/minions/` (6 files) → `apps/minecraft/skyblock/minions/`
- `minecraft/skyblock/profile/` (13 files) → `apps/minecraft/skyblock/profile/`
- `minecraft/skyblock/social/` (1 file) → `apps/minecraft/skyblock/social/`
- `minecraft/skyblock/skyhanni/` (4 files, excluding JAR) → `apps/minecraft/skyblock/skyhanni/`
  - The SkyHanni `.jar` (35 MB) is gitignored. The Kotlin examples and architecture doc come over.

### REPO — Minecraft skins → `apps/minecraft/skins/`

Dragon skin script and output PNGs, organized into a dedicated subfolder.

- `minecraft/make_dragon_skin.py` → `apps/minecraft/skins/make_dragon_skin.py`
- `minecraft/pink_dragon_skin.png` → `apps/minecraft/skins/pink_dragon_skin.png`
- `minecraft/pink_dragon_skin_preview.png` → `apps/minecraft/skins/pink_dragon_skin_preview.png`

### REPO — World stories → `apps/minecraft/world-stories/luntr_great-railway/`

Markdown story/prompt files for Minecraft world-building.

- `minecraft/great railway 5.1.md` → `apps/minecraft/world-stories/luntr_great-railway/great railway 5.1.md`
- `minecraft/great railway 6.1.md` → `apps/minecraft/world-stories/luntr_great-railway/great railway 6.1.md`

### REPO — Mac scripts (Prism Sync) → `apps/minecraft/mac-scripts/`

These are specifically for syncing Minecraft Prism Launcher instances across the family Mac fleet. They belong under the Minecraft app umbrella.

- `mac-scripts/2026-05-22_prism-sync.md` → `apps/minecraft/mac-scripts/2026-05-22_prism-sync.md`
- `mac-scripts/Prism Sync Log.md` → `apps/minecraft/mac-scripts/Prism Sync Log.md`
- `mac-scripts/prism-sync.sh` → `apps/minecraft/mac-scripts/prism-sync.sh`

### REPO — TV Robopoli web (3D) → `apps/games/robopoli/`

The web/3D version of Robopoli (Three.js). The fof-mono `apps/games/robopoli/` already has the three Python files; these JS/HTML files go alongside them in the same directory.

- `tv_robopoli/audio.js` → `apps/games/robopoli/audio.js`
- `tv_robopoli/environment.js` → `apps/games/robopoli/environment.js`
- `tv_robopoli/gameState.js` → `apps/games/robopoli/gameState.js`
- `tv_robopoli/tv_robopoli_3d.html` → `apps/games/robopoli/tv_robopoli_3d.html`
- `tv_robopoli/tv_robopoli_3d.js` → `apps/games/robopoli/tv_robopoli_3d.js`
- `tv_robopoli/tv_robopoli_README.md` → `apps/games/robopoli/tv_robopoli_README.md`
- `tv_robopoli/ui.js` → `apps/games/robopoli/ui.js`

### REPO — Sounds → `apps/games/robopoli/sounds/`

Two small WAV files (184 KB total) used by the Robopoli game.

- `sounds/remote_success.wav` → `apps/games/robopoli/sounds/remote_success.wav`
- `sounds/remote_fail.wav` → `apps/games/robopoli/sounds/remote_fail.wav`

Requires gitignore exception: `!apps/games/robopoli/sounds/*.wav` (since `*.wav` is globally ignored in fof-mono).

### REPO — Dancing experiments → `apps/games/3js-expt/`

Three iterations of Three.js character animation experiments. Small files, kid-facing. Each dancing folder preserved as-is under the `3js-expt` umbrella.

- `dancing-1/` → `apps/games/3js-expt/dancing-1/`
- `dancing-2/` → `apps/games/3js-expt/dancing-2/`
- `dancing-3/` → `apps/games/3js-expt/dancing-3/`

### REPO — Milestone web → `apps/family/milestone-web/`

A small web milestone tracker app. Goes under `apps/family/` since it's a family-facing tool.

- `milestone-web/` → `apps/family/milestone-web/`

### REPO — Computer info → `plans/computer-info.md`

Randy's family Mac fleet inventory. Placed in `plans/` as reference documentation.

- `computer-info.md` → `plans/computer-info.md`

### REPO — Prompts → `prompts/kids/`

Prompt templates related to kid activities. Reorganized into `prompts/kids/` subfolder.

- `prompts/kids/pipa-math-lessons-prompt.md` → `prompts/kids/pipa-math-lessons-prompt.md`
- `prompts/kids/youtube channel parent review.md` → `prompts/kids/youtube channel parent review.md`
- `prompts/kids/youtube video parent review.md` → `prompts/kids/youtube video parent review.md`

### REPO — Package manifests → `apps/games/`

Node.js package manifests for Three.js games (dancing, viewers, robopoli web). These are the equivalent of requirements.txt — they define what `npm install` installs.

- `package.json` → `apps/games/package.json`
- `package-lock.json` → `apps/games/package-lock.json`

### REPO — Viewers → `apps/games/viewers/`

Three.js 3D model viewers. Brought over (Randy's decision).

- `viewers/poly-viewer.html` → `apps/games/viewers/poly-viewer.html`
- `viewers/poly-viewer-2.html` → `apps/games/viewers/poly-viewer-2.html`
- `viewers/simple-view.html` → `apps/games/viewers/simple-view.html`

### S3 — 3D model assets → `apps/games/poly-files/`

3D model assets (GLB, FBX, ZIP) from the Three.js era. 12 MB total, ~128 files. Uploaded to S3 (`[S3-FILES-BUCKET]`) at keys matching their fof-mono repo-relative paths. Gitignored locally but kept on disk.

- `poly-files/` (entire directory) → `apps/games/poly-files/`
- S3 key pattern: `s3://[S3-FILES-BUCKET]/apps/games/poly-files/...`

### S3 — Tile cache → `apps/games/arnis-tile-cache/`

Map tile cache images (PNG). 11 MB total, 169 files. Uploaded to S3, gitignored locally.

- `arnis-tile-cache/` (entire directory) → `apps/games/arnis-tile-cache/`
- S3 key pattern: `s3://[S3-FILES-BUCKET]/apps/games/arnis-tile-cache/...`

### REBUILD-LOCAL — Node modules

The `node_modules/` directory (34 MB, three.js + live-server) is recreated by running `npm install` in the directory containing `package.json`. NOT copied from the source repo. Gitignored in fof-mono.

After copying `package.json` and `package-lock.json` to `apps/games/`, run:
```
cd apps/games && npm install
```

### DISCARD — Not brought over

Moved to `discard-not-brought-over/` in kid-games for review.

- `CLAUDE.md` — content migrated to AGENTS.md files (see section below)
- `README.md` — outdated Three.js-era readme, no longer describes the repo
- `scratch.md` — pasted ChatGPT response about Minecraft caving; not code
- `PV EVAC - PLAN 2025-10-11.md` — already moved to fof-mono `plans/` by Randy
- `2025-01-20_cursorrules.md` — legacy Cursor IDE rules; superseded by CLAUDE.md/AGENTS.md
- `repo_size_audit.md` — historical size report; fof-mono has `repo_status.py`
- `repo_size_audit.py` — audit script; fof-mono has `repo_status.py`
- `data/cspell_dictionary_common.txt` — VS Code spell checker data
- `.cursor/rules/mathquest.mdc` — Cursor IDE rule; superseded
- `.cursor/rules-inactive/developer-profile.mdc` — Cursor IDE rule; superseded

Not brought over (stays in source repo as-is):

- `.vscode/` — stays tracked in kid-games for continuity; not copied to fof-mono (fof-mono has its own)
- `.gitignore` — kid-games source gitignore; fof-mono has its own comprehensive one

Already deleted from kid-games (confirmed identical to fof-mono):

- `tv_robopoli_code.py`, `tv_robopoli_power-up.py`, `tv_robopoli_power-up-2.py` — already in `apps/games/robopoli/`

Gitignored (not tracked, not brought over):

- `minecraft/__pycache__/` — Python bytecode cache, auto-regenerated when Python runs .py files
- `minecraft/mods/mathquest/_deprecated/` — 201 MB old build artifacts (JARs, loom-cache from pre-multi-target era)
- `minecraft/skyblock/skyhanni/SkyHanni-7.13.0-mc1.21.11.jar` — 35 MB downloadable third-party mod


## CLAUDE.md / AGENTS.md migration

The kid-games repo has two CLAUDE.md files with substantial operational knowledge:

**Root `CLAUDE.md`** (235 lines) — repo-wide conventions: workflow patterns, branching, mobile-friendly markdown, communication patterns, planning doc format, audio-to-issue-comment loop, etc.

Most of this content is kid-games-repo-specific workflow guidance that does not transfer to fof-mono (fof-mono has its own `AGENTS.md` covering the same topics). Items worth preserving:

- **MathQuest-specific conventions** (task IDs, owner tags, pause-and-handoff, phase gating, playtest check) → migrate to the mod-level AGENTS.md
- **"Randy does not read the code" communication pattern** → already covered by fof-mono AGENTS.md to the degree relevant
- **Mobile-friendly markdown rules** → already in fof-mono AGENTS.md (mobile-friendly markdown is mentioned in PROJECTS.md context)

**`minecraft/mods/CLAUDE.md`** (524 lines) — the most valuable content. Covers: mod layout, active targets, Java versions, Gradle wrappers, nested loader roots, adding targets, build dispatcher, versioning, changelogs, playtest check, hosting/infra, and mod-specific "don'ts."

Plan:
1. Convert `minecraft/mods/CLAUDE.md` → `apps/minecraft/mods/AGENTS.md` (rename, preserve content)
2. Create a thin `apps/minecraft/mods/CLAUDE.md` that says `@AGENTS.md` (same pattern as root CLAUDE.md → AGENTS.md)
3. The content is mod-specific and self-contained — no need to merge into the root AGENTS.md
4. Update any kid-games-specific references (paths, branch conventions) to match fof-mono conventions


## fof-mono changes (import branch)

### 1. Create `apps/minecraft/mods/` with source code

Copy all REPO-disposition Minecraft mod files preserving the directory structure. The existing `apps/minecraft/enchanments.md` and `apps/minecraft/rail.md` are left untouched.

### 2. Create `apps/minecraft/skyblock/`, `apps/minecraft/mac-scripts/`, `apps/minecraft/skins/`, `apps/minecraft/world-stories/`

New subdirectories under `apps/minecraft/`.

### 3. Add Robopoli web content to `apps/games/robopoli/`

JS/HTML files go directly alongside the existing Python files (no `web/` subfolder).

### 4. Create `apps/games/3js-expt/`, `apps/family/milestone-web/`

New subdirectories: Three.js experiments under games, milestone tracker under family.

### 5. Add `plans/computer-info.md`

Single file addition to existing `plans/` area.

### 6. Add prompts to `prompts/kids/`

Three prompt templates moved to `prompts/kids/` subfolder.

### 7. Add viewers to `apps/games/viewers/`

Three HTML model viewer files.

### 8. Add package manifests to `apps/games/`

`package.json` and `package-lock.json` for Three.js dependencies. These define what `npm install` installs.

### 9. S3 setup for poly-files and arnis-tile-cache

- Add gitignore rules for `apps/games/poly-files/` and `apps/games/arnis-tile-cache/` BEFORE copying data
- Copy the files locally to those paths (they live on disk, gitignored)
- Set up S3 manifests and upload to `[S3-FILES-BUCKET]` bucket using `core/s3_archive.py`
- S3 keys: `apps/games/poly-files/...` and `apps/games/arnis-tile-cache/...` (1:1 with repo paths)
- IF AWS creds are not available in this session, hand Randy a punch-list of upload/verify commands

### 10. Gitignore additions

Add to fof-mono `.gitignore`:
```
# robopoli: small UI sound effects, keep in repo despite global *.wav rule
!apps/games/robopoli/sounds/*.wav

# S3-backed asset directories (uploaded to [S3-FILES-BUCKET], gitignored locally)
apps/games/poly-files/
apps/games/arnis-tile-cache/
```

The `apps/minecraft/mods/.gitignore` from kid-games covers Gradle/build artifacts and will be copied as-is.

### 11. AGENTS.md migration

- Convert `minecraft/mods/CLAUDE.md` → `apps/minecraft/mods/AGENTS.md`
- Create thin `apps/minecraft/mods/CLAUDE.md` with `@AGENTS.md` reference
- Update internal path references from `minecraft/mods/` to `apps/minecraft/mods/`

### 12. Update fof-mono AGENTS.md (Directory guide)

Add entries:
- `apps/minecraft/mods/` — Minecraft Fabric mods (MathQuest, remove-singleplayer); each subfolder is an independent multi-target Gradle build. Has its own AGENTS.md.
- `apps/minecraft/skyblock/` — Hypixel Skyblock reference materials (rules, minion optimizer, profiles, SkyHanni examples)
- `apps/minecraft/mac-scripts/` — Prism Launcher sync scripts for the family Mac fleet
- `apps/minecraft/skins/` — dragon skin script and PNG outputs
- `apps/minecraft/world-stories/` — Minecraft world-building story prompts
- `apps/games/3js-expt/` — Three.js character animation experiments (dancing-1/2/3)
- `apps/family/milestone-web/` — web milestone tracker app
- `apps/games/viewers/` — Three.js 3D model viewers

Update existing entries:
- `apps/minecraft/` — expand description to note mods/, skyblock/, mac-scripts/, skins/, world-stories/ subdirs
- `apps/games/` — add 3js-expt, viewers alongside existing robopoli, wingspan
- `apps/family/` — add milestone-web alongside existing Kid1, reading

### 13. Update PROJECTS.md

Add entries for Minecraft mods area and update the games entries.

### 14. Per-app AGENTS.md

Only `apps/minecraft/mods/` gets its own AGENTS.md (migrated from kid-games `minecraft/mods/CLAUDE.md`). The other apps are too small to need one.

### 15. Dependencies and environment setup

- **Node.js**: `package.json` and `package-lock.json` are REPO at `apps/games/`. After import, run `cd apps/games && npm install` to recreate `node_modules/`. The `node_modules/` directory is already globally gitignored in fof-mono. See "Follow-up steps" section below.
- **Java/Gradle**: Self-contained via Gradle wrapper. No setup needed beyond JDK installation (see mod AGENTS.md for version requirements per target).
- **Python**: No new Python dependencies needed.

### 16. Tests

MathQuest has Java unit tests (ConfigTest, DatabaseTest, QuizManagerTest, SessionExporterTest, StandaloneTestRunner) that run via Gradle. They are self-contained and will work as-is after the copy. No test retargeting needed.

### 17. Known code path issues

- `apps/minecraft/skins/make_dragon_skin.py` — may have import paths that need updating. Non-blocking: it's a standalone script.
- `apps/minecraft/skyblock/minions/redstone_minion_optimizer.py` — standalone script, should work as-is.
- `apps/minecraft/skyblock/profile/fetch_skycrypt_profile.js` — standalone Node.js script. Will need `npm install` to run.
- `apps/minecraft/mac-scripts/prism-sync.sh` — uses absolute paths to `~/Library/Application Support/`; machine-specific, works as-is on Randy's Macs.
- The Three.js apps (3js-expt/dancing, robopoli web, viewers) need `three.js` installed via `npm install` or loaded from CDN. These are archived experiments — they'll work after running `npm install` in `apps/games/`.


## Execution checklist (Phase 4)

Source organization in kid-games `export/to-fof-mono` branch now matches fof-mono target layout. Phase 4 is a direct copy from kid-games into fof-mono.

- [x] Source `export/to-fof-mono` branch: stepwise organization complete. Commit and leave FROZEN.
- [x] fof-mono `import/from-kid-games` branch: copy all REPO files (235 files, 2.2 MB)
- [x] fof-mono: add gitignore rules for S3 directories + robopoli sounds exception + SkyHanni JAR + _deprecated
- [x] fof-mono: convert mods CLAUDE.md → AGENTS.md + thin CLAUDE.md (path refs updated)
- [x] fof-mono: update AGENTS.md directory guide
- [x] fof-mono: update PROJECTS.md
- [x] fof-mono: verify no data files slipped into git (caught and removed _deprecated JARs + SkyHanni JAR)
- [x] fof-mono: add S3 area definitions to `core/s3_archive.py` EXTRA_AREAS (games_poly-files, games_arnis-tile-cache)
- [x] fof-mono: npm install in `apps/games/` (193 packages; 4 platform-specific native modules differ Linux vs macOS — expected)
- [x] fof-mono: commit on import branch
- [x] fof-mono: functional test — MathQuest mod build (see follow-up steps)
- [x] S3: copy poly-files and arnis-tile-cache to fof-mono disk, build manifests, upload (see S3 punch-list below)
- [ ] ASK Randy's permission to open PR


## S3 upload punch-list (run locally with AWS creds)

This session has no AWS credentials. Run these commands locally on a machine with `boto3` configured for the `[S3-FILES-BUCKET]` bucket. Follow the guide at `plans/2026-04-09_repos-reorg/bring-over-s3-upload-guide.md`.

**Prerequisites**: fof-mono venv active, AWS creds configured, kid-games repo accessible.

### Step 1: Copy S3-disposition files from kid-games to fof-mono (gitignored paths)
```bash
# From the fof-mono repo root:
cp -r /path/to/kid-games/poly-files apps/games/poly-files
cp -r /path/to/kid-games/arnis-tile-cache apps/games/arnis-tile-cache

# Verify gitignored:
git status  # should NOT show poly-files or arnis-tile-cache as untracked
```

### Step 2: Build manifests
```bash
.venv/bin/python3 core/s3_archive.py build --area games_poly-files
.venv/bin/python3 core/s3_archive.py build --area games_arnis-tile-cache
```

### Step 3: Dry-run upload (review output)
```bash
.venv/bin/python3 core/s3_archive.py upload --area games_poly-files
.venv/bin/python3 core/s3_archive.py upload --area games_arnis-tile-cache
```

### Step 4: Execute upload
```bash
.venv/bin/python3 core/s3_archive.py upload --area games_poly-files --execute
.venv/bin/python3 core/s3_archive.py upload --area games_arnis-tile-cache --execute
```

### Step 5: Verify
```bash
.venv/bin/python3 core/s3_archive.py verify --area games_poly-files --execute --redownload --sample 10
.venv/bin/python3 core/s3_archive.py verify --area games_arnis-tile-cache --execute --redownload --sample 10
```

### Step 6: Check status
```bash
.venv/bin/python3 core/s3_archive.py status --area games_poly-files
.venv/bin/python3 core/s3_archive.py status --area games_arnis-tile-cache
```

### Step 7: Commit manifests
```bash
git add plans/2026-04-09_repos-reorg/s3_manifests/games_poly-files.manifest.jsonl
git add plans/2026-04-09_repos-reorg/s3_manifests/games_arnis-tile-cache.manifest.jsonl
git commit -m "Add S3 manifests for kid-games poly-files and arnis-tile-cache"
```


## Follow-up steps (post-import)
- [x] **npm install**: Run `cd apps/games && npm install` — 193 packages installed. 4 platform-specific native modules (fsevents, bindings, nan, file-uri-to-path) are macOS-only and expected to be absent on Linux.
- [x] **Verify node_modules**: Compared fof-mono (147 packages) vs kid-games (151 packages). The 4 differences are all platform-specific native modules — no real discrepancies.
- [x] **Functional test — MathQuest build**: On Randy's Mac, run `./apps/minecraft/mods/build-and-deploy.py mathquest --target fabric-26.1.2` and confirm the build succeeds. This validates the imported mod tooling works at its new path.
_ran again after fixing /data folder change to /persistence_
- [x] **Environment setup**: Verify JDK availability for Minecraft mod builds (Java 21 for fabric-1.21.11, Java 25 for fabric-26.1.2) on Randy's Mac.
- [x] **S3 upload**: Run the S3 punch-list above to upload `poly-files/` and `arnis-tile-cache/` to `[S3-FILES-BUCKET]` bucket.


## Troubleshooting
### Java `data/` package silently ignored by root `.gitignore`
**Symptom:** MathQuest build fails with `package com.kidgames.mathquest.data does not exist` after import. The Java source files (`QuizDatabase.java`, `SessionExporter.java`) exist on disk but are not tracked by git — `git status` doesn't show them, and `git add` silently skips them.

**Root cause:** The fof-mono root `.gitignore` contains a `data/` rule (line ~129) intended for S3 corpus data. Git's directory-matching ignores `data/` at **any** depth, so the Java package directory `com/kidgames/mathquest/data/` was caught. The `cp -r` from kid-games copied the files to disk, but every subsequent `git add` silently skipped them.

**Why it was hard to spot:** `git add .` and `git add -A` don't warn when files are skipped by gitignore. The build worked on Randy's local machine (where the local agent had copied the files directly to disk), but the files were never committed, so any fresh checkout would fail.

**Fix applied:** Renamed the Java package from `com.kidgames.mathquest.data` to `com.kidgames.mathquest.persistence`. This avoids the `data/` gitignore collision entirely. Updated `package` declarations in `QuizDatabase.java` and `SessionExporter.java`, and updated all `import` statements in 7 files across `fabric/` and `targets/fabric-26.1.2/`.

**Prevention rule added:** AGENTS.md now states that `data/` is reserved exclusively for gitignored data files. Source code packages must use a different name (e.g. `persistence/`, `storage/`, `datamodel/`).

**Diagnosis command:** To check if a path is caught by gitignore: `git check-ignore -v <path>`. Exit code 0 = ignored (bad for source files); exit code 1 = not ignored (good).

