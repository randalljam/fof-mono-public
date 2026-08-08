file: apps/transcription/stellar-transcriber/docs/2026-07-03_milestone-2-plan.md
title: Stellar Transcriber — Milestone 2 plan: eval harness implementation
last-updated: 2026-07-03_0835
ai: Cursor - Fable 5
session: `Stellar Transcriber M2 — eval harness implementation`

Milestone 2 of the Stellar Transcriber project. Design of record: `references/eval-scoring-design.md`. Pair list: `references/corpus-inventory-catalog.csv` (127 pairs). Working branch: `stellar-transcriber-start`.


## Milestone 2 objective
Implement the eval harness designed in Milestone 1: per-corpus config, disfluency/normalization policy layer, composite overall score, non-interactive batch runner, S3 fetch of eval-pair transcripts, and baseline scores across the three corpora.


## Phases

### Phase A — M2 milestone doc and per-corpus config
- Write this plan and `config/eval-corpora.json` (ref suffix priority, eval suffixes, search folders, policy_id, weights, proper-names method).
- Add `load_eval_corpus_config()` in `core/transcript_eval.py`; keep existing constants as fallback defaults.

### Phase B — Normalization and disfluency policy layer
- Add `normalize_dialogue(text, policy)` in `core/transcript_eval.py` with filler stripping, adjacent-repeat collapse, partial-word stripping, optional numeral/contraction handling.
- Wire into alignment, WER, and quotations steps; `keep-all` policy reproduces current `normalize_text` behavior exactly.

### Phase C — Composite overall score
- Compute five 0-100 subscores and weighted `overall_score`; stamp `policy_id` and `eval_code_version` on every metrics row.
- Add `rescore_metrics_csv()` for re-scoring historical rows when weights change.

### Phase D — Non-interactive batch runner
- Add `interactive=False` / `on_mismatch` paths for all `input()` prompts in eval code.
- New `scripts/run_baseline_eval.py`: catalog-driven batch eval with per-corpus/per-model summaries.

### Phase E — Fetch data and baseline runs
- New `scripts/fetch_eval_pairs.py`: read-only S3 GETs for pair `.md` files from the catalog.
- Run baselines: deutsch (101 pairs), pv (19), sovereign-child (7), models `_nova2gen` + `_dgwhspm`.
- Write `references/baseline-eval-results.md`; fill eval-policy placeholders in `eval-corpus-profiles.md`.


## Next Milestone Planning (M3 and beyond)

M3 — De novo pipeline: single- and multi-raw-transcript modes on diarize-latest output — end-to-end audio/link → raw diarized transcript(s) → cleaned draft transcript, including the (to-be-designed) merge of multiple model outputs; scored with the M2 harness.

M4 — Corpus-informed enrichment: leverage the corrected corpus and supporting files (proper names, people titles) to improve output on corpus-adjacent recordings.

M5 — Speaker identification integration: wire `core/speakerid.py` (SpeechBrain ECAPA) into the pipeline — enrollment sets per corpus, matching diarized speaker labels to names.

M6 — Audio archival and local ASR: save source MP3s to S3 (coordinated with the manifest/re-key procedures); explore local diarizing-ASR models as an alternative to Deepgram.


## To-dos (Milestone 2)
- [x] Phase A: M2 milestone doc; `config/eval-corpora.json` + loader
- [x] Phase B: normalization policy layer; wire into eval steps
- [x] Phase C: composite overall score and score provenance
- [x] Phase D: non-interactive batch runner
- [x] Phase E: S3 fetch; baseline runs; baseline results doc
- [x] Tests: eval scoring, policy, runner smoke test
