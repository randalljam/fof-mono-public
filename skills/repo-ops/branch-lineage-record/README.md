file: skills/repo-ops/branch-lineage-record/README.md
title: Record durable branch lineage
source-github-url: original
source-guide-url: original
history:
  - 2026-07-30 · Randy · Codex [Codex Workspace Setup](019faf02-bddf-76c1-bbfc-6e43cc8b0adf) — add v2 relationship, update reason, stable IDs, supersession, rebase, and rewrite evidence
  - 2026-07-30 · Randy · Codex [Codex Workspace Setup](019faf02-bddf-76c1-bbfc-6e43cc8b0adf) — initial branch-start and recorded-late lineage procedure


**Use this skill to create, update, review, or validate a durable Git commit that declares a branch’s parent, fork, and purpose. Apply `AGENTS.md` branch discipline and Git safety rules. Never rewrite an already-pushed lineage record; append a superseding record.**


## Core model
- `Lineage-Type` says when/how the record was created: `branch-start` or `recorded-late`.
- `Relationship` says what the parent edge means: `created-from` or `rerooted-to`.
- `Update-Reason` says why this record exists: `initial`, `late-migration`, `correction`, `reroot`, `rebase`, or `history-rewrite`.
- `Lineage-ID` is one canonical lowercase UUID for the logical branch lineage. Reuse it across v2 corrections, renames, rebases, and history rewrites.
- `Record-ID` is one canonical lowercase UUID for the logical record. Generate a new value for a superseding record; preserve it when Git recreates that same logical record during a rewrite.

Scan a branch’s first-parent history newest-to-oldest. Select the newest record applicable to that branch before validating it. An inherited record whose `Branch` names a stacked parent is not applicable. Never fall back when the newest applicable record is malformed, pending, unsupported, or has a bad supersession link; expose that state.


## Preflight
1. Fetch current refs; require the exact branch, no merge/rebase, a clean index/worktree, and `0 0` local/remote divergence. Preserve only a separately approved working-tree exception.
2. Resolve full branch names, the current parent ref, full fork SHA, exact fork subject, concise branch purpose, and the executing agent’s exact Holodeck label via `apps/holodeck/turns/labels.py`.
3. Generate UUIDs with `uuidgen | tr '[:upper:]' '[:lower:]'`; never reuse another lineage’s `Lineage-ID` or another logical record’s `Record-ID`.
4. For an update, inspect the selected predecessor’s full message and commit. Reuse its v2 `Lineage-ID`; generate a new `Record-ID`; use `Supersedes-Record-ID`. A first v2 upgrade of a v1 record instead uses `Supersedes-Record-Commit` and establishes both IDs.
5. Obtain explicit human review for every recorded-late declaration. Use `pending` without reviewer fields until approved.


## Canonical v2 order
Use one blank line after the exact subject and no blank lines between fields. Reject duplicate, unknown, or out-of-order fields. Omit conditional fields rather than leaving them blank.

- `branch-start` subject: `chore(repo): record branch lineage at branch start for <Branch>`
- Every `recorded-late` subject, regardless of update reason: `chore(repo): record branch lineage late for <Branch>`

```text
Record-Type: branch-lineage
Lineage-Type: branch-start | recorded-late
Lineage-ID: <canonical lowercase UUID>
Record-ID: <canonical lowercase UUID>
Relationship: created-from | rerooted-to
Update-Reason: initial | late-migration | correction | reroot | rebase | history-rewrite
Created-By: <exact Holodeck session/model label>
Branch: <exact full branch name>
Parent-Branch: <exact full parent name>
Fork-Commit: <full current fork SHA>
Fork-Subject: <exact one-line fork subject>
Branch-Purpose: <concise branch purpose>
Related-Work: <optional real issue, PR, or plan>
Supersedes-Record-ID: <required for a v2 predecessor; mutually exclusive with Supersedes-Record-Commit>
Supersedes-Record-Commit: <required for a v1 predecessor; mutually exclusive with Supersedes-Record-ID>
Previous-Record-Commit: <required for rebase/history-rewrite>
Previous-Fork-Commit: <required whenever the fork SHA changed or was rewritten>
Evidence-Commit: <required for reroot>
Evidence-Artifact: <required repo-relative rewrite map for rebase/history-rewrite>
Evidence-Artifact-Blob: <required full Git blob SHA for Evidence-Artifact>
Evidence-Type: <required for recorded-late>
Evidence: <required specific auditable evidence>
Confidence: high | medium | low
Review-Status: pending | approved
Reviewed-By: <required when approved>
Reviewed-At: <required ISO-8601 timestamp when approved>
Lineage-Version: 2
```

`branch-start` ends after optional `Related-Work` with `Lineage-Version: 2`; it has no supersession, evidence, confidence, or review fields. `recorded-late` includes evidence/review fields and any applicable conditional fields in the order above.


## Branch-start: initial created-from
Use only while the branch still equals its fork and has no unique commit. Create this empty commit as the first unique commit.

```text
chore(repo): record branch lineage at branch start for feature/example

Record-Type: branch-lineage
Lineage-Type: branch-start
Lineage-ID: 11111111-1111-4111-8111-111111111111
Record-ID: 22222222-2222-4222-8222-222222222222
Relationship: created-from
Update-Reason: initial
Created-By: <resolved executing-agent label>
Branch: feature/example
Parent-Branch: main
Fork-Commit: <full fork SHA>
Fork-Subject: <exact fork subject>
Branch-Purpose: Build the example capability.
Lineage-Version: 2
```

Verify `HEAD^ == Fork-Commit`, this is the first commit in `Fork-Commit..HEAD`, both trees match, the message is exact, and the fork is reachable from the parent. Then push normally and require `0 0`.


## Recorded-late: late migration
Use for the first declaration on a pre-v2 branch when no lineage record exists. Set `Relationship: created-from`, `Update-Reason: late-migration`, new IDs, and no supersession fields. Preserve historical fork evidence rather than substituting a later merge-base.

```text
chore(repo): record branch lineage late for feature/example

Record-Type: branch-lineage
Lineage-Type: recorded-late
Lineage-ID: 11111111-1111-4111-8111-111111111111
Record-ID: 33333333-3333-4333-8333-333333333333
Relationship: created-from
Update-Reason: late-migration
Created-By: <resolved executing-agent label>
Branch: feature/example
Parent-Branch: main
Fork-Commit: <full historical fork SHA>
Fork-Subject: <exact fork subject>
Branch-Purpose: Build the example capability.
Evidence-Type: first-parent-root
Evidence: Earliest branch commit <full SHA> has Fork-Commit as first parent and the fork is reachable from parent and child.
Confidence: high
Review-Status: approved
Reviewed-By: <reviewer>
Reviewed-At: <ISO-8601 timestamp>
Lineage-Version: 2
```


## Recorded-late: correction
Use `Update-Reason: correction` to supersede wrong or invalid metadata without changing history. Preserve the intended relationship. Reuse a v2 predecessor’s `Lineage-ID`, generate a new `Record-ID`, and reference `Supersedes-Record-ID`; for a v1 predecessor establish IDs and reference its full commit SHA.

```text
Relationship: created-from
Update-Reason: correction
Supersedes-Record-Commit: <full v1 record SHA>
Evidence-Type: reviewed-correction
Evidence: Human review corrected <specific field>; Git validates the replacement parent/fork.
```

A correction may supersede an invalid predecessor. The supersession reference must still identify that exact predecessor. Include `Previous-Fork-Commit` when the corrected fork differs. If the preserved relationship is `rerooted-to`, use `Evidence-Commit` and `Evidence-Type: explicit-reroot-merge`; describe both the correction and merge proof in `Evidence`.


## Recorded-late: reroot
Use `Relationship: rerooted-to` and `Update-Reason: reroot`. Require `Evidence-Commit`; it must be a merge on the child’s first-parent history whose second parent equals `Fork-Commit`, and that fork must be reachable from the declared parent.

```text
chore(repo): record branch lineage late for feature/voice-router-design

Record-Type: branch-lineage
Lineage-Type: recorded-late
Lineage-ID: <new stable UUID established by this v1 upgrade>
Record-ID: <new unique UUID>
Relationship: rerooted-to
Update-Reason: reroot
Created-By: <resolved executing-agent label>
Branch: feature/voice-router-design
Parent-Branch: feature/voice-router-kickoff
Fork-Commit: c5807155b2243f14d2db28b619df3a75cce8a559
Fork-Subject: Add dashboard design variants
Branch-Purpose: Develop and preserve the voice-router dashboard design variants on the implementation branch lineage.
Supersedes-Record-Commit: 99b76da0a87d9e0d68d3a00f4f46f0cb05360164
Evidence-Commit: f9f01b083c9ae3415276bc108f7ba87b48be3f96
Evidence-Type: explicit-reroot-merge
Evidence: Merge f9f01b083c9ae3415276bc108f7ba87b48be3f96 reroots design on kickoff and has Fork-Commit as its second parent.
Confidence: high
Review-Status: approved
Reviewed-By: Randy True
Reviewed-At: 2026-07-30T09:48:16-07:00
Lineage-Version: 2
```


## Recorded-late: base-changing rebase
A base-changing rebase cannot leave a stale branch-start claim authoritative. After the approved rewrite, append a v2 recorded-late record with the unchanged intended `Relationship`, `Update-Reason: rebase`, reused `Lineage-ID`, new `Record-ID`, `Supersedes-Record-ID`, `Previous-Record-Commit`, and `Previous-Fork-Commit`. Require an approved tracked map:

```text
Update-Reason: rebase
Supersedes-Record-ID: <stable predecessor Record-ID>
Previous-Record-Commit: <pre-rebase predecessor commit SHA>
Previous-Fork-Commit: <pre-rebase fork SHA>
Evidence-Artifact: docs/git/<dated-rebase-map>.tsv
Evidence-Artifact-Blob: <full blob SHA>
Evidence-Type: rebase-map
Evidence: Map <artifact path> connects the prior record and fork to their rewritten commits; Git validates the current parent/fork.
```

Validate map rows from the old record SHA to the recreated predecessor commit carrying the same `Record-ID`, and from the old fork SHA to `Fork-Commit`. Old SHAs may be historical identifiers after publication; never require them to remain reachable when the tracked map proves the rewrite.


## Recorded-late: history rewrite
After a whole-history rewrite, append a record with `Update-Reason: history-rewrite`; do not imply reroot unless the intended relationship changed. Reuse `Lineage-ID`, generate `Record-ID`, and require:

```text
Supersedes-Record-ID: <stable predecessor Record-ID>
Previous-Record-Commit: <pre-rewrite record SHA>
Previous-Fork-Commit: <pre-rewrite fork SHA>
Evidence-Artifact: docs/git/<dated-history-rewrite-map>.tsv
Evidence-Artifact-Blob: <full blob SHA>
Evidence-Type: history-rewrite-map
Evidence: Map <artifact path> connects the prior record and fork to their rewritten commits; Git validates the current parent/fork.
```

The artifact must be tracked in the record’s tree. Its blob must match `Evidence-Artifact-Blob`, and it must map the old record and fork SHAs to rewritten equivalents. The rewritten predecessor must carry the same `Record-ID`. Old object SHAs may legitimately no longer resolve. Upgrade a v1 predecessor to v2 before a planned whole-history rewrite; a missing v1 object has no stable ID and cannot meet this proof.


### Rewrite-map contract
Use UTF-8 without a byte-order mark and LF line endings. The first line is exactly `kind<TAB>old-sha<TAB>new-sha`. Data rows use `record` or `fork` plus full lowercase 40-hex SHAs, sorted by `kind` then `old-sha`. Reject blank rows, unknown kinds, duplicate `(kind, old-sha)` keys, and conflicting targets. A record must have exactly one matching `record` row from `Previous-Record-Commit` to the recreated predecessor and one `fork` row from `Previous-Fork-Commit` to `Fork-Commit`; unrelated repository-wide rows are allowed. The reviewed, tracked map is the trust anchor when an old object no longer exists.


## v1 compatibility
Do not rewrite pushed v1 records. Normalize them as follows:

| v1 value | Normalized v2 view |
|---|---|
| `Lineage-Type: branch-start` | `branch-start`, `Relationship: created-from`, `Update-Reason: initial` |
| `Lineage-Type: recorded-late` + `Evidence-Type: explicit-reroot-merge` | `recorded-late`, `Relationship: rerooted-to`, `Update-Reason: late-migration` |
| Other v1 recorded-late evidence | `recorded-late`, `Relationship: created-from`, `Update-Reason: late-migration` |

V1 has no logical IDs. A first v2 correction/schema upgrade establishes `Lineage-ID` and `Record-ID` and uses `Supersedes-Record-Commit`. Existing v1 structural, evidence, review, subject, order, fork, and empty-commit checks still apply.

V1 field order is the v2 order with `Lineage-ID`, `Record-ID`, `Relationship`, `Update-Reason`, all supersession/history/artifact fields, and `Evidence-Commit` omitted; `Lineage-Version` is `1`. V1 `branch-start` ends after optional `Related-Work`. V1 `recorded-late` then requires `Evidence-Type`, `Evidence`, `Confidence`, and `Review-Status`; approved records require `Reviewed-By` and `Reviewed-At`.


## Final verification
Before committing, save `PRE_RECORD_TIP="$(git rev-parse HEAD)"`. Create exactly one empty commit without staging files. Verify its sole parent equals the saved tip, its tree and changed-path list are empty, its full message is exact, applicable fork/evidence/supersession checks pass, and unrelated working state is unchanged. Across all current refs, reject duplicate `Record-ID` values, a `Lineage-ID` used by another branch lineage, supersession cycles, and a supersession target that is not the selected predecessor. Push only the current branch normally, fetch/prune, require local/remote equality and `0 0`, and report record/fork IDs plus verification and review state.
