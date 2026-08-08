file: plans/2026-07-01_repo-snapshot-oss-discovery/fable5-prompts/2-safety-rails-ci-floor.md
title: Fable 5 prompt 2 — Safety Rails (CI + test floor)
last-updated: 2026-07-01_0930
ai: Claude Code (cloud)
session: `repo-analysis-oss-discovery`

Copy everything below the line into a fresh Claude Fable 5 session running in `fof-mono`.
Closes Randy's #1 named gap (no CI). Additive and gated — nothing deploys.

---

You are working in the `fof-mono` monorepo as an autonomous agent. Before doing anything, read these
two files in full and operate under them for the whole session:
- `plans/2026-07-01_repo-snapshot-oss-discovery/fable5-context-brief.md`
- `plans/2026-07-01_repo-snapshot-oss-discovery/fable5-operating-contract.md`

**Mission — stand up the minimum continuous-integration and test floor.**
Randy's roadmap (`ai-coding-system-dev.md` §9) names this as the prerequisite for granting agents more
autonomy: today the `tests/` suite exists but nothing runs it automatically, and there is no required
check before merge. Build the smallest real CI floor that makes future agent work verifiable. This
needs judgment about the existing suite's real-vs-mocked split and what's safe to gate on — reason it
through before writing.

**What to actually produce (in priority order — land what you can, cleanly):**
1. **Survey first.** Read `tests/` (`test_fileops.py`, `test_llm.py`, `test_transcribe.py`), the
   `dependencies/requirements_*.txt`, and how the `.venv` is used. Determine which tests run offline
   without secrets or network, and which need real API keys (the `llm` module especially). Write your
   findings to `plans/2026-07-01_ci-floor.md` before touching config.
2. **Add a GitHub Actions workflow** (`.github/workflows/ci.yml`) that, on pull requests, sets up
   Python + the project venv and runs the **offline-safe** portion of the suite. Gate cleanly: mocked
   tests run in CI; real-API tests are marked/skipped in CI (e.g. a `pytest` marker + env guard) so the
   pipeline is green and deterministic without secrets. Document exactly what runs and what's skipped.
3. **Make the suite CI-runnable** if small changes are needed — a `pytest.ini`/`pyproject` marker
   convention (`@pytest.mark.real_api`), a minimal `conftest.py` skip guard, and a one-line "how to run
   locally vs in CI" note. Do not rewrite the tests themselves beyond what's needed to separate the two
   classes.
4. **Write the runbook**: update `plans/2026-07-01_ci-floor.md` with how the gate works, how to run it
   locally, and a short **proposal (not implementation)** for the next two layers — an AI PR-review step
   (CodeRabbit CLI or self-hosted PR-Agent) and a self-verification harness with local "fakes" of
   S3/Pinecone/Webflow/LLM providers (the StrongDM pattern). Leave those as a plan for Randy to approve.

**Boundaries beyond the operating contract:** Do not add any workflow that deploys, publishes, or needs
production secrets. CI must pass with **no secrets configured** — if a test needs a key, it is skipped in
CI, not run. Touch only test-scaffolding and CI config plus the minimum marker plumbing; do not refactor
`core/` or app code. Do not enable branch-protection or required-check settings yourself (that's a
GitHub-settings change for Randy) — just note it as the follow-up that activates the gate.

**Definition of done:** `ci.yml` exists and its offline-safe run is green on a PR-style trigger (verify by
reasoning through / dry-running the job; state clearly what you could and couldn't execute in your
harness); the real-API tests are cleanly separated and skipped in CI; `2026-07-01_ci-floor.md` documents
the gate and the two proposed next layers. Finish with the approval packet, and state plainly which parts
you verified by running vs. by inspection. Default to stopping at "branch pushed + approval packet."
