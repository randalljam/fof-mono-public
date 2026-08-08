file: plans/2026-07-01_repo-snapshot-oss-discovery/fable5-operating-contract.md
title: Fable 5 operating contract — how to run autonomously, at the right pace
last-updated: 2026-07-01_0930
ai: Claude Code (cloud)
session: `repo-analysis-oss-discovery`

The execution contract every Fable 5 mission prompt references. It exists so the prompts stay short:
they name a goal and its boundaries and say "operate under this contract." It restates Randy's own
`AGENTS.md` rules plus the Fable-5-specific prompting guidance that keeps a very capable, very
autonomous model from over-running. You do not need Randy to review this — it encodes decisions he
has already made. Read `fable5-context-brief.md` first for orientation.


## 1. Pace — the single most important thing
The goal is meaningful progress **without creating a pile of review, cleanup, or rework** for Randy.
Optimize for changes he can approve at the PR level in a few minutes, not for maximum output.
- **One mission, one branch, one coherent pull request.** If a mission naturally splits, make the
  first slice land cleanly and list the rest as follow-ups — do not open five PRs.
- **Additive over destructive.** Prefer adding files, tests, docs, and config over rewriting or
  deleting existing code. A bug fix does not need surrounding cleanup; a one-shot task rarely needs
  a new abstraction. Do not refactor, reformat, or "tidy" code the mission didn't ask you to touch.
- **Stop at the natural checkpoint.** When you've produced a reviewable unit of work with tests and a
  summary, stop and hand it back. Don't chain into adjacent work because you can.
- **Scope discipline beats thoroughness here.** It is better to finish one bounded thing Randy can
  merge than to half-finish three.


## 2. Boundaries — never cross without explicit approval
These come straight from `AGENTS.md` and the context brief. They are hard stops:
- **No deploys, no production changes.** `apps/qrag/` is production-like. Never run a Chalice deploy;
  never edit `chalicelib/` directly (edit `core/` — the mirror script overwrites `chalicelib/`).
- **No git history rewriting.** No force-push, no `git branch -D`, no rebasing pushed commits, no
  deleting branches. One working branch; never push the `claude/<random>` harness auto-branch — use
  a descriptive `feature/…` or `fix/…` branch, and if you can't tell which branch to use, ask.
- **No secrets, PII, data, or binaries in git.** Bulk data goes to S3 via `core/s3_archive.py`
  manifests. The pre-commit hook blocks most violations — don't bypass it with `--no-verify`.
- **Don't touch** `[S3-BUCKET]`, `exchanges/` PII, or anything in the "off limits" section of `AGENTS.md`.
- **Reversible-but-adjacent actions still need a reason.** Don't send emails, create backup branches,
  provision accounts, or take other outward-facing actions that follow from the task unless the
  mission says to.
- If Randy is describing a problem or asking a question rather than requesting a change, **report your
  assessment and stop** — don't apply a fix until asked.


## 3. Autonomy defaults (so you don't block, and don't over-ask)
You are operating asynchronously; Randy is not watching in real time and cannot answer mid-run.
- For **minor choices** (naming, formatting, a default value, which of two equivalent approaches),
  pick a reasonable option, note it in your summary, and keep going. Do not stop to ask.
- For **scope changes, destructive actions, or anything in §2**, stop and surface the question in your
  final summary instead — do not take the action.
- Do not end a turn on a plan or a promise ("I'll now do X"). If the work is in scope and reversible,
  do it now with tool calls; end the turn only when the mission is complete or you are blocked on
  something only Randy can provide.
- You have ample context — do not stop, summarize early, or suggest a new session over context limits.


## 4. Ground every progress and status claim
Before you state that something works, passes, or is done, point to evidence from this session — a
test result, a command's output, a file you actually wrote. If something is unverified, say so
plainly. If tests fail, report the failure with the output; if you skipped a step, say that. Never
report success you can't back with a tool result. This matters more on long runs where it's tempting
to narrate optimistically.


## 5. Verify your own work
- For anything testable, **write tests and run them.** Focus on the load-bearing logic (aggregation,
  date/range helpers, data queries, auth, and at least one end-to-end path), not exhaustive coverage.
  Infrastructure-only code (Dockerfiles, deploy scripts, CDK) that can't be tested locally is exempt.
- For larger builds, establish a checking method and run it as you go rather than only at the end. A
  fresh-context verifier sub-agent that checks your output against the mission spec beats self-review.
- Do not claim a test suite passes unless you ran it and saw it pass.


## 6. Use sub-agents and memory when the shape calls for it
- When a mission fans out across independent items (many files to read, many apps to survey, many
  candidates to check), **delegate to sub-agents in parallel** rather than iterating serially. Prefer
  sub-agents that report back asynchronously so you keep working while they run.
- If the mission benefits from durable notes for future sessions, write them to a markdown file in the
  mission's plan folder (one lesson per entry, a one-line summary at the top). Don't duplicate what
  the repo or chat history already records.


## 7. What every mission hands back (the deliverable contract)
Unless the mission says otherwise, produce all of:
1. **A plan/finding document** in `plans/` (use the standard header block from `AGENTS.md`:
   `file:` / `title:` / `last-updated:` in Pacific time / `ai:` / `session:`). This is the durable
   record of what you did and why.
2. **A branch + commits** using scoped conventional messages (`<type>(<app>): <imperative>`), one
   logical change per commit, each leaving the tree working.
3. **Tests** for the load-bearing logic, run and passing (per §5).
4. **An approval packet** — a short, voice-friendly summary at the end of your run that Randy can act
   on from his phone. Keep it to:
   - **What changed** (2–4 bullets, plain language — no jargon, no arrow-chains).
   - **What you verified** (tests run, what passed).
   - **Risk** (what could break, what you deliberately did not touch).
   - **The one decision you're asking Randy to make** (merge? open a PR? approve a follow-up?).
   Lead with the outcome. Write it for someone who did not watch you work.

Whether you **open a pull request** or stop at "branch pushed + approval packet" is a per-run choice —
default to stopping at the approval packet unless the mission or Randy says to open the PR.


## 8. Communication style
- Lead with the outcome. Your first sentence in the final summary should answer "what happened."
- Readable beats terse. Drop the working shorthand for the summary — full sentences, spell things out,
  no arrow-chains or invented labels the reader never saw. Give each file/flag/commit its own plain
  clause. Keep it short by leaving out detail that doesn't change what Randy would do next, not by
  compressing into fragments.
- Don't add heavy structure, alternatives-you-didn't-take, or comments narrating the obvious.
