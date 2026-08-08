file: skills/web/minecraft-mod-publish/references/production-publish.md
title: Production-only publish — Focus on Foundations static/unlisted pages
source-github-url: original
source-guide-url: original
history:
  - 2026-07-19 · Randy True · Cursor [Minecraft bestiary web viewer](03bb58d9-b1ae-4dbf-ae3e-a80fca72b5d1) — imported scoped production-only publishing procedure

## Production-only publish (skip staging) — Focus on Foundations static/unlisted pages

Use this path **only when the user explicitly says** to skip staging and push straight to production at a given URL (for example `/bestiary`). Do **not** use the full Astro site deploy for this.

### Hard rules
- **Production only.** Never run `npm run deploy:staging` or touch the staging bucket.
- **Do not** run `npm run deploy:production` / `node scripts/deploy.js production`. That rebuilds the whole Astro site and runs `aws s3 sync --delete` across the bucket — unsafe when staging/WIP branches exist or when only adding an unlisted page.
- Use the scoped tool: `apps/focusonfoundations/web/scripts/deploy-static-page.js` via `npm run deploy:static-page`.
- Work from the Focus on Foundations website repo checkout that has `apps/focusonfoundations/web/` and a valid `deploy-config.json` (production bucket + CloudFront ID). AWS CLI credentials must be account `[AWS-ACCOUNT-ID]`.
- Source files may be gitignored under `data/` — copy from the absolute path the user provides; do not assume `git checkout` has the assets.
- Prefer an unlisted direct URL (no main nav links unless the user asks).

### Map URL → deploy args
If the user wants `https://www.focusonfoundations.org/<slug>/` (or `https://focusonfoundations.org/<slug>/`):
- `--slug <slug>` — no leading/trailing slash (e.g. `bestiary`, or `minecraft/ice-and-fire-bestiary`)
- `--base-href /<slug>/` — **required** for extensionless routes so relative CSS/JS/asset paths resolve under the slug (must exactly match `/<slug>/`)
- `--source <absolute-path-to-local-folder>` — folder containing the built static site
- `--allow <entry>` — one or more source-relative files/dirs to upload (repeatable)

### First publish (full page under the slug)
Allow every production file the page needs. Example for a bestiary-style static viewer:

```bash
cd apps/focusonfoundations/web
printf 'CANCEL\n' | npm run deploy:static-page -- \
  --source /ABSOLUTE/PATH/TO/LOCAL/PAGE \
  --slug bestiary \
  --allow index.html \
  --allow bestiary.css \
  --allow bestiary.js \
  --allow bestiary-manifest.json \
  --allow assets \
  --base-href /bestiary/
```

(Replace `bestiary` / paths / allowlist with the user’s URL and files. Omit allow entries that do not exist.)

### Partial update (replace only some files; leave rest on S3)
If the user says to update only certain files (e.g. `index.html`, `bestiary.css`, `bestiary.js`) and leave `assets/` / manifest already on production:

```bash
cd apps/focusonfoundations/web
printf 'CANCEL\n' | npm run deploy:static-page -- \
  --source /ABSOLUTE/PATH/TO/LOCAL/PAGE \
  --slug bestiary \
  --allow index.html \
  --allow bestiary.css \
  --allow bestiary.js \
  --base-href /bestiary/ \
  --no-delete
```

**Always use `--no-delete` for partial updates.** Without it, remote keys under the slug that are not in the allowlist are reported as **DELETIONS** and would be removed after confirmation.

### Mandatory report review before confirming
1. Run the command once with confirmation cancelled (`printf 'CANCEL\n' | …`) so it prints the report and makes **no** changes.
2. Read the report. Expected for a safe additive/partial publish:
   - Every key under `bestiary/` (or the requested slug) only — never `/`, `/demos/`, `/_astro/`, applets, etc.
   - For a first publish: additions under the slug; deletions `0` (unless intentionally replacing/removing under that slug).
   - For a partial update with `--no-delete`: only the allowlisted files as CHANGES/ADDITIONS; DELETIONS `(0)`; other keys listed as KEPT REMOTE.
3. **ABORT in big red terms and do not confirm** if the report shows:
   - Any key outside the requested slug prefix
   - Unexpected deletions of assets/manifest or other site content
   - Changes that are not explained by the user’s requested files
4. If the report is clean, re-run the same command and type the exact phrase it prints:
   - `DEPLOY <slug> TO PRODUCTION`
   - Example: `DEPLOY bestiary TO PRODUCTION`
   - Non-interactive: `printf 'DEPLOY bestiary TO PRODUCTION\n' | npm run deploy:static-page -- …`

### What the tool does (do not reinvent)
- Compares local allowlisted files to S3 under that slug by content hash (SHA-256 / metadata / ETag)
- Uploads only additions/changes; with default mode, deletes stale keys **only under the slug**; with `--no-delete`, never deletes
- Injects `<base href="/<slug>/">` into deployed `index.html` when `--base-href` is set (source file on disk stays unchanged)
- Invalidates CloudFront only for `/<slug>` and `/<slug>/*` (not `/*`)
- Never builds Astro, never targets staging

### After deploy — verify
```bash
# Live URL (www and apex both fine; CloudFront rewrite serves index.html)
curl -fsSIL "https://www.focusonfoundations.org/<slug>/"
curl -fsS "https://www.focusonfoundations.org/<slug>/" | head -40   # expect <base href="/<slug>/">

# Spot-check allowlisted assets return 200
curl -fsSIL "https://www.focusonfoundations.org/<slug>/bestiary.css"
# etc.
```

Browser-check: open the **production** URL only (not `localhost`, not LAN `:9876`). Confirm the page loads, relative assets work, and any device behaviors the user asked for (e.g. iPhone single-page vs desktop/iPad double-page). If they mention Add to Home Screen, they must add the icon from the **production** URL.

### Report back to the user
- Final production URL: `https://www.focusonfoundations.org/<slug>/`
- S3 prefix: `s3://[S3-SITE-BUCKET]/<slug>/`
- What was uploaded vs kept; that staging was not touched
- Redeploy command for next time (include `--no-delete` if partial)

### Docs in repo
See `apps/focusonfoundations/README.md` → “Safe scoped production deploy for unlisted pages”.
