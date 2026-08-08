file: plans/2026-07-01_repo-snapshot-oss-discovery/fable5-prompts/1-portfolio-cartographer.md
title: Fable 5 prompt 1 — Portfolio Cartographer
last-updated: 2026-07-01_0930
ai: Claude Code (cloud)
session: `repo-analysis-oss-discovery`

Copy everything below the line into a fresh Claude Fable 5 session running in `fof-mono`.
Docs-only mission — lowest risk, highest "get organized" value. Run first.

---

You are working in the `fof-mono` monorepo as an autonomous agent. Before doing anything, read these
two files in full and operate under them for the whole session:
- `plans/2026-07-01_repo-snapshot-oss-discovery/fable5-context-brief.md` (who/what/why + boundaries)
- `plans/2026-07-01_repo-snapshot-oss-discovery/fable5-operating-contract.md` (pace, autonomy, deliverables)

**Mission — organize the whole portfolio into one decision-ready map.**
Randy runs ~20 small-to-medium projects across `apps/`, `core/`, `web-shared/`, and nine in-flight
branches. He needs a single, current, honest picture of what exists, what state each thing is in, what
depends on what, and — most valuably — what the highest-leverage next moves are. This is a
judgment-and-synthesis task over the entire repo, which is why it's worth your capability.

**What to actually produce:**
1. Refresh `plans/2026-04-09_repos-reorg/PROJECTS.md` so the index and records match reality on `main`
   plus the live branches (status, primary folder, visibility, one honest note each). Correct anything
   stale; don't invent structure that isn't there.
2. Write a new roadmap document, `plans/2026-07-01_portfolio-roadmap.md`, containing:
   - A **prioritized "top 10 next actions"** across the whole portfolio, each with: the project, the
     concrete next step, why it's high-leverage now, rough effort (S/M/L), and any dependency or risk.
     Rank by leverage-to-effort, and say what you're deprioritizing and why.
   - A **dependency / sequencing view** — which projects block or feed others (e.g. the web-stack
     migration, the CI/test floor, the skills standard), so Randy can see what order to tackle things.
   - A short **risk register** — the few things most likely to bite (production `qrag`, unmerged
     branches drifting from `main`, data/S3 hygiene, single points of failure).
3. Ground every claim by actually reading the relevant files and branches — use parallel sub-agents to
   survey `apps/`, `core/`, the branches, and the planning docs concurrently, then synthesize. Do not
   assert a project's status without having looked at it.

**Boundaries beyond the operating contract:** This mission is **documentation only** — do not modify
application code, config, or tests, and do not merge or rebase any branch. You are producing a map, not
changing the territory.

**Definition of done:** `PROJECTS.md` is accurate and current; `2026-07-01_portfolio-roadmap.md` exists
with the three sections above; both use the standard doc header. Finish with the approval-packet summary
from the operating contract, leading with the single most important thing you found and the top three
recommended next moves. Stop at "branch pushed + approval packet" — do not open a PR.
