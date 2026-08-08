 MathQuest Playtest Log

Each section is one playtest run. Copy the template, fill in the datetime in the markdown heading 1, check off steps as you go, and note any issues inline.
AI Instructions: -Insert new instances of the playtest checklist above previous ones and below these instructions.
**Checkbox legend** — Use **no space inside empty brackets**: `[]`, not `[ ]`, so you can click between `[` and `]` and drop in one marker (below). GitHub treats these as literal text, not clickable task widgets; this log is intentional about that.

- **`[x]`** — Checked off: outcome matched what **this checklist line says** you should see.
- **`[]`** — Not scored yet **(empty brackets, no gap)** until you replace the emptiness with another marker below.
- **`[~]`** — **Current row** / in progress (“this is the one I’m on now”).
- **`[?]`** — **Uncertain or blocked**: can’t decide pass/fail from this session, prerequisites missing, or needs another look.
- **`[!]`** — **Bug / bad behavior**: the **game/mod** didn’t do what **should** happen (real failure, not a typo in the checklist).
- **`[w]`** — **Worked, but wording is wrong**: what you observed is plausible/correct given the design direction, yet **what this checklist line asserts as “expected” is outdated or incorrect** — fix or rewrite the playbook, not necessarily the build. Older entries sometimes use `[wrong-expected]` for the same idea.
- **Other tags sometimes used**: **`[skip]`** — skipped step (upstream/cascade); **`[fix]`** — flagged for a follow-up code change **in addition** to logging notes.

---

# v1.24.0 — M6 playtest matrix Datetime 2026-06-30_1227
**Branch:** `feature/minecraft-mod-forge`
**Targets:** Forge 1.20.1 + Fabric 26.1.2 + Fabric 1.21.11

Deploy: `./apps/minecraft/mods/build-and-deploy.py mathquest --target forge-1.20.1,fabric-26.1.2,fabric-1.21.11`

**Server startup (2026-06-30 ~12:25):** Forge dedicated server reached `Done!`; MathQuest logged control panel at `http://127.0.0.1:8765/` and fluency bridge OK. Unrelated mod noise: Player Locator Plus Reforged tag error (`hoglin_head`); MathQuest version bump warn (1.23.1 → 1.24.0).

## Forge 1.20.1 (Prism + `mathquest-server-forge`)
- [x] 1. Dedicated server: core control panel — `/`, `/api/status`, `/api/config`, `/api/spawn`, `/api/open`, `/api/vanish`

  **Live config:** `~/Documents/Code/mathquest-server/config/mathquest.json` (see `mathquest-server-forge/config/minecraft_LIVE-CONFIG-JSON-IS-IN-MATHQUEST-SERVER-FOLDER.txt`).

  1a. **[x] Dashboard** — `http://127.0.0.1:8765/` loads.
  1b. **[x] `/api/status`** — JSON OK; no quest section.
  1c. **[x] `/api/config`** — Changed global **Quiz Mode** to Popup; after **Save** (pre-1.24.1) `quizMode` became `"popup"` in live config. *(1.24.1+ autosaves global settings — no top Save button. Checked the save button was gone and confirmed Mode change to json, no other playtests for this version.)*
  1d. **[x] `/api/spawn`** — Spawn NPC; Wandering Nerd appeared (unlock not required for spawn).
  1e. **[x] Quiz via nerd** — Right-click nerd → 20-question fluency feast quiz (source label at bottom).
  1f. **[x] Nerd gone** — Despawned after quiz complete.

- [x] 2. Quiz + SQLite — Session written to active `tlkids` DB with today’s timestamp.
- [x] 3. Client `/mathquest` rejects in multiplayer; server console: `mathquest status` at `>` prompt (no `/`).
- [x] 4. No automatic interval nerd in 5+ minutes; panel spawn only.

## Fabric 26.1.2 using `mathquest-server` (regression — full panel)
- [x] 5. Terrain-map + mob-spawn admin — terrain map updated; mobs spawned via panel (`~/Documents/Code/mathquest-server`).
- [skip] 5b. Quest `/api/quest/*` routes — not exercised this session.
- [x] 6. NPC quiz + internal quick quiz + SQLite ingest — session appended to active `tlkids` DB.

## Fabric 1.21.11 (sanity)
- [skip] 7. Launch profile / quiz — skipped (no Prism instance; preserved-capability target).

## Result
**Pass / Fail:** Pass (M6 matrix complete for merge gate, 2026-06-30)
**Notes:** Forge 1.20.1 steps 1–4 at 1.24.0/1.24.1; Fabric 26.1.2 quick server regression at 1.24.1 (quest routes and 1.21.11 skipped). Full checklist: this file, section `v1.24.0 — M6 playtest matrix`.

---

# v1.4.0 — Quick smoke test (~5 min) Datetime YYYY-MM-DD_HHMM
**Branch:** `claude/mathquest-phase-2-server-authority`

Use this when you just want to confirm a recent change didn't break the core flow. Covers subtraction, server-controlled operation switch, vanishnerds, and shared data dir. Skip the long P1-6 regression unless the change is broad.

- [] 1. (server console) Start server in `~/Documents/Code/mathquest-server`, wait for `[MathQuest] Loaded!`
- [] 2. (server console) `op <username>`
- [] 3. (client) Connect to `127.0.0.1:25565`
- [] 4. (server console) `mathquest mode npc` — confirmation
- [] 5. (server console) `mathquest operation subtraction` — confirmation
- [] 6. (server console) `mathquest range 0 9` — confirmation
- [] 7. (server console) `mathquest start <username>` — Wandering Nerd spawns near target
- [] 8. (client) Right-click nerd → "Let's Go!" — **subtraction problems shown** (e.g. `7 - 3 = ?`)
- [] 9. (client) Answer all problems, click "Back to Adventure!" — **reward in inventory, nerd despawns**
- [] 10. (server console) `mathquest vanishnerds` — reports `Removed N Wandering Nerd(s)`
- [] 11. (server) Check `~/Documents/Code/mathquest-server/config/mathquest_sessions/` — new session JSON for this player
- [] 12. (client) Disconnect, open singleplayer world, trigger a quiz (NPC or popup), complete it
- [] 13. (server) Check `~/Documents/Code/mathquest-server/config/mathquest_sessions/` — **new file from singleplayer too** (proves shared dir)

## Result

**Pass / Fail:** _______________

**Notes:**


---

# v1.3.1 — Phase 2 follow-up fixes verification Datetime 2026-05-12_0801
**Branch:** `claude/mathquest-phase-2-server-authority`

## Setup
- [x] 1. (server console) Start server in `~/Documents/Code/mathquest-server` (`java -Xmx2G -jar fabric-server-launch.jar nogui`)
- [x] 2. (server console) Confirm `[MathQuest] Loaded!` line in server log
- [x] 3. (server console) Op yourself (`op <username>`)
- [x] 4. (client) Launch Minecraft, connect to `localhost` at Server Address `127.0.0.1:25565`

## P1-6 regression (steps 5–23)
- [x] 5. (server console) `mathquest mode npc` — confirmation message, mode switches to NPC
- [x] 6. (chat) `/mathquest status` — prints "Connected to a multiplayer server. Run 'mathquest status' from the server console for active settings."
- [x] 6b. (server console) `mathquest status` — shows NPC mode, interval, presets, rewards (the real active settings)
- [w] 7. (chat) `/mathquest start` — Wandering Nerd spawns nearby (in NPC mode, op start spawns a nerd)
Here I think the expected is wrong because I got the blocked message that says "On a dedicated server, nerd spawn on the server." Which is what I think should happen.
- [x] 8. (client) Right-click nerd — math joke, then quiz offer screen
- [x] 9. (client) Click "Let's Go!" — quiz screen with problem + number pad
- [x] 10. (client) Answer all problems — green/red feedback after each
- [x] 11. (client) Result screen — score, encouragement, reward earned
- [x] 12. (client) "Back to Adventure!" — returns to game, reward in inventory, **nerd despawns**
- [x] 13. (server console) `mathquest start <username>` — in NPC mode, **a Wandering Nerd spawns** near the target (the server's `start <player>` honors mode)
- [x] 14. (client) "Not Now" on a fresh nerd's offer — dismisses cleanly, **nerd despawns**
- [x] 15. (server console) `mathquest start all` — a Wandering Nerd spawns near every online player
- [x] 16. (server console) `mathquest interval 300` — confirmation message, timer reset
- [x] 16b. (chat) `/mathquest interval 60` — **blocked** with "use server-side /mathquest commands" message
- [] 17. See P2-A below (operation change tested there)
- [x] 18. (client) Wait ~5 min (interval is 300s) for auto-spawn — nerd appears
- [x] 19. (client) Press K — nothing happens (hidden on remote)
- [x] 20. (server) Check server `config/mathquest.json` — reflects changes
- [x] 21. (server) Check server for session data — see P2-D below
- [x] 22. (client) Disconnect from server
- [x] 23. (client, after reconnect) `/mathquest status` — prints the redirect message (no stale local values)
- [x] 23b. (server console) `mathquest status` — settings persisted across the disconnect

## P2-A: Server operation controls quiz content
- [x] 24. (server console) `mathquest operation addition` — confirmation
- [x] 25. (server console) `mathquest start <username>`, take quiz — **addition problems shown** (not local config)
- [x] 26. (server console) `mathquest operation multiplication` — confirmation
- [x] 27. (server console) `mathquest start <username>`, take another quiz — **multiplication problems shown**

## P2-B: Server range controls quiz content
- [x] 28. (server console) `mathquest range 1 5` — confirmation
- [x] 29. (server console) `mathquest start rjcomp`, take quiz — **all factors between 1 and 5**
- [x] 30. (server console) `mathquest range 0 12` — reset

## P2-C: Client config commands blocked in multiplayer
- [x] 31. (chat) `/mathquest operation addition` — **blocked with message** (not changed)
- [x] 32. (chat) `/mathquest interval 10` and `/mathquest range 0 5` — **both blocked**
- [x] 33. (chat) `/mathquest status` — prints multiplayer redirect message (no local config dump)

## P2-D: Session data lands server-side
- [x] 34. Check `~/Documents/Code/mathquest-server/config/` for `mathquest_data.db` and `mathquest_sessions/*.json`
- [x] 35. Check client `~/.minecraft/config/` — **no new** multiplayer session data

## P2-E: Singleplayer regression
- [x] 36. (client) Disconnect, open singleplayer world
- [x] 37. (client) Trigger a quiz (popup timer, `/mathquest start`, or NPC)
- [x] 38. (client) Complete quiz — **uses local config**, session data written to client's local DB

## P2-F: 1.3.1 fixes
- [x] 39. (server console) `mathquest vanishnerds` — all Wandering Nerds in the overworld removed, count reported
- [x] 40. (client, NPC mode multiplayer) Spawn a nerd via server `start`, dismiss with "Not Now" — nerd disappears (no waiting for the despawn timer)
- [x] 41. (client, NPC mode multiplayer) Spawn a nerd, complete a quiz, click "Back to Adventure!" — nerd disappears

## Result

**Pass / Fail:** _______________

**Notes:**


---

# v1.3.0 — Phase 2 server-authority verification Datetime 2026-05-12_0523
**Branch:** `claude/mathquest-phase-2-server-authority`

## Setup
- [x] 1. Start server in `~/Documents/Code/mathquest-server` (`java -Xmx2G -jar fabric-server-launch.jar nogui`)
- [x] 2. Confirm `[MathQuest] Loaded!` line in server log
- [x] 3. Op yourself from server console (`op <username>`)
- [x] 4. Launch Minecraft, connect to `localhost` at Server Address `127.0.0.1:25565`

## P1-6 regression (steps 5–23)
- [?] 5. `/mathquest mode npc` — gold feedback, mode switches to NPC
The MathQuest appears in gold with brackets and it says on a multiplayer server use server-side/MathQuest commands, OP required. Client commands only affect local config which is ignored in multiplayer.
- [?] 6. `/mathquest status` — shows NPC mode, interval, presets, rewards
There is a mismatch between the parameters for running this command in the client versus running it on the server. For example, the interval on the client says 10 minutes, the number of problems says 10, whereas on the server it's 15 seconds and number of problems 5. And the server seems to be what it's doing, so those seem to be actually the active ones. But we need to clean this up because there shouldn't be a mismatch.
- [x] 7. `/mathquest start` — Wandering Nerd spawns nearby
- [x] 8. Right-click nerd — math joke, then quiz offer screen
- [x] 9. Click "Let's Go!" — quiz screen with problem + number pad
- [x] 10. Answer all problems — green/red feedback after each
- [x] 11. Result screen — score, encouragement, reward earned
- [x] 12. "Back to Adventure!" — returns to game, reward in inventory
- [?] 13. Server console: `mathquest start <username>` — quiz offer opens (no nerd)
The nerd did spawn here so I changed to do and issued a server command for the math quest interval to be 300 which will give time for the current ones to despawn and then I can confirm this again that this is spawning the NPC. Yep, okay, I did this again and it does indeed spawn the Wondering Nerd, which is what it should do when the mode is set to NPC. It should spawn the NPC, so I'm not sure why you said there should be no nerd, but I think that was incorrect.
- [fix] 14. "Not Now" — dismisses cleanly
When I hit not now, this is on NPC mode, it does dismiss the quiz but then the nerd should disappear and he's not. And I also need a command to make all of the wondering nerds disappear so add that command.
- [x] 15. Server console: `mathquest start all` — quiz offer opens
A new nerd spawned.
- [wrong-expected?] 16. `/mathquest interval 300` — confirmation message
This gave me the message on a multiplayer server, use server-side, MathQuest commands, which is what I think it should do, because that shouldn't work anymore from the client side, right? Isn't that the whole point of this work? So why did you... what were you expecting in the confirmation message?
- [] 17. See P2-A below (operation change now tested there)
- [x] 18. Wait ~15s for auto-spawn — nerd appears
- [x] 19. Press K — nothing happens (hidden on remote)
- [x] 20. Check server `config/mathquest.json` — reflects changes
- [x] 21. Check server for session data — see P2-D below
- [x] 22. Disconnect from server
- [fix] 23. Reconnect, `/mathquest status` — settings persisted
Okay, when I reconnect and if I run the client command, the interval that it gives is wrong. It says 10 minutes. And when I run the server command, MathQuest status, it says interval 4 minutes, which is what I set it at. So again, this is the same issue I brought up for number 6 above. There's a mismatch and the client info is wrong.

## P2-A: Server operation controls quiz content
- [see-16] 24. `/mathquest operation addition` — confirmation
Same as 16 above.
- [wrong-expected] 25. `/mathquest start`, take quiz — **addition problems shown** (not local config)
This is giving me a new message, again with MathQuest in gold, that says, "On a dedicated server, nerds spawn on the server as an op use /mathquest start or ask the host to run mathquest start in the server console."
- [skip] 26. `/mathquest operation multiplication` — confirmation
- [skip] 27. Take another quiz — **multiplication problems shown**

## P2-B: Server range controls quiz content
- [skip] 28. `/mathquest range 1 5` — confirmation
- [skip] 29. Take quiz — **all factors between 1 and 5**
- [skip] 30. `/mathquest range 0 12` — reset

## P2-C: Client config commands blocked in multiplayer
- [x] 31. `/mathquest operation addition` — **blocked with message** (not changed)
- [x] 32. `/mathquest interval 10` and `/mathquest range 0 5` — **both blocked**
- [x] 33. `/mathquest status` — **still works** (not blocked)

## P2-D: Session data lands server-side
- [x] 34. Check `~/Documents/Code/mathquest-server/config/` for `mathquest_data.db` and `mathquest_sessions/*.json`
- [x] 35. Check client `~/.minecraft/config/` — **no new** multiplayer session data

## P2-E: Singleplayer regression
- [x] 36. Disconnect, open singleplayer world
- [x] 37. Trigger a quiz (popup timer, `/mathquest start`, or NPC)
- [x] 38. Complete quiz — **uses local config**, session data written to client's local DB

## Result

**Pass / Fail:** _______________

**Notes:**


