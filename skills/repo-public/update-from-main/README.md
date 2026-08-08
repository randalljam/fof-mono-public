file: skills/repo-public/update-from-main/README.md
title: Update the export branch from main (selective bring-over)
source-github-url: original
source-guide-url: original
skills-referenced:
  - skills/repo-public/public-snapshot
history:
  - 2026-08-07 · Randy · Cursor (Grok 4.5) [update-from-main skill](fc97c720-3e68-4413-b0fd-692ca5e17d89) — initial skill: dry-run propose, selective bring-over from origin/main, pare-down / confirm / PII gates, `update-from-main:` commit prefix + Main-Tip marker


**Use this skill on the export branch to selectively bring safe changes from `origin/main` into `export/to-fof-mono-public` without reintroducing intentionally purged or redacted content.** Always propose first (dry run); apply only after the user approves.


## When to use
- User says "update from main", "bring main changes onto the export branch", "sync export with main", or similar.
- Periodic refresh of the public-snapshot export tree after private-repo work landed on `main`.

Do **not** use this as a full `git merge origin/main` into the export branch. Prefer selective bring-over (see `skills/repo-public/public-snapshot/README.md`).


## Where to run
**Required checkout:** a worktree on branch `export/to-fof-mono-public`.

```bash
git branch --show-current   # must be export/to-fof-mono-public
```

If the branch is wrong, stop and say so. Do not run the bring-over on `main` or on a random feature branch.


## Commit message convention (mandatory)
Every commit created while **executing** this skill (bring-over commits, post–pare-down redaction commits, marker commit) must use this subject prefix:

```text
update-from-main: <what files and changes>
```

Examples:
```text
update-from-main: AGENTS.md monorepo blurb + structure
update-from-main: skills/ai/migrate-cursor-ai-sessions
update-from-main: redact private git remote after pare-down
update-from-main: marker Main-Tip=8d624a61
```

Do **not** use the ordinary `skills(…):` / `docs(…):` prefixes for commits made under this skill — the `update-from-main:` prefix is how the next run finds the window.


## Main-Tip marker (how the window is computed)
After a successful update (or when seeding the skill), ensure the newest `update-from-main:` commit on this branch carries a body trailer:

```text
Main-Tip: <full-sha of origin/main at the time of the update>
```

**Next run — resolve the window of main commits to consider:**
1. `git fetch origin --prune`
2. Find newest commit on `HEAD` whose subject starts with `update-from-main:` → `$MARKER`
3. If `$MARKER` has a `Main-Tip:` trailer → window is `Main-Tip..origin/main`
4. Else if `$MARKER` exists → use committer-date cutoff: main commits with `%cI` strictly after `$MARKER`'s `%cI`
5. Else (no marker yet) → window is `$(git merge-base HEAD origin/main)..origin/main` and say in the proposal that this is a first-run / merge-base fallback

List the window with:
```bash
git log --oneline --reverse <window-start>..origin/main
```


## Hard rules — do not reintroduce purged or private content
`snapshot-exclude.md` and `snapshot-replace.md` on **`origin/main`** are the contracts. Load excludes the same way `pare_down_pass.sh` / `confirm_export_checkout.sh` do (`git show origin/main:skills/repo-public/public-snapshot/snapshot-exclude.md`).

**Never bring onto the export tip:**
- Any path matching a prefix in `snapshot-exclude.md` (including the two private list files themselves, `docs/repo-public/`, `manifests/`, `skills/pv/`, `docs/git/git-exclude-public/`, agent dirs, etc.)
- Commits whose *only* useful payload is those excluded paths (skip the whole commit)
- Unredacted values that `snapshot-replace.md` exists to strip — if a brought file still has private find-strings, pare-down must rewrite them before the update is considered done; do not leave functional private identifiers on the export tip

**Allowed even when related to a skip commit:** path-limited checkout of public-safe files from a mixed commit (e.g. take a skill README but not a `docs/repo-public/` edit from the same main commit).

**Policy restores:** if `main` *narrows* an exclude (path was excluded, now public), restoring that path from `origin/main` is intentional — call it out explicitly in the dry-run proposal. Do not silently restore exclude-list shrinks without saying so.


## Procedure

### 0. Preconditions
```bash
git branch --show-current    # export/to-fof-mono-public
git status --porcelain       # prefer clean; stop or stash if dirty mid-flight work isn't yours
git fetch origin --prune
```

Confirm `origin/main` is readable for the private lists:
```bash
git show origin/main:skills/repo-public/public-snapshot/snapshot-exclude.md >/dev/null
git show origin/main:skills/repo-public/public-snapshot/snapshot-replace.md >/dev/null
```

### 1. Dry run — propose only (stop and wait)
Compute the main commit window (see Main-Tip above). For each commit in the window, list files touched and classify:

| Class | Action |
|-------|--------|
| **BRING** | Public-safe; cherry-pick whole commit or path-checkout listed files |
| **SKIP** | Entirely excluded / private-list-only / would reintroduce purged content |
| **PARTIAL** | Mixed commit — bring only the listed safe paths |
| **ALREADY** | Export tip already matches `origin/main` for those paths |

Also tip-to-tip check key shared skill files if helpful:
```bash
git diff --stat HEAD origin/main -- skills/repo-public/
```

**Output a proposal** with:
1. Window definition (`Main-Tip` / date cutoff / merge-base) and `git log --oneline` of main commits considered
2. BRING / SKIP / PARTIAL / ALREADY tables (commit SHA, subject, paths, reason)
3. Planned commit grouping on the export branch (one commit if cohesive; multiple if mirroring distinct main commits or distinct concerns)
4. Reminder that apply waits for user approval

**Stop. Do not cherry-pick, checkout paths, or commit until the user approves.**

### 2. Apply (only after approval)
Prefer, in order:
1. **Cherry-pick** whole BRING commits when they apply cleanly and touch only safe paths
2. **Path-checkout** from `origin/main` for PARTIAL commits or when cherry-pick is noisy:
   `git checkout origin/main -- <safe-paths>`
3. Never checkout excluded paths

Commit with `update-from-main: …` subjects. Use multiple commits when the brought work came from clearly separate main commits or unrelated areas; one commit is fine when the set is small and cohesive.

### 3. Pare-down, then gates (always after apply)
From the export checkout, in order:

```bash
./skills/repo-public/public-snapshot/scripts/pare_down_pass.sh
```

Review the resulting changes. Commit any redaction/exclude deltas with `update-from-main:` subjects (group by `snapshot-replace.md` / exclude section when there are several).

```bash
./skills/repo-public/public-snapshot/scripts/confirm_export_checkout.sh
```

Must print `ALL CHECKS PASSED` (exit 0). If it fails, fix (usually pare-down leftovers or a stale confirm script) before continuing.

```bash
# Prefer primary checkout venv when this worktree shares it; else .venv here
<primary-or-local>/.venv/bin/python3 skills/repo-public/public-snapshot/scripts/pii_sweep.py \
  --root . \
  --allowlist skills/repo-public/public-snapshot/pii-allowlist.md \
  --terms <primary>/docs/personal/pii-terms.md
```

Expect **0 findings**. Non-zero → do not claim the update is done; report findings and disposition (exclude / redact / allowlist) per `skills/repo-public/public-snapshot/README.md`.

### 4. Marker commit
If the last commit is not already an `update-from-main:` commit that records the tip, create one (empty commit is OK when the tree is otherwise clean):

```bash
MAIN_TIP="$(git rev-parse origin/main)"
git commit --allow-empty -m "$(cat <<EOF
update-from-main: marker Main-Tip=${MAIN_TIP}

Main-Tip: ${MAIN_TIP}
EOF
)"
```

If the final bring-over / redaction commit can carry the trailer instead, that is fine — avoid a pointless empty commit when the trailer already landed on the tip commit. Prefer recording the **full** `origin/main` SHA.

### 5. Report (required end-of-run)
Report to the user:
1. **Window used** and which main commits were BRING / SKIP / PARTIAL / ALREADY
2. **Commits created** on the export branch (`git log --oneline` of new commits)
3. **Gate results:** confirm script summary + PII sweep finding count (and report path if written)
4. **Further actions needed**, explicitly, e.g.:
   - push `export/to-fof-mono-public` if not pushed
   - propagate a shared skill fix back to `main` (if the update edited skill sources that should live on `main`)
   - mirror to `fof-mono-public` when ready
   - residual privacy items noticed but out of scope
   - confirm/exclude policy mismatches found on `main` that should be fixed there

Do not push or mirror unless the user asked.


## Anti-patterns
- Full merge of `origin/main` into the export branch “to save time”
- Cherry-picking commits that only move or edit `docs/git/git-exclude-public/`, `docs/repo-public/`, `manifests/`, `skills/pv/`, or the private list files
- Copying unredacted `.gitignore` / docs that reintroduce `[S3-BUCKET]`, account IDs, private remotes, or personal emails — let pare-down apply `snapshot-replace.md` and commit those redactions separately
- Hardcoding a second exclude path list in any script (see `confirm_export_checkout.sh` — it must read `snapshot-exclude.md`)
- Applying the bring-over before the user approves the dry-run proposal


## Related
- `skills/repo-public/public-snapshot/README.md` — exclude/replace lists, pare-down, confirm, sweep, mirror
- `skills/repo-public/assess-security-privacy/README.md` — judgment pass after machine gates
)
