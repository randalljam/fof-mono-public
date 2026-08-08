file: apps/math-quiz/2026-06-12_manual-test-script.md
title: Math Quiz — manual test script (narrated session)
last-updated: 2026-06-12_0512
ai: Claude Code (cloud)
session: `MathQuiz thorough review`

A scripted manual test session for `apps/math-quiz`, designed to be run while voice-recording a think-aloud narration. Each item is tagged **[auto]** (the automated suite already covers the behavior — you're confirming it matches reality), **[auto-partial]** (mechanics automated, look/feel is not), or **[manual-only]** (automation can't reach this — these are the most valuable minutes). Concepts and terminology: `docs/web-testing-guide.md`.


## Setup
From the repo root:
```
python3 -m http.server 8907 --directory apps/math-quiz
```
Then open `http://localhost:8907/math_quiz.html` in **Chrome** (speech recognition is Chrome-only). Use `localhost` consistently rather than double-clicking the HTML file — browser-stored sessions are tied to the page origin, so sessions saved on `localhost:8907` are only visible there.

**Recording tips:** say the test ID aloud ("M5"); for each, state what you expect, then what you actually see; call out timings that feel off; and go off-script freely when something surprises you — just narrate it (that's the exploratory part, and often where the gold is). Keep DevTools console open (Cmd-Option-J) and mention any red errors.


## A. Quiz — core flow
- **M1 [auto-partial]** Name screen: pick a preset name, then instead type a brand-new name and Continue. Later (M25) confirm the new name appears at the top of the dropdown.
- **M2 [auto]** Preset `t5`, all three toggles OFF: answer all 5 correctly. Expect "Correct!" each time, ~1 s pause between problems, summary shows 5/5.
- **M3 [manual-only]** Sound effects: correct answer plays the horn, wrong answer plays the buzzer. Volume/annoyance check for a kid.
- **M4 [manual-only]** Read-aloud: "Read Problems Aloud" ON. Each problem is spoken ("four plus three equals"). Is the voice and speed OK for Kid1? Try a subtraction and a multiplication — does it say "minus"/"times" correctly?
- **M5 [manual-only]** Speech answers: "Automatic Speech Detection" ON, allow mic. After the problem is read, say the answer. Expect it recognized, filled into the box, and submitted. Try a two-digit answer ("fourteen"). **Watch specifically for the old bug where it jumped two problems ahead** — that should be fixed; narrate if you ever see a skipped problem.
- **M6 [auto-partial]** Wrong answer on purpose: expect "Incorrect. The correct answer is N", an Override button, and ~5 s before the next problem. Click Override on one — expect confetti + marked correct. (Confetti looking right is the manual part.)
- **M7 [auto]** Click "I don't know" on a problem — expect incorrect feedback; later confirm it shows as "I Don't Know" in the analysis list (M16).
- **M8 [auto]** Flag a problem: pick "Distracted" from the dropdown, type a comment in the box that appears, answer normally.
- **M9 [auto]** Start preset `a9` (20 problems), answer 2, click End Quiz, confirm. Expect summary for just 2.
- **M10 [auto-partial]** Auto-submit ON: type an answer and watch it submit without Enter. Manual judgment: does it ever submit before you finished typing (especially 2-digit answers)? How does it feel at kid typing speed?
- **M11 [manual-only]** Narrow the browser window to phone width (or open on your phone on the same network: `http://<your-mac-ip>:8907/math_quiz.html`). Is the problem readable, input usable, End Quiz button not overlapping?
- **M12 [auto]** Custom quiz: Custom → 3 problems, range 2–5, operations `*`. Expect problems shown with `×` on screen.
- **M13 [manual-only]** On the final screen: "Download This Session Data" and "Download All Sessions Data" — confirm real files land in Downloads (a `.json` and a `.zip`), and the JSON looks like the session you just did (problems use `*`, not `×` or `&times;`, in `problem_text`).

## B. Analysis dashboard
- **M14 [auto-partial]** Click "Go To Analysis". Expect the heatmap with your session data. Manual judgment: colors readable? Cell equations legible? Incorrect cells shown in dark red text?
- **M15 [auto]** Operation filter → Multiplication: your M12 problems appear. Flag filter default "Exclude All Flagged": the M8 problem is excluded and the count text says so; switch to "All" and it returns.
- **M16 [auto-partial]** Open "Session List View", try the sort buttons. Expect order changes; the M7 problem displays "I Don't Know"; time bars look proportional (manual).
- **M17 [auto]** With sorting on "Time ↓", Edit Flags on the top item, check a flag, Save. Expect "Saved!" and the flag to appear **on that same problem**.
- **M18 [auto-partial]** Select that specific session in the session dropdown → "Export Modified Session". Expect a `_MODIFIED.json` download and an alert. Reload the page — the flag edit from M17 should still be there.
- **M19 [manual-only]** Drag the min/max response-time sliders — heatmap colors should rescale sensibly.
- **M20 [manual-only]** Switch Duplicate Handling (average/first/last/min/max) and Color Scale options — values and colors change plausibly, title updates.

## C. Fluency tracker
- **M21 [auto-partial]** Click through to the Fluency Tracker. Expect addition/subtraction/multiplication sections, a fluency % per section, and status dots. Manual judgment: do the green/yellow/red/gray statuses match your intuition for the data you just generated?
- **M22 [auto]** In a "Problems Needing Work" grid, click a problem → edit dialog. Set a manual status with a reason, Save. Expect the override (⭐) reflected.
- **M23 [auto-partial]** "Generate Problem List": set total 5, percentages summing to 100, "Use in Quiz". Expect the quiz to open with the "problem-list" preset pre-selected and run exactly those problems. Manual judgment: is the red/green mix what you asked for?
- **M24 [manual-only]** Change the threshold controls (Fluent Speed ms, Window Size, Sessions for Permanent) — statuses should re-compute plausibly. Try "Sessions for Permanent" = 1 after a couple of sessions of the same fact: expect blue (Permanent) dots.

## D. Cross-cutting
- **M25 [manual-only]** Quit the browser entirely, reopen `localhost:8907` — sessions, your new name (M1), and overrides all still present.
- **M26 [manual-only]** "Clear All Sessions" (after M13's download!): confirm dialog, then dashboards show their empty states with a sensible message rather than errors.
- **M27 [manual-only]** The real acceptance test: have Kid1 run a session while you watch. Friction points, confusion, delight — narrate everything. No automated test can do this one.


## After the session
Hand the recording/transcript to an agent for **triage and coverage gap analysis**: each observation becomes (a) a bug → fix + new automated regression test, (b) a UX/design item → backlog, (c) untested-but-fine behavior → candidate automated test, or (d) confirmation of existing coverage. Ask the agent to map findings to test IDs (M1–M27) and to the automated specs in `tests/`.

## Test Results 2026-06-13
### M1-M4 OK
### M5 Lots of problems with ASR
I saw many errors here just with the five problems I did so I was doing this in Chrome and I allowed the microphone and I had AirPods plugged into my bluetooth because I made a hotel so I wanted the sounds to come through there and they were they are and part way through I did go to the sound set and check the microphone and that was set to the AirPods and I could see the input indicator responding so here's what I observed most of the time it did not detect the input numbers that I was saying very well I would have to say multiple times and then sometimes it would then show up once and sometimes it would show up with two numbers like seven something that happened once then another time I think on the fourth question I just couldn't get it to detect it at all after five or six attempts so I just typed it even saying it very loudly I kept having to hit this start listening again so overall this was very problematic but I'm not surprised about that I think the sound aspect for the played problems and for the automatic speaker speech recognition I want to come back to overhaul anyway at some point so at this point I don't consider it core behavior or functionality. So for now in this review branch before we do the PR what I want you to do is make the default to have Both the read aloud and the Automatic speech detection change that to automatic speech recognition. So just because that's a more standard term And then have those both by default not checked And Then just put in parentheses for the automatic speech recognition just put "may be buggy".
### M6-M10 OK
### M11 Narrow window
In quiz is overlapping the flag button so I think the solution for this is to put in quiz in the middle below the I don't know And then have those buttons be different colors in quiz can be gray And I don't know I think the font and the button should match just that font size because it's smaller right now I think that's so the button is the same size but I just think it looks weird.
### M12-M13 OK
### M14 Analysis resize window
I'm noticing things are fine when the screen and I'm doing this on my laptop 16 inch MacBook Pro So in the window is about two thirds of the size, everything looks fine As I start to narrow it at about half way I lose the Y axis time in milliseconds And then also at that point the problem digits and operator text inside each cell becomes too small to read And then as I narrow it even further it just totally starts to cut off the plot So that's a problem
### M15 OK
### M16 Session List view
Sorting works here, but I don't see the "I don't know" problem. My guess is because it wasn't the first time. And I think this session list view is only showing the first instance of a particular problem. So, ideally that would change, although I think I may want to make some more overhauls in this session list view, so... Hold off on this for now and just flag that it's showing only the first time and confirm that that is indeed the case.
### M17 OK
### M18 Export Modified Session
I had trouble finding which session held the problem that I modified by setting a flag I had to just do this with trial and error because in the list view there's no correspondence to the session and that's probably, I mean that's okay right now, I think just flag this as a follow up consideration. The rest of this test worked fine and was exactly as described.
### M19 response-time scale
This is fine and working as expected except for when I slide the max scale all the way to zero That actually resets the scale to I think up to the maximum time Which in this case is like, or maybe it's some default, it says 25k, I think that's 25 seconds But I think there was one that was really long because I was looking at the list testing So what we want that to do, I think it's just a big jump like as you're dragging it down you're seeing more things go, I have it on the classic Or red and red and red and then all of a sudden at the bottom it jumps everything to zero So I think for the set scale you want to have the zero point be the same as 200ms max So, or 100ms max Yeah, I can set it at where the max is 100ms, so I think just that's a small tweak I think just go ahead and make that change here in this review branch And then update one of the unit tests or level 2 tests to reflect that change and then confirm it's correct.
### M20 OK
### M21
Okay, here's what I'm seeing on my first view of the Fluency Tracker And I didn't review this much when CT was coding it up I did give her some light feedback on it, but it was a late thing in her work on this app So, um... First thing I'm noticing as I scan down is for single digit subtraction, I didn't do any And yet it says "problems needing work, all problems are fluent" and it has the celebration emoji So that's a mistake I mean if this is... if there is no data for one of these sections, I should just say that and shouldn't show it at all But then there may be another bug related to if the problems needing work are empty I mean I guess that's only going to show if there's zero problems done This case of zero problems done plus no problems needing work, which there aren't a misunderstanding that that's all problems are fluent Yeah I'm surprised that it shows I'm 67% fluent for single digit multiplication because I think I only did a handful of problems Fluent for slow to total problem 6 So I think that's just based on the problems that I've done Whereas, you know, I want the 67% to be... I want the high level of these numbers to be... To be, you know, overall percent of the way fluent Not just for the ones that have been tried, so that's a major... A major thing to fix, although I think... I think a lot of the fluency things here we're going to want to defer Just flag in this review branch and then defer I don't want to fix these here now in this branch
### M22-M24 OK
### M25-M26 OK
### M27 Kid1 test
Ha this is a good idea, but She's still asleep, and I need to get this done, and I want to get this merged in Miss PR Finished yeah, I'm reaching to Maine and so I'm gonna skip this one for now.

## Feature/Changes Ideas
### S3 upload

### session audio recording
powerful to use along with read aloud

### rename
Math Flu and call json/zip files math-flu_session_<name>_<date>_<time>

### Sessions dump md for AI analysis
Here's all this data. Now, answer these questions. Does the learner have fluency in single digit addition, up to 20 subtraction, and single digit multiplication? And what should you do next for practice?


## Disposition 2026-06-13 (triage of results)
Agent triage of the results above into changes-made / confirmed / deferred, done on branch `review/math-quiz` before the PR. Most of the app passed; the items below are the exceptions.

### Changed in this branch
- **M5 — audio/speech defaults.** "Read Problems Aloud" and the speech toggle now default **off**. The toggle was renamed "Enable Automatic Speech Detection" → **"Enable Automatic Speech Recognition (may be buggy)"** (standard term + honest caveat). The whole audio subsystem (read-aloud + ASR) is acknowledged as needing a later overhaul and is not treated as core for this checkpoint. Covered by existing quiz E2E tests (which run with these toggles off).
- **M19 — heatmap K2 Scale slider.** Dragging K2 Scale to 0 made Plotly discard the manual range and autoscale (the scale appeared to "jump" to ~25 s). Fixed two ways: the slider floor is now 100 ms (was 0), and a new `clampHeatmapScale()` helper guarantees an always-valid increasing range (max ≥ 100 ms and always above min). New unit test `clampHeatmapScale ... (M19)` in `tests/math_analysis_page.test.mjs`.
- **jszip 3.7.1 → 3.10.1** (test dependency) — clears the moderate `npm audit` advisory noted in `security/2026-06-12_math-quiz-playwright-audit-note.md`. `npm audit` now reports 0 vulnerabilities; all tests still pass.

### Confirmed (no change — working as designed)
- **M16 — session list "only first instance?"** Confirmed it does **not** dedupe: `renderProblemList` shows every attempt returned by `queryDatabase`. The "I don't know" attempt was hidden because the default flag filter is **"Exclude All Flagged"** and "I don't know" records a `dontknow` flag — switch the flag filter to "All" (or "I Don't Know") to see it. A broader session-list-view overhaul is still wanted later (see deferred).

### Deferred — flagged for future work (not changed in this branch)
- **M5 (audio/ASR overhaul).** Speech recognition was unreliable in testing (frequent non-detection, occasional double digits). Whole read-aloud + ASR subsystem to be reworked later; defaults-off + "may be buggy" is the interim mitigation.
- **M11 — narrow-window button overlap.** The fixed "End Quiz" button overlaps the flag dropdown at phone width. Proposed fix (for later): move End Quiz below the "I don't know" button, centered, gray, font size matched to the other buttons.
- **M14 — analysis heatmap responsiveness.** As the window narrows past ~half, the Y-axis (ms) label disappears, in-cell equation text becomes unreadable, and the plot starts clipping. Needs a responsive-layout pass.
- **M16 — session-list-view overhaul.** Beyond the confirmation above, a fuller rethink of the list view is wanted.
- **M18 — list ↔ session correspondence.** When editing flags in the list view there's no indication of which session a problem belongs to, so targeting "Export Modified Session" is trial-and-error. Follow-up consideration.
- **M21 — fluency percentage scope (major).** Section fluency % is computed only over facts that have been *attempted*, not the full fact space, so a handful of tried problems can read as "67% fluent". Separately, a section with **no data** (e.g. subtraction never practiced) shows "All problems are fluent 🎉" instead of a no-data/empty state. Both belong to a planned fluency-tracker overhaul; deferred deliberately.

### Backlog — feature ideas captured during testing
- S3 upload of session data.
- Per-problem session **audio recording** (pairs with read-aloud).
- Rename app to **"Math Flu"**; session/zip files `math-flu_session_<name>_<date>_<time>` (touches naming + any future S3 keys — defer).
- **Sessions → markdown dump for AI analysis**: export all session data as markdown to ask an LLM "does the learner have fluency in single-digit addition / to-20 subtraction / single-digit multiplication, and what should they practice next?"

