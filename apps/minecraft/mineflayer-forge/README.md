**Mineflayer + Forge 1.20.1 (FML3)**

This client adds Forge 47's modern FML3 login negotiation to Mineflayer 4.25.0 for Minecraft 1.20.1. It can join the tested Forge 47.4.2 Ice and Fire server as a stationary Mineflayer bot. When an authorized human controller is configured, it can also follow that player or collect and deliver a requested number of vanilla logs. Mod entities, items, weapons, menus, recipes, commands, and custom payloads remain unsupported data.

The implementation is independent of MathQuest. Its handshake and packet adapters live only in this `mineflayer-forge` app; MathQuest does not need to be installed for the bot to work. The earlier MathQuest 1.24.2 change that makes MathQuest's own channel optional remains a separate server-mod compatibility choice. It is not used by this client implementation, and MathQuest was not present in the Ice and Fire verification server.

## What the Forge layer implements
- Appends Forge's `\0FML3\0` marker to the handshake hostname.
- Handles `fml:loginwrapper` / `fml:handshake` login-plugin requests.
- Reads Forge mod metadata and the server's mod, channel, and registry lists.
- Replies with the client's implemented mod identities and compatible channel versions.
- Acknowledges Forge registry and configuration synchronization packets so login can finish.
- Suppresses ModernFix's optional smart-ingredient capability because Mineflayer uses the vanilla recipe wire format.
- Consumes Forge registry-driven recipe and command declarations as opaque packets instead of partially decoding them with vanilla packet schemas.

This is a best-effort vanilla-subset Forge client, not a Java mod loader. It does not apply Forge registry snapshots to Mineflayer's static data, implement mod network messages, or teach Mineflayer the meaning of modded blocks and entities. Vanilla behavior worked in the verified pack because its vanilla protocol remains compatible; another modpack can still require an additional packet or channel adapter.

## Safety boundary
- Installing dependencies and running `npm test` do not contact a Minecraft server.
- `npm run ping` and `npm run bot` make a network connection only when you invoke them.
- Without `--controller`, the bot configures no command-driven movement, mining, or inventory actions.
- With `--controller NAME`, only that player can issue the small set of addressed commands documented below. The follow and log commands move the bot, and the log command deliberately changes the world by breaking nearby vanilla log blocks.
- Task pathfinding is configured not to dig unrelated terrain, build scaffold towers, or parkour. The log action manually breaks only `*_log` blocks that have nearby `*_leaves`, but it can still mistake player-placed logs beside leaves for a natural tree. Supervise it in a known area.
- A smoke timeout disconnects the client; it does not send a Minecraft chat/server command.
- These tools do not start, stop, restart, signal, or administer the Forge server process.

Do not run the ping or bot commands against an in-progress game until making that connection is acceptable. Development and unit testing require no server access.

## Setup
Node 20 is supported. From this directory:

```sh
npm ci
npm test
```

Mineflayer is pinned to `4.25.0`. `minecraft-protocol` is a direct dependency because the ping command uses its status API; it is pinned to `1.54.0`, the newest release in Mineflayer 4.25.0's supported range that supports Node 20. `mineflayer-pathfinder` is pinned to `2.4.5` for the explicitly authorized movement tasks.

## Manual Forge smoke test with SkulkScraper
This connection-only test proves that the real SkulkScraper Microsoft account can complete Forge negotiation, appear in the world, remain connected, and disconnect cleanly. Because it omits `--controller`, the bot remains stationary during this test.

### 1. Protect the Microsoft account
Do not put the Microsoft email address or password in this repository, a command-line flag, an environment variable, or a script. The Microsoft device-code flow does not need the password. It opens a browser sign-in and stores a reusable token under the gitignored `.profiles/` directory.

Make sure the SkulkScraper account:
- owns Minecraft Java Edition;
- is allowed through the server whitelist, if the whitelist is enabled; and
- is not simultaneously logged into this server from another Minecraft client.

Use a different Minecraft account for the human player who observes SkulkScraper in-game.

### 2. Start the real Forge server
Start the backed-up Ice and Fire Forge server exactly as you normally do. Do not change its mods, world, port, online-mode setting, or Forge version for this test. Wait until the server console reports that startup is complete, normally with a line containing `Done`.

Leave that server console open so you can see the SkulkScraper join and disconnect messages.

### 3. Prepare the Mineflayer app
Open a separate Terminal window and run:

```sh
cd /Users/randytrue/.codex/worktrees/0013/fof-mono/apps/minecraft/mineflayer-forge
npm ci
npm test
```

Expected result: all 20 tests pass. These commands do not contact the Minecraft server.

### 4. Confirm the server is reachable
With the Forge server running on the default local port, run:

```sh
npm run ping -- --host 127.0.0.1 --port 25565 --ping-timeout-ms 5000
```

Expected result: the command prints the server status JSON. This confirms reachability only; it does not exercise the Forge login handshake.

### 5. Run the five-minute SkulkScraper smoke test
Run:

```sh
npm run bot -- \
  --host 127.0.0.1 \
  --port 25565 \
  --version 1.20.1 \
  --auth microsoft \
  --username SkulkScraper \
  --profiles-folder ./.profiles/skulk-scraper \
  --smoke-timeout-ms 300000
```

On the first run, Mineflayer prints a Microsoft device-code sign-in instruction. Open the shown Microsoft URL, enter the shown one-time code, and select the Microsoft account whose Minecraft Java profile is named `SkulkScraper`. Do not enter the account password in the Terminal. Later runs should reuse the token cached in `.profiles/skulk-scraper/`.

The Mineflayer Terminal should reach lines equivalent to:

```text
[fml3] server advertised ... mod records
[fml3] accepted ... mods, advertised ... channels, ... synced registries
[bot] login accepted as SkulkScraper
[bot] spawned; remaining stationary (no controller configured)
```

While the five-minute timer is running:

1. Join the server with the separate human account.
2. Confirm `SkulkScraper` appears in the player list and in the world.
3. Confirm the bot remains connected and stationary.
4. Watch the Forge console for errors, kicks, or repeated packet warnings.

After five minutes, the bot should disconnect itself and the command should exit successfully. The final bot lines should say that a smoke-timeout disconnect was requested and the connection ended. The Forge console should report that SkulkScraper left the game without a server crash.

The smoke test passes only if all of these are true:

- FML3 negotiation finishes without a channel-mismatch kick.
- Mineflayer reports `spawned`.
- The human player sees SkulkScraper in the world.
- The connection stays healthy for the full five minutes.
- The timed disconnect is clean and the command exits with status 0.

### 6. Optional longer observation
After the five-minute test passes, run the same command with `--smoke-timeout-ms 0` to leave SkulkScraper connected. Press `Control-C` in the Mineflayer Terminal when finished. Without `--controller`, the bot remains stationary.

## Follow and 10-log in-game playtests

This is a constrained chat-command controller, not a general AI prompt interface. Commands must address `SkulkScraper` by name, and the bot accepts them only from the Minecraft username supplied with `--controller`.

### 1. Start the server and human player

1. Start the backed-up Forge server normally and wait for its console to report `Done`.
2. Join the game using the separate Minecraft account that will control SkulkScraper.
3. Make a note of that account's exact Java profile name. The examples below call it `YOUR_HUMAN_MINECRAFT_USERNAME`.

Do not use the SkulkScraper Microsoft account as the controller account, and do not run SkulkScraper in another Minecraft client at the same time.

### 2. Start command-enabled SkulkScraper

In a separate Terminal window, run:

```sh
cd /Users/randytrue/.codex/worktrees/0013/fof-mono/apps/minecraft/mineflayer-forge
npm run bot -- \
  --host 127.0.0.1 \
  --port 25565 \
  --version 1.20.1 \
  --auth microsoft \
  --username SkulkScraper \
  --controller rjcomp \
  --profiles-folder ./.profiles/skulk-scraper \
  --smoke-timeout-ms 0
```

Replace `YOUR_HUMAN_MINECRAFT_USERNAME` with the controlling player's Java profile name. Do not put either account's password in the command. The existing Microsoft device-code token cache should be reused.

Wait until the Terminal says that SkulkScraper spawned and commands are enabled. In the game, move your human player close enough to see SkulkScraper. You can type `SkulkScraper help` to see the supported commands.

### 3. Test follow and stop

1. Stand near SkulkScraper and type this exact message in Minecraft chat: `SkulkScraper follow me`
2. Confirm SkulkScraper replies that it is following you.
3. Walk about 10 to 20 blocks across ordinary, safe ground. Confirm SkulkScraper follows and stops within roughly two blocks of you.
4. Type: `SkulkScraper stop`
5. Confirm SkulkScraper replies `Stopped.`
6. Walk another 10 to 20 blocks away. Confirm SkulkScraper stays where it stopped.

`SkulkScraper stop` also cancels an active log-collection task. It does not disconnect the bot.

### 4. Prepare the 10-log test

1. Bring SkulkScraper to an open area with at least 10 reachable vanilla tree logs within 48 blocks. Start with ordinary oak, birch, spruce, jungle, acacia, cherry, dark oak, or mangrove `*_log` blocks; modded trees and crimson/warped stems are not understood.
2. Put an axe in SkulkScraper's inventory before issuing the command. The bot will refuse to start if it cannot find an item whose name ends in `_axe`.
3. Keep empty inventory space on your human player so you can pick up the delivered logs.
4. Stand near SkulkScraper and remain in the loaded area while it works.

### 5. Test collect, return, and delivery

1. Type this exact message in Minecraft chat: `SkulkScraper chop 10 logs and bring them back to me`
2. Confirm SkulkScraper announces that it is starting the 10-log task.
3. Supervise it as it walks to nearby trees, breaks only log blocks, and collects the drops. It should report progress at 5/10 and 10/10.
4. Stay in a reachable place. After collecting 10 new raw logs, SkulkScraper should return to within about three blocks of you.
5. Confirm it announces that it is dropping 10 logs, then reports `Task complete: delivered 10 logs`.
6. The logs are tossed onto the ground rather than inserted directly into your inventory. Walk over them if you do not pick them up immediately, then confirm you received exactly 10 raw logs.
7. When finished, press `Control-C` in the Mineflayer Terminal to disconnect SkulkScraper cleanly. This does not stop the Forge server.

The task fails with an explanatory chat message if the axe is missing, no qualifying tree is found, a route or pickup repeatedly fails, the controller is no longer visible for the return, or the requested logs cannot be delivered. A failed task can leave already collected logs in SkulkScraper's inventory. Supported log counts are 1 through 64; the parser does not yet understand phrases such as “three stacks.”

## Verified compatibility
On 2026-07-15, the client completed FML3 negotiation, logged in, emitted Mineflayer's `spawn` event, remained connected for a 15-second smoke window, and disconnected cleanly with exit code 0. The disposable server used Forge 47.4.2, Minecraft 1.20.1, a fresh world, an offline-mode test account, and copies of the stopped game's active root-level mod jars:

- Citadel 2.6.3
- Ice and Fire 2.1.13 beta 5
- ModernFix 5.27.25
- FerriteCore 6.0.1
- Embeddium 0.3.31
- Player Locator Plus Reforged 1.0.1

MathQuest was not installed. The original backed-up game world and stopped server folder were not modified by this verification.

On the same disposable Forge 47.4.2 server, the command controller was verified end to end: SkulkScraper followed the authorized player, stopped and remained at the exact same coordinates after the player moved away, collected 10 oak logs, returned, dropped exactly 10 logs, and reported task completion. The temporary action bot, controller, and disposable server were then shut down cleanly. The live game server on port 25565 was not contacted or signaled during this test.

## Status ping
The status command performs only a Minecraft server-list ping and prints the JSON response:

```sh
npm run ping
npm run ping -- --host 127.0.0.1 --port 25565 --ping-timeout-ms 5000
```

## Stationary bot
Offline authentication is the explicit default. It supplies only the configured username and is appropriate only when the server permits offline-mode clients:

```sh
npm run bot -- --username MineflayerBot --smoke-timeout-ms 15000
```

The smoke timeout caps the whole connection attempt. A timeout of `0` (the default) leaves the client running until it disconnects or receives `SIGINT`/`SIGTERM`.

Microsoft authentication must be selected explicitly:

```sh
npm run bot -- --auth microsoft --username account-profile --smoke-timeout-ms 15000
```

Microsoft device-code credentials are cached under `.profiles/` by default. That directory is separate from the normal Minecraft profile directory and is ignored by git. Treat it as sensitive account material. `--profiles-folder` can point at another private location.

## Configuration
Command-line flags take precedence over environment variables.

| Setting | Environment variable | Flag | Default |
| --- | --- | --- | --- |
| Host | `MINEFLAYER_HOST` | `--host` | `127.0.0.1` |
| Port | `MINEFLAYER_PORT` | `--port` | `25565` |
| Protocol version | `MINEFLAYER_VERSION` | `--version` | `1.20.1` |
| Username/profile identifier | `MINEFLAYER_USERNAME` | `--username` | `MineflayerBot` |
| Authentication | `MINEFLAYER_AUTH` | `--auth` | `offline` |
| Microsoft profile cache | `MINEFLAYER_PROFILES_FOLDER` | `--profiles-folder` | `.profiles/` |
| Authorized controller username | `MINEFLAYER_CONTROLLER` | `--controller` | disabled |
| Bot smoke timeout | `MINEFLAYER_SMOKE_TIMEOUT_MS` | `--smoke-timeout-ms` | `0` |
| Status ping timeout | `MINEFLAYER_PING_TIMEOUT_MS` | `--ping-timeout-ms` | `5000` |

Valid authentication values are only `offline` and `microsoft`; invalid or ambiguous values are rejected instead of silently choosing an account flow.

## Tests
```sh
npm test
```

The 20 tests exercise configuration precedence and validation, controller authorization and command parsing, safe pathfinding configuration, exact 10-log collection and delivery, auth profile isolation, the finite smoke-timeout disconnect path, FML3 framing and negotiation, capability filtering, truncated-packet rejection, and Forge packet adapters. They do not open a network socket.
