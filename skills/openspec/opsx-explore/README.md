file: skills/openspec/opsx-explore/README.md
title: OPSX explore — think before you propose
source-github-url: https://github.com/Fission-AI/OpenSpec
source-guide-url: https://github.com/Fission-AI/OpenSpec/blob/main/docs/explore.md
history:
  - 2026-07-09 · Randy · Cursor [OpenSpec skills implementation](openspec-skills) — initial skill


**Use this skill when requirements are fuzzy, you need to compare approaches, or you want to investigate the codebase before committing to a change.** Explore is a no-stakes thinking partner: it reads code and existing specs, weighs options, and shapes a plan. **It creates no OpenSpec artifacts.**

Upstream equivalent: `/opsx:explore [topic]` (Cursor: read this skill or `/opsx-explore` if wrappers exist).


## When to use
- You are unsure *what* to build or *how* to approach it.
- A feature touches multiple modules and you need to map the landscape first.
- You want to compare tradeoffs (e.g. JWT vs sessions, lite vs full spec rigor).
- You are onboarding to an opted-in app and want to read `openspec/specs/` plus the code together.

## When to skip
- The change is obvious and small (typo, one-line fix, config tweak) — go straight to implementation or a lite propose.
- A change folder already exists — use `opsx-apply` or `opsx-propose` instead.
- The app has not opted into OpenSpec — do not scaffold `openspec/`; explore in chat or a `docs/` doc instead.


## Prerequisites
- The target app has an OpenSpec store: `apps/<app>/openspec/` (see [`skills/openspec/README.md`](../README.md) → Opt in an app).
- You know which app you are exploring.


## The explore procedure
### 1. Orient
- Read `apps/<app>/openspec/specs/` if any specs exist (current behavior baseline).
- Read `apps/<app>/AGENTS.md` and `apps/<app>/README.md` for app conventions.
- Skim the relevant source files for the topic at hand.

### 2. Investigate
- Answer the user's question or topic with evidence from the codebase.
- Compare 2–3 viable approaches with tradeoffs (complexity, risk, fit with existing patterns).
- Call out dependencies, test implications, and what would change in the spec if each approach wins.
- Use diagrams when they clarify architecture or data flow.

### 3. Converge
- Summarize the recommended direction in plain language.
- State scope: what is in, what is out (non-goals).
- Suggest spec rigor: **lite** (short behavior-first) vs **full** (requirements + Given/When/Then scenarios for API/contract/migration/security work).
- **Do not create** `openspec/changes/` folders or any artifacts during explore.

### 4. Hand off
When the user approves the direction, transition to [`skills/openspec/opsx-propose/README.md`](../opsx-propose/README.md):
```text
Ready to propose. Suggested change name: <kebab-case-name>
```


## Guardrails
- Opt-in only: never run `openspec init` or create change folders without explicit user approval for that app.
- Explore is read-only with respect to OpenSpec artifacts — no `proposal.md`, no delta specs, no `tasks.md`.
- If exploration reveals the app should opt in first, say so and stop; point to the hub README opt-in procedure.


## Related
- [`skills/openspec/opsx-propose/README.md`](../opsx-propose/README.md) — next step after explore crystallizes.
- [`skills/openspec/README.md`](../README.md) — lifecycle, decisions, CLI setup.
- Upstream: [Explore guide](https://github.com/Fission-AI/OpenSpec/blob/main/docs/explore.md).
