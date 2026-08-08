file: plans/2026-07-30_branch-lineage-records-proposal.md
title: Open Branch Lineage Record Review Proposal
last-updated: 2026-07-30_0948
ai: Codex Subagent (fable5-w-codex) - GPT 5.6 Sol xhigh
session: `Codex Workspace Setup`

This is a human-review and migration proposal, not a runtime ancestry ledger or source of truth. It records the evidence inspected on 2026-07-30 so Randy can approve or correct each declaration before any recorded-late commits are created. In this document, **legacy registry** means only the committed file `apps/holodeck/branch-ancestry.toml`, and every **legacy registry comparison** means a comparison against that committed file. The TOML file is intentionally left unchanged throughout this proposal work and the lineage-commit migration; it remains authoritative for the current legacy path until the new commit-based system reaches verified parity and a later, separately reviewed deprecation removes it.

After `git fetch origin --prune`, 14 open remote branch refs were readable as commit objects: `main` as the root/reference, `feature/branch-lineage-records` as already complete, and 12 branches needing recorded-late review. The symbolic `origin/HEAD` alias is not a branch.


## Proposed hierarchy
```text
main
├── dragon-baby/finish-100
├── feature/admin-automation-skills
├── feature/family-schedule-dashboard
├── feature/holodeck-start
│   └── holodeck/swing-v2
│       └── feature/branch-lineage-records  [branch-start record complete]
├── feature/knowledge-base
├── feature/transcribe-diarize-dg-latest
├── feature/voice-router-kickoff
│   └── feature/voice-router-design         [explicitly rerooted]
├── fof-website-update1
└── stellar-transcriber-start
    └── diarz-landscape
```


## Evidence and validation summary
Every listed remote tip passed `git rev-parse <ref>^{commit}` and `git cat-file -t` as a readable commit. “Root-parent pass” means the earliest first-parent commit after the proposed fork has the proposed fork as its first parent, and the fork is reachable from both the proposed parent and child. A later current merge-base is reported rather than substituted for the creation/reroot fork.

| Branch | Remote tip | Proposed parent / fork | Validation state | Legacy registry comparison (`apps/holodeck/branch-ancestry.toml`) |
|---|---|---|---|---|
| `main` | `0274a63a822cdb2f33698c1ee57d8b4e39c80778` | root; no parent | Root/reference only; no lineage commit proposed. | **no legacy entry** |
| `dragon-baby/finish-100` | `24c90eab2e2849c466aa629fe36cbc5eb67d1c4a` | `main` / `92b9dceaa695d5ed3ad6738198b62483cd8361c7` | **Pass:** direct local creation reflog at the fork, source-worktree HEAD provenance to `main`, root-parent pass (`8174deb99a335206b0f0d6c75eb537eecb9dd9d3`), current merge-base equals fork. | **no legacy entry** |
| `feature/admin-automation-skills` | `b7b8558fc7a7ce28cb26edadf8068e2c6d9547c4` | `main` / `a9686a2400b31bf21a6ba219b3936acf901ad470` | **Pass:** root-parent pass (`64df1f6e1ab65939047e144907386473aff050b5`); current merge-base is later `a6fb8a737460d9f2bd80ca083556a891d3c9971a`, so it is not used as the fork. | **agrees** on parent and fork |
| `feature/family-schedule-dashboard` | `50faa176f167335d710c2e6687ea801a19a2cb21` | `main` / `3ce1278928c4e1111f607e733adae9581aa7726e` | **Pass:** root-parent pass (`853f04b41c27edc9f2c78573c917cf255fb0322f`); current merge-base is later `16deac9bbf7151be1a40561ec9742f06152fefc6`. | **agrees** on parent and fork |
| `feature/holodeck-start` | `4890a7560a2912a5c8df287b5c01e6208d93d261` | `main` / `dc29744f84197c6047a64afa1ae41f53e7b0c6af` | **Pass:** root-parent pass (`b521053eaa3dfacea0902cee72b76d2b7fb77fc2`), current merge-base equals fork, and the first branch commit contains the Holodeck plan/specs. | **agrees** on parent and fork |
| `feature/knowledge-base` | `1990fb1ff53edded79fed92f5e0f7e60dd88a440` | `main` / `a2c9394b7c223a51e528c5dc12e96a747c9d9ad7` | **Pass:** root-parent pass (`59e7b17ba2405ee096e946de1a6d57e951d9b409`), current merge-base equals fork, and the root commit adds the Drive-backed design. | **agrees** on parent and fork |
| `feature/transcribe-diarize-dg-latest` | `1e1047c1668d8a17064b35799ca7084db494db1f` | `main` / `69c3c7644e07bd0fdf2fed911d5f49ce091a7793` | **Pass:** root-parent pass (`f9f1b55d0d29655db6c5a3f090a688b4fbee843f`); current merge-base is later `a6fb8a737460d9f2bd80ca083556a891d3c9971a`. | **agrees** on parent and fork |
| `feature/voice-router-kickoff` | `98165c0008ec241f224a88831ffa42283765556c` | `main` / `172093ed79111d5a65a7865174cc48013b106495` | **Pass:** root-parent pass (`a58c2a3fc35c859fe627f3e018a9cece3746b3ce`); current merge-base is later `a6fb8a737460d9f2bd80ca083556a891d3c9971a`. | **agrees** on parent and fork |
| `feature/voice-router-design` | `f23296f6a5ef02f4fe37407ea4c5f7f6640d94fe` | `feature/voice-router-kickoff` / `c5807155b2243f14d2db28b619df3a75cce8a559` | **Pass, reroot:** merge `f9f01b083c9ae3415276bc108f7ba87b48be3f96` explicitly says design was rerooted on kickoff and has the proposed fork as second parent. Current merge-base `bb9c8510b4e737d13ed11b51ed0243e8ca790006` is a later integration point, not the reroot fork. | **agrees** on reroot parent and fork |
| `fof-website-update1` | `a4037e3b6e8ab232dfd29a2e7bd4cd9e3cbb29ba` | `main` / `6c257af85341de97ec67f8cd2f87a1c3b5a5ca3f` | **Pass:** direct local creation reflog from `main` at the fork, root-parent pass (`0c2fd84d423050d0b70f5476685c7fd1ef6a65a8`), current merge-base equals fork. | **agrees** on parent and fork |
| `holodeck/swing-v2` | `acbdcd3930c1cb84bb045be8b2cdeeb43e8c9a1b` | `feature/holodeck-start` / `1daacb7a9c03dcc114605fa4c23ccc829bf54f32` | **Pass:** direct local creation reflog from the parent at the fork, root-parent pass (`31090dd70f895b38007ce89d046cc60d02f68583`), current merge-base equals fork. | **agrees** on parent and fork |
| `stellar-transcriber-start` | `4caf60e48379dd0466a5a60bed344bdd7ed8b707` | `main` / `2cc3de027671745093f71c280b10d4d19eb9e802` | **Pass after documented rewrite:** historical branch-map named pre-purge fork `7e39123c0d512b95dd2af8b2a3e00617503014ba`; `plans/git/2026-07-22_history-purge-commit-map.tsv` maps it to current equivalent `2cc3de...`; root-parent pass (`5a6ad21e9fc95fe02f82bcdfc526f79d4ca38c68`), current merge-base equals rewritten fork. | **agrees** on current rewritten parent/fork |
| `diarz-landscape` | `6f41fa52c5a221e3a0bf2ddbba7cb7ddbe621cd2` | `stellar-transcriber-start` / `c195a76522a5a8bbf20cb16bb779f07e99e7ab51` | **Pass:** direct local creation reflog from the parent at the fork, root-parent pass (`de29360e3ce42e89cc342b803542214bf7a4281e`), current merge-base equals fork. | **agrees** on parent and fork |
| `feature/branch-lineage-records` | `085deccad44c51e3e6feccb723c1438725586d5c` | `holodeck/swing-v2` / `acbdcd3930c1cb84bb045be8b2cdeeb43e8c9a1b` | **Complete:** `50ba3f68c231d6447c65f8c892537c0e7001d198` is the sole first commit after the fork, its sole parent equals the fork, its tree is unchanged, and its branch-start message is verified. | **no legacy entry** |

No proposed result disagrees with a committed `apps/holodeck/branch-ancestry.toml` entry. “Agrees” is still independently supported by the evidence above; it is not a blind copy. The two no-entry branches are independently resolved by direct creation evidence (`dragon-baby/finish-100`) or a structurally verified branch-start record (`feature/branch-lineage-records`).


## Execution access
No branch was checked out, moved, committed, or pushed while gathering this inventory. No temporary worktree was created. Current branch/worktree access is:

| Branch | Current worktree | Current read-only state | Approved migration access |
|---|---|---|---|
| `main` | `/Users/randytrue/Documents/Code/fof-mono` | tip matches origin; clean | Root only; no lineage commit. |
| `dragon-baby/finish-100` | `/Users/randytrue/Documents/Code/dragon-baby` | tip matches origin; clean | Use existing worktree after fresh clean/sync preflight. |
| `feature/admin-automation-skills` | `/Users/randytrue/Documents/Code/flex` | tip matches origin; only ` M .vscode/settings.json`, an intentional user-owned title-bar color customization; index clean | Use the existing worktree with the approved preservation exception below; never create a competing worktree or stage/commit the settings file. |
| `feature/family-schedule-dashboard` | none | remote and local refs readable | Use an approved disposable worktree. |
| `feature/holodeck-start` | none | remote and local refs readable | Use an approved disposable worktree. |
| `feature/knowledge-base` | none | remote and local refs readable | Use an approved disposable worktree. |
| `feature/transcribe-diarize-dg-latest` | none | remote and local refs readable | Use an approved disposable worktree. |
| `feature/voice-router-kickoff` | none | remote and local refs readable | Use an approved disposable worktree before its child. |
| `feature/voice-router-design` | none | remote and local refs readable | Use an approved disposable worktree after kickoff. |
| `fof-website-update1` | `/Users/randytrue/Documents/Code/fof-website` | tip matches origin; clean | Use existing worktree after fresh clean/sync preflight. |
| `stellar-transcriber-start` | none | remote and local refs readable | Use an approved disposable worktree before its child. |
| `diarz-landscape` | `/Users/randytrue/Documents/Code/stellar-transcriber` | tip matches origin; clean | Use existing worktree after stellar’s record is complete. |
| `holodeck/swing-v2` | none | remote and local refs readable | Use an approved disposable worktree after `feature/holodeck-start`. |
| `feature/branch-lineage-records` | `/Users/randytrue/Documents/Code/holodeck` | tip matches origin; clean | Already complete; no migration commit. |

For a branch without a worktree, the execution agent will first fetch/prune, prove the local ref equals `origin/<branch>`, prove no worktree already holds it, and create a uniquely named disposable worktree under `/private/tmp` only after approval. It will commit and push from that worktree, verify `0 0` divergence, then remove it with `git worktree remove` and prune worktree metadata; it will never delete a worktree directory directly. Existing active worktrees take precedence. An unapproved modification or any divergence blocks that branch, but the specific Admin Automation settings customization is approved under the exception below and does not need to be cleaned, stashed, staged, or committed.

### Admin Automation settings-preservation exception
The future `feature/admin-automation-skills` lineage operation must run in `/Users/randytrue/Documents/Code/flex` while preserving `.vscode/settings.json` exactly as-is. The lineage record remains an empty commit: do not run `git add`, do not stage any file, and leave the settings customization unstaged and uncommitted.

Preflight:
```bash
git fetch origin --prune
test "$(git branch --show-current)" = "feature/admin-automation-skills"
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/feature/admin-automation-skills)"
test "$(git status --porcelain=v1)" = " M .vscode/settings.json"
git diff --cached --quiet
PRE_RECORD_TIP="$(git rev-parse HEAD)"
SETTINGS_BLOB_BEFORE="$(git hash-object .vscode/settings.json)"
SETTINGS_DIFF_BEFORE="$(git diff --no-ext-diff --binary -- .vscode/settings.json | git hash-object --stdin)"
```

Create the approved lineage commit with `git commit --allow-empty` and its exact reviewed message, without staging anything. Postflight before push:
```bash
test "$(git show -s --format='%P' HEAD | wc -w | tr -d ' ')" = "1"
test "$(git rev-parse HEAD^)" = "$PRE_RECORD_TIP"
git diff-tree --quiet HEAD^ HEAD
test -z "$(git diff-tree --no-commit-id --name-only -r HEAD)"
git diff --cached --quiet
test "$(git status --porcelain=v1)" = " M .vscode/settings.json"
test "$(git hash-object .vscode/settings.json)" = "$SETTINGS_BLOB_BEFORE"
test "$(git diff --no-ext-diff --binary -- .vscode/settings.json | git hash-object --stdin)" = "$SETTINGS_DIFF_BEFORE"
git show -s --format='%H%n%P%n%B' HEAD
```

After the normal push and local/remote `0 0` check, repeat the index, porcelain-status, settings blob-hash, and binary-diff-hash comparisons. Success requires that the commit contains no path, the index remains empty, `.vscode/settings.json` remains the only working-tree difference, and its content and diff are byte-for-byte unchanged.


## Proposed recorded-late commit messages
Randy True approved all 12 exact declarations on 2026-07-30. The executing task’s actual Codex session metadata resolves through Holodeck’s label vocabulary to `Codex Subagent (fable5-w-codex) - GPT 5.6 Sol xhigh`; that label is therefore the exact `Created-By` for this serialized migration. Every commit uses the same approval metadata: `Reviewed-By: Randy True` and `Reviewed-At: 2026-07-30T09:48:16-07:00`.

### `dragon-baby/finish-100`
```text
chore(repo): record branch lineage late for dragon-baby/finish-100

Record-Type: branch-lineage
Lineage-Type: recorded-late
Created-By: Codex Subagent (fable5-w-codex) - GPT 5.6 Sol xhigh
Branch: dragon-baby/finish-100
Parent-Branch: main
Fork-Commit: 92b9dceaa695d5ed3ad6738198b62483cd8361c7
Fork-Subject: docs(repo-ops): add watcher-set skill for process done-detect alarms
Branch-Purpose: Finish the Dragon Baby 100% fluency experience with an easier Fluency Feast start.
Evidence-Type: local-reflog-and-worktree-head
Evidence: Local branch reflog at 2026-07-30T04:49:24-07:00 records creation from HEAD at 92b9dceaa695d5ed3ad6738198b62483cd8361c7; the source math-quiz worktree HEAD reflog records checkout to main at that SHA; earliest child commit 8174deb99a335206b0f0d6c75eb537eecb9dd9d3 has the fork as first parent; current merge-base with main equals the fork.
Confidence: high
Review-Status: approved
Reviewed-By: Randy True
Reviewed-At: 2026-07-30T09:48:16-07:00
Lineage-Version: 1
```

### `feature/admin-automation-skills`
```text
chore(repo): record branch lineage late for feature/admin-automation-skills

Record-Type: branch-lineage
Lineage-Type: recorded-late
Created-By: Codex Subagent (fable5-w-codex) - GPT 5.6 Sol xhigh
Branch: feature/admin-automation-skills
Parent-Branch: main
Fork-Commit: a9686a2400b31bf21a6ba219b3936acf901ad470
Fork-Subject: Merge pull request #14 from FocusOnFoundationsNonprofit/feature/fly-fly-sync
Branch-Purpose: Build reusable admin automation skills for ScanSnap, masterlist reminders, QBO reporting, and recurring-task management.
Evidence-Type: legacy-registry-and-first-parent-root
Evidence: The committed legacy registry identifies main and a9686a2400b31bf21a6ba219b3936acf901ad470 with high confidence; earliest branch first-parent commit 64df1f6e1ab65939047e144907386473aff050b5 has that fork as first parent and the fork is reachable from main and child. Current merge-base a6fb8a737460d9f2bd80ca083556a891d3c9971a is later integration history and is not substituted.
Confidence: high
Review-Status: approved
Reviewed-By: Randy True
Reviewed-At: 2026-07-30T09:48:16-07:00
Lineage-Version: 1
```

### `feature/family-schedule-dashboard`
```text
chore(repo): record branch lineage late for feature/family-schedule-dashboard

Record-Type: branch-lineage
Lineage-Type: recorded-late
Created-By: Codex Subagent (fable5-w-codex) - GPT 5.6 Sol xhigh
Branch: feature/family-schedule-dashboard
Parent-Branch: main
Fork-Commit: 3ce1278928c4e1111f607e733adae9581aa7726e
Fork-Subject: docs(repo-ops): add promote-to-main skill + AGENTS pointer
Branch-Purpose: Add a live family schedule to the lesson-logger dashboard with local editing and refresh support.
Evidence-Type: legacy-registry-and-first-parent-root
Evidence: The committed legacy registry identifies main and 3ce1278928c4e1111f607e733adae9581aa7726e with high confidence; earliest branch first-parent commit 853f04b41c27edc9f2c78573c917cf255fb0322f has that fork as first parent and the fork is reachable from main and child. Current merge-base 16deac9bbf7151be1a40561ec9742f06152fefc6 is later integration history and is not substituted.
Confidence: high
Review-Status: approved
Reviewed-By: Randy True
Reviewed-At: 2026-07-30T09:48:16-07:00
Lineage-Version: 1
```

### `feature/holodeck-start`
```text
chore(repo): record branch lineage late for feature/holodeck-start

Record-Type: branch-lineage
Lineage-Type: recorded-late
Created-By: Codex Subagent (fable5-w-codex) - GPT 5.6 Sol xhigh
Branch: feature/holodeck-start
Parent-Branch: main
Fork-Commit: dc29744f84197c6047a64afa1ae41f53e7b0c6af
Fork-Subject: feat(skills): add fable5-w-codex orchestration skill (#41)
Branch-Purpose: Build the Holodeck control center for repository, worktree, application, and AI-session visibility.
Related-Work: plans/2026-07-09_holodeck/2026-07-09_holodeck-plan.md
Evidence-Type: legacy-registry-and-first-parent-root
Evidence: The committed legacy registry identifies main and dc29744f84197c6047a64afa1ae41f53e7b0c6af with high confidence; earliest branch first-parent commit b521053eaa3dfacea0902cee72b76d2b7fb77fc2 has that fork as first parent, adds the cited plan/specs, and the current merge-base equals the fork.
Confidence: high
Review-Status: approved
Reviewed-By: Randy True
Reviewed-At: 2026-07-30T09:48:16-07:00
Lineage-Version: 1
```

### `feature/knowledge-base`
```text
chore(repo): record branch lineage late for feature/knowledge-base

Record-Type: branch-lineage
Lineage-Type: recorded-late
Created-By: Codex Subagent (fable5-w-codex) - GPT 5.6 Sol xhigh
Branch: feature/knowledge-base
Parent-Branch: main
Fork-Commit: a2c9394b7c223a51e528c5dc12e96a747c9d9ad7
Fork-Subject: chore: remove conflicting cursor rules
Branch-Purpose: Build a Drive-backed internal knowledge base with resilient OAuth and paginated content ingestion.
Related-Work: plans/2026-07-21_knowledge-base/2026-07-21_design.md
Evidence-Type: legacy-registry-and-first-parent-root
Evidence: The committed legacy registry identifies main and a2c9394b7c223a51e528c5dc12e96a747c9d9ad7 with high confidence; earliest branch first-parent commit 59e7b17ba2405ee096e946de1a6d57e951d9b409 has that fork as first parent, adds the cited design, and the current merge-base equals the fork.
Confidence: high
Review-Status: approved
Reviewed-By: Randy True
Reviewed-At: 2026-07-30T09:48:16-07:00
Lineage-Version: 1
```

### `feature/transcribe-diarize-dg-latest`
```text
chore(repo): record branch lineage late for feature/transcribe-diarize-dg-latest

Record-Type: branch-lineage
Lineage-Type: recorded-late
Created-By: Codex Subagent (fable5-w-codex) - GPT 5.6 Sol xhigh
Branch: feature/transcribe-diarize-dg-latest
Parent-Branch: main
Fork-Commit: 69c3c7644e07bd0fdf2fed911d5f49ce091a7793
Fork-Subject: Enhance README for merge operations with detailed file overlap preflight checks
Branch-Purpose: Update transcription to use Deepgram's latest diarization model and preserve its source tagging.
Evidence-Type: legacy-registry-and-first-parent-root
Evidence: The committed legacy registry identifies main and 69c3c7644e07bd0fdf2fed911d5f49ce091a7793 with high confidence; earliest branch first-parent commit f9f1b55d0d29655db6c5a3f090a688b4fbee843f has that fork as first parent and the fork is reachable from main and child. Current merge-base a6fb8a737460d9f2bd80ca083556a891d3c9971a is later integration history and is not substituted.
Confidence: high
Review-Status: approved
Reviewed-By: Randy True
Reviewed-At: 2026-07-30T09:48:16-07:00
Lineage-Version: 1
```

### `feature/voice-router-kickoff`
```text
chore(repo): record branch lineage late for feature/voice-router-kickoff

Record-Type: branch-lineage
Lineage-Type: recorded-late
Created-By: Codex Subagent (fable5-w-codex) - GPT 5.6 Sol xhigh
Branch: feature/voice-router-kickoff
Parent-Branch: main
Fork-Commit: 172093ed79111d5a65a7865174cc48013b106495
Fork-Subject: updated local files check
Branch-Purpose: Build the voice-router capture, routing, digest, delivery, and VoiceMarks review system.
Evidence-Type: legacy-registry-and-first-parent-root
Evidence: The committed legacy registry identifies main and 172093ed79111d5a65a7865174cc48013b106495 with high confidence; earliest branch first-parent commit a58c2a3fc35c859fe627f3e018a9cece3746b3ce has that fork as first parent and the fork is reachable from main and child. Current merge-base a6fb8a737460d9f2bd80ca083556a891d3c9971a is later integration history and is not substituted.
Confidence: high
Review-Status: approved
Reviewed-By: Randy True
Reviewed-At: 2026-07-30T09:48:16-07:00
Lineage-Version: 1
```

### `feature/voice-router-design`
```text
chore(repo): record branch lineage late for feature/voice-router-design

Record-Type: branch-lineage
Lineage-Type: recorded-late
Created-By: Codex Subagent (fable5-w-codex) - GPT 5.6 Sol xhigh
Branch: feature/voice-router-design
Parent-Branch: feature/voice-router-kickoff
Fork-Commit: c5807155b2243f14d2db28b619df3a75cce8a559
Fork-Subject: Add dashboard design variants
Branch-Purpose: Develop and preserve the voice-router dashboard design variants on the implementation branch lineage.
Evidence-Type: explicit-reroot-merge
Evidence: Merge f9f01b083c9ae3415276bc108f7ba87b48be3f96 explicitly states that design was rerooted on kickoff and has c5807155b2243f14d2db28b619df3a75cce8a559 as its second parent; the fork is reachable from parent and child. Current merge-base bb9c8510b4e737d13ed11b51ed0243e8ca790006 is a later kickoff integration and is not substituted for the reroot fork.
Confidence: high
Review-Status: approved
Reviewed-By: Randy True
Reviewed-At: 2026-07-30T09:48:16-07:00
Lineage-Version: 1
```

### `fof-website-update1`
```text
chore(repo): record branch lineage late for fof-website-update1

Record-Type: branch-lineage
Lineage-Type: recorded-late
Created-By: Codex Subagent (fable5-w-codex) - GPT 5.6 Sol xhigh
Branch: fof-website-update1
Parent-Branch: main
Fork-Commit: 6c257af85341de97ec67f8cd2f87a1c3b5a5ca3f
Fork-Subject: Merge pull request #54 from FocusOnFoundationsNonprofit/feature/web-site-redo-fof
Branch-Purpose: Iterate the Focus on Foundations website design with a skin system, inspiration library, and review workflow.
Evidence-Type: local-reflog
Evidence: Local branch reflog at 2026-07-25T11:23:51-07:00 records creation from main at 6c257af85341de97ec67f8cd2f87a1c3b5a5ca3f; earliest branch first-parent commit 0c2fd84d423050d0b70f5476685c7fd1ef6a65a8 has that fork as first parent and the current merge-base equals the fork.
Confidence: high
Review-Status: approved
Reviewed-By: Randy True
Reviewed-At: 2026-07-30T09:48:16-07:00
Lineage-Version: 1
```

### `stellar-transcriber-start`
```text
chore(repo): record branch lineage late for stellar-transcriber-start

Record-Type: branch-lineage
Lineage-Type: recorded-late
Created-By: Codex Subagent (fable5-w-codex) - GPT 5.6 Sol xhigh
Branch: stellar-transcriber-start
Parent-Branch: main
Fork-Commit: 2cc3de027671745093f71c280b10d4d19eb9e802
Fork-Subject: Merge pull request #34 from FocusOnFoundationsNonprofit/ops/create-worktree-skill
Branch-Purpose: Develop an evaluation-driven Stellar transcription and diarization pipeline through staged milestones.
Related-Work: apps/transcription/stellar-transcriber/docs/2026-07-03_milestone-1-plan.md
Evidence-Type: history-rewrite-map
Evidence: Historical immutable branch-map named pre-purge fork 7e39123c0d512b95dd2af8b2a3e00617503014ba; plans/git/2026-07-22_history-purge-commit-map.tsv maps it to rewritten equivalent 2cc3de027671745093f71c280b10d4d19eb9e802 with the same subject; earliest current first-parent commit 5a6ad21e9fc95fe02f82bcdfc526f79d4ca38c68 has the rewritten fork as first parent and current merge-base equals it.
Confidence: high
Review-Status: approved
Reviewed-By: Randy True
Reviewed-At: 2026-07-30T09:48:16-07:00
Lineage-Version: 1
```

### `diarz-landscape`
```text
chore(repo): record branch lineage late for diarz-landscape

Record-Type: branch-lineage
Lineage-Type: recorded-late
Created-By: Codex Subagent (fable5-w-codex) - GPT 5.6 Sol xhigh
Branch: diarz-landscape
Parent-Branch: stellar-transcriber-start
Fork-Commit: c195a76522a5a8bbf20cb16bb779f07e99e7ab51
Fork-Subject: chore: update .gitignore and symlink paths
Branch-Purpose: Research, implement, and benchmark a multi-backend diarization landscape against standard metrics and corpora.
Related-Work: apps/transcription/stellar-transcriber/docs/2026-07-25_diarization-bench-plan.md
Evidence-Type: local-reflog
Evidence: Local branch reflog at 2026-07-25T10:07:36-07:00 records creation from stellar-transcriber-start at c195a76522a5a8bbf20cb16bb779f07e99e7ab51; earliest branch first-parent commit de29360e3ce42e89cc342b803542214bf7a4281e has that fork as first parent and the current merge-base equals the fork.
Confidence: high
Review-Status: approved
Reviewed-By: Randy True
Reviewed-At: 2026-07-30T09:48:16-07:00
Lineage-Version: 1
```

### `holodeck/swing-v2`
```text
chore(repo): record branch lineage late for holodeck/swing-v2

Record-Type: branch-lineage
Lineage-Type: recorded-late
Created-By: Codex Subagent (fable5-w-codex) - GPT 5.6 Sol xhigh
Branch: holodeck/swing-v2
Parent-Branch: feature/holodeck-start
Fork-Commit: 1daacb7a9c03dcc114605fa4c23ccc829bf54f32
Fork-Subject: Merge pull request #53 from FocusOnFoundationsNonprofit/feature/holodeck-commits
Branch-Purpose: Rebuild Holodeck around Active AI, To-do, Active Work, and Universe.
Related-Work: apps/holodeck/openspec/changes/2026-07-23-swing-v2-deck/proposal.md
Evidence-Type: local-reflog
Evidence: Local branch reflog at 2026-07-23T05:46:54-07:00 records creation from feature/holodeck-start at 1daacb7a9c03dcc114605fa4c23ccc829bf54f32; earliest branch first-parent commit 31090dd70f895b38007ce89d046cc60d02f68583 has that fork as first parent and the current merge-base equals the fork.
Confidence: high
Review-Status: approved
Reviewed-By: Randy True
Reviewed-At: 2026-07-30T09:48:16-07:00
Lineage-Version: 1
```


## Ordered migration after review
1. Randy True approved every exact message, parent, fork, purpose, evidence, confidence, and legacy registry comparison against committed `apps/holodeck/branch-ancestry.toml` at `2026-07-30T09:48:16-07:00`. Preserve the approved text exactly during execution.
2. Refresh remote refs and re-run the evidence/DAG audit. Stop a branch if its tip, fork reachability, evidence, worktree assignment, or local/remote equality changed.
3. Process parent branches before stacked children: main children first; then `stellar-transcriber-start` → `diarz-landscape`, `feature/voice-router-kickoff` → `feature/voice-router-design`, and `feature/holodeck-start` → `holodeck/swing-v2`. `feature/branch-lineage-records` is already complete and receives no migration commit.
4. For each branch, resolve the executing agent’s exact `Created-By`, require a synchronized checkout with no merge/rebase in progress, record the pre-commit tip, create exactly one empty recorded-late commit, and verify its sole first parent is the saved tip. Require a clean worktree except for the explicitly approved Admin Automation `.vscode/settings.json` customization, which must pass the byte-for-byte preservation checks above and remain unstaged. Revalidate the historical fork independently; never treat the late commit parent as fork proof.
5. Inspect the full commit message and empty tree diff before pushing. Push only the current branch with a normal fast-forward push—never force—and require local/remote SHA equality plus `0 0` divergence.
6. Remove each disposable worktree safely before moving to the next branch. Never switch, clean, stash, reset, or otherwise disturb an active worktree without its owner’s explicit coordination.
7. After all approved branches are migrated, audit every open remote ref for exactly one applicable lineage record, expected parent/fork/evidence, expected worktree state (clean except for the preserved Admin Automation settings customization), and remote synchronization. Compare the result to this approved proposal and retain an execution report.


## Holodeck follow-on required before PR
This feature branch is not ready to PR into `holodeck/swing-v2` until all of the following are implemented and verified:
1. Ingest both commit formats: structurally verified `branch-start` and evidence-backed `recorded-late`. Parse strict subjects and ordered fields, require full SHAs and exact fork subjects, and validate branch names, parent refs, version, and commit reachability.
2. Adopt the new evidence/status model. Keep structural status distinct from confidence and human review; treat branch-start as structurally verified only when its sole parent/fork/first-unique/tree checks pass, and treat recorded-late as declarative evidence whose commit position cannot prove the fork. Preserve explicit reroot evidence and keep original fork/reroot anchors distinct from later current merge-bases or rebase bases.
3. Reject or surface malformed, duplicate, stale, conflicting, cross-branch, wrong-version, or unreachable records. Define deterministic precedence only for valid records; never silently choose between conflicting declarations.
4. Migrate every approved open branch using the ordered process above, then recollect from fresh remote refs.
5. Compare commit-derived results branch by branch with the current committed `apps/holodeck/branch-ancestry.toml` path, including the no-entry branches and the voice-router reroot. Investigate every mismatch; do not manufacture parity.
6. Deprecate and remove the legacy `branch-ancestry.toml` reader and registry only after commit-derived parity is complete, tests are green, live output is verified, and Randy approves removal. The committed `apps/holodeck/branch-ancestry.toml` file remains untouched throughout this proposal and every lineage-commit migration operation; only a later, separately reviewed deprecation may modify or remove it.
7. Update Holodeck UI labels and details to show record type, structural status, evidence type, confidence, review status/reviewer/time, and actionable invalid/conflict states without presenting pending or late evidence as structural truth.
8. Update branch-creation workflows to invoke `skills/repo-ops/branch-lineage-record/README.md` before any other unique commit and publication. Update rebase workflows to invoke `skills/repo-ops/rebase-rules/README.md`, preserve the branch-start record as the first unique empty commit, and revalidate its rewritten first parent/base and full metadata after rebase.
9. Add regression coverage for valid branch-start and recorded-late records; malformed/missing/unknown fields; duplicate and conflicting records; wrong branch/parent/fork/subject/version; branch-start records that are late, non-empty, merged, or have the wrong first parent; rebases and history rewrites; explicit reroot merges; deleted branches; stacked parent/child chains; changed current merge-bases; pending versus approved review; and legacy parity/removal.
10. Regenerate the Holodeck snapshot from clean fetched refs, live-verify the branch hierarchy and every evidence/status label, and restart the Holodeck server if code or snapshot loading requires it.
11. Before the PR, run focused lineage tests and the full Holodeck suite, inspect the complete diff, verify `apps/holodeck/branch-ancestry.toml` is changed only by the later deliberate removal commit, confirm a clean worktree, fetch/prune again, and prove local/remote synchronization and expected ancestry for `feature/branch-lineage-records`, `holodeck/swing-v2`, and `origin/main`.


## Review decision
Randy True approved all 12 recorded-late declarations and authorized their serialized creation and normal publication at `2026-07-30T09:48:16-07:00`. Execution must follow the ordered safeguards above, skip only a branch whose fresh preflight conflicts with the approved evidence or safe worktree state, and stop after the migration audit without beginning Holodeck implementation or legacy deprecation.
