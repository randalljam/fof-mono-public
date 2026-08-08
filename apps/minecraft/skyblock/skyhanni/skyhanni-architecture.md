# SkyHanni Architecture & Complexity Breakdown

> **Source repo:** https://github.com/hannibal002/SkyHanni (branch: `beta`)
> **Version analyzed:** 7.13.0 for Minecraft 1.21.11 (Fabric)
> **License:** LGPL

## What Is SkyHanni?

SkyHanni is a **client-side Fabric mod** for Hypixel SkyBlock. It adds overlays, HUD elements, automation helpers, and quality-of-life features on top of the SkyBlock game mode. It does NOT modify the server — it only reads game state and renders extra information on the client.

---

## Scale & Complexity: This Is a Big Mod

| Metric | Value |
|--------|-------|
| Compiled .class files in the jar | ~6,153 |
| Primary language | **Kotlin** (all new code must be Kotlin) |
| Legacy code | Some Java (being ported to Kotlin over time) |
| Jar file size | ~35 MB |
| Bundled dependencies | MoulConfig, libautoupdate, Keval, commons-net, Hypixel Mod API |
| Build system | Gradle with Kotlin DSL + Stonecutter (multi-version support) |
| Mod loader | Fabric (with Fabric Language Kotlin) |
| Java version | 21+ (toolchain targets Java 25 for dev) |
| Code quality tooling | detekt (Kotlin linter) |

**Honest assessment:** This is a **large, mature, professionally-structured open source project** with hundreds of contributors. It would be overwhelming to try to understand all of it. But the patterns are very consistent, so once you understand one feature, you understand the pattern for all of them.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    SkyHanniModLoader                     │
│               (Fabric ModInitializer)                    │
│         Entry point — loads all modules & events         │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                      SkyHanniMod                         │
│     Singleton object — holds config, modules, state      │
│     Manages coroutines, commands, config saving          │
└──────────────────────┬──────────────────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐
    │   API    │ │ Features │ │  Config  │
    │ Layer    │ │  Layer   │ │  Layer   │
    └──────────┘ └──────────┘ └──────────┘
```

### The Three Layers

1. **API Layer** (`api/` package)
   - Listens to raw Fabric/Minecraft events
   - Processes them and fires SkyHanni-specific events
   - Feature code should NEVER listen to Fabric events directly
   - Examples: `CollectionApi`, `SkillApi`, `PetStorageApi`, `HypixelLocationApi`

2. **Features Layer** (`features/` package)
   - The actual user-facing features (overlays, timers, helpers, etc.)
   - Each feature is a **Kotlin `object`** annotated with `@SkyHanniModule`
   - Listens to SkyHanni events via `@HandleEvent` annotation
   - Checks its config toggle before doing work
   - Organized into sub-packages by category (mining, farming, fishing, combat, etc.)

3. **Config Layer** (`config/` package)
   - Config stored as JSON, rendered with MoulConfig library
   - Single config file, single storage file
   - Config migration system (`ConfigUpdaterMigrator`) handles version upgrades

---

## Key Patterns (The Stuff You'd Replicate)

### Pattern 1: The Module System

Every feature is a Kotlin singleton `object` annotated with `@SkyHanniModule`:

```kotlin
@SkyHanniModule
object MyFeature {
    // Automatically registered with the event bus at compile time
}
```

At compile time, annotation processing generates `LoadedModules.kt` which lists every `@SkyHanniModule` class. On startup, `SkyHanniModLoader` iterates this list and registers them all.

### Pattern 2: The Event System

SkyHanni has its own event system layered on top of Fabric's. The flow:

```
Minecraft/Fabric Event
    → API class catches it
        → Fires a SkyHanniEvent
            → Feature classes with @HandleEvent receive it
```

Event handler methods are annotated with `@HandleEvent` which supports:
- `onlyOnSkyblock = true` — only fire when on SkyBlock
- `onlyOnIsland = IslandType.GARDEN` — only on specific islands
- `priority = HandleEvent.HIGH` — ordering control

### Pattern 3: Feature Toggle Pattern

Every feature checks its config toggle at the top of its event handler:

```kotlin
@HandleEvent(onlyOnSkyblock = true)
fun onSomeEvent(event: SomeEvent) {
    if (!SkyHanniMod.feature.myCategory.myFeatureEnabled) return
    // ... actual logic
}
```

### Pattern 4: RepoPattern (Remote Regex)

Instead of hardcoding regex patterns, SkyHanni stores them in a separate "repo" that can be updated without a mod release. Each pattern has a local fallback:

```kotlin
private val myPattern by RepoPattern.pattern("myfeature.pattern", "(?i)Some Regex (?<data>.*)")
```

### Pattern 5: Utilities

Heavy use of extension functions and utility classes:
- `SimpleTimeMark` instead of `System.currentTimeMillis()`
- `ChatUtils` for sending formatted chat messages
- `ErrorManager` for error handling (never raw `e.printStackTrace()`)
- `InventoryUtils` for reading inventory state

---

## Source Directory Structure

```
src/main/java/at/hannibal2/skyhanni/
├── SkyHanniMod.kt          # Main mod object (singleton)
├── SkyHanniModLoader.kt    # Fabric entry point
├── api/                    # API layer — processes raw events
│   ├── event/              # Custom event system (SkyHanniEvent, HandleEvent, etc.)
│   ├── minecraftevents/    # Bridges Fabric events → SkyHanni events
│   ├── hypixelapi/         # Hypixel-specific APIs
│   ├── pet/                # Pet data APIs
│   └── enoughupdates/      # NEU repo integration
├── config/                 # Configuration system
│   ├── commands/           # Chat command registration (brigadier)
│   ├── storage/            # Persistent data storage classes
│   └── features/           # Config option definitions (one class per category)
├── data/                   # Data processing & state management
│   ├── jsonobjects/        # JSON deserialization models
│   ├── repo/               # Remote repo system
│   └── model/              # Data models (waypoints, etc.)
├── events/                 # Event class definitions
├── features/               # THE FEATURES — the bulk of the codebase
│   ├── mining/             # Mining-related features
│   ├── garden/             # Garden/farming features
│   ├── fishing/            # Fishing features
│   ├── combat/             # Combat features
│   ├── dungeon/            # Dungeon features
│   ├── inventory/          # Inventory overlay features
│   ├── gui/                # Custom GUI elements
│   ├── misc/               # Miscellaneous features
│   └── ...                 # Many more categories
├── mixins/                 # Mixin classes (Java, not Kotlin)
│   └── transformers/       # The actual mixin injection code
├── skyhannimodule/         # Module loading annotation & generated code
├── utils/                  # Utility functions and extensions
│   ├── compat/             # Cross-version compatibility
│   ├── render/             # Rendering utilities
│   └── ...
└── test/                   # Test infrastructure
```

---

## What Makes It Complex

1. **Multi-version support** — Uses Stonecutter to compile for different MC versions from one codebase
2. **Custom event bus** — Not just using Fabric's events; has a full custom annotation-driven event system
3. **Remote repo system** — Regex patterns and static data can be updated without a mod release
4. **Mixin injection** — Modifies Minecraft's own code at runtime
5. **Annotation processing (KSP)** — Generates module loading code at compile time
6. **Coroutine-based async** — Uses Kotlin coroutines for background tasks
7. **Config migration** — Handles upgrading config between mod versions

## What Makes It Approachable

1. **Consistent patterns** — Every feature follows the same object + annotation + event handler pattern
2. **Clear separation** — API layer vs feature layer vs config layer
3. **Small features are simple** — See `BrewingStandOverlay.kt` (included as an example) — it's ~30 lines
4. **Good CONTRIBUTING.md** — Thorough onboarding docs for new developers

---

## If You Were Building a Simpler Mod

You wouldn't need most of SkyHanni's infrastructure. A minimal Fabric mod needs:

1. A `fabric.mod.json` declaring your mod
2. A class implementing `ModInitializer` (your entry point)
3. Event listeners registered with Fabric's event system
4. A `build.gradle.kts` with Fabric Loom

You could study SkyHanni's patterns and selectively adopt:
- The `@HandleEvent` annotation pattern (nice and clean)
- The feature-as-singleton-object pattern
- The config toggle guard at the top of handlers
- MoulConfig for a settings GUI

But you'd skip:
- Stonecutter multi-version support
- KSP annotation processing for module loading
- The remote repo system
- The custom event bus (just use Fabric's directly for a simpler mod)

---

## Useful Links

- **Source code:** https://github.com/hannibal002/SkyHanni
- **Contributing guide:** https://github.com/hannibal002/SkyHanni/blob/beta/CONTRIBUTING.md
- **Feature list:** https://github.com/hannibal002/SkyHanni/blob/beta/docs/FEATURES.md
- **SkyHanni data repo:** https://github.com/hannibal002/SkyHanni-REPO
- **MoulConfig (config GUI library):** https://github.com/NotEnoughUpdates/MoulConfig
- **Fabric modding wiki:** https://fabricmc.net/wiki/start
- **Fabric API docs:** https://docs.fabricmc.net/
- **Mixin documentation:** https://github.com/SpongePowered/Mixin/wiki
