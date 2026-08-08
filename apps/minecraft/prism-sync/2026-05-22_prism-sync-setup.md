# Prism Sync Setup Plan

This is the setup plan for getting the family Macs ready for remote administration and repeatable Prism Launcher instance sync.

## Recommendation

Use Randy's laptop, **host4**, as the master Prism Launcher machine. Build and test the official family Minecraft instances there, then push selected instance folders to the other Macs with `apps/minecraft/prism-sync/prism-sync.sh`.

For `host1`, do the setup in this order:

1. [x] Finish macOS updates and record the version in `computer-info.md`.
2. [x] Install Prism Launcher on `host1`.
3. [x] Launch Prism once on `host1`, then quit it.
4. [x] Enable remote access on `host1`.
5. [x] Confirm SSH from `host4` to `host1`.
6. [x] Edit the Prism sync script's instance list.
7. [ ] Run a preview Prism sync.
8. [ ] Confirm the prompt to run the real Prism sync.
9. [ ] Open Prism on `host1` and confirm the instances appear.

Yes, install Prism on `host1` before running the sync script. The script can create the target `instances` folder, but launching Prism once first is cleaner because Prism initializes its own data layout and permissions.

## [x] Step 1: Update And Name `host1`

On `host1`:

1. Open **System Settings**.
2. Go to **General -> Software Update**.
3. Confirm it is fully updated.
4. Go to **General -> About**.
5. Confirm or set the computer name to `host1`.
6. Write down the macOS version and computer name in `computer-info.md`.

Current known info:

- **host1:** macOS Tahoe 26.5, updated 2026-05-22.
- **host4:** macOS Sequoia 15.3.1.

## [x] Step 2: Install Prism On `host1`

On `host1`:

1. Download Prism Launcher from the official Prism Launcher site.
2. Install it into `/Applications`.
3. Open Prism Launcher once.
4. Complete any first-run setup it asks for.
5. Quit Prism Launcher.

Do not manually copy random mod `.jar` files around for this workflow. `host1` should receive whole approved Prism instances from `host4`.

## [x] Step 3: Enable Remote Access On `host1`

On `host1`:

1. Open **System Settings -> General -> Sharing**.
2. [x] Turn on **Remote Login**.
3. [x] Set access to Randy's admin account, or to **Administrators** if all admin accounts should be allowed.
4. [x] Turn on **Screen Sharing** if you want visual remote control.
5. [NA] If Screen Sharing asks who can connect, allow Randy's admin account.

For "root-level" administration, do not enable the macOS root account. Use an admin account and `sudo` over SSH when needed.

Optional but useful:

- [x] Turn on **File Sharing** if you want Finder-based drag-and-drop access.
- [skip] Confirm Randy has the FileVault recovery key or the family recovery process before doing major admin work.

## [x] Step 4: Find The `host1` SSH Address

On `host1`:

1. Open **System Settings -> General -> Sharing**.
2. Look for the local hostname. For this Mac, it is `host1.local`.
3. [x] Record that hostname in `computer-info.md`.
4. [x] Record the macOS username that owns the Prism setup.

From `host4`, test SSH:

```bash
ssh host-user@host1.local
```
_Worked: `ssh host-user@host1.local`._
Use the real username and hostname. If that works, type:

```bash
exit
```

## [x] Step 5: Optional SSH Key Setup

This lets `host4` connect to `host1` without typing the `host1` password every time. It is not required for the first setup, but it makes repeated Prism syncs faster and less annoying.

_Worked: copied the `host4` SSH key to `host1`, then `ssh host-user@host1.local` logged in successfully without asking for the password again._

Password SSH is fine for the first test. For smoother repeated syncs, set up an SSH key from `host4` to `host1`.

On `host4`:

```bash
ls ~/.ssh/id_ed25519.pub
```

If that file does not exist:

```bash
ssh-keygen -t ed25519 -C "randy-family-mac-admin"
```

Then copy the public key to `host1`:

```bash
ssh host-user@host1.local 'mkdir -p ~/.ssh && chmod 700 ~/.ssh && touch ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys'
cat ~/.ssh/id_ed25519.pub | ssh host-user@host1.local 'cat >> ~/.ssh/authorized_keys'
```

Test again:

```bash
ssh host-user@host1.local
```

## [x] Step 5b: SSH Key Setup For Kid1's Prism Account

This should have been done for the **Kid1** user, not only the **Randy Pink** admin user. The Prism sync now targets Kid1's Prism data, so `host4` needs passwordless SSH access to `Kid1@host1.local`.

Status from the first attempt: SSH to Kid1 now works after Remote Login was changed from **Administrators only** to **All users**. The key-copy attempt did **not** finish correctly because the commands were run while already inside the `Kid1@host1` shell. That made `cat ~/.ssh/id_ed25519.pub` look for a key on the iMac at `/Users/Kid1/.ssh/id_ed25519.pub`, instead of using Randy's key on `host4`.

First, if the Terminal prompt says this:

```text
Kid1@host1 ~ %
```

run:

```bash
exit
```

You should be back at this prompt before continuing:

```text
host4:kid-games randytrue$
```

Then run this first command from `host4`:

```bash
ssh Kid1@host1.local 'mkdir -p ~/.ssh && chmod 700 ~/.ssh && touch ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys'
```

Then run this second command from `host4`:

```bash
cat ~/.ssh/id_ed25519.pub | ssh Kid1@host1.local 'cat >> ~/.ssh/authorized_keys'
```

Then test passwordless SSH:

```bash
ssh Kid1@host1.local
```

If it works, you should land at:

```text
Kid1@host1 ~ %
```

without typing Kid1's password. Then run:

```bash
exit
```
_WORKED!_

## [x] Step 6: Review The Sync Script

The script is:

```bash
apps/minecraft/prism-sync/prism-sync.sh
```

The script now discovers Prism instances automatically from `host4` instead of maintaining a manual allow-list.

The current instance-name exclusion list is:

```bash
INSTANCE_NAME_EXCLUDES=(
  "_BASE"
)
```

Any local Prism instance whose name contains `_BASE` is skipped. Matching is case-insensitive, so this also skips instance folders named `_Base`.

The script has four computer slots. Slots 1 and 2 are enabled right now:

```bash
TARGET_IDS=("1" "2" "3" "4")
TARGET_NAMES=("host1-Kid1" "host3-carer" "computer3" "computer4")
TARGET_HOSTS=("host1.local" "host3.local" "" "")
TARGET_USERS=("Kid1" "carer" "" "")
TARGET_ENABLED=("1" "1" "0" "0")
```

Slot 1 targets Kid1's Prism data on `host1`. Slot 2 targets Carer's Prism data on K2's laptop, `host3`.

To add another family Mac later, fill in its name, host, and the macOS username that owns Prism, then change its matching `TARGET_ENABLED` value from `0` to `1`.

Important: Prism data lives inside the macOS user account that launched Prism. For `host1`, Prism should be run from Kid1's account, so the sync target uses `Kid1@host1.local`. The previous `host-user@host1.local` SSH login works for administration, but it cannot write into `/Users/Kid1/Library` because macOS protects each user's Library folder.

Before running the sync against Kid1's account, confirm SSH works:

```bash
ssh Kid1@host1.local
```

For smoother repeated syncs, copy `host4`'s SSH key into Kid1's account too:

```bash
ssh Kid1@host1.local 'mkdir -p ~/.ssh && chmod 700 ~/.ssh && touch ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys'
cat ~/.ssh/id_ed25519.pub | ssh Kid1@host1.local 'cat >> ~/.ssh/authorized_keys'
```

After that, test again:

```bash
ssh Kid1@host1.local
```

To preview which local Prism instance folders exist, open Prism on `host4` and use **Folders -> Instances**, or list:

```bash
ls "$HOME/Library/Application Support/PrismLauncher/instances"
```

## [ ] Step 6b: Set Up `host3` (Computer Slot 2)

K2's laptop is **host3**. Prism Launcher is installed under the **Carer** admin account. The sync script uses computer slot 2.

On **host3** as Carer:

1. [x] Install Prism Launcher into `/Applications`.
2. [x] Open Prism Launcher once, complete first-run setup, then quit.
3. [x] Open **System Settings -> General -> Sharing**.
4. [x] Turn on **Remote Login**.
5. [x] Set access to **All users** or at least allow the **Carer** account.
6. [x] Confirm the local hostname is `host3.local`.
7. [x] Open **System Settings -> Users & Groups** and confirm Carer's **short name** for SSH. The script uses `carer`; if the short name is different, update `TARGET_USERS` slot 2 in `apps/minecraft/prism-sync/prism-sync.sh`.

From **host4**, test SSH:

```bash
ssh carer@host3.local
```

GOT THIS:
host4:kid-games randytrue$ ssh carer@host3.local
The authenticity of host 'host3.local (fe80::835:932b:e25f:4c7a%en0)' can't be established.
ED25519 key fingerprint is SHA256:Xqxc8loOu6KCUdzy0lcSyjaQG42jBFVbTzhIXRvD4Ts.
This key is not known by any other names.
Are you sure you want to continue connecting (yes/no/[fingerprint])? y
Please type 'yes', 'no' or the fingerprint: yes
Warning: Permanently added 'host3.local' (ED25519) to the list of known hosts.
(carer@host3.local) Password:
Last login: Wed May  6 10:28:45 2026

Optional but recommended — passwordless SSH from `host4` to Carer's account:

```bash
ssh carer@host3.local 'mkdir -p ~/.ssh && chmod 700 ~/.ssh && touch ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys'
cat ~/.ssh/id_ed25519.pub | ssh carer@host3.local 'cat >> ~/.ssh/authorized_keys'
ssh carer@host3.local
```

Run those commands from `host4`, not from inside an existing SSH session on `host3`.

Then preview sync for slot 2 only:

```bash
apps/minecraft/prism-sync/prism-sync.sh --computer 2
```

Important: Prism data lives inside the macOS user account that launched Prism. On `host3`, Carer is both the admin account and the Prism owner, so the sync target is `carer@host3.local`.

Before running the sync, quit Prism on `host3`.

## Step 7: Run A Preview Sync

From the repo root on `host4`:

```bash
apps/minecraft/prism-sync/prism-sync.sh
```

The script selects every enabled computer by default. Right now that means `host1` (slot 1) and `host3` (slot 2).

Every run first shows:

- The `rsync` dry-run preview for each selected computer.
- Which computers are selected.
- Whether existing target instance folders will be updated.
- Whether the Prism icon library will sync.
- Which instance-name exclusions are active.
- Which `rsync` excludes are active.
- Which Prism instances will sync.
- Which Prism instances are skipped because they already exist on the target.
- Which Prism instances are skipped.

The detailed `rsync` preview prints first because it can be long. The readable summary prints after the detail so it stays near the bottom of the Terminal output.

By default, if an instance folder already exists on the target Mac, the script skips that entire instance folder and leaves it untouched. This keeps target machines from having their already-created Prism/Minecraft instance data rewritten during routine runs.

The bottom summary's **Instances that will sync** section means instances that will actually be copied to the target in this run. Existing target instances appear under **Instances skipped because they already exist on target** instead.

If it says an instance is excluded, confirm that the exclusion is intentional before running the real sync.

To select a specific enabled computer:

```bash
apps/minecraft/prism-sync/prism-sync.sh --computer 1
apps/minecraft/prism-sync/prism-sync.sh --computer 2
```

To update instance folders that already exist on the target Mac, add `--update-existing`:

```bash
apps/minecraft/prism-sync/prism-sync.sh --update-existing
```

Use `--update-existing` when you intentionally want the source `host4` instance folders to refresh the target's existing instance folders. Without that switch, only missing target instances are copied.

## Step 8: Confirm The Real Sync

After the preview finishes, the script asks:

```text
Continue with the real sync to the selected computers? Type yes to continue:
```

Type:

```text
yes
```

For automation only, skip that confirmation prompt with:

```bash
apps/minecraft/prism-sync/prism-sync.sh --skip-prompt
```

`--skip-prompt` still runs the dry-run preview first. It just continues to the real sync without waiting for you to type `yes`.

For automation that also updates existing instance folders:

```bash
apps/minecraft/prism-sync/prism-sync.sh --update-existing --skip-prompt
```

Then on `host1`:

1. Open Prism Launcher.
2. Confirm the synced instances appear.
3. Launch one instance as a smoke test.

## What The Script Syncs

The script copies selected Prism instance folders from:

```text
~/Library/Application Support/PrismLauncher/instances
```

It syncs to the same Prism instance location on the target Mac.

The script also syncs Prism's custom icon library from:

```text
~/Library/Application Support/PrismLauncher/icons
```

This matters because Prism launcher tiles use the `iconKey` in `instance.cfg`, such as `iconKey=alexs caves`, and those keys point at Prism's icon library. The per-instance `minecraft/icon.png` file can exist and copy correctly without being the icon Prism uses in the launcher grid.

It intentionally excludes:

- Minecraft saves.
- Screenshots.
- Logs.
- Crash reports.
- Local options files.

That means it should update the modpack setup without overwriting each person's worlds or local video/control settings.

## Sync Log

When a real sync completes, the script appends a markdown entry to:

```text
apps/minecraft/prism-sync/_data/prism-sync_log.md
```

Each log entry uses the sync date as a heading, puts the readable core info directly under that heading, and puts the long dry-run and real-sync details under a **Details** heading.

## Troubleshooting

### Prism Icons Do Not Appear

Prism launcher tile icons are controlled by `iconKey` in each instance's `instance.cfg`. For example, Alex's Caves can have `iconKey=alexs caves`.

That `iconKey` points to Prism's custom icon library:

```text
~/Library/Application Support/PrismLauncher/icons
```

The per-instance file `minecraft/icon.png` may copy correctly but still not be the icon Prism uses in the launcher grid. The sync script now copies both the selected instance folders and the Prism custom icon library.

After a real sync, quit and reopen Prism on the target Mac so it reloads the icon library.

### Not Enough RAM Warning

If Prism says an instance needs more RAM than macOS currently has available, first quit other apps on the iMac and restart the iMac before launching Minecraft. Browsers, video apps, other games, and old Minecraft/Java processes are the usual memory hogs.

On the iMac, use **Activity Monitor -> Memory** to check memory pressure and sort by memory usage. If the graph is yellow or red, quit the largest unnecessary apps.

For Forge modpacks like Alex's Caves, 4 GB allocated to Minecraft is normal. If the iMac has only 8 GB of total RAM, macOS Tahoe plus background apps may leave too little free memory. If restarting and quitting apps does not help, either reduce the instance memory setting in Prism and accept possible slowdowns, or use a Mac with more RAM for heavier Forge packs.

## Important Cautions

- Quit Prism on the target Mac before running a real sync.
- Do not sync the entire Prism Launcher data folder.
- Do not point multiple Macs at one shared network Prism folder.
- Do not include saves unless you intentionally want to copy worlds.
- Use `--skip-prompt` only for automation after you trust the preview behavior.
- If the target Prism account is a different macOS user from the SSH user, stop and adjust the plan first. Copying into another user's Library needs ownership handling.

## Repeat For The Other Family Macs

For each additional Mac:

1. Add its details to `computer-info.md`.
2. Update macOS.
3. Install and launch Prism once under the account that will own the instances.
4. Enable Remote Login for that account.
5. Confirm SSH from `host4`.
6. Fill in the next open computer slot in `apps/minecraft/prism-sync/prism-sync.sh` and set its `TARGET_ENABLED` value to `1`.
7. Run the preview sync.
8. Confirm the prompt to run the real sync.
9. Open Prism and confirm the instances appear.
