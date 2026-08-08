file: apps/transcription/stellar-transcriber/docs/2026-07-09_BA-iteration-notes.md
title: Stellar Transcriber — de novo deterministic and EPC iteration notes (Jul 2026)
last-updated: 2026-07-09_2307
ai: Cursor - Composer 2.5 Fast
session: `Stellar Transcriber — denovo diff review and prompt tightening`

Snapshot of work through diff-based review on the Deutsch eval sample and the harder PV/EPC meeting transcript `2025-03-06_PV-EPC`. Documents the kept current state in `core/denovo.py`, `core/llm.py`, and `tests/test_stellar_denovo.py` (plus the review runs that motivated them). For broader project context see `2026-07-03_project-notes.md` and `references/denovo-pipeline-design.md`.


## Goal of this iteration
Improve **speaker-segmentation cleanup** on raw and speaker-assigned diarized transcripts — not copyediting, not wording polish. Primary deliverable: trustworthy `_draftds` (deterministic single-transcript cleanup). Secondary: document why `_draftls` / `_draftld` are paused: `_draftls` is mostly no-op/slightly worse, and `_draftld` still copyedits, duplicates, and drops content despite prompt guardrails.


## Pipeline terminology
```
raw transcript (_nova2gen or _dgwhspm)
  → deterministic cleanup (_draftds)     # core/denovo.py rules
  → single LLM cleanup (_draftls)        # PROMPT_DENOVO_SINGLE_V2 in core/llm.py

raw A + raw B
  → dual LLM reconciliation (_draftld)   # PROMPT_DENOVO_DUAL_V2 + merge_dual_llm
```

Suffix scheme: `_draftds` deterministic-single, `_draftls` LLM-single, `_draftld` LLM-dual. Config: `apps/transcription/stellar-transcriber/config/denovo-pipeline.json` (`prompts_version: denovo-v2`).

Speaker-assigned inputs use `_spasgn_` before the model suffix, e.g. `2025-03-06_PV-EPC_spasgn_dgwhspm.md`. Assigned names are useful evidence but not final truth: remaining generic `Speaker N` labels inside mostly named transcripts are strong blip candidates, and named segments can still be blips because speaker assignment was done by find/replace from original speaker numbers.


## Review method
Eval numbers (`run_alignment_eval.py`) are useful but secondary. Primary QA was **side-by-side diff review**:

1. Raw/spasgn vs `_draftds` — did deterministic cleanup fix real boundary/speaker errors without damaging good turns?
2. `_draftds` vs human reference (`_vrb` for Deutsch, `_cemanual` for PV/EPC) — how close to the reference, and are remaining gaps acceptable ambiguity?
3. Full ladder (with LLM) — only after `_draftds` looked decent; LLM arms judged by whether they helped segmentation without copyedits, duplicate spans, dropped words, or timestamp damage.

Data paths:
- Raw: `data/deutsch/f9_raw/*_nova2gen.md`, `*_dgwhspm.md`
- PV/EPC raw/spasgn: `data/pv/meetings_epc/f9_raw/2025-03-06_PV-EPC*_nova2gen.md`, `*_dgwhspm.md`
- Draft outputs: `*_draftds.md`, `*_draftls.md`, `*_draftld.md` (written beside raw)
- Reference: `data/deutsch/f8_done_qafixed_and_vrb/*_vrb.md`
- PV/EPC reference: `data/pv/meetings_epc/2025-03-06_PV-EPC_cemanual.md`
- Eval reports: `data/stellar-eval/alignment-runs/alignment-ladder_*.md`


## Episodes exercised
Five-episode Deutsch sample from `references/alignment-results-real5.md`:

| Episode | Diff review | Full LLM ladder |
|---------|-------------|-----------------|
| `2024-01-01_Arjun Khemani - Free-Will TCS and Anarcho-Capitalism` | Yes | No (`--skip-llm`) |
| `2024-01-04_Reason Is Fun - Ep5 The Art of Decision Making` | Heavy | Partial |
| `2024-03-04_Alex OConnor - The Multiverse is Real` | Yes (incl. overlap ~1:03:07) | No |
| `2024-03-31_Sagenhaft und Sonderbar der Podcast` | Yes (rerun after fixes) | No |
| `2024-08-26_Reason Is Fun - Ep6 Are Feelings Ideas` | Yes | Yes |
| Markus Arndt (3+ speakers, outside real5) | — | Yes (dual broken) |
| `2025-03-06_PV-EPC` raw meeting transcript | Heavy | Yes (`_draftld` broken) |
| `2025-03-06_PV-EPC` speaker-assigned (`_spasgn`) | Heavy | Yes (`_draftls` no help, `_draftld` broken) |


## Changes in `core/denovo.py`
All items below are in the current diff on this branch.

### Timestamp link preservation (LLM path)
- `llm_segments_to_internal` accepts optional `source_segments` and copies `timestamp_link` by matching timestamp.
- Wired in `create_draft_llm` and `merge_dual_llm` so LLM output keeps clickable `[timestamp](url)` markdown instead of plain timestamps.

### Deterministic boundary / speaker repair
| Fix | Behavior |
|-----|----------|
| Short meaningful responses | `is_short_meaningful_response` — e.g. `I'm not sure` — not treated as disposable blip or incomplete fragment |
| Answer echo detection | `blip_echoes_start_of_next` — when next turn repeats middle fragment (e.g. `Isn't yeah`), do not collapse A-B-A blip |
| Acknowledgement + dangling tail | `split_short_trailing_fragment` extended — e.g. `Yeah. Fair` / `enough. Helping` / `them would be a crime` splits into complete middle turn + continuation |
| Question tail to next speaker | Existing `question_tail_to_next` path — e.g. move `Yeah. So what's…` from wrong speaker onto following question |
| Connector fragments | `Because if` and similar can join following lowercase continuation |
| Discourse opener overlap | `Whereas` crosstalk preserved for human review — removed `OVERLAP_CONTINUATION_START` rewrite that invented smoother wording |
| Blip collapse guardrails | Skip blip merge when prev is discourse opener; skip when echo pattern matches; skip meaningful short responses in `repair_broken_sentence_transition` |
| Conservative drop-middle | `repair_drop_middle_speaker_noise` no longer collapses when prev segment is a discourse opener |
| Meeting cutoff ellipses | `append_cutoff_ellipsis` marks interrupted segment ends with `...`, e.g. `trying to...`, `And then...`, `go back to...` |
| Short completion before capitalized next turn | Move tiny preposition completions like `to` back to the previous speaker when next text starts a capitalized new turn, e.g. `go back` + `to We've already...` → `go back to...` / `We've already...` |
| Stranded capitalized turn opener | Move `So`/similar from end of one segment to next speaker when next segment starts with the same opener lowercased, e.g. `that So` + `so right now...` |
| Lowercase continuation blips | Collapse A-B-A fragments like `But yeah` + `if there's...` when same outer speaker and grammar proves continuity |
| Terminal completion blips | Collapse short middle fragments that complete the previous incomplete sentence, e.g. `I think that was really different` + `from her on my end.` |
| Content-question guard | Only move generic questions like `Why is that?` backward; keep content questions like `Why is community concerned?` with the speaker who asked them |
| `make sure` guard | Do not treat `sure` inside `make sure...` as a standalone short answer/cutoff |
| Speaker-assigned unnamed blips | In `_spasgn` files, generic `Speaker N` between the same assigned human speaker can collapse when continuation evidence is present |

Regression cases are named in `tests/test_stellar_denovo.py` (see below).


## Changes in `core/llm.py`
### `PROMPT_DENOVO_SINGLE_V2` (single / `_draftls`)
Reframed as **second pass after `_draftds`**, segmentation only:
- Use LLM only for: missed speaker split inside one segment; whole-segment speaker relabel when context is overwhelming; no-op when evidence is weak.
- Explicit invented examples (not deterministic-rule cases).
- No copyediting, no redoing obvious boundary repairs deterministic code already handles.

### `PROMPT_DENOVO_DUAL_V2` (dual / `_draftld`)
Kept arbitration intent with stricter guardrails:
- Segmentation arbitration only — no paraphrase, grammar fixes, filler removal, or polished third versions.
- Preserve timestamps verbatim from A or B; never reformat.
- Prefer version that keeps short answers / acknowledgements as separate turns when context supports it.
- Do not output both A and B copies of the same underlying speech span, even when speaker numbers differ.
- When speaker numbers differ, choose the label that best preserves local speaker continuity; do not invent speaker names unless real names already appear in the input.
- Examples: messy ASR (pick A or B, don't polish), `Isn't yeah` echo, ambiguous `Whereas` overlap (leave messy for human review), duplicate audience-question span (choose one copy only).

Current status: these prompt guardrails are kept, but `_draftld` remains paused because live runs still show severe word-accuracy collapse.


## Tests added in `tests/test_stellar_denovo.py`
New regression tests (direct `apply_deterministic_cleanup` or helper calls):

| Test | Covers |
|------|--------|
| `test_apply_deterministic_cleanup_preserves_short_meaningful_response_blip` | `I'm not sure` kept on correct speaker |
| `test_apply_deterministic_cleanup_splits_middle_turn_with_dangling_tail` | `Fair enough` / `Helping them` split |
| `test_apply_deterministic_cleanup_preserves_answer_after_question_when_next_echoes` | `Isn't yeah` echo — no blip merge |
| `test_apply_deterministic_cleanup_preserves_acknowledgement_blip` | `Yeah. Yeah.` on middle speaker |
| `test_apply_deterministic_cleanup_moves_question_tail_before_blip` | Question tail forwarded |
| `test_apply_deterministic_cleanup_preserves_discourse_opener_overlap_for_review` | `Whereas` overlap left intact (renamed/updated expectations) |
| `test_llm_segments_to_internal_preserves_timestamp_links` | Timestamp link copy from source segments |
| `test_apply_deterministic_cleanup_marks_meeting_cutoffs_with_ellipsis` | PV/EPC `trying to...` / `And then...` cutoff handling |
| `test_apply_deterministic_cleanup_moves_stranded_capitalized_turn_opener` | `that So` + `so right now` split |
| `test_apply_deterministic_cleanup_collapses_discourse_blip_before_lowercase_continuation` | `But yeah if...` blip collapse |
| `test_apply_deterministic_cleanup_collapses_terminal_blip_that_completes_sentence` | `different from her on my end.` blip collapse |
| `test_apply_deterministic_cleanup_does_not_cutoff_make_sure_phrase` | Avoid `make...` / `sure...` false cutoff |
| `test_apply_deterministic_cleanup_keeps_large_cutoff_phrase_before_tiny_completion` | `go back to...` cutoff with tiny completion |
| `test_repair_keeps_content_question_on_answer_speaker` | Keep content questions on asking speaker |
| `test_apply_deterministic_cleanup_collapses_unassigned_blip_between_named_speaker` | `_spasgn` generic `Speaker N` blip between same named speaker |
| `test_apply_deterministic_cleanup_preserves_unassigned_segment_without_continuation` | Avoid blindly merging standalone `Speaker N` in named transcripts |
| `test_denovo_dual_prompt_forbids_duplicate_a_b_copies` | Dual prompt duplicate-span guard |
| `test_denovo_dual_prompt_handles_disagreeing_speaker_numbers` | Dual prompt speaker-number mismatch guard |

Run:
```bash
.venv/bin/python3 -m pytest tests/test_stellar_denovo.py
```

Latest verification: `45 passed, 1 warning` (`UnsupportedFieldAttributeWarning`, non-blocking).


## LLM / dual ladder findings (not trustworthy yet)
Full ladder = deterministic + single LLM + dual LLM on same episode.

| Run | Observation |
|-----|-------------|
| Reason Is Fun Ep6 | `_draftls` ≈ `_draftds` (no harm, little gain on A); dual `word_acc` dropped to ~0.70–0.73 |
| Markus Arndt (3 speakers) | `_draftls_B` = `_draftds_B` (good); dual `word_acc` ≈ -0.97 (broken) |
| PV/EPC raw | `_draftds_B` improved to 143 errors / 98 strict; `_draftls` no practical gain; `_draftld` word accuracy collapsed (~0.33–0.35 on later runs) |
| PV/EPC `_spasgn` | Best deterministic result: `spasgn_dgwhspm_draftds` = 137 errors / 93 strict / 0.740 word accuracy; `_draftls_B` identical by metrics; `_draftld` still unsafe (`word_acc` ~0.328–0.350) |

User-facing issues before prompt tightening: LLM changed timestamp format, made incorrect copyedits, duplicated A/B spans, and dual merge produced worse word accuracy than raw. Prompt guardrails now document the intended behavior, but live output still copyedits/duplicates/drops content. **Dual merge architecture still needs redesign** before `_draftld` is usable.


## Recommendation (current)
| Variant | Status |
|---------|--------|
| `_draftds` | **Use** — best practical output; for PV/EPC prefer `spasgn_dgwhspm_draftds` when speaker-assigned input is available |
| `_draftls` | **Paused / experimental** — usually no gain over `_draftds`; sometimes slightly worse |
| `_draftld` | **Avoid / paused** — dual arbitration still not review-safe; copyedits, duplicates spans, drops words, and collapses word accuracy |
| `_draftls_draftld` | **Avoid / paused** — dual merge after single LLM remains messy and unsafe |

Report summary for Randy: tested deterministic cleanup on Deutsch samples and PV/EPC meeting transcripts via diff review; improved `denovo.py` for meeting cutoffs, blips, content-question false positives, and speaker-assigned generic `Speaker N` blips; single LLM prompt remains conservative but not useful enough; dual prompt is guardrailed but still very bad in live output. Ship/review `_draftds` for now.


## How to rerun
Fixture smoke (no API, no real files):
```bash
.venv/bin/python3 apps/transcription/stellar-transcriber/scripts/run_alignment_eval.py --fixture --skip-llm
```

One real episode (deterministic only):
```bash
RAW="data/deutsch/f9_raw"
REF="data/deutsch/f8_done_qafixed_and_vrb"
STEM="2024-01-01_Arjun Khemani - Free-Will TCS and Anarcho-Capitalism"

.venv/bin/python3 apps/transcription/stellar-transcriber/scripts/run_alignment_eval.py \
  --raw-a "$RAW/${STEM}_nova2gen.md" \
  --raw-b "$RAW/${STEM}_dgwhspm.md" \
  --ref "$REF/${STEM}_vrb.md" \
  --profile deutsch \
  --skip-llm
```

PV/EPC speaker-assigned deterministic run:
```bash
.venv/bin/python3 apps/transcription/stellar-transcriber/scripts/run_alignment_eval.py \
  --raw-a "data/pv/meetings_epc/f9_raw/2025-03-06_PV-EPC_spasgn_nova2gen.md" \
  --raw-b "data/pv/meetings_epc/f9_raw/2025-03-06_PV-EPC_spasgn_dgwhspm.md" \
  --ref "data/pv/meetings_epc/2025-03-06_PV-EPC_cemanual.md" \
  --profile pv \
  --skip-llm
```

PV/EPC single LLM only (currently paused unless testing):
```bash
.venv/bin/python3 apps/transcription/stellar-transcriber/scripts/run_alignment_eval.py \
  --raw-a "data/pv/meetings_epc/f9_raw/2025-03-06_PV-EPC_spasgn_nova2gen.md" \
  --raw-b "data/pv/meetings_epc/f9_raw/2025-03-06_PV-EPC_spasgn_dgwhspm.md" \
  --ref "data/pv/meetings_epc/2025-03-06_PV-EPC_cemanual.md" \
  --profile pv \
  --skip-dual
```

Omit `--skip-llm` / `--skip-dual` for full ladder (requires LLM API keys and can take ~30 minutes on PV/EPC). Fetch eval pairs first if data missing: `apps/transcription/stellar-transcriber/scripts/fetch_eval_pairs.py`.


## Git status at time of writing
Uncommitted changes in:
- `core/denovo.py`
- `core/llm.py`
- `tests/test_stellar_denovo.py`

Branch: `stellar-transcriber-start`. Commit when ready with scoped messages per repo convention (e.g. `fix(stellar-transcriber): …`, `test(stellar-transcriber): …`).


## Deferred / out of scope for this snapshot
- Redesign of `merge_dual_llm` island arbitration (anchor/island logic unchanged in this diff)
- Deterministic dual (`_draftdd`) — not exercised in this review pass
- Composite eval score / disfluency policy (`core/transcript_eval.py` gaps noted in `2026-07-03_project-notes.md`)
- Friendly wrapper script for one-stem eval commands
