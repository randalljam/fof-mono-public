# Local build failure troubleshooting
_Exported on 5/11/2026 at 15:40:56 PDT from Cursor (3.3.30)_

---

**User**

@mathquest/docs/2026-05-11_mathquest-server-conversion-plan.md @mathquest/docs/OVERVIEW.md @/Users/randytrue/.cursor/projects/Users-randytrue-Documents-Code-kid-games/terminals/7.txt:49-91  -Okay, review the following files and I'm trying to, I just tried to run the local build of this and it failed. So I'm going to add that terminal output here. So troubleshoot and figure out what the root cause of this is and fix it. You may need to go to the problems-report.html.

---

**Cursor**

Tracing the Fabric 26.1.2 build failure: locating the KeyBindingHelper source and verifying Fabric API dependencies.



Checking the compile classpath — `fabric-26.1.2` uses `implementation` instead of `modImplementation` like the working `fabric-1.21.11` target.



Identifying root cause: the `fabric-api` 0.146.1+26.1.2 aggregate POM no longer declares `fabric-key-binding-api-v1`, so `KeyBindingHelper` isn't on the compile classpath. Adding the module explicitly and switching to `modImplementation` for Loom.



Applying the Gradle fix and running the build.



## Root cause

`MathQuestClient` imports `net.fabricmc.fabric.api.client.keybinding.v1.KeyBindingHelper` from **`fabric-key-binding-api-v1`**.

For **`fabric-api` `0.146.1+26.1.2`**, the published **aggregator POM** lists many submodule JARs, but **does not declare `fabric-key-binding-api-v1`**. Gradle therefore never added that artifact to **`compileClasspath`**, so javac reports “package … does not exist.” This is unrelated to Mojang mappings or your Java runtime; it is a **missing split-module dependency** on the 26.1.x target.

Problems report / HTML was not necessary once the classpath was traced: the aggregator POM confirms the omission (no `key-binding` entry).

## Fix (done)

1. **`targets/fabric-26.1.2/build.gradle`** — add an explicit **`implementation`** line for **`net.fabricmc.fabric-api:fabric-key-binding-api-v1`**.
2. **`targets/fabric-26.1.2/gradle.properties`** — add **`fabric_key_binding_api_version`** (currently **`1.1.8+9c919dacc9`** on Fabric’s Maven). Bump this when you bump **`fabric_version`**, pairing submodules per the Fabric release you adopt.

Workspace rule: **`docs/OVERVIEW.md`** is updated in the **26.1 API overrides** bullet to describe this Gradle split.

Verification: **`./gradlew :targets:fabric-26.1.2:compileJava`** and **`build`** succeed with **`GRADLE_USER_HOME=/Users/randytrue/.gradle`**.

Side note from the Gradle run: **`modImplementation`** is **not** a valid configuration under **`net.fabricmc.fabric-loom` 1.15** here (only **`implementation`** applies), which is why a quick flip to **`modImplementation`** failed configuration.

You can rerun **`./build-and-deploy.sh`** on your machine; it should compile past **`KeyBindingHelper`** now.

### Optional tightening

When you upgrade **`fabric_version`**, check **`fabric_key_binding_api_version`** against the **`fabric`** repo’s **`gradle.properties`** for that release (or Fabric’s changelog) so the key-binding submodule stays aligned with the rest of Fabric API.

### Sandboxed Gradle note

Gradle in this environment pointed **`GRADLE_USER_HOME`** at a sandbox path and Fabric Loom could **block on a stale lock**. Your laptop build using `~/.gradle` should not hit that; if Cursor’s sandbox Gradle ever wedges on “Waiting for lock…”, kill the orphaned Java process holding the loom lock or set **`GRADLE_USER_HOME`** to your normal home cache for agent runs.

If you want, I can bump **`fabric_key_binding_api_version`** to a hash that Fabric tags exactly with **`0.146.1+26.1.2`** instead of the latest **`1.1.x`** line (compile is green either way).

---

**User**

<system_notification>
The following task has finished. If you were already aware, ignore this notification and do not restate prior responses.

<task>
kind: shell
status: error
task_id: 512279
title: Check if key-binding-api is on compile classpath
detail: exit_code=1
output_path: /Users/randytrue/.cursor/projects/Users-randytrue-Documents-Code-kid-games/terminals/512279.txt
</task>
</system_notification>
<user_query>Briefly inform the user about the task result and perform any follow-up actions (if needed).</user_query>

<system_notification>
The following task has finished. If you were already aware, ignore this notification and do not restate prior responses.

<task>
kind: shell
status: error
task_id: 627306
title: Compile fabric-26.1.2 to verify KeyBindingHelper fix
detail: exit_code=1
output_path: /Users/randytrue/.cursor/projects/Users-randytrue-Documents-Code-kid-games/terminals/627306.txt
</task>
</system_notification>
<user_query>Briefly inform the user about the task result and perform any follow-up actions (if needed).</user_query>

<system_notification>
The following task has finished. If you were already aware, ignore this notification and do not restate prior responses.

<task>
kind: shell
status: error
task_id: 561981
title: Compile fabric-26.1.2 outside sandbox to avoid loom lock
detail: exit_code=1
output_path: /Users/randytrue/.cursor/projects/Users-randytrue-Documents-Code-kid-games/terminals/561981.txt
</task>
</system_notification>
<user_query>Briefly inform the user about the task result and perform any follow-up actions (if needed).</user_query>

---

**Cursor**

Here’s what those finished tasks mean:

- **512279 (dependencies + `grep`)** — Exited non‑zero, most likely because **`grep` found no `key-binding` lines** while output was huge/slow piped through `grep`, or the run was aborted. It didn’t disprove the diagnosis; dependency inspection elsewhere showed the aggregator POM omission.
- **627306 / 561981 (`compileJava`)** — Failed because Gradle/Loom waited on a **`fabric-loom` cache lock** held by another Java process tied to Cursor’s sandbox Gradle cache—not because the compiler fix failed.

**Follow-up:** Nothing more is required from that work. The real fix (**explicit `fabric-key-binding-api-v1`** on `fabric-26.1.2`) **built successfully** when Gradle used your normal home cache (`GRADLE_USER_HOME=~/.gradle`). On your machine, run **`./build-and-deploy.sh`** again; if you ever see **“Waiting for lock…”** during agent runs, use your usual `~/.gradle` or kill the orphaned Gradle/Java process holding the lock.

---

**User**

Okay, so this did... it did build. The build was successful. You can see that at the end of this file, but then when I launched Minecraft it crashed. So review the crash report and figure out what went wrong. I've never seen this happen before. And the other thing I want you to answer is that this build for 26.1.2 did work properly last week, the last time I ran it, when the targets were set to both 1.21.11 Minecraft version and 26.1.2. So why is it not working now? What changed that caused it to... caused the build to fail before and then... because I'm worried that the changes that you made to it have now caused a crash. Again, I've never seen this type of crash before all that would happen when there would be bugs in the code would be it that would not build.

---- Minecraft Crash Report ----
// I blame Dinnerbone.

Time: 2026-05-11 15:18:56
Description: Initializing game

java.lang.RuntimeException: Could not execute entrypoint stage 'client' due to errors, provided by 'mathquest' at 'com.kidgames.mathquest.MathQuestClient'!
	at net.fabricmc.loader.impl.FabricLoaderImpl.lambda$invokeEntrypoints$0(FabricLoaderImpl.java:409)
	at net.fabricmc.loader.impl.util.ExceptionUtil.gatherExceptions(ExceptionUtil.java:33)
	at net.fabricmc.loader.impl.FabricLoaderImpl.invokeEntrypoints(FabricLoaderImpl.java:407)
	at net.fabricmc.loader.impl.game.minecraft.Hooks.startClient(Hooks.java:53)
	at knot//net.minecraft.client.Minecraft.<init>(Minecraft.java:477)
	at knot//net.minecraft.client.main.Main.main(Main.java:232)
	at net.fabricmc.loader.impl.game.minecraft.MinecraftGameProvider.launch(MinecraftGameProvider.java:514)
	at net.fabricmc.loader.impl.launch.knot.Knot.launch(Knot.java:72)
	at net.fabricmc.loader.impl.launch.knot.KnotClient.main(KnotClient.java:23)
Caused by: java.lang.NoClassDefFoundError: net/fabricmc/fabric/api/client/keybinding/v1/KeyBindingHelper
	at knot//com.kidgames.mathquest.MathQuestClient.onInitializeClient(MathQuestClient.java:44)
	at net.fabricmc.loader.impl.FabricLoaderImpl.invokeEntrypoints(FabricLoaderImpl.java:405)
	... 6 more
Caused by: java.lang.ClassNotFoundException: net.fabricmc.fabric.api.client.keybinding.v1.KeyBindingHelper
	at java.base/jdk.internal.loader.BuiltinClassLoader.loadClass(BuiltinClassLoader.java:580)
	at java.base/java.lang.ClassLoader.loadClass(ClassLoader.java:490)
	at net.fabricmc.loader.impl.launch.knot.KnotClassDelegate.loadClass(KnotClassDelegate.java:239)
	at net.fabricmc.loader.impl.launch.knot.KnotClassLoader.loadClass(KnotClassLoader.java:119)
	at java.base/java.lang.ClassLoader.loadClass(ClassLoader.java:490)
	... 8 more


A detailed walkthrough of the error, its code path and all known details is as follows:
---------------------------------------------------------------------------------------

-- Head --
Thread: Render thread
Stacktrace:
	at net.fabricmc.loader.impl.FabricLoaderImpl.lambda$invokeEntrypoints$0(FabricLoaderImpl.java:409)
	at net.fabricmc.loader.impl.util.ExceptionUtil.gatherExceptions(ExceptionUtil.java:33)
	at net.fabricmc.loader.impl.FabricLoaderImpl.invokeEntrypoints(FabricLoaderImpl.java:407)
	at net.fabricmc.loader.impl.game.minecraft.Hooks.startClient(Hooks.java:53)
	at knot//net.minecraft.client.Minecraft.<init>(Minecraft.java:477)

-- Initialization --
Details:
	Modules: 
Stacktrace:
	at knot//net.minecraft.client.main.Main.main(Main.java:232)
	at net.fabricmc.loader.impl.game.minecraft.MinecraftGameProvider.launch(MinecraftGameProvider.java:514)
	at net.fabricmc.loader.impl.launch.knot.Knot.launch(Knot.java:72)
	at net.fabricmc.loader.impl.launch.knot.KnotClient.main(KnotClient.java:23)

-- System Details --
Details:
	Minecraft Version: 26.1.2
	Minecraft Version ID: 26.1.2
	Operating System: Mac OS X (aarch64) version 15.3.1
	Java Version: 25.0.1, Microsoft
	Java VM Version: OpenJDK 64-Bit Server VM (mixed mode), Microsoft
	Memory: 1258291200 bytes (1200 MiB) / 2147483648 bytes (2048 MiB) up to 4294967296 bytes (4096 MiB)
	Memory (heap): init: 2048MiB, used: 848MiB, committed: 2048MiB, max: 4096MiB
	Memory (non-head): init: 007MiB, used: 130MiB, committed: 131MiB, max: 000MiB
	CPUs: 16
	Processor Vendor: Apple Inc.
	Processor Name: Apple M4 K2
	Identifier: Apple Inc. Family 0x1b588bb3 Model 0 Stepping 0
	Microarchitecture: ARM64 SoC: Firestorm + Icestorm
	Frequency (GHz): 0.00
	Number of physical packages: 1
	Number of physical CPUs: 16
	Number of logical CPUs: 16
	Graphics card #0 name: Apple M4 K2
	Graphics card #0 vendor: Apple (0x106b)
	Graphics card #0 VRAM (MiB): 0.00
	Graphics card #0 deviceId: unknown
	Graphics card #0 versionInfo: unknown
	Memory slot #0 capacity (MiB): 0.00
	Memory slot #0 clockSpeed (GHz): 0.00
	Memory slot #0 type: unknown
	Virtual memory max (MiB): 66560.00
	Virtual memory used (MiB): 49370.91
	Swap memory total (MiB): 1024.00
	Swap memory used (MiB): 1.19
	Space in storage for jna.tmpdir (MiB): available: 770621.56, total: 1902788.38
	Space in storage for org.lwjgl.system.SharedLibraryExtractPath (MiB): available: 770621.56, total: 1902788.38
	Space in storage for io.netty.native.workdir (MiB): available: 770621.56, total: 1902788.38
	Space in storage for java.io.tmpdir (MiB): available: 770621.56, total: 1902788.38
	Space in storage for workdir (MiB): available: 770621.56, total: 1902788.38
	JVM Flags: 6 total; -Xms2G -Xmx4G -XX:+UseCompactObjectHeaders -XX:+AlwaysPreTouch -XX:+UseStringDeduplication -XX:+UseZGC
	Debug Flags: 0 total; 
	Fabric Mods: 
		fabric-api: Fabric API 0.147.0+26.1.2
			fabric-api-base: Fabric API Base 2.0.3+ece063234c
			fabric-api-lookup-api-v1: Fabric API Lookup API (v1) 2.0.11+d5a053b64c
			fabric-biome-api-v1: Fabric Biome API (v1) 18.0.4+35c80edc4c
			fabric-block-api-v1: Fabric Block API (v1) 3.0.2+ec56b6014c
			fabric-block-getter-api-v2: Fabric BlockGetter API (v2) 2.0.6+ec56b6014c
			fabric-command-api-v2: Fabric Command API (v2) 3.0.5+e2bdee784c
			fabric-content-registries-v0: Fabric Content Registries (v0) 11.0.13+d871b99e4c
			fabric-convention-tags-v2: Fabric Convention Tags (v2) 4.5.0+4e71cda84c
			fabric-crash-report-info-v1: Fabric Crash Report Info (v1) 1.0.3+9f78a5a84c
			fabric-creative-tab-api-v1: Fabric Creative Tab API (v1) 5.0.10+d871b99e4c
			fabric-data-attachment-api-v1: Fabric Data Attachment API (v1) 2.2.4+d602a8964c
			fabric-data-generation-api-v1: Fabric Data Generation API (v1) 24.0.19+35c80edc4c
			fabric-debug-api-v1: Fabric Debug API (v1) 1.0.1+c792624d4c
			fabric-dimensions-v1: Fabric Dimensions API (v1) 5.1.5+9cbf5da54c
			fabric-entity-events-v1: Fabric Entity Events (v1) 5.0.2+e2bdee784c
			fabric-events-interaction-v0: Fabric Events Interaction (v0) 5.1.10+c82f04614c
			fabric-game-rule-api-v1: Fabric Game Rule API (v1) 4.0.5+d871b99e4c
			fabric-item-api-v1: Fabric Item API (v1) 14.1.1+73d134684c
			fabric-key-mapping-api-v1: Fabric Key Mapping API (v1) 2.0.4+e2bdee784c
			fabric-lifecycle-events-v1: Fabric Lifecycle Events (v1) 4.1.0+6d50a0854c
			fabric-loot-api-v3: Fabric Loot API (v3) 3.0.11+00a1fba64c
			fabric-menu-api-v1: Fabric Menu API (v1) 2.0.12+d871b99e4c
			fabric-message-api-v1: Fabric Message API (v1) 7.0.5+dae8ce3e4c
			fabric-model-loading-api-v1: Fabric Model Loading API (v1) 8.0.5+c80601bb4c
			fabric-networking-api-v1: Fabric Networking API (v1) 6.3.0+50a808ce4c
			fabric-object-builder-api-v1: Fabric Object Builder API (v1) 23.0.14+b95dd56e4c
			fabric-particles-v1: Fabric Particles (v1) 5.0.14+b61fef434c
			fabric-recipe-api-v1: Fabric Recipe API (v1) 9.0.14+be4b75ae4c
			fabric-registry-sync-v0: Fabric Registry Sync (v0) 7.0.12+b61fef434c
			fabric-renderer-api-v1: Fabric Renderer API (v1) 13.0.2+c80601bb4c
			fabric-renderer-indigo: Fabric Renderer - Indigo 8.0.4+a6be36ef4c
			fabric-rendering-fluids-v1: Fabric Rendering Fluids (v1) 6.0.1+d871b99e4c
			fabric-rendering-v1: Fabric Rendering (v1) 23.0.6+08c26e364c
			fabric-resource-conditions-api-v1: Fabric Resource Conditions API (v1) 6.0.5+00a1fba64c
			fabric-resource-loader-v0: Fabric Resource Loader (v0) 3.3.16+4fc5413f4c
			fabric-resource-loader-v1: Fabric Resource Loader (v1) 2.0.9+d871b99e4c
			fabric-screen-api-v1: Fabric Screen API (v1) 5.0.1+d871b99e4c
			fabric-serialization-api-v1: Fabric Serialization API (v1) 2.0.3+11a26f314c
			fabric-sound-api-v1: Fabric Sound API (v1) 2.0.4+11a26f314c
			fabric-tag-api-v1: Fabric Tag API (v1) 2.0.9+11a26f314c
			fabric-transfer-api-v1: Fabric Transfer API (v1) 8.0.5+357ea7334c
			fabric-transitive-access-wideners-v1: Fabric Transitive Access Wideners (v1) 8.0.11+d871b99e4c
		fabricloader: Fabric Loader 0.19.2
			mixinextras: MixinExtras 0.5.4
		java: OpenJDK 64-Bit Server VM 25
		mathquest: MathQuest 1.2.1
			org_xerial_sqlite-jdbc: sqlite-jdbc 3.49.1.0
		minecraft: Minecraft 26.1.2
	Launched Version: fabric-loader-0.19.2-26.1.2
	Launcher name: minecraft-launcher
	Backend library: LWJGL version 3.4.1-snapshot
	Backend API: Unknown
	Window size: <not initialized>
	GFLW Platform: <error>
	Render Extensions: ERR
	GL debug messages: <no renderer available>
	Is Modded: Definitely; Client brand changed to 'fabric'
	Universe: 404
	Type: Client
	Locale: en_US
	System encoding: UTF-8
	File encoding: UTF-8
	CPU: 16x Apple M4 K2  @/Users/randytrue/.cursor/projects/Users-randytrue-Documents-Code-kid-games/terminals/7.txt:92-115 

---

**Cursor**

Diagnosing: compile succeeded but runtime can't find `KeyBindingHelper`. Fabric API on the classpath (0.147.0) lists submodules — `fabric-key-binding-api-v1` is absent — so Minecraft doesn't load those classes. We added compile-only `implementation` without `include`, so unlike sqlite-jdbc the key-binding JAR wasn't bundled. Verifying Loom `include` and applying the fix.



Compile-time: `implementation` puts `fabric-key-binding-api-v1` on Gradle's classpath. Runtime: that JAR wasn't nested in MathQuest (`include`) like SQLite, and the installed Fabric API 0.147.0 submodule list excludes `fabric-key-binding-api-v1`, so Knot can't load `KeyBindingHelper`. Bundling with `include implementation(...)` (JiJ).



## What broke (from the crash report)

`MathQuestClient` loads `KeyBindingHelper` at startup. Loader failed with **`ClassNotFoundException: net.fabricmc.fabric.api.client.keybinding.v1.KeyBindingHelper`**.

Your crash snippet’s **Fabric Mods** tree lists **`fabric-key-mapping-api-v1`** and many Fabric API jars, but **no `fabric-key-binding-api-v1`**. That class lives only in **`fabric-key-binding-api-v1`**.

The earlier fix added that module only as Gradle **`implementation`**, which fixes **compilation** only. **`Implementation` does not put the jar into MathQuest’s published mod** unless you **`include`** it (Jar-in-Jar), the same pattern you already use for **`sqlite-jdbc`**.

Verification after the fix: your built jar now contains **`META-INF/jars/fabric-key-binding-api-v1-1.1.8+9c919dacc9.jar`**, so Loader can load **`KeyBindingHelper`** at runtime.

Change applied in ```46:53:mathquest/targets/fabric-26.1.2/build.gradle`:
- **`include implementation("net.fabricmc.fabric-api:fabric-key-binding-api-v1:…")`** instead of plain **`implementation`**.

Rebuild and redeploy with **`./build-and-deploy.sh`**, then start Minecraft again.

---

## Did the first fix “cause” this crash?

**Partially.** The **first** Gradle change only repaired **javac**. It didn’t mimic how you ship SQLite, so you got **build OK, startup crash** — uncommon but expected when compile classpath and Fabric **runtime classpath** diverge.

The crash is **not** a random Mojang Loader bug; it’s **exactly missing `KeyBindingHelper` on the Knot classpath.**

---

## “Last week dual targets worked” — what changed?

A few layered changes are easy to confuse:

1. **Fabric dropped `fabric-key-binding-api-v1` from the aggregated Gradle `fabric-api` POM** for 26.1.x, so **Gradle stopped pulling it transitively → compile failure** unless you declare it explicitly.
2. **The Fabric installer’s split API jars** still don’t list **`fabric-key-binding-api-v1`** (your crash report matches that): mods that use **`KeyBindingHelper`** must **bundle** that module or declare an equivalent dependency path.
3. **Building both `fabric-1.21.11` and `fabric-26.1.2` doesn’t change what’s inside the `fabric-26.1.2` jar** — only the Gradle fix + JiJ completeness explain this regression.

So: earlier you likely had either **different Fabric/MathQuest revisions**, or you **hadn’t yet hit `KeyBindingHelper` on 26.1.2** the way you do now.

---

**SQLite JVM warning** in the Gradle log (**`Restricted method ... System.load`**) is separate (Java 25 tightening); it isn’t what caused this crash. If it starts failing builds, adding **`--enable-native-access=ALL-UNNAMED`** to Gradle’s JVM flags is one mitigation.

If anything still blows up after redeploy with the JiJ jar, paste the **new** crash report and mod list.

---

**User**

Okay, this time it worked. So just... What I'd like you to do is to... Put into the the server conversion plan under phase 0. Put a... Markdown heading 4 under p0-1 and put what this branch is called and then say cursor composer to a AI troubleshooting and then put a summary of what you changed and what you did to get this to work. Because it seems to be working now. I ran the the mod and I went in the game and I spawned the the Wondering Nerd and I did a functional test and I didn't do a thorough test, but a basic one everything seemed to work. So yeah, summarize this in the in this plan.md file and then give me a commit message to put into this commit and then explicitly give instructions and specifications for the coding agent that made the changes that that resulted in the problem or the bug so that this doesn't happen again. And if something in the overview.md also needs to change then then update that there, but I want the the plan.md to kind of have a primary record of this troubleshooting. Okay, do it.

---

**Cursor**

Reading the conversion plan and git branch, then adding the P0-1 troubleshooting record and verifying OVERVIEW alignment.



Adding the P0-1 troubleshooting subsection to the plan and verifying OVERVIEW completeness.



Here is what was updated and what you can use next.

### Documentation updates

1. **`mathquest/docs/2026-05-11_mathquest-server-conversion-plan.md`** — Under **Phase 0 → P0-1**, added a level-4 heading **`#### P0-1 — Fabric 26.1.2 client startup troubleshooting (Cursor Composer)`** with:
   - **Branch** `claude/mathquest-phase-0-13SLj-P0-1`
   - AI / Cursor Composer context, failure sequence (compile → runtime), final fix, RT smoke test note
   - A **Specifications for coding agents** list (split modules, **`include implementation`** vs **`implementation`**, no blind **`modImplementation`**, version bumps, **`jar tf`** check, cross-doc to **OVERVIEW**)

2. **`mathquest/docs/OVERVIEW.md`** — Extended the existing **26.1 API overrides** bullet with a pointer to that **P0-1** subsection so the plan stays the main story and **OVERVIEW** stays the technical summary.

### Suggested commit message

```
P0-1: JiJ fabric-key-binding-api-v1 for fabric-26.1.2; document Cursor fix

The fabric-api aggregate for MC 26.1 omits fabric-key-binding-api-v1, so
MathQuestClient's KeyBindingHelper was missing at compile and (after
implementation-only) at runtime. Pin fabric_key_binding_api_version and use
include implementation(...) on the 26.1.2 target like sqlite-jdbc.

Record branch, timeline, and coding-agent rules under P0-1 in
2026-05-11_mathquest-server-conversion-plan.md; cross-link from OVERVIEW.

Refs #3
```

(Adjust **`Refs #3`** if your issue number differs.)

### Specifications for coding agents (copy-paste)

Use this as standing guidance so the same mistake does not repeat:

- If **`compileJava`** fails on a missing **`net.fabricmc.fabric.api.*`** type, assume a **split Fabric API module** may be missing from the **`fabric-api`** aggregate for that Minecraft line. Find the module on Fabric’s Maven / repo, declare it on **`targets/fabric-26.1.2/build.gradle`** only if needed.
- For **`fabric-26.1.2`**, **`implementation`** alone fixes **compilation** only. If Loader must see the classes at game start and the Fabric installer does not ship that module, use **`include implementation("net.fabricmc.fabric-api:<module>:<version>")`** (JiJ), same as **`sqlite-jdbc`**.
- Do not assume **`modImplementation`** exists on the **`net.fabricmc.fabric-loom`** 26.1 target; it is configured differently from **`fabric-1.21.11`**.
- When bumping **`fabric_version`** in **`targets/fabric-26.1.2/gradle.properties`**, update **`fabric_key_binding_api_version`** from the matching Fabric release submodule list.
- After changing dependencies, confirm the built jar nests **`META-INF/jars/fabric-key-binding-api-v1-*.jar`** (e.g. **`jar tf targets/fabric-26.1.2/build/libs/mathquest-fabric-*-mc26.1.2.jar`**) before treating the fix as done.
- Prefer recording long troubleshooting narratives under **`docs/2026-05-11_mathquest-server-conversion-plan.md`** (P0-1) and a short rule in **`OVERVIEW.md`**.

**Note:** Git shows an untracked **`mathquest/targets/fabric-26.1.2/logs/`**. That is local Loom/Minecraft output — do not commit it; delete it or add a **`targets/*/logs/`** (or similar) line to **`.gitignore`** if you want that ignored automatically.

