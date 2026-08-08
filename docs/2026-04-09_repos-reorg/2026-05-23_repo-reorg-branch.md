# prompt
Okay. So I don't want you to do any new coding. I just want you to answer this in a in a... using the context of this thread. So I think that what I'm going to need to do is to create a new repo that only has the paired down version of this repo, only the the key, you know, two hundred megabytes. So I've been working on general AI coding and, like, repo rules for, like, what files to put in the Git ignore and how to... then I'm gonna need to create the the Amazon s three scripts to, you know, upload those. So that's that's all, I think, totally manageable. But just in terms of a practical way to do this, I think that what I should do is create a branch off of off of main in in this corpus tools repo and then work on the... pair down in that branch. And just plan to never do a PR of that branch into main. And then when I get that good enough and, you know, get... when I get it, you know, ready... well, I guess not good enough, but when I get it complete, then I just copy that wholesale into the new repo give the new repo a name and then make a commit, and then that'll be the first commit of the new repo. Then I just leave the corpus tools repo as it is, so it will have two two versions. It'll have the static, you know, copied over files, and then it'll have the original full set of files and also have the full get history. It's just I don't plan on using it except for sort of historical or archive purposes or I wanna find a file that somehow didn't make it over to the end of migration, then I can do that. Oh, and I, you know, I should have mentioned that that I'll be uploading a lot of the data files and files to store into Amazon s three and at the same time creating the scripts to download them if I need to use them again. Does that sound like a good plan? If so, summarize that as a plan and if... then if you have additional recommendations, make those and then give me an updated plan based on your recommendations. So give me my version, your recommendations, then an updated version of the plan. and keep keep the plan very concise. You know, assume this is this is just for me and, um, just to track this this kind of to dos. So... yeah.

# cursor GPT5.5 - repo consolidation
_add primo.d file and tweak prompt_
Yes, your plan sounds good. The key idea is right: make the new repo a clean source-control repo, not a cleaned history rewrite of the old repo. Keep `corpus-tools` as the archive/source of truth for old history and data recovery.

## Your Version
- Create a cleanup branch from `main` in current `corpus-tools`.
- Pare the repo down there: source code, agent rules, docs, scripts, core configs, no bulky data/file-storage content.
- Move large datasets and working files to S3.
- Add scripts/manifests for uploading/downloading/restoring S3-backed files.
- Do not PR this branch back into `main`.
- When complete, copy the cleaned tree into a brand-new repo.
- Make that the new repo’s first commit.
- Leave old `corpus-tools` untouched as historical archive with full git history and old files.

## Recommendations
- Treat the cleanup branch as a staging workspace only. The new repo should not inherit `.git`, old branches, or old history.
- Create a clear S3 manifest format early: local path, S3 URI, size, checksum, category, restore notes.
- Keep small representative fixtures in git for tests; move real corpora, media, logs, exports, PDFs, and generated artifacts to S3.
- Add `.gitignore` and agent rules before doing the final copy, so the new repo starts with clean boundaries.
- Before finalizing, run a “new repo rehearsal”: clone/copy fresh, install deps, run tests, verify scripts, and confirm no missing files.
- Keep the old repo read-only in practice after migration, perhaps with an archive note in its README.

## Updated Concise Plan
1. Create a `repo-paredown` branch from current `main`.
2. Audit repo contents into categories: keep in git, move to S3, delete, archive-only.
3. Build S3 layout plus upload/download scripts and manifest files.
4. Move bulky data/artifacts out of the future repo; keep only source, docs, configs, tests, small fixtures, and manifests.
5. Clean `.gitignore`, `AGENTS.md`, repo structure, README, and setup/test instructions.
6. Do a fresh-copy rehearsal without `.git`; verify install, tests, scripts, and restore flow.
7. Create the new repo and commit the pared-down tree as its first commit.
8. Freeze old `corpus-tools` as the historical/archive repo.


# claude code - analyze monorepo structure
Good plan. Here's what you described, my suggestions, then the combined version.

---

## Your Plan

1. Create a branch off main in corpus-tools (e.g., `migration`)
2. Pare down the repo on that branch — remove data/, logs/, archives, build artifacts, stale files
3. Build S3 upload scripts to archive large files before removing them from git
4. Build S3 download scripts so data can be retrieved when needed
5. When the branch is lean and complete, copy all files into a brand new repo (fresh commit, no history)
6. Leave corpus-tools as-is — static archive with full history, for reference only

## My Recommendations

**A. Name the new repo now** so you can reference it in scripts and docs. Something like `fof-tools` or `fof-core` — shorter than corpus-tools, reflects its broader purpose.

**B. Don't just copy files — use the branch to also fix the directory structure.** Since you're making a clean break anyway, this is the time to settle the projects/apps question, clean up root clutter, and get AGENTS.md right for the new repo. Cheaper to do it once during migration than to shuffle things after the first commit.

**C. Create a manifest file for S3 data** — a simple JSON or markdown file that lives in the new repo listing every S3 object with its key, size, corpus name, and description. This way the repo always knows what data exists even though the data itself is remote. Your download script can read this manifest.

**D. Do a secrets scan on the pared-down files before the first commit** of the new repo. Since you're getting a fresh history, this is the one chance to make sure nothing leaks into commit #1.

**E. Keep a migration log** — a single markdown file in the new repo that says "migrated from FocusOnFoundationsNonprofit/corpus-tools on [date], here's what was kept, what went to S3, what was dropped." Future-you will thank present-you.

## Combined Plan

1. Pick a name for the new repo
2. Create `migration` branch off main in corpus-tools
3. On that branch:
   - Remove data/, logs/, _archive/, ms-graphrag/, lancedb/, _misc_to_be_sorted/, pretrained_models/
   - Remove build artifacts (langchain-layer/, node_modules/)
   - Remove root clutter (=, scratch.*, temp.json, Default.code-profile, etc.)
   - Remove tracked credentials (token.pickle, .sesskey)
   - Settle directory structure (projects/ vs apps/ vs whatever you decide)
   - Clean up .gitignore (strip the data-specific patterns, keep what's relevant)
   - Update AGENTS.md for the new repo shape
4. Build S3 upload scripts — archive data/, logs/, and any other large files to S3
5. Build S3 manifest file — index of everything in S3 with download script
6. Run secrets scan on remaining files
7. When ready: create new repo, copy files in, write migration log, make first commit
8. corpus-tools becomes read-only archive