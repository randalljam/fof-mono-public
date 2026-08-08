file: apps/transcription/stellar-transcriber/docs/2026-07-11_dual-merge-redesign.md
title: Stellar Transcriber — word-anchored dual merge redesign and first results
last-updated: 2026-07-11_1820
ai: Claude Code - Fable 5
session: `Stellar Transcriber — dual merge redesign from BA review`

Response to the 2026-07-09/10 BA review (`2026-07-09_BA-iteration-notes.md`), which concluded `_draftds` is the only trustworthy variant and `_draftld` (LLM dual) is broken. This iteration diagnosed the dual failure, rebuilt the dual path on word-anchored chunking, added the chunk-triple exploration dataset, and validated on live runs.


## Diagnosis — why `_draftld` collapsed
Two compounding, code-confirmed defects:
1. **Timestamp anchors never fire across two ASR models.** `find_anchors_between_transcripts` required exact timestamp-string equality between `_nova2gen` and `_dgwhspm`. Real pairs almost never match (7 anchors on the 75-minute `2025-03-06_PV-EPC`), so islands degenerated into index-parallel 20-segment windows pairing *different audio*, and the LLM was asked to reconcile unrelated text.
2. **No word-conservation guard on the dual path.** The single path enforces ≥0.995 in/out text similarity; `llm_arbitrate_dual_island` had no equivalent, so paraphrase, duplicated A+B copies, and drops passed validation into the merged output.

Together these produced the observed word-accuracy collapse (~0.33 on PV/EPC, negative on Markus Arndt).


## New architecture (in `core/denovo.py` / `core/llm.py`, pipeline 0.2.0, prompts denovo-v3)
Word-anchored chunking, per the M4 plan's named redesign direction ("anchor on matching word n-grams, not whole-segment equality"):
- **Word anchors:** both deterministic-cleaned transcripts flatten to normalized word streams; matching runs ≥ `dual_min_anchor_words` (6) are the confident anchors. On PV/EPC these cover 81% of words.
- **Cut points:** chunk boundaries only where BOTH transcripts start a segment at the same matched word (≥3 matched words each side), so every chunk pairs the same speech and seams sit on agreed segmentation.
- **Chunk classification:** `match` (near-identical) and `wording` (same turn structure, only ASR wording differs) pass through from the base side verbatim; only `diff` chunks (structural disagreement) go to the LLM. Base side = `dual_base_side` (default `b` = `_dgwhspm`, consistently the stronger ASR).
- **Conservation guard:** `llm_arbitrate_dual_chunk` rejects output < `dual_conservation_min` (0.9) similar to version A or B, plus timestamp-verbatim and count-bound checks; failures fall back to the base-side chunk, bounding damage per chunk.
- Timestamp links survive the merge; merged word counts land between the two inputs (no duplication, no mass drops).

New tools for prompt iteration (Randy's chunk-triples ask):
- `scripts/extract_dual_chunks.py` → `data/stellar-eval/dual-chunks/<stem>_dual-chunks.json`: JSON list of dicts pairing raw A, raw B, and the word-alignment-projected reference for each chunk.
- `scripts/explore_dual_prompts.py`: runs a dual prompt over diff chunks and scores each consensus against the reference chunk (word similarity, segment counts, boundary recall/precision) — the fast inner loop for prompt work without full-episode runs.


## Results (gpt-5-mini cheap tier, denovo-v3)

### 2025-03-06_PV-EPC (hard meeting; ref `_cemanual`)
| Variant | Errors | Strict | Word acc |
|---------|--------|--------|----------|
| raw_B_dgwhspm (best raw) | 170 | 122 | 0.740 |
| draftds_B (BA-review best) | 143 | 98 | 0.740 |
| **draftld_raws (new)** | 141 | 85 | 0.695 |
| **draftld_singles (new)** | **139** | **83** | 0.692 |

Dual is now the best variant on both error counts: 18.2% error / 32.0% strict reduction vs best raw, vs 15.9% / 19.7% for `draftds_B`. Word accuracy no longer collapses (0.33 → ~0.69) but still sits below raw B (0.740) — the LLM sometimes picks A-side wording inside structural chunks; see next steps.

### 2024-08-26_Reason Is Fun Ep6 (clean podcast; ref `_vrb`)
| Variant | Errors | Strict | Word acc |
|---------|--------|--------|----------|
| raw_B_dgwhspm | 59 | 28 | 0.939 |
| draftds_B | **49** | **25** | 0.939 |
| draftld_raws (new) | 65 | 32 | 0.792 |
| draftld_singles (new) | 63 | 28 | 0.908 |

When one ASR is already clearly better, dual arbitration still can't beat just cleaning that transcript. Prior full-arbitration base-b run scored 67/27/0.891 — run-to-run LLM variance in the large structural chunks is visible.

### Fixture (defect-injection, 30 segments)
`draftld_singles` 8 errors / 4 strict / word acc 1.000 vs best raw 14/11 — matches the best single arm with perfect conservation. Old dual: word acc 0.70–0.73.

### Chunk-level prompt scoring (PV/EPC, first 8 diff chunks)
0 fallbacks / 0 retries; mean output-vs-ref word similarity 0.923; boundary recall 0.24 — the model currently defaults to the "safer" side rather than the better-segmented one. This is the prompt-iteration target, now measurable per chunk against the reference.


## Recommendations (supersedes the `_draftld` "avoid" rows in the BA notes)
| Variant | Status |
|---------|--------|
| `_draftds` | Use — unchanged, still the deterministic workhorse |
| `_draftld` (new) | **Use for hard meeting transcripts (PV/EPC-style)** where both raws are weak and complementary — best segmentation results on PV/EPC. Not yet for clean podcast pairs where `_dgwhspm` dominates — use `draftds_B` there |
| `_draftls` | Still no practical gain over `_draftds` (confirmed again on both episodes) |


## Next steps
1. **Prompt iteration on the chunk triples** (`explore_dual_prompts.py`): raise boundary recall (0.24 → target ≥0.5) and add a prefer-base-wording rule so word accuracy holds at the base ASR's level; compare prompts per-chunk against the reference before paying for episode runs.
2. **Close the word-accuracy gap on PV/EPC** (0.69 vs 0.74): candidate rule — arbitration picks segmentation structure, but wording is re-anchored to the base side within matched regions.
3. **Auto base-side / per-chunk gating**: only run dual on episodes (or chunks) where the two raws genuinely disagree structurally; skip dual when one side dominates (Ep6 case).
4. **Scale validation**: full ladder over the real-five Deutsch sample plus 2–3 more EPC meetings; compare against `references/alignment-results-real5.md` corpus totals.
5. **Then** revisit `_draftls` per-transition repair (M4 next-step 1) with the same chunk-triple method applied single-transcript.


## Rerun commands
Chunk triples + prompt scoring:
```bash
.venv/bin/python3 apps/transcription/stellar-transcriber/scripts/extract_dual_chunks.py \
  --raw-a "data/pv/meetings_epc/f9_raw/2025-03-06_PV-EPC_nova2gen.md" \
  --raw-b "data/pv/meetings_epc/f9_raw/2025-03-06_PV-EPC_dgwhspm.md" \
  --ref "data/pv/meetings_epc/2025-03-06_PV-EPC_cemanual.md" --profile pv
.venv/bin/python3 apps/transcription/stellar-transcriber/scripts/explore_dual_prompts.py \
  --chunks "data/stellar-eval/dual-chunks/2025-03-06_PV-EPC_dual-chunks.json" --limit 10
```
Full ladder (LLM, ~$0.5–0.7 and 30–60 min per episode):
```bash
.venv/bin/python3 apps/transcription/stellar-transcriber/scripts/run_alignment_eval.py \
  --raw-a "data/pv/meetings_epc/f9_raw/2025-03-06_PV-EPC_nova2gen.md" \
  --raw-b "data/pv/meetings_epc/f9_raw/2025-03-06_PV-EPC_dgwhspm.md" \
  --ref "data/pv/meetings_epc/2025-03-06_PV-EPC_cemanual.md" --profile pv
```
Rescore existing drafts without LLM calls: add `--rescore`. Reports land in `data/stellar-eval/alignment-runs/`.
