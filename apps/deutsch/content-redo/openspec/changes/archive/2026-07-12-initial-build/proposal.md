file: apps/deutsch/content-redo/openspec/changes/archive/2026-07-12-initial-build/proposal.md
title: Initial Build - Content Redo
last-updated: 2026-07-12_0627
ai: Codex GPT-5.5 via Claude Code (Fable 5, local)
session: Build content tools #3/#4/#5

# Initial Build - Content Redo
Build the initial local prototype for use case #4.


## Why
Use case #4 from `apps/deutsch/deutsch-graph/docs/use-cases.md` needs a defensible local prototype that can take existing content, reuse the shared divergence detector, and produce a more optimistic improved version with transparent graph-cited changes rather than an opaque propaganda-grade rewrite.


## What Changes
- Create `apps/deutsch/content-redo/` with CLI, engine package, renderer, hand-authored web UI, README, and OpenSpec baseline.
- Reuse `dgraph.claims`, `dgraph.divergence`, `dgraph.grounding`, and `dgraph.llm_util` for parsing, segmentation, routing, judging, grounding, and JSON parsing.
- Implement remix degree filters for `correct`, `reframe`, and `add` changes.
- Implement adult, young, and child reading-level prompts, with child mode passing BOI concept definitions from claim grounding.
- Render rewritten markdown, change-list markdown, JSON sidecar, marked additions, skipped notes, and per-turn diff rows for the UI.
- Persist server runs to the app's gitignored `data/runs/` through the shared harness.


## Non-Goals
- No changes to `dgraph`, `content-tools`, `deutsch-interject`, or `worldview-mirror` source.
- No whole-document rewrite mode, publishing-safe excerpt mode, picture-text children's-book layout mode, deployment, accounts, or shared backend database.
- No claim that transformed copyrighted work is safe to publish.
