file: skills/repo-ops/pr-prep/README.md
title: PR prep — ready a (often long-lived) branch for a pull request into main
source-github-url: original
source-guide-url: original
skills-referenced:
  - skills/repo-ops/local-files-audit
  - skills/repo-ops/merge-main-to-branches
  - skills/repo-ops/promote-to-main
history:
  - 2026-07-30 · Randy · Cursor [local-files-audit skill](a382ac41-327f-4a1d-acf2-960cc34a1971) — initial composite checklist from Deutsch / Dragon Baby long-lived PR prep


**Use this skill when preparing a feature branch for a pull request into `main` (or into its parent), especially a long-lived branch with child sub-branches.** It is a composite checklist: do the steps in order, and follow the referenced skills for the detailed mechanics of merge-forward, promote, and local-files audit.

This skill does **not** open or merge the PR unless the user asks. It prepares the branch and packages a reviewable handoff so the user can open (or ask to open) the PR.


## When to use
- User says "prep this branch for a PR", "ready for PR", "pre-PR checklist", or similar.
- A long-lived app branch (Deutsch-style stack, Dragon Baby-style trunk) is about to land on `main`.
- Before asking for a final review of a large feature PR.

Do **not** use this for day-to-day small PRs that are already synced and scoped — skip to tests + open PR. Use judgment: short branches may only need steps 4–7.


## Principles (this repo)
- **Merge `main` forward; never rebase published history** for shared PR branches (`AGENTS.md` → Git safety).
- **Preserve individual commits** when merging into `main` unless the user explicitly requests squash (and then follow the squash message rules in `AGENTS.md`).
- **One working branch per session**; get branch approval before switch/create (`AGENTS.md` → Branch discipline).
- **Verify claims with command output** — do not say a step is done without proof.


## Checklist (run in order)

### 1. Confirm branch and working tree
```bash
git fetch origin --prune
git branch --show-current
git status --short --branch
git log --oneline --decorate -15
git merge-base origin/main HEAD
git log --oneline origin/main..HEAD | head -40
```
Confirm with the user that this is the intended PR head (not a harness `claude/<random>` scratch branch). Working tree should be clean, or remaining changes should be committed/explained before continuing.


### 2. Stabilize the child stack (if any)
If open child/sub-branches still need to land into this parent, merge them **bottom-up** into the long-lived parent first (cascade of child → parent PRs, as with Deutsch `#62` → `#63` → parent). Do not open the parent → `main` PR until the approved stack is integrated.

Dependent work rides with its parent; only *independent* core/infra can leave early (step 3).


### 3. Promote unrelated core/infra off the branch (if needed)
If the branch contains general `core/`, cross-cutting ops, or other work that should not wait on this feature, follow **`skills/repo-ops/promote-to-main/README.md`**.

Only promote commits that do not depend on unmerged feature work. Get explicit approval before any force-with-lease cleanup of the feature branch.


### 4. Merge `origin/main` into this branch
Bring current `main` into the PR head with a **normal merge commit** (no rebase, no force-push).

**Single branch (usual for PR prep):** on the PR branch, after fetch:
```bash
# optional conflict preview
git merge-tree $(git merge-base HEAD origin/main) HEAD origin/main
git merge --no-edit origin/main
# resolve conflicts if any; keep feature intent; preserve worktree title-bar colors in .vscode/settings.json
git push
```
Proof: show merge commit / push output; `git merge-base --is-ancestor origin/main HEAD` should succeed after the merge.

**Many active branches** need the same `main` update: use **`skills/repo-ops/merge-main-to-branches/README.md`** (overlap preflight, merge-tree, per-branch report). For one PR head, the single-branch merge above is enough; that skill is the multi-branch / conservative fan-out form of the same idea.

Recent pattern: Deutsch used a dedicated sync PR (`main` → feature) before the final feature → `main` PR; Dragon Baby merged `main` on the feature branch itself. Either is fine; prefer whatever the user asks for.


### 5. Clean the review surface
Make the eventual `origin/main...HEAD` diff mostly *this feature*:
- Drop or restore worktree-only noise (e.g. title-bar color should match `main` expectations for the final PR if that was a local identity tweak).
- No bulk media, PII, or accidental large binaries (pre-commit / `AGENTS.md` → Commit hygiene).
- No unrelated apps in the diff unless intentional.
- Optional durable review note for complex stacks (e.g. Deutsch branch-chain audit) when the user wants a written source of truth for known limits.


### 6. Local-files audit (before the worktree goes away)
If this checkout is a worktree that will be removed after merge — or the branch accumulated local-only data — run **`skills/repo-ops/local-files-audit/README.md`** (pre-removal check for this worktree). Get approval on disposable vs move-to-existing-mount vs create-new-mount before anything is deleted with the folder.

For a primary `fof-mono` checkout that will not be removed, still run the audit if there are `WARN: ignored` paths that matter; otherwise note that the worktree is staying.


### 7. Pre-PR testing (`AGENTS.md`)
Mandatory unless the user explicitly waives it for this PR:
1. Write focused tests for important new/changed logic when missing.
2. Run them with the project venv / app test command (per-app `AGENTS.md` → `## Tests` when present).
3. Tell the user what ran, where tests live, and pass/fail with real output.
4. Put the run command and results in the PR body’s test plan.

Do not claim tests passed unless this session saw them pass. If the harness cannot run them, say so and leave the exact local command.


### 8. Package the PR handoff (then open only if asked)
Draft (or create, if the user asked) a PR with:
- **Summary** — what lands, in plain bullets
- **Stack / sync notes** — child PRs already merged; how `main` was brought in
- **Test plan** — commands + results
- **Impact / scope** — what is *not* changed; known limits
- **Review record** — link to any durable audit doc if one exists

Default merge strategy into `main`: preserve commits (not squash), per `AGENTS.md`.

After the PR merges, human worktree retirement follows `docs/worktrees-guide.md` (Step 1 of that checklist is the local-files audit skill above).


## Done when
- Branch tip includes current `origin/main` (merge-forward done) or the user deferred that with an explicit reason
- Child stack integrated or none
- Promote-to-main done or N/A
- Local-files audit done or explicitly N/A
- Tests run (or waived) and described
- PR body ready (and PR opened only if requested)


## Guardrails
- No rebase / force-push of published PR branches unless the user explicitly approves that operation.
- No opening a PR, merging a PR, or deleting branches/worktrees unless the user asks.
- Push only the branch being prepared; never a `claude/<random>` harness branch.
- When a referenced skill applies, **read and follow that skill** — do not re-derive its procedure here.


## Related (docs, not skills)
- `AGENTS.md` — Branch discipline, Git safety, Pre-PR testing, PR merge strategy, Commit message format
- `docs/worktrees-guide.md` — remove worktree after PR merge (human UI steps)
