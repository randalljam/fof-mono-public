file: skills/repo-ops/session-start-check/README.md
title: Session-start branch-discipline check
source-github-url: original
source-guide-url: original
history:
  - 2026-07-28 · Randy · Cursor [deprecate branch-map](880da643-cbda-496b-8b24-5a5667d9c9d7) — drop branch-map ledger checks; ancestry/purpose from git + first-commit convention
  - 2026-07-06 · Randy · Claude Code [repo-analysis-oss-discovery](session_01NAjDu2KyLuHTPDnTnWmqha) — initial skill: read-only session-start check that surfaces the working branch, ancestry, and a verdict per AGENTS.md branch discipline


**Use this skill at the start of a session — before the first commit — to confirm you are on the intended working branch, per `AGENTS.md` → Branch discipline.** It is the executable form of the "mechanical session-start check" that document mandates. It fetches remote-tracking refs (non-destructive) and prints a report plus a verdict.

**READ-ONLY.** This skill never switches branches, resets, commits, or pushes. Switching or creating a branch requires explicit user approval (`AGENTS.md` → "Never create or switch branches without explicit user approval"). This skill only *tells you where you stand*; you and the user decide what to do.


## When to use
- The very start of any session that will make commits — **especially cloud sessions**, which begin on a `claude/<random>` auto-branch that is a harness scratch default, not the working branch.
- Before the first commit, whenever you are unsure which branch you should be on.
- After resuming a carried-over branch, to check it is not behind/diverged unexpectedly.

This addresses what `AGENTS.md` calls "the single most-repeated mistake in cloud sessions": committing or pushing to the `claude/<random>` auto-branch instead of the user's real branch.


## What it checks
- **Current branch**, and whether it is a `claude/` auto-branch.
- **Remote branches** on `origin` (so you can see the descriptively-named branches that exist).
- **Ancestry vs `origin/main`** — the shared fork-base, how far ahead the branch is, and how far behind `main` it is (normal "behind main" is reported plainly; a missing common ancestor is flagged as DISCONNECTED to investigate).
- **Candidate real working branches** — when on a `claude/` auto-branch, the descriptively-named branches at or just below `HEAD` (the harness usually forks the auto-branch off the tip of the user's real branch, so the real branch sits at or near `HEAD`).
- **VERDICT** — a plain-language recommendation: proceed, or STOP and confirm/switch/ask.


## Run
From any checkout of the repo:
```bash
.venv/bin/python3 skills/repo-ops/session-start-check/scripts/session_start_check.py
```

Options:
```bash
... --no-fetch          # skip git fetch (offline, or already fetched this session)
... --max-distance 25   # how many commits below HEAD to search for the real branch (default 25)
```


## Interpreting the verdict
- **On a convention branch (`feature/…`, `fix/…`, …):** confirm it is the branch the user intends, then proceed. The check is a confirmation, not a guarantee — only the user knows their intent.
- **On `main`:** do **not** commit. Create/switch to a feature branch — ask the user first.
- **On a `claude/` auto-branch:**
  - If there is **one** descriptive candidate → that is very likely the user's real branch. **Confirm with the user, then switch to it before the first commit** (`git checkout <branch>`). Do not push the auto-branch.
  - If there are **multiple** or **zero** candidates → **ask the user** which branch to use. Do not guess, and do not default to the auto-branch.
  - **Exception:** if the user (or the task) has *explicitly designated this specific `claude/…` branch* as the working branch, it is legitimate to work on it — the verdict still flags it so a human can confirm that designation. When in doubt, ask.

Never resolve a STOP by force-pushing, rebasing, or `git branch -D`. If anything looks wrong (e.g. DISCONNECTED ancestry), report it and stop — see `AGENTS.md` → Branch discipline / Git safety rules.


## After the check
- To move a stray commit off an auto-branch onto the real branch, see `AGENTS.md` → "If you already committed on the auto-branch by mistake" (clean fast-forward; the user deletes the stray remote branch — cloud agents usually can't).
- To create or check out a branch in a new window, use `skills/repo-ops/create-worktree/README.md`.
- Put branch purpose in the first commit (`AGENTS.md` → Branch purpose and ancestry). Do not maintain a markdown ancestry ledger.


## Related
- `AGENTS.md` → Branch discipline (the rules this skill operationalizes).
- `skills/repo-ops/create-worktree/README.md` — creating/checking out a branch (needs user confirmation).
- `skills/repo-ops/mission-closeout/README.md` — the end-of-session counterpart.
