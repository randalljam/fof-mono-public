file: 2026-05-30_followup-folder-organization.md
title: Follow-up plan for remaining root-level folders after Option B reorg

This is the continuation work after the 2026-05-29 monorepo reorg (Option B). Core, apps, web-shared, AGENTS.md, and PROJECTS.md changes landed in commits `d051eefe..e7e23326` on the `pare-down` branch. The remaining top-level folders need scoping before the new repo cutover. This file is structured so each folder section can drive one focused coding session.


## Context prompt for a new agent session
You are continuing work on the corpus-tools monorepo Option B reorg.

### How to start (drag-and-submit kickoff):
This file is self-contained. If it is handed to you with no other instructions, treat that as the standing prompt: "Orient yourself from this section, then work through the next per-folder section that is not yet marked `[x]`." Specifically:
1. Read this "Context prompt for a new agent session" section, then read AGENTS.md for execution rules.
2. Find the next "## Per-folder plan" section whose heading is NOT prefixed with `[x]` (the first unchecked section after the last completed one).
3. Check that section's "Open questions". If they are already answered (look for italic `_..._` answers or an `_ANSWERS: ..._` block beneath them), proceed and do the work under those answers without re-asking. Normalize any raw dictated answers into clean per-question answers plus a short `Resolution (date):` note, matching the style of the already-completed sections.
4. If the open questions are unanswered (or an answer is genuinely ambiguous on a point that matters), ask the user a small number of focused questions before moving anything.
5. Do the work per "For the per-folder task you are running" below, then give a compact summary.

### Project context:
- Repo: /Users/randytrue/Documents/Code/corpus-tools. Active branch: pare-down.
- Recently reorganized to apps-centric "Option B" layout: single shared core/, per-app apps/<name>/, cross-app webflow shells in web-shared/, single chalicelib mirror script that anchors paths via find_repo_root() so Chalice apps can live at any depth.
- Background: plans/2026-04-09_repos-reorg/2026-05-28_monorepo-folder-structure.md (full Option B decision + completed migration plan). Its `# Current folder structure` H1 (last section) is the living, accepted folder-structure tree — the single source of truth for the repo layout. Whenever a per-folder move or any other change alters the layout, update that tree, bump its `Last updated:` line (date/timestamp + which follow-up root folder the change was made in conjunction with), and add a `## Change log` entry there describing what changed and why.
- Operator profile: plans/2026-04-09_repos-reorg/PROFILE.md (Randy is a pure AI coder, prefers compact recommendations, voice-dictated input, ask before hard-to-reverse changes).
- Portfolio map and area tags: plans/2026-04-09_repos-reorg/PROJECTS.md.
- Dev / system roadmap: plans/2026-04-09_repos-reorg/ai-coding-system-dev.md.
- Per-session execution rules: AGENTS.md (read first; defines safety / approval boundaries; chalicelib mirror pattern; Python style; markdown style).
- This follow-up plan: plans/2026-04-09_repos-reorg/2026-05-30_followup-folder-organization.md (the per-folder move plan; per-folder sections live below).
- Companion verification/cleanup tracker: plans/2026-04-09_repos-reorg/2026-05-30_post-file-organization-followup.md (post-move checks — running the test suite, S3 uploads/manifests, and anything a move surfaces that is not itself a move). It does NOT block per-folder moves; run its items once the moves settle. When a folder move turns up a non-move follow-up, record it there rather than here.
- Move manifest: plans/2026-04-09_repos-reorg/MOVE_MANIFEST.md (human-readable index of where everything moved; append a section per move session).

### Conventions to follow:
- Folders organize by application, not by domain or by code-type.
- Areas (deutsch, pv, floodlamp, education, family, minecraft, qrag, ai-coding-system) are tags in PROJECTS.md, not folders. Multi-sub-project areas become umbrella folders under apps/.
- One shared core/ Python library; promote a module to packages/ only when an app's public release or breaking change forces it.
- Chalice apps live at any depth via chalicelib_mirror_deploy.sh (refactored to use find_repo_root() and CHALICE_APP_REL).
- Prefer git mv over copy+delete to preserve history.
- Commit per logical unit; push to pare-down. Use a tmp file for any commit message that contains apostrophes.
- Production chalice deploy requires explicit human approval.
- PII, family/child-related material, credentials, and any cross-public/private-boundary moves require explicit approval.

### NEVER remove tracked files or rewrite git history on this repo (HARD RULE)
This is an absolute rule for the `corpus-tools` repo — do not violate it and do not ask to:
- NEVER run history-rewriting operations: `git filter-branch`, `git filter-repo`, BFG, history-dropping `git rebase`, or `git push --force`. (Already in AGENTS.md; restated here as load-bearing.)
- NEVER run `git rm --cached` to "untrack" files for cleanup/scrubbing, and NEVER propose it. Leave tracked files tracked.
- NEVER try to excise sensitive content from history. Committed secrets are handled by ROTATION (e.g. rotate a leaked API key), not removal. Committed low-sensitivity PII is accepted as-is.

Why: `corpus-tools` is a ~2.5-year, ~2500-commit, multi-GB private repo that will be FROZEN at cutover. The new repo is a fresh / shallow copy that inherits NO history, so nothing needs scrubbing and untracking buys nothing — it only risks damaging the repo. What does or doesn't land in the NEW repo is controlled at cutover-copy time (selective copy / the new repo's `.gitignore`), never by removing or untracking files here.

Context on the PII specifically: the QRAG signup PII here is just names and emails (and in the early-names case, mostly names) of a small set of mostly-known users — low sensitivity, low risk. Do not touch git history over it.

Narrow exception — explicit deletion only: if Randy explicitly asks to delete specific files (as with `exchanges/_del/` + `exchanges/deepseek/` on 2026-05-31), deleting them is fine — that is a normal forward commit and does not rewrite history (the files still exist in prior commits). Never delete or untrack as unprompted "cleanup." Normal forward ops (`git add`, `git commit`, `git mv`, `git push` to `pare-down`) are always fine.

### For the per-folder task you are running:
1. Read the section for the folder in this follow-up file.
2. Read AGENTS.md for execution rules.
3. Resolve the open questions with the user before moving (or proceed under the recommendation / the user's recorded answers if already approved). Do NOT run `chalice deploy` — production deploys need explicit approval.
4. Make moves with git mv. Update any imports, file markers, or config paths the moves break.
5. Run a smoke check (imports, lint, file existence) where applicable.
6. Append a new section to plans/2026-04-09_repos-reorg/MOVE_MANIFEST.md describing the moves (folder-scoped; commit hash; brief affected non-move files list). See the "How to update this file" instructions at the bottom of MOVE_MANIFEST.md.
7. If the move surfaces a non-move follow-up (test breakage, S3 upload, verification, etc.), record it in 2026-05-30_post-file-organization-followup.md rather than here.
8. Mark the corresponding section in this follow-up plan as completed by prefixing the heading with `[x] ` once the work lands. If the change altered the repo layout, also update the living `# Current folder structure` tree in `2026-05-28_monorepo-folder-structure.md` (bump `Last updated:` and add a `## Change log` entry). Do NOT regenerate that tree wholesale — Randy hand-edits it for readability (custom `##` section headings and intentionally pared-back detail under many folders). Make only the minimal edit matching the actual change (add / rename / remove the specific folder line) and preserve his existing formatting, `##` headings, and chosen level of detail; do not re-expand trimmed folders or re-add omitted subfolders. See the "Maintenance rule" note in that file's `# Current folder structure` section.
9. Commit per logical unit with a clear message and push to pare-down. Default to committing and pushing without waiting for confirmation, unless there is an important open question that genuinely needs answering first — and even then, err on the side of committing and pushing what is done (a follow-up commit can always be added).
10. Continuity: if during the session the user gives any instructions meant to persist for future sessions (changes to this plan, to the conventions, or to this "Context prompt" section itself), update this file so the next drag-and-submit session inherits them. Call out in your summary whether any such persistent updates were made.


## [x] Critical safety pre-work (do before any folder reorg)
Repository-root credential files (NOT git-tracked, but on disk):
- `client_secret_119941763167-c0oqkp63cv6elses4828p7fvthdqredv.apps.googleusercontent.com.json`
- `client_secret_119941763167-jmob7gtcjbpamdukm8in6ekfp72r154h.apps.googleusercontent.com.json`
- `floodlamp-gdrive-jackie-cce56b4f953f.json`
- `gdrive_service_account_fofgeneral20_personal.json`

These are Google OAuth client secrets and service-account keys. They are not currently tracked in git (verified). They sit at the working-tree root, where any future `git add .` could accidentally commit them.

Recommendation:
1. Verify `.gitignore` explicitly covers `*.json` at repo root or these specific filenames.
2. Move them out of the repo root entirely. Suggested location: `~/.config/corpus-tools/credentials/` (outside the repo). _chose different location `~/.config/credentials-gdrive/`_
3. Update any code that loads them to use absolute paths or `GOOGLE_APPLICATION_CREDENTIALS` env var.
4. If credentials may have been committed to any repo (this one or another), or shared via screenshare / paste, rotate them.

Do this before the new repo cutover regardless of folder reorg.

Open questions:
- Are these credentials still in active use? Where should they live?
_I don't think we've used them in a while, I'm not sure. I put them in a folder that was explicitly called `credentials-gdrive`._
- Have they ever been committed to any repo or shared elsewhere? If yes, rotate.
_Not Sure - It would be to this, only to this repo. And I think we're gonna rotate some API keys and other stuff so I'll look at these as well._


## Per-folder plan
Each section below: contents summary, recommendation, options (where the call depends on answers), open questions.

### [x] `web/` (residual after step 3b)
Current contents:
- Files: `hash.js`, `navigator.md`, `test_back-end_validation.md`, `test_back-end_validation_vrag-llm.md`, `test_front-end_validation_inputs.js`, `z_count_chars_in_js.sh`.
- Subdirectories: `_archive-web/`, `aws_chalice/` (covered separately below), `fasthtml/`, `local_dev/`, `md_to_html_dev/`, `md_view/`, `view_sources/`, `web_docs/`, `web_test_files/`, `webflow-site-downloads/`.

Recommendation: disperse and remove the top-level `web/` folder. The leftovers are QRAG-adjacent tooling, dev harnesses, exploratory pages, and historical Webflow downloads.
- `hash.js` — client-side HMAC helper used by QRAG flow → `apps/qrag/web/hash.js`.
- `test_back-end_validation_vrag-llm.md` — QRAG-specific → `apps/qrag/web/`.
- `test_back-end_validation.md`, `test_front-end_validation_inputs.js` — generic API/input validation docs. If QRAG-only on inspection → `apps/qrag/web/`. Otherwise → `web-shared/`.
- `navigator.md` — small note → inspect; likely QRAG.
- `z_count_chars_in_js.sh` — utility script → `scripts/`.
- `local_dev/` — Flask QRAG dev harnesses (already updated to import from `core.` in step 1) → `apps/qrag/dev/` or `apps/qrag/web/local_dev/`.
- `webflow-site-downloads/` — dated webflow downloads → `_archive/webflow-site-downloads/`.
- `_archive-web/` — already archive content → consolidate into `_archive/web/`.
- `fasthtml/`, `md_to_html_dev/`, `md_view/`, `view_sources/`, `web_docs/`, `web_test_files/` — classify each as QRAG/active/archive on inspection.

Once empty, delete the top-level `web/` folder so the layout is clean.

Open questions:
- Is `local_dev/` actively used?
_Not heavily, but treat it as active like the rest and move it over (no large files in here). → moved to `apps/qrag/web/local_dev/`._
- Are `fasthtml/`, `md_to_html_dev/`, `md_view/`, `view_sources/` still active or exploratory/dead?
_Keep `md_to_html_dev/` (it is consumed by `core/corpuses.py`) → moved to `web-shared/md_to_html_dev/`. Omit the rest: `fasthtml/` was an abandoned FastHTML demo attempt; `md_view/` was a one-off zero-md CMS embed experiment; `view_sources/` were saved rag-devpage view-source HTML snapshots I won't need. Each is noted in the MOVE_MANIFEST; if ever needed they remain in this repo's git history before cutover._
- Keep `webflow-site-downloads/` as historical reference or delete?
_Omit (delete). It is a dated full Webflow static-site export; not needed. Noted in MOVE_MANIFEST; recoverable from git history._
- Anything in `_archive-web/` worth reviving, or all archive?
_All archive — omit (delete). Noted in MOVE_MANIFEST; recoverable from git history._

Resolution (2026-05-30): top-level `web/` residual dispersed. QRAG-specific assets (`hash.js`, `navigator.md`, `test_back-end_validation.md`, `test_back-end_validation_vrag-llm.md`, `local_dev/`) → `apps/qrag/web/`; cross-app assets (`test_front-end_validation_inputs.js`, `md_to_html_dev/`, `web_docs/`, `web_test_files/`) → `web-shared/`; `z_count_chars_in_js.sh` → `scripts/`. Omitted/deleted (with notes in MOVE_MANIFEST): `_archive-web/`, `fasthtml/`, `md_view/`, `view_sources/`, `webflow-site-downloads/`. `web/` now contains only `aws_chalice/` (handled in its own section). Path references updated in `core/aws_valid.py`, `core/aws_valid_other-api-report-versions.py`, `core/corpuses.py`, and the `local_dev` harnesses.

Follow-up uncovered: `tests/test_fileops.py` still uses `@patch('primary.fileops....')` mock targets left over from the step-1 `primary/`→`core/` rename, causing 79 pre-existing `ModuleNotFoundError: No module named 'primary'` errors in the suite. Unrelated to this web/ work; should be fixed by retargeting those patches to `core.fileops`.


### [x] `web/aws_chalice/` (residual after step 3b)
Current contents:
- Active scripts and notes: `chalicelib_mirror_deploy.sh`, `chalicelib_mirror_deploy_composite_log.md`, `aws_notes.md`, `chalice_new_lambda_checklist.md`, `chalice_bug_deploy-with_manage IAM role false.md`, `aws_lambda_first.py`.
- Older variant: `chalicelib_mirror_deploy_03-29 w log.sh`.
- Lambdas not yet placed under their owning app: `hash-store/`, `hmac-hash/`, `send-email/`, `deepgram-callback/`, `testapp/`.
- Build artifacts: `langchain-layer/` (gitignored), `langchain-layer.zip`.
- Archive: `_archive chalice/`.

Recommendation per Lambda:
- `hash-store/`, `hmac-hash/` — tightly coupled to QRAG's privacy flow (PII hashing) → `apps/qrag/api/hash-store/` and `apps/qrag/api/hmac-hash/`.
- `deepgram-callback/` — Deepgram webhook used in QRAG ingestion → `apps/qrag/api/deepgram-callback/`.
- `send-email/` — generic transactional email; could serve multiple apps. Two options:
  - (A) Make it its own app: `apps/send-email/api/`.
  - (B) Keep at `web/aws_chalice/send-email/` as "shared infrastructure" until it has 2+ consumers. Recommended for now.
- `testapp/` — sandbox lambda. Likely `_archive/aws_chalice/testapp/` or delete after confirming unused.

Active scripts (chalice mirror deploy + notes) stay at `web/aws_chalice/`. The composite deploy log especially must stay there to keep history continuous.

Older / archive items:
- `chalicelib_mirror_deploy_03-29 w log.sh` — older variant → `_archive/aws_chalice/` or delete.
- `aws_lambda_first.py` — early example → likely archive.
- `_archive chalice/` — already archive content → consolidate into `_archive/aws_chalice/`.
- `langchain-layer.zip` — built artifact (rebuildable) → gitignore if not already; archive or delete.

Open questions:
- Confirm `hash-store`, `hmac-hash`, `deepgram-callback` are exclusively for QRAG (no cross-app use). If yes, move under `apps/qrag/api/`.
_No — `hash-store` and `hmac-hash` are general/cross-app (like `send-email`), so they stay at `web/aws_chalice/` as shared infrastructure, not under `apps/qrag/api/`. `deepgram-callback` is transcription-related → moved to a new `apps/transcription/api/deepgram-callback/`._
- Is `send-email` used outside QRAG? If only QRAG, move to `apps/qrag/api/send-email/`.
_Yes, treat as general/cross-app → stays at `web/aws_chalice/send-email/` as shared infrastructure._
- Is `testapp` still needed as a sandbox?
_No. Keep it (don't delete) since the tracked source is tiny (~484 KB; the only bulk was a single gitignored 18 MB deployment zip). Archived to `_archive/aws_chalice/testapp/`._
- Approve archiving / deleting the older mirror script variant?
_Archive, don't delete → `_archive/aws_chalice/chalicelib_mirror_deploy_03-29 w log.sh`._

Resolution (2026-05-31): `deepgram-callback/` → `apps/transcription/api/deepgram-callback/` (new `apps/transcription/` umbrella; `git mv` preserved history). `hash-store/`, `hmac-hash/`, `send-email/` confirmed general/cross-app and left at `web/aws_chalice/` as shared infrastructure pending a future owning app. `testapp/` and the dated `chalicelib_mirror_deploy_03-29 w log.sh` variant retired to `_archive/aws_chalice/` (gitignored; recoverable from git history before cutover). Chalice build-artifact gitignore rules generalized to any depth (`**/.chalice/deployed/`, `**/.chalice/deployments/`, `**/vendor/`, `**/langchain-layer/`) so relocated Lambdas keep artifacts ignored. Path references updated in `AGENTS.md` (directory guide), `PROJECTS.md` (Deepgram-callback row), `cloc_paths.txt`, and the `# cd ...` comments inside the moved `app.py` / `app_initial0347.py`.

Follow-up (2026-05-31) — leftovers documented as un-migrated rather than moved:
- `aws_lambda_first.py` — left in place, not migrated; one-sentence description recorded in MOVE_MANIFEST. It is the earliest (~April 2024) throwaway Lambda scratch file: three echo "Hello from Lambda" handlers (one JS `exports.handler`, two Python `lambda_handler` variants with floodlamp.bio CORS) from the first API Gateway + Webflow wiring.
- `_archive chalice/` (~373 MB) — not migrated to the new repo (stays in the frozen pre-cutover repo). A tracked stand-in inventory, `web/aws_chalice/_archive-chalice-contents.md`, describes its contents so an agent can decide whether to retrieve any item from frozen git history.
- `langchain-layer.zip` (~46 MB) — not migrated; rebuildable build artifact, langchain no longer in use. Noted in MOVE_MANIFEST only.

Follow-up (2026-05-31) — top-level `web/` retired: the whole `web/aws_chalice/` folder moved to `web-shared/aws_chalice/` and the empty `web/` root was deleted, so `web-shared/` is now the single shared web/infra home (subfolders `webflow/` for the Webflow shells and `aws_chalice/` for shared Lambdas + mirror script). The mirror script, its composite log, and `core/aws_valid.py`'s hardcoded paths were updated to the new location. See MOVE_MANIFEST Step 10. (The hash-store/hmac-hash/send-email Lambdas stay shared infra; their owning-app placement is still open.)


### [x] `secondary/`
Current contents (~25 files): runners (`run_bert.py`, `run_randy.py`, `run_k1.py`, `run_brandon.py`, `run_theresa.py`); exploratory (`agent_trial.py`, `assistants.py`, `assistant_settings.json`, `langchain.py`, `rag_langchain.py`, `streamlit_bots/`, `tkinter_minimal_test.py`); domain modules (`audio.py`, `speakerid.py`, `speakerid_scratch.py`, `video.py`); utilities (`gdrive.py`, `gdrive_mtests.py`, `helper.py`, `conversion_validator.py`); domain-specific scripts (`pvprogress.py`, `deutsch_well_gen.py`, `books_fix.py`, `create_chroma_db.py`); scratch (`max/` subdir).

Recommendation: split deliberately rather than keeping `secondary/` as a generic "less mature" tier:
- Per-user runners (`run_bert.py`, `run_randy.py`, `run_k1.py`, `run_brandon.py`, `run_theresa.py`) — personal workspace files. Either move to `apps/scratch/<user>/` or gitignore them since they are personal. Recommend: keep tracked for collaborator continuity but consolidate under one umbrella.
- Mature domain modules (`audio.py`, `gdrive.py`, `speakerid.py`, `video.py`) — if used by core consumers, promote to `core/`. If only used by exploratory scripts, leave or move to relevant app.
- Exploratory / abandoned (`langchain.py`, `rag_langchain.py`, `streamlit_bots/`, `assistants.py`, `assistant_settings.json`, `agent_trial.py`, `tkinter_minimal_test.py`) — `_archive/secondary/` if abandoned; `apps/experiments/` if still being tried.
- Domain-specific scripts (`pvprogress.py`, `deutsch_well_gen.py`, `books_fix.py`, `create_chroma_db.py`) — under the relevant area or app: `apps/pipelines/<name>/` or per-app folder.
- `helper.py`, `gdrive_mtests.py`, `conversion_validator.py`, `speakerid_scratch.py` — inspect; promote, archive, or delete.
- `max/` subdir — inspect; probably scratch.

Open questions:
- Which `secondary/` files are still actively used vs abandoned? (Most should likely move to `_archive/` or be deleted.)
_Split three ways: mature modules promoted to `core/`; per-user runners kept (tracked) under `apps/scratch/<user>/`; everything else (exploratory + abandoned + rough one-off domain scripts) archived to `_archive/secondary/`. See Resolution for the per-file list._
- Should `run_<user>.py` files be gitignored as personal scratch, or kept tracked for EA and other collaborators?
_Keep tracked (not gitignored) for collaborator continuity → `apps/scratch/<user>/run_<user>.py`._
- Promote `audio.py`, `speakerid.py`, `video.py`, `gdrive.py` to `core/`?
_Yes, promote all four. Also promote `gdrive_mtests.py` (it pairs with `gdrive.py`) and `transcript_eval.py` (library-shaped, its own file marker already pointed at `core/`)._
- Imports: step 1 already updated `from primary.X` to `from core.X` inside `secondary/*.py`. Any remaining import drift?
_Yes, two spots: `gdrive_mtests.py` still used bare `from fileops import *` / `from gdrive import *` (→ `core.*`), and `run_bert.py` imported `secondary.transcript_eval` / `secondary.audio` / `secondary.books_fix` (first two → `core.*`; `books_fix` commented out since it was archived). Consumers `voice/tts.py` (`secondary.audio`) and `docs/codeindex/create_codeindex.py` (`secondary.video`) retargeted to `core.*`._

Resolution (2026-05-31): `secondary/` dispersed and removed.
- Promoted to `core/` (`git mv`, history preserved): `audio.py`, `speakerid.py`, `video.py`, `gdrive.py`, `gdrive_mtests.py`, `transcript_eval.py`. `transcript_eval.py` was an unlisted file that appeared after this plan was written; it is a substantial library that imports `core.*` and whose own file marker already read `core/transcript-eval.py`, so it was promoted (marker normalized to `core/transcript_eval.py`).
- Per-user runners → `apps/scratch/<user>/` (kept tracked): `run_bert.py`→ea, `run_randy.py`→randy, `run_k1.py`→Kid1, `run_brandon.py`→bs, `run_theresa.py`→tl.
- `max/` → `apps/games/robo-polly/` (Robo-Polly game; `tv_robopoli_code.py`, `tv_robopoli_power-up.py`, `tv_robopoli_power-up-2.py`). New `apps/games/` umbrella; more is expected from another repo.
- Archived to `_archive/secondary/` (gitignored; recoverable from git history before cutover): exploratory/abandoned — `langchain.py`, `rag_langchain.py`, `streamlit_bots/`, `assistants.py`, `assistant_settings.json`, `agent_trial.py`, `tkinter_minimal_test.py`, `speakerid_scratch.py`; rough one-off domain scripts (agent's call) — `pvprogress.py` (PV PDF split, "NEEDS REVIEW"), `deutsch_well_gen.py` (one-off Obsidian md gen), `books_fix.py` ("buggy, unused 6+ months"), `create_chroma_db.py` (abandoned langchain); unused utilities — `helper.py`, `conversion_validator.py`, `webscrape.py`, `xcom.py`. None are imported by active code. The two area-specific scripts (`pvprogress.py`, `deutsch_well_gen.py`) were archived rather than promoted to an `apps/pipelines/` app because they are unmaintained module-level-execution one-offs, not maintained pipelines; pull them into an app later if a real pipeline emerges.
- `speakerid_scratch.py` is NOT an exact copy of `speakerid.py`: it is a rougher, incomplete earlier draft (stub bodies, an invalid-syntax line `link_youtube_url = #...`) while the promoted `speakerid.py` has the fuller implementations. Archived, as Randy expected.

Follow-ups recorded in `2026-05-30_post-file-organization-followup.md`: (1) hardcoded OpenAI API key in `create_chroma_db.py` needs rotation (already in git history); (2) pre-existing orphaned-line bug in `gdrive.py` was commented out to make `core.gdrive` importable.


### [x] `voice/`
Current contents: `tts.py`, `run_tts.py`, `video_capture.py`, `voices.txt`, `elevenlabs_voices.txt`, `kokoro/`, `captured_frames/`, `frame_log.md`, `frame_001 copy.png`, `elevenlabs_test.mp3`, `openai_tts_test.mp3`, oddly-named text files (`Testing the text to speech`, `You'll find more Softwood around my workshop and all over Patchi Forest!`), `PLAN_voice.md`.

Recommendation: this is more substantial than the AGENTS.md description suggests — it looks app-shaped. Promote to `apps/voice/` so it has the same shape as other apps (its own README, optional AGENTS.md, contained data).
- Test mp3s and `captured_frames/` content → if large, move to `data/voice/` (S3) and gitignore.
- Two oddly-named text files appear to be TTS prompts → `apps/voice/prompts/` or delete.
- `kokoro/` — if it contains model weights, gitignore (per file-types-to-exclude policy).

Open questions:
- Is `voice/` an active app or an exploratory area? If active → `apps/voice/`. If exploratory → `apps/experiments/voice/` or stay.
_Active app → `apps/voice/`._
- `kokoro/` contents — model weights or code?
_Both: code (`kokoro.py`) plus a downloaded model-weights folder (`kokoro models - gitignore/`, ~350 MB ONNX + voices). The weights folder is already gitignored (via the `**/*gitignore*/` catch-all) and stays local-only — carry it over but never track it. Generated kokoro mp3s (the loose test files + the `samples/` voice previews) go into a dedicated `kokoro/kokoro_audio/` folder that is also kept local-only._
- `captured_frames/` — data (gitignored, S3) or generated test output?
_Generated test output (~5 MB) from an old experiment reading on-screen text aloud from a video feed — frames captured for OCR→TTS. Keep local, do not track (no need for S3); gitignore it. Same for the loose `frame_001 copy.png` and the root test mp3s (`elevenlabs_test.mp3`, `openai_tts_test.mp3`)._

Resolution (2026-05-31): `voice/` promoted to `apps/voice/` (`git mv`, history preserved). Internal reorg: the two oddly-named TTS prompt text files → `apps/voice/prompts/`; loose kokoro test mp3s + `kokoro/samples/` → `apps/voice/kokoro/kokoro_audio/` (and `.../kokoro_audio/samples/`); stray `frame_001 copy.png` → `apps/voice/captured_frames/`. The `kokoro models - gitignore/` weights folder rode along untouched (still ignored by the `**/*gitignore*/` catch-all). All generated binaries were untracked with `git rm --cached` (kept on disk): every `*.mp3`/`*.wav` is already covered by the global media ignore, so only the frame PNGs needed new path rules — added `apps/voice/captured_frames/` and `apps/voice/kokoro/kokoro_audio/` to `.gitignore` (replacing the old `voice/captured_frames/` line). Path strings updated in `apps/voice/kokoro/kokoro.py` (model/voices paths, `samples` output dir, run-comment, mrun example), `apps/voice/video_capture.py` (`captured_frames`/`frame_log.md` literals), and a commented path in `apps/voice/tts.py`. Nothing elsewhere imports `voice` as a module, so no downstream import updates. `py_compile` passes on all four edited Python files. Docs updated: `AGENTS.md` (added `apps/voice/` to the apps list, removed the stale top-level `voice/` entry) and `cloc_paths.txt` (`voice/` → `apps/voice/`).

### [x] `lib/`
Current contents: `bindings/`, `tom-select/`, `vis-9.1.2/` — vendored third-party JS libraries.

Recommendation: keep as-is. Standard vendored-deps folder. Optionally rename to `vendor/` later for clarity, but not required.

Open questions:
- Are these still used by current Webflow custom code?
- Will future migration off Webflow change this? (Likely yes; defer.)

Resolution (2026-05-31): keep `lib/` as-is — no move. It is a small (~748 KB, under 1 MB) standard vendored-deps folder; nothing to disperse. The optional `vendor/` rename and any future-off-Webflow reconsideration are deferred (not blocking). Recorded in the living folder-structure tree at `2026-05-28_monorepo-folder-structure.md` § "Current folder structure".


### [x] `tests/`
Current contents: `test_fileops.py`, `test_llm.py`, `test_transcribe.py`, `testTEMPLATE.py`, `check_openai.py`, `deprecated_unittests.py`, `test_manual_files/`, `vectordb_test/`.

Recommendation: keep `tests/` as the shared/cross-cutting tests of `core/`. Per-app tests live at `apps/<app>/tests/` when apps add tests. Cleanups:
- `deprecated_unittests.py` → `_archive/tests/` or delete.
- `vectordb_test/` — inspect; if a test fixture, OK; if a one-off script, archive.
- `test_manual_files/` — keep with `tests/` if reasonable size; large fixtures move to `data/samples/` or S3.
- Verifying the suite (run `python -m unittest discover -s tests`) and repairing failures left over from the `primary/` → `core/` rename is now its own next-step task — see `2026-05-30_post-file-organization-followup.md` §1. As of 2026-05-30 the suite has 79 `ModuleNotFoundError: No module named 'primary'` errors from stale `@patch('primary.fileops....')` targets in `tests/test_fileops.py`. Run this after the folder moves settle, not blocking on each per-folder move.

Open questions:
- Set up CI now or defer (per `ai-coding-system-dev.md` §9)?
_Defer CI; recorded as a post-file-org follow-up item (see `2026-05-30_post-file-organization-followup.md` §3 "From the tests/ session")._
- `deprecated_unittests.py` — delete or archive?
_Delete. (Reviewed; it is dead — it calls `print_chars_with_indices`, a function from a long-gone module that it never even imports.)_
- `vectordb_test/` — fixture or one-off?
_Live fixture (referenced by `core/vectordb_mtests.py`). It belongs under the manual fixtures — move it under `test_manual_files/` as a `vectordb` subfolder, "where it should have been."_
- `test_manual_files/` (~39 MB) — keep, trim, or relocate to data/S3?
_Lean: keep as-is; they are curated fixtures deliberately kept for specific module tests. Wanted the per-folder size breakdown + a recommendation before finalizing (see size table + recommendation below)._

Resolution (2026-05-31) — done this session:
- `deprecated_unittests.py` → deleted (`git rm`).
- `vectordb_test/` → `git mv` to `tests/test_manual_files/vectordb/` (4 md fixtures, 44 KB). The two `tests/vectordb_test` path strings in `core/vectordb_mtests.py` (lines 16, 22) were retargeted to `tests/test_manual_files/vectordb`.
- CI setup deferred → recorded in `2026-05-30_post-file-organization-followup.md`.
- `tests/` stays the home of the shared `core/` suite (`test_fileops.py`, `test_llm.py`, `test_transcribe.py`, `testTEMPLATE.py`, `check_openai.py`); per-app tests go under `apps/<app>/tests/` later. Suite repair (the `primary`→`core` patch targets) and the S3/manifest checks remain in the post-file-org follow-up, not blocking here.
- `test_unit_files/` is an empty (0 B, untracked) placeholder dir — left in place; no action.

`test_manual_files/` size breakdown (per subfolder, all git-tracked; total 39 MB / 238 files + the new `vectordb/`):

| subfolder | size |
| --- | --- |
| pv_test_files | 18 MB (single `EPC_testing_packet.pdf` = 18 MB) |
| transcribe | 6.8 MB |
| file_conversion | 4.1 MB |
| zip_tests | 2.7 MB |
| megaparse_test | 2.1 MB |
| 1min youttube | 1.6 MB |
| jsons | 748 KB |
| timestamp_link_tests | 396 KB |
| rag | 356 KB |
| llm_test_files | 288 KB |
| copyedit_tests | 252 KB |
| docwork_tests | 240 KB |
| timestamp_double | 176 KB |
| get_files_tests / quote_tests | 152 KB each |
| misc | 84 KB |
| qatest | 76 KB |
| word_error_rate | 68 KB |
| folder_tests | 36 KB |
| markdown_tester | 32 KB |
| find_and_replace_from_csv_tests (+ copy) | 24 KB each |
| delete_tests | 16 KB |
| gdrive / write / youtube_tests | 8 KB each |
| mermaid / qrag_tests | 4 KB each |
| vectordb (moved in) | 44 KB |

Composition: **13 binary files (mp3/wav/pdf/docx/zip) = 33.8 MB**; **228 text fixtures (md/json/csv/txt/html) = 4.4 MB**. The one 18 MB PDF is ~47% of the folder.

Decision (2026-05-31, Randy): **keep `test_manual_files/` tracked as-is** — no relocation. 39 MB is modest, the fixtures are curated and live (referenced by `core/*_mtests.py`), and they are already in git history so removing them would not shrink `.git` anyway. Section is `[x]`.
- Noted for later: if working-tree size ever becomes a concern, the single 18 MB `pv_test_files/EPC_testing_packet.pdf` (≈47% of the folder) is the first relocation candidate to `data/test-fixtures/` (S3) + gitignore, optionally followed by the other 12 binaries (33.8 MB of the 39 MB total), leaving the 228 text fixtures (4.4 MB) tracked. Not doing it now.

### [x] `docs/` (~9 MB)
Current contents: `_build/`, `codeindex/`, `misc/`, `my_refs/`, `packages/`, `sphnix/`, `vis/`.

Recommendation: keep top-level. Specific cleanups:
- `_build/` (~1 MB) — auto-generated; gitignore if not already; verify nothing tracked.
- `codeindex/` (~7 MB) — keep `create_codeindex.py` (the generator); consider gitignoring the generated outputs (`all_source_code_dev.md`, `all_ast_trees_dev.md`, `all_graph_dev.json`, `column_layout_graph.html`, `all_user_defined_functions_dev.md`, `all_source_defs_docstrings_dev.md`) since they regenerate.
- `sphnix/` (<1 MB) — typo; rename to `sphinx/` (small `git mv`).
- `vis/` (<1 MB) — visualization code (`codebase_graph_vis.py`, `codebase_graph_vis.js`); active or archive?
- `misc/` (<1 MB), `my_refs/` (<1 MB), `packages/` (<1 MB) — inspect each.

Open questions:
- Track `docs/codeindex/` outputs in git or gitignore (regenerable)?
_Gitignore the regenerable outputs (kept on disk, untracked). Leave `docs/codeindex/_archive/` tracked as-is — it's already in git history and the dated snapshots are small enough to keep._
- Rename `docs/sphnix/` → `docs/sphinx/`?
_Yes — `git mv` typo fix. Only reference to "sphnix" anywhere in the tree was in this plan file; no code or config breaks._

Resolution (2026-05-31): `docs/` kept top-level. Targeted cleanups:
- `docs/codeindex/` — generator (`create_codeindex.py`) stays tracked. The 6 regenerable outputs (`all_ast_trees_dev.md`, `all_graph_dev.json`, `all_source_code_dev.md`, `all_source_defs_docstrings_dev.md`, `all_user_defined_functions_dev.md`, `column_layout_graph.html`) plus `create_codeindex_log.txt` were `git rm --cached`'d (kept on disk) and added to `.gitignore` under a new "docs/ generated outputs" section. `_archive/` of dated snapshots (~11 MB) left tracked as-is.
- `docs/_build/` — 25 tracked stale Sphinx HTML files (last touched 2024-11-01) were `git rm -r --cached`'d (kept on disk) and `docs/_build/` added to `.gitignore` in the same new section. Sphinx config in `docs/sphinx/` remains so the output can be regenerated.
- `docs/sphnix/` → `docs/sphinx/` (`git mv`, history preserved). Internal refs (`BUILDDIR=_build` in Makefile/make.bat, `exclude_patterns=['_build', ...]` in conf.py) are all relative and stayed correct; no `sphnix` string lived anywhere outside this plan file.
- `docs/vis/` — kept `codebase_graph_vis.py/.js` and the three example_graph_* files (active vis tooling for the codeindex graph). Moved `graphviz_and_example_OLD.py` and `module_based_network_OLD.html` to `_archive/docs-vis/` (gitignored; recoverable from git history before cutover).
- `docs/misc/` — kept `openai_reasoning_models.md` and `call_graph_incoming.svg`; deleted the empty 0-byte `call_graph.dot` (`git rm`).
- `docs/my_refs/` (`objects_pickle_json.md`) and `docs/packages/` (16 API/SDK reference notes — deepgram, openai, pinecone, webflow, pypandoc, speechbrain) — kept as-is. Small useful cross-cutting reference library.

Follow-up: none surfaced. The previously-recorded `docs/codeindex/create_codeindex.py` reference to `secondary.video` was already retargeted to `core.video` during the `secondary/` session (see that section's Resolution).


### [x] `dependencies/` (~2 MB)
Current contents: many dated `requirements_*.txt` snapshots, `get_direct_dependencies.sh`, `global_packages.txt`, `log_pip_install.md`, `code file copies/` (historical Python file snapshots used as reference).

Recommendation:
- Keep one canonical requirements: pick `requirements_2024-09-26_add_CURRENT.txt` as canonical, or migrate to `pyproject.toml` at repo root (lightweight; aligns with future packaging promotion path).
- Move historical snapshots into `_archive/dependencies/`.
- `code file copies/` (~1 MB) — historical snapshots of code now in `core/` → `_archive/code-file-copies/` or delete.

Open questions:
- Convert to `pyproject.toml` now or defer?
_Defer — recorded as a post-file-org follow-up item (see `2026-05-30_post-file-organization-followup.md`)._
- Approve archiving / deleting historical snapshots and `code file copies/`?
_Yes — archive the historical requirements snapshots (plus `global_packages.txt`, `log_pip_install.md`) to `_archive/dependencies/`; delete `code file copies/` outright._
- Which requirements file is canonical?
_The dictated answer was "the most recent one," but on inspection the most recent (`requirements_2025-12-19_1626 Randy.txt`) is a raw `pipreqs` dump that is structurally broken as an install file (bogus local-package entries `corpus_tools.egg`/`docs`/`secondary`, duplicate lines, and missing un-importable infra deps like `awscli`/`chalice`/`torch`/`speechbrain`/`flask`). Randy was shown this and chose to keep the hand-curated `requirements_2024-09-26_add_CURRENT.txt` (the one `setup.py` already reads) as canonical, with the real version refresh deferred to the pyproject migration._
- What about `get_direct_dependencies.sh`?
_Keep it in `dependencies/` but update its paths (`primary/` → `core/`) and drop the "code file copies" mirror step._

Resolution (2026-05-31): `dependencies/` pared to two files. Kept `requirements_2024-09-26_add_CURRENT.txt` as canonical (unchanged wiring in `setup.py`/`README_external.md`; its stale `# primary/*.py` provenance comments were normalized to `# core/*.py` and the Chalice path note to `apps/qrag/api/...`). Kept `get_direct_dependencies.sh` with paths updated to `core/`, the "code file copies" mirror step removed, and pipreqs now run directly on `core/`. Archived all older dated requirements snapshots + the 2025-12-19 pipreqs dumps + `global_packages.txt` + `log_pip_install.md` to `_archive/dependencies/` (gitignored; recoverable from git history). Deleted `code file copies/` (14 tracked file snapshots, redundant with git history). Removed the now-dead `code file copies` (and the also-dead `web/_archive-web/`) entries from `.vscode/settings.json`'s `python.analysis.exclude`. See MOVE_MANIFEST Step 15.

Follow-up recorded in `2026-05-30_post-file-organization-followup.md`: migrate dependency management to `pyproject.toml` and, as part of that, do a real requirements refresh (merge current installed versions, drop dead deps).


### [x] `scripts/` (<1 MB)
Current contents: `deutsch/`, `mirror-to-public-corpus-tools/`, `z_count_chars_in_js.sh`.

Recommendation: stop treating `scripts/` as a generic catch-all and disperse it (then delete it). The original Opus 4.7 Option B never actually defined `scripts/` — it was carried along as-is on the retained-folders line (`plans/, docs/, scripts/, tests/, voice/, lib/`), not designed. The ChatGPT Pro layout put repo/meta tooling in a dedicated `ops/` folder, but Option B intentionally deferred `ops/`. So each item gets a real home instead:
- `deutsch/` (<1 MB) — Deutsch corpus processing → `apps/deutsch/`.
- `mirror-to-public-corpus-tools/` (<1 MB) — repo-mirror tooling → `apps/repo-mirror/`.
- `z_count_chars_in_js.sh` — generic JS-char-count utility (Webflow custom-code size limits) → `web-shared/`.

Open questions:
- What's in `scripts/deutsch/`? Pipeline candidates → `apps/pipelines/`?
- Are any EA-runnable? If so, ensure runbook.md exists per the convention.
_Deutsch: even though it is a simple script now, more Deutsch work is coming, so make it an app — not a pipeline. Just `apps/deutsch/` and put it there._
- Where should the repo-mirror tooling live (no home under Option B)? Its own app, under an `apps/ai-coding-system/` umbrella, or a new top-level `ops/`?
_Its own app → `apps/repo-mirror/`. It is just a repo mirror, not AI-coding-system tooling, so don't bury it under an ai-coding-system umbrella. And delete the `scripts/` catch-all afterward — it no longer makes sense to keep it._

Resolution (2026-05-31): `scripts/` dispersed and the folder deleted (no longer a catch-all). `git mv` preserved history on all three:
- `scripts/deutsch/extract_boi_problems_snippets.py` → `apps/deutsch/extract_boi_problems_snippets.py` (new `apps/deutsch/` app; more Deutsch work expected). Its `Path(__file__).resolve().parents[2]` still resolves to the repo root from the new two-deep location, so no path edit was needed.
- `scripts/mirror-to-public-corpus-tools/` (`mirror_public_corpus_tools.py` + `public_corpus_tools_files_log.md`) → `apps/repo-mirror/` (new app, kept within Option B's apps + area-tag vocabulary rather than minting a top-level `ops/`). The script's `PRIVATE_ROOT = SCRIPT_DIR/../..` still resolves to the repo root from `apps/repo-mirror/` (also two deep), so only the docstring path references were updated (`scripts/mirror-to-public-corpus-tools/` → `apps/repo-mirror/`).
- `scripts/z_count_chars_in_js.sh` → `web-shared/` (loose cross-app web asset, alongside `test_front-end_validation_inputs.js`). Updated its own `file_path:` marker and usage/chmod comment to the new location.
- Empty `scripts/` (plus its stray `.DS_Store`) deleted.
- Docs updated: `AGENTS.md` (added `apps/deutsch/` and `apps/repo-mirror/` to the apps list; added `z_count_chars_in_js.sh` to the `web-shared/` loose-assets list) and the living folder-structure tree (removed the `scripts/` block; added `apps/deutsch/` and `apps/repo-mirror/`). No `scripts/` path references remained in tracked code (the `core/transcribe.py` / `smol_podcaster.py` hits were unrelated `transcripts/` strings; `cloc_paths.txt` had no `scripts/` entry).


### [x] `prompts/` (~2 MB)
Current contents: `README_prompts.md`, generic prompt files (`p-apply-code.txt`, `p-cmd-clean.md`, `p-code-eval-csv.md`, `p-code-eval-nocsv.md`, `p-code-org-v1.1.md`, ...), `_archive/`, `custom_instructions/`, `kids/`, `mckay/`.

Recommendation:
- Keep `prompts/` as the cross-cutting prompt-template library.
- App-specific prompt subfolders (`kids/` (~2 MB), `mckay/` (<1 MB) if a person/area-specific) might move to `apps/<app>/prompts/` or under the relevant area's app folder.
- `prompts/_archive/` (<1 MB) → consolidate into top-level `_archive/prompts/`.

Open questions:
- Are `kids/`, `mckay/`, `custom_instructions/` cross-cutting or app-specific?
- Are these prompts loaded by code anywhere (path references)? Moves require path updates.
_ANSWER: Okay, so I agree with this decision. Let's just keep prompts as a root level folder. And I can just leave it as is. Don't move the prompts under under apps. I think I could consider that later. I just let's just not do that now. And then I let's see here. I think just leave the _archive under prompts as well. So really there's... I think I've decided there's not anything to do here. If if you just... if I made a mistake or you disagree, I'm missing something, then just reply here. Otherwise there really really is indeed nothing to do here. Just check this one off as done._


### [x] `sounds/` (<1 MB)
Current contents: `remote_fail.wav`, `remote_success.wav` — UI/notification sounds.

Recommendation: move to wherever they're consumed. `grep` for `remote_fail.wav` / `remote_success.wav` to find consumer; if voice/TTS related → `apps/voice/sounds/`. If a CLI/notification helper in `core/` → `core/sounds/` or per-app folder.

Open questions:
- What plays these? Find the consumer first.
_ANSWER: I manually moved them ro apps/games/robopoli_


### [x] `security/` (<1 MB)
Current contents: `First-Web-ACL.json`, `aws_security-info.md`, `hash-store_security thread.md`.

Recommendation: keep top-level. Audit `First-Web-ACL.json` for sensitive content (account IDs, IPs, rule data) before any commit verification or future public publish.

Open questions:
- Is `First-Web-ACL.json` git-tracked? Confirm.
_Yes — all three files in `security/` are git-tracked (`security/First-Web-ACL.json`, `security/aws_security-info.md`, `security/hash-store_security thread.md`). `First-Web-ACL.json` is the exported AWS WAFv2 Web ACL config (a regional rate-based rule: block at 50 requests / 300s per IP) for the QRAG public-demo APIs._
- Does it contain sensitive identifiers needing redaction before publish?
_Yes — not live secrets, but identifiers that should be redacted before any public publish (no API keys, no credentials, and `USERS_HMAC_SECRET_KEY` appears by name only). Across the three files: the AWS account ID `[AWS-ACCOUNT-ID]` (in the WAF ARN/LabelNamespace and the SNS topic + subscription ARNs); the WAF Web ACL id/ARN; six API Gateway IDs (hash-store `[API-GATEWAY-ID]`, hmac-hash `[API-GATEWAY-ID]`, qrag-llm `[API-GATEWAY-ID]`, qrag-routing `[API-GATEWAY-ID]`, send-email `[API-GATEWAY-ID]`, vrag-llm `[API-GATEWAY-ID]`); four SNS subscription ARN UUIDs; the private S3 bucket name `[S3-BUCKET]`; and personal/collaborator emails (`[REDACTED-EMAIL]`, `randy@`/`contact@focusonfoundations.org`, `ea@`/`[REDACTED-EMAIL]`). Not an active leak: the repo is private and the public mirror (`apps/repo-mirror/`) only updates paths that already exist in the public clone — it never adds `security/`. Recorded as a pre-publish redaction follow-up (see `2026-05-30_post-file-organization-followup.md`)._
- Move to a future `infra/` folder or stay as-is?
_Stay as-is (top-level `security/`). Confirmed consistent with Option B: per `2026-05-28_monorepo-folder-structure.md` (Decision line, "Plan and next steps for implementation"), Option B was chosen over the heavier ChatGPT Pro layout that included `infra/`/`ops/`, intentionally deferring those folders with an incremental upgrade path "if/when specific overhead earns its keep." AWS code currently lives in `core/`; a future consolidation of `core/`'s AWS modules + `security/` into a top-level `infra/` remains a deferred, optional upgrade — not done now._

Resolution (2026-05-31): `security/` kept top-level — no move (audit + documentation only). Confirmed all three files are git-tracked and audited for sensitive content (see answers above): no live secrets, but AWS account/resource identifiers, the private bucket name, and personal/collaborator emails should be redacted before any public publish. Keeping `security/` as a root folder is consistent with the Opus 4.7 Option B decision (which deferred `infra/`/`ops/`); a future `infra/` consolidation is left as a deferred upgrade. Recorded a no-move note in `MOVE_MANIFEST.md` and a pre-publish redaction follow-up in `2026-05-30_post-file-organization-followup.md`. `security/` already appears in the living folder-structure tree; added a change-log entry there._


### [x] `ai-threads/` (<1 MB)
Current contents: dated AI conversation thread markdown files (e.g., `2026-01-23_cursor_vs_code_git_sync_problem.md`).

Recommendation: this overlaps `exchanges/`. Pick one home. Both are personal-knowledge-base material.
- Consolidate into one folder.
- Consider moving to a private notes location (Obsidian vault, separate notes repo, or S3 private bucket). Not all conversation history needs to live in this code repo.

Open questions:
- What's the difference between `ai-threads/` and `exchanges/`?
- Should AI conversation logs be tracked in this repo at all, or stored elsewhere?
_ANSWER: Okay, I do want to keep this folder, so I just put it under docs. And the reason AI conversation, I'm putting some conversation logs in here is because then they're easily available within my code editor within cursor which has integrated AI for troubleshooting, particularly the ones that are related to kind of coding and metacoding. So it's tiny, I just want to keep it and I might put more in here so nothing to do here._


### [x] `exchanges/` (~12 MB; PII subset git-ignored, bulk actually git-tracked)
Current contents: `_del/` (<1 MB), `deepseek/`, `pii_user_hash_log_2024-12-17.csv` (PII), `pii_user_hash_log_2024-12-17_test.csv`, QRAG corpus folders (`qrag_deutsch/`, `qrag_deutsch_early/`, `qrag_fda-c19-townhalls/`, `qrag_pv-evac/`, `qrag_sovereign-child/`), and `response_files/`.

Recommendation: keep `exchanges/` in place for now (it is QRAG usage data). Preserve the curated "selected list" in a manifest, route the data to S3, and route the PII to `[S3-BUCKET]`. The broader code/storage redesign is deferred.

Status correction (found this session): the "gitignored" label was wrong. Only the PII files are git-ignored (via `**/pii*` and `**/user_hash_log*`). The non-PII-named bulk (`exchange_jsons/`, non-PII `exchanges_*.db`, `response_files/` — **680 files** now; was 682 before `_del/`+`deepseek/` deletion) is currently **git-tracked**. They stay tracked — do NOT `git rm`/`git rm --cached` (see the HARD RULE above); they just won't be carried into the fresh new repo at cutover. The bulk of the count is `qrag_deutsch_early/` (464, mostly its 374-file `not-reviewed/`) + `response_files/` (40); the four small corpuses' `exchange_jsons/` are only ~168 combined.

Resolution (2026-05-31): documentation + targeted deletes only; no folder move and no code changes.
- Deleted `exchanges/_del/` and `exchanges/deepseek/` (`git rm` for the tracked files + cleared the ignored PII remnant in `_del/`).
- Created the "selected exchanges" manifest under the QRAG app: `apps/qrag/selected_exchanges_manifest.md` (per-corpus exchange sets, the `qrag_deutsch_early` triage buckets, `response_files/`, PII-file local-only/[S3-BUCKET] status, and the tracked-vs-ignored correction). This is the start of the list Randy does not want to lose.
- Recorded the S3 work in `2026-05-30_post-file-organization-followup.md` §2: (a) **PRE-cutover** — upload the selected exchanges + `response_files/` to S3 and record the prefix back in the manifest; (b) **PRE-cutover** — upload PII (`pii_user_hash_log_*.csv` + every `pii-exchanges_*.db`) to `[S3-BUCKET]`, then keep local copies out of the repo tree; (c) **POST-cutover** — the broader QRAG usage-tracking overhaul (how new data is produced). The S3 data upload is explicitly a must-do-before-cutover step.
- The 680 currently-tracked exchange files stay tracked — do NOT `git rm`/`git rm --cached` them (see the HARD RULE above). They simply won't be carried into the fresh new repo at cutover.
- `exchanges/` does not appear in the living folder-structure tree (it is data), so no tree edit; MOVE_MANIFEST gets a no-move/deletion note.

Open questions:
- Why are PII hash logs in the working tree? Move to S3 / encrypted storage?
_Leaving them git-ignored was deemed good enough to keep them out of the repo. Upload them (and every `pii-exchanges_<corpus>.db`) to the private `[S3-BUCKET]` S3 bucket; afterward keep the working copies outside the repo working tree so repo backups don't sweep them (Time Machine / local-disk backup is acceptable — secured by the machine login). No code changes this session — the QRAG code still writes these locally as designed. Recorded as a post-file-org follow-up._
- `_del/` — files staged for deletion?
_Yes — deleted. `_del/` was a staged-for-deletion duplicate; the live copies remain under `qrag_deutsch/`. Also deleted `deepseek/` (a one-off reasoning test). Both done this session._
- Consolidate `exchanges/` and `ai-threads/`?
_No. `ai-threads/` was kept under `docs/` (see its section); `exchanges/` is QRAG usage data with a different lifecycle (S3 migration) and stays separate._

_Original dictated answer (preserved):_
_ANSWER: Okay, so these are QRAG exchanges and they are listed as gitignore apparently. So I think we are going to need to upload these to Amazon S3 and I think put this list. So these are selected ones, that's an important thing and I don't want to lose this list. So I think create the manifest for these and put them under the QRAG application as selected exchanges and then put into the post file organization follow up. I mean there's going to be a bunch of stuff that needs to be uploaded to S3 and manifest that are created. So just make sure that this entry gets put in there and just create the start of the manifest list under the QRAG application. Okay, so that's for the actual markdown files. Let me see here. You can delete the one that's underscore D-E-L and the deep sequence for a test. Yeah, and these do span different applications, different QRAG corpuses. So I'm not sure what to do with that. Just put them under the QRAG. Okay, so that's that and now for the PII, I thought of, I mean, if you're asking why the hash logs are in the working tree. So I thought it was good enough just to leave them in that gitignore So that they're not put up in the repo I guess Yeah, we can upload them to Amazon S3 and put them in FOF secure And then I Guess if I download them keep them out of the repo folder on my local disk so that they're not unintentionally backed up although they you know, they're gonna get backed up in my like Mac time machine or however I back up my local machine, but then that's secured by the user Password and such so I guess that's good enough So Yeah create the follow-up post file organization follow-up item to take care of that and then you know organize these Kind of files as what's appropriate here But you know the code is set up to create these now So, you know, I don't want to get into changing the code now here at this stage so I don't know tell me kind of like what my options are Yeah, I think you know, I want to overhaul how I'm you know updating and managing that, you know the tracking of the of the You know usage of the qrack application. It's not and so that's a whole I mean, that's really what the The follow the post file organization follow-up is gonna be but that that I'm probably gonna push off to you know Well after the cutover, that's like a that's a project, you know That will come about when I want to work on kind of like the qrack application itself Okay, so, you know figure out what to do if you think it's clear what to do then Do it and just tell me and ask me to confirm if you if you really think You need to to present me with some options and ask follow-up Questions to determine what to do then do that instead._


### [x] `_archive/` (gitignored, ~19 MB)
Current contents: `2025-01-17_transcribe_depreacted dg callback w lambda/` (<1 MB), `backup_2024-12-09_git problems/` (<1 MB), `refactor_idaho_2024-07-08/` (<1 MB), `aws_chalice/` (~18 MB — the bulk of this folder), `secondary/` (<1 MB), ...

Recommendation: keep as the explicit retired-code area. Add `_archive/README.md` with the rule "Agents must not modify archived projects unless explicitly instructed; do not import from archived code into active code." (Per the ChatGPT Pro recommendation in `2026-05-28_monorepo-folder-structure.md` §3.)

Open questions:
- Anything in `_archive/` that should be deleted entirely vs kept for reference?
- Enforce "no agent modifies archive" via hook or just document in README?
_ANSWER: Okay, so the last thread on the exchanges, I clarified kind of what the plan was with this cutover. I mean, we're paring down the repo. We're not changing the git history on Corpus Tools because it's going to be frozen. And then we're just going to make a shallow copy over to the new repo. So I'm a bit confused by kind of your comments here. So I want to have a conversation about them. You say, "Keep this as an explicit retired code area." Yeah, I think I do want to keep underscore archive in the new repo. But I don't think I want to keep this stuff that's in here. I don't think we need to copy it over. So I don't think it Should be included in what's copied over to the new repo, meaning the cutover. And that means, you know, it needs to be deleted here, but I think it is because it's showing up as grayed right now in my Explorer here. So I think that means it's on my disk but not actually, you know, tracked or it wouldn't be part of a shallow, you know, clone that's copied over. Is that correct?. Okay, so I'm checking in the original folder structure proposed for the recommendation option B over in the monorepo folder structure under opus 4.7 there was no underscore archive. How is this usually dealt with in as sort of best practice in a monorepo like this? Because I mean what I have been doing is saying okay this isn't the active code but I might, you know, I'm not, I don't want to delete it so that I can't see it in the current copy of the repo and I have to go back and get history to find it so I want it kind of available but it's not active and so I'm going to just, you know, put it in the archive folder as this, you know. So it's still accessible but out of the way but perhaps I should stop doing that. I mean I could do it on a per application basis, you know, I'm not sure what's the best way to handle this. I mean, one thought I have is that you can make just a manifest of the folders that are in here under archive. You can just have that, you know, save that as a markdown file, which will be very small in file size. And then it can just say what these folders are and in the short description what was in there so that, you know, at cut over if for some reason we ever need to go back and look at any of the stuff like, you know, in our new repo we have just the kind of manifest of what was in here in case. So I think that's probably, you know, good to do. I see, I think secondary is just like a copy of all of those at some point. So I don't think we need to worry about that one. I mean, same thing for DocViz. Doc's viz. The backup git problems looks empty now. AWS Chalice one. We don't need to keep that. I'm not worried about it. Yeah, I don't think we need the trans... You know what? On further look at this I just think we don't need to carry any of this over. But for some reason I need to look back at history stuff. I'll have to come over to this frozen Corpus Tools repo anyway. So let's just not worry about it here. But I do want you to tell me kind of in best practice how this is type of archives thing that I did before. Typically done, what should my kind of new policy be? Should I create a folder called _archive and do the same thing I did before? It seems like that's not the best. Because it's just too easy to keep dragging stuff into there and then just end up with bloat. Although that's not really bloat because that stuff is in the git history anyway. It's just, I don't know, it seems like I'd be better off making markdown file notes that refer to that stuff and using agents to go back into git history to get it and use it as I need it, since that's a lot easier to do now that the AI coding agents are so good. Okay, help me out and explain what the options are here and what the best practice is, what I should do._

Resolution (2026-05-31): no action; `_archive/` is gitignored (`.gitignore:113`) with 0 tracked files, so it is local-only and will not be carried into the new repo at cutover (confirmed). Decided to carry **none** of the current contents over (`aws_chalice/` ~18 MB is the bulk; rest are small dated/deprecated folders, `secondary/`, `dependencies/`, `docs-vis/`). No manifest of the current contents — if old `_archive/` material is ever needed, recover it from the frozen corpus-tools repo / git history. New-repo archive policy (delete + rely on git history/tags, optional small ledger, S3 for large non-code artifacts, and reserving a physical `_archive/` only for browse-often reference material) is understood but deferred — it belongs with later version-control / release / mature code-management work, not this pare-down. Not updating `AGENTS.md` or the `.gitignore` comment now.


### [x] `plans/` (~2 MB)
Current contents: many dated `PLAN_*.md` files, `2025-03-14_aws-prod/` (<1 MB), `2026-04-09_repos-reorg/` (<1 MB) (this work), `FloodLAMP Closeout/` (<1 MB), `merge-prep-incoming-repos.md`, `2026-01-23_cursor_vs_code_git_sync_problem.md`, ...

Recommendation: keep top-level `plans/` for planning documents. Low-priority cleanup:
- Group dated `PLAN_*.md` files into `plans/_archive/` once the work is done.
- Add `plans/README.md` describing convention (dated single-file plans for one-shot work; named subfolders like `2026-04-09_repos-reorg/` for multi-doc plans).

Open questions:
- Worth tidying now, or wait until plans grows further?
_ANSWER: So I think since this is small, it's only about two megs, I think I just want to keep this plan folder as is and bring it over. You know, maybe I'll be moving some of the stuff in the repos reorg out, just like right before cut over, but I'm not sure yet. So put that in the post file organization to consider moving stuff out of the repos reorg just prior to cut over. But besides that, I don't want to reorg these, I don't want to kind of cull them, I don't think I need to and I like how they're organized now. So, yep. Yeah, nothing, so I think nothing to do here except just updating the post file organization follow-up markdown file._

Resolution (2026-05-31): no reorg or culling — keep `plans/` as-is and carry it into the new repo. No `plans/_archive/` grouping and no `plans/README.md` (the current organization is liked as-is). Only follow-up: a PRE-CUTOVER note to consider trimming `2026-04-09_repos-reorg/` contents just before cutover, recorded in `2026-05-30_post-file-organization-followup.md` ("From the `plans/` session").


### [x] `_xfer gitignore/` (~40 MB)
Current contents: `2025-01-27_RT morning.mp3`, `.wav`, `.md`, `process_notes.py`.

Recommendation: this is a one-off transfer area (folder name signals "transfer, gitignored"). Either move contents to where they belong (transcript material → `data/<project>/` → S3; `process_notes.py` → `scripts/` or relevant app), or delete the folder if no longer needed.

Open questions:
- What was this transfer for? Is it complete?
- Can the contents move to `data/`/S3 and the folder be removed?
_ANSWER: Okay, so I figured out what this was. This one is...this one was a test to like process a personal message. This one, um...this one is related to an app that I actually want to create related to a kind of a voice memo router. It's kind of an important and cross-cutting project. So, let me take a look at what the process note's PY is. This thing is just converting the words to MP3. Yeah, we don't need to keep this, so that's okay. I'm not worried about the Python code at all. It's just...hey, what's that? Two lines. So, um...I think we just ignore this and we don't carry it over. It just, you know, sits here on my disk. I may just move it...you know what? I think I'm just gonna move it out of this repo and then... delete it since it was a personal message. Okay._


### Auto-generated / config dirs (no action needed)
Confirmed not tracked or already handled:
- `.git/`, `.venv/`, `.venv_python12/` — local dev (not tracked).
- `.cursor/`, `.devcontainer/`, `.vscode/` — IDE config (mostly tracked, OK).
- `__pycache__/` (root + per-folder) — auto-generated; verify gitignored everywhere. Note: root `__pycache__/` contains a 90 MB `chroma.sqlite3` which should be confirmed gitignored.
- `corpus_tools.egg-info/` — `setup.py` output; gitignore if not already.
- `node_modules/` — npm install output; off-limits.
- `data/`, `logs/` — gitignored data per the file-types-to-exclude policy.
- `_misc_to_be_sorted/`, `limbo/`, `ms-graphrag/`, `lancedb/`, `pretrained_models/` — gitignored / off-limits.


## Root-level files (not folders) — quick disposition
Tracked at root (verify and decide each):
- `AGENTS.md`, `CLAUDE.md`, `README_external.md`, `README_internal.md` — keep.
- `setup.py` — keep, but consider migrating to `pyproject.toml` (see `dependencies/` section).
- `__init__.py` — vestigial top-level package marker; verify needed; otherwise delete.
- `run_sovereign_child_html.py` — root-level one-off → `apps/pipelines/sovereign-child-html/` or `scripts/`.
- `cloc_count.sh`, `cloc_paths.txt`, `cloc_report.md` — code-counting tooling/output. Keep tooling at root or move to `scripts/`. The output (`cloc_report.md`) regenerates; consider gitignore.
- `chalicelib_mirror_deploy_log.md` — orphan log at root (composite log lives at `web/aws_chalice/`); verify and either delete or merge into the actual composite log.
- `package.json`, `package-lock.json` — Node.js package files. Verify what they declare; if minimal/unused, consider removing. If actively used, document what they're for.

On disk but not tracked (action required, see "Critical safety pre-work"):
- `client_secret_*.json`, `gdrive_service_account_*.json`, `floodlamp-gdrive-jackie-*.json` — credentials.

Auto-generated at root:
- `__pycache__/` — gitignore confirmation.


## Suggested execution order
Tackle higher-risk and higher-impact items first; cosmetic ones last. Each line is roughly one focused coding session.

1. Critical safety pre-work — credentials moved out of repo, `.gitignore` verified.
2. `web/aws_chalice/` residual Lambdas — finish QRAG cohesion (hash-store, hmac-hash, deepgram-callback). Decide on `send-email` and `testapp`.
3. `web/` residual — disperse to `apps/qrag/`, `web-shared/`, `_archive/`. Empty top-level `web/` afterward.
4. `secondary/` — split into archive vs core promotion vs personal-scratch.
5. `voice/` — promote to `apps/voice/`.
6. `tests/`, `docs/`, `dependencies/`, `prompts/`, `scripts/` — cleanups (lower urgency).
7. `security/`, `sounds/`, `ai-threads/`, `_archive/` — small cleanups.
8. `_xfer gitignore/` and root-level cleanup — last.

Each session should leave the migration plan in this file updated (mark sections completed and note any new questions or follow-ups uncovered).
