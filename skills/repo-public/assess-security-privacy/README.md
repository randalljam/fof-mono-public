file: skills/repo-public/assess-security-privacy/README.md
title: Assess security and privacy of a path for the public snapshot
source-github-url: original
source-guide-url: original
skills-referenced:
  - skills/repo-public/public-snapshot
history:
  - 2026-08-07 · Randy · Cursor (Grok 4.5) [assess-security-privacy skill](60469b04-31e0-4126-b9b0-4e017fce2462) — initial skill: agent judgment pass for secrets/security and residual PII after machine sweep + pare-down


**Use this skill to review one folder path (and everything under it) for security/secrets risk and residual privacy/PII risk before that tree ships in `fof-mono-public`.** It is a judgment pass for a human+agent review — not a re-run of the machine gates.


## When to use
- Pre-publish checklist items under **Security check** or **Privacy check** (see `docs/repo-public/2026-08-01_public-snapshot-review-checklist.md`).
- User says "assess security/privacy of `<path>`", "public-snapshot security pass on …", or similar.
- Spot-checking a folder that survived exclude + redaction and needs a comfort call.

Do **not** use this as a substitute for the machine gates. Those must already be done (or the agent must refuse and point back to them).


## Prerequisites (assume already done)
1. **Pare-down** on the export checkout: `./skills/repo-public/public-snapshot/scripts/pare_down_pass.sh` (exclusions + publish-time redactions applied).
2. **Confirm script** (optional but preferred): `./skills/repo-public/public-snapshot/scripts/confirm_export_checkout.sh` → `ALL CHECKS PASSED`.
3. **PII sweep** clean on the tree under review (usually the export checkout root):
```bash
.venv/bin/python3 skills/repo-public/public-snapshot/scripts/pii_sweep.py \
  --root . \
  --allowlist skills/repo-public/public-snapshot/pii-allowlist.md \
  --terms docs/personal/pii-terms.md
```
Expect **0 findings**. The machine sweep catches emails, IPs, phones, AWS keys/ARNs/account IDs, secret-looking assignments, street-address shapes, and terms from `docs/personal/pii-terms.md`. This skill looks for what heuristics miss: context, operational disclosure, and identity that is not pattern-shaped.

If any prerequisite is not done, say so briefly and stop (or ask whether to run the missing gate first). Do not pretend a judgment pass replaces a failed sweep.


## Input
- **Required:** a repo-relative folder path to review (e.g. `docs/2025-03-14_aws-prod`, `docs/git`, `apps/education/lesson-logger`).
- **Scope:** that path and all files/subfolders under it that would ship (tracked / export-tree content). Skip `.git`, `node_modules`, `.venv`, `__pycache__`, and other non-shipping noise.
- Prefer running this on the **export branch checkout** (`export/to-fof-mono-public`) so the tree matches what would publish. If reviewing on `main`, say so — some paths may still be private-only or unredacted there.


## Procedure
Work the two passes below in order. Read enough of the tree to judge; for large folders, enumerate files first, then deep-read high-risk ones and sample the rest. Do not re-run a full-repo PII sweep unless the user asks.

### Pass A — Security / secrets (public-repo risk)
Look for anything that would help an attacker, expose credentials, or leak operational detail you would not want in a public friends-facing snapshot:
- API keys, tokens, passwords, HMAC/shared secrets, private URLs with embedded credentials
- Cloud account IDs, ARNs, IAM user/role names, bucket names that were meant to stay obscure, region+resource combos that map to a live account
- Deploy credentials, SSH material, `.pem` / key files, webhook secrets, OAuth client secrets
- Internal hostnames, VPN/bastion details, production endpoint maps, runbooks that amount to an attack surface guide
- Hard-coded credentials in examples, “temporary” debug dumps, pasted CLI output with secrets
- Instructions that reveal how to reach private infra (even if values look redacted — incomplete redaction, leftover real IDs next to `[S3-BUCKET]` placeholders, etc.)

**Sanctioned / usually OK (still confirm in context):** placeholder forms (`[S3-BUCKET]`, `[REDACTED-…]`), public product names, collaborator initials already accepted for the public snapshot (EA/BS/TL/Kid1), MIT license identity, and architecture discussion that does not include live secrets.

### Pass B — Privacy / residual PII
Assume pattern/term sweep already passed. Look for identity and personal context the machine may miss:
- Real personal names (kids, family, friends, collaborators beyond sanctioned initials), addresses, schools, workplaces, medical/financial notes
- Contact info in prose or screenshots/transcripts that is not a classic email/phone regex hit
- Location, schedule, or family-life detail that identifies people even without a “PII-shaped” string
- User-exchange content, hash logs, or anything that belongs under PII mounts / private buckets
- Docs that describe private life or private org internals more specifically than the public “build in public” framing warrants

Do not re-litigate allowlisted benign patterns from `pii-allowlist.md` unless the *context* makes them sensitive.


## Disposition buckets (per finding)
For each issue, assign one action:

| Bucket | Meaning |
|--------|---------|
| **EXCLUDE** | Path (or parent folder) should not ship — add to `skills/repo-public/public-snapshot/snapshot-exclude.md` on `main` |
| **REDACT** | String should be publish-time replaced — add a rule to `skills/repo-public/public-snapshot/snapshot-replace.md` on `main` |
| **KEEP** | Comfortable shipping; note why (benign / already redacted / intentional public) |
| **ASK** | Needs a human comfort call; do not invent the decision |

List files: edit on `main` only; they are themselves excluded from the public snapshot. After list edits: push `main` → fetch in export checkout → re-run pare-down → re-confirm / re-sweep as needed (see `skills/repo-public/public-snapshot/README.md`).


## Output format
Return a short structured summary — no long essay. Use this shape:

```markdown
## Assess: <path>
**Checkout / branch:** …
**Prerequisites:** pare-down ✓/✗ · confirm ✓/✗/skipped · pii_sweep ✓/✗ (N findings)

### Security / secrets
- Verdict: CLEAR | ISSUES | NEEDS HUMAN
- Findings (if any):
  - `path:line` — what · why it matters · **EXCLUDE|REDACT|KEEP|ASK**

### Privacy / residual PII
- Verdict: CLEAR | ISSUES | NEEDS HUMAN
- Findings (if any):
  - `path:line` — what · why it matters · **EXCLUDE|REDACT|KEEP|ASK**

### Recommended next steps
- (bullets the human can act on — exclude/redact edits, or “ship as-is”)
```

Rules for the write-up:
- Quote or paraphrase the sensitive fragment carefully; prefer describing the *kind* of secret (e.g. “live-looking AWS account id”) over pasting a full credential into chat when a short locator (`file:line`) is enough.
- If CLEAR on both passes, say so in one line each and skip empty finding lists.
- Do not modify exclude/replace lists or delete files unless the user asks after reading the summary.


## Related
- `skills/repo-public/public-snapshot/README.md` — build, pare-down, sweep, mirror.
- `skills/repo-public/public-snapshot/scripts/pii_sweep.py` — machine heuristic gate this skill assumes already passed.
- `docs/repo-public/2026-08-01_public-snapshot-review-checklist.md` — human pre-publish checklist that invokes this skill per path.
