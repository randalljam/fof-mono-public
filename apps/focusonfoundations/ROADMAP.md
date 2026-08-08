file: apps/focusonfoundations/ROADMAP.md
title: Focus on Foundations — roadmap and vision
last-updated: 2026-07-25_1105

## Vision
Focus on Foundations is moving toward a repo-owned, AWS-hosted public site for source-backed AI Q&A and transcript exploration. The current Astro site already serves the public domains, preserves the QRAG demo workflows from Webflow, and restores transcript indexes for four corpora.

The longer-term direction is to make the site a durable archive and demo platform: easy to inspect locally, safe to deploy through staging, independent of Webflow for serving, and ready to add more vetted corpora and serious-use Q&A experiences without reworking the whole frontend.

## Now / Next / Later
- **Now** — Keep the deployed Astro site stable on staging and production, with current QRAG demo UX, transcript pages, legacy redirects, legal pages, and CloudFront/S3 content deploys documented in the app README.
- **Done (2026-07-25)** — Branch-closeout hygiene: M4b deploy results in README; milestone plans under `docs/plans-web-site-redo/`; OpenSpec baseline preserved as the current behavior contract.
- **Next** — Decommission Webflow after the rollback window, archive or remove legacy Webflow assets, and decide whether `core/webflow_api.py` is still needed once CMS export and upload workflows are no longer Webflow-centered.
- **Next** — Consolidate the dev -> staging -> production runbook now that DNS lives in Route 53 and production is served from CloudFront.
- **Next** — Do a focused landing-page design pass and add optional debug logging behind an explicit flag for troubleshooting QRAG flows without restoring noisy production console output.
- **Later** — Move DNS record ownership into CDK or another tracked infrastructure path instead of leaving the Route 53 record set CLI-managed.
- **Later** — Harden backend deploy operations by making QRAG CORS origins environment-driven and replacing code-only Lambda redeploy workarounds with an idempotent production deploy path.
- **Later** — Consider migrating the PV evacuation transcript pages away from the preserved Van11y rendering path into the same generic transcript/Q&A viewer model used by the other corpora.

## Post-merge follow-ups (after PR #54 / `feature/web-site-redo-fof`)
Tracked here and in `openspec/changes/2026-07-17-auth-accounts-init/tasks.md` — not blockers for merging the site/auth branch.

### OpenSpec leftovers
- **5.5** Wire math-quiz `sqlite-sync` once math-quiz is served on the site domain (recipe in `web/src/lib/sqlite-sync.js`).
- **6.1** Google sign-in — deferred until focusonfoundations.org Google Workspace exists (checklist §D).
- **6.2** Facebook sign-in — needs Meta developer app first; infra already config-gated.
- **6.5** Production auth cutover — deploy `FofAuthProduction`, fill production block in `web/src/lib/auth-config.js`.

### Pinned from accounts/auth testing (2026-07-20, Randy)
- **Terms + Privacy doc updates for child accounts** — the legal docs (2024-12-17) predate accounts, families, and guardian-created child accounts; update them for FERPA/COPPA posture (what learning data is stored, guardian consent/review/deletion rights) before public launch.
- **Pinecone → AWS vector store migration** — Pinecone is $50/mo minimum; consolidate on an AWS-native vector service. Includes the 50-chunk bug: UI 50 × internal 4 = top_k 200 → Pinecone 431 error (see Randy's cursor thread "QRag 50 Error").
- **Email + downloaded-markdown ordering** — the web view now shows the AI answer above the quoted Q&A, but the emailed results and downloaded markdown still put the question/quotes first; move the AI answer to the top in both.
- **Nice-name backend retirement (client done 2026-07-20)** — the site no longer collects names; hash-store now logs 'guest' consent events and still issues the QRAG JWT. Full backend cutover (qrag lambdas accepting Cognito identities, hash-store slimming, plaintext-PII CSV retirement) remains tracked in the OpenSpec change.

## Idea inbox
- 2026-07-10 — Investigate the intermittent `qrag-llm` CORS failure noted in M4 if it recurs; the suspected path is a Lambda error or timeout response that omits CORS headers.
- 2026-07-10 — Add a `?debug=1` or similar debug mode for QRAG demo request tracing, keeping the default console quiet.
- 2026-07-10 — Capture the 15 Route 53 records in CDK once the preferred ownership model is decided.
- 2026-07-10 — Make `ALLOWED_ORIGINS` config-driven for the six QRAG-related Lambdas so origin changes do not require large code package uploads.
- 2026-07-10 — Revisit the PV evacuation Van11y viewer after the generic transcript viewer has more production mileage.
- 2026-07-10 — Expand the site with additional vetted corpora and archive sections only after the current QRAG/transcript/deploy foundation remains stable.
