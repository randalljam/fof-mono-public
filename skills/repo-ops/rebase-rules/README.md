file: skills/repo-ops/rebase-rules/README.md
title: Rebase rules
source-github-url: original
source-guide-url: original
history:
  - 2026-07-30 · Randy · Codex [Codex Workspace Setup](019faf02-bddf-76c1-bbfc-6e43cc8b0adf) — require a superseding v2 record and tracked map when a rebase changes lineage evidence
  - 2026-07-30 · Randy · Codex [Codex Workspace Setup](019faf02-bddf-76c1-bbfc-6e43cc8b0adf) — initial rule: preserve and revalidate the branch-start lineage commit


**Use this skill whenever planning, performing, or reviewing a Git rebase. Apply it in addition to `AGENTS.md` branch discipline, Git safety rules, and `skills/repo-ops/branch-lineage-record/README.md`.**


## Rule 1: classify the rebase before acting
A rebase that only replays unpushed commits after the selected lineage record, on the same
fork, may preserve that record unchanged. A base-changing rebase, or any rebase that recreates
the selected record commit, changes lineage evidence and requires a newer v2 `recorded-late`
record. Never keep a stale `branch-start` declaration authoritative merely because its message
survived.

Before rebasing:
1. Fetch/prune, require a clean worktree and index, verify local/remote equality, and obtain
   explicit user approval before rewriting any published commit.
2. Scan first-parent history newest-to-oldest. Select the newest record whose `Branch` exactly
   matches the current branch, validate it, and record its full commit SHA, `Lineage-ID`,
   `Record-ID`, `Parent-Branch`, and `Fork-Commit`.
3. Determine whether the selected record or fork will be rewritten. If neither changes, preserve
   the record commit and verify it remains byte-for-byte identical. If either changes, use the
   workflow below.
4. Upgrade a v1 predecessor to an approved v2 record before a planned base-changing rewrite so
   the rewrite has stable `Lineage-ID` and `Record-ID` identifiers.


## Rule 2: preserve records during the rewrite
Keep every lineage record in the rebase range as its own intentionally empty commit. Leave it as
`pick`; never `drop`, `squash`, `fixup`, or `reword`. Use the applicable keep-empty options:

```bash
git rebase --keep-empty --empty=keep <new-base>
# Or:
git rebase --keep-empty --empty=keep --onto <new-base> <old-base>
```

Save `OLD_TIP`, the selected old record SHA, and old fork SHA before the rewrite. Preserve the
record's full message, tree, author identity, and author date. Re-sign a recreated signed commit
because rewriting invalidates the old signature.


## Rule 3: create deterministic rebase evidence
After an approved base-changing rewrite, locate the recreated predecessor by its unchanged
`Record-ID`, not by commit position alone. Create the tracked UTF-8/LF map required by the
branch-lineage skill:

```text
kind	old-sha	new-sha
fork	<old full fork SHA>	<new full fork SHA>
record	<old full record SHA>	<recreated predecessor SHA>
```

Use full lowercase SHAs and sort rows by `kind`, then `old-sha`. Reject missing, duplicate,
conflicting, or unverifiable rows. Commit the map artifact, record its exact repo-relative path
and Git blob SHA, then append an empty v2 `recorded-late` record with:

```text
Lineage-Type: recorded-late
Lineage-ID: <reuse predecessor Lineage-ID>
Record-ID: <new canonical lowercase UUID>
Relationship: <preserve intended relationship>
Update-Reason: rebase
Supersedes-Record-ID: <recreated predecessor Record-ID>
Previous-Record-Commit: <old pre-rebase record SHA>
Previous-Fork-Commit: <old pre-rebase fork SHA>
Evidence-Artifact: <repo-relative tracked map path>
Evidence-Artifact-Blob: <full map blob SHA>
Evidence-Type: rebase-map
```

Use the exact `recorded-late` subject and remaining canonical fields from
`skills/repo-ops/branch-lineage-record/README.md`. Obtain explicit human review; do not infer
approval. A rebase does not imply `rerooted-to` when the intended parent relationship is
unchanged.


## Rule 4: verify before any push
Verify all of the following:
- The recreated predecessor is on the branch's first-parent history and carries the same stable
  `Lineage-ID` and `Record-ID`.
- The map blob matches `Evidence-Artifact-Blob` and maps the old record/fork SHAs to the exact
  recreated record and new fork.
- The newest applicable record is the superseding record, has a new unique `Record-ID`, and
  validates as `evidence-validated`; there is no fallback to the recreated predecessor.
- The superseding record is empty, its sole parent is the saved pre-record tip, its tree is
  unchanged, and its full message is exact.
- `git range-diff` shows no unintended drops, duplicates, or reorderings; the intended parent,
  fork, and `origin/main` ancestry checks pass.
- Local and remote state and every affected worktree are coordinated for the exact approved
  push. Never force-push without the explicit approval required by `AGENTS.md`.

If any check fails, do not push. Keep the old identifiers and rewrite map for diagnosis, recover
using the approved backup/reflog procedure, and correct the operation without inventing lineage
facts.
