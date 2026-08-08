Primo — Master Plan for corpus-tools

## Session Info

- **Tool**: Claude Code (cloud VM — "Claude Code on the web", not running locally)
- **Repo**: `focusonfoundationsnonprofit/corpus-tools`
- **Branch**: `primo` (renamed from `claude/analyze-monorepo-aws-7JaV4`)
- **Session started**: 2026-04-09
- **Platform**: Linux cloud VM, 252 GB disk, ~21 GB available

## What is Claude Code on the Web?

This session is running in **Claude Code on the web** — a cloud-hosted virtual machine where Claude has direct access to a cloned copy of your GitHub repo, a terminal, file system, and git. It is NOT running on your local machine. The VM has its own disk, its own environment, and persists for the life of the session. When you push from here, it pushes to GitHub, and your local machine can pull those changes.

---

## Plan

### Phase 1: Foundations (done)
- [x] Full repo sweep and characterization (Exchange 1)
- [x] Rename branch to `primo`
- [x] Create this tracking document
- [x] Educate on Claude Code context management (Exchange 2)
- [x] Create `CLAUDE.md` for this repo (Exchange 3)
- [x] Revise `CLAUDE.md` based on feedback (Exchange 4)

### Phase 2: Repo Prep for Agentic Coding (current)
- [ ] Create `apps/` directory — new convention for applications (replaces `projects/`)
- [ ] Move existing `projects/math_quiz/` to `apps/math_quiz/`
- [ ] Clean up root-level clutter (stray files: `=`, `temp.json`, `scratch.py`, etc.)
- [ ] Delete in-place backup files (`app_*.py` copies, `chalicelib_old/`, etc.)
- [ ] Untrack build artifacts (`langchain-layer/`, log zips)
- [ ] Audit `.gitignore` (833 lines — consolidate)
- [ ] Verify no secrets tracked in git history

### Phase 3: Merge Incoming Repos
- [ ] Generate merge prep doc for math repo (see `plans/merge-prep-incoming-repos.md`)
- [ ] Generate merge prep doc for games repo
- [ ] Run prep in separate Claude Code sessions on those repos
- [ ] Bring math code into `apps/math/` (fresh copy, no history)
- [ ] Bring games code into `apps/games/` (fresh copy, no history)
- [ ] Reconcile any shared deps or patterns with `primary/`
- [ ] Update `CLAUDE.md` directory guide with new apps

### Phase 4: AWS Infrastructure
- [ ] Document current AWS architecture (services, Lambdas, buckets, API Gateways)
- [ ] Evaluate Chalice vs CDK migration path
- [ ] Set up Lambda alias discipline (`dev`/`prod` instead of `$LATEST`)
- [ ] Create deploy runbook

### Phase 5: Agentic Workflow Setup
- [ ] Establish branching strategy and document in `CLAUDE.md`
- [ ] Set up Claude Code skills for common workflows (deploy, test, etc.)
- [ ] Add pre-commit hooks or CI checks for `chalicelib` mirror drift
- [ ] Define test coverage floor before agent-driven refactors

### Phase 6: Ongoing
- [ ] Per-area README stubs (`primary/`, `web/aws_chalice/`, `apps/`, `data/`)
- [ ] Consider moving large data to S3 with manifest files in git
- [ ] Set up a basic CI/CD pipeline (GitHub Actions → test → deploy dev)

---

## Claude Code Context Management — Reference

### CLAUDE.md (the equivalent of .cursorrules)

**Yes, `CLAUDE.md` is the direct equivalent of Cursor's `.cursorrules`.** It's a markdown file containing persistent instructions that Claude reads at the start of every session. It's your "system prompt" for all Claude Code work in this repo.

**Where it can live (all are loaded, not just one):**

| Location | Scope | Shared via git? |
|---|---|---|
| `./CLAUDE.md` (repo root) | All sessions in this repo, all team members | Yes |
| `./.claude/CLAUDE.md` | Same as above, just tucked in a folder | Yes |
| `./CLAUDE.local.md` | You only, this repo only (add to .gitignore) | No |
| `~/.claude/CLAUDE.md` | You, across ALL projects | No |
| Subdirectory `CLAUDE.md` | Loaded on-demand when Claude reads files in that dir | Yes |

**Key behaviors:**
- Loaded automatically at start of every session — no manual action needed
- Multiple files are concatenated (not overridden) — broader loads first, then more specific appends
- Subdirectory CLAUDE.md files load on-demand when Claude enters that directory
- Keep under ~200 lines per file for best adherence (long files dilute in context)
- Use `@path/to/file` syntax to import other files

**What goes in CLAUDE.md (not settings.json):**
- Coding standards, naming conventions, formatting rules
- Build/test/deploy commands
- Architectural decisions ("we use Chalice, not CDK")
- Directory structure guide ("data/ is read-only, never modify")
- Branch naming conventions
- What agents should/shouldn't touch

### Sessions

Claude Code calls each conversation a **"session"**. Key facts:

- Each session starts with a fresh context window
- CLAUDE.md and memory files are loaded at the start of every session
- As the conversation grows, Claude **auto-compacts** (summarizes older messages to free space)
- Sessions are saved as JSONL files under `~/.claude/projects/`
- Use `/resume` or `--continue` to pick up a previous session
- Use `--worktree` to work on an isolated branch in parallel

In your case, right now, this is **one session**. When you start a new Claude Code thread (from the web UI or CLI), that's a new session. Each session is independent unless you explicitly resume one.

### Settings (.claude/settings.json)

Settings control **permissions and automation**, not coding conventions:

| Scope | File | Shared? |
|---|---|---|
| Project (team) | `.claude/settings.json` | Yes (commit it) |
| Project (personal) | `.claude/settings.local.json` | No (gitignored) |
| User (global) | `~/.claude/settings.json` | No |

**What goes in settings.json:**
- Tool permissions (allow/deny rules for Read, Edit, Bash, etc.)
- Hooks (shell commands that fire on lifecycle events)
- Environment variables
- Default permission mode

### Skills

Skills are **reusable workflows** packaged as markdown files. They live in `.claude/skills/<skill-name>/SKILL.md`.

| Location | Scope |
|---|---|
| `.claude/skills/` in repo | This project, shared via git |
| `~/.claude/skills/` | All your projects, personal |

Skills are loaded on-demand (not at session start like CLAUDE.md). They can be invoked as slash commands (`/skill-name`) or auto-triggered when relevant. Good candidates: deploy scripts, test runners, code review checklists.

### Hooks

Hooks are **automated actions** that fire at lifecycle events (session start, before/after tool use, on file change, etc.). Configured in settings.json:

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash",
      "hooks": [{ "type": "command", "command": "./scripts/check-something.sh" }]
    }]
  }
}
```

Use cases: enforce linting before commits, validate that chalicelib mirrors are in sync, block edits to data directories.

### File Exclusions (no .claudeignore)

There is **no `.claudeignore` file**. Instead, use deny rules in settings.json:

```json
{
  "permissions": {
    "deny": ["Read(data/**)", "Read(logs/**)", "Edit(data/**)"]
  }
}
```

Or, more practically, just tell Claude in CLAUDE.md: "Never read files under data/, logs/, _archive/ unless explicitly asked."

### Auto Memory

Claude can save notes to itself across sessions in `~/.claude/projects/<project>/memory/MEMORY.md`. First 200 lines load at each session start. This is automatic — Claude writes what it learns as you work.

### Comparison: Cursor vs Claude Code

| Concept | Cursor | Claude Code |
|---|---|---|
| System prompt / rules | `.cursorrules` | `CLAUDE.md` |
| Per-session context | Chat window | Session (auto-compacts) |
| Ignore files | `.cursorignore` | Deny rules in settings.json |
| Conversation history | Thread in sidebar | Session (resume with `/resume`) |
| Reusable workflows | N/A | Skills (`.claude/skills/`) |
| Automation | N/A | Hooks (in settings.json) |
| Parallel branches | Manual | `--worktree` flag |

---

## Exchange Log

**Session**: Claude Code on the web (cloud VM)
**Repo**: `focusonfoundationsnonprofit/corpus-tools`
**Branch**: `primo`

### Exchange 1 — Full repo sweep and analysis
**Prompt timestamp**: 2026-04-09 ~17:30 UTC
**User prompt**: Full sweep of repo — summarize structure, characterize codebase, repo size, disk space, AWS infrastructure analysis, scaling questions, red flags for agentic work.
**Response summary**: Detailed analysis provided. Key findings:
- Repo is 9.6 GB on disk (5.6 GB data, 2.6 GB .git, rest is code/logs/artifacts)
- ~28,770 lines of code across ~80 files — small code surface, bulk is data/media
- AWS: 8 Chalice Lambda functions, API Gateway, S3, JWT auth, HMAC privacy hashing
- Architecture: Webflow → API Gateway → Lambda → OpenAI/Pinecone/S3
- Top recommendations: create CLAUDE.md, untrack build artifacts, clean up backup files, add Lambda alias discipline
- 12 specific red flags identified for cleanup before heavy agentic work
- 10 strategic questions for scaling with agentic tools

### Exchange 2 — Branch rename, primo.md setup, Claude Code education
**Prompt timestamp**: 2026-04-09 ~18:00 UTC
**User prompt**: Rename branch to primo. Create plans/2026-04-09_primo.md tracking doc. Log all exchanges. Explain CLAUDE.md — is it like .cursorrules? Per-session or persistent? Explain sessions, settings, skills, hooks. How does context management work? What are my options for repo-wide vs session-wide config?
**Response summary**: Branch renamed to `primo`. This file created. Full Claude Code context management reference written above. Key answers:
- CLAUDE.md IS the equivalent of .cursorrules — persistent, loaded every session, lives in repo root
- A "session" = one conversation/thread; each starts fresh; use /resume to continue
- Settings.json controls permissions and hooks (not coding rules)
- Skills are reusable workflows in .claude/skills/ — per-repo or global
- No .claudeignore exists — use deny rules in settings.json or instructions in CLAUDE.md
- Recommended next step: create CLAUDE.md for this repo

### Exchange 3 — Create CLAUDE.md
**Prompt timestamp**: 2026-04-09 ~19:35 UTC
**User prompt**: Review .cursorrules, review this thread, create CLAUDE.md. Explain where it lives. Show the full text.
**Response summary**: Created `CLAUDE.md` at repo root (NOT inside `.claude/` folder — it lives at `./CLAUDE.md`). Ported all .cursorrules content (python rules, formatting, docstrings, mrun pattern, markdown style, comments). Added repo-specific sections from thread analysis: directory guide (what to read vs skip), chalicelib mirror pattern warning, git/branching rules, testing commands, AWS deploy notes, and agent safety guardrails (never read data dirs, never deploy without approval, never push to main). Full file text provided in response for review.

### Exchange 4 — Revise CLAUDE.md based on feedback
**Prompt timestamp**: 2026-04-09 ~23:25 UTC
**User prompt**: Detailed revision of CLAUDE.md. Key feedback: (1) repo is a general-purpose monorepo, not specifically for interview corpus RAG; (2) add note that cleanup/reorg is in progress for agentic coding; (3) fix secondary/ description (less mature code, not "helper scripts"); (4) frontend and vector search are current choices, exploring alternatives; (5) LLM providers are swappable, don't tie to local/lambda; (6) what's in lib/? (7) standardize access-level language — define "read freely" vs "on request only" vs "off limits" instead of inconsistent "ignore" / "never read" / "do not read"; (8) data/ should be accessible when user directs, not "never read"; (9) condense chalicelib mirror — point to script file instead of full explanation; (10) Python rules are fine inline; (11) remove AWS deploy as standalone section (fold into agent safety); (12) more applications coming into monorepo.
**Response summary**: Rewrote CLAUDE.md (156 lines, down from 166). Key changes:
- Repo description now says "multiple applications sharing common Python code" with note about consolidation
- Defined three standardized access levels: "read freely" / "on request only" / "off limits"
- data/ moved to "on request only" (agents go there when directed, not on their own)
- secondary/ described accurately as less mature/inactive code
- lib/ described as vendored JS libs (vis-network, tom-select, bindings)
- Chalicelib mirror condensed to 2 lines pointing to the deploy script
- AWS deploy section removed (key rule kept in agent safety)
- Agent safety rules no longer blanket-ban data/ access
- data/floodlamp/ noted as containing mixed code and document files

### Exchange 5 — Plan next phase, merge prep doc
**Prompt timestamp**: 2026-04-10 ~00:15 UTC
**User prompt**: Check off CLAUDE.md tasks. Set up next todos focused on preparing repo for agentic coding and merging in two external repos (math and games, both on a personal GH account, both early-stage prototypes). math_quiz already exists under projects/ but incoming repo is more current. Generate a doc another Claude Code session can use to prepare those repos for merge. Ask clarifying questions.
**Decisions made**:
- Repos are on a different GitHub account (personal, not FocusOnFoundationsNonprofit)
- Fresh copy only — no git history preservation
- New `apps/<app-name>/` directory convention (replacing `projects/`)
- Standalone merge prep file (not inline in primo.md)
**Response summary**: Updated primo.md plan — Phase 1 marked done, added Phase 2 (repo prep), Phase 3 (merge incoming repos), renumbered remaining phases. Created `plans/merge-prep-incoming-repos.md` — a standalone doc that can be pasted into a Claude Code session on each incoming repo. It specifies exactly what info to generate: repo summary, file inventory, dependency analysis, shared code candidates, config/secrets audit, entry points, and suggested directory layout. Includes a ready-to-paste prompt block for the prep session.

### Exchange 6 — Split CLAUDE.md into AGENTS.md + thin CLAUDE.md
**Prompt timestamp**: 2026-04-10 ~00:20 UTC
**User prompt**: Restructure repo instruction files to use the portable AGENTS.md pattern. AGENTS.md becomes the canonical shared rules file (read by Codex, Cursor, and Claude Code). CLAUDE.md becomes a thin adapter that imports AGENTS.md plus Claude-specific extras. Cursor-only rules go in `.cursor/rules/`. This follows the emerging cross-tool convention for agent instructions.
**Decisions made**:
- AGENTS.md = single source of truth for all repo-wide rules (156 lines, same content as old CLAUDE.md)
- CLAUDE.md = thin adapter (7 lines): `@AGENTS.md` import + 3 Claude-specific behavioral notes
- `.cursor/rules/cursor-only.md` = Cursor-specific overrides (just the `required_permissions` rule)
- Old `.cursorrules` file kept for now (user can delete after verifying Cursor reads .cursor/rules/)
- Directory reorg (apps/ vs projects/) deferred until user maps out project landscape
**Response summary**: Created AGENTS.md with all shared rules. Rewrote CLAUDE.md to 7 lines. Created `.cursor/rules/cursor-only.md` for the one Cursor-specific rule. Old `.cursorrules` left in place as fallback.


## Recommendations

### The Problem

Your working tree is 7.1 GB. Of that, **5.6 GB is `data/`** and **536 MB is `logs/`**. The actual source code is under 10 MB. Every time a cloud AI coding session clones this repo, it pulls ~9.7 GB (files + history). That's slow, wasteful, and most sessions don't need the data at all.

### Options

#### Option 1: Git LFS (Large File Storage)
Move large files (data/, logs/, audio, PDFs) to Git LFS. They stay in the same repo, same paths, same git commands — but the actual bytes live on a separate server. A normal clone only downloads pointer files (tiny). When you actually need a data file, LFS fetches it on demand.

- **Pro**: No workflow change. Files stay at the same paths. `git clone` becomes fast.
- **Pro**: GitHub supports LFS natively.
- **Con**: GitHub LFS has bandwidth/storage quotas (free tier: 1 GB storage, 1 GB/month bandwidth). 5.6 GB of data would need a paid plan or self-hosted LFS.
- **Con**: Migrating existing files into LFS rewrites history.

#### Option 2: Move data to S3 (your primo.md already mentions this)
Keep data files in S3 (you already have AWS infra). Put a manifest or small index file in git that lists what's in S3 and where. Add a simple download script for when you need local copies.

- **Pro**: Repo becomes ~200 MB (source + archives + web). Clones are fast.
- **Pro**: You already have S3 and know it. No new service.
- **Pro**: AI sessions that don't need data just skip it. Sessions that do can pull specific files.
- **Con**: Data is no longer version-controlled (unless you version in S3, which is possible but manual).
- **Con**: Need a script/convention for "give me the deutsch corpus locally."

#### Option 3: Separate data repo
Move `data/` to its own git repo (e.g., `corpus-tools-data`). In the main repo, either git-submodule it or just document where to clone it alongside.

- **Pro**: Main repo becomes small. Data repo can be cloned only when needed.
- **Con**: Submodules are painful. Everyone hates them.
- **Con**: Paths change or you need symlinks.

#### Option 4: .gitignore the data, keep it local-only
Add `data/` and `logs/` to `.gitignore`. They stay on your local machine but stop being part of the repo. Back them up separately (S3, external drive, whatever).

- **Pro**: Simplest change. Repo shrinks immediately for new clones.
- **Con**: Doesn't help with existing history (`.git/` stays 2.6 GB until you rewrite history).
- **Con**: No version control on data at all. If your local drive dies, data is gone.

### Option 5: Shallow clone for AI sessions only
Don't change the repo at all. Configure AI coding sessions to use `git clone --depth 1 --filter=blob:none` (partial clone). This downloads only the current tree and fetches file contents lazily.

- **Pro**: Zero repo changes. No migration work.
- **Pro**: Works today.
- **Con**: You don't control how Claude Code clones — it might not support custom clone flags.
- **Con**: Doesn't solve the working tree being 7 GB on the VM's disk.

---

### My Recommendation

**Option 2 (S3) for `data/`**, combined with **Option 4 (.gitignore) as the first step**. Here's why:

1. **Right now**: `.gitignore` the data and logs directories so new clones don't include them. Your local copies stay put — nothing is deleted.
2. **Soon**: Upload data to S3 (you already have the infrastructure) with a simple script to sync specific corpora down when needed.
3. **Later**: If you want to shrink the `.git/` history too, do a one-time `git filter-repo` to strip large blobs from history. This rewrites history and requires all clones to re-clone, so it's a "do it once when you're ready" operation.

The key insight: AI coding sessions almost never need your 5.6 GB of transcripts and PDFs. When they do, they need one specific corpus, not all of them. S3 with selective download is the right pattern for that.

Want me to sketch out what the S3 manifest + download script would look like? Or do you want to think about this more first?