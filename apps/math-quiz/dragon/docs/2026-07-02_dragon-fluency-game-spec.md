file: apps/math-quiz/docs/2026-07-02_dragon-fluency-game-spec.md
title: Dragon fluency game — spec prompt (dragon egg → 100% fluency → ride)
last-updated: 2026-07-02_1709
ai: Cursor - Composer 2.5 Fast
session: `Dragon fluency game spec`

A math-fluency practice game wrapped around raising a baby dragon. The **quiz engine already exists** in `apps/math-quiz/` (single-digit arithmetic quizzes, fluency tracking, objective 100%-fluency determination) — this game is the **motivation and scaffolding layer** on top of it. See the math-quiz overview: `apps/math-quiz/README.md` (and canonical `docs/SPEC.md` / `docs/PLAN.md`) for the quiz/fluency logic to build on.

The technical / presentation requirements below are lifted from the earlier RTS spec prompt (`2026-07-02_ai-rts-browser-game-spec-prompt.md`) and pared down to only what fits this game — condensed, with related items combined.

## Game description (verbatim dictation)
> A math-fluency for single-digit arithmetic practice game where the user is going to be doing quizzes in bursts of 10 to 20 questions, and all of the quiz logic and the whole quiz is already done. That work is in an app called `app/math-quiz` and there's an overview document for that — I want to refer to that and then build a game here that is going to be based upon the user finding a dragon egg and hatching a baby dragon and raising it, and then the culmination of it is going to be, as she gets to demonstrating 100% fluency after lots of practice and on the objective determination of her 100% fluency, it's going to involve her getting to ride the dragon. The dragon is going to be able to fly and it's going to invite her to ride it. So the dragon needs to be cute and this should appeal to an eight-year-old girl. So I'd like this to encourage her to do lots of practice, but the expectation is not to do it in one sitting — the expectation is to play the game and complete-to-fluency over the course of at least a couple days if not like a week. So I want there to be some parameters and some control mechanisms that can be tuned by the parent/admin, because we're trying to build consolidation of memory and transfer the math facts (the single-digit addition problems) to long-term memory, and she largely knows them already and she's at about demonstration of about 50% fluency but needs practice. And the purpose of this game is the motivation and the scaffolding for the practice.

## Prompt (for Fable 5 — produce a detailed plan)
You are a highly agentic, high-capability planning model (**Fable 5**), running in the harness's **plan mode**. **Do not write the game.** Your sole deliverable is a **super-detailed implementation plan** for the game described here, using the condensed spec below as your requirements. The plan will then be **executed by a mid-level coding model (Composer 2.5 Fast)**, so it must be explicit and self-contained: assume the executing model has less capability and less judgment than you and will follow the plan closely rather than improvising.

Create the plan so Composer 2.5 Fast can build it step by step with minimal ambiguity: break the work into ordered phases and concrete tasks, specify files/modules to create and their responsibilities, name the key functions and data shapes, spell out how to integrate with the existing `apps/math-quiz/` engine (including reading Kid1's `.sqlite` file and using Fluency Feast generation), and include per-phase live-in-browser verification steps. Call out decisions, assets to source, and any risks or open questions explicitly rather than leaving them implicit.

**The important goal:** the point of this game is **motivation and scaffolding for math-fluency practice** — not the game for its own sake. Everything the plan specifies should exist to make an eight-year-old *want* to keep practicing single-digit arithmetic until she reaches objective 100% fluency, at which point the dragon she has raised can fly and invites her to ride it. Progression is tied strictly to her real fluency score (see Progression), so the reward is earned by genuine mastery, not by playing longer.

**Controls — mirror Minecraft:** the player (my daughter) is **very experienced and proficient at Minecraft**, so lean into that. Use Minecraft-style controls and interaction conventions (movement, camera, interaction) so the game feels immediately familiar and she can focus on playing and practicing rather than learning new controls.

**Standalone, not a mod:** this is a **standalone browser game** — **not a Minecraft mod**. Reuse Minecraft's *control scheme and feel*, but do not build against or depend on Minecraft/Forge/Fabric. Everything ships as its own Three.js app per the tech stack below.

## Condensed spec
### Genre & camera
3D dragon-raising / pet-companion game in the browser, bird's-eye-to-close-up camera as suits the scene (nest, play area, flight).

### Theme & narrative
Find a dragon egg → hatch a baby dragon → raise it through practice → on **objective 100% fluency** the now-grown dragon can fly and **invites her to ride it** (the reward/culmination). Cute, warm, aimed at an **eight-year-old girl**.

### Progression (replaces economy/win-condition)
Practice happens in **bursts of 10–20 questions** (single-digit arithmetic, starting addition). Progression is **objective and tied directly to the fluency score** from the existing engine — the dragon grows as fluency rises, and the flight/ride unlocks on the objective **100% fluency** determination. This keeps the learner motivated to genuinely try hard rather than game the pacing. No in-game pacing or parent/admin knobs: any tuning of difficulty or what counts as fluent is done **through the math-quiz engine itself** (its fluency parameters and algorithms), not through game-side settings.

### Milestones & foreshadowing (intermediate goals + discovery)
Give her **intermediate goals** along the way, not just the far-off 100% ride. Tie **fluency-percentage milestones** to visible, unlockable steps in the dragon's growth and the game world (e.g. hatching, first steps, new abilities/areas) so each practice burst feels like it's building toward the next reveal. **Foreshadow** the upcoming milestone — hint at what's coming as fluency climbs so she has a concrete near-term thing to chase. Toward the end, **foreshadow the final push** (that something big unlocks near full fluency) **without explicitly telling her what it is** — the flight/ride should stay a **discovery**, teased but not spelled out, so the culmination lands as a surprise reward for reaching objective 100%.

### Quiz engine (reuse, don't rebuild)
All quiz logic, arithmetic generation, and the objective 100%-fluency determination already exist in `apps/math-quiz/` — the game consumes/wraps that rather than reimplementing it.
- **Operation scope:** initially tied to an **addition** run, and planned to run **one operation at a time** (mixed operations possible later, but not the initial target).
- **Problem generation:** use the **Fluency Feast** problem-list generation mode (the per-file fluency-driven list preset), not hand-authored lists.
- **Learner starting point:** plan for the learner (**Kid1**) starting at **~50% fluency** — analyze her existing history file rather than treating her as a blank slate.
- **Her database file (relative path):** `apps/math-quiz/_data/tlkids/math-flu_K1_<YYYY-MM-DD>.sqlite` — the latest-dated `math-flu_K1_*.sqlite` in the `tlkids` source folder (the app's Continue/latest logic picks the most recent). The `_data/` folder is gitignored, so the file exists locally, not in the repo.

### Characters & animation
One **cute rigged dragon** with skeletal animations spanning its life stages — hatching, idle/play, walking, growing, and flying (plus the "invite to ride" moment). Appealing and expressive for a young child.

### Visual presentation
Cinematic and juicy: dramatic lighting, real shadows, and satisfying feedback on every action (correct answers, growth milestones, hatching, unlocking flight).

### Audio
Full soundscape — real sound effects (answers/feedback, hatching, growth, flight) with quiet background music underneath. Never harsh; cozy and encouraging.

### Tech stack, architecture & dev process
Three.js with plain ES modules, no build step, served from a local static server. Keep **simulation/game state separate from rendering**, and **verify each system live in the browser** as it's built.

### Assets
Real, high-quality downloaded assets (model, textures, sounds) — **never AI-generated**.

### Controls, UI & onboarding
Trackpad-first controls, a clean overlay HUD, and an in-game how-to-play guide suited to an eight-year-old.
