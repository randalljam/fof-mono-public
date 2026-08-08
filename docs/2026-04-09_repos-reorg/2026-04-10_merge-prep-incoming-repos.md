# Merge Prep: Incoming Repos into corpus-tools

**Created**: 2026-04-10
**Purpose**: Hand this doc to a Claude Code session working on each incoming repo so it can prepare the code for merge into the corpus-tools monorepo.


## Target Monorepo

- **Repo**: `FocusOnFoundationsNonprofit/corpus-tools`
- **Branch**: `primo`
- **Destination**: `apps/<app-name>/` (new convention — each app gets its own subdirectory)
- **Merge method**: Fresh copy of current code (no git history preservation)


## Repos to Merge

### 1. math (repo name TBD)
- **Source account**: personal (not FocusOnFoundationsNonprofit)
- **Status**: Prototype with ~5-6 feature iterations by a junior developer
- **Note**: An earlier version already exists at `corpus-tools/projects/math_quiz/` — the incoming repo is the more current version
- **Target path**: `apps/math/`

### 2. games (repo name TBD)
- **Source account**: personal (not FocusOnFoundationsNonprofit)
- **Status**: Early prototype
- **Target path**: `apps/games/`


## What the Prep Session Should Produce

For each repo, a Claude Code session should generate a single markdown file called `merge-report.md` at the repo root containing:

### A. Repo Summary
- What the application does (1-2 sentences)
- Languages and frameworks used
- Total file count and lines of code
- Any external services or APIs used

### B. File Inventory
- List every file with a one-line description of what it does
- Flag any files that should NOT be brought over (build artifacts, node_modules, .env, caches, IDE config, etc.)
- Flag any large files (>1 MB) — these need review before copying in

### C. Dependencies
- List all dependencies (from requirements.txt, package.json, or imports)
- Flag any that might conflict with corpus-tools existing deps
- Note which dependencies are already available in corpus-tools' `primary/` library

### D. Shared Code Candidates
- Identify any code that duplicates functionality already in `primary/` (file I/O, LLM calls, transcription, etc.)
- Recommend: keep the app's version, use primary's version, or merge
- List any utility functions that might belong in `primary/` rather than the app

### E. Config and Secrets
- List any config files, environment variables, API keys, or secrets the app needs
- Note how they're currently managed (hardcoded, .env, config.py, etc.)
- Recommend how they should be managed in the monorepo

### F. Entry Points and How to Run
- How to start/run the application
- Any build steps required
- Test commands if tests exist

### G. Suggested Directory Layout
Propose how the files should be organized under `apps/<app-name>/`:
```
apps/<app-name>/
  README.md          (brief: what this is, how to run, status)
  <source files>
  requirements.txt   (app-specific deps only, not duplicating primary/)
  tests/             (if any exist)
```


## What the Merge Session (in corpus-tools) Will Do

After receiving the merge-report.md files, a session on the corpus-tools repo will:

1. Create `apps/` directory if it doesn't exist
2. Copy in the files (excluding flagged items from the report)
3. Wire up any shared imports to use `primary/` modules
4. Add the new app to CLAUDE.md's directory guide
5. Add a brief README.md in each app directory
6. Run existing tests to confirm nothing breaks
7. Commit on the `primo` branch


## Instructions for the Prep Session

Paste this into a Claude Code session connected to the target repo:

```
Read this merge prep doc and generate a merge-report.md at the repo root
following the template described. Be thorough on the file inventory and
dependency analysis — this report will be used by a different session
to actually perform the merge into a monorepo.

The target monorepo has these Python modules in its shared library (primary/):
- fileops.py (file I/O, path manipulation, JSON/CSV/markdown read/write)
- transcribe.py (audio transcription via Deepgram, speaker ID)
- llm.py (OpenAI and Anthropic API calls, prompt management, token counting)
- rag.py (RAG pipeline, vector search query building)
- vectordb.py (Pinecone integration, index management)
- aws.py (S3 upload/download, HMAC hashing, JWT, Lambda helpers)
- structured.py (structured data extraction and processing)
- video.py (video processing, frame extraction)
- webflow_api.py (Webflow CMS integration)
- conversion.py (file format conversion)
- corpuses.py (corpus metadata and configuration)

Flag any code in this repo that overlaps with those modules.
```
