# Auth Accounts Init

## Why
The site currently has no real user accounts. Identity for the QRAG demos is a session-scoped "nice name" plus HMAC-hashed context logged to a CSV in `[S3-BUCKET]`, with a self-issued 30-day HS256 JWT. That flow cannot support per-user saved work (chat history, configs, quiz progress), compliance obligations (FERPA for kids, GDPR deletion rights), or future payments/AI-credit features. This change establishes modern authentication and per-user data storage as the foundation for all FoF applications.

## Source requirements (captured from Randy, 2026-07-17)
These points are the requirements of record for this initiative, captured from the kickoff voice prompt. Phasing may split them, but none should be silently dropped.

1. **Stay on AWS.** Use AWS-native services (Cognito for auth; DynamoDB assumed for the user database) rather than a third-party auth/identity service. Rationale: existing AWS investment and infrastructure, assumption that AWS is cheapest to scale (most auth vendors are resellers on top of hyperscalers), and willingness to take on AWS's integration overhead early because AI coding absorbs it.
2. **What user accounts store.** (a) For the David Deutsch apps (e.g. QRAG): chat messages, configuration, and analysis files, possibly some content. (b) Database files for tracking applications and especially education applications: math quiz, and the new applets — counting creatures, logic gates. Storage per user is expected to be modest ("normal user account stuff") — do NOT design for large per-user video/audio/file storage.
3. **Security and compliance.** Must be secure. Eventually FERPA-compliant (kids/education) and probably GDPR-compliant — including the user's right to delete their data. Design for this now even if certification work comes later.
4. **Guest mode.** Users can try things without logging in. Message to guests: "your work will be stored in your local session data — if you decide to create an account, you won't lose what you do here." Guest work must migrate into a new account on sign-up.
5. **Anonymous mode** (may be a later phase). A totally private mode where nothing is stored server-side — e.g. ask questions and they just disappear. Working name: anonymous mode (alternatives floated: "disappeared mode").
6. **Authentication methods.**
   - Email + password (username is an email; email confirmation required).
   - Social sign-in via what AWS/Cognito supports (OAuth): Google, Facebook, and GitHub to start.
   - Email-a-code sign-in (passwordless option): user can log in with a code instead of a password. A typical emailed 6-digit code the user types in is fine; prefer whatever AWS already has built in if smoother.
7. **Standard account flows.** Reset password, create account ("new here?"), confirm email — the typical set.
8. **Cutover from nice-name flow.** Move away from the current session "user nice name" identification toward accounts — but do not put the whole site's functionality behind an account wall; users must still be able to try things (see guest mode).
9. **Payments and AI/API features (later phase — put hooks in now).** Eventually include payments. Enable AI/API features where a user can bring their own API key or purchase credits. Much of the site requires no payment; design the account model so payments/credits/keys attach cleanly later.
10. **Phasing.** Implementing in phases is acceptable; take the work as far as possible per session and pause to ask questions when decisions need Randy.
11. **Family accounts and per-app access control** (captured 2026-07-18; implementation may be a later phase, but the accounts setup must be designed for it):
    - Accounts need **per-application access options** — e.g. for the education apps, whether an account has access to the **analysis tools** (like math quiz's `math_analysis`), separate from access to the app itself.
    - When an account does have analysis access, there's a second setting: scope — access to **only its own data**, or to **other associated accounts'** data.
    - This requires a **family account** concept: parents have access to some tools, sites, and content that the kids' accounts don't. Parents can see their own files too (for testing, or for parent-facing content — e.g. "how computers add numbers"), but **primarily parents need access to their kids' accounts** — that's the main use of the association.
    - The goal driving this: get the education apps set up the way they'll actually be used, pushed live, and available to other people — not just this family.

## What Changes
- Add an `AuthStack` to the existing CDK app (`apps/focusonfoundations/infra`): Cognito User Pool per environment (staging, production) with email sign-in, email verification, password auth, and email-OTP passwordless sign-in; a browser (SPA) app client; a Cognito hosted domain for OAuth redirects; config-gated Google and Facebook identity providers; and a DynamoDB user-data table (on-demand, single-table design) for per-user app data.
- Add account UI to the Astro site under `/account/`: sign in (password or emailed code), create account, confirm email, forgot/reset password, and a signed-in account page — custom-branded pages backed by Cognito APIs, not the Cognito hosted UI look.
- Add a site auth library (`src/lib/auth*`) wrapping Cognito token handling, session state, and a header sign-in/account indicator.
- Add a guest-mode storage library that namespaces unauthenticated work in browser local storage and shows the "your work is stored locally; creating an account keeps it" message, with a migration hook that runs at account creation.
- Record the cutover plan: QRAG demos keep working for guests; the nice-name + hash-store flow remains until accounts reach parity, then is retired in a later phase.

## Non-Goals (this change)
- No GitHub sign-in yet — Cognito has no native GitHub IdP; it needs an OIDC shim (own later phase).
- No payments, credits ledger, or bring-your-own-API-key implementation — only the data-model hooks.
- No anonymous ("nothing stored") mode yet — later phase; named and reserved in the design.
- No FERPA/GDPR certification work — but the design must not block it (deletable per-user data, minimal PII, no plaintext PII logging in the new path).
- No migration of existing hash-store CSV history into accounts.
- No removal of the existing nice-name/hash-store flow yet.
