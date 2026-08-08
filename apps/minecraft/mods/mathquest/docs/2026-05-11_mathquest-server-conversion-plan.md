MathQuest server conversion plan

**Date:** 2026-05-11
**Status:** Phase 0 complete (merged). Phase 1 complete (merged, PR #7). Phase 2 complete (PR pending merge). Phase 3 not yet started.
**Tracking issue:** [#3](https://github.com/randalljam/kid-games/issues/3)

## Task list

Condensed view of every task in this plan, in execution order. Detailed descriptions live in the phase sections below.

Each task is tagged with **who runs it**:

- *(claude)* — Claude executes autonomously: writes code, runs tests, commits.
- *(randy)* — Randy runs it manually on his own machine. Claude pauses, commits work-to-date, and provides explicit step-by-step instructions; resumes once Randy reports results back.
- *(claude + randy)* — Mixed: Claude does the code/doc part and hands off to Randy for hands-on verification.

Status legend: `[ ]` pending · `[~]` in progress · `[x]` done · `[!]` blocked.

### Phase 0 — Foundations *(complete, merged)*

- [x] **P0-1** *(claude)* — confirm `fabric-26.1.2` is the default build target; keep `fabric-1.21.11` as preserved capability
- [x] **P0-2** *(claude)* — declare the client-side-only mod pattern as a first-class reusable mode

### Phase 1 — Server-capable MathQuest *(complete, merged — PR #7)*

- [x] **P1-1** *(claude + randy)* — run the current jar on a fresh local Fabric dedicated server
- [x] **P1-2** *(claude)* — audit code for singleplayer-only assumptions
- [x] **P1-3** *(claude)* — add server-side `/mathquest` Brigadier tree, op-gated
- [x] **P1-4** *(claude)* — hide the Control Panel `K` hotkey on remote multiplayer
- [x] **P1-5** *(claude)* — add server-side `/mathquest start <player|all>` that sends `OpenQuizPayload`
- [x] **P1-6** *(claude + randy)* — end-to-end NPC-mode test from a real remote client. **Result:** 21 of 23 steps passed; step 17 exposed a config-authority mismatch (server controls timing but client builds quiz content from its own local config). See test results in `2026-05-11_multiplayer-npc-test-script.md`. Addressed by Phase 2.

### Phase 2 — Server-authoritative quiz content *(complete, PR pending merge)*

- [x] **P2-1** *(claude)* — design the server-authority model
- [x] **P2-2** *(claude)* — extend or replace `OpenQuizPayload` to carry resolved quiz parameters
- [x] **P2-3** *(claude)* — update client quiz screens to use server-provided settings in multiplayer
- [x] **P2-4** *(claude)* — deprecate client-side commands and Control Panel for multiplayer
- [x] **P2-5** *(claude)* — server-side quiz session recording via C2S payload
- [x] **P2-6** *(claude + randy)* — re-run the P1-6 test script, verifying server authority works end-to-end

### Phase 3 — DM experience *— not yet Randy-reviewed*

- [ ] **P3-1** *(claude + randy)* — enable RCON on the local dedicated server
- [ ] **P3-2** *(claude)* — DM recipe scripts (RCON-backed shell commands for common session presets)
- [ ] **P3-3** *(claude)* — local read-only dashboard (webapp reading the server-side SQLite DB)
- [ ] **P3-4** *(claude)* — read-write dashboard via RCON (add "start quiz on Player X" and config buttons)

### Phase 4 — Session data to S3 *— not yet Randy-reviewed*

- [ ] **P4-1** *(claude)* — design the S3 upload approach (session JSON and/or DB snapshots)
- [!] **P4-2** *(randy, blocked)* — wire in AWS credentials and target S3 bucket
- [ ] **P4-3** *(claude)* — implement server-side S3 upload of session data
- [ ] **P4-4** *(claude + randy)* — verify session files appear in S3 after a family playtest

### Phase 5 — Math-quiz repo integration *— not yet Randy-reviewed*

- [ ] **P5-1** *(claude)* — audit `milestone-web` MathQuiz features and identify what to bring into MathQuest
- [ ] **P5-2** *(claude)* — design doc for the integration (what features, what stays web-only, what moves into the mod)
- [ ] **P5-3** *(claude)* — implement the agreed-upon feature set

### Phase 6 — Hosting on AWS *— not yet Randy-reviewed*

- [!] **P6-1** *(randy, blocked)* — wire in AWS CLI profile, region, existing infra references (may be unblocked by repo consolidation work)
- [ ] **P6-2** *(claude)* — ECS/EC2 architecture doc with cost estimate
- [!] **P6-3** *(claude + randy, blocked on architecture + cost approval)* — provision the deployment
- [ ] **P6-4** *(claude)* — two-tier permission model (player whitelist + world-creator list)

### Phase 7 — Multi-world plumbing *— not yet Randy-reviewed*

- [ ] **P7-1** *(claude)* — design doc for multi-world support
- [!] **P7-2** *(claude, blocked on architecture)* — implement the chosen multi-world option

---

## Near-term goal: local multiplayer with the family

Randy's priority is getting MathQuest fully functional as a **local multiplayer experience** before any cloud hosting work. The setup: Randy runs the Fabric dedicated server on his laptop, his family (wife + two kids = four players) connects, and Randy acts as DM — controlling quiz settings, triggering quizzes, monitoring progress.

This is already happening in early form. Randy's daughter has run real practice sessions: multiplication, 7 problems per quiz, 5 sessions. There's tuning to do (operations, difficulty, pacing), and Randy wants better tools for doing that tuning in real time during a family play session.

The plan is structured around this: **Phases 2–5 all target the local server setup.** They make the server authoritative, give Randy better DM tooling, get session data into a shared location, and integrate features from the existing math-quiz web app. AWS hosting (Phase 6) comes after the local experience is solid and Randy's repo consolidation work has progressed enough to make AWS infrastructure code project-wide.

## Scope

Convert MathQuest into a server-hosted experience the user can steer like a dungeon master, **without** removing the current client-side-only mod pathway. This plan has two arcs:

**Local arc (Phases 2–5):** Get the full DM + multiplayer experience working on a local dedicated server. Server controls all quiz content, Randy has ergonomic tools for steering sessions, session data is accessible centrally, and features from the math-quiz web app are folded in.

**Cloud arc (Phases 6–7):** Move the validated local setup to always-on AWS hosting. Add multi-world support. These phases are deliberately deferred until the local experience is solid and Randy's parallel repo consolidation work is ready.

The repo retains its current capability to ship a **client-only mod** as a first-class mode throughout.

Explicitly **out of scope** for this plan (see the roadmap section at the bottom):

- New gameplay content types (yes/no, multiple choice, open-ended voice).
- Curriculum / preset sequencing.
- Multi-user dashboard with kid/parent logins.
- DM teleport-to-arena mechanic.

## How this plan is organized

The plan has two arcs. The **local arc** (Phases 2–5) targets the local dedicated server and can proceed without any AWS infrastructure. The **cloud arc** (Phases 6–7) lifts the validated local setup to AWS. Within each arc, phases are loosely sequential but the boundaries are soft.

The task IDs in this document (`P0-1`, `P2-3`, etc.) match the checklist at the top. Use those IDs when referring to tasks in chat or commits. Detailed sections below carry the same ID so they are easy to find.

**Pause-and-handoff pattern for *(randy)* tasks.** When a task is owned by Randy (or mixed), Claude does its part — code change, doc write, instructions doc — then commits the work-to-date on the current branch with a message like `P2-1 prep: instructions for Randy`, pauses, and provides the explicit step-by-step instructions in the chat reply. Randy runs the steps, reports findings, and Claude resumes by either (a) flipping the checkbox to `[x]` if the step succeeded, or (b) opening follow-up tasks for any failures.

---

## Phase 0 — Foundations (no game-behavior changes)

**Goal:** lock in the conventions the rest of the plan depends on.

### P0-1 — confirm default build target *(claude)*

Make sure `fabric-26.1.2` is the default `buildAll` target when no flag is passed, and that the docs (`OVERVIEW.md` and `EXPLAINER.md`) reflect this. `fabric-1.21.11` stays in the multi-target apparatus as preserved capability (older obfuscated-class pathway). **No removals.** Verify by reading `settings.gradle` and `build.gradle` and updating only what's needed.

#### P0-1 — Fabric 26.1.2 client startup troubleshooting (Cursor Composer)
2026-05-11_1630 Cursor - Composer 2

**Branch:** `claude/mathquest-phase-0-13SLj-P0-1`

**Context:** AI-assisted troubleshooting in **Cursor Composer** while validating the **primary** `fabric-26.1.2` build. Shared `fabric/` client code calls **`KeyBindingHelper`** (`net.fabricmc.fabric.api.client.keybinding.v1`). The aggregated **`fabric-api`** Gradle artifact for Minecraft **26.1.x** does **not** declare the split module **`fabric-key-binding-api-v1`**, so the symbol was missing from the compile classpath until it was wired explicitly.

**Timeline of failure modes**

1. **Compile failure** (`compileJava`): `package ... keybinding.v1 does not exist` — no **`fabric-key-binding-api-v1`** on Gradle classpath.
2. **Runtime crash** (`ClassNotFoundException` for **`KeyBindingHelper`**) after adding compile-only Gradle **`implementation`**: Gradle could compile and **`BUILD SUCCESSFUL`**, but the published mod jar did **not** nest that module. The Fabric installer split for **Fabric API** on the client (crash report lists submodules such as **`fabric-key-mapping-api-v1`**) also does **not** load **`fabric-key-binding-api-v1`** by default — so Knot had no bytecode for **`KeyBindingHelper`**.
3. **Working state:** Declare **`fabric-key-binding-api-v1`** with **`include implementation(...)`** in **`targets/fabric-26.1.2/build.gradle`** (Jar-in-Jar / same pattern as **`sqlite-jdbc`**), and pin **`fabric_key_binding_api_version`** in **`targets/fabric-26.1.2/gradle.properties`** next to **`fabric_version`**. Rebuild and redeploy; verify the output jar contains **`META-INF/jars/fabric-key-binding-api-v1-*.jar`**.

**Randy verification (2026-05-11):** After redeploy, Minecraft launched; basic in-game smoke test (spawning Wandering Nerd, core flow) looked good — not a full regression pass.

**Specifications for coding agents — do not regress this**

- **Split Fabric API modules:** When **`compileJava`** fails on a missing **`net.fabricmc.fabric.api.*`** type, check whether the symbol lives in a **split submodule** not pulled by the **`fabric-api`** aggregate POM for that Minecraft line. Search Maven (`maven.fabricmc.net`) and the Fabric repo's **`gradle.properties`** for the module name; add an explicit dependency on the **`fabric-26.1.2`** target only if older targets do not need it.
- **Compile vs runtime for `fabric-26.1.2`:** Plain Gradle **`implementation`** fixes the **compiler only**. For Minecraft/Fabric Loader to see classes at startup, **`include implementation(...)`** (JiJ) is required whenever the standalone Fabric API install does **not** ship that module — mirror how this repo bundles **`sqlite-jdbc`**.
- **Do not substitute `modImplementation` blindly:** The **`net.fabricmc.fabric-loom`** (**1.15**) MathQuest target uses ordinary **`implementation`** for loader/API deps; **`modImplementation`** is not the configured shorthand on that subproject (unlike **`fabric-1.21.11`** legacy **`fabric-loom`**).
- **`fabric_version` bumps:** When **`fabric_version`** changes in **`targets/fabric-26.1.2/gradle.properties`**, reconcile **`fabric_key_binding_api_version`** with the submodule version Fabric publishes for that API release line (Maven / Fabric changelog / upstream **`gradle.properties`**). Mismatch risk is lower when both are updated together.
- **Proof after changes:** Run **`./build-and-deploy.sh`** (or **`./gradlew :targets:fabric-26.1.2:build`**) and confirm **`jar tf` on `targets/fabric-26.1.2/build/libs/mathquest-fabric-*-mc26.1.2.jar`** lists **`META-INF/jars/fabric-key-binding-api-v1-`** (the nested JiJ jar), not only successful compilation.
- **Cross-doc:** Keep **`docs/OVERVIEW.md`** aligned with any new split-module or JiJ rule; this plan subsection remains the **primary narrative** for P0-1 troubleshooting history.

### P0-2 — document the client-side-only mod pattern *(claude)*

Add a short doc declaring that the **client-side-only mod pattern** (today's MathQuest) is a first-class, reusable mode of this codebase. This is a doc-only change. Sketch of contents:

- "Start a new client-only mod" — minimum surface area: a new `ClientModInitializer`, screen classes, optional client-only data persistence. **No** `ServerTickEvents`, **no** server commands, **no** custom C2S payloads required.
- Which parts of the existing MathQuest source are reusable as-is (e.g. `config/`, `screen/` widgets, `data/` SQLite layer if the mod wants client-side persistence).

This doc protects the option to spin up a tiny client-only mod from this codebase later without inheriting all the server machinery from Phase 1+.

---

## Phase 1 — Make MathQuest server-capable (no hosting changes)

**Goal:** the current MathQuest jar runs cleanly on a vanilla-Fabric dedicated server, with a real DM command surface, before we move it to AWS.

### P1-1 — sanity-check the jar on a fresh local Fabric server *(claude + randy)*

**Claude does:** write a short how-to doc that walks Randy through:

1. Downloading the matching Fabric server launcher for `fabric-26.1.2`.
2. Setting up a fresh server folder, accepting the EULA, and starting the JVM.
3. Dropping the locally-built `build-and-deploy`-produced MathQuest jar (and Fabric API) into `mods/`.
4. Starting the server and noting whether the world starts, `mathquest.json` is created, the Wandering Nerd spawner ticks server-side, a finished quiz writes to `mathquest_data.db`, and a `mathquest_sessions/*.json` is emitted.

Then commit the how-to and **pause**.

**Randy does:** run through the how-to on his laptop and report back what worked, what crashed, and any unexpected behavior. Failures observed here become inputs to `P1-2`.

### P1-2 — audit code for singleplayer-only assumptions *(claude)*

Code audit pass over `fabric/src/main/java/com/kidgames/mathquest/`. Specifically look for:

- `MinecraftClient.getServer() != null` checks that are correct (singleplayer-only fast paths) vs. ones that should be reworked.
- Anything client-side that mutates state assumed to be authoritative.
- Path resolution that assumes integrated-server config dir vs. dedicated-server config dir.
- `MathQuestCommands` registration — currently `ClientCommandRegistrationCallback`, needs a server counterpart in `P1-3`.

Output: a short audit summary in the PR description plus any code fixes that don't fit cleanly under `P1-3` / `P1-4` / `P1-5`.

### P1-3 — server-side `/mathquest` Brigadier tree *(claude)*

Add a parallel Brigadier tree registered via `CommandRegistrationCallback` (Fabric API). Mirror the existing client commands, but **gate** any state-changing command with `.requires(src -> src.hasPermissionLevel(2))` so only ops can change settings.

Commands to include server-side: `interval`, `mode`, `operation`, `range`, `player <name> {operation|range|clear}`, `npcspawn {all|random|only <name>}`, `bundle <name|clear>`, `start`, `status`, `enable`, `disable`.

Keep the client-side `/mathquest` registration **in place** for singleplayer. The two trees diverge slightly: client-side stays open to non-op players in singleplayer; server-side enforces op level.

### P1-4 — hide Control Panel on remote multiplayer *(claude)*

`ControlPanelScreen` (hotkey `K`) currently edits a client-local `mathquest.json`. On a dedicated server those edits don't sync. **Phase 1 decision (Randy-approved):** when the client is connected to a remote multiplayer server (`MinecraftClient.getServer() == null`), **hide the `K` hotkey entirely** so it has no effect. No read-only variant in this phase.

The full "op-only network-synced control panel" design is a later, optional follow-up — not required for the dashboard to be the primary DM surface.

### P1-5 — server-side `/mathquest start <player|all>` *(claude)*

**What this is and why it matters:** Today `/mathquest start` is a *client* command. In **popup mode** it just opens the offer screen on whoever typed it. In **NPC mode** it queues a Wandering Nerd spawn for the local player. Neither version lets you, the operator, target someone else.

This task adds a **server-side** variant of the command that an op can type from anywhere (chat, console, RCON later, dashboard later) targeting a specific player or all players. Mechanically:

- Server receives `/mathquest start <username>` from an op.
- Server looks up the matching `ServerPlayerEntity`.
- Server sends `OpenQuizPayload` (the existing S2C packet) to that player's client connection.
- That player's client opens `QuizOfferScreen` just as if they'd been spawned a nerd.
- `<all>` variant loops over all online players and sends to each.

This single command is the building block for the DM dashboard's "start a quiz on Wildpetal right now" button (Phase 3). Until this exists, the dashboard would have no way to start a quiz — it would only be able to twist dials.

### P1-6 — validate NPC mode end-to-end with a remote client *(claude + randy)*

**Claude does:** write a step-by-step test script covering the multiplayer NPC flow. Then commit and **pause**.

**Randy does:** with one machine running the local dedicated Fabric server from `P1-1` (still running, or restarted), and a second client (or even the same machine, separate Minecraft instance) connecting to it, run the script:

1. Connect as an op and switch to NPC mode (`/mathquest mode npc`).
2. Trigger a spawn (`/mathquest start <your-username>`).
3. Confirm the Wandering Nerd appears nearby.
4. Right-click the nerd to open the quiz.
5. Complete the quiz; confirm rewards land in inventory and the session writes to the server-side SQLite DB.
6. Disconnect and reconnect; confirm the player UUID + username are recorded correctly.

Report back. Any failure here generates a follow-up task before Phase 2 starts.

---

## Phase 2 — Server-authoritative quiz content *— NOT YET RANDY-REVIEWED*

> **Hold here.** Do not begin Phase 2 without an explicit Randy greenlight.

**Goal:** make the server the single source of truth for quiz content in multiplayer. When a quiz fires on a remote client — whether from a Wandering Nerd interaction, `/mathquest start <player>`, or `start all` — the server resolves the quiz parameters and sends them to the client. The client renders from the server-provided settings, not from its own local `mathquest.json`. In singleplayer, the current local-config behavior is preserved unchanged.

**Why this phase exists:** P1-6 testing (step 17) showed that `/mathquest operation addition` was accepted by the server but the remote client's quiz still used its local `RJComp` exponentiation preset. The root cause: `QuizManager` on the client builds questions from the client's local config. The server controls world behavior (NPC spawning, timing) but has no way to tell the client *what* to quiz on.

Randy's strategic direction (from issue #3, 2026-05-12): move to full server-side authority over quiz settings. Players interact only with the NPC/quiz UI. All configuration happens server-side — commands now, dashboard later. No client-side commands or Control Panel needed for multiplayer.

Phase 2 keeps server commands as the primary DM control surface. Phase 3 adds ergonomic tooling on top.

### P2-1 — design the server-authority model *(claude)*

Write a short design section (here in this plan or as a standalone doc) covering:

- What settings the server resolves per player: operation, range, problemsPerQuiz, and player preset.
- The resolution order: player-specific preset overrides server defaults.
- What payload carries these settings: extend `OpenQuizPayload` with fields, or define a new `QuizSettingsPayload`.
- How the client distinguishes "use server settings" (multiplayer) from "use local config" (singleplayer).
- Whether the server generates the actual problems or just sends parameters and lets the client generate them. (Recommendation from issue #3 analysis: for now, send parameters and let the client generate. Full server-generated problems is a later step that enables server-side answer validation.)

#### P2-1 design: server-authoritative quiz parameters

**Settings the server resolves per player.** Before sending a quiz-start packet the server calls `MathQuestConfig.resolveForPlayer(playerName)` which returns `EffectiveQuizParams(minNumber, maxNumber, operation, problemsPerQuiz)`. Resolution order: per-player preset fields (from `playerPresets`) override the server's global defaults; any preset field left null inherits the global value. This is the same logic that exists today — the difference is that it now runs on the server, not the client.

**Payload design.** Extend the existing `OpenQuizPayload` (S2C) to carry four fields: `operation` (String), `minNumber` (int), `maxNumber` (int), `problemsPerQuiz` (int). The payload is always fully populated when the server sends it. No new payload type is needed.

**Client multiplayer vs singleplayer.** Two code paths open the quiz offer screen:

- **Payload-triggered** (NPC interaction, `/mathquest start`, `start all`): The payload always carries server-resolved params. `QuizOfferScreen` receives the params and passes them to `QuizManager(EffectiveQuizParams)`. Works identically in singleplayer (integrated server sends the payload too) and multiplayer.
- **Popup timer** (singleplayer only): The timer directly opens `new QuizOfferScreen()` with no params. `QuizOfferScreen` falls back to `MathQuestMod.CONFIG.resolveForPlayer(playerName)` — the current local-config behavior, unchanged.

**Problem generation stays client-side for now.** The server sends parameters; the client generates random problems from those parameters. This keeps the change small. A future enhancement could have the server generate the actual problems (enabling server-side answer validation), but that is not needed for Phase 2.

**Quiz result recording (P2-5 design).** A new `QuizResultPayload` (C2S) carries quiz results as a JSON string: operation, problem count, correct count, reward description, and per-problem detail (factors, correct answer, player answer, is-correct, response time). The server handler deserializes this, writes to the server-side `mathquest_data.db`, and exports a session JSON file to the server's `config/mathquest_sessions/`. In multiplayer the client skips all local DB writes and session exports. In singleplayer the client continues writing locally as before (client and integrated server share the same config dir, so either path produces the same result).

**Client-side command deprecation (P2-4 design).** When connected to a dedicated server (`getSingleplayerServer() == null`), client-side `/mathquest` commands that modify config are no-ops. They print a message directing the user to server-side commands. The `status` command remains functional (useful for debugging). In singleplayer, all client commands work as before.

### P2-2 — extend the quiz-start payload *(claude)*

Implement the payload change from P2-1. The server resolves the target player's effective settings from `MathQuestConfig` (including per-player preset if one exists) and sends them in the payload. All existing server-side triggers — Wandering Nerd interaction, `/mathquest start <player>`, `start all` — use this enriched payload.

### P2-3 — client uses server-provided settings *(claude)*

Update `QuizOfferScreen` and `QuizManager` to use the payload's settings when they are present. When the payload carries settings (multiplayer), ignore local config for quiz content. When the payload has no settings (singleplayer, or the old empty payload for backwards compatibility during transition), fall back to local config.

### P2-4 — deprecate client-side controls for multiplayer *(claude)*

- Remove or no-op client-side `/mathquest` commands when connected to a dedicated server (they edit local config that no longer governs quiz content in multiplayer).
- The Control Panel K hotkey is already hidden (P1-4); this task confirms there is no other client-side path that edits quiz-governing config on a remote connection.
- In singleplayer, client commands and Control Panel remain fully functional.

### P2-5 — server-side quiz session recording *(claude)*

Move quiz result persistence to the server:

- Add a new C2S payload (`QuizResultPayload` or similar) that the client sends when a quiz completes, carrying the score, answers, and timing data.
- Server receives this and writes to the server-side `mathquest_data.db` and emits session JSON.
- Client no longer writes to its own local DB in multiplayer (still does in singleplayer).

This closes the other P1-6 observation: session data currently lands client-side even in multiplayer.

### P2-6 — re-run the NPC test script *(claude + randy)*

Re-run the P1-6 test script with the server-authority changes in place. Key verification for step 17: `/mathquest operation addition` on the server should now control what the remote client's quiz shows. Also verify session data now lands in the server's `config/` directory, not the client's.

---

## Phase 3 — DM experience *— NOT YET RANDY-REVIEWED*

> **Hold here.** Do not begin Phase 3 without an explicit Randy greenlight.

**Goal:** give Randy ergonomic tools for steering a family play session — beyond typing `/mathquest` commands in the Minecraft chat or server console. This phase targets the **local dedicated server** (Randy's laptop). Everything here works without AWS.

The progression: Phase 2 gave the server authority over quiz content via commands. Phase 3 wraps those commands in tools that are faster and less error-prone during a live session with the kids.

### P3-1 — enable RCON on the local dedicated server *(claude + randy)*

RCON lets external programs send commands to the running Minecraft server. Turn it on in `server.properties` (it ships disabled by default). RCON password stays local — no secrets management needed for a laptop server.

**Claude does:** write a short how-to for enabling RCON and testing it with `mcrcon` or a similar CLI tool.

**Randy does:** follow the how-to, confirm RCON commands work from a second Terminal window while the server is running.

### P3-2 — DM recipe scripts *(claude)*

Write a handful of common-recipe shell scripts in `mathquest/tools/dm/`. Each is a thin RCON wrapper that issues one or more `/mathquest` commands. Examples:

- `warmup.sh` — short interval, addition, range 0–10.
- `challenge.sh` — longer interval, multiplication, range 5–12.
- `celebrate.sh` — swap to a generous reward bundle.
- `kid-session.sh wildpetal` — apply a kid-specific preset for one player.
- `quiz-now.sh wildpetal` — start a quiz on a specific player immediately.

These are the "one-click" versions of the command sequences Randy would otherwise type by hand. They work against any RCON-accessible server — local or eventually AWS.

### P3-3 — local read-only dashboard *(claude)*

Scaffold a read-only dashboard webapp that reads the server-side SQLite DB (the one that P2-5 now writes to on the server). Views:

- Per-player accuracy over time (line chart).
- Operation mix (pie/bar).
- Problems most often missed (filterable by player and operation).
- Live "session in progress" indicator (poll DB or watch the sessions JSON dir).

Stack choice TBD when we get there. Pragmatic options: Node/Express + a static SPA, or FastAPI + HTMX. The repo already has a `milestone-web/` sibling that may have reusable styling.

Runs on Randy's laptop, binds to `127.0.0.1`, opens in a browser tab alongside Minecraft. DM-only, no auth needed.

### P3-4 — read-write dashboard via RCON *(claude)*

Add write endpoints to the dashboard, each backed by an in-process RCON client that issues `/mathquest` commands on the local server. This adds interactive controls:

- "Start a quiz on Wildpetal right now" button.
- Operation / range / interval pickers that issue the corresponding server commands.
- Per-player preset selector.

Same posture (localhost, DM-only). This is the "dashboard as DM cockpit" — Randy can steer the session from a browser tab instead of typing commands.

---

## Phase 4 — Session data to S3 *— NOT YET RANDY-REVIEWED*

> **Hold here.** Do not begin Phase 4 without an explicit Randy greenlight.

**Goal:** get quiz session data off Randy's laptop and into a durable, accessible location. This is the first lightweight contact with AWS infrastructure — just an S3 bucket, no servers.

**Why before AWS hosting:** even while running the server locally, Randy wants session data accessible from other devices (phone, other laptop) and backed up. S3 is the simplest path: the server already produces session JSON files (after P2-5 moves recording server-side); uploading them to S3 is a small addition.

**Relationship to the later AWS hosting phase:** once the server moves to AWS (Phase 6), session data will naturally live on that server's filesystem or a mounted volume. At that point, S3 upload might become redundant or might stay as a backup/export mechanism. Either way, the S3 integration built here carries forward.

**Note:** Randy is doing parallel repo consolidation work that will affect how AWS infrastructure code is organized project-wide. Phase 4 is intentionally lightweight (just S3 uploads) so it doesn't conflict with that consolidation. Heavier AWS work (ECS, networking) is deferred to Phase 6 when the repo structure is ready.

### P4-1 — design the S3 upload approach *(claude)*

Decide what gets uploaded and when:

- **Option A — session JSON files.** After each quiz session completes, the server uploads the session JSON to S3. Simple, append-only, easy to browse. Downside: many small files.
- **Option B — periodic DB snapshot.** Upload `mathquest_data.db` to S3 on a schedule (e.g. every 10 minutes or on server shutdown). Single file, queryable. Downside: not real-time.
- **Option C — both.** Session JSON for real-time, DB snapshot for backup. Probably overkill for v1.

Recommendation: start with Option A (session JSON upload on completion). It's the simplest, gives immediate access to individual session results, and doesn't require SQLite locking coordination.

Also decide: does the mod's server-side code do the upload directly (AWS SDK in the mod jar), or does a sidecar script watch the session directory and upload new files? The sidecar approach is simpler and keeps AWS dependencies out of the mod.

### P4-2 — wire in AWS credentials *(randy, blocked)*

Randy provides or configures:

- AWS CLI profile or environment variables for S3 access.
- Target S3 bucket name and region.
- IAM permissions: the upload process needs `s3:PutObject` on the target bucket/prefix.

This is a gating step. The S3 bucket might already exist from Randy's other AWS work, or it might need to be created.

### P4-3 — implement S3 upload *(claude)*

Implement the chosen approach from P4-1. Likely a small script or daemon in `mathquest/tools/` that watches the server's `config/mathquest_sessions/` directory and uploads new JSON files to S3.

### P4-4 — verify S3 upload *(claude + randy)*

Run a family play session, confirm session files appear in S3, confirm they're readable and contain the expected data.

---

## Phase 5 — Math-quiz repo integration *— NOT YET RANDY-REVIEWED*

> **Hold here.** Do not begin Phase 5 without an explicit Randy greenlight.

**Goal:** bring relevant features from the `milestone-web` MathQuiz web app into MathQuest. The web app has accumulated question-generation logic, filtering, flagging, and other features that would enrich the in-game quiz experience.

This phase is deliberately placed late in the local arc. By this point, server authority is working (Phase 2), the DM has good tooling (Phase 3), and session data is flowing to S3 (Phase 4). The integration work here builds on that foundation — and naturally raises the question of what should stay in-mod vs. what should live on the AWS server, which feeds into Phase 6 scoping.

### P5-1 — audit `milestone-web` features *(claude)*

Read through the `milestone-web/` codebase and catalog its features. Identify:

- What can transfer directly to the MathQuest mod (question generation logic, difficulty scaling, operation types).
- What is web-specific and stays in the web app (UI components, browser-only features).
- What makes sense as a server-side/dashboard feature rather than an in-game feature.

### P5-2 — integration design doc *(claude)*

Write a design doc covering which features to bring in, how they map to the mod's architecture, and what the implementation looks like. Randy reviews and greenlights specific features before implementation.

### P5-3 — implement the agreed-upon feature set *(claude)*

Implement the features Randy approved in P5-2. This may involve multiple sub-tasks depending on what's selected.

---

## Phase 6 — Hosting on AWS *— NOT YET RANDY-REVIEWED*

> **Hold here.** Randy has explicitly deferred AWS hosting work. Do not begin any Phase 6 task without an explicit Randy greenlight in chat or as a comment on issue #3. Randy's parallel repo consolidation work may need to reach a certain point before this phase is practical.

**Goal:** lift the locally-validated server to an always-on AWS deployment with persistent storage and a two-tier permission model. By this point, the local experience is solid (Phases 2–5 complete), and Randy wants the server running 24/7 so the kids can play without him starting the server manually.

### P6-1 — wire in AWS context *(randy, blocked)*

This is the gating step. Randy wants to **link in existing AWS infrastructure** (CLI profile, region, possibly a VPC and CloudWatch log group conventions) rather than have Claude provision new AWS context from scratch. Until Randy does this, Phase 6 stays paused.

Concrete asks for Randy:

- Provide the AWS CLI profile name to use (`AWS_PROFILE` value).
- Confirm the target region.
- Point to an existing VPC/subnet/security-group setup or confirm we should design a fresh one.
- Confirm how cost approval should work (single-shot approval up to $X/month? per-resource approval?).

### P6-2 — architecture doc *(claude)*

Once P6-1 resolves, write the architecture doc. The hosting approach (ECS vs. EC2) is an open question — ECS is Randy's preference for new AWS work, but a single EC2 instance may be simpler for a Minecraft server with persistent world state. The architecture doc will evaluate both.

Expected components regardless of approach:

- Server JVM (`openjdk:25-jdk` base + Fabric server launcher).
- Persistent storage for world dir, `mathquest.json`, the SQLite DB, and `mathquest_sessions/`.
- CloudWatch logs for server stdout/stderr.
- Security group exposing Minecraft TCP `25565`.
- Dashboard co-located with the server (RCON over localhost).
- S3 session upload (carried forward from Phase 4, or possibly replaced by direct DB access if the dashboard is co-located).

Include a cost estimate at 4–5 concurrent players.

### P6-3 — provision the deployment *(claude + randy, blocked)*

Provision per the architecture doc. **No autonomous provisioning.** Each cost-incurring step gets confirmed with Randy before execution.

### P6-4 — two-tier permission model *(claude)*

Implement the two-tier permission model:

- **Player whitelist** = standard Minecraft `whitelist.json` (already supported by vanilla; the server enforces it).
- **World-creator list** = new field `worldCreators` in `mathquest.json`, a `List<String>` of lowercase player names. Defaults to Randy's three-person family. Add `/mathquest worldcreator {add|remove|list} <name>` (op-only).

This phase is just data + commands. The actual *capability* to spin up worlds is Phase 7.

---

## Phase 7 — Multi-world plumbing *— NOT YET RANDY-REVIEWED*

> **Hold here.** Do not begin Phase 7 without an explicit Randy greenlight. This phase is deliberately late and exploratory until the single-world flow is comfortable.

**Goal:** members of the world-creator list (defined in P6-4) can spin up additional worlds that share the family whitelist.

### P7-1 — multi-world architecture doc *(claude)*

Design doc only. Evaluate:

- **(a) Multiple server processes** on the same host (or separate hosts), each with its own world dir and port, fronted by the dashboard. Whitelist sync via a shared `whitelist.json` and a small sync job.
- **(b) Single server, multiple worlds** — there is no clean Multiverse equivalent in Fabric, so this likely requires writing one. Defer or skip.

Strong prior: option (a) is the realistic path.

### P7-2 — implement multi-world *(claude, blocked)*

Implement the chosen option. Includes lifecycle management (start/stop additional server processes via the dashboard), shared whitelist, and DB strategy (per-world DB vs. one DB with a `world_id` column).

---

## Roadmap (deferred — explicitly NOT in this plan)

For posterity so we don't lose track of where things are going.

1. **Non-math question types** — yes/no, multiple choice. Canned content. Probably the immediate next plan after this one ships.
2. **Open-ended questions with voice input** — kid speaks an answer, we transcribe (Whisper or similar), an AI model evaluates correctness. Significant lift; needs careful UX.
3. **Curricula / saved presets** — group questions into structured sequences with progression.
4. **Multi-user dashboard** — kids/parents can log in and see their own data. Adds an auth story.
5. **DM teleport-to-arena mechanic** — alternative to NPC mode where the DM yanks a player into a dedicated quiz arena.

---

## Decisions captured from the tracking issue

Pulled out of [#3](https://github.com/randalljam/kid-games/issues/3) for visibility here:

- Standardize on `fabric-26.1.2`; keep `fabric-1.21.11` as preserved capability.
- Codebase is a "Minecraft mod creation codebase," not just MathQuest. Preserve the client-side-only mod pattern as a first-class reusable mode.
- ~5–10 concurrent players target. Always-on AWS hosting is the end goal, but local-first development comes first.
- Two worlds and two permission lists: standard whitelist + world-creator list.
- Dashboard is DM-only for now.
- Keep both quiz modes (popup + NPC); teleport-to-arena is roadmap.
- Curriculum sequencing is roadmap; next content step is non-math (yes/no, multiple choice), then voice/open-ended.
- Near-term priority is local multiplayer with Randy's family (4 players), iterating on the DM experience before investing in AWS hosting.
