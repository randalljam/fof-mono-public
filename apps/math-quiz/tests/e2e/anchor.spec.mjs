// E2E for the live anchor page: a fluent learner answers fast (auto-submit, no
// Enter), the page administers the curated single-digit addition plan, draws the
// predictive-mastery conclusion, offers continue/stop, persists the session to a
// per-user SQLite store (IndexedDB) AND a separate per-run .sqlite file, and
// reports the filename + total time. CDN sql.js is routed to the local copy by
// routeCdns so the test is hermetic.
import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { routeCdns, trackPageErrors, clickAnchorGo, stubFolderUsers } from './helpers.mjs';

// A valid (empty) SQLite db, base64'd, so the stubbed latest-user-db load hydrates a real
// cache the page can open on Start. Built with the test's sql.js; the internal-RUN test is
// skipped if sql.js isn't installed (the display/disabled tests don't need it).
let VALID_DB_B64 = '';
let SQL_AVAILABLE = false;
try {
  const initSqlJs = (await import('sql.js')).default;
  const wasmBinary = readFileSync(new URL('../node_modules/sql.js/dist/sql-wasm.wasm', import.meta.url));
  const SQL = await initSqlJs({ wasmBinary });
  const db = new SQL.Database();
  VALID_DB_B64 = Buffer.from(db.export()).toString('base64');   // empty DB -> '' (0 bytes); that's fine for stubs
  db.close();
  SQL_AVAILABLE = true;
} catch { /* sql.js absent */ }

// Two internal lists as the dev server's /api/latest-user-db would return them (ordered 1..N).
const INTERNAL_LISTS = [
  { problem_list_id: 5, list_order: 1, list_name: 'Warm set', retain: 0, times_used: 0, item_count: 2,
    items: [{ item_order: 1, problem_text: '8 + 2', num1: 8, operation: '+', num2: 2 },
            { item_order: 2, problem_text: '3 + 4', num1: 3, operation: '+', num2: 4 }] },
  { problem_list_id: 6, list_order: 2, list_name: 'Next set', retain: 1, times_used: 1, item_count: 1,
    items: [{ item_order: 1, problem_text: '5 + 5', num1: 5, operation: '+', num2: 5 }] },
];
async function stubLatestUserDb(page, problemLists, base64 = VALID_DB_B64, extra = {}) {
  await page.route(/\/api\/latest-user-db/, (route) => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({ ok: true, found: true, filename: 'math-flu_Max_2026-06-19.sqlite',
      sessionCount: 2, problemLists, base64, ...extra }),
  }));
}

async function answerCurrent(page) {
  const text = (await page.textContent('#anchor-problem')) || '';
  const m = text.match(/(-?\d+)\s*\+\s*(-?\d+)/); // addition-only default
  if (!m) throw new Error(`could not parse problem "${text}"`);
  const value = Number(m[1]) + Number(m[2]);
  // Type the digits; auto-submit fires when the length matches — no Enter.
  await page.locator('#anchor-answer').pressSequentially(String(value));
}

// Answer the current addition problem WRONG, with the same digit count as the
// correct answer so auto-submit fires cleanly. Returns the sum + the wrong value.
async function answerWrong(page) {
  const text = (await page.textContent('#anchor-problem')) || '';
  const m = text.match(/(-?\d+)\s*\+\s*(-?\d+)/);
  if (!m) throw new Error(`could not parse problem "${text}"`);
  const sum = Number(m[1]) + Number(m[2]);
  const wrong = sum >= 10 ? (sum < 18 ? sum + 1 : sum - 1) : (sum + 1) % 10; // same digit count, != sum
  await page.locator('#anchor-answer').pressSequentially(String(wrong));
  return { text, sum, wrong };
}

// The flag panel always shows Continue / Continue & insert; "⚑ Flag" reveals the reasons.
async function openFlagReasons(page) {
  await expect(page.locator('#anchor-correct-flag')).toBeVisible();
  await page.click('#anchor-correct-flag');
  await expect(page.locator('#anchor-flag-menu')).toBeVisible();
}

async function runToPrompt(page) {
  await clickAnchorGo(page);
  for (let i = 0; i < 120; i++) {
    if (await page.locator('#anchor-prompt').isVisible()) return;
    await answerCurrent(page);
  }
}

// Every learner name this spec types, so the combobox treats them as known
// and the continue-latest lookup runs (the semantics these tests assert).
const FOLDER_USERS = [
  'Again', 'BigKeys', 'Cert', 'Demo', 'EnterOff', 'EnterOn', 'Fb', 'FirstGuinea',
  'FlagPrev', 'FlagPrevInsert', 'Flagger', 'GoGate', 'InsertBack', 'Kid1',
  'KeepGoing', 'Keypad', 'Keys', 'ListOrdered', 'K2', 'NoFlagContinue',
  'Progress', 'Punker', 'QuitAbandon', 'QuitSave', 'Readout', 'Repeat',
  'SignKeys', 'SkipReason', 'Skipper', 'Staying', 'Struggler', 'Warmup',
  'WarmupSave', 'WrongPause',
];
let pageErrors;
test.beforeEach(async ({ context, page }) => {
  await routeCdns(context);
  await stubFolderUsers(context, FOLDER_USERS);
  pageErrors = trackPageErrors(page);
});
test.afterEach(() => { expect(pageErrors).toEqual([]); });

async function enterNumber(page, n) {
  for (const d of String(n)) await page.click(`#anchor-keypad button[data-key="${d}"]`);
}
async function chooseProblemList(page, listName) {
  // Wait for the specific .txt option to be discovered (robust to the static "Use internal"
  // option, which is present from load and would satisfy a bare options.length > 1 poll).
  await expect.poll(
    async () => page.evaluate((wanted) => {
      const sel = document.getElementById('anchor-problem-list-file');
      return sel ? [...sel.options].some((opt) => opt.textContent.includes(wanted)) : false;
    }, listName),
    { timeout: 15_000 }
  ).toBe(true);
  const value = await page.evaluate((wanted) => {
    const sel = document.getElementById('anchor-problem-list-file');
    const option = [...sel.options].find((opt) => opt.textContent.includes(wanted));
    return option ? option.value : null;
  }, listName);
  expect(value).toBeTruthy();
  await page.selectOption('#anchor-problem-list-file', value);
}

test('warm-up: practice the fixed numbers, then Ready to start quiz', async ({ page }) => {
  await page.goto('/anchor.html?setup=1&fb=0&practice=1');
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'Warmup');
  await page.keyboard.press('Escape');
  await page.click('#anchor-start');
  await expect(page.locator('#anchor-progress')).toContainText('Warm-up');
  for (const n of [3, 8, 6, 12, 19, 15]) {            // round 1 is fixed
    await expect(page.locator('#anchor-problem')).toHaveText(String(n));
    await enterNumber(page, n);
  }
  await expect(page.locator('#anchor-practice-done')).toBeVisible();
  await page.click('#anchor-practice-ready');
  await clickAnchorGo(page);
  await expect(page.locator('#anchor-problem')).toHaveText(/\d\s*\+\s*\d/); // quiz now
});

test('warm-up entries are persisted (separately from problems)', async ({ page }) => {
  page.on('dialog', (d) => d.accept()); // for Quit & save confirm
  await page.goto('/anchor.html?setup=1&fb=0&practice=1');
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'WarmupSave');
  await page.keyboard.press('Escape');
  await page.click('#anchor-start');
  await expect(page.locator('#anchor-progress')).toContainText('Warm-up');
  for (const n of [3, 8, 6, 12, 19, 15]) { await enterNumber(page, n); } // 6 warm-up entries
  await expect(page.locator('#anchor-practice-done')).toBeVisible();
  await page.click('#anchor-practice-ready');
  await clickAnchorGo(page);
  await expect(page.locator('#anchor-problem')).toHaveText(/\d\s*\+\s*\d/);
  await page.click('#anchor-quit-save'); // finalize → persists warm-up + session
  await expect(page.locator('#anchor-summary')).toBeVisible();
  const warmups = await page.evaluate(() => globalThis.__anchorStore.warmupCount());
  expect(warmups).toBe(6);
});

test('problem-list controls load files and defaults stay one replicate + randomize off', async ({ page }) => {
  await page.goto('/anchor.html?setup=1&fb=0&practice=0');
  await expect.poll(
    async () => page.evaluate(() => document.querySelectorAll('#anchor-problem-list-file option').length),
    { timeout: 15_000 }
  ).toBeGreaterThan(1);
  await expect(page.locator('#anchor-problem-list-replicates')).toHaveValue('1');
  await expect(page.locator('#anchor-problem-list-randomize')).not.toBeChecked();
  await expect(page.locator('#anchor-problem-list-status')).toContainText('Found');
});

test('problem-list mode honors file order and replicates when randomize is off', async ({ page }) => {
  await page.goto('/anchor.html?setup=1&fb=0&practice=0');
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'ListOrdered');
  await page.keyboard.press('Escape');
  await chooseProblemList(page, '2026-06-18_addition_28problems.txt');
  await page.selectOption('#anchor-problem-list-replicates', '2');
  await page.uncheck('#anchor-problem-list-randomize');
  await page.click('#anchor-start');
  await clickAnchorGo(page);
  await expect(page.locator('#anchor-order')).toHaveText('external list');   // randomize off
  await expect(page.locator('#anchor-progress')).toHaveText('0 of 56 answered · 0% complete'); // 28 × 2 replicates

  const config = await page.evaluate(() => {
    const cfg = globalThis.__anchorProblemListConfig && globalThis.__anchorProblemListConfig();
    const run = globalThis.__anchorRun && globalThis.__anchorRun();
    return {
      source: cfg ? cfg.sourceName : null,
      baseCount: cfg ? cfg.baseCount : null,
      replicates: cfg ? cfg.replicates : null,
      randomize: cfg ? cfg.randomize : null,
      sequenceLength: run ? run.sequence.length : null
    };
  });
  expect(config.source).toBe('2026-06-18_addition_28problems.txt');
  expect(config.baseCount).toBe(28);
  expect(config.replicates).toBe(2);
  expect(config.randomize).toBe(false);
  expect(config.sequenceLength).toBe(56);

  await expect(page.locator('#anchor-problem')).toHaveText(/\s*6\s*\+\s*8\s*/);
  for (let i = 0; i < 28; i++) await answerCurrent(page);
  await expect(page.locator('#anchor-problem')).toHaveText(/\s*6\s*\+\s*8\s*/);
});

test('Go gate: overlay covers the quiz until Go! is tapped; problem slot stays empty', async ({ page }) => {
  await page.goto('/anchor.html?setup=1&fb=0&practice=0');
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'GoGate');
  await page.keyboard.press('Escape');
  await page.click('#anchor-start');
  await expect(page.locator('#anchor-go-overlay')).toBeVisible({ timeout: 30_000 });
  await expect(page.locator('#anchor-problem')).toHaveText('');
  await expect(page.locator('#anchor-keypad button[data-key="5"]')).toBeVisible();
  await clickAnchorGo(page);
  await expect(page.locator('#anchor-problem')).toHaveText(/\d\s*\+\s*\d/);
});

test('warm-up: Skip to start quiz jumps straight into the quiz', async ({ page }) => {
  await page.goto('/anchor.html?setup=1&fb=0&practice=1');
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'Skipper');
  await page.keyboard.press('Escape');
  await page.click('#anchor-start');
  await expect(page.locator('#anchor-problem')).toHaveText('3'); // first warm-up target
  await page.click('#anchor-practice-skip');
  await clickAnchorGo(page);
  await expect(page.locator('#anchor-problem')).toHaveText(/\d\s*\+\s*\d/); // quiz now
});

test('warm-up: Continue to practice gives another round (random)', async ({ page }) => {
  await page.goto('/anchor.html?setup=1&fb=0&practice=1');
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'KeepGoing');
  await page.keyboard.press('Escape');
  await page.click('#anchor-start');
  for (const n of [3, 8, 6, 12, 19, 15]) { await enterNumber(page, n); }
  await expect(page.locator('#anchor-practice-done')).toBeVisible();
  await page.click('#anchor-practice-continue');
  await expect(page.locator('#anchor-progress')).toContainText('1 of 6'); // a fresh round
});

test('fluent learner reaches the prompt, stops, and the run is saved as a .sqlite file', async ({ page }) => {
  await page.goto('/anchor.html?setup=1&fb=0&practice=0');
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'Demo');
  await page.keyboard.press('Escape');
  await page.click('#anchor-start');
  await runToPrompt(page);

  await expect(page.locator('#anchor-prompt')).toBeVisible({ timeout: 30_000 });
  await expect(page.locator('#anchor-prompt-text')).toContainText('fluent');
  await expect(page.locator('#anchor-prompt-text')).toContainText('%');

  await page.click('#anchor-stop');
  await expect(page.locator('#anchor-summary')).toBeVisible();
  await expect(page.locator('#anchor-summary-title')).toContainText('Fluent');
  await expect(page.locator('#anchor-summary-body')).toContainText('Total time');
  // No dev server in this static-server e2e: the session is saved to the browser store and
  // the page notes it could not be written to disk (the dev server writes the .sqlite files).
  await expect(page.locator('#anchor-upload')).toContainText('Could not reach the dev server', { timeout: 10_000 });

  const sessions = await page.evaluate(() => globalThis.__anchorStore.sessionCount());
  expect(sessions).toBe(1);

  // Every recorded attempt carries an ISO presented_at timestamp (captured at render).
  const presented = await page.evaluate(() => {
    const r = globalThis.__anchorStore.db.exec('SELECT presented_at FROM ProblemAttempts');
    return r.length ? r[0].values.map((v) => v[0]) : [];
  });
  expect(presented.length).toBeGreaterThan(0);
  expect(presented.every((t) => typeof t === 'string' && /^\d{4}-\d\d-\d\dT/.test(t))).toBe(true);
});

test('the default keypad has no big number keys and answers via digit keys', async ({ page }) => {
  await page.goto('/anchor.html?setup=1&fb=0&practice=0');
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'Keypad');
  await page.keyboard.press('Escape');
  await page.click('#anchor-start');
  await clickAnchorGo(page);
  // big number keys hidden by default
  await expect(page.locator('#anchor-keypad button[data-key="17"]')).toHaveCount(0);

  for (let i = 0; i < 120; i++) {
    if (await page.locator('#anchor-prompt').isVisible()) break;
    const m = ((await page.textContent('#anchor-problem')) || '').match(/(-?\d+)\s*\+\s*(-?\d+)/);
    const value = Number(m[1]) + Number(m[2]);
    for (const d of String(value)) await page.click(`#anchor-keypad button[data-key="${d}"]`); // two presses for two digits
  }
  await expect(page.locator('#anchor-prompt-text')).toContainText('fluent');
});

test('big number keys can be enabled and single-press a two-digit sum', async ({ page }) => {
  await page.goto('/anchor.html?setup=1&fb=0&practice=0&bigkeys=1');
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'BigKeys');
  await page.keyboard.press('Escape');
  await page.click('#anchor-start');
  await expect(page.locator('#anchor-keypad button[data-key="17"]')).toBeVisible({ timeout: 30_000 });
  await clickAnchorGo(page);

  for (let i = 0; i < 120; i++) {
    if (await page.locator('#anchor-prompt').isVisible()) break;
    const m = ((await page.textContent('#anchor-problem')) || '').match(/(-?\d+)\s*\+\s*(-?\d+)/);
    const value = Number(m[1]) + Number(m[2]);
    if (value >= 10 && value <= 21) await page.click(`#anchor-keypad button[data-key="${value}"]`); // single press
    else for (const d of String(value)) await page.click(`#anchor-keypad button[data-key="${d}"]`);
  }
  await expect(page.locator('#anchor-prompt-text')).toContainText('fluent');
});

test('the keypad has ±/0/C on the bottom row and no Enter key', async ({ page }) => {
  await page.goto('/anchor.html?setup=1&fb=0&practice=0');
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'Keys');
  await page.keyboard.press('Escape');
  await page.click('#anchor-start');
  await clickAnchorGo(page);
  await expect(page.locator('#anchor-keypad button[data-key="negate"]')).toHaveText('±');
  await expect(page.locator('#anchor-keypad button[data-key="clear"]')).toHaveText('C');
  await expect(page.locator('#anchor-keypad button[data-key="enter"]')).toHaveCount(0);
});

test('± toggles the negative sign and C clears the entry', async ({ page }) => {
  await page.goto('/anchor.html?setup=1&fb=0&practice=0');
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'SignKeys');
  await page.keyboard.press('Escape');
  await page.uncheck('#anchor-autosubmit');   // off so digits don't auto-submit mid-entry
  await page.click('#anchor-start');
  await clickAnchorGo(page);
  await page.click('#anchor-keypad button[data-key="5"]');
  await expect(page.locator('#anchor-answer')).toHaveValue('5');
  await page.click('#anchor-keypad button[data-key="negate"]');
  await expect(page.locator('#anchor-answer')).toHaveValue('-5');
  await page.click('#anchor-keypad button[data-key="negate"]');   // toggles back
  await expect(page.locator('#anchor-answer')).toHaveValue('5');
  await page.click('#anchor-keypad button[data-key="clear"]');    // erases everything
  await expect(page.locator('#anchor-answer')).toHaveValue('');
});

test('the Enter button shows only when auto-submit is off and submits the answer', async ({ page }) => {
  // Auto-submit on (default): Enter button stays hidden.
  await page.goto('/anchor.html?setup=1&fb=0&practice=0');
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'EnterOn');
  await page.keyboard.press('Escape');
  await page.click('#anchor-start');
  await clickAnchorGo(page);
  await expect(page.locator('#anchor-enter')).toBeHidden();

  // Auto-submit off: the Enter button appears and submits the typed answer.
  await page.goto('/anchor.html?setup=1&fb=0&practice=0');
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'EnterOff');
  await page.keyboard.press('Escape');
  await page.uncheck('#anchor-autosubmit');
  await page.click('#anchor-start');
  await clickAnchorGo(page);
  await expect(page.locator('#anchor-enter')).toBeVisible();
  const first = (await page.textContent('#anchor-problem')) || '';
  const m = first.match(/(-?\d+)\s*\+\s*(-?\d+)/);
  const value = Number(m[1]) + Number(m[2]);
  for (const d of String(value)) await page.click(`#anchor-keypad button[data-key="${d}"]`);
  await expect(page.locator('#anchor-answer')).toHaveValue(String(value));   // not auto-submitted yet
  await page.click('#anchor-enter');
  await expect(page.locator('#anchor-answer')).toHaveValue('', { timeout: 30_000 });   // submitted -> next problem (box reset)
});

test('Continue to 100% certifies a fluent learner', async ({ page }) => {
  await page.goto('/anchor.html?setup=1&fb=0&practice=0');
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'Cert');
  await page.keyboard.press('Escape');
  await page.click('#anchor-start');
  await runToPrompt(page);
  await page.click('#anchor-continue');
  for (let i = 0; i < 200; i++) {
    if (await page.locator('#anchor-summary').isVisible()) break;
    await answerCurrent(page);
  }
  await expect(page.locator('#anchor-summary')).toBeVisible({ timeout: 30_000 });
  await expect(page.locator('#anchor-summary-title')).toContainText('certified');
});

test('guardrail: being wrong on several easy facts prompts to end the session', async ({ page }) => {
  await page.goto('/anchor.html?setup=1&fb=0&practice=0&guardrail=1&correct=0'); // guardrail defaults OFF; enable it. correct=0: skip the wrong-answer correction pause
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'Punker');
  await page.keyboard.press('Escape');
  await page.click('#anchor-start');
  await clickAnchorGo(page);

  // Answer easy facts (max operand <= 5) WRONG, hard facts correct. Several wrong
  // easy facts is the "something's off" pattern the guardrail watches for.
  for (let i = 0; i < 80; i++) {
    if (await page.locator('#anchor-guardrail').isVisible()) break;
    if (await page.locator('#anchor-summary').isVisible()) break;
    const m = ((await page.textContent('#anchor-problem')) || '').match(/(-?\d+)\s*\+\s*(-?\d+)/);
    const a = Number(m[1]), b = Number(m[2]);
    const value = Math.max(a, b) <= 5 ? a + b + 1 : a + b; // wrong on easy, correct on hard
    await page.locator('#anchor-answer').pressSequentially(String(value));
  }
  await expect(page.locator('#anchor-guardrail')).toBeVisible({ timeout: 30_000 });
  await expect(page.locator('#anchor-guardrail-text')).toContainText('Something looks off');

  await page.click('#anchor-guardrail-end');
  await expect(page.locator('#anchor-summary-title')).toContainText('unusual pattern');
});

test('auto-revert: struggling on hard-first flips the order to EF (indicator updates)', async ({ page }) => {
  await page.goto('/anchor.html?setup=1&fb=0&practice=0&correct=0'); // HF + auto-revert default-on; correct=0 skips the wrong-answer pause
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'Struggler');
  await page.keyboard.press('Escape');
  await page.click('#anchor-start');
  await clickAnchorGo(page);
  await expect(page.locator('#anchor-order')).toHaveText('HF');

  // Get several (hard-first) facts wrong → struggle → revert to easy-first.
  for (let i = 0; i < 3; i++) {
    const m = ((await page.textContent('#anchor-problem')) || '').match(/(-?\d+)\s*\+\s*(-?\d+)/);
    await page.locator('#anchor-answer').pressSequentially(String(Number(m[1]) + Number(m[2]) + 1)); // wrong
  }
  await expect(page.locator('#anchor-order')).toContainText('EF'); // 'HF→EF' then 'EF'
});

test('Skip & flag: NA answer, correct-answer shown, defaults to "skip - no reason", Continue advances', async ({ page }) => {
  await page.goto('/anchor.html?setup=1&fb=0&practice=0');
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'FirstGuinea');
  await page.keyboard.press('Escape');
  await page.click('#anchor-start');
  await clickAnchorGo(page);

  const first = await page.textContent('#anchor-problem');
  await page.click('#anchor-skip-flag');
  // The flag panel pops up like a wrong answer: correct answer shown, reasons open with the
  // default "Skip - no reason" pre-checked, Continue / Continue & insert available.
  await expect(page.locator('#anchor-correction')).toBeVisible();
  await expect(page.locator('#anchor-correction-answer')).toContainText('Correct answer:');
  await expect(page.locator('#anchor-flag-menu')).toBeVisible();
  await expect(page.locator('#anchor-flag-reasons input[value="skip-noreason"]')).toBeChecked();
  await page.click('#anchor-correct-continue');
  await expect(page.locator('#anchor-correction')).toBeHidden();
  await expect(page.locator('#anchor-problem')).not.toHaveText(first || ''); // advanced

  const skips = await page.evaluate(() =>
    globalThis.__anchorSession().filter((p) => (p.flags || []).some((f) => f.reason === 'skip-noreason')));
  expect(skips.length).toBe(1);
  expect(skips[0].is_correct).toBe(false);
  expect(skips[0].user_answer).toBe(null);              // NA — no answer entered
  expect(skips[0].user_answer_string).toBe('');
  expect(skips[0].flags[0].label).toBe('Skip - no reason');
});

test('Skip & flag: choosing a reason replaces the default', async ({ page }) => {
  await page.goto('/anchor.html?setup=1&fb=0&practice=0');
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'SkipReason');
  await page.keyboard.press('Escape');
  await page.click('#anchor-start');
  await clickAnchorGo(page);
  await page.click('#anchor-skip-flag');
  await page.uncheck('#anchor-flag-reasons input[value="skip-noreason"]');
  await page.check('#anchor-flag-reasons input[value="interrupted"]');
  await page.click('#anchor-correct-continue');
  const flags = await page.evaluate(() => globalThis.__anchorSession()[0].flags.map((f) => f.reason));
  expect(flags).toEqual(['interrupted']);
});

test('Flag previous rewinds the display to the prior problem, then returns to the current one', async ({ page }) => {
  await page.goto('/anchor.html?setup=1&fb=0&practice=0');
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'FlagPrev');
  await page.keyboard.press('Escape');
  await page.click('#anchor-start');
  await clickAnchorGo(page);

  const prior = await page.textContent('#anchor-problem');   // problem #1
  const pm = (prior || '').match(/(-?\d+)\s*\+\s*(-?\d+)/);
  const priorSum = Number(pm[1]) + Number(pm[2]);
  await answerCurrent(page);                                  // answer #1 correctly
  const current = await page.textContent('#anchor-problem');  // problem #2 now on screen

  await page.click('#anchor-flag-previous');
  // The DISPLAY rewinds to the prior problem and the answer that was entered for it.
  await expect(page.locator('#anchor-problem')).toHaveText(prior || '');
  await expect(page.locator('#anchor-answer')).toHaveValue(String(priorSum));
  await expect(page.locator('#anchor-correction')).toBeVisible();
  await expect(page.locator('#anchor-flag-menu')).toBeVisible();
  await page.check('#anchor-flag-reasons input[value="distracted"]');
  await page.click('#anchor-correct-continue');
  // Back on the SAME current problem (#2) — Flag previous does not advance.
  await expect(page.locator('#anchor-correction')).toBeHidden();
  await expect(page.locator('#anchor-problem')).toHaveText(current || '');
  await expect(page.locator('#anchor-answer')).toHaveValue('');   // re-presented fresh

  const flagged = await page.evaluate(() =>
    globalThis.__anchorSession().filter((p) => (p.flags || []).some((f) => f.reason === 'distracted')));
  expect(flagged.length).toBe(1);                      // the PRIOR problem got the flag
  expect(flagged[0].is_correct).toBe(true);            // it was answered correctly
});

test('Flag previous & insert re-asks the prior fact later, keeping the current one next', async ({ page }) => {
  await page.goto('/anchor.html?setup=1&fb=0&practice=0');
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'FlagPrevInsert');
  await page.keyboard.press('Escape');
  await page.click('#anchor-start');
  await clickAnchorGo(page);

  const prior = await page.textContent('#anchor-problem'); // problem #1
  await answerCurrent(page);
  const current = await page.textContent('#anchor-problem'); // #2 on screen
  await page.click('#anchor-flag-previous');
  await expect(page.locator('#anchor-problem')).toHaveText(prior || '');   // rewound to #1
  await page.click('#anchor-correct-insert');          // re-ask #1's fact later
  await expect(page.locator('#anchor-problem')).toHaveText(current || ''); // back on #2

  let reappeared = false;
  for (let i = 0; i < 8; i++) {
    if (await page.locator('#anchor-prompt').isVisible()) break;
    if ((await page.textContent('#anchor-problem')) === prior) { reappeared = true; break; }
    await answerCurrent(page);
  }
  expect(reappeared).toBe(true);
});

test('progress reads "N of M answered · X% complete" and auto mode shows HF/EF', async ({ page }) => {
  await page.goto('/anchor.html?setup=1&fb=0&practice=0');
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'Progress');
  await page.keyboard.press('Escape');
  await page.click('#anchor-start');
  await clickAnchorGo(page);
  await expect(page.locator('#anchor-progress')).toHaveText(/^0 of \d+ answered · 0% complete$/);
  await expect(page.locator('#anchor-order')).toHaveText(/^(HF|EF)$/);
  await answerCurrent(page);
  await expect(page.locator('#anchor-progress')).toHaveText(/^1 of \d+ answered · \d+% complete$/);
});

test('Quit & save ends early and stores the partial run', async ({ page }) => {
  page.on('dialog', (d) => d.accept()); // confirm "are you sure?"
  await page.goto('/anchor.html?setup=1&fb=0&practice=0');
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'QuitSave');
  await page.keyboard.press('Escape');
  await page.click('#anchor-start');
  await clickAnchorGo(page);
  for (let i = 0; i < 5; i++) await answerCurrent(page); // a few problems, then bail
  await page.click('#anchor-quit-save');
  await expect(page.locator('#anchor-summary-title')).toContainText('Saved');
  const sessions = await page.evaluate(() => globalThis.__anchorStore.sessionCount());
  expect(sessions).toBe(1);
});

test('cancelling the quit confirmation keeps the run going', async ({ page }) => {
  page.on('dialog', (d) => d.dismiss()); // say "no" to "are you sure?"
  await page.goto('/anchor.html?setup=1&fb=0&practice=0');
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'Staying');
  await page.keyboard.press('Escape');
  await page.click('#anchor-start');
  await clickAnchorGo(page);
  await page.click('#anchor-quit-save');
  await expect(page.locator('#anchor-quiz')).toBeVisible();    // still in the quiz
  await expect(page.locator('#anchor-summary')).toBeHidden();
});

test('Quit & abandon ends without saving', async ({ page }) => {
  page.on('dialog', (d) => d.accept()); // confirm "are you sure?"
  await page.goto('/anchor.html?setup=1&fb=0&practice=0');
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'QuitAbandon');
  await page.keyboard.press('Escape');
  await page.click('#anchor-start');
  await clickAnchorGo(page);
  for (let i = 0; i < 3; i++) await answerCurrent(page);
  await page.click('#anchor-quit-abandon');
  await expect(page.locator('#anchor-summary-title')).toContainText('Abandoned');
  const sessions = await page.evaluate(() => globalThis.__anchorStore.sessionCount());
  expect(sessions).toBe(0); // nothing saved
});

test('auto-entry shows the full entered number and a green check', async ({ page }) => {
  await page.goto('/anchor.html?setup=1&fb=1500&practice=0'); // long feedback window so it's assertable
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'Fb');
  await page.keyboard.press('Escape');
  await page.click('#anchor-start');
  await clickAnchorGo(page);
  await expect(page.locator('#anchor-correction')).toBeHidden(); // no flag panel while answering
  const m = ((await page.textContent('#anchor-problem')) || '').match(/(-?\d+)\s*\+\s*(-?\d+)/);
  const value = Number(m[1]) + Number(m[2]);
  for (const d of String(value)) await page.click(`#anchor-keypad button[data-key="${d}"]`);
  // within the feedback window: the full number stays visible and a green ✓ shows
  await expect(page.locator('#anchor-answer')).toHaveValue(String(value));
  await expect(page.locator('#anchor-feedback')).toHaveText('✓');
  await expect(page.locator('#anchor-feedback')).toHaveClass(/correct/);
  await expect(page.locator('#anchor-correction')).toBeHidden(); // a correct answer shows no panel
});

test('wrong answer pauses on the correct answer with three choices; Continue advances', async ({ page }) => {
  await page.goto('/anchor.html?setup=1&fb=0&practice=0'); // correction flow ON by default
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'WrongPause');
  await page.keyboard.press('Escape');
  await page.click('#anchor-start');
  await clickAnchorGo(page);

  const first = await page.textContent('#anchor-problem');
  const { sum, wrong } = await answerWrong(page);

  await expect(page.locator('#anchor-correction')).toBeVisible();
  await expect(page.locator('#anchor-feedback')).toHaveText('');
  await expect(page.locator('#anchor-correction-answer')).toContainText(`Correct answer: ${sum}`);
  await expect(page.locator('#anchor-answer')).toHaveValue(String(wrong)); // entered answer stays in the box
  // Continue / Continue & insert are available immediately; the reasons sit behind ⚑ Flag.
  await expect(page.locator('#anchor-correct-continue')).toBeVisible();
  await expect(page.locator('#anchor-correct-insert')).toBeVisible();
  await expect(page.locator('#anchor-flag-menu')).toBeHidden();

  await page.click('#anchor-correct-continue');     // proceed without re-inserting
  await expect(page.locator('#anchor-correction')).toBeHidden();
  await expect(page.locator('#anchor-problem')).not.toHaveText(first || '');
});

test('Continue & insert re-asks the missed fact about five problems later', async ({ page }) => {
  await page.goto('/anchor.html?setup=1&fb=0&practice=0');
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'InsertBack');
  await page.keyboard.press('Escape');
  await page.click('#anchor-start');
  await clickAnchorGo(page);

  const missed = await page.textContent('#anchor-problem');
  await answerWrong(page);
  await expect(page.locator('#anchor-correction')).toBeVisible();
  await page.click('#anchor-correct-insert');       // re-insert this fact ~5 problems later
  await expect(page.locator('#anchor-correction')).toBeHidden();

  let reappeared = false;
  for (let i = 0; i < 8; i++) {
    if (await page.locator('#anchor-prompt').isVisible()) break;
    if ((await page.textContent('#anchor-problem')) === missed) { reappeared = true; break; }
    await answerCurrent(page);                       // answer the in-between problems correctly
  }
  expect(reappeared).toBe(true);
});

test('Flag opens the reason menu and records the flag on the problem', async ({ page }) => {
  await page.goto('/anchor.html?setup=1&fb=0&practice=0');
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'Flagger');
  await page.keyboard.press('Escape');
  await page.click('#anchor-start');
  await clickAnchorGo(page);

  await answerWrong(page);
  await expect(page.locator('#anchor-correction')).toBeVisible();
  await expect(page.locator('#anchor-flag-menu')).toBeHidden();

  await openFlagReasons(page);                       // reveal the reason checkboxes
  await expect(page.locator('#anchor-correct-continue')).toBeVisible();
  await page.check('#anchor-flag-reasons input[value="distracted"]');
  await page.fill('#anchor-flag-comment', 'phone rang');

  // After flagging the user still has to choose Continue / Continue & insert.
  await expect(page.locator('#anchor-correction')).toBeVisible();
  await page.click('#anchor-correct-continue');

  const flagged = await page.evaluate(() =>
    globalThis.__anchorSession().filter((p) => (p.flags || []).some((f) => f && f.reason === 'distracted')));
  expect(flagged.length).toBe(1);
  expect(flagged[0].flags[0].notes).toBe('phone rang');
  expect(flagged[0].flags[0].label).toBe('Distracted');
});

test('Continue with open flag menu and no changes leaves the problem unflagged', async ({ page }) => {
  await page.goto('/anchor.html?setup=1&fb=0&practice=0');
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'NoFlagContinue');
  await page.keyboard.press('Escape');
  await page.click('#anchor-start');
  await clickAnchorGo(page);

  await answerWrong(page);
  await openFlagReasons(page);
  await expect(page.locator('#anchor-correct-continue')).toBeVisible();
  await page.click('#anchor-correct-continue');

  const flagged = await page.evaluate(() =>
    globalThis.__anchorSession().filter((p) => (p.flags || []).length > 0));
  expect(flagged.length).toBe(0);
});

test('a returning user loads prior history from IndexedDB', async ({ page }) => {
  await page.goto('/anchor.html?setup=1&fb=0&practice=0');
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'Repeat');
  await page.keyboard.press('Escape');
  await page.click('#anchor-start');
  await runToPrompt(page);
  await page.click('#anchor-stop');
  await expect(page.locator('#anchor-summary')).toBeVisible();

  // Reload (same browser context → IndexedDB persists) and start again.
  await page.goto('/anchor.html?setup=1&fb=0&practice=0');
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'Repeat');
  await page.keyboard.press('Escape');
  await page.click('#anchor-start');
  await clickAnchorGo(page);
  const priorSessions = await page.evaluate(() => globalThis.__anchorStore.sessionCount());
  expect(priorSessions).toBeGreaterThanOrEqual(1);
});

test('"Load for analysis" is hidden until the run is saved, then opens the accumulated file', async ({ page, context }) => {
  await page.route(/\/api\/health/, (route) =>
    route.fulfill({ contentType: 'application/json', body: JSON.stringify({ ok: true }) }));
  await page.route(/\/api\/save-run/, (route) => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({
      ok: true, action: 'append', sourceFolder: 'tlkids', destination: 'source',
      filename: 'math-flu_K1_2026-06-17.sqlite',
      localPath: '/x/_data/tlkids/math-flu_K1_2026-06-17.sqlite',
      singleSessionPath: '/x/_data/_single-session-sqlite-files/math-flu_K1_2026-06-20_103814.sqlite',
    }),
  }));
  await page.goto('/anchor.html?setup=1&fb=0&practice=0');
  await page.fill('#anchor-source-folder', 'tlkids');
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'Kid1');
  await page.keyboard.press('Escape');
  await expect(page.locator('#anchor-dev-tools')).toBeHidden();
  await page.click('#anchor-start');
  await runToPrompt(page);
  await expect(page.locator('#anchor-dev-tools')).toBeHidden();
  await page.click('#anchor-stop');
  await expect(page.locator('#anchor-summary')).toBeVisible();
  await expect(page.locator('#anchor-dev-tools')).toBeVisible({ timeout: 10_000 });
  const [popup] = await Promise.all([
    context.waitForEvent('page'),
    page.click('#anchor-load-analysis'),
  ]);
  const url = popup.url();
  expect(url).toContain('math_analysis.html');
  expect(url).toContain('folder=tlkids');
  expect(url).toContain('user=Kid1');
  expect(url).toContain('file=math-flu_K1_2026-06-17.sqlite');
  await popup.close();
});

test('internal lists: the file box renders the stored lists, top flagged "runs next"', async ({ page }) => {
  await stubLatestUserDb(page, INTERNAL_LISTS);
  await page.goto('/anchor.html?setup=1&fb=0&practice=0');
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'K2');
  await page.keyboard.press('Escape');
  await page.locator('#anchor-username').blur();
  const box = page.locator('#anchor-internal-lists');
  await expect(box).toBeVisible();
  await expect(box).toContainText('Internal problem lists in this file (2)');
  await expect(box).toContainText('Warm set');
  await expect(box).toContainText('consume after use');     // retain off
  await expect(box).toContainText('runs next');             // the top of the queue
  await expect(box).toContainText('Next set');
  await expect(box).toContainText('keep');                  // retain on
  // The "Use internal" option is enabled + labeled with the count.
  const opt = page.locator('#anchor-problem-list-file option[value="__internal__"]');
  await expect(opt).toHaveText('Use internal (2 in this file)');
  await expect(opt).not.toBeDisabled();
  await page.selectOption('#anchor-problem-list-file', '__internal__');
  await expect(page.locator('#anchor-problem-list-status')).toContainText('Using internal list #1: Warm set');
});

test('internal lists: "Use internal" runs the top list (its problems, config wired)',
  { skip: VALID_DB_B64 ? false : 'sql.js not installed (run npm install in apps/math-quiz/tests)' },
  async ({ page }) => {
    await stubLatestUserDb(page, INTERNAL_LISTS);
    await page.goto('/anchor.html?setup=1&fb=0&practice=0');
    await page.click('#anchor-username');
  await page.fill('#anchor-username', 'K2');
  await page.keyboard.press('Escape');
    await page.locator('#anchor-username').blur();
    await expect(page.locator('#anchor-internal-lists')).toBeVisible();
    await page.selectOption('#anchor-problem-list-file', '__internal__');  // enables the list controls
    await page.uncheck('#anchor-problem-list-randomize');                  // deterministic: list order
    await page.click('#anchor-start');
    await clickAnchorGo(page);
    const cfg = await page.evaluate(() => globalThis.__anchorProblemListConfig && globalThis.__anchorProblemListConfig());
    expect(cfg.sourceName).toBe('internal #1: Warm set');
    expect(cfg.baseCount).toBe(2);
    expect(cfg.internalProblemListId).toBe(5);
    expect(cfg.sequence.length).toBe(2);
    await expect(page.locator('#anchor-problem')).toHaveText(/\s*8\s*\+\s*2\s*/);   // first list item, order preserved
    await expect(page.locator('#anchor-order')).toHaveText('internal list');         // randomize off
    await expect(page.locator('#anchor-progress')).toHaveText('0 of 2 answered · 0% complete');
  });

// Regression: a fixed list answered SLOWLY must not be re-asked past its length (the bug where
// a 20-problem list asked 21, 22… because slow-but-correct answers triggered glitch re-delivery).
test('internal lists: slow answers do NOT inflate a list past its length',
  { skip: VALID_DB_B64 ? false : 'sql.js not installed (run npm install in apps/math-quiz/tests)' },
  async ({ page }) => {
    await stubLatestUserDb(page, INTERNAL_LISTS);
    await page.goto('/anchor.html?setup=1&fb=0&practice=0');
    await page.click('#anchor-username');
  await page.fill('#anchor-username', 'K2');
  await page.keyboard.press('Escape');
    await page.locator('#anchor-username').blur();
    await expect(page.locator('#anchor-internal-lists')).toBeVisible();
    await page.selectOption('#anchor-problem-list-file', '__internal__');
    await page.uncheck('#anchor-problem-list-randomize');
    await page.selectOption('#anchor-problem-list-replicates', '2');     // 2 facts × 2 = 4 problems
    await page.click('#anchor-start');
    await clickAnchorGo(page);
    await expect(page.locator('#anchor-progress')).toHaveText('0 of 4 answered · 0% complete');
    for (let i = 0; i < 4; i++) {
      await page.waitForTimeout(2100);        // answer SLOWLY (> fastMs) — would queue re-asks before the fix
      await answerCurrent(page);
    }
    // The run ends after exactly the 4 list problems — no glitch re-asks, no "5 of 4".
    await expect(page.locator('#anchor-quiz')).toBeHidden({ timeout: 10_000 });
    expect(await page.evaluate(() => globalThis.__anchorSession().length)).toBe(4);
  });

// Regression: a list run that would trip predictive mastery must NOT show the auto-mode
// continue/stop prompt (fluency feast, internal lists, quick quiz, external lists).
test('internal lists: predictive mastery does NOT show the continue/stop prompt', async ({ page }) => {
    test.skip(!SQL_AVAILABLE, 'sql.js not installed (run npm install in apps/math-quiz/tests)');
    const facts = ['1 + 2', '3 + 4', '5 + 6', '7 + 8', '2 + 3', '4 + 5', '6 + 7', '8 + 9', '1 + 8', '3 + 6'];
    const fluentList = [{
      problem_list_id: 5, list_order: 1, list_name: 'Fluent set', retain: 0, times_used: 0, item_count: facts.length,
      items: facts.map((t, i) => {
        const m = t.match(/(\d+) \+ (\d+)/);
        return { item_order: i + 1, problem_text: t, num1: +m[1], operation: '+', num2: +m[2] };
      }),
    }];
    await stubLatestUserDb(page, fluentList);
    await page.goto('/anchor.html?setup=1&fb=0&practice=0');
    await page.click('#anchor-username');
  await page.fill('#anchor-username', 'K2');
  await page.keyboard.press('Escape');
    await page.locator('#anchor-username').blur();
    await page.selectOption('#anchor-problem-list-file', '__internal__');
    await page.uncheck('#anchor-problem-list-randomize');
    await page.click('#anchor-start');
    await clickAnchorGo(page);
    for (let i = 0; i < facts.length; i++) await answerCurrent(page);   // fast; > warmup discard
    await expect(page.locator('#anchor-prompt')).toBeHidden({ timeout: 10_000 });
    await expect(page.locator('#anchor-summary')).toBeVisible();
    await expect(page.locator('#anchor-summary-title')).toContainText('Done');
    await expect(page.locator('#anchor-summary-body')).toContainText('Fluent set');
  });

test('internal lists: option disabled + box hidden when the file has none', async ({ page }) => {
  await stubLatestUserDb(page, []);
  await page.goto('/anchor.html?setup=1&fb=0&practice=0');
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'K2');
  await page.keyboard.press('Escape');
  await page.locator('#anchor-username').blur();
  await expect(page.locator('#anchor-name-status')).toContainText('Continuing');   // file loaded
  await expect(page.locator('#anchor-internal-lists')).toBeHidden();
  const opt = page.locator('#anchor-problem-list-file option[value="__internal__"]');
  await expect(opt).toBeDisabled();
  await expect(opt).toHaveText('Use internal (none in this file)');
});

// ----- problem-list editor (the shared collapsible panel) -----
// An in-memory stub of the dev server's /api/problem-lists (GET view + POST mutations),
// mirroring problem_list_store so the editor can be driven end-to-end without a real server.
async function stubProblemListApi(page, initial) {
  let lists = initial.map((l, i) => ({
    problem_list_id: l.id, list_order: i + 1, list_name: l.name, retain: l.retain ?? 1,
    times_used: l.times_used ?? 0, item_count: l.items.length,
    items: l.items.map((t, j) => ({ item_order: j + 1, problem_text: t, category: 'problem-list' })),
  }));
  let nextId = Math.max(0, ...lists.map((l) => l.problem_list_id)) + 1;
  const parse = (text) => String(text || '').split(/\r?\n/).map((s) => s.trim()).filter(Boolean).map((t, j) => {
    const m = t.match(/(-?\d+)\s*([+\-*])\s*(-?\d+)/);
    if (!m) throw new Error('bad line');
    return { item_order: j + 1, problem_text: `${+m[1]} ${m[2]} ${+m[3]}`, num1: +m[1], operation: m[2], num2: +m[3], category: 'problem-list' };
  });
  const norm = () => { lists.forEach((l, i) => { l.list_order = i + 1; l.item_count = l.items.length; }); };
  await page.route(/\/api\/problem-lists(\?|$)/, async (route) => {
    const req = route.request();
    const send = (obj) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(obj) });
    if (req.method() === 'GET') return send({ ok: true, found: true, file: 'f.sqlite', folder: 'tlkids', user: 'K2', problemLists: lists });
    let p; try { p = JSON.parse(req.postData() || '{}'); } catch { p = {}; }
    const find = (id) => lists.find((l) => l.problem_list_id === Number(id));
    try {
      if (p.action === 'create') lists.push({ problem_list_id: nextId++, list_order: lists.length + 1, list_name: p.listName || 'New list', retain: p.retain === false ? 0 : 1, times_used: 0, items: parse(p.text || '') });
      else if (p.action === 'save-items') { const l = find(p.problemListId); if (l) l.items = parse(p.text || ''); }
      else if (p.action === 'rename') { const l = find(p.problemListId); if (l) l.list_name = p.listName; }
      else if (p.action === 'set-retain') { const l = find(p.problemListId); if (l) l.retain = p.retain ? 1 : 0; }
      else if (p.action === 'reorder') { const o = p.order.map(Number); lists.sort((a, b) => o.indexOf(a.problem_list_id) - o.indexOf(b.problem_list_id)); }
      else if (p.action === 'delete') lists = lists.filter((l) => l.problem_list_id !== Number(p.problemListId));
    } catch { return send({ ok: false, error: 'bad line', folder: 'tlkids', user: 'K2' }); }
    norm();
    return send({ ok: true, folder: 'tlkids', user: 'K2', file: 'f.sqlite', problemLists: lists });
  });
}
async function openEditor(page, name = 'K2') {
  // The editor opens by default (startOpen); filling + blurring the name refreshes it to that learner.
  await page.click('#anchor-username');
  await page.fill('#anchor-username', name);
  await page.keyboard.press('Escape');
  await page.locator('#anchor-username').blur();
}
const editor = (page) => page.locator('#anchor-problem-list-editor');

test('editor: renders lists left-to-right in queue order with their text', async ({ page }) => {
  await stubProblemListApi(page, [
    { id: 5, name: 'Warm set', retain: 0, items: ['8 + 2', '3 + 4'] },
    { id: 6, name: 'Next set', retain: 1, items: ['5 + 5'] },
  ]);
  await page.goto('/anchor.html?setup=1&fb=0&practice=0');
  await openEditor(page);
  const cards = editor(page).locator('[data-plp="card"]');
  await expect(cards).toHaveCount(2);
  await expect(cards.nth(0).locator('.plp-order')).toHaveText('#1');
  await expect(cards.nth(0).locator('[data-plp="name"]')).toHaveValue('Warm set');
  await expect(cards.nth(0).locator('[data-plp="text"]')).toHaveValue('8 + 2\n3 + 4');
  await expect(cards.nth(1).locator('[data-plp="name"]')).toHaveValue('Next set');
});

test('editor: editing a list textarea auto-saves on blur', async ({ page }) => {
  await stubProblemListApi(page, [{ id: 5, name: 'Warm', retain: 1, items: ['8 + 2'] }]);
  await page.goto('/anchor.html?setup=1&fb=0&practice=0');
  await openEditor(page);
  const card = editor(page).locator('[data-plp="card"]').first();
  await card.locator('[data-plp="text"]').fill('8 + 2\n3 + 4\n6 + 7');
  await card.locator('[data-plp="text"]').blur();   // flush save on blur
  await expect(card.locator('.plp-card-status')).toHaveText(/Saved ✓ \(3 problems\)/);
});

test('editor: reorder, create, and delete update the cards', async ({ page }) => {
  page.on('dialog', (d) => d.accept());   // delete confirm
  await stubProblemListApi(page, [
    { id: 5, name: 'Warm', retain: 1, items: ['8 + 2'] },
    { id: 6, name: 'Next', retain: 1, items: ['5 + 5'] },
  ]);
  await page.goto('/anchor.html?setup=1&fb=0&practice=0');
  await openEditor(page);
  const cards = editor(page).locator('[data-plp="card"]');
  // Move the first card later -> "Next" becomes #1.
  await cards.nth(0).locator('[data-plp="right"]').click();
  await expect(cards.nth(0).locator('[data-plp="name"]')).toHaveValue('Next');
  // New list -> a third card appears.
  await editor(page).locator('[data-plp="new"]').click();
  await expect(cards).toHaveCount(3);
  // Delete the first card -> back to two.
  await cards.nth(0).locator('[data-plp="delete"]').click();
  await expect(cards).toHaveCount(2);
});

test('editor: the generator adds a list of the requested size', async ({ page }) => {
  await stubProblemListApi(page, [{ id: 5, name: 'Seed', retain: 1, items: ['1 + 1'] }]);
  await page.goto('/anchor.html?setup=1&fb=0&practice=0');
  await openEditor(page);
  await editor(page).locator('[data-plp="gen-cat"]').click();          // open the by-category form
  await editor(page).locator('[data-plp="gen-count"]').fill('8');
  await editor(page).locator('[data-plp="gen-add"]').click();          // add generated list (appended)
  const cards = editor(page).locator('[data-plp="card"]');
  await expect(cards).toHaveCount(2);
  // Position defaults to "Add as first", so the generated "Category" list is now card #1.
  await expect(cards.nth(0).locator('[data-plp="name"]')).toHaveValue('Category');
  const lines = (await cards.nth(0).locator('[data-plp="text"]').inputValue()).split('\n').filter(Boolean);
  expect(lines.length).toBe(8);
  expect(lines.every((l) => /^\d+ \+ \d+$/.test(l))).toBe(true);
});

test('editor: shows a hint when no learner is selected', async ({ page }) => {
  await stubProblemListApi(page, []);
  await page.goto('/anchor.html?setup=1&fb=0&practice=0');
  // Editor is open by default; with no learner picked it shows the hint and disables actions.
  await expect(editor(page).locator('.plp-note')).toContainText('Pick a learner');
  await expect(editor(page).locator('[data-plp="new"]')).toBeDisabled();
});

test('editor: creating the first list un-greys "Use internal" without switching users', async ({ page }) => {
  await stubProblemListApi(page, []);          // the file exists but has no internal lists yet
  await page.goto('/anchor.html?setup=1&fb=0&practice=0');
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'K2');
  await page.keyboard.press('Escape');
  const opt = page.locator('#anchor-problem-list-file option[value="__internal__"]');
  await expect(opt).toBeDisabled();            // grayed out: no lists in this file
  await page.locator('#anchor-username').blur();            // refreshes the open editor for K2
  await editor(page).locator('[data-plp="new"]').click();   // create a list
  const card = editor(page).locator('[data-plp="card"]').first();
  await card.locator('[data-plp="text"]').fill('8 + 2\n3 + 4');
  await card.locator('[data-plp="text"]').blur();
  // The bug: the option stayed grayed until a user switch. Now it refreshes immediately.
  await expect(opt).toBeEnabled();
  await expect(opt).toHaveText(/Use internal \(1 in this file\)/);
});

test('editor: Generate by fluency adds a list from the learner\'s history', async ({ page }) => {
  test.skip(!SQL_AVAILABLE, 'sql.js not installed');
  // Build a learner file with a few attempts so the fluency generator has data to classify.
  const initSqlJs = (await import('sql.js')).default;
  const wasmBinary = readFileSync(new URL('../node_modules/sql.js/dist/sql-wasm.wasm', import.meta.url));
  const SQL = await initSqlJs({ wasmBinary });
  const db = new SQL.Database();
  db.run(`CREATE TABLE Sessions (session_id TEXT PRIMARY KEY, user_name TEXT, start_time TEXT);
          CREATE TABLE ProblemAttempts (attempt_id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT,
            problem_text TEXT, is_correct INTEGER, response_time_ms INTEGER, flags_json TEXT);`);
  db.run(`INSERT INTO Sessions VALUES ('s1','K2','2026-06-17_080000')`);
  for (let i = 0; i < 3; i++) db.run(`INSERT INTO ProblemAttempts (session_id, problem_text, is_correct, response_time_ms) VALUES ('s1','2 + 2',1,900)`);
  const b64 = Buffer.from(db.export()).toString('base64');
  db.close();

  await stubProblemListApi(page, []);
  await stubLatestUserDb(page, [], b64);
  await page.goto('/anchor.html?setup=1&fb=0&practice=0');
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'K2');
  await page.keyboard.press('Escape');
  await page.locator('#anchor-username').blur();
  await expect(page.locator('#anchor-name-status')).toContainText('Continuing');   // file cached to IndexedDB

  await editor(page).locator('[data-plp="gen-flu"]').click();                       // by-fluency form
  await editor(page).locator('[data-plp="genf-count"]').fill('6');
  for (const [k, v] of [['fluent', '0'], ['almost', '0'], ['needs-practice', '0'], ['incorrect', '0'], ['missing', '100']]) {
    await editor(page).locator(`[data-flu="${k}"]`).fill(v);
  }
  await editor(page).locator('[data-plp="gen-add"]').click();
  const cards = editor(page).locator('[data-plp="card"]');
  await expect(cards).toHaveCount(1);
  await expect(cards.first().locator('[data-plp="name"]')).toHaveValue('Fluency');
  const lines = (await cards.first().locator('[data-plp="text"]').inputValue()).split('\n').filter(Boolean);
  expect(lines.length).toBe(6);                                                     // 6 unseen addition facts
  expect(lines.every((l) => /^\d+ \+ \d+$/.test(l))).toBe(true);
});

test('Fluency feast: one click builds a no-retain list, adds it first, and runs it', async ({ page }) => {
  test.skip(!SQL_AVAILABLE, 'sql.js not installed');
  const initSqlJs = (await import('sql.js')).default;
  const wasmBinary = readFileSync(new URL('../node_modules/sql.js/dist/sql-wasm.wasm', import.meta.url));
  const SQL = await initSqlJs({ wasmBinary });
  const db = new SQL.Database();
  db.run(`CREATE TABLE Sessions (session_id TEXT PRIMARY KEY, user_name TEXT, start_time TEXT);
          CREATE TABLE ProblemAttempts (attempt_id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT,
            problem_text TEXT, is_correct INTEGER, response_time_ms INTEGER, flags_json TEXT);`);
  db.run(`INSERT INTO Sessions VALUES ('s1','K2','2026-06-17_080000')`);
  for (let i = 0; i < 3; i++) db.run(`INSERT INTO ProblemAttempts (session_id, problem_text, is_correct, response_time_ms) VALUES ('s1','2 + 2',1,900)`);
  const b64 = Buffer.from(db.export()).toString('base64');
  db.close();

  // Capture the create payload (retain + name) and serve an existing list to prove it stays.
  let lastCreate = null;
  let lists = [{ problem_list_id: 5, list_order: 1, list_name: 'Existing', retain: 1, times_used: 0, item_count: 1, items: [{ item_order: 1, problem_text: '8 + 2' }] }];
  let nextId = 100;
  await page.route(/\/api\/problem-lists(\?|$)/, async (route) => {
    const req = route.request();
    const send = (o) => route.fulfill({ contentType: 'application/json', body: JSON.stringify(o) });
    if (req.method() === 'GET') return send({ ok: true, found: true, file: 'f.sqlite', folder: 'tlkids', user: 'K2', problemLists: lists });
    const p = JSON.parse(req.postData() || '{}');
    if (p.action === 'create') {
      lastCreate = p;
      const items = (p.text || '').split('\n').map((t) => t.trim()).filter(Boolean).map((t, i) => ({ item_order: i + 1, problem_text: t }));
      lists = [...lists, { problem_list_id: ++nextId, list_order: lists.length + 1, list_name: p.listName, retain: p.retain ? 1 : 0, item_count: items.length, items }];
    } else if (p.action === 'reorder') {
      const byId = new Map(lists.map((l) => [l.problem_list_id, l]));
      lists = p.order.map((id, i) => ({ ...byId.get(id), list_order: i + 1 }));
    }
    return send({ ok: true, problemLists: lists });
  });
  // The file carries a saved preset (count 8); the feast should use it over the defaults.
  await stubLatestUserDb(page, [], b64, { fluencyFeast: { count: 8, session: { mode: 'all' }, mix: { missing: 100, incorrect: 0, almost: 0, 'needs-practice': 0, fluent: 0 } } });
  await page.route(/\/api\/folder-users/, (route) => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({ ok: true, folder: 'tlkids', users: [
      { name: 'K2', label: 'K2', filename: 'math-flu_K2_2026-06-16.sqlite' },
    ] }),
  }));
  await page.goto('/anchor.html?fb=0&practice=0');     // kid landing (default)
  await page.getByRole('button', { name: 'K2', exact: true }).click();  // pick K2 -> loads + caches the file
  await expect(page.locator('#anchor-kid-modal')).toBeVisible();
  await page.click('#kid-mode-feast');                 // one-click feast
  await clickAnchorGo(page);
  await expect(page.locator('#anchor-problem')).toHaveText(/\d\s*\+\s*\d/);   // the feast run started

  expect(lastCreate).not.toBeNull();
  expect(lastCreate.listName).toBe('Fluency feast');
  expect(lastCreate.retain).toBe(false);               // not kept — removed after the run
  // Saved count 8 + two easy-start warm-ups (FLUENCY_FEAST_EASY_START default on).
  expect(lastCreate.text.split('\n').filter(Boolean).length).toBe(10);
  // The feast list was inserted at the front (reorder put its id first); "Existing" stays.
  expect(lists.map((l) => l.list_name)).toContain('Existing');
  expect(lists[0].list_name).toBe('Fluency feast');
});

test('kid landing: when the local server is down, it says to start the server (not "ask Baba")', async ({ context, page }) => {
  // Replace the suite-wide folder-users stub with a network failure.
  await context.unroute(/\/api\/folder-users/);
  await page.route(/\/api\/folder-users/, (route) => route.abort('failed'));
  await page.goto('/anchor.html?fb=0&practice=0');
  await expect(page.locator('#landing-status')).toContainText('start it');
  await expect(page.locator('#landing-status')).not.toContainText('ask Baba');
});

test('summary "Do another quiz" reloads back to the kid landing', async ({ page }) => {
  page.on('dialog', (d) => d.accept());   // Quit & save confirm
  await page.goto('/anchor.html?setup=1&fb=0&practice=0');
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'Again');
  await page.keyboard.press('Escape');
  await page.click('#anchor-start');
  await clickAnchorGo(page);
  await page.click('#anchor-quit-save');                       // -> summary
  await expect(page.locator('#anchor-summary')).toBeVisible();
  await page.click('#anchor-do-another');                      // reload without ?setup
  await expect(page.locator('#anchor-landing')).toBeVisible({ timeout: 15_000 });
});

test('summary shows the start → end %-fluent readout', async ({ page }) => {
  await page.goto('/anchor.html?setup=1&fb=0&practice=0');
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'Readout');
  await page.keyboard.press('Escape');
  await page.click('#anchor-start');
  await runToPrompt(page);                                     // answer fluently -> prompt
  await page.click('#anchor-stop');                            // -> summary
  await expect(page.locator('#anchor-summary')).toBeVisible();
  const readout = page.locator('#anchor-fluency-readout');
  await expect(readout).toBeVisible();
  // Starts at 0% (fresh learner), ends higher after a fluent run; rendered "Fluent: A% → B%".
  await expect(readout).toHaveText(/Fluent:\s*\d+%\s*→\s*\d+%/);
});

test('setup: "Show % fluent" checkbox reflects the file flag and auto-saves on toggle', async ({ page }) => {
  let lastProfilePost = null;
  await page.route(/\/api\/profile(\?|$)/, async (route) => {
    const req = route.request();
    if (req.method() === 'POST') lastProfilePost = JSON.parse(req.postData() || '{}');
    return route.fulfill({ contentType: 'application/json',
      body: JSON.stringify({ ok: true, profile: { showFluencyPercent: lastProfilePost ? lastProfilePost.showFluencyPercent : true } }) });
  });
  // The loaded file says the readout is OFF -> the checkbox loads unchecked.
  await stubLatestUserDb(page, [], VALID_DB_B64, { profile: { showFluencyPercent: false } });
  await page.goto('/anchor.html?setup=1&fb=0&practice=0');
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'K2');
  await page.keyboard.press('Escape');
  await page.locator('#anchor-username').blur();              // -> refreshNameStatus reads the flag
  await expect(page.locator('#anchor-show-fluency-percent')).not.toBeChecked();
  // Re-checking it auto-saves true back to the file.
  await page.click('#anchor-show-fluency-percent');
  await expect.poll(() => lastProfilePost && lastProfilePost.showFluencyPercent).toBe(true);
  expect(lastProfilePost.user).toBe('K2');
});
