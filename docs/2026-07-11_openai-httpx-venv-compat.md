file: 2026-07-11_openai-httpx-venv-compat.md
title: OpenAI SDK / httpx venv incompatibility — root cause, fix, and dependency-update playbook
last-updated: 2026-07-13_0715
ai: Claude Code - Opus 4.8 (1M context)
session:

## Summary
The shared venv had `openai==1.50.0` (pinned) alongside `httpx 0.28.1` (unpinned, drifted forward). openai versions below **1.55.3** pass the `proxies=` keyword to httpx, which httpx 0.28 removed — so every `OpenAI()` / `AsyncOpenAI()` client construction crashed with `TypeError: Client.__init__() got an unexpected keyword argument 'proxies'`. Fixed on branch `fix/openai-httpx-venv-compat` by upgrading to `openai==1.109.1` (latest 1.x) and cutting a new dated requirements file. One venv serves all worktrees (symlinked), so the single upgrade fixed every worktree at once.


## Symptom
Reported from the `feature/worldview-mirror` branch (deutsch-graph worktree): "openai 1.50.0 is incompatible with the installed httpx 0.28.1, so every OpenAI() client call in the repo currently throws." Reproduced in the main checkout and all worktrees:
```
TypeError: Client.__init__() got an unexpected keyword argument 'proxies'
```

## Root cause
1. `dependencies/requirements_2026-06-02.txt` pinned `openai==1.50.0` (Sep 2024 vintage) and did not pin `httpx` at all.
2. Later package installs (the venv also drifted to `anthropic 0.116.0` vs the pinned `0.34.2`) pulled `httpx` forward to 0.28.1.
3. httpx 0.28 (Nov 2024) removed the long-deprecated `proxies` argument. The openai SDK stopped passing it in **1.55.3**. Any older openai + httpx ≥ 0.28 combination breaks at client construction.
4. `pip` never flagged it: openai 1.50.0's metadata allows `httpx>=0.23.0,<1`, so the break is behavioral, not declared.

## Blast radius — what was broken vs. what kept working
**Broken (constructs an SDK client):**
- `core/llm.py` — `openai_chat_completion_request_sdk`, `deepseek_chat_completion_request_sdk`, `get_openai_models`
- `core/vectordb.py`, `core/conversion.py` — module-level/function `OpenAI()` clients (embeddings etc.)
- Apps: `apps/voice/tts.py`, `apps/smol-podcaster/`, `apps/education/lesson-logger/scripts/extract_lesson.py`, `apps/autolearner/pipeline.py` (SDK import path)

**Kept working (no SDK client):**
- `core/llm.py` raw-`requests` paths: `openai_chat_completion_request`, `openai_function_call`, `simple_openai_chat_completion_request` — these POST directly to `api.openai.com`. This is why the voice router (`apps/voice-router/integrations.py` uses `openai_chat_completion_request` / `openai_function_call`) and the stellar transcriber (arbitration via `core.llm.llm_arbitrate_dual_chunk` → `openai_function_call` path) never noticed.
- All Anthropic paths (`anthropic 0.116.0` is compatible with httpx 0.28).
- Deployed QRAG Chalice Lambdas — they bundle their own deps at deploy time from unpinned `openai` in their `requirements.txt`, independent of this venv.

## Venv architecture (why one fix covers everything)
`scripts/worktree_bootstrap.sh` symlinks each worktree's `.venv` → `/Users/randytrue/Documents/Code/fof-mono/.venv` (shared mode, the default). Verified: all active worktrees (deutsch-graph, stellar-transcriber, voice-router, autolearner, content-studio, holodeck) point at the one venv. Upgrading the main venv instantly fixed every worktree.

## The fix
1. **Upgraded `openai` 1.50.0 → 1.109.1** in the shared venv. 1.109.1 is the last 1.x release: it contains the httpx fix (≥1.55.3), keeps the same major-version API surface as 1.50 (no call-site changes needed anywhere), and satisfies `langchain_openai==0.2.1`'s `openai<2.0` constraint. **openai 2.x was deliberately NOT chosen** — it would force a langchain-stack upgrade (`core/vectordb.py` and `core/conversion.py` use langchain).
2. **New dated requirements file** `dependencies/requirements_2026-07-11.txt` (successor to `requirements_2026-06-02.txt`), with three changes:
   - `openai==1.109.1` (with a warning comment about the <1.55.3 + httpx≥0.28 trap and the 2.x/langchain constraint)
   - explicit `httpx>=0.28.0,<1.0.0` (records the floor that forces openai ≥1.55.3)
   - `anthropic==0.116.0` (pin aligned to what the venv actually runs — was drifted)
3. **Updated all live references** to the requirements filename: `setup.py`, `scripts/worktree_bootstrap.sh` (REQ default), `README_external.md`, `docs/worktrees-guide.md`, `apps/autolearner/README.md`. (Historical snapshot `plans/2026-04-09_repos-reorg/2026-06-01_repo-status.md` left as-is.)
4. **Regenerated editable-install metadata** with `.venv/bin/pip install -e . --no-deps` so `pip check` validates against the new pins without churning other packages. (As of 2026-07-31, `setup.py` is metadata-only — no `apps`/`core` install — plus a venv import guard; see `docs/2026-07-31_worktree-shared-venv-editable-import-trap.md`.)
5. **Removed the stale `corpus-tools 1.0` editable install** — leftover metadata from the pre-cutover repo (it pointed at the same fof-mono directory and advertised the old pins, producing permanent false `pip check` conflicts). `import core` verified to still resolve to `fof-mono/core/` after removal.

## Verification (all on 2026-07-11)
- `OpenAI()` and `AsyncOpenAI()` construct cleanly; `core.llm` and `core.conversion` import cleanly.
- `pip check` → "No broken requirements found." (was 4 conflicts before)
- `tests/test_llm.py` → **44 passed** (mocked APIMOCK suite).
- **Live smoke tests** (gpt-4o-mini / text-embedding-3-small): raw-requests path ✓, SDK path (previously broken) ✓, SDK embeddings (the vectordb pattern) ✓.
- Worktree propagation: deutsch-graph, stellar-transcriber, voice-router venvs all report `openai 1.109.1`, `OpenAI() OK`.

## Known remaining issue #1 — pinecone / langchain_pinecone import conflict (separate, pre-existing)

### The mechanical break
`import pinecone` — and therefore `import core.vectordb`, `import core.rag`, `import core.corpuses` — currently raises `pinecone.deprecated_plugins.DeprecatedPluginError`. Cause: the venv holds BOTH `pinecone 6.0.2` (what our requirements ask for) and the legacy `pinecone-client 5.0.1`, which is pulled in transitively by `langchain_pinecone==0.2.0`. `pinecone-client` drags along `pinecone-plugin-inference`, and pinecone 6.x refuses to import if that plugin is merely present. So the requirements file is internally self-conflicting: `pinecone>=6` and `langchain_pinecone==0.2.0` cannot cleanly coexist. This predates and is unrelated to the openai/httpx fix.

### What is the actual impact — and why QRAG is unaffected (verified)
**This does NOT touch the deployed QRAG application.** The QRAG Lambdas run from their own mirrored copies under `apps/qrag/api/*/chalicelib/`, and those copies do **not** import langchain at all. Verified directly: the top-of-file imports in `apps/qrag/api/qrag-llm/chalicelib/vectordb.py` are just `from openai import OpenAI` and `from pinecone import Pinecone, ServerlessSpec` — no `from langchain_pinecone import ...`. (There is a function *named* `create_vectordb_vrag_langchain`, but it is a leftover name with no langchain import behind it, and it is an offline index-**creation** function, not part of the live query path.) This is exactly why your key QRAG app keeps working: the langchain dependency was already stripped out of the deployed side.

The break is confined to the **local `core/` copy** — specifically anything that imports these modules at top level:
- `core/vectordb.py` (has the `from langchain_pinecone import Pinecone as LangchainPinecone` at line 18, a top-level import — so the whole module fails to import)
- `core/rag.py`, `core/corpuses.py` (they do `from core.vectordb import *` / `from core.rag import *`)
- `core/vectordb_mtests.py`, `core/rag_mtests.py`

So what is actually broken right now is **local corpus-building / RAG-ingestion / dev tooling** run out of `core/`. Note `core/llm.py` is NOT broken by this: its `from core.vectordb import generate_embedding` is a **lazy import inside a function** (line 3816), so `import core.llm` succeeds — which is why the whole openai fix and its tests ran fine.

### Is langchain even wanted here?
Per your note: langchain is long-deprecated in your stack and you've been removing it everywhere; the deployed QRAG side already has none. In `core/vectordb.py`, `LangchainPinecone` is used in exactly **one** place — line 597, `LangchainPinecone.from_documents(documents=..., embedding=OpenAIEmbeddings(), index_name=...)`, an ingestion/upsert call. Everything else in that module already uses the native `pinecone` 6.x client directly. So the langchain dependency in `core/` is a single vestigial ingestion call, not a load-bearing integration.

### Fix options (for a deliberate, separate branch off main)
1. **Recommended — drop langchain from `core/` entirely.** Replace the one `LangchainPinecone.from_documents(...)` call at `core/vectordb.py:597` with the native pinecone 6.x upsert path plus direct OpenAI embeddings (the same `generate_embedding` pattern the module already uses elsewhere). Then remove `langchain_pinecone`, `langchain_community`, `langchain_openai`, `langchain` from the requirements to the extent nothing else in `core/` needs them (grep first — `core/vectordb.py` also imports `langchain_community.document_loaders.ObsidianLoader` and `langchain.text_splitter.RecursiveCharacterTextSplitter`, so those two call sites must be ported too, e.g. to a plain file reader + a simple splitter). This un-conflicts the requirements permanently and matches your "no langchain" direction. This is a code change with its own tests, best done on its own branch — not folded into this venv fix.
2. **Stopgap only — bump `langchain_pinecone`.** Dry-run resolutions (2026-07-11):
   - `langchain-pinecone==0.2.13` (latest) → pulls langchain-core 1.x, langchain-openai 1.3.5, **openai 2.45** — a full stack jump that would also undo the openai 1.x pin from this fix.
   - `langchain-pinecone==0.2.8` → bumps langchain-core 0.3.1→0.3.86, langchain-openai 0.2.1→0.3.35 + test deps.
   - `langchain-pinecone==0.2.3` → downgrades pinecone to 5.4.2 (keeps the deprecated plugin, i.e. doesn't really fix it).
   None of these are attractive; they deepen the langchain dependency you're trying to shed. Option 1 is the right long-term move.

**Bottom line for issue #1:** low urgency, contained blast radius (local ingestion/dev tooling only, QRAG unaffected), and the clean fix is to finish removing langchain from `core/vectordb.py` on its own branch off main.

## Known remaining issue #2 — QRAG Lambda `openai` is unpinned (reproducibility risk, not a guaranteed break)

### First, clear up the terminology (this is the source of the confusion)
"The openai package" and "the OpenAI SDK" are **the same thing**. `openai` is the name of the one PyPI package, and that package *is* the official OpenAI Python SDK. `openai==1.109.1` and `openai==2.45.0` are just two versions of that single package/SDK. There is no separate "SDK" package. So:
- The **local venv** (this fix) now pins that package to **openai 1.109.1** (a 1.x version).
- The **QRAG Lambda** `requirements.txt` files list it as a bare `openai` with **no version at all**.

These are two independent environments. The venv pin does not reach the Lambda, and the Lambda's unpinned entry does not reach the venv.

### What actually happens on a redeploy
When you run `chalice deploy`, Chalice does a fresh `pip install` of that Lambda's `requirements.txt` into the deployment bundle. Because the entry is an unpinned `openai`, pip grabs **whatever is latest at deploy time** — today that is **openai 2.45.0**. So the next redeploy would ship the Lambda with openai 2.45.0, even though all your local development and testing now happens on openai 1.109.1. (The httpx problem that caused this whole fix does **not** carry over to the Lambda: Chalice resolves the bundle fresh, so pip picks an httpx that is compatible with whatever openai it installs. httpx drift was purely a local-venv problem.)

### Would openai 2.x actually break the QRAG Lambda? — I tested it, and: no, not today
My first-pass note flagged this as a redeploy-time risk without verifying it — that was overstated. To get a real answer instead of guessing, I built a throwaway venv, installed the latest openai (2.45.0), and exercised it against the **exact** call patterns the Lambda uses (`apps/qrag/api/qrag-llm/chalicelib/llm.py` and `chalicelib/vectordb.py`). Results (2026-07-13):
- `OpenAI(api_key=...)` and `OpenAI(api_key=..., base_url="https://api.deepseek.com")` — both construct fine.
- `client.chat.completions.create`, `client.embeddings.create`, `client.models.list` — all still exist.
- Every parameter the code passes — `model, messages, tools, tool_choice, reasoning_effort, temperature, max_completion_tokens, max_tokens` — is still accepted by `chat.completions.create`; `input, model` still accepted by `embeddings.create`.

So a redeploy **today** with openai 2.45.0 would very probably run correctly. The Chat Completions surface this code uses is stable across the 1.x→2.x boundary. (openai 2.0's breaking changes were mostly the removal of the pre-1.0 `openai.ChatCompletion`-style module API and some deprecated aliases — none of which this code uses; it already uses the modern client-based API.)

### So what is the real problem, and why pin?
The problem is **not** a specific known break — it is **unpinned = untested + non-reproducible**:
1. **Untested divergence.** You develop and test on openai 1.109.1, but production would run openai 2.45.0 — a version combination you never exercised. "Probably fine" is not "verified fine," and the one thing I could not test without live API calls is the exact runtime shape of response objects (`.choices[0].message.content`, `.tool_calls`, `.usage.*`); those are stable across 1.x/2.x by every indication, but they were not exercised end-to-end.
2. **Non-reproducible builds.** Two deploys on two different days can silently bundle two different openai versions. A deploy that worked last month is not guaranteed to reinstall the same thing today.
3. **The real future hazard.** The next time OpenAI ships a version with an actual breaking change (a hypothetical 3.0, or even a 2.x that changes a default), an unpinned `openai` will pull it in on the *very next deploy* with no warning and no code review — and *that* is the redeploy that could break, quietly, whenever it happens to land. Pinning removes that surprise.

Note the same is technically true of the other unpinned entries in those files (`chalice`, `boto3`, `pinecone`, etc.), but `openai` is the one with a recent major-version bump and a demonstrated history of breaking installs (the very httpx issue this doc is about), so it is the one worth pinning first.

### Recommendation — and what it fixes
Add an explicit version bound to `openai` in all three files (`apps/qrag/api/{qrag-llm,vrag-llm,qrag-routing}/requirements.txt`). Two viable choices:
- **`openai>=1.55.3,<2.0`** — keeps the Lambda on the **same major (1.x) that local dev is now pinned to**, so deploy == what you test locally. `>=1.55.3` guarantees the httpx-`proxies` fix is present regardless of what httpx pip resolves alongside it; `<2.0` stops a future major from landing silently. This is the most conservative "make prod match dev" option and is what I recommend unless you specifically want to move to 2.x.
- **`openai>=2.0,<3.0`** — deliberately adopt 2.x on the Lambda (I verified the call patterns work), but then you should also move the local venv to 2.x so dev and prod stay on the same major, which in turn requires the langchain-stack upgrade from issue #1 (`langchain_openai` 0.2.1 caps openai at `<2.0`). That is a bigger, coordinated change.

To be explicit about your question "are you recommending keeping the earlier SDK version?": I am recommending you **pin to a tested, bounded range so deploys are reproducible** — not that the old version is inherently better. Because local dev is on 1.x right now, the *low-effort, low-risk* way to make prod reproducible and matched to dev is to pin the Lambda to `>=1.55.3,<2.0`. Moving everything to 2.x is also fine but is a larger coordinated change (it entangles with issue #1). What fixes the hazard in either case is the **upper bound** — that is the line that prevents a future openai major from silently deploying itself.

**This was intentionally not changed in this branch:** these are deploy-adjacent Chalice files, and per the repo's caution rules around Lambda/deploy code, the pin belongs on its own Chalice-focused branch with a redeploy, not folded into a local venv fix. It is a one-line-per-file change when you're ready.

## Dependency-update playbook (how to handle this class of problem)
1. **Reproduce and name the exact break** — import/construct in the venv, capture the traceback. Distinguish metadata conflicts (`pip check`) from behavioral breaks (like this one, which pip cannot see).
2. **Scope the blast radius before changing anything** — grep for the import (`from openai import`), separate the code paths that touch the broken surface from those that don't; check what worktrees/apps/deploys share the environment vs bundle their own.
3. **Pick the smallest-jump target version** — the minimum-risk release that contains the fix while staying inside other packages' declared constraints (`pip show <pkg>` → Requires/Required-by; `pip install --dry-run` to preview resolver fallout before committing to anything).
4. **Upgrade narrowly** — `pip install pkg==X.Y.Z`, never a broad `-U` sweep of the venv.
5. **Mirror the venv change in git the same day** — new dated `dependencies/requirements_YYYY-MM-DD.txt`, update every live reference (setup.py, bootstrap script, docs), regenerate metadata-only editable (`pip install -e . --no-deps`), reinstall the worktree import guard, and get `pip check` to zero so future drift is visible instead of buried in noise.
6. **Test in layers** — imports → mocked unit suite → small live smoke calls of each affected path → confirm propagation to shared consumers (worktrees).
7. **Record what you deliberately didn't do** (this doc's pinecone and Lambda sections) so the next session doesn't rediscover it from scratch.
