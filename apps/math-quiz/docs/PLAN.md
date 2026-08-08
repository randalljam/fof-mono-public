file: apps/math-quiz/docs/PLAN.md
title: Math Quiz — Integrated Execution Plan (living roadmap)
last-updated: 2026-06-16_0844
ai: Claude Code (cloud) — Opus
session: `math quiz goal`


## Purpose of this document (read first)
This is the **single, living execution plan** for the math-quiz application — the sequenced,
status-tracked work that AI coding agents (and humans) should do next to integrate all periods of work
into one product. It is the companion to `SPEC.md`.

**What goes here (PLAN):** the **decision log** (with dates), **phases and tasks** (ordered, with
acceptance tests), and **status** (`[ ]` todo / `[~]` in progress / `[x]` done). If it's "do this / in
this order / is it done?", it goes here.

**What goes in `SPEC.md` instead:** durable definitions and contracts (the rubric, principles, data
model). If a task here changes "what is true," update `SPEC.md` in the same change.

**How to work this plan:** pick the lowest-numbered unblocked task; implement DOM-free + tested; keep
`SPEC.md` consistent; end every task with `cd apps/math-quiz/tests && npm run test:all` green; update
the status box and the change log. Branch per the repo's branch rules.


## Decision log
Newest first. Each resolves an open question from the compare report
(`docs/2026-06-16_compare-report/index.html`).
- **2026-06-16 — Q1 (speed/threshold & rubric):** Fluency ≠ accuracy. Canonical rubric is
  **red/yellow/green/blue** applied at **operation / category / individual-problem** levels; thresholds
  are **adjustable & level-appropriate** (not a fixed 2 s). Not a speed-competitor mode. → SPEC §2–§4,
  §7. Implement in **Phase A**.
- **2026-06-16 — Q2 (one verdict vs two axes):** Accuracy is **table stakes**, encoded as the **red
  floor**; the headline metric is **automaticity (fluency)**. The app is **not designed around
  accuracy** (auto-submit accepts only the correct answer). → SPEC §2–§3.
- **2026-06-16 — Q3 (storage):** Move to **per-user SQLite**; **retire session-JSON** as the math-quiz
  store; keep JSON only as interchange for other producers, gated by the write-mode switch; add a
  legacy-JSON importer. → SPEC §8. Implement in **Phase C**.
- **2026-06-16 — Q4 (modality):** **Add structured modality capture** per session/attempt. → SPEC §9.
  Implement in **Phase D**.
- **2026-06-16 — Q5 (cloud-agent S3 access):** Keep the repo **source-only**; commit only a few small
  anonymized canonical fixtures. For real captures, give the cloud agent S3 read via **(a) env-var
  secret creds in the cloud environment config** (no repo commit) **and (b) opening network egress** to
  the S3 host. Details in **Phase G**.
- **2026-06-16 — Q6 (re-ask policy):** **Stop re-asking correct-but-slow facts in assess**; re-ask only
  wrong/skipped (once); speed work moves to practice mode. Specifics in **Phase B**.
- **2026-06-16 — Q7 (deploy):** **Local-first on device** (touchscreen keypad) for real use now;
  revisit hosted/Webflow + auth only when sharing beyond the family. No work item — posture.


## Status snapshot
- [ ] Phase A — Fluency rubric + adjustable, level-appropriate thresholds
- [ ] Phase B — Re-ask policy in assess
- [ ] Phase C — Storage unification on per-user SQLite (+ legacy-JSON importer)
- [ ] Phase D — Modality capture
- [ ] Phase E — Curated plans for subtraction & multiplication
- [ ] Phase F — Integrated dashboards on the new data + adaptive engine + operator control panel
- [ ] Phase G — Cloud-agent S3 access (infra)
- [ ] Phase H — Real-use hardening + profiles 5–10 (G1/G2)

Sequencing rationale: A makes the verdict honest for the kids already using it (highest leverage);
B halves the kid session; C makes data durable/mergeable; D enables modality analysis; E removes the
×/− marathon; F delivers the always-on tracking + adaptivity that is the real goal; G unblocks
real-capture review; H is polish for sustained use. A and B can land together; G is independent infra.


## Phase A — Fluency rubric + adjustable thresholds  (highest leverage)
Encode SPEC §3–§4 as the canonical evaluation.
- [ ] **A1 — Canonical rubric.** Reconcile `evaluateFluencyStatus`: fold low-accuracy (`gray`) into
  **red**; keep red/yellow/green/blue by the SPEC meanings; keep `nodata` distinct. Document the mapping
  inline.
- [ ] **A2 — Level-appropriate, adjustable thresholds.** Make `greenMs` / `redMs` / `minAccuracy`
  configurable **per learner/level** (presets: "adult" ≈ 2 s, "developing" ≈ 3.5–4 s). No hard-coded 2 s.
- [ ] **A3 — Three-level rollup.** Compute the rubric at **operation**, **category** (segmentation), and
  **individual-problem** granularity, with aggregate stats that roll up and drill down. Expose a
  DOM-free function the dashboards and control panel can consume.
- [ ] **A4 — Longitudinal per-problem history.** From the per-user DB, return a fact's full attempt
  history (time/correct/flags) across sessions.
- **Tests:** rubric mapping (inaccurate ⇒ red; accurate-slow ⇒ yellow; fast ⇒ green; sustained ⇒ blue);
  threshold presets change verdicts as expected; rollup parity (problem→category→operation); G1/G2
  re-score to yellow/green (not red) at the developing preset.


## Phase B — Re-ask policy in assess  (Q6 specifics)
Today `engine/assess_flow.mjs` re-delivers **every** slow/missed fact (`redeliverSpacing` = 5),
~doubling kid sessions. Change to:
- [ ] **B1 — Classify first-attempt outcome:** `fast+correct` (clean, no re-ask) · `slow+correct`
  (record the slow time as the automaticity signal; **no re-ask in assess**) · `wrong/skip`
  (re-deliver **once** later to distinguish a fat-finger/glitch from a real gap).
- [ ] **B2 — Config flags:** `reaskSlowCorrect: false` (new default), `reaskOnErrorOrSkip: true`,
  `maxReasksPerFact: 1`; keep warm-up discard of the first ~2.
- [ ] **B3 — Speed work to practice:** slow-but-correct facts feed practice-mode targeting, not assess
  re-asks.
- **Tests:** a slow+correct fact is **not** re-asked; a wrong fact is re-asked exactly once; total
  presentations ≈ unique in-scope facts (not ~2×); a real fat-finger that's fast+correct on re-ask is
  discarded as a glitch.


## Phase C — Storage unification on per-user SQLite  (Q3)
- [ ] **C1 — Per-user DB is canonical** for math-quiz; per-run `.sqlite` = capture/transport.
- [ ] **C2 — Retire session-JSON writes** for math-quiz (write-mode `sqlite-only`); keep JSON only as
  interchange behind the switch.
- [ ] **C3 — Legacy-JSON importer** → per-user DB, so historical `math_session_*.json` and the
  Minecraft-format feed unify (parity with direct fluency computation).
- [ ] **C4 — Wire the capture→combine→re-evaluate loop** using `tools/combine_sqlite.py`.
- **Tests:** ingest N legacy JSON sessions → DB-derived rubric equals direct computation; per-run files
  combine into the per-user DB; re-evaluate after a threshold change reproduces expected statuses.


## Phase D — Modality capture  (Q4)
- [ ] **D1 — Schema:** add a `modality` record (device, presentation/read-aloud, input method, keypad
  mode, auto-submit) to `Sessions` (and per-attempt where it can vary).
- [ ] **D2 — Capture:** anchor/quiz pages record it; default to the touchscreen-keypad path.
- [ ] **D3 — Surface:** modality available for filtering/grouping in analysis.
- **Tests:** a run records its modality; analysis can filter/group by it.


## Phase E — Curated plans for subtraction & multiplication
- [ ] **E1 — Multiplication segmentation** (reuse the addition category scheme where it maps) +
  curated hard-first plan.
- [ ] **E2 — Subtraction segmentation** + plan.
- [ ] **E3 — Anchor/assess use the curated plan** for ×/− (no more full 55-fact fallback marathon).
- **Tests:** ×/− assess runs administer the curated plan; coverage by category; lengths are bounded.


## Phase F — Integrated dashboards + adaptive engine + operator control panel
- [ ] **F1 — Render the per-fact fluency grid/heatmap** on the live page from the SQLite store (extract
  `prepareFluencyDatasets` from the fluency page's bootstrap).
- [ ] **F2 — Mode machine + batched practice** wired into the main quiz UI (assess↔practice transitions
  logged; batches default 10; mix default 50/50).
- [ ] **F3 — Operator control panel:** alongside a live run, show a real-time heatmap + roll-up
  (rubric at all three levels, flags); start **read-only**, then add **queue injection** — let the
  operator populate upcoming problems by category (Add-Zero … Sneaky-Six; hard products), steering or
  overriding the adaptive selector mid-session.
- [ ] **F4 — Flags + filters** carried through (flag, recency/date, session range) per SPEC §4.
- **Tests:** grid matches DB-derived rubric; transitions fire on signals (not isolated glitches); batch
  cadence + mix hold; queue injection changes the upcoming order.


## Phase G — Cloud-agent S3 access  (Q5 — infra; proposal below)
**Problem.** Real captures live in S3 (`[S3-BUCKET]`, PII). The cloud agent runs in an ephemeral VM that
(verified 2026-06-16) **cannot reach S3** — egress returns *"Host not in allowlist: aws.amazon.com"* —
and has **no AWS creds**. Two independent blockers: **network egress** and **credentials**.

**Recommended solution (no secrets in the repo):**
1. **Open egress (user action, web UI):** in the Claude Code web environment's **network policy**, allow
   the S3 host(s) — `s3.us-west-2.amazonaws.com` and the bucket virtual-host
   `[S3-BUCKET].s3.us-west-2.amazonaws.com` (or `*.amazonaws.com`). Without this, creds are useless.
   Docs: https://code.claude.com/docs/en/claude-code-on-the-web.
2. **Inject scoped creds as environment secrets (user action, web UI):** add
   `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION=us-west-2` as the environment's
   configured **environment variables**. This is the **same mechanism that already injects
   `OPENAI_API_KEY`** into this environment (verified present 2026-06-16) — so it's proven to work and
   keeps secrets **out of git**. boto3/`core/aws.py` read these from the environment automatically (no
   `.env` needed); the existing download helpers (`get_s3_object`, `download_s3_files_new`) then work.
3. **Least privilege:** a dedicated IAM user/policy with **read-only** `s3:GetObject` + `s3:ListBucket`
   scoped to a single prefix (e.g. `arn:aws:s3:::[S3-BUCKET]/math-quiz/test/anchor/*`). Prefer short-lived
   **STS** creds if convenient; otherwise static keys with a **rotation reminder** (e.g. monthly).
4. **Why not commit a token:** committing any credential (even scoped/temporary) risks leak via history
   and adds the kind of bloat the repo just shed — avoid.

**Preferred near-term (often makes G moot):** generalize to a **few small anonymized canonical
fixtures** committed as test data (SPEC §11), so agents work from representative captures and rarely
need live S3. Use real-capture fetch only when a fixture can't stand in.
- [ ] **G1 — User:** open S3 egress + add AWS env secrets in the web environment (scoped IAM).
- [ ] **G2 — Agent:** a small `tools/` fetch helper (boto3) reading env creds, pulling a prefix to a
  gitignored local path; verify against `core/aws.py`.
- [ ] **G3 — Fixtures policy:** dedicated gitignored capture dir + a small committed `tests/fixtures/`
  for the few anonymized canonical DBs; document the cap.
- **Tests (when creds present):** fetch helper lists/downloads a known key; skips cleanly when creds
  absent (like the sql.js-gated unit tests).


## Phase H — Real-use hardening + profiles
- [ ] **H1 — Long-pause handling** (exclude 8–31 s outliers from speed stats; optional "still there?").
- [ ] **H2 — Actionable "facts to practice"** (surface slowest/hardest, capped — Sneaky Six, hard
  products — not the whole list).
- [ ] **H3 — Prominent operation labeling** in UI/summary.
- [ ] **H4 — Profiles to 5–10**, including G1/G2 (accurate-but-slow addition / multiplication) as
  regression cases for the threshold/verdict changes.
- **Tests:** each profile reaches its declared end state; outlier handling changes speed stats as
  expected.


## Change log
Newest first.
- **2026-06-16** — Created `SPEC.md` + this `PLAN.md` as the integrated, living pair; resolved Q1–Q7
  (decision log above); referenced from `AGENTS.md`; updated the compare report. (cloud agent)
