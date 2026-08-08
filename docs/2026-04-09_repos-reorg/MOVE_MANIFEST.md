file: MOVE_MANIFEST.md
title: Folder-and-file move manifest for the Option B reorg

Running mapping of where things moved during the corpus-tools Option B reorg (started 2026-05-29 on branch `pare-down`). Append a new section per move session.

Conventions:
- Folder-level entries when a whole folder moved as a unit.
- Individual file entries only when they didn't follow their parent folder, or when the move requires special context.
- "Affected non-move files" lists files whose contents were edited (imports, file markers, path strings, dev URLs) without moving — kept short, not exhaustive.
- Each section notes the commit (or "manual" for ungoverned moves done outside agent commits).
- "out-of-repo" means the destination is outside the working tree (e.g., credentials moved to a user-config location).


## Step 1 — `primary/` → `core/`
Commit: `d051eefe` (2026-05-29).

Folder moves:
- `primary/` → `core/` (entire folder, 21 modules).

Affected non-move files:
- All `core/*.py` `START OF FILE` / `END OF FILE` markers updated.
- Imports updated in `tests/test_*.py`, `tests/testTEMPLATE.py`, all `secondary/*.py`, `voice/tts.py`, `apps/meta_coder/meta_coder.py`, `apps/math_quiz/math_quiz.py`, `apps/math_quiz/math_quiz.ipynb`, `apps/ads_scrape/extract_url.py`, `run_sovereign_child_html.py`, `web/local_dev/flask_qrag_deutsch_v1_create_html.py`, `flask_qrag_deutsch_v2_no_create_html.py`, `docs/codeindex/create_codeindex.py`.
- `web/aws_chalice/chalicelib_mirror_deploy.sh` updated (`FILES_TO_COPY` paths, heredoc imports, sed replacement pattern).
- `AGENTS.md`, `cloc_paths.txt` updated.

Verification: all 14 active core modules import cleanly under `.venv`.


## Step 2 — `projects/` → `apps/` + family umbrella
Commit: `f7a95b1d` (2026-05-29).

Folder moves:
- `projects/` → `apps/` (entire folder).
- `apps/Kid1/` → `apps/family/Kid1/`.
- `apps/reading/` → `apps/family/reading/`.

Apps that simply followed the parent rename (no further restructuring): `ads_scrape`, `live_transcript`, `math_quiz`, `meta_coder`, `minecraft`, `smol_podcaster`, `wingspan`.

Affected non-move files:
- `core/conversion.py` (mrun_combine_files_into_md path strings).
- `apps/meta_coder/meta_coder.py` (default `folder_path` argument).
- `apps/math_quiz/*.css`, `*.js`, `*.py`, `*.md` (file markers and dev URL paths).
- `apps/wingspan/*.md` (file markers).
- `AGENTS.md`, `cloc_paths.txt`.


## Step 3a — `chalicelib_mirror_deploy.sh` refactor
Commit: `7ec03ad1` (2026-05-29).

No file or folder moves. Refactored `web/aws_chalice/chalicelib_mirror_deploy.sh` to use `find_repo_root()` and `CHALICE_APP_REL` so Chalice apps can live at any depth (precondition for step 3b).


## Step 3b — QRAG physical move + `web-shared/`
Commit: `21534aad` (2026-05-29).

Folder moves (3 Chalice Lambdas):
- `web/aws_chalice/qrag-llm/` → `apps/qrag/api/qrag-llm/`.
- `web/aws_chalice/qrag-routing/` → `apps/qrag/api/qrag-routing/`.
- `web/aws_chalice/vrag-llm/` → `apps/qrag/api/vrag-llm/`.

QRAG-specific Webflow files moved as a group (`web/<file>` → `apps/qrag/web/<file>`):
- `webflow-rag-devpage.js` and 3 dated variants (`_2025-02-27.js`, `_Gateway-Timeout.js`, `_dev-api-urls.js`).
- `webflow-qrag-input-component-date-embed.html`.
- `webflow-dummy-qrag-embed.html`.
- `webflow-local-dev.html` (QRAG dev harness despite the generic-looking name).
- `webflow-local-dev-qrag-deutsch.html`.
- `functree_webflow_qrag-deutsch-v3-2step.md`.

Cross-app Webflow shells moved as a group (`web/<file>` → `web-shared/<file>`):
- `webflow-fof-site-head.html`, `webflow-fof-site-head_2-5.html`.
- `webflow-fof-site-body.js`.
- `webflow-fof-home-body.html`, `webflow-fof-home-body_users.html`.
- `webflow-fof-log-in.html`.
- `webflow-cms-template-embed.html`, `webflow-cms-template-embed-fda-vth.html`, `webflow-cms-template-van11y-accordion.html`.
- `webflow-custom-code-template.html`.
- `webflow-privacy-consent-embed.html`.

Stayed at `web/aws_chalice/` (placement deferred to a later session — see `2026-05-30_followup-folder-organization.md`):
- `hash-store/`, `hmac-hash/`, `send-email/`, `deepgram-callback/`, `testapp/`.
- `chalicelib_mirror_deploy.sh` and `chalicelib_mirror_deploy_composite_log.md` (intentionally shared regardless of where individual Chalice apps live).

Affected non-move files:
- `apps/qrag/web/webflow-local-dev.html` and `apps/qrag/web/webflow-local-dev-qrag-deutsch.html`: relative paths to `webflow-fof-site-head.html` and `webflow-fof-site-body.js` updated to `../../../web-shared/`.
- `web/z_count_chars_in_js.sh`: example usage path updated.
- `AGENTS.md`, `cloc_paths.txt`: directory references updated.


## Step 4 — `AGENTS.md` Option B convention section
Commit: `a9100d63` (2026-05-29).

No file or folder moves. Added "Repo layout convention (Option B)" section, updated chalicelib mirror note (refactor reference), and updated working-branch reference (`primo` → `pare-down`).


## Step 5 — `PROJECTS.md` portfolio map
Commit: `e7e23326` (2026-05-29).

No file or folder moves. Replaced the prior sketches with structured Areas + Projects index + Shared components + Project records.


## Followup plan added
Commit: `974a5800` (2026-05-30).

New file (no moves): `plans/2026-04-09_repos-reorg/2026-05-30_followup-folder-organization.md`.


## Move manifest added
Commit: pending (this commit, 2026-05-30).

New file (no moves): `plans/2026-04-09_repos-reorg/MOVE_MANIFEST.md` (this file).


## Manual moves done outside agent commits
### Credential cleanup (2026-05-30)
Untracked credential files moved out of the repo root by Randy. None were git-tracked, so the file moves themselves had no commit. The accompanying code and `.gitignore` updates that point at the new location landed in the commit recorded under "Step 6 — Credential cleanup follow-up" below.

Files relocated (`<repo-root>/<file>` → `~/.config/credentials-gdrive/<file>`):
- `client_secret_119941763167-c0oqkp63cv6elses4828p7fvthdqredv.apps.googleusercontent.com.json`.
- `client_secret_119941763167-jmob7gtcjbpamdukm8in6ekfp72r154h.apps.googleusercontent.com.json`.
- `floodlamp-gdrive-jackie-cce56b4f953f.json`.
- `gdrive_service_account_fofgeneral20_personal.json`.


## Step 6 — Credential cleanup follow-up
Commit: pending (this commit, 2026-05-30). Step 1 of `2026-05-30_followup-folder-organization.md`.

No file/folder moves in git. Code and config updates that pair with the manual credential relocation above:
- `.gitignore`: added two explicit `client_secret_*.json` filenames as a belt-and-suspenders safety net alongside the pre-existing `client_secret_*.*` wildcard.
- `core/transcribe.py`: load `client_secret_*.json` from `~/.config/credentials-gdrive/` via `os.path.expanduser`.
- `secondary/gdrive.py`: introduced `GDRIVE_CREDENTIALS_DIR = ~/.config/credentials-gdrive` and rewrote the two key-path constructions to use it.
- `plans/2026-04-09_repos-reorg/2026-05-30_followup-folder-organization.md`: marked Critical safety pre-work `[x]`, recorded the destination, answered open questions, and added a "Append to MOVE_MANIFEST.md" step to the new-session context prompt.


## Step 7 — `web/` residual dispersal
Commits: `d6d6bce3`, `8b89b128`, `d9f83d75`, `992ca0fa` (2026-05-30). Step 3 of `2026-05-30_followup-folder-organization.md`. Docs/manifest update in the following commit.

QRAG-specific assets (`web/<x>` → `apps/qrag/web/<x>`) — commit `d6d6bce3`:
- `hash.js`, `navigator.md`, `test_back-end_validation.md`, `test_back-end_validation_vrag-llm.md`.
- `local_dev/` (entire folder — Flask QRAG dev harnesses + van11y accordion test pages).

Cross-app assets (`web/<x>` → `web-shared/<x>`) — commit `8b89b128`:
- `test_front-end_validation_inputs.js` (mirrors the shared `webflow-fof-site-body.js` input validation).
- `md_to_html_dev/` (entire folder — transcript md→html dev; `additions_*.html` templates are consumed by `core/corpuses.py`).
- `web_docs/` (privacy-policy / terms-of-service markdown).
- `web_test_files/` (Closer-to-Truth transcript md-conversion test fixtures).

Utility script (`web/` → `scripts/`) — commit `d9f83d75`:
- `z_count_chars_in_js.sh`.

Omitted / deleted (commit `992ca0fa`; not carried into the reorg, recoverable from git history before cutover):
- `_archive-web/` — old pre-general-QRAG Webflow JS/HTML archive (rag-devpage variants, validation experiments, embed history). All archive.
- `fasthtml/` — abandoned FastHTML demo of the RAG devpage (single `demo-rag-devpage/main.py` prototype).
- `md_view/` — one-off zero-md CMS embed experiment for rendering a markdown transcript on Webflow.
- `view_sources/` — saved rendered "view source" HTML snapshots of the rag-devpage captured during dev.
- `webflow-site-downloads/` — dated full Webflow static-site export (`2024-10-16_1830/`).

Affected non-move files:
- `core/aws_valid.py`, `core/aws_valid_other-api-report-versions.py`: default `output_file` → `apps/qrag/web/test_back-end_validation.md`.
- `core/corpuses.py`: `add_additional_html_from_template` paths → `web-shared/md_to_html_dev/additions_{transcript,qa}.html`.
- `apps/qrag/web/local_dev/` Flask harnesses + `index*.html`: internal `web/local_dev` path strings → `apps/qrag/web/local_dev`.
- `scripts/z_count_chars_in_js.sh`: self-referencing `file_path` / chmod comment paths.
- `AGENTS.md`: directory guide updated (web-shared contents; `web/` now holds only `aws_chalice/`).

Note: the public-mirror log `scripts/mirror-to-public-corpus-tools/public_corpus_tools_files_log.md` still lists the old `web/test_back-end_validation.md` path; it is auto-generated output and was intentionally not hand-edited.


## Post-reorg followup plan added
Commit: pending (this commit, 2026-05-30).

New file (no moves): `plans/2026-04-09_repos-reorg/2026-05-30_post-file-organization-followup.md` — tracks post-move verification/cleanup (starting with running the test suite and fixing the stale `primary` patch targets). Also updated the `tests/` section of `2026-05-30_followup-folder-organization.md` to point at it.


## Step 8 — `web/aws_chalice/` residual Lambdas
Commits: `46ff78c5`, `3130020a` (2026-05-31). Step 2 of `2026-05-30_followup-folder-organization.md`. Docs/manifest update in the following commit.

Folder move (transcription Lambda) — commit `46ff78c5`:
- `web/aws_chalice/deepgram-callback/` → `apps/transcription/api/deepgram-callback/` (new `apps/transcription/` umbrella; `git mv` preserved history).

Archived (commit `3130020a`; moved into gitignored `_archive/aws_chalice/`, recoverable from git history before cutover):
- `web/aws_chalice/testapp/` → `_archive/aws_chalice/testapp/` — unused sandbox Lambda; tracked source ~484 KB, only bulk was a gitignored 18 MB deployment zip.
- `web/aws_chalice/chalicelib_mirror_deploy_03-29 w log.sh` → `_archive/aws_chalice/` — superseded dated mirror-script variant.

Stayed at `web/aws_chalice/` (confirmed general/cross-app shared infrastructure; placement under an owning app deferred until a 2nd consumer or clear owner):
- `hash-store/`, `hmac-hash/`, `send-email/`.

Not addressed this session (deferred): `aws_lambda_first.py`, `_archive chalice/` (~373 MB), `langchain-layer.zip` (~46 MB).

Affected non-move files:
- `.gitignore`: generalized Chalice build-artifact ignores to any depth (`**/.chalice/deployed/`, `**/.chalice/deployments/`, `**/vendor/`, `**/langchain-layer/`) so relocated Lambdas keep artifacts ignored.
- `AGENTS.md`: directory guide — added `apps/transcription/api/`; `web/aws_chalice/` line now lists only the shared Lambdas (hash-store, hmac-hash, send-email).
- `PROJECTS.md`: Deepgram-callback row path → `apps/transcription/api/deepgram-callback/` and area tag → transcription.
- `cloc_paths.txt`: `deepgram-callback/app.py` path updated.
- `apps/transcription/api/deepgram-callback/app.py`, `app_initial0347.py`: `# cd ...` invocation comments updated to the new path.

Note: `cloc_report.md` still lists the old `web/aws_chalice/deepgram-callback/app.py` path; it is auto-generated output and was intentionally not hand-edited.


## Step 9 — `web/aws_chalice/` un-migrated leftovers documented
Commit: pending (this commit, 2026-05-31). Follow-up to Step 8 of `2026-05-30_followup-folder-organization.md`.

No folder moves. The remaining `web/aws_chalice/` leftovers are left in place and explicitly marked **not migrated** to the new repo (they stay in the frozen pre-cutover repo's history):
- `aws_lambda_first.py` — NOT migrated, left in place. Earliest (~April 2024) throwaway Lambda scratch file: three echo "Hello from Lambda" handlers (one JS `exports.handler`, two Python `lambda_handler` variants with floodlamp.bio CORS) from the first API Gateway + Webflow wiring.
- `_archive chalice/` (~373 MB, 2024-vintage) — NOT migrated. New tracked stand-in created: `web/aws_chalice/_archive-chalice-contents.md` inventories the folder (`helloworld/`, `bot-reply/`, `qrag-deutsch-v3/`, `chalicelib_mirror_deploy_2024-10-03.sh`) so an agent can decide whether to pull any item from frozen git history.
- `langchain-layer.zip` (~46 MB) — NOT migrated; rebuildable build artifact, langchain no longer in use. Recorded here only.

New file (tracked): `web/aws_chalice/_archive-chalice-contents.md`.


## Step 10 — `secondary/` dispersal + removal
Commit: pending (this commit, 2026-05-31). `secondary/` section of `2026-05-30_followup-folder-organization.md`.

Promoted to `core/` (`git mv`, history preserved):
- `secondary/audio.py` → `core/audio.py`.
- `secondary/speakerid.py` → `core/speakerid.py`.
- `secondary/video.py` → `core/video.py`.
- `secondary/gdrive.py` → `core/gdrive.py`.
- `secondary/gdrive_mtests.py` → `core/gdrive_mtests.py` (pairs with `gdrive.py`).
- `secondary/transcript_eval.py` → `core/transcript_eval.py` (unlisted file added after the plan; library-shaped, marker already pointed at core).

Per-user runners → `apps/scratch/<user>/` (`git mv`, kept tracked):
- `run_bert.py`→`apps/scratch/ea/`, `run_randy.py`→`apps/scratch/randy/`, `run_k1.py`→`apps/scratch/Kid1/`, `run_brandon.py`→`apps/scratch/bs/`, `run_theresa.py`→`apps/scratch/tl/`.

Game → `apps/games/robo-polly/` (`git mv`; new `apps/games/` umbrella, more expected from another repo):
- `secondary/max/tv_robopoli_code.py`, `tv_robopoli_power-up.py`, `tv_robopoli_power-up-2.py`.

Archived to `_archive/secondary/` (gitignored; recoverable from git history before cutover):
- Exploratory/abandoned: `langchain.py`, `rag_langchain.py`, `streamlit_bots/`, `assistants.py`, `assistant_settings.json`, `agent_trial.py`, `tkinter_minimal_test.py`, `speakerid_scratch.py` (a rough incomplete earlier draft of `speakerid.py`, not an exact copy).
- Rough one-off domain scripts (agent's call — unmaintained, module-level execution, not imported): `pvprogress.py`, `deutsch_well_gen.py`, `books_fix.py`, `create_chroma_db.py`.
- Unused utilities: `helper.py`, `conversion_validator.py`, `webscrape.py`, `xcom.py`.

Top-level `secondary/` folder removed (empty after moves; stray `__pycache__/` and `.DS_Store` discarded).

Affected non-move files:
- `voice/tts.py`: `from secondary.audio import *` → `from core.audio import *`.
- `docs/codeindex/create_codeindex.py`: `from secondary.video import *` → `from core.video import *`.
- `core/gdrive_mtests.py`: bare `from fileops import *` / `from gdrive import *` → `core.*`.
- `apps/scratch/ea/run_bert.py`: `secondary.transcript_eval`/`secondary.audio` → `core.*`; `secondary.books_fix` import commented out (archived).
- `core/transcript_eval.py`: START/END file markers `core/transcript-eval.py` → `core/transcript_eval.py`.
- `core/gdrive.py`: commented out a pre-existing orphaned trailing `print(...)` line so `core.gdrive` imports cleanly (see post-file-organization followup §3).
- `AGENTS.md`: directory guide — `core/` module list expanded (audio, gdrive, speakerid, transcript_eval); added `apps/scratch/` and `apps/games/`; removed the `secondary/` "On request only" entry.
- `cloc_paths.txt`: removed `secondary/`; added `apps/scratch/` and `apps/games/robo-polly/`.

Follow-ups surfaced (recorded in `2026-05-30_post-file-organization-followup.md` §3): rotate the hardcoded OpenAI key in the now-archived `create_chroma_db.py`; FYI on the `gdrive.py` orphaned-line fix and the stale `core.docwork` import in `apps/scratch/Kid1/run_k1.py`.

Note: auto-generated outputs (`cloc_report.md`, `docs/codeindex/*_dev.md`, `scripts/mirror-to-public-corpus-tools/public_corpus_tools_files_log.md`) still list old `secondary/` paths; intentionally not hand-edited (they regenerate).


## Step 10 — Retire top-level `web/`; consolidate under `web-shared/`
Commits: `7f72e9bc`, `efaba75b` (2026-05-31). Docs/manifest update in the following commit. Goal: eliminate the top-level `web/` folder so `web-shared/` is the single shared web/infra home, organized into typed subfolders.

Folder move (commit `7f72e9bc`):
- `web/aws_chalice/` → `web-shared/aws_chalice/` (entire folder; `git mv` preserved history). Top-level `web/` then removed (it held nothing else).

Webflow regrouping (commit `efaba75b`) — loose `web-shared/<file>` → `web-shared/webflow/<file>`:
- `webflow-fof-site-head.html`, `webflow-fof-site-head_2-5.html`, `webflow-fof-site-body.js`, `webflow-fof-home-body.html`, `webflow-fof-home-body_users.html`, `webflow-fof-log-in.html`, `webflow-cms-template-embed.html`, `webflow-cms-template-embed-fda-vth.html`, `webflow-cms-template-van11y-accordion.html`, `webflow-custom-code-template.html`, `webflow-privacy-consent-embed.html`.
- Stayed in `web-shared/` root (not Webflow shells): `md_to_html_dev/`, `web_docs/`, `web_test_files/`, `test_front-end_validation_inputs.js`.

Affected non-move files (commit `7f72e9bc`, the aws_chalice move):
- `web-shared/aws_chalice/chalicelib_mirror_deploy.sh`: hardcoded `COMPOSITE_LOG_FILE` path + self/file-path/illustrative-layout comments → `web-shared/aws_chalice/`.
- `web-shared/aws_chalice/chalicelib_mirror_deploy_composite_log.md`: `START OF FILE` marker path.
- `core/aws_valid.py`: 12 hardcoded `web/aws_chalice/` path literals (incl. `CHALICE_FOLDER`, `COMPOSITE_LOG_FILE_PATH`, deployed-log relative-path builders, and a path-parsing regex) → `web-shared/aws_chalice/`. Imports smoke-tested.
- `core/aws.py`: mirror-deploy log path. `core/aws_valid_other-api-report-versions.py`: deploy-script comment. `README_internal.md`: `cd` hint.
- `.gitignore`: `web/aws_chalice/langchain-layer/` → `web-shared/aws_chalice/langchain-layer/`.
- `AGENTS.md`, `PROJECTS.md`, `cloc_paths.txt`, `security/aws_security-info.md`: directory/path references.
- `web-shared/aws_chalice/{hash-store,hmac-hash,send-email}/app.py`: `# cd ...` invocation comments. `web-shared/aws_chalice/_archive-chalice-contents.md`: self-references.

Affected non-move files (commit `efaba75b`, the webflow regroup):
- `apps/qrag/web/webflow-local-dev.html`, `apps/qrag/web/webflow-local-dev-qrag-deutsch.html`: `../../../web-shared/webflow-fof-*` fetch/script paths → `../../../web-shared/webflow/webflow-fof-*`.
- `AGENTS.md` (web-shared bullet + conventions), `cloc_paths.txt`.

Notes:
- Several git-tracked `user_hash_log_*.csv` files under `hash-store/` (which contain user PII hashes) were relocated along with the folder. This is pre-existing tracking, not introduced here — flagged as a separate cleanup (they likely should be untracked/moved to private storage like the `exchanges/` PII logs).
- Historical deployed logs (`deployed_dev_logs/`, `deployed_prod_logs/`) and old `plans/PLAN_*`/sweep docs still contain old `web/aws_chalice/` strings; left as historical record.
- `cloc_report.md` (auto-generated) not hand-edited.


## Step 11 — Untrack hash-store PII logs (keep local-only)
Commit: pending (this commit, 2026-05-31). Follow-up to Step 10's PII flag.

These git-tracked CSVs under `web-shared/aws_chalice/hash-store/` contain user PII (hash logs) and should never have been in version control:
- `user_hash_log_2024-12-09 _portal-test.csv`
- `user_hash_log_2024-12-09_tests.csv`
- `user_hash_log_2024-12-17.csv`

What was done (NOT deleted — Randy wants local access):
- `git rm --cached` on all three: removed from the git index/tracking, but the files remain on disk locally.
- `.gitignore`: added `**/user_hash_log*` under the PII safety-net section so they (and future hash logs) can never be re-added.
- Verified: files still present on disk, now reported by `git check-ignore`, and no `*user_hash_log*` paths remain tracked.

Caveat (history): untracking stops future commits from including them, but the files still exist in prior git history (including the Step 10 move commits). They are not purged from history here — that would require a history rewrite (forbidden without explicit approval). Cleanest resolution is to not carry this history into the new repo at cutover (fresh init), and/or move the CSVs to private encrypted storage. The repo is private; rotate/scrub if it was ever exposed.


## Step 12 — `voice/` → `apps/voice/` (promote to app)
Commit: pending (this commit, 2026-05-31). `voice/` section of `2026-05-30_followup-folder-organization.md`.

Folder move (`git mv`, history preserved):
- `voice/` → `apps/voice/` (entire folder; the untracked, gitignored `kokoro models - gitignore/` weights folder rode along on the directory rename).

Internal reorg under `apps/voice/` (`git mv`):
- `Testing the text to speech`, `You'll find more Softwood around my workshop and all over Patchi Forest!` → `apps/voice/prompts/` (TTS prompt/test text).
- `kokoro/test1_kokoro-bella.mp3`, `kokoro/test_text_kokoro-bella.mp3`, `kokoro/test_text_kokoro-nicole.mp3` → `apps/voice/kokoro/kokoro_audio/`.
- `kokoro/samples/` → `apps/voice/kokoro/kokoro_audio/samples/` (generated Kokoro voice previews).
- `frame_001 copy.png` → `apps/voice/captured_frames/` (stray captured frame folded into its folder).

Untracked (kept on disk; `git rm --cached`) — generated/captured binaries that should never have been tracked:
- All `apps/voice/captured_frames/*.png` (OCR→TTS video-frame experiment output, ~5 MB).
- All mp3s under `apps/voice/kokoro/kokoro_audio/` (loose test files + `samples/`) and the root `apps/voice/elevenlabs_test.mp3`, `apps/voice/openai_tts_test.mp3`.
- (`*.mp3`/`*.wav` were already globally gitignored; they were tracked from before that rule. The frame PNGs needed new path rules — see below.)

Affected non-move files:
- `.gitignore`: replaced `voice/captured_frames/` with `apps/voice/captured_frames/` and added `apps/voice/kokoro/kokoro_audio/` (frame PNGs aren't covered by the global media ignore). The `kokoro models - gitignore/` weights folder stays ignored via the pre-existing `**/*gitignore*/` catch-all.
- `apps/voice/kokoro/kokoro.py`: `KOKORO_MODEL_PATH` / `KOKORO_VOICES_PATH`, `create_kokoro_voice_samples` default `output_dir` (→ `kokoro_audio/samples`), run-comment, and the mrun example mp3 path → `apps/voice/...`.
- `apps/voice/video_capture.py`: `get_next_frame_num("voice/captured_frames",...)` and `log_frame("voice/frame_log.md",...)` (+ a commented path) → `apps/voice/...`.
- `apps/voice/tts.py`: one commented `voice/openai_tts_test.mp3` path → `apps/voice/...`.
- `AGENTS.md`: directory guide — added `apps/voice/` to the apps list; removed the stale top-level `voice/` "Read freely" entry.
- `cloc_paths.txt`: `voice/` → `apps/voice/`.

Verification: `py_compile` passes on the four edited Python files; nothing else in the repo imports `voice` as a module (it is a leaf app), so no downstream import changes. `git check-ignore` confirms the weights folder, frame PNGs, and audio are all ignored at their new paths.


## Step 13 — `tests/` internal cleanup
Commit: pending (this commit, 2026-05-31). `tests/` section of `2026-05-30_followup-folder-organization.md`.

Moves / deletions:
- `tests/vectordb_test/` → `tests/test_manual_files/vectordb/` (`git mv`, history preserved; 4 md fixtures, 44 KB). It is a live fixture for `core/vectordb_mtests.py`, so it belongs with the other manual fixtures.
- `tests/deprecated_unittests.py` → deleted (`git rm`). Dead file: it tested `print_chars_with_indices` from a long-removed module and never even imported it.

Affected non-move files:
- `core/vectordb_mtests.py`: two `'tests/vectordb_test'` path strings (lines 16, 22) → `'tests/test_manual_files/vectordb'`.

Not moved (pending decision): `tests/test_manual_files/` (~39 MB, 238 tracked files) left tracked as-is. Recommendation recorded in the follow-up plan: keep as-is; the only relocation candidate is the single 18 MB `pv_test_files/EPC_testing_packet.pdf` (≈47% of the folder) if working-tree size becomes a concern. `tests/test_unit_files/` is an empty untracked placeholder — left in place.

Verification: `py_compile core/vectordb_mtests.py` passes; no `vectordb_test` references remain in tracked code.


## Step 14 — `docs/` internal cleanup
Commit: pending (this commit, 2026-05-31). `docs/` section of `2026-05-30_followup-folder-organization.md`.

Moves / renames:
- `docs/sphnix/` → `docs/sphinx/` (`git mv`, history preserved; 5 tracked files — `Makefile`, `conf.py`, `fileops.rst`, `index.rst`, `make.bat`). Pure typo fix. No external references to the old folder name existed in the tree outside the follow-up plan.
- `docs/vis/graphviz_and_example_OLD.py`, `docs/vis/module_based_network_OLD.html` → `_archive/docs-vis/` (gitignored; recoverable from git history before cutover). The active `codebase_graph_vis.py/.js` and the three `example_graph_*` files stay tracked.
- `docs/misc/call_graph.dot` → deleted (`git rm`). Empty 0-byte file. The non-empty `call_graph_incoming.svg` and `openai_reasoning_models.md` stay tracked.

Untracked (kept on disk; `git rm --cached`) — regenerable outputs that should never have been tracked:
- `docs/codeindex/all_ast_trees_dev.md`, `all_graph_dev.json`, `all_source_code_dev.md`, `all_source_defs_docstrings_dev.md`, `all_user_defined_functions_dev.md`, `column_layout_graph.html`, `create_codeindex_log.txt` — regenerable by `create_codeindex.py`. The generator stays tracked. `docs/codeindex/_archive/` of dated historical snapshots (~11 MB) stays tracked as-is.
- `docs/_build/` (25 files, ~1.1 MB) — Sphinx HTML output, last regenerated 2024-11-01. Sphinx config in `docs/sphinx/` stays tracked so the build can be rerun.

Not moved (kept as-is): `docs/codeindex/_archive/` (~11 MB dated snapshots), `docs/my_refs/objects_pickle_json.md`, all 16 files under `docs/packages/` (deepgram, openai, pinecone, webflow, pypandoc, speechbrain reference notes). Small cross-cutting reference library.

Affected non-move files:
- `.gitignore`: new "docs/ generated outputs (regenerable; keep generators tracked)" section listing the 6 codeindex outputs, the log file, and `docs/_build/`.

Verification: `git check-ignore` confirms all 8 newly-ignored paths are caught. No path-string references to the codeindex outputs or `_build/` exist in tracked code (only this plan file and `README_internal.md` mention them by name as outputs). The `create_codeindex.py` `secondary.video` import was already retargeted to `core.video` during the `secondary/` session.


## Step 15 — `dependencies/` cleanup
Commit: pending (this commit, 2026-05-31). `dependencies/` section of `2026-05-30_followup-folder-organization.md`.

No folder moves. `dependencies/` pared down to a single canonical requirements file plus the generator script.

Deleted (`git rm`):
- `dependencies/code file copies/` (entire folder — 14 tracked historical Python file snapshots of code now living in `core/`/`docs/`). Redundant with git history.

Archived to `_archive/dependencies/` (gitignored; recoverable from git history before cutover) — `mv` on disk + staged deletion of the tracked paths:
- All older dated requirements snapshots: `requirements_2024-07-14_387_before-graphrag.txt`, `requirements_2024-09-24_122_before-fixing-venv.txt`, `requirements_2024-09-24_541_after-freeze-req.txt`, `requirements_2024-09-25_540_trying-to-resolve.txt`, `requirements_2024-09-26_mod.txt`, `requirements_2024-09-26_piprecs.txt`, `requirements_2025-12-19_1626 Randy.txt`, `requirements_2025-12-19_piprecs.txt`.
- `global_packages.txt` (Nov 2024 global-package snapshot), `log_pip_install.md` (Dec 2024 install log).

Kept in `dependencies/`:
- `requirements_2024-09-26_add_CURRENT.txt` — confirmed canonical (read by `setup.py` + `README_external.md`). It is hand-curated with version ranges + dated rationale and includes un-importable infra/ML deps (`awscli`, `chalice`, `torch`, `speechbrain`, `flask`, ...) that the auto-generated `pipreqs` dumps miss. Chosen over the newer 2025-12-19 `pipreqs` dump, which reflected current installed versions but was structurally broken as an install file (bogus local-package entries `corpus_tools.egg`/`docs`/`secondary`, duplicate lines, missing infra deps). The real version refresh is deferred to the pyproject.toml migration (see post-file-org follow-up).
- `get_direct_dependencies.sh` — kept, paths updated.

Affected non-move files:
- `dependencies/get_direct_dependencies.sh`: dropped the "code file copies" mirror step (folder creation/clear/copy loop + the `requirements_.txt` duplicate); `FILES_TO_COPY` (now `SOURCE_FILES`, provenance-only) paths `primary/` → `core/` (and dropped the un-migrated `docwork.py`); pipreqs now runs directly on `core/` via `--savepath`. Added a header note that the script is slated for pyproject replacement.
- `dependencies/requirements_2024-09-26_add_CURRENT.txt`: stale `# primary/*.py` provenance comments → `# core/*.py` (dropped `docwork.py`, not in `core/`); `#web/aws_chalice/qrag-routing/app.py` → `#apps/qrag/api/qrag-routing/app.py`.
- `.vscode/settings.json`: removed the now-dead `**/dependencies/code file copies/**/*.py` and `**/web/_archive-web/**/*.py` entries from `python.analysis.exclude` (both reference deleted paths; the `**/_archive/**/*.py` catch-all remains).

Note: `scripts/mirror-to-public-corpus-tools/public_corpus_tools_files_log.md` still lists the deleted `dependencies/code file copies/*` paths and the old canonical name; it is auto-generated mirror output and was intentionally not hand-edited (next mirror run reconciles it).


## Step 16 — `scripts/` dispersed and deleted
Commit: pending (this commit, 2026-05-31). `scripts/` section of `2026-05-30_followup-folder-organization.md`.

`scripts/` was a generic catch-all the original Option B never actually defined; dispersed to real homes and the folder deleted.

File moves (`git mv`, history preserved):
- `scripts/deutsch/extract_boi_problems_snippets.py` → `apps/deutsch/extract_boi_problems_snippets.py` (new `apps/deutsch/` app).
- `scripts/mirror-to-public-corpus-tools/mirror_public_corpus_tools.py` → `apps/repo-mirror/mirror_public_corpus_tools.py` (new `apps/repo-mirror/` app).
- `scripts/mirror-to-public-corpus-tools/public_corpus_tools_files_log.md` → `apps/repo-mirror/public_corpus_tools_files_log.md`.
- `scripts/z_count_chars_in_js.sh` → `web-shared/z_count_chars_in_js.sh` (loose cross-app web asset).

Deleted:
- Empty `scripts/` folder (plus stray untracked `.DS_Store` and the two now-empty subdirs).

Affected non-move files:
- `apps/repo-mirror/mirror_public_corpus_tools.py`: docstring path references `scripts/mirror-to-public-corpus-tools/` → `apps/repo-mirror/`. The `PRIVATE_ROOT = SCRIPT_DIR/../..` logic is unchanged (new location is still two levels below the repo root).
- `web-shared/z_count_chars_in_js.sh`: `file_path:` marker and usage/chmod comments `scripts/` (and a stale `web/`) → `web-shared/`.
- `AGENTS.md`: added `apps/deutsch/` and `apps/repo-mirror/` to the apps list; added `z_count_chars_in_js.sh` to the `web-shared/` loose-assets list.
- `2026-05-28_monorepo-folder-structure.md`: living tree — removed the `scripts/` block, added `apps/deutsch/` and `apps/repo-mirror/`; bumped `Last updated:` + change-log entry.

Note: `apps/deutsch/extract_boi_problems_snippets.py` needed no path edit — its `Path(__file__).resolve().parents[2]` still resolves to the repo root from the new two-deep location.

Verification: `py_compile` passes on both relocated Python files. No `scripts/` path references remain in tracked code (the `core/transcribe.py` / `apps/smol_podcaster/smol_podcaster.py` hits are unrelated `transcripts/` strings; `cloc_paths.txt` has no `scripts/` entry).


## Step 17 — `security/` audit (no move)
Commit: pending (this commit, 2026-05-31). `security/` section of `2026-05-30_followup-folder-organization.md`.

No file or folder moves. `security/` kept top-level per the Option B decision (which deferred a heavier `infra/`/`ops/` layout). Audit-and-document only:
- Confirmed all three files git-tracked: `security/First-Web-ACL.json` (exported AWS WAFv2 Web ACL: 50 req / 300s per-IP rate block), `security/aws_security-info.md`, `security/hash-store_security thread.md`.
- Sensitive-identifier audit: no live secrets (no keys/credentials; `USERS_HMAC_SECRET_KEY` named only). Identifiers to redact before any public publish — AWS account ID `[AWS-ACCOUNT-ID]`, WAF Web ACL id/ARN, six API Gateway IDs, four SNS subscription ARN UUIDs, private bucket `[S3-BUCKET]`, and personal/collaborator emails. Not an active leak (private repo; `apps/repo-mirror/` never adds new paths to the public clone). Pre-publish redaction recorded in `2026-05-30_post-file-organization-followup.md`.

Affected non-move files: none (docs/plan files only — followup plan marked `[x]`, this manifest, the post-file-org followup, and a change-log entry + `Last updated:` bump in `2026-05-28_monorepo-folder-structure.md`). The living tree already listed `security/`; no tree-line change.


## Step 18 — `exchanges/` deletions + selected-exchanges manifest (no move)
Commit: pending (this commit, 2026-05-31). `exchanges/` section of `2026-05-30_followup-folder-organization.md`.

No folder move and no code changes — documentation plus two authorized deletions.

Deleted (`git rm` for tracked files; ignored PII remnant in `_del/` cleared on disk):
- `exchanges/_del/` — staged-for-deletion duplicate (tracked `exchanges_qrag_deutsch.db` + ignored `pii-exchanges_qrag_deutsch.db`); live copies remain under `qrag_deutsch/`.
- `exchanges/deepseek/` — one-off `2025-01-29_reasoning_tests.md` reasoning test.

New file (tracked): `apps/qrag/selected_exchanges_manifest.md` — start of the curated "selected QRAG exchanges" list (per-corpus exchange sets, the `qrag_deutsch_early` triage buckets, `response_files/`, PII local-only/[S3-BUCKET] status).

Key finding (recorded for the deferred S3 migration): the top-level `exchanges/` folder is NOT gitignored as the plan assumed — only the PII files are (`**/pii*`, `**/user_hash_log*`). The de-identified bulk (`exchange_jsons/`, non-PII `exchanges_*.db`, `response_files/` — 682 files) is currently git-tracked and should be `git rm --cached`'d as part of the S3 migration. Logged in `2026-05-30_post-file-organization-followup.md` §2 (S3 uploads + PII → `[S3-BUCKET]` + deferred QRAG usage-tracking overhaul).

Affected non-move files: none (docs only — this manifest, the post-file-org followup §2, and the `exchanges/` section marked `[x]`). `exchanges/` is data and not in the living folder-structure tree, so no tree edit.


## Step 19 — S3 manifests → `manifests/` (root)
Original sub-branch commit: `7e04020` (2026-07-05) on `refactor/manifests-relocation` off `stellar-transcriber-start`. Main promotion: PR #37 provides the detailed branch history; this entry is also promoted to `main` as part of the repo-wide manifest relocation.

Folder moves:
- `plans/2026-04-09_repos-reorg/s3_manifests/` → `manifests/` (per-area `.manifest.jsonl` files, flat at repo root).
- `plans/2026-04-09_repos-reorg/s3_archive_manifest.jsonl` → `manifests/s3_archive_manifest.jsonl`.
- `plans/2026-04-09_repos-reorg/s3_archive_manifest_README.md` → `manifests/s3_archive_manifest_README.md`.

New file (no moves): `plans/2026-04-09_repos-reorg/s3_manifests_MOVED-to-manifests_2026-07-05/README.md` (tombstone pointer).

Affected non-move files:
- `core/s3_archive.py`: `MANIFEST_SUBDIR = "manifests"`.
- Living docs: `AGENTS.md`, `apps/qrag/selected_exchanges_manifest.md`.
- `manifests/2026-07-05_relocate-s3-manifests.plan.md`: durable copy of the relocation plan moved out of `.cursor/plans/`.
- New skill: `skills/repo-ops/s3-archive-upload/README.md`; pointer added to `bring-over-s3-upload-guide.md`.


## How to update this file
Append a new `## Step N — <name>` or `## Manual moves — <name>` section per move session. Within each:
- Folder-level moves first (`old_path/` → `new_path/`).
- Individual file moves only when they didn't follow a parent folder.
- Brief "Affected non-move files" bullet list when imports or path strings were edited.
- Note the commit hash (or "manual" + brief context).

Keep entries terse and folder-scoped. The full diff lives in the commit; this file is the human-readable index.
