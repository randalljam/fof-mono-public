# chatgpt pro (5.5) - FOF account in Coding
## 1. Organize by operational shape
The folder-structure problem is not just “where should files go?” It is really: how do you organize a growing software/workflow portfolio so AI agents can understand it, operate safely, and eventually help you move toward low-touch autonomous development? Your PROFILE.md says you are the primary system owner, final decision-maker, and “pure AI coder” rather than a professional software engineer, with projects spanning transcripts, education, automation, web apps, AWS-backed systems, and AI-assisted workflows.  ￼Your devlog also explicitly says the system should support more than 10 and fewer than 20 projects, increasing autonomy, reusable workflow patterns, and clear approval boundaries.  ￼

My recommendation: do not organize the monorepo primarily by life/project domain. Organize the repo by operational shape, and organize PROJECTS.md by project metadata.

__That means the filesystem should answer:__
“What kind of thing is this technically?”

__And PROJECTS.md should answer:__
“What project is this part of, what domain is it in, what is its status, who uses it, how risky is it, and what should agents know?”

Instead, use folders for how the thing behaves:

### Folder question	Example answer
Is this a deployed or deployable application?	apps/
Is this reusable code used by multiple projects?	packages/
Is this an automation/data/document pipeline?	workflows/
Is this infrastructure or deployment code?	infra/
Is this repo/project management context?	ops/ or system/
Is this generated or external data?	S3 + manifests, not source folders
Is this experimental?	experiments/
Is this retired but not deleted?	archive/

Then let PROJECTS.md hold the messy human meaning: education, Focus on Foundations, FloodLAMP, family, transcript processing, Minecraft, public/private, active/paused, AWS-backed, prototype, etc.

## 2. The main options

### Option A: domain-first monorepo
repo/
  education/
  transcripts/
  floodlamp/
  personal/
  minecraft/
  ai-coding-system/
  aws/

This feels natural because it matches how you think about your life and work.

Advantages

Advantage	Why it helps
Human-intuitive at first	You can say “this is an education project” or “this is FloodLAMP.”
Good for small portfolios	Works when there are only a few stable domains.
Easy for personal memory	Similar to a folder system on a computer.

Problems

Problem	Why it matters for you
Projects cross domains	FloodLAMP can be education, archive, web, nonprofit, and transcript-related.
Agents may infer too much from folders	A folder named personal/ or education/ does not tell an agent how to test, deploy, or modify code.
Shared code gets awkward	Does an LLM wrapper go under ai-coding-system, transcripts, or packages?
Public/private boundaries get muddy	A public education app and private family learning material should not be mixed just because both are “education.”

I would not use this as the main monorepo structure.

### Option B: app-first monorepo
repo/
  apps/
    floodlamp-archive/
    minecraft-mod/
    transcript-dashboard/
    family-learning-app/
  packages/
    llm-core/
    transcript-core/
    aws-utils/
  infra/
  docs/

This is closer to a typical software monorepo.

Advantages

Advantage	Why it helps
Clearer for software agents	Agents can identify apps, shared packages, and infra.
Easier to test and deploy	Each app can have its own run/test/deploy instructions.
Better for future public repos	An app can be extracted or mirrored more cleanly.
Encourages reusable packages	Shared code does not get buried inside one project.

Problems

Problem	Why it matters
Not enough for transcript/document workflows	Some of your work is not a normal “app.”
Can underrepresent content/data pipelines	Conversion workflows and transcript archives need their own category.
Needs good PROJECTS.md metadata	The folder alone does not say whether something is nonprofit, personal, public, private, active, or archived.

This is a strong option, but I would extend it.

### Option C: workflow-first monorepo
repo/
  transcript-processing/
  document-conversion/
  llm-extraction/
  web-publishing/
  aws-deployment/
  repo-analysis/

This fits your current corpus-tools history because a lot of the repo has been about processing files, transcripts, Deepgram outputs, Markdown conversions, and AI-ready archives.

Advantages

Advantage	Why it helps
Very natural for your data-pipeline work	Many current tasks are workflows rather than apps.
Good for EA-facing procedures	“Run the document conversion workflow” is clear.
Good for automation	Each workflow can have inputs, outputs, manifests, scripts, and runbooks.

Problems

Problem	Why it matters
Weak for actual applications	Web apps, Minecraft mods, and future products do not fit neatly.
Can blur source vs generated output	Workflows often produce lots of files, which you are trying to keep out of Git.
Shared libraries may be duplicated	Each workflow may grow its own helper code unless you separate packages.

Useful, but not enough as the top-level strategy.

### Option D: project-first monorepo
repo/
  projects/
    floodlamp-archive/
      app/
      infra/
      workflows/
      docs/
    transcript-archive/
      workflows/
      content/
      manifests/
    minecraft-mod/
      app/
      docs/
    ai-coding-system/
      orchestrator/
      docs/
      workflows/

Each project gets its own self-contained folder. This is appealing when you are struggling with PROJECTS.md, because the repo folder structure and project records line up one-to-one.

Advantages

Advantage	Why it helps
Easy to map to PROJECTS.md	Every folder can have a project record.
Good for agent context	Agents can stay inside one project folder.
Good for heterogeneous projects	A web app, Minecraft mod, and transcript workflow can each have their own shape.
Good for archiving	Move a whole project to archive/ when retired.

Problems

Problem	Why it matters
Shared code can get trapped	If project-a/app needs code from project-b/app, structure gets messy.
Reusable packages are less obvious	You still need packages/.
Multiple deployable apps inside one project can get confusing	Example: one project may have a public website, admin tool, and API.

This is a good option if the repo is mostly a portfolio of distinct projects. But for you, I would not make everything live only under projects/.

### Option E: hybrid operational monorepo
repo/
  apps/
  packages/
  workflows/
  infra/
  ops/
  docs/
  data/
  content/
  experiments/
  archive/

This combines the strengths of app-first, workflow-first, and project-first organization.

Advantages

Advantage	Why it fits you
Works for apps and non-app workflows	Your portfolio includes both.
Agent-friendly	Agents can infer whether they are modifying an app, package, workflow, or infra.
Extensible	New project types can be added without reorganizing everything.
Public-repo compatible	Apps/packages can later be extracted to public repos.
Keeps PROJECTS.md useful	The file becomes a portfolio map instead of trying to duplicate the filesystem.
Supports your low-touch goal	Clear folders make it easier for agents to route tasks, run tests, avoid data, and summarize risk.

This is the best default for your current state.


## 3. Recommended top-level monorepo structure
repo-root/
  AGENTS.md
  CLAUDE.md
  PROFILE.md
  PROJECTS.md
  ai-coding-system-dev.md
  README.md
  apps/
  packages/
  workflows/
  infra/
  ops/
  docs/
  data/
  content/
  experiments/
  archive/
  scripts/
  tests/
  .github/
  .cursor/

Now each top-level folder has a narrow job.

### definition for each folder
/apps - deployable or runnable applications
/packages - reusable code used by multiple apps or workflows
/workflows - pipelines and automations that process files, content, data, transcripts, or administrative work
/infra - cloud infrastructure and deployment code
/ops - AI coding operating system: standards, work orders, agent policies, approval packets, repo audits, and portfolio-level automation
/docs - cross-repo documentation that is not itself an operational rule
/data - manifests, schemas, and tiny fixtures — not bulk data
/content - human-edited canonical content that truly belongs in Git
/experiments - prototypes that may be thrown away
/archive - retired code that agents must not treat as active

### detail for each folder
#### apps/
apps/
  floodlamp-archive/
  transcript-dashboard/
  minecraft-mod/
  family-learning-app/
  ai-work-order-console/

An app is something a user can run, visit, install, or interact with.

Examples:

Thing	Folder
Web app	apps/floodlamp-archive/
Dashboard	apps/transcript-dashboard/
Minecraft mod	apps/minecraft-mod/
Mac menu bar app	apps/menu-bar-assistant/
Future mobile app	apps/family-learning-mobile/

Each app should eventually have:

apps/example-app/
  README.md
  AGENTS.md              # optional project-specific rules
  PROJECT.md             # optional local project record
  src/
  tests/
  docs/
  scripts/
  package/config files

Use apps/ even for prototypes if they are serious enough to keep. Very temporary experiments can start in experiments/.

#### packages/
packages/
  llm-core/
  transcript-core/
  corpus-tools-core/
  aws-deploy-core/
  markdown-conversion-core/

A package is code that multiple apps or workflows can import.

Examples:

Thing	Folder
LLM wrapper functions	packages/llm-core/
Transcript parsing utilities	packages/transcript-core/
Markdown conversion helpers	packages/markdown-conversion-core/
AWS deployment helpers	packages/aws-deploy-core/
Shared UI components	packages/ui/

This matters a lot for your agentic goal. If reusable code is clearly in packages/, agents are less likely to create duplicate helper functions inside random apps.

#### workflows/
workflows/
  deepgram-transcription/
  transcript-cleanup/
  markdown-archive-conversion/
  llm-extraction/
  ai-ready-archive/
  repo-audit/

A workflow is not mainly an app. It is a repeatable process.

Examples:

Thing	Folder
Deepgram JSON → Markdown	workflows/deepgram-transcription/
Manual transcript cleanup support	workflows/transcript-cleanup/
Word/PPT/PDF → Markdown conversion	workflows/markdown-archive-conversion/
Function-calling extraction loop	workflows/llm-extraction/
Repo/project audit generator	workflows/repo-audit/

Each workflow should have:

workflows/example-workflow/
  README.md
  AGENTS.md              # optional workflow-specific instructions
  inputs.example.md
  outputs.example.md
  runbook.md
  scripts/
  tests/
  samples/

This is especially important because your collaborator EA runs scripts, processes files, edits transcripts, proofreads Markdown, and needs safe predictable workflows. Your profile explicitly says workflows should be clear, safe, usable by a remote collaborator, avoid brittle one-off commands, separate source code from generated outputs, and use Markdown runbooks well.  ￼

#### infra/
infra/
  aws/
    shared/
    floodlamp-archive/
    transcript-api/
  templates/
    lambda-api/
    static-site/
    containerized-web-app/

This folder should not be a dumping ground for all deployment scripts. It should contain reusable infrastructure definitions, deployment templates, and project-specific IaC.

Examples:

Thing	Folder
Shared AWS patterns	infra/aws/shared/
App-specific AWS infra	infra/aws/floodlamp-archive/
Lambda/API Gateway template	infra/templates/lambda-api/
Containerized app template	infra/templates/containerized-web-app/

Your devlog says AWS is a major existing bias because you have already implemented API Gateway, Lambda, S3, Chalice, dev/prod paths, validation tooling, and deployment/testing scripts, while still needing to compare AWS with simpler platforms for agent-friendliness and complexity.  ￼ That argues for keeping infra visible and structured, not scattered through app folders only.

For apps with simple deployment, app-local deployment config can stay inside the app. For shared or complex AWS patterns, put the reusable pieces under infra/.

#### ops/
ops/
  agent-system/
  approval-packets/
  work-orders/
  repo-audits/
  standards/
  runbooks/

This is where your “system that manages the system” lives.

Examples:

Thing	Folder
Work order schema	ops/work-orders/
Approval packet templates	ops/approval-packets/
Agent workflow standards	ops/agent-system/
Repo audit reports	ops/repo-audits/
Safe Git runbooks	ops/runbooks/

Your prior system design says the personal version should use GitHub as source of truth, GitHub Issues/Projects as task ledger, Codex/Claude/Cursor as coding engines, GitHub Actions as verification, and a small orchestrator as glue.  ￼ The ops/ folder is the natural home for the glue, standards, and records that do not belong to just one app.

#### docs/
docs/
  architecture/
  decisions/
  guides/
  research/
  codeindex/

Examples:

Thing	Folder
Architecture decision records	docs/decisions/
Research notes	docs/research/
General guides	docs/guides/
Code index artifacts, if kept	docs/codeindex/

Your profile already mentions docs/codeindex/ as a historical area containing code index artifacts.  ￼ I would keep that under docs/ if it remains documentation/analysis, or move the actual generator code into workflows/repo-audit/ or packages/code-intelligence/ if it becomes active tooling.

#### data/
data/
  README.md
  manifests/
  schemas/
  samples/

Recommended rule:

data/ = Git-tracked description of data
data_local/ = ignored local downloaded data
S3 = real raw/generated/large data

Examples:

Thing	Folder
Asset manifest	data/manifests/assets.jsonl
Deepgram schema	data/schemas/deepgram-response.schema.json
Tiny test fixture	data/samples/deepgram-small.json
Downloaded audio	not in Git; data_local/
Raw transcript corpus	S3

This matches the previous file policy direction and supports your devlog’s near-term need to pare down the current repo into a cleaner source-only branch with bulk data and artifacts moved to S3.  ￼

#### content/
content/
  canonical-transcripts/
  public-site-copy/
  curriculum/
  essays/

This is optional, but useful for your case because some Markdown outputs are not just generated artifacts. Some may be final, human-edited, canonical knowledge or public content.

Rule:

Content type	Where it goes
Human-edited canonical Markdown	content/
Raw/generated transcript output	S3
Public website copy	content/ or app-local docs/content
Sensitive personal/family content	usually S3/private storage, not public Git

#### experiments/
experiments/
  2026-05-voice-to-prototype/
  2026-06-new-ui-library-test/
  2026-06-hosting-comparison/

Rule:

Experiments are allowed to be messy, but each experiment needs a short README explaining what it was testing and whether it should be promoted, archived, or deleted.

This is important because your devlog says the tool stack is uneven and the right combination per task class will only become clear through deliberate experimentation.  ￼

#### archive/
archive/
  old-webflow-exports/
  old-transcript-scripts/
  deprecated-prototypes/

Add an archive/README.md that says:

Agents must not modify archived projects unless explicitly instructed.
Archived code is retained for reference only.
Do not import from archived code into active code.

This prevents agents from “helpfully” reviving old patterns.


## 4. Recommended structure in full
repo-root/
  README.md
  PROFILE.md
  PROJECTS.md
  ai-coding-system-dev.md
  AGENTS.md
  CLAUDE.md
  apps/
    floodlamp-archive/
    minecraft-mod/
    transcript-dashboard/
    ai-work-order-console/
  packages/
    corpus-core/
    llm-core/
    transcript-core/
    markdown-conversion-core/
    aws-deploy-core/
  workflows/
    deepgram-transcription/
    transcript-cleanup/
    markdown-archive-conversion/
    llm-extraction/
    repo-audit/
    project-intake/
  infra/
    aws/
      shared/
      apps/
    templates/
      lambda-api/
      containerized-web-app/
      static-site/
  ops/
    agent-system/
    work-orders/
    approval-packets/
    repo-audits/
    standards/
    runbooks/
  docs/
    architecture/
    decisions/
    guides/
    research/
    codeindex/
  data/
    README.md
    manifests/
    schemas/
    samples/
  content/
    canonical-transcripts/
    public-site-copy/
    curriculum/
  experiments/
    README.md
  archive/
    README.md
  scripts/
    data/
    repo/
    dev/
  tests/
    integration/
    smoke/
  .github/
    workflows/
    ISSUE_TEMPLATE/
    pull_request_template.md
  .cursor/
    rules/

This does not mean you need to populate all folders immediately. Empty or premature folders are not useful. But these are the categories I would standardize around.


## 5. How this should relate to PROJECTS.md
Your PROJECTS.md should not mirror the filesystem exactly. It should act as a portfolio database in Markdown.

Each project record should include fields like:

```markdown
## Project: FloodLAMP Archive
### Project Metadata
- Project slug: `floodlamp-archive`
- Domain tags: `floodlamp`, `education`, `archive`, `web`
- Organization: `FOF`
- Visibility: `public-facing/private repo/public repo TBD`
- Status: `active`
- Maturity: `deployed prototype` or `production-like`
- Primary folder(s):
  - `apps/floodlamp-archive/`
  - `workflows/markdown-archive-conversion/`
  - `infra/aws/apps/floodlamp-archive/`
- Related packages:
  - `packages/markdown-conversion-core/`
  - `packages/aws-deploy-core/`
- Data/storage:
  - S3 prefix:
  - Manifest:
- Agent risk level:
  - Medium / High
```

A project can point to multiple folders. That is the key unlock.

For example:

Project	Folders it might use
FloodLAMP Archive	apps/floodlamp-archive/, content/public-site-copy/, workflows/markdown-archive-conversion/, infra/aws/apps/floodlamp-archive/
Transcript Processing System	workflows/deepgram-transcription/, workflows/transcript-cleanup/, packages/transcript-core/, data/manifests/
AI Coding System	ops/agent-system/, workflows/repo-audit/, apps/ai-work-order-console/, PROJECTS.md, PROFILE.md
Minecraft Mod	apps/minecraft-mod/
Shared LLM Tools	packages/llm-core/, maybe workflows/llm-extraction/

This solves the categorization problem. The filesystem does not need to decide whether FloodLAMP is “education” or “archive” or “web.” PROJECTS.md records all of those tags.


## 6. The best PROJECTS.md organization

I would make PROJECTS.md use four levels:
```markdown
# PROJECTS.md
## 1. Project Index
## 2. Active Projects
## 3. Shared Components
## 4. Project Records
```

The most important part is the index.

```markdown
## 1. Project Index
| Project | Status | Maturity | Domain Tags | Primary Folder | Visibility | Risk |
|---|---|---|---|---|---|---|
| FloodLAMP Archive | Active | Deployed prototype | floodlamp, archive, web, education | `apps/floodlamp-archive/` | Public-facing | Medium |
| Transcript Processing | Active | Internal workflow | transcripts, deepgram, markdown, corpus | `workflows/deepgram-transcription/` | Private | Medium |
| AI Coding System | Active | Internal system | agents, repo-management, automation | `ops/agent-system/` | Private | High |
| Minecraft Mod | Experimental | Local/dev | game, minecraft | `apps/minecraft-mod/` | TBD | Low |
```

Then use project records below.

```markdown
## Project: Transcript Processing
### Summary
...
### Folder Map
- Main workflow: `workflows/deepgram-transcription/`
- Cleanup workflow: `workflows/transcript-cleanup/`
- Shared code: `packages/transcript-core/`
- Data manifests: `data/manifests/transcripts.jsonl`
- Local ignored data: `data_local/transcripts/`
- S3 prefix: `s3://...`
### Agent Instructions
...
### Current Next Actions
...
```

This also fits the attached design direction: your devlog says PROJECTS.md should be the portfolio map and project records, while PROFILE.md is stable human context and AGENTS.md/project files are execution rules.  ￼


## 7. How to handle projects that may become public repos
For future open-source projects, use this rule:

Keep the monorepo as the private/internal development estate unless a project has a clear public boundary. When a project becomes contributor-facing, extract or mirror the clean app/package into its own public repo.

That means:

### Stage	Recommended structure
Early idea	experiments/<slug>/
Serious internal prototype	apps/<slug>/ or workflows/<slug>/
Shared internal library	packages/<slug>/
Public-ready library/app	Extract to standalone public repo or maintain as public repo from that point
Private deployment/config around public project	Keep in private monorepo under infra/ or separate private deploy repo

Do not make your main private monorepo the place where outside contributors work. If a project gets real contributors, it should probably have a clean public repo with its own:

README.md
AGENTS.md
CONTRIBUTING.md
LICENSE
.github/workflows/
tests/
src/

Your monorepo can still contain private deployment tooling, private notes, experiments, and shared internal workflows.


## 8. What not to do
I would avoid these patterns.

### Do not organize everything under projects/
This seems simple:

projects/
  floodlamp/
  transcript-tools/
  minecraft/
  ai-coding-system/

But it hides the difference between apps, packages, workflows, and infra. Agents need that difference.

### Do not organize mainly by organization
Avoid:

fof/
personal/
floodlamp/
family/

Those are important metadata fields, but bad top-level code folders. They mix privacy, ownership, purpose, and implementation.

### Do not keep bulk data beside workflows
Avoid:

workflows/deepgram-transcription/raw-audio/
workflows/deepgram-transcription/all-json/
workflows/deepgram-transcription/generated-output/

Instead:

workflows/deepgram-transcription/     # scripts, tests, docs
data/manifests/                       # index
data_local/                           # ignored local downloads
S3                                    # actual large/raw/generated files

Do not let every app invent its own agent instructions

Have a root AGENTS.md, then project-specific AGENTS.md only where needed. Your previous planning file explicitly points toward durable repo/project instruction files that tell agents how to run, test, summarize, and respect production risk.  ￼


## 9. Best-practice recommendation for your case
Use a hybrid operational monorepo:

apps/        deployable things
packages/    reusable code
workflows/   repeatable file/data/content automations
infra/       cloud/deployment/infrastructure code
ops/         AI coding system, work orders, approvals, standards
docs/        cross-project documentation and research
data/        manifests, schemas, tiny samples only
content/     human-authored or canonical content
experiments/ temporary prototypes
archive/     retired code

Then use PROJECTS.md as the cross-cutting map with tags:

domain tags: education, transcripts, floodlamp, minecraft, family, ai-coding, web
organization: FOF, personal, mixed
status: active, maintenance, experimental, paused, archived
maturity: idea, prototype, deployed prototype, production-like, public OSS
visibility: private, public-facing, public repo, planned public
risk: low, medium, high
primary folders: apps/..., workflows/..., packages/..., infra/...

That is the cleanest way to support:

Need	How the structure supports it
Many different project types	Separate apps/, workflows/, packages/, infra/
Low-touch agent operation	Agents can infer task type from folder
Future public repos	Apps/packages can be extracted cleanly
EA-safe workflows	workflows/ + runbooks + predictable local/S3/data policy
AWS-backed systems	infra/ separated from app logic
Transcript/document automation	workflows/ plus data/manifests/
Human-out-of-loop direction	ops/ for work orders, approval packets, repo audits
Project metadata complexity	PROJECTS.md tags instead of awkward folders


## 10. The rule I would put at the top of PROJECTS.md
```

```markdown
# PROJECTS.md organizing rule
This file is the portfolio map. It is allowed to classify projects by domain, organization, maturity, visibility, status, risk, and related folders.
The repo folder structure is organized by operational shape, not by life domain.
Use:
- `apps/` for deployable or runnable applications.
- `packages/` for reusable code.
- `workflows/` for repeatable file, data, transcript, document, and automation pipelines.
- `infra/` for infrastructure and deployment code.
- `ops/` for AI coding system operations, work orders, approvals, standards, and repo audits.
- `docs/` for cross-project documentation.
- `data/` only for manifests, schemas, and small samples.
- `content/` for human-authored or canonical content that belongs in Git.
- `experiments/` for temporary prototypes.
- `archive/` for retired code.
A project may span multiple folders. Do not force a project into only one filesystem location. Instead, each project record must list its primary folders, related packages, workflows, infrastructure, data manifests, and public/private boundary.
```


## 11. The first migration step
Do not reorganize everything at once. Start with a classification pass.

For each existing top-level folder or major body of code, assign:

app
package
workflow
infra
ops
docs
data-manifest
content
experiment
archive
external-data-to-S3

Then create a rough PROJECTS.md index before moving files. The index should tell you where each thing should go.

The first practical target should be:

1. Create PROJECTS.md index.
2. Create the recommended top-level folders.
3. Move only the obvious things first.
4. Move bulk data/generated artifacts out of Git or into the S3 migration plan.
5. Add local README files for each active app/workflow/package.
6. Add project records gradually.

That gives you structure without turning the cleanup itself into a giant project.


# opus 4.7 (Cursor)
I've read PROFILE.md, PROJECTS.md, REPOS.md, ai-coding-system-dev.md, the 2026-05-23 AI responses on system, the 2026-05-25 pare-down log, the public/private repo and using-code-from-another-repo notes, the repo-reorg-branch plan, the file-types-to-exclude guide, and the original repo full sweep. I also looked at the current top-level layout and `primary/`, `projects/`, `web/` to ground the options in what's actually here.

## The core decision

Three structural axes are tangled in your question; the recommendation hinges on separating them:

1. **Primary organizing principle for folders** — application, area/domain, or code-type/layer.
2. **Where shared code lives** — one `core/`, several small packages, or vendored per app.
3. **How "areas" (Deutsch, PV, Minecraft, education, family) relate to folders** — as folder hierarchy, as metadata only, or hybrid umbrella folders when an area has multiple sub-projects.

Your instinct ("apps first, areas/code-types cascade from there") is the right one. The main question is how much per-app structure to enforce now versus defer. Here are three options across that complexity range.

## Three options, most → least overhead

### Option A — Layered monorepo with packages + apps + infra (most structure)

```
apps/
  deutsch-archive/
  qrag/
  math-quiz/
  ...
packages/
  fof-fileops/          # was primary/fileops.py
  fof-llm/
  fof-transcribe/
  fof-rag/
  fof-aws/
infra/
  chalice/              # all chalice apps grouped
  cdk/                  # future
content/
  manifests/
  schemas/
  samples/
docs/, plans/, scripts/, tools/, tests/
```

- Each app has its own `pyproject.toml`, README, AGENTS.md.
- Each package is independently versionable; apps depend on pinned versions (editable in dev, tagged in CI).
- "Areas" are pure metadata in `PROJECTS.md`.
- Closest to a professional team layout.
- **Cost**: real packaging discipline (releases, version bumps, editable installs), 5+ `pyproject.toml`s, multi-package CI. Heavy for a solo part-time operator. Worth it only when shared code starts breaking apps in non-obvious ways or when public extraction of packages becomes a goal.

### Option B — Apps-centric monorepo with single `core/` (medium, recommended)

```
apps/
  qrag/                       # AWS-backed RAG (api + web together)
    api/                      # chalice lambdas (moved from web/aws_chalice/qrag-*)
    web/                      # webflow custom code for qrag
    README.md
    AGENTS.md                 # optional override; otherwise root AGENTS.md applies
  deutsch-archive/
  math-quiz/
  minecraft/                  # umbrella because area has multiple sub-projects
    mc-mod-tools/
    mathquest/
    remove-single-player/
    mod-dm-control-panel/
  family/                     # private umbrella: Kid1, reading, kid-games
    Kid1/
    reading/
  pipelines/                  # one-shot or recurring transformations
    deutsch-copyright-release/
  tools/                      # reusable CLI utilities
    diarized-transcription/
core/                         # renamed from primary/; single shared lib, no packaging yet
  fileops.py, llm.py, transcribe.py, rag.py, aws.py, ...
web-shared/                   # cross-app webflow code (site head/body, log-in)
data/
  manifests/                  # git-tracked index of S3 content
  samples/                    # tiny fixtures for tests
  README.md
plans/, docs/, scripts/, tests/, voice/, lib/
AGENTS.md, PROFILE.md, PROJECTS.md, ai-coding-system-dev.md
```

- Single shared lib (`core/`) — no formal packaging until pain demands it.
- Each app is a self-contained folder that **could be extracted to its own public repo later** by copying out plus pulling in needed `core/` modules as either a vendored copy or a small dependency.
- Areas live as **metadata** in PROJECTS.md (tags, not folders) **except** when an area has 2+ sub-projects; then it becomes an umbrella folder under `apps/` (e.g., `apps/minecraft/`, `apps/family/`). This avoids forcing every solo app into a deep hierarchy.
- AWS, web, and lib code for a given app live **with the app**, not split across `web/aws_chalice/` and `web/`. Cross-app webflow shells stay in `web-shared/`.
- Per-app `AGENTS.md` is optional. Most apps inherit the root one; only add when an app has materially different rules (e.g., public repo, contributors, different deploy posture).

### Option C — Minimal rename (least change)

```
projects/        → apps/           # rename only
primary/         → core/           # rename only
web/             stays as-is
everything else  stays as-is
```

- Update `PROJECTS.md` and `AGENTS.md` to reflect the renames; nothing else moves.
- "Areas" are PROJECTS.md metadata only.
- Defers the QRAG-style "code spread across three top-level folders" problem.
- **Cost**: every time you add or modify QRAG-like cross-cutting work, an agent has to learn that "QRAG" is split across `web/aws_chalice/qrag-*`, `web/webflow-rag-devpage.js`, and `core/rag.py`. That cost grows with portfolio size.

## Recommendation: Option B
```
apps/
  qrag/                       # AWS-backed RAG (api + web together)
    api/                      # chalice lambdas (moved from web/aws_chalice/qrag-*)
    web/                      # webflow custom code for qrag
    README.md
    AGENTS.md                 # optional override; otherwise root AGENTS.md applies
  deutsch-archive/
  math-quiz/
  minecraft/                  # umbrella because area has multiple sub-projects
    mc-mod-tools/
    mathquest/
    remove-single-player/
    mod-dm-control-panel/
  family/                     # private umbrella: Kid1, reading, kid-games
    Kid1/
    reading/
  pipelines/                  # one-shot or recurring transformations
    deutsch-copyright-release/
  tools/                      # reusable CLI utilities
    diarized-transcription/
core/                         # renamed from primary/; single shared lib, no packaging yet
  fileops.py, llm.py, transcribe.py, rag.py, aws.py, ...
web-shared/                   # cross-app webflow code (site head/body, log-in)
data/
  manifests/                  # git-tracked index of S3 content
  samples/                    # tiny fixtures for tests
  README.md
plans/, docs/, scripts/, tests/, voice/, lib/
AGENTS.md, PROFILE.md, PROJECTS.md, ai-coding-system-dev.md
```

### Reasoning, in priority order:

1. **Agent ergonomics scale with app-folder cohesion.** When an agent is told "work on QRAG," everything QRAG is in `apps/qrag/`. That single fact makes context loading, per-app `AGENTS.md`, per-app skills, per-app deploy runbooks, and per-app preview environments all dramatically simpler. It is the largest leverage move for the AI-coding-system-dev vision in `ai-coding-system-dev.md` §12.
2. **Future public-repo extraction is preserved** without paying packaging overhead now. A self-contained `apps/<name>/` folder lifts cleanly into its own repo when an app earns it (math-quiz, mc-mod-tools, etc.). At that point, the relevant `core/` modules either get vendored in or you finally promote them to a real package — but only the ones that justify it.
3. **Areas-as-folders only when they earn it.** Minecraft, family, and possibly education already have 2+ sub-projects, so umbrella folders pay rent. Deutsch, PV, Floodlamp are corpora — they belong as area tags on apps (in PROJECTS.md) plus a `data/manifests/<area>.jsonl` row, not as top-level folders.
4. **Single `core/` matches your skill profile and workload.** PROFILE.md is honest that you are a pure AI coder and EA is a collaborator with limited git depth. Multi-package CI, version bumps, and editable installs add real overhead per change. Promote to Option A package-by-package only when a specific core module starts breaking apps or when an app's public release demands it.
5. **Reversible.** Option B can graduate to Option A incrementally (one promoted package at a time). Option A is hard to walk back. Starting at A risks paying ongoing overhead for hypothetical benefit.

## How the three dimensions resolve under Option B

| Dimension | Resolution |
|---|---|
| Folder organizing principle | Application first. Code-type splits (`api/`, `web/`, `data/`) happen **inside** an app folder when relevant. |
| Areas (Deutsch, PV, Floodlamp, education, family, minecraft, qrag-as-system) | Metadata in `PROJECTS.md` as area tags. Become umbrella folders under `apps/` only when 2+ sub-projects share the umbrella. |
| Shared code | Single `core/` (renamed from `primary/`). No formal packaging. Promote individual modules to `packages/` only when justified. |
| AWS/Chalice code | Moves into the owning app's `apps/<app>/api/`. `web/aws_chalice/chalicelib_mirror_deploy.sh` and the mirror rule still apply — just from `core/` into per-app `chalicelib/`. |
| Webflow code | Per-app under `apps/<app>/web/`. Truly shared site shells live in `web-shared/`. |
| Data | Stays out of git (S3). `data/manifests/` is the in-git catalog. `data/samples/` holds tiny fixtures. |
| Per-app instruction files | Root `AGENTS.md` applies by default. Per-app `apps/<app>/AGENTS.md` only when overrides are needed. Same for `CLAUDE.md`. |
| Public-repo readiness | Each `apps/<app>/` is a candidate for extraction. Public ones get full `CONTRIBUTING.md`, `LICENSE`, `.github/`, etc. before extraction, not before. |

## Notes on the awkward edges

- **QRAG is the hardest case.** It is currently split across `web/aws_chalice/qrag-llm`, `qrag-routing`, `vrag-llm`, plus `web/webflow-rag-devpage.js` and `web/webflow-fof-site-body.js`, plus `core/rag.py`, `core/rag_prompts_routes.py`. Recommended grouping under Option B: treat QRAG as one app at `apps/qrag/` with `api/qrag-llm/`, `api/qrag-routing/`, `api/vrag-llm/`, `web/`. Keep `hash-store`, `hmac-hash`, `send-email`, `deepgram-callback` as either sibling apps under `apps/` or as `apps/qrag/api/<name>/` if they are exclusively in service of QRAG.
- **"Diarized transcription tool" and similar reusable capabilities.** If it is a CLI/library used across pipelines, it can either be its own app under `apps/tools/diarized-transcription/` or, if it is purely shared functions, just live in `core/transcribe.py`. The criterion: does it have a user-facing entry point (CLI, script, web)? If yes, it is an app. If no, it is core.
- **Pipelines vs apps.** A one-shot "Deutsch copyright release" is fine as `apps/pipelines/deutsch-copyright-release/`. The `pipelines/` umbrella prevents one-offs from cluttering `apps/` later.
- **Family-related projects (Kid1, kid games, reading).** Under `apps/family/` keeps them grouped and makes them easier to keep private even if other apps go public.
- **Don't add `packages/` yet.** Add it only when you promote your first module. That single event will teach you the right shape for the rest.

## Suggested migration order, after pare-down completes

1. Rename `primary/` → `core/`. Update imports and AGENTS.md.
2. Rename `projects/` → `apps/`. Move existing entries: `apps/math_quiz/`, `apps/meta_coder/`, etc. Group existing minecraft work under `apps/minecraft/`. Group family work under `apps/family/`.
3. Create empty `apps/qrag/`, move chalice qrag/vrag lambdas into `apps/qrag/api/`, move QRAG-specific webflow JS into `apps/qrag/web/`. Keep `web-shared/` for cross-app shells.
4. Update root `AGENTS.md` directory guide to the new shape.
5. Fill out `PROJECTS.md` with the Areas + Projects sections sketched above. Use area tags rather than folder names.
6. Only after #1–5 settle: consider per-app `AGENTS.md`, per-app deploy runbooks, and the first `packages/` promotion.

This sequence keeps Option B reversible at every step and avoids batching too many breaking moves into one commit.


# Plan and next steps for implementation

Decision: Option B (apps-centric monorepo with single `core/`). Selected on 2026-05-29 after comparing the ChatGPT Pro "Recommended structure in full" (a more granular 10-folder layout with multiple `*-core/` packages, top-level `workflows/`, `infra/`, `ops/`, `content/`, `experiments/`, `archive/`) against Option B above. Option B wins on simplicity, familiarity to current state, lower migration overhead, and incremental upgrade path toward the heavier ChatGPT layout if/when specific overhead earns its keep.


## Decision answers from the comparison questions
- Q1 — Shared Python code: single `core/` for now. Defer packaging. Promote one module to `packages/` only when an app's public release or a breaking change forces it. The public-repo path (possibly a public mirror monorepo with agent routing for app-specific contributors) is to be decided later and does not block this structure.
- Q2 — AWS / Chalice code location: per-app inside `apps/<app>/api/`. Cohesion wins; an agent told to "work on QRAG" finds everything for QRAG in one folder. Side benefit: it is easy to generate a manifest of all Lambdas grouped by app from this layout.
- Q3 — Multi-sub-project areas: umbrella folders under `apps/` when an area has 2+ sub-projects (e.g., `apps/minecraft/`, `apps/family/`). Single-sub-project areas stay flat with their area as a tag in `PROJECTS.md`.
- Q4 — Repeatable workflows / pipelines: inside `apps/`, not a top-level `workflows/`. Use `apps/pipelines/<one-shot>/` and `apps/tools/<reusable-cli>/` only when the workflow has a clear CLI/runbook surface. Many workflows can stay as wrapper functions in the relevant module (in `core/` or in a project-specific module), per Randy's existing pattern of keeping wrapper functions next to lower-level functions.
- Q5 — AI coding system meta-tooling: no dedicated `ops/` folder for now. Continues to live in `plans/` and the root meta files (`AGENTS.md`, `PROFILE.md`, `ai-coding-system-dev.md`); when meta-tooling becomes executable code (work-order bot, repo-audit script, etc.), it lives with the app or workflow that owns it.
- Q6 — `content/`, `experiments/`, `archive/` top-level folders: none added now. Revisit per-folder when a specific need arises.


## Migration sequence
Follow the migration order from the recommendation above. Each numbered step is one commit on the current `pare-down` branch.

1. Rename `primary/` → `core/`. Update all imports across the codebase, the chalicelib mirror script (`web/aws_chalice/chalicelib_mirror_deploy.sh`), root `AGENTS.md`, README files, and tests. The chalicelib mirror continues to rewrite `from core.` to `from chalicelib.` in copied files at deploy time, so Lambda runtime imports are unaffected.
2. Rename `projects/` → `apps/`. Move existing entries (`math_quiz`, `meta_coder`, `ads_scrape`, `wingspan`, `live_transcript`, `smol_podcaster`). Group existing Minecraft work under `apps/minecraft/`. Group family work (`Kid1`, `reading`) under `apps/family/`.
3. Create `apps/qrag/`. Move the Chalice Lambdas `qrag-llm`, `qrag-routing`, `vrag-llm` into `apps/qrag/api/`. Move QRAG-specific Webflow JS (`webflow-rag-devpage.js` and variants) into `apps/qrag/web/`. Decide per-Lambda whether `hash-store`, `hmac-hash`, `send-email`, `deepgram-callback` belong as siblings under `apps/` or under `apps/qrag/api/`. Create `web-shared/` for cross-app Webflow shells (`webflow-fof-site-head.html`, `webflow-fof-site-body.js`, `webflow-fof-log-in.html`, etc.).
4. Update root `AGENTS.md` directory guide to reflect the new shape (`apps/`, `core/`, `web-shared/`, etc.). Update the chalicelib mirror rule and references to `primary/`.
5. Fill out `PROJECTS.md` with Areas + Projects sections. Use area tags (`deutsch`, `pv`, `floodlamp`, `education`, `family`, `minecraft`, `qrag`) rather than forcing areas into the folder structure.
6. Only after #1–5 settle: consider per-app `AGENTS.md`, per-app deploy runbooks, and the first `packages/` promotion.


## Execution notes
- Branch: continue on `pare-down`. The structure migration is part of step 5 of the broader pare-down plan in `2026-05-23_repo-reorg-branch.md` ("clean repo structure"). The new repo will be a fresh first-commit copy of the result.
- Commit per numbered step. Push after each commit.
- Do not run `chalice deploy` during migration. Production deploys require explicit approval per `AGENTS.md` and are gated until structure + mirror script + imports are all consistent and verified.
- Historical artifacts (deployed dev logs, `_archive chalice/`, `chalicelib_old/`, dated requirements files, dated planning docs) are not updated as part of the rename — they reference `primary/` for historical accuracy and can be left as-is.
- Verification per step is import-level (Python can resolve `from core.X import Y`) and grep-level (no remaining stray references to `primary/` outside historical files). End-to-end Lambda testing happens later, off the migration commits.

# Current folder structure

Last updated: 2026-05-31 4:30 PM (UTC-7), in conjunction with the `security/` follow-up folder.

This is the living, accepted repo layout — the single source of truth as the Option B reorg proceeds. It started as Option B (above) from Opus 4.7 and is amended as each per-folder section in `2026-05-30_followup-folder-organization.md` lands. See the `## Change log` below for what changed from the original and why. Areas (deutsch, pv, floodlamp, education, family, minecraft, qrag, transcription, ai-coding-system) remain tags in `PROJECTS.md`, not folders, except where an area has 2+ sub-projects and earns an umbrella folder under `apps/`.

The tree below mirrors the VS Code Explorer: folders only (no root-level files), alphabetical within each level, one folder per line. Omitted as noise: generated/dependency/IDE dirs (`.git/`, `.venv/`, `.venv_python12/`, `node_modules/`, `__pycache__/`, `corpus_tools.egg-info/`, `.cursor/`, `.devcontainer/`, `.vscode/`) and Chalice build artifacts (`.chalice/`, `langchain-layer/`, `chalicelib_old/`, `deployed_dev_logs/`, `deployed_prod_logs/`). Shown but collapsed (heavy data stores / off-limits, contents not expanded): `data/`, `logs/`, `ms-graphrag/`, `_archive/`.

Maintenance rule (do not regenerate this tree wholesale): Randy hand-edits this tree for readability — promoting some top-level folders to `##` section headings (so they fold in the editor) and intentionally paring back the detail shown under many folders. That hand-curated version is the one to keep. When a per-folder session changes the actual layout, make only the minimal corresponding edit (add / rename / remove the specific folder line) and otherwise preserve Randy's existing formatting, `##` headings, and chosen level of detail/collapsing. Do not re-expand folders he has trimmed, do not re-add omitted subfolders, and do not reformat the whole block.


_archive/
_xfer gitignore/
ai-threads/
## apps/
  ads_scrape/
  deutsch/
  family/
    Kid1/
    reading/
  games/
    robo-polly/
    wingspan/
  live_transcript/
  math_quiz/
  meta_coder/
  minecraft/
  qrag/
  repo-mirror/
  scratch/
    ea/
    bs/
    Kid1/
    randy/
    tl/
  smol_podcaster/
  transcription/
    api/
      deepgram-callback/
  voice/
## core/
## data/
dependencies/
docs/
  _build/
  codeindex/
  misc/
  my_refs/
  packages/
  sphinx/
  vis/
exchanges/
lib/
logs/
ms-graphrag/
plans/
prompts/
  _archive/
  custom_instructions/
  kids/
  mckay/
  proper names audit/
  qa extract/
  qa_combine/
security/
sounds/
tests/
  test_manual_files/
## web-shared/
  aws_chalice/
    _archive chalice/
    hash-store/
    hmac-hash/
    send-email/
  md_to_html_dev/
  web_docs/
  web_test_files/
  webflow/


## Change log
- 2026-05-31 — Amendments from the original Opus 4.7 Option B sketch (above), reflecting the per-folder follow-up sessions completed so far. Why: the original sketch used placeholder/illustrative app names; the layout below reflects what actually landed on `pare-down`.
  - Top-level `web/` retired. The original Option B kept `web-shared/` only for Webflow shells; it now holds all cross-app web/infra code in subfolders: `webflow/` (the shells) and `aws_chalice/` (shared Lambdas + mirror/deploy script), plus loose cross-app assets (`md_to_html_dev/`, `web_docs/`, `web_test_files/`, `test_front-end_validation_inputs.js`). The old `web/` and `web/aws_chalice/` paths are gone.
  - `apps/transcription/api/deepgram-callback/` added (new transcription umbrella) — the Deepgram webhook is transcription-related, not QRAG-only, so it did not go under `apps/qrag/api/`.
  - `apps/voice/` added — `voice/` promoted from a top-level folder to a self-contained app (TTS + video-frame OCR-to-speech); model weights, generated audio, and captured frames stay local-only/gitignored.
  - `apps/scratch/<user>/` added — per-collaborator runner scripts from the retired `secondary/` folder, kept tracked for collaborator continuity.
  - `apps/games/robo-polly/` added — game sub-project recovered from `secondary/max/`; new `apps/games/` umbrella anticipating more from another repo.
  - `secondary/` removed — mature modules (`audio.py`, `video.py`, `speakerid.py`, `gdrive.py`, `gdrive_mtests.py`, `transcript_eval.py`) promoted into `core/`; exploratory/abandoned/one-off scripts archived to `_archive/secondary/`.
  - `hash-store`, `hmac-hash`, `send-email` Lambdas confirmed general/cross-app and kept as shared infrastructure under `web-shared/aws_chalice/` (not moved under `apps/qrag/api/`); their eventual owning-app placement is still open.
  - Placeholder app names from the sketch (`deutsch-archive`, `math-quiz`, the illustrative `minecraft/` sub-projects, `pipelines/`, `tools/`) are not literal; the real `apps/` contents are listed above. `pipelines/` and `tools/` umbrellas are not created until a real pipeline/CLI earns them.
- 2026-05-31 — `lib/` kept as-is (no move). Standard vendored third-party JS (`bindings/`, `tom-select/`, `vis-9.1.2/`), ~748 KB, under 1 MB — nothing to disperse. Optional `vendor/` rename and any future-off-Webflow reconsideration deferred.
- 2026-05-31 — `tests/` kept top-level as the shared `core/` suite home; internal cleanup only (top-level tree line unchanged). `deprecated_unittests.py` deleted (dead). `vectordb_test/` → `tests/test_manual_files/vectordb/` (it is a live fixture for `core/vectordb_mtests.py`, belongs with the other manual fixtures). `test_manual_files/` (~39 MB, 238 tracked files; 33.8 MB of that is 13 binaries, the single 18 MB `pv_test_files/EPC_testing_packet.pdf` ≈ 47%) left tracked as-is pending Randy's confirmation on whether to relocate the large binaries to data/S3. CI setup deferred to the post-file-org follow-up.
- 2026-05-31 — `docs/` kept top-level; internal cleanup only (top-level tree line unchanged). Typo fix: `docs/sphnix/` → `docs/sphinx/` (`git mv`, Sphinx config). Regenerable outputs untracked + gitignored: 6 `docs/codeindex/all_*_dev.*` / `column_layout_graph.html` files + `create_codeindex_log.txt`, plus all of `docs/_build/` (25 stale Sphinx HTML files); the `create_codeindex.py` generator and the Sphinx config remain tracked so both can be rerun. `docs/codeindex/_archive/` of dated historical snapshots (~11 MB) left tracked as-is. `docs/vis/{graphviz_and_example_OLD.py, module_based_network_OLD.html}` → `_archive/docs-vis/` (gitignored; recoverable from git history). `docs/misc/call_graph.dot` (empty 0-byte) deleted. `docs/misc/{openai_reasoning_models.md, call_graph_incoming.svg}`, `docs/my_refs/objects_pickle_json.md`, and all 16 `docs/packages/*.md` reference notes kept as-is.
- 2026-05-31 — `dependencies/` kept top-level; pared to a single canonical requirements file plus the generator script. Removed the `code file copies/` subfolder (deleted — 14 redundant code snapshots). Older dated `requirements_*` snapshots + the 2025-12-19 pipreqs dumps + `global_packages.txt` + `log_pip_install.md` archived to `_archive/dependencies/`. Kept the hand-curated `requirements_2024-09-26_add_CURRENT.txt` as canonical (what `setup.py` reads) over the newer-but-broken pipreqs dump; the real version refresh + `pyproject.toml` migration are deferred to the post-file-org follow-up. `get_direct_dependencies.sh` kept with paths updated (`primary/` → `core/`) and the "code file copies" step dropped.
- 2026-05-31 — `scripts/` dispersed and deleted (no longer a catch-all). The original Opus 4.7 Option B never defined `scripts/`; it was carried along as-is, so its three items were rehomed: `scripts/deutsch/` → new `apps/deutsch/` app (more Deutsch work expected); `scripts/mirror-to-public-corpus-tools/` → new `apps/repo-mirror/` app (repo-mirror tooling; kept as an app rather than minting a top-level `ops/`); `scripts/z_count_chars_in_js.sh` → `web-shared/` (loose cross-app JS-char-count utility). Both relocated Python scripts compute the repo root via relative `__file__` parents and still resolve correctly from their new two-deep locations. Tree: removed the `scripts/` block; added `apps/deutsch/` and `apps/repo-mirror/`.
- 2026-05-31 — `security/` kept top-level (no move; tree line unchanged). Audit-and-document only: all three files (`First-Web-ACL.json`, `aws_security-info.md`, `hash-store_security thread.md`) confirmed git-tracked; no live secrets, but AWS account/resource identifiers, the private bucket name `[S3-BUCKET]`, and personal/collaborator emails should be redacted before any public publish (recorded as a follow-up). Keeping `security/` as a root folder is consistent with the Option B decision, which deferred the heavier `infra/`/`ops/` layout; a future consolidation of `core/`'s AWS modules + `security/` into a top-level `infra/` remains a deferred, optional upgrade.
- 2026-05-31 — Tree reformatted (no folder moves). Replaced the curated Option-B-style summary tree (top-level folders + inline comments + a few representative subfolders) with a full Explorer-style view: folders only, alphabetical within each level, one folder per line, nested to mirror the VS Code Explorer. Generated/dependency/IDE dirs and Chalice build artifacts are omitted; heavy data stores (`data/`, `logs/`, `ms-graphrag/`, `_archive/`) are shown but collapsed (see the intro note for the exact exclusion/collapse lists). The earlier inline comments describing each app/area are preserved in the change-log entries above; this view is purely structural.
