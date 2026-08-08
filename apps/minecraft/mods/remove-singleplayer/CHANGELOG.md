# remove-singleplayer changelog

All notable changes to remove-singleplayer are recorded here, newest first. The
version recorded in `gradle.properties` (`mod_version` — kept in sync across the
mod's fabric/ and forge/ gradle roots) is the source of truth for what the next jar
will be built as; this file is the human-readable log of what changed and when.

Format: each entry has a date (PDT), a version (semver), a short summary, and any
test notes captured under a **Tested:** sub-bullet.

## Currently shipping

The latest jar produced for each target, with the last playtest date. The
**Tested** column shows the most recent build/version that Randy has actually
launched and verified in Minecraft.

- **fabric-26.1.2** — latest: **0.3.0**. Last successful playtest: 2026-05-24
  (0.3.0). ✅
- **fabric-1.21.11** — latest: **0.3.0** *(behavior re-verified at 0.3.0 via the
  Screens.getButtons → screen.children swap that is itself behavior-equivalent;
  full gameplay playtest at 0.1.0)*. Last successful playtest: 2026-05-24 (0.1.0). ✅
- **fabric-1.21.1** — latest: **0.3.0** *(same as above; behavior re-verified at
  0.3.0)*. Last successful playtest: 2026-05-24 (0.2.0). ✅
- **forge-1.20.1** — latest: **0.3.0** *(behavior-unchanged from 0.1.0; the
  Screens.getButtons swap is Fabric-only — Forge uses ScreenEvent.Init.Post and
  was not touched)*. Last successful playtest: 2026-05-24 (0.1.0). ✅

The 0.2.0 → 0.3.0 bump was primarily a build-infrastructure restructure (splitting
the mod into separate `fabric/` and `forge/` gradle roots) plus the new
`fabric-26.1.2` target. The Fabric Java source has one behavioral-equivalent tweak
— the loop that walks the title screen's widgets switched from
`Screens.getButtons()` (Fabric API helper, dropped in the 26.x line) to
`screen.children()` (vanilla Minecraft API). Same buttons reached either way. The
0.1.0/0.2.0 playtests inform our confidence in the rebuilt 0.3.0 Fabric jars, but
re-confirming behavior on at least one target is a good idea.

## 0.3.0 — 2026-05-24

Restructure the mod to use **nested loader gradle roots**: the mod now contains a
`fabric/` gradle root (Gradle 9.4.1 wrapper, supports Loom 1.14 + Loom 1.15) and a
sibling `forge/` gradle root (Gradle 8.10.2 wrapper, supports ForgeGradle 6) inside
the same mod folder. This unblocks adding the Fabric 26.1.2 target without dropping
the Forge 1.20.1 target — the previous flat layout couldn't satisfy both
constraints at once (Loom 1.15 needs Gradle 9, ForgeGradle 6 rejects Gradle 9).

Add the **fabric-26.1.2 target** under the new `fabric/` root. The single
`RemoveSingleplayerClient.java` is still shared across all three Fabric targets,
but it required one tweak to compile against the 26.x Fabric API: switch the loop
that walks the title screen's widgets from `Screens.getButtons(screen)` (a Fabric
API helper) to `screen.children()` (vanilla Minecraft API). The helper was dropped
from Fabric API somewhere between the 1.21.x and 26.x release lines; the vanilla
`Screen.children()` list has always contained every `GuiEventListener` the screen
added via `addRenderableWidget`, so the buttons are reachable without the helper.
Behavior is identical on all Fabric targets.

Build dispatcher updated to recognize the nested-loader-root layout: target prefix
(`fabric-`, `forge-`) routes to the matching `<mod>/<loader>/` gradle root. The
flat layout still works for single-loader mods like mathquest (the dispatcher
falls back to `<mod>/gradlew` when no loader-named subfolder exists).

Bumped `mod_version` 0.2.0 → 0.3.0 in **both** `fabric/gradle.properties` and
`forge/gradle.properties`. They must stay in sync; see
`minecraft/mods/CLAUDE.md` § *Cross-loader-root metadata sync*.

Fabric-1.21.1's `loom_version` bumped from 1.7 to 1.14 to match the rest of the
Fabric targets — 1.14 supports both Gradle 8 and Gradle 9, which the new fabric/
root wrapper provides.

**Tested:** Randy ran the playtest for `fabric-26.1.2`:
- Built `remove-singleplayer-fabric-0.3.0-mc26.1.2.jar` (3s, Gradle 9.4.1 +
  Loom 1.15.5 + Java 25; first-run downloads complete from prior 26.1.2 work).
- Dispatcher deployed to `~/Library/Application Support/minecraft/mods/` (the
  default Minecraft profile — no dedicated `minecraft-fabric-26.1.2/` instance
  folder on this machine, so the dispatcher correctly fell through to default).
- Launched the default Fabric 26.1.2 profile through the normal Minecraft
  launcher (alongside the mathquest 1.4.3 jar already in that mods folder),
  observed the title screen, confirmed the Singleplayer button is hidden. ✅

## 0.2.0 — 2026-05-24

Add a `fabric-1.21.1` target alongside the existing `fabric-1.21.11` and
`forge-1.20.1`. No source changes — the shared `fabric/` Java tree compiles against
1.21.1 without modification. Only the per-target gradle subproject is new: a
`gradle.properties` pinning Fabric Loader 0.16.10 / Fabric API 0.102.4+1.21.1 /
Loom 1.7, a `build.gradle` copied from the 1.21.11 target (build logic is fully
parameterized by the properties file), and a `fabric.mod.json` with
`"minecraft": "~1.21.1"`. Registered in `settings.gradle` under both `ALL_TARGETS`
and `DEFAULT_TARGETS`.

Why this target was added: Randy keeps a dedicated Minecraft 1.21.1 Fabric profile
(`~/Library/Application Support/minecraft-fabric-1.21.1/`) for a separate mod
ecosystem and wanted `remove-singleplayer` available there too. The dispatcher's
per-target dedicated-mods-folder discovery routes the 1.21.1 jar to that profile
automatically.

The recipe for adding a Minecraft-version target to an existing mod is documented
in `minecraft/mods/CLAUDE.md` § *Adding a new Minecraft-version target to an
existing mod*.

**Tested:** Randy ran the playtest for `fabric-1.21.1`:
- Built `remove-singleplayer-fabric-0.2.0-mc1.21.1.jar` (2m 46s, Loom 1.7.4, Fabric
  Loader 0.19.2, Fabric API 0.116.12+1.21.1).
- Dispatcher deployed to `~/Library/Application Support/minecraft-fabric-1.21.1/mods/`
  via the per-target dedicated-folder mechanism — same path Randy's Fabric 1.21.1
  profile (set up for the Aether mod) already reads from.
- Launched the 1.21.1 Fabric profile through the normal Minecraft launcher; the
  Aether mod's customized title screen rendered with its custom graphic and the
  Singleplayer button absent — confirming remove-singleplayer hides the button
  correctly on a modded title screen with other mods active. ✅

Initial scaffolding of this target took two retries to land the correct Fabric API
and Loader version pins; my first-attempt guesses were wrong and only
`https://raw.githubusercontent.com/FabricMC/fabric-example-mod/1.21.1/gradle.properties`
gave the authoritative numbers. The cross-Claude-session lesson — *always look up
the example mod's per-MC-version branch; do not guess from memory* — is now codified
in `minecraft/mods/CLAUDE.md` § *Version pin sourcing*.

## 0.1.0 — 2026-05-24

Initial release. Tiny client-side mod that hides the **Singleplayer** button on the
main-menu title screen. Built against two loader / Minecraft-version combinations:

- **Fabric 1.21.11** (primary). Uses Fabric API's `ScreenEvents.AFTER_INIT` to find
  the button whose `Component` is a `TranslatableContents` keyed on
  `menu.singleplayer`, then hides it (`visible = false`, `active = false`) so it
  also can't be reached via keyboard.
- **Forge 1.20.1**. Same effect via Forge's `ScreenEvent.Init.Post`; entrypoint is
  `@Mod`-annotated and only registers on `Dist.CLIENT`.

Multi-target Gradle layout mirrors MathQuest: each target is a Gradle subproject
under `targets/<target>/`, shared Fabric source lives in `fabric/`, Forge source
lives in `targets/forge-1.20.1/src/` (Forge entrypoints differ from Fabric).

Gradle wrapper pinned at **Gradle 8.10.2**. ForgeGradle 6 explicitly rejects
Gradle 9.x, and Loom 1.14 (used by the Fabric target) accepts both, so Gradle 8
satisfies every target this mod ships. See `minecraft/mods/CLAUDE.md`
§ *Gradle wrapper version per mod* for the cross-mod rule.

**Tested:** Randy ran the playtest for both shipped targets:
- `fabric-1.21.11`: launched Minecraft 1.21.11 Fabric profile, observed the title
  screen, confirmed the Singleplayer button is hidden while Multiplayer, Realms,
  and Options remain visible. ✅
- `forge-1.20.1`: built (4m 6s, ForgeGradle 6 + Forge 47.4.0, fresh Gradle 8.10.2
  download + Forge userdev download), dispatcher deployed the jar to
  `~/Library/Application Support/minecraft-forge-1.20.1/mods/` via the per-target
  dedicated-folder mechanism, launched Minecraft 1.20.1 Forge profile, observed
  the title screen, confirmed the Singleplayer button is hidden. ✅
