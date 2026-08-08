---
name: mathquest migration
overview: "Execute the MathQuest migration as a controlled toolchain and source-mapping transition: first preserve the known-good 1.21.11 build, then convert shared Fabric source to Mojang names, then enable and validate 26.1.2 from the same source tree. The end state is one shared Fabric codebase that can build current `fabric-1.21.11` and `fabric-26.1.2`, with clear rules for adding older 1.21.x-and-before or newer 26.1.x+ targets later."
todos:
  - id: preflight-current-build
    content: Preflight current git state, Java/Gradle readiness, and the known-good `fabric-1.21.11` build.
    status: completed
  - id: generate-mojang-source
    content: Run Loom mapping migration on `fabric-1.21.11` and inspect `remappedSrc` before promotion.
    status: completed
  - id: verify-promote-source
    content: Compile-check migrated source on 1.21.11, then promote it into shared `fabric/src/main/java`.
    status: completed
  - id: update-legacy-target
    content: Switch `fabric-1.21.11` permanently to official Mojang mappings and remove Yarn-only properties.
    status: completed
  - id: upgrade-toolchain
    content: Bump Gradle wrapper and legacy Loom in lockstep, then revalidate 1.21.11.
    status: completed
  - id: enable-modern-target
    content: Clean up `fabric-26.1.2` source sets, add Java 25 settings, and fix 26.1 compile issues.
    status: completed
  - id: validate-both-targets
    content: Build both selected targets together and verify deploy-script behavior per target.
    status: completed
  - id: update-docs
    content: Update overview, multi-target docs, and migration notes to match the completed state.
    status: completed
isProject: false
---

# MathQuest 1.21 to 26.1 Migration Plan

## Scope

Use one Mojang-named shared Fabric source tree for both existing targets:

- Legacy family: `fabric-1.21.11` remains buildable and becomes the template for future <= 1.21.11 Fabric targets.
- Modern family: `fabric-26.1.2` becomes buildable and becomes the template for future >= 26.1.2 Fabric targets.
- Do not maintain parallel Yarn and Mojang source trees unless the single-source migration proves impossible.

Key files to touch during implementation:

- [mathquest/fabric/src/main/java](mathquest/fabric/src/main/java) — promote Loom-generated Mojang-named source here.
- [mathquest/targets/fabric-1.21.11/build.gradle](mathquest/targets/fabric-1.21.11/build.gradle) — switch 1.21.11 from Yarn mappings to `loom.officialMojangMappings()`.
- [mathquest/targets/fabric-1.21.11/gradle.properties](mathquest/targets/fabric-1.21.11/gradle.properties) — remove `yarn_mappings`, bump Loom only when the wrapper moves to Gradle 9.4+.
- [mathquest/targets/fabric-26.1.2/build.gradle](mathquest/targets/fabric-26.1.2/build.gradle) — remove the temporary local Java source slot and add Java 25 compile settings.
- [mathquest/settings.gradle](mathquest/settings.gradle) — keep `fabric-26.1.2` out of `DEFAULT_TARGETS` until both targets build on the upgraded wrapper.
- [mathquest/build-and-deploy.sh](mathquest/build-and-deploy.sh) — make target selection/deploy still work when building both Java 21 and Java 25 targets.
- [mathquest/docs/OVERVIEW.md](mathquest/docs/OVERVIEW.md), [mathquest/docs/2026-04-26_multi-target-build.md](mathquest/docs/2026-04-26_multi-target-build.md), and [mathquest/docs/2026-04-26_migration-1.21-to-26.1.md](mathquest/docs/2026-04-26_migration-1.21-to-26.1.md) — update once the migration is complete.

## Execution Steps

1. Preflight the current branch before changing mappings.
   - Confirm only expected user changes are present.
   - From `mathquest/`, run the known-good target first: `./gradlew :targets:fabric-1.21.11:build`.
   - Confirm local toolchain readiness: Gradle wrapper currently uses 8.14; Java 21 is required for the current target; Java 25 must be installed or discoverable before compiling 26.1.2.

2. Generate Mojang-named source from the current 1.21.11 target.
   - Run `./gradlew :targets:fabric-1.21.11:migrateMappings --mappings "net.minecraft:mappings:1.21.11"`.
   - Inspect `targets/fabric-1.21.11/remappedSrc/` for expected package rewrites such as `MinecraftClient` to `Minecraft`, `Identifier` to `ResourceLocation`, and `Text` to `Component`.
   - Do not replace `fabric/src/main/java` until the generated source has been compile-checked.

3. Verify the migrated source against 1.21.11 before promoting it.
   - Temporarily point `targets/fabric-1.21.11/build.gradle` at `remappedSrc` and switch its mappings line to `loom.officialMojangMappings()`.
   - Run `./gradlew :targets:fabric-1.21.11:compileJava`.
   - Fix migration misses, especially mixin/reflection/string identifiers if any appear. This codebase appears mostly direct Java/Fabric API calls, so likely issues are import/method rename misses rather than resource changes.

4. Promote the source migration.
   - Replace `fabric/src/main/java` with the verified `remappedSrc` output.
   - Restore `targets/fabric-1.21.11/build.gradle` to read from `rootProject.file('fabric/src/main/java')`.
   - Permanently keep `mappings loom.officialMojangMappings()` for 1.21.11.
   - Remove the unused `yarn_mappings` property from `targets/fabric-1.21.11/gradle.properties`.
   - Run `./gradlew :targets:fabric-1.21.11:test` and `./gradlew :targets:fabric-1.21.11:build`.

5. Move the shared toolchain forward carefully.
   - Bump the Gradle wrapper to 9.4+ only after the Mojang-named 1.21.11 target builds on the current wrapper.
   - In the same change window, bump `targets/fabric-1.21.11/gradle.properties` from Loom 1.13 to a Gradle-9-compatible Loom 1.14 line.
   - Re-run the 1.21.11 build immediately after the wrapper/Loom bump to catch plugin compatibility issues before involving 26.1.2.

6. Bring `fabric-26.1.2` online.
   - Remove the placeholder `targets/fabric-26.1.2/src/main/java` source slot and the `'src/main/java'` entry from its `sourceSets.main.java.srcDirs`.
   - Add Java 25 compile/toolchain settings in `targets/fabric-26.1.2/build.gradle`, while leaving root defaults at Java 21 for legacy targets.
   - Build explicitly with `./gradlew :targets:fabric-26.1.2:build`.
   - Resolve 26.1-specific Fabric API or Minecraft API changes using the Fabric 26.1 porting guide. Expect mechanical fixes around client UI, entity/rendering, networking, registry, and identifier/component APIs.

7. Validate both target families together.
   - Run `./gradlew buildAll -Ptargets=fabric-1.21.11,fabric-26.1.2`.
   - Once both pass, add `fabric-26.1.2` to `DEFAULT_TARGETS` in `settings.gradle` so normal `buildAll` covers both.
   - Confirm `./build-and-deploy.sh --target fabric-1.21.11 --no-deploy` and `./build-and-deploy.sh --target fabric-26.1.2 --no-deploy` both produce correctly named jars.
   - For playtesting, deploy one target at a time to the matching Minecraft profile to avoid installing incompatible jars together.

8. Update docs and future-target guidance.
   - Update `OVERVIEW.md` so targets no longer say 26.1.2 is pending migration.
   - Update the multi-target doc with the new default targets, Gradle 9.4+ wrapper, Java 21/25 split, and source now being Mojang-named.
   - Update or close out the migration doc with what actually changed and any 26.1 porting fixes discovered.
   - Add a short rule for future targets: <= 1.21.11 Fabric targets should follow the legacy target template but use official Mojang mappings; >= 26.1.2 targets should follow the modern Loom plugin/template and Java 25+ requirements.

## Risk Controls

- Keep `fabric-26.1.2` excluded from defaults until Gradle 9.4+, Loom 1.14 for 1.21.11, and Loom 1.15 for 26.1.2 all work together.
- Promote generated source only after `compileJava` succeeds against 1.21.11 official mappings.
- Avoid clearing global Gradle/Loom caches unless a cache corruption error points there; prior docs warn it forces large re-downloads.
- Preserve unrelated user edits, especially the existing modified [mathquest/docs/PLAN-TASKS.md](mathquest/docs/PLAN-TASKS.md).
- Treat `fabric/src/main/resources` as unaffected by mappings; only update resources if compilation or runtime behavior proves a resource identifier changed.
- Keep the frozen dual-mode/stub build out of this migration unless explicitly needed; it is documented as inactive technical debt.

## Success Criteria

- `./gradlew :targets:fabric-1.21.11:build` passes using Mojang-named source and official mappings.
- `./gradlew :targets:fabric-26.1.2:build` passes using the same shared Fabric source.
- `./gradlew buildAll -Ptargets=fabric-1.21.11,fabric-26.1.2` passes.
- Target jars are produced as `mathquest-fabric-<mod_version>-mc1.21.11.jar` and `mathquest-fabric-<mod_version>-mc26.1.2.jar` under each target's `build/libs` directory.
- Docs describe the new state accurately before we consider the migration complete.
