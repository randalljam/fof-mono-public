file: docs/web-testing-guide.md
title: Web Testing Guide — unit, integration, and browser E2E (plain-language, reusable)
last-updated: 2026-06-12_0613
ai: Claude Code (cloud)
session: `MathQuiz thorough review`

A plain-language guide to the three-layer web testing setup first built for `apps/math-quiz/` (June 2026), written to be reused as the template for testing other web apps in this repo. It assumes you know Python unit tests with mocks (pytest-style) and builds from there. The worked example throughout is `apps/math-quiz/tests/`.


## The big picture: three layers
Think of testing a car. You can bench-test individual parts (does this spark plug fire?), run the assembled engine on a test stand (do the parts work together?), or actually drive the car around the block (does the whole thing work for a driver?). Each level catches problems the others can't, and each is slower and more expensive than the one before. Software testing calls this the **testing pyramid**: lots of fast unit tests at the bottom, fewer integration tests in the middle, a small number of full end-to-end tests on top.

| Layer | Question it answers | Speed | math-quiz files |
|---|---|---|---|
| 1. Unit | Does this one function compute the right thing? | milliseconds | `tests/math_*.test.mjs` |
| 2. Integration | Do the functions work together against a real database? | ~100 ms | `tests/db_import.test.mjs` |
| 3. End-to-end (E2E) | Can a user actually do the thing in a real browser? | seconds each | `tests/e2e/*.spec.mjs` |

A bug like "the Save Flags button writes to the wrong row when the list is sorted" is invisible to layer 1 (each function is individually correct) — it only appears when a real click flows through the real page. That's why all three layers exist.

### Layer 1 — unit tests (the same thing as your pytest work)
These are exactly the unit tests you already know from Python, just in JavaScript using Node's built-in test runner (`node --test`, the equivalent of `pytest` — no install needed). Each test calls one function with known inputs and asserts the output:

```js
test('parseProblemText parses legacy display forms', () => {
  assert.deepEqual(parseProblemText('5 &times; 3'), { num1: 5, operation: '*', num2: 3 });
});
```

The one twist: this app's JavaScript was written to run in a browser, so it expects browser things to exist — `document` (the page), `localStorage` (the browser's little key-value store). Node has none of those. So `tests/load_app.mjs` loads the app's JS files into a sandbox with **stub** versions of those objects — fake `document` and `localStorage` that do just enough to not crash. This is the same concept as `unittest.mock` / `monkeypatch` in pytest: replace the things the code touches but you don't care about, so you can test the logic you do care about.

### Layer 2 — integration tests (fewer mocks, real database)
You hit this tension in your LLM unit-test work: mock the external thing (fast, free, but you're testing against your *assumption* of how it behaves) or use the real thing (slower, but tests reality). The practical rule: **mock what is slow, expensive, or external (network, paid APIs); use the real thing when it's cheap and deterministic.**

The math-quiz dashboards store data in SQLite running *inside the browser* (a library called sql.js — SQLite compiled to WebAssembly). That same library runs happily inside Node, in memory, for free. So `db_import.test.mjs` mocks nothing database-related: it creates a real SQLite database, runs the app's actual import code on realistic session files, and checks the rows. This caught things no stub could — like verifying that re-importing the same session doesn't double the row counts.

### Layer 3 — end-to-end tests with Playwright (the new part)
**Playwright** is a tool (from Microsoft; the main alternative is Cypress) that launches a real Chrome/Firefox/Safari and drives it from a script, exactly like a human: open this page, type in this box, click this button, now read the screen and check what it says. The browser usually runs **headless** — fully real, just without a visible window — so it can run fast and on servers.

A test reads like a user story:

```js
test('wrong answer shows the correct answer and override marks it correct', async ({ page }) => {
  await page.goto('/math_quiz.html');                    // open the page
  // ... enter name, pick preset, start quiz ...
  await page.fill('#answer-input', String(answer + 1));  // type a wrong answer
  await page.press('#answer-input', 'Enter');
  await expect(page.locator('.feedback-message'))        // read the screen
    .toContainText(`Incorrect. The correct answer is ${answer}`);
  await page.click('#override-button');                  // click Override
  await expect(page.locator('#summary')).toContainText('Number of correct answers: 1');
});
```

The handful of concepts that cover 90% of Playwright:
- **Spec**: a test file (`*.spec.mjs`). **Test runner**: `npx playwright test` finds and runs them, in parallel.
- **Locator**: how you point at something on the page — `page.locator('#answer-input')` by id, or by visible text. (`#answer-input` is a CSS selector, the same ids you see in the HTML.)
- **Auto-waiting**: the killer feature. `expect(locator).toBeVisible()` automatically retries for up to N seconds. Web pages load and update asynchronously; older tools made you sprinkle `sleep(2)` everywhere and tests were flaky. Playwright waits for the condition, then proceeds immediately.
- **webServer**: the config can start your app automatically before testing (for math-quiz: a one-line static file server) and shut it down after.
- **Route interception**: the test can intercept any network request the page makes and answer it itself (see "hermetic" below).
- **Artifacts on failure**: when a test fails, Playwright saves a screenshot, a video, and a step-by-step **trace** you can replay — so you can see exactly what the browser saw.
- **Headed / UI mode**: `npx playwright test --headed` shows the browser window while tests run — watching the suite drive your app is the single best way to build intuition. `npx playwright test --ui` opens an interactive runner where you can step through each action.


## What "hermetic" means and why the tests intercept the CDN
A **CDN** (content delivery network) is just a fast public file server. The math-quiz pages don't bundle their third-party libraries; each page has script tags that download them at load time from public CDNs — sql.js and the md5 hasher from `cdnjs.cloudflare.com`, the Plotly charting library from `cdn.plot.ly`, etc. That's a common pattern for no-build-step apps (it came from the Webflow custom-code days).

A test that depends on five external servers is slow and flaky, and fails entirely with no internet. So the E2E setup makes itself **hermetic** (sealed — no outside dependencies): the exact same library versions are installed once from npm into `tests/node_modules`, and a Playwright route interception rule says "whenever the page requests anything from those CDN domains, serve the local copy instead" (`tests/e2e/helpers.mjs`). This is the moral equivalent of mocking a network call in pytest — except nothing is fake: it's the identical bytes the CDN would have served, just from disk. The app code is completely unaware and unmodified.


## Running the tests — cheat sheet
All test code lives in `apps/math-quiz/tests/` with its own `package.json`. Nothing about the app itself changes; you can delete the tests folder and the app still works.

### On your Mac (Cursor / local)
1. One-time setup:
```
cd apps/math-quiz/tests
npm install                          # test libraries (pinned by package-lock.json)
npx playwright install chromium      # downloads the test browser (~150 MB, once)
```

2. Run the tests:
```
npm test               # unit + integration (41 tests, ~1 s)
npm run test:e2e       # browser E2E (17 tests, ~20 s)
npm run test:all       # everything
npx playwright test --headed    # watch the browser do it (recommended once!)
npx playwright test --ui        # interactive step-through mode
```

3. Debug / Inspector cheat sheet:
When `npm run test:e2e -- --headed --debug` runs, expect two windows: **Google Chrome for Testing** is the real browser being driven, and **Playwright Inspector** is the remote control for the test script.
```
npm run test:e2e -- --headed --debug
PLAYWRIGHT_SLOW_MO_MS=500 npm run test:e2e -- --headed
PLAYWRIGHT_SLOW_MO_MS=500 npm run test:e2e -- --headed --debug
npx playwright test --ui
```
- Press **Resume** / the play button to let the test continue until the next pause or completion.
- Press **Step over** / `F10` to move one scripted action at a time, useful when the Inspector says something like `navigate to math_analysis.html` and you want to watch exactly what happens next.
- Use `PLAYWRIGHT_SLOW_MO_MS=500` to let the browser run automatically but more slowly; use `1000` for very slow.
- To abort cleanly, go back to the terminal running the test and press `Ctrl-C`. It is also okay to close the Inspector/browser windows, but `Ctrl-C` is the clean terminal habit because it stops the Playwright process and its local web server.
- The browser may look idle while the Inspector is paused; that is normal. The test is waiting for you, not hung.
- Avoid manually clicking around in the browser during an automated run unless you are intentionally experimenting, because the script expects to control the page state.
- `npx playwright test --ui` opens Playwright's interactive test dashboard. Use debug mode for one step-through run; use UI mode to browse, choose, rerun, and inspect tests from a control panel.

The unit layer alone also runs with zero install: `node --test apps/math-quiz/tests/*.test.mjs` from repo root (the database tests skip themselves politely if `npm install` hasn't happened).

### In a Claude Code cloud session (sandbox)
Nothing to do — same commands work. See the next section for why the configuration has a special fallback there.


## The sandbox environment note, explained
Two unrelated things both happen to be called "downloading from a CDN", and the Claude Code cloud sandbox blocks both:

1. **The app's runtime libraries** (cdnjs, cdn.plot.ly). Already handled for tests by the hermetic interception above — tests never touch those domains anyway.
2. **Playwright's browsers.** Real browsers are too big to ship inside an npm package, so `npx playwright install chromium` downloads Chromium from Microsoft's own browser CDN as a separate step. The sandbox's network policy allows the npm registry and GitHub but blocks general web traffic — so that download fails with a 403 in cloud sessions.

The workaround: a package called `@sparticuz/chromium` ships an actual Chromium binary *inside* an npm package (it exists for AWS Lambda, which has the same constraint). Since npm is allowed, that gets through. `tests/playwright.config.mjs` resolves the browser in priority order, so the same config works everywhere with zero changes:
1. `PLAYWRIGHT_CHROMIUM_PATH` environment variable (manual override),
2. a browser previously installed by `npx playwright install chromium` ← **your Mac**,
3. the npm-packaged `@sparticuz/chromium` (Linux only) ← **cloud sandbox**.

**Impact on your cloud → local workflow: effectively none, and that's the point.** A cloud agent can build features and run the full suite before handing off; you (or your local agent) pull the branch, run the one-time `npx playwright install chromium`, and run the identical suite locally. The hermetic CDN interception also means test results don't depend on which machine has internet access to which domains. The standing instruction for the local agent is just: `cd apps/math-quiz/tests && npm install && npx playwright install chromium && npm run test:all`.


## Reusing this as a template for other apps
The pattern to copy for a new web app `apps/<name>/`:

1. **`apps/<name>/tests/` with its own `package.json`** — test code and dependencies fully separate from app code. Pin versions; commit `package-lock.json`; gitignore `node_modules/` and Playwright artifacts.
2. **Unit layer**: pure-logic functions get direct tests. (The vm-loader trick in `load_app.mjs` is only needed for no-build-step apps whose JS isn't importable; an app built with a framework would use ordinary imports with a runner like Vitest instead.)
3. **Integration layer**: run the app's real data code against the real (local, in-memory) engine — mock only what's external or paid.
4. **E2E layer**: copy `playwright.config.mjs` and change one line — the `webServer.command` that starts the app (static server here; `npm run dev` for a framework app; `uvicorn`/`chalice local` for a Python backend). Copy the helpers patterns:
   - **CDN/route interception** for any external resources (or skip if the app bundles everything),
   - **seed data via `addInitScript`** — preload localStorage/state before the page loads, so dashboard tests don't have to click through 10 minutes of setup to have data,
   - **page-error tracking** — every test asserts the browser console threw zero uncaught errors, which catches whole categories of breakage for free,
   - **driver helpers** — reusable functions like `startPresetQuiz()` so specs read as user stories.
5. **What to test at which layer**: calculations and parsing → unit; data import/query → integration; one E2E test per user journey (the "happy path"), plus E2E regression tests for any bug that only manifested through real UI interaction.
6. **Document the run commands** in the app's `AGENTS.md` under `## Tests` so future agent sessions test before PRs.

Future step (tracked in `ai-coding-system-dev.md` direction items): wire `npm run test:all` into CI (GitHub Actions) so every PR runs the suite automatically. The hermetic design was chosen partly so that step is trivial later.


## Manual testing alongside automated testing — terminology
Automated tests don't replace using the app yourself; they change what your hands-on time is *for*. Standard vocabulary, mapped to what you're doing:

- **Manual testing** — a human operating the app and judging the results. Two flavors:
  - **Scripted manual testing** — following a predefined checklist of steps and expected results (the checklist is a **test script** or **test plan**).
  - **Exploratory testing** — unscripted poking around, following your instincts to find surprises. Time-boxed exploratory work guided by a goal ("try to break the upload feature") is called **session-based testing**, and the goal statement is a **test charter**.
- **Smoke test** — a quick pass over the basics to confirm nothing is obviously on fire. (From hardware: power it on, look for smoke.)
- **Happy path** — the normal, everything-goes-right flow. **Edge cases** are the weird inputs and corner conditions.
- **Acceptance testing / UAT (user acceptance testing)** — the owner verifying the product actually serves the user's need, beyond technical correctness. When you run the quiz the way Kid1 would and judge whether it *feels* right, that's acceptance testing — no automated test can do it.
- **Think-aloud protocol** — narrating what you're doing, expecting, and observing as you go (borrowed from usability research). **Your voice-recording-while-testing workflow is a think-aloud narrated test session** — a genuinely good practice, and ideal input for an agent.
- **Coverage gap analysis** — comparing what your manual session exercised and found against what the automated suite covers, then triaging each finding into: (a) a bug → fix it and *add an automated regression test so it can never silently return*, (b) a UX/design observation → backlog, (c) behavior that's fine but untested → candidate for a new automated test, or (d) already covered → confidence confirmed.

So the full loop you're setting up, in standard terms: **scripted manual test session with think-aloud narration → transcript → agent triage and coverage gap analysis → new regression tests and fixes.** The manual script for math-quiz, with each item pre-tagged as automated-covered or manual-only, lives at `apps/math-quiz/2026-06-12_manual-test-script.md`.
