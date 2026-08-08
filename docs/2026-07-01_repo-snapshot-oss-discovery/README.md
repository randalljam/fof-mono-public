file: plans/2026-07-01_repo-snapshot-oss-discovery/README.md
title: Repo system snapshot + OSS discovery
last-updated: 2026-07-01_0930
ai: Claude Code (cloud)
session: `repo-analysis-oss-discovery`

A point-in-time snapshot of the fof-mono system — the operator, the portfolio, the in-flight
branches, and the AI-agent-first workflow — paired with a research sweep for open-source
projects and companies that are one or two steps ahead of it.


## What's here
- **`index.html`** — the interactive, browsable snapshot. Open it directly in a browser
  (no build step, no network needed). Sidebar nav + a filterable/searchable catalog of
  ~50 OSS/company recommendations in section 06. Links to the Fable 5 playbook.
- **`oss-discovery.md`** — the full long-form research report behind section 06, with links,
  grouped by theme, plus status flags (adopt / watch / caution / skip) and "steps ahead"
  framing. Kept in markdown so the content is citable and diffable, not trapped in the HTML.
### OSS deep-dive pages (added 2026-07-01)
Sculptor-style deep dives for the tools/companies most on Randy's radar. Each: how it works
technically, a practical application to the fof-mono workflow (his lanes/constraints), frictions,
and a try-it/verdict. All are nested under the OSS Discovery entry in `index.html`'s left pane, and
the corresponding OSS catalog cards carry a "★ deep dive →" badge. Where a project's canonical docs
blocked automated fetching, claims are hedged inline with verify tags.
- **`sculptor.html`** — Sculptor (Imbue): parallel local agents, Pairing Mode, applied to the three
  lanes (Cursor worktrees, Claude Code in the Cataclysm cloud env, Codex local worktrees).
- **`compound-engineering.html`** — Every Inc.'s compounding methodology + the MIT plugin; framed as
  the name for what Randy already does (docs/rules/skills as compounding context).
- **`pi.html`** — `earendil-works/pi`, the minimal embeddable harness (OpenClaw's foundation); an
  engine for a future custom agent, not a daily driver — with the no-permission-system caution.
- **`openspec.html`** — Fission-AI's delta-spec SDD system; the durable/reviewable upgrade to the
  `plans/` markdown habit.
- **`superpowers.html`** — obra/Jesse Vincent's SKILL.md methodology; the uncanny match to Randy's
  worktree + skills conventions — best library to mine.
- **`factory.html`** — Factory.ai "Droids": commercial multi-model platform; patterns to steal
  (headless CI one-shots, tiered autonomy) rather than re-platform.
- **`stripe-minions.html`** — Stripe's internal one-shot agents; Blueprints, isolation-as-permissions,
  Slack-triggered PRs — reference pattern feeding Fable mission 5.
- **`strongdm.html`** — StrongDM Software Factory + Attractor: satisfaction testing + digital-twin
  fakes of external deps (S3/Pinecone/Webflow/LLM); the keystone practice for self-verification.

Two new catalog entries (Compound Engineering, Pi) were also added to the OSS discovery panel in
`index.html`.

### Fable 5 playbook (added 2026-07-01)
Five prompts to spend the Claude Fable 5 window on high-leverage, judgment-heavy missions that
advance the AI-coding system without creating review/cleanup burden.
- **`fable5.html`** — interactive page: the play, the modular model, the five prompts with a TLDR
  each (why Fable 5 not Opus 4.8 / what it accomplishes), a token+budget table, and a live budget
  calculator (how many runs fit in the 50% Fable pool). Linked from `index.html`.
- **`fable5-context-brief.md`** + **`fable5-operating-contract.md`** — the two enduring, cross-purpose
  support docs every prompt references (orientation + execution contract). Distilled from existing
  repo docs, so no review needed.
- **`fable5-prompts/1..5-*.md`** — the five copy-paste mission prompts (Portfolio Cartographer,
  Safety Rails/CI, Meta-System Upgrade, App Baseline, HOTL Blueprint).
- **`fable5-questions.md`** — 20 prioritized quick questions (with defaults) to tune the prompts;
  the first five fold straight into the prompt headers.

### Web stacks × design (added 2026-07-01)
- **`webstacks.html`** — interactive page for two audiences (Randy, the AI-first builder; and a
  professional UX/design lead): (1) a review of the stack behind every web app in the repo, verified
  from the files, grouped into five patterns; (2) a plain-language primer on the full-stack option
  space (rendering models, frameworks, styling/UI, backend, hosting); (3) the design × stack
  intersection as an interactive positioning map (design ceiling vs AI-drivability/ownership) plus a
  comparison matrix; (4) per-audience takeaways; (5) a four-lane recommendation for this repo with a
  live "which lane is this app?" picker. Linked from `index.html`. Chart palette validated with the
  dataviz skill's validator for the dark surface.


## How it was built
Four parallel analysis passes over the repo at the 2026-07-01 state of `origin/main` plus the
9 in-flight remote branches:
1. Deep-dive on `use/prism-sync` (the FastAPI Prism Launcher sync web app).
2. Deep-dive on `feature/minecraft-mod-build-local` (MathQuest mod + the merged Forge port, PR #31).
3. A map of the agent-first tooling infrastructure (multi-harness setup, skills, worktrees,
   hooks, conventions), read from `AGENTS.md`, `docs/worktrees-guide.md`, `scripts/`, `.claude/`,
   `.cursor/`, `.codex/`, `agents/hermes/`.
4. A web research sweep for aligned OSS/companies, filtered against the system's actual shape
   (multi-harness orchestration, worktree-parallel agents, one-source skills, cloud/local
   handoff, convergence planning, human-out-of-the-loop).

Primary source docs read: `AGENTS.md`, `plans/2026-04-09_repos-reorg/PROFILE-randy.md`,
`plans/2026-04-09_repos-reorg/ai-coding-system-dev.md`, `plans/2026-04-09_repos-reorg/PROJECTS.md`,
`docs/worktrees-guide.md`.


## Caveats
- Line-of-code figures are rough (tracked files via `git ls-files`, includes some vendored JS).
- OSS project *status* flags (projects wound down, companies shut down, tools deprecated) were
  captured from mid-2026 web search excerpts and should be re-verified before you invest time —
  a few source sites returned 403 to the fetcher. All links are correct; open them directly.
- This is a snapshot, not a living doc. If it's still useful in a month, re-run the passes
  rather than hand-patching it.
