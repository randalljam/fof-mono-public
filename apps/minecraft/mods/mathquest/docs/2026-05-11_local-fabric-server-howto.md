# Running MathQuest on a local Fabric dedicated server

**Date:** 2026-05-11
**Task:** P1-1 (server-conversion plan)
**Purpose:** Sanity-check that the current MathQuest jar loads and runs on a real
Fabric dedicated server before making any code changes for multiplayer.

> **Already set up? Skip this doc.** The steady-state "I've already done this once,
> what do I run today?" quick-start lives in `OVERVIEW.md` under
> **Running the dedicated server**. This dated doc walks through the **initial
> one-time setup** (Fabric installer, EULA, Fabric API jar download, mods folder
> creation) plus the historical 1.2.2 upgrade transcript. It also predates the
> reorg that moved the repo from `mathquest/` to `minecraft/mods/mathquest/` —
> any path of the form `mathquest/...` in the steps below now lives at
> `minecraft/mods/mathquest/...`, and `./build-and-deploy.sh` has been
> superseded by `./minecraft/mods/build-and-deploy.py mathquest` (the legacy
> shell script still works as a fallback).

---

## What you need

- **Java 25** — the same JDK used to build the `fabric-26.1.2` target. Minecraft **26.1.2
  dedicated server** bytecode needs Java **25** (class file **69**). If Terminal’s default
  `java` is **21** (class files up to **65**), the server will crash with
  `UnsupportedClassVersionError`. Use the **Java 25** binary explicitly (see below), not
  plain `java`, unless `java -version` already reports **25**.
- **The Fabric Installer** — download `fabric-installer-1.0.3.jar` (or latest) from
  https://fabricmc.net/use/installer/
- **Fabric API jar** — version `0.146.1+26.1.2` (matching the mod's dependency).
  Download from Modrinth: search for "Fabric API" and pick the build for MC 26.1.2.
- **The MathQuest jar** — built by `./build-and-deploy.sh`. The output jar lives at
  `mathquest/targets/fabric-26.1.2/build/libs/mathquest-fabric-1.2.2-mc26.1.2.jar`.

On macOS with Homebrew, Java 25 is often:

- **Intel / `/usr/local` Homebrew:** `/usr/local/opt/openjdk/bin/java` — matches
  `JAVA25_HOME` in `mathquest/build-and-deploy.sh`.
- **Apple Silicon / `/opt/homebrew`:** `/opt/homebrew/opt/openjdk/bin/java` (or
  `openjdk@25` if you use that formula).

Confirm before you run the server:

```bash
/usr/local/opt/openjdk/bin/java -version
```

You want **`openjdk version "25`** in the first line of output — **not** version 21.

---

## Step-by-step

### 1. Build MathQuest

From the repo root:

```bash
cd mathquest
./build-and-deploy.sh
```

This builds the jar and copies it into your client mods folder. The jar you need for the
server is at:

```
targets/fabric-26.1.2/build/libs/mathquest-fabric-1.2.2-mc26.1.2.jar
```

### 2. Create a server directory

Create a folder named `mathquest-server` **next to** the `kid-games` repo — same parent
directory as the repo root, **not** inside the repo — so world files, logs, and server
config never land in git.

Example: if your clone is `~/Documents/Code/kid-games`, use `~/Documents/Code/mathquest-server`:

```bash
mkdir -p ~/Documents/Code/mathquest-server
cd ~/Documents/Code/mathquest-server
```

From this directory, the MathQuest repo is the sibling folder `kid-games` (see step 5).

### 3. Install Fabric server

Run the Fabric Installer in server mode. Prefer the **Java 25** binary (same as for the
server — see the block above); the installer usually runs fine on 21, but one JDK for
everything avoids confusion.

The installer is just a normal JAR you run with `java -jar`; it does not need to live
in `mods/` for anything to load it as a mod. If you keep it next to your client mods,
on macOS a typical path is:

```bash
/usr/local/opt/openjdk/bin/java -jar "$HOME/Library/Application Support/minecraft/mods/fabric-installer-1.0.3.jar" server \
  -mcversion 26.1.2 \
  -loader 0.18.5 \
  -downloadMinecraft
```

(Use `/opt/homebrew/opt/openjdk/bin/java` instead if that is where Homebrew put Java 25.)

The quotes are required because of the space in `Application Support`. If your copy of
the installer lives somewhere else, substitute that path for the `java -jar` argument.

This downloads the Minecraft server jar and creates `fabric-server-launch.jar` plus a
`libraries/` directory.

### 4. Accept the EULA

Start the server once — it will create `eula.txt` and stop. **Must use Java 25** (see
top of this doc); plain `java` is often 21 and will crash.

```bash
/usr/local/opt/openjdk/bin/java -Xmx2G -jar fabric-server-launch.jar nogui
```

Edit `eula.txt` and change `eula=false` to `eula=true`:

```bash
sed -i '' 's/eula=false/eula=true/' eula.txt
```

### 5. Copy mods

Create a `mods/` folder and copy both jars into it:

```bash
mkdir -p mods
cp ../kid-games/mathquest/targets/fabric-26.1.2/build/libs/mathquest-fabric-1.2.2-mc26.1.2.jar mods/
```

Manually copy fabric-api-0.147.0+26.1.2.jar to mathquest-server/mods

If your server directory is not a sibling of `kid-games`, use the full path to the jar
under your clone instead of `../kid-games/...`.

Adjust paths as needed. The key is that both MathQuest and Fabric API jars end up in
`mods/`.

### 6. Start the server

```bash
/usr/local/opt/openjdk/bin/java -Xmx2G -jar fabric-server-launch.jar nogui
```

Watch the console output for:

- `[MathQuest] Loaded! Mode: popup, quiz every 30 seconds, 5 problems, range 0-9` —
  confirms the mod initialized and created `config/mathquest.json`.
- The world generating and the server reaching `Done!` without crashes.

### 7. Things to check and note

Once the server is running, leave that Terminal window alone (the server keeps running
there). You should eventually see a **`>`** prompt in that same window — that is the
**server console** (commands typed there are **not** chat; they run as the server).

#### Join from the Minecraft client (what to click)

**1. Client mods must match what the server loads.** Use the same machine and mods folder
you already use for MathQuest single-player:  
`~/Library/Application Support/minecraft/mods` should contain the **MathQuest** jar and
**Fabric API** for **26.1.2** (same lineup as in `mathquest-server/mods/`). If you update
one side, update the other before connecting.

**2. Launch the game** with your **Fabric** profile for **Minecraft 26.1.2** (the one you
used when you tested the Wandering Nerd in single-player). Click **Play**.

**3. Use Multiplayer, not Single-player.** From the main menu choose **Multiplayer**.  
This world is the **dedicated server** in `mathquest-server/` — it is **not** any
single-player world you already have.

**4. Connect to this machine.** Choose **Direct Connection** (quickest):

- **Server Address:** `localhost`  
  (equivalent: `127.0.0.1`. Default port is **25565**; you only need `:25565` on the end
  if you changed the server port in `server.properties`.)

Alternatively, **Add Server** with any server name you like and address `localhost`, then
join it.

**5. First-time “operator” if you want in-game commands.** Server-side **`/mathquest`**
commands require **permission level 2** (game master). Easiest: in the **server Terminal**
(at the **`>`** prompt), run **`op <YourMinecraftUsername>`** (exact Java Edition name,
case-sensitive). After that you can use **`/mathquest`** from inside the game. You can
still change modes from the **server console** without being op — see below.

**6. After you join.** You should spawn in the server’s **world** (the one the dedicated
server created). Watch the server Terminal: it usually logs when a player connects.

**7. Test the Wandering Nerd (NPC mode).** Popup timers are intentionally quiet on remote
clients for this build — see **Known expectations** below. For nerd flow, switch to NPC
mode, then wait / interact:

- **Option A — server console:** at the **`>`** prompt in the server Terminal, run  
  **`mathquest mode npc`** (no leading **`/`** in the dedicated-server console).
- **Option B — in-game:** if you **`op`**’d yourself, run **`/mathquest mode npc`** in
  chat.
- **Option C — config file:** edit **`mathquest-server/config/mathquest.json`**, set
  **`"quizMode"`** to **`"npc"`**, save, and **restart the server** (`stop`, then start
  again with step 6).

Then wait for the spawn interval (default 30 seconds), find the **Wandering Nerd** near
your player, **right-click** it, and run through a quiz like you did in single-player.

---

**Check these and report what happened:**

- Did the server start without errors? Note any warnings or exceptions in the console.
- Does `config/mathquest.json` exist in the server directory? Open it and confirm it
  has the expected default values (quiz mode "popup", interval 30, etc.).
- Using **Multiplayer** → **Direct Connection** to **`localhost`**, does the client join
  successfully?
- Once connected, after switching to **NPC** mode (command or config), does a
  Wandering Nerd spawn? Does the quiz offer open on right-click, and do results and
  rewards work?
- Check the server directory for:
  - `config/mathquest_data.db` — the SQLite database (may be created on the client
    side instead; note which machine has it)
  - `config/mathquest_sessions/*.json` — session export files (same note)

**Known expectations for this first run:**

- The **popup mode timer** should **not** fire on the client (the client checks for an
  integrated server and skips the timer on remote connections). This is correct behavior.
- The **K hotkey** (Control Panel) **does not open** on a remote dedicated-server
  connection (only in single-player / integrated server). Use **`mathquest …`** from the
  **server console** or **`/mathquest …`** in-game after **`op`**’ing yourself.
- **`/mathquest start` from the game chat** only works for **nerd spawns** when the
  **server** runs the command (you are **op** level 2+ so the server accepts it). The
  **client-only** `/mathquest start` path only has access to a **single-player /
  integrated** server, so on a **dedicated** server it cannot spawn nerds and used to
  show a misleading “single-player world” message — use **op** **`/mathquest start`**,
  or from the **server console** run **`mathquest start <exactPlayerName>`** (no `/`) in
  **NPC** mode.
- The **SQLite database and session JSON exports** currently write to the Fabric config
  dir. On a dedicated server, that's the server's config dir. On the client, it's the
  client's config dir. Note where files actually appear — this tells us whether
  persistence is running client-side or server-side (expected: client-side, since
  `QuizDatabase` and `SessionExporter` are called from the client's screen classes).

### 8. Stopping the server

Type `stop` at the server console prompt, or press Ctrl+C.

---

## Reporting back

After running through these steps, report:

1. Did the server start cleanly? Any errors or warnings?
2. Did a client connect successfully?
3. In NPC mode, did the Wandering Nerd spawn and the quiz flow work end-to-end?
4. Where did `mathquest_data.db` and session JSON files end up (server or client)?
5. Any unexpected behavior or crashes?

Failures here become inputs to P1-2 (audit code for singleplayer-only assumptions).

# version 1.2.2 - fixing "NPC spawning requires a singleplayer world"
_with 1.2.1 version, run commands from server prompt not in-game (client)_

Here is the distilled answer.

## Should you still rebuild and redeploy?

**Yes, if you want 1.2.2 on disk.** What you saw in the log matches **pre-1.2.2** behavior:

- **`mathquest start rjcomp`** printed **`Opening quiz for rjcomp...`** — on the old server code, **`start <player>`** always sent the **popup** payload, even in **NPC** mode.
- The **`Spawned Wandering Nerd...`** lines a bit later are very likely the **30-second auto-spawner**, not that `start` line doing the right thing for NPC.

After rebuild, **`mathquest start rjcomp`** in **NPC** mode should log **spawning the nerd** (and not treat console `start <player>` as popup-only).

## Version **1.2.2** (bumped for you)

Updated:

- `mathquest/gradle.properties` → **`mod_version=1.2.2`** (this drives **both** `fabric-26.1.2` and **`fabric-1.21.11`** jars).
- `mathquest/versions/26.1.1/gradle.properties` → **1.2.2** for consistency.
- `docs/OVERVIEW.md` — version line + a short **1.2.2 changes** bullet.
- `docs/2026-05-11_local-fabric-server-howto.md` — jar names now **`mathquest-fabric-1.2.2-mc26.1.2.jar`**.

The built file will be:

`mathquest/targets/fabric-26.1.2/build/libs/mathquest-fabric-1.2.2-mc26.1.2.jar`

## After `./build-and-deploy.sh`

- **Client:** script deploys to your launcher **`mods`** folder (as today).
- **Dedicated server:** copy that **same** new jar into **`mathquest-server/mods/`** (replace the old MathQuest jar). Keep Fabric API aligned with the client.
- **Restart** the dedicated server so it loads the new jar; **restart the client** (or relaunch) after the client jar updates.

## What changed in code (1.2.2)

1. **`MathQuestServerCommands`** — **`/mathquest start <player>`** and **`/mathquest start all`** respect **quiz mode**: **NPC** → **force-spawn** nerd(s); **popup** → **`OpenQuizPayload`** (unchanged intent for popup).
2. **`MathQuestCommands`** (client) + **26.1.2 target copy** — clearer error when **`/mathquest start`** can’t spawn on a **dedicated** server (no more vague “single-player world” only).
3. **Docs** — `OVERVIEW.md` server-command section + local-server howto jar paths; howto notes about client vs server **`start`**.

I did **not** change historical **`debug-threads`** transcripts.

When you’re ready: run **`cd mathquest && ./build-and-deploy.sh`**, copy the new jar to **`mathquest-server/mods/`**, restart the server, then run the playtest check if you want end-to-end confirmation.

# Explaining the Fabric Server
Here is the short version.

## What the “server directory” is

It is **any empty folder you choose** on disk that will hold **only** the dedicated server: launcher scripts, `fabric-server-launch.jar`, `mods/`, world files, `eula.txt`, server `config/`, and logs. The how-to suggests something like `~/mathquest-server` **outside the repo** so server junk does not mix with your git checkout.

It is **not** your normal Minecraft folder (`~/Library/Application Support/minecraft/...`) and **not** your Fabric profile inside the launcher.

## Is “install the Minecraft server” different from the launcher Fabric install?

**Yes.** Those are two different programs:

| | **Launcher (what you already did)** | **Dedicated server (steps 2–6)** |
|--|-------------------------------------|-----------------------------------|
| **What it is** | Minecraft **client** + Fabric Loader for playing the game with graphics | **Headless** Minecraft **server** JAR + Fabric, run from Terminal with `java -jar ...` |
| **Where it lives** | App Support `minecraft`, launcher profiles, client `mods` | The folder **you** create (e.g. `~/mathquest-server`) |
| **How Fabric gets there** | Installer / profile / mods you already use | **Fabric Installer in `server` mode** in that folder (`-mcversion 26.1.2` etc.), which downloads the **server** artifacts into **that** folder |

So you are **not** re-doing the launcher setup. You are adding a **second** install: a small server “instance” next to it, then putting **MathQuest + Fabric API** in **that** folder’s `mods/`.

## Do you start from step 2?

**Yes.** Step 1 was “build MathQuest”; you already built, deployed to the client, and smoke-tested in single-player. **Start at step 2** (create the server directory) and continue through the doc: Fabric server installer → EULA → copy **both** jars into **the server’s** `mods/` (not only the client’s) → run `fabric-server-launch.jar`.

Your client can keep using the same jar you already copied to the client `mods` folder; for the server you still **copy (or reuse the path to) the same built jar** into **the new** `~/mathquest-server/mods/` (or whatever folder you picked), plus the matching **Fabric API** jar there, as step 5 says.

**Summary:** server directory = **new folder for the dedicated server**; **yes**, it is **different** from launcher Fabric; **yes**, follow **from step 2 onward** now that the build and client test are done.
