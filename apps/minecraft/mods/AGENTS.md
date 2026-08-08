# Minecraft-mods conventions

This is the `apps/minecraft/mods/` AGENTS.md. It is loaded via the thin CLAUDE.md in this
directory. Read it before making any change to a mod under this directory.

The repo-root AGENTS.md holds the repo-wide rules (branching, naming, git safety, etc.);
this file holds the rules that only matter while you're working on Minecraft mods.

## What this directory is

This is a **Minecraft-mod creation codebase**, not just MathQuest. MathQuest is the
first reference implementation. As we add capabilities (server-side mode, dashboards,
AWS deploy), **preserve existing pathways and keep things reusable for the next mod.**

Concretely that means:

- The **client-side-only mod pattern** (what MathQuest is today, and what
  `remove-singleplayer` is by design) must remain a first-class, reusable mode. A
  future "tiny client-only mod" should be able to lean on this codebase without
  inheriting the server-side machinery.
- **Server-side mode is being added as an additional mode**, not as a replacement.
- When you propose changes that would remove or hide a capability, **flag it as such
  and ask before doing it.**

## Layout

Each subdirectory of `apps/minecraft/mods/` is an independent multi-target Gradle build:

- `apps/minecraft/mods/mathquest/` — the headline mod (quiz/reward gameplay loop, multi-
  target Fabric build).
- `apps/minecraft/mods/remove-singleplayer/` — tiny client-side mod that hides the
  Singleplayer button on the title screen; ships for Fabric 1.21.11 and Forge 1.20.1.

Future mods follow the same pattern: one subdirectory per mod, each with its own
`gradlew`, `settings.gradle`, `build.gradle`, `targets/<target>/` subprojects, and
`fabric/` (and optionally `forge/`) shared source tree.

A single `.gitignore` at `apps/minecraft/mods/.gitignore` covers gradle caches, build
output, IDE files, run/, logs/, and remappedSrc/ for every mod. Don't add per-mod
`.gitignore`s unless a mod has a genuinely unique pattern to ignore.

## Active version targets (MathQuest)

MathQuest has standardized going forward on:

- **Primary:** `fabric-26.1.2` (Mojang-named, no-remap Loom).
- **Preserved capability:** `fabric-1.21.11` (the last Yarn/obfuscated era). **Keep
  the multi-target apparatus and this target intact** — it is the codebase's reference
  for building against pre-26.1 Minecraft (obfuscated-class pathway). Do not rip it
  out for tidiness.
- The `forge-1.20.1` target is a placeholder; not enabled.

When the user says "build MathQuest" without qualification, build `fabric-26.1.2`.
When they say "build both" or "build all," the dispatcher's `--target` flag covers
both Fabric targets.

## Java versions per Minecraft version

Different Minecraft / loader versions require different JDKs to compile and run. The
build dispatcher (`apps/minecraft/mods/build-and-deploy.py`) knows the standard mapping and
picks `JAVA_HOME` per target automatically, but it's worth knowing the table:

- **Minecraft 1.20.x (Fabric or Forge)** — Java 17. ForgeGradle 6 specifically *requires*
  Java 17 and will not run under a newer JDK, which is why a forge-1.20.1 target must
  be invoked with `JAVA_HOME` pointed at JDK 17 even if other targets in the same mod
  use a newer Java.
- **Minecraft 1.21.x (Fabric)** — Java 21. Mojang bumped the runtime requirement at
  1.20.5. This is the version `fabric-1.21.11` is built with.
- **Minecraft 26.1.x (Fabric)** — Java 25. Current Mojang requirement; this is the
  version `fabric-26.1.2` is built with.

On Randy's Intel Mac the dispatcher expects Homebrew JDKs at the standard locations:
`/usr/local/opt/openjdk@17/...`, `/usr/local/opt/openjdk@21/...`, and
`/usr/local/opt/openjdk/...` (which is Java 25 — Homebrew's `openjdk` without a `@`
suffix tracks the latest). If a machine has JDKs elsewhere, override per-target in the
mod's `.mod-build.toml` under a `[java_home]` table.

When **mixing Java versions in one invocation** (e.g. `--target fabric-26.1.2,forge-1.20.1`),
the dispatcher runs gradle separately per target so each invocation gets its own
`JAVA_HOME`. Do not try to run a mixed Java-version build in a single gradle invocation
— ForgeGradle 6 won't tolerate a Java 21+ runtime.

## Gradle wrapper version per mod

A mod's Gradle wrapper version (recorded in `<mod>/gradle/wrapper/gradle-wrapper.properties`)
has to be compatible with **every** loader toolchain the mod uses. The two relevant
constraints today:

- **Loom 1.15+** (used by mathquest's `fabric-26.1.2` target) requires Gradle 9.x.
- **ForgeGradle 6.x** (used by any `forge-1.20.x` target) requires Gradle 8.x and
  explicitly rejects Gradle 9.x with an error at apply-plugin time.
- **Loom 1.14** is happy with both Gradle 8 and Gradle 9.

In practice this means:

- A mod that ships any **Loom 1.15+ Fabric target** needs a **Gradle 9** wrapper for
  that target's gradle root.
- A mod that ships any **ForgeGradle 6 Forge target** needs a **Gradle 8** wrapper
  for that target's gradle root.
- A mod that wants both at once — like remove-singleplayer (Fabric 26.1.2 +
  Forge 1.20.1) — uses the **nested loader gradle roots** layout described below.

When a mod ships only targets compatible with one wrapper version, use the flat
layout (gradlew at the mod root). Mathquest today is flat — all Fabric, Gradle 9.
When a mod must straddle wrapper versions, use the nested layout.

## Nested loader gradle roots

For a mod that must satisfy two incompatible wrapper-version constraints (today: a
Loom 1.15+ Fabric target alongside a ForgeGradle 6 Forge target), the layout is:

```
apps/minecraft/mods/<mod>/
├── README.md, CHANGELOG.md, .mod-build.toml         # mod-level
├── fabric/                                           # gradle root for all Fabric targets
│   ├── gradlew + gradle/wrapper/    (Gradle 9.x)
│   ├── settings.gradle, build.gradle, gradle.properties
│   ├── shared/  (Fabric-shared Java source — was the flat-layout `fabric/` subproject)
│   ├── common/
│   └── targets/{fabric-X.Y.Z}/
└── forge/                                            # gradle root for all Forge targets
    ├── gradlew + gradle/wrapper/    (Gradle 8.x)
    ├── settings.gradle, build.gradle, gradle.properties
    └── targets/{forge-X.Y.Z}/
```

Each loader subdirectory is its own self-contained gradle root with its own wrapper.
The mod-level `README.md`, `CHANGELOG.md`, and `.mod-build.toml` stay at the mod
folder level.

The dispatcher routes each target to the right gradle root automatically based on
the target name's loader prefix. From the dispatcher's perspective, the mod still
has one identity (`<mod>`) — the loader-root split is internal. You don't pass any
extra flag.

**Cross-loader-root metadata sync.** Both `fabric/gradle.properties` and
`forge/gradle.properties` declare `mod_version` and `archives_base_name`. They
**must stay in sync** — bumping the mod's version means bumping both files in the
same commit. The dispatcher reads from whichever gradle root applies to the target
it's currently deploying, so divergence between the two would silently produce
inconsistent jars. The mod's CHANGELOG.md is the canonical source of truth for what
"the current version" means.

**When to use the nested layout vs split into separate mod folders.** Prefer
nested loader gradle roots when the loaders ship the same logical mod identity
(same display name, same install audience, same evolving feature set). Split into
separate mod folders when the loaders are evolving independently or have a
materially different feature surface.

**Mathquest uses nested loader gradle roots** (`mathquest/fabric/` for Fabric, `mathquest/forge/` for Forge 1.20.1). Keep `mod_version` in both `fabric/gradle.properties` and `forge/gradle.properties` in lockstep.

## Adding a new Minecraft-version target to an existing mod

The dispatcher is target-name-agnostic: it handles any target name following the
`<loader>-<mc-version>` convention out of the box (JDK selection, dedicated mods-folder
discovery, jar path computation). The Java source under a mod's `fabric/src/main/java/`
is also target-agnostic for a given Mojang-mappings era (the same code compiles
against every `fabric-1.21.x` target without changes — Mojang API drift inside a 1.21.x
line is rare).

What does *not* generalize automatically is the per-target gradle subproject. Each
Minecraft version pins specific Fabric Loader, Fabric API, and Loom Gradle plugin
versions, and the right combination is a per-Minecraft-version lookup — there's no
formula. Those facts have to live in the target's gradle subproject. Likewise the
`fabric.mod.json` `depends.minecraft` range pins the supported Minecraft version
explicitly.

So adding e.g. `fabric-1.21.5` to a mod that today only ships `fabric-1.21.11` is a
three-file scaffold plus a registration line. Recipe below — read the *Version pin
sourcing* and *Fabric era differences* and *Adding a Forge target* subsections too,
because the gradle-subproject contents differ across those axes.

### Version pin sourcing (do not guess from memory)

**Always cross-reference an authoritative source. Do not guess Fabric Loader / Fabric
API version numbers from memory** — they don't follow a predictable pattern and the
wrong number produces a "Could not resolve net.fabricmc.fabric-api:fabric-api:X+Y" build
failure that wastes a turn. The two sources to use, in order of preference:

- **The Fabric example mod, per-Minecraft-version branch:**
  `https://raw.githubusercontent.com/FabricMC/fabric-example-mod/<mc-version>/gradle.properties`
  (e.g. `.../fabric-example-mod/1.21.1/gradle.properties`). This is the canonical
  "what versions go with this Minecraft" reference; it's what `fabricmc.net/develop/`
  generates from. The properties file lists `minecraft_version`, `loader_version`,
  `fabric_api_version` (which becomes our `fabric_version`), and `loom_version`.
- **The Fabric API releases on GitHub:**
  `https://github.com/FabricMC/fabric/releases`. Useful to find the *latest* released
  `<api-version>+<mc-version>` tag if the example mod branch has fallen behind, or to
  pick a specific older release if you need to pin to an older API for compatibility.

If both sources are unreachable (sandbox/network constraints), say so explicitly and
ask Randy to look up the pins on his machine rather than guessing. A guessed version
that doesn't exist costs an extra dispatcher run; a guessed version that does exist
but is wrong for the Minecraft version can produce subtle runtime mismatches that are
harder to diagnose.

### Fabric era differences (pre-26 vs 26+)

Mojang changed how Minecraft ships its bytecode at the 26.x line:

- **Pre-26 (Minecraft 1.x — including 1.20.x, 1.21.x):** ships with **obfuscated**
  class/method/field names. Loom remaps the bytecode at build time using
  `loom.officialMojangMappings()` (or Yarn mappings on older builds). Source code in
  the mod is written against the Mojang-mapped names (`Button`, `TitleScreen`,
  `ScreenEvents`, etc.); Loom handles the obfuscated-to-Mojang substitution behind
  the scenes. Every `fabric-1.21.x` and `fabric-1.20.x` target in this codebase is
  in this category.
- **26.x and later:** ships **unobfuscated** — the bytecode shipped by Mojang already
  uses the same Mojang names the source code is written against. Loom is configured
  in "no-remap" mode for these targets. The build.gradle differs noticeably from a
  pre-26 target. Only mathquest's `fabric-26.1.2` target is in this category today.

**Implication for new target scaffolding:** when adding a `fabric-1.21.x` or
`fabric-1.20.x` target, **copy the build.gradle from `fabric-1.21.11`** as the
template — that's the canonical pre-26 layout with `loom.officialMojangMappings()`.
Do **not** copy from `fabric-26.1.2`; its no-remap setup will not work for an
obfuscated Minecraft version. When adding a 26.x+ target, copy from `fabric-26.1.2`.

### Adding a Fabric target — recipe

1. **Pre-flight check the Gradle wrapper.** Open
   `apps/minecraft/mods/<mod>/gradle/wrapper/gradle-wrapper.properties` and note the
   `distributionUrl` Gradle version. The new target's Loom version must support that
   Gradle version (Loom 1.14 supports both Gradle 8 and 9; older Loom versions are
   typically Gradle 8 only). If the mod ships any ForgeGradle 6 Forge target, the
   wrapper is pinned to Gradle 8.x — see *Gradle wrapper version per mod* above.
2. **Look up versions** for the target Minecraft version using the *Version pin
   sourcing* sources above. Note `minecraft_version`, `loader_version`,
   `fabric_api_version` (-> `fabric_version` in our properties), and `loom_version`.
3. **Create the target directory** at `apps/minecraft/mods/<mod>/targets/<loader>-<mc>/`
   with three files. For a pre-26 Fabric target use `targets/fabric-1.21.11/` as the
   template; for 26.x+ use `targets/fabric-26.1.2/` (mathquest):
   - `gradle.properties` — set the four version values from step 2.
   - `build.gradle` — copy verbatim from the era-appropriate template. The build logic
     is fully parameterized by gradle.properties; no edits needed.
   - `src/main/resources/fabric.mod.json` — copy from the template; update only the
     `depends.minecraft` range (e.g. `"minecraft": "~1.21.5"`) and the
     `depends.fabricloader` lower bound if the Loader version warrants it.
4. **Register the target** in `apps/minecraft/mods/<mod>/settings.gradle` by adding the new
   target name to `ALL_TARGETS` (always) and `DEFAULT_TARGETS` (if you want it in the
   default build set).
5. **Build it** via `./apps/minecraft/mods/build-and-deploy.py <mod> --target <loader>-<mc>`.
   The dispatcher will find Java 21 (or whatever the target's MC line needs), look for
   a `~/Library/Application Support/minecraft-<loader>-<mc>/mods/` instance folder for
   deploy (falling back to the default `apps/minecraft/mods/` if no dedicated folder
   exists), and proceed.

### Adding a Forge target

Same overall shape, but Forge differs from Fabric in several places that matter for
the scaffold:

- **Build tool:** Forge uses **ForgeGradle 6** (`net.minecraftforge.gradle`) instead
  of Loom. ForgeGradle 6 **requires Gradle 8.x and rejects Gradle 9.x** with an
  apply-plugin error. Confirm the mod's wrapper is pinned at Gradle 8 before adding;
  otherwise pin it down or split the Forge target into a separate mod folder (see
  *Gradle wrapper version per mod*).
- **Java runtime:** Forge 1.20.x requires **Java 17** — not 21. The dispatcher already
  knows this via `required_java()` and will pick the right JDK from `JAVA_HOME_PROBES`;
  no manifest override is needed if the machine has a JDK 17 at a standard location
  (Temurin or Homebrew).
- **Manifest file:** **`META-INF/mods.toml`** (not `fabric.mod.json`). Different
  schema; copy from `targets/forge-1.20.1/src/main/resources/META-INF/mods.toml` as
  the template and update `versionRange` lines for Forge and Minecraft.
- **Entrypoint:** Forge uses an `@Mod`-annotated class wired onto the Forge event
  bus, not a `ClientModInitializer`. The Java source lives **in the target's own
  `src/main/java/` tree**, not in the shared `fabric/` module, because the
  entrypoint shape is different. See
  `targets/forge-1.20.1/src/main/java/com/kidgames/removesingleplayer/forge/RemoveSingleplayerForge.java`.
- **`pack.mcmeta`:** Forge resources need a `pack.mcmeta` under
  `targets/<target>/src/main/resources/`. Copy from `targets/forge-1.20.1/`.

First-time build of a Forge target on a fresh machine downloads ForgeGradle 6
artifacts and decompiles Minecraft — ~5–10 minutes the first time, then cached.
**Bump the gradle-wrapper `networkTimeout` to 120000** (2 minutes per socket read);
the default 10s is too aggressive for multi-MB downloads on slower connections.
Both existing wrappers in this repo are already at 120000.

### Verifying a new target

A clean target build ends with a `[build-and-deploy] deployed <jar> -> <path>` line.
Confirm the path is what you expect — the per-target dedicated profile folder (e.g.
`minecraft-fabric-1.21.5/mods/`) if you have one for that version, otherwise the
default `apps/minecraft/mods/`.

For a true end-to-end check, launch the matching Minecraft profile and verify the
mod's observable behavior (the title-screen check for `remove-singleplayer`; the
quiz flow for `mathquest`). Update the mod's `CHANGELOG.md` **Tested:** sub-bullet
with the result.

### Bookkeeping after a successful new-target build

Bump the mod's `mod_version` per the rules in *Versioning and changelogs* below
(adding a new target is a minor bump if it's the first build for that Minecraft
version — it's a new deployable jar). Add an entry to the mod's `CHANGELOG.md` and
update its README to list the new target alongside existing ones.

## Building and deploying

`apps/minecraft/mods/build-and-deploy.py` is the unified entrypoint. From the repo root:

```
./apps/minecraft/mods/build-and-deploy.py <mod>                          # default target for the mod
./apps/minecraft/mods/build-and-deploy.py <mod> --target fabric-1.21.11  # one target
./apps/minecraft/mods/build-and-deploy.py <mod> --target fabric-1.21.11,fabric-26.1.2
./apps/minecraft/mods/build-and-deploy.py <mod> --no-deploy              # build only
./apps/minecraft/mods/build-and-deploy.py <mod> -- --info --offline      # forward args to gradle
./apps/minecraft/mods/build-and-deploy.py --list-mods                    # list available mods
```

Anything after a literal `--` separator on the command line is forwarded verbatim to
`./gradlew` inside the mod's directory. This is the only supported way to pass
gradle-side flags; do not put them before `--` (argparse will treat them as unknown
dispatcher flags). Without the `--`, every option is parsed by the dispatcher.

What it does, in order: picks the right gradle root for each target (the mod folder
itself for flat-layout mods, or the matching `<mod>/<loader>/` subdirectory for mods
using the nested loader-roots layout described above), picks the right `JAVA_HOME`
for the target (see *JDK discovery* below), runs `./gradlew buildAll -Ptargets=...`
inside that gradle root, locates the produced jar under
`<gradle-root>/targets/<target>/build/libs/`, then deploys it to the per-target
Minecraft mods folder (see *Per-target Minecraft mods folder* below) and any
per-mod extra deploy paths declared in the manifest. Different targets in the same
invocation can resolve to different gradle roots — e.g. `--target
fabric-26.1.2,forge-1.20.1` on remove-singleplayer runs gradle once in `fabric/`
(Gradle 9) and once in `forge/` (Gradle 8).

### JDK discovery

For each target, the dispatcher determines the required Java major version (see the
*Java versions per Minecraft version* section above) and probes a list of standard
install locations in order, taking the first one that exists on disk:

- Java 17: Temurin (`/Library/Java/JavaVirtualMachines/temurin-17.jdk/Contents/Home`),
  Homebrew Intel (`/usr/local/opt/openjdk@17/...`), Homebrew Apple Silicon
  (`/opt/homebrew/opt/openjdk@17/...`).
- Java 21: Homebrew Intel, Homebrew Apple Silicon, Temurin.
- Java 25: Homebrew Intel, Homebrew Apple Silicon, Temurin.

If a machine has a JDK at one of those paths it works out of the box. If no probed
path resolves, the dispatcher exits with an explicit list of every path it tried and
the override syntax for the mod's `.mod-build.toml`. To add a path the dispatcher
should know about generally (across mods), edit the `JAVA_HOME_PROBES` table at the
top of `build-and-deploy.py`. To override for one mod/target only, use the
`[java_home]` table in that mod's `.mod-build.toml`.

### Per-target Minecraft mods folder

Randy keeps a separate Minecraft profile per loader / Minecraft-version pair, with
each profile's data living next to the default Minecraft folder under
`~/Library/Application Support/`:

- `~/Library/Application Support/minecraft/` — default profile (used today for
  fabric-26.1.2).
- `~/Library/Application Support/minecraft-fabric-1.21.11/` — dedicated profile for
  the fabric-1.21.11 target.
- `~/Library/Application Support/minecraft-forge-1.20.1/` — dedicated profile for
  the forge-1.20.1 target.

The dispatcher follows the same convention: for each target it's deploying, it looks
for a folder named `~/Library/Application Support/minecraft-<target>/mods/`. If that
folder exists, the target's jar is deployed there; otherwise the dispatcher falls
back to the default `~/Library/Application Support/minecraft/mods/`. Because the
detection is by folder existence, adding a new dedicated profile just means creating
the folder — no dispatcher config change required.

This means: don't tell Randy to manually copy a jar from the default mods folder
into a dedicated one. The dispatcher already lands it in the right place per target.

### Per-mod `.mod-build.toml`

Each mod can ship an optional `apps/minecraft/mods/<mod>/.mod-build.toml`. Recognized keys:

- `default_target` — the target name used when `--target` is omitted on the CLI. With
  no manifest and no `--target`, gradle picks the mod's `DEFAULT_TARGETS` and the
  dispatcher skips the deploy step (no deterministic jar path to copy).
- `extra_deploy_paths` — a list of additional directories (beyond the per-target
  primary deploy folder described above) that the freshly-built jar should be copied
  into. MathQuest uses this to keep a local dedicated-server mods folder in sync.
  `~` is expanded.
- `[java_home]` — a table mapping `target = "/absolute/path/to/JDK_HOME"` for machines
  whose JDKs aren't where the dispatcher's `JAVA_HOME_PROBES` look. Most machines
  shouldn't need this — the probe list covers the standard Homebrew and Temurin
  layouts on Intel and Apple Silicon macOS.

Mods without any of these quirks can omit the manifest entirely.

### Legacy mathquest scripts (deleted)

The per-mod `apps/minecraft/mods/mathquest/build-and-deploy.sh` and
`apps/minecraft/mods/mathquest/deploy.sh` were removed in mathquest 1.4.3 once the Python
dispatcher had been playtested. They are still recoverable from git history if a
diff against the dispatcher is ever needed:

```bash
# These paths are from the kid-games repo (pre-import history)
git log --diff-filter=D -- minecraft/mods/mathquest/build-and-deploy.sh
git log --diff-filter=D -- minecraft/mods/mathquest/deploy.sh
git show <commit>:minecraft/mods/mathquest/build-and-deploy.sh
```

Do not restore them. Behavior changes go into the dispatcher.

## Authoritative MathQuest docs

- **`apps/minecraft/mods/mathquest/docs/OVERVIEW.md`** — the canonical reference for the
  MathQuest codebase. Read it before making changes to MathQuest. Keep it accurate
  when you do.
- **`apps/minecraft/mods/mathquest/docs/EXPLAINER.md`** — newcomer-friendly explainer of
  Fabric / Gradle / Loom / Maven. Useful background.
- **`apps/minecraft/mods/mathquest/docs/CLIENT_ONLY_MOD_PATTERN.md`** — canonical statement
  of the client-side-only mod pattern, plus a recipe for what a client-only mod needs
  from this codebase. `remove-singleplayer` is the second-ever mod built to this
  pattern.
- **`apps/minecraft/mods/mathquest/docs/2026-*-*.md`** — dated docs (migration plans,
  transcripts, decision records). New planning docs follow the same
  `YYYY-MM-DD_topic.md` format.

## Hosting & infrastructure (MathQuest)

- **Target deployment for the MathQuest server:** an always-on **AWS** server running
  the Fabric dedicated server JVM. Randy prefers **ECS** as the runtime, since he is
  already standardized on AWS (AWS CLI configured, Lambda, CloudWatch, security
  tooling). He wants to **build the core capability himself** on AWS rather than
  relying on managed Minecraft hosts (Aternos, BisectHosting, etc.).
- **AWS infrastructure is currently a flagged TODO / placeholder.** Any plan that
  involves provisioning AWS resources should mark that step as gated on Randy wiring
  in his AWS account and existing infra references, and **should not attempt to
  provision AWS resources autonomously.**
- **Acceptable third-party dependencies:** RCON libraries, dashboard webapp
  frameworks, SQLite, Java/Node/Python libs. **Not acceptable** as a substitute for
  the core capability: managed Minecraft hosts, hosted dashboard SaaS.

## Versioning and changelogs

Every mod under `apps/minecraft/mods/` carries a `mod_version` in its root
`gradle.properties` and a `CHANGELOG.md` in its root. The two are kept in lockstep:
the version recorded in `gradle.properties` is what the next built jar will declare;
the top entry in `CHANGELOG.md` describes what changed at that version and (once
playtested) records the test result.

**When to bump.** Bump `mod_version` whenever the work in a session produces a
distinct deployable jar — that includes source changes, but also build-pipeline
changes, packaging changes, dependency bumps, or anything else that means the jar a
fresh build emits is *not* the same artifact as the previous version's jar. The rule
of thumb: if Randy would benefit from telling two builds apart by filename, bump.

**Semver:**

- **Major** for breaking changes (save-file format, network-protocol incompatibility,
  removal of a player-facing command).
- **Minor** for new features or significant behavior changes (new payloads, new
  commands, server-authority shifts, new screens).
- **Patch** for bug fixes, small tweaks, and build-only / packaging-only releases.

**Changelog format.** Each entry in `CHANGELOG.md` has a heading of the form
`## <version> — <YYYY-MM-DD>` (PDT), a short summary paragraph or bulleted list of
what changed, and — once Randy has playtested — a **Tested:** sub-bullet capturing
the playtest result (target, what was exercised, ✅ / ❌). Entries go newest first.
A build-only / packaging-only release that produces a functionally identical jar to
the prior version should call that out explicitly in the summary.

**Do not ship a branch with code changes and no version bump.** It is fine to make
several small commits inside a session without bumping each one, but the session's
PR must bump the version exactly once and the bump and the matching CHANGELOG entry
must be in the same commit.

For MathQuest specifically, [`docs/OVERVIEW.md`](mathquest/docs/OVERVIEW.md) records
the *current* version on the `Mod version:` bullet and links out to CHANGELOG.md for
history. Don't duplicate per-version notes between the two — CHANGELOG.md is
canonical.

## The playtest check

Shorthand for "did this actually work end-to-end in Minecraft?" Randy runs this from
his laptop:

1. From the repo root:
   `./apps/minecraft/mods/build-and-deploy.py mathquest`
   (add `--target <name>` only if the PR's test plan calls for a non-default target).
2. Confirm the script finishes successfully and prints a `deployed <jar>` line for the
   expected target.
3. Confirm the freshly-built jar is now in `~/Library/Application Support/minecraft/mods/`,
   replacing any previous MathQuest jar.
4. Launch Minecraft with the matching Fabric profile, load a world (existing or new),
   and confirm MathQuest behaves as expected for whatever the change touched (timer
   ticks, popup or NPC quiz appears, answers are accepted, rewards drop, etc.).

**Always tell Randy what version he's testing.** Whenever you ask for a playtest
check (or any rebuild/retest), state the version number that the next build will
produce — read it from the mod's `gradle.properties` `mod_version`. The pattern is:
*"Run the playtest check; the resulting jar will be `<mod>-<loader>-<version>-mc<mc>.jar`
(e.g. `mathquest-fabric-1.4.3-mc26.1.2.jar`)."* This lets Randy confirm the build he
actually deployed matches the version recorded in CHANGELOG.md, so the **Tested:**
sub-bullet there is unambiguous.

When asking Randy to do this, just say **"run the playtest check"** — the definition
lives here, so instructions don't need to repeat the steps each time. If a specific
change requires extra in-game verification beyond the baseline (e.g. "confirm the new
`/mathquest start` command spawns a nerd on Wildpetal"), call that out as an addendum
after the playtest-check instruction.

For `remove-singleplayer` (or any future client-only mod), the equivalent
playtest is: launch Minecraft with the matching profile, observe the title screen, and
confirm the Singleplayer button is hidden while Multiplayer, Realms, and Options
remain visible.

## Things not to do (mods-specific)

- Don't rip out `fabric-1.21.11` or the multi-target build files in MathQuest; they
  are preserved capability.
- Don't fold the client-side-only mod pattern into the server-mode codepaths in a way
  that breaks "tiny client-only mod" as a future use case.
- Don't provision cloud (AWS, etc.) resources without explicit Randy permission.
- Don't duplicate gradle build logic between mods. If two mods need the same piece of
  build glue, lift it up — to `apps/minecraft/mods/build-and-deploy.py` for orchestration,
  or to a shared gradle script for compile-time logic.
- Don't reintroduce per-mod shell entrypoints. The legacy
  `mathquest/build-and-deploy.sh` and `mathquest/deploy.sh` were removed in 1.4.3;
  behavior changes go into the Python dispatcher.
