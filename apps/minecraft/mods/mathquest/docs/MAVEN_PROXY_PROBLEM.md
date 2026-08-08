# Maven Proxy Problem: Can't Build MathQuest Mod Remotely

## The Problem (Simple Version)

MathQuest is a Minecraft mod built with a tool called "Fabric." To compile the mod, the build system (Gradle) needs to download Minecraft's code and Fabric's libraries from a server called `maven.fabricmc.net`. 

**The problem:** In our remote development environment (Claude Code), there's a network proxy that blocks access to `maven.fabricmc.net`. The proxy returns "403 Forbidden - host_not_allowed." This means we literally cannot run the normal build command (`./gradlew build`) remotely. The mod can only be compiled on a local machine that has unrestricted internet access.

This also means we can't run Gradle-based tests, including Minecraft GameTest tests (which simulate an actual Minecraft server to test mod behavior).

## The Problem (Technical Details)

### What Fabric Loom Does

Fabric mods use a Gradle plugin called **Fabric Loom** (`fabric-loom`). When you run `./gradlew build`, Loom does several things before compilation even starts:

1. Downloads Minecraft's client/server JARs from Mojang
2. Downloads Fabric intermediary mappings from `maven.fabricmc.net`
3. Downloads Yarn mappings (human-readable names) from `maven.fabricmc.net`
4. Remaps Minecraft's obfuscated code using those mappings
5. Downloads the Fabric API modules from `maven.fabricmc.net`
6. Sets up the classpath so your mod code can compile against Minecraft + Fabric

Steps 2, 3, and 5 all require access to `maven.fabricmc.net`, which is blocked.

### What We Tried

1. **Direct Gradle build** (`./gradlew build`): Fails immediately because Fabric Loom can't download mappings from `maven.fabricmc.net`.

2. **Changing Loom versions** (tried 1.7-SNAPSHOT, 1.9-SNAPSHOT, 1.13.+): All fail for the same reason - every version of Loom needs `maven.fabricmc.net`.

3. **Checking if Fabric artifacts are on Maven Central**: They're not. Fabric hosts its own Maven repository exclusively. There's no mirror or alternative source.

4. **Verified the block with curl**: 
   ```
   curl -v https://maven.fabricmc.net
   → 403 Forbidden, "host_not_allowed"
   ```
   The proxy explicitly blocks this host.

### Our Workaround (Unit Tests Only)

We created a standalone test runner that bypasses Gradle entirely:

- Downloaded JUnit, SQLite JDBC, and Gson JARs directly from Maven Central (which IS accessible)
- Created a `FabricLoader` stub class that provides minimal implementations (e.g., returns a temp directory for `getConfigDir()`)
- Compiled main source files + test files with `javac` directly
- Ran tests with JUnit Platform Console Standalone runner

This lets us run **52 unit tests** that cover the pure-Java logic (QuizManager, Config, Database, SessionExporter). But it **cannot** test anything that depends on Minecraft classes (screens, rendering, commands, item giving, etc.).

### Files Related to the Workaround

- `mathquest/test-libs/` - JUnit, SQLite, Gson JARs (in .gitignore)
- `mathquest/test-build/stubs/FabricLoader.java` - Minimal Fabric stub
- `mathquest/test-build/classes/` - Compiled output (in .gitignore)
- `mathquest/src/test/java/com/kidgames/mathquest/StandaloneTestRunner.java` - Script to download JARs and run tests

## Why This Matters

1. **Can't verify the mod compiles** without building locally. If someone introduces a typo or import error, we won't catch it remotely.

2. **Can't run Minecraft GameTest tests** remotely. GameTests spin up a headless Minecraft server and test mod behavior in-game (e.g., "does the quiz screen open?", "do rewards get given?"). These require Fabric Loom to build.

3. **Can't set up CI/CD** that builds the mod, since any CI runner behind this proxy would hit the same block.

4. **Development feedback loop is slow** - changes have to be pushed, pulled locally, built locally, and tested locally before we know if they work.

## Current Build Configuration

- **Minecraft**: 1.21.11
- **Fabric Loader**: 0.18.3
- **Fabric API**: 0.139.4+1.21.11
- **Yarn Mappings**: 1.21.11+build.3
- **Fabric Loom**: 1.13.+
- **Java**: 21
- **Gradle**: via wrapper (gradle-wrapper.jar committed)

Key build files:
- `mathquest/build.gradle` - Main build config with Fabric Loom plugin
- `mathquest/settings.gradle` - Plugin repository configuration
- `mathquest/gradle.properties` - Version properties

## Next Steps for Resolution

Here are potential approaches to explore, ordered by likelihood of success:

### Option A: Get `maven.fabricmc.net` Added to the Proxy Allowlist

The most direct fix. The proxy has an allowlist of permitted hosts. If `maven.fabricmc.net` (and potentially `maven.mojang.com`, `libraries.minecraft.net`, `piston-meta.mojang.com`) can be added, everything would just work.

**To investigate:** Check if the environment has any configuration for proxy allowlists. Look at environment variables, proxy config files, or documentation about the proxy setup.

### Option B: Pre-populate Gradle Cache

If we can get a full Gradle cache from a local build (the `~/.gradle/caches/` directory), we could copy it into the remote environment. Loom wouldn't need to download anything if all artifacts are already cached.

**To investigate:** 
- Check what's in `~/.gradle/caches/` on a machine that has successfully built the mod
- Determine if we can commit or transfer a Gradle cache snapshot
- May need `fabric-loom-cache/` directory specifically

### Option C: Offline Gradle Build with Pre-downloaded Dependencies

Gradle supports `--offline` mode. If all dependencies are pre-downloaded and cached, `./gradlew build --offline` should work without any network access.

**To investigate:**
- Build locally with `./gradlew build --refresh-dependencies` to ensure full cache
- Archive the entire `.gradle` directory
- Transfer to remote environment
- Test `./gradlew build --offline`

### Option D: Vendor All Dependencies in the Repository

Bundle all required JARs (Fabric API, Loom, mappings, Minecraft) directly in the repo and configure Gradle to use local file repositories instead of remote ones.

**To investigate:**
- This is complex because Loom does special remapping steps
- Would need to modify `build.gradle` significantly
- May break when updating Minecraft versions

### Option E: Use a SOCKS Proxy or SSH Tunnel

If there's a machine with unrestricted access, set up a tunnel through it.

**To investigate:**
- Do we have access to any machine with unrestricted internet?
- Can we configure Gradle's proxy settings to use a tunnel?

### Recommended Starting Point

**Start with Option A** - check if there's a way to modify the proxy allowlist. If not, **try Option C** (offline Gradle) as the most practical workaround that doesn't require changing infrastructure.

To verify the fix works, the success criteria is:
```bash
cd mathquest
./gradlew build
# Should complete successfully and produce a JAR in build/libs/
```
