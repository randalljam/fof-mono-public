file: skills/web/minecraft-mod-publish/README.md
title: MC — Minecraft mod publish
source-github-url: original
source-guide-url: original
history:
  - 2026-07-19 · Randy True · Cursor [Minecraft bestiary web viewer](03bb58d9-b1ae-4dbf-ae3e-a80fca72b5d1) — created JAR-to-static-site workflow, responsive book defaults, QA gates, and scoped production publishing

**Extract assets and guide content from a Minecraft mod, build and verify a local static website, then publish it as an unlisted production page when explicitly requested.**


## When to use
Use when the user asks to turn a Minecraft mod JAR, in-game guide, bestiary, manual, recipe book, or other mod assets into a website; asks for “MC” or “Minecraft mod publish”; or wants to update an existing mod-derived static page.


## Required inputs
Establish these before building:

- Absolute path to the exact mod JAR and its Minecraft/mod version.
- Desired local output folder. Default to a gitignored path under `data/minecraft/`.
- Whether the source is a book/guide or another UI format.
- Desired production URL slug and whether it must remain unlisted.
- Permission to republish the mod’s text and artwork. Inspect the mod license and attribution requirements; do not assume public JAR assets are licensed for website publication.
- Whether the user wants local-only work, production publishing, or both.

Do not publish the JAR, source maps containing private paths, QA artifacts, credentials, personal data, or unrelated extracted assets.


## Workflow
1. Inventory the JAR and identify the guide’s actual data model.
2. Reproduce the in-game rendering locally.
3. Build a self-contained static site.
4. verify every page and target device.
5. Get local user approval.
6. Publish only through the scoped production workflow when the user explicitly requests it.
7. Verify the production URL independently from localhost.


## 1. Inspect before extracting
Treat the JAR as a ZIP. Inventory paths before copying anything:

```bash
unzip -l "/ABSOLUTE/PATH/mod.jar"
```

Look for:

- `assets/<modid>/lang/` and guide text files
- `assets/<modid>/textures/gui/`, `textures/item/`, `textures/block/`, and custom fonts
- guide definitions, chapter ordering, recipes, page overlays, and localization keys
- code or mappings that define blit coordinates, UV texture dimensions, page turns, and draw order

Extract only required files into the local build output. Preserve source names in a manifest so missing or ambiguous assets are auditable.

Do not infer texture geometry from the PNG dimensions alone. Minecraft GUI code may blit a region using a virtual texture size different from the source image. Reproduce the runtime UV/blit math.


## 2. Build locally
Prefer a deterministic builder plus generated static output:

```text
<output>/
  build_<viewer>.py
  index.html
  <viewer>.css
  <viewer>.js
  <viewer>-manifest.json
  assets/
    pages/
  qa_<viewer>.py
  serve.sh
```

Use `.venv/bin/python3` for Python. Keep generated/local assets under `data/`; that directory is gitignored and reserved for data. Do not add source packages under `data/`.

The production site should need only static HTTP hosting. Do not require the JAR, Python, npm, or a backend at runtime.

Pre-render complex guide pages to PNG when exact game-like placement matters. Use a render scale such as 3× for crisp text and pixel art, then display with `image-rendering: pixelated`. Keep navigation and responsive behavior in HTML/CSS/JS.


## 3. Book and guide defaults
For an in-game book, use the responsive defaults in `skills/web/minecraft-mod-publish/references/book-viewer-defaults.md`.

The required baseline is:

- Desktop and iPad: full left/right spread.
- iPhone portrait: one leaf at a time, left then right.
- Phone index: one leaf and one chapter column at a time, not a squeezed two-column spread.
- Bottom controls: visible, evenly sized, safe-area padded, and never covered by the book.
- Add to Home Screen: production URL only; standalone mode fills the home-indicator safe area with the app background.

Do not call phone mode complete after testing chapter pages only. Test the index and chapter views independently.


## 4. Content and visual QA
Build automated checks that fail on:

- missing manifest images or assets
- wrong output dimensions
- text cut off mid-word or beyond page bounds
- icons, drawings, and recipes overlapping text
- content crossing the spine or page rim
- images spilling below the book
- duplicate or stacked overlays

Create representative QA screenshots, including:

- introduction/text-heavy page
- item-heavy page
- recipe-heavy page
- large creature illustration
- first and last index pages
- left and right leaves from the same spread

Compare against the game or trusted screenshots. Check typography, book UV/background, spine location, bottom rim, draw order, and icon scale.


## 5. Browser and device QA
Serve from the output directory:

```bash
.venv/bin/python3 -m http.server 9876 --bind 0.0.0.0
```

Do not rely only on visual inspection. Use browser automation and assert geometry:

- iPhone 15 Plus portrait: `430 × 932`
- regular iPad portrait: `820 × 1180`
- iPad with reduced Safari content height: approximately `820 × 1000`
- desktop: `1280 × 800`

Assert:

- phone index and chapter shell ratio equals one leaf
- phone book occupies roughly the available width
- phone left/right navigation changes the crop instead of squashing the spread
- all bottom buttons fit inside the viewport and have equal widths
- book bottom does not overlap HUD title or buttons
- iPad and desktop retain the spread ratio
- iPad is not misclassified when Safari reports a desktop-style user agent

Review screenshots after assertions pass. Headless geometry passing is necessary but not sufficient.


## 6. Local approval gate
Before production:

1. Give the user the LAN/local URL.
2. Ask them to check the actual phone and iPad.
3. Iterate locally until explicitly approved.
4. List production files separately from build/dev files.

For a pre-rendered viewer, production normally includes:

```text
index.html
viewer.css
viewer.js
viewer-manifest.json
assets/
```

Do not deploy builders, source JARs, QA scripts/screenshots, caches, or obsolete manifests.


## 7. Production publish
Read and follow `skills/web/minecraft-mod-publish/references/production-publish.md`.

Key constraints:

- Publish only when the user explicitly requests production.
- Use the source folder’s absolute path because it may be gitignored and absent from another worktree.
- Use the scoped static-page deploy tool; never run a whole-site deploy for an unlisted page.
- Run a cancelled report first and inspect every addition, change, and deletion.
- Abort on any key outside the requested slug or any unexplained deletion.
- Use `--no-delete` for partial updates.
- Verify the production URL and assets after CloudFront invalidation.


## 8. Report
Report:

- local output path and source JAR/version
- page/chapter count and what was extracted
- QA commands and device results
- production URL and S3 prefix, if published
- files uploaded, kept, or deleted
- confirmation that staging and unrelated production paths were untouched
- exact scoped redeploy command


## Reference implementation
The Ice and Fire viewer developed in the source thread is the canonical example:

```text
data/minecraft/bestiary/
data/minecraft/bestiary/build_bestiary_viewer.py
data/minecraft/bestiary/qa_spotcheck.py
data/minecraft/bestiary/bestiary-manifest.json
data/minecraft/ice-and-fire-bestiary.md
```

These paths are local/gitignored and may not exist in every checkout. Use them when available as implementation evidence, not as a runtime dependency of this skill.
