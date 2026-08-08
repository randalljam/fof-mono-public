file: apps/transcription/stellar-transcriber/docs/2026-07-14_BA-iteration-notes.md
title: Stellar Transcriber — BA dual-selector iteration notes (Jul 2026)
last-updated: 2026-07-17_0100
ai: Cursor - Composer 2.5 Fast
session: `Stellar Transcriber — draftds review complete, deferred fixes noted`

Snapshot of the current Stellar Transcriber de novo cleanup state after the July 15 BA review and PV/EPC reruns. This supersedes the dual-LLM status in `apps/transcription/stellar-transcriber/docs/2026-07-09_BA-iteration-notes.md` and updates the word-anchored v3 design described in `apps/transcription/stellar-transcriber/docs/2026-07-11_dual-merge-redesign.md`.


## Current recommendation
- **Use `_draftds` as the dependable default.** On the current PV/EPC speaker-assigned sample, freshly regenerated `spasgn_dgwhspm_draftds` remains the best content-preserving result: **126 errors / 85 strict / 0.741 word accuracy** (rescore 2026-07-17). Manual review (2026-07-17) judged both March `_draftds` arms good overall — deterministic cleanup is in strong shape for this episode.
- **Next code work (documented, not started):** two remaining dgwhspm edge cases (comma-in-sentence cutoffs; end-of-segment errors skipped after a beginning fix). See deferred checklist below. Do not block production use of `_draftds` on these until more samples are reviewed.
- **Pause `_draftld` for production use** until a planned dual re-check. It is safe from LLM copyediting by construction, but prior manual review found too many incorrect A/B segmentation choices. Re-evaluation is scheduled after `_draftds` corpus review expands.
- **Pause `_draftls` speaker relabeling work.** It gives little aggregate gain over `_draftds` and live output still includes incorrect whole-segment speaker relabels.
- **Runtime remains a blocker** for full LLM ladders (~39–40 minutes).
- For production inputs, use the two raw or speaker-assigned ASR transcripts only. Human-reviewed files are evaluation references, never merge inputs.


## Pipeline terminology and current versions
```text
raw/spasgn A (_nova2gen) ─┐
                          ├─ deterministic cleanup in memory
raw/spasgn B (_dgwhspm) ──┘
        → word-anchored aligned chunks
        → oversized differences split at safe internal dual segment starts
        → match/wording chunks copied from base B
        → localized structural differences: LLM selects A or B only
        → selected source chunk copied verbatim
        → _draftld
```

Current configuration in `apps/transcription/stellar-transcriber/config/denovo-pipeline.json`:
- `pipeline_version`: `0.4.0`
- `prompts_version`: `denovo-v4`
- default model: `gpt-5-mini`
- base side: `b` (`_dgwhspm`)
- word anchors: minimum 6 matched words, 3 edge words
- match similarity threshold: 0.98
- adjacent read-only context: 2 segments
- retries: 3

Output suffixes remain:
- `_draftds`: deterministic single
- `_draftls`: LLM single
- `_draftdd`: deterministic dual
- `_draftld`: LLM dual


## Human reference separation
`merge_dual_llm` receives only transcript A and transcript B. It never receives `_cemanual`, `_vrb`, or another human-reviewed transcript.

The evaluation runner creates each draft first, then separately passes the finished draft and human reference to `score_alignment`. The chunk exploration script follows the same separation: A and B are the only LLM inputs; projected reference chunks are used afterward to score the selected side.

This preserves the real production condition: the dual merge must work when no human-reviewed transcript exists.


## Current `core/denovo.py` behavior
The word-anchored architecture introduced in pipeline 0.2.0 remains:
1. Run deterministic cleanup independently on A and B.
2. Flatten both cleaned transcripts into normalized word streams.
3. Use matched word runs to create cut points where both sources begin a segment.
4. Tile both transcripts into aligned chunks covering the same speech.
5. Subdivide oversized structural differences at relaxed matching-word anchors only where both sources already start a segment. If no safe cut exists, keep the parent chunk intact.
6. Classify each decision chunk:
   - `match`: near-identical text and segment count; copy base B.
   - `wording`: same turn structure with wording differences; copy base B.
   - `diff`: structural speaker segmentation differs; ask the v4 selector to choose A or B.
7. Deep-copy the chosen source chunk into the merged output.
8. If the selector response is invalid after retries, fall back to base B for that decision chunk only.

For v4 outputs, metadata includes:
```text
denovo pipeline version: 0.4.0
denovo prompts version: denovo-v4
denovo dual strategy: verbatim-side-selector
denovo base side: b
denovo parent chunk count: <count>
denovo chunk count: <count>
denovo diff chunk count: <count>
```


## Current `PROMPT_DENOVO_DUAL_V4`
The v4 prompt changes the LLM from a transcript generator into a side selector.

The structured tool output is only:
```json
{"selected_version": "a"}
```
or:
```json
{"selected_version": "b"}
```

Current selection rules:
- Choose the existing version with the better speaker segmentation.
- Choose a different version only for a meaningful existing turn, clearly better existing boundary, or clearly better existing speaker attribution.
- Never create a segment or speaker turn.
- Never return transcript text.
- Never decide based on grammar, punctuation, fluency, fillers, or copyediting quality.
- Treat speaker numbers as ASR-local labels and judge each version's internal turn-taking coherence with adjacent context.
- If the difference is ambiguous or requires audio judgment, choose base B.
- Copy the selected source exactly, including words, punctuation, timestamps, speaker labels, and boundaries.


## Short interjection clarification
The intended behavior for `yeah`, `yes`, `no`, `yep`, `right`, `okay`, and similar short interjections is:
- Never extract one from inside an unsplit source to invent a new speaker turn.
- If neither A nor B contains a separate turn, no separate turn may be created.
- If A or B already contains a separate turn, that segmentation is eligible for normal contextual comparison.
- The selector decides whether the existing split or unsplit version is more coherent; code does not automatically prefer either.

An intermediate v4 implementation incorrectly added an “always prefer unsplit” deterministic override. That bypassed the LLM whenever it found an A-B-A short-answer pattern. This was broader than the requirement and has been removed.

Regression coverage now proves that an existing short `Right.` turn remains eligible: when the mocked selector chooses the split source, the merge preserves that source exactly.


## Copyediting and invented-boundary guarantees
Problems in v2/v3 included paraphrasing, punctuation changes, duplicated A+B spans, generated consensus wording, and new speaker splits.

V4 prevents these structurally:
- The function schema does not contain speaker, timestamp, dialogue, or segment-list fields.
- The LLM cannot return transcript content through the expected tool call.
- `llm_select_dual_chunk_side` accepts only `a` or `b`.
- `merge_dual_llm` copies the selected source segment dictionaries instead of converting generated LLM segments.
- Invalid responses fall back to source B.

Therefore the dual LLM stage cannot copyedit, blend A/B wording, duplicate both versions, or invent a boundary absent from the selected source.


## Current prompt status
- `PROMPT_DENOVO_DUAL_V4` remains selector-only: the model returns `a` or `b`, never transcript text.
- Existing short-interjection splits remain eligible for contextual selection, but the model cannot create one absent from both sources.
- No new dual prompt text was added for pipeline 0.4.0. Today's main dual change was code-side decision localization, not prompt expansion.
- `PROMPT_DENOVO_SINGLE_V2` still permits a missed split or whole-segment speaker correction only when evidence is overwhelming. Live EPC output shows that the model still sometimes relabels mixed-speaker segments incorrectly, so this path remains experimental.


## Chunk prompt exploration
`apps/transcription/stellar-transcriber/scripts/explore_dual_prompts.py` now:
- calls `llm_select_dual_chunk_side`;
- records `selected_a`, `selected_b`, or base-side fallback;
- scores the selected existing source against the projected human reference;
- reports word similarity, segment count, boundary recall/precision, token usage, and cost.

The first five-chunk v4 selector run completed with no invalid responses or fallbacks. Mean word similarity versus reference was 0.9025 and mean boundary recall was 0.395. The mean word-similarity gain versus the better source was -0.0153, showing that selector decisions still need improvement even though generated text damage is eliminated.


## Latest PV/EPC full validation
Inputs:
- `data/pv/meetings_epc/f9_raw/2025-03-06_PV-EPC_spasgn_nova2gen.md`
- `data/pv/meetings_epc/f9_raw/2025-03-06_PV-EPC_spasgn_dgwhspm.md`

Evaluation-only reference:
- `data/pv/meetings_epc/2025-03-06_PV-EPC_cemanual.md`

Last full run before pipeline 0.4.0 localized decision subchunks:
- report: `data/stellar-eval/alignment-runs/alignment-ladder_2025-03-06_PV-EPC-spasgn-v4-contextual-interjections_2026-07-14_204220.md`
- runtime: 26 minutes 16 seconds
- model: `gpt-5-mini`
- 59 word-anchored chunks / 35 raw diff chunks

| Variant | Errors | Strict | Word accuracy |
|---------|-------:|-------:|--------------:|
| raw A (`nova2gen`) | 183 | 97 | 0.577 |
| raw B (`dgwhspm`) | 170 | 122 | 0.740 |
| `_draftds_A` | 162 | 85 | 0.577 |
| `_draftds_B` | **137** | 93 | **0.740** |
| `_draftls_A` | 165 | 87 | 0.577 |
| `_draftls_B` | **137** | 93 | 0.739 |
| `_draftld` from raws | **136** | 78 | 0.684 |
| `_draftld` after singles | 142 | **76** | 0.669 |

The dual raw selector reduced total errors 20.0% and strict errors 36.1% versus best raw B. It did not preserve B's word-accuracy level because choosing A for some chunks also chooses A's exact ASR wording. This is source selection, not copyediting.

The reviewed `Right.` example at 26:04 confirms the corrected behavior:
- raw dual selected A and preserved the existing separate Chris Raanes `Right.` turn;
- dual after singles selected B and kept it unsplit;
- both are valid selector outcomes from different A/B input pairs; neither was forced by code or created from human-reference information.

Pipeline 0.4.0 localized-decision full run:
- report: `data/stellar-eval/alignment-runs/alignment-ladder_2025-03-06_PV-EPC-spasgn-v4-localized-decisions_2026-07-15_222703.md`
- runtime: 39 minutes 26 seconds
- 75 decision chunks from 59 parents / 46 LLM-selected differences
- `_draftld` from raws: 143 errors / 80 strict / 0.667 word accuracy
- `_draftld` after singles: 142 errors / 78 strict / 0.680 word accuracy

The localized target behaved correctly: the Kristi/Chris/Jerry exchange selected dgwhspm, preserving separate Chris and Jerry turns. Overall episode metrics did not improve versus the prior 0.3.0 full run, and runtime increased because localized decisions raised the LLM calls from 35 to 46 per dual variant.

Second pipeline 0.4.0 validation (`2025-02-06_PV-EPC`):
- report: `data/stellar-eval/alignment-runs/alignment-ladder_2025-02-06_PV-EPC-spasgn-v4-localized-decisions_2026-07-15_231344.md`
- runtime: 40 minutes 5 seconds
- 56 decision chunks from 47 parents / 35–36 LLM-selected differences
- best deterministic: `_draftds_A` = 166 errors / 110 strict / 0.669 word accuracy
- `_draftld` from raws = 153 errors / 99 strict / 0.717 word accuracy
- `_draftld` after singles = **146 errors / 95 strict / 0.715 word accuracy**

Unlike the March sample, localized dual selection materially improved February segmentation: the after-singles dual reduced total errors 30.1% and strict errors 35.4% versus best raw A. All 56 output decisions matched source A or B exactly (27 A / 29 B), confirming no dual-stage copyediting or invented text.

Manual review still judged the February dual output insufficiently reliable despite the metric improvement. The metrics confirm aggregate boundary gains, not that every local A/B choice is correct.


## Additional deterministic safety fixes
- Preserve sentence-completing A-B-A middle words: `You can` / `hear me` / `okay here?` now becomes `You can hear me okay here?` instead of dropping `hear me`.
- After all boundary and blip repairs finish, mark a remaining unpunctuated turn with `...` when the next different speaker starts with a capital letter. No words move between speakers. Example: `I can always flip` + `Yeah. No...` becomes `I can always flip...` + `Yeah. No...`.
- Skip the cutoff marker after commas, semicolons, colons, complete short responses, and short discourse-overlap openers so it does not interfere with earlier structural repairs or produce invalid punctuation such as `,...`.
- Move a trailing comma acknowledgement onto the next speaker when it follows a completed sentence, e.g. `Okay. Yeah,` + `I'm sorry...` becomes `Okay.` + `Yeah, I'm sorry...`.
- Replace a transcription-tool cutoff dash at the end of a segment (`-`, `–`, or `—`) with exactly `...`, e.g. `So-` becomes `So...` rather than `So-...`.
- Merge adjacent segments when one is only a short phrase and the substantially longer segment completes it. Keep the earlier timestamp/link and use the longer segment's speaker name. Skip A-B-A overlap patterns and require the longer side to contain at least twice as many words as the phrase.
- Removed the destructive “drop middle speaker noise” path. A-B-A blip words are never deleted; 5–6 word middle fragments now use the same content-preserving merge as shorter blips.
- Run specific broken-boundary repairs before the general phrase-only fallback so cases such as stranded `So` are categorized correctly.
- Merge all consecutive same-speaker segments in raw deterministic cleanup, keeping the earliest timestamp. This is not rerun after LLM speaker changes.
- Extracted the duplicated A-B-A logic into one shared content-preserving pass that runs before and after boundary repair.
- Question-tail repair now backtracks one pair after a successful move so a newly exposed neighboring case is not skipped.

Latest March deterministic-only rerun after phrase merging:
- report: `data/stellar-eval/alignment-runs/alignment-ladder_2025-03-06_PV-EPC-spasgn-draftds-phrase-merge_2026-07-16_000833.md`
- `_draftds_A`: 153 errors / 74 strict / 0.577 word accuracy
- `_draftds_B`: **130 errors / 88 strict / 0.740 word accuracy**

Latest March deterministic-only rerun after rule-order cleanup:
- report: `data/stellar-eval/alignment-runs/alignment-ladder_2025-03-06_PV-EPC-spasgn-draftds-organized-rules_2026-07-16_002658.md`
- `_draftds_A`: 158 errors / 82 strict / 0.577 word accuracy
- `_draftds_B`: **126 errors / 85 strict / 0.741 word accuracy**


## Rejected post-LLM merge experiment
A post-LLM step was briefly added to merge two or three consecutive segments after the single LLM changed them to the same speaker. It correctly combined one Craig/Jerry/Craig cutoff example, but exposed a more serious failure: the LLM sometimes relabeled an entire mixed-speaker segment as Tom, and the merge then amplified that wrong label across adjacent Tom segments.

That post-LLM relabel merge was fully removed before this snapshot. Current `_draftls` preserves the LLM-returned segment boundaries and does not automatically combine runs created by speaker relabeling.


## Draftds regeneration (2026-07-17)
Resumed deferred checklist item 1: regenerate on-disk March EPC `_draftds` files from current `core/denovo.py` (pipeline 0.4.0) before manual review.

**Command used** (`create_draft_deterministic`, profile `pv`):
```bash
.venv/bin/python3 - <<'PY'
# see session; build_draft_transcript.py also works once elevenlabs import is mocked/skipped
from core.denovo import create_draft_deterministic
create_draft_deterministic("data/pv/meetings_epc/f9_raw/2025-03-06_PV-EPC_spasgn_nova2gen.md", profile="pv")
create_draft_deterministic("data/pv/meetings_epc/f9_raw/2025-03-06_PV-EPC_spasgn_dgwhspm.md", profile="pv")
PY
```

**Outputs written:**
- `data/pv/meetings_epc/f9_raw/2025-03-06_PV-EPC_spasgn_nova2gen_draftds.md` — `denovo repair count: 45`
- `data/pv/meetings_epc/f9_raw/2025-03-06_PV-EPC_spasgn_dgwhspm_draftds.md` — `denovo repair count: 49`

**Rescore vs `_cemanual`** (existing `_draftls` / `_draftld` files unchanged; no LLM calls):
| Variant | Errors | Strict | Word accuracy |
|---------|-------:|-------:|--------------:|
| raw A (`nova2gen`) | 183 | 97 | 0.577 |
| raw B (`dgwhspm`) | 170 | 122 | 0.740 |
| **`draftds_A` (fresh)** | **158** | **82** | 0.577 |
| **`draftds_B` (fresh)** | **126** | **85** | **0.741** |
| `draftls_A` (stale) | 165 | 88 | 0.577 |
| `draftls_B` (stale) | 137 | 93 | 0.740 |

B-arm metrics match the 2026-07-16 organized-rules rerun. A-arm remains worse than the pre–same-speaker-merge best (153 / 74) — same-speaker merge review is still open (deferred item 3).

**Pipeline-change ledger** (draftds-only run, 2026-07-17):
- Live run: `data/stellar-eval/review-ledgers/pipeline-change-ledger_2025-03-06_PV-EPC-draftds-regen_2026-07-17_002402.md`
- Reference (full six stages, committed): `apps/transcription/stellar-transcriber/references/pipeline-change-ledger-sample-only.md`
- Active review uses the draftds-only run (**94** decisions; stages `raw_to_draftds_a`, `raw_to_draftds_b`). The reference sample shows all six pipeline stages (**207** decisions) for format comparison only.

```bash
.venv/bin/python3 apps/transcription/stellar-transcriber/scripts/build_review_ledger.py pipeline-change \
  --profile pv --run-suffix draftds-regen \
  --raw-a data/pv/meetings_epc/f9_raw/2025-03-06_PV-EPC_spasgn_nova2gen.md \
  --raw-b data/pv/meetings_epc/f9_raw/2025-03-06_PV-EPC_spasgn_dgwhspm.md
```

**Manual review (2026-07-17):** Both regenerated `_draftds` outputs judged **good overall**. Deterministic cleanup is doing strong work on this episode.

| Arm | Source | Verdict |
|-----|--------|---------|
| A | nova2gen (Deepgram Nova) | All good — almost no remaining beginning/end boundary errors. |
| B | dgwhspm (Deepgram Whisper) | Good overall — **2** remaining issues understood; root causes documented in deferred checklist (no code change yet). |

**Next:** expand review to additional episodes (deferred item 3); then revisit dual (deferred item 4). Targeted deterministic fixes for the two dgwhspm edge cases wait until after broader sample review unless a fix is obvious from logged examples.


## Bulk review ledger
`apps/transcription/stellar-transcriber/scripts/build_review_ledger.py` supports three modes:

**Pipeline-change** (stage-to-stage, no human reference) — primary tool for `_draftds` QA. Only includes stages you pass on the CLI.

Draftds-only (current active review):
```bash
.venv/bin/python3 apps/transcription/stellar-transcriber/scripts/build_review_ledger.py pipeline-change \
  --profile pv --run-suffix draftds-regen \
  --raw-a data/pv/meetings_epc/f9_raw/2025-03-06_PV-EPC_spasgn_nova2gen.md \
  --raw-b data/pv/meetings_epc/f9_raw/2025-03-06_PV-EPC_spasgn_dgwhspm.md
```

Full pipeline (all six stages — when `_draftls` / `_draftld` outputs exist and you want the whole ladder in one report):
```bash
.venv/bin/python3 apps/transcription/stellar-transcriber/scripts/build_review_ledger.py pipeline-change \
  --profile pv --run-suffix full-pipeline \
  --raw-a data/pv/meetings_epc/f9_raw/2025-03-06_PV-EPC_spasgn_nova2gen.md \
  --raw-b data/pv/meetings_epc/f9_raw/2025-03-06_PV-EPC_spasgn_dgwhspm.md \
  --draftls-a data/pv/meetings_epc/f9_raw/2025-03-06_PV-EPC_spasgn_nova2gen_draftls.md \
  --draftls-b data/pv/meetings_epc/f9_raw/2025-03-06_PV-EPC_spasgn_dgwhspm_draftls.md \
  --draftld data/pv/meetings_epc/f9_raw/2025-03-06_PV-EPC_spasgn_nova2gen_draftld.md \
  --draftls-draftld data/pv/meetings_epc/f9_raw/2025-03-06_PV-EPC_spasgn_nova2gen_draftls_draftld.md
```

**Reference sample (committed):** `apps/transcription/stellar-transcriber/references/pipeline-change-ledger-sample-only.md` — March EPC full six-stage report (207 decisions) saved for documentation. Shows the alignment-ladder-style row labels (`raw_A_nova2gen → draftds_A`, …, `draftls A+B → draftld_singles`) and per-stage decision breakdowns. Not a live run artifact; use timestamped outputs under `data/stellar-eval/review-ledgers/` for actual review sessions.

Default output: `data/stellar-eval/review-ledgers/pipeline-change-ledger_{episode}_{suffix}_{timestamp}.md`. Pass `--out` to pin a path and preserve JSON review fields across regenerations.

**Single** (raw → draftds vs human reference) — eval-vs-ref cases:
```bash
.venv/bin/python3 apps/transcription/stellar-transcriber/scripts/build_review_ledger.py single \
  --raw <raw.md> --draft <draftds.md> --ref <cemanual-or-vrb.md> --profile pv
```

**Dual** (source A/B → dual output vs human reference):
```bash
.venv/bin/python3 apps/transcription/stellar-transcriber/scripts/build_review_ledger.py dual \
  --raw-a <source-a.md> --raw-b <source-b.md> --dual-output <draftld.md> \
  --ref <cemanual-or-vrb.md> --profile pv
```

Each run writes JSON for review status/category/notes and Markdown for reading in Cursor. Existing manual review fields are preserved by stable case ID when regenerated.

First March single ledger: 201 cases = 145 remaining / 40 fixed / 16 made worse. These are alignment-generated review candidates, not automatically trusted judgments; manual review confirms or corrects each category.


## Tests
Run:
```bash
.venv/bin/python3 -m pytest tests/test_stellar_denovo.py
```

Latest targeted result: `95 passed, 1 warning` across review-ledger, alignment-fixture, and denovo tests.

The warning is the existing non-blocking `UnsupportedFieldAttributeWarning`. Lint diagnostics report no errors in the edited files.

Current v4 tests cover:
- valid A/B structured selection;
- rejection of generated transcript payloads;
- verbatim copying of a selected chunk;
- invalid-response fallback to base B;
- existing short-interjection split eligibility;
- wording-only chunk pass-through;
- word-anchored chunk tiling and classification;
- safe oversized-diff subdivision and exact source coverage;
- independent A/B selection and fallback per decision subchunk;
- v4 prompt and resolver selection.


## Current limitations and next work
1. **Dual selection is paused.** Pipeline 0.4.0 reduces the scope of oversized decisions, but manual review still finds too many locally wrong choices.
2. **Word accuracy remains below best B.** Any A selection also selects A's wording; v4 intentionally does not blend B wording with A segmentation.
3. **Runtime worsened with localization.** The pipeline 0.4.0 full ladder took about 39 minutes because diff decisions increased from 35 to 46 per dual variant and are processed sequentially.
4. **Human review remains useful for development evaluation.** It must remain isolated from production merge inputs.
5. **Metrics are not sufficient approval.** February aggregate scores improved while manual review still rejected the output quality.
6. **Do not run further full dual evaluations until the selection strategy is reconsidered** — but a **planned dual re-check** remains on the deferred list after more `_draftds` samples are reviewed (see below).
7. **Phrase thresholds still need corpus-level review.** Existing helpers use limits of 3, 4, 6, and 8 words for different boundary types; these should not be standardized without checking more real examples.


## Deferred deterministic cleanup review
Checklist for the next deterministic / pipeline iteration. **No code changes started** for items 1–2 as of 2026-07-17 — document first, fix after more samples or when examples are pinned.


### Done
**March EPC `_draftds` manual review (2026-07-17).**
- Fresh `_draftds` regenerated for both arms (45 / 49 repairs).
- Live draftds-only ledger: `data/stellar-eval/review-ledgers/pipeline-change-ledger_2025-03-06_PV-EPC-draftds-regen_2026-07-17_002402.md`
- Full-ladder format reference: `apps/transcription/stellar-transcriber/references/pipeline-change-ledger-sample-only.md`
- **Verdict:** both arms good; nova2gen essentially clean on beginning/end errors; dgwhspm has two understood misses (below).


### Next (priority order)

1. **Cutoff not repaired when the interrupted sentence contains commas (dgwhspm).**
   - Observed on March EPC Whisper arm: a cutoff that should get `...` / word-move treatment was left alone.
   - Likely related to the existing guard that skips cutoff marking after commas, semicolons, colons, complete short responses, and discourse-overlap openers (see “Additional deterministic safety fixes” above).
   - **Planned fix (later):** narrow the comma guard — distinguish “sentence continues after comma” from “comma ends a complete clause but turn is still cut off mid-thought.” Capture the two March examples in a regression test before changing behavior.

2. **Second error at segment end skipped after a beginning fix on the same segment (dgwhspm).**
   - When deterministic repair fixes the **start** of a segment (e.g. blip merge or boundary word move), a separate problem at the **end** of that same segment can remain unfixed in the same pass.
   - **Planned fix (later):** after a repair mutates a segment, re-run applicable boundary/cutoff checks on that segment (or loop until stable) so beginning and end repairs are not mutually exclusive in one cleanup sweep. Add a regression from the March Whisper example.

3. **Review `_draftds` on more samples.**
   - March EPC alone is not enough to tune phrase limits, same-speaker merge, or comma/cutoff rules.
   - Pick 2–4 additional PV/EPC (or other profile) episodes; regenerate `_draftds`; run pipeline-change ledgers with `--run-suffix` per episode.
   - Goal: confirm March verdict generalizes before implementing items 1–2.

4. **Re-check dual (`_draftld`).**
   - Still paused for production, but worth another look after `_draftds` is validated on more files.
   - Use alignment rescore + pipeline-change ledger with explicit `--draftld` / `--draftls-*` flags (see full-pipeline command in Bulk review ledger). Compare to pre-0.4.0 manual review notes; do not assume aggregate metrics alone.


### Still deferred (lower priority until more samples)

5. **Review phrase-length limits across real transcripts.**
   - Current rules use limits of 3, 4, 6, and 8 words for different cases.
   - Build a small review set containing correct and incorrect examples near each limit.
   - Decide whether each rule needs its own limit or whether some can safely share one.
   - Do not increase limits without checking for overlap/crosstalk false positives.

6. **Review all new capitalized cutoff ellipses.**
   - Diff raw versus `_draftds` and inspect every new `interrupted_turn_ellipsis` log.
   - Look specifically for capitalized `I`, proper names, acronyms, and quoted words.
   - Add explicit exceptions rather than moving this rule earlier; it should remain the final annotation step.

7. **Review unconditional same-speaker merging across more files.**
   - The rule now combines A-A and B-B-B runs in raw deterministic cleanup.
   - It improved March dgwhspm but worsened nova2gen from 153 to 158 errors.
   - Compare several interview and meeting transcripts to determine whether some legitimate same-speaker boundaries should remain.
   - Keep this rule out of the post-LLM stage because LLM speaker relabeling is still unreliable.

8. **Review phrase-only merging beyond the three current EPC examples.**
   - Current guard: phrase is at most 8 words, the longer side has at least twice as many words, the continuation starts lowercase, and the pair is not inside A-B-A.
   - Inspect every `merge_phrase_only_transition` log on additional files.
   - Pay special attention to short but meaningful replies that happen to begin lowercase.

9. **Confirm the two A-B-A passes remain necessary.**
   - They now share one helper, so the code cannot drift between passes.
   - Add a focused regression where the first pass cannot fix a case but a boundary move makes the second pass necessary.
   - If no real example requires the second pass, simplify to one pass; otherwise document the example beside the code.

10. **Rename old “noise” terminology.**
    - The destructive drop rule has been removed and blip words are now always preserved.
    - Remaining helper names such as `is_short_overlap_noise_fragment` should be renamed to describe content-preserving continuation behavior.
    - Do this as a separate refactor with no behavior changes.


## Files changed in this iteration
- `apps/transcription/stellar-transcriber/config/denovo-pipeline.json`
- `apps/transcription/stellar-transcriber/scripts/extract_dual_chunks.py`
- `apps/transcription/stellar-transcriber/scripts/explore_dual_prompts.py`
- `apps/transcription/stellar-transcriber/references/pipeline-change-ledger-sample-only.md`
- `core/denovo.py`
- `core/llm.py`
- `tests/test_stellar_denovo.py`
- `apps/transcription/stellar-transcriber/docs/2026-07-14_dual-selector-implementation-plan.md`
- `apps/transcription/stellar-transcriber/docs/2026-07-14_BA-iteration-notes.md`
- `apps/transcription/stellar-transcriber/docs/2026-07-15_dual-decision-subchunks-implementation-plan.md`

These changes are currently uncommitted.
