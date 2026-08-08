**🐉 Dragon Baby Game - Math Fluency**

3D browser game for kids: explore a dragon nest, answer addition problems to feed the egg, hatch and name your dragon, follow story scrolls and sparkle trails through the meadow and hills, and ride your dragon home to Mount Ember. Fluency progress comes from the same per-learner SQLite file as the math-quiz anchor app.

## Run Commands Cheat Sheet
- Start (or restart) the dev server from repo root: `.venv/bin/python3 apps/math-quiz/tools/dev_server.py` — if port 8907 is already in use, the script stops the old process and starts fresh
- Game (laptop): `http://127.0.0.1:8907/dragon/index.html`
- Game (iPad/phone/other computer, same Wi-Fi): `http://<your-laptop-LAN-IP>:8907/dragon/index.html` (or `/dragon/index` — the dev server maps that too)
- Game Master dashboard (parent phone, same Wi-Fi): `http://<your-laptop-LAN-IP>:8907/dragon/gm.html`
- Quick LAN IP on macOS: `ipconfig getifaddr en0 || ipconfig getifaddr en1`

**Do not** open `index.html` with VS Code Live Server, Live Preview, or `file://`. The game needs the math-quiz dev server on port **8907** so it can load your learner file (`/api/latest-user-db`), save quiz bursts, and sync with the Game Master page. If you use the wrong server, the game shows a “Need the game server” screen with the correct URL.

## How to Play
1. Start the dev server (above), then open the game URL in a browser (Chrome works best).
2. Pick **Kid1** or **Randy** at startup. Kid1 loads her live `tlkids` file every time. Randy (and other testers) can **Continue my game** or **Clone Kid1's game** to copy her math file and dragon world save (boulders, signs, nest projects, story) for testing.
3. **Laptop:** click the screen to capture the mouse, then move with **W A S D**, look around with the mouse (Minecraft-style), and press **Space** to jump. **iPad / phone:** on-screen Minecraft-style touch pads appear — **Look** + **Jump** (lower left), **Move** (lower right); when you can interact with something, a **Tap** button shows too.
4. Walk to the egg in the nest and click it to start a math burst. Tap **Go!** when the keypad appears (the problem stays hidden until then), then answer with the keyboard; try to answer fast — speed affects fluency.
   During the quiz you have the same coach controls as the anchor math quiz: **Skip & flag**, **Flag previous**, **Pause**, **Quit & save**, and **Quit & abandon**. Wrong answers open a flag panel (reasons, comment, **Continue** / **Continue & insert**) instead of auto-advancing.
5. After each burst, a story scroll appears. Collect the beats; use the **📜 Story** button on the HUD to re-read your journal.
6. Watch the progress bar fill. At **60%** the egg hatches and you name your dragon. At **70%** Pipa grows into a juvenile dragon; at **80%** she becomes almost fully grown. Fire breath unlocks at **90%**, and the flight ride home at **100%**.
7. Follow sparkle trails to **Story Stones** in the meadow, hills, and grove. Click a stone when you arrive to play that leg of the story.
8. 🌋 **Mount Ember challenge** (starts with a letter at login): the mountains are real now — walk up any of them. Five boulders block the climb up the smoking volcano to the north; do a quiz at each one to smash it (just finish the quiz — no score needed), then climb to the lava pool at the very top for a surprise.
9. 🔥 **Lava defense** (starts on your next login after finding the egg): Mount Ember erupts — five lava streams race toward the nest on parallel paths. Click each glowing tip and finish a quiz to cool that stream (lava pauses while you quiz). Hurry before it reaches the nest!
10. 💎 **Dragon Gems**: every quiz earns gems (extra for correct answers and finishing). As gems pile up, the nest grows on its own — flower garden, string lights, banner flags, a fountain, and a golden dragon statue.
11. 🎁 **Daily gift**: on the first login each day a balloon crate lands near the nest — click it for bonus gems and a note.
12. 🐉 **Play with your dragon** (after the hatch): stand close and press **F** to pet it; **1–4** perform unlocked tricks (play, wing-stretch, jump, fire breath).
13. 🗺️ **Map button** on the HUD opens The Road Home — every stop on the journey to Mount Ember, with "you are here" and the next nest upgrade.
14. 🪧 **Nest projects** (after the egg is found): five clickable quiz stations around the nest. Two wooden **signs** (one by the meadow path, one by the grove path) — finish a quiz at a sign and you get to paint ANY words on it, and you can redo a quiz to change them whenever you like. The **dry fountain**, the **nest**, and the **trees** each grow through three levels, one level per finished quiz — running water, second tier, and a rainbow for the fountain; cushions, a canopy, and golden straw for the nest; blossoms, fruit, and lanterns for the trees.

Hard refresh always opens **Who's playing?** (Kid1 / Randy — buttons show friendly names from local config when set). Sticky `?user=` is not kept in the address bar. Handoff **Take over here** reloads once with `?resume=1&user=…`, then clears those params.

## Private display names
Learner ids in code and saved files stay as **Kid1**, **Randy**, etc. When a kid's on-disk files still use an older name, map the code id to that local name in **`dragon/data/display_names.json`** (gitignored; local-files mount via `scripts/local_files_mounts.txt`). Example: `"Kid1": "Kid1"` shows **Kid1** on screen and resolves math / dragon saves on disk. The dev server auto-creates the file from `display_names.example.json` the first time it is needed; edit the values locally — nothing to copy between machines beyond normal `_LOCAL_FILES` sync.

## Mobile / desktop handoff (LAN only)
One device owns the game at a time. The dev server keeps a checkpoint under `_data/<folder>/dragon-sync/` (world state, camera pose, and an unopened quiz waiting at **Go!**).

**First time after this update:** open the game once on the **desktop/laptop** so your existing browser save becomes the server checkpoint.

**Hand off to iPad/phone:**
1. On the laptop, tap **Transfer to mobile** on the HUD, or start a quiz and use **Transfer to mobile** under **Go!** (there is also **Cancel quiz** to leave without answering).
2. The laptop shows a **Transferred** screen — play stops there (**Take over here** stays on this side only, for recovery).
3. On the iPad (same learner open, or hard refresh → pick the learner): the transfer is **claimed automatically** — no confirmation. A Go! quiz transfers with it when you sent one.

**Hand back to laptop:** on the iPad, **Transfer to desktop**. The laptop’s Transferred screen auto-picks it up (or hard refresh → Who's playing → same learner). Ordinary hard refresh does **not** reopen a Go quiz by itself unless a transfer is waiting to claim.

**After a quiz on mobile:** a **Transfer to desktop** button appears so you can hand the game back without digging through the HUD.

Requires the same dev server, same learner (`Kid1` / folder `tlkids`), and both devices on the same Wi-Fi. This is local-only — not for production deploy.

## Game Master (parent dashboard)
Open `gm.html` on your phone while on the same Wi-Fi. It shows real fluency %, current objective, story chapter, recent burst activity, and lets you send in-game letters (“From the Dragon Keeper”) that appear in the story overlay after the next quiz. Defaults to Kid1 / `tlkids`; use `?user=&folder=` to switch.

## Components
- **icons/favicon-dragon.svg** — browser tab icon (little purple baby dragon; shared with `gm.html`)
- **assets/models/** — Pipa life-stage GLBs (gitignored); auto-copied from content_studio approved on `dev_server.py` start — without them the game shows the old procedural purple blob
- **display_names.js** — loads local-only learner id → friendly name map for UI labels
- **display_names.example.json** — template for `data/display_names.json` (gitignored)
- **index.html / main.js** — game entry, player picker, burst loop, milestone reveals
- **quiz_bridge.js** — loads learner SQLite via dev server, runs Fluency Feast bursts, saves sessions
- **handoff.js** — cross-device checkpoint sync (`/api/dragon-handoff`), transfer UX, ownership polling
- **world_sync.js** — canonical full-world save to disk (`/api/dragon-world` → `_data/<folder>/dragon-world/`); mirrors localStorage gems/signs/nest so another computer on the same server loads the same game
- **device.js** — shared touch vs desktop detection for controls and handoff targets
- **sim/** — game state, milestones, story engine (`story.js`, `story_content.js`), burst session, GM snapshot, nest quiz stations (`stations.js`), lava defense (`lava_quest.js`)
- **world/** — Three.js scene, controls, egg, dragon, environment, ambient life, journey/story stones, flight, climbable mountains (`mountains.js`), volcano boulder blockades (`boulders.js`), lava streams (`lava_streams.js`), gem-grown nest upgrades (`homestead.js`), wildlife (`critters.js`), writable signs + growable nest/trees (`nest_stations.js`)
- **ui/** — HUD, quiz overlay, story overlay, how-to card, Road Home map (`map_overlay.js`), sign-writing dialog (`sign_overlay.js`)
- **gm.html / gm.js** — Game Master phone dashboard
- **audio/** — Kenney UI sounds + Web Audio fallbacks (see `ASSETS.md`)

## Tech stack
Vanilla ES modules + Three.js (CDN, no build step). Shares `math_utils.js` and `fluency_core.js` with the rest of math-quiz. Requires the repo venv dev server for persistence and GM APIs.

## Tests
From repo root: `node --test apps/math-quiz/tests/dragon*.test.mjs` (story engine, GM state, handoff hydration, playthrough smoke). Handoff server store: `cd apps/math-quiz && python3 -m unittest tools.test_dragon_handoff_store`. E2E handoff (mocked API): `cd apps/math-quiz/tests && npm run test:e2e -- e2e/dragon_handoff.spec.mjs`. Full playthrough apparatus: see `playtests/README.md`.

## Branch
The integration line is `feature/math-quiz-dragon-baby`. Its completed sub-branches are merged and deleted locally and on the remote:
- `feature/math-quiz-app-tuning` — [PR #35](https://github.com/FocusOnFoundationsNonprofit/fof-mono/pull/35) (squash: anchor clone workflow, app-wide fluency percent, favicons)
- `feature/dragon-baby-story-world` — [PR #40](https://github.com/FocusOnFoundationsNonprofit/fof-mono/pull/40) (story world, Game Master, living world)
- `feature/dragon-baby-richer-world` — [PR #45](https://github.com/FocusOnFoundationsNonprofit/fof-mono/pull/45) (Dragon Gems, daily gift, dragon play, Road Home map)
- `feature/dragon-baby-nest-quiz-stations` — [PR #47](https://github.com/FocusOnFoundationsNonprofit/fof-mono/pull/47) (writable signs, growable fountain/nest/trees)

See `docs/2026-07-05_story-world-gm-plan.md` for the original feature plan.
