file: apps/deutsch/content-redo/openspec/specs/app/spec.md
title: Content Redo Specification
last-updated: 2026-07-12_0627
ai: Codex GPT-5.5 via Claude Code (Fable 5, local)
session: Build content tools #3/#4/#5

# Content Redo Specification
Content Redo is a local content transformation app that takes an external article, essay, transcript, or story and produces a more optimistic improved version while preserving structure, grounding every applied change in the Deutsch graph, and exposing a transparent diff. This `app` capability is the S1-dev baseline for use case #4 and runs through the shared `content-tools` harness.


## Workflows
### Workflow: Run from the Web UI
Open the shared content-tools server -> choose the Redo page -> paste content or select a sample -> choose tone, degree, and reading level -> run -> inspect original-vs-rewritten turns, additions, why lines, citation links, downloads, and saved runs.
Exercises requirements: Shared Harness Integration, Local Server and Session Security, Redo Pipeline, Degree-Gated Change Classes, Reading-Level Behavior, Markdown and Sidecar Output, Saved Runs

### Workflow: Run from the CLI
Call `run_redo.py process <input-file>` with tone, degree, and reading-level knobs -> write rewritten markdown, change-list markdown, and JSON sidecar to gitignored output -> print summary counts.
Exercises requirements: CLI Entry Points, Redo Pipeline, Provenance and Disclosure, Markdown and Sidecar Output

### Workflow: Verify Readiness
Run `run_redo.py selftest` or `content-tools/run_tools.py selftest` -> load the committed Deutsch graph -> report corpus, installed tool, degree, reading-level, and API-key readiness.
Exercises requirements: CLI Entry Points, Shared Harness Integration


## Requirements
### Requirement: Shared Harness Integration
The system SHALL plug into `apps/deutsch/content-tools/` through the generic tool registry and `run_from_request(payload, state)`.

#### Scenario: Tool is discovered
- **WHEN** `ctools.config.tool_available("redo")` runs
- **THEN** it returns true only when `apps/deutsch/content-redo/` and `dredo/engine.py` exist.

#### Scenario: Engine import is lazy
- **WHEN** the content-tools server starts
- **THEN** it loads graph state but does not import `dredo.engine` until `POST /api/redo/run` is called.

### Requirement: Local Server and Session Security
The system SHALL use the shared localhost-only server and require a per-run token for API access.

#### Scenario: API requires token
- **WHEN** any `/api/` path is requested without `X-CT-Token`
- **THEN** the server responds 401 and does not process the request.

#### Scenario: Page receives token
- **WHEN** `GET /redo` is requested for an installed tool
- **THEN** the served hand-authored page has `__CT_TOKEN__` replaced by the session token.

### Requirement: Redo Pipeline
The system SHALL parse external content, extract claims, judge divergence using shared dgraph services, generate a sanitized rewrite plan, perform constrained rewrites, and render output.

#### Scenario: Shared front half is reused
- **WHEN** a run receives source text
- **THEN** `dgraph.claims.parse_content`, `dgraph.claims.segment_claims`, and `dgraph.divergence.detect` are used in order, with no local reimplementation of parsing, routing, judging, or grounding.

#### Scenario: Plan is generated before rewrite
- **WHEN** claims have been judged
- **THEN** the app makes one structured rewrite-plan LLM call before any rewrite batch and records kept and dropped plan rows.

### Requirement: Degree-Gated Change Classes
The system SHALL enforce remix degree after the LLM proposes a plan.

#### Scenario: Degree 1 allows corrections only
- **WHEN** degree is `1`
- **THEN** only `correct` changes are kept and `reframe` or `add` plan rows are dropped with reasons.

#### Scenario: Degree 2 allows corrections and reframes
- **WHEN** degree is `2`
- **THEN** `correct` and `reframe` changes are kept and `add` plan rows are dropped with reasons.

#### Scenario: Degree 3 allows marked additions
- **WHEN** degree is `3`
- **THEN** `add` changes may be applied as new paragraphs marked `[added]` after their target turn.

### Requirement: No-Position Honesty
The system SHALL not treat claims Deutsch never addressed as corrections.

#### Scenario: Correct changes require divergence
- **WHEN** a `correct` plan row references no `diverge` claim
- **THEN** the row is dropped and is not rewritten.

#### Scenario: No-position claim is not corrected
- **WHEN** the detector returns `no-position` for a claim
- **THEN** the app may retain that claim in the sidecar but SHALL NOT apply a `correct` change grounded only in that claim.

### Requirement: Citation Grounding
The system SHALL ensure every applied change carries citations resolving in the graph.

#### Scenario: Outside citation is filtered
- **WHEN** the model proposes a citation id not present in the referenced claims' grounding
- **THEN** that citation is omitted from the kept plan row and sidecar.

#### Scenario: Uncited change is dropped
- **WHEN** a plan row has no grounded citations after filtering and fallback to the referenced claim citations
- **THEN** the plan row is dropped and no change is applied.

#### Scenario: Applied change carries citation details
- **WHEN** a change is applied
- **THEN** its sidecar row includes citation ids and renderable citation details from the graph citation index.

### Requirement: Unchanged-Text Verbatim Passthrough
The system SHALL copy unchanged turns byte-identically from parsed source turns.

#### Scenario: Unplanned turn is untouched
- **WHEN** a turn has no kept `correct` or `reframe` plan row
- **THEN** its `rewritten_text` in the diff equals its original parsed turn text exactly.

#### Scenario: Add-only turn keeps original text
- **WHEN** a turn only receives `add` changes
- **THEN** the original turn text is copied exactly and the added paragraph is represented separately.

### Requirement: Length Guard
The system SHALL keep each rewritten turn within approximately +/-40% of the original length.

#### Scenario: Overlong rewrite retries once
- **WHEN** a generated rewrite exceeds the allowed word-count bounds
- **THEN** the app retries once with an explicit length instruction.

#### Scenario: Failed retry keeps original
- **WHEN** the retry still exceeds the allowed bounds
- **THEN** the app keeps the original turn and records a skipped note.

### Requirement: Reading-Level Behavior
The system SHALL pass reading-level instructions into rewrite prompts.

#### Scenario: Adult preserves register
- **WHEN** reading level is `adult`
- **THEN** the rewrite prompt instructs the model to preserve the source register.

#### Scenario: Young shortens and defines
- **WHEN** reading level is `young`
- **THEN** the rewrite prompt instructs the model to use shorter sentences and define hard terms inline.

#### Scenario: Child uses BOI concepts
- **WHEN** reading level is `child` and BOI concept nodes are present in claim grounding
- **THEN** the rewrite prompt includes two or three concept definitions and asks for kid-friendly inline definitions.

### Requirement: Provenance and Disclosure
The system SHALL include provenance metadata and a fixed private-education disclosure on every output.

#### Scenario: Rewritten markdown has provenance
- **WHEN** markdown is rendered
- **THEN** it includes source name, tool, tone, degree, reading level, model, and generated timestamp.

#### Scenario: Disclosure is present
- **WHEN** rewritten markdown or change-list markdown is rendered
- **THEN** it includes `AI-TRANSFORMATION: This is an AI transformation of the named source for private educational use; every change is listed with its grounding.`

### Requirement: Markdown and Sidecar Output
The system SHALL return rewritten markdown, change-list markdown, and a JSON sidecar for every successful run.

#### Scenario: Diff data is complete
- **WHEN** output is rendered
- **THEN** the sidecar includes turns, claims, plan audit rows, per-turn diff data, applied changes, skipped notes, provenance, knobs, and disclosure.

#### Scenario: UI can render without recomputing
- **WHEN** the UI receives a run result
- **THEN** it can render original-vs-rewritten turns, additions, why lines, and citation links from the returned diff and change data alone.

### Requirement: Saved Runs
The system SHALL persist server runs through the shared run store.

#### Scenario: Run is saved with deterministic id
- **WHEN** `POST /api/redo/run` completes
- **THEN** the result is written under `apps/deutsch/content-redo/data/runs/` with a `run-0001-<slug>` style id derived from existing files.

#### Scenario: Runs round-trip
- **WHEN** a saved run is listed and loaded through `/api/redo/runs`
- **THEN** the JSON file is returned without rerunning the engine.

### Requirement: CLI Entry Points
The system SHALL provide `process`, `selftest`, and `serve` commands.

#### Scenario: Process writes files
- **WHEN** `run_redo.py process <input-file>` runs
- **THEN** it writes `<stem>_redo.md`, `<stem>_redo_changes.md`, and `<stem>_redo.json` under the requested output directory or gitignored `data/out/`, and prints summary counts.

#### Scenario: Selftest reports readiness
- **WHEN** `run_redo.py selftest` runs
- **THEN** it prints graph node counts, corpus availability, content-tools installation status, remix degrees, reading levels, and API-key presence.
