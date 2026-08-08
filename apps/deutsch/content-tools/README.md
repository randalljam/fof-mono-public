file: apps/deutsch/content-tools/README.md
title: content-tools — shared harness for Deutsch content apps
last-updated: 2026-07-28_1349
ai: Codex GPT-5.5 via Claude Code (Fable 5, local)
session: Build content tools #3/#4/#5

`content-tools` is shared local infrastructure, not a product app. It hosts the common tone knob, saved-run storage, sample files, and one localhost FastAPI server for the three Deutsch content tools: #3 `deutsch-interject`, #4 `content-redo`, and #5 `content-forge`. The harness discovers installed tools through a registry and imports each engine lazily so later apps can plug in by creating their app directory and engine module, without editing `ctools/server.py`.


## Quickstart
From the repo root with the venv active:
```
python apps/deutsch/content-tools/run_tools.py selftest
python apps/deutsch/content-tools/run_tools.py serve --port 8971
```
Then open `http://127.0.0.1:8971/`. The server binds localhost only, injects a per-run token into pages, and requires `X-CT-Token` for `/api/` calls.


## Layout
```
run_tools.py              CLI: serve / selftest
ctools/
  config.py               paths, sys.path wiring, tone knob, tool registry
  runs.py                 saved-run JSON files under each app's gitignored data/runs/
  server.py               one local FastAPI server for all registered content tools
web/index.html            landing page showing installed/missing tools
samples/sample-discussion.md   original sample transcript for interjector testing
```


## How the harness works
`ctools.config.TOOLS` is the contract. Each row names an app directory, HTML page, Python engine module, and label. `tool_available(key)` checks that the app directory and engine module exist. `ctools.server` loads the Deutsch graph and citation index once at startup, serves `/` and `/{tool}`, and handles `POST /api/{tool}/run` by lazily importing the tool module and calling `run_from_request(payload, state)`.


## Run Storage
Runs are stored as JSON files under the owning app's gitignored `data/runs/` directory. Run ids are deterministic counters with short slugs, such as `run-0001-sample-discussion`, derived from existing files rather than timestamps or randomness. The server returns saved runs through `GET /api/{tool}/runs` and `GET /api/{tool}/runs/{run_id}` and can delete them with `DELETE`.


## Trade-offs
- **One server, many tools**: pro: one local security posture, one token, one graph load, one saved-run API. Con: if a later tool needs very different live state, it must fit the shared `state` dict or add a small harness extension.
- **Lazy engine imports**: pro: #4 and #5 can be absent without breaking #3. Con: engine import errors appear when the tool is invoked, not at server boot.
- **Local JSON runs**: pro: easy to inspect, no database dependency, consistent with worldview-mirror. Con: no multi-user concurrency or server-side account model.


## TODOs
- Add explicit per-tool request schemas so malformed inputs produce precise 4xx responses.
- Make saved-run writes atomic and collision-safe before supporting concurrent processes.
- Consider a small shared citation-resolution endpoint if multiple UIs need graph-node lookup outside run results.


## Rules for agents
- Do not put product-specific logic in `ctools/server.py`; add it to the product engine and expose it through `run_from_request`.
- Keep imports of tool engines lazy so missing future apps do not break the installed app.
- `data/` directories are gitignored run/user data. Do not commit or casually read them.
- The server must stay localhost-only with token-authenticated `/api/` routes.


## Tests
```
.venv/bin/python3 -m pytest tests/test_deutsch_interject.py -q
```
The harness tests live in `tests/test_deutsch_interject.py` and cover run storage plus the shared FastAPI server with a stubbed engine.
