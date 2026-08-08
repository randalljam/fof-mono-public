file: plans/2026-07-01_repo-snapshot-oss-discovery/fable5-prompts/3-meta-system-upgrade.md
title: Fable 5 prompt 3 — Meta-System Upgrade (skills standard + one OSS integration)
last-updated: 2026-07-01_0930
ai: Claude Code (cloud)
session: `repo-analysis-oss-discovery`

Copy everything below the line into a fresh Claude Fable 5 session running in `fof-mono`.
Advances the coding system itself. Mostly additive; one working integration.

---

You are working in the `fof-mono` monorepo as an autonomous agent. Before doing anything, read these
two files in full and operate under them for the whole session:
- `plans/2026-07-01_repo-snapshot-oss-discovery/fable5-context-brief.md`
- `plans/2026-07-01_repo-snapshot-oss-discovery/fable5-operating-contract.md`
Also read `skills/README.md`, the OSS scan at
`plans/2026-07-01_repo-snapshot-oss-discovery/oss-discovery.md`, and skim `agents/hermes/skills/`.

**Mission — consolidate the skills system toward the open standard, and land one real OSS integration.**
Randy's "one source of truth, many platform wrappers" skills model is ahead of most solo setups but is
maintained by hand. Two moves that compound: (a) align it with the emerging conventions so it stops
being bespoke, and (b) wire in one high-leverage tool from the OSS scan so agents get sharper
immediately. This is a design-and-judgment task about his meta-system — the reason to use your capability.

**What to actually produce:**
1. **Audit + standardize the skills system.** Survey `skills/` and `agents/hermes/skills/`. Produce
   `plans/2026-07-01_skills-standardization.md` that maps the current layout to the `SKILL.md` open
   standard (progressive disclosure, provenance/history headers) and to a `rulesync`-style
   one-source-many-wrappers flow that can generate the Hermes / Claude Code / Cursor / AGENTS.md
   wrappers. Then **apply the low-risk parts**: normalize the provenance/history headers across existing
   skill READMEs, fix any drift, and add a short `skills/CONVENTIONS.md` (or extend `skills/README.md`)
   documenting the target format. Do not rename or restructure skill folders wholesale in this run —
   propose that as a follow-up with an explicit migration list.
2. **Land one OSS integration end-to-end** — pick the single highest-leverage, lowest-risk item from the
   scan for Randy's setup (default: **context7** and/or **Serena** as MCP servers, since they cut the
   hallucination-from-stale-docs and token-bloat failure modes across every harness). Add the config so
   it works in at least one harness he uses, write a `skills/repo-ops/` or docs entry on how to enable
   it, and **demonstrate it working** on a real query in this repo (show the before/after). If you
   cannot fully wire it in your harness, get as far as you can and document the exact remaining steps.
3. **Write the integration plan for the rest** — a short, ranked adoption plan in the standardization doc
   for the other top picks (the Ralph loop runner template, a CodeRabbit/PR-Agent review gate,
   codegraph's Hermes-native code graph), each with the concrete first step. Plan, don't build these.

**Boundaries beyond the operating contract:** Additive only — do not break existing skills, Hermes, or
any harness config that's currently working. Don't restructure skill folders in this run. Anything that
touches Hermes's live deployment or credentials is out of scope (note it as a follow-up); do not deploy
or restart Hermes.

**Definition of done:** provenance headers normalized across skill READMEs; a documented target
convention; one OSS tool actually enabled and demonstrated (or maximally wired with exact remaining
steps); `2026-07-01_skills-standardization.md` holds the audit, the applied changes, and the ranked
adoption plan. Finish with the approval packet, leading with what's now sharper and the single next tool
worth adopting. Default to stopping at "branch pushed + approval packet."
