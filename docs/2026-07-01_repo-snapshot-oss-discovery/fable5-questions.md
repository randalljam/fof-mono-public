file: plans/2026-07-01_repo-snapshot-oss-discovery/fable5-questions.md
title: 20 quick questions to sharpen the Fable 5 prompts and process
last-updated: 2026-07-05_1746
ai: Cursor - Composer 2.5 Fast
session: `repo-analysis-oss-discovery`

Prioritized by how much each answer changes the prompts. Each is a few-seconds answer — most have a sensible default in **bold** you can just confirm. Answer as many as you like, top-down; even the first five materially improve the runs. Format: answer inline (e.g. "1) Claude Code cloud. 2) Yes. …").


## Tier 1 — biggest impact (answer these five first)
1. **Which harness will you run these in?** (Claude Code on the web / Cursor / Codex / raw API) — decides how "automatic" they can be, whether they can run tests, and how much prompt caching cuts the token bill. Default assumption: **Claude Code on the web (cloud)**. **Answer: Claude Code cloud (in a virtual machine). Not raw API; may also use Cursor locally sometimes, but primary harness is Claude Code cloud.**
2. **Can that harness run the tests locally, or is it code-only?** — changes whether "verified by running" is possible or the prompt should say "verify by inspection + leave a run command." Default: **can run**. **Answer: No — cloud VM cannot run tests locally. Recreate the environment, test as much as the harness can, and leave remaining verification for local follow-up after code is generated.**
3. **Autonomy gate: open PRs, or stop at "branch pushed + approval packet"?** — every prompt currently defaults to stopping at the packet. Default: **stop at the packet; you open the PR after reading it.** **Answer: Stop at branch pushed + approval packet. Open the PR myself after reading, testing, or further developing locally.**
4. **What's your Fable usage allowance for this window** (a rough number, or your plan tier)? — needed to turn the token estimates into "how many runs before July 7." If you don't know, say so and I'll leave the budget page as the interactive calculator. **Answer: Ignored — not worrying about token usage for this work; I have a sense of it now after a few runs.**
5. **Total Fable budget you're willing to spend before July 7** — a run count (e.g. "about 6 runs") or a dollar/percentage cap. Default: **treat the 50% Fable pool as the ceiling and fit as many as it allows.** **Answer: Ignored — no budget cap for this work.**


## Tier 2 — scope and safety (answer if you can)
6. **Which app should the "App Baseline" mission target first?** Default: **`apps/math-quiz/`** (active, non-production, real logic). Name another if you'd rather. **Answer: Ignored — I'll specify app-specific or core work per run.**
7. **Any apps/paths strictly off-limits to autonomous runs** beyond `qrag` prod and `[S3-BUCKET]`? Default: **just those two.** **Answer: I'll ask for app-specific or core work per run. QRAG is possible but unlikely. `[S3-BUCKET]` is an AWS bucket — must not do anything destructive to it. Otherwise no extra off-limits paths beyond the defaults.**
8. **Are GitHub Actions allowed to be added now**, or do you want to review the workflow file before it lands? Default: **add it on a branch; you review before enabling required checks.** **Answer: Add on a branch. I'll review the missions again alongside other Fable 5 prompts before enabling.**
9. **Priority order of the five missions** (or just "run them in the listed order")? Default order: **1 Cartographer → 2 Safety Rails → 4 App Baseline → 3 Meta-System → 5 HOTL Blueprint.** **Answer: Default order is fine — I'll decide which prompts and apps to run.**
10. **Breadth or depth?** Prefer touching many projects lightly, or fully finishing one at a time? Default: **depth — finish one clean thing per run.** **Answer: Depth — finish one clean thing per run.**


## Tier 3 — tuning (nice to have)
11. **Should Fable actually adopt new OSS tools** (Serena / context7) itself, or only plan them? Default: **wire in one (context7 or Serena) if it can; plan the rest.** **Answer: No — not unless I make that a specific point in the prompt.**
12. **Voice-router: advance with real code now, or design-only this round?** Default: **one small tested increment if there's an obvious safe one; otherwise design-only.** **Answer: Already done one increment; design-only this round unless I ask otherwise.**
13. **Default effort level** for these runs — `high` or `xhigh`? Default: **high** (Fable's `low`/`medium` often already beat older models; save `xhigh`/`max` for the hardest mission, #5). **Answer: Yes — default high.**
14. **Who runs these — only you, or EA too?** Affects the per-user-awareness design in mission 5. Default: **you.** **Answer: Me only — I'll own all of these runs.**
15. **Any hard deadline tied to a specific project** (e.g. the FOF website redo) I should weight in the roadmap? Default: **none.** **Answer: No hard deadlines — I'll decide which prompts and apps to work on.**
16. **Should each mission write a durable memory/notes file** for future sessions? Default: **yes, one per mission in its plan folder.** **Answer: Yes — write notes and pull composable, reusable content out into files as appropriate.**
17. **Is the 2026-07-01 snapshot (this folder) canonical context** the prompts should trust? Default: **yes.** **Answer: Yes — canonical context. Note: review of the files it generated is still pending on my side.**
18. **Preferred branch convention** — one `feature/…` branch per mission is assumed. Confirm or override. Default: **one `feature/…` branch per mission.** **Answer: Yes — one branch per Fable 5 prompt.**
19. **Do you want a PR opened as a draft** (so CI/review can run but it won't auto-merge) when a mission does open one? Default: **draft PRs.** **Answer: Don't worry about PRs — not a priority; I'll open them once I'm happy with the work (see Q3).**
20. **Any secrets/keys Fable will legitimately need** for a mission (e.g. to run real-API tests), or must it stay entirely offline? Default: **stay offline; skip anything needing a key and note it.** **Answer: If API keys or other secrets are needed for particular apps or runs, I'll add them to the Claude Code cloud environment.**


## How your answers get used
- Tier 1 answers get folded directly into the prompt headers (harness note, autonomy gate, budget) before you run them — that's the highest-value edit.
- Tier 2/3 answers mostly tweak defaults already written into the prompts, so the prompts work as-is if you answer nothing; they just get a little sharper and cheaper with your input.
