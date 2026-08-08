file: apps/math-quiz/dragon/docs/2026-07-05_story-world-gm-plan.md
title: Dragon game — story, world, journey, and Game Master improvements
last-updated: 2026-07-05_1430
ai: Claude Code (cloud) - Fable 5
session: `Dragon game improvements`

Branch: `feature/dragon-baby-story-world` (off `feature/math-quiz-dragon-baby`). Goal: the game works mechanically (egg → hatch at 60% → milestones to the 100% ride) but is thin on engagement. This round adds a real story delivered after every quiz, a richer world, somewhere to GO after hatching, and a phone-friendly Game Master page for the parent.


## Open-source models drawn from
Researched (2026-07-05) for an open-source game with a similar stack/approach to model rather than inventing everything:

| Project | License | What we borrow |
|---------|---------|----------------|
| [Quick_3D_RPG](https://github.com/simondevyoutube/Quick_3D_RPG) (SimonDev) | MIT | Closest stack match (no-build CDN ES-module Three.js). Quest/level-up component pattern → our objective system (`nextObjectiveFor`); FSM character states → dragon anim states |
| [The Aviator](https://github.com/yakudoo/TheAviator) (Codrops tutorial) | Codrops (adapt, don't redistribute) | Procedural low-poly art techniques: character as a Group of primitives, flat shading, palette module, clouds built from clustered primitives, micro-animations (squash-and-stretch) |
| [Moments of Happiness dragon](https://moments.epic.net/) (Maaloul) | Educational reference | Cuteness techniques for a primitive-built dragon: eye tracking via lookAt, expressive idle motion |
| [Tuxemon](https://github.com/Tuxemon/Tuxemon) | GPLv3 (design only) | Creature progression and story beats as **data, not code** → `sim/story_content.js` beat tables with unlock conditions |
| [TuxMath](https://github.com/tux4kids/tuxmath) | GPL (design only) | Fact-fluency drill ladder pedagogy; math events living inside the game world |
| [ClassQuiz](https://github.com/mawoka-myblock/ClassQuiz) | MPL-2.0 (pattern only) | Host/player second-screen split → Game Master page (parent's phone observes + injects messages), shrunk to dev-server JSON polling |

Patterns and data schemas only are taken from GPL/Codrops projects; no verbatim code.


## What's being built
### 1. Story system (after every quiz burst)
- `sim/story_content.js` — pure data. Arc: a storm separated Mama Dragon from her egg; her letters arrive as the child practices; the baby hatches and is **named by the child**; the "dragon road" home to Mount Ember runs through the Butterfly Meadow → Whispering Hills → Firefly Grove (beacon); at 100% the beacon is lit, the mountain answers, and the dragon invites the ride (never spelled out in advance).
- `sim/story.js` — DOM-free engine: phase from game state, sequential unseen beats then rotating extras (no repeats until pool exhausted), performance-tiered quiz reactions, `nextObjectiveFor` (HUD + GM), journal of seen beats.
- `ui/story_overlay.js` — parchment scroll card shown at burst end: reaction line + next story beat + any Game Master messages; naming dialog for the `name`-kind beat; journal (re-read collected scrolls) from the HUD.
- Game-state additions (additive, no version bump): `seenBeatIds`, `dragonName`, `visitedStones`, `recentBursts` (rolling last 20 for the GM feed).

### 2. World visuals (egg phase onward)
`world/environment.js` + new `world/ambient.js`: mountain ring with a smoking **Mount Ember** on the horizon (story anchor), drifting primitive clouds, flowers/mushrooms/rocks, pond, campfire at the nest (flicker light), butterflies (meadow + nest), fireflies (grove), circling birds. Egg gains **crack stages** as fluency approaches 60% plus a faster glow pulse — visible build-up to hatching.

### 3. Post-hatch journey (somewhere to go)
`world/journey.js`: each unlocked area gets a **Story Stone** with a sparkle trail leading to it (meadow at 70, hilltop at 80 — new area, grove/beacon at 90). Walking there with the dragon and clicking the stone plays that leg's story beat + effect and is tracked (`visitedStones`) as the current objective. Keeps the quiz loop primary; the journey is the connective tissue between milestones.

### 4. Game Master companion page (parent's phone)
- Dev server (`tools/dev_server.py`) additions, all under gitignored `_data/<folder>/dragon-gm/`:
  - `GET/POST /api/dragon-state` — the game posts a snapshot (pct, phase, objective, story progress, recent bursts) at load + every burst end; the GM page polls it.
  - `GET/POST /api/dragon-messages` — GM sends messages ("From the Dragon Keeper"); the game polls at burst end and shows them in the story overlay, then marks them read.
- `dragon/gm.html` + `gm.js` — mobile-first dashboard: real fluency % (the kid HUD deliberately never shows this), next milestone + objective, story chapter, activity feed of recent bursts/milestones, message composer with quick phrases. Served by the same dev server; phone reaches it via the LAN URL the server already prints.
- `sim/gm_state.js` — DOM-free snapshot builder (testable in Node).

### 5. Tests & simulation
Baseline verified on branch creation: 221 unit tests pass; headless playthrough (`simulation/dragon_playthrough.mjs`) runs seed → 100% in 24 bursts with all milestones in order. Added: story engine tests (phase/beat/no-repeat/reaction determinism), gm_state shape tests, dev-server endpoint tests (stdlib unittest), and a story-aware assertion pass in the playthrough smoke test. Re-run the full suite + sim before PR.


## Commit plan (stepwise) — all landed 2026-07-05
1. ✅ docs: this plan + research
2. ✅ feat: story engine + content (sim modules) + unit tests (`dragon_story.test.mjs`)
3. ✅ feat: story overlay UI, naming, burst-end integration (+ e2e playthrough driver updates)
4. ✅ feat: world visual enrichment + journey (one commit — `ambient.js`, egg cracks, `journey.js`, hills)
5. ✅ feat: dev-server GM endpoints + python tests (`test_dev_server_dragon.py`)
6. ✅ feat: GM companion page (`gm.html`/`gm.js`) + game-side state posting/message polling
7. ✅ docs: README/ASSETS/AGENTS updates; story timeline in playthrough reports
8. ✅ fix: gate arches, scalloped wings; flight range to the mountain foothills

## Verification (2026-07-05)
- Unit: 235/235 pass (`node --test apps/math-quiz/tests/*.test.mjs`); Python tools: 128/128.
- Headless sim (`simulation/dragon_playthrough.mjs`, real dev-server pipeline): 24 bursts seed→100%, all milestones in order, one story beat per burst (`egg-letter-1` → … → meadow beats), naming beat handled.
- Browser playthrough (`npm run test:playthrough`): full arc through the real UI incl. story-card dismissal and the naming dialog (dragon named Sparkle); see `dragon/playtests/runs/`.
- GM flow verified live: state POST/GET roundtrip, message send → unread → mark-read; `gm.html` rendered on a phone-sized viewport against a seeded server.
