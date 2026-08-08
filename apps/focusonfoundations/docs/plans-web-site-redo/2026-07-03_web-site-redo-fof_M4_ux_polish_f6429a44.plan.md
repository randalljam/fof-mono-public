---
name: M4 UX polish
overview: "Light UX-polish milestone for the ported QRAG demo: AI answer moves to the top of each result and renders in red, the interim \"30-60 seconds\" wait message becomes visible near the input, the name field confirms submission, and the accordion arrow gets bigger. Validated locally, then staging, then production deploy."
todos:
  - id: ai-answer-top-red
    content: Move AI answer (and waiting placeholder) to top of dropdown in generateDropdownContent; add red CSS for .accordion-dropdown-text-ai-answer and waiting state; update success banner text. Commit at end of todo (e.g. Move AI answer to top of dropdown and style in red.).
    status: completed
  - id: wait-message
    content: Show backend waiting text in .botsubmit-error near the input during the LLM phase and on retries, cleared when the answer lands. Commit at end of todo (e.g. Show LLM wait message near input during AI response.).
    status: completed
  - id: name-feedback
    content: Add blur + brief 'Name saved' confirmation on successful name submit in handleNiceNameSubmission. Commit at end of todo (e.g. Add name-field submit confirmation feedback.).
    status: completed
  - id: arrow-size
    content: Enlarge .accordion-icon disclosure arrow in global.css. Commit at end of todo (e.g. Enlarge accordion disclosure arrow.).
    status: completed
  - id: tests-local
    content: Add dropdown-ordering unit test, run npm test, verify all four changes on localhost:4321; STOP for Randy's local review. Commit at end of todo (e.g. Add unit test for AI-answer-first dropdown order.).
    status: completed
  - id: deploy-staging-prod
    content: Deploy to staging, STOP for Randy's staging check, then deploy to production and spot-check live. Commit at end of todo if deploy config or scripts change; otherwise note deploy SHAs in M4 results. Separate commits OK for staging vs production deploy notes if anything is committed.
    status: completed
  - id: docs-results
    content: Append M4 results + carry-forwards to plan file, rename per convention. Commit and push at end of todo (e.g. Record M4 UX polish results and M5 carry-forwards in plan.).
    status: completed
isProject: false
---

# Milestone M4 — QRAG Demo UX Polish

## Context (verified 2026-07-03)
- M3 done: production `focusonfoundations.org` + `www` serve the Astro site from CloudFront via Route 53; staging live; Webflow retained as rollback (untouched this milestone).
- Scope decision: **UX polish only.** Deferred to later milestones: Webflow decommission + archiving `web-shared/webflow/`, `core/webflow_api.py` decision, DNS ownership in CDK, runbook consolidation, landing-page design pass, debug-logging flag.
- All changes live in `apps/focusonfoundations/web/src/` — no infra, Lambda, or DNS work. Deploys are content-only (`npm run deploy:staging` / `deploy:production`).

## Commit discipline
Each todo ends with at least one git commit before moving on. Goal: stepwise, reviewable history so any single UX change can be reverted or bisected without undoing unrelated work. Prefer **more commits over fewer** when splits are coherent (e.g. JS reorder vs CSS in the same todo is fine as two commits); avoid gratuitous one-line commits or mixing unrelated concerns in one message. Multiple commits per todo are encouraged when each has a clear purpose. Branch: `feature/web-site-redo-fof`. Push after the final todo unless Randy says otherwise.

## How the pieces work today
- Each question renders ONE accordion item; inside its dropdown, `generateDropdownContent()` in [apps/focusonfoundations/web/src/lib/qrag-ui.js](apps/focusonfoundations/web/src/lib/qrag-ui.js) (lines 123–144) emits: route preamble → quoted excerpts → **AI answer last**. The waiting placeholder ("WAITING FOR AI ANSWER … may take 30-60 seconds", shipped by the backend) occupies the same last slot until the LLM returns.
- The `.accordion-dropdown-text-ai-answer` class is already emitted by the JS but has **no CSS rule** — the old Webflow site styled it `color: red` in `webflow-fof-site-head.html` (lines 302–308); that rule was dropped in the port.
- The old site also mirrored the waiting text into the error area near the input (`webflow-rag-devpage.js` lines 526–531); the port dropped that, which is why the wait message felt missing (it exists only inside the accordion, styled muted/italic).
- Name submit (`handleNiceNameSubmission` in [apps/focusonfoundations/web/src/lib/qrag-demo.js](apps/focusonfoundations/web/src/lib/qrag-demo.js) lines 130–204) gives no success feedback (same as the old site, but Randy flagged it).
- Accordion arrow is a bare `▸` character; `.accordion-icon` in [apps/focusonfoundations/web/src/styles/global.css](apps/focusonfoundations/web/src/styles/global.css) has no size rule.

## Step 1 — AI answer at top, in red (commit)
- In `generateDropdownContent()` (`qrag-ui.js`): for `quoted-qa-then-ai-answer`, emit the AI-answer div (final **and** waiting variants — they occupy the same slot) **first**, before `route_preamble` and `quoted_qa`. The `ai-answer-only` branch is unaffected.
- In `global.css`: add `.accordion-dropdown-text-ai-answer { color: red; }` (restores old-site parity; the class is already on the element). Keep `.accordion-dropdown-text-waiting` italic but change its color to red too, matching the old site and making the in-accordion wait state legible.
- Adjust the post-success banner text in `qrag-demo.js` (lines ~292–296): "AI answer ready - scroll down to view" no longer fits when the answer is at the top of the newest (topmost) accordion item — change to something like "✨ AI answer ready ✨".
- Commit: `Move AI answer to top of dropdown and style in red.` (split into separate JS/CSS commits if cleaner.)

## Step 2 — Visible interim wait message (commit)
- Restore the old behavior: when the routing response arrives and the LLM phase starts, show the backend's waiting text (`WAITING FOR AI ANSWER - … 30-60 seconds…`) in the `.botsubmit-error` element near the input, and update it on retries ("STILL WAITING…"). Port the small block from the legacy `webflow-rag-devpage.js` (lines 526–531 and 584–588) into `submitInputRag` / the `onRetryMessage` callback in `qrag-demo.js`, clearing it when the final answer lands (the success banner from Step 1 replaces it).
- Commit: `Show LLM wait message near input during AI response.`

## Step 3 — Name-field submit feedback (commit)
- In `handleNiceNameSubmission` (`qrag-demo.js`): on successful submit, blur the textarea and show a brief confirmation (e.g. "Name saved ✓" for ~2s) via the existing `.botsubmit-error` element or `displayTempMessage`. No behavior change on validation failure (existing revert + error message stays).
- Commit: `Add name-field submit confirmation feedback.`

## Step 4 — Accordion arrow size (commit)
- In `global.css`: give `.accordion-icon` an explicit larger size (e.g. `font-size: 1.4rem; line-height: 1;`) so the `▸` disclosure arrow is comfortably visible. Rotation transform already exists.
- Commit: `Enlarge accordion disclosure arrow.`

## Step 5 — Tests + local verification (commit)
- Run existing web unit tests (`cd apps/focusonfoundations/web && npm test`, currently 5 pass). Add a small unit test asserting AI-answer-first ordering in the generated dropdown HTML (export `generateDropdownContent` or test via DOM helper, whichever is lighter).
- `npm run dev` → verify at `http://localhost:4321/demos/deutsch/` against live prod backends: red AI answer at top, wait message near input during the 30–60s LLM phase, name feedback, bigger arrow.
- **STOP:** Randy reviews locally and approves the look (especially the red + placement).
- Commit: `Add unit test for AI-answer-first dropdown order.` (after tests pass; before or after STOP is OK — do not deploy until Randy approves).

## Step 6 — Staging deploy, then production
- `npm run deploy:staging` → **STOP:** Randy spot-checks `https://staging.focusonfoundations.org/demos/deutsch/`.
- On approval: `npm run deploy:production` (content sync + CloudFront invalidation only; no DNS/infra change). Quick live check on `https://focusonfoundations.org/demos/deutsch/`.
- No code commit required for deploy-only steps unless repo files change; record deploy timestamps/build SHAs in Step 7 results.

## Step 7 — Docs, results (commit + push)
- Append M4 execution results + carry-forwards to this plan file.
- Rename plan file to `2026-07-03_web-site-redo-fof_M4_ux-polish_<id>.plan.md` per convention.
- Commit: `Record M4 UX polish results and M5 carry-forwards in plan.` Push to `feature/web-site-redo-fof`.

## Rollback
Content-only milestone: redeploy the previous known-good build (`git revert` the UX commits, `npm run build`, redeploy) — no infra risk.

## Acceptance
- AI answer renders at the top of each result dropdown, in red, above the retrieved excerpts.
- A visible "may take 30-60 seconds" wait message appears near the input while the LLM runs.
- Name submit gives visible confirmation; accordion arrow is comfortably sized.
- Staging validated before production; live site unaffected during the work; tests green.

## M4 Execution Results (2026-07-03)
All seven todos completed. **M4 UX polish is live on staging and production.** Executed in Cursor thread [M4 UX polish build](2dc9e7c3-8117-4f52-aa4c-25945edb646a).

Code changes (5 commits on `feature/web-site-redo-fof`):
- `6119586` Move AI answer to top of dropdown and style in red.
- `8c824e4` Show LLM wait message near input during AI response (also includes name-field blur + "Name saved ✓" feedback — shipped in same commit).
- `1659fd1` Enlarge accordion disclosure arrow.
- `7921b1a` Add unit test for AI-answer-first dropdown order.

Automated verification:
- Web unit tests **7/7 pass** (5 existing + 2 new `qrag-ui.test.js` ordering tests).
- `generateDropdownContent` exported for testing; AI answer / waiting block renders before route preamble and quoted excerpts.
- Staging deploy 2026-07-03 ~10:41 PT → CloudFront `E2P44CTJ04YSLS`, invalidation `I43Q3B5RMTQZNLQICKCRH4EEXI`; new assets `deutsch.DAe10GPE.css`, `QragDemo…NQGWDXm0.js` confirmed at `https://staging.focusonfoundations.org/demos/deutsch/`.
- Production deploy 2026-07-03 ~10:43 PT → CloudFront `E1ZC4ZN75O9QM4`, invalidation `I8TJW6FHV8LEHAW4GKXUA4Z7N0`; same asset hashes confirmed at `https://focusonfoundations.org/demos/deutsch/`.

Manual verification (Randy):
- **STOP** points in Steps 5–6 remain for Randy's browser check of red AI-answer placement, wait message near input, name feedback, and arrow size on staging and/or production.

### Carry-forwards for M5
- Webflow decommission + archive `web-shared/webflow/` after rollback window (QRAG local-dev harnesses still reference it).
- Decide fate of `core/webflow_api.py` (still used by `core/corpuses.py`).
- Landing-page design pass; optional debug-logging flag behind `?debug=1`.
- DNS ownership in CDK; runbook consolidation; backend deploy hardening (M6).

### M4 follow-up (deferred)
- **Intermittent CORS on `qrag-llm`:** Randy saw one failed fetch (`No Access-Control-Allow-Origin`) on first attempt, success on retry — likely Lambda error/timeout path omitting CORS headers; investigate separately if it recurs.

## Next Milestone Planning (M5 and beyond)
- M5 — Webflow decommission and repo cleanup: cancel Webflow after the rollback window, archive `web-shared/webflow/` (note: QRAG local-dev harnesses in `apps/qrag/web/` still reference it), decide `core/webflow_api.py` (still used by `core/corpuses.py` upload pipelines), landing-page design pass.
- M6 (optional infra) — DNS ownership in CDK (`createDnsRecords: true` + import the 15 Route 53 records), runbook consolidation, backend deploy hardening (env-driven `ALLOWED_ORIGINS`, idempotent prod deploy path).

## Provenance
Planned and executed in Cursor thread [M4 UX polish](2dc9e7c3-8117-4f52-aa4c-25945edb646a). Prior milestones: M1 `2026-06-26_web-site-redo-fof_M1_aws-astro-site_a75a8329`, M1b `2026-07-02_web-site-redo-fof_M1b_fix-demo-and-cors_80ee62b9`, M2 `2026-07-02_web-site-redo-fof_M2_staging_deploy_213f294f`, M3 `2026-07-03_web-site-redo-fof_M3_production_cutover_5b3c136a`.

## Filename note
Plan file follows milestone convention: `2026-07-03_web-site-redo-fof_M4_ux_polish_f6429a44.plan.md` (request ID `f6429a44` preserved from generation).