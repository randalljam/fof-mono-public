file: apps/math-quiz/ROADMAP.md
title: Math Quiz — roadmap and vision

## Vision
Math Quiz is moving toward a local-first arithmetic fluency system that can assess what a learner knows, deliver targeted practice at the right facts, and make progress visible to both the child and the coach. The durable center is one per-learner SQLite file with raw attempts as the source of truth; fluency, profiles, generated practice lists, dashboards, and game rewards are all recomputed or configured from that file. The dragon game is the current motivation layer: real fluency practice feeds an earned progression from egg to ride, while parent-facing tools keep the learning loop observable.
## Now / Next / Later
- **Now** — Keep the deployed anchor flow stable: kid landing, Continue latest / Start New, SQLite save-run accumulation, Targeted practice, Fluency feast, problem lists, quick quizzes, analysis load-for-review, and per-file profile thresholds.
- **Now** — Finish verification and polish on the `feature/math-quiz-dragon-baby` line: animated dragon GLB adoption, phase-gated dragon animations, story/world/Game Master integration, and browser playthrough checks.
- **Now** — Preserve the dragon playthrough apparatus as a regression path: seeded SQLite, simulated learner, headless full loop, Playwright real-UI run, and markdown reports.
- **Next** — Reconcile the fluency rubric and thresholds for developing learners: canonical red/yellow/green/blue semantics, per-learner threshold presets, full-universe rollups, and G1/G2 regression profiles.
- **Next** — Shorten assessment sessions by changing re-ask policy: stop re-asking correct-but-slow facts during assess, keep wrong/skip re-asks, and route speed work into practice.
- **Next** — Add curated subtraction and multiplication plans so non-addition sessions are not full 55-fact marathons.
- **Next** — Integrate dashboards and controls into the active practice loop: live per-fact/category heatmaps, generated next-quiz planning, queue injection by category, and clearer live goals.
- **Next** — Reuse targeted-practice logic for small Minecraft / Wondering Nerd micro quizzes and compare engagement against iPad anchor practice.
- **Later** — Move beyond local-family use with hosted/authenticated sync only when sharing requires it; keep source-only repo posture and protect learner data.
- **Later** — Grow the simulation/profile ladder to 5-10 learner profiles across addition, subtraction, multiplication, accurate-but-slow learners, and sticky hard facts.
- **Later** — Explore richer review aids such as synchronized session audio, AI-readable session exports, and LLM-supported coaching summaries.
## Idea inbox
- **2026-07-10** — Record full-session audio synchronized to the problem timeline so glitches, pauses, and learner comments can be reviewed against exact attempts.
- **2026-07-10** — Export sessions and fluency state as markdown for AI-assisted questions like "what does this learner know, and what should they practice next?"
- **2026-07-10** — Build a parent/operator live control panel with heatmap, rollups, upcoming queue, and category-based injection while a learner is practicing.
- **2026-07-10** — Design a 5-10 question Minecraft / Wondering Nerd targeted micro-quiz that writes the same single-session SQLite shape.
- **2026-07-10** — Add an optional confidence tap to targeted practice after a target graduation or hard fact.
- **2026-07-10** — Improve targeted-practice reward art, target-rings visuals, and per-student sounds without committing local-only media assets.
- **2026-07-10** — Rework read-aloud and automatic speech recognition; current legacy speech support is available but not treated as core.
- **2026-07-10** — Establish small anonymized committed SQLite fixtures and optional cloud-agent S3 read access for cases where real captures are needed.
