# Fabric target — Minecraft 26.1.2

This is the new generation: unobfuscated Minecraft, Mojang official mappings, the new
`net.fabricmc.fabric-loom` plugin id (Loom 1.15+), Java 25, Gradle 9.4+.

## State

Buildable. The shared `fabric/src/` source tree is Mojang-named, and this target compiles
the shared source plus a small local override set for APIs that changed source names in
26.1.

## Source layout

Most code comes from `fabric/src/main/java`. `build.gradle` syncs that shared tree into
`build/generated/shared-main`, excluding classes with 26.1-only API differences. The local
`src/main/java` tree then supplies overrides for:

- `MathQuestMod` networking payload registration names.
- `MathQuestCommands` client command builder name.
- `WanderingNerdEntity` and `WanderingNerdSpawner` interaction/message names.
- Screen rendering classes that use `GuiGraphicsExtractor` and `extractRenderState`.

This is not a full parallel port; it is a compatibility layer around source-incompatible
Minecraft/Fabric API renames.

## Quick reference (versions)

See `gradle.properties` in this directory:

- minecraft_version
- loader_version
- fabric_version
- loom_version

The full migration guide is in `mathquest/docs/2026-04-26_migration-1.21-to-26.1.md`.
