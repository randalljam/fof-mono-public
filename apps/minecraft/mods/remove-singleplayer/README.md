# remove-singleplayer

A tiny client-side Minecraft mod that hides the **Singleplayer** button on the main-menu
title screen. Intended for installs where you only want the player launching into
multiplayer worlds.

## Targets

This mod ships against four loader/Minecraft-version combinations:

- **Fabric 26.1.2** — Mojang's first unobfuscated release line; Java 25; Loom 1.15
  (new `net.fabricmc.fabric-loom` plugin id).
- **Fabric 1.21.11** — Java 21; Loom 1.14 (legacy `fabric-loom` plugin id);
  `loom.officialMojangMappings()` for the obfuscated-to-Mojang remap.
- **Fabric 1.21.1** — Java 21; Loom 1.14; same pre-26 pattern as 1.21.11.
- **Forge 1.20.1** — Java 17; ForgeGradle 6; uses Forge's `ScreenEvent.Init.Post`
  instead of Fabric's `ScreenEvents.AFTER_INIT` (entrypoint differs accordingly).

The three Fabric targets share a single Java source file (`shared/src/main/java/com/kidgames/removesingleplayer/RemoveSingleplayerClient.java`). The Forge target has
its own entrypoint at `forge/targets/forge-1.20.1/src/main/java/.../RemoveSingleplayerForge.java`.

## Layout (nested loader gradle roots)

Because ForgeGradle 6 requires Gradle 8.x while Loom 1.15+ for Fabric 26.x requires
Gradle 9.x, this mod is split into two gradle roots living side-by-side inside the
mod folder:

```
remove-singleplayer/
├── README.md, CHANGELOG.md, .mod-build.toml          # mod-level
├── fabric/                                            # Gradle 9.x wrapper
│   ├── gradlew + gradle/wrapper (Gradle 9.4.1)
│   ├── settings.gradle, build.gradle, gradle.properties
│   ├── shared/  (Fabric-shared Java source)
│   ├── common/  (loader-agnostic, currently empty)
│   └── targets/
│       ├── fabric-1.21.1/
│       ├── fabric-1.21.11/
│       └── fabric-26.1.2/
└── forge/                                             # Gradle 8.10.2 wrapper
    ├── gradlew + gradle/wrapper (Gradle 8.10.2)
    ├── settings.gradle, build.gradle, gradle.properties
    └── targets/
        └── forge-1.20.1/
```

The build dispatcher (`minecraft/mods/build-and-deploy.py`) hides this split from
the user — pass any target and the dispatcher routes to the matching gradle root.
See `minecraft/mods/CLAUDE.md` § *Gradle wrapper version per mod* for the rule, and
§ *Nested loader gradle roots* for the dispatcher behavior.

## How it hides the button

Both Fabric and Forge implementations do the same thing: after the title screen
finishes init, walk its widget list, find the button whose `Component` is a
`TranslatableContents` keyed on `menu.singleplayer`, and set `visible = false`
(and `active = false` to keep keyboard navigation from landing on the now-invisible
button).

The mod does not modify world data, does not add commands, and does not register
any server-side handlers. It is safe to install on a vanilla-server connection.

## Build

From the repo root, via the dispatcher (recommended — handles JDK selection, jar
location, and per-target deploy automatically):

```bash
./minecraft/mods/build-and-deploy.py remove-singleplayer --target fabric-26.1.2
./minecraft/mods/build-and-deploy.py remove-singleplayer --target fabric-1.21.11
./minecraft/mods/build-and-deploy.py remove-singleplayer --target fabric-1.21.1
./minecraft/mods/build-and-deploy.py remove-singleplayer --target forge-1.20.1
```

Or directly via the right gradle root if you need to:

```bash
# Fabric targets
cd minecraft/mods/remove-singleplayer/fabric
./gradlew :targets:fabric-26.1.2:build -Ptargets=fabric-26.1.2

# Forge target
cd minecraft/mods/remove-singleplayer/forge
./gradlew :targets:forge-1.20.1:build -Ptargets=forge-1.20.1
```

Built jars land in `<gradle-root>/targets/<target>/build/libs/`. The dispatcher
deploys each jar to its dedicated profile folder under
`~/Library/Application Support/minecraft-<target>/mods/` when one exists, else to
the default Minecraft mods folder.
