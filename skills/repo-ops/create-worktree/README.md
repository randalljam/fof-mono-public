file: skills/repo-ops/create-worktree/README.md
title: Create a git worktree (parallel Cursor window)
source-github-url: original
source-guide-url: original
history:
  - 2026-07-31 · Randy · Cursor [Permanent worktree import fix](permanent_worktree_import_fix) — bootstrap verifies worktree import guard after venv setup
  - 2026-07-30 · Randy · Codex [Codex Workspace Setup](019faf02-bddf-76c1-bbfc-6e43cc8b0adf) — replace retired start metadata with the durable v2 branch-lineage record and structural verification
  - 2026-07-28 · Randy · Codex local Holodeck parent derivation — create a canonical first commit with exact branch, purpose, and Parent metadata before publishing every new branch
  - 2026-07-23 · Randy · Cursor — on window open: auto terminal + `.venv` activate via folderOpen task + `task.allowAutomaticTasks` / `python.terminal.activateEnvironment`; bootstrap copies `.vscode/tasks.json` from main
  - 2026-07-23 · Randy · Cursor — preview scans app `requirements.txt`, classifies lambda-deploy vs local-app, and proposes shared vs `--local-venv` (with optional `REQ=`) from that scan instead of a “no memory” rule
  - 2026-07-23 · Randy · Cursor — document shared `.venv` (symlink to main) as default; preview states venv mode; optional `--local-venv`
  - 2026-07-11 · Randy · Cursor holodeck worktrees — apply stable colors from `apps/holodeck/worktree-colors.yaml` to `.vscode/settings.json` when worktree slug matches a rule; fall back to deterministic hash
  - 2026-07-02 · Randy · Cursor [create-worktree skill](35074399) — clarify it runs from any branch/any state; add new-branch base rule (origin/main on main, else current HEAD, user-overridable) and require the preview to state the base explicitly
  - 2026-07-02 · Randy · Cursor [create-worktree skill](35074399) — add confirm-first preview (state detection, contradiction flag, last-commit + color info, ask to proceed); document that all steps run from the initiating window
  - 2026-07-02 · Randy · Cursor [create-worktree skill](35074399) — initial procedure; replaces Worktree Manager menu creation and guide TL;DR


**Use this skill when the user asks to create a worktree, open a branch in a new Cursor window, or check out a cloud-agent branch locally.** This is the **only** supported path for worktree creation — do not use the Worktree Manager **+** menu or the old guide TL;DR/commands blocks (retired 2026-07-02; see `docs/worktrees-guide.md`).

**Confirm before acting.** The agent's **first reply must be a preview** (state detection +
contradiction check + plan) that ends by asking the user to proceed — it does **not** run
`git worktree add`, bootstrap, or open a window until the user confirms. See
[First reply: preview and confirm](#first-reply-preview-and-confirm).

**Everything runs from the initiating window.** All steps are path-addressable against the
shared repo (`git worktree add <path>`, `worktree_bootstrap.sh <path>`, `apply-color <path>/…`,
`cursor <path>`), so the agent runs the **entire** flow from the window it was invoked in. The
new worktree window opens **ready to go** — the user does **not** need to invoke a second agent
inside it.


## When to use
- User says "create a worktree for `<branch>`" or describes a branch in plain English.
- A cloud agent pushed `feature/<name>` and the user wants a local Cursor window on it.
- User needs a new branch checked out in a sibling folder without touching the main `fof-mono` window.

Do **not** use Worktree Manager → **Create Worktree** (`+`). It cannot distinguish remote-only from diverged local branches and has stranded branches on stale `main`.


## Prerequisites
- Run from **any checkout of the repo, on any branch, in any working-tree state** — you do **not**
  need a synced or clean `main`. `git worktree add` operates on the shared repo, so the initiating
  checkout's current branch and dirty/clean state do not affect the result. (Only restriction:
  the initiating checkout must not already have branch `B` checked out — a branch can live in one
  worktree at a time.)
- `FOF_MONO_LOCAL_FILES_ROOT` must be set on this machine (see `skills/repo-ops/clone-bootstrap/README.md`). Bootstrap mount checks fail when it points at the wrong user's home.
- `cursor` CLI on `PATH` for opening the new window.
- Clone bootstrap completed once on this machine (hooks, local-files mounts).

The only thing that depends on your context is the **base** for a *new* branch — see
[Base for a new branch](#base-for-a-new-branch). For an *existing* branch there is no choice:
it always anchors on that branch's ref regardless of where you are.


## Helper script
Pure, testable helpers live at `skills/repo-ops/create-worktree/scripts/worktree_identity.py`:

```bash
.venv/bin/python3 skills/repo-ops/create-worktree/scripts/worktree_identity.py plan feature/my-branch --parent "$(git rev-parse --show-toplevel)"
.venv/bin/python3 skills/repo-ops/create-worktree/scripts/worktree_identity.py lineage-message feature/my-branch --parent main --purpose "one-line branch purpose" --fork-commit "<full SHA>" --fork-subject "<exact subject>" --created-by "<Holodeck label>" --lineage-id "<UUID>" --record-id "<UUID>"
.venv/bin/python3 skills/repo-ops/create-worktree/scripts/worktree_identity.py apply-color .vscode/settings.json feature/my-branch
```

Commands: `slug`, `path`, `lineage-message`, `color`, `apply-color`, `plan`.


## Fuzzy branch resolution (plain-English input)
When the user does not give an exact branch name:

1. Run `git fetch origin --prune`.
2. Collect candidates from `git branch -a` (strip `remotes/origin/` prefix; drop `HEAD`).
3. Normalize user input and branch names: lowercase; treat `/`, `_`, `-`, and spaces as equivalent token separators.
4. Match when every token in the user phrase appears in the branch name (case-insensitive).
5. **One match** → confirm the resolved name with the user, then proceed.
6. **Multiple matches** → list candidates; ask which branch.
7. **Zero matches** → re-fetch, widen search (drop tokens, try substring), then ask. **Never invent a branch name.**

Follow `AGENTS.md` → "When a referenced branch can't be found" if still ambiguous.


## Branch-state decision table
After resolving branch name `B`, classify state and pick the `git worktree add` form. Always `git fetch origin --prune` first.

| State | Action |
|-------|--------|
| Neither local `B` nor `origin/B` exists | New branch — anchor on the resolved base (see [Base for a new branch](#base-for-a-new-branch)): `git worktree add -b B <path> <base>` |
| `origin/B` exists, no local `B` (typical cloud-agent case) | `git worktree add -b B <path> origin/B` |
| Local `B` exists AND `git rev-parse B` == `git rev-parse origin/B` | `git worktree add <path> B` |
| Local `B` exists but **diverged** from `origin/B` | **STOP.** Show `git log --oneline origin/B..B` (local-only) and `git log --oneline B..origin/B` (remote-only). Ask before `git branch -f B origin/B` then `git worktree add <path> B` |
| Local `B` exists, no `origin/B` (purely local) | `git worktree add <path> B` (bootstrap will publish) |
| `B` already checked out in another worktree | **STOP.** Report `git worktree list`; a branch can live in only one worktree |

**Worktree path `<path>`:** sibling folder next to the main checkout. Use the helper:

```bash
REPO="$(git rev-parse --show-toplevel)"
PATH="$(
  .venv/bin/python3 skills/repo-ops/create-worktree/scripts/worktree_identity.py path "$REPO" "$B"
)"
```

Convention: slashes in `B` become dashes (e.g. `feature/math-quiz` → `../feature-math-quiz` under `Documents/Code/`).


## Base for a new branch
Only relevant when `B` is **brand-new** (neither local nor remote). Pick the base by where the
agent was invoked, then **state it explicitly in the preview** and let the user override.

**Default base:**
- Initiating checkout is on **`main`** → base on **`origin/main`** (fetched tip, never stale
  local `main` — avoids the trap in `AGENTS.md` → Branch discipline / worktrees guide).
- Initiating checkout is on **any other branch** → base on the **current position** (that
  checkout's `HEAD`), so you can stack a new branch off the branch you're working on.

**Override:** the user can name any base, e.g. "off the tip of `main`, not from here", "off
`origin/feature/foo`". Honor it. They should never *have* to say "not from here" — the preview
already states the base, so they only speak up to change it.

Detect and resolve:

```bash
CURRENT="$(git rev-parse --abbrev-ref HEAD)"
if [ "$CURRENT" = "main" ]; then
  BASE="origin/main"          # fresh tip after fetch
else
  BASE="HEAD"                 # current position of the branch you're on
fi
# User override, when given, replaces BASE (e.g. BASE="origin/main").
git worktree add -b "$B" "$PATH" "$BASE"
```

For an **existing** branch this section does not apply — the base is fixed (`origin/B`, or `B`
when in sync / purely local).


## Virtual environment
**Default: shared `.venv`** — bootstrap symlinks `<worktree>/.venv` → the main checkout's
`.venv` (usually `…/fof-mono/.venv` on `main`). One install, less disk, and every worktree
already has the monorepo Python tooling. Cursor settings from main set
`python.defaultInterpreterPath` to `${workspaceFolder}/.venv/bin/python`, so the new window
resolves through that symlink. Agents always invoke `.venv/bin/python3` (never system
Python); no separate `activate` step is required for the skill flow.

**Detect from the branch / app (do this in the preview).** Do not rely on a remembered
prior worktree venv — git does not keep closed-worktree registration history. Instead,
infer the app focus from the branch name and the user's request, then **scan that app
tree for `requirements.txt`** and classify each hit before proposing venv mode:

| Class | How to recognize | Meaning for this skill |
|-------|------------------|------------------------|
| **lambda-deploy** | Next to Chalice `app.py` / `.chalice/`, or file lists `chalice` as a top dep; under `apps/*/api/*` or `web-shared/aws_chalice/*` | Packaged into the AWS Lambda deploy zip by `chalice deploy`. **Not** a signal for a worktree-local venv. Keep **shared** `.venv` for local Python. |
| **local-app** | FastAPI/uvicorn (or similar) local server; README says `pip install -r requirements.txt` to run/tests (e.g. `apps/minecraft/prism-sync`, `apps/education/lesson-logger/dashboard`) | App-specific package list for **local** runs. Default remains **shared** (often `repo/.venv/bin/pip install -r <app>/requirements.txt`). Offer **`--local-venv`** with `REQ=<that file>` when the user wants isolation or a smaller env. |
| **monorepo** | `dependencies/requirements_*.txt` | Source of truth for the shared main `.venv`. |

Scan commands (read-only, during preview):

```bash
# Infer app roots from branch tokens / user wording, then:
find apps/<app> web-shared/aws_chalice -name requirements.txt 2>/dev/null
# Also check a focused path the user named, e.g. apps/minecraft/prism-sync
```

**Preview must state:** each relevant `requirements.txt` path, its class
(lambda-deploy / local-app / monorepo), and the proposed venv mode. If only
lambda-deploy files match → shared. If a local-app file matches → shared by default,
but call out the local-app file and ask whether to silo with that `REQ`.

**Optional: siloed `.venv`** — user asks, or preview proposes after a **local-app** hit:

```bash
# Full monorepo requirements into a worktree-local venv:
./scripts/worktree_bootstrap.sh "$PATH" --local-venv

# Smaller / app-specific install (bootstrap honors REQ):
REQ="$MAIN/apps/minecraft/prism-sync/requirements.txt" \
  ./scripts/worktree_bootstrap.sh "$PATH" --local-venv
```

Package lists stay in git; which folder holds the install is chosen at bootstrap from this
scan + user confirmation. Details: `docs/worktrees-guide.md` → "Shared vs siloed virtualenv".


## First reply: preview and confirm
**Do not jump in and build.** After fetching and classifying state (read-only steps), the
agent's **first response** is a preview that ends by asking permission to proceed. Only run
`git worktree add` and everything after it once the user confirms.

The preview must:

1. **State detection** — say plainly whether `B` **already exists on remote** (`origin/B`),
   exists only locally, exists in both, or is **brand-new** (no local, no remote).
2. **Base statement (new branch only)** — explicitly state what the new branch will be created
   from (see [Base for a new branch](#base-for-a-new-branch)): `origin/main` when on main, or the
   current branch/position otherwise. Make clear the user can override (e.g. "off the tip of
   `main`, not from here") without having to — the base is already spelled out.
3. **Purpose statement (new branch only)** — state the one-line purpose that will be recorded
   in the branch's durable v2 lineage commit. Ask if the request does not establish a concrete
   purpose; do not publish an unidentified new branch.
4. **Contradiction check (flag big time)** — compare the detected state to what the user asked
   for or implied. If they conflict, **lead with a prominent warning** and do **not** proceed
   past the question. Examples to catch:
   - User said "new branch" but `origin/B` already exists (would reuse existing work, not create fresh).
   - User said "check out the branch the cloud agent pushed" but no `origin/B` exists (nothing to check out).
   - User named branch X but fuzzy match resolved to a different branch Y.
   - User implied a base that conflicts with the default (e.g. "off main" while on a feature branch) — state the resolved base and confirm.
   - Local `B` has **diverged** from `origin/B` (local-only commits would be dropped by a reset).
   - `B` is already checked out in another worktree.
5. **Compact info block** — the header block (template below): target path, branch, new-vs-existing, base, and purpose (for new branches).
6. **Venv mode + requirements scan** — default **shared** (symlink to main `fof-mono/.venv`).
   Scan the inferred app folder(s) for `requirements.txt`, classify each
   (lambda-deploy / local-app / monorepo), and state the proposal. User can override with
   "local venv" / siloed (`--local-venv`, optional `REQ=`). See
   [Virtual environment](#virtual-environment).
7. **Last-commit detail (only if `B`/`origin/B` exists)** — commit count, last commit short
   hash, date, author, and the first line of the last commit message.
8. **Title-bar color** — the color the skill will assign, and a note the user can request a
   different one.
9. **Steps to run** — the concrete actions, emphasizing the v2 branch-start record and
   bootstrap steps (including venv symlink or `--local-venv`). Note that all of
   it runs from **this** window and the new window opens ready to go.
10. **Ask to proceed** — end with an explicit confirmation question.

Gather the facts with read-only commands (no state change):

```bash
git fetch origin --prune
git rev-parse --verify --quiet "origin/$B"    # exists on remote?
git rev-parse --verify --quiet "$B"           # exists locally?
git worktree list                             # already checked out elsewhere?
git rev-parse --abbrev-ref HEAD               # current branch → picks the new-branch base
# If B or origin/B exists, pull last-commit detail from the ref that exists:
REF="origin/$B"; git rev-parse --verify --quiet "$REF" >/dev/null || REF="$B"
git rev-list --count "$REF"
git log -1 --format='%h · %ad · %an · %s' --date=format:'%Y-%m-%d %H:%M' "$REF"
.venv/bin/python3 skills/repo-ops/create-worktree/scripts/worktree_identity.py plan "$B" --parent "$(git rev-parse --show-toplevel)"
# Requirements scan (infer apps/<slug> from B / user wording; classify each hit):
find apps web-shared/aws_chalice -name requirements.txt 2>/dev/null | head -50
```

### Preview template
Adapt to the detected case. Existing-remote-branch example:

```text
Before I create the worktree, here's the plan — confirm to proceed.

⚠️  [only if contradiction] You asked for a NEW branch, but `feature/foo` already exists on
    origin with 12 commits. Creating this worktree will CHECK OUT the existing branch, not
    start fresh. Tell me if you meant a different/new name.

Worktree:   /Users/randytrue/Documents/Code/feature-foo   (branch: feature/foo)
Branch:     already exists on remote (origin/feature/foo)  ← will anchor here
Venv:       shared — symlink <path>/.venv → fof-mono/.venv
App reqs:   apps/qrag/api/qrag-llm/requirements.txt → lambda-deploy (keep shared)
            (say "local venv" for siloed --local-venv; optional REQ= for a local-app file)
Last commit: a1b2c3d · 2026-07-01 14:32 · Randy True · feat(foo): add widget parser
Commits:    12 on origin/feature/foo
Title bar:  #4a2f8c  (say if you want a different color)

Steps I'll run from THIS window (the new window opens ready to go):
  1. git worktree add <path> anchored on origin/feature/foo
  2. ./scripts/worktree_bootstrap.sh <path>
       → symlinks .env + .venv (→ main), mounts local files, merges settings from main
         (Python interpreter → .venv/bin/python), installs git hooks if missing,
         sets upstream / publishes
  3. apply title-bar color to <path>/.vscode/settings.json (uncommitted)
  4. cursor <path>  → opens the new worktree window
       → folderOpen task: bottom terminal + source .venv/bin/activate
  5. verify (branch, upstream, ancestry, .env/.venv symlinks, color) and report proof

Proceed?
```

Brand-new-branch example — note the explicit **Base** and **Venv** lines (state them every time):

```text
Worktree:   /Users/randytrue/Documents/Code/feature-bar   (branch: feature/bar)
Branch:     NEW — no local or remote branch
Base:       origin/main (you're on main)          ← say "off <ref>" to change
            # or, when on another branch:
            # Base: current position of feature/foo (HEAD) — say "off tip of main" to change
Purpose:    <one-line purpose recorded in the v2 branch-start record>
Venv:       shared — symlink → fof-mono/.venv
App reqs:   apps/minecraft/prism-sync/requirements.txt → local-app
            (default still shared + pip into repo .venv; say "local venv" to silo with REQ=)
Title bar:  #2f6d8c  (say if you want a different color)
(no last-commit / commit-count lines — nothing exists yet)
```


## Ordered procedure
Run all steps from the initiating window (the main repo checkout, or whichever checkout
invoked the agent — not the new worktree). **Only start here after the user confirms the
[preview](#first-reply-preview-and-confirm).**

### 1. Fetch (already done for the preview)
```bash
git fetch origin --prune
```

### 2. Resolve branch `B`
Fuzzy-match or take exact name; confirm with user when ambiguous.

### 3. Classify and add worktree
Apply the decision table. Example commands:

```bash
# Remote-only (most common after cloud agent push):
git worktree add -b "$B" "$PATH" "origin/$B"

# Brand-new branch — anchor on the resolved base (see "Base for a new branch"):
git worktree add -b "$B" "$PATH" "$BASE"     # BASE=origin/main on main, else HEAD, or user override

# Local in sync with remote:
git worktree add "$PATH" "$B"
```

If `<path>` already exists, **STOP** and report — do not overwrite.

### 4. Record durable v2 lineage (brand-new branches only)
Before bootstrap publishes a new branch, follow
`skills/repo-ops/branch-lineage-record/README.md` and create its empty v2 `branch-start`
record as the first unique commit. Existing local or remote branches skip this step.

Resolve `PARENT_BRANCH` to the exact full branch name, never `HEAD` or a remote prefix:
`main` for `origin/main`; the initiating branch name when the base is `HEAD`; or the named
branch from a user override. Resolve `CREATED_BY` from the executing task's actual metadata
using `apps/holodeck/turns/labels.py`; never guess. Then capture the untouched fork and create
fresh canonical lowercase UUIDs:

```bash
FORK_COMMIT="$(git -C "$PATH" rev-parse HEAD)"
FORK_SUBJECT="$(git -C "$PATH" log -1 --format=%s "$FORK_COMMIT")"
LINEAGE_ID="$(uuidgen | tr '[:upper:]' '[:lower:]')"
RECORD_ID="$(uuidgen | tr '[:upper:]' '[:lower:]')"
LINEAGE_MESSAGE="$(
  .venv/bin/python3 skills/repo-ops/create-worktree/scripts/worktree_identity.py \
    lineage-message "$B" \
    --parent "$PARENT_BRANCH" \
    --purpose "$PURPOSE" \
    --fork-commit "$FORK_COMMIT" \
    --fork-subject "$FORK_SUBJECT" \
    --created-by "$CREATED_BY" \
    --lineage-id "$LINEAGE_ID" \
    --record-id "$RECORD_ID"
)"
git -C "$PATH" commit --allow-empty -m "$LINEAGE_MESSAGE"
```

Do not stage any file. Verify the structure and exact message before continuing:

```bash
git -C "$PATH" log -1 --format='%H%n%P%n%B'
git -C "$PATH" rev-parse HEAD^ "$FORK_COMMIT"
git -C "$PATH" rev-list --count "$FORK_COMMIT..HEAD"  # exactly 1
git -C "$PATH" diff-tree --no-commit-id --name-only -r HEAD  # empty
git -C "$PATH" rev-parse 'HEAD^{tree}' 'HEAD^^{tree}'  # identical
git merge-base --is-ancestor "$FORK_COMMIT" "$BASE"
```

The `HEAD^` and fork SHAs and both tree SHAs must match. The full commit message must equal
`LINEAGE_MESSAGE`, and `git status --porcelain` must remain empty. If any check fails,
**STOP**; do not bootstrap or publish the branch.

### 5. Bootstrap
Ensure `FOF_MONO_LOCAL_FILES_ROOT` is set, then:

```bash
# Default — shared venv (symlink to main fof-mono/.venv):
./scripts/worktree_bootstrap.sh "$PATH"

# Siloed — full monorepo requirements (only if preview/user chose local venv):
./scripts/worktree_bootstrap.sh "$PATH" --local-venv

# Siloed — app-specific requirements (local-app class from the scan):
REQ="$MAIN/apps/<app>/requirements.txt" ./scripts/worktree_bootstrap.sh "$PATH" --local-venv
```

Bootstrap symlinks `.env` and (by default) `.venv` → main, mounts local files, merges
`.vscode/settings.json` from main (interpreter path + auto-activate + allow automatic
tasks), copies `.vscode/tasks.json` from main (folderOpen terminal with `.venv`),
installs hooks if missing, and publishes/sets upstream. Main must already have a
working `.venv`; create it there first if missing.
See [Virtual environment](#virtual-environment).

### 6. Title-bar color
Apply the Cursor title-bar colors to `.vscode/settings.json` (`titleBar.activeBackground`,
`titleBar.inactiveBackground`, and foreground lines). **First** check
`apps/holodeck/worktree-colors.yaml` — if the worktree folder slug (e.g.
`feature-holodeck-start`) matches a rule, use that stable color so Holodeck cards and Cursor
windows stay consistent across new branches. **Otherwise** use the deterministic per-branch hash
(distinct from main green `#068102`). Leave **uncommitted** (same as Worktree Manager):

```bash
.venv/bin/python3 skills/repo-ops/create-worktree/scripts/worktree_identity.py apply-color "$PATH/.vscode/settings.json" "$B" --parent "$(git rev-parse --show-toplevel)"
```

If `.vscode/settings.json` is missing, copy from main first, then apply-color.

### 7. Open Cursor window
Run from the initiating window; the new window opens ready to go (bootstrap already ran above).

```bash
cursor "$PATH"
```

**Terminal + venv on open.** Opening the folder runs the workspace task
**Open terminal with .venv** (`.vscode/tasks.json`, `runOn: folderOpen`): reveals the
bottom terminal, `source`s `.venv/bin/activate`, and leaves an interactive bash with
the venv active (`(.venv)` in the prompt). Bootstrap copies that `tasks.json` from
main and merges settings that set `task.allowAutomaticTasks: on` and
`python.terminal.activateEnvironment: true` (so later terminals also activate). If the
terminal does not appear, check workspace trust and
**Tasks: Manage Automatic Tasks** → Allow.

### 8. Verify and report
Show command output for each check — do not claim success without proof.

```bash
git -C "$PATH" branch --show-current          # must equal B
git -C "$PATH" status -sb                     # tracks origin/B; no ahead/behind (or newly published)
git -C "$PATH" branch -vv                     # [origin/B]
git -C "$PATH" log -1 --format='%s%n%b'       # new branch: exact v2 lineage record
git -C "$PATH" rev-list --count "$FORK_COMMIT..HEAD"  # new branch: exactly 1
git -C "$PATH" diff-tree --no-commit-id --name-only -r HEAD  # new branch: empty
git merge-base --is-ancestor origin/main "$B" && git merge-base origin/main "$B"
test -L "$PATH/.env"                          # .env symlink
# shared venv (default): .venv is a symlink to main; siloed: real directory
if [[ -L "$PATH/.venv" ]]; then readlink "$PATH/.venv"; else test -x "$PATH/.venv/bin/python"; fi
"$PATH/.venv/bin/python" --version            # resolves via symlink or local venv
"$PATH/.venv/bin/python3" "$MAIN/scripts/python/install_worktree_import_guard.py" --venv-python "$PATH/.venv/bin/python3" --check
"$PATH/.venv/bin/python3" "$MAIN/scripts/python/diagnose_worktree_imports.py"
.venv/bin/python3 skills/repo-ops/create-worktree/scripts/worktree_identity.py color "$B"  # != #068102
```

Report slug, path, title-bar hex, venv mode (shared vs local), and upstream status in the session summary.


## Troubleshooting

| Problem | Fix |
|---------|-----|
| Diverged local vs remote (`ahead` / `behind` on wrong base) | Do **not** auto-reset. Show both `git log` directions; ask before `git branch -f B origin/B`. |
| `fatal: '<path>' already exists` | Pick a different path or remove the old folder after confirming it is safe. |
| `already checked out` | Switch the other worktree to `main`, or use the worktree that already has `B`. |
| Bootstrap mount / `_LOCAL_FILES` errors | Set `FOF_MONO_LOCAL_FILES_ROOT` per clone-bootstrap; re-run bootstrap. |
| Bottom-left **Publish branch** after bootstrap | Re-run `./scripts/worktree_bootstrap.sh "$PATH"` or `git push -u origin "$B"`. |
| `.vscode/settings.json` stripped to title-bar only | Re-run bootstrap; it merges full settings from main and keeps worktree colors. |
| Invalid Python interpreter warning | Cosmetic with shared venv (real path is sibling `fof-mono/.venv`) — dismiss, or re-bootstrap with `--local-venv`. |
| Main has no `.venv` | Create/install the venv in the main `fof-mono` checkout first, then re-run bootstrap. |
| Need isolated packages mid-work | Remove the worktree `.venv` symlink, then `./scripts/worktree_bootstrap.sh <path> --local-venv`. |
| New window has no bottom terminal / no `(.venv)` prompt | Confirm bootstrap copied `.vscode/tasks.json` and settings include `task.allowAutomaticTasks: on`. Allow automatic tasks if prompted; ensure the folder is trusted. Re-open the window or run **Tasks: Run Task** → **Open terminal with .venv**. |

For removal after PR merge, see `docs/worktrees-guide.md` → "Remove a worktree after PR merge".


## Related docs
- `docs/worktrees-guide.md` — what worktrees are, bootstrap details, local files, removal (creation content retired; points here).
- `skills/repo-ops/branch-lineage-record/README.md` — authoritative v2 lineage schema and validation.
- `skills/repo-ops/clone-bootstrap/README.md` — first-clone setup including `FOF_MONO_LOCAL_FILES_ROOT`.
- `scripts/worktree_bootstrap.sh` — called by this skill after `git worktree add`.
