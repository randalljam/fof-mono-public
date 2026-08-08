=== MathQuest — Application Overview =====

**Last updated:** 2026-07-22 (PDT) — v1.25.4 Ice and Fire EntityMutlipartPart projectile filter

> **For coding agents:** This is the authoritative reference for the MathQuest codebase.
> Read this file first when starting a new session. **You must update this file whenever
> you add features, fix bugs, change file structure, modify behavior, or alter
> configuration.** Keep every section accurate and current. When in doubt, update it.
>
> **Deploying your changes:** After implementing or fixing code, run `./gradlew :common:test` and `./gradlew :targets:fabric-26.1.2:test` (and a Forge `--no-deploy` build when Forge glue changed), then **always run `./apps/minecraft/mods/build-and-deploy.py mathquest` from the repo root as the very last step** when you want the new jar copied into your local Minecraft `mods` folder. Do not treat `./gradlew build` alone as "done" for playtesting — the **final section** of this document (**Build and Deploy**) is the canonical instruction for that last step.
>
> **Multi-target build:** MathQuest uses **nested loader gradle roots**: `mathquest/fabric/` (Gradle 9, Fabric targets) and `mathquest/forge/` (Gradle 8, Forge 1.20.1). Shared loader-agnostic code lives in `fabric/common/`; Fabric-specific code in `fabric/shared/src/`. Per-target build files live under each loader's `targets/<loader>-<mc-version>/`. Default dispatcher target is **`fabric-26.1.2`** (`.mod-build.toml`). Forge: `./apps/minecraft/mods/build-and-deploy.py mathquest --target forge-1.20.1` (Prism instance **"Forge 1.20.1 MathQuest"**). Forge deploy copies the **jarJar `-all.jar`** artifact (~12 MB, bundles sqlite-jdbc) — not the slim jar.
>
> **Client-side-only mod pattern:** Today's MathQuest is a client-side-only Fabric mod, and that pattern is a **first-class reusable mode** of this codebase even as server-side capability is added. See [`CLIENT_ONLY_MOD_PATTERN.md`](CLIENT_ONLY_MOD_PATTERN.md) before lifting MathQuest internals into a new mod.
>
> **Version bumps:** Bump `mod_version` in **both** `fabric/gradle.properties` and `forge/gradle.properties` (keep them in lockstep) when a session produces distinct deployable jars.

---

## What Is MathQuest?

MathQuest is a **Minecraft mod** (Fabric primary + Forge 1.20.1 port) that interrupts gameplay on a configurable timer to present the player with a math quiz (addition, subtraction, multiplication, or exponentiation). It is designed for kids (the developer's 8-year-old daughter) to practice math facts while playing Minecraft. Correct answers earn in-game item rewards when TP-credit earning is off. Players can instead opt into **TP credits**, earning a configured number for each completed quiz and spending one credit to teleport; TP-credit mode does not also grant item rewards.

- **Targets:**
  - `fabric-26.1.2` *(primary)* — Minecraft 26.1.2, Fabric Loader 0.18.5, Fabric API 0.146.1+26.1.2, Java 25 bytecode, unobfuscated Minecraft via `net.fabricmc.fabric-loom`/Loom 1.15. This is the default target for the build dispatcher and is listed first in `settings.gradle`.
  - `fabric-1.21.11` *(preserved capability)* — Minecraft 1.21.11, Fabric Loader 0.18.3, Fabric API 0.139.4+1.21.11, Java 21 bytecode, Mojang official mappings via legacy `fabric-loom`/Loom 1.14. Kept in the multi-target apparatus as the codebase's reference for building against pre-26.1 Minecraft (the obfuscated-class pathway). Do not remove.
  - `forge-1.20.1` *(Milestone 6 — v1.25.4)* — Minecraft 1.20.1, Forge 47.4.0, Java 17. Popup + **NPC mode**, in-game **Control Panel** + **K** keybind, **HTTP control panel core** (`status`/`config`/`spawn`/`open`/`vanish`), fluency-feast result UI, server-side reward/result handling and one-use TP-credit sessions via `SimpleChannel`, client + op `/mathquest` commands, non-op TP-credit teleport commands, SQLite export/ingest. The current multiplayer trust limitations are documented under [Known Limitations / Technical Debt](#known-limitations--technical-debt). **v1.25.4:** client mixin skips Forge `PartEntity` and Ice and Fire `EntityMutlipartPart` in projectile picking (dragon / trident freeze workaround); toggle `excludeMultipartFromClientProjectileHits` / `/mathquest multipartProjectileFix`. MathQuest 1.24.2+ permits vanilla/unmodded clients without the MathQuest channel; those clients receive no MathQuest UI or protocol support, while real MathQuest clients must match protocol exactly. Build root: `mathquest/forge/`. Dedicated server: `~/Documents/Code/mathquest-server-forge` (see Forge howto). Deploy also targets Prism **Forge 1.20.1 Ice and Fire**. **Core (non-quest) feature parity declared at M6.** **On hold for Forge:** written-column quiz screen, terrain-map control panel, mob-spawn admin panel. **Quest FROZEN past M6** (Fabric-only).
- **Forge parity roadmap:** M1 (popup singleplayer) → M2 (platform + networking + commands + SQLite) ✅ → M3 (NPC mode) ✅ → M3B (parity fixes) ✅ → M4 (in-game control panel + K key + fluency result UI) ✅ → M4B (Quiz source selector + fluency backfill) ✅ → M5 (HTTP control panel core + written-column; quest frozen) ✅ → **M6 (parity hardening + merge to build-local) ✅**. See `.cursor/plans/2026-06-30_forge-port-milestone6_181d7d32.plan.md`.
- **Version history:** Current version, dated build notes, and playtest status live in [`../CHANGELOG.md`](../CHANGELOG.md). The root `gradle.properties` supplies the build artifact `mod_version`; per-target Minecraft / loader / API versions live in each target's own `gradle.properties`.
- **Local web control panel:** Dedicated-server operator UI lives in [`CONTROL_PANEL.md`](CONTROL_PANEL.md). It is served by the running MathQuest server at `http://127.0.0.1:8765/`.

### Upgrading to Minecraft 26.1.1

Pre-built config files for **MC 26.1.1** are saved in **`versions/26.1.1/`**. As of 2026-04-08, Fabric tooling **cannot build for 26.1.1** because neither Yarn mappings nor Mojang official mappings are published yet. When mappings become available, copy the saved files into place:

| Source (`versions/26.1.1/`) | Destination (relative to `mathquest/`) |
|-----------------------------|----------------------------------------|
| `gradle.properties` | `gradle.properties` |
| `build.gradle` | `build.gradle` |
| `fabric.mod.json` | `src/main/resources/fabric.mod.json` |
| `build-and-deploy.sh` | `build-and-deploy.sh` |
| `gradle-wrapper.properties` | `gradle/wrapper/gradle-wrapper.properties` |
| `stubs-VERSIONS` | `stubs/VERSIONS` |
| `build.gradle.dual-mode` is unchanged (Yarn path works once mappings exist) | |

**What the 26.1.1 files change:** Gradle **9.2.0**, Loom **1.15.+**, JDK **25** (`brew install openjdk@25`), Fabric Loader **0.18.6**, Fabric API **0.145.4+26.1.1**, `mappings_kind=official_mojang` (switch to `yarn` once Yarn is published). See `versions/26.1.1/README.md` for full details.

**Before building for 26.1.1**, check:
- **Yarn:** https://maven.fabricmc.net/net/fabricmc/yarn/maven-metadata.xml (search for `26.1.1`)
- **Mojang mappings:** fetch `26.1.1.json` from Mojang's version manifest and look for `client_mappings`

If Yarn is available, update `gradle.properties` in the saved files: set `mappings_kind=yarn` and `yarn_mappings=26.1.1+build.N`. Also update this overview's version bullets.

---

## Quiz Modes

MathQuest supports two quiz trigger modes, set via the `quizMode` config field or `/mathquest mode` command:

### Popup Mode (`quizMode = "popup"`, default)
A timed screen overlay pops up every `quizIntervalSeconds` **only in singleplayer** (integrated server). **On a remote multiplayer connection**, the popup timer is **disabled** so each client does not spam the offer screen independently; use **NPC mode** on the server for quizzes in shared worlds.

### NPC Mode (`quizMode = "npc"`)
Instead of a popup, a custom NPC entity spawns near a player every `quizIntervalSeconds`. The default persona is **The Wandering Nerd**, and the local web control panel can also select **Professor Pi**, **Countess Calc**, **Geo Sage**, or **Paper Coach Penny** for targeted spawns. NPC names, texture paths, and default one-line dialogue live in `fabric/src/main/java/com/kidgames/mathquest/npc/MathQuestNpcCatalog.java`; control-panel dialogue edits are persisted in `mathquest.json` under `npcDialogueOverrides`. The NPC wanders around within the world like a wandering trader, carrying a book. When the player right-clicks the NPC, it sends a random persona-specific greeting and opens the quiz offer screen (after a short client-side delay). **The NPC stays in the world** after that (no instant removal); it despawns after `npcDespawnSeconds` (default 120 s) or when the client clears nearby NPCs after quiz UI. Only one NPC will exist near a player at a time unless multiple NPCs are enabled.

**Who gets an automatic spawn** is controlled by `npcSpawnTargetMode` (and `npcSpawnTargetPlayer` when mode is `one`):
- **`all`** (default): On each interval, **every online player** in the **overworld** gets an independent spawn attempt (skip if a nerd is already within `npcSpawnRadiusBlocks` of that player).
- **`random`**: On each interval, **one** online player is chosen uniformly at random; a spawn is attempted only for them (if they do not already have a nerd nearby).
- **`one`**: On each interval, only the configured username (`npcSpawnTargetPlayer`, matched case-insensitively) gets a spawn attempt if they are online **in the overworld**; if they are elsewhere or offline, nothing spawns that tick.

**Dimension:** The spawner runs only on the **overworld** (`ServerWorld` from `server.getOverworld()`). `world.getPlayers()` lists players **in that dimension**, so anyone in the Nether, End, or another dimension is skipped until they return.

NPC-mode config fields:
- `npcSpawnRadiusBlocks` (default 10): How far away the nerd can spawn from the chosen player
- `npcDespawnSeconds` (default 120): How long the nerd lingers before disappearing
- `npcSpawnTargetMode` (default `all`): `all`, `random`, or `one`
- `npcSpawnTargetPlayer` (default unset): lowercase name; used only when mode is `one`

---

## Gameplay Flow

1. **Quiz trigger** — Depends on `quizMode`:
   - **Popup mode:** `MathQuestClient` registers a `ClientTickEvents.END_CLIENT_TICK` handler. Every `quizIntervalSeconds` (default 30 s), if the mod is enabled, no screen is open, and the client has an **integrated server** (`MinecraftClient.getServer() != null`, i.e. singleplayer), it opens `QuizOfferScreen`. **Remote multiplayer clients** skip this timer so offer screens are not triggered on an interval for every player.
   - **NPC mode:** `WanderingNerdSpawner` runs on the **overworld** server tick. Every `quizIntervalSeconds`, it selects target player(s) according to `npcSpawnTargetMode` (see **NPC Mode** above) and attempts to spawn a `WanderingNerdEntity` within `npcSpawnRadiusBlocks` of each selected player who does not already have an NPC nearby. When a player interacts with the NPC, the server sends a `OpenQuizPayload` S2C packet to open the quiz.

2. **Offer screen** — Shows "Math Quest!" with two buttons: **Let's Go!** (starts the quiz) and **Not Now** (dismisses). In **multiplayer**, the quiz uses **server-provided parameters** (operation, range, problem count, quiz type, problem list, reward plan) sent in the `OpenQuizPayload`. In **singleplayer** (popup timer path), the quiz resolves per-player presets from the local client's config; players without a preset use the global defaults. Before generating random problems, the standard arithmetic offer checks math-quiz SQLite problem lists for mapped players in `~/Documents/Code/fof-mono/apps/math-quiz/_data/tlkids`; if a current list is found, the quiz uses that ordered list instead.

3. **Quiz screen** — Standard arithmetic displays the current problem in operation-specific form (`a + b`, `a - b`, `a x b`, `a / b`, or `a ^ b` for exponentiation) with an on-screen number pad (0–9), a `+/-` sign toggle in the lower-left cell, Clear, Enter, and a Quit button. The player types their answer via the number pad or keyboard (answers are compared as 64-bit integers; `+/-` flips the sign of the current input buffer for negative answers). Written column arithmetic opens `WrittenColumnQuizScreen`, which asks the child to solve one vertical addition, subtraction, or multiplication problem on paper; the evaluator enters the configured code, the student's answer, notes, and a Correct/Partial/Needs Work evaluation. Standard arithmetic features:
   - **Auto-accept:** If the typed number equals the correct answer, the answer is submitted automatically without pressing Enter.
   - **Feedback:** Correct → green "Amazing!" text + XP orb pickup sound. Wrong → red "The answer is N" text + villager "no" sound. Feedback displays for 1.5 seconds before advancing.
   - **Quit confirm:** Pressing Quit or Escape shows a "Yes, quit / No, continue" confirmation dialog. Quitting discards the session.

4. **Result screen** — Shows final score, encouragement tier (perfect / great / keep practicing), and the reward earned. Plays the level-up sound when items are granted. A "Back to Adventure!" button closes the screen.

5. **Rewards** — If the player got at least one correct answer:
   - The active reward **plan** comes from `MathQuestConfig.resolveRewardPlanForPlayer()`: a per-player reward group ref, a per-player single item override, or the global active group / flat list fallback.
   - **Named group active** (`rewardGroup` set): uses that group's **mode** — `all` (every entry), `random` (one random entry), or `choose` (player picks one on the quiz-complete screen).
   - **Flat list only** (`rewardGroup` unset): `rewardMode = "random"` (default) picks **one** random entry from `rewards`; `rewardMode = "all"` gives **every** entry in `rewards`.
   - Groups are defined in `rewardGroups` (map keys are lowercase group ids). Each group has `mode` plus `entries`. The default **`jtree`** group uses mode `random` and contains: 1 diamond, 8 cooked beef (steak), 1 golden apple, 1 cactus.
   - Items are granted **server-side** via a custom C2S network packet (`GiveRewardPayload`). The client sends the packet; the server creates the `ItemStack` and inserts it into the player's inventory via `offerOrDrop`. This ensures items persist across sessions and behave like normal items (food restores hunger, etc.).
   - If zero correct: no items, message "Keep practicing to earn rewards!"

6. **TP credits** — Per-player earning is **off by default**. When enabled in the web control panel, TP credits **replace standard and fluency item rewards**: every completed standard, fluency-feast, quest-result, or written-column quiz awards that player's configured credit amount (default **1**), even when the score is zero, without also granting the configured reward item/count. Item selections remain stored for use if earning is turned off. Each delivered quiz receives an opaque, server-issued one-use token that remains pending until the corresponding result is processed; only then can the amount-free completion request redeem it. Saving a partial quiz through **Quit Quiz** cancels the token. Incomplete, cancelled, invalid, and replayed tokens cannot award. The server resolves the setting and amount, atomically replaces `mathquest.json`, and reports the new balance in chat. Teleport is the first spend choice and costs **1 credit**. `/tpc <player>` teleports to an online player, `/tpc <x> <y> <z>` teleports within the current dimension, and `/tpt`, `/tpp`, `/tpr`, `/tpw` target TreasureHunterM, PumaJockey, RJComp, and WildPetal. Invalid/offline destinations and insufficient balances do not deduct a credit. Failed config replacements restore the prior in-memory balance and report the failure.

7. **Persistence** — In **singleplayer**, every standard arithmetic answer is recorded to the legacy local SQLite database (`mathquest_data.db`) and the completed quiz is exported as a **single-session SQLite file** for math-quiz intake. On **Forge singleplayer**, export also runs on the client (integrated server path + local fallback, same as Fabric). In **multiplayer**, the client sends standard quiz results to the server via `QuizResultPayload` (C2S); the server records to its own `mathquest_data.db` and exports the single-session SQLite file. Standard export filenames are `mathquest_{real-name}_{YYYY-MM-DD}_{HHMMSS}.sqlite`, and the schema contract lives at `apps/math-quiz/docs/2026-06-20_minecraft-mod-single-session-sqlite-spec.md`. Completed sessions are ingested into per-player active DB files under `mathQuizActiveDbDir` (default `apps/math-quiz/_data/tlkids/`). Written column arithmetic skips the legacy quiz DB and writes separate files named `mathquest_written_column_{real-name}_{YYYY-MM-DD_HHMMSS}.sqlite` in `mathQuizSingleDbDir`, using `WrittenColumnSessions` and `WrittenColumnAttempts`.

---

## Sound Effects

| Event | Sound | Where |
|---|---|---|
| Correct answer | `SoundEvents.ENTITY_EXPERIENCE_ORB_PICKUP` | `QuizScreen.submitAnswer()` |
| Wrong answer | `SoundEvents.ENTITY_VILLAGER_NO` | `QuizScreen.submitAnswer()` |
| Rewards granted | `SoundEvents.ENTITY_PLAYER_LEVELUP` | `QuizResultScreen.giveRewards()` |

All sounds are vanilla Minecraft sounds — no custom audio assets. The stubs for these are declared in `stubs/.../SoundEvents.java` for the test compilation path.

---

## Project Structure

```
mathquest/
├── .mod-build.toml               # Per-mod manifest read by the build dispatcher
├── CHANGELOG.md
├── fabric/                       # Fabric gradle root (Gradle 9)
│   ├── gradle.properties         # mod_version (sync with forge/)
│   ├── gradlew
│   ├── common/src/               # Loader-agnostic Java + unit tests (config, quiz, persistence, platform, server, net)
│   ├── shared/src/               # Fabric-specific Java + Fabric API tests
│   └── targets/
│       ├── fabric-26.1.2/        # Primary target
│       └── fabric-1.21.11/       # Preserved capability
├── forge/                        # Forge gradle root (Gradle 8, Java 17)
│   ├── gradle.properties         # mod_version (sync with fabric/)
│   ├── gradlew
│   └── targets/forge-1.20.1/     # M3 complete: popup + NPC mode + SimpleChannel + commands + SQLite
│       └── src/main/java/.../forge/
│           ├── MathQuestForge.java, MathQuestClientForge.java, MathQuestForgeModEvents.java
│           ├── entity/WanderingNerdEntityForge.java, WanderingNerdSpawnerForge.java, WanderingNerdRendererForge.java
│           ├── net/MathQuestNetworkForge.java
│           ├── platform/ForgePlatform*.java
│           └── screen/Quiz*ScreenForge.java
└── tools/                        # GenerateNerdTexture, control_panel_dev.py
```

Other top-level dirs: `docs/`, `stubs/`, `versions/`, `quests/`.

---

## Common vs loader-specific (M2 platform layer)

Loader-agnostic code lives once under `fabric/common/` and is compiled into both Fabric and Forge via extra `srcDir` wiring. **`common/` must not import Minecraft or loader APIs** — pass `PlayerContext` (username + UUID) and call platform interfaces for glue.

**Shared in `common/`** (write once, test in `:common:test`):
- Config, quiz, persistence, NPC catalog, quest defs, control state
- **`control/http/*`** — HTTP control panel core (`MathQuestHttpControlPanelServer`, `MathQuestHttpRouter`, assets resolver, status builder, `ControlPanelBridge`); no loader imports
- `platform/MathQuestPaths`, `platform/MathQuestLog`, `platform/PlatformInventory`, `platform/PlatformServer`, `platform/PlatformNetwork`
- `net/*` neutral payload data records (plain fields — loader trees wrap them in codecs)
- `server/QuizResultProcessor`, `server/OpenQuizPayloadBuilder`

**Loader-specific** (one implementation per loader; keep in tandem):
- Entrypoints: Fabric `MathQuestMod` / `MathQuestClient` vs Forge `MathQuestForge` / `MathQuestClientForge`
- Networking: Fabric `PayloadTypeRegistry` / `ServerPlayNetworking` vs Forge `MathQuestNetworkForge` (`SimpleChannel`)
- Screens, entity/renderer/spawner glue, command registration, key bindings
- Control-panel bridges: `FabricControlPanelBridge` / `ForgeControlPanelBridge` implement `ControlPanelBridge`; Fabric also registers optional HTTP handlers (terrain-map PNG, mob admin tools, `/api/quest/*`). **Quest (`CaveEscapeQuestService`) is Fabric-only and FROZEN past M6.** **On hold for Forge:** written-column quiz screen (fix in Fabric 26.1.2 first), terrain-map panel, mob-spawn admin panel.

Full contract and tandem-development rules: [`../AGENTS.md`](../AGENTS.md).

---

## Source File Details

### Entrypoints

**`MathQuestMod.java`** — Implements `ModInitializer`. Loads config from `mathquest.json` on server/common init. Registers the `GiveRewardPayload` C2S packet type and its server-side handler (looks up the item from the registry and inserts it into the player's inventory). Registers `MathQuestServerCommands`. Holds the static `CONFIG` instance and `LOGGER`.

**`MathQuestClient.java`** — Implements `ClientModInitializer`. In **popup** mode, registers a tick timer that opens `QuizOfferScreen` at the configured interval **only when `MinecraftClient.getServer() != null`** (singleplayer / integrated server); remote multiplayer clients skip the timer. Handles delayed `QuizOfferScreen` after `OpenQuizPayload` (NPC interaction). Registers commands via `MathQuestCommands.register()`. Registers the **`openControlPanelKey`** `KeyMapping` (default key **`K`**, category **`MathQuest`**) via Fabric's `KeyBindingHelper`; on each client tick, `consumeClick()` opens `ControlPanelScreen` **only in singleplayer** (`getSingleplayerServer() != null`) — the hotkey is hidden on remote multiplayer connections. Adds a shutdown hook to close the database. Provides `resetTimer()` to restart the countdown (called when interval changes or mod is re-enabled).

### Forge entrypoints (1.20.1)

**`MathQuestForge.java`** — Forge `@Mod` entrypoint. Loads config, registers `DeferredRegister` entity type (`WanderingNerdEntityForge`), `MathQuestNetworkForge` (`SimpleChannel`), and holds the `WanderingNerdSpawnerForge` singleton. Delegates quiz-result processing to shared `QuizResultProcessor` via `ForgeQuizResultHooks`.

**`MathQuestClientForge.java`** — Client-side Forge entrypoint. Popup-mode client tick timer (integrated server only), **`K` hotkey** opens `ControlPanelScreenForge` in singleplayer, `MathQuestClientCommandsForge` for tab-complete `/mathquest`, opens quiz screens from S2C `OpenQuizPacket`, `despawnNearbyNerds()` for NPC cleanup, public `resetTimer()`.

**`MathQuestForgeModEvents.java`** — Mod-bus listeners: `EntityAttributeCreationEvent`, `EntityRenderersEvent.RegisterRenderers` (client), `RegisterKeyMappingsEvent` (client, `OPEN_PANEL_KEY` default **K**).

**`WanderingNerdEntityForge.java`** — Forge 1.20.1 NPC entity (`PathfinderMob`). Synced persona id, invulnerable, book in hand, despawn timer, `mobInteract` → greeting + S2C open-quiz.

**`WanderingNerdSpawnerForge.java`** — Overworld server-tick spawner using shared `NpcSpawnPlanner` for target selection.

**`WanderingNerdRendererForge.java`** — Classic 1.20.1 `MobRenderer` with `VillagerModel`; texture from `MathQuestNpcCatalog` (glasses baked into PNG assets, no feature renderer).

**`MathQuestNetworkForge.java`** — Forge `SimpleChannel` with C2S `GiveRewardPayload`, C2S `QuizResultPayload`, C2S `DespawnNerdsPacket`, S2C `OpenQuizPayload`, and S2C **`FluencyFeastResultPacket`**. Server handlers enqueue work on the server thread and call shared processors + platform impls. The client-side channel predicate remains exact (`PROTOCOL::equals`). The server-side predicate uses `NetworkRegistry.acceptMissingOr(PROTOCOL)`, so a vanilla/unmodded client without the MathQuest channel can join but receives no MathQuest UI or protocol support; any client advertising the MathQuest channel must use the exact protocol version. Other required server-mod channels can still reject an unmodded client.

**`ForgePlatformInventory` / `ForgePlatformNetwork` / `ForgePlatformPlayers`** — Forge implementations of the common platform interfaces.

**`QuizOfferScreenForge.java`** — Forge quiz entry screen. Both popup (`payload == null`) and NPC (`OpenQuizPacket`) paths resolve the same quiz via shared `OpenQuizPayloadBuilder.create(playerName)` → `OpenQuizData` → `QuizManager` + `QuizSessionOptions` (including fluency feast). Written-column type opens **`WrittenColumnQuizScreenForge`**; results submit via C2S `QuizResultPacket` → `QuizResultProcessor.processWrittenColumn`.

**`WrittenColumnQuizScreenForge.java`** — Forge 1.20.1 paper-column quiz UI (port of Fabric `WrittenColumnQuizScreen`). **On hold** — known issues; troubleshoot in Fabric 26.1.2 before Forge acceptance testing. Code remains for config-gated `written_column_arithmetic` quiz type.

**`QuizScreenForge.java`** — Full layout parity with Fabric `QuizScreen` (26.1.2) on 1.20.1 APIs: 3× problem text, styled answer box (2× input), feedback positioned under the answer box, quit save/abandon, skip/flag controls with flag panel, pause overlay, progress and source label; driven by `QuizSessionOptions`.

**`QuizResultScreenForge.java`** — Result + reward screen. Standard quizzes: C2S reward + local SP export (or MP server path). **Fluency feast:** sends C2S result with `fluencyFeastMode`; server runs shared `QuizResultProcessor` and returns S2C `FluencyFeastResultPacket` for before→after % readout, FF reward-group choice, and fluency-improvement grant. NPC despawn on "Back to Adventure!" when in NPC mode.

**`ControlPanelScreenForge.java`** / **`PlayerSettingsScreenForge.java`** — Forge 1.20.1 in-game settings UI (parity with Fabric `ControlPanelScreen` / `PlayerSettingsScreen`). Opens on **K** in singleplayer; edits local `mathquest.json`.

### Config

**`MathQuestConfig.java`** — POJO serialized to/from `mathquest.json` in the Fabric config dir via Gson. Fields and defaults:

| Field | Type | Default | Description |
|---|---|---|---|
| `quizIntervalSeconds` | int | 30 | Seconds between quiz offers |
| `problemsPerQuiz` | int | 5 | Questions per quiz session |
| `minNumber` | int | 0 | Minimum operand (global default; players without a preset use `minNumber`–`maxNumber` and `operation`) |
| `maxNumber` | int | 9 | Maximum operand (global default) |
| `operation` | String | `"multiplication"` | Global default: `addition`, `subtraction`, `multiplication`, or `exponentiation` |
| `playerPresets` | Map\<String, PlayerQuizPreset\> | three family defaults (see below) | Per-player operation, range, and optional problem-count overrides; keys are **lowercase** player names |
| `playerQuizTypes` | Map\<String, String\> | family defaults: `standard_arithmetic` | Per-player quiz type: `standard_arithmetic` or `written_column_arithmetic`; keys are lowercase player names |
| `playerNpcSelections` | Map\<String, String\> | family defaults: `wandering_nerd` | Per-player selected NPC id for the local web control panel |
| `playerNpcLocks` | Map\<String, Boolean\> | family defaults: `true` | Per-player Lock to player default for the local web control panel and automatic NPC spawns |
| `playerTpCreditEarningEnabled` | Map\<String, Boolean\> | empty / `false` | Per-player opt-in for earning TP credits on completed quizzes |
| `playerTpCreditsPerQuiz` | Map\<String, Integer\> | empty / `1` | Per-player completed-quiz award amount, clamped to 1–100 |
| `playerTpCreditBalances` | Map\<String, Integer\> | empty / `0` | Persistent nonnegative per-player TP-credit balance |
| `playerTpCreditRewardChoices` | Map\<String, String\> | empty / `teleport` | Per-player spend choice; `teleport` is currently the supported choice and costs one credit |
| `writtenColumnEvaluatorCode` | String | `"paper"` | Adult/evaluator code entered before recording written-column paper work |
| `npcDialogueOverrides` | Map\<String, List\<String\>\> | empty | Runtime dialogue overrides saved by the local web control panel, keyed by NPC id |
| `rewards` | List\<RewardEntry\> | diamond ×1, golden_apple ×2, enchanted_golden_apple ×1 | Flat reward list when **`rewardGroup`** is unset |
| `rewardGroups` | Map\<String, RewardGroup\> | includes **`jtree`** (mode `random`) | Named groups of item stacks plus per-group mode (`all` / `random` / `choose`) |
| `rewardGroup` | String | `"jtree"` on fresh default | Active group id, or null/blank to use **`rewards`** only |
| `playerRewardGroups` | Map\<String, String\> | empty | Per-player group name override (control panel Reward item field when value matches a group) |
| `rewardMode` | String | "random" | For **flat** `rewards` only: "random" (one entry) or "all" (every entry). Groups use their own **`mode`**. |
| `enabled` | boolean | true | Whether the mod timer is active |
| `excludeMultipartFromClientProjectileHits` | boolean | true | **Forge client:** skip Forge `PartEntity` and Ice and Fire `EntityMutlipartPart` hitboxes in projectile picking (dragon/trident freeze workaround). Server collision unchanged. Toggle `/mathquest multipartProjectileFix on\|off`. |
| `quizMode` | String | "popup" | "popup" (timed overlay) or "npc" (Wandering Nerd) |
| `npcSpawnRadiusBlocks` | int | 10 | K2 spawn distance from player in NPC mode |
| `npcDespawnSeconds` | int | 120 | How long the nerd stays before despawning |
| `npcAllowMultipleNerds` | boolean | false | When false, a targeted control-panel spawn replaces any active nerd assigned to the same player. |
| `npcSpawnTargetMode` | String | `"all"` | `all`, `random`, or `one` — who receives automatic nerd spawns (see NPC Mode section) |
| `npcSpawnTargetPlayer` | String | null | Lowercase username; used only when `npcSpawnTargetMode` is `one` |
| `controlPanelEnabled` | boolean | true | Starts the localhost web control panel with the dedicated server. |
| `controlPanelHost` | String | `"127.0.0.1"` | Bind host for the local web control panel. |
| `controlPanelPort` | int | 8765 | HTTP port for the local web control panel. |
| `controlPanelAssetsDir` | String | null | Optional MathQuest asset root for disk-first control-panel hot reload. Point at `assets/mathquest`; HTML/CSS/JS and NPC preview PNG files are served from disk first with jar fallback. Leading `~` is expanded. |
| `sharedDataDir` | String | `"~/Documents/Code/mathquest-server/config"` | Where MathQuest writes the legacy `mathquest_data.db`. Leading `~` is expanded to the user home. When unset, the Fabric config dir is used. Lets singleplayer and the dedicated server share one local DB directory. Pre-1.4 configs auto-migrate to this default on first load. |
| `mathQuizSingleDbDir` | String | `"~/Documents/Code/fof-mono/apps/math-quiz/_data/_single-session-sqlite-files"` | Where MathQuest writes canonical single-session SQLite exports for math-quiz intake. Leading `~` is expanded to the user home. When unset or unwritable, falls back to `resolveDataDir()/mathquest_sessions`. Legacy JSON key `mathQuizExportDir` still loads. The 1.6.0 default `_data/mathquest` auto-migrates to this folder on load. |
| `mathQuizActiveDbDir` | String | `"~/Documents/Code/fof-mono/apps/math-quiz/_data/tlkids"` | Per-player active fluency DB folder (`math-flu_<name>_*.sqlite`) updated by the Python ingest bridge after each quiz. Legacy JSON key `mathQuizActiveDir` still loads. |
| `playerRealNames` | Map\<String, String\> | family defaults plus `skulkscraper -> Guest` | Editable Minecraft-player to real-name mapping used for internal math-quiz list lookup and SQLite export filenames/user rows |

`RewardEntry` has fields `String item` (e.g. `"minecraft:diamond"`) and `int count`.

`PlayerQuizPreset` has optional fields `Integer minNumber`, `Integer maxNumber`, `String operation`, and `Integer problemsPerQuiz`. Any field omitted (null) inherits from the global defaults. Default `playerPresets` ship with: `wildpetal` → 5–9 multiplication; `treasurehunterm` → 0–3 addition; `pumajockey` → 0–4 exponentiation.

**`MathQuestConfig.resolveForPlayer(String playerName)`** returns an `EffectiveQuizParams` record used to build the quiz.

**`MathQuestConfig.resolveActiveRewardPlan()`** / **`resolveRewardPlanForPlayer()`** return entries plus mode for quiz rewards. **`resolveActiveRewardEntries()`** remains a thin wrapper returning entries only.

**Control-panel static assets** can be served from disk by setting `controlPanelAssetsDir` to the MathQuest asset root. The embedded server maps `/`, `/index.html`, `*.html/css/js`, and `/npc/*.png` through a traversal-guarded disk lookup first, then falls back to bundled jar assets. The development proxy at `tools/control_panel_dev.py` serves the same live files on `127.0.0.1:8766` and proxies `/api/*` to the running mod server on `127.0.0.1:8765`.

### Quiz Logic

**`QuizManager.java`** — Generates `problemsPerQuiz` random problems from resolved `EffectiveQuizParams` or accepts an explicit ordered problem list from math-quiz SQLite. Random operands are integers in `[minNumber, maxNumber]` inclusive. **Addition:** `factorA + factorB`. **Subtraction:** `factorA - factorB`. **Multiplication:** `factorA * factorB`. **Division:** integer `factorA / factorB`. **Exponentiation:** `factorA` raised to `factorB` (iterated integer power; `0^0` is treated as `1`). Tracks `currentIndex`, `correctCount`, and `operation` string. Key methods:
- `submitAnswer(long)` — records answer, returns boolean correct/wrong.
- `advanceToNext()` — increments the problem index.
- `isQuizComplete()` — true when all problems answered.
- `fromCompletedProblems(operation, problemList, correctCount)` — static factory for reconstructing a completed quiz on the server side (used by `QuizResultPayload` handler).
- `Problem` inner class: `operation`, `factorA`, `factorB`, `correctAnswer` (long), `playerAnswer` (Long), `isCorrect`, `responseTimeMs`; factory `Problem.create(...)`.

### Screens

**`QuizOfferScreen.java`** — Simple prompt with "Let's Go!" and "Not Now" buttons. Has two constructors: a no-arg constructor (popup timer, singleplayer — resolves params from local config) and a params constructor (payload-triggered — uses server-provided `EffectiveQuizParams`). On accept, checks for a mapped math-quiz problem list, creates a `QuizManager` from that list when available, otherwise creates one from the appropriate params, then opens `QuizScreen`.

**`QuizScreen.java`** — The main quiz UI. Number pad built from `ButtonWidget`s. Input buffer accumulates typed digits. Features:
- Auto-accept when typed number matches correct answer.
- 1.5-second feedback display (`FEEDBACK_DURATION_MS`).
- Sound on correct (XP orb pickup) and wrong (villager no).
- Quit confirmation flow with Escape key or Quit button.
- Keyboard input: digit keys (top row + numpad), backspace, enter/numpad-enter.
- On quiz completion, opens `QuizResultScreen`.

**`QuizResultScreen.java`** — Displays score and encouragement. Calls `giveRewards()` once on init:
- Redeems one server-issued TP-credit completion token; the request carries no amount, and the server applies the per-player opt-in and award amount exactly once.
- Resolves the reward plan via server payload (`rewardMode` + entries) or local `resolveRewardPlanForPlayer()`; applies group mode (`all`, `random`, or `choose` with inline pick buttons).
- Grants items by sending a `GiveRewardPayload` C2S packet per reward entry (server creates the items).
- Plays level-up sound on reward.
- **Multiplayer:** sends quiz results to the server via `QuizResultPayload` (C2S JSON). The server records the session to its DB and exports the math-quiz-compatible single-session SQLite file. The client skips local DB/export writes.
- **Singleplayer:** records session end in the local database and exports the single-session SQLite file locally.

**`ControlPanelScreen.java`** — In-game settings UI that mirrors most `/mathquest` commands as cycle-buttons and increment/decrement controls. Opened with the **`K`** hotkey (rebindable in vanilla **Options → Controls** under category "MathQuest") or any other binding the user assigns. Renders only stock widgets (`Button`, `CycleButton`, `StringWidget`) so the same source compiles for both `fabric-1.21.11` and `fabric-26.1.2` without target-local rendering overrides. Controls:
- **Quizzes Enabled** (on/off cycle).
- **Quiz Mode** (popup / Wandering Nerd cycle).
- **Operation** (addition / subtraction / multiplication / exponentiation cycle — global default).
- **Problems** (cycle: **5 / 10 / 15** problems per quiz).
- **Interval** (cycle: 15 s / 30 s / 1 min / 2 min / 5 min).
- **Nerd Spawn** (all / random / one cycle).
- **Default range** (Min ± / K2 ± buttons with live value label).
- **Reward Pool** (cycle through `rewardGroups` keys plus a `(flat list)` option, with the active reward stacks summarized below).
- **Player Presets** read-only summary list (up to 4 visible; "+N more..." indicator beyond that).
- **Add Me as Preset** (creates an empty preset keyed to the local client's username).
- **Edit Player Presets...** opens `PlayerSettingsScreen`.
- **Start Quiz Now** triggers the same flow as `/mathquest start` (NPC spawn or popup depending on mode).
- **Done** closes the screen.

Every cycle change saves `mathquest.json` immediately and calls `MathQuestClient.resetTimer()` for fields that affect the popup cadence. **Edits are local only** — they do not currently sync from a LAN host to remote clients (see **Known Limitations**).

**`PlayerSettingsScreen.java`** — Per-player preset editor reachable from the control panel. One row per player in `playerPresets`, each row showing:
- Player name (left).
- **Operation** cycle: `(default)`, `addition`, `subtraction`, `multiplication`, `exponentiation` — `(default)` clears the preset's operation so it inherits the global default.
- **Min ± / K2 ±** buttons with a live `min – max` label between them. Changing min/max from `(default)` materializes the preset's range from the global defaults.
- **Remove** button (deletes the entry).

Bottom row buttons:
- **Add Me** — adds the local client's username as an empty preset.
- **Add Default Family** — re-creates the family presets (`wildpetal`, `treasurehunterm`, `pumajockey`) if any are missing, leaving any existing entries alone.
- **Back** — returns to the control panel.

### Entity (NPC Mode)

**`WanderingNerdEntity.java`** — Custom `PathAwareEntity` subclass. This is the shared NPC entity that triggers quizzes in NPC mode; its selected persona id is synced to clients so the rendered texture, name, and dialogue can vary by `MathQuestNpcCatalog` entry. Uses wandering AI goals (SwimGoal, LookAtEntityGoal, WanderAroundGoal, LookAroundGoal). Holds a book in its main hand. Is invulnerable and cannot be leashed. When right-clicked (`interact`), sends an `OpenQuizPayload` S2C packet to the interacting player; the entity is **not** discarded on click so the NPC remains visible until the normal despawn timer or client-side cleanup. Has a despawn timer (`npcDespawnSeconds × 20` ticks).

**`MathQuestNpcCatalog.java`** — Central catalog for selectable NPC personas. It defines the id, display name, entity type label, texture path, and default single-line dialogue strings for The Wandering Nerd, Professor Pi, Countess Calc, Geo Sage, and Paper Coach Penny. The dedicated-server web control panel uses this same catalog for its NPC gallery and overlays saved dialogue edits from `MathQuestConfig.npcDialogueOverrides`.

**`WanderingNerdRenderer.java`** — Client-side renderer. Extends `MobRenderer` with a villager model and a custom `MathQuestVillagerRenderState`. It resolves the synced NPC persona id through `MathQuestNpcCatalog` so The Wandering Nerd, Professor Pi, Countess Calc, Geo Sage, and Paper Coach Penny render with their selected texture. Nerd glasses are **baked into the persona PNG textures** (see `tools/GenerateNerdTexture.java`); there is no separate feature-renderer layer.

**`WanderingNerdSpawner.java`** — Server-side spawner registered on `ServerTickEvents.END_WORLD_TICK`. Tracks a tick counter. Every `quizIntervalSeconds` (only when the mod is enabled and `quizMode` is `npc`), selects target player(s) via shared **`NpcSpawnPlanner.selectTargetNames`** using `npcSpawnTargetMode`: **all** loops every online overworld player; **random** picks one random online player; **one** resolves `npcSpawnTargetPlayer` by case-insensitive name among online players. For each selected player, if no nerd already exists within `npcSpawnRadiusBlocks`, spawns a `WanderingNerdEntity` at a random offset (minimum distance enforced inside `spawnNerdAt`). Picks a random surface position on solid ground.

The entity type `WANDERING_NERD` is registered in `MathQuestMod` with `Registry.register()` and `FabricDefaultAttributeRegistry`. The renderer is registered in `MathQuestClient` via `EntityRendererRegistry.register()`.

### Networking

**`GiveRewardPayload.java`** — A `CustomPayload` record (`itemId`, `count`) sent C2S to request reward items. Registered in `MathQuestMod.onInitialize()` via `PayloadTypeRegistry.playC2S()`. The server-side handler in `MathQuestMod` resolves the item from `Registries.ITEM` and inserts it into the `ServerPlayerEntity`'s inventory with `offerOrDrop`. This ensures reward items are real server-side items that persist across sessions and have full functionality (food restores hunger, tools have durability, etc.).

**`OpenQuizPayload.java`** — A `CustomPayload` record sent S2C to tell the client to open the quiz offer screen. Carries server-resolved quiz parameters: `operation` (String), `minNumber` (int), `maxNumber` (int), `problemsPerQuiz` (int), explicit problem-list JSON, reward JSON, reward mode, and quiz type. The server calls `MathQuestConfig.resolveForPlayer(playerName)` and `resolveQuizType(playerName)` before sending, so per-player presets, problem lists, rewards, and quiz type are applied server-side. Registered in `MathQuestMod.onInitialize()` via `PayloadTypeRegistry.playS2C()`. The client-side handler in `MathQuestClient` stores the params and opens `QuizOfferScreen` with server-provided settings.

**`QuizResultPayload.java`** — A `CustomPayload` record (`resultJson` String) sent C2S when a quiz completes in multiplayer. The JSON carries operation, problem count, correct count, reward description, and per-problem detail (operation, factors, answers, correctness, response time). The server handler in `MathQuestMod` deserializes the JSON, writes to the server-side `mathquest_data.db`, and exports a single-session SQLite file. Registered in `MathQuestMod.onInitialize()` via `PayloadTypeRegistry.playC2S()`.

**`DespawnNerdsPayload.java`** — An empty `CustomPayload` record sent C2S when the client dismisses a quiz ("Not Now" on `QuizOfferScreen` or "Back to Adventure!" on `QuizResultScreen`) on a multiplayer server. The server handler in `MathQuestMod` removes Wandering Nerd entities within ~50 blocks of the requesting player. In singleplayer the client cleans up nerds directly on the integrated server and does not send this payload. Registered in `MathQuestMod.onInitialize()` via `PayloadTypeRegistry.playC2S()`.

**`EarnTpCreditsPayload.java`** — A C2S completion request carrying only the opaque one-use session token issued with the delivered quiz payload. It deliberately carries no amount. The token begins pending; successful server result processing marks it complete, while a partial result cancels it. The earn handler atomically consumes only a completed, player-bound token, reads `playerTpCreditEarningEnabled` and `playerTpCreditsPerQuiz`, awards through shared `TpCreditBank`, persists the balance, and sends earned/new-balance chat feedback. Read-only delivery previews never issue tokens.

**Forge networking (`MathQuestNetworkForge.java`):** Forge `SimpleChannel` mirror of the Fabric payload set (give-reward C2S, quiz-result C2S, open-quiz S2C, **despawn-nerds C2S**, **earn-TP-credits C2S**). Payload *data* records live in `common/.../net/`; Forge wraps them in `FriendlyByteBuf` encode/decode. Server handlers call shared `QuizResultProcessor`, `ForgeQuizResultHooks`, and `TpCreditBank`. The TP-credit packet raises the exact modded-client protocol from 1 to 2. Since v1.24.2, the server accepts the exact protocol or Forge's missing/vanilla channel markers, while the client accepts only the exact protocol. This lets unmodded clients join without MathQuest UI/protocol support; it does not relax any other mod's required channels.

### Data

**`QuizDatabase.java`** — Singleton wrapping a SQLite connection to `mathquest_data.db`. Two tables:
- `sessions`: id, started_at, ended_at, problems_total, problems_correct, reward_given.
- `answers`: id, session_id, question_index, factor_a, factor_b, correct_answer, player_answer, is_correct, response_time_ms, answered_at.

**`SessionExporter.java`** — Exports a completed quiz as a single-session SQLite file compatible with the math-quiz app. Written to `mathQuizSingleDbDir` (default `~/Documents/Code/fof-mono/apps/math-quiz/_data/_single-session-sqlite-files`) with fallback to `resolveDataDir()/mathquest_sessions`. Runtime callers pass the resolved real name, so the filename pattern is `mathquest_{real-name}_{YYYY-MM-DD}_{HHMMSS}.sqlite`. Schema contract: `apps/math-quiz/docs/2026-06-20_minecraft-mod-single-session-sqlite-spec.md`.

**`MathQuizSessionIngestor.java`** — After export, runs the bundled Python ingest script to append the session into the player's active DB under `mathQuizActiveDbDir`. Uses `SqliteDriver.requireLoaded()` — Forge requires the jarJar `-all.jar` deploy artifact so sqlite-jdbc is on the classpath.

**`WrittenColumnSessionExporter.java`** — Exports adult-evaluated paper practice as a separate SQLite file in `mathQuizSingleDbDir`. Runtime callers pass the resolved real name, so the filename pattern is `mathquest_written_column_{real-name}_{YYYY-MM-DD_HHMMSS}.sqlite`. Schema tables: `WrittenColumnSessions` and `WrittenColumnAttempts`, including prompt text, operation, operands, correct answer, student answer text, evaluator code acceptance, evaluation (`correct`, `partial`, `needs_work`), notes, and response time.

**`MathQuizProblemListLoader.java`** — Loads ordered problem lists from math-quiz SQLite files for mapped Minecraft players. The built-in/default mapping is `rjcomp -> Randy`, `TreasureHunterM -> K2`, `PumaJockey -> TL`, `SkulkScraper -> Guest`, and `WildPetal -> Kid1`; runtime control-panel edits are stored in `playerRealNames` and override those defaults. The default source folder is `~/Documents/Code/fof-mono/apps/math-quiz/_data/tlkids`. For each real name it chooses the most recently modified `math-flu_<name>_*.sqlite` file, selects the next queued `ProblemLists` row for that user, reads ordered `ProblemListItems`, and falls back to generated quiz params when no usable list is available.

### Commands

**`MathQuestCommands.java`** — Registers **client-side** `/mathquest` commands via `ClientCommandRegistrationCallback`. All commands that change settings write `mathquest.json` immediately. In singleplayer, the server-side commands (from `MathQuestServerCommands`) shadow these but behave equivalently.

**`MathQuestServerCommands.java`** — Registers **server-side** `/mathquest` commands via `CommandRegistrationCallback`. All commands require **COMMANDS_GAMEMASTER** (op level 2+). Modifies the server's `mathquest.json`. **`start` / `start <player>` / `start all`** honor **quiz mode**: in **NPC** mode they **force-spawn** Wandering Nerds (or one nerd per player for `start all`); in **popup** mode they send **`OpenQuizPayload`** instead.

**`MathQuestHttpControlPanelServer.java`** *(common)* — JDK `HttpServer` lifecycle (start/stop on dedicated server when `controlPanelEnabled`). Dispatches all requests through **`MathQuestHttpRouter`**, which registers core routes (`GET /api/status`, `POST /api/config`, `POST /api/spawn`, `POST /api/open`, `POST /api/vanish`, static assets) and exposes `register(method, path, handler)` for loader-supplied optional routes. **`ControlPanelBridge`** (implemented by `FabricControlPanelBridge` / `ForgeControlPanelBridge`) supplies game-thread spawn/vanish/open-quiz/world primitives. Fabric registers optional handlers for terrain-map PNG, mob admin tools, and quest APIs; Forge registers core routes only. Static assets: `assets/mathquest/control_panel/` (Fabric shared + Forge copy). See `docs/CONTROL_PANEL.md`.

Root literal: **`mathquest`**. Below, each **`##`** heading is one command path (or family) with parameters and behavior.

## Client Commands
### `/mathquest interval <seconds>`

- **`<seconds>`:** integer **≥ 5** (Brigadier enforces the minimum).
- **Effect:** Sets `quizIntervalSeconds` and calls `MathQuestClient.resetTimer()` for popup mode.

### `/mathquest problems <count>`

- **`<count>`:** integer **1–50** (Brigadier enforces both bounds).
- **Effect:** Sets the **global** `problemsPerQuiz`. Read each time a new quiz starts, so the change takes effect on the very next quiz with no restart needed.
- **Scope:** **Global only.** There is no per-player override for the number of problems — the `/mathquest player <name>` subcommand tree only supports `operation`, `range`, and `clear`. Every player on the server gets `problemsPerQuiz` problems per quiz, regardless of their `playerPresets` entry. (Per-player problem counts can be added later by extending `PlayerQuizPreset` if needed.)
- **From server console:** `mathquest problems 7` (no leading slash). From a player chat: `/mathquest problems 7` — but only an op can run this on a dedicated server; non-op clients in multiplayer get the "use server-side commands" rejection.

### `/mathquest reward <item> [count]`

- **`<item>`:** namespaced ID or short name (e.g. `diamond` → `minecraft:diamond`).
- **`[count]`:** optional integer **1–64**; default **1** if omitted.
- **Effect:** Replaces **`rewards`** with a **single** entry, sets **`rewardMode`** to **`"all"`**, clears **`rewardGroup`** (so the flat list is used).

### `/mathquest status`

- **Effect:** Prints enabled state, quiz mode, interval, NPC radius/despawn (if NPC mode), NPC auto-spawn target, problems per quiz, default operation and range, `playerPresets`, **`rewardMode`**, whether the pool is a **bundle** or **flat list**, and the **active reward entries** (from `resolveActiveRewardEntries()`).

### `/mathquest enable`

- **Effect:** Sets `enabled` to true, saves, resets timer when enabling.

### `/mathquest disable`

- **Effect:** Sets `enabled` to false, saves.

### `/mathquest mode popup` and `/mathquest mode npc`

- **Literals:** exactly **`popup`** or **`npc`** (no other values).
- **Effect:** Sets `quizMode`, saves, resets timer.

### `/mathquest start`

- **Effect:** **NPC mode:** queues a Wandering Nerd spawn near the **local** player on the integrated server (single-player / LAN client with server). **Popup mode:** opens `QuizOfferScreen` on the client.

### `/mathquest operation addition` — or `subtraction`, `multiplication`, or `exponentiation`

- **Literals:** only **`addition`**, **`subtraction`**, **`multiplication`**, **`exponentiation`**.
- **Effect:** Sets global default **`operation`** (normalized internally).

### `/mathquest range <min> <max>`

- **`<min>` `<max>`:** any integers (operand bounds); if **`min > max`** they are **swapped** when saved.
- **Effect:** Sets global **`minNumber`** and **`maxNumber`**.

### `/mathquest player <name> operation addition` — or `subtraction`, `multiplication`, or `exponentiation`

- **`<name>`:** player name for the preset (stored **lowercase**); quote if it contains spaces.
- **Literals:** **`addition`**, **`subtraction`**, **`multiplication`**, **`exponentiation`** only.
- **Effect:** Sets or merges **`playerPresets`** entry: **`operation`**.

### `/mathquest player <name> range <min> <max>`

- **Integers:** swapped if **`min > max`** when saved.
- **Effect:** Sets preset **`minNumber`** / **`maxNumber`** for that player.

### `/mathquest player <name> clear`

- **Effect:** Removes that player’s entry from **`playerPresets`**.

### `/mathquest npcspawn all`

- **Effect:** Sets **`npcSpawnTargetMode`** to **`all`**, clears **`npcSpawnTargetPlayer`**. Each interval, every online **overworld** player gets a spawn attempt (if no nerd nearby).

### `/mathquest npcspawn random`

- **Effect:** Sets **`npcSpawnTargetMode`** to **`random`**, clears **`npcSpawnTargetPlayer`**. Each interval, **one** random online overworld player gets a spawn attempt.

### `/mathquest npcspawn only <name>`

- **`<name>`:** case-insensitive Minecraft username; stored **lowercase**.
- **Effect:** Sets mode to **`one`** and **`npcSpawnTargetPlayer`**. Only that player gets automatic spawns when online **in the overworld**.

### `/mathquest group <name>`

- **`<name>`:** lowercase group id defined in **`rewardGroups`** (e.g. **`jtree`**). Unknown names error and list known keys.
- **Effect:** Sets **`rewardGroup`** to that id. The group's own **`mode`** controls how rewards are granted (see Gameplay → Rewards).

### `/mathquest group clear`

- **Effect:** Clears **`rewardGroup`** (null); rewards use the flat **`rewards`** list again.

**Notes:** Client commands run on the **client** and edit the client's local **`mathquest.json`**. In **singleplayer**, the server-side commands (below) shadow these and behave equivalently since both share the same `CONFIG` instance. In **multiplayer** (connected to a dedicated server), all config-changing client commands are **blocked** with a message directing the user to ask the server operator. Only `/mathquest status` and `/mathquest start` remain functional on the client in multiplayer.

Most of these settings are also editable through the in-game **Control Panel** (default hotkey **`K`**) — including the per-player **Quiz source** selector (`generated`, internal problem list, internal quick quiz, internal fluency feast) on both Fabric and Forge — see `ControlPanelScreen` / `ControlPanelScreenForge` and `PlayerSettingsScreen` under **Screens**.

## Server Commands

**`MathQuestServerCommands.java`** — Registers server-side `/mathquest` commands via `CommandRegistrationCallback`. All commands require **COMMANDS_GAMEMASTER** permission (op level 2+). These commands modify the **server's** `mathquest.json` and take effect immediately for server-side behavior (NPC spawning, interval timing, etc.).

The server command tree mirrors the client commands: `interval`, `problems`, `mode`, `operation`, `range`, `player <name> {operation|range|clear}`, `npcspawn {all|random|only <name>}`, `group {<name>|clear}`, `start`, `status`, `enable`, `disable`, `vanishnerds`.

TP-credit teleport commands are separate non-op roots available to ordinary players on both Fabric and Forge. Vanilla `/tp` is unchanged:

- `/tpc <online-player>` — teleport to that player's position/dimension for 1 credit.
- `/tpc <x> <y> <z>` — teleport to validated absolute coordinates in the current dimension for 1 credit.
- `/tpt` → TreasureHunterM, `/tpp` → PumaJockey, `/tpr` → RJComp, `/tpw` → WildPetal.
- A teleport is attempted only when the destination is valid and the player has a credit. The balance is deducted after a successful teleport, and the command reports the remaining balance.

### `/mathquest start` (server, no args)

When executed by a player: in NPC mode, force-spawns a Wandering Nerd nearby; in popup mode, sends `OpenQuizPayload` to the executing player.
When executed from the server console or RCON: prints an error directing the operator to use `/mathquest start <player>`.

### `/mathquest start <player>`

Targets the named **online** player. In **NPC** mode, **force-spawns** a Wandering Nerd near them. In **popup** mode, sends **`OpenQuizPayload`** so their client opens the quiz offer screen (bypasses walking to a nerd). If the player is not online, the command fails with an error.

### `/mathquest start all`

In **NPC** mode, **force-spawns** a Wandering Nerd near **each** online player (each gets a spawn attempt). In **popup** mode, sends **`OpenQuizPayload`** to **all** online players.

These targeted start commands are the building blocks for the DM dashboard (Phase 3) — they let an op or RCON trigger quizzes on specific players from anywhere.

### `/mathquest vanishnerds`

Removes **all** Wandering Nerd entities from the overworld. Reports the count of removed nerds. Useful for DM cleanup when too many nerds have accumulated or when starting a fresh session. Op-gated (permission level 2+).

### Control Panel on remote multiplayer

When the client is connected to a **remote multiplayer server** (`getSingleplayerServer() == null`), the **`K` hotkey** is **hidden** — pressing it has no effect. The Control Panel only edits the client's local `mathquest.json` which does not sync to the server, so showing it on a remote server would be misleading. Use the server-side `/mathquest` commands instead.

## Control Panel UI Propagation

The Control Panel writes only the local installation's `mathquest.json`; there is no config sync packet yet. On a LAN host, the Minecraft client and integrated server share the same in-process `MathQuestMod.CONFIG`, so host edits affect **server-side world behavior** such as Wandering Nerd auto-spawns. Remote LAN players still build their quiz screens, presets, and rewards from **their own** local `mathquest.json`.

When reviewing or changing the UI, treat the visible controls this way:

- **Quizzes Enabled** — Host change works for shared **NPC auto-spawn** because the server spawner checks the host's `enabled` flag. It also controls the host's own popup timer in single-player / LAN host play. It does **not** toggle remote players' local configs, and existing nerd interactions can still open the remote player's local quiz screen.
- **Quiz Mode** — Host change works for shared world spawning: `npc` enables server-side Wandering Nerd scheduling; `popup` means the host can get timed popups but remote LAN clients do not get timed popups from the host. Remote clients do not automatically switch their local mode.
- **Interval** — Host change works for host popup timing and server-side NPC auto-spawn timing. Remote clients do not receive the changed value locally; it only affects them indirectly by changing when the host/server spawns Wandering Nerds.
- **Nerd Spawn** — Host change works for shared NPC auto-spawn targeting (`all`, `random`, `one`) because `WanderingNerdSpawner` runs on the host's integrated server and reads the host config. The `one` target name must be present in the host's config.
- **Start Quiz Now** — In NPC mode, this works only from the LAN host / single-player process because it requires `getSingleplayerServer()` to force-spawn a nerd near the local server player. A remote LAN client cannot force a server nerd this way. In popup mode, it opens a quiz only for the player who pressed it and uses that player's local config.
- **Operation** — Requires each player to change locally if it should affect their own quiz questions. Host changes only affect the host's quizzes and any players using the same config file; a remote player who receives an NPC-triggered offer still creates `QuizManager` from their own local `MathQuestMod.CONFIG`.
- **Problems** — Requires each player to change locally. The number of questions is read when that player's client creates the quiz.
- **Default range (Min/K2)** — Requires each player to change locally for quiz difficulty. Host range edits do not affect remote players' quiz generation unless config sync is added later.
- **Reward Pool** — Requires each player to change locally for the reward shown/requested at quiz completion. Rewards are selected on the client in `QuizResultScreen` from that client's active reward pool, then requested from the server with `GiveRewardPayload`.
- **TP credits** — Server-authoritative and configured per player. Each player card shows the live persistent balance plus **Earn TP credits**, **Credits per quiz**, and **Reward choice**. The browser never edits the balance directly; quiz completion and successful spend commands mutate it on the server.
- **Player Presets summary / Add Me as Preset / Edit Player Presets** — Requires each player to change locally. Presets are keyed by lowercase player name, but they are resolved from the local client's config when the quiz starts. Editing `wildpetal` on the host does not change `wildpetal`'s quiz on a separate LAN computer.
- **Add Default Family** in `PlayerSettingsScreen` — Requires each player to run locally if they need those preset entries in their own config. It only fills missing entries in the local `playerPresets` map.
- **Remove / per-player Operation / per-player Min-K2** in `PlayerSettingsScreen` — Requires local changes on the player machine whose quiz should change. Host edits are useful as host-local defaults or documentation of desired presets, but they are not enforced for remote clients.
- **Done / Back** — Local UI navigation only; no gameplay propagation.

Practical LAN rule: use the host's panel for **world timing and Wandering Nerd targeting**; use each player's own panel/config for **their quiz content, preset difficulty, problem count, and rewards**. **On a dedicated server** (Phase 2+), the server is fully authoritative for quiz content — use server-side `/mathquest` commands instead. The Control Panel is hidden on remote multiplayer connections and client-side config commands are blocked.

---

## Stubs

The `stubs/` directory contains minimal no-op implementations of Minecraft and Fabric API classes. These exist so the project can compile and run unit tests in environments where the full Fabric toolchain is unavailable (e.g., a proxy-blocked CI server). The stubs are **not used** during normal Fabric Loom builds — they are only relevant for the dual-mode build path (currently frozen in `*.dual-mode` files).

When you add a new Minecraft API reference to the mod source code, you should also add the corresponding stub if it doesn't exist. Current stubs cover: `MinecraftClient`, `Screen`, `DrawContext`, `ButtonWidget`, `TextRenderer`, `KeyInput`, `PlayerEntity`, `PlayerInventory`, `Item`, `ItemStack`, `Registries`, `Registry`, `Identifier`, `Text`, `MutableText`, `Formatting`, `SoundEvent`, `SoundEvents`, `CustomPayload`, `PacketCodec`, `PacketCodecs`, `RegistryByteBuf`, `MinecraftServer`, `ServerPlayerEntity`, `PayloadTypeRegistry`, `ServerPlayNetworking`, `ClientPlayNetworking`, `FabricLoader`, `ModInitializer`, `ClientModInitializer`, `ClientTickEvents`, `ClientCommandManager`, `ClientCommandRegistrationCallback`, `FabricClientCommandSource`, and Brigadier types. Note: entity and rendering classes used by the NPC mode (`PathAwareEntity`, `MobEntityRenderer`, `VillagerResemblingModel`, etc.) do not have stubs — they are only needed at Fabric Loom build time.

---

## Tests

Run target tests with `./gradlew buildAll` (both default Fabric targets) or with `./gradlew buildAll -Ptargets=fabric-26.1.2` / `fabric-1.21.11` for one target. Shared logic tests live in `:common:test`; Forge jar verification in `:targets:forge-1.20.1:test`. All tests are JUnit 5 and cover pure-Java logic (no Minecraft runtime needed).

| Test class | Coverage |
|---|---|
| `QuizManagerTest` | Problem generation range, addition/multiplication/division/exponentiation, explicit problem-list constructor, per-player preset resolution, correct/wrong detection, full quiz flow, edge cases (min=max, zero answer, negative answer, submit after completion) |
| `ConfigTest` | Default values (including `operation` and `playerPresets`), JSON round-trip, partial JSON, file I/O, legacy `mathQuizExportDir` key migration |
| `DatabaseTest` | Session create/end, answer recording, multiple answers, mastery aggregation query |
| `MathQuizProblemListLoaderTest` | Minecraft player mapping, latest SQLite file selection by mtime, next queued problem-list load, fallback parsing from `problem_text` |
| `NpcCatalogTest` | Selectable NPC ids, persona labels, texture paths, single-line dialogue defaults, unknown-id fallback |
| `SessionExporterTest` | Single-session SQLite schema, row counts, canonical operators, nullable answers, filename sanitization |
| `WrittenColumnSessionExporterTest` | Written-column SQLite schema, session row, attempt row, evaluation fields, filename prefix |
| `QuizResultProcessorTest` | Shared server-side result processing (JSON parse, DB writes, export hooks) |
| `TpCreditBankTest` | Earning-disabled/enabled behavior, configured awards, case-insensitive balances, one-credit spending, and save-on-success semantics |
| `SingleSessionSqliteExportIntegrationTest` | End-to-end single-session SQLite file write |
| `ActiveDbIngestIntegrationTest` | Export + Python ingest into active DB dir (skipped if no `python3`) |
| `SqliteDriverTest` | JDBC driver load behavior and fail-fast when missing |
| `ForgeReleaseJarIncludesSqliteTest` | Forge `-all.jar` bundles `META-INF/jarjar/sqlite-jdbc` |

When you are ready to **playtest in Minecraft**, the **last step** is **`./apps/minecraft/mods/build-and-deploy.py mathquest`** (run from the repo root) — see the **Build and Deploy** section at the **end** of this document (do not skip it after `gradlew build`).

---

## Configuration at Runtime

The mod config file is `mathquest.json` in the Fabric config directory (typically `~/.minecraft/config/mathquest.json` or the launcher profile's config dir). It is created with defaults on first launch and can be edited by hand or via `/mathquest` commands in-game. On load, if the global range is still the old default **2–9**, it is migrated to **0–9** so players **without** a `playerPresets` entry get **0–9 multiplication** (unless you change `operation` globally).

---

## Known Limitations / Technical Debt

- **Multiplayer item-reward authorization:** Fabric and Forge accept a client-provided item ID and count in their reward packet handlers. When TP-credit earning is off, a modified client can request an item or quantity that the server did not independently authorize.
- **Quiz-result and TP-credit verification:** The server processes client-reported answers, correctness, totals, and TP-credit eligibility. The one-use completion token prevents simple replay and cross-player redemption, but it proves that a quiz was opened rather than independently verifying the reported completion.
- **TP-credit teleport persistence ordering:** Fabric and Forge teleport the player before the credit deduction is durably saved. If saving fails, the teleport remains completed while the balance is restored.
- **Mineflayer dependency advisories:** The companion `apps/minecraft/mineflayer-forge` production dependency tree reports four high and four moderate advisories, centered on its supported Microsoft-auth path and transitive Axios 0.21.4. Offline auth remains the default.
- **Review record and follow-up:** Evidence, Randy's review decisions, and verification for these four findings are preserved in [`docs/reviews/2026-07-28_pr-60-code-review.md`](reviews/2026-07-28_pr-60-code-review.md). They remain unprioritized in [`ROADMAP.md`](../ROADMAP.md).
- **Hardcoded UI strings:** `QuizScreen` and `QuizResultScreen` use hardcoded English strings instead of the translation keys defined in `en_us.json`. The translation file exists but is only partially wired up.
- **No difficulty scaling:** Operand range is static per global or per-player preset. There is no adaptive difficulty based on performance.
- **Database recording path:** In singleplayer, `QuizDatabase` writes to the client's local DB. In multiplayer, quiz results are sent to the server via `QuizResultPayload` and the server records to its own DB. The client skips local DB writes in multiplayer.
- **Dual-mode build frozen:** The proxy-compatible build path (`*.dual-mode` files + `stubs/`) is not actively maintained. See `docs/MAVEN_PROXY_PROBLEM.md` for context.
- **26.1 API overrides:** Most Fabric code is shared after the Mojang mapping migration, but `fabric-26.1.2` keeps a small target-local override set for APIs that are not source-compatible with 1.21.11 (`ClientCommands`, `PayloadTypeRegistry.serverboundPlay/clientboundPlay`, `GuiGraphicsExtractor`, and entity interaction/message method names). The `fabric-26.1.2` target nests **`fabric-key-binding-api-v1`** via **`include implementation`** (version **`fabric_key_binding_api_version`** beside **`fabric_version`** in that target's `gradle.properties`): the Gradle **`fabric-api`** aggregate and typical Fabric installers omit this submodule, while shared **`fabric/`** uses **`KeyBindingHelper`**. Declaring **`implementation`** alone satisfies the compiler but does **not** ship classes at runtime; without JiJ (**`include`**), Minecraft throws **`ClassNotFoundException`** for **`KeyBindingHelper`** (same idea as bundling **`sqlite-jdbc`**). Narrative troubleshooting and agent rules for this fix live under **P0-1** in **`docs/2026-05-11_mathquest-server-conversion-plan.md`**.
- **Popup mode on LAN:** The **host** of an opened-to-LAN world has an integrated server, so timed popups can still run there; **joining LAN clients** do not. Prefer **NPC mode** if everyone should rely on the Wandering Nerd only.
- **Control Panel edits are local-only:** `ControlPanelScreen` and `PlayerSettingsScreen` write to the **local** `mathquest.json`. There is **no server-authoritative config sync** yet — when the host of a LAN world toggles a setting or edits `playerPresets`, those changes do **not** propagate to remote clients. Each LAN client that wants different operation/range/rewards needs its own local edit (or its own preset entry in its own `mathquest.json`). On a **remote multiplayer connection** the `K` hotkey is **hidden entirely** — use the server-side `/mathquest` commands instead. A future change can introduce a sync packet or external control plane; for now treat the panel as local groundwork.
- **Nerd despawn on dismissal:** When a client dismisses a quiz via "Not Now" or "Back to Adventure!", nearby Wandering Nerds are removed. In singleplayer the client cleans them up directly on the integrated server; in multiplayer the client sends a `DespawnNerdsPayload` (C2S) and the server discards Wandering Nerd entities within ~50 blocks of the player.

---

## Generated Build Artifacts

Everything Gradle writes under `mathquest/build/` and `mathquest/targets/<target>/build/` is **not** tracked in Git — see `mathquest/.gitignore` (`/build/`, `**/build/`, `**/.gradle/`). That includes compiled `.class` files, test reports, Loom remap caches, and the produced `mathquest-fabric-<ver>-mc<mc>.jar`. The built jar is a **local deploy artifact**:

- For **local playtesting**, `./apps/minecraft/mods/build-and-deploy.py mathquest` runs the build and copies the jar into your Minecraft `mods/` folder (archiving any previous MathQuest jar to `mathquest-inactive-mods/`), and also into the dedicated server's `mods/` folder via the `extra_deploy_paths` entry in `apps/minecraft/mods/mathquest/.mod-build.toml`.
- For **sharing a build with someone else**, attach the jar to a **GitHub Release** (or a CI artifact), don't commit it. Re-tracking a specific jar would require an explicit `!path/to/file.jar` exception in `.gitignore` below the `**/build/` line.

The `mathquest/_deprecated/` tree intentionally retains its older `build/` snapshots as a frozen reference of the pre-multi-target layout; that's why `git ls-files` still shows files under it.

---

## Build and Deploy

**This section is intentionally last.** After code changes, tests, and any local `./gradlew build`, run the build dispatcher as the **final** step when you want the mod jar installed for Minecraft. It is easy to run `gradlew build` and forget to copy the jar into `mods`; the dispatcher is the single canonical "ship it to my game" step.

**Canonical entrypoint:** `./apps/minecraft/mods/build-and-deploy.py mathquest` (run from the repo root). It picks the right JDK per target, builds via the mod's local `./gradlew`, archives any prior MathQuest jar from your Minecraft mods folder, and copies the new jar into both the client mods folder and (via `extra_deploy_paths` in `apps/minecraft/mods/mathquest/.mod-build.toml`) the dedicated server's `mods/` folder when present. Full dispatcher docs live in `apps/minecraft/mods/AGENTS.md`.

> The legacy per-mod shell scripts `mathquest/build-and-deploy.sh` and `mathquest/deploy.sh` were removed in mathquest 1.4.3. They are recoverable from git history (`git log -- apps/minecraft/mods/mathquest/build-and-deploy.sh` and likewise for `deploy.sh`) if a side-by-side diff against the dispatcher is ever needed. Don't restore them — behavior changes go into the dispatcher.

### When to run what

1. **`cd mathquest/fabric && ./gradlew :common:test`** and **`./gradlew :targets:fabric-26.1.2:test`** — Verify shared + Fabric logic before deploy.
2. **`./apps/minecraft/mods/build-and-deploy.py mathquest --no-deploy`** — Build without copying jars.
3. **`./apps/minecraft/mods/build-and-deploy.py mathquest`** — **Run this last** for Fabric 26.1.2 deploy (default target).
4. **`./apps/minecraft/mods/build-and-deploy.py mathquest --target forge-1.20.1`** — Build + deploy Forge jarJar artifact to Prism (**"Forge 1.20.1 MathQuest"**). Copies `-all.jar` (~12 MB, sqlite-jdbc bundled).

### Common dispatcher invocations

From the repo root:

```bash
# Default target (fabric-26.1.2), full build + deploy
./apps/minecraft/mods/build-and-deploy.py mathquest

# A specific target
./apps/minecraft/mods/build-and-deploy.py mathquest --target fabric-1.21.11

# Both fabric targets in one run
./apps/minecraft/mods/build-and-deploy.py mathquest --target fabric-26.1.2,fabric-1.21.11

# Forge 1.20.1 Milestone 2 (popup + SimpleChannel + commands + SQLite)
./apps/minecraft/mods/build-and-deploy.py mathquest --target forge-1.20.1

# Build only, skip the deploy copy
./apps/minecraft/mods/build-and-deploy.py mathquest --no-deploy

# Pass extra flags through to gradle
./apps/minecraft/mods/build-and-deploy.py mathquest -- --info --offline
```

The dispatcher:

- Reads `mod_version` and `archives_base_name` from the active loader gradle root (`fabric/gradle.properties` or `forge/gradle.properties`)
- Picks `JAVA_HOME` per target (Java 17 for forge-1.20.1, Java 21 for fabric-1.21.x, Java 25 for fabric-26.x)
- Runs **`./gradlew buildAll -Ptargets=<target>`** inside `mathquest/fabric/` or `mathquest/forge/`
- Produces target jars named `<archives_base_name>-<loader>-<mod_version>-mc<mc_version>.jar`
- Archives any existing MathQuest jars in the client `mods` folder into **`mathquest-inactive-mods/`**
- Copies the newly built jar into your Minecraft **`mods`** folder, plus any directories listed under `extra_deploy_paths` in `apps/minecraft/mods/mathquest/.mod-build.toml` (currently the dedicated server's `mods/` folder)
- **Forge:** deploys the jarJar **`-all.jar`** output (sqlite-jdbc bundled); copied without `-all` suffix into the Prism mods folder

Anything after `--` on the command line is forwarded verbatim to gradle (e.g. `--offline`, `-x test`).

**Key requirements:**

- **Java 21 and Java 25** — `fabric-26.1.2` builds with Java 25 bytecode; `fabric-1.21.11` builds with Java 21 bytecode. The build dispatcher picks the right JDK per target automatically (Homebrew OpenJDK 25 for fabric-26.x, Homebrew OpenJDK 21 for fabric-1.21.x). Override per-machine in the mod's `.mod-build.toml` under `[java_home]` if your JDKs live somewhere other than the standard Homebrew Intel paths.
- **Network** — Fabric Loom may need `maven.fabricmc.net` unless you use `--offline` with cached dependencies.

---

## Running the dedicated server

MathQuest supports **two separate dedicated servers** — one per loader. Each has its own folder, world, and deploy path. Do not mix Fabric and Forge jars in the same `mods/` folder.

| | **Fabric 26.1.2** | **Forge 1.20.1** |
|--|-------------------|------------------|
| **Server folder** | `~/Documents/Code/mathquest-server` | `~/Documents/Code/mathquest-server-forge` |
| **One-time setup** | [`2026-05-11_local-fabric-server-howto.md`](2026-05-11_local-fabric-server-howto.md) | [`2026-06-29_local-forge-server-howto.md`](2026-06-29_local-forge-server-howto.md) |
| **Java** | 25 — `/usr/local/opt/openjdk/bin/java` | 17 — `/Library/Java/JavaVirtualMachines/temurin-17.jdk/Contents/Home/bin/java` |
| **Start command** | `java -Xmx2G -jar fabric-server-launch.jar nogui` | `./run.sh nogui` |
| **Prism client** | **Fabric 26.1.2 MathQuest** | **Forge 1.20.1 MathQuest** |
| **Deploy jar** | `./apps/minecraft/mods/build-and-deploy.py mathquest` | `… mathquest --target forge-1.20.1` |

Only one server can use port **25565** at a time. Stop one before starting the other.

### Fabric server (steady state)
**Start** (from Terminal):
```bash
cd ~/Documents/Code/mathquest-server
/usr/local/opt/openjdk/bin/java -Xmx2G -jar fabric-server-launch.jar nogui
```

**Deploy** (builds Fabric jar → Prism + `mathquest-server/mods`):
```bash
./apps/minecraft/mods/build-and-deploy.py mathquest
```
**Connect:** launch **Fabric 26.1.2 MathQuest** in Prism → **Multiplayer → Direct Connection** → `localhost`.

### Forge server (steady state)
**Start** (after one-time Forge install — see Forge howto):
```bash
cd ~/Documents/Code/mathquest-server-forge
./run.sh nogui
```

**Deploy** (builds Forge jar → Prism + `mathquest-server-forge/mods`):
```bash
./apps/minecraft/mods/build-and-deploy.py mathquest --target forge-1.20.1
```

**Connect:** launch **Forge 1.20.1 MathQuest** in Prism → **Multiplayer → Direct Connection** → `localhost`.

### HTTP control panel (both loaders)
With `controlPanelEnabled: true` in `config/mathquest.json`, open **`http://127.0.0.1:8765/`** in a browser while the server is running (dedicated or integrated single-player).

- **Forge:** core routes only — dashboard, status, config, spawn nerd, open quiz, vanish. No quest, terrain-map, or mob-spawn admin pages.
- **Fabric:** full panel including quest, terrain-map PNG, and mob admin tools.

### Server console and operator
The Terminal window shows a **`>`** prompt while the server runs — that is the **server console** (commands run as the server; no leading `/`).

**First-time operator:** at the `>` prompt run `op <YourMinecraftUsername>` (exact Java Edition name). Then `/mathquest` works from in-game chat; or run `mathquest …` at the console directly.

**LAN connect** (family on home Wi‑Fi): use your machine's local IP (e.g. `ipconfig getifaddr en0`) with port `:25565`. Remote access outside the LAN is not set up; see `2026-05-11_mathquest-server-conversion-plan.md`.

**Stopping:** type `stop` at the `>` prompt, or Ctrl+C the Terminal window. Restart the server after deploying a new jar.

### Forge port — on hold (not in server playtest scope)
These remain **Fabric-only** or **deferred**; do not expect them on the Forge server or client until a later milestone:

| Feature | Status |
|---------|--------|
| **Written-column quiz screen** | On hold — troubleshoot in Fabric 26.1.2 first, then revisit Forge |
| **Terrain-map control panel** (`/api/terrain-map.png`) | On hold for Forge — Fabric-only optional route |
| **Mob-spawn admin panel** (spawn-mobs / spawn-mob-plan / kill-mob-area) | On hold for Forge — Fabric-only optional route |
| **Quest / Cave Escape** | Frozen past M6 — Fabric-only |

### Forge port — core parity matrix (M6 audit)
**Core (non-quest) feature parity is achieved** for the family quiz workflow: popup + NPC quizzes, rewards, SQLite export/ingest, fluency-feast result UI, in-game Control Panel + **K** keybind, HTTP control panel core routes, op server commands, and dedicated-server deploy. Documented minor UX deltas below are acceptable for M6; deferred items remain out of scope.

| Capability | Fabric 26.1.2 | Forge 1.20.1 | Status |
|------------|---------------|--------------|--------|
| Entrypoints & lifecycle (spawner, control panel, config) | ✅ | ✅ | **At parity** |
| Core networking (OpenQuiz, QuizResult, GiveReward, DespawnNerds, FluencyFeastResult) | ✅ | ✅ | **At parity** (quest payloads Fabric-only) |
| Quiz / offer / result / control-panel / player-settings screens | ✅ | ✅ | **At parity** |
| Op server `/mathquest` commands | ✅ | ✅ | **At parity** |
| Client `/mathquest` commands (SP + MP guards) | ✅ | ✅ mostly | **Minor delta:** Forge SP lacks client `reward`, `player`, `npcspawn` subcommands (server console + web panel cover dedicated-server ops); Forge adds client `vanishnerds` |
| Wandering Nerd entity / renderer / spawner | ✅ | ✅ | **At parity** |
| HTTP control panel core (`status`, `config`, `spawn`, `open`, `vanish`) | ✅ | ✅ | **At parity** |
| Shared `MathQuestConfig` + quiz-source selector | ✅ | ✅ | **At parity** |
| SQLite session export + active DB ingest | ✅ | ✅ | **At parity** |
| Title-screen version label | ✅ | ✅ | **At parity** |
| Fluency-feast result UI + S2C payload | ✅ | ✅ | **At parity** |
| TP credits (web config/balance, quiz awards, `/tpc` + shortcuts) | ✅ | ✅ | **At parity** |
| NPC click → quiz offer delay (5s greeting UX) | ✅ 5s delay | immediate offer | **Minor UX delta** — acceptable for M6 |
| Quest invitation + Cave Escape | ✅ | — | **Deferred / Fabric-only** |
| Written-column quiz screen | ✅ (on hold) | code present, on hold | **Deferred** |
| Terrain-map + mob-spawn admin panel | ✅ | — | **Deferred / Fabric-only** |
