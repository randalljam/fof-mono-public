file: plans/2026-07-01_repo-snapshot-oss-discovery/skills-recommendations.md
title: Recommended new skills — descriptions and rationale (no implementations yet)
last-updated: 2026-07-06_2105
ai: Claude Code (cloud) — Fable 5
session: `repo-analysis-oss-discovery`

Fourteen proposed skills, prioritized in three tiers, each with a short description and why it earns a place. Grounded in: the seven existing `skills/repo-ops/` skills, the work patterns visible across the repo and its nine branches, the two Fable support docs (`fable5-context-brief.md`, `fable5-operating-contract.md`), and the OSS deep dives (Superpowers, compound engineering, StrongDM). Nothing here is implemented — this is the pick list.


## Where the current skills stand
The existing library is strong on **git/repo plumbing** and thin everywhere else:
- **`repo-ops/` (7):** clone-bootstrap, promote-to-main, merge-main-to-branches, hermes-branch-testing, repo-size-audit, repo-status-report, local-files-snapshot-backup. These cover repo *hygiene* — the mechanics of clones, branches, sizes, and local files.
- **Domain (3):** education/lesson-logger, family/schedule-coordinator, media/youtube-transcript.
- **Hermes wrappers** exist for the domain skills plus a Hermes-only `sync-skills`.

What's missing is everything **around the work itself**: how a session starts and ends, how tests get run before a PR, how the dangerous procedures (S3, Chalice, public mirror) are done safely, and the self-verification substrate your human-out-of-the-loop goal depends on. Every skill below targets a procedure you already perform (or mandate in `AGENTS.md`) that currently lives only in prose — which means agents re-derive it each session and sometimes get it wrong.


## Tier 1 — do these first (prevent repeated mistakes, make every session land clean)

### 1. `repo-ops/session-start-check`
**What:** The mechanical session-start procedure from `AGENTS.md`, executable: fetch + prune, enumerate remote branches, identify the user's real working branch (never the `claude/<random>` auto-branch), verify ancestry against `plans/git/branch-map.md`, and report what it found before any commit.
**Why:** `AGENTS.md` calls the auto-branch mistake "the single most-repeated mistake in cloud sessions" — and it nearly happened in this very session. This is the highest-frequency, highest-annoyance failure you have, and it's purely procedural. One skill ends it.
**Effort:** S (procedure + a small script).

### 2. `repo-ops/mission-closeout`
**What:** The end-of-session ritual from your operating contract, packaged: verify claims against tool output, run the tests, produce the **approval packet** (what changed / what verified / risk / the one decision), update the branch-map ledger, and — the compound-engineering step — write any lesson learned back as a rule, skill note, or test.
**Why:** Your operating contract §7 already specifies this, but only Fable missions reference that doc. As a skill, *every* agent session (Cursor, cloud, Codex) ends the same way, and the "compound" step stops being aspirational. This is the single biggest consistency win per unit of effort.
**Effort:** S–M. *Harvest note:* the packet format is yours; the compound step borrows Every's `/ce-compound` idea.

### 3. `repo-ops/run-app-tests`
**What:** Locate and run the right tests for whatever the session touched: per-app `AGENTS.md` `## Tests` sections, the root `tests/` suite (offline-safe vs real-API split), math-quiz's Playwright setup, prism-sync's mocked pytest — with the venv rules (`.venv/bin/python3`, never system Python) baked in. Reports pass/fail with output, refuses to claim success it didn't see.
**Why:** Pre-PR testing is **mandatory** in `AGENTS.md`, yet each agent re-discovers how to run each app's tests. This skill is also the enforcement arm of the CI floor (Fable mission 2) — same knowledge, usable locally before CI exists.
**Effort:** M (an inventory of run commands + a dispatch procedure).

### 4. `data-ops/s3-archive-ops`
**What:** A safe driver for `core/s3_archive.py`: build / status / upload / verify / refresh with the guardrails encoded — always dry-run first, require `--execute` deliberately, **stop and ask before `build`/`refresh` on `exchanges/`** (the mtime-reset trap), never touch a keyed path without the re-key procedure, never let PII near `[S3-FILES-BUCKET]`.
**Why:** This is your most dangerous routine procedure, and `AGENTS.md` devotes more warning text to it than to anything except git. Dangerous + procedural + documented-in-prose is exactly what skills are for. Also the first skill in a new `data-ops/` category your data-pipeline-heavy work deserves.
**Effort:** S (the tool exists; the skill is the guardrails).

### 5. `repo-ops/worktree-closeout`
**What:** The post-merge worktree retirement flow from `docs/worktrees-guide.md`: run the local-files pre-removal check, classify every WARN path (✓ disposable / ✗ preserve / ?), move keepers into `_LOCAL_FILES` after approval, re-verify, then hand the actual removal back to you.
**Why:** The worktrees guide literally says "a skill could be useful later" — and the workflow has now stabilized across many branch retirements. It's multi-step, loss-risky (gitignored files die with the worktree), and has a clean agent/human split already written down.
**Effort:** S (the checker script exists; the skill wraps the judgment procedure).


## Tier 2 — build out the system (consistency across apps and platforms)

### 6. `repo-ops/app-baseline`
**What:** The repeatable "bring one app to standard" checklist from Fable mission 4: per-app `AGENTS.md` (with `## Tests`), README/runbook, tests for load-bearing logic, a one-page health report. Run it against any `apps/<name>/`.
**Why:** You have ~20 apps at wildly different maturity. Mission 4 was designed to produce this checklist once; making it a skill means the next fifteen apps get baselined by Opus-tier sessions cheaply, not by re-specifying each time.
**Effort:** S once mission 4 runs (M if written from scratch).

### 7. `docs-ops/write-plan-doc`
**What:** Create plan/spec/design docs that actually follow your conventions: the `file:/title:/last-updated:` header (Pacific time, correct format), `YYYY-MM-DD_slug` naming, your markdown spacing rules, and the milestone structure your best plans use (the MathQuest M1–M6 pattern: context → phases → status → future items).
**Why:** With 878 markdown files, docs *are* your codebase, and agents get the conventions wrong constantly (wrong timezone, wrong heading spacing, dated filenames for stable reports). Small skill, applied on nearly every session.
**Effort:** S.

### 8. `aws-ops/chalice-preflight`
**What:** The pre-deploy discipline for Chalice/Lambda work: read `chalicelib_mirror_deploy.sh` first, verify the edit is in `core/` (never `chalicelib/`), check config/env expectations, confirm dev-vs-prod target, and prepare the deploy-log entry. Explicitly does **not** deploy — it makes the human-approved deploy safe.
**Why:** `CLAUDE.md`'s only two instructions are "plan mode for risky refactors" and "be extra cautious with Chalice/Lambda." QRAG is production with real users. The caution currently lives in prose; a preflight skill makes it a checklist an agent can't skip.
**Effort:** S.

### 9. `repo-ops/public-mirror-audit`
**What:** A PII/secrets sweep to run before `apps/repo-mirror` pushes anything to the public corpus-tools clone: scan the outgoing file set for names (especially the kids'), emails, keys, tokens, `[S3-BUCKET]`-adjacent content, and data-file leaks; produce a pass/block verdict with findings.
**Why:** You have a public mirror pipeline, a documented PII audit (`2026-06-05_public-repo-pii-audit.md`), explicit child-privacy rules in `PROFILE`, and a stated plan to open-source more. Publishing is the one irreversible act in your workflow — it deserves a gate.
**Effort:** M.

### 10. `meta/skills-sync`
**What:** Maintain the "one source of truth, many wrappers" machine itself: verify every `skills/` README has correct provenance/history headers, regenerate the Hermes SKILL.md wrappers (extending the existing Hermes-side `sync-skills`), and stub Claude Code command wrappers — the rulesync direction, hand-rolled first.
**Why:** The wrapper layer is maintained by hand today and drifts. This is also the concrete first step of Fable mission 3 (skills standardization), scoped down to a repeatable skill.
**Effort:** M.


## Tier 3 — the human-out-of-the-loop substrate (creative, higher effort, highest ceiling)

### 11. `testing/build-digital-twin`
**What:** A procedure for building a local fake of one `core/` external dependency — `llm.py` (canned responses), `s3_archive.py` (filesystem-backed), `vectordb.py` (in-memory), `webflow_api.py` (fixtures) — with a standard layout, fixture format, and a "twin parity" checklist.
**Why:** Straight from the StrongDM deep dive, targeted at your #1 named gap: agents can't verify their own work without hitting real services (cost, rate limits, production risk). Your `core/` already isolates each dependency in one module, which makes twinning unusually cheap here. Each twin built via this skill compounds.
**Effort:** M per twin (the skill is the pattern; twins are produced by running it).

### 12. `testing/satisfaction-scenarios`
**What:** Write and run LLM-graded acceptance "scenarios" — plain user stories per app, stored **outside the repo** (so coding agents can't game them), graded by an LLM against a running app or its twins. Includes the scenario format, storage convention, and a grading harness procedure.
**Why:** The other half of the StrongDM pattern and the mechanism that eventually replaces "Randy reviews every PR" with "Randy reviews what the scenarios flag." Pairs with #11; both feed Fable missions 2 and 5.
**Effort:** M.

### 13. `repo-ops/new-app-scaffold`
**What:** Scaffold a new `apps/<name>/` correctly on day one: kebab-case naming, the right web lane (the four lanes from the webstacks analysis), a per-app `AGENTS.md` stub with `## Tests`, gitignore/data-dir rules (`_data/` not `data/` for code), and a `PROJECTS.md` index row.
**Why:** Your portfolio grows by several apps a year and "prefer the lightest existing pattern" is currently tribal knowledge. Every app born correct is an app that never needs baselining (#6).
**Effort:** S.

### 14. `meta/dictated-intent-check`
**What:** A small skill for handling voice-dictated instructions: normalize likely transcription mangles (branch names with underscores-for-hyphens, homophones, run-on tool names), search-with-tolerance before declaring something missing, and echo back a one-line interpretation of ambiguous asks before acting on them.
**Why:** The creative pick. Voice is your declared front door (phone dispatch, the voice-router branches), and `AGENTS.md` already tells agents to tolerate dictation mangling in branch names — but nothing generalizes it. Cheap insurance on every dictated instruction, and a small piece of the voice-router future.
**Effort:** S.


## Considered and not recommended (for the record)
- **Worktree-create skill** — creation is already well-served by `worktree_bootstrap.sh` + the guide + Cursor's UI; the gap was closeout (#5), not creation.
- **Commit-message skill** — the `.cursor/rules/commit-messages.mdc` rule + `AGENTS.md` already enforce this at the right layer.
- **Code-index revival** — your own assessment in `PROFILE` stands: modern agents navigate the repo well without it; Serena/codegraph (OSS scan) are better paths if needed.
- **A general "deploy" skill** — deploys should stay human-gated and app-specific; #8 deliberately stops at preflight.


## Pick list (for choosing)

| # | Skill | Tier | Effort | Prevents / unlocks |
|---|---|---|---|---|
| 1 | session-start-check | 1 | S | The #1 repeated agent mistake (auto-branch) |
| 2 | mission-closeout | 1 | S–M | Inconsistent session endings; lost lessons |
| 3 | run-app-tests | 1 | M | Untested PRs; re-derived test commands |
| 4 | s3-archive-ops | 1 | S | The exchanges/ mtime trap; S3 mistakes |
| 5 | worktree-closeout | 1 | S | Lost local-only files at branch retirement |
| 6 | app-baseline | 2 | S* | Re-specifying app cleanup 15 more times |
| 7 | write-plan-doc | 2 | S | Convention drift across 878 docs |
| 8 | chalice-preflight | 2 | S | Production-adjacent Chalice accidents |
| 9 | public-mirror-audit | 2 | M | PII/secrets reaching the public repo |
| 10 | skills-sync | 2 | M | Hand-maintained wrapper drift |
| 11 | build-digital-twin | 3 | M | Agents unable to self-verify (cost/risk) |
| 12 | satisfaction-scenarios | 3 | M | You as the only acceptance gate |
| 13 | new-app-scaffold | 3 | S | Apps born non-standard |
| 14 | dictated-intent-check | 3 | S | Misread voice instructions |

*\* S if Fable mission 4 runs first and produces the checklist.*

**If you pick only three:** 1 (session-start-check), 2 (mission-closeout), 3 (run-app-tests) — they touch every session and directly serve the "no cleanup for Randy" goal. **If you pick five:** add 4 (s3-archive-ops) and 5 (worktree-closeout). Tier 3 is where the compounding is biggest but should follow the CI floor.
