file: plans/2026-07-01_repo-snapshot-oss-discovery/fable5-prompts/4-app-baseline.md
title: Fable 5 prompt 4 — App Baseline (bring one app to standard)
last-updated: 2026-07-01_0930
ai: Claude Code (cloud)
session: `repo-analysis-oss-discovery`

Copy everything below the line into a fresh Claude Fable 5 session running in `fof-mono`.
Bounded to ONE app — a repeatable pattern you can re-run per app. Pick the target (see Q1 in the
questions list) or let it choose; default target below.

---

You are working in the `fof-mono` monorepo as an autonomous agent. Before doing anything, read these
two files in full and operate under them for the whole session:
- `plans/2026-07-01_repo-snapshot-oss-discovery/fable5-context-brief.md`
- `plans/2026-07-01_repo-snapshot-oss-discovery/fable5-operating-contract.md`

**Mission — bring one app up to a documented, tested baseline.**
Randy's apps vary widely in how well-documented and tested they are. Establish a repeatable "app is up
to standard" baseline on **one** app, and produce it as a pattern that can be re-run on the next app.
Reasoning well about an unfamiliar app's actual state, and judging what the load-bearing logic is, is
the judgment-heavy part.

**Target app:** unless told otherwise, choose the highest-value app that is (a) not production-critical
and (b) currently under-documented or under-tested — a strong default is **`apps/math-quiz/`** (active,
public planned, real logic, non-production). State which app you chose and why in your first summary
line. Do **not** choose `apps/qrag/` (production-like) for this run.

**What "up to standard" means — produce all of, for the chosen app:**
1. A per-app `AGENTS.md` (if absent) covering: what the app is, how to run it locally, where its data
   lives, a `## Tests` section with the run command, and any gotchas. Match the style of the existing
   `apps/minecraft/mods/AGENTS.md`.
2. A `README.md` (or refresh) and a short runbook for the common operations.
3. **Real tests for the load-bearing logic** — per the operating contract, focus on aggregation/scoring
   functions, date/range helpers, data queries, and at least one end-to-end path through the main
   feature. Run them; report pass/fail with output. Mock external systems rather than hitting them.
4. A one-page **health report** for the app in `plans/2026-07-01_app-baseline-<app>.md`: current state,
   what you added, what's still weak, and the top three improvements you'd make next.
5. A short **"baseline checklist"** at the end of that doc — the repeatable steps you followed — so this
   mission can be pointed at the next app with almost no re-specification.

**Boundaries beyond the operating contract:** Stay inside the chosen app's folder plus its tests and
docs; do not modify `core/` or other apps (if you find a `core/` issue, note it, don't fix it here). Do
not change runtime behavior — this is about documentation and test coverage, not features or refactors.
Mostly additive: new tests, new docs. If a test reveals a real bug, document it in the health report and
ask before fixing.

**Definition of done:** the chosen app has an accurate `AGENTS.md` + README/runbook, a passing test file
covering its core logic (run, with output shown), and a health report with the reusable checklist.
Finish with the approval packet, leading with the app's real state and the top next improvement. Default
to stopping at "branch pushed + approval packet."
