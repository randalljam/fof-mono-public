file: skills/openspec/opsx-propose/README.md
title: OPSX propose — create a change and planning artifacts
source-github-url: https://github.com/Fission-AI/OpenSpec
source-guide-url: https://github.com/Fission-AI/OpenSpec/blob/main/docs/commands.md#opsxpropose
history:
  - 2026-07-09 · Randy · Cursor [OpenSpec skills implementation](openspec-skills) — initial skill


**Use this skill when you know what to build and need a structured change folder before writing code.** Propose creates `openspec/changes/<change-name>/` with planning artifacts: `proposal.md`, delta `specs/`, `design.md`, and `tasks.md`. The change is ready for implementation when all apply-required artifacts exist.

Upstream equivalent: `/opsx:propose [change-name-or-description]`.


## When to use
- A feature, fix, or refactor on an opted-in app needs reviewable intent before code.
- Explore (or the user) has settled on scope and approach.
- You want a durable record the next agent (or human) can read without replaying chat history.

## When to skip
- Trivial changes that do not warrant ceremony (typo, comment, one-line config).
- The app has not opted in — use `docs/` or direct implementation instead.
- A change folder for this work already exists — use `opsx-apply` or `opsx-update` (expanded profile) instead.


## Prerequisites
- OpenSpec store at `apps/<app>/openspec/` (initialized with `core` profile).
- Kebab-case change name agreed with the user (e.g. `add-session-export`, `fix-mastery-threshold`).
- Working from repo root or `apps/<app>`; CLI commands run against the app directory.


## The propose procedure
### 1. Confirm scope with the user
State in plain language:
- **What** is changing and **why**
- **Non-goals** (what this change deliberately does not touch)
- **Rigor level**: lite vs full (see below)
- Proposed change name (`kebab-case`)

Wait for approval before creating files.

### 2. Create the change folder
Under `apps/<app>/openspec/changes/<change-name>/`, create artifacts in dependency order (default `spec-driven` schema):
```text
proposal.md          # why, what's changing, impact
specs/<domain>/spec.md   # delta spec (ADDED / MODIFIED / REMOVED)
design.md            # technical approach, decisions, risks
tasks.md             # implementation checklist
```
Optional metadata: `.openspec.yaml` (schema, created date) if using expanded workflow commands.

You may use `openspec new change <name>` (CLI) to scaffold, then fill artifacts — or create files directly following OpenSpec templates. Check status:
```bash
cd apps/<app> && openspec status --change <change-name>
```

### 3. Write artifacts (progressive rigor)
**Lite** (small work, internal behavior tweaks):
- Short `proposal.md` (problem, approach, non-goals).
- Compact delta spec — behavior-first, minimal scenarios.
- Brief `design.md` only if non-obvious.
- `tasks.md` with checkbox items sized for one session each.

**Full** (API contracts, migrations, security, cross-module refactors):
- Detailed `proposal.md` with impact and rollback notes.
- Delta specs with requirements and **Given/When/Then** scenarios per requirement.
- `design.md` with decisions, alternatives considered, and test strategy.
- Granular `tasks.md` grouped by phase.

Delta spec format (the signature brownfield move):
```markdown
## ADDED Requirements
### Requirement: Theme Selection
...

## MODIFIED Requirements
...

## REMOVED Requirements
...
```
Never edit `openspec/specs/` directly during propose — only the change's delta specs.

### 4. Validate and hand off
```bash
cd apps/<app> && openspec validate --change <change-name> --strict
```
Report artifact checklist to the user. When complete, transition to [`skills/openspec/opsx-apply/README.md`](../opsx-apply/README.md).


## Guardrails
- Opt-in only: do not propose changes for apps without `apps/<app>/openspec/`.
- Confirm scope before writing — state extracted intent in plain language.
- Use descriptive change names; avoid `update`, `changes`, `wip`.
- Populate `apps/<app>/openspec/config.yaml` `context:` when agents repeatedly miss stack/conventions.


## Related
- [`skills/openspec/opsx-explore/README.md`](../opsx-explore/README.md) — prior step when requirements were unclear.
- [`skills/openspec/opsx-apply/README.md`](../opsx-apply/README.md) — next step after propose is complete.
- [`skills/openspec/README.md`](../README.md) — opt-in procedure, lifecycle.
- Upstream: [commands — propose](https://github.com/Fission-AI/OpenSpec/blob/main/docs/commands.md#opsxpropose).
