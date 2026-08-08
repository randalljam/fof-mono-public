file: skills/repo-ops/hermes-branch-testing/README.md
title: Hermes branch testing — test skills from a feature branch before merging
source-github-url: original
source-guide-url: original
history:
  - 2026-06-12 · Randy · Claude Code [schedule-coordinator](https://claude.ai/code/session_01FRAdJZvkLq89hmPU6D2z6x) — initial procedure

**Test a skill from a feature branch on the live Hermes agent, then switch back to main.**

Hermes syncs its skills from a read-only sparse clone of this repo at `/opt/data/repo`
on the Fly container, normally tracking `main`. When developing a new skill on a feature
branch, use this procedure to point that clone at the branch, test via Telegram, and
restore `main` when done.

**This procedure runs from your laptop** (Mac with `flyctl` authenticated), not from
Telegram. Branch testing happens during active development — you're already at your
computer pushing code, so the laptop drives the switch. Telegram-driven branch switching
exists (`sync_skills.sh --branch`, see the sync-skills Hermes skill) but laptop-driven
is the standard workflow.


## When to use
- A new or changed skill is on a feature branch, pushed to GitHub, and you want to test
  it on the live Hermes agent before creating/merging the PR.
- After the test, to switch the container clone back to `main`.


## Prerequisites
- The feature branch is pushed to GitHub (`git push -u origin <branch>` from your dev
  environment).
- `flyctl` installed and authenticated on your Mac.
- Know your app name (default `[FLY-APP-NAME]`).


## Step 1 — Switch the container clone to the feature branch
From your Mac terminal:
```bash
fly ssh console -a [FLY-APP-NAME]
```
Inside the container:
```bash
su - hermes
cd /opt/data/repo
git fetch origin feature/schedule-coordinator
git checkout feature/schedule-coordinator 2>/dev/null || git checkout -b feature/schedule-coordinator FETCH_HEAD
git pull --ff-only origin feature/schedule-coordinator
git branch --show-current
```
Replace `feature/schedule-coordinator` with your branch. Expected: the last command
prints the branch name.

**Why the `|| git checkout -b ... FETCH_HEAD` fallback:** the container clone is sparse
and shallow; a plain `git checkout <branch>` fails with `pathspec ... did not match` the
first time because fetch updates `FETCH_HEAD` without creating a local branch. The
fallback creates it. (Documented in
`agents/hermes/2026-06-06_skills-dev-deploy-workflow.md` § Step 2b.)

Optionally verify the new/changed skill files are on disk before exiting:
```bash
ls agents/hermes/skills/<category>/<skill-name>/
exit   # leave su - hermes
exit   # leave fly ssh
```


## Step 2 — Restart the gateway
From your Mac (image `v2026.6.5` has no hot-reload):
```bash
fly apps restart [FLY-APP-NAME]
```
Or restart just the machine: `fly machine restart <machine-id> -a [FLY-APP-NAME]`
(machine id in `agents/hermes/RUNBOOK.md`).

Then send `/new` in Telegram to start a fresh session so skill discovery is current.


## Step 3 — Verify the skill loaded
In Telegram, ask Hermes something that should match the new skill's description (or ask
it to list its skills). If it doesn't recognize the skill:
- Re-check the branch on the container (`git branch --show-current` via Step 1's SSH).
- Confirm the SKILL.md exists under `/opt/data/repo/agents/hermes/skills/...`.
- Restart again and `/new`.


## Step 4 — Run the skill's test
Follow the skill's own test procedure (e.g.
`skills/family/schedule-coordinator/eval/manual-test-procedure.md`). Design tests to
leave the agent's data in the same state they found it (add → verify → remove).


## Step 5 — Switch back to main
From your Mac:
```bash
fly ssh console -a [FLY-APP-NAME]
```
Inside:
```bash
su - hermes
cd /opt/data/repo
git checkout main
git pull --ff-only origin main
git branch --show-current   # expect: main
exit
exit
```
Then restart (Step 2) and `/new`. The under-test skill disappears from Hermes until the
PR merges — expected.


## Step 6 — Merge, then final confirmation on main
1. Create and merge the PR for the feature branch.
2. In Telegram: **"sync your skills"** (the normal sync-skills flow pulls `main`).
3. Restart if the sync output says to.
4. Re-run a quick smoke test of the skill (one add/verify/remove cycle or equivalent).


## Notes and gotchas
- **The container clone is read-only.** Never commit or push from `/opt/data/repo`. All
  authoring happens in the repo via a coding agent; the container only pulls.
- **Sparse checkout**: the clone contains only `skills/` and `agents/hermes/skills/`.
  Changes outside those paths won't appear on the container — that's fine; skills should
  only depend on files inside them.
- **Agent data is branch-independent.** Skill runtime data lives on the Fly volume
  (e.g. `$HERMES_HOME/schedule/`, lesson logs), not in the repo clone. Switching branches
  never touches it.
- **Stale feature branches on the container**: after the PR merges and the remote branch
  is deleted, the local feature branch ref remains in the container clone. Harmless;
  optionally clean up while SSH'd in: `git branch -D <branch>` (safe here because the
  clone is a read-only consumer — this is the one place `-D` is fine).
- **If `git pull --ff-only` fails** (diverged history, e.g. after a force-push upstream):
  `git fetch origin <branch> && git reset --hard origin/<branch>`. Safe on this clone
  because it never holds local work.
