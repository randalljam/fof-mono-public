file: 2026-05-30_post-file-organization-followup.md
title: Post-reorg verification and cleanup tasks (after the Option B folder moves)


## Purpose
Verification and cleanup tasks that come after the folder reorg moves tracked in `2026-05-30_followup-folder-organization.md`. These run once the moves settle — they are not meant to block each per-folder move. As later folder sections (web/aws_chalice, secondary, voice, docs, etc.) land, append any new follow-ups they surface here.


## 1. Run the test suite and fix what surfaces
The `primary/` → `core/` rename (step 1) and the subsequent folder moves changed module paths and a few path strings. Run the suite and repair what breaks.

Run:
- `.venv/bin/python3 -m unittest discover -s tests`

Known failures as of 2026-05-30 (recorded during the web/ residual session):
- 79 errors, all `ModuleNotFoundError: No module named 'primary'`.
- Root cause: `tests/test_fileops.py` still uses `@patch('primary.fileops....')` mock targets (plus a `'primary.'` reference in a comment near the top) left over from the step-1 rename. The `primary` module no longer exists (it is now `core`).
- Fix: retarget those patches from `primary.fileops` to `core.fileops`. Then re-run and confirm the import errors drop to 0.
- Also scan the other test files (`test_llm.py`, `test_transcribe.py`, `testTEMPLATE.py`, `check_openai.py`) for any remaining `primary` imports or patch targets.

After the patch-target fix:
- Re-run the full suite and triage any remaining real failures (skips are fine).
- Per AGENTS.md, run the suite before pushing further `core/` changes.


## 2. S3 uploads and manifests
- check where this is at

Note: this section will likely be split into PRE-cutover (must happen before the new-repo cutover so data is not lost) and POST-cutover (redesign work) once the list firms up. The exchanges-data upload below is explicitly PRE-cutover.


### From the `exchanges/` session (2026-05-31)
QRAG user-exchange captures under the top-level `exchanges/` folder need to move to S3, with the curated "selected list" preserved. Manifest started: `apps/qrag/selected_exchanges_manifest.md` (indexes the kept exchange sets per corpus + the `qrag_deutsch_early` triage; this is the list Randy does not want to lose).

- **[PRE-CUTOVER] Upload the selected exchanges to S3 and record the prefix.** The corpus exchange sets (`exchanges/qrag_deutsch`, `qrag_deutsch_early`, `qrag_fda-c19-townhalls`, `qrag_pv-evac`, `qrag_sovereign-child`) and `response_files/` (680 tracked files total — see the manifest's reconciliation table) should be uploaded to S3, then their S3 location recorded back in `apps/qrag/selected_exchanges_manifest.md` so the on-disk copies can be cleared. This is a must-do-before-cutover step and is expected to be a sizeable area to do and verify (it overlaps the general "bunch of data to upload to S3 + manifest" pre-cutover work).
- **[PRE-CUTOVER] PII hash logs + PII exchange DBs → `[S3-BUCKET]` S3, then keep local copy out of the repo.** `exchanges/pii_user_hash_log_2024-12-17.csv` and `..._test.csv`, plus every `pii-exchanges_<corpus>.db`, are PII and already git-ignored (`**/pii*`). Upload them to the private `[S3-BUCKET]` bucket; afterward keep the working copies somewhere outside the repo working tree so a repo backup never sweeps them up (Time Machine / local-disk backups are acceptable per Randy — secured by the machine login). No code changes made this session (the QRAG code still writes these files locally as designed).
- **The exchanges are mostly git-tracked (key finding) — but do NOT untrack them.** Contrary to the "gitignored" label in the folder plan, only the PII files in `exchanges/` are git-ignored (`**/pii*`, `**/user_hash_log*`). The non-PII-named bulk — `exchange_jsons/`, non-PII `exchanges_*.db`, and `response_files/` (**680 files**, was 682 before `_del/`+`deepseek/` deletion) — is currently **git-tracked**. Per the HARD RULE in `2026-05-30_followup-folder-organization.md` ("NEVER remove tracked files or rewrite git history"), leave them tracked — do NOT `git rm --cached`. Exclusion from the NEW repo is handled at cutover-copy time (selective copy / the new repo's `.gitignore`), not by untracking here. The PRE-cutover S3 upload is what preserves this data going forward.
- **[POST-CUTOVER] QRAG usage-tracking overhaul.** Randy plans to overhaul how QRAG application usage is tracked/managed going forward (where exchanges + PII logs are written, S3 vs local, the manifest workflow, the writing code). That is a dedicated project to take on **well after the cutover**, when he next works on the QRAG app itself. The PRE-cutover S3 uploads above preserve the existing data; this redesign changes how new data is produced and is separate.

## 3. Other items uncovered during the reorg
- (append here as later folder sections surface follow-ups.)


### From the `tests/` session (2026-05-31)
- **Set up CI (deferred).** During the `tests/` folder session the call was made to defer CI setup rather than wire it up as part of the reorg. Stand up CI later per `ai-coding-system-dev.md` §9 (run `python -m unittest discover -s tests` on push/PR to `pare-down`, gate `core/` changes). Sequence it after §1 (test-suite repair) lands so CI starts green.

### From the `dependencies/` session (2026-05-31)
- **Migrate dependency management to `pyproject.toml`.** Currently `setup.py` reads the hand-curated `dependencies/requirements_2024-09-26_add_CURRENT.txt` (kept as canonical). As part of the migration: (1) move dependency declaration into a root `pyproject.toml` (lightweight; aligns with the future packaging promotion path), and (2) do a real requirements refresh — the canonical file's pins are ~14 months old. The `dependencies/_archive/` `requirements_2025-12-19_*` pipreqs dumps capture the *current* installed versions (e.g. `openai==2.14.0`, `anthropic==0.75.0`, `langchain==1.2.0`) and are a useful reference for the refresh, but they are raw pipreqs output (bogus local-package entries, duplicates, and missing the un-importable infra deps `awscli`/`chalice`/`torch`/`speechbrain`/`flask`) so they cannot be used directly. Update `README_external.md` and remove/repoint `setup.py` once `pyproject.toml` lands.

### From the `security/` session (2026-05-31)
- **Redact `security/` identifiers before any public publish.** All three files in `security/` are git-tracked and contain sensitive (not secret) AWS/personal identifiers. No API keys, credentials, or HMAC secret values — `USERS_HMAC_SECRET_KEY` appears by name only. To redact before publishing publicly: AWS account ID `[AWS-ACCOUNT-ID]`; the WAF Web ACL id/ARN; six API Gateway IDs (hash-store `[API-GATEWAY-ID]`, hmac-hash `[API-GATEWAY-ID]`, qrag-llm `[API-GATEWAY-ID]`, qrag-routing `[API-GATEWAY-ID]`, send-email `[API-GATEWAY-ID]`, vrag-llm `[API-GATEWAY-ID]`); four SNS subscription ARN UUIDs; the private S3 bucket name `[S3-BUCKET]`; and personal/collaborator emails (`[REDACTED-EMAIL]`, `randy@`/`contact@focusonfoundations.org`, `ea@`/`[REDACTED-EMAIL]`). Not an active leak: the repo is private and `apps/repo-mirror/` only updates paths already present in the public clone (it never adds `security/`). Fold this into the planned key-rotation / pre-cutover scrub pass; this is the same review surface as the "Codex sessions → security" item below.

### From the `plans/` session (2026-05-31)
- **[PRE-CUTOVER] Consider trimming `plans/2026-04-09_repos-reorg/` just before cutover.** The top-level `plans/` folder (~2 MB) is being carried into the new repo as-is — no reorg or culling, the current organization is fine. The one open item: just before cutover, decide whether to move some of the `2026-04-09_repos-reorg/` contents out (this reorg work is finishing then, so parts may no longer need to come along). Not sure yet — revisit at cutover time.

### From the `secondary/` session (2026-05-31)
- **Rotate hardcoded OpenAI API key.** `_archive/secondary/create_chroma_db.py` (formerly `secondary/create_chroma_db.py`) contains a hardcoded key on line ~16 (`os.environ["OPENAI_API_KEY"] = "sk-Jcb...pllWd"`). The file is now archived (gitignored), but the key is already in this repo's git history at the old `secondary/` path, so archiving does not remove the exposure. Rotate this key (it is almost certainly long-dead 2024 langchain-era, but rotate to be safe) as part of the planned key-rotation pass. Also a good candidate to scrub from history before the public cutover.
- **`core/gdrive.py` orphaned-line fix (done, FYI).** Promoting `gdrive.py` to `core/` surfaced a pre-existing `IndentationError`: a dangling, undefined-`file` `print(...)` at module scope at the end of the file made `import core.gdrive` fail. It was commented out so `core.gdrive` imports cleanly. If that trailing block was meant to be inside a function, restore it properly; otherwise the comment can be deleted.
- **Scratch runners with stale/missing imports (FYI).** The per-user runners moved to `apps/scratch/<user>/` are kept tracked as personal scratch and were not all made import-clean. Notably `apps/scratch/Kid1/run_k1.py` imports `core.docwork`, which does not exist in `core/`. Left as-is per the "keep runners as personal scratch" decision; fix only if a collaborator needs the runner to run.

## EA
[] rotate api keys and set up system to track

## Codex sessions
[] paths
[] security

## Skill to comeback to frozen corpus-tools and the AI sessions to troubleshoot