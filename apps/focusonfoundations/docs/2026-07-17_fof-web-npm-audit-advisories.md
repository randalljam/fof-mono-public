file: 2026-07-17_fof-web-npm-audit-advisories.md
title: FoF web — pre-existing npm audit advisories (follow-up task)
last-updated: 2026-07-17_0727
ai: Claude Code - Fable 5
session: `fof-website/auth-accounts-init kickoff`

**Task for a future session/agent:** resolve the `npm audit` advisories in
`apps/focusonfoundations/web`. These pre-date the accounts work (observed 2026-07-17 while
adding `aws-amplify`; none are introduced by it). Do this on its own branch off
`feature/web-site-redo-fof` (or `main` after merge), not mixed into feature work.

## What npm audit reports
Run `npm audit` in `apps/focusonfoundations/web`. Two advisory groups:

1. **astro <= 7.0.0-beta.6 — high severity** (project is on `astro ^5.2.0`):
   - XSS in `define:vars` via incomplete `</script>` sanitization (GHSA-j687-52p2-xcff)
   - Server-island encrypted params replay (GHSA-xr5h-phrj-8vxv)
   - Reflected XSS via unescaped slot name (GHSA-8hv8-536x-4wqp)
   - XSS via unescaped attribute names in spread props (GHSA-jrpj-wcv7-9fh9)
   - Host-header SSRF in prerendered error-page fetch (GHSA-2pvr-wf23-7pc7)
   - Also pulls a vulnerable `esbuild` transitively.
2. **yaml 2.0.0–2.8.2 — moderate** — stack-overflow on deeply nested YAML
   (GHSA-48c2-rrv3-qjmp), reached only through `yaml-language-server` (editor tooling
   dependency, not runtime).

## Risk context
The site is a fully static build (S3 + CloudFront, no SSR, no server islands, no dev server
exposed), so most of these are build-time/dev-time rather than production-exposed. Still
worth clearing: some advisories involve HTML escaping in the build output path, and staying
current keeps future upgrades cheap.

## Suggested fix procedure
1. `cd apps/focusonfoundations/web`
2. `npm audit fix` first (non-breaking). Re-run `npm audit`; the astro group likely needs a
   minor/patch bump within v5 — prefer the latest fixed 5.x over jumping majors.
3. Verify: `npm test` (24+ tests), `npm run build` (438+ pages), then serve `dist/` with
   `npx astro preview` and spot-check `/`, a demo page, a transcript page, and `/account/sign-in/`.
4. If a fix requires astro v6+/v7, stop and flag the major-version decision to Randy instead
   of forcing it.
5. Commit on a `fix/fof-web-npm-audit` branch and push.
