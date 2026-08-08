## Direct answers
Balm is not “just a multiloader template.” Balm is primarily a multiloader abstraction library/API. Its docs say it lets you write code once and build for NeoForge, Fabric, and Forge, using abstractions for common functionality such as registries and events. Its GitHub README describes it as a library mod that provides common interfaces/events, removes much loader-specific code, has no custom Gradle tooling, supports Jared’s MultiLoader Template, and covers things “from networking to configs.”    

But there is also a Balm Mod Template. That template is a starter project for using Balm in a multiloader setup, and its README explicitly says the Gradle setup is heavily based on Jared’s MultiLoader Template. It also says most code should live in common, while loader-specific folders should stay small.  

So the clean distinction is:

Balm = abstraction library + optional Balm-based template.
Jared’s MultiLoader Template = build/layout template only.
Stonecutter = multi-version management tool.
Stonecraft = Stonecutter + Architectury convenience wrapper, so not aligned with your “no Architectury” decision.


## Comparison
Tool	What it is	What it helps with	What it does not solve
Balm	Runtime/library abstraction layer for multiloader mods	Shared registries, events, networking/config-style infrastructure, loader-neutral APIs, Forge/Fabric/NeoForge support	Does not magically port your custom screens, NPC behavior, HTTP server, persistence, or gameplay logic
Balm Mod Template	Starter repo for Balm projects	Gives you a Jared-style multiloader repo already wired for Balm	Still requires migration if applied to an existing project
Jared’s MultiLoader Template	Neutral Gradle/project layout template	common + loader projects, no third-party runtime dependency	Does not provide API abstractions; you still write PlatformNetwork, PlatformServer, etc., or add Balm
Stonecutter	Multi-version Gradle/source management	Supporting many Minecraft versions from one codebase	Not primarily a loader abstraction; not needed just to finish Forge parity
Stonecraft	Gradle plugin that wires Stonecutter + Architectury	Reduces boilerplate for multi-loader + multi-version projects	It uses Architectury, so I would exclude it for this project given your preference

Jared’s template is the cleanest “standard shape”: its README says the template compiles mods for multiple loaders using a common project, does not require third-party libraries, and keeps loader-specific APIs out of common.     Balm’s template is basically that same idea plus Balm dependencies/examples.  

Stonecutter is different. The current Gradle Plugin Portal describes it as a modern Gradle plugin for multi-version management. The older Stonecutter README explains the basic model: split a project into versioned variants and use comment-based/versioned code to maintain multiple versions.     That is useful later, when your pain is “support 1.20.1, 1.21.x, 26.x, etc.” It is not the main answer to “how do I avoid writing Fabric and Forge networking twice?”

Stonecraft is also different: it explicitly says it removes boilerplate for multi-loader, multi-version work by using Stonecutter and Architectury. Since you do not want Architectury, I would not use Stonecraft for MathQuest.  


## What this means for MathQuest
Your current project is already structurally close to Jared’s template philosophy: common/ for shared logic, loader trees for loader-specific APIs, and small platform interfaces. The M4 handoff says M5 should refactor the localhost HTTP control panel so the HTTP/asset-serving core is shared and only entity-spawn/packet hooks are per-loader; it also says written-column and quest-invitation are loader-specific screen/wiring tasks backed by common payloads/flow logic.  

That strongly supports the same decision as before:

Do M5 in the current architecture, but make it Balm-compatible. Do not migrate to Balm, Stonecutter, or Stonecraft during M5.

The reason is simple: adopting Balm into an existing project is not just “add a dependency.” Balm’s docs say migrating from a single-loader setup generally means replacing much of the Gradle setup, adding the template’s build-logic, and moving source into common/src/main/java, with loader folders mostly holding entrypoints.   You already did a custom version of that migration across M1–M4. Replatforming during M5 would mix framework migration risk with feature-parity risk.

Also, Balm will not remove the hard M5 work. The local HTTP control panel is your own domain/product feature. The written-column screen is a Minecraft UI port. The quest invitation screen is loader-specific UI/network glue. Balm may help later with generic events/networking/configs, but it will not make those features disappear.


## My recommendation
For M5:

Stay on the current hand-built multiloader architecture.
Do not add Balm yet.
Do not use Stonecutter yet.
Do not use Stonecraft because it brings Architectury.
But design every new M5 seam so that a later Balm or internal-template migration is easy.

For future new mods:

Start from Balm Mod Template or an internal template derived from Balm + Jared’s MultiLoader Template.
Use Jared-style structure as the layout rule.
Use Balm as the standard abstraction layer unless a mod has a strong reason to avoid a runtime library dependency.
Add Stonecutter only once multi-version support becomes a real maintenance burden.
Avoid Stonecraft as long as “no Architectury” remains a project constraint.

Balm has published compatibility across Fabric, Forge, and NeoForge on Modrinth, including a Forge 1.20.1 version, so it is plausible for your target world; still, an actual migration branch should verify the exact Balm versions against your Forge 1.20.1, Fabric 1.21.11, and Fabric 26.1.2 targets before committing.    

⸻


## Guidance to transmit to the M5 planning agent
Use this as the instruction block:

We are not using Architectury for MathQuest. Therefore, do not propose Architectury or Stonecraft for M5. Stonecraft is excluded because it is built around Stonecutter + Architectury.

For M5, continue the current MathQuest multiloader architecture:

* fabric/common/ remains the shared logic home.
* Forge 1.20.1 remains a loader-specific target.
* Fabric targets must stay green.
* Loader-specific code stays limited to Minecraft/loader API glue: screens, packets, event registration, keybinds, entity/spawn hooks, renderer hooks, and server-thread scheduling.

Add an explicit M5.0 standard-tooling decision note at the top of the M5 plan. The decision is:

* No Balm migration in M5.
* No Stonecutter migration in M5.
* No Stonecraft/Architectury.
* Build M5 in a way that can later migrate to Balm or an internal Jared-style template without rewriting feature logic.

M5 scope is:

1. Refactor the localhost HTTP control panel so the HTTP server, routing, JSON/status building, and asset-serving core are in common/.
2. Keep only the Minecraft/loader hooks per-loader: schedule work on the server thread, list/resolve players, open screens/send packets, force-spawn/vanish nerds, and read/write loader config paths.
3. Port the Forge 1.20.1 written-column screen without copying newer Fabric APIs blindly.
4. Wire written-column export/result handling through existing common server/result code where possible.
5. Port the quest-invitation flow with common decision/state logic and loader-specific screen/network wrappers.

Do not create a large MathQuestControlPanelServerForge copy. The acceptable shape is:

common/control/http/
  MathQuestHttpControlPanelServer
  MathQuestHttpRouter
  MathQuestHttpAssets
  MathQuestHttpActions
  MathQuestControlPanelBridge
forge/.../
  ForgeControlPanelBridge
fabric/.../
  FabricControlPanelBridge

The bridge should expose domain-level operations, not generic framework sprawl:

runOnServerThread(...)
listPlayers()
getStatus()
openQuizForPlayer(...)
forceSpawnNerd(...)
vanishNerds(...)
sendQuestInvitation(...)
sendChat(...)
configDir()

Do not add a new generic Platform* abstraction unless it is clearly necessary for M5 and has an obvious future owner. If the abstraction is generic loader infrastructure — networking, events, commands, registries, config — mark it as a future Balm-candidate. If it is MathQuest product logic — quiz state, HTTP routes, control-panel state, session export, quest decisions — keep it in common/ and do not wait for Balm.

Acceptance criteria:

* No duplicated 1000-line HTTP control panel server.
* HTTP core compiles from common code.
* Forge-specific HTTP bridge is thin.
* Written-column Forge fallback is removed.
* Quest invitation works on Forge through common payload/flow logic.
* :common:test passes.
* Fabric 26.1.2 tests pass.
* Fabric 1.21.11 build passes.
* Forge 1.20.1 build/deploy/playtest passes.
* Version bumps remain lockstep in both Gradle roots.
* Changelog and overview are updated.

After M5/M6, create a separate standardization branch:

feature/mathquest-standard-tooling-spike

In that branch, evaluate only two serious options:

1. Keep the current architecture but clean it into an internal Jared-style template.
2. Introduce Balm incrementally and replace only the custom platform code that Balm actually covers.

Stonecutter should be evaluated only after full parity, when the main problem becomes supporting multiple Minecraft versions. Stonecraft remains out of scope unless the project reverses the “no Architectury” decision.


## Rationale to give the agent
The agent should understand this as the governing rule:

M5 is a feature-parity milestone, not a build-system migration milestone.

Balm is promising, but it is a post-parity standardization candidate, not something to splice into M5 while the HTTP control panel, written-column screen, and quest invitation flow are still unfinished. Jared’s template validates the architectural direction we are already using. Stonecutter is for multi-version maintenance later. Stonecraft is excluded because it depends on the tool we have decided not to use.

The correct M5 behavior is therefore: continue, but stop digging the bespoke-framework hole deeper. Use the current platform layer, keep new shared logic in common/, keep loader code thin, and leave clean seams for a later Balm/internal-template refactor.
