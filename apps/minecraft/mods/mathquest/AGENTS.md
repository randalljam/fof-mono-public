file: apps/minecraft/mods/mathquest/AGENTS.md
title: MathQuest — Agent Instructions
last-updated: 2026-06-30_0915 — Cursor - Composer 2.5 Fast

Minecraft mod (Fabric + Forge): timed math quizzes, rewards, NPC mode, dedicated-server control panel, fluency-feast integration with math-quiz SQLite.

**Read first:** [`docs/OVERVIEW.md`](docs/OVERVIEW.md) (canonical codebase reference — keep it current when you change behavior). Shared multi-mod rules (targets, JDK, dispatcher, versioning, playtest check) live in [`../AGENTS.md`](../AGENTS.md).


## Build and deploy (default)
After implementing or fixing MathQuest code, **run build-and-deploy as the last step** unless the user says otherwise (e.g. build-only, no deploy, or a docs-only edit).

From the repo root:
```
./apps/minecraft/mods/build-and-deploy.py mathquest
```
- Default target: **`fabric-26.1.2`** (see `.mod-build.toml`).
- Use `--no-deploy` only when the user wants a jar built but not copied to Prism / the local dedicated-server mods folder.
- Use `--target forge-1.20.1` for the Forge build (also builds/deploys **fabric-26.1.2** via `companion_targets_by_target` in `.mod-build.toml` — lockstep jars to Prism + both dedicated-server folders).
- Dedicated-server deploy is **per-target** in `.mod-build.toml` `[extra_deploy_paths_by_target]`: Fabric → `~/Documents/Code/mathquest-server/mods`, Forge → `~/Documents/Code/mathquest-server-forge/mods`.
- Forward gradle flags after `--`, e.g. `./apps/minecraft/mods/build-and-deploy.py mathquest -- --offline`.

A successful run prints `[build-and-deploy] deployed mathquest-fabric-<version>-mc26.1.2.jar -> …` for the Prism instance **Fabric 26.1.2 MathQuest** and, when present, `~/Documents/Code/mathquest-server/mods`. Forge deploy goes to Prism **Forge 1.20.1 MathQuest** and `~/Documents/Code/mathquest-server-forge/mods`. Do not treat `./gradlew build` alone as done for playtesting.

When asking Randy to playtest, state the jar version from `gradle.properties` `mod_version` (see *The playtest check* in [`../AGENTS.md`](../AGENTS.md)).


## Common vs loader-specific (Fabric + Forge)
MathQuest uses **nested loader gradle roots** (`fabric/` Gradle 9, `forge/` Gradle 8). Loader-agnostic code lives once under `fabric/common/` and is compiled into both loaders via extra `srcDir` wiring.

**Shared in `common/`** (write once, test in `:common:test`):
- `config/MathQuestConfig`, `quiz/QuizManager`, `quiz/QuizSessionOptions`
- `persistence/*` (QuizDatabase, SessionExporter, WrittenColumnSessionExporter, MathQuizProblemListLoader, MathQuizFluencyLoader, FluencyFeastBridge)
- `npc/MathQuestNpcCatalog`, `quest/QuestQuizDefinitions`, `control/MathQuestControlState`
- `control/http/*` (HTTP control panel core: `MathQuestHttpControlPanelServer`, `MathQuestHttpRouter`, assets resolver, status builder, `ControlPanelBridge`)
- `util/MathQuestDurationFormat` (status/compact duration labels for commands and in-game control panel)
- `platform/MathQuestPaths`, `platform/MathQuestLog`, `platform/PlatformInventory`, `platform/PlatformServer`, `platform/PlatformNetwork`
- `net/*` neutral payload data records (plain fields — no loader codecs)
- `server/QuizResultProcessor`, `server/OpenQuizPayloadBuilder`

**Loader-specific** (one implementation per loader; **keep in tandem**):
- Entrypoints: `MathQuestMod` / `MathQuestClient` (Fabric) vs `MathQuestForge` / `MathQuestClientForge` (Forge)
- Networking registration + send/receive (Fabric `PayloadTypeRegistry` / `ServerPlayNetworking` vs Forge `SimpleChannel`)
- Screens (`Screen` / `GuiGraphics` / `Button` APIs differ across 1.20.1, 1.21.11, 26.1.2)
- Entity registration, renderer, feature renderer, spawner glue
- Command registration, key binding, control-panel loader hooks (`FabricControlPanelBridge` / `ForgeControlPanelBridge` + optional Fabric-only HTTP route handlers)
- Quest runtime hooks (`CaveEscapeQuestService`) — **Fabric only; FROZEN past M6**
- **On hold for Forge** (Fabric-only or fix-in-Fabric-first): written-column quiz screen (troubleshoot Fabric 26.1.2 first), terrain-map PNG route, mob-spawn admin routes (`spawn-mobs` / `spawn-mob-plan` / `kill-mob-area`)

**Rule:** `common/` must **not** import `net.minecraft.*`, `net.fabricmc.*`, or Forge namespaces (see `fabric/common/build.gradle` comment). Pass player context as `PlayerContext` (username + UUID) and use platform interfaces for loader glue.

**M5.0 tooling (governing):** Grow `common/`, freeze the build tooling. No Balm, Stonecutter, or Architectury in M5. Post-M6 standardization (MultiLoader-Template + raw Stonecutter + NeoForge for 1.20.2+) is a **separate branch**, not this milestone.

**M6 complete:** Core (non-quest) Forge 1.20.1 feature parity declared. On-hold items (written-column acceptance, terrain-map, mob-spawn admin) and frozen quest unchanged — see OVERVIEW parity matrix.


## Tandem development rule
A feature or fix is **done** only when implemented and verified on **both** Fabric (primary: `fabric-26.1.2`) **and** Forge (`forge-1.20.1`):
1. Prefer new logic in `common/`; loader trees hold thin API glue only.
2. Touching shared logic → run `:common:test` **and** Forge `--no-deploy` build.
3. Touching screens/networking/commands → update **both** loader implementations.
4. Bump `mod_version` in **both** `fabric/gradle.properties` and `forge/gradle.properties` when the session produces deployable jars.


## Tests
Before build-and-deploy on a branch with logic changes, run tests from `apps/minecraft/mods/mathquest/fabric/`:
```
./gradlew :common:test
./gradlew :targets:fabric-26.1.2:test
```
Forge build (from repo root):
```
./apps/minecraft/mods/build-and-deploy.py mathquest --target forge-1.20.1 --no-deploy
```
Fabric regression (both Fabric targets):
```
./apps/minecraft/mods/build-and-deploy.py mathquest --target fabric-26.1.2,fabric-1.21.11 --no-deploy
```
Target-overridden sources exist in both `fabric/shared/src/...` and `fabric/targets/fabric-26.1.2/src/...` — edit both when the change applies to the primary Fabric build.


## Commits and push (default)
Unless the user says not to commit, not to push, or to use one combined commit:
1. **Split work into stepwise commits** — one logical chunk per commit (config model, UI, commands, tests, version bump + changelog, docs, etc.). Do not fold unrelated concerns into a single commit.
2. **Commit each chunk** when it leaves the tree in a sensible state (tests passing where applicable).
3. **Push to the current branch** after committing (`git push`, or `git push -u origin <branch>` on first push).

Follow repo-root `AGENTS.md` for branch discipline and git safety (no force-push, confirm branch before push, etc.). Bump `mod_version` in **both** `fabric/gradle.properties` and `forge/gradle.properties` and add a matching `CHANGELOG.md` entry when the session produces distinct deployable jars.


## Key paths
- Shared loader-agnostic Java: `fabric/common/src/main/java/com/kidgames/mathquest/`
- Platform + server abstractions: `fabric/common/src/main/java/com/kidgames/mathquest/platform/`, `.../server/`, `.../net/`
- Fabric-specific Java: `fabric/shared/src/main/java/com/kidgames/mathquest/`
- Fabric platform impls: `fabric/shared/src/main/java/com/kidgames/mathquest/platform/`
- Forge 1.20.1 source: `forge/targets/forge-1.20.1/src/main/java/com/kidgames/mathquest/forge/`
- Primary Fabric target overrides: `fabric/targets/fabric-26.1.2/src/main/java/...`
- Control panel static assets: `fabric/shared/src/main/resources/assets/mathquest/control_panel/` (also copied into `forge/targets/forge-1.20.1/src/main/resources/assets/mathquest/control_panel/` until a future common-resources dedupe)
- Config on disk (server): `config/mathquest.json` under the world/server directory
- Build manifest: `.mod-build.toml`
