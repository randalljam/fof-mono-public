# Stellar Transcriber evaluation
_Exported on 7/21/2026 at 16:05:04 PDT from Cursor (3.10.20)_

---

**User**

@core/transcript_eval.py Okay, so I'm jumping back into this project and this application called Stellar Transcriber and what I want you to do is find the list of five, I think it's five David Deutsch transcripts that we use as like a test bed and make sure you have those references and that links, those links and tell me what those are and tell me how you're how you're storing those and where they're where basically the file paths to those are and how I can, how should I reference them and then what I want you to do is go to the, in core there is a transcript eval python package here, I'm just going to drag it into this context window and then what I want you to do is I want you to run the segmentation evaluation code, I'm trying to review, it's been so long since I made this, I'm trying to review what it is there's top level eval so my recollection was that there are certain sections I'm looking at the transcript eval steps what is currently used for the, I think I sometimes called it segmentation, sometimes alignment, sometimes transitions what is that metric and what is the code that's used, I think it's alignment, so there's like compute, sub score alignment metric what does that do, I want to focus in on this segment alignment and I want to understand what the eval code, how the eval code works for that, what's the current active function that's called to compute that and then I want you to run that on the deep gram whisper medium and deep gram nova 2 transcripts against the Deutsch reference ones for this Deutsch set of 5 so summarize my ask because it's been kind of discursive and messy here and then do everything I ask in here but start with a summary of what my asks are.

---

**Cursor**

**Summary of your asks**

1. Identify the Deutsch test-bed set (~5 transcripts): links, storage, file paths, how to reference them
2. Explain the segment-alignment eval in `core/transcript_eval.py` (segmentation / alignment / transitions) — active metric and how it works
3. Run that alignment eval: Deepgram Whisper Medium + Deepgram Nova 2 vs the Deutsch reference set of 5

I'll start by locating the test-bed paths and the active alignment code.

Found Deutsch10 and a “next-five” set in the stellar-transcriber docs. Digging into those lists and the alignment eval path next.

Running alignment-only eval on the five-set (nova2gen + dgwhspm vs `_vrb` refs).

Stubbing the unused ElevenLabs import so we can run the alignment eval.

## Your asks (summary)

1. Identify the ~5 Deutsch test-bed transcripts (links, storage, paths, how to reference them)
2. Explain the segment-alignment / segmentation / transitions metric in `core/transcript_eval.py` — what’s active and how it works
3. Run that alignment eval: Deepgram Whisper Medium (`_dgwhspm`) + Nova 2 (`_nova2gen`) vs the Deutsch `_vrb` refs for that set of 5

---

## 1. The Deutsch five-set

This is the **“Deutsch10 next-five”** set used in M3B (documented in `apps/transcription/stellar-transcriber/references/m3b-model-comparison.md`). It’s the first five of historical `BATCH_DEUTSCH_LAST_10` in `core/transcript_eval.py` (minus the Boghossian pilot).

| # | Stem (how you reference it) | YouTube |
|---|-----------------------------|---------|
| 1 | `2024-08-26_Reason Is Fun - Ep6 Are Feelings Ideas` | https://youtu.be/25kJdNHlZk0 |
| 2 | `2024-03-31_Sagenhaft und Sonderbar der Podcast` | https://youtu.be/EozCoAeMPTA |
| 3 | `2024-03-04_Alex OConnor - The Multiverse is Real` | https://youtu.be/bux0SjaUCY0 |
| 4 | `2024-01-04_Reason Is Fun - Ep5 The Art of Decision Making` | https://youtu.be/Sdgl_Z3Tc7Y |
| 5 | `2024-01-01_Arjun Khemani - Free-Will TCS and Anarcho-Capitalism` | https://www.youtube.com/watch?v=Hh9xOB2oDHk |

**How files are stored / named**

| Role | Suffix | Folder |
|------|--------|--------|
| Human reference (gold) | `_vrb.md` | `data/deutsch/f8_done_qafixed_and_vrb/` |
| Deepgram Nova 2 | `_nova2gen.md` | `data/deutsch/f9_raw/` |
| Deepgram Whisper Medium | `_dgwhspm.md` | `data/deutsch/f9_raw/` |

Example:
- Ref: `data/deutsch/f8_done_qafixed_and_vrb/2024-08-26_Reason Is Fun - Ep6 Are Feelings Ideas_vrb.md`
- Nova2: `data/deutsch/f9_raw/2024-08-26_Reason Is Fun - Ep6 Are Feelings Ideas_nova2gen.md`
- Whisper: `data/deutsch/f9_raw/2024-08-26_Reason Is Fun - Ep6 Are Feelings Ideas_dgwhspm.md`

Same triples also live in the M3B review bundle: `data/stellar-eval/m3b-five-model-review/inputs/`.

**How to reference them in code:** use the stem list + standard suffixes via `create_eval_ref_pairs` / `evaluate_raw_with_std_suffixes` (`ref_folder=f8…`, `eval_folder=f9_raw`, `ref_suffixpat="_vrb.md"`, `eval_suffixpat_list=["_nova2gen.md","_dgwhspm.md"]`).

Note: there is also a full **Deutsch10** (`BATCH_DEUTSCH_LAST_10`, 10 titles). The five above are the recent focused test bed.

---

## 2. Alignment / segmentation metric — what it is

Naming in the code:
- **Active name:** **alignment** (composite weight 20%)
- **Computation step:** `evaluate_step_segments_align` (under `### TRANSCRIPT EVAL STEPS`)
- **Score rollup:** `compute_subscore_alignment`
- **`evaluate_transitions`:** aborted WIP — not used
- Segmentation / transitions language in comments = same alignment dimension (boundary placement)

**Call chain (full eval):**
`evaluate_transcript` → first step is `evaluate_step_segments_align(...)` → later `compute_composite_scores` → `compute_subscore_alignment(metrics)`.

**What `evaluate_step_segments_align` does**

1. Normalize dialogue; 3-pass segment matching (anchors by unique timestamp + gap, then fill gaps, then leftover eval segments)
2. Classify each aligned segment’s **boundary** (start/end words vs ref; “misplaced” if displaced words sit across the transition)
3. Absolute error accounting:
   - **missing** = ref segments with no eval counterpart
   - **spurious** = eval segments marked `is_delete`
   - **boundary-error** = aligned but start/end on wrong side
   - `seg_error_count = missing + spurious + boundary_error`
   - strict variant uses only misplaced boundaries (repairable segmentation)

**What `compute_subscore_alignment` does**

```text
subscore_alignment = 100 * (1 - seg_error_count / total_ref_segments)   # clamped 0–100
```

Legacy fallback (if no `seg_error_count`): aligned fraction minus delete/missing penalties.

---

## 3. Alignment run results (five-set × 2 ASR)

Ran alignment-only on all 10 pairs. Outputs:
`data/deutsch/dev-eval/align_results_five_2026-07-21_153008/`
(CSV + per-file `.log.md`)

| Episode | Nova2 `subscore_alignment` | WhisperM `subscore_alignment` |
|---------|---------------------------:|------------------------------:|
| Ep6 Feelings Ideas | 26.51 | **63.86** |
| Sagenhaft | 29.20 | 30.97 |
| Alex O’Connor Multiverse | 24.26 | 22.49 |
| Ep5 Decision Making | 51.39 | **58.33** |
| Arjun Khemani | 53.57 | **67.86** |
| **Mean** | **36.99** | **48.70** |

**Takeaway:** Whisper Medium wins on mean alignment (~49 vs ~37). Biggest gap is Ep6 (64 vs 27). Boundary errors dominate total `seg_error_count` on both ASRs; strict (repairable) errors are much lower.

**Caveat:** import currently requires stubbing `elevenlabs` (not in `.venv`); alignment itself doesn’t need it — top-level import in `transcript_eval.py` is the blocker.

---

**User**

So is this alignment code good? Is it accurate? Is it working? Is the metric that it produces a reliable measure of basically the percent of the segments that match the reference with respect to the boundary placement? What I'm wondering is can we use this for evaluation of code that corrects the alignment, corrects these boundary errors. Because that's what we're trying to produce in this Stellar Transcriber app is automated improvement of these di-rise transcripts in one of the most important and starting areas is this alignment or boundary placement. So is the current eval code sufficient to give us a numeric metric for that?

---

**Cursor**

Good question — the metric’s usefulness for boundary-correction hinges on whether it isolates segmentation defects from ASR word errors. I’ll check that distinction in the code and against a couple of real scored segments.

**Short answer:** The alignment code works and is useful, but the headline `subscore_alignment` is **not** a clean “% of segments with correct boundary placement.” For evaluating boundary-fix code, use the **strict** accounting (`seg_error_count_strict` / misplaced + missing + spurious), not the current composite alignment subscore.

### Is it working / accurate?
**Yes, it runs and the machinery is sound:**
- Matches eval segments to ref segments (anchors → fill gaps → leftovers)
- Counts missing / spurious segments
- Classifies boundaries, and explicitly separates repairable “misplaced text” from ASR edge word errors

That last split is the important part — the code already knows the distinction your product cares about.

### Is `subscore_alignment` the right metric for boundary repair?
**No — not as currently defined.**

It uses:
```text
100 * (1 - seg_error_count / total_ref)
```
where
```text
seg_error_count = missing + spurious + boundary_error
```

`boundary_error` includes many segments that are **aligned correctly but have ASR word differences at the edge** (not fixable by moving a cut).

Ep6 Whisper example from the run you just did:
- 52 `boundary_error`, but only **20 misplaced** (true cut/bleed)
- **32** are ASR-edge-only (e.g. `head on` vs `headon`, `as familiar` vs `this familiar`)
- Loose score: **63.9** · Strict score: **83.1**

So the published alignment subscore mixes segmentation quality with word accuracy. A perfect boundary-fixer can leave that score mostly stuck.

### What *is* a reliable numeric metric for your use case?
For “did we fix diarization / boundary placement?” track:

| Signal | Meaning |
|--------|---------|
| `seg_missing_count` | Ref speaker-turn absent in eval |
| `seg_spurious_count` | Extra eval turn with no ref |
| `seg_boundary_misplaced_count` | Words actually landed on the wrong side of a cut |
| **`seg_error_count_strict`** | `missing + spurious + misplaced` ← use this |
| Strict score | `100 * (1 - strict / total_ref)` |

That is much closer to “percent of segments whose boundary placement matches the reference” (as an error-rate inverted to a score).

Caveats even for strict:
- Matching mistakes can cascade into false missing/spurious
- Misplaced detection is phrase-probe based (can miss subtle bleeds / rare false positives)
- Good enough as a **primary regression metric** for boundary repair; spot-check a few episodes when scores move a lot

### Bottom line for Stellar Transcriber
- **Sufficient infrastructure:** yes — `evaluate_step_segments_align` already produces the numbers you need
- **Sufficient as currently rolled into `subscore_alignment`:** **no** for boundary-correction eval
- **Use instead:** strict segment-error rate / strict score (and report missing / spurious / misplaced separately)

If you want, next step is a small change: make `compute_subscore_alignment` (or a sibling `compute_subscore_alignment_strict`) use `seg_error_count_strict`, and wire that as the metric for alignment-repair experiments.

---

**User**

Okay, then what I want you to do is to update the transcript eval to use the new metric that you created and have this be an addition that I want to be able to revert and use my previous metric if I want to and then, so yeah, so have this be sort of additional code but then change the compute sub-score alignment so that it uses the new metric rather than the old one and just comment that appropriately or if it makes sense to, I mean maybe what it makes sense to do is to create a compute sub-score alignment loose and a compute sub-score alignment strict and then, have the roll-up code which is I think like the compute composite scores whichever one rolls up all the different areas call the strict one instead of the lose and then I'll be clear what's going on and then I want you to reproduce the table that we did for the sub score alignment but with sub score alignment strict and just round it to the nearest tenth don't give two don't give two decimal places just give one decimal place but actually you know put the loose and the strict right next to each other for for these sub score alignments and around each to just a single decimal place okay that oh and by the way update the import to comment out the 11 labs and I think there might might need to comment out some code is this the transcribe oh I think the transcribe the 11 lab scribe yeah how do we just kind of comment that out I guess you just comment out that whole section but I'm not sure just figure out a way to disable comment that out but not like delete

---

**Cursor**

I'll add strict/loose alignment subscores (rollup → strict), comment out ElevenLabs without deleting it, then rerun the five-set table with both scores to one decimal.

Implementing strict/loose alignment subscores, disabling ElevenLabs imports (keeping the scribe helpers), updating tests, then rerunning the table.

Tests passed and import works without ElevenLabs. Rerunning the five-set table with loose vs strict.

Done. Summary of changes:

### Code (`core/transcript_eval.py`)
- **`compute_subscore_alignment_loose`** — previous metric (`seg_error_count`)
- **`compute_subscore_alignment_strict`** — new metric (`seg_error_count_strict`)
- **`compute_subscore_alignment`** — alias → strict
- **`compute_composite_scores`** — rolls up **strict** into `subscore_alignment`, and also writes both `subscore_alignment_strict` and `subscore_alignment_loose`
- To revert overall rollup: one-line swap noted in `compute_composite_scores`

### ElevenLabs
- Imports / env load **commented out** at top (not deleted)
- Helpers kept; guarded by `_ELEVENLABS_SCRIBE_ENABLED = False` with a clear re-enable message
- Module imports cleanly without `elevenlabs` installed

### Tests
`tests/test_stellar_eval_scoring.py` — 23 passed

### Five-set: loose vs strict (1 decimal)

| Episode | ASR | loose | strict |
|---------|-----|------:|-------:|
| Ep6 Feelings Ideas | nova2 | 26.5 | 71.7 |
| Ep6 Feelings Ideas | whisperM | 63.9 | 83.1 |
| Sagenhaft | nova2 | 29.2 | 68.1 |
| Sagenhaft | whisperM | 31.0 | 68.1 |
| Alex O’Connor | nova2 | 24.3 | 56.8 |
| Alex O’Connor | whisperM | 22.5 | 51.5 |
| Ep5 Decision Making | nova2 | 51.4 | 82.6 |
| Ep5 Decision Making | whisperM | 58.3 | 74.3 |
| Arjun Khemani | nova2 | 53.6 | 85.7 |
| Arjun Khemani | whisperM | 67.9 | 82.1 |
| **MEAN** | **nova2** | **37.0** | **73.0** |
| **MEAN** | **whisperM** | **48.7** | **71.8** |

On strict, the two ASRs are much closer (nova2 slightly ahead on mean); loose had overstated Whisper’s edge because of ASR edge-word “boundary” noise.
