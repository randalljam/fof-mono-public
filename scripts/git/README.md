file: scripts/git/README.md
title: Tracked git hooks (local install)


## What this is
Deterministic pre-commit protection: blocks commits that stage disallowed binary types
or **new** files over **512 KB** before they enter git history. Enforcement lives in
Git, not in agent docs.

### Blocked by extension (always, unless allowlisted)
Session DBs and editor state: `.sqlite`, `.sqlite3`, `.db`, `.vscdb`

Images: `.webp`, `.jpg`, `.jpeg`, `.gif`, `.png`, `.bmp`, `.tiff`, `.tif`, `.ico`,
`.heic`, `.heif`

Audio/video: `.mp3`, `.wav`, `.m4a`, `.flac`, `.aac`, `.ogg`, `.wma`, `.mp4`, `.mov`,
`.avi`, `.mkv`, `.webm`

Archives: `.zip`, `.tar`, `.gz`, `.tgz`, `.bz2`, `.xz`, `.7z`, `.rar`

Office / documents: `.doc`, `.docx`, `.ppt`, `.pptx`, `.xls`, `.xlsx`, `.pdf`

Binaries / libs: `.dylib`, `.so`, `.dll`, `.exe`, `.bin`, `.jar`, `.war`, `.wasm`

ML / data blobs: `.pkl`, `.pickle`, `.onnx`, `.pt`, `.pth`, `.npy`, `.npz`, `.parquet`

Transcript pipeline dumps (suffix match): `*.deepgram.json`, `*.transcription.raw.json`

Aligned with root `.gitignore` media and large-binary policy.

### Size rule (new files only)
Any **new** staged file over **512 KB** is blocked. Files already tracked in `HEAD`
can be modified without triggering the size check (legacy large paths stay committable).
During an in-progress merge, paths already present on `MERGE_HEAD` (the commit being
merged in) are also exempt — so bringing main’s renamed/moved large files onto a
long-lived feature branch does not false-positive as a brand-new blob.

### Allowlisted exceptions (small runtime assets already tracked)
- `apps/math-quiz/sounds/*.mp3`
- `apps/games/robopoli/sounds/*.wav`
- `apps/math-quiz/sql-wasm.wasm`

FoF applet TTS mp3s are **not** allowlisted — they live in S3 (`manifests/focusonfoundations_applet-audio.manifest.jsonl`); pull via `apps/focusonfoundations/web` `npm run audio:pull` before test/build/deploy.


## One-time install (each machine / clone)
From the repo root:
```bash
./scripts/git/install-hooks.sh
```
This sets **local** `core.hooksPath` to `scripts/git/hooks/` (stored in `.git/config`).
All worktrees of the same repo share that config — run once, not per worktree window.

**Worktree bootstrap** (`./scripts/worktree_bootstrap.sh`) checks this and installs hooks
when missing (interactive prompt on a TTY; auto-install when non-interactive / agents).

Verify:
```bash
git config core.hooksPath
# -> scripts/git/hooks
```

Emergency bypass (explicit): `git commit --no-verify`


## Cloud agents
Ephemeral cloud clones do not run the installer automatically. **Before the first commit**
in a session, run `./scripts/git/install-hooks.sh` (or run `./scripts/worktree_bootstrap.sh`,
which installs hooks when missing). See root `AGENTS.md` → Commit hygiene.


## Smoke test — should fail
```bash
git add apps/math-quiz/_assets/pipa_no_wand_clap_jump_fixed.webp
git commit -m "test hook"
git restore --staged apps/math-quiz/_assets/pipa_no_wand_clap_jump_fixed.webp
```
