# MathQuest changelog

All notable changes to MathQuest are recorded here, newest first. The version recorded
in `gradle.properties` (`mod_version`) is the source of truth for what the next jar
will be built as; this file is the human-readable log of what changed and when.

Format: each entry has a date (PDT), a version (semver), a short summary line, then
either prose or bullets describing the change. When Randy playtests a version, the
result is captured under a **Tested:** sub-bullet on that entry.

## Currently shipping

The latest jar produced for each target, with the last playtest date. The **Tested**
column shows the most recent build/version that Randy has actually launched and
verified in Minecraft.

- **fabric-26.1.2** — latest: **1.25.4** *(version lockstep; Fabric unchanged)*.
  Not actively playtested on this branch — day-to-day play has been on **Forge**. Only prior Fabric note: **1.25.0** smoke on **2026-07-16** (TP earn/spend basically worked; exposed dual item+credit rewards fixed in 1.25.1). Quest routes and **fabric-1.21.11** not re-tested.
- **forge-1.20.1** — latest: **1.25.4**.
  TP-credit basic functionality used heavily in normal play through mid/late July 2026 (earn on quiz complete, spend via `/tpc` shortcuts). **2026-07-26:** switched earning off and returned to regular item rewards — that path works. Ice and Fire trident-vs-dragon freeze: **1.25.4** seemed improved at first but freezes/crashes still occur — further work tracked separately; **not a PR gate**. Earlier successful Forge core playtest: **1.24.1** on **2026-06-30** (see [`docs/playtest-log.md`](docs/playtest-log.md)).
- **fabric-1.21.11** — latest: **1.25.4** *(preserved-capability target; version lockstep)*.
  Not playtested on this branch.

## 1.25.4 — 2026-07-22
Hotfix: 1.25.3 loaded but still froze on the second trident hit — Ice and Fire parts were never filtered.

- **Root cause:** Ice and Fire `EntityDragonPart` / `EntityMutlipartPart` extend plain `Entity`, not Forge `PartEntity`. The prior `instanceof PartEntity` check was a no-op for dragons.
- **Fix:** soft-dep filter also skips `com.github.alexthe666.iceandfire.entity.EntityMutlipartPart` (and subclasses) on the logical client. Toggle unchanged.
- **Tested:** Randy, Forge Ice and Fire — initially seemed better / thought fixed; further play still hit trident-related freezes/crashes. Needs more work on parent or a follow-up branch; not gating the TP-credits PR. If capturing hangs, use `capture-client-freeze.sh` (Force Quit does not write a crash report).

## 1.25.3 — 2026-07-22
Hotfix: 1.25.2 crashed on join because a mixin redirected a `ProjectileUtil` overload that never calls `Level.getEntities`.

- **Forge mixin retarget:** redirect the Entity+double and Level+float overloads (the ones that actually invoke `getEntities`). The Level-only overload only delegates to the float variant — redirecting it caused `InjectionError` / client crash right after connecting.
- **Tested:** Randy — join crash addressed enough to continue Ice and Fire play on **1.25.4**; trident-vs-dragon freeze remains open (see 1.25.4).

## 1.25.2 — 2026-07-22
Patch release: stop client freezes when throwing tridents at Ice and Fire (multipart) dragons on a dedicated server.

- **Forge client mixin:** `ProjectileUtil` entity picking on the logical client skips Forge `PartEntity` hitboxes (dragon parts) so trident AABB clips cannot wedge the render thread. Server-side collision/damage is unchanged.
- **Discrete toggle:** `excludeMultipartFromClientProjectileHits` in `mathquest.json` (default **true**; existing configs without the key migrate to true). Client command `/mathquest multipartProjectileFix on|off|status` works in multiplayer.
- **Deploy:** Forge jar also copies to Prism instance **Forge 1.20.1 Ice and Fire** plus the dedicated Forge server mods folder.
- **Superseded for playtest notes by 1.25.4** — multipart filter alone was insufficient for Ice and Fire dragons.

## 1.25.1 — Codex — 2026-07-16
Patch release: make TP credits an alternative to item rewards and remove the legacy TreasureHunterM diamond-stack fallback.

- **Credit-only reward mode:** when **Earn TP credits** is enabled for a player, both standard and fluency item-reward plans resolve to empty. Standard, fluency-feast, quest-result, and written-column completion can still award TP credits, but no configured reward item/count is granted.
- **Forge authority fix:** standard Forge result screens now retain and honor the reward plan delivered with the quiz instead of re-reading a potentially different client-local reward default; an empty server plan stays empty through completion.
- **Server enforcement:** Fabric and Forge item-reward handlers reject reward packets for players whose TP-credit earning is enabled, so stale or replayed client requests cannot produce both rewards.
- **Fabric 26 multiplayer:** successful standard and written-column result persistence now completes the server-issued TP-credit token before redemption, matching the shared Fabric/Forge processor.
- **Settings retained:** the control panel continues to store and display each player's item and fluency reward selections. Those settings become active again if TP-credit earning is turned off.
- **TreasureHunterM fallback:** replace the historical `diamond ×64` built-in default with `polished_deepslate ×1` for new or missing settings. Explicit saved reward selections are not rewritten.
- **Tests:** cover credit-only standard/fluency plan resolution, retained web-panel selections, explicit reward preservation, server-side item suppression, and the required Fabric/Forge target builds.
- **Tested:** Randy, Forge — credit-only rewards used in ongoing play after 1.25.1; no dual item+credit stacks observed in normal use. **2026-07-26:** turned TP-credit earning off and confirmed regular item rewards work again. Fabric path not re-playtested.

## 1.25.0 — Codex — 2026-07-16
Minor release: add an opt-in, per-player TP-credit economy to MathQuest and its local web control panel.

- **Earning:** each player has an **Earn TP credits** setting (off by default) and **Credits per quiz** amount (default 1, range 1–100). Standard, fluency-feast, quest-result, and written-column quizzes receive a server-issued one-use session token that becomes redeemable only after the result is processed; the server then resolves the award, persists it in `mathquest.json`, and reports the new balance. Partial quizzes saved through **Quit Quiz** cancel their session, and incomplete or replayed completions cannot award.
- **Spending:** ordinary players can spend 1 credit with `/tpc <online-player>` or `/tpc <x> <y> <z>`. Shortcuts are `/tpt` → TreasureHunterM, `/tpp` → PumaJockey, `/tpr` → RJComp, and `/tpw` → WildPetal. Invalid/offline/self destinations and insufficient balances do not deduct a credit; successful commands report the remaining balance. Vanilla `/tp` is unchanged.
- **Web control panel:** every player card displays a live **TP credits: N** balance and autosaving earning, credits-per-quiz, and reward-choice controls. The first spend choice is **Teleport (1 credit)**. Fabric and Forge bundle byte-identical HTML/CSS/JS assets.
- **Durability:** config saves use a same-directory temporary file and atomic replacement. Award and spend mutations roll back in memory when `mathquest.json` cannot be replaced, and the player receives an explicit failure message instead of a false success.
- **Persistence and tests:** shared `TpCreditBank` serializes balance mutations and saves only successful awards/spends. Common config/bank/HTTP tests, Fabric 26.1.2 tests, Fabric 1.21.11 compilation, Forge 1.20.1 tests, mirrored-asset checks, JavaScript syntax, and an in-browser autosave/layout smoke test pass.
- **Forge protocol:** exact modded-client protocol increases from 1 to 2 for the new completion packet. Missing/vanilla clients remain accepted under the existing server policy and receive no MathQuest features.
- **Tested:** Randy — basic TP earn/spend exercised heavily on **Forge** in regular play after release (see Currently shipping). Fabric: only the **2026-07-16** 1.25.0 smoke; not used day-to-day.

## 1.24.2 — Codex — 2026-07-15
Patch release: allow a vanilla/unmodded client without the MathQuest Forge channel while preserving exact protocol matching for clients that do advertise the channel.

- Forge networking: the server-side `SimpleChannel` predicate now uses Forge `NetworkRegistry.acceptMissingOr(PROTOCOL)`; the client-side predicate remains strict `PROTOCOL::equals`.
- Compatibility boundary: an unmodded client receives no MathQuest UI or protocol support. This change does not make other required Forge channels optional.
- Tests: focused JUnit coverage accepts exact, absent, and vanilla channel markers and rejects a mismatched modded protocol; Forge and companion Fabric builds run with `--no-deploy`.
- Isolated smoke test: a disposable Forge **47.4.2** server with MathQuest **1.24.2** on `127.0.0.1:25566` accepted Mineflayer **4.25.0**, reached player spawn, stayed connected for 10 seconds, and disconnected cleanly. The temporary server then stopped cleanly.
- Actual game-server verification is pending. Diagnosis used only a status ping and a short stationary login probe against the existing 1.24.1 server; it was not stopped, deployed to, restarted, or otherwise administered.

## 1.24.1 — Cursor — 2026-06-30
Patch release: web control panel global settings and reward groups autosave (remove top **Save** and **Save groups** buttons).

- Control panel: global Mode / Multiple NPCs / Despawn / Evaluator code autosave (debounced, same pattern as player cards).
- Control panel: reward groups editor autosaves on edit; **Save groups** button removed.
- Deploy: add Prism **Forge 1.20.1 MathQuest Cataclysm MP** to `prism_instance_suffix_by_target` for forge-1.20.1.
- Docs: sidecar `minecraft_LIVE-CONFIG-JSON-IS-IN-MATHQUEST-SERVER-FOLDER.txt` for Forge server bootstrap config folder.
- **Tested:** Randy, 2026-06-30 — M6 matrix in [`docs/playtest-log.md`](docs/playtest-log.md): Forge server steps 1–4; global Save removed (autosave not fully re-tested). Fabric 26.1.2 on `mathquest-server`: terrain-map, mob-spawn, NPC quick quiz + SQLite ✅; quest routes skipped. Fabric 1.21.11 skipped.

## 1.24.0 — Cursor — 2026-06-30
Minor release (Forge M6): declare **core (non-quest) feature parity** on Forge 1.20.1; parity audit + matrix in OVERVIEW; lift duplicated duration formatting into `common/util/MathQuestDurationFormat`.

- **Parity audit:** documented Forge vs Fabric 26.1.2 matrix — core quiz workflow at parity; quest, written-column acceptance, terrain-map, and mob-spawn admin remain deferred/Fabric-only.
- **Common:** `MathQuestDurationFormat.forStatus` / `forCompactUi` — replaces six duplicated `formatDuration` helpers in Fabric/Forge command and control-panel screens.
- **Tested:** Randy, 2026-06-30 — see [`docs/playtest-log.md`](docs/playtest-log.md) M6 section (`v1.24.0` matrix at 1.24.0/1.24.1). Forge dedicated-server core panel + quiz + SQLite ✅. Fabric 26.1.2 dedicated-server quick regression ✅ (quest routes not re-tested). Fabric 1.21.11 skipped.

## 1.23.1 — Cursor — 2026-06-29
Patch release: disable automatic interval Wandering Nerd spawning; NPCs spawn only from the web control panel (or manual server/console commands).

- **Config:** new `npcAutomaticSpawnEnabled` (default `false`). When off, the world-tick spawner no-ops; `/api/spawn` and `forceSpawn` paths unchanged (player, radius, NPC id, lock-to-player).

## 1.23 — Cursor — 2026-06-29
Patch release: Forge client `/mathquest` chat commands reject on dedicated servers with guidance (use web panel or server console), matching Fabric behavior.

- **Forge client commands:** add `isRemoteMultiplayer()` / `rejectIfMultiplayer()` guards to config-mutating handlers (`interval`, `problems`, `mode`, `operation`, `range`, `group`, `enable`/`disable`). `status` on multiplayer directs to server console; `start` (NPC mode) and `vanishnerds` messages aligned with Fabric.

## 1.22 — Cursor — 2026-06-29
Patch release: fix Forge dedicated-server crash when registering client-bound network packets; bump past 1.20.x to avoid confusion with Minecraft 1.20.x version numbers.

- **Forge networking:** client packet handlers (`OpenQuiz`, `FluencyFeastResult`) moved to `MathQuestNetworkClientHandlers` (`@OnlyIn(Dist.CLIENT)`). Common registration uses `DistExecutor.unsafeRunWhenOn` so the dedicated server never loads `Screen` classes during mod init.
- **Version scheme:** skip 1.20.x–1.21.x mod versions that mirror Minecraft release numbers; resume at **1.22**.

## 1.20.0 — Cursor — 2026-06-29
Minor release (Forge M5): HTTP control panel core on Forge + written-column quiz screen; quest frozen past M6.

- Common: lift HTTP control panel core into `control/http/` — JDK `HttpServer`, router with optional-handler registry, static assets resolver, status JSON builder, `ControlPanelBridge` interface (no loader imports in `common/`).
- Fabric: `FabricControlPanelBridge` + optional Fabric-only routes (terrain-map PNG, mob spawn/plan/kill, `/api/quest/*`); behavior-preserving refactor off monolithic `MathQuestControlPanelServer`.
- Forge: `ForgeControlPanelBridge` + core routes only (`status`, `config`, `spawn`, `open`, `vanish`, static assets); starts from `MathQuestForgeEvents` when `controlPanelEnabled`; control panel assets copied into Forge jar.
- Forge: `WrittenColumnQuizScreenForge` — paper-column quiz UI; results via existing C2S `QuizResultPacket` → `QuizResultProcessor.processWrittenColumn`.
- Quest **FROZEN past M6** — `CaveEscapeQuestService` / quest invitation remain Fabric-only; no quest routes or wiring on Forge.
- M5.0 tooling decision: grow `common/`, freeze build tooling (no Balm/Stonecutter/Architectury in M5); post-M6 migration evaluated on a separate branch.
- **Tested:** `./gradlew :common:test :targets:fabric-26.1.2:test`; Forge + Fabric 26.1.2 + Fabric 1.21.11 `--no-deploy` builds clean. Pending Randy M5 playtest on Forge 1.20.0 (Prism **Forge 1.20.1 MathQuest**).

## 1.19.2 — Cursor — 2026-06-29
Patch release: fix in-game Quiz source CycleButton stuck after first change.

- Forge + Fabric: stop calling `rebuild()` on Quiz source change (it destroyed the button mid-click and broke further cycling); toggle Operation/Problems/Range disabled state in place instead.

## 1.19.1 — Cursor — 2026-06-29
Patch release (Forge M4B): in-game Quiz source selector + fluency-feast backfill regression fix.

- Forge + Fabric: **Quiz source** `CycleButton` on the in-game Control Panel (under Global Settings) — cycles `generated`, internal problem list, internal quick quiz, and internal fluency feast; persists `playerInternalQuizSources` and syncs legacy `playerUseInternalProblemLists`; disables Operation/Problems/Range for internal sources (`internal_quick_quiz` keeps Operation).
- Shared math-quiz: cherry-pick `c17ebb7` — fluency-feast **backfill** restores 20-question lists when repeat cap limits a tiny pool (fixes 15-question shortfall from M4 playtest).
- **Tested:** `./gradlew :common:test :targets:fabric-26.1.2:test`; Forge + Fabric 26.1.2 `--no-deploy` builds clean; `node --test apps/math-quiz/tests/fluency_list_generator.test.mjs` (22 pass). Pending Randy M4B playtest on Forge 1.19.1 (Prism **Forge 1.20.1 MathQuest**).

## 1.19.0 — Cursor — 2026-06-29
Minor release (Forge M4): in-game Control Panel + K keybind + fluency-feast result UI.

- Forge: `ControlPanelScreenForge` + `PlayerSettingsScreenForge` — parent-facing settings UI (mode, operation, problems, interval, range, reward pool, player presets); default hotkey **K** via `RegisterKeyMappingsEvent`, singleplayer-only.
- Forge: `FluencyFeastResultPacket` (S2C) — fluency feast completions route through shared `QuizResultProcessor`; `QuizResultScreenForge` shows before→after fluency % readout, FF reward-group choice buttons, and fluency-improvement reward grant.
- Fabric: version lockstep bump only (no gameplay changes).
- **Tested:** Pending Randy playtest on Forge 1.19.0 (Prism **Forge 1.20.1 MathQuest**).

## 1.18.9 — Cursor — 2026-06-29
Patch release: move title-screen MathQuest version label to bottom-center.

- Fabric + Forge: version string centered above the bottom edge (avoids Mojang disclaimer on the right and mod lines on the left).
- **Tested:** Pending Randy full playtest on Forge 1.18.9.

## 1.18.8 — Cursor — 2026-06-29
Patch release: fix status feast question count; move title version to bottom-right.

- Common: `/mathquest status` **Next quiz** for fluency feast now reads question count and operation from `FluencyFeastConfig` (default 20 / addition), not the player preset `problemsPerQuiz` (e.g. 3) when generation preview is empty or partial.
- Common: `OpenQuizPayloadBuilder` uses feast config count for fluency-feast payloads when problems are not yet generated.
- Fabric + Forge: title-screen version label moved to bottom-right (avoids overlapping ModernFix / other bottom-left mod lines).
- Tests: `QuizDeliveryPreviewTest` feast count regression; `./gradlew :common:test`.
- **Tested:** Pending Randy status + title-screen check on Forge 1.18.8.

## 1.18.7 — Cursor — 2026-06-29
Patch release: show MathQuest version on the title screen (Forge + Fabric).

- Common: `MathQuestPaths.titleScreenVersionLabel()` formats `MathQuest <mod_version> + MC <minecraft>`.
- Fabric: `MathQuestTitleScreenOverlay` draws bottom-left on `TitleScreen` (26.1.2 target uses `GuiGraphicsExtractor.text`).
- Forge: `MathQuestTitleScreenForge` renders the same label via `ScreenEvent.Render.Post`.
- **Tested:** Pending Randy title-screen check on Forge 1.18.7 and Fabric 26.1.2.

## 1.18.6 — Cursor — 2026-06-29
Patch release: remove stale **Problems per quiz** from `/mathquest status` (Next quiz line is authoritative).

- Fabric + Forge client and server status commands no longer print global `problemsPerQuiz` after **Next quiz** (misleading when quiz source is fluency feast / problem list / quick quiz).
- **Tested:** Pending Randy quick status re-check on Forge 1.18.6.

## 1.18.5 — Cursor — 2026-06-29
Patch release: fluency feast operation comes from `FluencyFeastConfig.operation` (default addition).

- Common: `FluencyFeastConfig` gains `operation` column (after `num_problems`); loader migrates missing column, defaults to addition with log, and passes operation to the Node bridge instead of hardcoded `+`.
- Common: default feast init uses 20 questions + addition when table/row/field absent.
- math-quiz: `fluency_feast_store.py` + bridge read `feast.operation`; TLKids learner DBs updated to `addition`.
- Tests: `MathQuizFluencyLoaderTest` operation migration/symbol mapping; `./gradlew :common:test`.
- **Tested:** Randy, 2026-06-29 — Forge 1.20.1 MathQuest **1.18.5**. `/mathquest status` **Next quiz** correct (`fluency feast, 20 questions, addition`); popup and NPC both delivered 20-question addition; single-session + active multi-session SQLite updated. Fluency-feast **FF** reward group and before/after fluency % result UI still deferred (see M3B plan).

## 1.18.4 — Cursor — 2026-06-29
Patch release: `/mathquest status` shows resolved next quiz (same code path as quiz open).

- Common: `QuizDeliveryPreview` calls `OpenQuizPayloadBuilder.create` and reports source, question count, and operation (e.g. `fluency feast, 20 questions, addition`); shows generation failure when fluency feast would not open.
- Fabric + Forge: client and server status commands append **Next quiz** lines from shared preview.
- Tests: `QuizDeliveryPreviewTest`; `./gradlew :common:test`.
- **Tested:** Pending Randy playtest (Forge 1.18.4 + Fabric 26.1.2 SP/server).

## 1.18.3 — Cursor — 2026-06-29
Patch release: fix fluency feast problem generation when Node is not on Prism's PATH.

- Common: `FluencyFeastBridge` now discovers `node` under `/usr/local/bin`, Homebrew, NVM/Volta, and PATH (GUI launches often miss `/usr/local/bin`).
- Common/Fabric/Forge: refuse fluency-feast quiz open when generation fails instead of silently falling back to control-panel preset (e.g. 3-question double-digit addition).
- Tests: `FluencyFeastBridgeTest.resolveExecutableOnPathFindsNodeInCommonMacLocations`, `./gradlew :common:test`.
- **Tested:** Pending Randy playtest on Forge 1.20.1 MathQuest profile (1.18.3).

## 1.18.2 — Cursor — 2026-06-29
Patch release: Forge SP reads quiz settings from shared server config; restore client vanishnerds command.

- Common: when instance `mathquest.json` sets `sharedDataDir` and that directory contains `mathquest.json`, load/save the shared file (Forge Prism SP now picks up `internal_fluency_feast` from `mathquest-server/config` instead of stale instance defaults).
- Forge: add `/mathquest vanishnerds` to client commands for integrated singleplayer tab-complete; run fluency bridge startup check on server start.
- Tests: `ConfigTest.loadsSharedConfigWhenLocalPointsAtSharedDataDir`, `./gradlew :common:test`, Forge build.
- **Tested:** Pending Randy playtest on Forge 1.20.1 MathQuest profile (1.18.2).

## 1.18.1 — Cursor — 2026-06-29
Patch release: Forge M3B playtest fixes — unified quiz delivery and QuizScreen layout parity with Fabric 26.1.2.

- Forge: popup and NPC now both resolve quizzes via shared `OpenQuizPayloadBuilder.create(playerName)` (`QuizOfferScreenForge` unified path; `OpenQuizPacket.toData()` for NPC branch).
- Forge: `QuizScreenForge` ported to full Fabric layout parity on 1.20.1 APIs — 3× problem text, styled answer box, feedback under answer box (not over keypad), quit save/abandon, flag panel, pause overlay, progress/source label, keyboard input.
- Forge: `QuizResultScreenForge` logs quiz mode on SQLite export; NPC despawn on "Back to Adventure!" unchanged.
- Deferred (not regressions): fluency-feast-specific result UI, written-column screen, control panel, legacy per-answer `mathquest_data.db` recording on Forge.
- Tests: `./gradlew :common:test`, `./gradlew :targets:fabric-26.1.2:test`, `./apps/minecraft/mods/build-and-deploy.py mathquest --target forge-1.20.1 --no-deploy`, Fabric regression `--target fabric-26.1.2,fabric-1.21.11 --no-deploy`.
- **Tested:** Pending Randy playtest on Forge 1.20.1 MathQuest profile (1.18.1).

## 1.18.0 — Cursor — 2026-06-29
Minor release: Forge M3 NPC mode (Wandering Nerd entity + renderer + spawner + interact → quiz + despawn).

- Forge: `WanderingNerdEntityForge` registered via `DeferredRegister`; villager-model renderer with 5 persona textures; server-tick spawner; right-click sends S2C `OpenQuizPacket`; C2S `DespawnNerdsPacket` + `/mathquest vanishnerds` / `npcspawn` / NPC-mode `start`.
- Common: `NpcSpawnPlanner.selectTargetNames` extracted; Fabric spawners refactored onto it (behavior-preserving).
- Tests: `:common:test` (incl. `NpcSpawnPlannerTest`), `:targets:fabric-26.1.2:test`, Forge `buildAll -Ptargets=forge-1.20.1`.
- **Tested:** Pending Randy playtest on Forge 1.20.1 MathQuest profile (1.18.0).

## 1.17.3 — Cursor — 2026-06-29
Patch release: fix Forge SQLite export by deploying the jarJar artifact that bundles sqlite-jdbc.

- Root cause: the slim `mathquest-forge-*.jar` lacked `META-INF/jarjar/sqlite-jdbc`; JDBC failed at runtime with "Failed to export MathQuest SQLite session".
- Deploy/build now uses the `-all.jar` jarJar output for Forge (copied without `-all` suffix into Prism).
- `SqliteDriver.requireLoaded()` fails fast with a clear message when the driver is missing.
- Tests: `SingleSessionSqliteExportIntegrationTest`, `ActiveDbIngestIntegrationTest`, `ForgeReleaseJarIncludesSqliteTest`; `./gradlew :common:test`, `./gradlew :targets:forge-1.20.1:test`.
- **Tested:** Randy, 2026-06-29 — Forge 1.20.1 MathQuest, 1.17.3. Popup quiz, rewards, `/mathquest status`, single-session SQLite file written, multi-session `tlkids` updated; in-game path chat confirmed.

## 1.17.2 — Cursor — 2026-06-29
Patch release: Forge singleplayer SQLite export fix, clearer DB directory names, in-game path feedback.

- Forge singleplayer now exports SQLite on the client (matches Fabric); integrated-server packet path was not writing files.
- In-game chat after each quiz: `Wrote single session to: <full path>` and `Updated active DB file: <full path>` (or ingest failure hint).
- Chat on world join: `MathQuest <version>`.
- Renamed config keys to `mathQuizSingleDbDir` / `mathQuizActiveDbDir` (legacy JSON keys still load); status labels are **Single DB directory** and **Active DB directory**.
- Added `MathQuizDbPaths.probeWritable()` tests that write a real session SQLite file to the configured single DB dir.
- Tests: `./gradlew :common:test`, `./gradlew buildAll -Ptargets=forge-1.20.1`.

## 1.17.1 — Cursor — 2026-06-29
Patch release: M2 Forge playtest fixes for SQLite export/ingest and client `/mathquest` commands.

- Forge: wire `ForgeQuizResultHooks` into `QuizResultPacket` handler (was passing null — ingest never ran).
- Common: `SqliteDriver.ensureLoaded()` before JDBC use; moved `MathQuizSessionIngestor` to common with bundled `session_ingest.py` fallback.
- Forge: client-side `/mathquest` commands via `RegisterClientCommandsEvent` (tab-complete in singleplayer, mirrors Fabric).
- Config: auto-detect `feature-minecraft-mod-forge` worktree for default `_data/` export and `tlkids` paths when present.
- Tests: `./gradlew :common:test`, `./gradlew :targets:fabric-26.1.2:test`, `./gradlew buildAll -Ptargets=forge-1.20.1`.

## 1.17.0 — Cursor — 2026-06-29
Minor release: Forge M2 platform abstraction, server-authoritative quiz flow, and op commands.

- Added loader-agnostic platform layer in `common/` (`PlatformInventory`, `PlatformServer`, `PlatformNetwork`, neutral `net/*` payload records).
- Extracted `QuizResultProcessor` and `OpenQuizPayloadBuilder` into `common/server/`; Fabric delegates packet handlers to shared logic.
- Forge: `SimpleChannel` networking (give-reward C2S, quiz-result C2S, open-quiz S2C); popup quiz rewards and SQLite export now go through the integrated server packet path (replaces M1 direct client grant).
- Forge: op-gated `/mathquest` server commands (popup subset); NPC-only commands stub with explicit M3 deferral message.
- Updated [AGENTS.md](apps/minecraft/mods/mathquest/AGENTS.md) with common-vs-loader contract and tandem-development rules.
- Tests: `./gradlew :common:test`, `./gradlew :targets:fabric-26.1.2:test`, `./apps/minecraft/mods/build-and-deploy.py mathquest --target forge-1.20.1 --no-deploy`, Fabric regression `--target fabric-26.1.2,fabric-1.21.11 --no-deploy`.

## 1.16.0 — Cursor — 2026-06-28
Minor release: nested loader gradle roots, shared `common/` module, and first Forge 1.20.1 Milestone 1 build.

- Migrated the Fabric build into `mathquest/fabric/` (Gradle 9) with shared source under `fabric/shared/src/`.
- Extracted loader-agnostic logic into `fabric/common/` (`MathQuestPaths`, quiz/config/persistence helpers, pure-logic tests).
- Added `mathquest/forge/` gradle root (Gradle 8, Java 17) with `forge-1.20.1` target: popup-mode singleplayer quiz, number-pad UI, direct inventory rewards, SQLite session export.
- Deferred on Forge M1: NPC mode, control panel, multiplayer networking, server commands, written-column quiz, quest flows.
- Tests: `./gradlew :common:test`, `./gradlew :targets:fabric-26.1.2:test`, `./apps/minecraft/mods/build-and-deploy.py mathquest --target forge-1.20.1 --no-deploy`.

## 1.15.3 — Codex — 2026-06-28
Patch release making player-card edits autosave and moving reward choice buttons below the result text.

- Player-card field changes now debounce-save automatically; the per-player Save button was removed.
- Reward choice buttons now render lower on the quiz-complete screen so they do not overlap the fluency reward text.
- Tests: `./gradlew :targets:fabric-26.1.2:test`.

## 1.15.2 — Codex — 2026-06-28
Patch release fixing the remaining fluency reward-group path.

- Control panel Open Quiz / Spawn NPC now include Fluency reward item/count in the same payload as Save, so selecting `ff (group)` and immediately opening a quiz persists the group instead of reverting to emerald.
- Multiplayer fluency-feast choose-mode groups now send choice options back to the result screen; the server does not auto-grant a random item for choose groups.
- Tests: `./gradlew :targets:fabric-26.1.2:test`.

## 1.15.1 — Codex — 2026-06-28

Patch release fixing control-panel reward group editor resets and fluency reward group selection.

- Reward Groups editor no longer wipes unsaved edits on the 2.5s status poll (dirty flag + wider focus guard).
- Reward item and Fluency reward item fields show `name (group)` after blur/Enter when the value matches a group; Fluency reward item uses the same group autocomplete as Reward item.
- Fluency improvement rewards honor per-player fluency reward group refs (`playerFluencyRewardGroups`) with the group's mode.
- Tests: `./gradlew :targets:fabric-26.1.2:test --tests com.kidgames.mathquest.ConfigTest` (21 tests).

## 1.15.0 — Codex — 2026-06-28

Minor release adding configurable **reward groups** (renamed from reward bundles).

- Each reward group is a named list of item/count pairs plus a mode: **give all**, **give one at random**, or **let the player choose one** (inline buttons on the quiz-complete screen).
- Control panel: collapsible **Reward Groups** editor below NPC Gallery; per-player **Reward item** field accepts either a group name or a literal item (group names autocomplete).
- Config keys renamed: `rewardGroups`, `rewardGroup`, `playerRewardGroups`; legacy `rewardBundles` / `rewardBundle` migrate automatically on load.
- Command renamed: `/mathquest group <name>` and `/mathquest group clear` (was `bundle`).
- Tests: `./gradlew :targets:fabric-26.1.2:test --tests com.kidgames.mathquest.ConfigTest` (20 tests).

## 1.14.4 — Codex — 2026-06-28

Patch release enlarging fluency feast result readout on the quiz complete screen.

- Fluency feast `Fluent: A% -> B%` and reward lines render large and centered (quest title gold with shadow), matching the in-quest `/title` gold styling instead of small green text at the top.

## 1.14.3 — Codex — 2026-06-28

Patch release fixing Prism client crash on launch with 1.14.2.

- Synced the `targets/fabric-26.1.2` `MathQuestMod` override with shared fluency-feast logic: registers `FluencyFeastResultPayload` on `clientboundPlay` (fixes `Cannot register handler as no payload type has been registered with name "mathquest:fluency_feast_result"`), runs `FluencyFeastBridge.verifyAtStartup`, and restores server-side fluency percent/reward handling on dedicated server.

## 1.14.2 — Codex — 2026-06-28

Patch release fixing fluency feast multiplayer result handling and quiz source labeling.

- Added explicit `fluencyFeastMode` on `OpenQuizPayload` so dedicated-server quizzes reliably enter the fluency-feast result/reward path on the client.
- Added S2C `FluencyFeastResultPayload` so multiplayer result screens show `Fluent: A% -> B%` and the fluency-improvement reward text; server grants the fluency reward directly (emerald by default) instead of the normal completion reward.
- Quiz UI now shows **fluency feast** as the source label during fluency-feast quizzes (was **external list**).
- Server log now reports requested vs generated fluency-feast problem counts and any bridge warnings when the fluency pool cannot fill every slot.

## 1.14.1 — Codex — 2026-06-28

Patch release fixing fluency feast bridge JSON parsing and adding a startup smoke test.

- Fixed `FluencyFeastBridge` response parsing: nested `{` in `counts` / `poolSizes` no longer breaks Gson parsing (was causing silent fallback to generated arithmetic).
- Added server-startup fluency bridge smoke test (`Fluency feast bridge OK` / `FAILED at startup` in the server log).
- Tests: `FluencyFeastBridgeTest` for nested JSON output parsing and optional Node smoke test.

## 1.14.0 — Codex — 2026-06-28

Minor release adding the internal fluency feast quiz source and fluency-improvement rewards.

- New quiz source `internal_fluency_feast`: reads `FluencyFeastConfig` + `Profile` rubric from the learner's active Math Quiz `.sqlite`, generates a fluency-based addition list via the shared `fluency_feast_bridge.mjs` Node bridge (bundled `fluency_core.js` / `math_utils.js`), and falls back to generated arithmetic when the bridge or DB is unavailable.
- End-of-quiz readout for fluency-feast quizzes: `Fluent: A% -> B%` computed before/after session ingest; when `% fluent` improves by at least one point, the dedicated per-player fluency-improvement reward replaces the normal completion reward.
- Control panel: new **Use internal fluency feast** quiz-source option; per-player **Fluency reward item/count** fields.
- Config: `mathQuizNodeExecutable` (default `node`), `fluencyFeastEnabled`, `playerFluencyRewards`.
- Requires Node.js on the machine running the mod/server for fluency feast generation and percent calculation (same algorithm as math-quiz PR #30).
- Tests: JUnit fixture SQLite loader tests; Node bridge equivalence test at `apps/math-quiz/tests/fluency_feast_bridge.test.mjs`.

## 1.13.7 — Codex — 2026-06-27

Patch release for Quest 01 quest keypad and the first M2 block-building loop.

- Added quiz session options carried by the quiz payload, so quest quizzes can
  hide flag buttons, quit buttons, pause button, progress text, and source labels
  without changing the normal MathQuest quiz UI
- Changed quest quiz result handling to suppress normal MathQuest item rewards in
  both multiplayer and singleplayer; quest rewards now only come from quest logic
- Changed M1 quest quizzes to repeat wrong or slower-than-`fluencyMs` facts inside
  the same quiz until every required fixed fact has met the fast-answer rule
- Excluded active Quest 01 learners from timed Wandering Nerd auto-spawns and
  removes assigned Wandering Nerds for the learner when a fresh quest starts
- Changed M2 fluency to require two consecutive fast correct answers for each
  fixed M2 problem
- Changed M2 quiz generation to seven-question batches drawn from remaining
  non-fluent M2 facts, with already-fluent facts used only as fillers when the
  remaining set is smaller than seven
- Added an M2 block-break trigger: after the active quest learner breaks three
  blocks in M2, a vanilla chime plays and the M2 quiz invitation opens
- Added M2 deepslate rewards: after each M2 quiz, the learner receives one
  `minecraft:deepslate` block per correct answer at or below `fluencyMs`; when
  those deepslate blocks are gone from inventory, the next M2 invitation opens
- Added a vanilla cave ambience loop during active M1; it stops by not replaying
  once M1 is no longer active
- Added ignored local-only OGG placeholder assets under
  `apps/minecraft/mods/mathquest/_assets/quest1/audio/` for future custom audio
  packaging; runtime currently uses vanilla `playsound`
- Added JUnit coverage for M2's two-consecutive-fast rule and updated payload
  coverage for carried quiz options
- **Tested:** `git diff --check`, `node --check
  apps/minecraft/mods/mathquest/fabric/src/main/resources/assets/mathquest/control_panel/quest.js`,
  `node --check
  apps/minecraft/mods/mathquest/fabric/src/main/resources/assets/mathquest/control_panel/control-panel.js`,
  `./gradlew :targets:fabric-26.1.2:test`, and
  `./apps/minecraft/mods/build-and-deploy.py mathquest` all passed locally. Jar
  `mathquest-fabric-1.13.7-mc26.1.2.jar` deployed to the Prism instance and
  local server mods folder; pending Minecraft playtest.

## 1.13.6 — Codex — 2026-06-27

Patch release for Quest 01 fixed quiz flow refinements.

- Changed quest quiz payloads to carry no normal MathQuest item rewards, so quest
  rewards now come only from quest action bundles such as the M1 torch reward
- Randomized the order of fixed quest quiz problems on each launch
- Added a quest-owned fixed M2 quiz definition: `2+n` and `n+2` for `n=3..9`,
  plus doubles `3+3` through `9+9`, for 21 required problems total
- Changed M2 completion to require each fixed M2 problem to have at least one
  correct answer at or below 2000 ms; non-fluent facts are reintroduced on the
  next M2 quiz launch
- Changed **Open Quest Quiz** in the Quest panel to use the same `start_quiz`
  command path as the command box
- Preserved expanded **Facts** sections in Problem Progress across panel refreshes
- Removed default start-teleport actions from M2 through M6 and migrates old
  exact single-teleport defaults to blank start action bundles
- Added JUnit coverage for the fixed M2 problem set, M2 fluency predicate, and
  no-default-teleport later milestone start bundles
- **Tested:** `git diff --check`, `node --check
  apps/minecraft/mods/mathquest/fabric/src/main/resources/assets/mathquest/control_panel/quest.js`,
  `node --check
  apps/minecraft/mods/mathquest/fabric/src/main/resources/assets/mathquest/control_panel/control-panel.js`,
  `./gradlew :targets:fabric-26.1.2:test`, and
  `./apps/minecraft/mods/build-and-deploy.py mathquest` passed; dispatcher
  deployed `mathquest-fabric-1.13.6-mc26.1.2.jar` to the configured Prism
  instance and `~/Documents/Code/mathquest-server/mods`; `unzip -l` verified the
  jar contains updated `QuestQuizDefinitions`, `CaveEscapeQuestService`, and
  `control_panel/quest.js`; pending Minecraft playtest

## 1.13.5 — Codex — 2026-06-27

Patch release for Quest 01 fixed zero/one quest quiz selection.

- Added a quest-owned fixed M1 quiz definition for `0+n`, `n+0`, `1+n`, and
  `n+1` for `n=0..9`, with duplicate same-side facts stored once
- Changed active Quest 01 quiz payloads to always use standard arithmetic and
  the quest-defined fixed problem set, so normal MathQuest player quiz type,
  internal source, range, and problem-count settings no longer leak into quest
  quizzes
- Changed M1 fluency to require at least one correct answer at or below
  `fluencyMs` per required oriented fact; default `fluencyMs` is 2000 ms
- Updated Quest 01 progress reporting so M1 shows 36 oriented zero/one targets
  instead of the older 19 canonical Add Zero/Add One facts
- Updated the regular MathQuest panel to mark an active quest learner as
  **In quest** and avoid saving normal quiz settings for that player while the
  quest run is active
- Updated Quest 01 docs/runbook for the fixed M1 problem set and completion rule
- Added JUnit coverage for the oriented M1 problem set and completion predicate
- **Tested:** `node --check
  apps/minecraft/mods/mathquest/fabric/src/main/resources/assets/mathquest/control_panel/quest.js`,
  `node --check
  apps/minecraft/mods/mathquest/fabric/src/main/resources/assets/mathquest/control_panel/control-panel.js`,
  `git diff --check`, `./gradlew :targets:fabric-26.1.2:test`, and
  `./apps/minecraft/mods/build-and-deploy.py mathquest` passed; dispatcher
  deployed `mathquest-fabric-1.13.5-mc26.1.2.jar` to the configured Prism
  instance and `~/Documents/Code/mathquest-server/mods`; `unzip -l` verified the
  jar contains `QuestQuizDefinitions`, updated `CaveEscapeQuestService`,
  `QuizPayloadBuilder`, and updated control-panel assets; direct Prism folder
  listing confirmed the 1.13.5 jar; direct server-folder listing was blocked by
  macOS permissions, but deploy helper output reported the server copy succeeded;
  pending Minecraft playtest

## 1.13.4 — Codex — 2026-06-27

Patch release for Quest 01 direct invitation quiz launch and action debugging.

- Changed the Quest 01 invitation payload to carry the direct quiz payload so
  **Accept** starts the quiz locally immediately; the server response is now used
  for logging and retry cleanup rather than being required to launch the quiz
- Added verbose server-thread info logging for quest action results
- Added a persisted Quest panel Run log backed by `quest.json`, plus a **Clear
  Log** button
- Added cautious Quest panel auto-refresh while no form control is focused, so
  delayed scheduled actions can appear in the Run log during playtests
- Added `start_quiz` as a custom command-box action and preset for immediate
  direct quiz launch
- Changed the Quest panel layout so Command and Run are equal-width side-by-side
  sections on wide screens
- Added direct handling for `gamerule keepInventory true/false` through the
  Minecraft game-rule API, avoiding the command parse failure seen in server logs
- Added JUnit coverage for invitation payload-to-direct-quiz conversion
- **Tested:** `node --check
  apps/minecraft/mods/mathquest/fabric/src/main/resources/assets/mathquest/control_panel/quest.js`,
  `./gradlew :targets:fabric-26.1.2:test`, and
  `./apps/minecraft/mods/build-and-deploy.py mathquest` all passed; dispatcher
  deployed `mathquest-fabric-1.13.4-mc26.1.2.jar` to the configured Prism
  instance and `~/Documents/Code/mathquest-server/mods`; `unzip -l` verified the
  jar contains updated `MathQuestClient`, `CaveEscapeQuestService`,
  `QuestInvitationPayload`, `QuestInvitationScreen`,
  `QuestInvitationResponseFlow`, `OpenQuizPayload`, and control-panel assets;
  direct Prism folder listing confirmed the 1.13.4 jar; pending Minecraft
  playtest

## 1.13.3 — Codex — 2026-06-27

Patch release for Quest 01 invitation accept launch behavior.

- Fixed the invitation **Accept** path to close the invitation screen before
  sending the accept response, preventing a client-side ordering race where the
  follow-up quiz screen could be cleared by the old prompt closing
- Removed the duplicate large title overlay from the M1 invitation and decline
  retry bundles; the invitation screen text above the buttons is now the visible
  prompt
- Migrates existing 1.13.2 local M1 start action bundles that still contain the
  duplicate invitation title line
- Added JUnit coverage for the title-free invitation action bundles and for the
  Accept/Decline response ordering
- **Tested:** `node --check
  apps/minecraft/mods/mathquest/fabric/src/main/resources/assets/mathquest/control_panel/quest.js`,
  `./gradlew :targets:fabric-26.1.2:test`, and
  `./apps/minecraft/mods/build-and-deploy.py mathquest` all passed; dispatcher
  deployed `mathquest-fabric-1.13.3-mc26.1.2.jar` to the configured Prism
  instance and `~/Documents/Code/mathquest-server/mods`; `unzip -l` verified the
  jar contains updated `MathQuestClient`, `MathQuestMod`,
  `CaveEscapeQuestService`, `QuestInvitationScreen`,
  `QuestInvitationResponseFlow`, `OpenQuizPayload`, and invitation payload
  classes; direct Prism folder listing confirmed the 1.13.3 jar; pending
  Minecraft playtest

## 1.13.2 — Codex — 2026-06-27

Patch release for Quest 01 knowledge invitation Accept / Decline flow.

- Fixed `fabric-26.1.2` `MathQuestMod` to register `CaveEscapeQuestService.tick()`
  and quest respawn/post-quiz hooks so scheduled `wait` actions actually run on
  the primary deploy target
- Replaced default M1 `open_quiz` with `open_quiz_invitation`: after the 20-second
  wait, chat, and title, the learner sees **Accept** and **Decline** buttons
- **Accept** opens the first quest quiz directly (skips the generic Math Quest offer
  screen)
- **Decline** closes the prompt; after **22 seconds** the chat, title, and
  invitation repeat until the learner accepts
- Added `QuestInvitationPayload` / `QuestInvitationResponsePayload` networking and
  `QuestInvitationScreen` (shared + 26.1.2 override)
- Extended `OpenQuizPayload` with `directToQuiz` for invitation-accept quiz launch
- **Tested:** `node --check
  apps/minecraft/mods/mathquest/fabric/src/main/resources/assets/mathquest/control_panel/quest.js`,
  `./gradlew :targets:fabric-26.1.2:test`, and
  `./apps/minecraft/mods/build-and-deploy.py mathquest` all passed; dispatcher
  deployed `mathquest-fabric-1.13.2-mc26.1.2.jar` to the configured Prism
  instance and `~/Documents/Code/mathquest-server/mods`; `unzip -l` verified the
  jar contains updated `CaveEscapeQuestService`, `QuestInvitationScreen`,
  `QuestInvitationPayload`, and `MathQuestMod`; pending Minecraft playtest

## 1.13.1 — Codex — 2026-06-27

Patch release for Quest 01 action flow refinements.

- Changed inactive Quest panel try-number display to use the server-computed next
  try number from existing files instead of `last try + 1`, so Reset no longer
  makes the UI look as if it already started a new attempt
- Added `M1`, `M2`, etc. labels to milestone cards
- Added `wait <seconds>` / `delay <seconds>` to milestone action bundles, executed
  from the server tick rather than blocking the server thread
- Updated default M1 start actions to enable `keepInventory`, set the learner to
  survival, teleport and clear inventory, wait 20 seconds, show the knowledge
  invitation text, then open the quiz offer
- Updated default M1 end actions to give one torch and show `Let there be light.`
  after the M1 milestone reaches fluency
- Added post-quiz progress recomputation and end-action execution for completed
  milestones
- Added active-quest respawn handling so a learner who dies returns to the current
  milestone coordinates
- Expanded player backups to include XP level, total XP, XP progress, and game
  mode; restore now restores those fields along with location, inventory,
  selected slot, health, food, and saturation
- Changed the `clear_inventory` action and Quest panel `Clear + Survival` preset
  to switch the learner to survival before clearing inventory
- **Tested:** `node --check
  apps/minecraft/mods/mathquest/fabric/src/main/resources/assets/mathquest/control_panel/quest.js`,
  `./gradlew :targets:fabric-26.1.2:test`, and
  `./apps/minecraft/mods/build-and-deploy.py mathquest` all passed; dispatcher
  deployed `mathquest-fabric-1.13.1-mc26.1.2.jar` to the configured Prism
  instance and `~/Documents/Code/mathquest-server/mods`; `unzip -l` verified the
  jar contains updated `MathQuestMod`, `CaveEscapeQuestService`,
  `control-panel.css`, `quest.html`, and `quest.js`; direct Prism folder listing
  confirmed the 1.13.1 jar; pending Minecraft playtest

## 1.13.0 — Codex — 2026-06-27

Feature release for Quest 01 run setup and operator action bundles.

- Stored the second Quest 01 location, `Deep passage`, at `1378 -13 1312`
- Changed `Start Fresh Run` to run the M1 start bundle after creating the run;
  the default bundle backs up the selected player, teleports them to M1, clears
  their carried inventory/armor/offhand, and shows the quest-start title
- Added player backup files under the Quest 01 local data folder before any
  start-bundle clear/teleport, plus a Quest panel `Restore Player` action that
  restores location, inventory, selected hotbar slot, health, food, and saturation
- Added editable per-milestone `startActions` and `endActions`, with panel buttons
  to run either bundle for builder/executor testing
- Added a Quest panel command runner with presets, `{player}` placeholder support,
  and server-backed Brigadier command suggestions
- Added `Continue Current Run` so an active test run can rerun the current
  milestone setup without incrementing the try number
- Fixed inactive/run-reset real-name autofill so selecting `rjcomp` populates
  `Randy` from the player-name lookup
- Fixed dark control-panel button hover states so white button text remains
  readable
- **Tested:** `node --check
  apps/minecraft/mods/mathquest/fabric/src/main/resources/assets/mathquest/control_panel/quest.js`,
  `./gradlew :targets:fabric-26.1.2:test`; dispatcher build/deploy succeeded
  for `mathquest-fabric-1.13.0-mc26.1.2.jar` to the configured Prism instance
  and `~/Documents/Code/mathquest-server/mods`; `unzip -l` verified the jar
  contains updated `CaveEscapeQuestService`, `MathQuestControlPanelServer`,
  `control-panel.css`, `quest.html`, and `quest.js`; pending Minecraft playtest

## 1.12.3 — Codex — 2026-06-27

Patch release for Quest 01 milestone coordinates and setup snapshots.

- Stored the current Cave Escape endpoints in the Quest 01 world config defaults:
  `Start` at `1375 -18 1311` and `Breakthrough` at `1401 86 1293`
- Persisted migrated `world.json` state after load so existing local configs pick
  up the known endpoint coordinates instead of only seeing them in memory
- Moved online-player selection into the Run panel and defaulted fresh inactive
  runs to the selected online player
- Removed the separate World panel; milestone cards now own their location label
  and a single Minecraft-style coordinate field formatted as `x y z`
- Added `Save Version`, which writes timestamped setup snapshots containing both
  `quest.json` and `world.json` under the Quest 01 `versions/` folder
- Updated Quest 01 docs to describe current coordinate storage and setup
  snapshots
- **Tested:** `node --check
  apps/minecraft/mods/mathquest/fabric/src/main/resources/assets/mathquest/control_panel/quest.js`,
  `./gradlew :targets:fabric-26.1.2:test`; dispatcher build/deploy succeeded
  for `mathquest-fabric-1.12.3-mc26.1.2.jar` to the configured Prism instance
  and `~/Documents/Code/mathquest-server/mods`; `unzip -l` verified the jar
  contains updated `CaveEscapeQuestService`, `quest.html`, and `quest.js`;
  pending Minecraft playtest

## 1.12.2 — Codex — 2026-06-27

Patch release for Quest 01 world/location setup.

- Removed the Quest panel world-seed field and seed display; Quest 01 now assumes
  the operator has already loaded the desired server world and only tracks spawn
  plus named coordinates in that current world
- Renamed milestone/location IDs and defaults to the simpler cave path:
  `m1_cave_start`, `m2_deep_passage`, `m3_winding_tunnel`, `m4_chamber`,
  `m5_connector`, `m6_surface_break`
- Updated milestone display text and default story snippets to remove interim
  glimmer/daylight wording before the final surface break
- Added migration logic so existing local `quest.json` and `world.json` files
  using the old IDs are rewritten to the new IDs on load
- Updated Quest 01 docs/spec to match the current-world-only model
- **Tested:** `node --check
  apps/minecraft/mods/mathquest/fabric/src/main/resources/assets/mathquest/control_panel/quest.js`,
  `./gradlew :targets:fabric-26.1.2:test`; dispatcher build/deploy succeeded
  for `mathquest-fabric-1.12.2-mc26.1.2.jar` to both the Prism instance and
  `~/Documents/Code/mathquest-server/mods`; `unzip -l` verified the jar
  contains updated `CaveEscapeQuestService`, `quest.html`, and `quest.js`;
  pending Minecraft playtest

## 1.12.1 — Codex — 2026-06-27

Patch release for Quest 01 run targeting.

- Changed Quest 01 runtime targeting so a fresh run can target any Minecraft
  player, not only WildPetal/Kid1
- Resolved the quest learner name from `playerRealNames`, falling back to the
  Minecraft username when no lookup exists
- Kept the quest active SQLite naming shape but made the learner segment generic:
  `quest1_try{N}_{resolvedName}_{YYYY-MM-DD}.sqlite`
- Updated the Quest panel so selecting an online player fills both the run target
  and resolved real name; manual real-name edits are still respected
- **Tested:** `node --check
  apps/minecraft/mods/mathquest/fabric/src/main/resources/assets/mathquest/control_panel/quest.js`,
  `./gradlew :targets:fabric-26.1.2:test`; dispatcher build/deploy succeeded
  for `mathquest-fabric-1.12.1-mc26.1.2.jar` to both the Prism instance and
  `~/Documents/Code/mathquest-server/mods`; `unzip -l` verified the jar
  contains updated `CaveEscapeQuestService` and `quest.js`; pending Minecraft
  playtest

## 1.12.0 — Codex — 2026-06-27

Feature release for the first Quest 01 Cave Escape implementation pass.

- Added `http://127.0.0.1:8765/quest.html`, a local Quest 01 control panel for
  run setup, world spawn/location editing, milestone/status editing,
  problem progress review, content cue editing, and mechanic controls
- Added file-backed Quest 01 state under
  `<sharedDataDir>/quests/quest1-caveescape/quest.json` and `world.json`
- Added Quest 01 addition problem generation from the canonical single-digit
  addition taxonomy, with milestone-aware prioritization of non-fluent facts
- Added exact active-file ingest support so Quest 01 appends into
  `quest1_try{N}_K1_{YYYY-MM-DD}.sqlite` instead of a normal `math-flu`
  learner file
- Added initial GM-driven mechanics for combat-gate entity spawn/clear,
  explore-gate block place/clear, and opening the current quest quiz for the
  learner when online
- Added local-only ignore coverage for `apps/minecraft/mods/mathquest/_assets/`
  so large/generated quest assets stay out of git
- Added implementation/runbook documentation at
  `docs/quests/2026-06-27_quest-01-cave-escape-implementation.md`
- **Tested:** `python3 apps/math-quiz/tools/test_session_ingest.py`,
  `python3 -m py_compile apps/math-quiz/tools/session_ingest.py`,
  `./gradlew :targets:fabric-26.1.2:test`; dispatcher build/deploy succeeded
  for `mathquest-fabric-1.12.0-mc26.1.2.jar` to both the Prism instance and
  `~/Documents/Code/mathquest-server/mods`; `unzip -l` verified the jar
  contains `CaveEscapeQuestService`, `quest.html`, `quest.js`, and bundled
  `mathquest-tools/session_ingest.py`; pending Minecraft playtest

## 1.11.11 — Codex — 2026-06-26

Patch release for Randy's 1.11.10 server playtest where ingest ran but used the
wrong active folder name.

- Changed the MathQuest active Math Quiz folder default from `_data/tl-kids` to
  `_data/tlkids`
- Added config normalization so existing `mathquest.json` files with an absolute
  or `~`-based path ending in `apps/math-quiz/_data/tl-kids` are rewritten to
  `apps/math-quiz/_data/tlkids` on startup
- Aligned the internal problem-list/quick-quiz loader default to `_data/tlkids`
- Added a regression test for the dashed-to-undashed TLKids path migration
- **Tested:** `python3 apps/math-quiz/tools/test_session_ingest.py`,
  `python3 apps/math-quiz/tools/test_dev_server.py`, `python3 -m py_compile
  apps/math-quiz/tools/session_ingest.py apps/math-quiz/tools/dev_server.py`,
  `./gradlew :targets:fabric-26.1.2:test -Ptargets=fabric-26.1.2`,
  `./gradlew :targets:fabric-1.21.11:compileJava
  -Ptargets=fabric-1.21.11`; dispatcher build/deploy succeeded for
  `mathquest-fabric-1.11.11-mc26.1.2.jar`; jar inspection verified the default
  active path contains `_data/tlkids`

## 1.11.10 — Codex — 2026-06-26

Patch release for Randy's 1.11.9 server playtest where the raw session export
worked but the Python ingest script could not be found.

- Bundled `apps/math-quiz/tools/session_ingest.py` and `anchor_store.py` inside
  the MathQuest jar under `mathquest-tools/`
- Added runtime fallback extraction to `mathquest_ingest_tools/` under the
  MathQuest data/config directory when no checkout copy of `session_ingest.py`
  is found
- Added an info log showing the ingest script path being used, so the server log
  now identifies both the raw single-session SQLite path and the ingest helper
  path before reporting the active multi-session update
- **Tested:** `python3 apps/math-quiz/tools/test_session_ingest.py`,
  `python3 apps/math-quiz/tools/test_dev_server.py`, `python3 -m py_compile
  apps/math-quiz/tools/session_ingest.py apps/math-quiz/tools/dev_server.py`,
  `./gradlew :targets:fabric-26.1.2:test -Ptargets=fabric-26.1.2`,
  `./gradlew :targets:fabric-1.21.11:compileJava
  -Ptargets=fabric-1.21.11`; dispatcher build/deploy succeeded for
  `mathquest-fabric-1.11.10-mc26.1.2.jar`; `unzip -l` verified the jar includes
  `mathquest-tools/anchor_store.py` and `mathquest-tools/session_ingest.py`;
  `javap` verified the ingestor falls back to bundled script extraction

## 1.11.9 — Codex — 2026-06-26

Patch release for the `fabric-26.1.2` target overlay after Randy's 1.11.8
server playtest.

- Fixed the target-specific `fabric-26.1.2` server result handler, which was
  still calling `SessionExporter.exportSession(...)` without invoking the shared
  Math Quiz ingest bridge
- Fixed the target-specific `fabric-26.1.2` single-player result screen to call
  the same ingest bridge after writing the raw session file
- Kept the 1.11.8 flexible active-file matching rule: append by exact
  `_<real name>_` filename boundary and newest filename date, regardless of
  prefix such as `math-flu`
- **Tested:** `python3 apps/math-quiz/tools/test_session_ingest.py`,
  `python3 apps/math-quiz/tools/test_dev_server.py`, `python3 -m py_compile
  apps/math-quiz/tools/session_ingest.py apps/math-quiz/tools/dev_server.py`,
  `./gradlew :targets:fabric-26.1.2:test -Ptargets=fabric-26.1.2`,
  `./gradlew :targets:fabric-1.21.11:compileJava
  -Ptargets=fabric-1.21.11`; dispatcher build/deploy succeeded for
  `mathquest-fabric-1.11.9-mc26.1.2.jar`; `javap` verified the built
  `MathQuestMod` bytecode calls `MathQuizSessionIngestor.ingest(...)`

## 1.11.8 — Codex — 2026-06-26

Patch release for Randy's first local ingest playtest.

- Changed shared Math Quiz session ingest to find an existing active SQLite file
  by exact `_<real name>_` filename boundaries and the newest filename date, even
  when that file has another prefix such as `math-flu`
- Preserved the existing active file name when appending MathQuest sessions into
  a Math Quiz lineage like `math-flu_Randy_2026-06-16.sqlite`
- Added server/client log lines for the raw single-session SQLite path and the
  active multi-session SQLite path updated by the ingest step
- **Tested:** `python3 apps/math-quiz/tools/test_session_ingest.py`,
  `python3 apps/math-quiz/tools/test_dev_server.py`, `python3 -m py_compile
  apps/math-quiz/tools/session_ingest.py apps/math-quiz/tools/dev_server.py`,
  `./gradlew :targets:fabric-26.1.2:test -Ptargets=fabric-26.1.2`,
  `./gradlew :targets:fabric-1.21.11:compileJava
  -Ptargets=fabric-1.21.11`; dispatcher build/deploy succeeded for
  `mathquest-fabric-1.11.8-mc26.1.2.jar`

## 1.11.7 — Codex — 2026-06-26

Patch release for shared Math Quiz/MathQuest SQLite accumulation.

- Added `apps/math-quiz/tools/session_ingest.py`, a reusable module/CLI that
  archives a raw single-session SQLite file and accumulates it into the active
  per-user multi-session SQLite folder using the existing `anchor_store` naming
  and append rules
- Updated the Math Quiz local `dev_server.py` source-save path to use the shared
  ingest module while preserving the existing "Continue latest requires an
  existing file" behavior
- Added MathQuest config for `mathQuizActiveDir`, defaulting to
  `~/Documents/Code/fof-mono/apps/math-quiz/_data/tl-kids`, plus an enabled
  local Python ingest bridge
- Hooked standard MathQuest session exports to invoke the shared ingest CLI after
  writing the raw `mathquest_<name>_<timestamp>.sqlite` file, so the active
  `tl-kids` per-user file is created/appended automatically
- Aligned MathQuest's internal problem-list/quick-quiz lookup default to the same
  `_data/tl-kids` active folder
- Added Python tests for the shared ingest path and MathQuest-prefix accumulation
- **Tested:** `python3 apps/math-quiz/tools/test_session_ingest.py`,
  `python3 apps/math-quiz/tools/test_dev_server.py`, `python3 -m py_compile
  apps/math-quiz/tools/session_ingest.py apps/math-quiz/tools/dev_server.py`,
  `./gradlew :targets:fabric-26.1.2:test -Ptargets=fabric-26.1.2`,
  `./gradlew :targets:fabric-1.21.11:compileJava
  -Ptargets=fabric-1.21.11`; dispatcher build/deploy succeeded for
  `mathquest-fabric-1.11.7-mc26.1.2.jar`

## 1.11.6 — Codex — 2026-06-26

Patch release for Randy's first playtest of the in-game flag-reason panel.

- Added more vertical room between the answer box, correct-answer text,
  `Choose flag reasons`, reason toggles, comment label, and comment field
- Changed `Flag previous` to open the same reason/comment panel and apply the
  selected flags to the previously answered problem
- Added local single-player SQLite flag updates for previously recorded answers
  so `Flag previous` updates `mathquest_data.db` instead of inserting a duplicate
  answer row
- `Continue & insert` from the previous-flag panel re-queues the previous fact
  later in the current quiz
- Applied the same UI behavior to the shared screen code and the active
  `fabric-26.1.2` target override
- **Tested:** `./gradlew :targets:fabric-26.1.2:test
  -Ptargets=fabric-26.1.2`,
  `./gradlew :targets:fabric-1.21.11:compileJava
  -Ptargets=fabric-1.21.11`, dispatcher build/deploy succeeded for
  `mathquest-fabric-1.11.6-mc26.1.2.jar`; Minecraft playtest still pending

## 1.11.5 — Codex — 2026-06-26

Patch release for the in-game `Skip & flag` flow.

- Changed `Skip & flag` from an immediate generic flag into an inline flag-reason
  panel with the same reason keys as Math Quiz: `skip-noreason`, `distracted`,
  `interrupted`, `error`, `stall`, `dontknow`, and `other`
- Added an optional comment field; comments are saved as `note:<text>` flags
- Added `Continue` and `Continue & insert`; insert re-queues the same fact later
  in the quiz
- Added `flags_json` to the local single-player `mathquest_data.db` answer table,
  with migration for existing DBs, and kept final single-session SQLite export
  writing `ProblemAttempts.flags_json`
- Applied the same UI flow to the shared screen code and the active
  `fabric-26.1.2` target override
- **Tested:** `./gradlew :targets:fabric-26.1.2:test
  -Ptargets=fabric-26.1.2`,
  `./gradlew :targets:fabric-1.21.11:compileJava
  -Ptargets=fabric-1.21.11`, dispatcher build/deploy succeeded for
  `mathquest-fabric-1.11.5-mc26.1.2.jar`; Minecraft playtest still pending

## 1.11.4 — Codex — 2026-06-26

Patch release for the in-game keypad follow-up.

- Reduced the answer entry box to about half its previous width
- Moved the answer entry box closer to the problem text
- Made `/mathquest start` in integrated single-player worlds spawn an unlocked
  NPC by default, while dedicated-server starts continue to use the configured
  player lock default
- Applied the same changes to the shared screen/spawner code and the active
  `fabric-26.1.2` target overrides
- **Tested:** `./gradlew :targets:fabric-26.1.2:test
  -Ptargets=fabric-26.1.2`,
  `./gradlew :targets:fabric-1.21.11:compileJava
  -Ptargets=fabric-1.21.11`, dispatcher build/deploy succeeded for
  `mathquest-fabric-1.11.4-mc26.1.2.jar`; Minecraft playtest still pending

## 1.11.3 — Codex — 2026-06-26

Patch release for Randy's first successful view of the updated in-game keypad.

- Reduced the number keypad buttons to about half the previous width while
  keeping the same four-row layout
- Added a larger boxed answer display so the current answer entry is visually
  distinct from the problem text
- Moved the answered-count and completion-percent text lower so it no longer
  overlaps the action/quit buttons
- Applied the same layout tuning to the shared screen and the active
  `fabric-26.1.2` target override
- **Tested:** `./gradlew :targets:fabric-26.1.2:test
  -Ptargets=fabric-26.1.2`,
  `./gradlew :targets:fabric-1.21.11:compileJava
  -Ptargets=fabric-1.21.11`, dispatcher build/deploy succeeded for
  `mathquest-fabric-1.11.3-mc26.1.2.jar`, jar metadata reports `1.11.3`, and
  the Prism mods folder contains only that MathQuest jar; Minecraft playtest
  still pending

## 1.11.2 — Codex — 2026-06-26

Patch release for the 1.11.1 keypad retest.

- Fixed the actual `fabric-26.1.2` target override for `QuizScreen`; 1.11.1
  changed the shared screen, but this target intentionally excludes that shared
  file and packages `targets/fabric-26.1.2/src/main/.../QuizScreen.java`
- Aligned the 26.1.2 target-local quiz offer/result/server result path with
  quick-quiz source labels and skip/previous flags
- Added a client-side chat line on join, `MathQuest <version> loaded`, so the
  loaded client jar version is visible in-game
- **Tested:** `./gradlew :targets:fabric-26.1.2:test
  -Ptargets=fabric-26.1.2`, dispatcher build/deploy succeeded for
  `mathquest-fabric-1.11.2-mc26.1.2.jar`, Prism mods folder contains only that
  MathQuest jar, and `QuizScreen.class` in the jar contains the new
  `Skip & flag` / `Flag previous` / `Quit & save` labels; Minecraft playtest
  still pending

## 1.11.1 — Codex — 2026-06-26

The in-game MathQuest quiz screen now follows the current math-quiz anchor
keypad layout more closely.

- Replaced the compact MathQuest keypad with the anchor-style layout:
  `7 8 9`, `4 5 6`, `1 2 3`, `+/- 0 C`
- Added action buttons matching the math-quiz flow: Skip & flag, Flag previous,
  Pause/Resume, Quit & save, and Quit & abandon
- Changed keypad auto-submit behavior to submit once the typed answer has enough
  digits for the correct answer, matching `anchor.js`
- Added partial-save support for Quit & save, keeping only answered/skipped
  problems in the saved result
- Persisted basic skip/previous flags through the existing MathQuest SQLite
  export path
- **Tested:** `./gradlew :targets:fabric-26.1.2:test
  -Ptargets=fabric-26.1.2`, and dispatcher build/deploy succeeded for
  `mathquest-fabric-1.11.1-mc26.1.2.jar`; Minecraft playtest still pending

## 1.11.0 — Codex — 2026-06-25

The control panel can now choose between generated quiz settings, coach-authored
internal problem lists, and math-quiz-generated internal quick quizzes.

- Replaced the per-player Use internal checkbox with a Quiz source selector:
  Use settings below, Use internal problem list, or Use internal quick quiz
- Made Use internal quick quiz the default per-player source
- Added Java loading for math-quiz `QuickPracticeItems`, reading the seven
  stored rows for the selected operation from the learner's latest SQLite file
- Kept Operation editable for quick quiz while Range and Problems are disabled;
  internal problem lists still disable Operation, Range, and Problems
- Preserved `playerUseInternalProblemLists` as a compatibility boolean while
  saving the clearer `playerInternalQuizSources` config
- Updated the dedicated server payload path and the local/client offer screen to
  honor the selected quiz source
- **Tested:** `node --check` for the control panel JS, `./gradlew
  :targets:fabric-26.1.2:test -Ptargets=fabric-26.1.2`, and dispatcher
  build/deploy succeeded for `mathquest-fabric-1.11.0-mc26.1.2.jar`; Minecraft
  playtest still pending

## 1.10.0 — Codex — 2026-06-23

The local web control panel can now be iterated without rebuilding the mod jar
for ordinary HTML/CSS/JS and NPC preview PNG changes.

- Added `controlPanelAssetsDir` config so the embedded `:8765` server can serve
  static MathQuest assets from disk first, with jar resources as fallback
- Added disk-first static routing for `control_panel/*.html/css/js` and
  `textures/entity/*.png`, with traversal guards and `Cache-Control: no-store`
- Added startup logging so the server reports whether it is using disk assets or
  bundled jar assets
- Added `tools/control_panel_dev.py`, a dependency-free local dev proxy on
  `127.0.0.1:8766` that serves live repo assets and proxies `/api/*` to `:8765`
- Added route/path tests for static asset mapping and traversal rejection
- Added the Codex hot-reload plan alongside the existing Composer plan under
  `.cursor/plans/`
- **Tested:** `py_compile` for `control_panel_dev.py`, `node --check` for
  the control panel JS, `./gradlew :targets:fabric-26.1.2:test
  -Ptargets=fabric-26.1.2`, dev proxy static index smoke test on `127.0.0.1:8766`,
  and dispatcher deploy succeeded from local Codex worktree; Minecraft playtest
  still pending

## 1.9.9 — Codex — 2026-06-23

The control panel can now edit the Minecraft-player to real-name mapping, and
MathQuest exports use the real name instead of the Minecraft username.

- Added saved `playerRealNames` config with defaults for Randy, K2, TL,
  Kid1, and `SkulkScraper -> Guest`
- Added compact editable Real name fields under each player dropdown in the
  MathQuest control panel
- Included real-name edits in Save, Spawn NPC, and Open Quiz requests so the
  setting is stored before the next quiz starts
- Changed internal problem-list lookup to use the saved real-name map
- Changed standard and written-column SQLite exports to name/session rows with
  the resolved real name instead of the Minecraft player name
- Added SkulkScraper to the selectable control-panel player list
- **Tested:** `node --check` for the control panel JS, `./gradlew
  :targets:fabric-26.1.2:test -Ptargets=fabric-26.1.2`, and dispatcher
  deploy succeeded from local Codex worktree; Minecraft playtest still pending

## 1.9.8 — Codex — 2026-06-22

The MathQuest control panel now has an explicit per-player internal problem-list
switch for standard arithmetic quizzes.

- Added a Use internal checkbox to each player card in the local control panel
- When Use internal is checked, operation, range, and problem-count controls stay
  visible but are disabled/gray because the math-quiz SQLite problem list supplies
  the exact problems
- Saved the new setting in `playerUseInternalProblemLists`, and included it when
  clicking Save, Spawn NPC, or Open Quiz
- Updated MathQuest's math-quiz SQLite loader to use the same "next internal list"
  queue order as the current math-quiz app: lowest `ProblemLists.list_order` first
- After a completed standard arithmetic quiz, MathQuest now honors the internal
  list's retain/delete-after-use flag by incrementing usage for retained lists or
  deleting/reindexing consumed lists
- Brought the current math-quiz `anchor.html` internal-list support files from
  `feature/math-quiz-further-dev` into this branch
- **Tested:** `node --check` for the control panel JS, `py_compile` for the
  pulled math-quiz Python files, `./gradlew :targets:fabric-26.1.2:test
  -Ptargets=fabric-26.1.2`, and dispatcher deploy succeeded from local Codex
  worktree; Minecraft playtest still pending

## 1.9.7 — Codex — 2026-06-22

The mob spawn planning map now uses actual server terrain instead of a blank grid.

- Added world seed to `/api/status` so the local panels can display the current seed
- Added `/api/terrain-map.png`, which renders a top-down terrain PNG from the selected
  server dimension, center, and view radius
- Added reusable `terrain-map.js` canvas component with terrain image loading, grid,
  drag-to-pan, mouse-wheel zoom, click-to-pick world positions, and overlay hooks
- Updated `/mob-spawn.html` to use the terrain component and draw mob spawn shapes
  over the terrain layer
- Current terrain layer colors surface blocks and biome grass/water; it does not yet
  discover external seed-map structures like villages or strongholds
- **Tested:** `./gradlew :targets:fabric-26.1.2:test -Ptargets=fabric-26.1.2`
  and dispatcher deploy succeeded from local Codex worktree; Minecraft playtest
  still pending

## 1.9.6 — Codex — 2026-06-22

Patch release for the first mob spawn planning page playtest.

- Added a Kill Area tool to `/mob-spawn.html` for clearing a selected mob type
  around the current center point
- Kill Area supports circle and square shapes with a configurable radius
- Added `/api/kill-mob-area`, which removes the selected entity type in the chosen
  dimension/area on the server thread
- Changed Use Player Location to fetch fresh server status before copying coordinates
- Changed the player dropdown to refresh/capture coordinates when selecting a player
- **Tested:** `./gradlew :targets:fabric-26.1.2:test -Ptargets=fabric-26.1.2`
  and dispatcher deploy succeeded from local Codex worktree; Minecraft playtest
  still pending

## 1.9.5 — Codex — 2026-06-22

Mob spawning now has a dedicated planning page.

- Added `/mob-spawn.html` as a second local control-panel page served on the same
  `127.0.0.1:8765` server as the main MathQuest panel
- Added links between the main MathQuest panel and the mob spawn panel
- Added online-player coordinate capture plus editable center X/Y/Z and dimension controls
- Added a top-down planning canvas for previewing the center point, queued spawn shapes,
  and click-to-place offsets
- Added a spawn recipe builder for point, filled circle, circle rim, and line shapes
- Added queued mob spawn entries with Spawn, Duplicate, Remove, Spawn All, and recent
  run history that can be queued again
- Added `/api/spawn-mob-plan`, which validates mobs, targets dimensions, and spawns
  batch entries on the server thread
- **Tested:** `./gradlew :targets:fabric-26.1.2:test -Ptargets=fabric-26.1.2`
  and dispatcher deploy succeeded from local Codex worktree; Minecraft playtest
  still pending

## 1.9.4 — Codex — 2026-06-21

Control-panel fun button release.

- Added per-player mob spawn controls below the active NPC status
- Added generated Minecraft 26.1.2 mob autocomplete data for living vanilla mobs
- Mob fields hide the `minecraft:` prefix and support Tab completion like reward items
- Added count and radius inputs for spawning a chosen mob around the selected online player
- Added `/api/spawn-mobs`, which validates summonable entity IDs and spawns on the
  Minecraft server thread in the player's current server level
- **Tested:** `./gradlew :targets:fabric-26.1.2:test -Ptargets=fabric-26.1.2`
  and dispatcher deploy succeeded from local Codex worktree; Minecraft playtest
  still pending

## 1.9.3 — Codex — 2026-06-21

Patch release for the 1.9.2 control-panel retest.

- Unlocked spawned NPCs no longer show the target player's Minecraft name in parentheses
- Confirmed unlocked NPC interaction remains public because the right-click gate only
  blocks other players when `lockedToTarget` is true
- Added a generated Minecraft 26.1.2 item autocomplete list for reward item fields
- Reward item fields now display vanilla item IDs without the `minecraft:` prefix
- Pressing Tab in a reward item field completes the first matching item ID
- Control-panel reward saves normalize plain item names like `diamond` or `Golden Apple`
  into namespaced Minecraft IDs before writing `mathquest.json`
- **Tested:** `./gradlew :targets:fabric-26.1.2:test -Ptargets=fabric-26.1.2`
  and dispatcher deploy succeeded from local Codex worktree; Minecraft playtest
  still pending

## 1.9.2 — Codex — 2026-06-21

Patch release for the 1.9.1 control-panel retest.

- Added saved per-player NPC lock settings so unchecked "Lock to player" stays unchecked
- Made Spawn NPC/Open Quiz persist the current lock checkbox value before acting
- Changed NPC spawn/location chat and logs to use the selected NPC persona name instead
  of hard-coded Wandering Nerd text
- Automatic timed NPC spawns now use each player's saved NPC and lock settings
- **Tested:** `./gradlew :targets:fabric-26.1.2:test -Ptargets=fabric-26.1.2`
  and dispatcher deploy succeeded from local Codex worktree; Minecraft playtest
  still pending

## 1.9.1 — Codex — 2026-06-21

Patch release for the first 1.9.0 dedicated-server control-panel test.

- Fixed the panel auto-refresh rebuilding active player cards while Randy was editing them
- Added saved per-player NPC selections so NPC dropdowns no longer reset to The Wandering Nerd
- Made operation, range, and problem count editable from each player card
- Added per-player problem counts to `PlayerQuizPreset` and server quiz resolution
- Saved player card edits together: reward, NPC, quiz type, operation, range, and problem count
- **Tested:** `./gradlew :targets:fabric-26.1.2:test -Ptargets=fabric-26.1.2`
  and dispatcher deploy succeeded from local Codex worktree; Minecraft playtest
  still pending

## 1.9.0 — Codex — 2026-06-21

MathQuest now supports editable NPC dialogue from the local control panel and a first
written-column paper-practice quiz type.

- Added Paper Coach Penny as the fifth selectable NPC persona with its own texture
- Changed the NPC gallery to show persona names instead of the generic villager-model label
- Made each NPC's dialogue lines editable in the web gallery and persisted in `mathquest.json`
- Added per-player quiz type selection: standard arithmetic or written column arithmetic
- Added a written-column screen where an evaluator enters a code, student answer, notes,
  and a Correct/Partial/Needs Work evaluation after the child solves on paper
- Added separate `mathquest_written_column_*.sqlite` exports with `WrittenColumnSessions`
  and `WrittenColumnAttempts` tables for paper-practice sessions
- **Tested:** `./gradlew :targets:fabric-26.1.2:test -Ptargets=fabric-26.1.2`
  and dispatcher deploy succeeded from local Codex worktree; Minecraft playtest
  still pending

## 1.8.0 — Codex — 2026-06-21

MathQuest now has four selectable NPC personas in the local web control panel, with
centralized dialogue lines that are easy to review and edit.

- Added Professor Pi, Countess Calc, and Geo Sage as selectable education-themed NPCs
- Added custom texture assets for each new NPC persona
- Moved Wandering Nerd jokes and all new NPC dialogue into `MathQuestNpcCatalog`
- Synced the selected NPC id to clients so spawned NPC names, dialogue, and rendered
  textures match the control-panel selection
- Added each NPC's dialogue under its gallery preview as single-line copyable text
- **Tested:** `./gradlew :targets:fabric-26.1.2:test -Ptargets=fabric-26.1.2`
  succeeded from local Codex worktree; Minecraft playtest still pending

## 1.7.0 — Codex — 2026-06-21

MathQuest dedicated servers now serve a localhost-only web control panel for running
family quiz sessions from Randy's laptop.

- Added embedded local control panel server at `http://127.0.0.1:8765/`
- Added four-column family dashboard for Randy, K2, TL, and Kid1
- Added per-player reward item/count controls, NPC spawn/open/vanish actions, spawn
  distance controls, and current/last NPC status
- Added targeted Wandering Nerd assignment and optional player lock; locked NPCs show
  the assigned Minecraft name in parentheses and ignore other players
- Added server-owned quiz-open payloads carrying explicit SQLite problem lists and
  reward plans to clients
- Added data-driven NPC gallery with a front-facing Wandering Nerd texture preview
- Added `docs/CONTROL_PANEL.md` with run instructions, feature spec, decisions, and
  first playtest checklist
- **Tested:** `./gradlew :targets:fabric-26.1.2:test -Ptargets=fabric-26.1.2`
  and dispatcher build-only run succeeded from local Codex worktree; Minecraft
  dedicated-server playtest still pending

## 1.6.1 — Codex — 2026-06-21

Patch release for the first 1.6.x playtest: MathQuest now writes Minecraft-origin
single-session SQLite exports directly to the math-quiz single-session staging folder.

- Changed the default `mathQuizExportDir` to
  `~/Documents/Code/fof-mono/apps/math-quiz/_data/_single-session-sqlite-files`
- Migrates an existing 1.6.0 config value that still points at `_data/mathquest` to
  the new default path
- Added Minecraft-to-real-name mappings: `rjcomp -> Randy`, `PumaJockey -> TL`,
  `SkulkScraper -> G1`
- **Tested:** `./gradlew :targets:fabric-26.1.2:test -Ptargets=fabric-26.1.2`
  and dispatcher build-only run succeeded from local Codex worktree; Minecraft playtest
  still pending

## 1.6.0 — Codex — 2026-06-20

MathQuest now looks up learner-specific math-quiz problem lists for mapped Minecraft
players before falling back to generated random quizzes.

- Added math-quiz problem-list loading from the latest `math-flu_<name>_*.sqlite`
  file in `~/Documents/Code/fof-mono/apps/math-quiz/_data/tlkids`
- Added Minecraft-to-real-name mapping: `TreasureHunterM -> K2`, `WildPetal -> Kid1`
- Added ordered mixed-operation quiz support, including per-problem operation data in
  multiplayer result payloads
- Added integer division problem support for math-quiz problem lists
- **Tested:** `./gradlew :targets:fabric-26.1.2:test -Ptargets=fabric-26.1.2`
  and dispatcher build-only run succeeded from local Codex worktree; Minecraft playtest
  still pending

## 1.5.0 — Codex — 2026-06-20

MathQuest now exports each completed quiz as a math-quiz-compatible single-session
SQLite file instead of the legacy JSON session file. The export follows
`apps/math-quiz/docs/2026-06-20_minecraft-mod-single-session-sqlite-spec.md` and writes
to the configured math-quiz intake folder, defaulting to
`~/Documents/Code/fof-mono/apps/math-quiz/_data/mathquest` in 1.5.0.

- Added canonical `Users`, `Sessions`, `ProblemAttempts`, and `ModeEvents` SQLite export
- Added `mathQuizExportDir` config with fallback to the MathQuest data directory
- Stored multiplication problem text and operation as canonical `*` for math-quiz analysis
- **Tested:** `./gradlew :targets:fabric-26.1.2:test -Ptargets=fabric-26.1.2`
  and dispatcher build-only run succeeded from local Codex worktree; Minecraft playtest
  still pending

## 1.4.5 — Codex — 2026-06-17

Local Codex app build-validation release. No gameplay, networking, or config behavior
changed; the version bump exists so Randy can distinguish the first jar built from the
local Codex worktree from the existing 1.4.4 jar in the local mods folder.

- Bumped `mod_version` to 1.4.5 for a distinct local build artifact
- **Tested:** dispatcher build succeeded from local Codex worktree on 2026-06-17;
  Randy completed a quick Minecraft smoke test successfully the same day

## 1.4.4 — 2026-06-05

Repo-migration release. MathQuest source imported from kid-games repo into fof-mono
at `apps/minecraft/mods/mathquest/`. No gameplay, networking, or config behavior changed;
the produced jar is functionally identical to 1.4.3. Version bump exists so the first
build from fof-mono has a distinct filename, confirming the import paths resolve correctly.

- Imported from kid-games `export/to-fof-mono` branch into fof-mono `import/from-kid-games`
- CLAUDE.md migrated to AGENTS.md (path references updated to `apps/minecraft/mods/`)
- Build dispatcher path is now `apps/minecraft/mods/build-and-deploy.py`
- **Tested:** pending — Randy to run playtest check from fof-mono

## 1.4.3 — 2026-05-24

Build-infrastructure release. No MathQuest gameplay, networking, or config behavior
changed; the bytecode in the produced jar is functionally identical to 1.4.2. The
version bump exists so the produced jar has a distinct filename
(`mathquest-fabric-1.4.3-mc26.1.2.jar`) and can be told apart from prior 1.4.2 builds
that were made before the multi-mod reorganization.

- Repo reorganized: `mathquest/` moved to `minecraft/mods/mathquest/`. Source paths
  inside the mod are unchanged; only the directory containing the mod moved.
- New sibling mod `minecraft/mods/remove-singleplayer/` introduced — see its own
  CHANGELOG.
- New unified build dispatcher `minecraft/mods/build-and-deploy.py` replaces the per-mod
  shell scripts as the canonical entrypoint. The legacy
  `minecraft/mods/mathquest/build-and-deploy.sh` and `minecraft/mods/mathquest/deploy.sh`
  are deleted in this release; recover them from git history via
  `git log --diff-filter=D -- minecraft/mods/mathquest/build-and-deploy.sh` (and likewise
  for `deploy.sh`) if a side-by-side diff against the dispatcher is ever wanted.
- Build dispatcher refinements (caught while validating Forge 1.20.1):
  - Fixed argparse to correctly recognize `--target`/`-t` when other arguments are
    present. The previous version used `argparse.REMAINDER` which swallowed every
    flag after the mod name into gradle-args; now extra gradle args must follow a
    literal `--` separator (`build-and-deploy.py <mod> --target X -- --info`).
  - JDK discovery probes a list of standard install locations per Java version
    (Temurin, Homebrew Intel, Homebrew Apple Silicon) instead of one hard-coded
    Homebrew Intel path. Machines with Temurin (e.g. JDK 17 commonly installed via
    Eclipse Temurin rather than Homebrew) work out of the box; on a miss the
    dispatcher exits with the full probe list and the per-mod override syntax.
  - Per-target Minecraft mods folder discovery: when a folder
    `~/Library/Application Support/minecraft-<target>/mods/` exists, the dispatcher
    deploys that target's jar there instead of the default
    `~/Library/Application Support/minecraft/mods/`. Matches Randy's per-profile
    Minecraft layout (`minecraft-fabric-1.21.11/`, `minecraft-forge-1.20.1/`).
- `.gitignore` lifted to `minecraft/mods/.gitignore` to cover every mod via one cascade.
- Per-mod `.mod-build.toml` manifests now declare default target and extra deploy paths;
  mathquest's lists `~/Documents/Code/mathquest-server/mods` so the dispatcher
  auto-deploys to the dedicated server in addition to the client mods folder.
- Documentation: split `CLAUDE.md` into a repo-root file + a mods-specific file at
  `minecraft/mods/CLAUDE.md` (Java-version-per-Minecraft-version table, dispatcher
  usage, playtest definition). Added a "Running the dedicated server" section to
  `docs/OVERVIEW.md` covering steady-state start/connect/deploy.

**Tested:** Randy ran the playtest check against `fabric-26.1.2`:
- Singleplayer integrated server — spawned Wandering Nerd via the Control Panel, took
  a quiz, rewards delivered. ✅
- Dedicated server (`~/Documents/Code/mathquest-server/`) — spawned Wandering Nerd via
  the server-console `mathquest start <player>` command, took a quiz. ✅
- Caveat: the playtested jar was a 1.4.2 build produced by the new dispatcher (the
  version bump landed after testing). Since 1.4.3 differs only in the version string,
  the 1.4.2 playtest applies.

## 1.4.2

Added a `+/-` toggle button at the lower left of the quiz number pad so negative
answers can be entered (needed for subtraction with `min > max` orderings like
`2 - 5`). Pressing it flips the sign of the current input buffer; flipping again
removes it. Auto-accept and Enter handling already parse signed integers, so no other
change was needed. Also updated `deploy.sh` to auto-pick the **newest jar** in
`targets/<target>/build/libs/` by mtime instead of relying on the version in
`gradle.properties`; pass `--version <X>` to pin a specific build.

## 1.4.1

Added `/mathquest problems <count>` command (1–50) on both the client (singleplayer)
and server (op-gated) command trees so the quiz length can be changed mid-session
without editing `mathquest.json` or restarting. New top-level `deploy.sh` script
copies an already-built jar to both mods folders without rebuilding; pair it with
`./build-and-deploy.sh --no-deploy` to bake a fresh jar while a game is in progress
and swap it in later.

## 1.4.0

Added **subtraction** as a fourth quiz operation alongside addition, multiplication,
and exponentiation (commands, in-game cycles, normalize aliases, and tests). Renamed
the DM cleanup command from `/mathquest killnerds` to **`/mathquest vanishnerds`**.
New **`sharedDataDir`** config field routes singleplayer DB and session-JSON writes
to a configurable directory (default `~/Documents/Code/mathquest-server/config`) so
singleplayer and dedicated-server sessions land in one place for analysis; older
configs auto-migrate.

## 1.3.1

Phase 2 follow-up fixes. Client `/mathquest status` now prints a redirect message on
a multiplayer server (instead of showing stale local config). New
`DespawnNerdsPayload` (C2S) lets the client request server-side removal of nearby
Wandering Nerds when dismissing a quiz on a multiplayer server. New op-only
`/mathquest vanishnerds` server command removes all Wandering Nerd entities from the
overworld for DM cleanup.

## 1.3.0

Server-authoritative quiz content (Phase 2). The server resolves quiz parameters
(operation, range, problem count, per-player presets) and sends them to the client in
`OpenQuizPayload`. Quiz results are reported back to the server via
`QuizResultPayload` for server-side DB recording and session export. Client-side
config commands are blocked in multiplayer. Singleplayer behavior unchanged.

## 1.2.2

On the **dedicated server**, **`/mathquest start <player>`** and
**`/mathquest start all`** now follow **quiz mode** — in **NPC** mode they
**force-spawn** Wandering Nerds (one attempt per targeted player); in **popup** mode
they still send **`OpenQuizPayload`**. (Before 1.2.2, those targeted starts always
opened the popup path even in NPC mode.) The **client-only** `/mathquest start`
message when not in single-player was clarified to point at **op**
**`/mathquest start`** or **`mathquest start <player>`** on the server console.

## Earlier versions

History before 1.2.2 lived in commit messages and the OVERVIEW prior to this file's
introduction. If you need to dig further back, the repo's git log on
`minecraft/mods/mathquest/` is the source of truth.
