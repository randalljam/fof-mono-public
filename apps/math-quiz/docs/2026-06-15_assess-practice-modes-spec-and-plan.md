file: apps/math-quiz/2026-06-15_assess-practice-modes-spec-and-plan.md
title: Math Quiz — Assess/Practice Modes, Per-User Store & Anchor-First Build (Spec + Plan)
last-updated: 2026-06-15_1352
ai: Claude Code (cloud) — Opus
session: `math quiz goal`

A combined **specification** (Part A), **overall implementation plan** (Part B), and **concrete next build slice** (Part C) for a new direction on the math quiz, captured from a 2026-06-15 design dictation. This file is **additive**: it does not replace `2026-06-14_adaptive-and-profiles-goal.md` (the adaptive-selector goal) or `learner_profiles/states/README.md` (the fluency-state file spec). It reframes the app around an explicit **dual purpose** — *assess* the learner's fluency, then *deliver practice* at that state — and proposes building **top-down from the fluent-demonstration "anchor" case**. Where it changes the role of prior artifacts, that is called out under "Impact on existing work."


## Branch keep-or-revert determination (decided 2026-06-15) — KEEP
The branch's `/goal` code work is kept, not reverted. Determination basis: a `git diff` of `feature/math-quiz-goal` vs its `main` merge-base shows **every change is an addition** — no live app file (`math_fluency.js`, `math_utils.js`, `index.html`, sounds, etc.) was modified or deleted. So the app behaves identically to its pre-branch state; "reverting" would only delete additive scaffolding, not restore altered behavior. And the new direction **builds on** that scaffolding:
- The **simulation harness** + real-fluency-code integration (vm via `tests/load_app.mjs`) is the proving ground Parts B/C depend on.
- The **adaptive selector** is the engine beneath the new mode machine; practice mode and the lower-rung profiles need its tiers / `hard_weight` / hole-targeting.
- The **predictive/thorough mastery** logic *is* the anchor prompt.
- The **3 profiles** are rungs 1/2/4 of the new profile ladder (grow to 5–10).

Reverting would force rebuilding all of the above. The only artifact whose role shifts is the fluency-state JSON/spec (demoted from primary store to derived snapshot under SQLite) — harmless to keep and still accurate. Decision: **keep the full branch; treat it as the foundation.**


## Decisions locked (2026-06-15)
Resolves the Phase-0 open questions with the design-dictation answers.
1. **Anchor assess order (Q1):** use a **fixed, predetermined hard-first sequence** as the starter. Seeded **variability within problem categories** is a later upgrade, pending a separate problem-grouping scheme being developed on another thread. Truncate the sequence the moment predictive mastery fires.
2. **Glitch handling (Q2):** the true fluent user answers **fast**; we cannot observe their mental state, so we infer from behavior. On a **slow or missed** item, **continue**, then **re-deliver that same fact later**; if it's answered **fast on re-delivery**, mark the earlier attempt **non-representative ("glitch")** and discard it from the fluency judgment. Additionally, apply a **warm-up discard**: drop roughly the **first ~2 problems** (interface settling / focus ramp-up) from the assessment. A single isolated slip never drops the fluent hypothesis; only a confirmed cluster does.
   - **Future TODO (not now):** optionally **record audio for the entire session** so a learner can annotate it ("I blanked there"), and **synchronize the audio to the on-screen problem timeline** (especially clean if problems are read aloud). This gives ground-truth for glitch vs. real deviation later. Defer.
3. **Practice batch & mix (Q3):** default **batch size = 10** problems between reassessments; default **known:unknown mix = 50/50**. Both tunable.
4. **SQLite compute & identity (Q4/Q5):** **compute in-memory** (sql.js) for speed. **Identity is lightweight** — a username/name string only; **no login, auth, or deployment** now; everything runs **locally**. **Persistence (confirmed 2026-06-15):** IndexedDB autosave keyed by username + manual `.sqlite` export/import; no server. Built in Part C.
5. **JSON-write switch (supersedes Q6 deprecation horizon):** add a **write-mode switch** controlling whether canonical session JSON is emitted: `sqlite-only` | `json+sqlite` | `json-only`. **Development default = `sqlite-only`** so dev runs don't spew test JSON files. JSON is not deprecated by a date; it's gated by this switch (kept available because the Minecraft mod and other games emit the same format).
6. **Addition segmentation + orientation (2026-06-15, from `single_digit_addition_segmentation.md`):** the 55 single-digit addition facts partition into five **non-overlapping** categories by smaller addend — `add-zero` (10), `add-one` (9), `add-two` (8), `doubles` (7, n≥3), `tough-21` (21). **Sneaky Six** = the tough facts with both addends ≥ 6 (a named subset, not a sixth bucket). A fact's two presentations are called its **orientation**: **ascending** (lower addend first, e.g. `3 + 4`) and **complement** (reversed, `4 + 3`); doubles are symmetric.
7. **Anchor sampling plan (addition):** Tough 21 each ≥ once (random orientation); **Sneaky Six in both orientations**; **all 7 doubles**; **≥ half of each easy set** (add-zero/one/two) → ~48 problems. Items are **interleaved with hard facts emphasized early** (operands jump around — no `8+1, 8+2, 8+3` marching) and fewer easy. Glitch rule (re-deliver any > `fastMs` response to check for a slip) applies.
8. **Anchor UI knobs:** operation **checkboxes** (Addition / Subtraction / Multiplication), **default Addition only**; **auto-submit** on by default (accept once entry has ≥ the correct answer's digit count — no Enter); show **total elapsed time** at the end; **each run saved as its own `.sqlite` file** (see "How to test").
9. **On-screen keypad:** a calculator-style keypad — **standard `7 8 9 / 4 5 6 / 1 2 3 / 0` block (default)** plus `⌫`/`↵`. Two-digit answers are entered with **two presses** (less cognitive load). An optional **"Big number keys (10–21)"** checkbox (default **off**) stacks the extra rows `10 11 12 / 13 14 15 / 16 17 18 / 19 20 21` above; those value keys are whole answers (single press submits). Physical typing still works.
10. **Summary wording:** report `N% coverage (sampled of total facts)`, **total time on its own line**, and explain re-asks as **momentary slips** (a slow/mistyped first try, re-asked and cleared — not counted against fluency) rather than a bare "X correct". Each run is saved as a `.sqlite` file; **downloads target the gitignored `math-quiz_data/` folder** (via the Save dialog — the browser can't force a repo path).
11. **Answer feedback:** on auto-submit, briefly show the **full entered number** + a green `✓` (red `✗` if wrong), then advance. The flash is short (default 100 ms, `?fb=` tunable) and the **response time is captured before it**, so it never affects fluency timing — only a small wall-clock confirmation.
12. **Continue-to-100% is glitch-tolerant (fixed 2026-06-15, TL regression):** the thorough/certification pass must **re-ask** any fact not yet answered fast-and-correct (incl. ones answered slow in the assess phase) and give each a clean retry (up to 2) before flagging it — a momentary slip (e.g. switching keyboard↔mouse, a 2017 ms answer) must not fail "100%". `engine/assess_flow.mjs` → `createThoroughRun`. The old hard pass/fail (`checkThoroughMastery`: every attempt ≤ 2000 ms, no resample) was too brittle. The "almost there" report now names the still-slow facts in human form and explains they're correct-but-not-automatic.
14. **Realism guardrail — slow/wrong on easy facts (2026-06-15):** a real learner struggles on *hard* facts, not easy ones, so several **easy** facts coming back slow or wrong signals a glitch / distraction / not-serious input, not a fluency result. When `≥ anomalyEasyThreshold` (default 3) easy facts have no fast+correct attempt, the page surfaces *"Something looks off … we suggest ending this session and starting fresh"* (End session / Continue anyway). Ending saves the run with an `anomaly:slow-on-easy` marker in the session note so evaluators see it. Detector `findSlowEasyFacts` is shared by the live run (`createAssessRun.anomaly()`) and static re-evaluation (`reevaluateState().anomaly`). A cheap guardrail, not a designed-for case — testing will hit it sometimes, which is fine.
15. **Dev quit buttons (2026-06-15):** the anchor page has **Quit & save** (finalize + upload the partial run — handy to test the S3 path fast) and **Quit & abandon** (end with no save; dump dev info), each behind an "are you sure?" confirm. Dev-mode UI, to be hidden/logged for real users later.
18. **Warm-up: practice entering numbers (2026-06-15):** a **"Warm-up: practice entering numbers first"** checkbox (default **on**) runs a keypad familiarization before the quiz. It shows 6 numbers to type — round 1 fixed (`3, 8, 6, 12, 19, 15`: three single-digit, three two-digit), later rounds random in the same pattern. A wrong entry just clears for a retry. A **"Skip to start quiz"** button is always available; after each 6 it offers **"Ready to start quiz"** or **"Continue to practice entering"**. The warm-up reuses the quiz keypad/input (phase = `practice`); total-time measures the quiz only, but the entries ARE persisted to a separate `WarmupAttempts` table (kept distinct from `ProblemAttempts`) — useful signal on number-entry skill. (`?practice=0` disables, used by quiz-focused e2e.)
17. **Re-ask spacing (2026-06-15):** the assess-phase glitch re-check re-asks **every** slow/missed fact (including easy ones — a >2 s answer is genuinely worth a second look), but with more breathing room: `redeliverSpacing` is **5** (was 3), so a re-ask comes ~5 problems later rather than right behind the first. (An earlier "never re-ask easy" idea was reverted — the observed `0+0`/`0+9` answers were actually >2 s, so re-asking is correct; just space it out.)
16. **Assessment order mode HF/EF + auto-revert (2026-06-15):** a **"Hard facts first"** checkbox (default **on** = HF; off = EF, easy categories lead via `buildAnchorAdditionPlan({order})`). A separate **"Auto-revert to easy if struggling"** switch (default on): while HF, after `REVERT_THRESHOLD` (3) struggle responses (wrong/skip, or slower than `REVERT_SLOW_MS` 4 s) it flips the remaining facts to easy-first (`run.reorderRemaining`). A bottom indicator shows **HF** / **EF**, and on a flip shows **HF→EF** for the one transition problem, then **EF**. Skip counts as a struggle. (A fluent learner never struggles, so HF stays HF — testing unaffected.)
13. **S3 upload via a local dev server (2026-06-15):** a browser page can't read `.env` or hold AWS creds, so uploads go through `tools/dev_server.py` (serves the app + `/api/save-run`). On a finished run the page (only when served from **localhost**) POSTs the per-run `.sqlite`; the dev server writes `math-quiz_data/<file>` **and** uploads to `s3://[S3-BUCKET]/math-quiz/test/anchor/<file>` using `.env` creds (boto3, like `core/aws.py`). Bucket/prefix are env-configurable (`ANCHOR_S3_BUCKET`/`ANCHOR_S3_PREFIX`) so files can be re-organized. Not served from localhost → the page shows an error and uploads nothing (deployment/auth deferred). **[S3-BUCKET] is the PII bucket** — these are test captures; keep that in mind as the path/organization evolves.


## Re-processing captured runs (Part C addition, 2026-06-15)
A captured per-run `.sqlite` holds **only raw data** — `Users`, `Sessions`, `ProblemAttempts` (every trial: operands, answer, correct?, `response_time_ms`, flags), and `ModeEvents`. The fluency **evaluation** (per-fact status, mastery verdict) is **not persisted**; it's recomputed. So "clear the evaluation, keep raw, re-run" is essentially already true — `engine/db_io.mjs` `stripEvaluation` is a future-proof guard (drops any later snapshot table), `loadRawAttempts` reads trials grouped by canonical fact key, and `loadOrderedProblems` returns the full list **in the exact administered order** (by `attempt_id`).

**Re-processing is STATIC re-evaluation only** (decided 2026-06-15): `engine/reevaluate.mjs` `reevaluateState` re-runs the fluency evaluation + mastery checks over the recorded attempts exactly as-is — deterministic, no responder, no re-simulation. This is exactly what's needed to change the evaluation algorithm/criteria and re-run old captures as fixed inputs (e.g. bump a recorded time and see the new verdict). Live re-simulation (inferring a learner model from the DB and re-answering) is intentionally **out of scope** — too complex for now and not needed for the evaluation-tweaking workflow.


# Part A — Specification

## 1. Core reframe: the app is a dual-purpose tool
The math quiz does two things, in this order:
1. **Assess** — determine the learner's per-fact fluency state.
2. **Practice** — deliver efficient, appropriately-targeted practice at that state.

When nothing is known about a learner, targeted practice is impossible — but the assessment signal is acquired **quickly**, so the app moves from "knows nothing" to "knows enough to target" within a couple of minutes of play. The two purposes are not separate apps; they are two **modes** of one tool, and the app should always know which mode it is in.


## 2. Explicit mode: `assess` vs `practice`
Make the operating mode a **first-class, explicit flag** the app tracks and records, rather than an implicit consequence of the selector's tier weights.
- **`assess`** — the app is forming or revising its fluency estimate. Problem choice is optimized to *learn about the learner* fast (broad, hard-fact-weighted coverage; predetermined or lightly-dynamic order — see §5).
- **`practice`** — the app has a usable estimate and is *delivering value*: a controlled mix of fluent and not-yet-fluent facts (see §6), with reassessment batched rather than per-problem.
- **Cold start** is `assess` with no prior; the app may still emit useful practice as a side effect, but its goal is estimation.

**Why explicit:** the two modes want *different problem-selection cadence*. Assessing a (claimed) fluent adult wants near-immediate responsiveness to deviation; practising a 7-year-old does **not** need a fresh dynamic recompute after every single problem — queueing 5–10 problems between reassessments is fine and cheaper. A stored mode flag also makes sessions reviewable ("this was an assessment run") and lets the Minecraft mod and other front-ends declare intent.

Mode is **logged with transitions** (timestamp, from→to, trigger) so a learner's history shows when the app was assessing vs practising.


## 3. Anchor use case: fast fluency demonstration
The primary, build-first scenario. Hand the app to a parent (or any adult/student/5-year-old/speed-math competitor) and say "you try it." The app assumes nothing about them. They start answering. As the app accumulates evidence it reaches a **sampling conclusion** and surfaces it:
> "It looks like you're totally fluent in all single-digit arithmetic — you've demonstrated this reliably on **52%** of the actual problems. Continue to **100% coverage**, or **stop here** based on this sample?"

The learner chooses. If they truly know single-digit arithmetic cold, the whole interaction takes **a couple of minutes**. This is the anchor because it stresses everything important: fast assessment, hard-fact-weighted sampling, glitch tolerance, the predictive-vs-thorough distinction, and a clear human decision point.

This prompt is the **UI surfacing of predictive mastery** (already specified as SC4 in the adaptive goal): predictive mastery firing = "stop here is justified"; "continue to 100%" = proceed to **thorough mastery** (SC5). The coverage % shown is the predictive sample's coverage at the moment it fired.


## 4. Working backwards from the anchor (the profile ladder)
The anchor sits at the top of a ladder of learners the app must serve. Building the anchor *with the lower rungs in mind* keeps the architecture general:
1. **Totally fluent** (anchor) — demonstrate full single-digit fluency in minutes.
2. **Nearly fluent, a few sticky facts** — fluent except a handful of slow/rusty hard facts (e.g. `6×9`). The tool's job is to **surface and target** those few for focused practice.
3. **Mid-learning** — knows some single-digit facts, not others; state **varies by day** (real day-to-day variability). Assess, then deliver efficient targeted practice.
4. **Early beginner** — a 5-year-old learning single-digit addition in the `0–5` range, still acquiring the basics.

We expect to grow from 3 profiles to **5–10**, added top-down as the architecture proves out.


## 5. Selection strategy in `assess` mode (incl. glitch tolerance)
For the fluent-assumption (anchor) path:
- **Fixed, predetermined order (starter).** Precompute an ordered, hard-first sampling sequence that reaches hard-fact coverage fast (hard facts confirmed nearly completely; easy facts inferred), and deliver it without per-problem recompute while the learner looks fluent. **Truncate** the moment predictive mastery fires. Seeded **variability within problem categories** is a later upgrade (depends on a separate problem-grouping scheme in development); not in the first build.
- **Adjust on signal, not on noise.** As soon as responses show **real deviation** (a confirmed cluster), switch to dynamic, targeted selection and flip toward `practice` on the affected facts.
- **Glitch handling (the re-deliver-and-confirm rule).** We can't observe the learner's mental state, so we infer from behavior. The true fluent user answers **fast**. When an item comes back **slow or wrong**, do **not** immediately conclude non-fluency: **continue**, then **re-deliver that same fact later**. If the re-delivery is **fast/correct**, treat the earlier attempt as **non-representative ("glitch")** and discard it from the fluency judgment; if the re-delivery is *also* slow/wrong, it counts as real signal. A single isolated slip never drops the fluent hypothesis — only a confirmed cluster does. This is consistent with windowed fluency evaluation (one miss inside a `windowSize` window doesn't by itself drop a fact below `minAccuracy`).
- **Warm-up discard.** Treat the **first ~2 problems** as non-representative (interface settling, focus ramp-up) and exclude them from the assessment timing/accuracy.
- **Future TODO — audio annotation (deferred).** Optionally record audio for the whole session so a learner can annotate it, **synchronized to the on-screen problem timeline** (clean if problems are read aloud). Gives ground-truth for glitch vs. real deviation. Not in scope now.

For unknown-state cold start, a short adaptive **pretest** brackets the competence boundary to seed initial priorities (already noted in the adaptive goal).


## 6. Selection strategy in `practice` mode
- **Batched delivery.** Queue a batch (**default 10**), deliver it, then reassess and choose the next batch. No need to dynamically reassess after every single problem for a learner who is clearly mid-acquisition. Cheaper and pedagogically fine.
- **Mix of known and not-known.** Practice interleaves facts the learner *is* fluent in with facts they are *not* — a controllable ratio (**default known:unknown = 50/50**). This is already supported by the selector's priority tiers + `hard_weight`; practice mode chooses the mix knob rather than always serving the single highest-priority fact. Both batch size and ratio are tunable.
- **Targeting the sticky few.** For the "nearly fluent" rung, practice concentrates presentations on the surfaced weak/slow facts (the existing hole-targeting behavior, SC7).


## 7. Per-user storage: one SQLite file per user
Persist everything about a learner in a **single SQLite file per user**. A person will not do enough problems for this to become unwieldy, so storing every attempt and every session together keeps all history queryable in one place.
- **Canonical store = the per-user SQLite DB.** Suggested tables (to be finalized in Part B):
  - `sessions` — one row per session (id, source app, start/end, settings, mode at session, summary).
  - `attempts` — one row per problem attempt (session_id, fact key `op|num1|num2`, presented text, correct answer, user answer, is_correct, response_time_ms, flags, mode, timestamp).
  - `mode_events` — assess/practice transitions (timestamp, from, to, trigger).
  - (optional) `fluency_snapshots` — computed per-fact state at points in time, for fast review and diffing.
- **Write-mode switch (JSON on/off).** A single config flag controls output: `sqlite-only` | `json+sqlite` | `json-only`. **Dev default = `sqlite-only`** (don't generate piles of test JSON during development). JSON is retained — not deprecated by date — because **other front-ends emit the same format**: the **Minecraft mod** (`apps/minecraft/mods/MathQuest`) and future math-quiz games. Multiple games → one shared JSON format → ingested into the same per-user DB. Flip to `json+sqlite` when interoperability/backup matters.
- **Ingestion is format-stable.** The DB ingests the existing canonical session-JSON shape (the one `importSessionData()` already consumes), so any producer of that format feeds the same store.

### 7a. Persistence mechanism (recommendation — pending confirmation)
**The problem:** today the app computes fluency in an **in-memory** sql.js DB that vanishes on page reload. "One SQLite file per user" means that DB must survive between visits and reload at start. The question is *where the per-user DB lives and how it moves in and out of the browser.* Options:
- **(a) Manual file download/upload** — "Save" downloads `username.sqlite`; on return the user uploads it. Zero infra, fully local, mirrors today's JSON export — but manual and easy to lose.
- **(b) Browser-local auto-persistence (IndexedDB)** — after each session, `db.export()` → bytes stored in IndexedDB keyed by username; on start, load bytes → `new SQL.Database(bytes)`. Seamless, no server, survives reloads — but tied to that browser/device and clearable by the browser. (OPFS + the official `sqlite-wasm` build is a more modern variant but a bigger swap from sql.js.)
- **(c) Server-side** — durable and cross-device, but needs deployment + auth, which we're explicitly **deferring**.

**Recommendation (confirmed 2026-06-15):** **compute in-memory** (sql.js, as now) for speed; **auto-persist to IndexedDB keyed by the lightweight username** (seamless, no server, no auth); **plus a manual `.sqlite` export/import** as the backup + cross-device escape hatch (which also pairs naturally with the write-mode switch). This needs **no deployment and no authentication** and runs fully locally now. Revisit server sync (c) only when auth/deployment is on the table; OPFS/`sqlite-wasm` only if we outgrow sql.js+IndexedDB. Built in Part C (`engine/persistence.mjs`).


## 8. Relationship to mastery determinations
The two mastery outputs already specified carry over unchanged and become the backbone of the anchor UX:
- **Predictive mastery (fast/short)** — the sampling conclusion behind "stop here" (≥ `predictive_min_coverage` overall **and** ≥ `predictive_hard_min_coverage` hard-fact coverage, all sampled facts `green`).
- **Thorough mastery (complete/certified)** — the "continue to 100% coverage" path (every in-scope fact attempted, correct, within `mastery_ms`).


## 9. Impact on existing work (what changes, what stays)
- **Adaptive selector** (`simulation/adaptive_selector.mjs`) — **stays.** It becomes the engine *underneath* the mode machine. New: a mode-aware wrapper that (a) in `assess`/anchor can run a **predetermined** sequence instead of per-problem recompute, and (b) in `practice` serves **batches** of 5–10 with a known/unknown **mix ratio**.
- **Simulation harness + response model** (`simulation/simulation.mjs`, `simulation/profiles.mjs`) — **stays and grows.** Add a **glitch/variability** component to the response model (occasional isolated slips) and grow profiles to 5–10.
- **Mastery determinations** (SC4/SC5) — **stay**; now surfaced as the anchor prompt.
- **Fluency-state JSON files** (`learner_profiles/states/*.json` + `states/README.md`) — **role demoted, spec retained.** Under per-user SQLite, the DB is the canonical store; the JSON state file becomes a **derived snapshot / export and interchange format**, not the primary persistence. The spec is still accurate as a *snapshot* shape and should gain a one-line note to that effect (deferred — not edited in this pass per instruction).
- **Adaptive goal doc** (`2026-06-14_adaptive-and-profiles-goal.md`) — **stays** as the record of the selector/simulation milestone; this document supersedes its "Vision/use cases" framing with the explicit-mode, anchor-first framing above.
- **Net-new:** explicit mode flag + `mode_events`, the **write-mode switch** (JSON on/off), the fixed glitch-tolerant assess sequence (re-deliver-and-confirm + warm-up discard), batched practice delivery, per-user SQLite store + ingestion + IndexedDB persistence, the anchor decision prompt, 5–10 profiles.


# Part B — Implementation Plan

## Approach: top-down from the anchor
Build the fluent-demonstration anchor **first**, but architect it so the lower rungs (sticky-few, mid-learning, early-beginner) drop in without rework. Prove each phase with the **deterministic simulation** (real fluency code, seeded RNG) before any live-UI wiring. Every phase ends with passing tests (`cd apps/math-quiz/tests && npm run test:all`).


## Phase 0 — Confirm decisions ✅ (done 2026-06-15)
Resolved — see "Decisions locked (2026-06-15)" near the top. One item remains pending: the SQLite **persistence mechanism** (recommendation in §7a awaiting confirmation). No code.


## Phase 1 — Anchor case: fast fluency demonstration (assess mode)
Goal: from a standing start, reliably conclude "totally fluent" in ~2 minutes of simulated play, glitch-tolerant, and present the continue/stop decision.
- **Mode-aware selection wrapper** over the existing selector, with an `assess` strategy that emits a **predetermined, hard-first sampling sequence** (optionally seed-varied).
- **Glitch-tolerant predictive conclusion**: predictive mastery fires despite isolated slips; a *cluster* of deviations instead drops the fluent hypothesis and switches to dynamic targeting.
- **Decision point**: when predictive mastery fires, produce the "continue to 100% / stop here" outcome with the coverage % (data-level result; UI later).
- **Tests:** proficient-adult reaches predictive mastery within a bounded number of problems; a **glitch variant** (inject k isolated slips) still reaches it; a **genuinely-not-fluent** learner does **not** falsely trip it and instead surfaces the weak facts.


## Phase 2 — Per-user SQLite store + ingestion
- Define the schema (§7) and a DOM-free **ingest** path: canonical session JSON → DB rows; **derive** fluency state from the DB using the **real** fluency code (no parallel model).
- Keep writing session JSON as backup/interchange; add an **importer** that accepts the shared format from any producer (math quiz, Minecraft mod).
- **Tests:** ingest N sessions → query attempts/sessions; fluency state derived from the DB equals the state computed directly from the same sessions (parity test); a Minecraft-format session ingests identically.


## Phase 3 — Explicit mode machine + batched practice
- Implement `assess`/`practice` as an explicit, **logged** state (`mode_events`), with the assess→practice transition triggered by a confirmed deviation cluster, and practice→assess by staleness/`needsRecheck`.
- **Practice strategy:** deliver in **batches (default 10)** with a configurable known/unknown **mix ratio (default 50/50)**; reassess between batches, not per problem.
- **Tests:** mode transitions fire on the right signals (and *not* on isolated glitches); batch cadence holds (reassessment happens between batches); practice mix ratio is respected; sticky-few profile gets its weak facts concentrated.


## Phase 4 — Grow profiles to 5–10 (top-down)
Add profiles down the ladder (§4), each with declared `final_state`/expected-outcome assertions and a glitch component where realistic:
- nearly-fluent-sticky-hard-facts, mid-learner-with-day-variability, early-beginner-addition-0–5, plus 1–3 more (e.g. subtraction-focused, multiplication-tables-in-progress, speed-competitor fast-RT).
- **Tests:** each profile's run reaches its declared end state / mastery outcome within tolerance.


## Phase 5 — Live-UI integration (anchor slice done 2026-06-15; rest follow-up)
The **anchor case is wired into a live page** (`anchor.html`/`anchor.js`) with the decision prompt, IndexedDB persistence, and the write-mode switch — runnable and e2e-tested (`tests/e2e/anchor.spec.mjs`). See "How to test the anchor case." Still to do: render a per-fact **fluency grid** on the page (extract `prepareFluencyDatasets` from the fluency page's bootstrap), and integrate the mode machine + batched practice into the main quiz UI once Phase 3 lands.


## Testing posture (all phases)
Reuse the established pattern: DOM-free engine code in `simulation/`, new tests in `tests/`, real browser functions via `tests/load_app.mjs` in a vm, deterministic seeds derived from `profile_id` (+ run name). Do not weaken existing criteria or tests to pass. Each phase is "done" only when `npm run test:all` exits 0 with its new tests included.


## Open questions (remaining)
None — all Phase-0 questions are resolved in "Decisions locked"; the SQLite persistence mechanism was confirmed 2026-06-15 (§7a) and built in Part C.


# Part C — Concrete next build slice

**Status: built 2026-06-15 — including a runnable live anchor page.** DOM-free engine modules in `apps/math-quiz/engine/` reuse the app's real DB functions by **dependency injection** (they're browser globals, not ES modules) and the selector/mastery code from `simulation/adaptive_selector.mjs`. A thin browser controller (`anchor.html` + `anchor.js`) wires them into a real, testable UI. Tests in `apps/math-quiz/tests/` (run: `cd apps/math-quiz/tests && npm run test:all` → 86 unit + 19 e2e). Files:
- C1 `engine/write_mode.mjs` + `tests/write_mode.test.mjs` — write-mode switch (default `sqlite-only`).
- C2 `engine/user_store.mjs`, `engine/persistence.mjs` + `tests/user_store.test.mjs` — per-user store (Users/Sessions/ProblemAttempts + new `ModeEvents`), ingest, DB-derived fluency, IndexedDB + memory persistence, manual `.sqlite` export/import.
- C3 `engine/assess_flow.mjs` + `tests/assess_flow.test.mjs` — fixed hard-first sequence, warm-up discard, glitch re-deliver-and-confirm, predictive-mastery conclusion.
- C4 mode-flag plumbing — `ModeEvents` table + `logModeEvent`/`currentMode` on the store.
- **Live anchor page** `anchor.html` + `anchor.js` + `tests/e2e/anchor.spec.mjs` — the runnable fast-fluency demonstration (see "How to test the anchor case" below).


## How to test the anchor case (as built)
The anchor demonstration is runnable now. Serve the app statically and open the page:
```
cd apps/math-quiz && python3 -m http.server 8907
# then open http://127.0.0.1:8907/anchor.html
```
Enter a name, leave **Addition** checked (Subtraction/Multiplication default off), click **Start**, and answer with the **on-screen calculator keypad** (Decision 9 — standard `0–9` block by default) or the physical keyboard — **auto-submit accepts each answer once its digit count is reached, so you don't press Enter** (uncheck Auto-submit to use ↵). Two-digit answers take **two presses**; tick **"Big number keys (10–21)"** to get single-press value keys instead. The run administers the **curated addition plan** (Decisions 6–7): hard facts (Tough 21 / Sneaky Six) come first and operands jump around; the Sneaky Six appear both ways; doubles all appear; ~half the easy facts appear. ~48 problems, a couple of minutes. When done it shows *"It looks like you're fluent … demonstrated on N% of the facts. Continue to 100% coverage, or stop here?"* — **Stop** ends with a "Fluent ✅" summary; **Continue** walks the remaining facts and certifies thorough mastery. As-built specifics:
- **Conclusion** comes from `createAssessRun` run over the curated plan (`truncateOnMastery:false` — it administers the whole plan, then judges) with warm-up discard of the first 2 and the glitch re-deliver-and-confirm rule. Hard-fraction gate is off (the plan guarantees hard coverage by construction); conclusion rests on accuracy/speed. `?cov=` tunes the coverage gate (default 0.7).
- **Total time** is shown in the summary.
- **Per-run file:** every run is saved as its **own SQLite database file**, `anchor_<name>_<timestamp>.sqlite`, in browser **IndexedDB** (database `mathQuizAnchorRuns`, key = filename), and also appended to the cumulative per-user store (`mathQuizUserStores`, key = name). The summary names the file and says what's stored: the single session — every problem with the answer, correct?, `response_time_ms`, flags — plus settings, summary, mode, and mode events. The **Download .sqlite** button opens a Save dialog (Chrome) so the file can be placed in **`apps/math-quiz/math-quiz_data/`** (gitignored); other browsers fall back to the Downloads folder. The browser can't force a repo path. Write-mode is `sqlite-only` by default (`?write=json+sqlite` also downloads the session JSON).
- **Summary wording (per Decision 10):** coverage % with sampled/total, total time on its own line, and re-asks framed as momentary slips — not a bare correct count.
- **sql.js** loads from the same CDN the other pages use (the e2e harness routes it to a local copy). **`math_fluency.js` is intentionally NOT loaded** (it auto-bootstraps the fluency page), so the live page does not yet render a per-fact fluency grid — the conclusion + weak-fact list stand in. Wiring the grid is a follow-up.
- **Subtraction/Multiplication:** if checked, they use a shuffled hard-first fallback (no segmentation yet — that's a later phase, addition first).
- **Not-fluent path:** if the plan is administered without mastery, the page surfaces the confirmed weak facts to practice (full practice mode is Phase 3).

Original Part C plan retained below for reference.

C1. **Write-mode switch.** A config flag `writeMode: 'sqlite-only' | 'json+sqlite' | 'json-only'`, default **`sqlite-only`** in dev. The session-writer honors it (emit JSON only when the mode includes JSON). Implemented as the single gate all session output passes through, so flipping it changes behavior everywhere.

C2. **Per-user SQLite store (in-memory) + ingestion.** Schema from §7 (`sessions`, `attempts`, `mode_events`, optional `fluency_snapshots`). A DOM-free `ingest(sessionJson)` writes rows; fluency state is **derived from the DB via the real fluency code** (no parallel model). Persistence per §7a: `db.export()` → IndexedDB keyed by username on session end; load on start; manual `.sqlite` export/import. Keyed by a **lightweight username** (no auth).

C3. **Anchor assess flow.** Mode-aware wrapper over the existing selector emitting the **fixed hard-first sequence**; apply **warm-up discard** (first ~2) and the **re-deliver-and-confirm glitch rule**; fire **predictive mastery** → produce the "continue to 100% / stop here" outcome with coverage % (data-level; UI later). Truncate on predictive mastery.

C4. **Mode flag plumbing.** `assess`/`practice` recorded on sessions/attempts and in `mode_events`; the anchor flow runs in `assess`. Full transition logic + batched practice are Phase 3, but the flag and logging land here so data is correct from the start.

**Tests (Part C done = these pass under `npm run test:all`):**
- C1: writer emits no JSON in `sqlite-only`; emits JSON in `json+sqlite`/`json-only`.
- C2: ingest N sessions → query attempts/sessions; **parity** — fluency derived from the DB equals fluency computed directly from the same sessions; a Minecraft-format session ingests identically; export→import round-trips the DB.
- C3: proficient-adult reaches predictive mastery within a bounded count; a **glitch variant** (inject isolated slips that resolve fast on re-delivery) still reaches it and the slips are discarded; warm-up problems are excluded; a **genuinely-not-fluent** learner does **not** falsely trip mastery and surfaces its weak facts.
- C4: sessions/attempts carry the correct mode; `mode_events` records the assess run.

**Explicitly deferred from C:** full assess↔practice transition machine + batched practice tuning (Phase 3), profiles 4–10 (Phase 4), live-UI wiring and the on-screen anchor prompt (Phase 5), audio annotation, and seeded category variability in the assess sequence.
