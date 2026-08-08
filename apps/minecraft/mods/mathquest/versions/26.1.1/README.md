# MathQuest — Minecraft 26.1.1 build files

**Saved:** 2026-04-08

These files are ready to swap into the project when Fabric tooling supports
Minecraft 26.1.1. As of this date, **neither Yarn mappings nor Mojang official
mappings** are published for MC 26.1.1, so Fabric Loom cannot set up the dev
environment. Check periodically:

- Yarn: https://maven.fabricmc.net/net/fabricmc/yarn/maven-metadata.xml
- Mojang: `client_mappings` in https://piston-meta.mojang.com/mc/game/version_manifest_v2.json → 26.1.1.json

## What's different from the 1.21.11 build

| Change | Detail |
|--------|--------|
| **Gradle wrapper** | 9.2.0 (Java 25 requires Gradle 9.1+) |
| **Fabric Loom** | 1.15.+ (supports Gradle 9.2) |
| **JDK** | 25 (`brew install openjdk@25`) |
| **Mappings** | `loom.officialMojangMappings()` via `mappings_kind=official_mojang` in `gradle.properties` (Yarn not available) |
| **Fabric Loader** | 0.18.6 |
| **Fabric API** | 0.145.4+26.1.1 |
| **fabric.mod.json** | `"minecraft": "~26.1.1"`, `"java": ">=25"` |

## How to activate

Copy these files over the project originals (paths listed below), then run
`./build-and-deploy.sh`. If Yarn is available by then, update
`gradle.properties`: set `mappings_kind=yarn` and `yarn_mappings=26.1.1+build.N`.

| This folder | Destination (relative to `mathquest/`) |
|-------------|---------------------------------------|
| `gradle.properties` | `gradle.properties` |
| `build.gradle` | `build.gradle` |
| `fabric.mod.json` | `src/main/resources/fabric.mod.json` |
| `build-and-deploy.sh` | `build-and-deploy.sh` |
| `gradle-wrapper.properties` | `gradle/wrapper/gradle-wrapper.properties` |
| `stubs-VERSIONS` | `stubs/VERSIONS` |
| `build.gradle.dual-mode` | `build.gradle.dual-mode` |
