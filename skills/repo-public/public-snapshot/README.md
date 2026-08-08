file: skills/repo-public/public-snapshot/README.md
title: Publish a filtered public snapshot of fof-mono
source-github-url: original
source-guide-url: original
history:
  - 2026-08-07 · Randy · Cursor (Grok 4.5) `public snapshot email checklist` — redact HMAC secret prefix `[HMAC-SECRET-PREFIX]` → `[HMAC-SECRET-PREFIX]` in snapshot-replace + confirm terms; KEEP `docs/2025-03-14_aws-prod`
  - 2026-08-07 · Randy · Cursor (Grok 4.5) `public snapshot email checklist` — hardcode randalljam GitHub noreply as default public commit email in mirror_export_branch.sh
  - 2026-08-07 · Randy · Cursor (Grok 4.5) [skills public-safe harden](2026-08-07_skills_public-safe_harden_9497f598) — confirm terms → excluded confirm-redaction-terms.md; extend replace/exclude for [S3-FILES-BUCKET], site bucket, Fly app, agents-md run-log
  - 2026-08-07 · Randy · Cursor (Grok 4.5) [update-from-main skill](fc97c720-3e68-4413-b0fd-692ca5e17d89) — link selective main→export bring-over skill (`skills/repo-public/update-from-main`)
  - 2026-08-07 · Randy · Cursor (Grok 4.5) `export confirm exclude single source` — confirm_export_checkout loads exclude paths from origin/main snapshot-exclude.md (no hardcoded second list)
  - 2026-08-06 · Randy · Cursor (Grok 4.5) `public snapshot copyright check` — keep snapshot-exclude.md private on main like snapshot-replace.md; pare_down reads both from origin/main
  - 2026-08-06 · Randy · Cursor (Grok 4.5) `public snapshot copyright check` — hand-merge export-branch skill docs onto main (confirm_export_checkout, pare-down wipe/unmount notes); `file:` and command paths → repo-public
  - 2026-08-05 · Randy · Cursor (Grok 4.5) `public snapshot copyright check` — add confirm_export_checkout.sh (exclusions + redaction spot-check for the export branch)
  - 2026-08-05 · Randy · Cursor (Grok 4.5) `public snapshot copyright check` — pare_down_pass.sh wipes non-mount exclude leftovers and unlinks all local-files mount symlinks except docs/personal
  - 2026-07-31 · Randy · Claude Code (Fable 5) `venv fix review + repo cleanup` — initial skill: exclude-list snapshot build, PII sweep, fof-mono-public push flow

**Use this to publish (and periodically re-publish) a filtered snapshot of the private `fof-mono` repo into the public `fof-mono-public` repo, with a PII sweep gate before every push.**


## What this does (for humans)
Builds a clean export of the current `main` tree (tracked files only — gitignored/local files can never leak), deletes everything on the exclude list, applies **publish-time replacements** (`snapshot-replace.md`: `find==>replace`, literal or `regex:`-prefixed — redacts identifiers like the AWS account ID and personal emails in the stage copy while the private repo keeps functional values), runs a heuristic PII sweep over what remains, and — only with `--execute` — rsyncs the result into a clone of `fof-mono-public` and pushes it as a single snapshot commit. Private git history is never carried over; each publish is one commit like `snapshot: 2026-07-31 from private abc1234`. Re-running on later dates accumulates snapshot commits, so the public repo shows build-in-public progress without exposing private history.


## Prerequisites
- Public repo exists: `github.com/FocusOnFoundationsNonprofit/fof-mono-public` (create empty, no README — the build supplies one). Override with env `FOF_PUBLIC_REMOTE` / clone location with `FOF_PUBLIC_CLONE` (default `~/Documents/Code/fof-mono-public`).
- Optional but recommended: `docs/personal/pii-terms.md` (local-only mount) listing personal terms — kid names, street, etc. — one per line. The sweep auto-loads it when present.
- License: **MIT** (decided 2026-07-31) — the root `LICENSE` file is tracked and flows into every snapshot.


## Private list files (edit on `main` only — never ship)
These live under `skills/repo-public/public-snapshot/` on **`main`** and are on the exclude list themselves. The export branch and public snapshot must not track them. `pare_down_pass.sh` and `confirm_export_checkout.sh` load them via `git show origin/main:…` (`build_public_snapshot.sh` reads the local copies on a `main` checkout).

| File | Role | Format |
|---|---|---|
| `snapshot-exclude.md` | Paths that never go public | Markdown `##` section headers + one repo-relative path prefix per line (`#` comments OK) |
| `snapshot-replace.md` | Publish-time find→replace (names the sensitive strings) | `##` sections; rules `find==>replace`; optional `regex:` prefix on find |
| `confirm-redaction-terms.md` | Spot-check terms for `confirm_export_checkout.sh` (broader than replace finds) | `##` sections `Identifier / host / address terms` and `Personal-name terms`; one term per line |

Edit these on the primary/`main` checkout, push `main`, then `git fetch origin` in the export checkout before re-running pare-down.


## Review-branch workflow (canonical, adopted 2026-07-31)
The pared-down public tree lives on branch **`export/to-fof-mono-public`** so it can be inspected commit-by-commit before anything ships. Its history: lineage record → one exclusion commit per `snapshot-exclude.md` section → public README → one redaction commit per `snapshot-replace.md` section. **The branch tip tree is exactly what mirrors to `fof-mono-public`.**

To refresh after list edits on `main`, or after selectively bringing private-repo content into the export branch:
1. Edit `snapshot-exclude.md` / `snapshot-replace.md` on `main` and push. In the export checkout: `git fetch origin`.
2. Run `./skills/repo-public/public-snapshot/scripts/pare_down_pass.sh` — re-applies excludes and replacements from `origin/main`, re-injects the README if needed.
3. Review the reported changes and commit them grouped by list section (same message style as the initial pass).
4. Run the sweep from the branch checkout — must be 0 findings:
```bash
<primary>/.venv/bin/python3 skills/repo-public/public-snapshot/scripts/pii_sweep.py --root . --allowlist skills/repo-public/public-snapshot/pii-allowlist.md --terms <primary>/docs/personal/pii-terms.md
```
5. Confirm exclusions + redactions: `./skills/repo-public/public-snapshot/scripts/confirm_export_checkout.sh` (must exit 0).
6. Push the branch, review, then mirror: `./skills/repo-public/public-snapshot/scripts/mirror_export_branch.sh --execute` (dry run without the flag). Snapshot commits use the hardcoded GitHub noreply for `randalljam` (override with `FOF_PUBLIC_EMAIL` if needed); private-repo git config is untouched.

A full `git merge origin/main` into the export branch is optional and often noisy (the export tree is intentionally pared down). Prefer selective bring-over of specific main changes, then pare-down — use skill `skills/repo-public/update-from-main/README.md` (dry-run propose → approve → bring → pare-down → confirm → PII sweep; commits prefixed `update-from-main:`).


## Confirm export checkout (exclusions + redactions)
After pare-down on `export/to-fof-mono-public`, run:
```bash
./skills/repo-public/public-snapshot/scripts/confirm_export_checkout.sh
```
Prints three sections: (1) exclude paths from `origin/main` `snapshot-exclude.md` are not tracked, (2) no unexpected working-tree leftovers for those paths (`docs/personal` mount OK), (3) redacted identifier/name spot-check terms absent from tracked files. Exit non-zero on any FAIL. Do not hardcode a second exclude list in the script — `snapshot-exclude.md` is the only path inventory.


## Stage-based dry run (verification / ad-hoc)
`build_public_snapshot.sh` builds the same result in a throwaway stage directly from `main` — useful as an independent check: its stage should diff empty against the export branch tree (verified 2026-07-31).
1. **Dry run** from the primary checkout on a clean `main`:
```bash
./skills/repo-public/public-snapshot/scripts/build_public_snapshot.sh
```
Builds the stage, applies `snapshot-exclude.md`, runs the PII sweep, prints a summary. Pushes nothing. A non-zero exit means the sweep found unsuppressed hits.
2. **Review sweep findings.** For each hit, pick a bucket: EXCLUDE (add the path to `snapshot-exclude.md`), REDACT (add a `find==>replace` rule to `snapshot-replace.md` — publish-time only), or KEEP (add a benign pattern/path to `pii-allowlist.md`). Fix the private source directly only when the content is wrong there too. Personal terms belong in `docs/personal/pii-terms.md`; both list files sit on the exclude list and never ship.
3. **Publish** when the dry run is clean:
```bash
./skills/repo-public/public-snapshot/scripts/build_public_snapshot.sh --execute
```
Clones/pulls `fof-mono-public`, rsyncs the stage in (with `--delete`, so removals propagate), commits, pushes, and shows the push output.
4. **Verify** on GitHub: snapshot commit present, spot-check that excluded paths (e.g. `README_internal.md`, `manifests/`, `agents/`, the two list files) are absent.


## Standalone PII sweep (private repo audit)
The sweep also runs directly against the working tree for the broader private-repo audit:
```bash
.venv/bin/python3 skills/repo-public/public-snapshot/scripts/pii_sweep.py --root . --report /tmp/pii-report.txt
```
Heuristics only — it catches emails, IPs, phone-shaped strings, AWS keys/ARNs/account IDs, secret-looking assignments, street-address shapes, and every term in `docs/personal/pii-terms.md`. A clean sweep is necessary, not sufficient; the human review in step 2 is the real gate.


## Maintaining the exclude list
`snapshot-exclude.md` (on `main` only) is the contract for what never goes public — one repo-relative path prefix per line. Current categories: personal/identity docs, agent/session internals (`.cursor/`, `.claude/`, `.codex/`, `.agents/`, `agents/`), S3 key inventory (`manifests/`), family/local-machine skills, git-surgery records (`docs/git/git-exclude-public/`), prompts, deploy logs, and the two publish-time list files themselves. When adding a new top-level folder to the repo, decide its public/private status here in the same PR. Seeded from `docs/2026-04-09_repos-reorg/2026-06-05_public-repo-pii-audit.md` and the 2026-07-22 history-purge manifest (both themselves excluded).

On the export branch, `pare_down_pass.sh` both `git rm`s tracked exclude paths and `rm -rf`s any **non-mount** working-tree leftovers under those paths (so stray `__pycache__` / sync-state under `agents/` cannot fake a failed exclusion check). Local-files mounts are untracked with `--cached`; every mount **symlink except `docs/personal`** is then unlinked so the export checkout stays visually clean. `docs/personal` is kept for `pii-terms.md` and review notes (checklist, copyright check) — it is gitignored / untracked and never ships. Unlinking a symlink does not touch the shared `_LOCAL_FILES` target.


## Limitations
- Snapshot only: no private commit history, issues, or branches are published; renames between snapshots appear as delete+add.
- The sweep is line-based and heuristic; it does not decode binaries beyond skipping them, and it cannot judge context (e.g. a collaborator's name in a commit message quoted in a doc).
- Secret rotation is a separate pre-public step (see the history-purge manifest's out-of-scope table) — publishing does not depend on it, but rotate anything the audit marked CRITICAL before inviting eyeballs.
