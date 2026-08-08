file: AGENTS.md
title: fof-mono — Agent Instructions

This monorepo is a work in progress. The applications are at various stages of maturity. All code is written by AI coding agents. The work is driven by primarily by Randy, who is tech generalist and not a trained/experienced software engineer. Expect uneven polish, evolving conventions, and apps that are experimental or incomplete.

Caveats:
- Prefer the lightest change that solves the task; do not "finish," redesign, or tidy unrelated areas.
- Layout and docs still evolve; if a path looks stale, search by basename before assuming it is gone.
- The operational rules below (branch discipline, git safety, S3, commits) are binding for agents working in this repo — not optional style tips.


## What this repo is
A monorepo for multiple applications sharing common Python code for file processing, transcription, LLM integration, RAG, and related tasks.

- **Owner**: FocusOnFoundationsNonprofit
- **Infra**: Primarily AWS (Chalice Lambdas, API Gateway, S3) — exploring alternatives
- **Frontend**: Currently Webflow — exploring alternatives
- **Vector search**: Currently Pinecone — may evaluate alternatives
- **LLM providers**: OpenAI, Anthropic (provider-swappable architecture)
- **Core library**: `core/` — most mature modules are `fileops.py`, `transcribe.py`, `llm.py`; `s3_archive.py` manages the S3 data archive (see "Data and S3")


## Verification and error reporting
- When performing multi-step operations (branch creation, renaming, deletion, pushes), verify each step succeeded before reporting completion.
- If any step fails, report the failure immediately with the exact error. Never say "done" or "renamed" when a step failed.
- For git operations that modify remote state (push, delete remote branch), always show the command output that confirms success (e.g. the `[deleted]` or `[new branch]` line).
- Never state a branch relationship claim without proof output. Claims like "created `X` off `Y`", "`X` is based on `Y`", or "safe to merge `A` into `B`" must include the command output (or key output lines) that proves the relationship.
- Minimum proof for "created `X` off `Y`": include both `git merge-base Y X` and `git log --oneline Y..X` output (or clearly state that `Y..X` is empty).


## High-level context files
Use these files for progressive disclosure when the task calls for broader context:
- `docs/2026-04-09_repos-reorg/PROFILE-randy.md` — top-level human/operator context, background, skill levels, organizations, collaborators, and Randy's higher-level coding posture. Execution-time agent rules (communication, voice-dictation, ask-versus-assume, approval boundaries) live in this `AGENTS.md`, not in `PROFILE-randy.md`.
- `docs/2026-04-09_repos-reorg/PROJECTS.md` — planned portfolio map for projects, repos, status, infrastructure, data, risks, and workflows.
- `docs/2026-04-09_repos-reorg/ai-coding-system-dev.md` — living devlog for AI coding tools, agent workflows, infrastructure tradeoffs, and repeatable software-production patterns. Treat as the place for evolving experiments and roadmap items rather than stable preferences.

Do not duplicate these files inside `AGENTS.md`. Read them only when their context is relevant to the task.


## Directory guide
Access levels for agent behavior:
- **Read freely** — explore, search, and modify as needed for the task.
- **On request only** — do not read or search unless the user directs you there.
- **Off limits** — never read or search under any circumstances.

**Read freely:**
- `skills/` — shared, platform-agnostic skill definitions (procedures, scripts, references, eval). See `skills/README.md` for conventions. Each skill is a folder with a `README.md` + `scripts/`. Skill markdown files (`README.md`, `references/*.md`, `eval/*.md`) carry a `file:` header with their **repo-relative path** (e.g. `file: skills/media/youtube-transcript/README.md`); cross-references inside skills use the same full paths. Platform-specific wrappers (Hermes SKILL.md, Claude Code commands, etc.) live in their respective platform dirs and reference skills here
- `core/` — shared Python library (fileops, transcribe, llm, rag, aws, s3_archive, vectordb, structured, audio, video, speakerid, gdrive, transcript_eval, webflow_api)
- `apps/` — standalone applications, each self-contained where possible
  - `apps/qrag/api/` — QRAG AWS Chalice Lambdas (qrag-llm, qrag-routing, vrag-llm)
  - `apps/qrag/web/` — QRAG-specific Webflow custom code and local dev harnesses
  - `apps/education/` — education / kid-facing apps (`lesson-logger/`, `reading/`, `milestone-web/`)
  - `apps/holodeck/` — agent/worktree ops UI and related tooling (has its own AGENTS.md)
  - `apps/focusonfoundations/` — Focus on Foundations site / applet work
  - `apps/deutsch/` — Deutsch corpus processing (e.g. `extract_boi_problems_snippets.py`); expected to grow
  - `apps/repo-mirror/` — repo-management tooling: mirrors selected files into a public clone
  - `apps/minecraft/` — Minecraft projects umbrella: `mods/` (MathQuest, remove-singleplayer — multi-target Fabric/Forge builds; has its own AGENTS.md), `skyblock/` (Hypixel Skyblock reference), `prism-sync/` (Prism Launcher sync web app + CLI), `skins/` (dragon skin script), `world-stories/` (world-building story prompts)
  - `apps/transcription/` — transcription umbrella: `api/` (deepgram-callback Chalice), `stellar-transcriber/`, `smol-podcaster/`, `live-transcript/`
  - `apps/scratch/` — per-collaborator personal runner scripts (ea, randy, Kid1, bs, tl)
  - `apps/games/` — game sub-projects: `robopoli/` (Python + web/3D), `3js-expt/` (Three.js animation experiments), `viewers/` (3D model viewers), `wingspan/`
  - `apps/voice/` — TTS (OpenAI / ElevenLabs / local Kokoro) + video-frame OCR-to-speech. Model weights, generated audio (mp3/wav), and captured frames are kept local-only / gitignored
  - `apps/voice-router/` — voice routing
  - `apps/math-quiz/` — math quiz web app for kids (quiz, fluency tracking, analysis). Imported from external `math-quiz` repo 2026-06-03
  - other apps: `ads-scrape`, `autolearner`, `content_studio`, `mac`, `meta-coder`
- `web-shared/` — cross-app web/infra shared code, grouped into subfolders: `webflow/` (cross-app Webflow shells: site head/body, home body, log-in, CMS templates, privacy embed, custom code template) and `aws_chalice/` (shared Chalice Lambdas + mirror/deploy script, see below). Loose cross-app assets stay in the root: `md_to_html_dev/` (transcript md→html dev, consumed by `core/corpuses.py`), `web_docs/` (privacy/terms), `web_test_files/`, `test_front-end_validation_inputs.js` (front-end input-validation harness), and `z_count_chars_in_js.sh` (counts chars in a JS file, e.g. against Webflow custom-code size limits)
- `web-shared/aws_chalice/` — shared/cross-app Chalice Lambdas not yet placed under an owning app (hash-store, hmac-hash, send-email); also holds the shared mirror/deploy script and composite deploy log. The top-level `web/` folder was retired; its only remaining content (`aws_chalice/`) moved here
- `lib/` — vendored third-party JS libraries (vis-network, tom-select, bindings)
- `tests/` — unit tests
- `docs/` — documentation, dated plan/decision docs, and code index tools. The former top-level `plans/` folder was retired 2026-07-31: cross-app planning docs moved here (keeping their subfolder names, e.g. `docs/2026-04-09_repos-reorg/`, `docs/git/`), and app-specific plan docs moved into their owning `apps/<name>/` folders. `docs/personal/` is a gitignored local-files mount for personal reference files (computer/account info, PII term lists) — local-only, never committed, never in public snapshots

**On request only:**
- `exchanges/` — saved QRAG user-exchange captures. Non-PII captures are git-tracked here; PII files (hash logs, `pii-exchanges_*.db`) are gitignored. Selected exchange sets are archived to S3 (`[S3-FILES-BUCKET]`) and PII to `[S3-BUCKET]` — see "Data and S3".
- `prompts/` — prompt templates.

**Off limits:**
- `node_modules/` — never read or search.
- The bulk dirs excluded at cutover (`_misc_to_be_sorted/`, `limbo/`, `ms-graphrag/`, `lancedb/`, `pretrained_models/`) are not in this repo — they remain only in the frozen `corpus-tools` predecessor. See `docs/2026-04-09_repos-reorg/2026-06-01_excluded-from-carryover.md`.

**Stale paths in historical docs:** the repo gets reorganized periodically (e.g. 2026-07-31: `plans/` retired into `docs/` and `apps/<name>/`). Dated/historical documents keep their original internal path references — do not mass-edit old docs to fix them. If a path referenced in a document does not exist, search for the file by basename (filename search, or `git log --follow -- <old-path>`) before concluding it is gone. Only fix stale paths in live surfaces: `AGENTS.md`, skill READMEs, active guides, and executing code.


## Data and S3
Bulk corpus/data files are NOT stored in this repo — they live in S3 and are pulled down on demand. The repo tracks only the catalog (per-area manifests).

- Private bucket `[S3-FILES-BUCKET]` (us-west-2, S3 Standard, Versioning on) holds the corpus data, keyed 1:1 with repo-relative paths and with NO prefix (e.g. `s3://[S3-FILES-BUCKET]/data/education/...`, `s3://[S3-FILES-BUCKET]/exchanges/qrag_deutsch/...`). The former top-level `data/`, `logs/`, and `_archive/` dirs from `corpus-tools` are archived here, not in the repo tree.
- Private bucket `[S3-BUCKET]` holds PII (user hash logs, `pii-exchanges_*.db`). Never put PII in `[S3-FILES-BUCKET]` or in git.
- The index lives in `manifests/*.manifest.jsonl` — one per area, recording `repo_path`, `size`, `sha256`, `s3_key`, `s3_uri`, and `status`.
- `core/s3_archive.py` manages all of this: `build` (manifests), `status`, `upload`, `verify`, `refresh` (make S3 match local edits). Real S3 writes require `--execute`; uploads carry no public ACL; the tool never deletes local files.
- **Never rename or move an S3-keyed path** (`data/`, `logs/`, `_archive/`, `exchanges/`, or `[S3-BUCKET]` paths) without the re-key procedure in `docs/2026-04-09_repos-reorg/naming-conventions-proposal.md` (refresh → upload → prune when intentional).
- **FoF applet TTS mp3s** (`apps/focusonfoundations/web/public/audio/`) are S3-backed via `focusonfoundations_applet-audio` on `[S3-FILES-BUCKET]` — not git-tracked and not pre-commit allowlist candidates. Do not add new media allowlists without an explicit size budget (e.g. &lt;200 KB total per app); tiny UI SFX only (math-quiz sounds, robopoli wav).
- **Do not run `build` or `refresh` casually on `exchanges/` areas** in a fresh checkout: clone/checkout changes file mtimes, so a rebuild resets manifest rows from `verified` to `pending_upload` (no data loss, but re-verify is required). The committed manifests are the source of truth for exchange captures. Ask for an explicit confirmation from the user before running `build` or `refresh` and explain why and what will be done to coordinate with the manifests.
- This repo was cut over from `corpus-tools` (2026-06). That predecessor is frozen as a reference — it retains full git history and the original on-disk files.
- **The directory name `data/` is reserved exclusively for gitignored data files** (S3-backed assets, local databases, downloaded corpora). The root `.gitignore` contains a `data/` rule that matches at any depth. Do not use `data/` as a source-code package or module name — git will silently ignore files inside it. Use a descriptive alternative (e.g. `persistence/`, `storage/`, `datamodel/`) for source code that handles data.


## Repo layout convention (Option B)
The repo follows the apps-centric monorepo layout decided on 2026-05-29 in `docs/2026-04-09_repos-reorg/2026-05-28_monorepo-folder-structure.md`:

- Folders are organized by application, not by domain/area or by code-type/layer.
- Shared Python code lives in a single `core/` folder. No formal packaging until a specific module's public release or a breaking change forces it.
- Each app is self-contained where possible: `apps/<name>/` may include `api/` (Chalice/Lambda code), `web/` (frontend), tests, runbooks, and (optionally) a per-app `AGENTS.md` override.
- Areas/domains (deutsch, pv, floodlamp, education, minecraft, qrag) are tags in `PROJECTS.md`, not folders — except when an area has 2+ sub-projects, in which case it becomes an umbrella folder under `apps/` (e.g., `apps/minecraft/<sub>`, `apps/education/<sub>`).
- Cross-app Webflow shells live in `web-shared/webflow/`. App-specific Webflow code lives in `apps/<name>/web/`.
- Chalice apps are migrating from `web-shared/aws_chalice/<app>/` to `apps/<owning-app>/api/<lambda>/`. Some Lambdas remain at `web-shared/aws_chalice/` until their owning app is decided.

When adding a new app or capability, prefer the lightest existing pattern that fits. Promote to a heavier pattern (per-app AGENTS.md, dedicated `packages/` entry, top-level `infra/` or `ops/`) only when the existing pattern is causing real friction.


## Skills

Skills are reusable agent procedures — structured instructions + scripts that any agent or
platform can consume. They follow the same "one source of truth, multiple platform entry
points" pattern as `AGENTS.md` / `CLAUDE.md`.

### Where skills live

| Location | What's there | Who consumes it |
|----------|-------------|----------------|
| `skills/` (repo root) | Platform-agnostic procedures, scripts, references, eval | All platforms |
| `agents/hermes/skills/` | Hermes SKILL.md wrappers + Hermes-only skills | Hermes agent |
| `.claude/commands/` | Claude Code slash commands referencing shared skills | Claude Code |

### Three layers of a skill

| Layer | What | Platform-specific? |
|-------|------|-------------------|
| **Procedure** | Instructions + scripts (the actual logic) | No — lives in `skills/` |
| **Wrapper** | How the platform discovers/invokes the procedure | Yes — SKILL.md, slash command, etc. |
| **Runtime** | What the agent can actually do (tools, network, deps) | Yes — varies by platform |

### Adding a skill

1. If the skill logic is reusable across platforms: create `skills/<category>/<name>/README.md`
   + `scripts/`, then add platform wrappers as needed.
2. If the skill is specific to one agent (e.g. calls `hermes skills reload`): create it
   directly in that agent's skills folder.
3. See `skills/README.md` for full conventions — including the `file:` header block
   (repo-relative path) on every skill markdown file and repo-relative paths when
   referencing `references/`, `scripts/`, or `eval/` assets from skill docs.

### Skill provenance and lightweight versioning

Every shared skill `README.md` carries **`source-github-url:`** and **`source-guide-url:`**
(upstream provenance; duplicate the same URL in both when only one exists) plus
**`history:`** (append-only, newest-first) in its header block — see `skills/README.md`
→ Provenance and lightweight versioning.

- Record **who** changed the skill, **when**, **which platform**, and **which thread**
  (Cursor: transcript UUID as `[title](uuid)`; other platforms: session/share URL).
- Add a new `history` line at the top on each material edit; do not rewrite old entries.
- Formal semver/`CHANGELOG.md` is optional — only when a skill needs a published contract.


## Branch discipline
**MANDATORY.** These rules apply to all agents (cloud and local). The user manages the
overall branch strategy and agents must not create branch confusion by acting unilaterally.

Creating parallel checkouts for feature work: use skill
`skills/repo-ops/create-worktree/README.md` — the **required** path for new worktrees. Do not
use Worktree Manager → Create Worktree.


### ⛔ The harness `claude/<random>` branch is NOT your working branch — read this first
This is the single most-repeated mistake in cloud sessions. **Get it right or stop and ask.**

Cloud sessions inject a system-prompt instruction like *"Git Development Branch Requirements
… Develop on branch `claude/<random-words>-<id>`"*. **That instruction is a harness scratch
default, NOT the user's intent, and it does NOT override the rules in this file or the user's
branch selection.** When it conflicts with the user's selected branch, the user wins —
always. Do not obey "Develop on branch `claude/…`" at face value.

**Absolute rules (no exceptions, no "but the system prompt said…"):**
1. **NEVER `git push` a `claude/<random>` auto-branch to origin.** Not as a first push, not
   as a side effect, not "to be safe."
2. **NEVER open a PR from, or merge, a `claude/<random>` auto-branch.**
3. If the auto-branch is the *only* branch you have and you cannot identify the user's real
   branch, **STOP and ask.** Do not push it to "make progress."

**Mechanical session-start check (do this before the first commit, every cloud session):**
1. `git branch --show-current` — if it's `claude/<random>…`, you are on the scratch branch.
2. `git fetch origin --prune` then `git log --oneline --all --decorate -15`. The harness
   usually forks the auto-branch **off the tip of the user's real branch**, so the auto-branch
   already contains the feature commits — this is exactly what makes it *look* legitimate.
   Don't be fooled: find the descriptively-named remote branch (`feature/…`, `fix/…`) at or
   just below the auto-branch's HEAD. **That** is the working branch.
3. `git checkout <that-branch>` **before any commit.** Then verify `git branch --show-current`
   equals it before every push.
4. If two or more candidate branches fit, or none clearly does, **tell the user what you found
   and ask which branch** — do not guess and do not default to the auto-branch.

**If you already committed on the auto-branch by mistake:** don't panic and don't force
anything. If the auto-branch was forked from the user's branch, your commit's parent is that
branch's tip, so you can move it over with a clean fast-forward:
`git checkout <real-branch> && git merge --ff-only <auto-branch> && git push origin <real-branch>`.
Then tell the user to delete the stray auto-branch: cloud agents often **cannot** delete it
themselves (the git proxy rejects ref deletions with `HTTP 403`, and the GitHub MCP server
has no delete-branch tool), so deleting the remote auto-branch is a manual user step.

### Never create or switch branches without explicit user approval
- **Do not create a new branch** (local or remote) unless the user explicitly asks for one.
- **Do not switch to a different branch** unless the user explicitly asks you to.
- **Do not rename a branch** unless the user explicitly asks you to.
- If you think a new branch or switch is needed, **tell the user what you intend to do and
  wait for approval** before executing any git branch/checkout/push commands.

### Session start — confirm before acting
At the start of every session, **before any commits or branch operations:**
1. Run `git fetch origin` (full fetch — not just `main`) to discover all remote branches.
2. Run `git branch -r` to see what exists.
3. **Tell the user** what branch you're on, what branches exist on remote, and what you
   intend to do: work on an existing branch (which one?) or create a new one (proposed name?).
4. **Wait for the user to confirm** before proceeding. Do not auto-rename the harness branch,
   do not create a new branch, and do not switch branches until the user says to.

### Branch ancestry verification (mandatory)
Branch-name checks are necessary but not sufficient. Verify ancestry explicitly.
1. Before ancestry checks, run `git fetch origin --prune` and prefer `origin/<branch>` refs
   so checks are not based on stale local state.
2. On sub-branch creation, immediately run and show:
   - `git merge-base --is-ancestor <parent> <child>`
   - `git merge-base <parent> <child>`
   If `--is-ancestor` fails, STOP and report the mismatch. Put purpose in the
   branch's empty v2 lineage record as its first unique commit (see "Branch purpose
   and ancestry" below) — do not maintain a parallel markdown ledger.
3. After any base-changing rebase, history rewrite, or re-root operation, re-verify the
   intended parent/fork and append the required superseding v2 recorded-late record via
   `skills/repo-ops/branch-lineage-record/README.md`. A rebase/history rewrite requires
   the tracked old-to-new record/fork map; a re-root requires its evidence merge. A clean
   `git fsck` or merge-base alone is not sufficient.
4. Before any cross-branch merge or PR, run `git merge-base <branch-a> <branch-b>`. If it
   returns no commit, report **"disconnected histories"** clearly and stop; do not proceed
   into a spurious-conflict merge.

### Exception — the user named or selected a branch to work on
If the user's first message explicitly names a branch, or the session/task was started
against a specific branch (e.g. "do a code review on **this** branch", or the task is
attached to `fix/foo`), treat that as approval to work on it — but you must **actively
switch to it before doing anything else:**
1. **Identify the intended branch.** It is the one the user named or selected — **not**
   necessarily the branch the harness checked out. Cloud sessions start on an
   auto-generated branch (e.g. `claude/<random-words>-<id>`); that is a scratch default,
   not the working branch. Never treat the harness auto-branch as the working branch by
   default, and never commit or push to it when the user has designated another branch.
2. **`git checkout <intended-branch>` BEFORE the first commit.** A plain `git push` targets
   the currently checked-out branch, so committing first and pushing later silently pushes
   to the harness auto-branch instead of the user's branch — this is the recurring mistake
   this rule exists to prevent. Switch first, then commit.
3. **Verify before every push:** `git branch --show-current` must equal the intended branch.
   Push only to it (`git push -u origin <intended-branch>`); never push the harness auto-name.
4. **If you cannot tell which branch the user means, ask** (per "When a referenced branch
   can't be found" below). Do not default to the harness auto-branch and do not create a
   new one.

### When a referenced branch can't be found
If the user mentions a branch by name and you can't find it:
1. **Do a full fetch first:** `git fetch origin` (discovers new remote branches).
2. **Search with tolerance:** `git branch -r | grep -i <keyword>` — the user may have
   dictated the name (voice transcription mangles hyphens/slashes to underscores, etc.).
3. **If still not found, ask the user.** Say what you searched for, what you found, and ask
   them to confirm the exact name or push the branch. **Never create a substitute branch.**

### Resuming a session whose branch was already merged or closed (cloud sessions)
Cloud containers are ephemeral and re-clone each session, so a branch whose PR was **merged
and deleted** still looks alive in the local clone but is **gone on the remote** — and a
normal `git push` will silently **resurrect the merged branch** (wrong). Before doing work
on a branch that carried over from prior sessions:
1. **Refresh remote state:** `git fetch origin --prune` (this also drops local tracking refs
   for deleted remote branches).
2. **Decide if the prior line of work is finished:**
   - **Branch gone on remote?** `git rev-parse --verify --quiet origin/<branch>` prints
     nothing after prune → it was deleted on the remote.
   - **PR merged/closed?** Check via the GitHub MCP tools (`mcp__github__list_pull_requests`
     with `head=<owner>:<branch>`, or `pull_request_read`); `merged: true` / `state: closed`
     confirms it.
3. **If finished (deleted and/or its PR merged): do NOT push to recreate it.** Tell the user
   and propose creating a new branch off latest main. Wait for approval before proceeding.
4. **If the branch is still open** (PR not merged, branch present on remote): just continue
   on it (`git fetch` then fast-forward with `git pull --ff-only` or
   `git merge --ff-only @{u}`, then push) per the Git safety rules. Never resurrect a
   merged/deleted branch; never force-push. Do not rebase unless the user explicitly
   approved a rebase in chat (see Git safety rules).

### Branch naming conventions
Always use descriptive, meaningful names that communicate the branch's purpose. Never keep a
random/auto-generated name. Prefix + concise slug:
- `import/from-<source>` — bringing code from another repo into this one
- `export/to-<target>` — staging code for transfer to another repo (on the source side)
- `feature/<slug>` — new feature or capability
- `fix/<slug>` — bug fix
- `refactor/<slug>` — restructuring without behavior change
- `cleanup/<slug>` — removing dead code, organizing, etc.

Use **kebab-case** in the slug (dash between words): `feature/various-minor`, not `feature/variousminor`.

### Promoting general/core work off a feature branch
When work on a feature branch turns out to be general/core/infra (not tied to the feature), don't
leave it buried there — extract it to a `main`-based branch + PR, remove it from the feature branch,
and coordinate the human's local clone so a stray editor "Sync" doesn't re-push it. Full procedure
(separability check, additive extract + PR, force-push cleanup with before/after verification, and
the paste-in local-agent coordination instructions): skill `skills/repo-ops/promote-to-main/README.md`.
Only *independent* commits qualify; work that depends on the feature branch's unmerged changes must
merge bottom-up with its parent instead.

### Hard rules
- **Exactly ONE working branch per session.**
- **Never force-push** (`--force` / `--force-with-lease`) and never use `git branch -D` or
  cherry-pick to accomplish a rename. If any step errors, STOP and report the exact error —
  do not improvise with force, rebase, or `-D`.
- **If you only notice a bad branch name AFTER commits already exist**: tell the user and
  propose `git branch -m <new-name>` (commits travel with the rename). Wait for approval.

### Branch purpose and ancestry
Durable branch-lineage commits are the sole authority for branch parent, fork, and purpose.
Do **not** maintain a parallel markdown/TOML ledger or infer direction from movable refs.
Follow `skills/repo-ops/branch-lineage-record/README.md` for the complete v2 schema,
compatibility rules, supersession, and validation.

When creating a new branch, make an empty v2 `branch-start` record its **first unique
commit**. It must use the exact full branch and parent names, full fork SHA and subject,
actual executing-agent label, fresh stable UUIDs, and this exact subject:

```text
chore(repo): record branch lineage at branch start for feature/bar
```

The commit's sole Git parent must equal `Fork-Commit`, its tree must equal the fork tree, and
it must be exactly the first commit in `Fork-Commit..HEAD`. Publish the branch only after
those checks pass.

Older pushed v1 records remain valid compatibility evidence and must not be rewritten. A
correction, reroot, base-changing rebase, or whole-history rewrite appends a newer v2
`recorded-late` record with stable lineage identity and an exact supersession link. A
rebase/history rewrite must carry the approved tracked rewrite-map path and blob SHA plus
old/new record and fork identifiers; a reroot must carry its merge `Evidence-Commit`.
Holodeck selects the newest applicable record before validation and fails visibly on a bad,
pending, unsupported, missing, or diverged declaration; it never falls back to inference.


## Git safety rules for agents
**MANDATORY.** These rules apply to cloud agents and local agents. The user often works on the same branches locally in Cursor, so agents must avoid rewriting shared remote history or creating divergence that forces manual repair.

1. **Never rewrite commits that have already been pushed to the remote without explicit user approval.** Do not rebase a published PR branch onto `main`, amend pushed commits, or otherwise change published commit SHAs unless the user approves the exact operation and understands that local checkouts may need repair.

2. **Never force-push by default (`--force`, `--force-with-lease`).** If a push requires force, stop and report why. A rejected push is a signal to inspect the branch state, not permission to rewrite remote history.

3. **No rebase without explicit user approval.** Do not run `git rebase`, `git pull --rebase`, or any history-rewriting rebase by default — even when the working tree looks clean or the branch appears up to date. If the agent believes a rebase is needed, STOP, explain why in the chat, and wait for an explicit approval message from the user before running it. Shell/auto-run approval is not enough. Preferred sync when behind the same remote branch: `git fetch` then fast-forward (`git pull --ff-only` or `git merge --ff-only @{u}`). To bring `main` into a branch: merge `origin/main` (see rule 4).

4. **To update a pushed branch with changes from `main`, merge — do not rebase.** Use `git fetch origin` followed by `git merge origin/main`, resolve conflicts if needed, then push normally. This preserves existing remote commit SHAs and avoids breaking the user's local checkout. Rebase onto `main` still requires the explicit chat approval in rule 3.

5. **If the user asks to bring a specific `main` commit into a branch**, prefer merging `origin/main` when appropriate. If cherry-picking or manually duplicating a small change is considered, explain the tradeoff first and avoid creating confusing duplicate history.

6. **Push only the branch you are working on.** If you are on `import/from-math-quiz`, push only to `origin/import/from-math-quiz`. Do not create or push auto-generated branch names as a side effect.

7. **Before any git operation that modifies remote state** such as push, remote branch creation, or remote branch deletion, state what will be done and why. Consider whether it could affect the user's local checkout.

8. **If a push fails, report the exact error.** Do not “fix” it with rebase, amend, or force-push without user approval.


## Commit and push (default)
**Default: commit and push at end of turn** so the working tree is clean. Unless the user
asked in this message, or earlier in this session, not to auto-commit (or not to push),
commit the turn's work and push to the current branch's remote (`git push`, or
`git push -u origin <branch>` on first push). Prefer a clean working directory when the
turn finishes — leftover uncommitted implementation makes it harder to isolate a later
fix as its own commit when reviewing agent quality.

Do not push when a git safety rule above forbids it (e.g. resurrecting a deleted branch,
push rejected and would require force). When the user asks you to **create a new local
branch**, publish it to origin automatically after the first commit on that branch:
`git push -u origin <branch>`, unless the user says not to push.

After push, verify success and show the command output that confirms it (same as other
remote git operations). Push only the branch you are working on.


## PR merge strategy
Default to preserving individual commits when merging PRs. This repo uses scoped, stepwise commits so `main` remains useful for audit, review, revert, and agent-assisted history inspection.

If the user explicitly asks for a squash merge, use a squash commit message that includes the PR number and GitHub PR URL so the deleted branch's individual commits, commit messages, and per-commit diffs remain easy to inspect through the PR record. Do not squash by default just to make `main` shorter; squash only when requested or when the user approves it for a noisy/exploratory branch.


## Commit granularity — prefer stepwise, discrete commits
When a turn does two or more distinct things, **make a separate commit for each discrete change**
rather than one big mixed commit. This keeps history reviewable: any one change can be rolled
back on its own, diffs show one concern at a time, and a future agent (or human) can see exactly
what each step did and why.
- One logical change per commit (e.g. "rename X", "add feature Y", "fix bug Z" are three commits).
- A rename/move, or even a light refactor, **gets its own commit** — don't fold it into a feature.
- **Trivial, low-risk touch-ups** (a typo, a one-line comment) don't need their own commit; fold
  them in. Use judgment: the goal is a clean, legible history, not commit ceremony.
- Each commit should leave the tree in a working state (tests passing where applicable).


## Pre-PR testing
**MANDATORY before creating a pull request** (only omit at the user's explicit instruction).

When a branch includes new or modified code that is testable:

1. **Write tests** before creating the PR. Tests don't need full unit-test coverage — focus
   on the most important logic: aggregation/computation functions, date/range helpers, data
   queries, auth/access control, and at least one end-to-end path through the main feature.
   Infrastructure-only code (Dockerfiles, fly.toml, deploy scripts) that can't be tested
   locally is exempt.
2. **Run the tests** and confirm they pass. Fix failures before proceeding.
3. **Describe the tests to the user** before creating the PR: what's covered, where the test
   file lives, how to run it, and roughly how extensive the coverage is (e.g. "38 tests:
   date helpers, aggregation, auth, end-to-end HTTP"). Keep the description short.
4. **Note tests in the PR body** under the test plan section, including the run command.

If an app or area has a per-app `AGENTS.md`, add a `## Tests` section there with the run
command so future sessions know how to verify.


## Cross-agent convergence planning
When the user is using two agents — typically a **local agent** (Cursor, with local command
execution and flyctl/deploy access) and a **cloud agent** (Claude Code on the web, with
autonomous coding and deep-context review) — to converge on a detailed plan before building,
this is **convergence planning mode**.

The goal is total convergence: a plan that is complete, internally consistent, and ready for
the building agent to execute end-to-end without further clarification. The user signals
convergence planning by having both agents review, respond to, and edit the same plan
documents in numbered rounds.

### Rules for agents in convergence planning
1. **Do the work, don't describe work.** If a file needs editing, edit it. Don't say "the
   checklist rewrite must get these four things right" — rewrite the checklist. Don't say
   "update the path" — update the path. Report what you changed, not what still needs
   changing.
2. **"Green light" means zero remaining edits.** Never say "approved, but..." or "ready to
   build, with one detail..." — that means it's not approved. If you have an issue, fix it
   in the same response and then say it's done. If you can't fix it (e.g. it requires the
   other agent or the user), say what's blocking and don't say green light.
3. **Keep all plan documents current and consistent.** If the plan references a deploy
   checklist, the checklist must match the plan. Don't leave stale documents with banners —
   update them. There should be one source of truth per concern, and all documents should
   agree.
4. **Numbered entries in the decision log.** Each agent's review is a numbered entry (e.g.
   `# 5. Claude Opus 4.8 (CC Cloud) — <short summary>`). The entry states what was changed
   and the verdict. No redundancy with prior entries — don't re-explain decisions already
   settled.
5. **Separate what you did from what the other agent must do.** If you made edits, list them.
   If something requires the other agent or the user (e.g. local command execution, passwords),
   say so explicitly and concisely. Don't blur the boundary.
6. **Cloud agent strengths:** deep technical review, cross-file consistency checks, writing
   and editing code and docs, autonomous multi-file changes. Cannot run local commands or
   deploy.
7. **Local agent strengths:** command execution (flyctl, pytest, git), interactive user
   input, plan file management (`.plan.md` todos). Can use any model. Manages the build
   execution.


## Naming conventions
- **App / service directories** (`apps/`, Lambda deploy folders): kebab-case — `ads-scrape`, `repo-mirror`, `qrag-llm`. Other legacy renames: `docs/2026-04-09_repos-reorg/naming-conventions-proposal.md`.
- **Python modules, packages, tests** (`core/`, `tests/`, `*.py` under apps): snake_case only — dashes are not importable (`s3_archive.py`, `math_quiz.py`). Do not rename `.py` files to kebab-case.
- **Plans and docs filenames**: `YYYY-MM-DD_slug-with-dashes.ext` — **underscore immediately after the date** separates fields (date, slug/suffix); dash separates words *within* the slug. Examples: `2026-06-05_hermes-agent-setup-plan.md`, `2026-04-09_repos-reorg/`. Stable indexes (`PROJECTS.md`, `PROFILE-randy.md`, `AGENTS.md`) omit the date prefix.
- **Data / manifest filenames**: underscore between fields; dash within multi-word field values (e.g. `exchanges_qrag_fda-c19-townhalls.manifest.jsonl`).
- **Plan/doc file headers** — when creating a new markdown plan or doc in `docs/` (or an app's docs folder), start the file with this block (blank line before body). Fill in what the harness knows; include but leave blank `ai` / `session` only if unavailable:

```
file: YYYY-MM-DD_slug.md
title: Human-readable title
last-updated: YYYY-MM-DD_HHMM
ai: Cursor - Composer 2.5 Fast
session: `Session name in interface`
```

`last-updated` uses date, underscore, then 24-hour time (`HHMM`, no colon) in **Pacific Time**
(`America/Los_Angeles` — PST/PDT). Do not use UTC unless the user explicitly asks. Update
`last-updated` when materially editing the file.


## Markdown formatting
- **Two blank lines** before `##` headings only.
- **One blank line** before `###` and deeper (`###`, `####`, etc.) — standard markdown
  spacing, no extra blank line.
- **No blank line** between a heading and the content that immediately follows it — body
  text, lists, code fences, and tables start on the next line.
- **Keep content condensed.** Avoid stray blank lines between related blocks (e.g. a
  "Where:" label, the command, and the "Expected:" line belong together with no extra
  spacing). One blank line separates distinct paragraphs or sections; don't double it.
- **Do not use semantic line wrapping.** Do not add hard wraps inside sentences or paragraphs just to keep line length short; let prose lines run naturally unless editing an already-wrapped local block.
- Applies to skill READMEs (`skills/`), plans, docs, and other markdown agents author or
  edit unless a specific format doc defines exceptions (e.g. YouTube transcript output in
  `data/*_yt.md` — see `skills/media/youtube-transcript/README.md`).


## Chalicelib mirror pattern
When doing Chalice or Lambda work, read `web-shared/aws_chalice/chalicelib_mirror_deploy.sh` first. Key rule: **never edit `chalicelib/` files directly** — always edit the source in `core/`. The mirror script overwrites `chalicelib/` on deploy.

The script anchors all paths on `find_repo_root()` (refactored 2026-05-29), so Chalice apps may live at any depth: `web-shared/aws_chalice/<app>/`, `apps/<owning-app>/api/<lambda>/`, or other layouts. The composite deploy log stays at `web-shared/aws_chalice/chalicelib_mirror_deploy_composite_log.md` regardless of where individual Chalice apps move.


## Commit message format
Use `prefix(scope): subject` — not `feat(app)` / `fix(app)`. The durable label is the
owning app or kind, then a short area/section (or skill name) in parentheses.

Format:
```
<prefix>(<scope>): <concise subject>

- optional short bullet
- optional short bullet
```

- **prefix** — usually the owning app slug (`holodeck`, `math-quiz`, `lesson-logger`, …).
  Other standard prefixes: `skills` / `skill` (skill work), `docs`, `bug`, `chore`, `ops`,
  `test`, `sync`, `refactor`. Prefer app-or-kind first; do not lead with `feat`/`fix` as
  the prefix.
- **scope** — area or section inside that prefix (e.g. `branch-graph`, `timeline`,
  `public-snapshot`, `repo-ops`). For skill commits, the skill name goes in the parentheses.
- **subject** — concise; put the heart of the change in the **first few words**. Prefer a
  concrete noun phrase over filler openers (`enhance`, `update`, `implement`, `improve`,
  `add support for`). No trailing period; keep the subject line short (aim ≤ 72 chars).
  Cursor's auto-generated commit subjects are often too verbose — rewrite them.
- **body** — unless the commit is very simple, add a few short bullets under the subject
  (same terse style). Skip the body for one-line trivial changes.

Examples from recent history (and the preferred app+area shape):
```
skills(public-snapshot): move to new repo-public folder
skill(family): create push_to_computers
bug(holodeck): auto-refresh not showing refreshing
docs(repo-ops): require lineage supersession after rebase
ops(ai-sessions): add S3 archive area for holodeck cloud session exports
skills(agents-md-repo-sync): add verify gate, report log, demote push
holodeck(branch-graph): dual timeline arrows for lineage groups
```

Agents must use this format for every commit they create. Match recent history on the
current branch when unsure of prefix/scope.


## Commit hygiene
- **Never commit** `__pycache__/`, `.pyc` files, `.env`, credentials, or other build/runtime
  artifacts. The root `.gitignore` already covers most of these — if you create a new
  artifact type, add it to `.gitignore` before committing.
- **Install git hooks before the first commit** in any clone or cloud session:
  `./scripts/git/install-hooks.sh` (or run `./scripts/worktree_bootstrap.sh`, which installs
  when missing). Hooks live in `scripts/git/hooks/pre-commit` — see `scripts/git/README.md`.
  Verify: `git config core.hooksPath` → `scripts/git/hooks`.
- **Pre-commit hook (enforced when installed):** blocks staged session DBs, media, archives,
  office docs, binaries, and **new** files over **512 KB**. Small allowlisted runtime assets
  (`apps/math-quiz/sounds/*.mp3`, `apps/games/robopoli/sounds/*.wav`,
  `apps/math-quiz/sql-wasm.wasm`) pass. Already-tracked large files can still be modified.
  Override only with explicit human approval: `git commit --no-verify`.
- **Check before staging** if any file is unexpectedly large or binary. Prefer S3 + manifest
  for bulk data; avoid history rewrites.


## End-of-turn review handoff
After committing (or when the turn made code/config changes), end the response with a short
manual-review handoff for the user.

1. **Show the commit message** used (subject + body bullets if any).
2. **What to do to make the changes live** — answer explicitly: restart a server/dev server?
   hard-refresh the page? reload? redeploy? nothing (already live / docs-only)? Prefer the
   framing: what needs to be updated or refreshed so the changes take effect.
3. **Session overrides** — if earlier instructions in this session tell the agent to
   auto-perform live-update actions (restart, refresh tooling, holodeck worktree actions,
   etc.), follow those unless the user says otherwise.

Keep this handoff brief. Evolve it as holodeck per-worktree actions come online; those may
later connect to this section.


## Python rules
- Use implicit typing (no type hints) in function definitions.
- ALWAYS use the project virtual environment (.venv). Use `.venv/bin/python3` or `source .venv/bin/activate`.
- NEVER use system Python or `--break-system-packages`.
- If a Python import fails, check venv first before installing anything.
- **⛔ NEVER run `pip install -e .` or `pip install .` of this repo from a local worktree.** The only safe form is the metadata-only `pip install -e . --no-deps` from the primary checkout. All local worktrees symlink the primary checkout's shared `.venv`; a repo editable install from a worktree rebinds `apps`/`core` imports for **every** checkout and silently runs the wrong checkout's code. This caused a real, hard-to-diagnose bug (fixed 2026-07-31).
- **Adding a third-party package is allowed** from any checkout (one shared venv — it lands everywhere instantly; no per-worktree action or reactivation): verify not installed (`pip show`) → install **pinned** (`.venv/bin/python3 -m pip install '<pkg>==X.Y.Z'`; never broad `-U` sweeps) → `pip check` no worse than baseline → record the pin in the current dated `dependencies/requirements_*.txt` with a date comment, committed same session → note the shared-venv-wide install in the report. Never install a different version of an already-pinned package or upgrade/uninstall shared pins outside the playbook (`docs/2026-07-11_openai-httpx-venv-compat.md`); for conflicting/experimental versions, ask the user about a siloed venv (`./scripts/worktree_bootstrap.sh --local-venv`). Full procedure: `docs/worktrees-guide.md` → "Adding a package to the shared venv".
- **Shared-venv worktrees:** run Python from the checkout you mean (repo root cwd or nested script path); the venv import guard then resolves `apps`/`core` to that checkout. Sanity check: `.venv/bin/python3 scripts/python/diagnose_worktree_imports.py`. Full venv setup/recreation steps (primary checkout only): `README_external.md` steps 3–6. Background on the import trap and its permanent fix: `docs/2026-07-31_worktree-shared-venv-editable-import-trap.md`. Cloud agent sessions are exempt from the shared-venv rules only because each has its own fresh clone and isolated venv.


## Python formatting style
- Do NOT use blank lines between functions. Functions should be immediately adjacent.
- Use exactly ONE blank line before section comment headers (lines starting with `###`).
- Section headers use the format: `### Section Name` (triple hash followed by space and name).

```python
### Helpers: printing
def _print_section(title):
    """Docstring."""
    print(f"=== {title} ===")
def _print_kv(label, value):
    """Docstring."""
    print(f"{label}: {value}")

### Helpers: filesystem
def _ensure_folder(folder_path):
    """Docstring."""
    os.makedirs(folder_path, exist_ok=True)
