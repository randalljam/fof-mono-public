# Tasks: swing-v2-deck

- [x] Backend: `classify_agent_state` + `list_agent_status` in `turns/db.py` with tests (`tests/test_agents_status.py`)
- [x] Backend: `GET /api/agents` endpoint in `server.py` (matches existing turns-endpoint style)
- [x] Backend: `web/sample-agents.json` sample payload covering all four states
- [x] Frontend: restructure `index.html` into Deck / Active Work / Universe + demoted More group
- [x] Frontend: `renderAgentDeck` light-tile strip with 4-state colors, summary counts, polling
- [x] Frontend: Active Work — to-do panel + active worktree cards with turn-state badge and recap
- [x] Frontend: Universe — parked worktrees, checkout-less branches, apps; copy `create-worktree` prompt buttons
- [x] Frontend: update `tests/test_web.py` symbols and route checks
- [x] Docs: README API + UI description refresh
- [x] Verify: full pytest run green (152); live-server smoke in sample and real modes via browser
