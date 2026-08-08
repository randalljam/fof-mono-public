file: skills/repo-ops/agents-md-repo-sync/README.md
title: Sync root AGENTS.md across main and active branch tips
source-github-url: original
source-guide-url: original
history:
  - 2026-07-28 · Randy · Cursor — include top-level remote branch names in default inventory and verification
  - 2026-07-28 · Randy · Cursor [agents-md-repo-sync skill](a0507ee5-461f-4062-a268-84ca67ba3074) — move run log into skill folder (git-tracked); add non-root AGENTS.md inventory section to report
  - 2026-07-28 · Randy · Cursor [agents-md-repo-sync skill](a0507ee5-461f-4062-a268-84ca67ba3074) — note worktree-locked tips and untracked dirty-tree blockers; first live fan-out run logged
  - 2026-07-28 · Randy · Cursor [agents-md-repo-sync skill](a0507ee5-461f-4062-a268-84ca67ba3074) — add verification gate, categorized agent report, prepended run log; demote commits scoped+root AGENTS.md together and push
  - 2026-07-28 · Randy · Cursor [agents-md-repo-sync skill](a0507ee5-461f-4062-a268-84ca67ba3074) — initial skill: consolidate branch-tip AGENTS.md into main, fan out to branches, demote contested/local rules to scoped AGENTS.md

**Use this when root `AGENTS.md` has drifted across `main` and active feature-branch tips, and you want one canonical repo-wide file everywhere — without silently forcing branch-specific agent rules into the shared doc.**


## What this does
This skill is a **two-phase sync** that combines:
- **Promote-to-main** thinking — branch tips that improved root `AGENTS.md` contribute those repo-wide edits into `main`.
- **Merge-main-to-branches** thinking — once `main` has the canonical file, fan that file out to every confirmed target branch tip.

**Success condition (mandatory):** after the run, every confirmed branch tip has the **same byte-for-byte root `AGENTS.md`** as `origin/main`. That equality is checked by an explicit verification step; the run is not complete until verification passes (or every failure is listed as skipped with a human owner).

Scoped demotions are the exception for *content that must not live in root*: that text moves into a nested `AGENTS.md`, and the **root** file on that tip still matches `origin/main`.

It never rebases or force-pushes as part of the fan-out.


## When to use
- Root `AGENTS.md` differs across several active branches and the user wants them aligned.
- A branch added durable repo-wide agent rules that should land on `main` and then everywhere else.
- `main` advanced `AGENTS.md` and feature branches are stale on that file only.
- The user says "sync AGENTS.md across branches", "agents-md-repo-sync", or "make every branch tip share the same AGENTS.md".

Do **not** use this to rewrite history or to merge whole branches. For general main fan-out of many files, use `skills/repo-ops/merge-main-to-branches/README.md`. For lifting arbitrary separable commits off a feature branch, use `skills/repo-ops/promote-to-main/README.md`.


## Terms
- **Root `AGENTS.md`** — repo-root agent instructions (`AGENTS.md`). This is the only file this skill treats as the repo-wide sync target.
- **Scoped `AGENTS.md`** — a nested agent file such as `apps/<app>/AGENTS.md` or `apps/<umbrella>/<sub>/AGENTS.md`. Already used in this monorepo (math-quiz, minecraft mods, content studio, etc.). Scoped files hold **app- or folder-specific** rules that must not fight in the root doc.
- **Canonical root** — the single root `AGENTS.md` content that will live on `main` after Phase A.
- **Promote phase (A)** — collect repo-wide-worthy branch tip deltas into `main`.
- **Fan-out phase (B)** — put that canonical root file onto every confirmed target branch tip.
- **Demote** — move contested or branch-local root `AGENTS.md` content into a scoped `AGENTS.md` instead of merging it into the root. Demotion is committed **and pushed** on that branch tip together with the root sync.


## Safety rules
- Get explicit user approval for the target branch list (and exclusions) before changing branches or pushing — unless the user already said to run the sync on the default active set.
- Confirm the Phase A plan (what goes into root vs what is demoted where) before committing when Phase A is non-empty.
- Keep a clean working tree before Phase A commits and before each Phase B branch update.
- Use `git fetch origin --prune` before inventory and before ancestry checks.
- Never rebase, amend published commits, or force-push in the fan-out phase.
- Push only the branch currently being updated; verify push output.
- Do not invent a substitute branch if a named target is missing — ask.
- Do not auto-resolve conflicting root `AGENTS.md` edits by picking a winner silently — demote or ask.
- **Do not declare success without verification** (see [Verification](#verification)).


## Helper scripts
Inventory (read-only):
```bash
.venv/bin/python3 skills/repo-ops/agents-md-repo-sync/scripts/agents_md_inventory.py
.venv/bin/python3 skills/repo-ops/agents-md-repo-sync/scripts/agents_md_inventory.py --no-fetch
.venv/bin/python3 skills/repo-ops/agents-md-repo-sync/scripts/agents_md_inventory.py --branches feature/foo,feature/bar
```

Verify + run log:
```bash
.venv/bin/python3 skills/repo-ops/agents-md-repo-sync/scripts/agents_md_report.py verify
.venv/bin/python3 skills/repo-ops/agents-md-repo-sync/scripts/agents_md_report.py verify --branches feature/foo,feature/bar
.venv/bin/python3 skills/repo-ops/agents-md-repo-sync/scripts/agents_md_report.py write-log --report-file /tmp/agents-md-repo-sync-report.md
```

`write-log` prepends the report entry to `skills/repo-ops/agents-md-repo-sync/run-log.md` (newest first). That file is **git-tracked** with the skill so collaborators see prior runs.


## Preflight
```bash
git fetch origin --prune
git status --short --branch
git branch --show-current
git branch -r
git log --oneline --decorate -20
git config core.hooksPath
git config user.name
git config user.email
whoami
```
Confirm:
- Working tree clean before any write phase (or only intentional skill edits already committed).
- Hooks installed (`scripts/git/hooks`); if not, `./scripts/git/install-hooks.sh`.
- Target branch list confirmed (or user already authorized the default active set).
- Record runner identity for the report.


## Build the target list
Default candidates: every remote branch tip on `origin`, including top-level legacy names such as `stellar-transcriber-start`.

```bash
git branch -r --format='%(refname:short)' | sort
```

Do not include:
- `origin/main`, `origin/HEAD`
- harness scratch `claude/<random>` branches unless the user explicitly names one
- archived, merged, or deleted branches
- branches the user excludes

Verify each after prune:
```bash
git rev-parse --verify --quiet origin/<branch>
```


## Inventory and classify (required)
Run the inventory helper, then for every `branch-only` or `diverged` tip, read the actual diff:

```bash
BASE=$(git merge-base origin/main origin/<branch>)
git log --oneline "$BASE"..origin/<branch> -- AGENTS.md
git diff "$BASE"..origin/<branch> -- AGENTS.md
git diff origin/main origin/<branch> -- AGENTS.md
```

Classify each delta into exactly one bucket:

| Bucket | Meaning | Action |
|--------|---------|--------|
| **Repo-wide promote** | Improvement or addition that belongs in the shared agent contract for the whole monorepo | Fold into canonical root `AGENTS.md` on `main` |
| **Main already has it / fan-out only** | Branch tip matches main, or branch never edited root `AGENTS.md` since fork and only needs main's file | No promote; fan-out in Phase B if needed |
| **Demote to scoped** | App-/folder-specific rules, temporary branch notes, or content that conflicts with another branch's root edit | Move into a scoped `AGENTS.md`; keep root free of the contested text |
| **Ask human** | Two branches both changed the same root section incompatibly, and scope is unclear | Stop that section; present both diffs and wait |

### Demote rules (important case)
Demote when **any** of these is true:
1. The change is clearly about one app, umbrella, or folder (paths, run commands, tests, deploy notes for that area).
2. Two (or more) branches edited the **same root section** in incompatible ways.
3. The user says a branch's root edit must **not** become repo-wide.

Where to put demoted content:
- Prefer an existing scoped file if one already owns that area (`apps/math-quiz/AGENTS.md`, `apps/minecraft/mods/AGENTS.md`, etc.).
- Otherwise create `apps/<app>/AGENTS.md` (or the nearest owning folder's `AGENTS.md`) with the standard `file:` / `title:` header block used elsewhere.
- Add a short pointer in root `AGENTS.md` only when a new scoped file is a durable pattern the whole repo should know about — do not dump the demoted body into root.

**Commit + push together on that tip:** when demoting on a branch, one commit must include both:
1. root `AGENTS.md` set to the canonical `origin/main` content, and
2. the new or updated scoped `AGENTS.md`.

Then `git push origin <branch>`. Document the demotion carefully in the run report (path created vs updated, topic moved, commit SHA, push confirmed). Never leave a demotion only in the working tree.


## Phase A — build canonical root on main
Only when inventory found **repo-wide promote** content. If every tip is `match` or `main-only`, skip Phase A and go to Phase B.

When Phase A is needed:
1. Start from `origin/main` on a short-lived branch (or user-approved direct-to-main for a tiny edit).
2. Apply promote hunks into root `AGENTS.md`.
3. Apply demotions that belong on `main` (durable scoped files).
4. Confirm the plan with the user, then land on `main` (PR merge or approved direct push).
5. `git fetch origin --prune` and confirm `origin/main` has the canonical file before Phase B.

Do **not** fan out an unmerged draft and call the sync complete.


## Phase B — fan out canonical root to branch tips
Only after `origin/main` has the canonical root file.

Default for this skill: **AGENTS.md-only** fan-out (keeps feature work untouched). Use full merge/cherry-pick from `skills/repo-ops/merge-main-to-branches/README.md` only when the user asks for a broader update.

For each confirmed target branch:
```bash
git fetch origin --prune
git checkout <branch>
# or: git checkout -B <branch> origin/<branch>
git status --porcelain   # must be empty
git pull --ff-only

# If tip already matches origin/main on AGENTS.md: record "already matched" and continue.

git checkout origin/main -- AGENTS.md
# If demoting on this tip: write/update the scoped AGENTS.md now, then:
git add AGENTS.md [<scoped/path/AGENTS.md> ...]
git commit -m "$(cat <<'EOF'
docs: sync root AGENTS.md from main

EOF
)"
# Demotion commit message should mention the scoped path, e.g.
# docs: sync root AGENTS.md; demote <topic> to apps/<app>/AGENTS.md
git push origin <branch>
```

After each push:
```bash
git diff origin/main origin/<branch> -- AGENTS.md   # must be empty
```

Return the checkout to the session's working branch when finished.

### Worktrees and dirty trees
- Run `git worktree list` during preflight. If a target branch is already checked out in another worktree, perform that tip's commit/push **inside that worktree** (do not try to check it out in the primary tree).
- A clean tree means `git status --porcelain` is empty. Unrelated **untracked** files in the primary worktree will block every checkout in that tree — move them aside temporarily (and restore after), or skip and report. Do not commit unrelated untracked files as part of this skill.


## Verification
**Required before writing the run log and before telling the user the sync succeeded.**

```bash
git fetch origin --prune
.venv/bin/python3 skills/repo-ops/agents-md-repo-sync/scripts/agents_md_report.py verify \
  --branches <comma-separated confirmed targets>
```

- Exit code `0` and `Verification: PASS` → every confirmed tip matches `origin/main` on root `AGENTS.md`.
- Exit code `1` / `FAIL` → do **not** claim success. List mismatches in the report under Skipped / still diverged and stop or fix.

Verification is about the **root** file equality. Scoped demotion files are additional paths; they do not excuse a root mismatch.


## Run report (agent response + log file)
Do **not** treat a terminal dump as the deliverable. This skill is agent-run: put the report in the **agent response** and prepend the same entry to the run log.

### Log file
- Path: `skills/repo-ops/agents-md-repo-sync/run-log.md` (git-tracked; newest entry first).
- Commit the updated run log on the skill/working branch after each run (same session as the sync when practical).
- Write via:
```bash
# write the report entry to a temp file (must start with ## YYYY-MM-DD_HHMM — agents-md-repo-sync)
.venv/bin/python3 skills/repo-ops/agents-md-repo-sync/scripts/agents_md_report.py write-log \
  --report-file /tmp/agents-md-repo-sync-report.md
```
When building the report, always include `non_root_agents_md` from:
```bash
.venv/bin/python3 -c "import sys; sys.path.insert(0,'skills/repo-ops/agents-md-repo-sync/scripts'); from agents_md_report import list_non_root_agents_md; print('\n'.join(list_non_root_agents_md()))"
```

### Report shape (condensed, complete, human-readable)
Group tips into buckets humans can scan. Prefer categories over a long identical per-branch essay.

```markdown
## YYYY-MM-DD_HHMM — agents-md-repo-sync

- Run by: <name> (<email>, login: <whoami>)
- Phase A: none (fan-out only) | <what landed on main>
- Canonical root SHA-256 (12): `<sha12>`

### Verification

- Canonical root SHA-256 (12): `<sha12>`
- Tips checked: N
- Tips matching `origin/main`: N
- **Verification: PASS** — every confirmed tip matches `origin/main` on root `AGENTS.md`

### Fan-out only — no branch `AGENTS.md` changes since fork

These tips had no root `AGENTS.md` edits for the life of the branch (relative to the fork from main). They only received the current `origin/main` file.

- `feature/a`: updated from main (`<sha>`)
- `feature/b`: already matched
- …

### Inventory — non-root `AGENTS.md` files

- `apps/<app>/AGENTS.md`
- …

### Promoted into root `AGENTS.md`

- `feature/x`: <short note of what was taken>

### Demoted to scoped `AGENTS.md` (committed + pushed on tip)

- `feature/y`: moved <topic> → `apps/<app>/AGENTS.md` (created|updated); root synced; commit `<sha>` (pushed)

### Other tip updates

- `feature/z`: <note if not covered above>

### Skipped

- `feature/w`: <reason>
```

Rules of thumb for grouping:
- **Fan-out only** — inventory class was `main-only` or tip already `match` with zero branch commits touching root `AGENTS.md` since fork. Even if the *main* edits they receive differ across calendar time, they are the same human bucket: "branch never changed root `AGENTS.md`; just took main."
- **Inventory — non-root** — always list every tracked non-root `AGENTS.md` at `origin/main` (paths only). This is informational; the sync target remains root `AGENTS.md`.
- **Demoted** — always call out individually; creating a new scoped `AGENTS.md` must be explicit (`created` vs `updated`).
- **Promoted** — list source branch and what entered root.
- Keep the report complete (every confirmed tip appears in exactly one bucket) but condensed.


## Conflict / overlap handling
- Prefer AGENTS.md-only fan-out so unrelated overlap does not block the sync.
- If a branch still has divergent root `AGENTS.md` after Phase A because demotion was skipped, **stop** — finish demotion first, then fan out.
- If `git merge` / `git cherry-pick` conflicts on `AGENTS.md` despite planning, abort, report, and do not hand-patch unless the user asks.


## Related
- `skills/repo-ops/merge-main-to-branches/README.md` — broader fan-out mechanics when the user wants more than `AGENTS.md`.
- `skills/repo-ops/promote-to-main/README.md` — extracting separable work onto a `main` PR.
- `AGENTS.md` → Directory guide / Repo layout — when a scoped per-app `AGENTS.md` is the right heavier pattern.
- `skills/repo-ops/session-start-check/README.md` — confirm working branch before Phase A/B commits.
