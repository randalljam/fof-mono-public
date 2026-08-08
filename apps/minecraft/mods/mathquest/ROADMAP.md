file: apps/minecraft/mods/mathquest/ROADMAP.md
title: MathQuest — roadmap and vision
last-updated: 2026-07-28_0620


## Vision

MathQuest should remain a dependable, enjoyable family Minecraft math-practice system
across its supported Fabric and Forge targets. New work should preserve the actively used
quiz, reward, control-panel, persistence, and build workflows while improving correctness,
maintainability, and multiplayer trust boundaries deliberately.


## Documentation roles

- [`docs/OVERVIEW.md`](docs/OVERVIEW.md) is the canonical description of current behavior,
  architecture, configuration, and known limitations.
- [`CHANGELOG.md`](CHANGELOG.md) records delivered versions and fixes.
- [`docs/playtest-log.md`](docs/playtest-log.md) records manual Minecraft verification.
- [`docs/reviews/`](docs/reviews/) preserves significant PR and code-review evidence.
- This roadmap holds intended or possible future work that has not yet become current
  behavior.

MathQuest has not opted into OpenSpec. The repo's OpenSpec guide suggests S1 development
for Minecraft mods and treats app stage and spec stage as separate decisions. MathQuest's
formal app and spec stages have not been decided; any stage decision or OpenSpec bootstrap
is separate future work.


## Now / Next / Later

### Now

- Complete the MathQuest 1.25.4 integration through PR
  [#60](https://github.com/FocusOnFoundationsNonprofit/fof-mono/pull/60) without disrupting
  the working family setup.
- Keep Fabric 26.1.2, Fabric 1.21.11, and Forge 1.20.1 build paths healthy.
- Keep the canonical Overview synchronized with observed behavior and known limitations.

### Next

- Triage the unscheduled PR #60 review findings below and decide their scope, priority, and
  implementation approach.
- Preserve the tandem Fabric/Forge rule for any follow-up that touches shared behavior,
  networking, commands, or screens.

### Later

- Reconsider OpenSpec onboarding when a living behavioral contract would reduce more
  duplication than it creates.
- Revisit broader multiplayer hardening before MathQuest is used with untrusted clients or
  users outside the household.


## Review follow-up inbox

These items are intentionally unprioritized. Recording an item here does not select a
solution or authorize implementation.

| ID | Finding | Owning area | Status | Source |
|---|---|---|---|---|
| PR60-1 | Client-provided item IDs and counts can reach server reward grants when TP-credit earning is off. | Fabric + Forge networking/rewards | Unscheduled | [PR #60 review](docs/reviews/2026-07-28_pr-60-code-review.md#1-client-controlled-item-grants) |
| PR60-2 | Quiz results and TP-credit eligibility rely on client-reported completion data. | Shared result processing + loader networking | Unscheduled | [PR #60 review](docs/reviews/2026-07-28_pr-60-code-review.md#2-client-controlled-quiz-completion-data) |
| PR60-3 | A teleport occurs before the credit deduction is durably saved. | Fabric + Forge TP-credit commands | Unscheduled | [PR #60 review](docs/reviews/2026-07-28_pr-60-code-review.md#3-teleport-precedes-durable-credit-deduction) |
| PR60-4 | The Mineflayer Microsoft-auth dependency tree has current high and moderate advisories. | `apps/minecraft/mineflayer-forge` | Unscheduled | [PR #60 review](docs/reviews/2026-07-28_pr-60-code-review.md#4-mineflayer-dependency-advisories) |


## Promotion rule

An inbox item becomes scheduled work only after Randy selects its priority and scope. At
that point, create or use the approved feature branch, define verification before changing
behavior, and link the implementation record back to this roadmap and its source review.
