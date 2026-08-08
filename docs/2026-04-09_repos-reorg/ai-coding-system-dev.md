file: ai-coding-system-dev.md
title: AI coding system devlog

This file is a living devlog for the evolving system that turns Randy's ideas into software, files, and project outputs using AI coding tools, agents, infrastructure choices, and documented workflows.

It is planning context, not a secrets file and not an always-loaded agent rule file. Do not store API keys, account IDs, private credentials, billing details, or sensitive personal information here.

Use `PROFILE.md` for Randy-specific human context and stable background. Use `PROJECTS.md` for the portfolio map and project records. Use `AGENTS.md` and project-specific instruction files for execution rules that agents must follow during coding sessions (including communication preferences and human approval boundaries).

Relationship to `PROFILE.md`:
- `PROFILE.md` holds stable facts (background, skill levels, organizations, collaborators, family) and Randy's higher-level coding posture. It does not hold execution-time agent rules — those live in `AGENTS.md`.
- This file holds anything actively evolving: tools being evaluated, frameworks being tried, experiments in progress, roadmap items, infrastructure decisions in flight, subscription/account landscape.
- When a topic has both stable background and active direction, keep the background in `PROFILE.md` and the direction here.


## 1. Purpose
The goal is to develop a practical AI-assisted software production system that lets Randy make efficient progress across a significant number of small-to-medium complexity applications and file/workflow projects.

Working assumption:
- Better organization, documented project context, clear infrastructure/security decisions, and reusable workflow patterns should make it possible to move faster with current and future AI programming systems.
- The system should support increasing autonomy while preserving safety, reversibility, and clear human approval boundaries.
- The system should work for a portfolio that may initially include more than 10 and fewer than 20 projects.


## 2. Current Tool Landscape And Variability Space
The system needs to be usable across multiple dimensions at once. Variability and inconsistency across this space — features that differ between a provider's own interfaces, partial implementations, bugs, and uneven cost behavior — is itself a major part of the work, not a side issue. A single "standardize on one workflow" answer (for example, "Cursor only, laptop only") would simplify a lot but would give up important capabilities, most notably voice dispatch from a phone and the ability to switch models when one provider degrades.

Dimensions of variability:
- Device and context: laptop with two 27-inch monitors for focused work, phone for voice dictation from the pool or car, occasional iPad or other surfaces.
- Interface: native IDE (Cursor), desktop apps and CLIs (Claude Code, Codex), browser/web app, mobile app, CLI on a remote VM, Slack/Telegram/iMessage dispatch.
- Model and provider: Anthropic (Claude, currently including Opus 4.7) and OpenAI (Codex and others), with deliberate effort to stay comfortable across providers rather than locked into one. Cursor is still the primary go-to interface and is where most heavy work happens today, including this dev log itself; Cursor with Opus 4.7 currently incurs overage on heavy use.
- Harness / agentic framework: Cursor's agent harness, Claude Code with its skills, hooks, subagents, MCP, permissions, and sessions, Codex modes, plus third-party harnesses worth evaluating such as Hermes, OpenClaw, and Pi.
- Workflow framework: OpenSpec, Superpowers, custom `skills.md`-based workflows, and other spec-driven or opinionated systems.
- Subscription and budget: multiple OpenAI subscriptions and at least one Anthropic subscription (with a second Anthropic subscription added by TL), plus pay-as-you-go API access in various configurations. Different workflows trigger different cost profiles.
- Execution location: local-with-remote-control, virtual machine, or cloud agent.
- Use case: throwaway prototype vs deployed app feature vs production change vs cross-repo refactor vs file/document workflow vs personal automation.

Reality check:
- Providers' features differ across their own surfaces (Mac OS app vs phone app vs CLI vs browser vs IDE plugin). What works in one is not always available in another.
- Bugs and partial implementations are common in this space as of 2026.
- The current tool stack is rich but uneven; expect that the right combination per task class will only become clear through deliberate experimentation, not by reading docs.

Subscription/account notes should stay non-secret:
- Capture only the shape of the subscription landscape (which providers, plan types at a high level, which workflows trigger overage).
- Do not record credentials, billing identifiers, private account IDs, or tokens.


## 3. Workflow Research
Research inputs and examples to collect here or in a linked resource folder:
- YouTube videos comparing Claude Code, Codex, and other AI coding workflows.
- Videos and resources on open-source meta-coding and agentic coding systems.
- Examples of human-out-of-the-loop coding practices.
- Stripe's writing and discussion around "minions" or similar internal coding-agent practices.
- StrongDM or other company examples of human-out-of-the-loop coding workflows.

When adding resources, capture:
- Title:
- Link:
- Date reviewed:
- Main takeaway:
- Relevance to Randy's system:
- Possible pattern to adopt:
- Risks or mismatch:


## 4. Infrastructure And Platform Exploration
Infrastructure choices should be tracked here at the pattern/decision level, while project-specific implementation details belong in `PROJECTS.md` or project docs.

Current context:
- Randy has implemented and managed AWS-backed systems using API Gateway, Lambda, S3, Chalice, dev/prod paths, validation tooling, and deployment/testing scripts.
- There is an overall bias toward AWS because significant setup work has already been done.
- AWS may be cheapest or strongest at scale, but it has meaningful complexity overhead.
- Simpler platforms such as Vercel, Railway, or other hosting/deployment systems should be evaluated where speed, simplicity, maintainability, or agent-friendliness may matter more than raw infrastructure control.
- Some simpler platforms may still be wrapper layers over AWS or similar cloud infrastructure.

Decision themes:
- Cost at current scale versus cost at future scale.
- Complexity overhead for a solo AI-assisted operator.
- Fit with agentic coding and automated deployment workflows.
- Security defaults and blast radius.
- Ease of dev/prod separation.
- Ease of logs, monitoring, rollback, and debugging.
- Ability to create repeatable templates for future applications.


## 5. Patterns To Develop
Patterns to standardize over time:
- Project intake and idea-to-spec workflow.
- Project record format in `PROJECTS.md`.
- Agent task planning and review workflow.
- Safe Git workflow for Randy and collaborators.
- Dev/prod infrastructure decision pattern.
- Security and secrets handling pattern.
- Data and generated-artifact policy.
- Human approval boundaries for deployment, publication, deletion, and billing-sensitive changes.
- Reusable examples for common app types.


## 6. Open Questions
Questions to resolve through experimentation:
- Which coding interfaces work best for which task types?
- Which tools are best for broad planning, implementation, debugging, review, and long-running autonomous work?
- Which infrastructure platforms are best for fast prototypes versus durable applications?
- What should be standardized globally versus left project-specific?
- How much autonomy should be given to agents for different classes of work?
- What evidence is needed before a pattern becomes the default?


## 7. Evaluation Notes
Use this section for short dated notes as experiments happen.

Template:
- Date:
- Tool or workflow:
- Task:
- What worked:
- What failed or felt brittle:
- Reusable pattern:
- Follow-up:


## 8. Web Stack Direction
Background on Randy's current web comfort level lives in `PROFILE.md` under "Web Development Background." This section tracks where the web stack is headed and what to evaluate.

Current direction:
- Move off Webflow entirely. Using Webflow purely as a shell for AI-managed custom code is clunky and defeats the point of the platform.
- Evaluate front-end UI libraries, starting with Daisy UI and ShadCN.
- Evaluate frameworks and stacks, including React, Svelte, and Next.js.
- Steer away from Vercel for deployment because of cost concerns at scale. This reinforces the existing bias toward AWS for infrastructure, while keeping open evaluation of simpler hosts.
- Do at least one project that deploys the full web app (front end and back end) as a container to a standard host such as Hostinger, Railway, or AWS (for example, an EC2 instance), so the entire deployment surface is owned end-to-end rather than split across Webflow plus Lambda.

Open questions to resolve through experimentation:
- Which framework gives Randy the best agent-friendliness, deployability, and long-term maintainability for the kinds of small-to-medium apps he expects to build?
- Which UI library produces the best AI-generated UI by default with the least manual tweaking?
- Which deployment platform balances cost, simplicity, agent-friendliness, and ability to keep AWS-style control where it matters?
- What does a clean "Webflow-to-containerized-app" migration look like for an existing site such as the FloodLAMP archive?


## 9. Testing Roadmap
Background on Randy's current testing experience lives in `PROFILE.md` under "Testing Background And Direction." This section tracks where testing practice is headed.

Roadmap items:
- Treat testing as a core part of the AI coding system. Establish a meaningful test floor before broader agentic autonomy is granted on shared code in `primary/`.
- Revisit the existing unit test suite in `tests/` (covering `fileops.py`, `transcribe.py`, `llm.py`). Decide what still applies, what needs rewriting, and how to handle the real-versus-mocked tradeoff cleanly, especially for LLM API calls.
- Develop firsthand familiarity with end-to-end testing. Playwright is the current candidate to learn first; a recent AI thread covered the basics.
- Try red-green / test-driven-development workflows on a small, contained piece of work to build firsthand intuition.
- Set up CI (continuous integration), starting with GitHub Actions, to run unit tests automatically on PRs. Expand to lint, type checks, and end-to-end tests as the suite matures.
- Codify a per-project minimum acceptable validation step that agents are expected to run before recommending a merge or deploy.


## 10. Code Intelligence And Repo Analysis
Background on Randy's existing `docs/codeindex/` work lives in `PROFILE.md` under "Code Index Background." This section tracks evolving direction around code-intelligence and repo-analysis tooling.

Direction and items to evaluate:
- Decide whether to revisit, modernize, or replace the existing `docs/codeindex/` code index. The original was useful exposure to AST parsing and graph representations of code; AI coding tools have improved enough that an explicit per-repo index may or may not still pull its weight.
- Evaluate `Understand-Anything` ([github.com/Lum1104/Understand-Anything](https://github.com/Lum1104/Understand-Anything), companion YouTube video [youtube.com/watch?v=VmIUXVlt7_I](https://www.youtube.com/watch?v=VmIUXVlt7_I)) as a more sophisticated successor to the code index concept. It is a multi-agent pipeline that builds an interactive knowledge graph of files, functions, classes, and dependencies, with cross-tool support (Claude Code, Codex, Cursor, Copilot, Gemini CLI, etc.). Note: token-heavy and slow per run, but produces an artifact that can be committed and shared. Worth a hands-on trial on one of Randy's repos.
- Continue light exploration of graph RAG approaches. Specifically interested in LightRAG and similar tools in the context of personal knowledge base integration with the transcript / corpus / document work that lives in this `corpus-tools` repo.
- Open question: where does an explicit code/knowledge graph add the most value in Randy's workflow — onboarding agents to a repo, change-impact analysis, cross-repo navigation, or personal knowledge base — and which tool best fits each use case?


## 11. Multi-User Agent Awareness
The system has two human users: Randy as primary operator and EA as collaborator. Today's repo instruction files (`AGENTS.md`, `CLAUDE.md`, project-level rules, Cursor rules) are blind to which user is currently running an agent session, so any per-user guidance has to be applied manually or by the user remembering to mention it.

Goal: give agents a reliable, low-effort way to know whether they are working with Randy or EA, and let one set of instruction files cleanly express shared rules plus per-user rules that get applied automatically.

Candidate identity-detection methods, simplest first:
- Git config user identity. Have agents read `git config user.email` (or `user.name`) at session start and map the address to a profile (Randy, EA) using a small lookup near the top of `AGENTS.md`. Works for any agent that can shell out; no per-user file proliferation. Recommended starting point.
- Per-user local file. Use the `CLAUDE.local.md` (or equivalent gitignored) pattern: each user keeps their own local-only file with their identity and per-user preferences, and `AGENTS.md` is told to read it if present. Avoids depending on git config; requires EA to set up her file once.
- Environment-variable convention. Set something like `CORPUS_TOOLS_USER=randy` or `=ea` in each user's shell profile and have agents check it. Low friction at runtime; needs one-time setup per user.
- Hook-driven injection. Use a Claude Code or Cursor session-start hook to detect and inject the user identity into the agent's context. Most powerful but most setup work.

Candidate file-organization patterns:
- Sectioned single `AGENTS.md`. Keep one file with clearly labeled `## Shared`, `## For Randy`, and `## For EA` sections. The agent identifies the user, then follows the shared section plus the matching per-user section. Simplest to maintain.
- Imported per-user files. Keep `AGENTS.md` for shared rules and `AGENTS.randy.md` / `AGENTS.ea.md` for per-user rules, imported via the agent's import mechanism when supported. Cleaner separation; more files to manage.
- Mixed. Sectioned `AGENTS.md` for most things, plus a per-user gitignored local file for anything user-specific that should not be in git.

Open questions:
- Should per-user instructions live inside one `AGENTS.md` (one file, three sections) or in separate per-user files imported by `AGENTS.md`?
- How should this interact with Cursor rules and Claude Code skills, both of which have their own scoping mechanisms?
- What is the right fallback when the user cannot be identified (for example, in a Cursor cloud agent, a CI environment, or a fresh clone)? Conservative default is probably "treat as Randy" for read-only work and "ask before any write or deploy" otherwise.
- For sensitive workflows that should only run when Randy is the user (for example anything in "Agent Safety And Human Approval Boundaries" of `AGENTS.md`), is a soft warning enough, or should the agent actively block until identity is confirmed?

Phasing of credential and account-related task automation (which classes of work move from human-only to agent-assisted, and in what order) belongs in this section's roadmap as the design solidifies.

Next actions:
- Pick the simplest identity-detection method (likely `git config user.email`) and prototype it as a small lookup table in `AGENTS.md`.
- Decide between sectioned `AGENTS.md` and separate per-user files.
- Document the chosen pattern in `AGENTS.md` so both human users and agents understand the convention.


## 12. Path To Human-Out-of-the-Loop Coding
The Randy-side posture lives in `PROFILE.md` under "Coding And Review Style." This section tracks the operational path from today's state toward that end-state vision.

End-state vision:
- Randy's role is operator and decision-maker, not code reviewer.
- A voice-dictated feature description flows through plan, implementation, test, review, and deploy with no human reading code or diffs along the way.
- Compressed human approval happens only at the right gates (typically production deploy, billing-sensitive change, or public/private boundary crossing).

Current state:
- Code is fully AI-generated. Randy reviews at the PR level, not at the line-by-line level.
- There is no automated PR review, no required CI gates, no preview-deploy gates, no rollback automation, and no formal approval-packet format across the portfolio.

Practical near-term step:
- Pare down the current `corpus-tools` repo into a clean source-only branch and a new replacement repo, with bulk data and artifacts moved to S3. Working plan: `plans/2026-04-09_repos-reorg/2026-05-23_repo-reorg-branch.md`. This is a prerequisite for most of the larger pipeline work because it makes the repo usable as an agent workspace.

Where the meat of the work actually is:
- Most of the path from today's state to human-out-of-the-loop is not a single linear sequence of CI/review gates. It is iterative experimentation across the variability space described in section 2: which interface + model + harness + framework combinations work for which use cases, where features are inconsistent across providers' own surfaces, where bugs bite, and where cost scales unfavorably.
- Expect to evaluate multiple combinations per use case, retire combinations that do not earn their keep, and gradually consolidate around a small set of standardized workflows per major task class (new prototype, production feature, bug fix, hardening, content/data pipeline change, personal automation, and so on).
- Cross-cutting subscription, token, and budget tradeoffs are part of every combination — for example, Cursor with Opus 4.7 versus Claude Code from a CLI versus Codex from the ChatGPT mobile app are all viable for different shapes of work and have very different cost and feature profiles.

Longer-term direction items:
- Replace human PR-level review with automated and AI-driven PR review. Plan for multiple reviewer roles (implementation, regression, security, product-behavior, test coverage, deployment risk) per meaningful PR.
- Introduce CI status checks as required gates before merge: lint, type checks, unit tests, end-to-end tests, secret scan. See section 9 for the testing roadmap that backs this.
- Introduce per-project preview deploys for visual or behavior verification on changes that warrant it.
- For projects with real users, add staging deploy gates, production deploy approval, rollback scripts, and basic monitoring.
- Define a compressed approval-packet format: a short, voice-friendly summary of what changed, what passed, what the risk is, and what action Randy is being asked to approve.
- Decide, per project and per task class, which approvals must remain human and which can become fully automated over time.

Open questions:
- Which interface + model + harness combinations are worth standardizing on for each major task class, and which should remain situational?
- Which gates does each project need today, and which can be added incrementally without blocking forward progress?
- What is the minimum approval-packet format that works equally well at a workstation and on a phone with voice?
- How should this interact with the multi-user awareness work in section 11 (some approvals should only count when Randy is the human)?
- For the prototype end of the spectrum (low-risk, non-production), how close to fully autonomous can the pipeline run by default?
