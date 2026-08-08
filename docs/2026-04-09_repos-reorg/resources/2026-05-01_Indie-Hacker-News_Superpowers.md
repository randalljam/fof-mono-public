## One dev's Claude workflow hit 174k stars in 7 months

**Channel:** Indie Hacker News  
**Date:** May 1, 2026  
**URL:** https://www.youtube.com/watch?v=utRYkiqGuZI  
**Length:** 8:38

**Creator description:** One developer's personal Claude workflow just hit 174,502 stars in seven months. obra/superpowers is Jesse Vincent's solo agentic-skills framework. It started as his own opinionated coding-agent process, ended up on Anthropic's official Claude plugin marketplace, and now ships on every coding agent that exists: Claude Code, Codex, Cursor, OpenCode, Copilot, and Gemini. Forced TDD. Spec-first conversations. Subagent-driven development. The most influential indie release in agentic coding this year.


### Chapters

| Time | Section |
| --- | --- |
| 00:00 | Intro |
| 01:25 | The README |
| 02:50 | Why it stands out |
| 03:32 | The spec sheet |
| 03:43 | The collaboration skills |
| 05:12 | Under the hood |
| 05:56 | Installation |
| 06:16 | Latest releases |
| 06:57 | Who it's for |
| 07:37 | Verdict |


### Resources

- https://github.com/obra/superpowers
- https://blog.fsck.com/2025/10/09/superpowers/
- https://claude.com/plugins/superpowers


## Transcript

### 00:00 — Intro

One developer's personal coding workflow just hit 174,000 stars. Okay, so here's something kind of wild that's been quietly happening on the trending list, and I don't think most people have wrapped their head around how big it got.

There's a developer named Jesse Vincent who runs a small consulting outfit called Prime Radiant. Back in October of 2025, he pushed up a repo called Superpowers. It's basically his personal collection of opinionated workflows for working with Claude Code — test-driven development, brainstorming patterns, plan writing rules, code review checklists, stuff he wrote for himself to stop his coding agent from going off the rails.

Seven months later, the repo is sitting at 174,500 stars, 15,400 forks, 439 commits, and Anthropic put it on the official Claude plugin marketplace. It now ships on every coding agent that exists.

174,000 stars, 15,400 forks, MIT licensed, and it's the only personal skills repo Anthropic listed on the official Claude plugin marketplace. It launched October 9th, 2025. The latest release went out March 31st, and the install instructions now cover Claude Code, Codex CLI, Codex Desktop, Cursor, OpenCode, GitHub Copilot, and Gemini CLI.

Let me show you what's actually inside this thing.


### 01:25 — The README

The readme opens with a thesis statement that's basically the entire pitch. Superpowers is a complete software development methodology for your coding agents — not a CLI tool, not a wrapper, not a fine-tune. It's a methodology encoded as a set of skills that load automatically when your agent sees you trying to build something.

The flow it forces on the agent is pretty rigid. As soon as you ask it to build, it stops. It doesn't write code — it interrogates you about what you're actually trying to do. It pulls a spec out of the conversation. It shows you the spec in chunks short enough to actually read. Once you sign off, it writes an implementation plan that's clear enough for a junior engineer with poor taste and no judgment to follow. Then it dispatches sub-agents to work each task while the parent reviews their output.

The installation section is genuinely impressive. Eight different coding agents, each with first-class instructions: Claude Code and the Claude plugin marketplace listing, OpenAI Codex CLI and the desktop app, Cursor, OpenCode, Copilot CLI, and Gemini CLI. Each one gets a different bootstrap script.

Then below that you get the basic workflow numbered out: brainstorming, Git work trees, plan writing, sub-agent driven development, test-driven development, requesting code review, finishing a development branch. Each one is its own skill, and they trigger automatically based on what the agent is doing.


### 02:50 — Why it stands out

Okay, so why does this repo get 174,000 stars when Matt Pocock's personal skills repo sits at 49,000 and Anthropic's own demo skills directory sits well below that?

The pitch is opinionated process, not just a list of helpers. Most agent skills repos are essentially a folder of one-shot prompt files that you copy into your editor. Superpowers ships a methodology that triggers automatically and then refuses to let the agent skip steps.

The skills include explicit guidance to the agent on when to invoke them, what counts as success, and what counts as failure. They use techniques borrowed from persuasion research — things like commitment and consistency — to keep the agent disciplined.


### 03:32 — The spec sheet

The repo has 14 named skills, 60 active branches, 26 tagged releases, 15,400 forks, and 700 people watching active development.


### 03:43 — The collaboration skills

Let me walk through what's actually in the skills library, because this is where the value is.

Brainstorming activates before any code gets written. It runs Socratic refinement, asks you about edge cases, presents the design back in chunks for you to validate, then saves a design document.

Using Git work trees activates after the design is approved — creates an isolated workspace on a fresh branch and verifies a clean test baseline before anything proceeds.

Writing plans turns the approved design into bite-size tasks of two to five minutes each, with exact file paths and verification steps spelled out.

Sub-agent driven development takes that plan and dispatches a fresh sub-agent per task, with two-stage review for spec compliance first, then code quality second.

On the testing and verification side, there are four more skills that genuinely change how the agent behaves.

Test-driven development enforces strict red-green-refactor. The agent has to write a failing test, watch it fail, write minimal code, watch it pass, and commit. If you wrote the implementation before the test, the skill instructs the agent to delete your code and start over with the test first.

Systematic debugging is a four-phase root cause process that explicitly bans guessing fixes.

Verification before completion stops the agent from declaring a task done before the actual evidence is in.

Requesting code review is a pre-review checklist that catches things the agent missed before another reviewer sees the work.


### 05:12 — Under the hood

Under the hood, every skill is a markdown file with structured front matter. Each skill declares its trigger conditions, its mandatory steps, its success criteria, and its failure modes.

The framework uses a session start hook that injects context into your coding agent the moment the session opens. It detects which agent is running using environment variables, then emits the right bootstrap format for that platform.

Recent commits added support for the Copilot CLI context injection format, and the Codex desktop app integration is now driven by committed plugin files instead of a sync script.

The whole thing is shell scripts and markdown — no runtime, no daemon, no dependencies beyond your coding agent.


### 05:56 — Installation

Setup is honestly the cleanest part of the whole project. The official Claude plugin marketplace command works in one line. There's a separate Superpowers marketplace if you want bleeding-edge releases.

Codex, Cursor, Copilot, and Gemini each have their own one-line install. You don't manage anything — the plugin updates automatically.


### 06:16 — Latest releases

There have been seven releases shipped since the original launch, and the recent ones are interesting.

Version 5.0.5 fixed a brainstorming server crash on Node 22 and a Windows PID bug.

Version 5.0.6 made the most controversial change. Jesse killed the sub-agent review loops. He ran regression tests across five versions with five trials each, and the results showed identical quality scores whether the review loop ran or not. So he replaced an entire 25-minute overhead with an inline self-review checklist.

Version 5.0.7 added Copilot CLI session start support and OpenCode skill path fixes.


### 06:57 — Who it's for

So who actually benefits from installing this in 2026?

If you're a solo builder shipping a product on Claude Code and you keep finding the agent goes off the rails, the brainstorming and plan writing skills are exactly the guardrails you've been wishing for.

If you're running a small team that wants to standardize how code gets written across humans and agents, the methodology gives you a shared protocol that everyone follows.

If you write a lot of test-heavy production code and you've watched coding agents pretend to write tests, the TDD skill literally refuses to let the agent skip the failing test step.

And if you're building your own skills or plugins, the writing skills meta skill is a complete guide for how to author one.


### 07:37 — Verdict

Okay, let's be real about the tradeoffs. The methodology is opinionated to the point of being annoying if you just want to bash out a quick script — forcing brainstorming and a written plan before every code change makes a 30-second task feel like a 15-minute task.

The framework only really shines on substantial work, anything more than a few hundred lines. There's a real argument that some of the structure is overkill for senior engineers who already do this stuff in their head.

But for everything that's a caveat, the project is the most important indie release in the agentic coding space this year. 174,000 stars on a one-person methodology repo, MIT licensed, Anthropic blessed it on the official marketplace. It works on every coding agent. The maintainer is shipping every two weeks.

If you build with coding agents in 2026 and you have not at least skimmed the skills directory, you're missing the most influential workflow shift in the entire space.

Repo link is in the description. Thanks for watching — I'll catch you tomorrow.
