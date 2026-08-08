file: apps/math-quiz/2026-06-15_guinea-pig-findings.md
title: Math Quiz Anchor — First Real-Learner Sessions (G1, G2): Findings & Recommendations
last-updated: 2026-06-15_1425
ai: Claude Code (cloud) — Opus
session: `math quiz goal`

Analysis of the first two **real-learner** anchor runs (2026-06-15), captured as per-run
SQLite files and anonymized as **G1** and **G2** ("guinea pigs" — two patient kids).
Both did long, complete sessions. This doc summarizes what each run shows and proposes
changes; **nothing here is implemented yet**.

Source files (not committed — local/`math-quiz_data/` + `s3://[S3-BUCKET]/math-quiz/test/anchor/`):
`anchor_G1_2026-06-15_135413.sqlite`, `anchor_G2_2026-06-15_140533.sqlite`.


## Headline learning
**Both kids are highly accurate but not sub-2-second fast.** They clearly *know* the facts
(G1 96% correct on addition, G2 99% on multiplication) but answer in ~2.5–4 s, so the tool's
adult-calibrated **2 s "fast" threshold rates almost everything as "not fluent."** The current
design conflates *accuracy* (do they know it) with *speed/automaticity* (is it instant) — and
for developing learners those are different things. This is the most important takeaway.


## G1 — Addition (90 problems, ~6m45s)
- **Accuracy:** 86/90 correct (**96%**), 4 wrong, 0 skips. Knows single-digit addition.
- **Speed:** median 3.5 s, mean 4.4 s. Fast-and-correct (≤2 s) only **8%** of answers — but
  **38%** ≤3 s and **57%** ≤4 s. So "slow" here means 2–4 s, not "doesn't know it."
- **Coverage / flow:** 42 of 55 facts seen. The order shows a **hard-first start that
  auto-reverted to easy-first** (first three problems were hard 6+8/9+7/6+7, all slow → 3
  "struggles" → flipped to EF; easy facts mid-run, hard facts last). The revert worked as designed.
- **Re-asks inflate the session:** ~42 unique facts but 90 presentations — nearly every
  correct-but-slow fact got re-asked once (because slow ≠ "clean"), roughly doubling the run.
- **Wrong answers:** `7+6→12`, `8+6→13`, `8+3→12` (off-by-one-ish on hard facts), and
  `3+5→1` (anomalous — likely a mis-key/misread). All hard or odd; the easy facts were solid.
- **Long pauses:** several 8–15 s answers (max 14.9 s on `3+4`) — breaks/distraction/thinking.
- **Warm-up:** 6/6 entered correctly (~2.3 s median) — keypad entry was not a problem.
- **Verdict the tool would give:** *not fluent* (only 8% sub-2 s), with a "facts to practice"
  list spanning ~all facts. Accurate but not automatic → a **consolidation/speed** learner.


## G2 — Multiplication (93 problems, ~6m10s)
- **Note:** G2 ran **multiplication**, not addition (operation selection worked).
- **Accuracy:** 92/93 correct (**99%**), 1 wrong (`1×8→5`, a clear slip), 0 skips. Strong.
- **Speed:** median 2.7 s, mean 3.8 s. Fast-and-correct ≤2 s **22%**, ≤3 s **52%**, ≤4 s **71%**.
- **Coverage / flow:** **all 55** multiplication facts seen, **hard-first throughout** (no
  revert this run). Covered the whole matrix because **multiplication has no curated
  segmentation plan** — it falls back to the *full 55-fact* shuffled list, so it's a longer
  marathon than the ~48-problem curated addition set.
- **Slowest facts (known but not automatic):** `5×7` (8.2 s), `6×7` (8.5 s), `7×8` (7.2 s),
  `7×9` (5.8 s), `6×8` (4.9 s) — exactly the classic "hard" products.
- **Long pauses:** up to **31 s** (`5×8`) and 15 s (`6×8`) — almost certainly a break.
- **Warm-up:** 6/6 correct.
- **Verdict the tool would give:** *not fluent* on speed despite near-perfect accuracy and full
  coverage → a **strong learner needing automaticity** on the hard products.


## Cross-cutting learnings
1. **The 2 s fluency bar is adult-calibrated.** Kids who *know* the facts (96–99% correct)
   land in 2.5–4 s and are flagged "not fluent" almost everywhere. At a 4 s bar, G1/G2 look
   57%/71% "fast." The threshold needs to be level-appropriate, not fixed.
2. **Accuracy and speed are different signals** and the tool currently merges them into one
   "fluent?" verdict. Both kids: accuracy mastered, speed developing.
3. **Re-asking every correct-but-slow fact ~doubles the session** (G1: 42 facts → 90 problems).
   For accurate-but-slow learners that's a long, repetitive run (they were patient; most won't be).
4. **Non-addition operations have no curated plan** — multiplication ran the full 55-fact
   fallback (G2's 93 problems). Subtraction would be the same. The segmentation/curation only
   exists for addition.
5. **Auto-revert keys off "slow OR wrong."** For an accurate-but-slow learner (G1), being slow
   tripped the revert even though correctness was fine — arguably the wrong trigger.
6. **Long pauses (8–31 s)** are real and unhandled — they inflate the averages and likely
   represent breaks, not thinking time.
7. **Data capture is excellent** — full per-attempt timing/correctness, warm-up entries in their
   own table, mode events. The files are rich enough for exactly this kind of analysis.


## Recommendations (proposed — not implemented)
Roughly prioritized; each is a proposal to discuss.
1. **Level-appropriate speed thresholds.** Make the "fast"/green threshold (now `greenMs = 2000`)
   configurable per learner/level (e.g. a "developing" preset around 3.5–4 s). Re-scoring G1/G2
   at 4 s would change the verdict from "not fluent" to "fluent-ish, polish a few."

2. **Report accuracy and speed as two axes.** Instead of a single fluent/not verdict, say
   "You *know* your facts — N% correct! Now let's make M of them faster." This matches what both
   kids actually are.

3. **Stop re-asking correct-but-slow facts during assessment** (or cap re-asks per fact). A
   correct answer establishes "knows it"; speed is a *practice* goal, not a reason to re-ask
   mid-assessment. This would roughly halve session length.

4. **Add curated plans for subtraction and multiplication** (segment like addition), so −/× runs
   aren't full 55-fact marathons. (Already on the roadmap; G2 shows the cost of not having it.)

5. **Base auto-revert on accuracy, not slowness.** Trigger the HF→EF flip on wrong/skipped facts
   (real struggle) rather than slow-but-correct, or raise the slow bar substantially.

6. **Make the "facts to practice" output actionable.** When most facts are slow, don't list all
   of them — surface the slowest / hardest (e.g. Sneaky Six, hard products) and cap the count.

7. **Handle long pauses.** Detect extreme per-problem times (e.g. >8–10 s) as breaks: exclude
   them from speed stats, and/or offer a "still there?" pause so they don't skew the data.

8. **Shorten the kid path.** 90+ problems / ~6 min is a lot. Consider a shorter assessment set,
   a target time, and routing developing learners into the (planned) batched **practice** mode
   for speed-building rather than a long one-shot assessment.

9. **Turn G1 and G2 into simulation profiles.** They're real mid-rung learners — "accurate-but-slow
   addition" and "accurate-but-slow multiplication (full coverage)" — ideal additions to the 5–10
   profile ladder, and good regression cases for the threshold/verdict changes above.

10. **Surface the chosen operation prominently** in the UI/summary (G2 ran multiplication); make it
    obvious which operation a run covered.
