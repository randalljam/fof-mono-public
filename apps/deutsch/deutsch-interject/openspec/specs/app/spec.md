file: apps/deutsch/deutsch-interject/openspec/specs/app/spec.md
title: Deutsch Interjector Specification
last-updated: 2026-07-12_0610
ai: Codex GPT-5.5 via Claude Code (Fable 5, local)
session: Build content tools #3/#4/#5

# Deutsch Interjector Specification


## Purpose
Deutsch Interjector is a local content annotation app that takes an external transcript or article and inserts clearly labeled virtual Deutsch turns where the source speakers' claims diverge from David Deutsch's recorded positions in the Deutsch graph. This `app` capability is the S1-dev baseline for use case #3 and runs through the shared `content-tools` harness.


## Workflows
### Workflow: Run from the Web UI
Open the shared content-tools server -> choose the Interjector page -> paste content or select a sample -> choose tone, fidelity, and whether agreements are included -> run -> inspect the annotated transcript, claims sidecar, citation links, downloads, and saved runs.
Exercises requirements: Shared Harness Integration, Local Server and Session Security, Interjection Pipeline, Fidelity Modes, Synthetic Labeling, No-Position Honesty, Saved Runs

### Workflow: Run from the CLI
Call `run_interject.py process <input-file>` with tone and fidelity knobs -> write annotated markdown and JSON sidecar to gitignored output -> print summary counts.
Exercises requirements: CLI Entry Points, Interjection Pipeline, Markdown and Sidecar Output

### Workflow: Verify Readiness
Run `run_interject.py selftest` or `content-tools/run_tools.py selftest` -> load the committed Deutsch graph -> report corpus, installed tool, fidelity, and API-key readiness.
Exercises requirements: CLI Entry Points, Shared Harness Integration


## Requirements
### Requirement: Shared Harness Integration
The system SHALL plug into `apps/deutsch/content-tools/` through the generic tool registry and `run_from_request(payload, state)`.

#### Scenario: Tool is discovered
- **WHEN** `ctools.config.tool_available("interject")` runs
- **THEN** it returns true only when `apps/deutsch/deutsch-interject/` and `dinterject/engine.py` exist.

#### Scenario: Engine import is lazy
- **WHEN** the content-tools server starts
- **THEN** it loads graph state but does not import `dinterject.engine` until `POST /api/interject/run` is called.

### Requirement: Local Server and Session Security
The system SHALL use the shared localhost-only server and require a per-run token for API access.

#### Scenario: API requires token
- **WHEN** any `/api/` path is requested without `X-CT-Token`
- **THEN** the server responds 401 and does not process the request.

#### Scenario: Page receives token
- **WHEN** `GET /interject` is requested for an installed tool
- **THEN** the served hand-authored page has `__CT_TOKEN__` replaced by the session token.

### Requirement: Interjection Pipeline
The system SHALL parse external content, extract claims, judge divergence using shared dgraph services, generate interjections, and render output.

#### Scenario: Claims are extracted and judged
- **WHEN** a run receives source text
- **THEN** `dgraph.claims.parse_content`, `dgraph.claims.segment_claims`, and `dgraph.divergence.detect` are used in order, with no local reimplementation of parsing, routing, judging, or grounding.

#### Scenario: Divergent claims are interjected
- **WHEN** a claim's verdict is `diverge`
- **THEN** a virtual Deutsch interjection may be generated and inserted after the source turn that contained the claim.

#### Scenario: Agreements are optional
- **WHEN** `include_agreements` is false
- **THEN** `agree` claims are not interjected.
- **WHEN** `include_agreements` is true
- **THEN** `agree` claims may receive brief compatibility interjections.

### Requirement: Fidelity Modes
The system SHALL support `quote`, `paraphrase`, and `voice` fidelity modes, defaulting to `quote`.

#### Scenario: Quote mode is default
- **WHEN** no fidelity is supplied
- **THEN** the run uses `quote` mode.

#### Scenario: Unsupported fidelity is normalized
- **WHEN** an unsupported fidelity value is supplied
- **THEN** the run falls back to `quote`.

### Requirement: Quote-Mode Verbatim Verification
The system SHALL verify long double-quoted spans in quote mode against the claim's grounding text.

#### Scenario: Verbatim quote passes
- **WHEN** a quote-mode interjection contains a double-quoted span of eight or more words that appears verbatim after whitespace normalization in the claim grounding
- **THEN** the interjection is kept.

#### Scenario: Fabricated quote is removed
- **WHEN** a quote-mode interjection contains a double-quoted span of eight or more words that does not appear in the claim grounding
- **THEN** the system regenerates the interjection once without the fake quote or drops it and records the reason in the sidecar notes.

### Requirement: Citation Filtering
The system SHALL filter generated citation ids to the grounding ids available for that claim.

#### Scenario: Outside citation is dropped
- **WHEN** the generated interjection cites a node id not present in that claim's grounding
- **THEN** that citation is omitted from the returned interjection and sidecar.

### Requirement: Synthetic Labeling
The system SHALL clearly label all virtual turns and disclose that they are AI-generated.

#### Scenario: Virtual speaker label is present
- **WHEN** markdown is rendered
- **THEN** every inserted block begins with `David Deutsch (virtual)`.

#### Scenario: Disclosure is present
- **WHEN** markdown is rendered
- **THEN** the provenance header includes `SYNTHETIC-CONTENT: The virtual-Deutsch turns are AI-generated, not spoken or endorsed by David Deutsch; quotes are verbatim-cited where marked.`

### Requirement: No-Position Honesty
The system SHALL never interject on claims where the shared detector returns `no-position`.

#### Scenario: No-position claim is skipped
- **WHEN** a claim has verdict `no-position`
- **THEN** no virtual Deutsch turn is inserted for it.

#### Scenario: No-position claim is listed
- **WHEN** a claim has verdict `no-position`
- **THEN** the JSON sidecar lists it as skipped with the reason that Deutsch has no recorded position in the routed grounding.

### Requirement: Markdown and Sidecar Output
The system SHALL return annotated markdown and a JSON sidecar for every successful run.

#### Scenario: Markdown preserves source order
- **WHEN** output is rendered
- **THEN** original turns appear in order and interjections appear immediately after the turn their claim came from.

#### Scenario: Sidecar includes audit data
- **WHEN** output is rendered
- **THEN** the sidecar includes provenance, knobs, turns, claims with verdicts and citations, interjections, skipped rows, notes, and the synthetic-content disclosure.

### Requirement: Saved Runs
The system SHALL persist server runs through the shared run store.

#### Scenario: Run is saved with deterministic id
- **WHEN** `POST /api/interject/run` completes
- **THEN** the result is written under `apps/deutsch/deutsch-interject/data/runs/` with a `run-0001-<slug>` style id derived from existing files.

#### Scenario: Runs round-trip
- **WHEN** a saved run is listed, loaded, and deleted through `/api/interject/runs`
- **THEN** the JSON file is returned and then removed without affecting other runs.

### Requirement: CLI Entry Points
The system SHALL provide `process`, `selftest`, and `serve` commands.

#### Scenario: Process writes files
- **WHEN** `run_interject.py process <input-file>` runs
- **THEN** it writes `<stem>_interjected.md` and `<stem>_interjected.json` under the requested output directory or gitignored `data/out/`, and prints summary counts.

#### Scenario: Selftest reports readiness
- **WHEN** `run_interject.py selftest` runs
- **THEN** it prints graph node counts, corpus availability, content-tools installation status, fidelity modes, and API-key presence.
