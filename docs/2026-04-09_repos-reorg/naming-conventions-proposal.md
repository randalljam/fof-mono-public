file: naming-conventions-proposal.md
title: Naming conventions — scan, proposed renames, rollout
last-updated: 2026-06-03_0727
ai: Cursor - Composer 2.5 Fast
session: `File naming conventions`


## Purpose
Inventory current underscore vs dash usage after the repo reorg; propose renames to align `apps/` and docs with a single convention; record what must stay snake_case for Python.


## Conventions (target state)

| Namespace | Rule | Example |
|-----------|------|---------|
| **App / service directories** | kebab-case (dashes between words) | `apps/ads-scrape/`, `apps/repo-mirror/` |
| **Python modules, packages, tests** | snake_case (underscores) — PEP 8; dashes are not importable | `core/s3_archive.py`, `apps/math_quiz/math_quiz.py`, `test_fileops.py` |
| **Plans / docs filenames** | `YYYY-MM-DD_slug-with-dashes.ext`; underscore separates **fields**, dash separates **words within a field** | `2026-06-01_repo-status.md`, `2026-04-09_repos-reorg/` |
| **Structured data / manifest tokens** | underscore between fields; dash within multi-word field values | `exchanges_qrag_fda-c19-townhalls.manifest.jsonl`, `qrag-exch_2025-01-19_114538.json` |
| **Stable index files** | short fixed names OK (no date prefix) | `PROJECTS.md`, `PROFILE.md`, `AGENTS.md` |

Leading `_` or `_archive` = retired / internal / private — unrelated to word separators.


## Explicit exception: `apps/math_quiz/`

**Do not rename** — leave `apps/math_quiz/` entirely as-is (folder name, internal paths, filenames). This is the one intentional snake_case app directory.

Reason: a separate MathQuiz repo was forked from this folder and developed independently. That repo will be merged back here and will overhaul this app. Keeping the current tree untouched avoids churn and path conflicts before the bring-over.


## Pre-rename verification: Python imports (2026-06-03)

Before kebab-casing the four app **directories**, confirm nothing imports them as Python packages (`from apps.ads_scrape import ...` — dashes are invalid in import paths).

```bash
grep -rnE "(from|import)[[:space:]]+apps\.(ads_scrape|live_transcript|meta_coder|smol_podcaster)" \
  --include='*.py' .
```

**Result: no matches** (grep exit 1). Also checked: no `__init__.py` under any of the four dirs; no `import meta_coder`-style bare imports; only path **strings** (e.g. `apps/meta_coder/cursor_chat_logs` default arg in `meta_coder.py`).

→ Kebab-case directory renames are safe from an import perspective; update path strings only.


## `apps/` top-level — proposed renames

| Current | Proposed | Action |
|---------|----------|--------|
| `ads_scrape` | `ads-scrape` | **Rename** |
| `live_transcript` | `live-transcript` | **Rename** |
| `meta_coder` | `meta-coder` | **Rename** |
| `smol_podcaster` | `smol-podcaster` | **Rename** |
| `math_quiz` | — | **Keep** (exception — see above) |
| `deutsch` | — | Keep (single word) |
| `family` | — | Keep |
| `games` | — | Keep |
| `minecraft` | — | Keep |
| `qrag` | — | Keep |
| `repo-mirror` | — | Keep (already kebab) |
| `scratch` | — | Keep |
| `transcription` | — | Keep |
| `voice` | — | Keep |

**New apps:** use kebab-case under `apps/` from here on (except any pre-declared merge targets like `math_quiz`).


## `apps/` nested — optional (lower priority)

| Current | Proposed | Notes |
|---------|----------|-------|
| `live_transcript/flask_starter` | `live-transcript/flask-starter` | Follows parent rename; few references |
| `games/robo-polly` | — | Already kebab |
| `games/wingspan` | — | Single word |
| `math_quiz/**` | — | **No changes** — entire tree frozen until external-repo merge |
| `meta_coder/cursor_chat_logs` | keep `cursor_chat_logs` | Python-adjacent data dir |

Do **not** rename Python entrypoints inside apps (`math_quiz.py`, `meta_coder.py`, `smol_podcaster.py`, etc.) — only directory paths and string references to those paths (for the four apps being renamed).


## Reference update scope (folder renames only)

Approximate tracked references to update when each top-level app folder is renamed:

| App folder | Ref count (repo-wide) | Hot spots |
|------------|----------------------|-----------|
| `meta_coder` | ~15 | **`apps/meta_coder/meta_coder.py`** — `folder_path` default (required); `cloc_paths.txt`, requirements comments, plans |
| `ads_scrape` | ~10 | `cloc_paths.txt`, `cloc_report.md`, `PROJECTS.md`, plans |
| `live_transcript` | ~5 | plans, `AGENTS.md`, `PROJECTS.md` |
| `smol_podcaster` | ~5 | plans, `AGENTS.md`, `PROJECTS.md` |
| `math_quiz` | — | **Out of scope** — no renames |

Also update after renames: `AGENTS.md`, `plans/2026-04-09_repos-reorg/PROJECTS.md`, `cloc_paths.txt`. **No S3 manifest changes** for these four app renames (see S3 section below).


## Do not rename (Python / import surface)

These stay snake_case — changing them breaks imports or PEP 8 expectations:

- All of `core/*.py` (e.g. `s3_archive.py`, `webflow_api.py`, `transcript_eval.py`)
- All of `tests/test_*.py`
- App Python modules: `math_quiz.py`, `meta_coder.py`, `smol_podcaster.py`, `scrape_ads.py`, etc.
- Chalice mirror targets under `chalicelib/` (edited only via `core/`)
- `plans/2026-04-09_repos-reorg/repo_status.py`

Lambda **deploy folder** names under `apps/qrag/api/` and `web-shared/aws_chalice/` are already kebab-case (`qrag-llm`, `hash-store`, `hmac-hash`, `send-email`) — no change.


## `plans/2026-04-09_repos-reorg/` — doc filename outliers

Files without a `YYYY-MM-DD_` prefix (stable indexes — **keep as-is**):

- `PROFILE.md`, `PROJECTS.md`, `REPOS.md`, `MOVE_MANIFEST.md`
- `ai-coding-system-dev.md` (already kebab; living devlog)
- `s3_manifests/` directory and `*.manifest.jsonl` entries — **do not rename** manifest files without updating `core/s3_archive.py` area `name` keys (see S3 section). Filenames already mix field underscores + kebab (`exchanges_qrag_fda-c19-townhalls.manifest.jsonl`).

**Optional renames** (cosmetic docs only — no effect on upload tooling):

| Current | Proposed |
|---------|----------|
| `bring-over-code-playbook.md` | `2026-06-03_bring-over-code-playbook.md` |
| `s3_archive_manifest_README.md` | `s3-archive-manifest_README.md` |

**Legacy `plans/` root** (outside reorg folder): many `PLAN_*`, spaced names, and undated files — defer; migrate opportunistically or in a separate cleanup. Not blocking app-folder renames.


## Suggested rollout order

1. **Document** — `AGENTS.md` naming + doc-header sections (done in same session as this file).
2. **Four app renames** — `ads-scrape`, `live-transcript`, `smol-podcaster`, `meta-coder` (`git mv` + update path strings and docs below). No S3 follow-up for these.
3. **Optional doc renames** in reorg folder when convenient (not `s3_manifests/*.manifest.jsonl`).
4. **`math_quiz`** — no rename step; handle when the external MathQuiz repo is brought over per `bring-over-code-playbook.md`.

Use `git mv` for directory renames to preserve history.


### Rollout checklist (step 2) — DONE 2026-06-03

**`git mv` (four dirs):**
- [x] `apps/ads_scrape` → `apps/ads-scrape`
- [x] `apps/live_transcript` → `apps/live-transcript`
- [x] `apps/smol_podcaster` → `apps/smol-podcaster`
- [x] `apps/meta_coder` → `apps/meta-coder`

**In-app path string (required — only Python hit among the four):**
- [x] `apps/meta-coder/meta_coder.py` — `clean_cursor_chat_logs()` default updated to `folder_path="apps/meta-coder/cursor_chat_logs"`

**Repo-wide path references:**
- [x] `AGENTS.md` (apps list), `plans/2026-04-09_repos-reorg/PROJECTS.md` (portfolio table)
- [x] `cloc_paths.txt` (`apps/ads-scrape/...`, `apps/meta-coder/...`)
- [x] Grep sweep done. Historical logs (`MOVE_MANIFEST.md`, `2026-05-28_monorepo-folder-structure.md`) left as past-tense records of the earlier reorg — not rewritten.


### Implementation notes (done by Opus 4.8 1M High)

- All four renames done with `git mv`, so git tracked them as renames (history preserved): 284 `R`, 1 `RM` (`meta_coder.py` = renamed dir + edited path string), plus modified docs.
- Python files inside the renamed dirs kept snake_case (`meta_coder.py`, `smol_podcaster.py`, `scrape_ads.py`, etc.) — only directory names went kebab-case.
- **Pre-existing bug fixed in `cloc_paths.txt`:** it listed `apps/ads_scrape/scrape.py`, but the real file is `scrape_ads.py` (the `scrape.py` path never existed). Corrected to `apps/ads-scrape/scrape_ads.py` while updating the prefix.
- Verification before commit:
  - Import grep `(from|import) apps.(ads_scrape|live_transcript|meta_coder|smol_podcaster)` → no matches.
  - Stale path-string sweep across `*.py/.js/.css/.html/.txt/.ipynb` → no matches.
  - `py_compile` on all moved Python files → passes (only pre-existing escape-sequence `SyntaxWarning`s in `smol_podcaster.py` and `extract_url.py`, untouched).
- No S3 manifest or object changes (confirmed `apps/` is not a mirror area in `core/s3_archive.py`).


## S3 archive and manifests (do not break)

Bulk data upload is managed by `core/s3_archive.py`. This is separate from git-tracked app code. Understanding the boundary keeps app-folder renames from breaking uploads.


### Two manifest layers

| Layer | Location | Role |
|-------|----------|------|
| **Area summary** (legacy) | `s3_archive_manifest.jsonl` + `s3_archive_manifest_README.md` | High-level pare-down record from corpus-tools cutover; reference only |
| **Per-file manifests** (operational) | `s3_manifests/<area>.manifest.jsonl` (32 files) | What `build`, `upload`, `verify`, and `refresh` actually use |

Each per-file row: `repo_path`, `corpus`, `size_bytes`, `mtime`, `sha256`, `s3_bucket`, `s3_key`, `s3_uri`, `status`, …  
**S3 key rule:** `s3_key` mirrors `repo_path` 1:1 (no prefix) → `s3://[S3-FILES-BUCKET]/data/education/foo.md`.


### What `s3_archive.py` scans (EXTRA_AREAS + data corpuses)

Mirrored paths today — **none under `apps/`**:

- `data/<corpus>/` — one manifest per immediate subdir of `data/` (e.g. `deutsch`, `floodlamp`, `education`, `misc-various`)
- `data/` root files only → `data_root_files.manifest.jsonl`
- `logs/` → `logs.manifest.jsonl`
- `_archive/` → `_archive.manifest.jsonl`
- `exchanges/qrag_*` and `exchanges/response_files` → `exchanges_qrag_*.manifest.jsonl`
- **PII** (separate bucket `[S3-BUCKET]`, explicit by-name only): `pii_*.manifest.jsonl` — sources live in sibling `../corpus-tools`, not in this repo

Area definitions live in `EXTRA_AREAS`, `PII_AREAS`, and auto-discovered `data/` subdirs in `core/s3_archive.py`. Manifest **filenames** must match each area's `name` field (`manifest_path_for(name)`).


### Scan result: four app renames → **zero S3 impact**

Searched all 32 files in `s3_manifests/` plus `s3_archive_manifest.jsonl`:

- **No rows** with `apps/`, `ads_scrape`, `meta_coder`, `smol_podcaster`, or `live_transcript`.
- App folders are git-tracked code/scratch — not registered as S3 mirror areas.
- **Action for the four renames:** none on manifests or S3 objects. Update repo path strings in code/docs only.

**Do not** run `refresh --prune` against any area as part of app renames — nothing to sync.


### `_archive/math_quiz/` is not `apps/math_quiz/`

`_archive.manifest.jsonl` has two verified rows under `_archive/math_quiz/` (old HTML/JS snapshots). That is the top-level **`_archive/`** tree archived to S3 during pare-down — unrelated to the live `apps/math_quiz/` app folder. Leave those manifest rows and S3 keys unchanged. The `math_quiz` app exception does not conflict with S3.


### Manifest filenames — leave as-is

The 32 `*.manifest.jsonl` names are **area identifiers wired into code**, not general docs:

| Pattern | Examples |
|---------|----------|
| data corpus = dir name | `deutsch.manifest.jsonl`, `misc-various.manifest.jsonl` |
| field + exchange set | `exchanges_qrag_fda-c19-townhalls.manifest.jsonl` |
| PII prefix | `pii_exchanges_qrag_deutsch.manifest.jsonl` |

Renaming a manifest file without updating the matching `name` in `EXTRA_AREAS` / `PII_AREAS` / `data/` subdir breaks `s3_archive.py build|upload|verify|refresh`. **Do not** rename these as part of the kebab-case app-folder pass.

Optional cosmetic rename: `s3_archive_manifest_README.md` → `s3-archive-manifest_README.md` (human doc only; tooling ignores it).


### When a mirrored path *does* get renamed later
Two cases — because most mirrored data is NOT in this repo (it lives only in S3):

A. Area whose files ARE in the repo (today only `exchanges/`): use refresh + prune.
   1. Rename/move locally first.
   2. Dry-run: `refresh --area <name>`
   3. `refresh --area <name> --execute`  (uploads new paths; old keys become local_missing)
   4. After verifying the new keys: `refresh --area <name> --execute --prune`  (removes old S3
      objects; versioning on [S3-FILES-BUCKET] allows recovery)
   5. Commit the updated manifest. Never hand-edit JSONL rows for this case — let refresh regenerate.

B. Area that is S3-only / not present locally (`data/`, `data_root_files`, `logs/`, `_archive/`,
   and the PII areas sourced from ../corpus-tools): DO NOT use refresh/prune — there are no local
   files to scan, so it cannot work and prune is dangerous. Re-key manually, like the corpus-tools
   prefix drop:
   1. Server-side copy objects old-prefix -> new-prefix (boto3 copy_object; no download).
   2. Rename the area in EXTRA_AREAS / PII_AREAS AND rename the manifest file; rewrite
      repo_path/s3_key/s3_uri (leave status/sha256).
   3. `verify --area <new> --execute --redownload` -> 0 missing / 0 mismatched.
   4. Only then delete the old prefix (recoverable via versioning).
   5. Commit.


### Future naming alignment (S3-specific, low priority)

- New **data corpus** subdirs under `data/`: prefer kebab-case dir names; manifest name will match the dir name automatically.
- New **exchange sets**: follow existing `exchanges_qrag_<slug>` manifest naming when adding to `EXTRA_AREAS`.
- **`data/` and `exchanges/` paths on S3** retain historical snake_case and mixed names from corpus-tools — do not mass-rename uploaded objects; use refresh+prune only when deliberately relocating content.


## Already aligned (no action)

- `apps/math_quiz/` — frozen exception until external-repo merge
- `apps/repo-mirror/`, `apps/games/robo-polly/`
- `apps/qrag/api/{qrag-llm,qrag-routing,vrag-llm}/`
- `web-shared/aws_chalice/{hash-store,hmac-hash,send-email}/`
- Dated plans in reorg: `2026-06-01_repo-status.md`, `2026-06-02_s3-version-lifecycle-rules.md`, etc.
- Exchange JSON pattern: `qrag-exch_YYYY-MM-DD_HHMMSS.json`
