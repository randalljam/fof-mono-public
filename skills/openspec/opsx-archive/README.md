file: skills/openspec/opsx-archive/README.md
title: OPSX archive — finalize a change and merge specs
source-github-url: https://github.com/Fission-AI/OpenSpec
source-guide-url: https://github.com/Fission-AI/OpenSpec/blob/main/docs/commands.md#opsxarchive
history:
  - 2026-07-09 · Randy · Cursor [OpenSpec skills implementation](openspec-skills) — initial skill


**Use this skill when a change is implemented and ready to finalize.** Archive syncs delta specs into the living spec store, moves the change folder to a dated archive, and preserves the full audit trail.

Upstream equivalent: `/opsx:archive [change-name]`.


## When to use
- All (or intentionally accepted subset of) tasks in `tasks.md` are complete.
- Tests pass and the user is ready to treat the change as done.
- You want the app's `openspec/specs/` updated to reflect new current behavior.

## When to skip
- Implementation is incomplete and the user wants to continue — resume `opsx-apply`.
- Artifacts and code diverged significantly — reconcile with `opsx-update` or manual artifact edits first.


## Prerequisites
- Change at `apps/<app>/openspec/changes/<change-name>/`.
- `opsx-apply` completed (or user explicitly accepts partial completion).
- Tests verified in the current session.


## The archive procedure
### 1. Pre-archive checks
```bash
cd apps/<app> && openspec status --change <change-name>
```
Confirm:
- Artifact completion (proposal, specs, design, tasks present).
- Task completion — report any unchecked items; archive warns but does not hard-block.
- Optional: run `/opsx:verify` logic (expanded profile) or manually confirm implementation matches delta specs.

Run tests one final time and cite output.

### 2. Sync delta specs
Archive merges ADDED/MODIFIED/REMOVED sections from the change's delta specs into `apps/<app>/openspec/specs/`. Prefer the CLI:
```bash
cd apps/<app> && openspec archive <change-name>
```
The CLI will offer to sync deltas if not already synced. You can also sync manually first (`/opsx:sync` or `openspec` sync commands) when you want to review the merge separately.

### 3. Confirm archive location
After archive, the change lives at:
```text
apps/<app>/openspec/changes/archive/YYYY-MM-DD-<change-name>/
```
All artifacts are preserved for audit. Active changes list should no longer include this change:
```bash
openspec list
```

### 4. Commit and close out
Commit the archived state and updated specs with a scoped message, e.g.:
```text
chore(<app>): archive OpenSpec change <change-name>
```
Then run [`skills/repo-ops/mission-closeout/README.md`](../../repo-ops/mission-closeout/README.md) for the session-level approval packet: what changed, what was verified, risks, and the one decision (merge? PR?).


## Guardrails
- Do not archive without user awareness of any incomplete tasks or validation warnings.
- Archive updates `openspec/specs/` — that is the new source of truth for app behavior; ensure deltas are correct.
- Opt-in only: archiving applies to opted-in apps under `apps/<app>/openspec/`.


## Related
- [`skills/openspec/opsx-apply/README.md`](../opsx-apply/README.md) — prior step (implementation).
- [`skills/openspec/README.md`](../README.md) — lifecycle, spec store layout.
- [`skills/repo-ops/mission-closeout/README.md`](../../repo-ops/mission-closeout/README.md) — verify, package, compound at session end.
- Upstream: [commands — archive](https://github.com/Fission-AI/OpenSpec/blob/main/docs/commands.md#opsxarchive).
