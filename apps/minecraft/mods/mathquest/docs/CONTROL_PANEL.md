file: apps/minecraft/mods/mathquest/docs/CONTROL_PANEL.md
title: MathQuest Local Web Control Panel
last-updated: 2026-07-16_1116
ai: Codex - GPT-5
session: `MathQuest TP credits`


## Purpose
The MathQuest local web control panel is a localhost-only browser interface for running a family MathQuest session from the dedicated Minecraft server on Randy's laptop. It is not deployed and does not need a cloud backend.
It is served directly by the MathQuest Fabric mod when the dedicated server is running. Default URL:
```bash
http://127.0.0.1:8765/
```
Quest 01 Cave Escape uses the same local server:
```bash
http://127.0.0.1:8765/quest.html
```


## Run It
Start the Minecraft dedicated server:
```bash
cd ~/Documents/Code/mathquest-server
/usr/local/opt/openjdk/bin/java -Xmx2G -jar fabric-server-launch.jar nogui
```
Open the control panel on the same laptop:
```bash
open http://127.0.0.1:8765/
```
Launch Minecraft from Prism with the matching MathQuest jar and connect through Multiplayer:
```text
localhost
```
The build dispatcher deploys the same jar to the Prism instance at:
```text
~/Library/Application Support/PrismLauncher/instances/Fabric 26.1.2 MathQuest/minecraft/mods
```
Other family devices on the home LAN connect to the laptop's LAN IP on the normal Minecraft port:
```text
<laptop-lan-ip>:25565
```


## Hot Reload UI Workflow
Most control-panel HTML, CSS, JavaScript, and NPC preview PNG edits can be tested without rebuilding the jar.

For active development, keep the Minecraft server running on `:8765`, then run the dev proxy from the repo root:
```bash
.venv/bin/python3 apps/minecraft/mods/mathquest/tools/control_panel_dev.py
```
Open the live-edit panel:
```text
http://127.0.0.1:8766/
```
The dev proxy serves static files from:
```text
apps/minecraft/mods/mathquest/fabric/src/main/resources/assets/mathquest
```
and proxies `/api/*` requests to the real embedded panel server at `http://127.0.0.1:8765`.

For the normal `:8765` panel to read files from disk, set `controlPanelAssetsDir` in the server's `mathquest.json` to the MathQuest asset root you edit, for example:
```json
"controlPanelAssetsDir": "/Users/randytrue/.codex/worktrees/0013/fof-mono/apps/minecraft/mods/mathquest/fabric/src/main/resources/assets/mathquest"
```
After one server restart with a jar that includes `controlPanelAssetsDir`, ordinary edits under that folder should apply with a browser refresh on `:8765`. The server log reports whether disk assets are active or whether it is falling back to bundled jar assets.

Still requires a jar rebuild/restart:
- New or changed Java API behavior
- Minecraft/game logic changes
- quiz payload or persistence behavior
- new Java config fields after this one
- NPC catalog defaults in Java


## Current Scope
The panel shows four player columns and each column can select from the known Minecraft players:
| Minecraft player | Real name |
|---|---|
| `rjcomp` | Randy |
| `TreasureHunterM` | K2 |
| `PumaJockey` | TL |
| `WildPetal` | Kid1 |
| `SkulkScraper` | Guest |
Each column can select one of those players, edit the displayed real name, choose the standard-arithmetic quiz source (including **Use internal fluency feast**), set that player's operation, range, problem count, quiz type, reward item/count, fluency-improvement reward item/count, configure TP-credit earning, choose the NPC, set spawn distance for the next spawn, lock the spawned NPC to that player, spawn the NPC, open the quiz directly, vanish that player's assigned NPC, and see current/last NPC status. Player-card edits autosave after a short debounce; there is no per-player Save button.
Real-name edits are saved to `mathquest.json` and are used for math-quiz internal-list lookup and for MathQuest single-session SQLite export filenames/user rows.
Each player card displays a prominent live **TP credits: N** balance. **Earn TP credits** is off by default, **Credits per quiz** defaults to 1, and **Reward choice** currently offers **Teleport (1 credit)**. The balance is display-only in the browser: completed quizzes add credits on the server, and successful in-game `/tpc`, `/tpt`, `/tpp`, `/tpr`, or `/tpw` commands spend them.

TP-credit earning is an alternative reward mode. While **Earn TP credits** is checked, completed quizzes do not also grant the standard or fluency **Reward item / Reward count**. Those item settings remain saved and become active again if TP-credit earning is unchecked. The built-in TreasureHunterM fallback for new or missing settings is polished deepslate ×1; explicit saved selections are preserved.

Delivered quizzes receive a player-bound, server-issued one-use token that becomes redeemable only after the result is processed, so incomplete quizzes and replayed completion packets cannot award. **Quit Quiz** saves answered work, cancels its token, and deliberately does not award TP credits. Config changes use a temporary file plus atomic replacement; if `mathquest.json` cannot be replaced, the in-memory balance mutation is rolled back and the player sees an explicit failure message.
The Quiz source selector has three choices:

- **Use internal quick quiz** (default): reads seven generated quick-practice problems for the selected operation from `QuickPracticeItems` in the learner's latest math-quiz SQLite file. Operation stays editable; Range and Problems stay visible but are disabled/gray.
- **Use internal problem list**: reads the first queued coach-authored list from `ProblemLists` / `ProblemListItems`. Operation, Range, and Problems stay visible but are disabled/gray because the queue supplies the exact problems.
- **Use settings below**: ignores internal SQLite problem rows and generates a quiz from Operation, Range, and Problems.
Reward item fields autocomplete vanilla Minecraft 26.1.2 item IDs without showing the `minecraft:` prefix, and also autocomplete known **reward group** names. If the Reward item or Fluency reward item value matches a group name, that field uses the group (with its mode). After blur or Enter, group selections display as `name (group)`. Otherwise the value is treated as a literal item. Typing part of an item name and pressing Tab completes the first matching item; autosaves normalize plain names like `diamond` to `minecraft:diamond`. Spawn NPC and Open Quiz also persist both standard and fluency reward selections before acting.
Below the NPC gallery, **Reward Groups** opens an editor for named groups. Each group has a name, a mode (**Give all**, **Give one at random**, or **Let player choose one**), and a list of item/count pairs. Save groups writes `rewardGroups` to `mathquest.json`.
Below the active NPC status, each player card also has a quick mob spawner: mob type, mob count, radius, and Spawn Mobs. Mob fields autocomplete living vanilla Minecraft 26.1.2 mob IDs without showing the `minecraft:` prefix. The server validates the selected entity is summonable before spawning.
For larger staged encounters, open the dedicated mob spawn page:
```text
http://127.0.0.1:8765/mob-spawn.html
```
That page can capture the current coordinates of an online player, let Randy edit the center point manually, preview point/circle/rim/line spawn shapes on a top-down planning canvas, queue several mob spawn entries, and trigger them together with Spawn All.
Use Player Location fetches fresh server status before copying coordinates, so it can be used while the player is moving without reloading the page. The mob spawn page also includes a Kill Area tool for clearing a selected mob type from a circle or square around the current center point.
The planning canvas uses reusable `terrain-map.js` plus `/api/terrain-map.png` to render the actual loaded/generated server terrain below the spawn overlays. Drag pans the map, mouse wheel zooms, and the View radius field controls the size of the rendered area. The first terrain implementation colors surface blocks and biome grass/water from the running Minecraft server; it does not yet overlay structure-finder data like an external seed-map site.


## Server Behavior
The control panel talks to a local HTTP server embedded in the MathQuest mod. The HTTP server binds to `127.0.0.1` by default, so it is reachable from Randy's laptop browser but not from other devices on the LAN.
Config fields:
| Field | Default | Meaning |
|---|---:|---|
| `controlPanelEnabled` | `true` | Starts the local web control server with the Minecraft server |
| `controlPanelHost` | `127.0.0.1` | Local bind host |
| `controlPanelPort` | `8765` | Local HTTP port |
| `controlPanelAssetsDir` | `null` | Optional MathQuest asset root for disk-first hot reload of panel static files |
| `npcAllowMultipleNerds` | `false` | When false, a targeted spawn replaces any active nerd assigned to that player |
| `playerRealNames` | per-family defaults | Editable Minecraft-player to real-name lookup used for internal lists and SQLite exports |
| `playerRewards` | per-family defaults | Per-player literal reward item/count when Reward item is not a group name |
| `playerRewardGroups` | empty | Per-player reward group override (set when Reward item matches a group name) |
| `playerFluencyRewardGroups` | empty | Per-player fluency-improvement reward group override (set when Fluency reward item matches a group name) |
| `rewardGroups` | includes `jtree` | Named reward groups (entries + mode: `all`, `random`, or `choose`) |
| `rewardGroup` | `jtree` | Global active reward group id, or blank for flat `rewards` list |
| `playerFluencyRewards` | per-family defaults | Per-player reward when a fluency-feast quiz improves `% fluent` by at least one point |
| `playerQuizTypes` | per-family defaults | Per-player quiz type: `standard_arithmetic` or `written_column_arithmetic` |
| `playerInternalQuizSources` | per-family defaults | Per-player quiz source: `generated`, `internal_problem_list`, `internal_quick_quiz`, or `internal_fluency_feast` |
| `mathQuizNodeExecutable` | `node` | Node executable for fluency feast generation and `% fluent` calculation |
| `fluencyFeastEnabled` | `true` | When false, `internal_fluency_feast` falls back to generated arithmetic |
| `playerUseInternalProblemLists` | per-family defaults | Legacy compatibility boolean derived from `playerInternalQuizSources` |
| `playerNpcSelections` | per-family defaults | Per-player selected NPC shown in the dropdown and used by Spawn NPC |
| `playerNpcLocks` | per-family defaults | Per-player Lock to player checkbox setting |
| `playerTpCreditEarningEnabled` | empty / `false` | Per-player completed-quiz earning checkbox |
| `playerTpCreditsPerQuiz` | empty / `1` | Per-player credits awarded per completed quiz (1–100) |
| `playerTpCreditBalances` | empty / `0` | Persistent server-owned per-player balance shown on the card |
| `playerTpCreditRewardChoices` | empty / `teleport` | Per-player spend choice; Teleport currently costs one credit |
| `playerPresets` | family defaults | Per-player operation/range/problem count settings |
| `writtenColumnEvaluatorCode` | `paper` | Adult/evaluator code required by the written-column screen |
| `npcDialogueOverrides` | empty | Saved NPC dialogue edits from the gallery |
The panel updates the server's `mathquest.json` and uses the server thread for Minecraft actions.


## Quiz Content
In dedicated-server mode, quiz content is server-owned. When a Wandering Nerd is clicked, or when the panel opens a quiz directly, the server:
1. Resolves that player's quiz params from `mathquest.json`.
2. If Quiz source is **Use internal quick quiz**, loads that player's latest math-quiz SQLite file from `~/Documents/Code/fof-mono/apps/math-quiz/_data/tlkids`, reads `QuickPracticeItems` for the selected operation (`+`, `-`, or `*`), and sends the exact ordered seven-problem set to the client.
3. If Quiz source is **Use internal problem list**, uses the first queued internal problem list in that file, ordered by lowest `ProblemLists.list_order`, and sends the exact ordered problem list to the client in the quiz-open payload.
4. If no matching internal quick quiz or problem list is found, falls back to normal generated arithmetic using the operation/range/problem-count settings.
5. Sends the current server-selected reward plan and quiz type to the client.
This means child/player machines do not need local copies of the math-quiz SQLite files.
After a standard arithmetic quiz completes from **Use internal problem list**, MathQuest consumes the internal list according to the list's own retain setting: retained lists stay in place with `times_used`/`last_used_at` updated, while consume-after-use lists are deleted and the remaining queue is reindexed. Quick quiz rows are not consumed; math-quiz regenerates them after saved sessions. MathQuest does not expose an internal-list editor; those lists are managed in the math-quiz app.
If a player's quiz type is `written_column_arithmetic`, the client opens a paper-practice screen instead of the number-pad quiz. The child solves one vertical-format addition, subtraction, or multiplication problem on paper. The evaluator enters the configured code, the student's answer, optional notes, and marks the attempt Correct, Partial, or Needs Work.


## NPC Behavior
The current NPC gallery contains five data-driven NPC personas:
| NPC id | Display name | Entity |
|---|---|---|
| `wandering_nerd` | The Wandering Nerd | custom villager-model entity |
| `professor_pi` | Professor Pi | custom villager-model entity |
| `countess_calc` | Countess Calc | custom villager-model entity |
| `geo_sage` | Geo Sage | custom villager-model entity |
| `paper_coach` | Paper Coach Penny | custom villager-model entity |
Their default names, texture paths, and dialogue lines live in `fabric/src/main/java/com/kidgames/mathquest/npc/MathQuestNpcCatalog.java`. The panel shows each NPC's dialogue under its preview as editable text boxes; saved edits are written to `npcDialogueOverrides` in `mathquest.json` and used by newly interacted NPCs.
The panel's preview renders a front-facing approximation from each NPC texture under `assets/mathquest/textures/entity/`, instead of showing the raw Minecraft texture atlas.
When a spawned NPC is locked, only the assigned player can trigger it. Other players who right-click it get a short message that the quest is for the assigned player. The NPC's in-game name is shown as:
```text
Professor Pi (<MinecraftPlayerName>)
```
When Lock to player is unchecked, the spawned NPC still appears in that player's panel column for status and Vanish bookkeeping, but its in-game name has no parenthesized player suffix and any player can be the first one to right-click it.


## Local File Writes
The Minecraft server and the math-quiz Python dev server can run at the same time. They use different ports and write different files:
| Process | Port | Writes |
|---|---:|---|
| MathQuest dedicated server | `25565` for Minecraft, `8765` for control panel | `~/Documents/Code/mathquest-server/config/mathquest.json`, `mathquest_data.db`, and MathQuest single-session SQLite exports |
| Math-quiz Python dev server | `8907` | `apps/math-quiz/_data/...` source/test/archive files |
MathQuest 1.6.1+ exports completed Minecraft quiz sessions to:
```text
apps/math-quiz/_data/_single-session-sqlite-files
```
Standard arithmetic exports use the math-quiz single-session schema and filenames like `mathquest_<real-name>_<timestamp>.sqlite`. Written-column paper sessions use a separate schema and filenames like `mathquest_written_column_<real-name>_<timestamp>.sqlite`, with `WrittenColumnSessions` and `WrittenColumnAttempts` tables.


## API
The browser uses these localhost endpoints:
| Endpoint | Method | Use |
|---|---|---|
| `/api/status` | GET | Server config, online players, player card state including TP-credit settings/balance, NPC gallery |
| `/api/config` | POST | Save global panel settings, per-player rewards, and TP-credit earning/amount/choice |
| `/api/spawn` | POST | Spawn a targeted NPC near a player |
| `/api/open` | POST | Open a quiz directly for an online player |
| `/api/vanish` | POST | Remove targeted or all Wandering Nerds |
| `/api/terrain-map.png` | GET | Render terrain image for a center/radius/dimension |
| `/api/spawn-mobs` | POST | Spawn a chosen mob count around an online player |
| `/api/spawn-mob-plan` | POST | Spawn queued mob entries at explicit coordinates/shapes |
| `/api/kill-mob-area` | POST | Remove a selected mob type in a circle/square area |


## Decisions and Tradeoffs
1. **Embedded HTTP server inside the mod.** Chosen so the panel can control the actual Minecraft server without a separate Python/Node backend. Alternative: a separate local web server using RCON. Tradeoff: embedded server adds Java code to the mod, but avoids enabling RCON and keeps all Minecraft actions on the server thread.
2. **Bind to localhost by default.** Chosen for safety because this is a local family control surface. Alternative: bind to `0.0.0.0` so phones/tablets can open the panel. Tradeoff: LAN access is convenient, but it exposes admin controls to the network.
3. **Server sends problem lists to clients.** Chosen because the math-quiz SQLite files live on Randy's laptop/server. Alternative: each client reads its own local `_data/tlkids`. Tradeoff: payloads are larger, but setup is much simpler and server-authoritative.
4. Per-player exact reward overrides. Reward item accepts a group name or literal item/count. Named groups support give-all, random-one, and player-choose modes via the Reward Groups editor.
5. **Editable dialogue stored in config.** Chosen so Randy can tune NPC lines live from the panel without a rebuild. Alternative: edit only the Java catalog. Tradeoff: config overrides add one more saved state layer, but make play-session adjustments much faster.
6. **Written column sessions use a separate SQLite schema.** Chosen because adult-evaluated paper work is not the same shape as auto-graded math-quiz attempts. Alternative: squeeze paper attempts into the math-quiz single-session schema. Tradeoff: separate files require downstream import awareness, but preserve the richer evaluation fields.
7. **Front-preview canvas from the texture atlas.** Chosen because the raw PNG is a Minecraft texture layout and does not look like the in-game character. Alternative: render a true 3D model preview. Tradeoff: canvas is lightweight and local; a true model viewer would be more accurate but more complex.
8. **Disk asset root is `assets/mathquest`, not only `control_panel`.** Chosen so HTML/CSS/JS and NPC preview PNG changes can refresh from disk. Alternative: point only at `control_panel`. Tradeoff: the broader root serves a few more local-only static files, but it keeps NPC appearance iteration in the same workflow.


## First Playtest Checklist
1. Build/deploy MathQuest and restart the dedicated server.
2. Open `http://127.0.0.1:8765/`.
3. Confirm the four player columns appear and online players show as Online after they join.
4. Confirm every card shows **TP credits: 0** (or its saved balance), **Earn TP credits** starts unchecked for an unconfigured player, **Credits per quiz** shows 1, and Reward choice shows **Teleport (1 credit)**.
5. Enable TP-credit earning for one player, set Credits per quiz to 2, wait for autosave, refresh, and confirm both settings persist while the balance remains read-only.
6. Complete a quiz as that player and confirm chat reports exactly 2 credits earned, no standard or fluency reward items are added to inventory, and the card balance updates on the next panel refresh.
7. Run `/tpc <online-player>` and confirm the teleport succeeds, exactly one credit is deducted, chat reports the remaining balance, and the card updates. Also check one shortcut assigned to an online family player.
8. With a zero balance or offline shortcut target, confirm the command refuses without deducting a credit.
9. Turn off TP-credit earning for that player, set a reward item/count or type a reward group name in Reward item, wait for autosave, refresh, and confirm the item selection persists and is granted on the next successful quiz.
10. Open **Reward Groups**, add or edit a group with each mode, click Save groups, refresh, and confirm the group appears in Reward item autocomplete.
11. In the reward item field, type `gold`, press Tab, and confirm it completes to a valid item such as `golden_apple`; wait for autosave and confirm it persists without a `minecraft:` prefix in the browser.
12. Confirm Quiz source defaults to Use internal quick quiz.
13. With Use internal quick quiz selected, confirm Operation stays editable while Range and Problems stay visible but gray out.
14. Change Quiz source to Use internal problem list and confirm Operation, Range, and Problems stay visible but gray out.
15. Change Quiz source to Use settings below, then change the same player's NPC, operation, range, and problem count; wait 5 seconds and confirm the controls do not revert while focused.
16. Edit a player's Real name field, wait for autosave, refresh the browser, and confirm the name persists.
17. Select SkulkScraper in one column and confirm the default real name is Guest.
18. Expand the NPC gallery and confirm The Wandering Nerd, Professor Pi, Countess Calc, Geo Sage, and Paper Coach Penny each show a preview plus editable dialogue lines.
19. Edit one dialogue line, save it, refresh the panel, and confirm the edit persists.
20. Select one of the new NPCs for a player and click Spawn NPC with Lock to player enabled.
21. Confirm the in-game NPC name includes that player in parentheses and the appearance matches the selected gallery persona.
22. Uncheck Lock to player, wait 5 seconds, click Spawn NPC, and confirm the checkbox stays unchecked.
23. Confirm the unlocked in-game NPC name has no player name in parentheses.
24. Confirm the in-game spawn/location chat uses the selected NPC name, not Wandering Nerd.
25. Have another player right-click the unlocked NPC and confirm it can open for them.
26. With Use internal quick quiz selected and quick-practice rows present, have the assigned player right-click it and confirm the seven-problem set matches the selected operation.
27. With Use internal problem list selected and an internal list queued, have the assigned player right-click it, complete the quiz, and confirm the queued list's retain/delete setting is applied in the math-quiz SQLite file.
28. Confirm the exported standard arithmetic SQLite filename uses the real name, not the Minecraft player name.
29. In the mob field, type `ske`, press Tab, and confirm it completes to `skeleton`.
30. Set mob count to `3`, radius to `12`, click Spawn Mobs, and confirm three skeletons spawn randomly near that player.
31. Try a passive mob such as `cow` and confirm it also spawns.
32. Open `/mob-spawn.html`, capture an online player's location, add a `zombie` circle-fill entry, add a `skeleton` rim entry, and confirm both appear in the planning canvas.
33. Click Spawn All and confirm the page reports the spawned/requested counts.
34. Use Queue Again from Recent Runs and confirm the previous entries return to the queue.
35. Move the selected player, click Use Player Location, and confirm the coordinates update without refreshing the page.
36. Confirm the map shows terrain colors instead of a blank background; drag to pan and use the mouse wheel or View radius field to zoom.
37. Click the terrain map and confirm the Offset X/Z fields update for the next spawn entry.
38. Use Kill Area with the matching mob type and a slightly larger radius than the spawn radius, then confirm the spawned mobs are removed.
39. Change a player to Written column arithmetic, open a quiz, solve/evaluate it with the evaluator code, and confirm a `mathquest_written_column_*.sqlite` file lands in `_data/_single-session-sqlite-files` with the real name in the filename.
40. Point a player's Reward item at a **choose**-mode group, complete a quiz, and confirm pick-one buttons appear on the quiz-complete screen.
