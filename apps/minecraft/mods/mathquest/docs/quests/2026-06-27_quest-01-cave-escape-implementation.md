file: apps/minecraft/mods/mathquest/docs/quests/2026-06-27_quest-01-cave-escape-implementation.md
title: Quest 01 Cave Escape — implementation status and runbook
last-updated: 2026-06-27
ai: Codex - GPT-5
session: Quest 01 Cave Escape implementation


## Purpose
This document describes the implemented Quest 01 Cave Escape system in MathQuest.
The design spec remains `apps/minecraft/mods/mathquest/docs/quests/quest-01-cave-escape.md`;
this file is the practical runbook for the code that exists now.


## URLs
When the MathQuest local control panel server is running:

```text
http://127.0.0.1:8765/quest.html
```

The existing panels link to it:

- MathQuest player/NPC panel: `http://127.0.0.1:8765/`
- Mob Spawn panel: `http://127.0.0.1:8765/mob-spawn.html`


## Hot Reload
The Quest page is a normal control-panel static asset. If `controlPanelAssetsDir`
points at:

```text
apps/minecraft/mods/mathquest/fabric/src/main/resources/assets/mathquest
```

then edits to `quest.html`, `quest.js`, and `control-panel.css` can be tested with
a browser refresh. Java changes still require rebuilding/redeploying the jar and
restarting the Minecraft server.


## File-Backed Quest State
Quest state is stored under the configured MathQuest `sharedDataDir`:

```text
<sharedDataDir>/quests/quest1-caveescape/
```

Files:

- `quest.json` — learner identity, active run, quiz parameters, milestone text,
  story/content cues, milestone start/end actions, mechanic definitions, status
- `world.json` — spawn point and named quest locations for the currently loaded server world
- `versions/*.json` — timestamped setup snapshots created by the Quest panel
  `Save Version` button
- `backups/*.json` — per-player safety backups written before quest start
  actions clear inventory or teleport the selected learner

The panel reads/writes both files through the embedded local server. The files are
not source files and should not be committed.

Current known coordinates:

| Name | Coordinates | Storage |
| --- | --- | --- |
| Start | `1375 -18 1311` | `world.json` `spawn` and `locations.m1_cave_start` |
| Deep passage | `1378 -13 1312` | `world.json` `locations.m2_deep_passage` |
| Breakthrough | `1401 86 1293` | `world.json` `locations.m6_surface_break` |

M3-M5 coordinates remain blank until discovered. The panel edits milestone
coordinates as a single Minecraft-style `x y z` text box.

## Quest Action Bundles

Each milestone can define `startActions` and `endActions`, edited as one action
per line in the Quest panel. Blank lines and lines starting with `#` are ignored.
The panel can run either bundle for a milestone.

Supported action lines:

- `teleport <locationId>` or `teleport x y z`
- `clear_inventory` — switches the learner to survival, then clears carried
  inventory, armor, and offhand
- `restore_player`
- `start_quiz` — immediately starts the quest-selected quiz for the current
  learner
- `open_quiz` — opens the generic MathQuest offer flow
- `open_quiz_invitation` — shows Accept / Decline buttons for the Quest 01
  knowledge invitation; Accept starts the embedded quiz payload locally and
  reports the response to the server, Decline re-prompts after 22 seconds
- `title <text>`
- `chat <text>`
- `wait <seconds>` / `delay <seconds>` — schedules the remaining actions without
  blocking the server thread
- `audio <registered_sound_id>` / `music <registered_sound_id>` via vanilla
  `playsound`
- any normal Minecraft command, either as `/command ...`, `command ...`, or a
  raw command line

Command text supports `{player}`, `{real}`, and `{milestone}` placeholders.
The top Quest panel Command box runs the same action language immediately, so it
can run vanilla commands or custom actions such as `clear_inventory` and
`start_quiz`. Server-backed command suggestions populate as you type; Tab accepts
the first available suggestion.
Every quest action writes a verbose server-thread info log entry and appends the
same structured result to the Quest panel Run log. The Run box's **Clear Log**
button clears the persisted panel log without changing quest progress.

Milestone buttons:

- **Set Current** marks earlier milestones completed, this milestone active, and
  later milestones locked.
- **Run Start** runs that milestone's `startActions`.
- **Run End** runs that milestone's `endActions`.

`Start Fresh Run` runs the M1 start bundle after creating the quest run. Before
any M1 start actions execute, MathQuest backs up the selected player's location,
carried inventory, armor, offhand, selected slot, health, food, saturation, XP
level, total XP, XP progress, and game mode. The ender chest is intentionally left
untouched.

Starting a fresh run also removes any Wandering Nerds already assigned to the
learner. While the learner is in an active Quest 01 run, timed Wandering Nerd
auto-spawn skips that learner.

Default death behavior for an active Quest 01 learner:

- `gamerule keepInventory true` is set by the M1 start bundle.
- If the learner dies, the Fabric respawn event returns them to the current
  milestone coordinates.
- There is no separate vanilla `keepLevel` game rule in this target; the player
  backup/restore includes XP fields, and `keepInventory` is the in-world loss
  prevention setting used during the quest.

Default M1 start bundle:

```text
gamerule keepInventory true
gamemode survival {player}
teleport m1_cave_start
clear_inventory
title A rumble seals the cave behind you.
wait 20
chat In the well of darkness, you have been offered an invitation of knowledge. Do you accept?
open_quiz_invitation
```

The invitation flow:

1. After the 20-second wait, the chat line runs.
2. `open_quiz_invitation` opens a screen with **Accept** and **Decline**.
3. **Accept** closes the invitation and starts the embedded first quest quiz
   payload locally (skips the generic Math Quest offer screen). The client still
   sends an accept response back to the server for logging and retry cleanup.
4. **Decline** closes the screen; after **22 seconds** the chat and
   invitation repeat until the learner accepts.

While M1 is active, MathQuest periodically plays vanilla `minecraft:ambient.cave`
for the learner. This is a runtime vanilla `playsound`; local-only placeholder
OGG files live under `_assets/quest1/audio/` for later custom sound packaging.

Default M1 end bundle:

```text
give {player} minecraft:torch 1
title Let there be light.
```

Default M2-M6 start bundles are blank. The operator can define those actions
later from the Quest panel after the cave route and story beats are settled.


## Local-Only Assets
Large or generated quest media/art/source assets should be kept out of git under:

```text
apps/minecraft/mods/mathquest/_assets/
```

That folder is ignored by the repo. Do not commit large media files. Upload/S3
cataloging can be handled later when assets become canonical.

Current local-only placeholder audio files:

```text
apps/minecraft/mods/mathquest/_assets/quest1/audio/m1_well_ambience_loop_placeholder.ogg
apps/minecraft/mods/mathquest/_assets/quest1/audio/m2_third_block_chime_placeholder.ogg
```

These are not packaged into the jar yet; runtime currently uses vanilla
`minecraft:ambient.cave` and `minecraft:block.amethyst_block.chime`.


## Quest Run SQLite
Starting a fresh run creates an active target path in the configured
`mathQuizActiveDir`. The learner name is resolved from `playerRealNames`; if the
Minecraft username is not in the lookup, MathQuest uses the Minecraft username
itself:

```text
apps/math-quiz/_data/tlkids/quest1_try{N}_{resolvedName}_{YYYY-MM-DD}.sqlite
```

For the original Kid1/WildPetal quest run, that means a path such as:

```text
apps/math-quiz/_data/tlkids/quest1_try1_K1_2026-06-27.sqlite
```

MathQuest still writes raw single-session files to:

```text
apps/math-quiz/_data/_single-session-sqlite-files/
```

The ingest bridge now supports an exact `--active-file`. When Quest 01 is active,
completed sessions append to the exact quest file instead of matching the latest
`math-flu_<name>_*.sqlite` or any other non-quest learner file.


## Problem Generation
Quest 01 currently overrides the configured quest learner's problem source only
while a Quest 01 run is active. The default learner is WildPetal/Kid1, but the
Quest panel can target any player. Active quest quizzes always use standard
arithmetic addition; the normal MathQuest player quiz type, internal problem-list
source, range, problem-count settings, and configured item rewards are ignored
for the active quest learner. Quest item rewards are delivered through quest
logic and quest action bundles.

Milestone 1 uses a fixed, oriented problem set:

- `0+n` and `n+0` for `n=0..9`
- `1+n` and `n+1` for `n=0..9`
- Duplicate orientations such as `0+0` and `1+1` are stored once
- Total required M1 problems: 36

Milestone 2 uses a fixed, oriented Add Two + Doubles problem set:

- `2+n` and `n+2` for `n=3..9`
- `n+n` for `n=3..9`
- `2+2` is not included in M2 so this milestone stays centered on add-two
  directions plus doubles from 3 through 9
- Total required M2 problems: 21

Quest quiz launch sends the remaining non-fluent fixed facts for the active
milestone, shuffled on each launch. M1 uses a mastery loop inside the same quiz:
wrong answers and answers slower than `fluencyMs` are appended again until every
required M1 problem has at least one fast correct answer. If no fixed facts
remain, the milestone is complete and the next active milestone determines the
next quest quiz.

M2 launches seven-question batches. The batch is drawn from remaining non-fluent
M2 facts; if fewer than seven remain, already-fluent M2 facts fill the batch but
do not affect the remaining required set.

Milestones 3 through 6 still use the canonical single-digit addition taxonomy:

- Add Two: `2+n` from `2+2`, 8 canonical facts
- Doubles: `3+3` through `9+9`, 7 canonical facts
- Tough 21: all remaining non-double canonical facts from addends 3-9
- Hardest Six: subset of Tough 21 where both addends are 6 or higher

The later-milestone generator prioritizes non-fluent and low-attempt facts. It
randomizes orientation, so a canonical fact such as `3+7` may appear as `7+3`.


## Fluency Rule
Quest 01 computes fluency from the active quest SQLite file. A fact is currently
treated as fluent with milestone-specific rules.

For M1, each required fixed problem is fluent when:

- at least one correct answer exists
- that answer's response time is at or below `fluencyMs`

For M2, each required fixed problem is fluent when:

- it has two consecutive correct answers
- both answers are at or below `fluencyMs`

Default M1/M2 timing:

- `fluencyMs`: `2000`
- M1 `fastCorrectRequired`: `1`
- M2 `fastCorrectRequired`: `2`

For later canonical milestones, a canonical fact is fluent when:

- at least 2 attempts exist
- at least 2 correct answers were at or below `greenMs`
- overall accuracy for that fact is at least `minAccuracy`

Later-milestone defaults:

- `greenMs`: `3500`
- `redMs`: `7000`
- `minAccuracy`: `0.90`
- `problemsPerQuiz`: `7`

These are editable in the Quest panel and saved to `quest.json`.


## Milestones
The panel exposes all milestone names, status, story text, exit rules, and optional
audio/music paths.

Implemented milestone progression:

| Milestone | Completion rule |
| --- | --- |
| Cave Start | M1 fixed oriented zero/one facts fluent: 36 problems |
| Deep Passage | M2 fixed add-two/doubles facts fluent: 21 problems |
| Winding Tunnel | 10 Tough 21 facts fluent |
| Chamber | 15 Tough 21 facts fluent |
| Connector | 18 Tough 21 facts fluent |
| Surface Break | 21 Tough 21 facts fluent |

After each successful ingest into the quest active file, MathQuest recomputes
progress and updates milestone status in `quest.json`.


## M2 Block-Building Loop
M2 begins after M1 completion. The current implemented M2 runtime loop is:

1. The learner breaks blocks in the M2 area.
2. After the third block break, MathQuest plays vanilla
   `minecraft:block.amethyst_block.chime` and opens the M2 quiz invitation.
3. Accepting opens a seven-question M2 quest quiz.
4. After the quiz result is ingested, MathQuest gives one `minecraft:deepslate`
   block for each answer that was correct at or below `fluencyMs`.
5. When the learner has no `minecraft:deepslate` left in inventory and M2 is
   still active, MathQuest opens the next M2 quiz invitation.

The M2 invitation text is:

```text
Three stones have fallen. You can earn building blocks by learning the next building-block addition problems. Do you accept?
```

The title/subtitle is:

```text
Fast answers become the blocks beneath your feet.
```


## Mechanics
The current mechanics layer is intentionally simple and file-backed:

- `combat_quiz_gate` can spawn or clear the configured entity near its named
  world location.
- `explore_button_gate` can place or clear the configured block at its named
  world location.
- `open-mechanic-quiz` opens the current Quest 01 quiz for the configured learner
  if the player is online.

The Quest panel exposes mechanic id, label, type, location, entity/block id,
success mode, respawn delay, and current status.

Current GM buttons:

- `Open Quiz`
- `Force Clear`
- `Respawn`

Automatic trigger wiring is not complete yet. Mob death and block interaction do
not currently auto-open or auto-resolve gates. The panel provides working GM
controls and a reusable state/parameter layer for the next trigger pass.


## Creative Content
Initial story/content defaults are included in `quest.json` generation:

- quest start cave-in cue
- quiz offer cue
- milestone clear cue
- finale cue with the surface reveal intentionally unnamed

The Quest panel makes these editable as content cues with text, delivery mode,
audio path, and music path. Custom audio/TTS/music path playback is not
implemented yet; current runtime sound cues use vanilla `playsound`, and the
paths are preserved for future runtime playback.


## Verification
Known useful checks:

```bash
python3 apps/math-quiz/tools/test_session_ingest.py
cd apps/minecraft/mods/mathquest
./gradlew :targets:fabric-26.1.2:test
```

Build and deploy:

```bash
./apps/minecraft/mods/build-and-deploy.py mathquest
```


## Decisions Made
1. Quest state is file-backed JSON under `sharedDataDir`, not Java config.
   - Pro: editable at runtime and appropriate for per-world quest state.
   - Tradeoff: not version-controlled by default.

2. Quest sessions append by exact active SQLite path.
   - Pro: prevents accidental writes into normal Kid1 `math-flu` files.
   - Tradeoff: Quest start must happen before the first quest quiz if a dedicated
     active file is required.

3. Quest problem lists are generated in Java from the canonical category taxonomy.
   - Pro: no need to mutate Math Quiz problem-list tables during live play.
   - Tradeoff: the generated list is not currently visible as a `ProblemLists`
     row inside SQLite before the session is completed.

4. Fluency defaults are quest-specific.
   - Pro: makes the adventure tunable without changing the standalone Math Quiz
     app's rubric.
   - Tradeoff: Math Quiz analysis may use different fluency thresholds unless
     those are aligned later.

5. Mechanics currently support GM-driven world actions before full event triggers.
   - Pro: immediately playable and testable from the local panel.
   - Tradeoff: automatic mob-death/block-interaction progression remains a follow-up.

6. Large quest assets are local-only for now.
   - Pro: keeps git clean and avoids premature S3/catalog work.
   - Tradeoff: another machine will need those files copied or archived later.
