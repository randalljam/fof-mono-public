## Randy Notes 2026-06-23

### targeted fluency practice
[x] add 3rd session sqlite to chatgpt to identify slow target problems
[x] choose 1-3 target facts for today's first trial (3+6, ) — evolved to up to 5 typed targets + per-learner defaults (Kid1/K2)
[x] define quick success metric for target facts: speed, accuracy, and confidence — cumulative fast-correct rings (default 3 under 2000 ms); streak stands in for confidence
[x] add targeted practice mode to math quiz / anchor flow
[x] make targeted mode use selected slow facts plus nearby review facts — coach targets + stored filler deck (shuffled); `nearbyReviewFacts` fallback when no filler list
[x] add short breaks between bursts — superseded by serial streaming: guaranteed filler spacing between target tries + Pause (Continue / Continue & skip)
[x] add lightweight animation / reward moment (use example gif for dev, later Pipa) after each burst — confetti + sound on graduation; Kid1 gets `_assets/pipa-dance_reject.webp`; Continue gates next problem
[x] show simple live progress toward target fluency during session — target-rings graphic (outer-in, green center) + progress text below Quit
[x] save targeted-practice metadata into the SQLite session — `TargetedConfig` table + session metadata via `targeted_store.py` / save-run payload

### iPad trial
[x] run first targeted practice session with Kid1 on iPad
[x] note setup friction: load time, keypad, attention, pacing
[x] note learner response: fun, frustration, speed, preference signals

### wondering nerd / math quest
[] design micro quiz format for Minecraft: 5-10 questions only
[] reuse same target fact selection logic for micro quizzes
[] decide how Minecraft should receive target facts
[] implement Wondering Nerd targeted micro quiz
[] keep interruption small enough to preserve gameplay flow
[] save or export enough result data to compare with iPad session

### compare
[] run Minecraft targeted micro quiz with Kid1
[] compare completion time, engagement, and correctness across both versions
[] ask Kid1 which version she prefers and why
[] decide next iteration based on her feedback


### Cloud Code new session questions
Three implementation questions from Claude Code (Opus 4.8, cloud session) for this plan, with Randy's answers (2026-06-23). These pin down the targeted-practice build.

#### Q1 — How should the 1–3 target facts get chosen?
Type them in now: up to **3 target facts** entered directly as fields on the anchor setup card (matches the ChatGPT-identifies → Randy-picks workflow). Keep the design open so **auto-detect-from-history** (the slowest facts from the learner's SQLite) can be added as a later option. A target entry covers **both orientations as one fact**: entering `3+6` practices both `3+6` and `6+3` — the canonical form and its complement/expanded form count as a single target entry.

#### Q2 — Burst structure and fact mix?
**Superseded (2026-06-23 redesign):** no bursts — targets stream **serially**, one current target at a time mixed with filler from a shuffled deck. Spacing between target tries is driven by percent-target (always ≥1 filler when a filler list exists). Pause provides manual breaks.

#### Q3 — Success metric for a target fact?
**Cumulative fast-correct** (updated after playtest): a target graduates after N correct answers under the fast threshold (default 2000 ms; e.g. 3 total — rings are **never lost** on slow/wrong). Live progress = target-rings for the current target + **% of targets graduated**; session ends when all targets graduate (no max-bursts cap). Speed + accuracy captured in SQLite; streak stands in for confidence (optional confidence tap later).


### Targeted practice — how it works (prompt snippet)
Targeted practice on the anchor page drills 1–5 coach-chosen facts until each graduates. Setup: type targets (e.g. `3+6` = both orientations), optional filler list, params (graduate-after, fast-ms, percent-target) — auto-saved to the learner's SQLite file. During the run, targets are worked **serially**: only the first not-yet-graduated target is mixed with filler drawn from a shuffled deck; spacing guarantees ≥1 filler problem between target tries (never back-to-back). A **fast-correct** (correct within the ms threshold) fills one ring toward graduation (default 3 cumulative; rings never lost). On graduation: confetti, per-student reward animation, **Continue** before the next problem; then the next target becomes current. Wrong answers use the standard correction flow (Flag / Continue / Continue & insert). Session ends when all targets graduate; Quit & save stores partial progress and full metadata in the session SQLite.


### Terminology
- **Session** — one full targeted-practice run for one learner; saved as **one** SQLite session (one file append). Ends only when all targets graduate; Quit & save at any point stores the partial session.
- **Serial targets** — targets are worked **one at a time, in order**: only the current (first not-yet-graduated) target is mixed with filler; the next becomes current when the current graduates. There is **no burst** — problems stream one at a time.
- **Target problem** — a coach-chosen problem (up to 5) pushed toward fluency. **One problem across both orientations** (`3+6` = `6+3`). Shown compact (`3+6`) in the target fields.
- **Filler problem** — a non-target problem from the stored **target filler** list (orientation preserved; `6 + 0` and `0 + 6` are distinct). Stored/shown spaced (`a + b`). Drawn as a **shuffled deck** (shuffle, draw off the top, reshuffle when exhausted). With no filler list, every problem is the current target.
- **Spacing** — a target never repeats back-to-back: between tries there are `gap` filler problems, `gap` random in `[1, round((100−percent)/percent)]` (so lower percent → more filler between tries). Always ≥ 1 when a filler list exists.
- **Graduate** — a target hits success: N **fast-correct** answers **cumulative** (not in a row — a slow/wrong answer never removes an earned ring). On graduation: rings fill, confetti + the math-quiz sound, then a **Continue** button below the problem gates the next problem.
- **Fast-correct** — correct **and** within the **fast threshold** (default 2000 ms).
- **Target rings** — the left-of-problem graphic: one ring per fast-correct needed, filled **outer-in** (outer = other colors → **center = green**, filled last) as the current target's fast-correct count grows. **Rings are never lost** (cumulative). No number under it.
- **Pause** — hides the problem; **Continue (same problem)** or **Continue & skip** (targeted: discard the current problem) / Continue & insert (assess: re-ask it later).
- **Persistence** — targets, filler, and params (graduate-after / fast-threshold / percent-target) live in the per-user SQLite file (`tools/targeted_store.py`, `TargetedConfig` table), read on load and written on save — same mechanism as internal problem lists. Prefilled from per-learner code defaults until the file has its own.


### Build status
- 2026-06-23 — **Done:** DOM-free engine `engine/targeted_practice.mjs` (parsing, canonical orientation-insensitive keys, filler pool, **serial streaming `nextProblem()`**, fast-correct-streak graduation reported by `record()`, `progress().current` for the rings, requeue, ends-only-on-all-graduated, SQLite metadata) + 22 unit tests.
- 2026-06-23 — **Done:** SQLite persistence — `tools/targeted_store.py` (`TargetedConfig` table) + dev-server `/api/targeted-config` (GET/POST) and `targetedConfig` in `/api/latest-user-db` and the save-run payload. 8 Python tests.
- 2026-06-23 — **Done:** anchor page — up to **5** target fields + params (graduate-after, fast-threshold ms, percent-target), per-learner prefill (Kid1/K2; **K2** = `1+8,2+7,2+5,2+8,4+7`, 5 / 4000ms / 30%), the single **target filler** editor (auto-saves), config persisted into the session, **Flag previous** + Continue & insert. 14 e2e tests (`tests/e2e/targeted.spec.mjs`).
- 2026-06-23 — **Done (redesign):** removed the burst — targets stream **serially**; added a **Pause** (Continue / Continue & skip); the **target-rings** graphic (left of the problem); **confetti + the math-quiz sound** on each graduation (right side); moved the progress text **below** Quit & save / Quit & abandon.
- 2026-06-23 — **Done (tuning):** rings fill **outer-in** with a **green center** (no number under them); a **Continue** button gates the next problem after each graduation; **guaranteed spacing** (≥1 filler between target tries, gap from the percent); filler drawn as a **shuffled deck**. K2's `8+1`→`2+8` etc. (now `1+8,2+7,2+5,2+8,4+7`). 15 e2e tests.
- 2026-06-23 — **Fixes:** targeted setup now **auto-saves** to the file on any change (targets — incl. deletions — params, filler) via `/api/targeted-config`, so edits stick right away; a **wrong answer** in targeted now shows the **same correction flow** as the regular quiz (correct answer + Flag / Continue / Continue & insert). +2 e2e tests (17 total).
- 2026-06-23 — **Done:** per-student graduation reward — `TARGETED_REWARDS` (by name) overrides the right-side animation/sound; **Kid1** = `_assets/pipa-dance_reject.webp` (image only). Default 🎉 + sound otherwise; missing image falls back to 🎉. The reward stays up until Continue. Asset notes are below. +1 e2e (18 total).
- 2026-06-23 — **Fix:** targeted settings now persist to the source file reliably — they save on change (param fields also flush on **blur**, robust on iPad where `change` is flaky) **and** the moment you click **Start** (config-only, no session), so changing settings + a partial quiz leaves the source file updated. +1 e2e (19 total).
- 2026-06-23 — **Fix (playtest):** dropped the "in a row" requirement — fast-correct is now **cumulative**, so an earned ring is never lost on a slow/wrong answer (Kid1 didn't like losing rings). Graduates at N total fast-correct. +1 e2e (20 total).
- 2026-06-24 — **Schema proposal:** added `docs/2026-06-24_targeted-practice-sqlite-schema-proposal.md` and first-class SQLite tables for targeted sessions, per-target final state, and per-attempt target/filler roles. Future sessions store exact metadata; Kid1's one historical targeted session is backfilled with `inferred=1`.
- 2026-06-24 — **Reviewed:** implementation todos above checked off; iPad trial + Minecraft micro quiz still open. Engine + anchor + persistence + 20 e2e / 22 unit / 8 Python tests in place.
- 2026-06-24 — **Done:** reward animations are now **per-learner paths in the SQLite file** (`TargetedConfig.reward_image` / `completion_image`), set without code changes. Two slots: `reward_image` shows on **each** target graduation; `completion_image` shows only on the **final** graduation that completes the whole session. Both fall back to one code default (`TARGETED_REWARD_FALLBACK` = `_assets/pipa-dance.webp`); a missing image still degrades to 🎉. A params-only auto-save never clobbers the image paths; older files migrate (ALTER TABLE) on first read. +4 Python, +1 e2e (21 e2e total).
- 2026-06-23 — **Next:** real-learner trial (iPad); nicer target-rings art; per-student sounds as needed; optional confidence tap; reuse the selection logic for the Minecraft micro quiz.

### Assets for targeted practice
Per-student graduation-reward assets for targeted practice — the right-side animation shown
when a learner hits a target. There are **two** animations, both set **per learner** as a
path in the learner's SQLite file (`TargetedConfig`), so they can be changed without touching
code:
- **`reward_image`** — shown on **each** target graduation.
- **`completion_image`** — shown only on the **last** graduation that completes the **whole**
  session (all targets fluent).

When a learner's file sets neither, both fall back to the single code default
`TARGETED_REWARD_FALLBACK` in `anchor.js` (`_assets/pipa-dance.webp`). These webp/gif files
are **gitignored / local-only** under `_assets/`, which is mounted from `_LOCAL_FILES` in local
worktrees. The paths live in each learner's SQLite file, and the binaries are kept out of the
repo. If a referenced file isn't present locally the image simply fails to load and **nothing is
shown** (no broken image, no placeholder); the confetti + standard "correct" sound still play on
every graduation.

| Asset | Role | Notes |
|-------|------|-------|
| `pipa-dance.webp` | fallback (both slots) | default right-side animation when a file sets no path |
| `pipa-dance_reject.webp` | — | an alternate take |
| `pipa_no_wand_clap_jump_fixed.webp` | Kid1 completion | shown when Kid1 finishes the whole session (set in her file) |

### Setting a learner's reward / completion animation
1. Drop the animated `.webp`/`.gif` here.
2. Point the learner's file at it — paths are relative to `anchor.html` / the app root, e.g.
   `_assets/pipa-dance.webp` (**not** the repo path `apps/math-quiz/_assets/...`). Either:
   - CLI: `python3 tools/targeted_store.py <file.sqlite> <Name> set --completion-image _assets/<file>`
     (and/or `--reward-image _assets/<file>`), or
   - direct SQL: `UPDATE TargetedConfig SET completion_image='_assets/<file>' WHERE user_name='<Name>';`
3. Leave a field unset (NULL / empty) to use the fallback for that slot.

These assets are served by the local static / dev server; they are not required for the app
to run (a referenced-but-absent file just shows nothing). Because the directory is gitignored
and mounted from `_LOCAL_FILES`, add the file to the canonical local `_assets` folder on each
machine that needs it — it won't (and shouldn't) be committed.
