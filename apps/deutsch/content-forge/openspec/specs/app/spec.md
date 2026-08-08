file: apps/deutsch/content-forge/openspec/specs/app/spec.md
title: Content Forge Specification
last-updated: 2026-07-12_0625
ai: Codex GPT-5.5 via Claude Code (Fable 5, local)
session: Build content tools #3/#4/#5

# Content Forge Specification


## Purpose
Content Forge is a local content generation app that creates new text pieces from a user description while grounding the generation in a selected deutsch-graph subgraph. This `app` capability is the S1-dev baseline for use case #5 and runs through the shared `content-tools` harness.


## Workflows
### Workflow: Run from the Web UI
Open the shared content-tools server -> choose the Forge page -> enter a description -> choose format, length, and tone -> run -> inspect the generated piece, citation links, per-section grounding table, retrieved-but-uncited context, downloads, and saved runs.
Exercises requirements: Shared Harness Integration, Graph-Conditioned Generation, Format Length and Tone Knobs, Inline Citation Validation, Per-Section Grounding Sidecar, Markdown and Sidecar Output

### Workflow: Run from the CLI
Call `run_forge.py create "<description>"` with format, length, tone, and output directory knobs -> write document markdown, sidecar markdown, and sidecar JSON to gitignored output -> print coverage counts.
Exercises requirements: CLI Entry Points, Graph-Conditioned Generation, Markdown and Sidecar Output

### Workflow: Review Grounding Quality
Open a run sidecar -> compare routed topics/categories, retrieved context nodes, section citation rows, invalid citation records, and ungrounded-section flags -> decide whether the draft is reviewable or should be rerun with a narrower description.
Exercises requirements: Context Package Manifest, Inline Citation Validation, Per-Section Grounding Sidecar, Honest Gap Behavior


## Requirements
### Requirement: Shared Harness Integration
The system SHALL plug into `apps/deutsch/content-tools/` through the generic tool registry and `run_from_request(payload, state)`.

#### Scenario: Tool is discovered
- **WHEN** `ctools.config.tool_available("forge")` runs
- **THEN** it returns true only when `apps/deutsch/content-forge/` and `dforge/engine.py` exist.

#### Scenario: Engine import is lazy
- **WHEN** the content-tools server starts
- **THEN** it loads graph state but does not import `dforge.engine` until `POST /api/forge/run` is called.

### Requirement: Graph-Conditioned Generation
The system SHALL build generation context from routed deutsch-graph nodes rather than asking the model to rely on memory.

#### Scenario: Context package is built from routed graph labels
- **WHEN** a description is submitted
- **THEN** the engine routes it to graph topics, categories, and concept needles, calls `dgraph.grounding.build_grounding`, and sends the resulting SOURCE blocks to the generation call.

#### Scenario: Context package is recorded in the sidecar
- **WHEN** a run completes
- **THEN** the JSON sidecar contains a context-package manifest listing the retrieved node ids, node metadata, counts, corpus availability, and retrieved-but-uncited nodes.

### Requirement: Routing Fallback
The system SHALL widen routing locally when the shared claim router under-selects topics for a generation task.

#### Scenario: Shared router is tried first
- **WHEN** a description is routed
- **THEN** the engine passes it to `dgraph.divergence.route_claims` as one claim-like item.

#### Scenario: Wider routing call is capped
- **WHEN** the shared router returns fewer than four topics
- **THEN** the engine makes at most one additional routing call asking for up to eight topics, two categories, and three concept needles using exact catalog labels.

### Requirement: Format Length and Tone Knobs
The system SHALL support essay, lesson, and dialogue formats; short, medium, and long length targets; and the shared content-tools tone levels.

#### Scenario: Defaults apply
- **WHEN** no format, length, or tone is supplied
- **THEN** the run uses essay, medium, and the shared default tone.

#### Scenario: Format template reaches the prompt
- **WHEN** format is `lesson`
- **THEN** the generation prompt asks for objectives, explanation, examples, and questions-to-explore.
- **WHEN** format is `dialogue`
- **THEN** the generation prompt asks for two named fictional speakers and forbids labeling a speaker as David Deutsch.

#### Scenario: Length retry is soft
- **WHEN** the first draft is more than 1.6x the selected target
- **THEN** the engine retries once with an explicit length instruction and records a sidecar note.

### Requirement: Inline Citation Validation
The system SHALL validate generated inline citations against the graph citation index and strip invalid citations from the document.

#### Scenario: Valid citation resolves
- **WHEN** a section cites a graph node id such as `[qa:...:000]`
- **THEN** the sidecar resolves it to label, work where available, and `youtube_ts_url` where present.

#### Scenario: Unknown citation is stripped and reported
- **WHEN** generated text cites an id not present in the graph citation index
- **THEN** that citation marker is removed from the markdown output and listed in `invalid_citations` in the JSON sidecar.

### Requirement: Per-Section Grounding Sidecar
The system SHALL split generated content on `##` headings and report grounding status for every section.

#### Scenario: Grounded section is marked
- **WHEN** a section contains at least one valid graph citation
- **THEN** the sidecar marks it `grounded: true` and lists its resolved citations.

#### Scenario: Ungrounded section is surfaced
- **WHEN** a section contains zero valid graph citations
- **THEN** the sidecar marks it `grounded: false`, includes it in ungrounded coverage counts, and the UI displays an ungrounded badge.

### Requirement: Markdown and Sidecar Output
The system SHALL return document markdown, sidecar markdown, and sidecar JSON for every successful run.

#### Scenario: Provenance header is present
- **WHEN** document markdown is rendered
- **THEN** it includes description, tool, format, length, tone, model, and generated-at fields.

#### Scenario: Disclosure is present
- **WHEN** document markdown is rendered
- **THEN** it includes `AI-GENERATED: This piece was generated from cited deutsch-graph sources; it was not written or endorsed by David Deutsch.`

#### Scenario: Coverage stats are present
- **WHEN** sidecar JSON is rendered
- **THEN** it includes section count, grounded count, ungrounded count, citation count, and invalid citation count.

### Requirement: Honest Gap Behavior
The system SHALL instruct generation to acknowledge uncovered requested aspects rather than invent Deutsch positions.

#### Scenario: Sources do not cover a requested aspect
- **WHEN** the selected SOURCE blocks do not support part of the description
- **THEN** the generation prompt requires the piece to say that the selected graph sources do not cover it.

#### Scenario: Gap statement is still section-audited
- **WHEN** a gap statement appears in its own section without a valid citation
- **THEN** the sidecar flags that section as ungrounded so a reviewer can decide whether the gap statement is acceptable.

### Requirement: CLI Entry Points
The system SHALL provide `create`, `selftest`, and `serve` commands.

#### Scenario: Create writes files
- **WHEN** `run_forge.py create "<description>"` runs
- **THEN** it writes `_forge.md`, `_citations.md`, and `_citations.json` files under the requested output directory or gitignored `data/out/`, and prints coverage counts.

#### Scenario: Selftest reports readiness
- **WHEN** `run_forge.py selftest` runs
- **THEN** it prints graph node counts, corpus availability, content-tools installation status, formats, lengths, tones, and API-key presence.
