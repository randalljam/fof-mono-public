# MathQuest multiplayer NPC-mode end-to-end test

**Date:** 2026-05-11
**Task:** P1-6 (server-conversion plan)
**Purpose:** Validate that the full NPC quiz flow works from a remote client
connected to a local Fabric dedicated server, using the new server-side commands.

---

## Prerequisites

- A local Fabric dedicated server set up per P1-1 (the `~/mathquest-server` from the how-to)
- The latest MathQuest jar (from `build-and-deploy.sh`) and Fabric API jar in the server's `mods/`
- A Minecraft client with the same MathQuest + Fabric API jars installed
- The server and client can run on the same machine (connect to `localhost`)

If you already ran P1-1 and the server is still set up, just update the MathQuest jar
in the server's `mods/` folder with the latest build (copy from
`targets/fabric-26.1.2/build/libs/`), then restart the server.

---

## Test script

### Setup

1. **Start the server** in `~/mathquest-server`:
   ```bash
   java -Xmx2G -jar fabric-server-launch.jar nogui
   ```

2. **Confirm MathQuest loaded** — look for the log line:
   ```
   [MathQuest] Loaded! Mode: popup, quiz every 30 seconds, 5 problems, range 0-9
   ```

3. **Op yourself** — from the server console, type:
   ```
   op <your-username>
   ```

4. **Launch Minecraft** and connect to `localhost`.

### Test 1: Switch to NPC mode via server command

5. **From the Minecraft chat** (not the server console), type:
   ```
   /mathquest mode npc
   ```
   **Expected:** Gold "[MathQuest]" feedback saying mode is now NPC, plus info
   about spawn radius and interval.

6. **Check status:**
   ```
   /mathquest status
   ```
   **Expected:** Shows mode as "NPC (Wandering Nerd)", interval 30s, your player
   presets, rewards, and online player count.

### Test 2: Force-spawn a nerd via server command

7. **Spawn a nerd near yourself:**
   ```
   /mathquest start
   ```
   **Expected:** A Wandering Nerd appears within ~10 blocks of your position.
   You should see "[MathQuest] The Wandering Nerd has spawned!" in chat
   (if `logNerdSpawn` is true in config).

8. **Right-click the Wandering Nerd.**
   **Expected:** A math joke greeting appears in chat, then after ~5 seconds
   the quiz offer screen ("Math Quest! Want to try?") opens.

### Test 3: Complete the quiz flow

9. **Click "Let's Go!"** to start the quiz.
   **Expected:** The quiz screen appears with a math problem and number pad.

10. **Answer all 5 problems** (correct or incorrect).
    **Expected:** Feedback after each answer (green "Amazing!" or red "The answer is N").

11. **Review the result screen.**
    **Expected:** Shows your score, encouragement message, and the reward earned.

12. **Click "Back to Adventure!"**
    **Expected:** Returns to the game. If you got at least one correct, a reward
    item should appear in your inventory.

### Test 4: Targeted start via server command

13. **From the server console** (the terminal where the server is running), type:
    ```
    mathquest start <your-username>
    ```
    (Note: no `/` prefix when typing in the server console.)

    **Expected:** The quiz offer screen opens on your client without a Wandering
    Nerd — this uses the direct `OpenQuizPayload` path.

14. **Dismiss with "Not Now".**
    **Expected:** Screen closes, back to gameplay.

### Test 5: Start all

15. **From the server console:**
    ```
    mathquest start all
    ```
    **Expected:** Quiz offer screen opens on your client. If other players were
    connected, they would all get the offer too.

### Test 6: Config changes via server commands

16. **Change the interval:**
    ```
    /mathquest interval 15
    ```
    **Expected:** Confirmation message. The NPC auto-spawn timer now uses 15s.

17. **Change operation:**
    ```
    /mathquest operation addition
    ```
    **Expected:** Confirmation. Next quiz should show addition problems.

18. **Wait ~15 seconds** for the auto-spawner to fire.
    **Expected:** A Wandering Nerd spawns near you (auto-spawn, not manual).
    Right-click and verify the quiz shows addition problems.

### Test 7: Control Panel hidden on remote

19. **Press the K key.**
    **Expected:** Nothing happens. The Control Panel should not open because
    you are connected to a remote server (even though it is localhost, the
    client sees it as a remote connection).

### Test 8: Persistence check

20. **Check the server directory** (`~/mathquest-server/`) for:
    - `config/mathquest.json` — should reflect the changes you made (mode "npc",
      interval 15, operation "addition")
    - Note whether `config/mathquest_data.db` exists here or only on the client side

21. **Check your client's config directory** (`~/.minecraft/config/` or your launcher
    profile's config dir) for:
    - `mathquest_data.db` — should contain the quiz sessions you just completed
    - `mathquest_sessions/*.json` — session export files

### Test 9: Reconnect

22. **Disconnect from the server** (Back to Title Screen or Quit).
23. **Reconnect to `localhost`.**
    **Expected:** Connection succeeds. The server remembers your op status.
    Run `/mathquest status` to confirm settings persisted.

---

## Randy run results — 2026-05-11

Overall: the multiplayer NPC flow worked through the basic server-command,
Wandering Nerd, quiz, K-hotkey, persistence, and reconnect checks. The first
important mismatch appeared at step 17, where a server-side operation change did
not control the quiz content shown by the remote client.

### Steps 1-16 — passed

- Server startup, op setup, client connection, NPC mode, status, manual nerd
  spawning, right-click interaction, quiz offer, quiz completion, reward flow,
  targeted start, start all, and interval change all worked as expected.
- The server accepted `/mathquest interval 15`, and later behavior showed the
  NPC auto-spawner using the 15-second interval.

### Step 17 — operation change mismatch

Observed result: `/mathquest operation addition` was accepted, but the next quiz
on Randy's `RJComp` client still showed exponentiation problems. Client-side
status also showed client-local settings that differed from the server status:
the client had a 10-minute interval, 10 problems per quiz, and an `RJComp`
exponentiation preset, while the server reported a 15-second interval, 5
problems per quiz, and no `rjcomp` player preset.

Working explanation: this is a config-authority mismatch. The dedicated server
currently controls world behavior such as enabled state, NPC mode, and Wandering
Nerd auto-spawn timing. However, when the server tells the client to open a quiz,
the quiz screen still builds its questions from the remote client's local
`mathquest.json`. That means Randy's local `RJComp` preset and local
`problemsPerQuiz` setting override the server's global operation and problem
count for the actual quiz content. Op status should not remove a player preset;
if the server status does not list `rjcomp`, the server's
`~/mathquest-server/config/mathquest.json` either does not contain that preset or
the running server did not load it.

Follow-up needed before closing P1-6: decide whether server-triggered quizzes
should carry server-resolved quiz settings to the client, so server-side
`/mathquest operation`, `/mathquest range`, `/mathquest player ...`, and problem
count govern remote-player quiz content.

### Step 18 — passed with caveat

- The auto-spawner fired after the interval change, and the Wandering Nerd
  spawned on the new 15-second cadence.
- Caveat: the spawned quiz still used the client-local operation, because of the
  step 17 config-authority mismatch.

### Step 19 — passed

- Pressing the `K` key while connected to the remote server did nothing.
- This matches the expected behavior: the Control Panel is hidden on remote
  multiplayer because it only edits local client config.

### Step 20 — passed

- The server-side `config/mathquest.json` reflected the server-command changes,
  including NPC mode, 15-second interval, and addition as the server default
  operation.

### Step 21 — client-local session export observed

- Session JSON files were not found in the MathQuest server config folder.
- They appeared in Randy's regular Minecraft profile/config location, alongside
  previous MathQuest session files.

Working explanation: this matches the current implementation documented in the
overview: quiz sessions and JSON exports are still client-local. It conflicts
with the server-conversion plan's end-state goal that all quiz data land in a
single server-side SQLite database. Treat this as another P1-6 follow-up rather
than a test-script mistake.

### Steps 22-23 — passed

- Disconnecting and reconnecting to `localhost` worked.
- Running `/mathquest status` after reconnect confirmed the server settings
  persisted.

---

## Reporting back (Phase 1)

After running through this script, report:

1. Did all server commands work (`mode`, `start`, `start <player>`, `start all`,
   `interval`, `operation`, `status`)?
2. Did the Wandering Nerd spawn and the full quiz flow complete?
3. Did the targeted `start <player>` open the quiz without a nerd?
4. Was the K hotkey correctly hidden?
5. Where did the database and session files end up?
6. Did the auto-spawner fire on the new 15-second interval?
7. Any errors, crashes, or unexpected behavior?

Failures here generate follow-up tasks before Phase 2 starts.

---

## Phase 2 — Server-authority verification addendum

**Date:** 2026-05-12
**Task:** P2-6 (server-conversion plan)
**Purpose:** Re-run key P1-6 tests with Phase 2 changes in place. Phase 2 makes the server
the single source of truth for quiz content and session recording in multiplayer.

### Prerequisites

Same as above. Update the MathQuest jar on both the server and client:

1. From the repo root: `cd mathquest && ./build-and-deploy.sh`
2. Copy the built jar from `targets/fabric-26.1.2/build/libs/mathquest-fabric-*-mc26.1.2.jar`
   to the server's `mods/` folder (replacing the old jar).
3. Restart the server.
4. The client jar is already in place from `build-and-deploy.sh`.

### Phase 2 test script

Run through the full P1-6 test script above (steps 1–23), then run these additional
Phase 2-specific checks.

#### Test P2-A: Server operation controls quiz content (the step 17 fix)

24. **Set the server operation to addition:**
    ```
    /mathquest operation addition
    ```
    **Expected:** Confirmation message.

25. **Spawn a nerd and take a quiz:**
    ```
    /mathquest start
    ```
    Right-click the nerd (or accept the offer screen), complete the quiz.

    **Expected:** The quiz shows **addition** problems, regardless of what your
    client's local `mathquest.json` says. This is the key fix — the server now
    sends quiz parameters to the client.

26. **Change the server operation to multiplication:**
    ```
    /mathquest operation multiplication
    ```

27. **Take another quiz** (via `/mathquest start` or wait for auto-spawn).

    **Expected:** The quiz now shows **multiplication** problems. The server
    controls what the client quizzes on.

#### Test P2-B: Server range controls quiz content

28. **Set the server range:**
    ```
    /mathquest range 1 5
    ```

29. **Take a quiz.**

    **Expected:** All factors in the quiz are between 1 and 5. The server's
    range setting is being used, not the client's local range.

30. **Reset to a wider range:**
    ```
    /mathquest range 0 12
    ```

#### Test P2-C: Client config commands blocked in multiplayer

31. **Try to change operation from the client:**
    ```
    /mathquest operation addition
    ```
    **Expected:** A yellow message saying something like "Config commands are not
    available in multiplayer. Ask your server operator to change settings."
    The command does **not** change anything.

32. **Try other config commands** (interval, range, etc.):
    ```
    /mathquest interval 10
    /mathquest range 0 5
    ```
    **Expected:** Same rejection message for each. Config changes are server-only
    in multiplayer.

33. **Confirm `/mathquest status` still works:**
    ```
    /mathquest status
    ```
    **Expected:** Status output is shown (not blocked). Status is read-only and
    remains useful for debugging.

#### Test P2-D: Session data lands server-side

34. **After completing at least one quiz**, check the server directory
    (`~/mathquest-server/`) for:
    - `config/mathquest_data.db` — should exist and contain the quiz session(s)
      you just completed. (If you have `sqlite3` installed, try
      `sqlite3 ~/mathquest-server/config/mathquest_data.db "SELECT * FROM sessions;"`)
    - `config/mathquest_sessions/*.json` — session export files should appear
      here, one per completed quiz.

35. **Check the client side** — your client's `~/.minecraft/config/` directory
    should **not** have new session data from the multiplayer quiz. (Old data from
    previous singleplayer sessions may still be there; that's fine. The key check
    is that the multiplayer quiz you just took did **not** write to the client's DB.)

#### Test P2-E: Singleplayer still works

36. **Disconnect from the server** and open a singleplayer world.

37. **Trigger a quiz** (via popup timer, `/mathquest start`, or NPC depending on
    your local config mode).

38. **Complete the quiz.**

    **Expected:** The quiz uses your local `mathquest.json` settings (not server
    settings, since there is no server). Session data is written to your local
    `~/.minecraft/config/mathquest_data.db` and `mathquest_sessions/` as before.

### Reporting back (Phase 2)

After running through tests P2-A through P2-E, report:

1. Did `/mathquest operation addition` on the server cause the remote client's quiz
   to show addition problems? (The step 17 fix.)
2. Did server range changes control the quiz content on the client?
3. Were client-side config commands properly blocked with a user-facing message?
4. Did session data (DB + JSON) land in the server's config directory?
5. Was the client's local config directory free of new multiplayer session data?
6. Did singleplayer still work with local config and local session recording?
7. Any errors, crashes, or unexpected behavior?

Failures here generate follow-up tasks before Phase 3 starts.
