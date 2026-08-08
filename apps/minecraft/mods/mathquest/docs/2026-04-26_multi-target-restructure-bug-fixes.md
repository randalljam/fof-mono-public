# Multi-target restructure: bug fixes log

**Date:** 2026-04-26
**Branch:** `claude/multi-target-build-system`
**Context:** During the restructure of MathQuest from a single-project Fabric build into a
multi-project Gradle layout (commit `45ca2b7`), four separate runtime bugs surfaced one at a
time when the user ran `./build-and-deploy.sh` on their local machine. Each round-trip
revealed exactly one bug because Gradle stops at the first failure. The Claude session
that wrote the restructure could not run Gradle itself in its environment, so every bug
had to be diagnosed from the user's pasted terminal output.

This file is the postmortem. Each entry below records: what the symptom was, what was
actually wrong, what attempts were tried, and which change finally made the build pass.

---

## Bug 1 — Plugins block rejected `${project.foo}` syntax

**Commit that fixed it:** `690dcc5` — *Fix plugins block: use bare property name for Loom version*

**Symptom**

```
* Where: Build file '.../targets/fabric-1.21.11/build.gradle' line: 6
* What went wrong:
  argument list must be exactly 1 literal String or String with property replacement
   @ line 6, column 5.
       id 'fabric-loom' version "${project.loom_version}.+"
```

**Root cause**

Gradle's `plugins {}` block runs very early in the build lifecycle and uses a strict
parser. It allows `${someProperty}` substitution but only with **bare property names**
that resolve from the subproject's `gradle.properties`. The `project.foo` form, which
works almost everywhere else in a build script, is rejected by this parser even though
the resulting string is identical.

**Failed approach (none — this was the first build attempt)**

**Final fix**

Drop the `project.` prefix:

```groovy
// before
id 'fabric-loom' version "${project.loom_version}.+"

// after
id 'fabric-loom' version "${loom_version}.+"
```

**Lesson**

Property substitution in `plugins {}` is the strict variant; outside that block the
permissive variant is fine. Always use bare property names inside `plugins {}`.

---

## Bug 2 — Loom 1.14 incompatible with the project's Gradle 8.14 wrapper

**Commit that fixed it:** `dc811ec` — *Pin Loom to 1.13 for fabric-1.21.11 (Gradle 8.14 wrapper compat)*

**Symptom**

```
* What went wrong:
  Could not resolve net.fabricmc:fabric-loom:1.14.10.
  > No matching variant ... attribute 'org.gradle.plugin.api-version' with value '9.2.0'
    and the consumer needed a component, as well as attribute
    'org.gradle.plugin.api-version' with value '8.14'
```

**Root cause**

The restructure's `gradle.properties` for the 1.21.11 target pinned `loom_version=1.14`
because Fabric's 26.1 announcement blog recommends "Loom 1.14 for 1.21.11". But the
**latest 1.14 patch** at the time was 1.14.10, which was published with metadata
declaring it compatible only with Gradle 9.x. The mathquest project's Gradle wrapper
is on **Gradle 8.14**.

**Failed approach (none — diagnosed correctly first try)**

The original single-project build was using Loom `1.13.+` successfully. That should
have been the first thing checked before bumping. The bump was based on the Fabric
blog's surface advice rather than what the existing wrapper supported.

**Final fix**

Pin to the version that was already proven to work:

```properties
loom_version=1.13
```

Also added a comment in the migration doc explaining that bumping Gradle wrapper to 9.4
(needed for 26.1.2's Loom 1.15) implies bumping 1.21.11's Loom to 1.14 in lockstep.

**Lesson**

When restructuring, preserve known-working version pins. Don't pre-emptively "modernize"
toolchain versions while the rest of the toolchain (here, the wrapper) hasn't moved.

---

## Bug 3 — Unselected targets still had their plugins resolved

**Commit that fixed it:** `f99e817` — *Only include selected targets in project graph*

**Symptom** (after Bug 2 was fixed)

```
* What went wrong:
  A problem occurred configuring project ':targets:fabric-26.1.2'.
  > Could not resolve net.fabricmc:fabric-loom:1.15.5.
    [...same Gradle-version mismatch as Bug 2 but for 26.1.2's Loom 1.15...]
```

The user had asked to build only `fabric-1.21.11`. The build still tried to configure
`fabric-26.1.2`, hit Loom 1.15 (which needs Gradle 9.4+), and failed.

**Root cause**

The restructure's `settings.gradle` was using:

```groovy
ALL_TARGETS.each { name ->
    include "targets:${name}"
}
```

This unconditionally registered every known target as a Gradle subproject. The Java
property `org.gradle.configureondemand=true` had been added on the assumption that it
would skip subprojects that aren't being touched — but **plugin resolution happens
before configuration**, and configure-on-demand only skips the configuration phase.
So `fabric-26.1.2/build.gradle`'s `plugins {}` block was being parsed and resolved
even when the user only asked to build `fabric-1.21.11`.

**Failed approach #1**

Adding `org.gradle.configureondemand=true` to root `gradle.properties`. Did not help
because plugin resolution is earlier in the lifecycle than configuration.

**Failed approach #2**

Splitting `ALL_TARGETS` (master list of valid names) and `DEFAULT_TARGETS` (what
`buildAll` fans out to), but still iterating `ALL_TARGETS.each { include ... }`. This
made `buildAll` more selective but didn't change which subprojects Gradle tried to
configure — the include list was the deciding factor.

**Final fix**

Only include selected targets in the project graph:

```groovy
selected.each { name ->
    include "targets:${name}"
    project(":targets:${name}").projectDir = file("targets/${name}")
}
```

Where `selected` defaults to `DEFAULT_TARGETS` and can be overridden via `-Ptargets=...`.
Added an auto-include shim that scans `startParameter.taskNames` so that running
`./gradlew :targets:fabric-26.1.2:build` directly still works without `-Ptargets`.

Also removed `org.gradle.configureondemand=true` since it was no longer doing useful
work and was emitting an "incubating feature" warning on every build.

**Lesson**

Plugin resolution is "during settings/init" — earlier than most other phases. If a
subproject's `build.gradle` declares a plugin that can't be resolved in the current
environment, including the subproject in `settings.gradle` is enough to break every
build, regardless of whether the user actually asked to build that subproject.

The fix is at the include-line level (don't add it to the graph), not at the
configure-on-demand level.

---

## Bug 4 — Duplicate `fabric.mod.json` from accidental srcDir double-add

**Commit that fixed it:** `1ef7a89` — *Fix duplicate fabric.mod.json: assign srcDirs instead of appending*

**Symptom**

```
> Task :targets:fabric-1.21.11:processResources FAILED

* What went wrong:
Execution failed for task ':targets:fabric-1.21.11:processResources'.
> Entry fabric.mod.json is a duplicate but no duplicate handling strategy has been set.
```

This appeared after Bug 3 was fixed, when Java compilation succeeded for the first time.

**Root cause**

Gradle's Java plugin sets a default for resource source directories:

```
sourceSets.main.resources.srcDirs = ['src/main/resources']
```

The restructure's `targets/fabric-1.21.11/build.gradle` then did:

```groovy
resources {
    srcDir rootProject.file('fabric/src/main/resources')   // shared assets
    srcDir 'src/main/resources'                            // target-local
}
```

`srcDir` (singular) **appends** to the existing list rather than replacing it. So the
final list became:

1. `src/main/resources` (Gradle default)
2. `fabric/src/main/resources` (first add)
3. `src/main/resources` (second add — same path as entry 1)

When `processResources` walked the list to copy files into `build/resources/main/`, it
found `fabric.mod.json` at both entry 1 and entry 3 (literally the same folder), each
trying to write to the same destination. Gradle 8 treats this as a hard error.

**Failed approach (none — diagnosed correctly first try)**

**Final fix**

Use `srcDirs = [...]` (plural with `=`), which replaces the list entirely instead of
appending:

```groovy
resources {
    srcDirs = [
        'src/main/resources',                              // target-local: fabric.mod.json
        rootProject.file('fabric/src/main/resources'),     // shared: assets, lang, textures
    ]
}
```

Same pattern applied to the `java` source set in both targets for consistency.

**Lesson**

In Gradle's Groovy DSL, `foo` (singular) and `fooDirs = [...]` (plural with assignment)
mean different things. Singular methods append; plural assignments replace. When you
want full control over a list that has framework defaults, **always assign the plural**.
Mental shortcut: if you find yourself listing a path that's already a default, you're
probably appending where you meant to replace.

---

## Non-fatal warning seen in the successful build (not fixed)

```
> Task :targets:fabric-1.21.11:processIncludeJars
(3.49.1.0) is not valid semver for dependency org.xerial:sqlite-jdbc:3.49.1.0
```

This is Loom's `processIncludeJars` task (which bundles `org.xerial:sqlite-jdbc` inside
the mod jar via the `include` configuration) complaining that the SQLite JDBC version
"3.49.1.0" has four numeric components instead of the standard three (semver expects
`major.minor.patch`). Fabric Loader uses semver for mod-version compatibility checks,
and bundled jars are listed as nested mods in `fabric.mod.json` — the warning is just a
heads-up that this dependency's version can't participate in semver range checks.

**Why we're not fixing it now:** SQLite JDBC has used the four-number scheme for years
(it appends a SQLite library revision). Picking an older 3-number release would lose
useful fixes. The warning is harmless for runtime — Loom still bundles the jar
correctly. Worth revisiting only if Fabric Loader starts rejecting it (it doesn't today).

---

## Process notes

The four bugs above represent four separate user round-trips: each invocation revealed
exactly one bug, the Claude session shipped a fix, the user pulled, ran again, and hit
the next one. This was inefficient but not avoidable in this environment — the session
had no Java/Loom toolchain available locally and couldn't dry-run the build. A few
takeaways for similar tasks in the future:

1. **Preserve working config first; reorganize structure second.** Bug 2 (Loom 1.14
   bump) wouldn't have happened if the restructure had kept `loom_version=1.13` from
   the original build and only changed it later when needed for 26.1.2.
2. **Read framework defaults before adding to lists.** Bugs 3 and 4 were both about
   appending to lists that already had relevant entries (the Java plugin's default
   `src/main/resources`, and the project graph's default of "everything in
   `settings.gradle`"). Both required swapping append for replace.
3. **Plugin resolution happens at settings time.** A `plugins {}` block in any
   included subproject runs very early. If you add a target that needs a plugin you
   can't resolve in the current environment, every build of every other target breaks
   until you either resolve the plugin or stop including the target.
4. **`gradle.properties`-driven version pins must be reachable from `plugins {}` as
   bare names.** Subproject `gradle.properties` are loaded in time for the strict
   plugins parser, but `project.foo` doesn't satisfy that parser; only `${foo}` does.

---

## Final commit chain

```
45ca2b7  Restructure mathquest into multi-target Gradle build         (initial structure; introduced bugs 1–4)
690dcc5  Fix plugins block: use bare property name for Loom version    (bug 1)
dc811ec  Pin Loom to 1.13 for fabric-1.21.11 (Gradle 8.14 wrapper compat) (bug 2)
f99e817  Only include selected targets in project graph                 (bug 3)
1ef7a89  Fix duplicate fabric.mod.json: assign srcDirs instead of appending (bug 4)
```

After `1ef7a89`, the user reported a successful build:

```
BUILD SUCCESSFUL in 24s
12 actionable tasks: 9 executed, 3 up-to-date

=== Deploying to Minecraft mods folder ===
Deployed mathquest-fabric-1.21.11-1.1.11.jar
```
