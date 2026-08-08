file: apps/minecraft/mods/mathquest/docs/reviews/2026-07-28_pr-60-code-review.md
title: PR #60 — MathQuest 1.25.4 integration code review
pr: https://github.com/FocusOnFoundationsNonprofit/fof-mono/pull/60
reviewed-code-head: d79a53dd24e2d66905ae72d5a232c6503420891d
review-followup-head: 58d9889905591017d2ab4a7dfec975b158dec735
date: 2026-07-28


## Purpose

This memo is the repo-native record of the code and PR review for the long-running
MathQuest integration branch. GitHub PR #60 remains the review conversation and merge
record; this file preserves the findings, Randy's review decisions, and verification in
the repository so future agents can discover them without querying GitHub.


## Scope

The review covered the 299-file PR from `feature/minecraft-mod-build-local` into `main`,
including:

- MathQuest 1.25.4 nested Fabric and Forge builds
- shared/common architecture and loader-specific networking
- TP-credit earning and spending
- the local HTTP control panel
- MathQuest and math-quiz SQLite integration
- the Mineflayer Forge companion
- build, test, and deployment tooling

The review emphasized regression risk because the code is actively used and was already
working. No findings 1–4 were changed as part of PR #60.


## Findings for follow-up

### 1. Client-controlled item grants

The Fabric and Forge reward receivers accept a client-provided item ID and count. When
TP-credit earning is off, a modified client can request unauthorized items or quantities.
This is an inherited Fabric authorization issue that is now also present in the Forge
path.

Relevant code:

- `apps/minecraft/mods/mathquest/fabric/shared/src/main/java/com/kidgames/mathquest/MathQuestMod.java`
  — `GiveRewardPayload` receiver
- `apps/minecraft/mods/mathquest/forge/targets/forge-1.20.1/src/main/java/com/kidgames/mathquest/forge/net/MathQuestNetworkForge.java`
  — `GiveRewardPacket.handle`
- `apps/minecraft/mods/mathquest/fabric/common/src/main/java/com/kidgames/mathquest/server/QuizResultProcessor.java`
  — `grantReward`

**Disposition:** Unscheduled follow-up. No solution was selected during this review.

### 2. Client-controlled quiz completion data

The server accepts client-reported answers, correctness, totals, and TP-credit eligibility.
The one-use token proves that a quiz was opened, but the current result flow does not
independently verify that the reported quiz was honestly completed. This is distinct from
the direct item-grant issue and can affect TP credits, fluency calculations, and SQLite
history.

Relevant code:

- `apps/minecraft/mods/mathquest/fabric/common/src/main/java/com/kidgames/mathquest/server/QuizResultProcessor.java`
  — `process` and `settleTpCreditSession`
- `apps/minecraft/mods/mathquest/forge/targets/forge-1.20.1/src/main/java/com/kidgames/mathquest/forge/net/MathQuestNetworkForge.java`
  — `QuizResultPacket.handle`
- `apps/minecraft/mods/mathquest/fabric/common/src/main/java/com/kidgames/mathquest/reward/TpCreditCompletionTracker.java`

**Disposition:** Unscheduled follow-up. No solution was selected during this review.

### 3. Teleport precedes durable credit deduction

Fabric and Forge perform the teleport before persisting the credit spend. If persistence
fails, the player remains teleported while the balance is restored, allowing free
teleports while the failure persists.

Relevant code:

- `apps/minecraft/mods/mathquest/fabric/shared/src/main/java/com/kidgames/mathquest/TpCreditCommands.java`
  — `teleportAndSpend`
- `apps/minecraft/mods/mathquest/forge/targets/forge-1.20.1/src/main/java/com/kidgames/mathquest/forge/TpCreditCommandsForge.java`
  — `teleportAndSpend`

**Disposition:** Unscheduled follow-up. No solution was selected during this review.

### 4. Mineflayer dependency advisories

`npm audit --omit=dev` reports eight production-tree vulnerabilities: four high and four
moderate. They are centered on the Microsoft-auth dependency chain and transitive Axios
0.21.4. Offline auth is the default, which limits current exposure, but Microsoft auth
remains supported.

Relevant code:

- `apps/minecraft/mineflayer-forge/package-lock.json`
- `apps/minecraft/mineflayer-forge/src/config.js`

**Disposition:** Unscheduled follow-up. No dependency change was selected during this
review.


## Randy's questions and review decisions

- **Is finding 1 an authorization bug?** Yes. The server currently accepts the client's
  requested item and quantity instead of independently establishing that the request is an
  authorized reward.
- **Is finding 2 the same issue?** No. It is a separate trust boundary: finding 1 concerns
  direct item grants, while finding 2 concerns whether quiz results and completion claims
  are independently verified.
- **Should findings 1–4 be fixed in PR #60?** No. They are documented for later assessment
  so future work can choose scope and solutions deliberately.
- **What happened to finding 5?** The inconsistent Python test fixture was corrected in
  commit `061b72f`; all 152 Python tool tests then passed.
- **How was the branch-map conflict handled?** Commit `58d9889` took
  `origin/main`'s `plans/git/branch-map.md` exactly. GitHub then reported the PR mergeable.
- **Where should the durable record live?** The selected documentation approach is a dated
  review memo, updates to the canonical Overview, and an app-level roadmap. OpenSpec
  onboarding remains a separate future decision.


## Verification

- `cd apps/minecraft/mods/mathquest/fabric && ./gradlew :common:test :targets:fabric-26.1.2:test`
  — build and tests succeeded.
- `./apps/minecraft/mods/build-and-deploy.py mathquest --target forge-1.20.1 --no-deploy`
  — Forge 1.20.1 full build/tests and companion Fabric 26.1.2 build succeeded; nothing
  deployed.
- `./apps/minecraft/mods/build-and-deploy.py mathquest --target fabric-1.21.11 --no-deploy`
  — the preserved Fabric target built successfully; nothing deployed.
- Mineflayer tests with a clean temporary dependency install — 20 of 20 passed.
- `node --test apps/math-quiz/tests/*.test.mjs` — 199 passed, 22 dependency-gated skips,
  and zero failed; the new fluency-feast bridge tests passed 2 of 2.
- `.venv/bin/python3 -m unittest discover -s apps/math-quiz/tools -p 'test_*.py'` — 152 of
  152 passed after the fixture correction.
- `plans/git/branch-map.md` matched `origin/main` byte-for-byte at blob
  `979cda102542f1a99c988c2eaafa5333dcaa330e`.
- GitHub reported PR #60 mergeable at `58d9889`.
- GitHub Actions reported no configured checks for the branch.


## Remaining manual checks

- Optional playtest of `mathquest-*-1.25.4-*.jar` for TP credits, the control panel, and
  Forge gameplay.
- After merge, confirm that `main` contains MathQuest 1.25.4 and that
  `apps/minecraft/mods/AGENTS.md` still describes the nested loader roots.


## Follow-up tracking

The four open findings are mirrored without solutions or priority commitments in
[`ROADMAP.md`](../../ROADMAP.md). The canonical current-state warnings live in
[`OVERVIEW.md`](../OVERVIEW.md#known-limitations--technical-debt). When a finding is
scheduled, its implementation plan or future OpenSpec change should link back to this memo
and PR #60.
