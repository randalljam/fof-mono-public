file: skills/openspec/opsx-bootstrap/README.md
title: OPSX bootstrap — baseline an existing app into OpenSpec
source-github-url: https://github.com/Fission-AI/OpenSpec
source-guide-url: https://github.com/Fission-AI/OpenSpec/blob/main/docs/examples.md
history:
  - 2026-07-10 · Randy · Claude Code (Fable 5) `OpenSpec skills revision + interactive guide` — stage model split into app stage (S0–S3) + spec stage (readme-only…openspec-strict) + tags; registry step updated
  - 2026-07-10 · Randy · Claude Code (Fable 5) `OpenSpec skills revision + interactive guide` — initial bootstrap skill: staged onboarding, workflow-first baseline spec, roadmap companion


**Use this skill to onboard an existing app into OpenSpec in one pass** — from "no spec at all" to a validated, readable baseline of current behavior plus a roadmap companion. This is the repeatable version of the ad-hoc baseline done for autolearner on 2026-07-10; it exists because most apps in this repo pre-date any spec tracking and need a cheap, consistent on-ramp.

No upstream equivalent — this is a repo-authored composite of `init` + explore + a baseline propose/archive cycle. Closest upstream reference: the baseline pattern in [OpenSpec examples](https://github.com/Fission-AI/OpenSpec/blob/main/docs/examples.md).


## When to use
- An app has real behavior worth contracting but no OpenSpec store, or an empty one.
- The user wants a readable "what does this app do today" document that agents will keep current.
- Onboarding several apps consistently (run once per app).

## When to skip
- The app is at stage S0 · experiment / spec stage `readme-only` (see the guide at `skills/openspec/docs/2026-07-10_openspec-guide/index.html`). A README "What it does" + "Roadmap" section is enough; revisit when the app stabilizes.
- The app already has living specs — use `opsx-propose` for new work instead.


## Prerequisites
- OpenSpec CLI installed globally (`openspec --version`; see `skills/openspec/README.md`).
- User approval for the app being onboarded, its app stage (S0 experiment / S1 dev / S2 deployed / S3 real), and its spec stage (normally `openspec-single-spec` at bootstrap).
- Work on the app's feature branch, never `main` directly.


## The bootstrap procedure
### 1. Confirm scope and stage with the user
State: which app, its stage on the adoption ladder, and the capability name for the baseline (default `app` — one capability for the whole application at S1/S2; split into narrower capabilities only at S3 or when the file grows too large).

### 2. Init the store (if missing)
```bash
openspec init apps/<app> --tools none --profile core
cd apps/<app> && openspec list && openspec validate --all; cd -
```
Fill `apps/<app>/openspec/config.yaml` `context:` with the app's stack, stage, and any shared profile/template references so agents inherit the right assumptions.

### 3. Explore current behavior
Per `opsx-explore`: read the app README, AGENTS.md, tests, and main modules. Identify the **user workflows** (the journeys a user actually takes) before listing requirements — the workflows organize the spec.

### 4. Author the workflow-first baseline spec
Create the baseline through a change so there is an audit trail:
```text
apps/<app>/openspec/changes/baseline-current-behavior/specs/<capability>/spec.md   # ## ADDED Requirements
```
The resulting living spec (after archive) uses the **workflow-first format**:
```markdown
# <App> Specification

## Purpose
Two–four sentences: what the app is and who it serves.

## Workflows
### Workflow: <User journey name>
One-line narrative of the journey (arrow chain is fine here).
Exercises requirements: <Requirement Name>, <Requirement Name>, ...

## Requirements
### Requirement: <Name>
The system SHALL ...
#### Scenario: ...
```
The `## Workflows` section is the readability layer — every requirement must appear in at least one workflow, so a human can fold the file to Workflows and understand what the app does and which requirements serve each journey. Verified 2026-07-10: `openspec validate --all --strict` accepts the extra section.

Baseline requirements describe **current behavior only** — no aspirations, no roadmap items.

### 5. Scaffold the roadmap companion
Create `apps/<app>/ROADMAP.md` (outside the OpenSpec store — intended-but-unbuilt behavior never goes in the living spec):
```markdown
file: apps/<app>/ROADMAP.md
title: <App> — roadmap and vision

## Vision
Where this app is ultimately going.

## Now / Next / Later
- **Now** — ...
- **Next** — ...
- **Later** — ...

## Idea inbox
Dated bullets captured from voice memos / sessions; graduate items upward, then into an OpenSpec change via `opsx-propose`.
```
Seed it from the app README, `docs/` planning docs, and anything the user dictates.

### 6. Validate and archive
```bash
cd apps/<app> && openspec validate --all --strict && openspec archive baseline-current-behavior
```
Confirm the living spec landed at `apps/<app>/openspec/specs/<capability>/spec.md` and validates.

### 7. Register (when available)
If the holodeck registry exists on the current branch (`apps/holodeck/registry.yaml`), add/update the app entry's `stage:` (S0–S3), `spec_stage:` (`readme-only` / `openspec-single-spec` / `openspec-core` / `openspec-strict`), and `tags:`. Tag vocabulary is provisional and user-iterated — don't invent new tags without flagging them. Otherwise note stage + spec stage in the app README header.


## Guardrails
- One capability at S1/S2; do not invent domain splits the app hasn't earned.
- Baseline = observed behavior. If code and docs disagree, the code wins; flag the discrepancy to the user.
- Do not run bootstrap repo-wide in one session — one app per approval.
- Commit as `docs(<app>): bootstrap OpenSpec baseline spec + roadmap` (plus a separate `chore(<app>): initialize OpenSpec store` if init ran).


## Related
- [`skills/openspec/README.md`](../README.md) — lifecycle, terminology, opt-in.
- [`skills/openspec/opsx-explore/README.md`](../opsx-explore/README.md) — the exploration step this skill embeds.
- [`skills/openspec/opsx-propose/README.md`](../opsx-propose/README.md) — for feature work after the baseline exists.
- `skills/openspec/docs/2026-07-10_openspec-guide/index.html` — interactive guide: app/spec stages + tags model, workflow-first format, roadmap companions.
