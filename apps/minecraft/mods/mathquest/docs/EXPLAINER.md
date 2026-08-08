# Minecraft modding toolchain — a technical explainer

This document is for someone comfortable with **Python**, **web development**, and general programming concepts, but **new to Java modding**. It explains how **Fabric**, **Gradle**, **Loom**, **Maven-style repositories**, and **Minecraft versions** fit together.

---

## 1. The big picture: you can’t just “drop a `.py` file” into Minecraft

Minecraft is a **Java** game. Its internals are **obfuscated** (class and method names are not the readable names you see in tutorials). To change behavior safely and in a supported way, you:

1. Use a **mod loader** that can inject code into the game at startup.
2. Build a **`.jar`** (a compiled Java archive, a bit like a `.zip` of `.class` files + resources).
3. Put that jar in the game’s **`mods`** folder alongside the loader.

**Fabric** is one such loader. **Forge** is another. They solve the same high-level problem with different designs and ecosystems.

---

## 2. Fabric vs Forge (high level)

| | **Fabric** | **Forge** |
|---|------------|-----------|
| **Philosophy** | Lightweight, modular; many small optional pieces (e.g. Fabric API). | Heavier, “batteries included” style; large API surface. |
| **Typical use** | Popular for newer Minecraft versions and for modders who want minimal overhead. | Long history; huge mod catalog; some teams still prefer it for certain projects. |
| **This project** | MathQuest is a **Fabric** mod. | Not used here. |

Neither is “wrong.” They are **incompatible at the mod level**: a Forge mod won’t load under Fabric and vice versa. Players install **one** loader profile (Fabric *or* Forge) for a given Minecraft install.

**Fabric** itself is maintained by the **Fabric team** (open-source community, centered around [fabricmc.net](https://fabricmc.net/) and GitHub). It is **not** made by Mojang, but it is designed to work with **official** Minecraft releases Mojang publishes.

---

## 3. What is Gradle?

**Gradle** is a **build automation** tool for Java (and other languages). Think of it as:

- **`pip` + `requirements.txt` + a build script`**, or  
- **`npm` + `package.json` + scripts`**,  

but for Java projects and often much more powerful (and verbose).

In a Fabric mod repo you’ll see:

- **`build.gradle`** — declares plugins (e.g. Fabric Loom), dependencies, and tasks (`build`, `test`, …).
- **`gradle.properties`** — version numbers and settings (Minecraft version, Yarn mappings version, mod version).
- **`gradlew` / `gradlew.bat`** — the **Gradle Wrapper**: runs a **specific Gradle version** so everyone gets the same build without installing Gradle globally.
- **`gradle/wrapper/gradle-wrapper.properties`** — which Gradle distribution ZIP to download (e.g. 8.14 vs 9.x).

You run **`./gradlew build`** from the project directory; Gradle downloads what it needs (once), compiles your mod, and produces **`build/libs/*.jar`**.

---

## 4. What is Fabric Loom?

**Fabric Loom** is a **Gradle plugin** maintained by the Fabric team. It is **not** Gradle itself; it **plugs into** Gradle.

Loom’s job is to turn “I want to mod Minecraft **1.21.11** with Fabric” into something Gradle can compile:

- Download the right **Minecraft** client (and often server) jars for that version.
- Apply **mappings** so that obfuscated names become **human-readable** names in your source (via **Yarn** or official **Mojang** mappings, depending on setup).
- Wire in **Fabric Loader**, **Fabric API**, and your mod.
- Produce a **remapped** mod jar that works inside the real game.

Without Loom (or an equivalent), you would be manually juggling jars and mappings — basically impractical.

---

## 5. “Maven” — repositories, not (just) the build tool

People say **“Maven”** in two related ways:

### A) Apache Maven — a build tool

**Maven** is another Java build system (like Gradle). Fabric mods in this repo **use Gradle**, not Maven, as the primary build tool.

### B) **Maven repositories** — a standard way to host libraries

Most Java ecosystems publish libraries to **Maven-compatible servers**. URLs look like:

- `https://maven.fabricmc.net/...` — **Fabric’s** artifacts (loader, Yarn, intermediary, Loom sometimes, etc.)
- `https://repo.maven.apache.org/...` — **Maven Central** (huge pile of open-source Java libs)
- Mojang-related hosts for **Minecraft** game jars (Loom handles much of this for you)

Gradle declares dependencies like coordinates:

```text
net.fabricmc:fabric-loader:0.18.3
```

Gradle then **resolves** them by downloading `.jar` / `.pom` files from those repositories — similar in spirit to **`pip`** talking to **PyPI** or **`npm`** talking to **registry.npmjs.org**.

So when docs say “Fabric publishes to Maven,” they mean: **the files live on a Maven-style server**, not that you must use the Maven build tool.

---

## 6. The toolchain end-to-end (what happens when you run `./gradlew build`)

Roughly:

1. **Gradle** reads `build.gradle` and `gradle.properties`.
2. **Fabric Loom** (a Gradle plugin) downloads **Minecraft** for the pinned version and sets up **mappings** (Yarn or Mojang mappings, depending on configuration).
3. Your **Java source** is compiled against the **mapped** Minecraft + **Fabric API** + **Fabric Loader** APIs.
4. Loom **remaps** your mod so it matches what the obfuscated game expects at runtime.
5. Output: a **mod `.jar`** you copy to the **`mods`** folder.

**Fabric Loader** is what actually loads mods **inside the game**. **Fabric API** is an optional (but common) library that adds many hooks and helpers; most Fabric mods depend on it.

---

## 7. Where do I see which Minecraft versions Fabric supports?

There isn’t one magic “green/red” page that never goes stale, but these are the right places:

| Resource | URL | What it’s for |
|----------|-----|----------------|
| **Fabric develop / template** | [fabricmc.net/develop](https://fabricmc.net/develop/) | Official entry: docs, template generator, links to versions. |
| **Fabric Wiki — versions** | [fabricmc.net/wiki](https://fabricmc.net/wiki/) | Community docs; often has version-related notes. |
| **Yarn (mappings) list** | [maven.fabricmc.net — Yarn metadata](https://maven.fabricmc.net/net/fabricmc/yarn/maven-metadata.xml) | Huge XML listing published **Yarn** builds; search for your game version string (e.g. `1.21.11`). |
| **Game version list (Fabric meta)** | [meta.fabricmc.net/v2/versions/game](https://meta.fabricmc.net/v2/versions/game) | JSON of Minecraft versions Fabric’s tooling knows about (used by installers/tools). |
| **Fabric API on Maven** | [fabric-api on Maven](https://maven.fabricmc.net/net/fabricmc/fabric-api/fabric-api/) | See which **`fabric-api`** versions exist; suffix often includes MC version (e.g. `...+1.21.11`). |

**Practical workflow:** open the **develop** page, use the **template/mod generator** if you’re starting fresh, or copy version triples from a **known working** `gradle.properties` (like MathQuest’s) and adjust when upgrading.

---

## 8. Who maintains what?

| Piece | Who maintains it | Notes |
|-------|------------------|--------|
| **Minecraft** (the game) | **Mojang** (Microsoft) | Ships clients/servers; publishes **version manifests** and, for many versions, **Mojang mappings** (not guaranteed for every future version). |
| **Fabric Loader, Loom, Yarn, installer** | **Fabric team** + contributors | Open source; [GitHub FabricMC](https://github.com/FabricMC). |
| **Fabric API** | **Fabric team** (separate project) | Adds APIs on top of Loader; version strings often end with `+1.xx.xx` for the MC version. |
| **Your mod (e.g. MathQuest)** | **You** | Your Java code + `fabric.mod.json` + Gradle project. |

Mojang does **not** ship Fabric. Fabric is a **third-party** modding stack built *on top of* what Mojang releases, within Mojang’s rules for modding.

---

## 9. Concepts that trip up newcomers

### Mappings (Yarn vs Mojang)

The real game code uses **obfuscated** names. **Mappings** translate those to names developers use in source.

- **Yarn** — community mappings published under the Fabric ecosystem (`net.fabricmc:yarn:...`).
- **Mojang official mappings** — when Mojang publishes them, Loom can use `officialMojangMappings()` (wording may vary slightly by Loom version).

If **no** Yarn build and **no** Mojang mappings exist for a brand-new Minecraft version, **you cannot complete a normal Loom setup** until one of those appears — that’s a toolchain gap, not something you fix with more Gradle flags alone.

### Why fabricmc.net/develop can list a Minecraft version before you can build

The **[Fabric develop / template](https://fabricmc.net/develop/)** page lets you pick a **Minecraft version** and prints **recommended** `minecraft_version`, **Fabric Loader**, **Loom**, and **Fabric API** for `gradle.properties`. Those recommendations are real for Loader, Loom plugin, and Fabric API — they are published on Maven.

**Mappings are separate.** Loom still needs either **Yarn** (`net.fabricmc:yarn:…`) or **Mojang’s** `client_mappings` / `server_mappings` in the version’s package JSON. The template does **not** guarantee Yarn exists on Maven yet, and Mojang does **not** always ship mapping downloads for every release. So you can fill in every line from the website and still get *Could not find net.fabricmc:yarn:…* or *Failed to find official mojang mappings* until the Fabric team publishes Yarn and/or Mojang publishes mappings.

### How to check if a Minecraft version is “ready” (three checks)

Use these when you want to know if **26.x** (or any version) is buildable yet — **without** changing your committed `gradle.properties`.

**1 — Yarn (Fabric)**

- **API:** `https://meta.fabricmc.net/v2/versions/yarn` — parse JSON and look for objects with `"gameVersion":"26.1.1"` (or your target). If the list is empty, **no Yarn** is registered for that game version yet.
- **Maven (heavy):** `https://maven.fabricmc.net/net/fabricmc/yarn/maven-metadata.xml` — search for your version string in `<version>` entries.

**Quick one-liner (macOS/Linux):**

```bash
curl -sL "https://meta.fabricmc.net/v2/versions/yarn" | grep -q '"gameVersion":"26.1.1"' && echo "Yarn: entries may exist (verify with jq/python)" || echo "Yarn: no 26.1.1 in meta yet"
```

**2 — Mojang official mappings**

- Open **`https://piston-meta.mojang.com/mc/game/version_manifest_v2.json`**, find your Minecraft version’s **`url`** (the per-version JSON URL **changes** when Mojang republishes the package — always follow `url` from the manifest, don’t hardcode an old hash).
- Fetch that JSON. Under **`downloads`**, check for **`client_mappings`** and **`server_mappings`**. If both are missing, Loom cannot use Mojang’s official mappings for that version (until Mojang adds them, if ever).

**3 — Ground truth (Gradle / Loom)**

The definitive test is resolving dependencies with **the same** `minecraft_version` / `yarn_mappings` you would put in `gradle.properties`. You can **override** properties for one command without editing files:

```bash
cd mathquest
./gradlew help --no-daemon \
  -Pminecraft_version=26.1.1 \
  -Pyarn_mappings=26.1.1+build.1 \
  -Ploader_version=0.18.6 \
  -Pfabric_version=0.145.4+26.1.1
```

Use a `yarn_mappings` string that appears in the Yarn meta API when it exists (e.g. `26.1.1+build.3`). If Yarn is missing, configuration fails with a **could not find net.fabricmc:yarn** error. Newer Minecraft may also require **JDK 25** to run Gradle/Loom — if you see a Java version error, fix the JDK first, then interpret mapping errors.

**Daily check:** run check **1** (and **2** if you rely on Mojang mappings) in a cron job or bookmark the URLs; only run **3** when **1** or **2** starts succeeding.

**Example snapshot (re-run these yourself; dates go stale):** On **2026-04-08**, check **1** reported **0** Yarn rows for `gameVersion` **26.1.1**; check **2** on the live **26.1.1** package had **no** `client_mappings` / `server_mappings`; check **3** (`./gradlew help` with `-Pminecraft_version=26.1.1` and the same Loader/Fabric API as the template, JDK **25**) failed with **Could not find net.fabricmc:yarn:26.1.1+build.1** — i.e. mappings still not available for a normal Yarn-based `build.gradle` like MathQuest’s.

### Java version

Minecraft and Gradle each have **Java version** requirements. Newer Minecraft may require **JDK 25** to *run the tooling*, while your mod might still **compile** with an older `--release` target — your project’s `build.gradle` and Fabric docs define that. MathQuest’s `docs/OVERVIEW.md` tracks what this repo actually uses.

### `fabric.mod.json`

Like a **`package.json`** manifest: mod id, version, entrypoints, dependency ranges on `minecraft`, `fabricloader`, `java`, etc. Gradle often **expands** `${version}` from `gradle.properties` at build time.

---

## 10. How this doc relates to MathQuest

- **`docs/OVERVIEW.md`** — deep reference for *this* codebase (files, behavior, deploy).
- **`gradle.properties`** — exact pinned versions for MathQuest’s current target Minecraft.
- **`versions/26.1.1/`** — saved snapshots for a **future** Minecraft line when mappings/tooling allow building; see `versions/26.1.1/README.md`.

If you only read one external page after this, make it **[fabricmc.net/develop](https://fabricmc.net/develop/)** — it’s the hub for “how Fabric development works today.”
