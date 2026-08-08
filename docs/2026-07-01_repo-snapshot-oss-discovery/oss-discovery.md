file: plans/2026-07-01_repo-snapshot-oss-discovery/oss-discovery.md
title: OSS & companies one-to-two steps ahead — research report
last-updated: 2026-07-01_0930
ai: Claude Code (cloud)
session: `repo-analysis-oss-discovery`

Full research sweep behind section 06 of `index.html`, current to mid-2026. Filtered for genuine
alignment with the fof-mono system (multi-harness orchestration, worktree-parallel agents,
one-source skills, cloud/local handoff, convergence planning, human-out-of-the-loop) and
de-prioritizing the obvious famous names in favor of things that advance the system. Dead or
wound-down projects are flagged.


## The 5 single best matches for the exact workflow
If chasing only a handful, these map most directly onto worktrees + multi-harness + skills + cloud/local handoff:

1. **Sculptor (Imbue)** — parallel agents each in an isolated container, with a one-click "Pairing Mode" that syncs a container agent's work + git state back into the local repo/IDE. The manual cloud/local handoff, productized. https://github.com/imbue-ai/sculptor
2. **container-use (Dagger)** — a harness-agnostic MCP primitive giving *any* agent (Claude Code, Cursor, Codex, Goose) its own container + git worktree. Better fit for a multi-harness user than any single app; wire it into skills/hooks. https://github.com/dagger/container-use
3. **rulesync** — generates and syncs skills, subagents, commands, hooks, MCP, and permissions across 40+ tools from one source — and explicitly targets Hermes + AGENTS.md + Agent Skills. Mechanizes the "one source, many wrappers" principle. https://github.com/dyoshikawa/rulesync
4. **Serena** — LSP-based, symbol-level code retrieval/editing as an MCP server that works across all harnesses; slashes token use vs "pack the repo into a prompt." Highest-leverage precision upgrade. https://github.com/oraios/serena
5. **HumanLayer's RPI → CRISPY methodology** — the open-source, battle-tested formalization of convergence planning (research → plan → implement, decomposed prompts, explicit human-alignment checkpoints). https://github.com/humanlayer/advanced-context-engineering-for-coding-agents


## 1. Agent orchestration harnesses (beyond Claude Code/Cursor)
- **Sourcegraph Amp** — `/handoff` context-handoff primitive, composable subagents (Oracle = stronger reasoner, Librarian = external-lib research, Painter), automatic per-task model selection. Speaks to the "which model fits each task class" question. Free tier, ~$10/day API cap. https://ampcode.com
- **Goose (Block, now under the Linux Foundation's Agentic AI Foundation)** — provider-swappable. **Recipes** (committable YAML bundling instructions + extensions + params + subrecipes — "skills as versioned, CI-runnable config") and parallel subagents. Stripe's "Minions" began as an internal Goose fork. https://github.com/block/goose
- **OpenHands + Software Agent SDK** (formerly OpenDevin) — hierarchical agent **delegation** and a "Large Codebase SDK" that orders multi-agent parallel refactors by **dependency graph** so they don't conflict. https://github.com/OpenHands/software-agent-sdk
- **Zed + Agent Client Protocol (ACP)** — decouples harness from editor, so Claude Code, Codex, Gemini CLI, OpenCode run as external agents in one UI. The interoperability standard the multi-harness stack may converge on. https://github.com/agentclientprotocol/agent-client-protocol
- **Aider** — **architect mode** (reasoning model proposes, cheaper model applies) and **watch mode** (acts on `AI!` comment markers, then commits). Every edit is a discrete git commit. https://aider.chat
- **Cline** — now SDK + CLI, not just a VS Code sidebar, so it can be a programmable worker inside your own orchestration; **shadow-git checkpoints** pair with experimental parallel runs. https://github.com/cline/cline

**Skip / caveats:** Roo Code (archived May 2026), Crystal (deprecated Feb 2026 → paid Nimbalyst), Terragon (company shut down Feb 2026; watch OSS only), RA.Aid (no current signal). Conductor and Claude Squad are solid but the *obvious* worktree-per-Claude incumbents — the picks above improve on that baseline.


## 2. Git-worktree parallel-agent tools
- **Sculptor**, **container-use** — see top-5 above (the two best here).
- **Vibe Kanban (BloopAI)** — kanban board that dispatches tasks to 10+ heterogeneous agent CLIs (Claude Code, Codex, Gemini, Amp, Cursor, OpenCode, Droid, Qwen…), each isolated in its own worktree. **Caveat:** Bloop wound down hosted services early 2026; self-host the OSS. https://github.com/BloopAI/vibe-kanban
- **uzi (DevFlow)** — closest OSS tool to what's done by hand, scaled: auto worktree + tmux per agent, dynamic dev-server ports, plus `uzi broadcast` (one instruction to all agents) and `uzi checkpoint` (commit + merge). https://github.com/devflowinc/uzi
- **Anthropic's C-compiler experiment** — a copyable **coordination protocol**: 16 parallel Claudes, each in its own Docker container sharing one git repo, coordinating via **lock files in `current_tasks/`** (a merge conflict tells another agent to pick a different task). https://www.anthropic.com/engineering/building-c-compiler


## 3. Spec-driven / skills workflow systems
- **OpenSpec** — lightest in-repo SDD (proposals/specs/tasks as markdown, strict propose→apply→archive lifecycle), brownfield-first, drives 25+ tools via slash-command wrappers. Adds a real **explore** phase and a **Stores** feature for structured spec persistence. https://github.com/Fission-AI/OpenSpec
- **Anthropic Agent Skills (SKILL.md open standard)** — the formal spec for "one source, many wrappers"; an **open standard (agentskills.io, Dec 2025)** read by ~32 tools. Built-in **progressive disclosure** mechanizes the "read only when relevant" convention. https://github.com/anthropics/skills
- **rulesync** — see top-5. Simpler rules-only sibling: **ruler**, https://github.com/intellectronica/ruler.
- **Superpowers (obra / Jesse Vincent)** — battle-tested skills library + methodology (brainstorm → plan → verify-first → implement, self-updating memory journal; auto-creates a **worktree** per task). Mine its **planning-gate structure** ("agent must earn the right to write code"). https://github.com/obra/superpowers
- **Agent OS v2 (Builder Methods)** — three-layer context model (standards / product / specs) mapping onto AGENTS.md/PROFILE/PROJECTS layering; its **standards layer** injects style/commit/naming conventions at spec-generation time. https://github.com/buildermethods/agent-os
- **GitHub Spec Kit** — first-party SDD reference (`specify` CLI, Spec→Plan→Tasks→Implement across 30+ agents). Heavier/greenfield-leaning; treat as validation. https://github.com/github/spec-kit
- **Tessl (Guy Podjarny)** — the horizon bet: **spec becomes the maintained artifact, code becomes regenerated output**, plus a **Spec Registry** ("npm for specs"). Still thesis-stage. https://tessl.io

**Down-weight:** BMAD-METHOD (heavyweight 12-persona SDLC — conflicts with a lightweight many-small-apps posture); Taskmaster (task decomposition, overlaps OpenSpec); AWS Kiro (consumes AGENTS.md + Skills.md + MCP but reported to over-engineer — track the standards support, skip the IDE).


## 4. Human-out-of-the-loop / autonomous SWE agents & the "fleets" canon
**Practice references (internalize these — most directly ahead of common solo practice):**
- **StrongDM "Software Factory" + open-source Attractor** — a 3-person team shipping production under "no human writes code, no human reviews code." Transferable: **LLM-graded "scenario" acceptance tests stored outside the codebase** ("satisfaction testing"), and a **"Digital Twin Universe"** — cheap local fakes of external deps (Okta/Slack/Jira/Google Docs) so agents self-verify thousands of scenarios/hour. For this system: build LLM-graded scenario suites + local fakes of S3/Pinecone/Webflow/LLM providers. https://github.com/strongdm/attractor · writeup: https://simonwillison.net/2026/Feb/7/software-factory/
- **Stripe "Minions"** — canonical fleet reference (1,300+ merged PRs/week from Slack triggers, human review only at the end). Adoptable: **"Blueprints"** (mix *deterministic* nodes with *agentic* nodes in one workflow — the key reliability unlock for unattended runs) and isolated, network-less **Devboxes** (isolation *is* the permission system). https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents
- **Geoffrey Huntley — the "Ralph" loop** — cheapest solo path to long-horizon unattended runs: agent in an infinite shell loop re-reading the same prompt file, fresh context each iteration, state in filesystem + `IMPLEMENTATION_PLAN.md` + git. https://ghuntley.com/ralph/ · ref impl: https://github.com/snarktank/ralph
- **HumanLayer RPI → CRISPY** — see top-5. The most rigorous open methodology matching convergence planning.
- **Steve Yegge — "Revenge of the Junior Developer" / "The Brute Squad"** — names the role transition: six waves ending in "agent clusters" (2025 H2) → "agent fleets" (2026), developer as "agent manager." Building OSS orchestrator **Gas Town**. https://sourcegraph.com/blog/revenge-of-the-junior-developer
- **Simon Willison — "parallel coding agent lifestyle"** — living the multi-agent life (worktrees/fresh checkouts per agent, "designing agentic loops"). https://simonwillison.net/2025/Oct/5/parallel-coding-agents/
- **David Crawshaw (sketch.dev) — "How I program with Agents"** — **container-per-agent + rich tool feedback** (compiler/LSP, run-the-product-and-screenshot). https://crawshaw.io/blog/programming-with-agents
- **Armin Ronacher** — grounded, cost-aware guidance (Sonnet over Opus for most work; "throwaway code as a tool"). https://lucumr.pocoo.org/2025/6/12/agentic-coding/

**Autonomous agent products (issue → PR, gated):**
- **Charlie Labs "Daemons"** — always-on agents defined by simple `.md` files (mirrors AGENTS.md), self-triggering from GitHub/Linear/Slack/Sentry. https://charlielabs.ai
- **Jules (Google)** — fully async, GitHub-native (issue → PR), with a **self-healing CI loop** + public API. https://jules.google
- **Factory.ai "Droids"** — parallel self-directed agents running the full SDLC with **per-task model routing**; #1 on Terminal-Bench. https://factory.ai
- **Devin (Cognition)** — end-to-end autonomy that now does its **own first-pass code review** before human review + desktop/GUI testing. https://devin.ai
- **Ellipsis** — agents defined as **config committed in your repo**, with an **auto-fix-from-review-comment loop**. https://ellipsis.dev
- **Tembo** — fleet-conductor that runs multiple agents across a backlog, across repos/envs/providers. https://tembo.io
- **Tusk** — dedicated **test-gate agent** (auto-generates unit/integration tests per PR from live context). https://usetusk.ai


## 5. Multi-agent AI code review / CI gates
- **CodeRabbit** — most mature/configurable, lowest false-positive rate; the aligned differentiator is the **free CLI** (`cr --agent` emits structured JSON) + **CodeRabbit Skills** — gate code *locally inside the agent loop before a PR exists*. https://coderabbit.ai
- **Greptile** — full-repo **RAG-context** reviewer (indexes the whole monorepo, reasons cross-module), self-hostable with an **API**. Highest raw bug-catch rate (~82%); noisier, pair with tight custom rules. https://greptile.com
- **PR-Agent (Qodo, community-owned)** — fully **self-hostable, BYO-LLM, Apache-2.0** — best privacy fit for a nonprofit already keeping data out of repo. https://github.com/The-PR-Agent/pr-agent
- **Entelligence AI** — reviewer with a persistent **learning graph** (writes root-causes to memory) + auto-refreshing docs. https://entelligence.ai
- **Baz** — turns past PR discussions into enforced custom reviewers ("Discussion Memory"); catches cross-service/schema-drift defects. https://baz.co
- **Graphite Agent** (formerly Diamond) — fast, low-noise reviews + a **stacked-PR** paradigm suited to many small dependent changes. https://graphite.com/features/ai-reviews


## 6. Codebase knowledge-graph / code-intelligence for agents
- **Serena** — see top-5 (the everyday driver).
- **`colbymchenry/codegraph`** — **sleeper find:** pre-indexed local code knowledge graph, auto-syncs on change, with **explicit Hermes Agent support** (rare) plus Claude Code/Codex/Cursor/Gemini. https://github.com/colbymchenry/codegraph
- **Understand-Anything** (canonical repo `Egonex-AI/Understand-Anything`) — codebase → interactive knowledge graph as a Claude Code plugin; **incremental** re-analysis, **diff-impact analysis**, domain/business-logic mapping. https://github.com/Egonex-AI/Understand-Anything
- **LightRAG** (EMNLP 2025) — dual-layer KG+vector built to fix GraphRAG's heavy compute and **expensive incremental updates** — the cost that bites when re-indexing often. https://github.com/HKUDS/LightRAG
- **Potpie** — repo + SDLC → living context graph, then spin **prompt-defined per-repo agents**. https://github.com/potpie-ai/potpie
- **Blarify / SCIP** — OSS codebase-to-graph using **SCIP (~330× faster reference resolution than LSP)**. https://github.com/blarApp/blarify
- **Morph (Fast Apply)** — decouples *reasoning* (big model) from *applying edits* (a 7B model at ~10.5k tok/s, 98% accuracy) — ~40% token and ~100× latency win on the edit step. https://morphllm.com
- **Packers (reliable fallback):** Repomix (best-maintained, token counting), gitingest, code2prompt. https://github.com/yamadashy/repomix


## 7. MCP ecosystem worth standardizing on
- **context7 (Upstash)** — injects **current, version-specific library docs** into context, killing stale-training-data hallucinations — the main failure mode when agents write everything. https://github.com/upstash/context7
- **Official MCP Registry** — canonical source-of-truth for server discovery/provenance; standardize here over ad-hoc GitHub installs. https://registry.modelcontextprotocol.io
- **Docker MCP Toolkit + Catalog** — 300+ MCP servers as **signed, sandboxed containers** behind a gateway. https://docs.docker.com/ai/mcp-catalog-and-toolkit/
- Core trio to run: **Serena** (symbol nav/edit) + **context7** (fresh docs) + the existing **GitHub MCP**.


## Suggested next moves (opinionated)
1. **Try this week:** the **Ralph loop** on top of Claude Code cloud sessions for unattended long-horizon runs — plugs into existing `plans/` / `IMPLEMENTATION_PLAN.md` conventions.
2. **Precision + tokens:** add **Serena** and **context7** as core MCP servers; evaluate **`colbymchenry/codegraph`** (Hermes-native).
3. **Handoff:** try **container-use** (harness-agnostic primitive for skills/hooks) and **Sculptor** (productized cloud/local handoff).
4. **Self-verification gate:** steal StrongDM's **LLM-graded scenario tests + local "digital twin" fakes** of S3/Pinecone/Webflow; add a pre-PR gate via **CodeRabbit CLI** or self-hosted **PR-Agent**.
5. **One-source discipline:** adopt the **SKILL.md standard** as canonical and **rulesync** to generate Hermes/CC/AGENTS.md wrappers.
6. **Watch:** Zed **ACP** (interoperability standard), Yegge's **Gas Town** (fleet orchestrator OSS), **Tessl Spec Registry** (specs-as-dependencies).


## Verification caveats
Some third-party star counts and a few blog details came from search excerpts (simonwillison.net,
StrongDM, Substack returned 403 to the fetcher); all URLs are correct and worth opening directly.
Project *status* flags (Roo Code / Crystal / Terragon wound down; Bloop/Vibe Kanban company
shutdown; Sweep in maintenance) are the load-bearing corrections to note before investing time.
