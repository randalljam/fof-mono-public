# MathQuest: Local Build Restore & Phase 2 Instructions

**Audience:** Local AI coding agent running on Randy's Mac (Cursor).
**Goal:** Restore the MathQuest Fabric mod build to the last-known-working state, verify it builds and runs locally, then consolidate branches (Phase 2).
**Date written:** 2026-04-04
**Last updated:** 2026-04-04 (Phase 1 and Phase 2 complete)
**Branch:** `minecraft-mod-1` (the remote agent has been committing here)

---

## 1. Background / What Happened

Randy is developing a Minecraft Fabric mod called **MathQuest** (multiplication practice for his 8-year-old daughter). It lives in `mathquest/` inside the `kid-games` repo.

At commit `ffd2696` ("mathquest working") on branch `main`, the mod built cleanly on Randy's Mac with a plain `./gradlew build` and was deployed via `mathquest/build-and-deploy.sh`. That is the **last-known-good state**.

After `ffd2696`, the remote agent (Claude Code on the web, working in a sandboxed VM) did a lot of additional work on branch `minecraft-mod-1` and two side branches:

- `claude/setup-kid-games-repo-lS5k9` — unit tests, auto-accept feature, session JSON export (MathQuiz-compatible)
- `claude/fix-fabric-maven-proxy-0cJzi` — a "dual-mode" build system that adds a stub compilation path for environments where `maven.fabricmc.net` is blocked by a proxy (the remote VM's situation)

Those were consolidated (fast-forward merge) into `minecraft-mod-1`, which now contains all the work.

### The problem

The **dual-mode build refactor** (commit `22f4529` and follow-ups) changed `mathquest/build.gradle` from the simple Fabric Loom plugin DSL:

```groovy
plugins {
    id 'fabric-loom' version '1.13.+'
    id 'maven-publish'
}
```

...to a conditional `apply plugin:` structure gated on `gradle.ext.useFabricLoom`, plus a custom `updateStubs` task and a `stubs/` directory for the proxy-blocked stub compilation path.

This works in the remote VM (where it falls through to stub mode) but **fails on Randy's Mac** when it tries to do a real Fabric Loom build. Two successive local failures:

1. **First failure:** `Plugin with id 'fabric-loom' not found` — because `apply plugin:` doesn't consult `pluginManagement.repositories` in `settings.gradle`; it needs a `buildscript { dependencies { classpath ... } }` block. The remote agent added that fix (commit `6ed42bd`).
2. **Second failure (after the buildscript fix):** `Execution failed for task ':updateStubs'` at `build.gradle` line 110, after ~3m39s. The custom `updateStubs` task is choking on the real local build.

Rather than keep debugging the dual-mode build blind (remote VM can't reproduce the Mac environment), the decision was: **freeze the dual-mode work, restore the `ffd2696` config as the default, and get Randy unblocked locally.**

---

## 2. What the Remote Agent Did (Commit `bb1ef07`)

On branch `minecraft-mod-1`, commit `bb1ef07` ("Restore ffd2696 build config as default; preserve dual-mode build"):

1. **Restored** `mathquest/build.gradle` to exactly what it was at `ffd2696`:
   ```bash
   git show ffd2696:mathquest/build.gradle > mathquest/build.gradle
   ```
2. **Restored** `mathquest/settings.gradle` to exactly what it was at `ffd2696`:
   ```bash
   git show ffd2696:mathquest/settings.gradle > mathquest/settings.gradle
   ```
3. **Preserved** the dual-mode work by copying (before the overwrite) to:
   - `mathquest/build.gradle.dual-mode`
   - `mathquest/settings.gradle.dual-mode`

---

## 3. Phase 1 — Local Build Restore (COMPLETED 2026-04-04)

### Step 3.1-3.3 — Pull and verify (DONE)

Pulled `minecraft-mod-1`, verified `build.gradle` and `settings.gradle` matched `ffd2696` exactly (both diffs empty). Dual-mode files confirmed present.

### Step 3.4 — Clear stale Gradle/Loom caches (DONE)

```bash
rm -rf ~/.gradle/caches/fabric-loom
rm -rf ~/Documents/Code/kid-games/mathquest/.gradle
rm -rf ~/Documents/Code/kid-games/mathquest/build
```

**Note for future reference:** Do NOT clear `~/.gradle/caches/fabric-loom` unless troubleshooting a corrupted cache — it forces a full re-download of Minecraft client (~30 MB) and server (~54 MB). The project-level `.gradle` and `build` directories are safe to clear without triggering re-downloads.

### Step 3.5 — Build and fix missing test dependencies (DONE)

The initial build failed with 100 `compileTestJava` errors: all `org.junit.jupiter.api` packages not found. This was expected — the test files were added after `ffd2696` by the remote agent, and the `ffd2696` `build.gradle` didn't have JUnit Jupiter.

**Fix applied (per the instructions' own guidance):** Compared `ffd2696` build.gradle against `build.gradle.dual-mode`, then ported ONLY the missing test dependency entries into `build.gradle`:

```groovy
testImplementation "org.junit.jupiter:junit-jupiter:5.11.4"
testRuntimeOnly "org.junit.platform:junit-platform-launcher"
testImplementation "org.xerial:sqlite-jdbc:3.49.1.0"
testImplementation "com.google.code.gson:gson:2.11.0"
```

Also added `test { useJUnitPlatform() }` block. No structural changes — no `buildscript`, no `updateStubs`, no conditional `useFabricLoom`.

Build then succeeded: `BUILD SUCCESSFUL in 51s`, all unit tests passed.

### Step 3.6 — Deploy and smoke-test (DONE)

Deployed via `build-and-deploy.sh`. Randy confirmed the mod loads and works in Minecraft (Fabric profile, 1.21.11).

### Additional improvements made during Phase 1

1. **Version bumped to 1.0.1** in `gradle.properties` (`mod_version=1.0.1`).
2. **`build-and-deploy.sh` upgraded:**
   - Reads `mod_version` and `archives_base_name` from `gradle.properties` automatically (single source of truth for version).
   - Accepts passthrough arguments: `./build-and-deploy.sh --offline` for cached-only builds, `./build-and-deploy.sh -x test` to skip tests, etc.
   - Archives old `mathquest*.jar` files from the mods folder into `mods/mathquest-inactive-mods/` with a timestamp before deploying the new one (e.g., `mathquest-fabric-1.0.1-mc1.21.11_2026-04-04_1547.jar`).

### Phase 1 commit

Phase 1 changes were committed to `minecraft-mod-1` as `2896418` ("phase 1 of LOCAL_BUILD_RESTORE done"):
- `mathquest/build.gradle` — test dependencies and `useJUnitPlatform()` added
- `mathquest/gradle.properties` — version bumped to 1.0.1
- `mathquest/build-and-deploy.sh` — auto-version, archiving, passthrough args

---

## 4. Phase 2 — Branch Consolidation (COMPLETED 2026-04-04)

### Step 4.1 — Commit Phase 1 changes (DONE)

Committed as `2896418` on `minecraft-mod-1`.

### Step 4.2 — Verify fast-forward (DONE)

`git merge-base --is-ancestor` confirmed FF-safe.

### Step 4.3 — Fast-forward `main` (DONE)

`main` fast-forwarded from `5c50dba` ("skyhanni agent run") to `2896418` ("phase 1 of LOCAL_BUILD_RESTORE done"). Pushed to `origin/main`.

### Step 4.4 — Verify final state (DONE)

Confirmed: `main`, `origin/main`, and `minecraft-mod-1` all point to `2896418`.

### Branch cleanup (DEFERRED)

The following branches are superseded but are being **intentionally kept** as a safety net, in case any code from the remote Claude Code sessions needs to be recovered:

- `claude/setup-kid-games-repo-lS5k9` (remote only)
- `claude/fix-fabric-maven-proxy-0cJzi` (remote only)
- `minecraft-mod-1` (local + remote)

Randy will review and delete these manually once he's confident everything needed has been merged. There is no cost to keeping them — Git branches are lightweight pointers and don't affect builds or other branches.

---

## 5. If Things Go Wrong

### The build still fails with the restored config

Diagnose in this order:

1. **Run with `--stacktrace`:**
   ```bash
   ./gradlew build --stacktrace 2>&1 | tee /tmp/mathquest-build.log
   ```
2. **Check Java version:** `java -version` must show 21.x. If not, fix `JAVA_HOME`.
3. **Check network:** `curl -I https://maven.fabricmc.net/` should return 200.
4. **Try `--offline`:** If network is flaky, `./gradlew build --offline` uses only cached dependencies.

### Test failures only

`./gradlew build -x test` to skip tests and ship the jar. Report the test failures separately; they can be fixed in a follow-up.

### Randy reports the in-game mod is broken

Do NOT start modifying code until you understand which commit regressed the behavior. Use `git log --oneline ffd2696..HEAD -- mathquest/src/` to list candidate commits and coordinate with Randy on which feature broke.

---

## 6. Key Files Reference

| Path | Purpose |
|---|---|
| `mathquest/build.gradle` | Based on `ffd2696` simple Fabric Loom plugin DSL, plus test dependencies (JUnit Jupiter, Gson, SQLite) added during Phase 1. |
| `mathquest/settings.gradle` | Identical to `ffd2696`. Standard `pluginManagement { repositories }`. |
| `mathquest/gradle.properties` | Mod version 1.0.1. Minecraft 1.21.11, Fabric Loader 0.18.3. |
| `mathquest/build-and-deploy.sh` | Builds, archives old jar, deploys new jar. Supports `--offline` and other Gradle flags. |
| `mathquest/build.gradle.dual-mode` | Frozen: the dual-mode build with stub compilation. Do not activate without a plan. |
| `mathquest/settings.gradle.dual-mode` | Frozen: companion to the dual-mode build.gradle. |
| `mathquest/stubs/` | Frozen stub sources used by dual-mode. Unused by current default build. |
| `mathquest/docs/MAVEN_PROXY_PROBLEM.md` | Writeup of the underlying proxy issue that motivated the dual-mode build. |
| `mathquest/docs/LOCAL_BUILD_RESTORE_INSTRUCTIONS.md` | This file. |

---

## 7. Summary

**Both Phase 1 and Phase 2 are complete as of 2026-04-04.**

- **The build works on Randy's Mac.** The mod loads and runs in Minecraft (v1.0.1).
- **`main` is fully up to date** — fast-forwarded to include all work from `minecraft-mod-1`.
- **`build.gradle`** is the `ffd2696` simple plugin DSL plus test dependencies ported from the dual-mode build.
- **No src/ changes were reverted** — unit tests, auto-accept, MathQuiz JSON export, and all feature work are intact.
- **The dual-mode (proxy-compatible) build is frozen** in `*.dual-mode` files. Can be revisited later without losing anything.
- **`claude/*` branches are intentionally kept** as a safety net until Randy confirms all needed code has been recovered.
- **Working branch:** `main`. Future MathQuest development should happen on `main` (or a new feature branch off `main`).
