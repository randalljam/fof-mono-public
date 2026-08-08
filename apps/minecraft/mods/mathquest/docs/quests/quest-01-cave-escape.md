file: apps/minecraft/mods/mathquest/docs/quests/quest-01-cave-escape.md
title: Quest 01 — Cave Escape (Kid1, single-digit addition fluency)
last-updated: 2026-06-27
ai: Cursor - Composer 2.5 Fast
session: Quest spec — Cave Escape rename, mechanics framework, world config

**Quest 01 — Cave Escape**

Specification for the first MathQuest story quest: hundreds of addition practice sessions woven into an underground escape adventure. This document captures math progression, named **game+quiz mechanics**, data contracts, tunable parameters, the **Quest control panel** (live Game Master UI), **event triggers**, **world config inputs**, and **dynamic story/content delivery**. Finale location and surface reveal are **intentionally omitted** from player-facing naming — surprises stay in-world, not in spec titles.


## Purpose and audience
This file is the handoff spec for an implementation agent building quest mechanics on top of the current MathQuest mod and Math Quiz data layer.
Read first:
- `apps/minecraft/mods/mathquest/docs/PROBLEM_SOURCES_AND_SESSION_INTEGRATION.md` — how quizzes run, export, and ingest.
- `apps/minecraft/mods/mathquest/docs/SQLITE_SCHEMA_REFERENCE.md` — SQLite shapes and append rules.
- `apps/math-quiz/single_digit_addition_categorization.md` — addition category definitions (canonical problem lists).
- `apps/math-quiz/docs/SPEC.md` — fluency rubric and segmentation model (baseline; this quest may override thresholds).
Out of scope for this document: AWS deploy, written-column arithmetic.


## Quest summary
| Field | Value |
| --- | --- |
| Quest id | `quest1-caveescape` |
| Quest display name | **Cave Escape** |
| Learner | **Kid1** (real name in Math Quiz / SQLite) |
| Minecraft player | **WildPetal** (default mapping; confirm at runtime) |
| Operation | Single-digit addition (`+`) |
| Primary goal | Hundreds of quiz sessions that build fluency while feeling like one integrated adventure |
| Spatial arc | Spawn in a **dark underground cave** → progress through milestones → **emerge to surface** (finale biome is a surprise — not named in UI or docs shown to player) |
| Math arc | Demonstrate category fluency in easy buckets first, then segment and conquer **Tough 21** individually |
| Session volume | High — design for **many** short-to-medium quizzes, not a single gate exam |
| Build priority | **Autonomous end-to-end first** — full quest runnable with implementer-chosen defaults; all story text, music paths, and cues **exposed and editable** on Quest panel for GM override |


## Design intent
- **Practice and story are integrated.** Math is not a sidebar; milestones unlock narrative/world progression.
- **Fluency, not mere accuracy.** Success means knowing facts cold (speed + correctness), aligned with Math Quiz's fluency principle but with quest-specific thresholds where noted.
- **Reuse existing plumbing.** All quizzes happen in Minecraft via MathQuest; each completed session exports to SQLite and appends into Kid1's quest learner file.
- **Fresh learner file per quest run.** Auto-created on quest start — do **not** append into prior Kid1 fluency files.
- **Tunable knobs live in the Quest panel.** Mix percentages, fluency thresholds, mechanics params, world locations — all editable live.
- **Dynamic story, not jar updates.** Narrative beats (text, pop-ups, TTS, music) are authored and triggered from the operator side at runtime.
- **Autonomous with optional GM.** Target: Kid1 can play through with zero operator clicks; GM can monitor, edit content files, and override anything in real time (also the dev workflow).
- **Named reusable mechanics.** Combat gates, explore-button gates, and quiz success modes are a **framework** — parameterized instances, not one-offs.
- **Preserve surprises.** Do not put finale biome or plot twists in quest titles, panel headers shown to player, or early story cues.


## World configuration (operator inputs — TBD values OK at build time)
Quest 01 assumes Randy has already loaded the desired local Minecraft world on the server. The quest does **not** create, switch, or regenerate worlds from a seed. Spawn and all beat locations are inputs, not hard-coded.
### World config file
Store world inputs in a **hot-reloadable file** the Quest panel reads and writes, e.g.:
```text
<sharedDataDir>/quests/quest1-caveescape/world.json
```
(or equivalent under `mathquest-server/config` — implementer picks path; document it).
Suggested shape:
```json
{
  "spawn": { "x": 1375, "y": -18, "z": 1311, "label": "Start" },
  "locations": {
    "m1_cave_start": { "x": 1375, "y": -18, "z": 1311, "label": "Start" },
    "m2_deep_passage": { "x": 1378, "y": -13, "z": 1312, "label": "Deep passage" },
    "m3_winding_tunnel": { "label": "Winding tunnel" },
    "m4_chamber": { "label": "Chamber" },
    "m5_connector": { "label": "Connector" },
    "m6_surface_break": { "x": 1401, "y": 86, "z": 1293, "label": "Breakthrough" }
  }
}
```
- **`spawn`** — player intended spawn (dark cave).
- **`locations`** — named sites for triggers, mechanics, and milestone hooks; extensible map (implementer adds keys as beats are built).
- Operator may keep a **master copy** elsewhere and copy into this path; panel should also edit fields directly and save back to file.

### Quest panel — milestone coordinates
Expose coordinates inside each milestone card:
- Location label
- One Minecraft-style coordinate text box: `x y z`
- Intermediate milestones may stay blank until discovered
- The `m1_cave_start` coordinates also define the quest spawn point
- `Save Version` writes a timestamped setup snapshot containing both `quest.json` and `world.json`
- Validation: warn when null coords but allow save (build phase); block autonomous world triggers only when coords missing

**Assumption:** Math milestone progression works without coordinates; location-bound mechanics stay dormant until coords are set.

### Quest panel — command and action execution
The Quest panel is both builder and executor:
- Command runner: runs normal Minecraft commands from the local server, supports
  `{player}`, `{real}`, and `{milestone}` placeholders, and uses server-backed
  command suggestions. The command box also accepts custom quest actions such as
  `clear_inventory` and `start_quiz`; Tab accepts the first available suggestion.
- Run log: every quest action writes a verbose server-thread info log entry and
  appends the same structured result to the Quest panel Run box. **Clear Log**
  clears this persisted panel log without changing quest progress.
- Start Fresh Run: creates the quest run and runs the M1 `startActions` bundle.
- Continue Current Run: reruns the current milestone's `startActions` without
  incrementing the try number.
- Restore Player: restores the latest player safety backup for the selected
  learner.
- Milestone cards: edit and run `startActions` and `endActions`, one action per
  line.
- Milestone buttons: **Set Current** changes milestone status, **Run Start** runs
  `startActions`, and **Run End** runs `endActions`.

Supported action lines: `teleport <locationId>`, `teleport x y z`,
`clear_inventory`, `restore_player`, `start_quiz`, `open_quiz`,
`open_quiz_invitation`, `title <text>`, `chat <text>`,
`wait <seconds>` / `delay <seconds>`, `audio <registered_sound_id>`,
`music <registered_sound_id>`, and vanilla command lines. `clear_inventory`
switches the learner to survival before clearing carried inventory, armor, and
offhand.

Before the M1 start bundle can clear inventory or teleport, MathQuest writes a
local backup of the selected player's location, carried inventory, armor, offhand,
selected slot, health, food, saturation, XP level, total XP, XP progress, and game
mode. Ender chest contents are not cleared or restored by this quest-start flow.
Starting a fresh run also removes any Wandering Nerds assigned to the learner,
and timed Wandering Nerd auto-spawn skips active Quest 01 learners.

Default M1 start actions:

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

After the invitation chat, the learner sees **Accept** and **Decline**
buttons. **Accept** closes the invitation and opens the embedded first quest quiz
payload locally, while also sending the accept response back to the server for
logging and retry cleanup. **Decline** closes the prompt with no other effect;
after **22 seconds** the chat and invitation buttons repeat until the learner
accepts.

Default M1 end actions:

```text
give {player} minecraft:torch 1
title Let there be light.
```

Death behavior for the active learner:
- `gamerule keepInventory true` is set by the M1 start bundle.
- If the learner dies, respawn handling returns them to the current milestone
  coordinates.
- There is no separate vanilla `keepLevel` game rule in this target; XP is backed
  up/restored, and `keepInventory` is the in-world loss-prevention setting.


## Player identity and data setup
### Identity
| Role | Value |
| --- | --- |
| Minecraft username | `WildPetal` |
| Real learner name (SQLite `Users.name`) | `Kid1` |
Confirm `playerRealNames` in `mathquest.json` if the control panel overrides defaults.

### Quest SQLite file (auto-created on quest start)
**Decision:** On quest instance start, automatically create a dedicated multi-session learner file.
| Field | Rule |
| --- | --- |
| Pattern | `quest1_try{N}_K1_{YYYY-MM-DD}.sqlite` |
| Example | `quest1_try1_K1_2026-06-27.sqlite` |
| Directory | `apps/math-quiz/_data/tlkids` (default `mathQuizActiveDir`) |
| `try` number | Integer per quest id + learner; default `1`, increment when operator starts a new run (panel control) |
| Date stamp | Quest **start date** (local) |
| Do not use | Any pre-existing `math-flu_K1_*.sqlite` from prior non-quest work |
**Implementation:** Quest engine passes explicit `active_sqlite_path` to ingest so `--match-any-prefix` does not pick the wrong file. Panel displays current path; GM can start `try2`, etc.
**Rationale:** Clean baseline per run; filename encodes quest id and attempt.

### What gets recorded per quiz
Each MathQuest completion already writes:
1. Raw single-session export → `_data/_single-session-sqlite-files/mathquest_K1_*.sqlite`
2. Append into quest active file → `ProblemAttempts`, `Sessions`, `ModeEvents`
Quest logic reads fluency from accumulated `ProblemAttempts`. Fluency status is computed, not stored in schema today.


## Game + quiz mechanics framework
Implement a **reusable mechanics layer** — named mechanic types with typed parameters, bindable to triggers and milestones. Quest 01 uses at least the two below; framework should allow adding more without jar changes.

### Quiz success modes (attach to any mechanic that opens a quiz)
| Mode id | Name | Behavior | Player can "fail"? |
| --- | --- | --- | --- |
| `mastery_loop` | **Open-ended mastery** | Quiz repeats until success predicate met (e.g. X fast correct, category demonstration). Player may stop/leave — counts as **abandon**, gate stays unresolved. | No hard fail while continuing; abandon = unresolved |
| `fixed_pass_fail` | **Fixed session pass/fail** | Bounded quiz (N problems). Predicate evaluated at end — can **fail after completing all questions** (e.g. did not demonstrate fluency in window). | Yes — explicit fail |
Parameters shared across modes where applicable: `problemsPerQuiz`, `success_predicate` (reference fluency rules), `max_attempts` (optional cap even in mastery loop).

### Mechanic: `combat_quiz_gate`
**Pattern:** Defeat mob → quiz opens → success keeps mob dead; failure or abandon → mob **respawns** after delay.
| Parameter | Description |
| --- | --- |
| `mob_type` | Entity id (e.g. `zombie`, `cave_spider`) |
| `spawn_x/y/z` or `spawn_location_key` | From world config |
| `respawn_seconds` | Delay before respawn if quiz not satisfied (e.g. 60) |
| `respawn_radius` | Horizontal spawn scatter around spawn point |
| `quiz_success_mode` | `mastery_loop` or `fixed_pass_fail` |
| `success_predicate` | e.g. N answers under `greenMs`, or category demo |
| `problems_per_quiz` | Override for this gate |
**Flow:** `mob_killed` → open quiz → on success predicate: mark gate cleared, mob stays dead; else schedule respawn at radius after `respawn_seconds`.
**In scope for v1:** Include this mechanic in framework; Cave Escape uses at least one instance (implementer places per world config).

### Mechanic: `explore_button_gate`
**Pattern:** Player must find and activate a hidden **button / lever / pressure plate** → quiz opens. Exploration failure = never finds button; quiz abandonment = unresolved gate.
| Parameter | Description |
| --- | --- |
| `interact_x/y/z` or `location_key` | Block position from world config |
| `block_type` | Expected block (button, lever, …) |
| `hint_cue_id` | Optional story cue when player enters nearby region |
| `quiz_success_mode` | `mastery_loop` or `fixed_pass_fail` |
| `success_predicate` | Same family as combat gate |
| `problems_per_quiz` | Override for this gate |
**Flow:** `world_interact` at registered coords → open quiz → success clears gate (e.g. opens passage, grants reward cue).

### Mechanic registry on Quest panel
- List active mechanic **instances** (id, type, status, bound location).
- Expand instance → edit all parameters above.
- GM: force-clear gate, force-respawn mob, manually open gate quiz.
- Autonomous: mechanics run from config defaults when coords + params are set.

### Milestone math vs gate quizzes
**Milestone progression** (M1–M6) remains driven by **accumulated SQLite fluency** across many sessions — not by a single gate quiz pass/fail.
**Gate quizzes** (combat, button, NPC) are **local beats** that unlock world/story; they use the success modes above per instance.


## Problem taxonomy
Canonical categories follow `apps/math-quiz/single_digit_addition_categorization.md`.
M1 and M2 are explicit quest overrides: they track fixed/oriented facts, so
`0+7` and `7+0` are separate required demonstrations in M1, and `2+7` and
`7+2` are separate required demonstrations in M2. Later milestones use canonical
orientation (`smaller + larger`) for classification and targeting.
| Category | Count | Quest grouping |
| --- | ---: | --- |
| M1 Zero/One oriented fixed set | 36 | Milestone 1 |
| M2 Add Two + Doubles fixed set | 21 | Milestone 2 |
| Tough 21 | 21 | Milestones 3–6 (per-fact fluency) |
| Hardest Six | 6 (subset of Tough 21) | Named subset only; milestones count against full Tough 21 |
**Implementation note:** active quest learners use quest-owned standard arithmetic
problem payloads. The normal MathQuest panel quiz type, internal source, range,
problem-count controls, and item reward settings are not consulted for the active
quest quiz. Quest item rewards are delivered by quest logic and action bundles.
Quest quiz payloads also carry display options, so quest quizzes use a stripped
keypad without flag buttons, quit buttons, progress text, or source labels while
normal MathQuest quizzes keep the full interface.


## Fluency criteria
### Baseline (Math Quiz SPEC)
Default rubric: red → yellow → green → blue, with speed thresholds (`greenMs`, `redMs`) and accuracy floor (`minAccuracy`). See `apps/math-quiz/docs/SPEC.md` §3–§4.
Segmentation engine: `apps/math-quiz/engine/addition_segmentation.mjs`.

### Quest-specific overrides (allowed)
This quest **may use different fluency criteria** than the Math Quiz web app defaults — especially fixed gates (M1–M2), per-fact Tough 21 classification, and child-appropriate speed bars.
Expose on Quest panel; used by milestone engine **and** gate `success_predicate` when configured to reference them.
**M1 fixed quiz predicate:** each required oriented zero/one problem must have at
least one correct answer at or below `fluencyMs` (default `2000` ms). The fixed
set is `0+n`, `n+0`, `1+n`, and `n+1` for `n=0..9`, with duplicate orientations
stored once.
**M2 fixed quiz predicate:** each required problem must have two consecutive
correct answers at or below `fluencyMs` (default `2000` ms). The fixed set is
`2+n` and `n+2` for `n=3..9`, plus `n+n` for `n=3..9`.
**"Demonstration of fluency" (later category level):** implement as configurable predicate (exact formula: implementer default, GM tunes).
**Per-fact fluency (Tough 21):** fact is **fluent** when per-fact predicate met; M3–M6 count fluent Tough 21 facts.


## Event triggers
Quest beats are fired by **triggers** → **actions**. Implementer binds per beat; all types data-driven from Quest panel / config files.
### Trigger types
- **`milestone_reached`** / **`milestone_progress`**
- **`quiz_completed`** / **`quiz_success_predicate`**
- **`location_enter`** / **`location_exit`** — uses `world.json` named locations
- **`world_interact`** — button/lever (explore_button_gate)
- **`npc_interact`**
- **`mob_killed`** — combat_quiz_gate
- **`mechanic_gate_cleared`** — generic follow-up when any gate succeeds
- **`gm_manual`**
- **`quest_start`**

### Design notes
- Triggers and mechanics configs are **file-backed + panel-editable**; no jar rebuild.
- GM manual must fire any automated action.
- Server-authoritative in dedicated-server mode.


## Milestone model
Milestones are sequential. Completing a milestone triggers reward/unlock/story beats (see Content delivery).
**Panel status:** `locked` | `active` | `complete`. One `active` milestone at a time.

### Milestone summary
- **`m1` — Cave Start — Zeros & Ones**
  - Math: fixed oriented zero/one set (36 required problems)
  - Progress: fluent oriented problems / 36
  - Exit: every required oriented problem has at least one correct answer under `fluencyMs`
  - Quiz behavior: one mastery-loop quiz repeats wrong/slow facts until all 36 are fluent
- **`m2` — Deep Passage — Twos & Doubles**
  - Math: fixed Add Two + Doubles set (21 required problems)
  - Progress: fluent fixed problems / 21
  - Exit: every required M2 problem has two consecutive correct answers under `fluencyMs`
  - Quiz behavior: seven-question batches; rewards one deepslate block per answer correct under `fluencyMs`
- **`m3` — Winding Tunnel — 10 Tough Facts**
  - Math: Tough 21 segmentation → targeted mix
  - Progress: min(fluent tough21, 10) / 10; secondary: facts classified / 21 in Phase A
  - Exit: ≥ 10 of 21 Tough 21 fluent
- **`m4` — Chamber — 15 Tough Facts**
  - Progress: min(fluent tough21, 15) / 15 — Exit: ≥ 15 fluent
- **`m5` — Connector — 18 Tough Facts**
  - Progress: min(fluent tough21, 18) / 18 — Exit: ≥ 18 fluent
- **`m6` — Surface Break — All Tough Facts**
  - Progress: fluent tough21 / 21 — Exit: 21 of 21 (quest complete; finale reveal is in-world surprise)

```
M1 → M2 → M3 (segment) → M3–M6 (targeted mix) → complete
```

### Milestone 1 — Add Zero + Add One
**Goal:** Demonstrate fluency across both directions of Add Zero and Add One.
**Quiz content:** Fixed standard-arithmetic list: `0+n`, `n+0`, `1+n`, and `n+1` for `n=0..9`.
**Exit:** every required oriented problem has at least one correct answer at or below `fluencyMs`.

### Milestone 2 — Add Two + Doubles
**Goal:** Add Two in both directions for 3 through 9, plus doubles 3 through 9.
**Quiz content:** Fixed standard-arithmetic list: `2+n` and `n+2` for `n=3..9`,
plus `n+n` for `n=3..9`.
**Trigger:** after the learner breaks three blocks in M2, a vanilla chime plays
and the M2 quiz invitation opens.
**Batch loop:** each accepted quiz contains seven questions from remaining
non-fluent M2 facts, with already-fluent facts used as fillers if needed.
**Reward:** one `minecraft:deepslate` block for each answer correct at or below
`fluencyMs`. When those deepslate blocks are gone from inventory and M2 remains
active, the next M2 invitation opens.
**Exit:** every required M2 problem has two consecutive correct answers at or
below `fluencyMs`.

### Milestones 3–6 — Tough 21
**Phase A:** segment all 21 facts (sticky vs fluent).
**Phase B:** targeted mix 50% sticky / 25% fluent tough / 25% easy review.
Thresholds: M3=10, M4=15, M5=18, M6=21 fluent facts.


## Quiz session shape
Prefer **`internal_problem_list`** for milestone mixes (`ProblemListItems.category` + `notes`); **`generated`** fallback if list empty.
Quest panel refreshes lists from milestone rules + SQLite (recommended: after each ingested session).


## Problem delivery state machine (implementation sketch)
```
START → auto-create quest1_tryN_K1_DATE.sqlite
  → M1 → M2 → M3 segment → M3–M6 targeted mix → M6 complete
```
Quest state owned by Quest panel backend (`sharedDataDir`); SQLite holds raw attempts.


## Quest control panel (Game Master page)
### Role in the control-panel family
| Page | URL (default) | Role |
| --- | --- | --- |
| **MathQuest panel** | `http://127.0.0.1:8765/` | Per-player quiz, NPC, rewards |
| **Mob spawn panel** | `http://127.0.0.1:8765/mob-spawn.html` | Staged encounters |
| **Quest panel** | `http://127.0.0.1:8765/quest.html` (proposed) | **Cave Escape** — milestones, mechanics, world, content |
Dungeon-master surface: monitor Kid1, tune params, edit **text and music file paths**, bind triggers, override automation — no jar rebuild.

### Build priority (confirmed)
1. **Autonomous path** — implementer wires default cue stacks, mechanics instances, and milestone automation so a full run works hands-off.
2. **Expose all content for editing** — story text, TTS source lines, music bed/cue **file paths or URLs**, world.json fields, mechanic params — visible and editable on panel (and underlying files).
3. **GM overrides** — same fields live-tweakable during play.

### Layout (conceptual)
```
┌─────────────────────────────────────────────────────────────┐
│ Cave Escape (quest1-caveescape)            [Kid1 / WildPetal]│
│ Active: M2 — Deep Passage…                 Overall: 34%      │
├─────────────────────────────────────────────────────────────┤
│ Run: player select + quiz params + Save Version                  │
│ ▼ M1 … ✓ 100%  ▶ M2 … ● 67% (expanded)  ▶ M3–M6 …            │
│ Mechanics instances │ Content cues (text/audio paths)         │
│ Global params │ GM actions                                    │
└─────────────────────────────────────────────────────────────┘
```

### Milestone sections (collapsible)
- Header: display name, status, **percent complete**, progress basis one-liner.
- Body: milestone params, story cue ids + **editable text/audio paths**, mechanic bindings.
- **Default:** active milestone expanded.

### Content editing on panel
For each cue / milestone beat, expose:
- Plain **story text** (chat, popup, TTS source)
- **TTS clip path or URL** (OGG after generation)
- **Music bed / cue path or URL**
- **Generate TTS** button (calls operator-side tooling)
Autonomous mode plays whatever paths are configured; GM edits paths or text without redeploy.

### Parameters by scope
**Global:** `fluencyMs`, `greenMs`, `redMs`, `minAccuracy`, `problemsPerQuiz`, `active_sqlite_path`, `quest_try_number`, `autonomous_mode`
**Locations:** milestone cards write to `world.json` fields (see World configuration)
**M1 / M2:** fixed quest quiz sets. **M3–M6:** as in prior spec (tough mix percents, thresholds, etc.)
**Per mechanic instance:** see Game + quiz mechanics framework


## Content delivery (story, audio, rewards)
Multimodal, operator-driven; milestone auto-fires default cue stacks in autonomous mode.
### Modalities
**Chat line**, **title/action bar**, **screen popup**, **TTS clip**, **sound sting**, **background music bed**, **music cue**, **world reward**, **item reward**.
### Dynamic delivery
Content **not** baked in jar. Panel + files authoritative; client fetches OGG/audio by URL/path (see `docs/2026-06-27_game-brainstorm.md`).
### Story hooks (structure only — no finale spoilers)
| Beat | Notes |
| --- | --- |
| Quest start | Cave spawn; welcome TTS + chat + ambient bed |
| M1–M5 complete | Passage/world rewards + cues (operator-authored) |
| M6 complete | Surface emergence at `finale_emergence` location; celebration cues — **biome/details are surprise** |


## Integration constraints (current mod)
| Capability | Status |
| --- | --- |
| Quiz UI, session export/ingest | Implemented |
| Quest panel, mechanics framework, world.json | **Not implemented** |
| Dynamic TTS/music playback | **Not implemented** |
| combat_quiz_gate / explore_button_gate | **Not implemented** |
Implement: Quest panel + autonomous automation + exposed content files first; gate mechanics as framework primitives early (combat + button called out for v1).


## Tunable parameters summary
| Key | Default | Panel location |
| --- | --- | --- |
| `fluencyMs` | 2000 | Global; M1/M2 fixed quest quizzes |
| `greenMs` | 3500 (later milestones; mirrored from `fluencyMs` in current panel) | Global |
| `problemsPerQuiz` | 7–10 (TBD) | Global |
| `active_sqlite_path` | auto `quest1_try1_K1_DATE.sqlite` | Global (read-only display + new try) |
| `quest_try_number` | 1 | Global |
| `autonomous_mode` | on | Global |
| `tough_*_pct`, `m3`–`m6` thresholds | see Milestone model | M3–M6 |
| Mechanic instance params | per instance | Mechanics registry |
| Milestone locations | start/deep passage/breakthrough set; middle blank until discovered | Milestone cards / `world.json` |


## Open questions (implementer defaults OK)
1. Category demonstration formula for M3-M6 — propose default.
2. `world.json` exact path and schema versioning.
3. Client audio player approach (OGG via URL).
4. Concrete default cue ids and stub text — implementer seeds; operator replaces via panel.


## Handoff note
**Ready for advanced implementation agent.** Build **autonomous Cave Escape** with implementer defaults; expose text, music, world locations, and mechanics on Quest panel. Operator loads the desired world separately and supplies locations via file + panel when ready. Keep finale surprise out of player-facing strings.


## Related files
| File | Role |
| --- | --- |
| `apps/minecraft/mods/mathquest/docs/quests/quest-01-cave-escape.md` | This spec |
| `apps/minecraft/mods/mathquest/docs/CONTROL_PANEL.md` | Existing panels |
| `apps/minecraft/mods/mathquest/docs/2026-06-27_game-brainstorm.md` | Combat quiz, TTS/audio |
| `apps/voice/tts.py` | Operator TTS |
| `apps/math-quiz/engine/addition_segmentation.mjs` | Category lookup |
