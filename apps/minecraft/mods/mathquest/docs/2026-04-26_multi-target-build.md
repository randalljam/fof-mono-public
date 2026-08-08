# Multi-target build system

MathQuest builds for more than one Minecraft version, and (eventually) for more than one
mod loader. This document explains the project layout, how target selection works, and
which everyday commands you'll actually use.

## Layout

```
mathquest/
├── settings.gradle             # multi-project + target selection
├── build.gradle                # root: aggregate tasks (buildAll / cleanAll / listTargets)
├── gradle.properties           # mod identity (version, group, base name)
│
├── common/                     # loader-agnostic code (no MC, no Fabric, no Forge imports)
│   └── src/main/java/...
│
├── fabric/                     # shared Mojang-named Fabric source consumed by fabric targets
│   └── src/                    # main + test trees
│
├── targets/
│   ├── fabric-1.21.11/         # last obfuscated MC; official mappings; legacy `fabric-loom`
│   │   ├── build.gradle
│   │   ├── gradle.properties   # MC + loader + Fabric API + Loom versions
│   │   └── src/main/resources/fabric.mod.json
│   │
│   ├── fabric-26.1.2/          # first unobfuscated MC; no-remap `net.fabricmc.fabric-loom`
│   │   ├── build.gradle
│   │   ├── gradle.properties
│   │   ├── src/main/java/      # minimal 26.1 API-name overrides
│   │   ├── src/main/resources/fabric.mod.json
│   │   └── README.md
│   │
│   └── forge-1.20.1/           # placeholder, NOT included in settings.gradle yet
│       └── README.md
│
├── stubs/                      # offline-build stubs (used by legacy build.gradle.dual-mode)
├── build.gradle.dual-mode      # legacy alternate build (kept as reference, unused)
├── settings.gradle.dual-mode   # legacy alternate settings (kept as reference, unused)
└── tools/                      # asset generation helpers (texture renderer)
```

## Target selection

`settings.gradle` declares an `ALL_TARGETS` list (every known target) and a
`DEFAULT_TARGETS` list (the ones included by default — currently both Fabric targets).
Only the **included** targets are part of the project graph; targets that aren't included
have their `build.gradle` ignored entirely, so Gradle won't try to resolve their plugins.

This matters because targets resolve their Gradle plugins as soon as they are included.
The wrapper is now Gradle 9.4.1, so both Fabric targets can be included by default.

```bash
./gradlew listTargets                                    # show what's selected this run
./gradlew buildAll                                       # build the default set
./gradlew buildAll -Ptargets=fabric-1.21.11              # explicit single target
./gradlew buildAll -Ptargets=fabric-1.21.11,fabric-26.1.2  # explicit multi-target
```

Standard subproject paths work too. Targets named in the requested task list are
auto-included even if they're not in `DEFAULT_TARGETS`, so this works without any flags:

```bash
./gradlew :targets:fabric-1.21.11:build       # build just this target
./gradlew :targets:fabric-1.21.11:test        # tests for this target
./gradlew :targets:fabric-1.21.11:runClient   # Loom dev client (when Loom is in scope)
```

Cleaning:

```bash
./gradlew cleanAll                            # clean every selected target + root
./gradlew :targets:fabric-1.21.11:clean       # clean one
```

## The everyday workflow

Most of the time you're iterating on one target. Suggested loop:

1. Pick the target you're testing against (the one whose Minecraft version is in your
   active Minecraft profile).
2. Build it: `./build-and-deploy.sh --target fabric-1.21.11`
   (or just `./build-and-deploy.sh` — defaults to fabric-1.21.11.)
3. Restart Minecraft and play with it.
4. Once stable, expand to multiple targets to verify the change still compiles for the
   other Minecraft versions:
   ```
   ./build-and-deploy.sh --target fabric-1.21.11,fabric-26.1.2
   ```

The deploy script archives existing MathQuest jars under
`~/Library/Application Support/minecraft/mods/mathquest-inactive-mods/` before copying
the new ones, so previous builds aren't lost.

## Adding a new target

1. Create `targets/<loader>-<mc-version>/`.
2. Drop in `gradle.properties` with the version pins for that target.
3. Drop in `build.gradle` configured for the right loader / mappings.
4. Add the entry to the `ALL_TARGETS` list in `settings.gradle`.
5. Add a `src/main/resources/fabric.mod.json` (or `META-INF/mods.toml` for Forge).
6. Run `./gradlew listTargets` to confirm Gradle sees it.

The fabric-26.1.2 README walks through what changes between Fabric target generations
(plugin id, mappings source, Loom version, Java version). The forge-1.20.1 README sketches
what's needed to add a Forge target.

## Build artifacts

Each target writes its jar to its own `build/libs/`:

```
targets/fabric-1.21.11/build/libs/mathquest-fabric-1.1.11-mc1.21.11.jar
targets/fabric-26.1.2/build/libs/mathquest-fabric-1.1.11-mc26.1.2.jar
```

The naming convention is `<archives_base_name>-<loader>-<mod_version>-mc<mc_version>.jar`,
which is what tools like CurseForge and Modrinth want you to upload.

## Common pitfalls

- **A target you want to build isn't in `DEFAULT_TARGETS`.** Without `-Ptargets=...`,
  only the targets in `DEFAULT_TARGETS` get included in the project graph. To build
  something else, either pass `-Ptargets=foo`, run the task by full path
  (`:targets:foo:build` — auto-included from the task name), or add it to
  `DEFAULT_TARGETS` once it's stable.
- **Mappings vs. plugin id vs. Gradle version chain.** All three have to line up:
  - 1.21.11 → Mojang official mappings + `fabric-loom` plugin id + Loom 1.14 + Gradle 9.4.1.
  - 26.1.x  → unobfuscated/no mappings dependency + `net.fabricmc.fabric-loom` plugin id + Loom 1.15 + Gradle 9.4.1.
- **Java version mismatch.** 1.21.11 needs Java 21; 26.1.x needs Java 25. The root
  `build.gradle` sets Java 21 defaults; `targets/fabric-26.1.2/build.gradle` overrides
  its JavaCompile release/toolchain to 25. `build-and-deploy.sh` selects the matching
  Homebrew JDK for each requested target set.
- **26.1 API overrides.** The shared source is Mojang-named, but a few Minecraft/Fabric
  APIs changed source names between 1.21.11 and 26.1.2. The 26.1 target copies the
  shared source into `build/generated/shared-main` excluding those classes, then compiles
  target-local overrides for commands, entrypoint registration, entity interaction/spawn
  messages, and screen rendering.
- **Source-set assignment vs. append.** When customizing `sourceSets.main.resources` or
  `sourceSets.main.java`, use `srcDirs = [...]` (plural with `=`), not `srcDir x` (singular,
  appends). The Java plugin already sets a default `src/main/...` entry; appending `'src/main/...'`
  again silently doubles it and `processResources` errors with "duplicate fabric.mod.json".
