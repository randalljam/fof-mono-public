file: apps/minecraft/mods/mathquest/docs/2026-06-29_local-forge-server-howto.md
title: Running MathQuest on a local Forge dedicated server
last-updated: 2026-06-29_1600
ai: Cursor - Composer 2.5 Fast

**Date:** 2026-06-29
**Purpose:** One-time setup for a Forge 1.20.1 dedicated server that runs MathQuest alongside the existing Fabric 26.1.2 server at `~/Documents/Code/mathquest-server/`.

> **Already set up?** Skip to **Steady-state workflow** below. The quick-start for both servers lives in [`OVERVIEW.md`](OVERVIEW.md) under **Running the dedicated server**.

---

## What you need

- **Java 17** — Forge 1.20.1 / ForgeGradle 6 requires Java 17. Same JDK the `forge-1.20.1` build uses. On macOS with Temurin or Homebrew:
  - `/Library/Java/JavaVirtualMachines/temurin-17.jdk/Contents/Home/bin/java`
  - or `/usr/local/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin/java`
- **Forge installer** — `forge-1.20.1-47.4.0-installer.jar` from https://files.minecraftforge.net/net/minecraftforge/forge/index_1.20.1.html (pick **47.4.0**, **Installer**).
- **MathQuest Forge jar** — built by `./apps/minecraft/mods/build-and-deploy.py mathquest --target forge-1.20.1`. Deploys to `~/Documents/Code/mathquest-server-forge/mods/` when that folder exists.
- **Prism client** — instance **Forge 1.20.1 MathQuest** (same loader/version as the server).

Confirm Java 17 before proceeding:

```bash
/Library/Java/JavaVirtualMachines/temurin-17.jdk/Contents/Home/bin/java -version
```

You want **`openjdk version "17`** in the output — not 21 or 25.

**No Fabric API jar.** Forge bundles its own loader; the server `mods/` folder needs only the MathQuest Forge jar.

---

## Step-by-step (one-time setup)

### 1. Create the Forge server directory

Keep the existing Fabric server untouched. Create a **sibling** folder:

```bash
mkdir -p ~/Documents/Code/mathquest-server-forge
cd ~/Documents/Code/mathquest-server-forge
mkdir -p mods
```

This folder holds its own world, config, logs, and EULA — separate from `~/Documents/Code/mathquest-server/`.

### 2. Install Forge server

Download `forge-1.20.1-47.4.0-installer.jar` into the new folder (or pass the full path to `java -jar`). Run the installer in **server** mode:

```bash
cd ~/Documents/Code/mathquest-server-forge
/Library/Java/JavaVirtualMachines/temurin-17.jdk/Contents/Home/bin/java \
  -jar forge-1.20.1-47.4.0-installer.jar --installServer
```

This downloads Minecraft server artifacts and creates `run.sh`, `user_jvm_args.txt`, and a `libraries/` tree.

### 3. Accept the EULA

Start once to generate `eula.txt`:

```bash
./run.sh nogui
```

Stop with Ctrl+C when it exits (EULA not accepted). Edit `eula.txt`:

```bash
sed -i '' 's/eula=false/eula=true/' eula.txt
```

### 4. Deploy MathQuest

From the repo root:

```bash
./apps/minecraft/mods/build-and-deploy.py mathquest --target forge-1.20.1
```

This builds **1.20.0** (or current `mod_version`), copies the jar into Prism **Forge 1.20.1 MathQuest**, and — when `~/Documents/Code/mathquest-server-forge/mods` exists — into that server's `mods/` folder. Only the MathQuest jar goes there; no Fabric API.

If the Forge server folder did not exist yet, create `mods/` and re-run deploy, or copy manually from:

```
apps/minecraft/mods/mathquest/forge/targets/forge-1.20.1/build/libs/mathquest-forge-<version>-mc1.20.1-all.jar
```

(drop the `-all` suffix when copying; deploy script strips it automatically).

### 5. Start the server

```bash
cd ~/Documents/Code/mathquest-server-forge
./run.sh nogui
```

Watch for:

- `[MathQuest]` log lines — mod initialized, config loaded.
- `Done!` — server ready on port **25565** (default).

The **`>`** prompt is the **server console** (no leading `/` on commands).

### 6. Connect from the client

1. Launch Prism instance **Forge 1.20.1 MathQuest** (must match server loader/version).
2. Main menu → **Multiplayer** → **Direct Connection**.
3. Server address: **`localhost`** (or `127.0.0.1`).
4. Join the server world (not single-player).

**First-time operator:** at the server console `>` prompt, run `op <YourMinecraftUsername>` (exact Java Edition name). Then `/mathquest` works from in-game chat; or run `mathquest …` (no `/`) at the console.

### 7. HTTP control panel (Forge core routes)

**Live config file:** When `sharedDataDir` points at `~/Documents/Code/mathquest-server/config` (default on this setup), MathQuest reads and writes **`~/Documents/Code/mathquest-server/config/mathquest.json`**, not the copy under `mathquest-server-forge/config/`. A sidecar note lives next to the bootstrap file: `mathquest-server-forge/config/minecraft_LIVE-CONFIG-JSON-IS-IN-MATHQUEST-SERVER-FOLDER.txt`.

With `controlPanelEnabled: true` in config (default), open in a browser while the server is running:

```
http://127.0.0.1:8765/
```

**Forge has core routes only:** dashboard, `/api/status`, `/api/config`, `/api/spawn`, `/api/open`, `/api/vanish`. Quest, terrain-map, and mob-spawn admin pages are **Fabric-only** (not registered on Forge).

**Single-player alternative:** open any Forge single-player world; the integrated server starts the same control panel at `http://127.0.0.1:8765/` without running a dedicated server.

### 8. Stopping the server

Type `stop` at the `>` prompt, or Ctrl+C the Terminal window.

---

## Steady-state workflow

**Start Forge server:**

```bash
cd ~/Documents/Code/mathquest-server-forge
./run.sh nogui
```

**Deploy a fresh MathQuest Forge jar:**

```bash
./apps/minecraft/mods/build-and-deploy.py mathquest --target forge-1.20.1
```

Restart the server after deploy (`stop`, then `./run.sh nogui` again).

**Connect:** Prism **Forge 1.20.1 MathQuest** → Multiplayer → Direct Connection → `localhost`.

---

## Two servers side by side

| | **Fabric 26.1.2** | **Forge 1.20.1** |
|--|-------------------|------------------|
| **Folder** | `~/Documents/Code/mathquest-server` | `~/Documents/Code/mathquest-server-forge` |
| **Java** | 25 (`/usr/local/opt/openjdk/bin/java`) | 17 (see above) |
| **Start** | `java -jar fabric-server-launch.jar nogui` | `./run.sh nogui` |
| **Extra mods** | Fabric API jar | *(none)* |
| **Prism client** | Fabric 26.1.2 MathQuest | Forge 1.20.1 MathQuest |
| **Deploy command** | `./apps/minecraft/mods/build-and-deploy.py mathquest` | `… mathquest --target forge-1.20.1` |

Only one server can bind port 25565 at a time. Stop one before starting the other, or change `server-port` in `server.properties` on one of them.

Fabric setup (historical): [`2026-05-11_local-fabric-server-howto.md`](2026-05-11_local-fabric-server-howto.md).
