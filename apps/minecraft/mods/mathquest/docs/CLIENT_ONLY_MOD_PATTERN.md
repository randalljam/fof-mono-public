# Client-side-only mod pattern (first-class)

**Last updated:** 2026-05-11

This repo is a **Minecraft-mod creation codebase**, not just MathQuest. MathQuest is the first reference implementation. As we add server-side capability, hosting, and a DM dashboard (see the [server-conversion plan](2026-05-11_mathquest-server-conversion-plan.md)), the **client-side-only mod pattern** — what MathQuest is today — must remain a **first-class, reusable mode**. A future "tiny client-only mod" should be able to lean on this codebase without inheriting the server-side machinery.

This document is the canonical statement of that commitment, plus a recipe for what a client-only mod actually needs from this codebase.

## What "client-side-only" means here

A client-side-only Fabric mod runs **inside the player's Minecraft client**. It has:

- A `ClientModInitializer` entrypoint (registered under `entrypoints.client` in `fabric.mod.json`).
- Optionally a `ModInitializer` entrypoint as well, for things like custom payload types that must be **declared** symmetrically on client and integrated server. MathQuest does this today only because it sends payloads between client and integrated server in singleplayer; a true client-only mod that doesn't talk to a server can skip the `ModInitializer` entirely.
- No reliance on a dedicated server. The mod jar can sit on a vanilla-server client connection and either no-op or operate purely against the local client.

The pattern explicitly **does not require**:

- `ServerTickEvents`.
- `CommandRegistrationCallback` (server-side `/foo` commands).
- A second `ModInitializer` JVM running on a dedicated server.
- AWS / ECS / RCON / dashboard plumbing.

If you find yourself reaching for any of those, you have left the client-only pattern and entered the server-capable pattern (Phase 1+ in the server-conversion plan).

## Minimum surface area for a new client-only mod

The smallest "hello, world" client-only mod that lives in this repo looks like this:

- A new package under `fabric/src/main/java/com/kidgames/<modname>/`.
- One `ClientModInitializer` class, e.g. `MyModClient.java`. Inside `onInitializeClient()`:
  - Register a `KeyMapping` via `KeyBindingHelper.registerKeyBinding(...)` if you want a hotkey.
  - Register a `ClientTickEvents.END_CLIENT_TICK` handler if you need an idle-loop hook.
  - Open `Screen`s with `MinecraftClient.getInstance().setScreen(...)` in response to input.
- One or more `Screen` subclasses for the UI.
- A `fabric.mod.json` under `fabric/src/main/resources/` (or its per-target override under `targets/<target>/src/main/resources/`) with:
  - `"environment": "client"` (or `"*"` if you also have a no-op `ModInitializer`).
  - An `entrypoints.client` array pointing at your `ClientModInitializer`.
  - No `entrypoints.main` if you really don't need a common-side init.
- A target-level `build.gradle` under `targets/<target>/` if you want to ship for a Minecraft version other than MathQuest's primary. For most cases, mirroring `targets/fabric-26.1.2/build.gradle` and changing the version pins is enough.

Persistence is optional. If the mod needs to persist anything, write it under `FabricLoader.getInstance().getConfigDir()` (JSON via Gson) or `getGameDir().resolve("<modname>_data.db")` (SQLite via JDBC, mirroring `data/QuizDatabase.java`). Both are client-local; no server is involved.

## What you can reuse from MathQuest

Today's MathQuest source contains pieces that are deliberately decoupled from the quiz domain and can be lifted into a new client-only mod, or extracted into a shared module later. Treat these as the "reusable surface":

- **`config/MathQuestConfig.java`** — Gson-backed JSON config in the Fabric config dir, with hand-rolled migration and a typed `EffectiveQuizParams` resolution path. The pattern (POJO + Gson + a single static `CONFIG` field on the main mod class) generalises to any client-only mod that wants `~/.minecraft/config/<modname>.json` persistence.
- **`data/QuizDatabase.java`** — Singleton wrapping a SQLite JDBC connection, lazy connect, shutdown hook. The DB filename and schema are MathQuest-specific, but the wrapper pattern is reusable for any client-only mod that wants local SQLite.
- **`data/SessionExporter.java`** — JSON-file export to a per-mod subdirectory. Generalises to any "emit a structured artifact per session" need.
- **`screen/` widgets** — `ControlPanelScreen`, `PlayerSettingsScreen`, `QuizOfferScreen`, `QuizScreen`, `QuizResultScreen`. The structural patterns (cycle buttons, ± increment buttons, two-column layouts, confirm-quit flow, number-pad input, feedback-with-sound-and-delay) are vanilla `Screen` + stock widget code that compiles unchanged against both Fabric targets. Lift the widget patterns; rewrite the labels and the wiring.
- **`MathQuestClient.java`** — entrypoint shape, hotkey registration via `KeyBindingHelper`, `ClientTickEvents` registration, payload receiver registration, and the integrated-server-only popup guard (`MinecraftClient.getServer() != null`). Useful as a template even if the new mod has no popup mode.
- **The multi-target build apparatus** under `settings.gradle`, root `build.gradle`, and `targets/<target>/build.gradle` — supports shipping the same source against multiple Minecraft versions. A tiny client-only mod can opt to support just one target by editing `ALL_TARGETS` / `DEFAULT_TARGETS`.

## What you should leave behind

Once we land the Phase 1 server-side work in the server-conversion plan, some MathQuest internals will become server-coupled and should **not** be lifted blindly into a client-only mod:

- The eventual server-side `CommandRegistrationCallback` Brigadier tree (added in P1-3).
- `WanderingNerdSpawner` and the rest of `entity/` — server-tick driven and only meaningful with an integrated or dedicated server.
- `network/GiveRewardPayload` and any other C2S/S2C payload — these require a server-side handler. A client-only mod that wants "give the player an item" without a server needs to use the integrated-server path or model the reward without inventory mutation.
- The `WanderingNerdEntity` entity registration in `MathQuestMod.onInitialize()` — server-side registration that has no place in a pure client mod.

If a future mod *does* want a wandering NPC, it joins the server-capable pattern, not the client-only pattern.

## Why this doc exists

Without it, the gravitational pull of the server-conversion work will quietly fold the client-only pathway into the server-capable pathway: "we already have a `ServerTickEvents` handler, just put it there; we already have an op-gated command, just hang it off that." Each such drift is small. The cumulative effect is that the codebase no longer supports a tiny client-only mod without paying for AWS, RCON, and a dashboard.

This doc is the brake. When you propose a change that would make the client-only pattern harder to use as a starting point — for example, moving a piece of `screen/` or `config/` behind a server-only abstraction — **flag it and ask before doing it.** That gate is repeated in the project-wide `CLAUDE.md`.

## Related docs

- [`OVERVIEW.md`](OVERVIEW.md) — authoritative MathQuest codebase reference.
- [`EXPLAINER.md`](EXPLAINER.md) — Fabric / Gradle / Loom / Maven primer for newcomers.
- [`2026-05-11_mathquest-server-conversion-plan.md`](2026-05-11_mathquest-server-conversion-plan.md) — the server-conversion plan this pattern is being preserved alongside.
