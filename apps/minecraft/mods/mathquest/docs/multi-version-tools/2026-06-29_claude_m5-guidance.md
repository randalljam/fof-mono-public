**MathQuest Forge port — guidance for the M5-planning agent (and future work)**

## Decision: Path 2 — finish parity in the current architecture, migrate tooling later on a separate branch

Do **not** redo M1–M4. Do **not** adopt any standard multiloader/multiversion tooling inside M5.
Implement M5 (HTTP control panel + written-column quiz + quest-invitation flow) in the **current independent architecture**, but execute it under one operating rule:

> **Grow `common/`, freeze the build tooling.**

Every change should make the eventual tooling migration *cheaper* without *being* the migration. The tooling migration happens later, on a dedicated branch, after full parity (M6).

### Why Path 2 (rationale to preserve in the plan doc)
- The standard-tools migration is **orthogonal to M5's content.** Stonecutter (versions), a MultiLoader-Template layout, or any abstraction library do not change what lives in `common/`. `common/` is the durable asset that survives any migration intact.
- M5's main lift — moving `MathQuestControlPanelServer` into `common/` — is **valuable and correct under every future tooling scenario.** It is not throwaway. It is, in fact, exactly the state you want `common/` to be in *before* migrating.
- The "M5 forces a tooling decision" premise is false. M5 needs the control panel **refactored into `common/`** (a source-level refactor that transfers cleanly across any build-tooling change). It does **not** need standard tooling to be done well. Do not conflate "lift control panel into common" (required now) with "migrate the build onto frameworks" (independent, deferred).
- Migrating mid-feature is the highest-risk option: it would mean doing the biggest feature lift in the project *while* re-platforming the build, losing the "both Fabric targets stay green" bisectability that has anchored every milestone. Keep changes sequential and bisectable.

## M5 scope (unchanged from the M4 handoff) and how to do each part

Reimplement all loader glue **fresh against real 1.20.1 APIs** — do **not** copy 26.1.2 source (same era lesson as M1/M3/M4). Keep **both Fabric targets green** (tandem rule).

1. **HTTP control panel → `common/` (the big lift).**
   `MathQuestControlPanelServer` (~1000 lines) is built on `com.sun.net.httpserver`, which is **pure JDK — not a Minecraft API at all**, therefore inherently loader-agnostic. Lift the HTTP server + asset-serving core into `common/`, running on the existing `PlatformServer`/`PlatformNetwork` interfaces. Only the touch points that reach into the game (entity spawn, packet send, config mutation that needs a timer reset) stay as thin per-loader hooks. **Maximize how much of this lands in `common/`** — it is the single biggest lever for both parity and future migration cost.

2. **Written-column quiz screen → Forge 1.20.1 (loader-specific).**
   Port `WrittenColumnQuizScreen` and remove the Forge `written_column_arithmetic → standard` fallback in `QuizOfferScreenForge.openQuizFromData`. The server-side path (`QuizResultProcessor.processWrittenColumn`) and `WrittenColumnSessionExporter` already exist in `common/`; this is screen + C2S wiring only.

3. **Quest-invitation flow → Forge 1.20.1 (loader-specific).**
   Port `QuestInvitationScreen`, wire `CaveEscapeQuestService`, and the invitation payloads. `QuestInvitationResponseFlow` and the neutral payload records already exist in `common/`.

## Hard rules for M5 (do these / don't do these)

**Do (cheap, aligned with where we're going):**
- Put as much new logic in `common/` as possible; keep loader trees to glue only.
- Keep the platform interfaces (`PlatformInventory`/`PlatformServer`/`PlatformNetwork`) **narrow and Minecraft-type-light** (opaque handles / primitives where practical). This keeps them portable to any future approach.
- Keep the `AGENTS.md` common-vs-loader contract **current** as M5 adds surfaces. That document is the map that turns the eventual migration into a mechanical "these glue files become per-loader source sets" exercise.
- Maintain version lockstep and bookkeeping exactly as prior milestones: bump `mod_version` in **both** `fabric/gradle.properties` and `forge/gradle.properties`, add a `CHANGELOG.md` entry with a `Tested:` sub-bullet, update `docs/OVERVIEW.md`.

**Do NOT (no half-migration — a half-converted state is worse than either pure state):**
- Do **not** introduce Stonecutter `//? if` comment directives into the source piecemeal.
- Do **not** adopt Architectury API, Balm, or any abstraction library — not even "a little." Partial adoption creates two competing abstraction layers.
- Do **not** reorganize the gradle layout toward MultiLoader-Template. That is the migration; it belongs on the dedicated branch.
- Do **not** extend `build-and-deploy.py` with new bespoke orchestration you will throw away. M5 is feature work.

## Future-work direction (so M5/M6 plan *toward* it without doing it)

The chosen tooling direction for the eventual migration (decided; no Architectury):
- **Layout:** Jared's **MultiLoader-Template** (de-facto standard, zero runtime dependency, NeoForge-first). The existing `common/` + the existing hand-rolled platform interfaces port into it directly.
- **Abstraction:** **keep the existing hand-rolled interfaces.** Do **not** adopt Balm or Architectury API — both are runtime libraries players must install, and the current interfaces already work. Balm is the **fallback only** if the hand-rolled layer later buckles under many-mods/many-versions maintenance.
- **Versions:** **raw Stonecutter** for the 1.20.1 / 1.21.x / 26.x API-drift axis (not Stonecraft, which bundles Architectury). This is the tool that eliminates the per-version source duplication that has been the main per-milestone time sink.
- **Modern loader:** **NeoForge** for any target 1.20.2+ (this is where new mods and templates live now). **Forge 1.20.1 is a legacy target**; its loader-specific glue (SimpleChannel networking, ForgeGradle screens) is the genuinely loader-locked part that will not transfer to NeoForge — which is another reason to push maximum logic into `common/` during M5.

## Sequencing after M5 (for the M6 / migration plan)

1. **Finish M5**, then **M6** = parity hardening + common maximization + docs + full playtest matrix → declare full feature parity. This produces a **green, known-good baseline** to diff against during migration.
2. **Between M5 and M6**, insert a **small, time-boxed migration spike on a throwaway branch** (kept off the main line): run the existing `common/` through a MultiLoader-Template + raw-Stonecutter scaffold for **one** version/loader pair only, to measure real migration cost and validate the tool choice. Settle the "keep-own-interfaces vs. Balm" question with one afternoon of prototyping rather than in the abstract.
3. **The migration itself** happens on a **dedicated branch after parity**, informed by the spike — never inline with feature work.

## One-line summary for the agent
Keep M1–M4. Build M5 in the current architecture. Push every line you can into `common/`, freeze the build tooling, keep both Fabric targets green, and leave the codebase one clean "lift the glue into source sets" step away from a future MultiLoader-Template + Stonecutter + NeoForge migration that happens on its own branch after parity.