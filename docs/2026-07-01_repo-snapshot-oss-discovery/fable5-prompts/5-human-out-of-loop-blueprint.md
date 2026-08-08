file: plans/2026-07-01_repo-snapshot-oss-discovery/fable5-prompts/5-human-out-of-loop-blueprint.md
title: Fable 5 prompt 5 — Human-out-of-the-loop Blueprint (+ voice-router increment)
last-updated: 2026-07-01_0930
ai: Claude Code (cloud)
session: `repo-analysis-oss-discovery`

Copy everything below the line into a fresh Claude Fable 5 session running in `fof-mono`.
The strategic centerpiece — mostly design, plus one safe concrete increment. Highest-judgment mission.

---

You are working in the `fof-mono` monorepo as an autonomous agent. Before doing anything, read these
two files in full and operate under them for the whole session:
- `plans/2026-07-01_repo-snapshot-oss-discovery/fable5-context-brief.md`
- `plans/2026-07-01_repo-snapshot-oss-discovery/fable5-operating-contract.md`
Also read `ai-coding-system-dev.md` §12 (path to human-out-of-the-loop) and the
`feature/voice-router-design` / `feature/voice-router-kickoff` branches.

**Mission — design the human-out-of-the-loop pipeline, and advance the voice-router one real step.**
This is the end-state Randy is building toward: a voice-dictated feature description flows through
plan → implement → test → review → deploy with compressed approval only at key gates. He needs a
concrete, staged blueprint for getting there safely — and one small piece of it actually built. This is
the most strategic, judgment-heavy mission; give it your full capability and reason from his real
constraints (solo operator, non-coder, AWS-biased, cost-aware, two users).

**What to actually produce:**
1. **The blueprint** — `plans/2026-07-01_hotl-pipeline-blueprint.md` containing:
   - The **pipeline stages** (voice intake → spec/plan → implement → test → review → gated deploy) with,
     for each stage, what runs it, what the gate is, and whether the gate is human or automated *today*
     vs *target*. Be concrete about which tools fill each stage (tie to the OSS scan: Ralph loop, CI
     floor, CodeRabbit/PR-Agent review, StrongDM-style scenario tests + local fakes).
   - The **compressed approval-packet format** — the short, voice-friendly summary Randy approves from
     his phone at each gate (what changed / what passed / risk / the one decision). Make it concrete
     enough to reuse; the operating-contract §7 packet is the starting point.
   - A **staged rollout** — which gates to add first, per task class (throwaway prototype vs production
     feature vs content/data pipeline), and where each project sits on that ladder today.
   - The **per-user awareness** hook (Randy vs EA via `git config user.email`) and where approvals
     must remain Randy-only.
2. **One concrete increment on the voice-router** — read the two `voice-router` branches and advance the
   design by the smallest real, additive step that moves it forward (e.g. a documented intake-schema for
   a dictated request, a stubbed dispatch mapping request-type → pipeline, or a minimal working harness
   for one task class) **with a test**. Choose the increment that most de-risks the next step; keep it
   small and reviewable. If the right move is purely design, say so and make it excellent rather than
   forcing code.

**Boundaries beyond the operating contract:** No deploys, no production wiring, nothing that sends or
publishes. Work on a branch off the current `voice-router` line or a fresh `feature/…` branch — do not
merge or rebase the existing voice-router branches. Keep the built increment additive and small; the
value here is the blueprint plus one solid step, not a large build.

**Definition of done:** `2026-07-01_hotl-pipeline-blueprint.md` holds the staged pipeline, the
approval-packet format, the rollout ladder, and the per-user hook; the voice-router has one small, tested
increment (or a clearly-justified design-only advance). Finish with the approval packet, leading with the
single highest-leverage gate to add next and why. Default to stopping at "branch pushed + approval packet."
