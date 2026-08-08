file: apps/autolearner/README.md
title: AutoLearner — AI mastery practice for PreCalc Test 1
last-updated: 2026-07-27_0705

Local MVP / quick prototype — built for in-browser local use, not deployed. An AI-driven study app from `Math PreCalc Test 1 Study Guide.md`. Two pieces:

1. **Interactive study guide** (`web/study-guide.html`) — the markdown guide as an interactive site: sidebar nav, search, formula flashcards, quick-check questions with reveal, and mastery checkboxes saved in the browser.
2. **AI practice app** (`web/index.html` + Flask backend) — mastery-based practice loop. The student is given one problem per concept, told to **think aloud the entire time** while solving on paper (record button, explicit instructions + example), then photographs their written work. The recording is transcribed with Deepgram (word-level timestamps via `core/transcribe.py`), pacing is analyzed (pauses, pace, hesitation), and a structured-output LLM call (`core/llm.py`, Anthropic tools with OpenAI fallback) assesses the transcript + timing + photo: correctness, reasoning quality, pacing, confusion flags, specific gaps with evidence, strengths, an overall assessment, and a 0–100 **mastery score**. Round 1 covers all 12 concepts; later rounds revisit only the concepts below the mastery threshold (85) with **new LLM-generated exercises targeted at the identified gaps**, until everything is mastered. Anytime the student is stuck they can hit "I'm stuck — teach me" and get a generated mini-lesson as a rich page plus TTS audio.


## Run locally
From the repo root:

```bash
# one-time setup (or use the existing repo venv)
python3 -m venv .venv
.venv/bin/pip install flask requests python-dotenv openai anthropic "deepgram-sdk>=3.7.3,<4.0.0"
# (or the full set: .venv/bin/pip install -r dependencies/requirements_2026-07-11.txt)

.venv/bin/python3 apps/autolearner/server.py
```

Then open:
- http://localhost:5055 — the AI practice app
- http://localhost:5055/guide — the interactive study guide

Port override: `AUTOLEARNER_PORT=8080 .venv/bin/python3 apps/autolearner/server.py`.

Use Chrome/Safari and allow microphone access when prompted (localhost is a secure context, so `MediaRecorder` works without HTTPS). On a phone, the photo input opens the camera directly.

### API keys (.env at repo root)
| Key | Used for | Without it |
|-----|----------|-----------|
| `DEEPGRAM_API_KEY` | word-timestamp transcription (`core/transcribe.py`) | mock transcript |
| `ANTHROPIC_API_KEY_LOCAL` | assessment / exercises / lessons (preferred) | falls to OpenAI |
| `OPENAI_API_KEY_LOCAL` | assessment fallback + TTS lesson audio | mock assessment, no audio |
| `OPENAI_API_KEY_TTS` | TTS lesson audio (preferred over `_LOCAL`) | falls to `_LOCAL` |

Every service degrades to a clearly-labeled **mock mode** when its key is missing, so the whole flow is testable in the browser with no keys at all — the header badges show `mock` vs live per service.


## Layout
- `Math PreCalc Test 1 Study Guide.md` — the source study guide
- `web/study-guide.html` — interactive study guide (self-contained + MathJax CDN)
- `web/index.html` — practice app frontend (single page)
- `content/concepts.json` — 12 mastery concepts × 3 seed exercises with reference solutions
- `server.py` — Flask dev server and API (`/api/state`, `/api/submit`, `/api/teach-me`)
- `pipeline.py` — Deepgram transcription, structured LLM assessment (transcript + pacing + photo), targeted exercise generation, lesson generation + TTS
- `pacing.py` — pure pacing analysis over Deepgram word timestamps
- `mastery.py` — pure session state + multi-round mastery scheduler
- `data/` — runtime sessions/uploads/lesson audio (gitignored via the root `data/` rule)


## Tests
```bash
.venv/bin/python3 -m unittest tests.test_autolearner -v
```
26 tests: pacing metrics (pause detection, fillers, timeline buckets), mastery scheduling (round-1 coverage, round-2 targeting of weak concepts, generated-exercise preference, done state, save/load), and the Flask API end-to-end with the pipeline services patched (submit records attempts and advances, round-2 triggers targeted generation, teach-me, validation errors, attempt/media review endpoints).
