# Baseline Current Behavior

## Why
This is the first OpenSpec baseline for deutsch-graph. The app already has implemented behavior across a Python graph build pipeline, committed graph artifacts, query helpers, generated viewer data, and a static graph viewer, but there is not yet a living contract that future agents can validate against before changing it.

## What Changes
- Capture the current observable application behavior in a single `app` capability.
- Establish requirements for the CLI, corpus fetch, inventory, parsing, graph build outputs, validation, query helpers, viewer export, and static viewer.
- Archive the baseline into `openspec/specs/app/spec.md` after strict validation.

## Non-Goals
- No behavior changes.
- No roadmap items or aspirational features in the baseline spec.
- No changes to generated graph data, viewer data shards, source modules, tests, or docs outside the new OpenSpec and roadmap files.
