file: PROJECTS.md
title: fof-mono — Portfolio Map
last-updated: 2026-08-07_1635

Portfolio map for the projects and applications in this monorepo. Complements the apps-centric folder structure (Option B, see `2026-05-28_monorepo-folder-structure.md`) by holding the cross-cutting metadata: areas/domains, status, visibility, primary folder(s), and notes that the filesystem cannot capture.

Execution rules live in `AGENTS.md`. Operator/human context lives in `PROFILE-randy.md`. Evolving infrastructure and AI-coding-system notes live in `ai-coding-system-dev.md`.

Many entries below are stubs — flesh out the records for a given project when it gains enough complexity or risk that the index alone can't capture it.


## Status definitions
- **Active** — currently developed or maintained.
- **Production-like** — live with real infrastructure; treat carefully.
- **Deployed prototype** — live with limited users.
- **Maintenance** — stable; only bug fixes / small improvements.
- **Experimental** — exploratory; may change direction.
- **Paused** — not currently active; may resume later.
- **Archived** — no longer active; do not modify without instruction.


## Areas
Areas are cross-cutting domain tags. They are folders only when an area has 2+ sub-projects (umbrella folder under `apps/`); otherwise they live as tags here.

| Area | Type | Folder? | Notes |
| --- | --- | --- | --- |
| qrag | system | yes (`apps/qrag/`) | RAG-over-transcripts; serves multiple corpora; AWS Chalice backend + Webflow/Astro frontends |
| deutsch | corpus | yes (`apps/deutsch/`) | Stephen Deutsch / David Deutsch interview corpus + graph/content tooling; data in S3 |
| pv | corpus | no | PV / EPC meetings corpus; data in S3 |
| floodlamp | corpus | no | FloodLAMP biotech archive; mostly archival; data in S3 |
| education | domain | yes (`apps/education/`) | Homeschool / kid-education tools (`lesson-logger/`, `reading/`, `milestone-web/`) |
| family | domain | no | Privacy tag for kid-facing / family-adjacent work (no `apps/family/` umbrella; material lives under education, math-quiz, minecraft, skills) |
| minecraft | domain | yes (`apps/minecraft/`) | Game mods and related tooling; multiple sub-projects |
| transcription | domain | yes (`apps/transcription/`) | Diarized transcription apps + Deepgram callback Lambda |
| ai-coding-system | meta | no | The system that builds the system (see `ai-coding-system-dev.md`; executable surface includes `apps/holodeck/`) |


## Projects index
| Project | Areas | Type | Status | Primary folder | Visibility |
| --- | --- | --- | --- | --- | --- |
| QRAG (RAG-over-transcripts) | qrag, deutsch, pv, floodlamp | web app + API | Production-like | `apps/qrag/` | Public-facing |
| Focus on Foundations site | qrag, floodlamp | Astro site + AWS static hosting | Production-like | `apps/focusonfoundations/` | Public-facing |
| Math quiz | education, family | web app | Active | `apps/math-quiz/` | Public planned |
| Lesson logger | education, family | app + skill | Active | `apps/education/lesson-logger/` | Private |
| Reading assessment | education, family | doc / material | Experimental | `apps/education/reading/` | Private |
| Milestone web | education, family | web UI | Paused | `apps/education/milestone-web/` | Private |
| AutoLearner | education | web app | Experimental | `apps/autolearner/` | Private |
| Diarized transcription tool | qrag, pv, deutsch, transcription | capability | Active | `core/transcribe.py` | Private |
| Stellar Transcriber | transcription, qrag | pipeline / app | Active | `apps/transcription/stellar-transcriber/` | Private |
| Live transcript | transcription, qrag | tool | Experimental | `apps/transcription/live-transcript/` | Private |
| Smol podcaster | transcription | tool | Experimental | `apps/transcription/smol-podcaster/` | Private |
| Deutsch Graph | deutsch, qrag | data + tooling | Active | `apps/deutsch/deutsch-graph/` | Private (public planned) |
| Deutsch content-forge | deutsch | tooling | Active | `apps/deutsch/content-forge/` | Private |
| Deutsch content-redo | deutsch | tooling | Active | `apps/deutsch/content-redo/` | Private |
| Deutsch content-tools | deutsch | shared harness | Active | `apps/deutsch/content-tools/` | Private |
| Deutsch interject | deutsch | tooling | Active | `apps/deutsch/deutsch-interject/` | Private |
| Worldview Mirror | deutsch | web app | Active | `apps/deutsch/worldview-mirror/` | Private |
| Deutsch transcript copyright release | deutsch | pipeline | Active | TBD | Private |
| PV / EPC meetings | pv | corpus work | Active | TBD | Private |
| Minecraft: mod build tooling | minecraft | tooling | Active | `apps/minecraft/mods/build-and-deploy.py` | Private |
| Minecraft: MathQuest (Wandering Nerd) | minecraft, education | game mod | Active | `apps/minecraft/mods/mathquest/` | Private |
| Minecraft: remove-singleplayer | minecraft | game mod | Active | `apps/minecraft/mods/remove-singleplayer/` | Private |
| Minecraft: DM control panel | minecraft | game mod | Experimental | `apps/minecraft/mods/` (planned) | TBD |
| Minecraft: prism-sync | minecraft, family | utility | Active | `apps/minecraft/prism-sync/` | Private |
| Minecraft: Skyblock reference | minecraft | reference | Paused | `apps/minecraft/skyblock/` | Private |
| Minecraft: mineflayer-forge | minecraft | tooling | Experimental | `apps/minecraft/mineflayer-forge/` | Private |
| Holodeck | ai-coding-system | local control center | Active | `apps/holodeck/` | Private |
| Content Studio | ai-coding-system | media generation | Experimental | `apps/content_studio/` | Private |
| Voice (TTS / OCR-to-speech) | personal | utility | Experimental | `apps/voice/` | Private |
| Repo mirror | ai-coding-system | tooling | Maintenance | `apps/repo-mirror/` | Private |
| Mac utilities | personal | local utilities | Active | `apps/mac/` | Private |
| Scratch runners | personal | personal scripts | Active | `apps/scratch/` | Private |
| Hash-store Lambda | qrag | utility lambda | Production-like | `web-shared/aws_chalice/hash-store/` | Public-facing API |
| Hmac-hash Lambda | qrag | utility lambda | Production-like | `web-shared/aws_chalice/hmac-hash/` | Public-facing API |
| Send-email Lambda | shared | utility lambda | Production-like | `web-shared/aws_chalice/send-email/` | Public-facing API |
| Deepgram-callback Lambda | transcription | webhook lambda | Production-like | `apps/transcription/api/deepgram-callback/` | Public-facing API |


## Shared components
### Core Python library (`core/`)
Shared library used by all apps and Chalice Lambdas. Major modules: `fileops.py`, `transcribe.py`, `llm.py`, `rag.py`, `aws.py`, `s3_archive.py`, `vectordb.py`, `structured.py`, `conversion.py`, `corpuses.py`, `dbgen.py`, `webflow_api.py`, `aws_valid.py`, `aws_logs.py`, `rag_prompts_routes.py`, `audio.py`, `video.py`, `speakerid.py`, `gdrive.py`, `transcript_eval.py`, plus diarization helpers (`diar_backends.py`, `diar_formats.py`, `diar_metrics.py`). Promotion to multi-package (`packages/`) is deferred per Option B until a specific module's public release or a breaking change forces it.

### Cross-app Webflow shells (`web-shared/`)
Site head/body, home body, log-in, CMS templates, privacy embed, custom code template. Shared across Webflow-fronted surfaces (QRAG and related); Focus on Foundations production site is now Astro under `apps/focusonfoundations/`.

### Chalicelib mirror script (`web-shared/aws_chalice/chalicelib_mirror_deploy.sh`)
Single shared deploy script used by every Chalice Lambda regardless of folder location. Anchors all paths on `find_repo_root()` so apps may live at `web-shared/aws_chalice/<app>/`, `apps/<owning-app>/api/<lambda>/`, or any other depth. See "Chalicelib mirror pattern" in `AGENTS.md`.


## Project records
Long-form notes for projects that need them. Add records here as projects gain enough complexity or risk that the index alone is insufficient.

### QRAG (RAG-over-transcripts system)
- Areas: qrag, deutsch, pv, floodlamp
- Folder: `apps/qrag/`
- Components:
  - `apps/qrag/api/qrag-llm/` — main LLM Lambda
  - `apps/qrag/api/qrag-routing/` — routing/dispatch Lambda
  - `apps/qrag/api/vrag-llm/` — variant LLM Lambda
  - `apps/qrag/web/` — Webflow custom code (devpage variants, qrag input component, dummy embed, local dev harnesses, functree doc)
- Related Lambdas: `hash-store`, `hmac-hash` (shared infra at `web-shared/aws_chalice/`); `deepgram-callback` (at `apps/transcription/api/`)
- Frontend: Webflow shells in `web-shared/`; QRAG-specific code in `apps/qrag/web/`; production FoF site migrating/migrated to Astro in `apps/focusonfoundations/`
- Backend: AWS API Gateway + Chalice Lambdas; Pinecone for vector search; S3 for large context
- Auth: JWT; HMAC PII hashing
- Deploy: `chalicelib_mirror_deploy.sh` invoked from each Lambda's directory; production deploys gated per `AGENTS.md`
- Risk: Medium — production-like with real users; `$LATEST` deploy posture (see `apps/qrag/api/*/deployed_*_logs/` and historical `aws_notes.md`)

### Focus on Foundations (Astro site)
- Areas: qrag, floodlamp
- Folder: `apps/focusonfoundations/`
- Production static Astro frontend for focusonfoundations.org (AWS static hosting under `infra/`), replacing the prior Webflow embed stack while keeping existing QRAG API Gateway/Lambda backends.
- Staging / production URLs and Webflow rollback notes: `apps/focusonfoundations/README.md`.
- Visibility: Public-facing site; some app docs (auth test walkthroughs) are private-only and listed on the public-snapshot exclude list.

### Holodeck
- Area: ai-coding-system
- Folder: `apps/holodeck/`
- Local AI-coding control center: aggregates worktrees, branches, apps, skills, OpenSpec stores, recent AI sessions, and deploy surfaces into a snapshot, served via FastAPI + vanilla web dashboard.
- Has its own `AGENTS.md`. Session/turn data under `apps/holodeck/data/` is gitignored (local-files mount).
- Visibility: Private tooling surface (may ship in a public snapshot as architecture, without session data).

### Minecraft (umbrella)
- Area: minecraft (+ education for MathQuest)
- Folder: `apps/minecraft/`
- Imported from `kid-games` repo (2026-06-05). Has its own `AGENTS.md` at `apps/minecraft/mods/AGENTS.md` covering build tooling, targets, versioning, and playtest workflows.
- Sub-projects:
  - `mods/mathquest/` — math-focused Fabric mod ("Wandering Nerd"). Multi-target: fabric-26.1.2 (primary), fabric-1.21.11 (preserved). Active.
  - `mods/remove-singleplayer/` — tiny client-only mod hiding the Singleplayer button. Multi-target: Fabric + Forge (nested loader gradle roots). Active.
  - `mods/build-and-deploy.py` — unified Python build dispatcher for all mods. Handles JDK selection, multi-target builds, per-profile deployment.
  - `skyblock/` — Hypixel Skyblock reference materials (minion optimizer, profile snapshots, SkyHanni examples). Paused.
  - `prism-sync/` — Prism Launcher sync web app + CLI for the family Mac fleet. Active.
  - `mineflayer-forge/` — Mineflayer + Forge bridge experiments.
  - `skins/` — dragon skin generation script + PNGs.
  - `world-stories/` — Minecraft world-building story prompts.
  - `litematica/` — schematic / Litematica-related materials.
- Legacy notes: `enchanments.md`, `rail.md` (Randy's notes, pre-import — leave untouched).

### Education apps (umbrella)
- Areas: education, family
- Folder: `apps/education/`
- Sub-projects:
  - `lesson-logger/` — homeschool lesson capture (app + `skills/education/lesson-logger/`); Active.
  - `reading/` — reading assessment material; Experimental.
  - `milestone-web/` — local milestone-map web UI; Paused.
- Related (flat apps, not under this umbrella): `apps/math-quiz/`, `apps/autolearner/`.
- Visibility: Private — child-related material; do not publish without explicit approval (per `AGENTS.md` approval boundaries). Note: a public snapshot may still include sanitized app skeletons; live lesson/learner data stays in gitignored local mounts.

### Deutsch (umbrella)
- Area: deutsch (+ qrag where graph/RAG-linked)
- Folder: `apps/deutsch/`
- Sub-projects: `deutsch-graph/`, `content-forge/`, `content-redo/`, `content-tools/`, `deutsch-interject/`, `worldview-mirror/`, plus root script `extract_boi_problems_snippets.py`.
- Corpus data lives in S3 (`[S3-FILES-BUCKET]`), not in git.

### Transcription (umbrella)
- Areas: transcription, qrag
- Folder: `apps/transcription/`
- Sub-projects: `stellar-transcriber/`, `live-transcript/`, `smol-podcaster/`, `api/deepgram-callback/`.
- Shared capability still centered on `core/transcribe.py` and related diarization/eval modules in `core/`.
