Corpus-tools monorepo: full sweep

## 1. Structure & characterization

**Repo root:** `/home/user/corpus-tools`, on branch `claude/analyze-monorepo-aws-7JaV4` (created from `main`). Only 2 remote branches exist (`main`, this analysis branch) — so the "too many branches" worry is about local/ephemeral ones, not upstream clutter.

**What this repo actually is:** a personal research/AI monorepo for an interview-corpus RAG system. It's code + data + notes + AWS backend + Webflow frontend glue, all in one place. Several distinct "projects" (deutsch, floodlamp, pv, sovereign-child, fda-townhalls, education) share one code library.

**Top-level layout (by role):**

| Area | Dirs | Purpose |
|---|---|---|
| Core Python library | `primary/`, `secondary/`, `lib/`, `voice/` | Shared modules: `llm.py` (2.7k LOC), `transcribe.py`, `fileops.py`, `aws.py`, `aws_valid.py`, `rag.py`, `vectordb.py`, `structured.py`, TTS, video |
| AWS backend | `web/aws_chalice/` | 8 Chalice apps (Lambdas): `qrag-llm`, `qrag-routing`, `vrag-llm`, `hash-store`, `hmac-hash`, `send-email`, `deepgram-callback`, `testapp` + a `langchain-layer/` (141 MB Lambda layer) |
| Frontend | `web/` (239 MB) | Webflow custom code: `webflow-fof-site-head.html`, `webflow-fof-site-body.js`, `webflow-rag-devpage.js`, local dev harness, `fasthtml/`, `md_view/` |
| Data (bulk of size) | `data/` (**5.6 GB**) | Transcripts & media per project: `floodlamp` 2.1 GB, `pv` 1.8 GB, `deutsch` 969 MB, `misc_transcripts` 516 MB, `sovereign-child` 173 MB, `education` 66 MB |
| Project-specific apps | `projects/` (153 MB) | `ads_scrape`, `math_quiz`, `meta_coder`, `wingspan` |
| Graph RAG experiment | `ms-graphrag/` (251 MB) | Microsoft GraphRAG integration |
| Vector DBs | `lancedb/`, `pretrained_models/` | Local LanceDB and model weights |
| Logs/artifacts | `logs/` (536 MB) | API swagger JSONs, call logs, Pinecone zip snapshots |
| Archive | `_archive/` (286 MB), `_misc_to_be_sorted/`, `limbo/` | Old code kept around |
| Docs/plans/prompts | `docs/`, `plans/`, `prompts/`, `ai-threads/`, `exchanges/` | Design notes, prompt templates, saved AI chats |
| Tests | `tests/` (40 MB) | `test_fileops.py`, `test_llm.py`, `test_transcribe.py` |

**Code size (from your existing `cloc_report.md`):** ~28,770 lines of actual code across ~80 files. This is a *small* code surface — most of it is concentrated in ~20 "primary" Python modules. The 5 GB is overwhelmingly data/media/logs, not source.

**Style:** research-style Python (long modules, many `# =====` banner comments, `mtest_*` inline tests, heavy `from X import *`), lots of markdown notes scattered at root, Webflow embed snippets in the frontend.

## 2. Repo size on this VM

- **Working tree:** `9.6 GB` total
- `.git/` alone: **2.6 GB** (large because of historical commits of data/media)
- `data/`: 5.6 GB
- Large binaries tracked: PDFs, .mp3s under `data/misc_transcripts/p_Ilya/` and `p_Rorty/`, `.pptx` decks in floodlamp, a numpy `.dylib` inside `langchain-layer/`

## 3. Disk space on this VM

```
Filesystem  Size  Used  Avail  Use%
/dev/vda    252G   17G    21G   45%
```

Note the oddity: 252 GB total, only 17 GB used, but just **21 GB available** and 45% in use — suggests a quota or reserved space on this VM image. You have room to work, but not unlimited room; you won't be able to, say, clone another copy of the repo plus build a large Lambda layer without watching it.

## 4. AWS infrastructure: analysis

**Framework:** AWS **Chalice** (not CDK, not SAM, not Terraform). Each Lambda is its own Chalice project under `web/aws_chalice/`, deployed to API Gateway.

**Services in use:**
- **Lambda** — 8 functions (qrag-llm, vrag-llm, qrag-routing, hash-store, hmac-hash, send-email, deepgram-callback, testapp)
- **API Gateway (REST)** — one gateway per Lambda, CORS restricted to `focusonfoundations.org` + a Webflow staging origin
- **S3** — buckets `fofpublic`, `[S3-BUCKET]`, `deutsch-audio` for uploads, logs, large-context passing, per-project `s3-qrag-*` paths
- **Lambda Layers** — custom `langchain-layer` (141 MB of vendored deps, including a stray macOS `.dylib` from numpy)
- **IAM** — roles managed via Chalice + custom `aws_valid.py` helpers
- **Deepgram callback** integration, **JWT auth** via PyJWT, **HMAC** hashing for user PII
- **Webflow** is the actual frontend host; Lambdas are called from Webflow custom code
- Vector search is **Pinecone** (external), not an AWS service. LanceDB runs locally.

**Architecture pattern:** Webflow page → JS calls API Gateway → Chalice Lambda → OpenAI / Pinecone / S3 → JSON back. The `qrag-routing` Lambda does routing/dispatch, the `qrag-llm` / `vrag-llm` Lambdas do the actual RAG calls. `hash-store` + `hmac-hash` handle privacy-preserving user tracking. `send-email` does transactional email. Large prompt contexts are passed via S3 filename references rather than inline.

**What's well set up:**
- Clear one-Lambda-per-route separation — easy to reason about blast radius.
- `primary/aws.py` → mirrored into each Chalice's `chalicelib/` via `chalicelib_mirror_deploy.sh`. This gives you a shared library across Lambdas without abandoning Chalice.
- CORS whitelisting by Origin, JWT verification on incoming requests, HMAC hashing of PII (name/email/IP) before storage — privacy posture is thought through.
- A monitoring thread + timeout+retry protocol inside `qrag-llm` for long LLM calls, with an explicit "Retry" status returned before API Gateway's 29 s ceiling. That's a real pattern, not a hack.
- S3 path routing by `vector_index_name` prefix — cleanly namespaced per project.
- `aws_valid.py` wraps request validation logic that Chalice overwrites on deploy, with a documented double-deploy workaround in `aws_notes.md`. The reasoning is written down, which is great.
- Extensive operational notes in `aws_notes.md` about API Gateway → Lambda versioning semantics.

**What's incomplete or smells:**
1. **No IaC for non-Lambda resources.** S3 buckets, API Gateway validators, IAM policy nuances, Pinecone indexes, and DNS are all managed by hand + ad-hoc scripts. If you lose AWS state you can't rebuild.
2. **Chalice's limits are biting you.** The `aws_notes.md` file catalogs several fights with Chalice: it clobbers request validators, versioning is manual, custom CF patching is painful. You've built scaffolding (`chalicelib_mirror_deploy.sh`, `aws_valid.py`) to paper over this. Consider whether **AWS CDK** or **SAM** would be less friction long-term — CDK especially pairs well with a Python codebase and removes most of these workarounds.
3. **`$LATEST` deploys.** `aws_notes.md` admits API Gateway currently invokes `$LATEST` — fast but no rollback, no staging alias discipline. Risky for anything users depend on.
4. **Duplicated app.py snapshots next to live code:** `app_2-19 internal retry.py`, `app_with json print code.py`, `app_broken o1pro error logging.py`. These are backups-in-place. They belong in git history, not on disk — they will confuse an agent doing codebase search.
5. **Chalicelib drift risk.** The mirror script copies code from `primary/` into each Chalice's `chalicelib/`. If you edit `chalicelib/aws.py` directly in one Lambda dir, the mirror will silently overwrite it on next deploy. Needs a lint/CI check.
6. **`langchain-layer/` (141 MB) checked into git**, including a macOS `.dylib`. Lambda layers should be built artifacts, not source-controlled — this is bloating `.git/` forever.
7. **`logs/` (536 MB) is checked in**, including Pinecone zip snapshots from 2024. This is recoverable state, not source.
8. **Secrets posture unclear.** `.env` / `config.py` mentioned in README_internal as living on a Google Drive; `token.pickle` exists at repo root; a stale key file `.sesskey` sits in root. Verify none of these are tracked. Your public IPv4/IPv6 is also in `README_internal.md` — not a real vuln but worth scrubbing.
9. **`qrag-llm/app.py` has hardcoded model/timing constants** (`FIRST_MODEL = "gpt-5.4"`, `RETRY_TIME = 23`) and handwritten thread-based timeout logic. Works, but a config file or SSM Parameter Store would make this far easier to tune without redeploy.
10. **No CI/CD pipeline** visible — deploys are local `chalice deploy` runs. Fine now, but a single GitHub Actions workflow that runs tests and deploys to a `dev` stage on push would pay for itself quickly.

## 5. Questions to think about as you scale with agentic coding

1. **What is "the code"?** An agent told to "analyze the codebase" will happily crawl 5.6 GB of transcripts and burn your context window. You need a clear answer to *which paths an agent should read by default*. Your `.cursorignore` is a start — extend it / mirror it for Claude Code (see §6).
2. **One repo or one repo with workspace boundaries?** You want a monorepo (good), but that doesn't mean a flat namespace. Consider declaring logical workspaces (e.g., `primary/`, `web/aws_chalice/`, `projects/*`, `data/`) with per-area README files that agents are told to read first. Agents do much better when each area has a one-page "what lives here, what to touch, what not to touch" doc.
3. **Is `primary/` → `chalicelib/` mirroring the right abstraction long-term?** If yes, make it enforced (CI check, pre-commit hook) so an agent can't accidentally edit the mirror copy and lose it. If no, move the shared code into a proper local package (`pip install -e ./lib`) that each Chalice imports.
4. **Where should agent-generated code go before it's "blessed"?** You have `limbo/`, `_misc_to_be_sorted/`, `scratch.py` — consider making one of them the designated "agent scratch" area with a convention that nothing there runs in production.
5. **How many projects live in here, and do they need to stay coupled?** The `data/` subdirs (deutsch, floodlamp, pv, sovereign-child, education, fda-townhalls) each look like potentially independent products. They share the library, which is good. But if one project needs to be handed off or open-sourced, is that possible from the current layout? You already have `publicrepo_files.md` — formalize that.
6. **What's your test coverage floor?** 3 test files for ~28k LOC. Before unleashing agents to refactor, decide the minimum smoke tests you want green on every agent commit. Agents with tests to run are 10× safer.
7. **LLM model references are hardcoded in Lambdas.** Do you want agents modifying production Lambda code to bump models? Or do you want a config layer they can touch instead? Decide before it happens.
8. **Branching strategy.** You said too many branches got generated yesterday. Pick one convention (e.g., `claude/<short-task>-<id>`, one branch per task, delete after merge) and put it in `CLAUDE.md` at repo root so every Claude Code session reads it. Add a weekly `git branch --merged main | xargs git branch -d` habit.
9. **What's the review surface?** Agents write fast. What's your rule — PR-only with a human review? Direct commits to feature branches OK but never `main`? Codify it.
10. **Data governance.** Transcripts likely have PII / consent considerations. Agents should not be allowed to upload transcript content to third-party tools (paste bins, diagram renderers, etc.) without thinking. Worth a line in `CLAUDE.md`.

## 6. Red flags to clean up before heavy agentic work

These are ordered by impact-to-effort for agentic productivity and safety.

1. **Add a `CLAUDE.md` at the repo root.** Tell any agent session: (a) what this repo is, (b) which directories are code vs data vs archive, (c) never read `data/`, `logs/`, `_archive/`, `_misc_to_be_sorted/`, `limbo/`, `ms-graphrag/`, `pretrained_models/`, `node_modules/`, `lancedb/` unless explicitly asked, (d) the `primary/ → chalicelib/` mirroring rule, (e) branch naming, (f) how to run tests. This is the single highest-leverage change.
2. **Delete or relocate the in-place backup files.** `app_2-19 internal retry.py`, `app_with json print code.py`, `app_broken o1pro error logging.py`, `chalicelib_old/`, `_archive chalice/`, `webflow-rag-devpage_2025-02-27.js`, `webflow-rag-devpage_Gateway-Timeout.js`, `README_internal.md` has a stray `=` file at root, `temp.json` (225 KB), `scratch.py`, `scratch.md`. Agents will match these as "relevant code" and get confused. Git history is the right place for old versions.
3. **Stop tracking build artifacts.** Untrack `web/aws_chalice/langchain-layer/` (141 MB), `logs/vectordb_pinecone_log_zips/` (zip snapshots), `node_modules/`, `token.pickle`, `.sesskey`, any `__pycache__`, any `layer.zip`. Use `git rm --cached` + `.gitignore`. This alone should meaningfully shrink the 2.6 GB `.git/` over time (a `git gc --aggressive` + history rewrite if you're brave — but only with a backup).
4. **Audit the 833-line `.gitignore`.** That length is a sign that many ad-hoc decisions accumulated. Consolidate it, add comments for why each section exists.
5. **Verify no secrets are tracked.** Search git history for `config.py`, `.env`, `*secret*`, `*_KEY`, AWS access keys, JWT signing keys. README_internal references a `config.py` on Google Drive, so hopefully it's ignored — confirm. Rotate anything that was ever committed, even transiently.
6. **Pin `$LATEST` → alias migration**, at least for prod Lambdas. Otherwise any agent-driven `chalice deploy` immediately changes production behavior. Even a simple `prod` alias that you manually advance is a big safety upgrade.
7. **Write a one-file deploy runbook** (could just be in `aws_notes.md`): "to deploy Lambda X, run Y from directory Z, with stage dev/prod." Agents will actually follow written runbooks and not improvise.
8. **Add a `.claudeignore`-equivalent** (Claude Code uses the same ignores as your `.gitignore` plus anything you put in `CLAUDE.md`). Make sure `data/`, `logs/`, `_archive/` are excluded from agent search by default. Right now, a Grep across the repo would scan 5 GB.
9. **Flatten root-level clutter.** Root has ~15 loose files (README copies, code profiles, log markdowns, `cloc_paths.txt`, `cloc_count.sh`, `publicrepo_files.md`, `settings COPY TO USER SETTINGS.json`, `run_sovereign_child_html.py`). Move them into `docs/`, `scripts/`, or delete. Agents weight root-level files heavily when orienting.
10. **Pick one AI coding tool's conventions and own them.** You currently have `.cursorrules`, `.cursorignore`, `2025-01-20_cursorrules.md`, and now Claude Code. If you're going Claude Code-heavy, port the Cursor rules content into `CLAUDE.md` and archive the rest so the agent doesn't get conflicting instructions.
11. **Separate "data" from "repo" mentally.** 5.6 GB of transcripts in git is workable today but will become painful. Worth at least considering moving the large per-project data under `data/<project>/` out to **S3** (you already have buckets) with a small manifest file committed to git that tells scripts where to fetch from. This is the single change that would make cloning fast and make agentic work on a VM practical.
12. **Kill the stray `=` file at repo root** (`-rw-r--r-- 1 root root 0 Apr 5 14:32 =`). Almost certainly a shell redirect typo. Harmless but an agent will ask about it.

---

**Bottom line:** the code itself is small, coherent, and the AWS architecture is sensible for where you are — one RAG-over-transcripts product replicated across a handful of projects, sharing a Python library, fronted by Webflow, backed by per-route Chalice Lambdas and S3. The main risks to agentic work are **not** architectural — they're **repo hygiene** (backup files, tracked build artifacts, no per-area docs, no `CLAUDE.md`, 5 GB of data in the search path) and **deploy safety** (Chalice + `$LATEST` + no IaC for surrounding resources). Fix the hygiene items first — they take a few hours and will 3× the quality of every future Claude Code session. The Chalice-vs-CDK question can wait until hygiene is done.

Want me to start on any of these? Good first PRs would be: (a) write `CLAUDE.md`, (b) untrack `langchain-layer/` and `logs/vectordb_pinecone_log_zips/` from git with a cleanup commit, (c) delete the in-place `app_*.py` backups, or (d) write per-area README stubs for `primary/`, `web/aws_chalice/`, `projects/`, `data/`. Say the word and I'll do it on this branch.

## Repo size breakdown

A few things to do here. Let me start with the quick answers and research in parallel.

### On how you launched this
You're right, I was wrong about the GitHub issue. This session was launched from Claude Code (probably your Mac desktop app). The task instructions came from the session configuration, not from a GitHub issue.

### On git clone
By default, `git clone` downloads the **full history** — every commit, every branch, every version of every file ever committed. That's what makes `.git/` so large. You can do a shallow clone (`git clone --depth 1`) to get just the current snapshot, but that's not the default.

Let me check the actual sizes and find that sweep content.

Now let me look for the sweep content from earlier in this conversation and add the commit preference to AGENTS.md.

The sweep was never saved to a file — it was only in the conversation. Unfortunately, due to context compression, the original full sweep text from Exchange 1 has been trimmed from my context. I can see references to it in the primo.md log but not the original content itself.

I have two options: I can reconstruct the sweep by running the same analysis again now, or I can note that it's lost. Let me regenerate it — the data is all here.

While the sweep regeneration runs in the background, let me add the commit preference to AGENTS.md.

Now to answer your size questions while the sweep runs:

### Repo size breakdown
| What | Size | Notes |
|---|---|---|
| Tracked files only (byte sum of `git ls-files`) | **~7.1 GB** | On 2026-04-22 this repo sums to **~7.09 GB** — not the same as `du -sh`. |
| `.git/` (object database, `du -sh .git`) | **~5.0 GB** | This Mac, 2026-04-22. §2’s Linux VM had **~2.6 GB** — history/compaction/machine differ. |
| Entire repo folder (`du -sh` at root) | **~36 GB** | This Mac, 2026-04-22 — includes `.git`, **`.venv` / `.venv_python12`**, gitignored `data/`, `web/` artifacts, etc. |

The old **“Total on disk 9.7 GB”** line was wrong: it **added** tracked checkout (~7.1 GB) and `.git` (~2.6 GB). Those are related measures, not two disjoint partitions of “everything on disk,” and **neither** counts gitignored files that still sit in your working tree.

### What these numbers mean
- The **~7.1 GB** and the **“Where the 7.1 GB lives”** table below are **git-tracked** sizes (per-path sums of `git ls-files` match the table within rounding). They **exclude** anything listed in `.gitignore` / `.cursorignore`.
- **`du -sh`** on a dev machine is usually **much larger**: local virtualenvs (~**3.6 GB** + ~**650 MB** here), **`node_modules`**, **`__pycache__`**, and large **gitignored** trees under `data/` (see next subsection).
- So the other thread was **not** wrong about **5.6 GB for `data/`** if it meant **tracked** `data/` only — that matches **~5.55 GB** from `git ls-files` under `data/` on 2026-04-22. The confusion is **mixing** that with a **`du`** table of `data/*`, which **includes** gitignored folders such as `data/0_gitignore` and `data/audio_0_pv_gitignore`.

### What a clone downloads
`git clone` pulls the full **`.git`** history (packs, all objects). The checkout size is the **tracked** tree (~7.1 GB here). **Ignored paths are not in the repo**, so they do not download — but any **ignored** folders you create locally (e.g. `data/0_gitignore`) still inflate **`du`** on your disk.

### Where the 7.1 GB lives
Sizes below are **tracked bytes** (rounded); they match `git ls-files` sums per path on 2026-04-22.

| Directory | Size | Notes |
|---|---|---|
| `data/` | 5.6 GB | Tracked transcripts/media only — **not** full `du` of `data/` |
| `logs/` | 536 MB | Tracked logs; **~1.9 GB** on disk here (extra local/ignored files) |
| `_archive/` | 286 MB | |
| `ms-graphrag/` | 251 MB | |
| `web/` | 239 MB | Tracked; **~7.2 GB** on disk here (ignored layer/build/node, etc.) |
| `projects/` | 153 MB | |
| Everything else | ~50 MB | primary/, docs/, tests/, etc. |

### Within `data/` (immediate children)
Per **`du -sh data/*`** on **2026-04-22** (this Mac) — **includes gitignored** directories if present. Largest first.

| Path | Size | Notes |
| --- | --- | --- |
| `data/0_gitignore` | 6.1 GB | **Gitignored** (`.gitignore` lists `data/0_gitignore`). Local scratch: large `.mkv`/`.mp3`, many `zips_pilot-data*` / `zips_pilot-data-extended*` dirs (~60–78 MB each), `audio_embeddings`, `audio_clips`, `voice_mp3s`, HTTrack mirror leftovers (`hts-cache`, `index.html`), etc. **0** files tracked under this path. |
| `data/floodlamp` | 5.3 GB | |
| `data/pv` | 1.7 GB | |
| `data/audio_0_pv_gitignore` | 1.7 GB | **Gitignored** (explicit rule). **0** files tracked. |
| `data/deutsch` | 968 MB | |
| `data/misc_transcripts` | 516 MB | |
| `data/sovereign-child` | 173 MB | |
| `data/education` | 66 MB | |
| `data/pdfs_dev` | 17 MB | |
| `data/programming` | 11 MB | |
| `data/0_floodlamp-archive_gitignore` | 7.8 MB | |
| `data/audio_inbox` | 1.1 MB | |
| `data/chat_converts` | 892 KB | |
| `data/large_context_files` | 680 KB | |
| `data/openai_threads` | 276 KB | |
| `data/misc_books` | 68 KB | |
| `data/misc-various` | 36 KB | |
| `data/x_twitter` | 32 KB | |
| `data/looms` | 24 KB | |
| `data/gdrive` | 20 KB | |
| `data/style_guide_transcripts.md` | 12 KB | File at `data/` root |
| `data/cspell_dictionary_common.txt` | 4 KB | File at `data/` root |
| `data/capitalized_words_not_proper_names.txt` | 4 KB | File at `data/` root |
| `data/log_deepgram_transcriptions` | 4 KB | File at `data/` root |
| `data/names.md` | 4 KB | File at `data/` root |

The actual **source code** (primary/, web/ minus build artifacts, tests/) is probably under 10 MB. The rest is data, logs, archives, and build artifacts.

I'll write the sweep to a file once the background agent finishes. One moment.

Committed and pushed. The background agent is still generating the full repo sweep — I'll save it to a file and commit once it finishes.

The sweep is done. Let me check when the original sweep happened and save it to a file.

The primo branch started on 2026-04-09, so the original sweep was that date. Let me write the sweep to a file.