file: skills/repo-ops/local-files-audit/README.md
title: Local-files audit — WARN review before losing gitignored files
source-github-url: original
source-guide-url: original
history:
  - 2026-07-30 · Randy · Cursor [local-files-audit skill](a382ac41-327f-4a1d-acf2-960cc34a1971) — extract pre-removal / WARN audit from docs/worktrees-guide.md as sole source of truth


**Use this skill to audit local-only (gitignored) files — especially before retiring a worktree — so durable data is not deleted with the folder.** Setup of mounts and `FOF_MONO_LOCAL_FILES_ROOT` stays in `skills/repo-ops/clone-bootstrap/README.md`. This skill is the audit and disposition procedure.

The checker script is `scripts/local_files_check.py`. Mount list: `scripts/local_files_mounts.txt`. Canonical storage: `$FOF_MONO_LOCAL_FILES_ROOT` (usually `…/_LOCAL_FILES/fof-mono/`).


## When to use
- **Before removing a worktree** (primary): PR is ready to merge / retire the feature window; run this while the worktree folder still exists.
- User asks for a local-files audit, pre-removal check, or WARN review of ignored files outside mounts.
- After a long-lived branch accumulated local-only data and you need to classify keep vs discard.
- Optional: periodic check across all worktrees (not only pre-removal).

Do **not** use this for first-time clone mount setup — use clone-bootstrap.


## Why it matters
Configured mounts are symlinks into `_LOCAL_FILES`, so those paths survive worktree deletion. Gitignored files **outside** those mounts live only in that worktree folder. When the folder is removed, they are **lost permanently** unless moved into canonical local storage first.


## Tools and modes
Dry-run by default (no changes):
```bash
.venv/bin/python3 scripts/local_files_check.py --worktree <worktree-path> --ignored-limit 999
```

All worktrees (no `--worktree`):
```bash
.venv/bin/python3 scripts/local_files_check.py --ignored-limit 999
```

Safe mount repairs only (missing symlink, wrong target, empty real folder that can migrate) — **after user confirms**:
```bash
.venv/bin/python3 scripts/local_files_check.py --worktree <worktree-path> --apply --ignored-limit 999
```

`--apply` copies any real mount folder it replaces into `_LOCAL_FILES/fof-mono/_sync-backups/<timestamp>/` before linking. It does **not** automatically move arbitrary ignored files outside configured mounts; those are `WARN` rows for this skill’s review.


## Labels (source of truth for disposition)
For each `WARN: ignored` path (and for groups of related paths), assign one disposition:

| Label | Meaning | Typical action |
|-------|---------|----------------|
| **disposable** | Safe to lose (cache, test artifact, generated output, redeployable noise). | Leave in place; it will vanish with the worktree. Optionally add a pattern to `DISPOSABLE_PATTERNS` in `scripts/local_files_check.py` if it should stop warning. |
| **move to existing mount** | Worth keeping; belongs under a path already in `scripts/local_files_mounts.txt`. | After approval, `mv` into that mount (physical path under `_LOCAL_FILES`, visible via the worktree symlink). |
| **create new mount** | Worth keeping as a durable local root not yet listed. | After approval: add a line to `scripts/local_files_mounts.txt`, create the target under `_LOCAL_FILES`, run checker `--apply` for that mount, then move files. Rare; prefer an existing mount when possible. |

When presenting to the user, a compact mark next to each path is fine:

| Mark | Maps to |
|------|---------|
| ✓ | disposable |
| ✗ | move to existing mount **or** create new mount (state which in the action column) |
| ? | unclear — need user input before choosing a label |


## Agent workflow: single worktree pre-removal check
**Primary procedure.** Use before the PR is merged and before the user removes the branch/worktree. Human closeout steps (merge PR, sync main, close window, Remove Worktree, delete branch) stay in `docs/worktrees-guide.md`; this skill is Step 1 of that checklist.

**Agent must not remove the branch or worktree.** The user deletes those manually. The agent only checks mounts, evaluates WARN files, and (with approval) moves non-disposable files into canonical local storage.

### 1. Run mount check for this worktree only
Replace `<worktree-path>` with the folder being retired:
```bash
.venv/bin/python3 scripts/local_files_check.py --worktree <worktree-path> --ignored-limit 999
```

- If any mount is `BLOCK`: stop, summarize conflicts, wait for user guidance. Do not proceed until resolved.
- If mounts need safe `FIX`: explain, then run `--apply` **for this worktree only** after user confirms.

### 2. Evaluate every WARN under “ignored files outside mounts”
These are untracked gitignored paths **not** under a configured mount and **not** filtered as routine disposable noise by the script.

For **each** WARN path, inspect (size, contents, mtime, purpose) and assign disposable / move to existing mount / create new mount / unclear.

Present a table:

```text
| Path | Verdict | Disposition | Rationale / proposed action |
|------|---------|-------------|-----------------------------|
| apps/math-quiz/tests/test-results/.last-run.json | ✓ | disposable | Playwright metadata; regenerated on next run. |
| apps/foo/_scratch/keeper.sqlite | ✗ | move to existing mount | → apps/foo/_data/keeper.sqlite (already mounted) |
```

If the section shows `OK: ignored: no ignored files…`, say so and skip to step 4.

### 3. Stop and seek approval — do not delete anything yet
End the response with:

1. **Verdict summary** — counts by disposition (disposable / move to existing / create new / unclear).
2. **Recommended actions** for each non-disposable path (exact `mv` source/dest, or proposed new mount line).
3. **Explicit question:** “Approve these verdicts and actions?”

Do **not** run branch deletion, `git worktree remove`, or `rm -rf` on the worktree folder.

### 4. Actions after user approval
**All disposable (or no WARNs):** Report that the worktree is safe to remove from a local-files perspective. Remind the user to remove the worktree and branch themselves when ready.

**Move to existing mount:** Place under an existing symlinked root so other worktrees see it immediately:
```text
_LOCAL_FILES/fof-mono/
  data/                    # general durable local data
  apps/math-quiz/_data/    # math-quiz-specific durable local data
  …
```
Tell the user the exact `mv` source and destination; run moves only after they approve.

**Create new mount (rare):** Propose the exact new line for `scripts/local_files_mounts.txt`, the `_LOCAL_FILES` directory to create, then `--apply` for that worktree, then move files. Do not invent mounts without approval.

**After any moves:** Re-run the single-worktree check:
```bash
.venv/bin/python3 scripts/local_files_check.py --worktree <worktree-path> --ignored-limit 999
```

Success criteria for removal prep:
- All mounts `OK`, no `BLOCK`; and
- No WARN paths left, **or** every remaining WARN path is disposable and the user has approved losing them.

If non-disposable WARNs remain, repeat evaluate → approve → move until clear.

### 5. Close-out message
When prep is complete:

- Confirm local-only data is either in `_LOCAL_FILES` or approved as disposable.
- Reminder: **the user** removes the worktree and deletes the branch (agent does not).
- Optional: list ✓ disposable paths that will still be deleted with the worktree.


## Agent workflow: check all worktrees
Use when the user wants a repo-wide local-files health check (not necessarily retiring one window).

1. Dry-run:
   ```bash
   .venv/bin/python3 scripts/local_files_check.py --ignored-limit 999
   ```
2. If output has only `OK` / safe `FIX` and no `BLOCK`, run `--apply` **after user confirms**.
3. If `BLOCK`, stop and summarize conflicted paths, differing files, and a recommended resolution; wait for confirmation.
4. For any `WARN: ignored` paths, run the same disposition labeling as the pre-removal workflow (do not move/delete without approval).


## Guardrails
- Require user approval before `--apply`, moves, deletes, new mount entries, or edits to `scripts/local_files_mounts.txt` / `DISPOSABLE_PATTERNS`.
- Never remove worktrees or branches as part of this skill.
- Prefer an existing mount over creating a new one.
- Ensure `FOF_MONO_LOCAL_FILES_ROOT` is set for this machine before `--apply` (see clone-bootstrap). Do not apply while dry-run wants to relink mounts to another user’s home path.
- Use `.venv/bin/python3` from the project virtualenv.


## Related
- `skills/repo-ops/clone-bootstrap/README.md` — rare first-clone / remachine **setup** of hooks and mounts.
- `docs/worktrees-guide.md` — human worktree remove checklist; Step 1 delegates here.
- `skills/repo-ops/local-files-snapshot-backup/README.md` — ZIP backup of `_LOCAL_FILES` to S3 (not WARN classification).
- `scripts/local_files_check.py`, `scripts/local_files_mounts.txt`
