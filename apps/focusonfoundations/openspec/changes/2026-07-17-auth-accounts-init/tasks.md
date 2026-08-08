# Tasks — Auth Accounts Init

## 1. Spec and planning
- [x] 1.1 Capture Randy's kickoff requirements in proposal.md
- [x] 1.2 Record architecture decisions and phase plan in design.md
- [x] 1.3 Add spec delta (specs/app/spec.md) for accounts, sign-in methods, guest mode
- [x] 1.4 Resolve open questions with Randy (UI approach, GitHub deferral, IdP gating, deploy timing) — all four resolved 2026-07-17, see design.md

## 2. Infrastructure (CDK)
- [x] 2.1 Add `lib/auth-stack.ts`: Cognito User Pool (email sign-in, verification, Essentials tier, EMAIL_OTP + password), SPA client, hosted domain prefix
- [x] 2.2 Config-gated Google and Facebook identity providers (Secrets Manager-backed secrets, off until credentials exist)
- [x] 2.3 DynamoDB `fof-user-data-<env>` single-table (on-demand, PITR, encryption)
- [x] 2.4 Instantiate `FofAuthStaging` / `FofAuthProduction` in bin/fof-site.ts (us-west-2)
- [x] 2.5 Stack assertion tests in test/ (15 pass); `cdk synth` passes
- [x] 2.6 Deploy staging stack; record pool/client/domain ids in web env config — deployed 2026-07-17 after Randy's one-time us-west-2 CDK bootstrap. Pool `us-west-2_U25uiNhpb`, client `1umi8t3jeq2la5mfnigg8gjj3b`, domain `fof-auth-staging.auth.us-west-2.amazoncognito.com`. Two deploy fixes along the way: (a) email removed as MFA second factor (Cognito rejects it with email-only recovery); (b) first-attempt rollback retained an empty `fof-user-data-staging` table, adopted on redeploy via `cdk deploy --import-existing-resources`. Staging site deployed; SignUp + SES email delivery verified live.

## 3. Web (Astro)
- [x] 3.1 Auth library wrapping Cognito (sign-up, confirm, sign-in via password and email OTP, forgot/reset, sign-out, session/token state)
- [x] 3.2 `/account/` pages: sign-in, create account, confirm email, forgot password, account home (+ OAuth callback page)
- [x] 3.3 Header auth state (Sign in ↔ Account link via localStorage hint, no auth bundle on non-account pages)
- [x] 3.4 Guest-store lib (`fofGuest.*` localStorage namespace) + guest messaging + migration hook point
- [x] 3.5 Social sign-in buttons (Google/Facebook), hidden until IdPs are enabled in config
- [x] 3.6 Web tests pass (`npm test`, 23), `astro build` clean (438 pages), all 6 `/account/` routes smoke-tested via `astro preview`

## 4. Phase 2 (built + deployed to staging 2026-07-17, session 2)
- [x] 4.1 User-data API: HTTP API + Cognito JWT authorizer + Node lambda in AuthStack (design.md D7 resolved); 8 handler unit tests + stack assertions
- [x] 4.2 Guest→account migration live: `fofGuest.*` uploads on first sign-in, cleared only after server confirmation
- [x] 4.3 Self-serve account deletion (GDPR): account page two-step confirm → partition sweep + Cognito user delete
- [x] 4.4 QRAG chat persistence for signed-in users (guests unchanged); account page lists saved items per app
- [x] 4.5 Verified live end to end with a throwaway user: 401 unauth, save/list/migrate, delete-account (then the throwaway removed via its own API)
- [x] 4.6 Staging-testing feedback fixes: inline confirm (no double sign-in), segmented sign-in selector, QRAG first-question 401 JWT race

## 5. Phase 3 — education-app storage (built + deployed to staging 2026-07-17, session 3)
- [x] 5.1 S3 per-user file storage: `fof-user-files-<env>` bucket + presigned upload/download/list/delete routes (design.md D11); GDPR sweep purges all object versions
- [x] 5.2 Web clients: `user-files.js`, `sqlite-sync.js` (math-quiz sql.js pattern), `applet-session-store.js` (account or guest fallback); account page lists stored files
- [x] 5.3 Verified live: real SQLite file round-trip (upload → list → download → query intact) and delete-account leaving zero S3 versions
- [x] 5.4 Wire logic gates + counting creatures — applet branch merged into parent via PR #50 (2026-07-18, conflicts resolved: README additive, branch-map superset), parent merged back into this branch, and applet-telemetry's flush now also upserts each session to the account (signed-in) or guest store (signed-out); the localhost dev receiver stays for local capture
- [ ] 5.5 Wire math quiz `sqlite-sync` — **post-merge follow-up** — waits until math-quiz is served on the site domain (it's currently a standalone app at `apps/math-quiz/` with its own pages); recipe documented in `web/src/lib/sqlite-sync.js`

## 7. Session 4 — Randy's 2026-07-20 testing feedback (built + deployed to staging)
- [x] 7.1 Hidden-attribute CSS bug (verification-code fields visible early on create/sign-in) fixed; browser suite regression T1.4
- [x] 7.2 Terms/privacy acceptance moved into account creation (required checkbox, recorded as profile `termsConsent` v2024-12-17); header/footer links removed; links added to account + create pages
- [x] 7.3 Nice-name retired from QRAG demos: consent-only guest flow; hash-store logs 'guest' consent events and issues the QRAG JWT pre-question (backend cutover pinned on ROADMAP)
- [x] 7.4 Family page instant render (per-user cache + loading status; cache cleared on auth transitions after the browser suite caught a role leak)
- [x] 7.5 Invite-by-email: SES-sent link with embedded single-use code, custom message, cc-self; auto-join on arrival after sign-in/create; ses:SendEmail scoped to the domain identity
- [x] 7.6 Browser walkthrough updated (T1.4 hidden-fields, T1.5 legal-link relocation, T2.1 terms gate, name-free T7.2, email invite T6.6) — 34/34 PASS
- [x] 7.7 Pins recorded on app ROADMAP: FERPA/COPPA terms-doc update, Pinecone→AWS vector store (50-chunk 431), email/markdown AI-answer ordering

## 6. Later phases (tracked, not this change)
Post-merge follow-ups after PR #54 (`feature/web-site-redo-fof`) — also summarized on `apps/focusonfoundations/ROADMAP.md`.
- [ ] 6.1 Google sign-in — **deferred until the focusonfoundations.org Google Workspace exists** (current Google Cloud lives on the deprecated floodlamp.bio org; Randy sets up the new Workspace ~next week, then console steps in `docs/2026-07-17_fof-auth-staging-test-checklist.md` §D)
- [ ] 6.2 Facebook sign-in (Randy creates Meta for Developers account + app first; infra already config-gated); custom auth domain; anonymous mode; same-email account linking if needed
- [x] 6.3 Family accounts + per-app entitlements — **built + deployed to staging 2026-07-18**: guardian/child roles with single-use guardian invites; guardian-created child accounts (COPPA consent statement recorded, version 2026-07-18; children sign in with guardian-set email+password, typically a parent plus-address); per-app entitlements (`analysis` + `analysisScope` own/family, app-specific overrides beat `*` default); guardian-only child data reads enforced server-side; child deletion = consent revocation (full sweep incl. files + Cognito); children cannot self-delete, self-manage entitlements, or read others; empty families fully cleaned up. `/account/family/` management UI. Verified live end-to-end (guardian → family → child → child data → authz denials → entitlement update → child deletion → guardian deletion → zero residue). Not yet done: hosted analysis tools that consume the entitlements (math_analysis is still local-only), under-13 age capture, and any verifiable-parental-consent step beyond the recorded checkbox statement — revisit before public launch
- [ ] 6.4 Phase 4 (much later): GitHub OIDC shim; payments/credits/BYO-API-key on BILLING hooks; FERPA hardening; nice-name flow retirement
- [ ] 6.5 Before production cutover of account pages: deploy `FofAuthProduction`, fill the production block in `web/src/lib/auth-config.js` (hostname switch keeps production inert until then)
