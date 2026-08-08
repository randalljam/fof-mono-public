# Forge target — Minecraft 1.20.1 (Milestone 1)

Build root: `mathquest/forge/` (Gradle 8.10.2, Java 17, ForgeGradle 6).

## Status

**Milestone 1 shipped** in mod version 1.16.0:

- Popup-mode timed quiz in **singleplayer** (integrated server)
- Offer / number-pad / result screens (`forge/.../screen/*Forge.java`)
- Direct inventory rewards (no network packets)
- `mathquest.json` load/save via shared `MathQuestConfig` + `MathQuestPaths`
- SQLite session export + legacy DB recording via shared `SessionExporter` / `QuizDatabase`

## Deferred (later milestones)

NPC mode, control panel HTTP server, multiplayer networking, server op commands, written-column quiz, quest invitation flow.

## Build

From repo root:

```bash
./apps/minecraft/mods/build-and-deploy.py mathquest --target forge-1.20.1
```

Requires Prism Launcher instance(s) **"Forge 1.20.1 MathQuest"** and/or **"Forge 1.20.1 MathQuest Cataclysm"** (from `prism_instance_suffix_by_target` in `.mod-build.toml`). Deploy copies the jar to every instance that exists.

Output jar: `forge/targets/forge-1.20.1/build/libs/mathquest-forge-<version>-mc1.20.1.jar`

## Source layout

- `src/main/java/com/kidgames/mathquest/forge/` — Forge entrypoint + client tick handler
- `src/main/java/com/kidgames/mathquest/forge/screen/` — 1.20.1 UI screens
- Shared logic compiled from `../fabric/common/src/main/java`
