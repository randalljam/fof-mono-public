file: apps/deutsch/content-forge/openspec/changes/archive/2026-07-12-initial-build/proposal.md
title: Initial Build — Content Forge
last-updated: 2026-07-12_0625
ai: Codex GPT-5.5 via Claude Code (Fable 5, local)
session: Build content tools #3/#4/#5

# Initial Build — Content Forge


## Why
Use case #5 from `apps/deutsch/deutsch-graph/docs/use-cases.md` needs a local prototype that can create new text content from a description while grounding the generation in deutsch-graph sources and producing a section-by-section citations sidecar. The sidecar is the quality-control differentiator: it makes review cheap and separates this from generic "write like Deutsch" prompting.


## What Changes
- Create `apps/deutsch/content-forge/` with CLI, engine package, renderer, hand-authored web UI, README, and OpenSpec baseline.
- Reuse `dgraph.divergence.route_claims`, `dgraph.grounding.build_grounding`, `dgraph.grounding.citation_index`, and `dgraph.llm_util`.
- Implement essay, lesson, and dialogue formats; short, medium, and long length targets; and the shared content-tools tone knob.
- Implement a local routing wrapper that tries the shared claim router first and makes one wider routing call when the topic set is too narrow for content generation.
- Generate one graph-conditioned markdown piece from SOURCE blocks and validate citations in pure post-processing.
- Emit document markdown, human-readable sidecar markdown, and JSON sidecar with per-section grounded flags, invalid citation records, coverage stats, and context-package manifest.


## Non-Goals
- No audio, video, or interactive-website export in v1.
- No multi-piece curriculum planner.
- No deployment, accounts, or shared backend database.
- No changes to `dgraph`, `content-tools`, `deutsch-interject`, `content-redo`, or `worldview-mirror` source.
