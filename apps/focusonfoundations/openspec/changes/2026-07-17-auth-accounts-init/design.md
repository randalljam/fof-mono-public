# Design — Auth Accounts Init

## Architecture decisions

### D1. Cognito User Pool, Essentials tier
AWS Cognito User Pools provide the account store, hosted OAuth endpoints for social sign-in, email verification, password reset, and token issuance (OIDC ID/access/refresh JWTs). The **Essentials** feature tier is required because it enables choice-based sign-in (`USER_AUTH` flow) with **EMAIL_OTP** — the native "email me a 6-digit code" passwordless option — alongside password (SRP) sign-in. Pricing: free for the first 10,000 MAUs, ~$0.015/MAU beyond; effectively $0 at current scale.

### D2. Region and environments
Auth stacks deploy to **us-west-2**, matching all existing Lambda/API/data infrastructure (the static-site stacks are us-east-1 only because CloudFront ACM certs require it; Cognito has no such constraint). Two fully separate stacks/pools: `FofAuthStaging` and `FofAuthProduction` — separate user pools, clients, domains, and tables, mirroring the static-site staging/production split.

### D3. Custom-branded UI, Cognito behind it
Account pages are normal Astro pages styled like the rest of the site. Email/password and email-OTP flows call Cognito APIs directly from the browser via the Amplify v6 modular auth library (`aws-amplify/auth` — tree-shakeable, supports `USER_AUTH`/EMAIL_OTP, SRP, token refresh, and social redirect). The Cognito **hosted domain** (default prefix domain, e.g. `fof-auth-staging.auth.us-west-2.amazoncognito.com`) is used only as the OAuth redirect endpoint for social sign-in; a custom `auth.focusonfoundations.org` domain can replace it later without app changes.

### D4. Social identity providers
- **Google, Facebook**: native Cognito IdPs. Wired in CDK behind context/config flags — each activates only when Randy creates the developer-console app and supplies client id + secret (secret referenced from Secrets Manager, never committed). Until then the pool runs email-only.
- **GitHub**: NOT a native Cognito IdP (GitHub's OAuth is not OIDC-compliant). Requires a small OIDC-shim (API Gateway + Lambda wrapping GitHub OAuth into OIDC endpoints) registered as a Cognito OIDC provider. Deferred to its own phase.
- Account linking: Cognito treats same-email social and password users as distinct identities by default; phase 2 adds a PreSignUp Lambda trigger to link same-email identities if that becomes a real user-confusion problem.

### D5. Emails via SES
Cognito's default mailer is capped at ~50 emails/day — fine for the first staging deploy, not for production. The stack accepts an optional SES-verified sender (e.g. `accounts@focusonfoundations.org`); SES is already in use by the send-email Lambda. Configure Cognito's email sending to SES mode when the sender identity is verified.

### D6. DynamoDB single-table user data
One on-demand table per environment, `fof-user-data-<env>`:
- `PK = USER#<cognito-sub>`, `SK` patterns per entity:
  - `PROFILE` — display name, preferences, consent records (versioned), account flags.
  - `APP#<app>#<entity>#<id>` — per-app records, e.g. `APP#qrag#chat#<ts>` (chat messages), `APP#qrag#config#<name>`, `APP#mathquiz#session#<ts>`, `APP#counting-creatures#state`, `APP#logic-gates#progress`.
  - `BILLING#...` — reserved hook: credits ledger entries, API-key references (keys themselves go in Secrets Manager or encrypted attributes, never plaintext), plan/entitlements. Not implemented this change; the key-space and an `entitlements` attribute on `PROFILE` are reserved so payments bolt on without remodeling.
- Point-in-time recovery on; server-side encryption (AWS-managed) on.
- GDPR/FERPA posture: all of a user's data lives under one partition key → account deletion is a partition sweep plus Cognito `DeleteUser`. No PII beyond what the user supplies; no plaintext PII in logs.
- Modest-size assumption (per requirement 2): items are KB-scale JSON. If an artifact ever exceeds ~300 KB, it goes to S3 under `user-data/<sub>/...` with a pointer item — pattern documented now, not built.

### D7. Data-plane API (phase 2) — RESOLVED 2026-07-17
Built CDK-native: API Gateway HTTP API + Cognito user-pool JWT authorizer + a Node 20
Lambda (`infra/lambda/user-data/`), all inside `AuthStack` — one stack, direct table
grants, no chalicelib mirror. Chose this over Chalice because the API is inseparable from
the auth stack (authorizer, table, pool permissions) and the rest of this app's infra is
already TypeScript CDK. Routes: `GET/PUT/DELETE /user/data...` (per-app entries),
`POST /user/migrate` (guest upload), `DELETE /user/account` (partition sweep + Cognito
user delete). Every route is JWT-authorized and partition-scoped to the token's `sub` —
the browser never holds AWS credentials.

### D8. Guest mode and migration
Unauthenticated users work in `localStorage` under a `fofGuest.` namespace via a small storage lib (`guest-store.js`). Guest-facing copy: work is saved locally in this browser; creating an account keeps it. On first sign-in after account creation, a migration hook enumerates `fofGuest.*` keys and (phase 2, once the data API exists) uploads them to the user's partition, then clears the namespace. Phase 1 ships the lib, the messaging, and the hook point.

### D9. Anonymous mode (reserved, later phase)
A "nothing stored" mode: no server-side persistence, no local persistence beyond the in-memory page session, and QRAG calls flagged so backends skip exchange capture. Reserved name: **anonymous mode**. Requires backend cooperation (hash-store/exchange logging bypass), so it is its own phase.

### D10. Nice-name flow cutover
Phase 1 leaves the existing consent + nice-name + hash-store flow untouched for guests. Signed-in users later (phase 2/3) skip the nice-name box — their identity is the Cognito sub, and QRAG `user_id` becomes the sub (or an HMAC of it) instead of `userEmailHmacHash`/`'NA'`. Full retirement of hash-store's plaintext-PII CSV happens only after accounts + guest mode cover its telemetry duties.

### D11. Education-app storage (phase 3) — decided 2026-07-17
Two storage shapes, matched to how the apps actually persist:
- **SQLite database files** (math quiz's sql.js `db.export()` blobs, ~50–260 KB/user): a
  versioned private S3 bucket `fof-user-files-<env>` keyed `user-files/<sub>/<app>/<name>`.
  The lambda issues short-lived presigned PUT/GET URLs (JWT-authorized, partition-scoped);
  bytes move browser↔S3 directly. Client: `user-files.js`; sql.js pull/push wrapper:
  `sqlite-sync.js`. Account deletion purges **all object versions** (versioned bucket —
  a plain delete would leave copies recoverable, breaking the GDPR story).
- **Applet session logs** (logic gates / counting creatures telemetry sessions, JSON):
  these fit the existing DynamoDB data API — no SQLite needed. `applet-session-store.js`
  saves signed-in sessions as `APP#<applet>#session-<stamp>` and guest sessions to
  `fofGuest.*` (which already migrates on sign-up). It replaces applet-telemetry's
  dev-only `localhost:8787/api/save-session` flush.
- **Integration status:** the applets live on `feature/counting-creatures-applet` (not this
  branch), so wiring happens when that branch merges — point applet-telemetry's flush at
  `saveAppletSession()`. Math quiz is a standalone app not served on the site domain; its
  `sqlite-sync` wiring waits until it's hosted under focusonfoundations.org.

### D12. Family accounts and per-app entitlements — BUILT 2026-07-18
Implemented as sketched below, with these concretizations: child accounts are created by
guardians via `AdminCreateUser` (no self-signup; email is typically a parent plus-address;
password guardian-set and permanent); consent is a recorded statement (guardian sub +
version + timestamp) required at creation and shown in the UI — a stronger verifiable-
parental-consent mechanism (e.g. card verification) is deliberately deferred until public
launch; guardian invites are single-use codes expiring in 7 days with the family id
embedded; children cannot self-delete (guardian-only, as consent revocation), self-manage
entitlements, or read any other account; the last member leaving removes the whole family
record. Routes live in `infra/lambda/user-data/family.mjs`; UI at `/account/family/`.
Original sketch:
- **Entitlements on PROFILE** (the hook reserved in D6): a per-account map like
  `entitlements: { 'math-quiz': { app: true, analysis: true, analysisScope: 'family' } }`.
  Absence of a key = default access (most site content needs no account at all).
- **Family as a relation, not a shared login**: each person has their own Cognito user.
  A family is a small item set in the user-data table — e.g. `FAMILY#<familyId>` partition
  with `MEMBER#<sub>` items carrying a role (`guardian` | `child`), plus a
  `PROFILE.familyId` back-pointer on each member. Guardians' `analysisScope: 'family'`
  resolves through this relation to the kids' partitions.
- **Enforcement lives in the user-data API** (the lambda already scopes every route to the
  token's sub): a guardian reading a child's data goes through new explicitly-scoped
  read-only routes (e.g. `GET /family/members`, `GET /family/member/{sub}/data?app=…`)
  that verify the guardian role server-side. Kids' tokens never gain cross-account access.
- **Kid accounts intersect FERPA/COPPA** (proposal req. 3): under-13 accounts need
  guardian-created/consented flows — design them together with this phase, not separately.
- **UI**: account page grows a Family section (create family, invite/link member, role
  badges); analysis tools (e.g. a future hosted math_analysis) check entitlements client-side
  for UX but rely on the API for actual authorization.

## Phases
1. **Phase 1 (this change):** AuthStack CDK (pool, client, domain, gated Google/Facebook IdPs, DynamoDB table), custom account UI + auth lib, header auth state, guest-store lib + messaging, tests, staging deploy.
2. **Phase 2:** user-data API with Cognito authorizer; QRAG chat/config persistence for signed-in users; guest→account data migration live; account deletion (GDPR) end-to-end; same-email account linking if needed.
3. **Phase 3:** GitHub OIDC shim; custom auth domain; anonymous mode (with backend no-store flag); education-app (math quiz, applets) persistence.
4. **Phase 4:** payments/credits/BYO-API-key on the reserved BILLING hooks; FERPA hardening (parental consent flows, data-minimization review); nice-name flow retirement.

## Open questions — resolved 2026-07-17
1. **Account UI:** custom-branded site pages (Cognito invisible behind them). Decided.
2. **GitHub:** deferred to phase 3 (OIDC shim). Decided.
3. **Google/Facebook:** wired config-gated now; launch email-only, add console credentials later. Decided.
4. **Deploy staging:** approved. Deploy was blocked mid-session because us-west-2 has no CDK bootstrap and creating the CDKToolkit IAM roles needs Randy's explicit approval — see tasks.md 2.6 for the exact commands.

## SES sender (resolved)
`focusonfoundations.org` is a verified SES domain identity in us-west-2 with production access enabled, so the pools send account email as `accounts@focusonfoundations.org` (default set in `infra/cdk.json` context `authSesFromEmail`), which activates email-OTP passwordless sign-in from the first deploy.
