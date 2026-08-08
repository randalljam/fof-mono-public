# Milestone Map (Local Website)

This folder is a tiny, dependency-free interactive milestone map inspired by the Hypixel “Museum Milestones” UI.

## Files
- `index.html` — the page
- `styles.css` — Minecraft-ish styling
- `app.js` — loads + parses `milestones.md` and renders the grid
- `milestones.md` — **edit this** to change milestone text, layout, and progress

## Run locally (VS Code Live Server)
1. Put this folder anywhere inside your existing repo (no new repo needed).
2. In VS Code, install the extension **Live Server** (if you don’t already have it).
3. Right-click `index.html` → **Open with Live Server**.
4. Edit `milestones.md`, then press **Reload** in the page (or refresh).

> Note: it must be served over HTTP. `fetch()` won’t work from `file://`.

## Edit progress
In `milestones.md` under **Current Status**, change:
- `Current Milestone: 1` → (set to 2, 3, 4…) to move the yellow highlight

By default:
- milestones < current are `done`
- milestone == current is `current`
- milestone == current+1 is `next`
- everything else is `locked`

If you want manual control, set:
- `AutoStatus: false`
and add `- Status: done/current/next/locked` under each milestone.

## Edit layout
Each milestone has a:
- `Position: row,col`

The grid size is set by:
- `Grid: 9x6`

Rows/cols are 1-indexed.

## Tooltip colors (optional)
In Rewards (or other list items), you can optionally prefix a line with:
- `{green}`, `{gold}`, `{aqua}`, `{red}`

Example:
- `{gold}+1 Dragon Planner`
