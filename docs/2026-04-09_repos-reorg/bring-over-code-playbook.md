file: bring-over-code-playbook.md
title: Playbook + reusable prompt for bringing code from another repo into fof-mono
last-updated: 2026-06-05_1430
ai: Claude Code - Opus 4.8 High
session: `S3 upload preparation for data folder`


## Purpose
A reusable recipe for merging another repo's contents into fof-mono — code, docs, data — the same way corpus-tools was pared down: deciding per item whether it lives in the repo, stays gitignored-local, goes to S3, or is discarded. Use it for the planned MathQuiz and Kid-Games repos, and for pulling in open-source code later.


## How to run it
- Start a Claude Code session (the cloud/web VM is ideal) with BOTH repos added to its scope: the SOURCE repo and fof-mono. The agent can then read both, copy across them, and commit + open a PR — all in the session.
- Branch model: the agent works only on a frozen `export` branch in the SOURCE (a reorganized, inspectable snapshot of what is being brought over) and on an `import` branch in fof-mono (where the actual copy/upload happens). See the BRANCHES block in the prompt.
- Plan first. Have the agent produce a written plan and STOP for your review before copying or uploading. Eyeball the per-file dispositions in Cursor/VS Code (two monitors: source `export` branch on one, fof-mono `import` branch on the other).
- AWS creds caveat: the cloud session has NO AWS credentials (that is why the corpus-tools S3 uploads ran locally). So the agent does the planning + code copy + manifest setup in the session, but the actual `--execute` S3 upload + verify runs LOCALLY via a punch-list the session hands you. Only skip this if you have put AWS creds into the environment's secrets.
- Network: to pull an open-source repo, make sure the session's network policy allows cloning it, or clone it locally and add it to scope.
- Non-destructive to the source: the agent only ever works on the frozen `export` branch there — never the source's main, never a PR/merge. The source stays intact as a backup; retire or archive it yourself once the bring-over is copied, uploaded, and verified.
- Secrets: before anything, scan the source for committed secrets/keys/.env — never copy them over; rotate anything that was exposed.


## Disposition framework
Decide, per file or group:

- **REPO:**
  - what: source code, configs, small canonical docs/markdown
  - where: into fof-mono at an apps-centric path, tracked in git

- **S3:**
  - what: bulk data, media, binaries, corpora — anything worth preserving/sharing that is not source code
  - where: upload to `[S3-FILES-BUCKET]` S3 bucket (`[S3-BUCKET]` for PII) via `core/s3_archive.py`. Files are also kept locally on disk and listed in `.gitignore` so they are NOT tracked in git. The S3 copy serves as backup and lets collaborators download the same assets. Even small binary assets (e.g. 12 MB of 3D models) go to S3 rather than git to maintain good monorepo hygiene — otherwise many small-seeming imports add up to bloat.
  - local workflow: the files live on disk at their fof-mono repo-relative paths (e.g. `apps/games/poly-files/`), gitignored. `core/s3_archive.py` builds manifests from the local files and uploads to S3; collaborators use the same tool to download/verify.

- **REBUILD-LOCAL:**
  - what: package installations (node_modules, .venv), build output (build/, .gradle/), caches (__pycache__) — anything that is recreated from source code or package manifests by running install/build commands
  - where: listed in `.gitignore`; remain on local disk only. NOT uploaded to S3 because any collaborator can rebuild them from the source code and package manifests (package.json, requirements.txt, build.gradle, etc.)
  - during bring-over: these files do NOT need to be manually copied from the source repo. Instead, run the appropriate install/build command in the target repo after copying the source files and package manifests. See "Environment setup" below.

- **DISCARD:**
  - what: superseded docs, legacy configs, IDE settings that belong to the source repo, duplicates that already exist in fof-mono, personal/non-code files
  - where: do not bring over at all. During stepwise source-repo organization, move to a `discard-not-brought-over/` folder for review before finalizing.


## Source repo preservation

The export branch is a reference snapshot — it should leave the source repo's working
environment intact so the repo remains usable after the bring-over.

- **Do NOT untrack or delete `.vscode/` from the source repo's export branch.** The
  source repo's VS Code settings (settings.json, tasks.json, snippets, cspell.json)
  should remain tracked for continuity. The `.vscode/` files are DISCARD disposition for
  fof-mono (not copied over — fof-mono has its own), but they stay intact in the source.
- **Add `.vscode/` to the source repo's `.gitignore`** if it is not already there. Since
  the files are already tracked, this prevents *new* IDE files from being added while
  preserving the existing ones.
- Same principle applies to any other source-repo working-environment files (editor
  configs, local tooling) — classify them as DISCARD for fof-mono but do not remove
  them from the source repo.


## Data hygiene -- preventing repo bloat

This repo was pared from 5+ GB to ~80 MB during the corpus-tools migration. Every bring-over must maintain that discipline:

1. **NEVER copy S3-disposition files into the git tree.** Data files (session JSON, audio, video, databases, corpora) go DIRECTLY from the source repo to S3. Only the manifest enters git.

2. **Add gitignore rules BEFORE staging any data.** Even if a file type is globally ignored (e.g. `*.wav`), add a directory-level rule for the data folder as defense in depth for types that AREN'T globally ignored (e.g. `*.json`, `*.db`):
   ```
   apps/<app-name>/<data-dir>/
   ```

3. **Use ONLY `core/s3_archive.py` for S3 uploads.** Do NOT install the AWS CLI. Do NOT use direct boto3 commands. Do NOT use `aws s3 sync/cp`. The s3_archive module handles manifests, checksums, dry-run safety, and idempotent retries.

4. **Verify before committing.** After copying REPO-disposition files, run `git status` and `git diff --stat` to confirm no data files slipped in. If they did, `git rm --cached` them and add the missing gitignore rule.

5. **Beware `cp -r` from disk.** When copying directories from the source repo, `cp -r` copies ALL files on disk — including ones that are gitignored in the source but NOT yet gitignored in fof-mono. This is the most common cause of unwanted files slipping in. After any `cp -r`, check `git status` carefully and `git rm --cached` anything that shouldn't be tracked. Common offenders: build artifacts (`_deprecated/`, `build/`), large binary downloads (third-party JARs), and platform-specific caches.

5. **S3 upload guide**: `bring-over-s3-upload-guide.md` has the full step-by-step workflow.

6. **Watch for gitignore collisions with source-code directory names.** fof-mono's root `.gitignore` has broad directory-name rules (`data/`, `logs/`, `build/`, etc.) that match at any depth. If the source repo has a source-code package or module whose directory name collides with one of these rules (e.g. a Java package `com.example.data`), the files will be silently ignored after copy — `git add` skips them without warning. **Diagnosis:** run `git check-ignore -v <path>` on any source file that doesn't appear in `git status` after copy. **Fix:** rename the source-code directory to avoid the collision (e.g. `data` → `persistence`). Do NOT rely on gitignore negation rules (`!path/`) — they are fragile and easy to forget on the next import.


## Stepwise source-repo organization

Before copying files into fof-mono (Phase 4), reorganize the REPO-disposition files in the source repo's `export` branch to match the exact folder layout they will have in fof-mono. This makes Phase 4 a straightforward direct copy with no path translation.

**Process:**

1. **Discard commit**: Move all DISCARD-disposition files into `discard-not-brought-over/` and commit. This gives Randy a chance to review what's being left behind before the folder is ignored.

2. **Plan + metadata commit**: Move the bring-over plan file and any reference docs into their target paths (e.g. `plans/2026-04-09_repos-reorg/`). Commit.

3. **Reorganization commit**: Reorganize the remaining REPO-disposition files into the fof-mono target layout using `git mv`. This includes:
   - Nesting flat directories under `apps/<area>/` (e.g. `minecraft/` → `apps/minecraft/`)
   - Creating new subdirectories for better organization (e.g. `apps/minecraft/skins/`, `apps/minecraft/world-stories/`)
   - Moving files to their owning app area (e.g. `sounds/` → `apps/games/robopoli/sounds/`)
   - Commit with a clear message listing all moves.

4. **Verify**: After reorganization, confirm that every tracked file maps to a fof-mono target path. Run `git ls-files | cut -d/ -f1 | sort -u` to check top-level directories. Only `apps/`, `plans/`, `prompts/`, `discard-not-brought-over/`, `.vscode/`, and root config files (`.gitignore`) should remain.

5. **Update plan**: Update the bring-over plan's disposition section and execution checklist to reflect the actual paths. The plan should now read as a direct 1:1 mapping from source export paths to fof-mono paths.

6. **Leave FROZEN**: After the reorganization commits, the export branch is done. Do not make further changes.

**Phase 4 then becomes:** copy each directory/file from the source export branch into the same path in fof-mono's import branch. No path translation needed — the source layout already matches the target.


## Environment setup

When a source repo's apps bring new language runtimes, package managers, or build tools into fof-mono, the target environment needs setup so the imported apps can run. This section covers the common cases.

**Python apps:** If the source app has Python dependencies not already in fof-mono's `.venv`, add them to the relevant requirements file and run `pip install` inside the existing `.venv`. Do NOT create a separate venv per app — fof-mono uses a single shared `.venv`.

**Node.js / npm apps:** If the source app has a `package.json`, that file comes over as REPO (it is the package manifest — equivalent to Python's `requirements.txt`). The `package-lock.json` also comes over (it pins exact versions — equivalent to a pip freeze). The `node_modules/` directory is REBUILD-LOCAL — it is NOT copied or committed. After copying the package manifests, run `npm install` in the app directory to recreate `node_modules/` from the manifest. The `node_modules/` directory should already be in fof-mono's root `.gitignore`.

**Java / Gradle apps (Minecraft mods):** The Gradle wrapper (`gradlew` + `gradle/wrapper/gradle-wrapper.jar`) is REPO — it bootstraps the build tool without any system install. Build output (`build/`, `.gradle/`) is REBUILD-LOCAL. Running `./gradlew build` in the mod directory downloads dependencies and compiles. No environment setup needed beyond having the correct JDK installed (see the mod's AGENTS.md for JDK version requirements).

**General principle:** Package manifests (package.json, requirements.txt, build.gradle, Cargo.toml, etc.) are REPO. Installed packages and build output are REBUILD-LOCAL. The bring-over plan should note any `npm install`, `pip install`, or other setup commands the user needs to run after the import to get the apps working in fof-mono.


## Post-import verification

After the import commit, verify the imported apps work in their new home:

1. **REBUILD-LOCAL verification**: Run install/build commands (`npm install`, `pip install`, `./gradlew build`) and compare the results against the source repo. For npm: `diff <(ls fof-mono/<app>/node_modules/ | sort) <(ls source-repo/node_modules/ | sort)`. Platform-specific native modules (e.g. `fsevents` on macOS vs Linux) will differ — that's expected.

2. **Functional test**: Pick the most important active app from the import and run its primary build/test workflow. For a Minecraft mod, that's the build dispatcher; for a web app, that's the dev server. This validates that paths, dependencies, and configs all resolve correctly at the new location.

3. **S3 punch-list**: If S3-disposition files couldn't be uploaded during the session (no AWS creds), create a step-by-step punch-list in the bring-over plan that Randy can copy-paste to run locally. Include: copy files from source, build manifests, dry-run, execute upload, verify, commit manifests. Reference `bring-over-s3-upload-guide.md` for the full workflow.

4. **AGENTS.md / PROJECTS.md**: Verify the directory guide and project records accurately reflect the imported content. The Minecraft mods AGENTS.md migration (CLAUDE.md → AGENTS.md) is a pattern to follow for any source repo with substantial operational knowledge in its CLAUDE.md.


## The prompt
Copy everything between the markers; replace {{SOURCE}} with the source repo's name/path.

--- PROMPT START ---
You are bringing code from a source repo into the fof-mono monorepo. Both repos are in this session:
SOURCE = {{SOURCE}}, TARGET = fof-mono. Work PLAN-FIRST: produce a written plan and STOP for my
approval before copying or uploading anything.

### BRANCHES - set these up first, and be strict about them:
- SOURCE repo: create a branch named `export` off its main. This is where you STAGE the bring-over —
  reorganize the kept files into the SAME folder layout they will have in fof-mono (app code under
  apps/<name>/, shared modules under core/, cross-app under web-shared/, etc.), so `export` is a clear,
  inspectable SNAPSHOT of exactly what is being brought over and where it lands. Fully non-destructive:
  the source's main is untouched. NEVER open a PR in the source and NEVER merge `export` into the
  source's main — it stays FROZEN as a reference.
- fof-mono (TARGET): create a branch named `import` off main. ALL copying, gitignore changes, S3 setup,
  and doc updates happen here. NEVER push to fof-mono main. ASK MY PERMISSION before opening the PR from
  `import`.

### PHASE 1 — Learn the target (fof-mono):
- Read fof-mono/AGENTS.md — especially the Directory guide, "Repo layout convention (Option B)"
  (apps-centric: apps/<name>/, shared code in core/, cross-app in web-shared/), and "Data and S3".
- Read in fof-mono/plans/2026-04-09_repos-reorg/: 2026-05-28_monorepo-folder-structure.md,
  2026-06-01_s3-upload-prep.md, 2026-06-01_excluded-from-carryover.md,
  2026-05-19_chatgpt-guide-to-file-types-to-exclude-in-repo.md, and PROJECTS.md.
- Summarize back: the layout conventions; the REPO vs S3 vs REBUILD-LOCAL vs DISCARD disposition
  model; how the S3 tooling works (core/s3_archive.py + plans/2026-04-09_repos-reorg/s3_manifests/,
  private bucket [S3-FILES-BUCKET] keyed 1:1 to repo paths with NO prefix, PII to [S3-BUCKET]); the gitignore
  conventions; the environment setup requirements. Confirm understanding before continuing.

### PHASE 2 — Survey the source ({{SOURCE}}):
- Inventory it: top-level structure, file types + counts + sizes; classify each as source code, docs,
  bulk data/media, build artifacts, secrets/credentials, or local-only working files.
- Map it to fof-mono apps/areas per Option B (propose target paths). If it is several projects (a
  catch-all repo), split per project.
- FLAG immediately: any secrets/API keys/.env (never bring; note if rotation needed), any PII, any
  large/bulk data, any vendored deps or build artifacts.

### PHASE 3 — Produce the PLAN (write it; do not execute):
- For every file/group assign a disposition: REPO / S3 ([S3-FILES-BUCKET]; PII->[S3-BUCKET]) /
  REBUILD-LOCAL / DISCARD — with the target path in fof-mono.
- Cover: the `export`-branch layout (which kept files move to which fof-mono target paths); new app
  folder(s) and whether any needs a per-app AGENTS.md; where markdown/docs go (app runbook, plans/, a
  PROJECTS.md entry); how to merge dependencies (flag version conflicts); how to integrate/retarget tests.
- Write the plan to fof-mono/plans/2026-04-09_repos-reorg/<YYYY-MM-DD>_bring-over_{{SOURCE}}.md (use the
  repo's file:/title: header + markdown style), including a per-item list (each item -> disposition ->
  target path). Then STOP and ask me to review.

### PHASE 4 — Execute (only after I approve the plan):
- SOURCE `export` branch: reorganize the REPO-disposition files into their fof-mono target paths
  (apps/<name>/, core/, web-shared/, etc.) so the branch mirrors what will land in the repo. Branch-only
  and non-destructive — never touch source main, never PR/merge it. Commit; leave it FROZEN.
- fof-mono `import` branch: copy the files from the `export` layout into fof-mono at the matching paths;
  add gitignore entries for S3 and REBUILD-LOCAL items.
- For S3 items: NEVER copy data files into git-tracked paths. Add gitignore rules for the data
  directories FIRST. Then add scoped areas to core/s3_archive.py EXTRA_AREAS, build manifests, dry-run,
  then upload + verify (keys 1:1 with repo paths, NO corpus-tools/ or other prefix; [S3-FILES-BUCKET],
  PII->[S3-BUCKET]). Use ONLY core/s3_archive.py for uploads -- do NOT install or use the AWS CLI, do NOT
  use direct boto3 commands. IF AWS creds are not available here, do everything EXCEPT the --execute
  upload and hand me a punch-list of the exact upload/verify commands to run locally. Follow the guide
  at plans/2026-04-09_repos-reorg/bring-over-s3-upload-guide.md.
- For REBUILD-LOCAL items: add gitignore rules. Note the install/build commands needed in the plan
  (e.g. `npm install`, `pip install -r requirements.txt`). Do NOT copy REBUILD-LOCAL directories from
  the source repo — they are recreated in the target.
- Environment setup: run any install/build commands needed to support the imported apps in fof-mono
  (see "Environment setup" section above). Note these in the plan so the user can run them locally.
- Update fof-mono/AGENTS.md (Directory guide) and PROJECTS.md for the new app(s). Run the test suite
  green. Commit on `import`. ASK MY PERMISSION, then open a PR (never push to main). NEVER commit secrets
  or PII.

Guardrails (fof-mono/AGENTS.md): plan before acting; get my approval for S3/billing, large deletes or
moves, secrets, and public/private boundary calls; ask before opening the fof-mono PR and never push
main; never PR or merge the source `export` branch — keep it frozen and non-destructive.
--- PROMPT END ---


## Notes for the specific repos
- MathQuiz -> DONE (2026-06-03). Imported into `apps/math-quiz/` (kebab-case). Old `apps/math_quiz/` (snake_case) deleted — fully superseded. See `2026-06-03_bring-over_math-quiz.md`.
- Kid-Games (catch-all, incl. the latest Minecraft mod work) -> split per project: Minecraft into `apps/minecraft/<sub>/`, other games into `apps/games/<sub>/`; send each project's bulk assets to S3 per the framework.
- Open-source repos later: keep their LICENSE; record provenance (source URL + commit SHA) in the bring-over plan doc; vendor under the owning app or `lib/` per existing patterns.

## Prompt for math-quiz
You are bringing code from a source repo into the fof-mono monorepo. Both repos are in this session:
SOURCE = math-quiz, TARGET = fof-mono. Work PLAN-FIRST: produce a written plan and STOP for my
approval before copying or uploading anything.

BRANCHES — set these up first, and be strict about them:
- SOURCE repo: create a branch named `export` off its main. This is where you STAGE the bring-over —
  reorganize the kept files into the SAME folder layout they will have in fof-mono (app code under
  apps/<name>/, shared modules under core/, cross-app under web-shared/, etc.), so `export` is a clear,
  inspectable SNAPSHOT of exactly what is being brought over and where it lands. Fully non-destructive:
  the source's main is untouched. NEVER open a PR in the source and NEVER merge `export` into the
  source's main — it stays FROZEN as a reference.
- fof-mono (TARGET): create a branch named `import` off main. ALL copying, gitignore changes, S3 setup,
  and doc updates happen here. NEVER push to fof-mono main. ASK MY PERMISSION before opening the PR from
  `import`.

PHASE 1 — Learn the target (fof-mono):
- Read fof-mono/AGENTS.md — especially the Directory guide, "Repo layout convention (Option B)"
  (apps-centric: apps/<name>/, shared code in core/, cross-app in web-shared/), and "Data and S3".
- Read in fof-mono/plans/2026-04-09_repos-reorg/: 2026-05-28_monorepo-folder-structure.md,
  2026-06-01_s3-upload-prep.md, 2026-06-01_excluded-from-carryover.md,
  2026-05-19_chatgpt-guide-to-file-types-to-exclude-in-repo.md, and PROJECTS.md.
- Summarize back: the layout conventions; the REPO vs S3 vs REBUILD-LOCAL vs DISCARD disposition
  model; how the S3 tooling works (core/s3_archive.py + plans/2026-04-09_repos-reorg/s3_manifests/,
  private bucket [S3-FILES-BUCKET] keyed 1:1 to repo paths with NO prefix, PII to [S3-BUCKET]); the gitignore
  conventions; the environment setup requirements. Confirm understanding before continuing.

PHASE 2 — Survey the source (math-quiz):
- Inventory it: top-level structure, file types + counts + sizes; classify each as source code, docs,
  bulk data/media, build artifacts, secrets/credentials, or local-only working files.
- Map it to fof-mono apps/areas per Option B (propose target paths). If it is several projects (a
  catch-all repo), split per project.
- FLAG immediately: any secrets/API keys/.env (never bring; note if rotation needed), any PII, any
  large/bulk data, any vendored deps or build artifacts.

PHASE 3 — Produce the PLAN (write it; do not execute):
- For every file/group assign a disposition: REPO / S3 ([S3-FILES-BUCKET]; PII->[S3-BUCKET]) /
  REBUILD-LOCAL / DISCARD — with the target path in fof-mono.
- Cover: the `export`-branch layout (which kept files move to which fof-mono target paths); new app
  folder(s) and whether any needs a per-app AGENTS.md; where markdown/docs go (app runbook, plans/, a
  PROJECTS.md entry); how to merge dependencies (flag version conflicts); how to integrate/retarget tests.
- Write the plan to fof-mono/plans/2026-04-09_repos-reorg/<YYYY-MM-DD>_bring-over_math-quiz.md (use the
  repo's file:/title: header + markdown style), including a per-item list (each item -> disposition ->
  target path). Then STOP and ask me to review.

PHASE 4 — Execute (only after I approve the plan):
- SOURCE `export` branch: reorganize the REPO-disposition files into their fof-mono target paths
  (apps/<name>/, core/, web-shared/, etc.) so the branch mirrors what will land in the repo. Branch-only
  and non-destructive — never touch source main, never PR/merge it. Commit; leave it FROZEN.
- fof-mono `import` branch: copy the files from the `export` layout into fof-mono at the matching paths;
  add gitignore entries for GITIGNORE-LOCAL items.
- For S3 items: add scoped areas to core/s3_archive.py, build manifests, dry-run, then upload + verify
  (keys 1:1 with repo paths, NO corpus-tools/ or other prefix; [S3-FILES-BUCKET], PII->[S3-BUCKET]). IF AWS creds
  are not available here, do everything EXCEPT the --execute upload and hand me a punch-list of the
  exact upload/verify commands to run locally.
- Update fof-mono/AGENTS.md (Directory guide) and PROJECTS.md for the new app(s). Run the test suite
  green. Commit on `import`. ASK MY PERMISSION, then open a PR (never push to main). NEVER commit secrets
  or PII.

Guardrails (fof-mono/AGENTS.md): plan before acting; get my approval for S3/billing, large deletes or
moves, secrets, and public/private boundary calls; ask before opening the fof-mono PR and never push
main; never PR or merge the source `export` branch — keep it frozen and non-destructive.

