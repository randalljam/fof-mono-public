file: skills/repo-ops/mission-closeout/README.md
title: Mission closeout — verify, package, and compound before ending a session
source-github-url: original
source-guide-url: original
history:
  - 2026-07-28 · Randy · Cursor [deprecate branch-map](880da643-cbda-496b-8b24-5a5667d9c9d7) — drop branch-map ledger step; parent default is origin/main
  - 2026-07-06 · Randy · Claude Code [repo-analysis-oss-discovery](session_01NAjDu2KyLuHTPDnTnWmqha) — initial skill: read-only closeout fact gatherer + approval-packet skeleton + compound-lesson step


**Use this skill at the end of a session — before you say "done" — to verify your claims against real tool output, package a phone-friendly approval packet for the user, and compound what you learned.** It turns the ad-hoc end of a session into a consistent ritual: any agent (Cursor, Claude Code, Codex) closes out the same way, so the user always gets the same decision-ready summary.

**READ-ONLY.** The helper script gathers facts and prints a packet skeleton; it does not commit, push, run tests, or switch branches. You run the tests and fill the packet from real output.


## When to use
- You have finished (or reached a natural checkpoint on) a piece of work and are about to hand it back.
- Before reporting completion, opening a PR, or ending a cloud/autonomous run.
- Any time you want a clean, reviewable summary the user can act on without reading the diff.


## Why it exists
`AGENTS.md` mandates verification ("never say done when a step failed", "claims must include proof output") and pre-PR testing, and the Fable operating contract defines an approval-packet format — but those live in prose that each session re-derives. This skill makes the closeout mechanical and adds the **compound step**: every session ends by writing durable lessons back, so the context that makes future work easier actually accumulates instead of evaporating.


## The closeout procedure
### 1. Gather the facts (read-only)
```bash
.venv/bin/python3 skills/repo-ops/mission-closeout/scripts/closeout_summary.py
```
Prints: branch & push state, commits since the base, diffstat, uncommitted changes (flagged), files-changed by area, an **approval-packet skeleton**, and a **closeout checklist**. Override the comparison base with `--parent <ref>` (default: `origin/main`).

### 2. Verify every claim against tool output
For each thing you are about to report as done or passing, point to a real result from this session — a test run, a command's output, a file you actually wrote. If something is unverified, say so. **If tests could not run in this harness** (e.g. a cloud VM that can't execute the suite), say that plainly and leave the exact run command for local follow-up — do not imply you ran them.

### 3. Run the tests (where testable)
Use `skills/repo-ops/run-app-tests` when it exists, or the app's `AGENTS.md` → `## Tests` command. Report pass/fail with output. Do not claim a suite passes unless you saw it pass.

### 4. Fill in the approval packet
Lead with the outcome; write for someone who did not watch you work. Keep it to:
- **What changed** — 2–4 plain bullets, no jargon or arrow-chains.
- **What I verified** — tests run and what passed (or "couldn't run here; run `<cmd>` locally").
- **Risk** — what could break, and what you deliberately did not touch.
- **The one decision** — merge? open a PR? approve a follow-up? nothing (pushed for review)?

### 5. Compound — write the lesson back
If the session produced a durable lesson (a correction, a confirmed approach, a gotcha, a reusable procedure), capture it so future sessions start smarter:
- A **rule** → the relevant `AGENTS.md` / per-app `AGENTS.md`.
- A **reusable procedure** → a new or existing skill under `skills/` (with the provenance/history header).
- A **regression** → a test.
- A **mission note** → a notes file in the work's plan folder.
Keep it to genuinely durable lessons — do not record what the repo or chat history already captures; update an existing note rather than duplicating.


## Guardrails
- Follow `AGENTS.md` → Commit and push defaults (push the current branch by default; never a `claude/<random>` auto-branch — run `skills/repo-ops/session-start-check` if unsure).
- Do not open a PR unless the user asked for one.
- Uncommitted changes are flagged by the script: commit them (scoped conventional message, one logical change per commit) or explain why they remain.


## Related
- `skills/repo-ops/session-start-check/README.md` — the start-of-session counterpart.
- `AGENTS.md` → Verification and error reporting, Pre-PR testing, Commit hygiene, Branch purpose and ancestry.
- `docs/2026-07-01_repo-snapshot-oss-discovery/fable5-operating-contract.md` — the approval-packet format this skill generalizes.
