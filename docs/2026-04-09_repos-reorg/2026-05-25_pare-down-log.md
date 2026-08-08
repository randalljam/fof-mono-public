file: 2026-05-25_pare-down-log.md
title: Pare-down log for the `pare-down` branch

Running log of prompt / response / status snapshots for the corpus-tools pare-down effort. Each exchange has the user prompt verbatim, the assistant response verbatim, and a `repo_status.py` snapshot after the pass.

Branch: `pare-down` (off `claude/brave-hamilton-b4czj`, which was off `main`). Intentionally never PR'd into main. The end state of this branch will be copy-pasted (no `.git/`) as the first commit of a new repo, name TBD.


# 2026-05-25 -- prompt 1

Okay, so I'm ready to start a very important project, which is to pare down this repo corpus tools. And so I want you to create a branch called pare down. And then if you go to the root folder plans, and then there's a folder called repos-reorg, that has a lot of the files that you're going to be looking at. So I want you to first review the file that's called repo reorg dash branch. Because that explains that, you know, what we're going to do here is, you're going to create this branch, and then we're going to be pairing down this ginormous bloated repo, which is, I think, at least five gigs, if not more. There's a repo full sweep file that's worth reviewing. Then the key file is called ChatGPT guide to file types to exclude in repo. So definitely review that thoroughly. And then I want you to create a new file that's going to be the pair, call it put today's date, call it pair down pair pair dash down dash log dot MD. And I want you to put every one of our exchanges in it as a markdown heading one. And so I want you to put my prompt verbatim, I want you to put your response verbatim. And then I want you to put I want you to put a summary of the let's see here. I want you to put some kind of repo status summary after you've made your changes, which is going to be I think if we do it as I think you're going to want to create a Python module to you can put it in the same repo reorg file and I want it to show all the root folders in the repo and then show the number of files and the total size in megabytes, rounded to the nearest megabyte and use commas from any numbers that are gigabytes. But you should quickly even in the first go, pair this down to less than a gigabyte. And the key thing that you're going to be doing in parallel is creating the entries to upload to Amazon S3. And then the key thing that's described to create the manifest of what is in Amazon S3 that's been archived from this repo and primarily that's going to be from the data folder, although there's other stuff that may need to get paired down as well. I'm not sure. And then you're also going to be updating the .gitignore in parallel and annotate the .gitignore really well so it's clear what's being excluded and why. And yeah, you'll be doing all those things in parallel. And do this as, prepare to do this in a few passes. And in the first pass, you're going to be pairing back the largest and most obvious files that violate the policy and shouldn't have been put in here in the first place. Although I'm saying you shouldn't have been put in here in the first place, it's important to know the history of this repo and that it's got thousands of commits over two years, fairly from just, from me, I'm Randy, I'm the principal, do read the profile.md as well. There's not much in projects yet. And it's served as almost like a remote file storage as well for me and my executive assistant to work on file heavy projects involving transcripts and a lot of file conversion of corpuses of material. So yeah. So yeah, I think create the Python module that will just deterministically give us a report of the current kind of file number and size. And then in your response, definitely summarize like, you know, what you, what you did. And you can feel free to adapt the, you know, guide to the file types to exclude in the repo. That is a starting working copy of this. So if it's helpful to, you know, update that then, then you can. And in terms of like, you know, where we're going with this, you should read the ai-coding-system-dev.md that will give guidance about that. I'm going to be managing lots of different applications and project areas in this single kind of modern repo. There are some core modules related to file processing in primary and transcript processing. And there are a few active projects or two other repos that we're going to eventually be merging into this, but that's outside of the scope of this kind of entire session. The purpose of this entire session is to do, is to do the pare down on this branch. And then we're going to freeze this repo as is and just leave that branch not merged in. And then I'm going to do a clean copy of all of those of the pare down files, which will now be, you know, primarily the source code and then other non-bloat files. So those are going to get copied over to a brand new repo, which has yet to be named. And then that's going to be the repo that we merge the other repos into, and then it's going to serve as the new organized pare down, but combined mono repo for kind of all future work and the kind of AI coding system development effort. Okay, so I think that's enough. With this branch, you can safely start the pairing process and do the first phase of it. And again, create that log file and go to it. And then, you know, at the end of this phase, you may have a couple of questions. Ask those questions to guide the next phase. And then ask questions, you know, describe what you did and if there's any in the first phase, and if there's questions related to what you did, like if I'm not happy with, you know, you say having moved some stuff out, or if you're then then ask, ask about that. So there would be questions for phase one, the questions for phase two, and I'll answer those in the next prompt. And you're going to be committing at the end of every one of your responses in this session. I'm not doing this on mobile, so you don't need to worry about that. I'm doing this at my computer, my laptop, and I'll be syncing, I'll be, you know, checking out this branch, this new branch that you're creating locally, so make sure to publish it, and then I'll be, you know, looking at the directory through cursor and VS code and following along of what you're doing for each phase. Okay? Let's do it.


# 2026-05-25 -- response 1

Branch `pare-down` is created off the current working branch and pushed. First pass focused on the largest and most obvious offenders. Tracked size dropped from **7,277 MB → 331 MB** in 2,180 files (was 20,422). Working-tree files are left on disk so they can be uploaded to S3 in the parallel-track step; nothing was physically deleted.

**Files added under `plans/2026-04-09_repos-reorg/`**
- `repo_status.py` -- deterministic report: per root folder, tracked file count, tracked MB, working-tree file count, working-tree MB. Run with `python3 plans/2026-04-09_repos-reorg/repo_status.py .`
- `s3_archive_manifest.jsonl` -- one row per untracked area, with target S3 URI, approx size, status (`pending_upload` / `discard_local`), and notes. Bucket `fof-archive` is a placeholder.
- `s3_archive_manifest_README.md` -- schema + workflow for the manifest.
- `2026-05-25_pare-down-log.md` -- this file.

**`.gitignore` rewritten**
Replaced the 833-line, file-by-file `.gitignore` with a clean ~150-line version organized by category with comments on *why* each section exists. References AGENTS.md and the file-types guide. Per-file paths inside `data/` are gone -- the whole tree is ignored, with `!` exceptions reserved for `data/README.md`, `data/manifests/**`, `data/schemas/**`, `data/samples/**` (the catalog scaffolding to be built next).

**Untracked via `git rm --cached` (files stay on disk for S3 upload)**
- `data/` -- 5,702 MB, 9,838 files. Largest target. Per the file-types guide, real corpora go to S3; git tracks the catalog only.
- `logs/` -- 535 MB, 279 files. Recoverable / discardable.
- `_archive/` -- 285 MB, 287 files. Old code; full history still in this repo.
- `ms-graphrag/` -- 243 MB, 3,585 files. Off-limits per AGENTS.md.
- `web/aws_chalice/langchain-layer/` -- 128 MB, 4,000 files. Built Lambda layer, rebuildable.
- `_misc_to_be_sorted/`, `limbo/`, `lancedb/`, `pretrained_models/`, `node_modules/` -- off-limits / local-state.
- Root junk: `=`, `scratch.py`, `scratch.md`, `temp.json`, `test_audio_nova2gen.json`, `Default.code-profile`, `settings COPY TO USER SETTINGS.json`, `token.pickle`, `.sesskey`.

**What I did *not* touch in phase 1**
- `projects/` (151 MB, 397 files) -- standalone apps; size suggests fixtures/data inside.
- `tests/` (39 MB, 248 files) -- larger than expected for unit tests; may contain fixtures that should move to S3 or `data/samples/`.
- `web/` (97 MB after langchain-layer removal) -- Webflow frontend + Chalice apps still tracked.
- `docs/` (19 MB), `exchanges/` (10 MB) -- in scope but moderate; safe for now.
- Git history rewriting -- explicitly forbidden by AGENTS.md and not needed (the new repo will be a fresh first commit, so the bloated history stays in this archive repo only).

**Commit + push**
Single commit on `pare-down`, pushed to `origin/pare-down`.

**Questions before phase 2**
1. **`projects/` is 151 MB** -- expected, or should I look inside `ads_scrape`, `math_quiz`, `meta_coder`, `wingspan` for data/fixtures to move?
2. **`tests/` is 39 MB** -- large for unit tests. Treat any fixtures over ~1 MB as `data/samples/` candidates?
3. **S3 bucket name** -- I used `fof-archive` as a placeholder in the manifest. Confirm the real bucket / prefix before phase 2, or wait until upload time?
4. **`data/` exceptions** -- I added `!` rules for `data/README.md`, `data/manifests/`, `data/schemas/`, `data/samples/`. Any other small canonical content in `data/` (e.g. `data/style_guide_transcripts.md`, `data/names.md`, `data/cspell_dictionary_common.txt`) you want kept in git? Easiest to add explicit `!` entries.
5. **Root-level docs** -- I kept `README_external.md`, `README_internal.md`, `AGENTS.md`, `CLAUDE.md`, `cloc_*`, `chalicelib_mirror_deploy_log.md`, `run_sovereign_child_html.py`. Any of those should also be untracked / moved into `docs/` / `scripts/`?
6. **Pre-commit hook** -- the file-types guide recommends `check-added-large-files` (1 MB cap). Add in phase 2, or wait until the new repo?


# 2026-05-25 -- repo status after pass 1

Output of `python3 plans/2026-04-09_repos-reorg/repo_status.py .`

```
folder               tracked#    tracked MB   worktree#    worktree MB
----------------------------------------------------------------------
.cursor                     1             0           1              0
.devcontainer               1             0           1              0
.vscode                     4             0           4              0
_archive                    0             0         287            285
_misc_to_be_sorted          0             0          12             40
ai-threads                  1             0           1              0
data                        0             0       9,842          5,704
dependencies               26             1          26              1
docs                      176            19         176             19
exchanges                 682            10         682             10
lancedb                     0             0           6             11
lib                         5             1           5              1
limbo                       0             0           4              0
logs                        0             0         279            535
ms-graphrag                 0             0       3,585            243
node_modules                0             0         222              1
plans                      71             1          74              1
pretrained_models           0             0           0              0
primary                    21             2          21              2
projects                  397           151         397            151
prompts                    74             2          74              2
scripts                     3             0           3              0
secondary                  33             1          33              1
security                    3             0           3              0
sounds                      2             0           2              0
tests                     248            39         248             39
voice                      59             7          59              7
web                       356            97       4,356            225
<root files>               17             0          17              0
----------------------------------------------------------------------
TOTAL                   2,180           331      20,420          7,278
```

Baseline before pass 1: 20,422 tracked files, 7,277 MB tracked. After pass 1: 2,180 tracked files, 331 MB tracked. Working tree on disk is unchanged on purpose -- those files are queued for S3 upload, not deleted.
