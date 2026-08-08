file: skills/repo-ops/watcher-set/README.md
title: Watcher — set
source-github-url: original
source-guide-url: original
history:
  - 2026-07-29 · Randy · Cursor [Watcher set skill](e2d9f1c1-9bb6-493c-8c5f-1d87749c7c8c) — initial skill: arm a recurring process watcher (frequency, done-detect, action/sound, elapsed + timestamps); patterned on flex Codex CLI watcher [a6e36e67-7173-4cc8-b30c-5cc744133807]


**Arm a recurring watcher that monitors a long-running process (or done-signal) and alarms when it finishes.** Built on Cursor's monitored shell loop (`notify_on_output` + sentinel), same mechanism as the built-in Loop skill — specialized for "tell me when X is done" rather than re-running an arbitrary prompt forever.


## When to use
- User says "set a watcher", "watch until done", "ping me when Codex finishes", or similar.
- A local CLI agent / long job is already running (Codex `exec`, build, upload, etc.) and the user wants periodic status plus a distinct completion alarm.
- Do **not** use this for cloud sessions — no local process / `afplay`. Prefer Loop only when the goal is recurring work, not a one-shot done-detect.


## Spec (what the user provides)
Capture these fields (ask only for what's missing):

| Field | Required | Example |
|-------|----------|---------|
| **Watching** | yes | Codex CLI `exec` on `feature/family-schedule-dashboard` |
| **Task label** | optional | `next week`, `next day` — short tag the user already recognizes; use in sentinel + shell title |
| **Done when** | yes | process PIDs gone **and/or** output file exists |
| **Frequency** | yes | `1m`, `5m` (default `1m` if user said "check often") |
| **Action** | yes | default: play Hero sound 3× (see below) |
| **On done** | optional | read report file, git status/log, concise summary |

Identifying the target: check terminals folder metadata + `ps` / `pgrep` for the process; record pid(s), cwd, start time, and any output path.


## Arm
1. Kill any prior watcher with the same task-label sentinel (avoid duplicates).
2. Convert frequency to seconds (`1m` → 60, `5m` → 300).
3. Start a background shell loop with `block_until_ms: 0` and `notify_on_output`:

```bash
while true; do
  sleep <seconds>
  echo 'AGENT_WATCHER_TICK_<task_slug> {"prompt":"<tick prompt>"}'
done
```

- Sentinel: `AGENT_WATCHER_TICK_<task_slug>` (unique per watcher; slug from task label, e.g. `codex_next_day`).
- Pattern: `^AGENT_WATCHER_TICK_<task_slug>`
- Reason: short, e.g. `Codex next day`
- Shell description: `Watcher every <freq>: <watching>`
- Tick prompt must instruct: if still running → one-line status only, leave loop armed; if done → stop loop, run Action, then On-done report.

4. Smoke-check once (loop pid alive; target still running or already done).
5. Optional: preview the completion sound once so the user knows what to listen for.
6. Confirm with the **armed** status block below. Do **not** rely on the Cursor turn-complete ding as the alarm — that fires on every tick.


## Tick behavior
On each wake:

1. Re-check done condition (pids / output file / whatever was specified).
2. If **still running** — reply with the **still-running** one-liner only. Leave the loop armed. Do not play the alarm. Do not write a long report.
3. If **done** — kill the loop pid, run Action, write the On-done report, end the turn.


## Status lines (required shape)

### Armed (once, after setup)
```text
Watcher: <watching> (<task label>)
Waiting for: <done when>
Frequency: <freq>
Action: <action>
Elapsed: <target etime> · now <HH:MM:SS PT> · armed <HH:MM:SS PT>
```

### Still running (every tick)
```text
Still going (<elapsed>) · now <HH:MM:SS PT> · last check <HH:MM:SS PT>
```

Keep it to one or two lines. Always include **elapsed** (from `ps -o etime=` on the target, or wall clock since watcher start if no pid) and **current timestamp** (Pacific). `last check` is this tick's time.

### Done
Play Action first, then a short completion report (what finished, elapsed total, where artifacts/commits are). Stop the watcher.


## Action: play sound (default)
macOS system sound, distinct from Cursor's turn ding:

```bash
for i in 1 2 3; do afplay /System/Library/Sounds/Hero.aiff; done
```

Other `/System/Library/Sounds/*.aiff` names are fine if the user names one. Preview once on arm when using a non-default sound. Skip sound in environments without `afplay`.


## Stop
User says stop / cancel watcher: kill the loop pid, `AwaitShell` so a stale completion notification does not re-wake later, confirm stopped.


## Related
- Cursor Loop skill (`~/.cursor/skills-cursor/loop/SKILL.md`) — generic recurring prompt; this skill is the done-detect + alarm specialization.
- Example session: flex worktree Codex watcher [a6e36e67-7173-4cc8-b30c-5cc744133807](a6e36e67-7173-4cc8-b30c-5cc744133807) — 1m checks, Hero.aiff ×3, elapsed updates while `codex exec` ran for "next week".
