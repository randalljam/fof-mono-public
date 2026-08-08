file: skills/openspec/opsx-apply/README.md
title: OPSX apply — implement tasks from a change
source-github-url: https://github.com/Fission-AI/OpenSpec
source-guide-url: https://github.com/Fission-AI/OpenSpec/blob/main/docs/commands.md#opsxapply
history:
  - 2026-07-09 · Randy · Cursor [OpenSpec skills implementation](openspec-skills) — initial skill


**Use this skill to implement an OpenSpec change by working through `tasks.md`.** Apply reads the change's artifacts (proposal, delta specs, design, tasks), writes code, runs tests, and checks off completed items. It is resumable — interrupted sessions pick up from the next unchecked task.

Upstream equivalent: `/opsx:apply [change-name]`.


## When to use
- A change folder exists with a complete `tasks.md` and apply-required artifacts.
- The user wants implementation to follow the agreed spec and design.
- You are continuing a partially implemented change (some tasks already `[x]`).

## When to skip
- Planning artifacts are missing or incomplete — use `opsx-propose` first.
- The user only wants to revise the plan, not code — use `opsx-update` (expanded profile) or edit artifacts manually with user approval.


## Prerequisites
- Change at `apps/<app>/openspec/changes/<change-name>/`.
- Read `proposal.md`, `design.md`, and relevant delta specs before coding.
- Per-app rules: `apps/<app>/AGENTS.md` (tests, conventions, guardrails).


## The apply procedure
### 1. Load context
```bash
cd apps/<app> && openspec status --change <change-name>
```
Read in order:
1. `proposal.md` — intent and non-goals
2. Delta `specs/` — what behavior must exist when done
3. `design.md` — how to implement
4. `tasks.md` — checklist (note already-completed `[x]` items)

### 2. Work tasks sequentially
For each unchecked task in `tasks.md`:
- Implement the change (code, config, tests as the task describes).
- Follow repo conventions:
  - Python: `.venv/bin/python3`, no type hints, section headers `### Name`, no blank lines between functions.
  - Respect per-app `AGENTS.md` and branch guardrails.
  - One logical change per commit when possible (scoped conventional messages).
- Mark the task complete: `- [x]` in `tasks.md`.
- Run relevant tests after substantive tasks (not after every typo).

### 3. Verify before handoff
Run the app's test suite. For autolearner:
```bash
.venv/bin/python3 -m pytest tests/test_autolearner.py -v
# or per apps/autolearner/AGENTS.md:
.venv/bin/python3 -m unittest tests.test_autolearner -v
```
Validate OpenSpec artifacts:
```bash
cd apps/<app> && openspec validate --change <change-name> --strict
```
Report: tasks completed, tests run (with output), any tasks deliberately deferred.

### 4. Hand off
When all tasks are `[x]` and tests pass, transition to [`skills/openspec/opsx-archive/README.md`](../opsx-archive/README.md). If implementation diverged from design, update artifacts with user approval before archiving.


## Guardrails
- Do not edit `openspec/specs/` directly during apply — deltas merge on archive.
- Do not skip reading artifacts; the spec is what the user reviews, not just the diff.
- If a task is blocked (needs schema change on another branch, missing dependency), stop and report — do not improvise scope.
- Pre-PR testing is mandatory per `AGENTS.md` before opening a pull request.


## Related
- [`skills/openspec/opsx-propose/README.md`](../opsx-propose/README.md) — creates the change this skill implements.
- [`skills/openspec/opsx-archive/README.md`](../opsx-archive/README.md) — next step when apply is complete.
- [`skills/repo-ops/mission-closeout/README.md`](../../repo-ops/mission-closeout/README.md) — session closeout ritual.
- Upstream: [commands — apply](https://github.com/Fission-AI/OpenSpec/blob/main/docs/commands.md#opsxapply).
