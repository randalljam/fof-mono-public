file: apps/deutsch/worldview-mirror/README.md
title: worldview-mirror — self-analysis worldview explorer + Worldview Atlas
last-updated: 2026-07-12_0645
ai: Claude Code (Fable 5, local)
session: `Build worldview-mirror + atlas`

Use cases #1 (Worldview Mirror) and #2 (Worldview Atlas) from `apps/deutsch/deutsch-graph/docs/use-cases.md`, built together as one app. A local chat tool for articulating and exploring **your own worldview** next to a chosen lens worldview — by default David Deutsch's **deep optimism**, fully cited to the deutsch-graph (verbatim answers, YouTube timestamps, book terms). The **Atlas** is the taxonomy inside it: 14 worldview axes and 9 named worldview profiles, any of which can be swapped in as the lens.

Core design values (from Randy's notes): **mirror, don't preach**; **high transparency** — everything inferred about the user is visible, editable, deletable; **user-directed** personalization; a **tone knob** from super-gentle to almost-critical.


## Quickstart
From the repo root with the venv active (needs `fastapi`/`uvicorn` for serve; `OPENAI_API_KEY_LOCAL` in `.env` for chat):
```
python apps/deutsch/worldview-mirror/run_mirror.py selftest       # taxonomy valid? corpus fetched? key present?
python apps/deutsch/worldview-mirror/run_mirror.py serve          # -> http://127.0.0.1:8970/
python apps/deutsch/worldview-mirror/run_mirror.py chat "..."     # one-shot terminal turn
```
For verbatim Deutsch answers in responses, fetch the corpus once first: `python apps/deutsch/deutsch-graph/build_graph.py fetch` (without it the engine degrades to questions/labels/definitions from the committed graph).

## How a turn works
1. **Route + extract** (1 structured LLM call): the message is classified against the graph's 353 topics / 34 categories, and belief statements are extracted and mapped onto taxonomy axes with position and confidence.
2. **Ground**: top-starred QA items (with verbatim answers read from the fetched corpus), Deutsch Well claims/excerpts, and book-term definitions are assembled from the deutsch-graph for the routed topics.
3. **Reply** (1 chat LLM call): system prompt = safety preamble + mirror duty + tone-knob instruction + lens profile positions + the user's visible profile + grounding. The reply cites node ids like `[qa:...:000]`, rendered as ▶ YouTube-timestamp links in the UI.
4. **Mirror**: extracted beliefs are appended to the user's profile (visible in the Profile tab), and touched axes are diffed user-vs-lens (aligned / leaning-apart / divergent chips under the reply).

All OpenAI traffic goes through `core/llm.py` (provider-swappable). Default model = `core.llm.OPENAI_MODEL`; override with `WVM_OPENAI_MODEL`.

## Layout
```
run_mirror.py        CLI (serve / selftest / chat)
wvmirror/            engine package
  config.py          paths, tone knob, model default
  atlas.py           taxonomy loading + validation (axes, profiles, graph-evidence check)
  graph_access.py    deutsch-graph loading, verbatim answer/excerpt resolution, grounding packages
  engine.py          route+extract -> ground -> reply; citation extraction
  profile_store.py   user profile: JSON + generated markdown mirror, observations, overrides, aggregation
  threads.py         local-file conversation threads
  compare.py         user-vs-profile and profile-vs-profile axis diffs
  server.py          FastAPI app (localhost-only, session token)
taxonomy/            the Worldview Atlas data (hand-curated; reviewed like overlays)
  axes.jsonl         14 axes with poles, definitions, framework support, sources
  profiles/*.json    9 named worldview profiles; deep-optimism.json is fully graph-cited
web/worldview-mirror.html   hand-authored UI (chat + Mirror/Profile/Atlas panels)
docs/worldview-taxonomy.md  research survey, axis design decisions, trade-offs
data/                (gitignored) user profiles + threads — never committed
```

## Security posture
**v1 ships "basic" security; "provably secure" is explicitly deferred** (per use-cases.md, it's the hardest requirement and is infrastructure, not product).

Basic (implemented):
- Server binds **127.0.0.1 only**; every `/api/` call requires a per-run session token injected into the served page (`WVM_TOKEN` env can pin it).
- **All user data is local files** under `apps/deutsch/worldview-mirror/data/` (gitignored by the repo-wide `data/` rule). Nothing is uploaded anywhere except the message text sent to the OpenAI API for inference, and the UI says so in plain sight.
- Full user control: profile and threads are readable JSON (+ a generated human-readable markdown mirror of the profile), editable and deletable in the UI, including one-click delete-everything.
- Safety posture for a therapy-adjacent tool: fixed non-medical framing + crisis-line pointer (988) in both the system prompt and the UI footer; no hidden analysis by design.

Placeholders (deliberately NOT built yet — the confidentiality ladder from use-cases.md §1):
1. **User accounts + server-side thread storage** — thread/profile file formats are import-ready for a future backend.
2. **Client-side encryption with user-held keys** (server sees ciphertext except during inference).
3. **No-retention inference calls** (or local/on-device inference for the profile step).
4. Enclave/zero-knowledge "provable" claims — research project; v1 should claim "local, user-owned data, auditable open code", never "provable".

## Trade-offs / decisions (alternatives considered)
- **One app, not two**: the Atlas lives inside worldview-mirror (taxonomy/ + Atlas tab) instead of a sibling `worldview-atlas` app. Pro: one OpenSpec, no cross-app import for v1's only consumer. Con: a future standalone Atlas needs extraction. Revisit when a second consumer appears.
- **Local FastAPI + static UI, not Chalice/Webflow**: fastest path to the real product shape with zero deploy surface; deployment is a placeholder anyway. Con: diverges from the QRAG serving stack — migration will mean a Lambda-shaped engine port (the engine is dependency-light on purpose).
- **OpenAI default (per Randy), raw-requests path**: `core.llm.openai_chat_completion_request` (not `*_sdk`) because the shared venv's openai SDK (1.50.0) is currently broken against httpx 0.28 (`proxies` kwarg removed). Swap back to the SDK path when the venv is upgraded.
- **Two LLM calls per turn** (route+extract, then reply) instead of one: keeps extraction structured and reply grounded; costs latency. A single-call variant is possible if latency hurts.
- **Beliefs auto-added to the profile** (visible immediately, deletable) instead of confirm-first. Pro: frictionless accumulation; Con: occasional misreads land in the profile — mitigated by visibility, per-item delete, and direct axis overrides. Flip to confirm-first if it feels presumptuous.
- **Numeric axis positions** (-2..+2, omission = no position) — see docs/worldview-taxonomy.md for the full design rationale and dropped alternatives.

## TODOs / next steps
- Confirm-or-edit flow for extracted beliefs; axis-elicitation question batteries (SAWV-style) as an alternative to chat-only profiling.
- Adopt the shared divergence service (`dgraph/divergence.py`, built 2026-07-12 for use cases #3/#4) in the reply pipeline — currently the reply prompt still does divergence implicitly.
- Clip end-times (derive from next `_vrb` segment) so ▶ links become real clips; TTS delivery via `apps/voice/`.
- Export Deutsch's cited axis positions into deutsch-graph L5 overlays once that format lands (`graph-spec.md`).
- More profiles (EA, existentialism, Confucianism, ...) and a taxonomy review log.
- Accounts + thread backend + the confidentiality ladder (see Security posture).

## Rules for agents
- `taxonomy/` is hand-curated data: edit it directly, keep `python run_mirror.py selftest` green (it validates every graph-cited evidence node against the committed deutsch-graph).
- `web/worldview-mirror.html` is hand-authored source — edit freely. `data/` is user data — never commit, never read without need.
- The engine must stay import-safe without API keys (`core.llm` is imported lazily inside `engine._chat` only).

## Tests
```
.venv/bin/python3 -m pytest tests/test_worldview_mirror.py -q
```
Self-contained: taxonomy validation runs against the committed graph; engine/server tests stub the LLM call (no network, no keys needed).
