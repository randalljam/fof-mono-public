file: plans/2026-07-01_repo-snapshot-oss-discovery/fable5-context-brief.md
title: Fable 5 context brief — orientation pack for autonomous sessions
last-updated: 2026-07-01_0930
ai: Claude Code (cloud)
session: `repo-analysis-oss-discovery`

Paste-once orientation for a fresh Claude Fable 5 session working in `fof-mono`. This is a
distillation of things already established in the repo (`AGENTS.md`,
`plans/2026-04-09_repos-reorg/PROFILE-randy.md`, `PROJECTS.md`, `ai-coding-system-dev.md`,
`docs/worktrees-guide.md`) plus the 2026-07-01 system snapshot. Nothing here is a new decision —
it is context you can trust without asking Randy to re-review it. Read this, then read the
specific files your mission names.


## Who you're working for
- **Randall (Randy) True** — executive director of Focus on Foundations (501c3), solo operator.
- Physics/EE background, scientific programming pre-2024; **not a professional software engineer**.
  He is a "pure AI coder": AI generates all code, he is the operator and decision-maker. He reviews
  at the pull-request level, not line-by-line.
- Comfort: strongest in data pipelines (transcripts/Deepgram/RAG/S3); reads Python with help; **not**
  comfortable in JS/CSS or command-line git (prefers the Cursor Source-Control UI).
- Second human: **EA** (remote executive assistant) — runs scripts, commits, is automating admin
  work with skills. Workflows must stay safe and legible for a non-coder.
- **End-state he is building toward:** a voice-dictated feature description flows through
  plan → implement → test → review → deploy with compressed human approval only at key gates
  (production deploy, billing, public/private boundary). Everything is scaffolding toward that.


## The repo in one screen
Apps-centric monorepo ("Option B" — organized by application, not by layer). Shared Python in one
`core/`. Bulk data lives in S3 keyed 1:1 to repo paths; only manifests are committed.
- `core/` — ~35 shared modules. Most mature: `fileops.py`, `transcribe.py` (Deepgram + diarization),
  `llm.py` (provider-swappable OpenAI/Anthropic), `rag.py`, `vectordb.py` (Pinecone), `aws.py`,
  `s3_archive.py`, `structured.py`, `conversion.py`, `corpuses.py`, `webflow_api.py`.
- `apps/` — qrag (RAG-over-transcripts, **production-like**, Chalice + Webflow), math-quiz,
  minecraft (MathQuest mod, Fabric+Forge), family, games, voice, transcription, deutsch, education,
  repo-mirror, meta-coder, ads-scrape, live-transcript, smol-podcaster, scratch.
- `web-shared/` — cross-app Webflow shells + shared Chalice Lambdas + the chalicelib mirror/deploy
  script. `skills/` — reusable agent procedures (richest: `repo-ops/`). `agents/hermes/` — an
  autonomous Telegram ops agent on Fly. `plans/` — planning docs, incl. the git branch ledger.
- Scale (2026-07-01): ~1,629 tracked files, ~133k lines Python, ~42k JS/HTML, **878 markdown docs**.
  The written context outweighs the code — that is deliberate.

## In-flight branches (each a live project — don't disturb without reason)
`use/prism-sync` (Prism Launcher sync web app), `feature/minecraft-mod-build-local` (MathQuest +
merged Forge port), `feature/web-site-redo-fof` (Astro + AWS CDK — the move off Webflow),
`feature/admin-automation-skills` (EA's skills), `feature/animation-studio` (vision-verifier loop),
`feature/voice-router-{kickoff,design}` (the voice front door), `feature/family-schedule-dashboard`,
`feature/transcribe-diarize-dg-latest`.


## The harness landscape you might be running in
Randy works across Cursor (local, primary), Claude Code (cloud, deep review), Codex (worktrees),
and Hermes (remote ops bot). Assume a git repo, a Python `.venv`, and the conventions in
`AGENTS.md`. If you can run commands and tests, do; if you're code-only, say so and produce work a
follow-up session can verify.


## The current gaps (where the highest-value work is)
From Randy's own roadmap in `ai-coding-system-dev.md`, these are acknowledged, not-yet-done:
- **No CI gates** — the `tests/` suite exists but nothing runs it automatically on PRs.
- **No automated/AI PR review**, no preview-deploy gates, no rollback automation.
- **No self-verification harness** — no LLM-graded acceptance tests, no local "fakes" of external
  systems (S3/Pinecone/Webflow/LLM providers) so agents can verify without Randy.
- **Web stack migration** off Webflow to an owned, containerized full-stack deploy is just starting.
- **Code-intelligence / knowledge-graph** tooling (Understand-Anything, LightRAG, Serena) is of
  interest but not standardized.
- **Per-user agent awareness** (Randy vs EA) is designed but not built.

Aligned open-source and companies to draw on (from the 2026-07-01 snapshot, `oss-discovery.md`):
Serena + context7 (MCP precision/fresh docs), the Ralph loop (cheap autonomy), StrongDM's
LLM-graded scenario tests + local "digital-twin" fakes, CodeRabbit/PR-Agent (review gate),
SKILL.md standard + rulesync (one-source skills), container-use/Sculptor (cloud/local handoff).


## Hard boundaries (never cross without explicit approval)
- **Do not deploy** anything, and do not touch production. `apps/qrag/` is production-like with real
  users. Never run a Chalice deploy or edit `chalicelib/` directly (edit `core/`, per AGENTS.md).
- **Do not force-push, rewrite pushed history, or delete branches.** One working branch per mission;
  never push the harness `claude/<random>` auto-branch.
- **Do not commit** secrets, PII, data files, or binaries (a pre-commit hook blocks most). Bulk data
  goes to S3 via manifests, never into git.
- **Do not touch** `[S3-BUCKET]` (PII) or anything under the "off limits" list in `AGENTS.md`.
- When Randy is describing a problem or thinking out loud rather than requesting a change, the
  deliverable is your assessment — report and stop, don't apply a fix.

Full execution rules live in `AGENTS.md` and in the companion `fable5-operating-contract.md` — read
that next.
