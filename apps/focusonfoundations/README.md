file: apps/focusonfoundations/README.md
title: Focus on Foundations — Astro site + AWS static hosting
last-updated: 2026-07-25_1105

**Static Astro frontend for focusonfoundations.org**, replacing the Webflow embed stack while keeping existing QRAG API Gateway/Lambda backends.


## Key URLs

| Site | URL |
|------|-----|
| Production (apex) | https://focusonfoundations.org |
| Production (www) | https://www.focusonfoundations.org |
| Staging | https://staging.focusonfoundations.org |
| Local dev | http://localhost:4321 |

### Webflow rollback site (dormant old site)

Since the M3 DNS cutover (2026-07-03), `www.focusonfoundations.org` serves the Astro site. The **only** place to view the old Webflow site is the staging project URL (Webflow subscription kept for rollback):

- **Home:** https://floodlamp-8c9d00d6ef3e90c375de806594d04.webflow.io/
- **FDA town halls index:** https://floodlamp-8c9d00d6ef3e90c375de806594d04.webflow.io/fl-fda-vth-index
- **Deutsch interviews index:** https://floodlamp-8c9d00d6ef3e90c375de806594d04.webflow.io/deutsch-interviews-index
- **Sovereign Child index:** https://floodlamp-8c9d00d6ef3e90c375de806594d04.webflow.io/sov-child-transcripts-index
- **PV evac Van11y example:** https://floodlamp-8c9d00d6ef3e90c375de806594d04.webflow.io/pv-evac-docs/2023-09-20-pvsd-wfpd---wildfire-preparedness-parent-presentation-1


## Milestone plan files

Completed milestone plans for this branch live under `docs/plans-web-site-redo/`:

| Milestone | Plan file |
|-----------|-----------|
| M1 — Astro site | `docs/plans-web-site-redo/2026-06-26_web-site-redo-fof_M1_aws-astro-site_a75a8329.plan.md` |
| M1b — Demo + CORS fix | `docs/plans-web-site-redo/2026-07-02_web-site-redo-fof_M1b_fix-demo-and-cors_80ee62b9.plan.md` |
| M2 — Staging deploy | `docs/plans-web-site-redo/2026-07-02_web-site-redo-fof_M2_staging_deploy_213f294f.plan.md` |
| M3 — Production cutover | `docs/plans-web-site-redo/2026-07-03_web-site-redo-fof_M3_production_cutover_5b3c136a.plan.md` |
| M4 — UX polish | `docs/plans-web-site-redo/2026-07-03_web-site-redo-fof_M4_ux_polish_f6429a44.plan.md` |
| M4b — Transcript pages | Not checked in (Cursor-local plan `m4b_transcript_pages_ed4176e0`); work landed via PR #46 |


## Layout

```text
apps/focusonfoundations/
  web/          Astro static site (portable — no CDK imports)
  infra/        AWS CDK stacks (S3 + CloudFront + ACM + Route 53)
  scripts/      Shared helper scripts (incl. Webflow manifest export)
```


## Prerequisites

- Node.js 20+ and npm
- AWS CLI v2 configured (`aws sts get-caller-identity`)
- AWS CDK (installed locally via `infra/package.json`)

Check tooling:

```bash
./scripts/check-tooling.sh
```


## Local development

```bash
cd apps/focusonfoundations/web
cp .env.example .env
npm install
npm run dev      # http://localhost:4321
npm run build
npm run preview  # review production build locally
npm test         # 12 tests (QRAG + transcript manifests/redirects)
```


## Infrastructure (us-east-1)

CDK creates **staging** and **production** stacks:

| Stack | Domains | DNS records |
|-------|---------|-------------|
| `FofSiteStaging` | `staging.focusonfoundations.org` | Route 53 CNAME (see DNS section) |
| `FofSiteProduction` | `focusonfoundations.org`, `www.focusonfoundations.org` | Route 53 A/AAAA aliases |

```bash
cd apps/focusonfoundations/infra
npm install
npm run synth

export CDK_DEFAULT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
export AWS_REGION=us-east-1

npm run deploy:staging
npm run deploy:production
```

After CDK deploy, save stack outputs for content deploys:

```bash
cd ../web
node scripts/save-deploy-config.js staging
node scripts/save-deploy-config.js production
```


## Content deploy (after local + staging review)

The existing full-site deploy runs a fresh Astro build, then uses `aws s3 sync --delete` across the site. S3 sync may decide uploads from file size and modification time rather than content. Use it only for intentional full-site releases:

```bash
cd apps/focusonfoundations/web
npm run deploy:staging
# validate https://staging.focusonfoundations.org

npm run deploy:production   # only after staging sign-off
```

### Safe scoped production deploy for unlisted pages
For an already-built standalone/unlisted page, deploy an explicit source allowlist beneath one production URL prefix:

```bash
cd apps/focusonfoundations/web
npm run deploy:static-page -- \
  --source /absolute/path/to/page-output \
  --slug applets/counting-creatures \
  --allow index.html \
  --allow assets \
  --base-href /applets/counting-creatures/
```

For a partial update that must not remove other keys under the same slug (for example, replace only `index.html` / CSS / JS and leave `assets/` alone), add `--no-delete`.

The optional `--base-href` adapts relative asset URLs for an extensionless route without changing the source HTML; it must exactly match the deployed slug. The tool compares content hashes, reports additions/changes/deletions/unchanged files, validates AWS account `[AWS-ACCOUNT-ID]`, and requires the exact production confirmation phrase it displays. It never builds Astro, never targets staging, never reads or changes S3 keys outside the slug, and invalidates only the slug and its descendants. Without `--no-delete`, remote keys under the slug that are not in the allowlist are reported as deletions. Symlinks, traversal, and prefix escapes abort the deploy.


## AWS resources (account [AWS-ACCOUNT-ID], us-east-1)

| Environment | S3 bucket | CloudFront ID | CloudFront domain |
|-------------|-----------|---------------|-------------------|
| Staging | `fofsitestaging-sitebucket397a1860-itzdhz8si8wd` | `E2P44CTJ04YSLS` | `d1w2h59hunmi32.cloudfront.net` |
| Production | `[S3-SITE-BUCKET]` | `E1ZC4ZN75O9QM4` | `dulamv7pmn3ar.cloudfront.net` |

**ACM certificates (us-east-1):**

| Cert | Domains | ARN |
|------|---------|-----|
| Staging | `staging.focusonfoundations.org` | `arn:aws:acm:us-east-1:[AWS-ACCOUNT-ID]:certificate/4582158a-ecb4-4902-b32c-4434c1bf4deb` |
| Production | `focusonfoundations.org`, `www.focusonfoundations.org` | `arn:aws:acm:us-east-1:[AWS-ACCOUNT-ID]:certificate/ce92bf3f-2f1d-4bdc-814e-2533499cca13` |


## DNS (Route 53 — cut over 2026-07-03)

- **Hosted zone:** `Z02230973OPK1REKMSJ5S` (`focusonfoundations.org`)
- **Nameservers:** `ns-1713.awsdns-22.co.uk`, `ns-548.awsdns-04.net`, `ns-1516.awsdns-61.org`, `ns-204.awsdns-25.com`

Record set (15 records; CLI-managed — CDK ownership is a future milestone). See M3 plan for the full table.


## Routes

| Path | Purpose |
|------|---------|
| `/` | Landing page |
| `/demos/` | Demo hub |
| `/demos/deutsch/` | Deutsch Interviews QRAG |
| `/demos/fda-town-halls/` | FDA COVID-19 Town Halls QRAG |
| `/demos/pv-evacuation/` | PV School Evacuation QRAG |
| `/demos/sovereign-child/` | Sovereign Child QRAG |
| `/transcripts/` | Transcript corpus hub |
| `/transcripts/deutsch/` | Deutsch source index (95 items) |
| `/transcripts/fda-town-halls/` | FDA town halls source index (100 items) |
| `/transcripts/sovereign-child/` | Sovereign Child source index (8 items) |
| `/transcripts/pv-evacuation/` | PV evac source index (3 items) |
| `/transcripts/<corpus>/<slug>/` | Per-document transcript + Q&A viewer |
| `/terms/`, `/privacy/` | Legal pages |
| `/applets/counting-creatures/` | Counting Creatures (unlisted: noindex, no nav links) |
| `/applets/logic-gates/` | Logic Gates (unlisted: noindex, no nav links) |
| `/fda-town-halls-qrag-demo/` | Legacy redirect → FDA demo |
| `/deutsch-interviews-index`, `/fl-fda-vth-index`, `/sov-child-transcripts-index` | Legacy index redirects → `/transcripts/...` |
| `/deutsch-transcripts/<slug>/`, `/fda-c19-townhalls/<slug>/`, etc. | Legacy item redirects → `/transcripts/...` |


## Transcript corpora (M4b)

Source HTML lives on S3 bucket **`fofpublic`** (us-west-2). The Astro site fetches it client-side (same pattern as the old Webflow embed). PV evacuation uses committed markdown + Van11y accordion (legacy mechanism preserved).

**Re-export manifests** after Webflow CMS changes:

```bash
cd /path/to/fof-mono
.venv/bin/python3 apps/focusonfoundations/scripts/export_webflow_corpus_manifests.py
# writes apps/focusonfoundations/web/src/corpus/*.json and pv-evac/*.md
cd apps/focusonfoundations/web && npm run build
```

Requires `WEBFLOW_API_KEY_FOF_CMS` in repo-root `.env`.


## Applets

Unlisted interactive teaching pages under `/applets/` (React islands via `@astrojs/react`; reachable only by direct link — robots `noindex`, no nav links).

**Counting Creatures** (`/applets/counting-creatures/`) teaches number bases: humans (base 10), three-toed sloths (base 6), computers (base 2). Component: `web/src/components/applets/CountingCreatures.jsx`; gate/adder logic + number words: `web/src/lib/counting-creatures.js`. **Screen copy** (titles, captions, narration): `web/copy/counting-creatures.md` — one section per bottom-dot screen.

**Logic Gates** (`/applets/logic-gates/`) teaches digital logic: a switch and a light, then NOT → OR → AND → XOR → NAND (interactive circuits with live truth tables and prediction quizzes), a mystery-gate game, combining XOR + AND into a half adder, a gate-level full adder, and a chained-adder finale that adds two 2-bit binary numbers. Component: `web/src/components/applets/LogicGates.jsx`; gate/adder logic: `web/src/lib/logic-gates.js`. **Screen copy**: `web/copy/logic-gates.md`.

After editing copy markdown, sync into the generated modules the applets import:

```bash
cd apps/focusonfoundations/web
npm run sync:copy
```

Field definitions and workflow: `web/copy/applet-markdown-field-guide.md`.

Narration uses pre-generated OpenAI TTS clips (`gpt-4o-mini-tts`, voice `nova`) served from `web/public/audio/<applet>/` with a browser speechSynthesis fallback. **Mp3 clips are gitignored** — canonical copies live on `[S3-FILES-BUCKET]` (`manifests/focusonfoundations_applet-audio.manifest.jsonl`). Pull before local dev, test, or deploy:

```bash
cd apps/focusonfoundations/web
npm run audio:pull
```

After changing any **spoken** line in the markdown, run `sync:copy`, regenerate clips and the manifest for that applet, then upload to S3 (from repo root):

```bash
cd apps/focusonfoundations/web
OPENAI_API_KEY=... node scripts/generate-tts.js --applet logic-gates   # default: counting-creatures; add --force to re-voice
cd ../../..
.venv/bin/python3 core/s3_archive.py refresh --area focusonfoundations_applet-audio --execute
.venv/bin/python3 core/s3_archive.py upload --area focusonfoundations_applet-audio --execute
git add manifests/focusonfoundations_applet-audio.manifest.jsonl web/src/lib/*-audio-manifest.js
```

Then `npm test`. Deploy (`npm run deploy:staging`) auto-pulls missing audio before build.

### Applet interaction logging (local dev)
Applets capture learner interactions — every click with timing, per-step time, and quiz attempts/tries — buffered in `sessionStorage` and POSTed to a localhost-only receiver that writes one SQLite file per session to `web/_data/applet-sessions/` (gitignored; same single-session conventions as math-quiz). The deployed static site has no receiver, so logging is a silent no-op there. To capture locally, run alongside `npm run dev`:

```bash
cd apps/focusonfoundations/web
npm run telemetry   # tools/telemetry_server.py on http://localhost:8787
```
Inspect a captured session (`../../../.venv/bin/python3` = repo venv; add `--events` for the raw timeline):

```bash
../../../.venv/bin/python3 tools/telemetry_report.py _data/applet-sessions   # newest file; or pass a specific .sqlite
```
Schema and conventions: `web/docs/2026-07-11_applet-interaction-logging.md`. To have an AI assess a student's session, attach the `.sqlite` file together with `web/docs/2026-07-12_applet-session-llm-analysis.md` (data dictionary + analysis prompt).


## CORS

### QRAG Lambdas (Chalice)

If API calls fail from new origins, add these to Chalice/API Gateway CORS config:

- `http://localhost:4321`
- `https://staging.focusonfoundations.org`
- `https://focusonfoundations.org`
- `https://www.focusonfoundations.org`

### fofpublic S3 bucket (transcript HTML)

Bucket `fofpublic` (us-west-2) CORS allows GET from:

- `https://focusonfoundations.org`
- `https://www.focusonfoundations.org`
- `https://staging.focusonfoundations.org`
- `http://localhost:4321`
- `https://floodlamp-8c9d00d6ef3e90c375de806594d04.webflow.io` (rollback site)

Updated 2026-07-04 for M4b (apex + staging + localhost added).


## Rollback

- **Full DNS rollback:** at Hover, switch nameservers back to `ns1.hover.com` / `ns2.hover.com`. The dormant Hover zone still points apex/www at Webflow.
- **Content rollback:** redeploy a known-good `dist/` build and invalidate CloudFront `/*`.
- **fofpublic CORS rollback:** restore prior two-origin config via `aws s3api put-bucket-cors` if needed.


## M4b execution notes (2026-07-04 / 2026-07-05)

Branch: `feature/web-site-transcript-pages` (forked from `feature/web-site-redo-fof` at `ef4db08`).

- Restored transcript index + per-document pages for Deutsch (95), FDA town halls (100), Sovereign Child (8), and PV evacuation (3) under `/transcripts/`.
- 209 legacy item redirect stubs + 3 legacy index redirects (`deutsch-interviews-index`, `fl-fda-vth-index`, `sov-child-transcripts-index`).
- fofpublic CORS updated 2026-07-04 (apex, staging, localhost added); verified for all five origins.
- Web unit tests: **14/14 pass** (7 QRAG + 7 transcript, including rendered transcript/Q&A fetch + toggle regression).
- Staging deploy 2026-07-04 ~22:13 PT → CloudFront `E2P44CTJ04YSLS`, invalidation `I4GLCZHJ3V70I3BBHQRGJZJS42`.
- Production deploy 2026-07-05 ~04:55 PT → CloudFront `E1ZC4ZN75O9QM4`, invalidation `I33WGY8Y45M213PG9R5FQABBLW`.
- Post-deploy verified: `/transcripts/deutsch/` 200 on staging + production; legacy redirects work; apex-origin S3 transcript fetch returns CORS header.
- Hotfix 2026-07-05: fixed broken transcript viewer browser loader (`define:vars` inline script emitted a non-module `import`), added regression coverage, redeployed staging invalidation `I10IKHRPNTZH8H53PECDIT3L03` and production invalidation `I4QZRY8N774Y55RSEM6SGAHI31`.

**Carry-forwards:** Webflow decommission (manifests are now CMS data of record); consider migrating PV evac off Van11y later. Milestone plans moved to `docs/plans-web-site-redo/` (2026-07-25).
