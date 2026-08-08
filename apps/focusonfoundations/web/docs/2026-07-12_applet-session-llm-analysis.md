file: 2026-07-12_applet-session-llm-analysis.md
title: Applet session SQLite — explainer + LLM analysis prompt
last-updated: 2026-07-12_0745
ai: Claude Code - Fable 5
session: `Logic Gates round-2 + session tooling`

**How to use this file:** attach it, together with one applet session `.sqlite` file (from `web/_data/applet-sessions/`), to a capable AI system, and ask it to perform the analysis at the bottom. Everything above the prompt is the data dictionary the AI needs to interpret the file correctly. (Developers: for a quick human-readable digest of the same file, run `../../../.venv/bin/python3 tools/telemetry_report.py <file>` from `web/`.)


## What this database is
One SQLite file = one learner session with an interactive teaching applet (currently **Logic Gates**, an 8-to-12-year-old-facing lesson that builds from a light switch to logic gates to a binary full adder). The applet records every click with millisecond timing, screen (step) enters/leaves, semantic interactions (switch toggles, reveals), and quiz attempts. The filename encodes applet, learner name, and local session start time: `logic-gates_K1_2026-07-12_073910.sqlite`.

All timestamps `t_ms` are **milliseconds since the learner pressed ▶** (session start). `Sessions.start_time` is the local wall clock at that moment.


## Tables
- **Users** — one row: the learner's name (from the launch URL; `anon` if not provided).
- **Sessions** — one row: `session_id`, `applet`, `user_name`, `start_time`, `end_time`, `duration_ms`, `user_agent`, `total_clicks`, `total_quiz_attempts`.
- **Events** — the raw, complete, time-ordered record. Columns: `t_ms`, `kind`, `step` (screen index at the time, 0-based), `target` (best-effort label of what was touched), `detail_json` (kind-specific payload). **This table is the source of truth**; the two tables below are derived from it.
- **StepVisits** — one row per continuous stay on a screen: `step`, `enter_t_ms`, `leave_t_ms`, `duration_ms` (`leave`/`duration` NULL if the session ended there). Use for per-screen time.
- **QuizAttempts** — one row per answer submission: `quiz`, `round`, `attempt_index` (1-based try count within that presentation of the round — 2+ means they got it wrong first), `prompt` (what was asked), `given` (their answer), `is_correct` (0/1), `t_ms`, `response_time_ms` (from when the round was presented to this attempt).

### Event kinds
| kind | meaning | detail_json |
|---|---|---|
| `start` | telemetry session created (t_ms 0) | applet |
| `applet-start` | learner pressed ▶ | `step`, **`steps`: the full ordered list of screen titles** — index = step number; use this to name steps |
| `step-enter` / `step-leave` | screen navigation | `title`, `phase`; step-enter also `previousStep` |
| `click` | any click/tap (capture-level; includes buttons, switches, nav dots) | target label in `target` |
| `toggle` | a switch was flipped (semantic) | inputs and resulting outputs, e.g. `{inputs:[1,0], out:1}` |
| `reveal` | a ?-button reveal was opened | item |
| `quiz-round` | a quiz round was presented | quiz, round, prompt |
| `quiz-attempt` | an answer was submitted | quiz, round, prompt, given, isCorrect |
| `mute` | sound toggled | muted true/false |
| `start-over` | learner reset the lesson from the final screen (same session continues) |

### Quizzes (`quiz` values)
- `NOT`, `OR`, `AND`, `XOR` — "will the light be on?" gate quizzes; `prompt` = the input bits (e.g. `10` means A=1, B=0), `given` = predicted output `0`/`1`.
- `mystery` — probe a hidden gate and name it; `prompt` = the hidden gate, `given` = the guess.
- `half-adder` — predict both output lights; `prompt` = `a=1,b=0`, `given` = `s=1,c=0`.
- `full-adder` — same with carry-in; `prompt` = `a=1,b=0,cin=1`.
- `ripple` — set four switches so two 2-bit numbers sum to a target; `prompt` = `target=3`, `given` = `a=2,b=1`.

### Logic Gates lesson flow (steps 0–20 at the time of writing)
The authoritative step list for a given file is the `steps` array in its `applet-start` event — prefer that over this table if they differ. Current flow: 0 switch+light, 1 inverted (normally-closed) switch, 2 NOT explore, 3 NOT quiz, 4 two-switch wiring reveal, 5 OR explore, 6 OR quiz, 7 AND explore, 8 AND quiz, 9 XOR explore, 10 XOR quiz, 11 NAND explore, 12 mystery-gate game, 13 gate-family recap, 14 half adder discovery (XOR+AND), 15 half-adder quiz, 16 full adder (gate level), 17 carry place-value lesson, 18 full-adder quiz, 19 chained-adder binary addition with targets, 20 finale. "Explore" screens expect the learner to try **all** input combinations (a truth table fills in; a `toggle` with `tableDone:true` marks completion).


## Interpretation notes
- **Intended sequence** is linear 0→20 via the "→" button. `step-enter.previousStep` shows actual navigation; jumps of more than ±1 mean the learner used the dot navigator (each such click also appears as a `click` on target `go to step N of 21`).
- **Tries**: `attempt_index` > 1 on a quiz round = wrong answers before the right one. Wrong mystery guesses are attempts with `is_correct=0`.
- **Exploration quality**: on explore screens, count `toggle` events and whether `tableDone:true` was reached; a learner who leaves before completing the table skipped the discovery.
- **Time**: `StepVisits.duration_ms` per screen; compare against the intro narration length (~5–15 s) — durations under ~5 s mean the narration was cut off / screen skimmed. Very long durations with no events may be absence.
- **Clicking around**: `click` events with no matching semantic event (rapid nav-dot hopping, repeated taps on non-interactive areas) indicate distraction or playfulness; repeated toggles of the same switch in quick succession often indicate playing with the lights (which is fine — it is a toy too — but distinguish it from task progress).
- **Re-plays**: "Play again" quiz restarts re-present round 0 (`quiz-round` events repeat); `start-over` restarts the whole lesson within the same file.
- Audio narration state matters: `mute` events tell you whether spoken instruction was heard.


## Analysis prompt
> You are given a SQLite session file recording one child's pass through the interactive lesson described above, plus this data dictionary. Analyze the session and report:
> 1. **Understanding** — Which concepts does the student demonstrably understand (correct first-try quiz answers, completed truth tables, efficient target-sums), and which do they not yet (repeated wrong tries, avoided or rushed screens)? Be specific per concept: switch/signal, each gate, place value, half adder, full adder, binary addition.
> 2. **Weak spots** — Rank the 2–3 weakest areas with the evidence (quiz rounds, tries, response times, time on screen), and suggest what to practice next.
> 3. **Engagement profile** — How focused vs. distracted or playful were they? Use navigation order vs. the intended 0→20 sequence, click-to-progress ratio, toggle play, dwell times, and narration muting/cutoffs. Distinguish productive play (exploring switch combinations) from off-task clicking.
> 4. **Pacing** — Total time, time per phase (switches / gates / combining / adder), and where time concentrated.
> 5. **Recommendations** — Three concrete suggestions for the next session, phrased for a parent or teacher.
>
> Ground every claim in specific rows (step numbers/titles, quiz rounds, timestamps). Note data limitations where relevant (e.g. a final screen with a NULL leave time, or an unmuted session where you still cannot verify the child listened).
