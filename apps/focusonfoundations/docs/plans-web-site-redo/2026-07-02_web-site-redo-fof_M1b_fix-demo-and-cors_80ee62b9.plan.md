---
name: fix-demo-and-cors
overview: Fix the Astro demo page's broken init script, then additively allow the new site origins (localhost:4321, staging, apex) in the six QRAG Lambdas via a safe, code-only prod redeploy that leaves env vars, API Gateway, and public URLs untouched.
todos:
  - id: fix-frontend-script
    content: "Fix QragDemo.astro: replace define:vars import script with a bundled module script that looks up demo by data-demo-slug; rebuild; commit."
    status: completed
  - id: verify-local-ui
    content: "STOP: Randy verifies local demo page UI (no SyntaxError, consent hides, name/chunks/dates work); backend calls still CORS-blocked until Step 6."
    status: completed
  - id: edit-cors-origins
    content: Additively add localhost:4321, staging, and apex origins to ALLOWED_ORIGINS in all six app.py (incl. hmac-hash OPTIONS gate); commit.
    status: completed
  - id: confirm-prod-deploy-cmd
    content: "STOP: investigate/confirm exact code-only update-function-code commands and prod function names; diff deployed app.py vs repo; show Randy and get approval."
    status: completed
  - id: snapshot-prod-lambdas
    content: Snapshot all six <app>-prod Lambdas (config + current deployment zips) to a local gitignored dir as rollback artifacts.
    status: completed
  - id: deploy-hash-store
    content: "Code-only update hash-store-prod, then STOP: Randy manually tests name submit locally and confirms live www still works."
    status: completed
  - id: deploy-remaining-five
    content: "Code-only update the remaining five: hmac-hash, qrag-routing, qrag-llm, send-email, vrag-llm."
    status: completed
  - id: verify-and-rollback-ready
    content: Verify live www end-to-end, full QRAG on localhost:4321, and apex/staging CORS; keep git revert + snapshot re-upload rollback ready.
    status: completed
isProject: false
---

# Fix Demo Init Script and Add CORS Origins

## Context
Two independent problems, done in order with stepwise commits and explicit STOP points for manual verification.

1. Frontend: [`QragDemo.astro`](apps/focusonfoundations/web/src/components/QragDemo.astro) uses `<script define:vars={{ demoConfig: demo }}>` containing `import` statements. Astro renders `define:vars` scripts as plain (non-module) inline scripts, so the top-level `import` throws `Uncaught SyntaxError: Cannot use import statement outside a module`. That is the single script that wires consent, name, chunks, dates, and submit, so the whole demo page is dead.

2. CORS: allow-listing is enforced in Lambda Python (`ALLOWED_ORIGINS` set in each `app.py`), not API Gateway. The POST response only sets `Access-Control-Allow-Origin` when `request_origin in ALLOWED_ORIGINS`. The only fix is to edit `ALLOWED_ORIGINS` in each `app.py` and redeploy the Lambda code. Six Lambdas are involved.

## CORS deploy approach (confirmed from repo)
- [`chalicelib_mirror_deploy.sh`](web-shared/aws_chalice/chalicelib_mirror_deploy.sh) `prod` path is init-only and self-aborts (exit 2) when a prod API Gateway exists. Do not use it.
- No `.chalice/deployed/*.json` in repo and `config.json` defines only a `dev` stage, so `chalice deploy --stage prod` would try to create new infra, not update the live stack. Avoid.
- Live prod Lambdas already hold their env vars/secrets from the last deploy; those persist across a code update.
- Chosen path: **code-only** `aws lambda update-function-code` on each `<app>-prod` function. This leaves env vars, API Gateway, stage, and public URLs untouched and never re-injects secrets. Region `us-west-2`, account `[AWS-ACCOUNT-ID]`.

## The six Lambdas and origins
Functions (names to confirm in Step 4): `hash-store-prod`, `hmac-hash-prod`, `send-email-prod`, `qrag-routing-prod`, `qrag-llm-prod`, `vrag-llm-prod`.

Source files:
- [`web-shared/aws_chalice/hash-store/app.py`](web-shared/aws_chalice/hash-store/app.py)
- [`web-shared/aws_chalice/hmac-hash/app.py`](web-shared/aws_chalice/hmac-hash/app.py) (also update its OPTIONS route gate)
- [`web-shared/aws_chalice/send-email/app.py`](web-shared/aws_chalice/send-email/app.py)
- [`apps/qrag/api/qrag-routing/app.py`](apps/qrag/api/qrag-routing/app.py)
- [`apps/qrag/api/qrag-llm/app.py`](apps/qrag/api/qrag-llm/app.py)
- [`apps/qrag/api/vrag-llm/app.py`](apps/qrag/api/vrag-llm/app.py)

Origins to ADD (additive; keep all existing entries, especially `https://www.focusonfoundations.org`, plus existing `localhost:3000`/`localhost:8000`/floodlamp):
- `http://localhost:4321`
- `https://staging.focusonfoundations.org`
- `https://focusonfoundations.org` (apex — not allowed anywhere today)

## Step 1 - Fix the frontend init script (commit)
In [`QragDemo.astro`](apps/focusonfoundations/web/src/components/QragDemo.astro): add `data-demo-slug={demo.slug}` to the `.bot-container` section and replace the `define:vars` script with a normal bundled module script that imports and looks up the demo by slug:

```astro
<script>
  import { initQragDemo } from '../lib/qrag-demo.js';
  import { initPrivacyConsent } from '../lib/privacy-consent.js';
  import { getDemoBySlug } from '../lib/demo-config.js';

  document.querySelectorAll('.bot-container[data-demo-slug]').forEach((el) => {
    const demo = getDemoBySlug(el.dataset.demoSlug);
    if (!demo) return;
    initPrivacyConsent(el);
    initQragDemo(demo);
  });
</script>
```

Astro bundles `<script>` without `define:vars` as `type=module`, resolving the imports. Rebuild and commit.
Commit: `Fix QRAG demo init script (module script instead of define:vars imports).`

## Step 2 - STOP: manual local UI verification
Randy checks `http://localhost:4321/demos/deutsch/` (dev server already running):
- No `Cannot use import statement outside a module` in console.
- "I agree" checkbox accepts and the consent box disappears.
- Typing a name + Enter/blur is accepted; chunk buttons highlight on click; date pickers work.
- Expected at this point: submitting a question or name still triggers a CORS failure to the prod APIs, because `localhost:4321` is not yet allow-listed. That is fixed after Step 6. Confirm only the UI wiring here.

## Step 3 - Edit ALLOWED_ORIGINS in all six app.py (commit)
Additively add the three origins to each `ALLOWED_ORIGINS` set, and to the `hmac-hash` OPTIONS gate. Diff to confirm only additions.
Commit: `Allow Astro local, staging, and apex origins in QRAG API CORS.`

## Step 4 - STOP: confirm exact code-only prod redeploy command
In-session investigation, then show Randy the exact commands before executing:
- Confirm prod function names/region: `aws lambda list-functions --region us-west-2 --query "Functions[?ends_with(FunctionName, '-prod')].FunctionName"`.
- For one app, download the live prod zip (`aws lambda get-function` -> `Code.Location` -> curl) and diff the deployed `app.py` (zip root) against the repo `app.py`. Goal: the only meaningful delta is the `ALLOWED_ORIGINS` addition (comment/"last updated" drift is acceptable). If real logic drift exists, surface it before proceeding.
- Decide the minimal-risk mechanism: prefer editing/replacing only `app.py` inside the downloaded prod zip and re-uploading via `aws lambda update-function-code`, so dependencies and `chalicelib` in the live package are untouched. Present the concrete command set and wait for approval.

## Step 5 - Snapshot all six prod Lambdas (rollback artifact)
Before any deploy, save the current live code as the rollback source (local, gitignored dir e.g. `tmp/cors-prod-snapshots/<timestamp>/`):
- `aws lambda get-function-configuration --function-name <app>-prod --region us-west-2 > <app>-prod.config.json` (records env vars/handler for reference).
- Download the current deployment zip for each `<app>-prod` to `<app>-prod.orig.zip`.
Rollback = re-upload the saved `.orig.zip` via `update-function-code`.

## Step 6 - Deploy hash-store first, then STOP for manual name test
- Apply the code-only update to `hash-store-prod` only.
- STOP: Randy tests locally at `http://localhost:4321/demos/deutsch/` - accept consent, enter name, confirm the `hash-store` call now succeeds (JWT stored, no CORS error in Network tab). Also confirm the live `https://www.focusonfoundations.org` site still works (regression check).

## Step 7 - Deploy the remaining five
After hash-store is confirmed: apply the same code-only update to `hmac-hash-prod`, `qrag-routing-prod`, `qrag-llm-prod`, `send-email-prod`, `vrag-llm-prod`.

## Step 8 - Full verification and rollback readiness
- Live regression: full Q&A on `https://www.focusonfoundations.org` still works.
- New origins: full QRAG flow on `http://localhost:4321` (consent -> name -> question -> quoted excerpts + AI answer -> download/email). Optionally spot-check apex/staging origins via `curl` with an `Origin:` header against each endpoint, expecting `Access-Control-Allow-Origin` echoed back.
- Rollback if anything breaks: `git revert` the Step 3 commit, and/or `aws lambda update-function-code --function-name <app>-prod --zip-file fileb://tmp/cors-prod-snapshots/<ts>/<app>-prod.orig.zip`. Downtime is acceptable, so rollback is low-stakes.

## Notes
- `.env` for the Astro site already points at the prod API URLs, so once `localhost:4321` is allow-listed, local dev exercises the real prod backends.
- Staging/production CloudFront custom domains still need DNS/ACM before those hostnames resolve; apex/staging origins are added now so CORS is ready when they do.


## M1b Manual Test Results (2026-07-02)
Randy tested `http://localhost:4321/demos/deutsch/` against the live prod backends. Verdict: **success — the demo works end-to-end and CORS is fixed.**

Confirmed working:
- No `Cannot use import statement outside a module` error in the console (the M1b frontend bug is fixed).
- Chunk-count selector: clicking `20` highlights correctly.
- Dates match the current Webflow live site.
- Question submit ("What is the meaning of life?") flips the input to the stop icon; retrieved excerpts appear within a couple seconds; Download and email icons render; the AI answer arrives and the accordion folding works.
- Full flow (consent → name → question → excerpts + AI answer) succeeds from `localhost:4321`, which required the `hash-store`/`qrag-routing`/`qrag-llm` CORS updates — so the prod deploy is verified from the browser, not just by zip inspection.

## Differences From Current Webflow Site (observed, non-blocking)
- **Console is silent (expected, not a defect).** The old Webflow scripts carried ~93 `console.*` debug statements (`webflow-fof-site-body.js` 31, `webflow-rag-devpage.js` 62). The ported modules keep only 7, all `console.error` inside catch blocks. So on a successful run nothing logs — and the quiet console actually confirms no errors fired. This is deliberate cleanup during the port; verbose step logging can be re-added behind a debug flag if wanted.
- **Name field gives no submit feedback.** Pressing Enter after typing a name doesn't visibly change the cursor/field, so it's unclear it was accepted (it was — the downstream question call succeeded). UX polish item for a later milestone.
- **No interim "waiting for AI response (30–60s)" message.** The stop icon stays but the old reassuring wait text isn't shown. Minor UX parity item.
- **Accordion disclosure arrow is small.** Cosmetic.
- **AI answer no longer renders in red.** Randy confirmed this styling change is acceptable.

None of these block the migration; they are tracked as UX-parity follow-ups (see M4).


## Next Milestone Planning (M2 and Beyond)
High-level roadmap only — each milestone gets its own detailed planning session. Prior work: **M1** = initial Astro build + CDK infra + local QRAG port (`2026-06-26_web-site-redo-fof_M1_aws-astro-site`); **M1b** = demo init-script fix + prod CORS origins (this file).

### M2 — Staging deploy and remote validation
- **Objective:** publish the locally reviewed build to `staging.focusonfoundations.org` and validate the full QRAG flow from a real remote origin (not just localhost).
- **Outcome:** staging site live over HTTPS; all routes resolve on direct refresh; QRAG works from the staging origin (already CORS-allow-listed); Webflow untouched.
- **Key technical:** ACM cert in `us-east-1` for the staging hostname; Route 53 record (or CNAME) for `staging.`; `deploy:staging` = `astro build` → `aws s3 sync` → CloudFront invalidation; CloudFront rewrite for extensionless Astro routes; conservative cache headers (short HTML, long hashed assets).

### M3 — Production cutover
- **Objective:** point `focusonfoundations.org` + `www.` at CloudFront/S3 and end reliance on Webflow for serving the site.
- **Outcome:** live domain served by the new Astro site over HTTPS; Webflow retained briefly as rollback.
- **Key technical:** DNS decision (move nameservers to Route 53 vs. point apex/`www` records at CloudFront at the current registrar); **preserve non-website records (MX, SPF, DKIM, DMARC, verifications)**; lower TTL ahead of cutover; staged verification of both hostnames + demo API calls; rollback = revert DNS to Webflow.

### M4 — Post-cutover cleanup and UX polish
- **Objective:** resolve the M1b UX-parity items and decommission Webflow.
- **Outcome:** polished demo UX, Webflow canceled, dev/deploy runbook documented.
- **Key technical:** name-field submit feedback, interim AI-wait message, accordion arrow sizing, AI-answer styling; landing-page design pass; archive `web-shared/webflow/` as legacy; decide fate of `core/webflow_api.py`.

### M5 (optional infra) — Backend deploy hardening
- **Objective:** make QRAG Lambda ops repeatable so CORS/config changes aren't 26 MB code redeploys over a slow link.
- **Outcome:** config-driven origins and an idempotent prod deploy path.
- **Key technical:** make `ALLOWED_ORIGINS` env-driven (`update-function-configuration`, kilobytes, instant) instead of hardcoded in `app.py`; define a real `prod` stage / committed deployed-state in `.chalice/config.json`; replace the init-only mirror `prod` path with an idempotent update path.