**guide to what types of files in include and exclude in repos**

Yes: for your Level 2 profile, I would stop treating the monorepo as a remote file-sharing service and instead make it a reproducible source-of-truth repo plus an S3-backed data/artifact store.

The repo should contain code, tests, specs, schemas, prompts, small representative fixtures, and manifests that say where larger files live. S3 should contain raw audio, raw Deepgram JSON, large transcript corpora, generated artifacts, build outputs, conversion outputs, and archived files. The missing piece is not just “upload to S3”; it is upload to S3 with a naming convention, manifest, hashes, and fetch/upload scripts.

GitHub’s own guidance is aligned with this: repositories should ideally remain under 1 GB and under 5 GB is strongly recommended; regular Git files over 50 MiB trigger warnings and files over 100 MiB are blocked on GitHub. GitHub also explicitly recommends storing generated files outside Git, such as in object storage.  ￼

⸻

## 1. The core policy

Use this mental model:

Category	Put in Git?	Put in S3?	Notes
Source code	Yes	No	Python, Java, scripts, infra code, app code.
Tests	Yes	No	Unit/integration tests.
Small test fixtures	Yes	Sometimes	Keep tiny representative samples in Git.
Prompts/templates/schemas	Yes	No	Especially important for AI workflows.
Human-authored docs/specs	Yes	Sometimes	Markdown specs belong in Git. Large docs may belong in S3.
Final small Markdown transcripts	Maybe	Maybe	Git is okay if small, canonical, private, and text-based.
Raw audio/video	No	Yes	MP3/WAV/M4A/MP4 should not be in Git.
Raw Deepgram JSON	Usually no	Yes	Keep only small fixtures in Git.
Generated transcripts	Usually no	Yes	Unless manually edited into canonical project docs.
Converted Word/PPT/PDF archives	Usually no	Yes	Keep conversion scripts and manifests in Git.
Build artifacts	No	Sometimes	JARs, wheels, zips, compiled outputs should not be committed.
Logs/caches/temp files	No	Sometimes	Usually ignore; upload only if needed for audit/debugging.
Secrets/config credentials	No	No, not raw	Use secret managers/env vars, not Git or ordinary S3 blobs.
Data manifest/index	Yes	Maybe	Git should track the catalog of external data.

The practical rule: Git should tell you how to reproduce or retrieve something; S3 should store the bulky thing itself.

⸻

## 2. Your specific transcript/data situation

You have several different “data” types that should be treated differently.

File type	Recommendation	Reason
MP3/audio recordings	S3 only; ignore in Git	Large, binary, not diff-friendly, often sensitive.
Deepgram raw JSON responses	S3 by default; small samples in Git only as fixtures	Useful for reproducibility, but raw API responses can be large and sensitive.
Extracted raw Markdown transcripts	S3 if generated/intermediate; Git if small and canonical	If they are just pipeline outputs, store outside Git. If they are hand-edited final documents, Git may be acceptable.
Manually polished transcript Markdown	Git or S3 depending on sensitivity/size	Git is useful for human text editing history, but private/sensitive transcripts may be better in S3 with access controls.
300-file AI-ready Markdown archive	If small and canonical: Git is okay; if large/private: S3 + manifest	Text diffs well in Git, but large corpora can bloat history.
Word/PPT/PDF source files	S3	Binary, large, poor Git diffs.
Conversion scripts	Git	These are source code.
Conversion outputs	S3 unless they are small canonical docs	Generated outputs should generally not be committed.
Minecraft mod build outputs	Ignore; publish release artifacts elsewhere	Build artifacts are reproducible from source.
Minecraft/Gradle wrapper files	Commit	Gradle says the wrapper is designed to be committed so others can build without installing a specific Gradle version first.  ￼

For the transcript workflow, I would make one distinction especially explicit:

Human-edited Markdown that represents final canonical project knowledge may live in Git. Raw/intermediate/generated transcript material should live in S3.

That gives your assistant a practical workflow: she can still edit text files when that is the work product, but the repo stops accumulating every raw and generated stage of every pipeline.

⸻

## 3. Recommended monorepo structure

I would change your data/ folder so it is no longer the actual data lake. Instead, make it the data catalog area.

repo-root/
  apps/
  packages/
  infra/
  tools/
  scripts/
    data/
      fetch_asset.py
      upload_asset.py
      validate_manifest.py
      list_assets.py
  data/
    README.md
    manifests/
      assets.jsonl
      transcript_assets.jsonl
      conversion_archive_assets.jsonl
    schemas/
      asset_manifest.schema.json
      deepgram_response.schema.json
    samples/
      deepgram/
        small_fixture.deepgram.json
      transcripts/
        sample_transcript.md
  content/
    canonical_transcripts/
      project-a/
        final-edited-transcript-001.md
  artifacts/          # ignored
  data_local/         # ignored
  .data/              # ignored
  tmp/                # ignored

Recommended meaning:

Path	Meaning
data/manifests/	Git-tracked index of external files.
data/schemas/	Git-tracked JSON schemas and validation specs.
data/samples/	Small representative test fixtures only.
content/	Optional Git-tracked canonical human-edited Markdown.
data_local/ or .data/	Local downloaded S3 files; always ignored.
artifacts/	Local generated outputs; always ignored.

Do not keep all real data under data/. Use data/ to describe data, not store all data.

⸻

## 4. S3 layout

Use S3 as a structured object store, not a miscellaneous bucket.

Example:

s3://your-org-project-data/
  projects/
    transcript-project-a/
      raw/
        audio/
          2024-02-14/session-001/source.mp3
        deepgram/
          2024-02-14/session-001/deepgram-response.json
      intermediate/
        extracted-markdown/
          2024-02-14/session-001/transcript.md
      curated/
        transcripts/
          2024-02-14/session-001/final.md
      exports/
        ai-ready-archive/
          2025-11-01/archive-v1.zip
    minecraft-mod/
      releases/
        v0.1.0/
          mod-name-0.1.0.jar

For raw objects, prefer immutable keys. Do not overwrite:

bad:
  projects/foo/raw/deepgram/latest.json
better:
  projects/foo/raw/deepgram/2026-05-14/session-001/deepgram-response.sha256_abcd1234.json

If you enable S3 Versioning, remember that S3 stores multiple object versions and each version is a full object, not a diff; AWS says normal rates apply to every stored version.  ￼ For your use case, I would still enable versioning on important buckets, but I would also design the workflow so raw inputs are normally immutable and not overwritten.

Use lifecycle rules for storage cost management. S3 Lifecycle can transition objects to other storage classes such as Intelligent-Tiering, Standard-IA, One Zone-IA, or Glacier classes, and can also expire objects.  ￼

⸻

## 5. The data manifest: the thing Git should track

Every S3 object that matters should have a Git-tracked manifest row.

Use JSONL because it is easy to append, diff, and parse:

{"asset_id":"asset_20260514_001","project":"transcript-project-a","kind":"audio","stage":"raw","format":"mp3","s3_uri":"s3://your-org-project-data/projects/transcript-project-a/raw/audio/2026-05-14/session-001/source.mp3","sha256":"...","size_bytes":123456789,"created_at":"2026-05-14T18:20:00Z","source":"manual_upload","pii_class":"private","status":"active"}
{"asset_id":"asset_20260514_002","project":"transcript-project-a","kind":"deepgram_response","stage":"raw","format":"json","s3_uri":"s3://your-org-project-data/projects/transcript-project-a/raw/deepgram/2026-05-14/session-001/deepgram-response.json","sha256":"...","size_bytes":987654,"created_at":"2026-05-14T18:30:00Z","source_asset_id":"asset_20260514_001","processor":"deepgram","pii_class":"private","status":"active"}
{"asset_id":"asset_20260514_003","project":"transcript-project-a","kind":"transcript","stage":"curated","format":"markdown","s3_uri":"s3://your-org-project-data/projects/transcript-project-a/curated/transcripts/2026-05-14/session-001/final.md","sha256":"...","size_bytes":45678,"created_at":"2026-05-14T19:00:00Z","source_asset_id":"asset_20260514_002","pii_class":"private","status":"active"}

Recommended fields:

Field	Purpose
asset_id	Stable internal ID.
project	Project or client/workstream.
kind	audio, deepgram_response, transcript, pptx, markdown_archive, etc.
stage	raw, intermediate, curated, export, release.
format	mp3, json, md, docx, pptx, pdf, jar.
s3_uri	Canonical object location.
sha256	Verifies file identity.
size_bytes	Helps prevent repo/data bloat.
created_at	Timestamp.
source_asset_id	Parent object, if any.
processor	Tool/model/API/pipeline version.
pii_class	public, internal, private, sensitive.
status	active, archived, superseded, deleted.
notes	Short human note, but no secrets.

This manifest is what makes S3 usable by agents and humans. Without it, S3 becomes a bucket-shaped junk drawer.

⸻

## 6. Should you just upload to S3, then download when needed?

Yes, but with a controlled workflow:

1. Agent or human needs data.
2. They search/read the Git-tracked manifest.
3. They run a fetch script using asset_id, project, or stage.
4. The file downloads into data_local/ or .data/.
5. Processing writes outputs to artifacts/ or data_local/outputs/.
6. Important outputs are uploaded to S3.
7. The manifest is updated in Git.

Example commands:

python scripts/data/fetch_asset.py --asset-id asset_20260514_002
python scripts/data/fetch_project.py --project transcript-project-a --stage curated
python scripts/data/upload_asset.py \
  --project transcript-project-a \
  --kind transcript \
  --stage curated \
  --file data_local/session-001/final.md
python scripts/data/validate_manifest.py

This gives you the benefit you originally wanted from “repo as file sharing” without making every clone carry years of historical data.

The AWS CLI s3 sync command can upload/download between local folders and S3, and it supports --include and --exclude filters.  ￼ For your workflow, I would wrap aws s3 cp / aws s3 sync in your own scripts so agents do not invent inconsistent bucket paths.

⸻

## 7. S3 indexing options

Start simple, then upgrade only when needed.

Level 2 default: Git manifest + S3 prefixes + S3 tags

Use:

Git manifest: data/manifests/assets.jsonl
S3 key structure: projects/<project>/<stage>/<kind>/...
S3 tags: project, stage, kind, pii_class, owner, status

S3 object tags are useful for classification, lifecycle rules, analytics, and access control; AWS allows up to 10 tags per object, and AWS specifically warns not to put confidential data inside tag values.  ￼

Use tags like:

project=transcript-project-a
stage=raw
kind=deepgram-response
pii=private
owner=ops
status=active

Do not use tags like:

client_name=Actual Private Client Name
speaker=Actual Person Name

When the bucket grows: S3 Inventory + Athena

If you accumulate thousands or millions of objects, use S3 Inventory and Athena. AWS says S3 Inventory can be queried with Athena, Redshift Spectrum, Presto, Hive, Spark, and similar tools; Athena can query S3 Inventory files in ORC, Parquet, or CSV, with ORC/Parquet recommended for faster and lower-cost queries.  ￼

Newer AWS-native option: S3 Metadata

AWS also has S3 Metadata tables, which automatically capture system metadata, user-defined metadata, tags, and event metadata into read-only Apache Iceberg tables queryable through analytics services.  ￼ This may be useful later, but I would still keep your own Git manifest because it encodes your project semantics, parent/child relationships, and processing lineage.

⸻

## 8. Git LFS, DVC, or plain S3?

You have three realistic options.

Option	Use when	Avoid when
Plain S3 + Git manifest	Best Level 2 default for your transcript/archive workflow	You need Git-like dataset checkout/versioning.
DVC + S3	You want data versioning integrated with Git commits	You want the simplest workflow for an assistant editing transcripts.
Git LFS	You have a small number of binary assets needed inside the repo	You have lots of raw audio, generated files, or frequently changing large files.

DVC remotes are designed for sharing large files/directories referenced by a DVC project, and DVC supports S3 as a remote storage backend.  ￼ DVC is worth considering if you want to say: “this Git commit corresponds to this exact dataset version.” But for your current practical workflow, I would start with plain S3 + manifest + scripts.

Git LFS is useful but not my first recommendation for your transcript system. GitHub LFS has plan-dependent per-file limits, and GitHub LFS billing counts storage and bandwidth; importantly, when you change and push an LFS file, a new version of the entire file counts toward storage.  ￼ That is not ideal for many transcript/audio/generated-data files.

⸻

## 9. Recommended .gitignore

This is a strong starter .gitignore for your monorepo. Adjust names to your repo.
``` markdown
# ============================================================
# Local data and external artifacts
# ============================================================
# Local downloads from S3 or other object stores
/data_local/
/.data/
/datasets/
/external_data/
# Generated artifacts and pipeline outputs
/artifacts/
/outputs/
/generated/
/runs/
/tmp/
/temp/
/cache/
# Logs
/logs/
*.log
# Raw media: store in S3, not Git
*.mp3
*.wav
*.m4a
*.flac
*.aac
*.ogg
*.mp4
*.mov
*.avi
*.mkv
# Large/archive/binary document formats: store in S3 unless explicitly approved
*.zip
*.tar
*.tar.gz
*.tgz
*.7z
*.rar
*.doc
*.docx
*.ppt
*.pptx
*.xls
*.xlsx
*.pdf
# Raw/generated transcript pipeline data
/data/raw/
/data/intermediate/
/data/generated/
/data/exports/
# But keep data documentation/catalog/schemas/samples
!/data/README.md
!/data/manifests/
!/data/manifests/**
!/data/schemas/
!/data/schemas/**
!/data/samples/
!/data/samples/**
# Avoid blanket ignoring all JSON; configs often use JSON.
# Instead ignore known generated/raw transcript response patterns.
*.deepgram.json
*.transcription.raw.json
# ============================================================
# Python
# ============================================================
.venv/
venv/
env/
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/
.ipynb_checkpoints/
# ============================================================
# Node/web
# ============================================================
node_modules/
dist/
.next/
.nuxt/
.vite/
coverage/
# ============================================================
# Java / Gradle / Minecraft modding
# ============================================================
.gradle/
**/build/
**/out/
*.class
# Ignore generated mod jars under build output.
# Do not globally ignore all *.jar because gradle/wrapper/gradle-wrapper.jar should be committed.
**/build/libs/*.jar
# Common IDE files
.idea/
.vscode/*
!.vscode/settings.example.json
*.iml
# OS/editor noise
.DS_Store
Thumbs.db
*.swp
*.swo
# ============================================================
# Secrets and local config
# ============================================================
.env
.env.*
!.env.example
*.pem
*.key
*.crt
*.p12
*.pfx
.aws/
```

Important: adding something to .gitignore does not affect files already tracked by Git. The Git documentation says ignored patterns are for intentionally untracked files; already tracked files are not affected.  ￼

So if a file is already in Git and you want to stop tracking it:

git rm --cached path/to/file
git commit -m "Stop tracking generated data file"

If it is already in history and causing major bloat or contains sensitive material, that is a separate cleanup problem.

⸻

## 10. Add pre-commit protection

Use pre-commit hooks so you and agents cannot casually add huge files.

Example .pre-commit-config.yaml:

repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v6.0.0
    hooks:
      - id: check-added-large-files
        args: ["--maxkb=1024"]
      - id: detect-private-key
      - id: check-json
      - id: check-yaml
      - id: check-toml
      - id: check-merge-conflict
      - id: end-of-file-fixer
      - id: trailing-whitespace

The check-added-large-files hook is specifically intended to prevent giant files from being committed, and it supports a configurable maximum size.  ￼

I would set the default to 1 MB. That sounds strict, but it forces conscious decisions. You can still allow exceptions.

Recommended thresholds:

Size	Policy
Under 1 MB	Usually fine if appropriate file type.
1–10 MB	Requires reason; prefer S3 for generated/binary/data files.
10–50 MB	Almost always S3 or release artifact.
50–100 MB	Do not commit to GitHub; GitHub warns above 50 MiB.
100 MB+	Blocked by GitHub regular Git.

⸻

## 11. Agent instructions for AGENTS.md / CLAUDE.md

AGENTS.md is intended as a dedicated instruction file for coding agents, and the spec supports nested files in monorepos so subprojects can have tailored instructions.  ￼ Claude Code also reads CLAUDE.md from the project root at the start of a session.  ￼

I would make AGENTS.md the canonical file and either copy or symlink the same content into CLAUDE.md.

Paste this section into your root AGENTS.md / CLAUDE.md:

## Repository File Policy
This repository is a source-code and reproducibility repository, not a general file-sharing service.
### Core rule
Commit source code, tests, documentation, schemas, prompts, small fixtures, and data manifests.
Do not commit large raw data, generated pipeline outputs, local downloads, build artifacts, logs, caches, or secrets.
When a large or generated file is needed, store it in S3 and update the Git-tracked manifest under `data/manifests/`.
### Files that belong in Git
Allowed by default:
- Source code under `apps/`, `packages/`, `infra/`, `tools/`, and `scripts/`.
- Tests and small test fixtures.
- Markdown documentation, project specs, coding standards, and runbooks.
- Prompt templates, evaluation specs, and JSON/YAML schemas.
- Data manifests under `data/manifests/`.
- Small sample data under `data/samples/`.
- Build configuration files such as `pyproject.toml`, `package.json`, `uv.lock`, `requirements*.txt`, `build.gradle`, `settings.gradle`, `gradle.properties`.
- Gradle wrapper files: `gradlew`, `gradlew.bat`, and `gradle/wrapper/**`.
### Files that do not belong in Git
Never commit these without explicit human approval:
- Audio/video files: `*.mp3`, `*.wav`, `*.m4a`, `*.flac`, `*.mp4`, etc.
- Raw transcription API responses, including Deepgram raw JSON, except tiny test fixtures.
- Generated or intermediate transcript outputs.
- Converted archive outputs from Word/PPT/PDF conversion pipelines.
- Build outputs: `build/`, `dist/`, `out/`, `target/`, `*.class`, generated JARs, wheels, zips.
- Dependency/cache folders: `.venv/`, `node_modules/`, `.gradle/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`.
- Local data folders: `data_local/`, `.data/`, `artifacts/`, `outputs/`, `runs/`, `tmp/`.
- Logs and debug dumps.
- Secrets, credentials, private keys, `.env` files, AWS credentials, tokens, certificates.
### Large-file rule
Before staging files, check file size and type.
- Files over 1 MB require a reason.
- Files over 10 MB should almost always go to S3.
- Files over 50 MB must not be committed.
- Files over 100 MB are forbidden in regular Git.
If a large file is necessary for release distribution, put it in S3 or a release artifact store, not in the repository.
### Data workflow
Use S3 for durable storage of raw, generated, and large data.
Use these local ignored folders:
- `data_local/` for downloaded S3 data.
- `.data/` for temporary local datasets.
- `artifacts/` for generated outputs.
- `outputs/` for pipeline outputs.
When adding an important external data file:
1. Upload the file to the correct S3 prefix.
2. Compute and record its SHA-256 hash.
3. Add or update a row in `data/manifests/*.jsonl`.
4. Include project, kind, stage, format, S3 URI, size, hash, source asset, processor, PII class, and status.
5. Do not commit the file itself unless it is a tiny approved fixture.
### Transcript policy
Raw audio, raw Deepgram JSON, and generated transcript intermediates go to S3.
Small final Markdown transcripts may be committed only when all of the following are true:
- They are canonical human-edited project content.
- They are not public-sensitive or legally sensitive.
- They are reasonably small.
- They are meant to be reviewed through Git diffs.
Otherwise, store final transcripts in S3 and track them in the manifest.
### Minecraft / Gradle policy
Commit source files and Gradle project files.
Commit:
- `src/**`
- `build.gradle` or `build.gradle.kts`
- `settings.gradle` or `settings.gradle.kts`
- `gradle.properties`
- `gradlew`
- `gradlew.bat`
- `gradle/wrapper/**`
Do not commit:
- `.gradle/`
- `build/`
- `out/`
- generated mod JARs under `build/libs/`
Release JARs should be uploaded as release artifacts or to S3.
### Before committing
Always run:
```bash
git status --short
git diff --cached --stat

Inspect staged files. Do not use blind git add . if the working tree contains data, generated files, local downloads, or build outputs.

Prefer:

git add path/to/specific/file

For new generated files, stop and decide whether they belong in S3 instead.

If a needed data file is missing locally

Do not recreate bucket paths manually. Use the repository data scripts:

python scripts/data/fetch_asset.py --asset-id <asset_id>
python scripts/data/fetch_project.py --project <project> --stage <stage>

If the scripts do not exist yet, create them instead of hardcoding one-off S3 commands throughout the repo.

---
# 12. Cursor rule version
Cursor supports persistent instructions through rules and AGENTS.md according to its docs.  [oai_citation:14‡Cursor](https://cursor.com/docs/rules?utm_source=chatgpt.com) I would create a focused project rule for this, either through Cursor’s UI or as a rule file depending on your current Cursor version.
Suggested `.cursor/rules/repository-file-policy.mdc`:
```markdown
---
description: Repository file policy for source, data, artifacts, and S3 usage
alwaysApply: true
---
# Repository File Policy
Treat this repository as a source-code and reproducibility repository, not a general file-sharing service.
Do commit:
- Source code, tests, docs, prompts, schemas, manifests, small fixtures.
- Data manifests under `data/manifests/`.
- Small samples under `data/samples/`.
- Build and dependency configuration files.
- Gradle wrapper files.
Do not commit:
- Raw audio/video.
- Raw Deepgram JSON except tiny fixtures.
- Generated transcript intermediates.
- Build outputs.
- Generated JARs/wheels/zips.
- Local data downloads.
- Logs, caches, temp files.
- Secrets or `.env` files.
Large-file rules:
- Files over 1 MB require a reason.
- Files over 10 MB should usually go to S3.
- Files over 50 MB must not be committed.
- Files over 100 MB are forbidden.
Data workflow:
- Download S3 data into `data_local/` or `.data/`.
- Write generated outputs to `artifacts/` or `outputs/`.
- Upload important generated/raw files to S3.
- Update `data/manifests/*.jsonl` with S3 URI, SHA-256, size, stage, kind, project, and status.
- Never invent one-off S3 paths if repository data scripts exist.
Before committing:
- Run `git status --short`.
- Run `git diff --cached --stat`.
- Inspect staged files.
- Avoid blind `git add .` when generated files or local data may be present.

⸻

13. Cleanup plan for your existing monorepo

Do this in stages.

Stage 1: Inventory

Run:

git count-objects -vH
du -sh .git
find . -type f -size +10M -not -path "./.git/*" -print

Then inspect tracked large files:

git ls-files | xargs -I{} sh -c 'test -f "$1" && du -h "$1"' sh {} | sort -h | tail -50

Stage 2: Add policy files

Add:

.gitignore
.pre-commit-config.yaml
AGENTS.md
CLAUDE.md
.cursor/rules/repository-file-policy.mdc
data/README.md
data/manifests/assets.jsonl
data/schemas/asset_manifest.schema.json

Stage 3: Move obvious data out of Git

For files that should no longer be tracked:

mkdir -p data_local_migration_backup
# copy important files somewhere safe first
git rm --cached path/to/large/or/generated/file
git commit -m "Stop tracking generated data files"

Upload them to S3 and add manifest rows.

Stage 4: Decide whether to rewrite history

If the repo is private, only used by you and your assistant, and the large files are merely annoying, you can choose not to rewrite history immediately. If the repo history is severely bloated or contains sensitive material, consider rewriting history with git-filter-repo.

History rewriting is disruptive: GitHub warns it requires coordination with anyone who cloned the repo, changes commit hashes, can affect PRs, and can reintroduce removed data if collaborators push old history back.  ￼

For a solo/private repo, this may be manageable. For a public or contributor-facing repo, be more cautious.

Stage 5: Create scripts so agents follow the system

At minimum:

scripts/data/
  upload_asset.py
  fetch_asset.py
  validate_manifest.py
  hash_file.py
  list_assets.py

The scripts should:

Script	Job
hash_file.py	Print SHA-256 and file size.
upload_asset.py	Upload to correct S3 prefix, set tags, update manifest.
fetch_asset.py	Download by asset_id into data_local/.
validate_manifest.py	Check JSONL validity, required fields, duplicate IDs, missing hashes.
list_assets.py	Search manifest by project/stage/kind/status.

⸻

14. My recommended final operating model for you

Use this:

Git monorepo
  = code + infra + automation + docs + specs + schemas + prompts + tests + small fixtures + manifests
S3
  = raw audio + raw Deepgram JSON + generated transcripts + large converted archives + release artifacts + large private content
Local ignored folders
  = downloaded data + temporary processing + generated outputs
Agents
  = forbidden from committing large/generated/local files
  = required to update manifests when using S3
  = required to inspect staged files before committing

For your current situation, I would not jump straight to a heavy professional data platform. I would implement:

1. .gitignore cleanup.
2. Pre-commit large-file blocking.
3. S3 bucket prefix convention.
4. Git-tracked assets.jsonl manifest.
5. Data fetch/upload scripts.
6. Agent rules in AGENTS.md, CLAUDE.md, and Cursor.

That will solve 80–90% of the problem while staying understandable for you, your assistant, and coding agents.
```

This file is the global portfolio map for the operator’s software, infrastructure, automation, transcript, content, and personal-system projects.
It is intended to give AI agents and human collaborators enough context to understand project purpose, status, repos, infrastructure, data handling, and risk boundaries.
Repo-specific instructions belong in each repo’s own `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, or equivalent files.
Do not store secrets, credentials, private keys, tokens, account numbers, or sensitive private details in this file.
## 1. Project Status Definitions
Use these status labels consistently.
### Active
The project is currently being developed or maintained.
### Maintenance
The project is mostly stable but may need bug fixes, small improvements, or dependency updates.
### Experimental
The project is exploratory and may change direction quickly.
### Paused
The project is not currently active but may resume later.
### Archived
The project is no longer active. Agents should not modify it unless explicitly instructed.
### Public / Open Source
The project is public or intended to be public.
### Private
The project contains private code, private notes, internal infrastructure, personal workflows, or unpublished ideas.
### Live
The project has deployed web, API, cloud, or automation components.
### Production-Like
The project has real infrastructure and should be treated carefully, even if it has few or no users.
## 2. Global Project Principles
Across projects:
- Prefer simple, maintainable systems appropriate for a serious solo developer.
- Do not assume a project has many users unless stated.
- Do not assume a project is revenue-generating unless stated.
- Treat live AWS-backed systems as production-like even if they are low-traffic.
- Separate source code from large data, generated outputs, and build artifacts.
- Use manifests and documented scripts for data stored outside Git.
- Avoid broad refactors unless they directly support the requested work.
- Keep public and private project materials clearly separated.
- Preserve future open-source compatibility where practical.
## 3. Project Index
| Project | Status | Repo | Visibility | Type | Live? | Notes |
|---|---|---|---|---|---|---|
| Main Corpus Tools | Active | `repo-name` | Private/Public | Monorepo / transcript tools / automation | Yes/No | Main long-running repo. |
| Minecraft Mod | Active/Experimental | `repo-name` | Private/Public | Game mod | No/Yes | Separate repo. |
| Shared LLM Core | Planned/Active | `repo-name` | Private/Public | Python package | No | Shared LLM wrapper utilities. |
| AWS Infra Core | Planned/Active | `repo-name` | Private | Infra package | Yes/No | Shared deployment patterns. |
## 4. Shared Components
### Shared Python Packages
List reusable Python packages here.
For each package:
- Name:
- Repo:
- Visibility:
- Purpose:
- Used by:
- Installation method:
- Release/versioning status:
- Test command:
- Notes:
### Shared Infrastructure Modules
List reusable AWS/CDK/Terraform/Pulumi/serverless components here.
For each module:
- Name:
- Repo:
- Visibility:
- Purpose:
- Used by:
- AWS services involved:
- Dev/prod support:
- Deployment risks:
- Notes:
### Shared Data/Content Workflows
List reusable transcript, conversion, archive, or data-processing workflows here.
For each workflow:
- Name:
- Repo:
- Purpose:
- Input types:
- Output types:
- Data storage:
- Manifest/index:
- Human editing step:
- Notes:
## 5. Project Records
Each project should have a record using the following template.
---
## Project: `<Project Name>`
### Summary
Briefly describe the project.
Include:
- What it is.
- Why it exists.
- Who uses it.
- Whether it is personal, internal, public, experimental, or infrastructure-backed.
### Current Status
- Status:
- Visibility:
- Live/deployed:
- Production-like:
- Has users:
- Revenue-generating:
- Current priority:
- Next milestone:
### Repositories
- Main repo:
- Related repos:
- Public repo:
- Private repo:
- Shared packages used:
- Shared infrastructure used:
### Project Type
Mark all that apply:
- Python package
- Web app
- API
- AWS-backed service
- Transcript-processing workflow
- Data/archive project
- Content-processing project
- Minecraft/game mod
- Personal automation
- Public open-source project
- Private internal project
- Other:
### Local Development
How to work on this project locally.
- Setup command:
- Run command:
- Test command:
- Build command:
- Lint/typecheck command:
- Important local folders:
- Known local requirements:
### Deployment / Infrastructure
Describe infrastructure at a high level.
- Cloud provider:
- AWS account/environment notes:
- Dev environment:
- Prod environment:
- Deployment command:
- AWS services:
- Domains/APIs:
- Logs/monitoring:
- Security resources:
- Cost-sensitive resources:
Agents must be careful with:
- 
- 
- 
Agents must not do without approval:
- 
- 
- 
### Data and Artifacts
Describe project data.
- Data types:
- Raw inputs:
- Generated outputs:
- Human-edited outputs:
- Build artifacts:
- S3 bucket/prefix:
- Manifest file:
- Local ignored data folders:
- Sensitive data classification:
Git policy:
- Files to commit:
- Files to ignore:
- Files to store in S3:
- Files that require approval:
### Public / Private Boundary
- Public-safe code:
- Private-only code:
- Private notes:
- Public docs:
- Unreleased ideas:
- Contributor-facing materials:
- Files that must never be public:
### Agent Instructions
Agents working on this project should read first:
- 
- 
- 
Agents may safely:
- 
- 
- 
Agents should avoid:
- 
- 
- 
Agents must ask or warn before:
- 
- 
- 
Preferred implementation style:
- 
- 
- 
### Testing and Quality Bar
- Required tests:
- Optional tests:
- Manual checks:
- CI status:
- Minimum acceptable validation before merge:
- Known weak spots:
### Current Risks
- 
- 
- 
Examples:
- Repo contains old generated files.
- AWS deployment paths are not fully standardized.
- Public/private boundaries are not clean yet.
- Tests are incomplete.
- Agent workflows are not fully guarded.
### Roadmap
Near-term:
- 
- 
- 
Medium-term:
- 
- 
- 
Long-term:
- 
- 
- 
### Archive / Cleanup Notes
Use this section for old project history, migration notes, and cleanup decisions.
- Files to migrate:
- Data to move to S3:
- Code to split into shared package:
- Repos to merge:
- Repos to archive:
- Docs to write:

⸻

Suggested relationship between the files

Use them like this:

PROFILE.md
  Describes you, collaborators, AI-agent expectations, autonomy, skill level, risk tolerance.
PROJECTS.md
  Describes the portfolio of projects, repos, infrastructure, data, and status.
AGENTS.md
  Describes how agents should work inside a specific repo.
CLAUDE.md
  Either references AGENTS.md or gives Claude-specific repo instructions.
.cursor/rules/*
  Cursor-specific behavior rules, usually repo-specific or project-specific.

A good root-level instruction in AGENTS.md or CLAUDE.md would be:

Before making architectural, repo-structure, data-storage, deployment, or public/private-boundary decisions, read:
- `PROFILE.md`
- `PROJECTS.md`
- this repo’s `AGENTS.md`
- this repo’s `CLAUDE.md` if present
Use `PROFILE.md` for operator preferences and autonomy boundaries.
Use `PROJECTS.md` for project status, infrastructure, data, and repo mapping.
Use repo-specific instruction files for local implementation rules.

⸻

My recommended first pass

For your first version, do not try to make these perfect. Create short but useful files.

Start with:

PROFILE.md
  1. Primary Human Operator
  2. AI-Assisted Coding Style
  3. Project Maturity Profile
  4. Approval Boundaries
  5. Security and Privacy Profile
  6. Communication Preferences
PROJECTS.md
  1. Project Status Definitions
  2. Global Project Principles
  3. Project Index
  4. Shared Components
  5. Project Records

Then add detail only when it helps an agent make better decisions.