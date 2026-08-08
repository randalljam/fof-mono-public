## Why
The baseline living spec is a flat requirements list — folding it reveals nothing about what the app does or which user journey each requirement serves. A `## Workflows` section makes the spec readable as "what the app does" without changing any behavior contract.

## What Changes
- Add a `## Workflows` section to `openspec/specs/app/spec.md` between Purpose and Requirements: each user journey as a one-line narrative naming the requirements it exercises. Every requirement appears in at least one workflow.

## Non-goals
- No requirement is added, modified, or removed. No app code changes.

## Notes
- Structure-only change: no delta specs exist, so `openspec validate` reports "Change must have at least one delta" for this change while it is active. Expected — OpenSpec's delta model covers requirements, not spec structure. The store validates clean after archive.
- Verified 2026-07-10: `openspec validate --all --strict` passes with the extra section, and archive-merge of later deltas preserves it.
