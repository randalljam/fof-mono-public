file: apps/transcription/stellar-transcriber/docs/2026-07-03_milestone-3-plan.md
title: Stellar Transcriber — Milestone 3 plan: de novo cleanup pipeline
last-updated: 2026-07-03_1150
ai: Cursor - Composer 2.5 Fast
session: `Stellar Transcriber M3 — de novo cleanup pipeline`

Milestone 3 of the Stellar Transcriber project. Design of record: `references/denovo-pipeline-design.md`. Eval harness: M2 (`references/eval-scoring-design.md`, `config/eval-corpora.json`). Working branch: `stellar-transcriber-start`.


## Milestone 3 objective
Build the de novo transcript cleanup pipeline — a 2×2 of single vs dual transcript modes and deterministic vs LLM cleanup methods — with the LLM path as the primary bet and speaker-segmentation repair as the core quality target. All variants scored against the M2 baseline with the eval harness.


## Phases

### Phase A — M3 milestone doc and cleanup-pipeline design
- Write this plan and `references/denovo-pipeline-design.md` (2×2 matrix, anchor-island design, transition-defect taxonomy, prompts, model tiers, output suffix scheme).

### Phase B — Deterministic cleanup (single mode + shared pre-pass)
- New module `core/denovo.py` with `create_draft_deterministic(raw_md_path, profile)` — broken-sentence transition repair, merge consecutive same-speaker segments, numeral conversion, ASR artifact normalization aligned with eval policy.
- Thin CLI `scripts/build_draft_transcript.py`.
- Deterministic pass is also the pre-pass for LLM modes and the deterministic comparison arm in Phase E.

### Phase C — LLM single-transcript cleanup mode
- Extend `core/llm.py` with structured transcript cleanup machinery (chunking, function-call schema, validation, retry).
- `create_draft_llm(raw_md_path, profile, model_tier)` — deterministic pre-pass → chunked LLM transition/cleanup → reassemble with provenance metadata.

### Phase D — Dual-transcript modes (LLM arbitration primary)
- `merge_dual_llm(path_a, path_b, profile, model_tier)` — anchor/island detection between two raws, per-island structured LLM arbitration.
- `merge_dual_deterministic(path_a, path_b, profile)` — simple rule-based comparison arm.

### Phase E — Batch scoring vs baseline (2×2 comparison)
- `scripts/run_draft_eval.py` — build all four variants per eval pair, score with M2 harness, write `references/denovo-eval-results.md`.

### Phase F — End-to-end smoke (audio/link → draft)
- `process_denovo(audio_or_link, mode, method, output_dir)` in `core/denovo.py` chains Deepgram diarize-latest → raw `.md`(s) → cleanup per mode/method.
- Smoke run **not executed** (2026-07-03): `DEEPGRAM_API_KEY` absent from environment. Re-run when key is available:
  `.venv/bin/python3 -c "from core.denovo import process_denovo; print(process_denovo('<short-youtube-url>', mode='single', method='deterministic'))"`


## Next Milestone Planning (M4 and beyond)

M4 — Corpus-informed enrichment: leverage the corrected corpus and supporting files (proper names, people titles) to improve output on corpus-adjacent recordings; includes promoting pv candidate references after review; natural home for tuning M3 model tiers and merge heuristics against eval results.

M5 — Speaker identification integration: wire `core/speakerid.py` (SpeechBrain ECAPA) into the pipeline — enrollment sets per corpus, matching diarized speaker labels to names.

M6 — Audio archival and local ASR: save source MP3s to S3 (coordinated with the manifest/re-key procedures); explore local diarizing-ASR models as an alternative to Deepgram.


## To-dos (Milestone 3)
- [x] Phase A: M3 milestone doc; `references/denovo-pipeline-design.md`
- [x] Phase B: deterministic cleanup pass + CLI
- [x] Phase C: LLM single-transcript cleanup mode
- [x] Phase D: dual-transcript anchor-island merge modes
- [x] Phase E: draft eval runner; `references/denovo-eval-results.md`
- [x] Phase F: end-to-end denovo entry point (`process_denovo` in `core/denovo.py`); smoke run skipped — `DEEPGRAM_API_KEY` not available in env (2026-07-03)
- [x] Tests: `tests/test_stellar_denovo.py`
