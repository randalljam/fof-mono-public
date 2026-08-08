file: apps/holodeck/ROADMAP.md
title: Holodeck - roadmap and vision

# Holodeck - roadmap and vision
## Vision
Holodeck is meant to become the local command center for fof-mono's parallel AI-coding work. Its core product is the snapshot aggregation layer: one privacy-conscious JSON view of worktrees, branches, apps, OpenSpec state, skills, recent agent sessions, and deploy surfaces. The web dashboard is the first UI over that snapshot, optimized for quickly answering "what is happening across this repo right now?" without walking worktrees or opening multiple agent histories.
## Now / Next / Later
- **Now** - Stabilize the S1 local loop: collect all eight layers into the gitignored snapshot, serve the FastAPI API and static dashboard on port 8790, focus already-open Cursor worktrees through the reusable `apps/mac` activation boundary, and keep the current behavior captured in OpenSpec.
- **Now** - Use the dashboard for read-only triage of dirty worktrees, branch drift, unpushed work, port collisions, active OpenSpec changes, recent AI sessions, and known deploy surfaces.
- **Now** - Maintain `registry.yaml` as the curated source for app names, purposes, dev commands, ports, local URLs, tests, deploy entries, notes, and tags.
- **Next** - Verify the real end-to-end collector/server/browser loop after meaningful app changes, including `/api/refresh` and a real session-detail fetch.
- **Next** - Expand and clean registry coverage as more apps are consolidated into the monorepo, especially app commands, test commands, deploy metadata, and known port collisions.
- **Next** - Render `stage` / `spec_stage` chips on dashboard app cards (fields added to registry + apps collector 2026-07-10; vocabulary provisional — see `skills/openspec/docs/2026-07-10_openspec-guide/index.html` on the feature/openspec-skills branch).
- **Next** - Let broader OpenSpec adoption feed the Specs section so active changes, task progress, and archived changes become a reliable planning surface across apps.
- **Next** - Add concrete, allowlisted Holodeck callers for the reusable exact-match Chrome and Safari tab adapters when dashboard entities have stable URL/title targets.
- **Later** - Add explicit live deploy probes, such as `fly status`, Chalice URLs, or other checks, behind user-triggered actions.
- **Later** - Add controlled dev-server launch and stop operations once there is a clear permission and process-management story.
- **Later** - Add deeper session search and token/cost rollups across Claude Code, Cursor, and Codex.
- **Later** - Add optional auto-refresh through local cron or launchd helpers.
## Idea inbox
- 2026-07-10 - Keep the snapshot as the stable product and allow the web dashboard to be redesigned without changing collectors.
- 2026-07-10 - Preserve the current privacy boundary: generated snapshots and AI-session previews stay local and gitignored; full session bodies are loaded lazily.
- 2026-07-10 - Consider registry validation for missing commands, duplicate ports, stale local URLs, and apps that should have tests or README files.
- 2026-07-10 - Consider a deploy-probe design that never performs network or CLI checks unless the user explicitly clicks a probe button.
- 2026-07-10 - Explore session search as a separate feature so the current capped previews remain fast and safe.
- 2026-07-17 - Add a work-mode input such as head-down vs. casual and one-screen vs. two-screen, then let it shape what the overview emphasizes.
- 2026-07-17 - Revisit branch naming for this workflow; the `feature/` prefix carries little information in the Holodeck view, so plain work-branch slugs may scan better.
- 2026-07-17 - Design a two-screen mode where Holodeck drives the work loop on one display and opens or focuses Cursor worktree windows on the other from Status rows.
