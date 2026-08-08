// E2E for the analysis page's SQLite "one-DB-per-person" flow (bridging the old
// JSON analysis to the new anchor SQLite format):
//   - load a single .sqlite locally -> its session appears, user locks to that person
//   - flag a problem in the list view -> Save to person's file writes
//     math-flu_<user>_<date>.sqlite with the flag included (the raw file is never touched)
//   - load a second raw file -> it replaces the first (only the new file's sessions remain)
//   - the loaded data is retained across a page reload (IndexedDB)
// Hermetic: CDN sql.js/Plotly are routed to local copies by routeCdns.
import { test, expect } from '@playwright/test';
import { routeCdns, trackPageErrors } from './helpers.mjs';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const require = createRequire(import.meta.url);
let SQL;
test.beforeAll(async () => {
  const initSqlJs = require('sql.js');
  SQL = await initSqlJs({ wasmBinary: fs.readFileSync(require.resolve('sql.js/dist/sql-wasm.wasm')) });
});

// Mirrors math_utils.js createTables (the schema the anchor writes).
const SCHEMA = `
  CREATE TABLE IF NOT EXISTS Users (name TEXT PRIMARY KEY);
  CREATE TABLE IF NOT EXISTS Sessions (session_id TEXT PRIMARY KEY, session_filename TEXT, user_name TEXT,
    start_time TEXT, end_time TEXT, num_problems INTEGER, number_range_start INTEGER, number_range_end INTEGER,
    numbers_include TEXT, numbers_exclude TEXT, num_numbers INTEGER, operations TEXT,
    total_problems INTEGER, correct_answers INTEGER, average_response_time_ms INTEGER);
  CREATE TABLE IF NOT EXISTS ProblemAttempts (attempt_id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT,
    problem_id TEXT, problem_text TEXT, num1 INTEGER, num2 INTEGER, operation TEXT, correct_answer REAL,
    user_answer_string TEXT, user_answer REAL, is_correct INTEGER, response_time_ms INTEGER, flags_json TEXT,
    presented_at TEXT);
`;

// Write a per-session .sqlite fixture to a temp path; returns the path.
function makeSqliteFixture({ name, user, sessionId, startTime, problems }) {
  const db = new SQL.Database();
  db.run(SCHEMA);
  db.run('INSERT OR IGNORE INTO Users (name) VALUES (?)', [user]);
  db.run(`INSERT INTO Sessions (session_id, session_filename, user_name, start_time, operations, total_problems, correct_answers)
          VALUES (?, ?, ?, ?, ?, ?, ?)`,
    [sessionId, name, user, startTime, '["+"]', problems.length, problems.filter((p) => p.ok).length]);
  problems.forEach((p, i) => {
    db.run(`INSERT INTO ProblemAttempts (session_id, problem_id, problem_text, num1, num2, operation,
              correct_answer, user_answer_string, user_answer, is_correct, response_time_ms, flags_json, presented_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [sessionId, `p${i}`, `${p.a} + ${p.b}`, p.a, p.b, '+', p.a + p.b,
        String(p.a + p.b), p.a + p.b, p.ok ? 1 : 0, p.ms, null, p.at ?? null]);
  });
  const bytes = db.export();
  db.close();
  // Unique dir per fixture so parallel workers never read/write the same path.
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'mq-fixture-'));
  const file = path.join(dir, name);
  fs.writeFileSync(file, Buffer.from(bytes));
  return file;
}

const S1 = {
  name: 'anchor_K1_2026-06-17_080000.sqlite', user: 'Kid1', sessionId: 'sess-Kid1-1', startTime: '2026-06-17_080000',
  problems: [{ a: 3, b: 0, ms: 900, ok: true }, { a: 4, b: 4, ms: 2100, ok: true }, { a: 7, b: 6, ms: 5200, ok: true }, { a: 8, b: 8, ms: 3900, ok: true }],
};
const S2 = {
  name: 'anchor_K1_2026-06-18_090000.sqlite', user: 'Kid1', sessionId: 'sess-Kid1-2', startTime: '2026-06-18_090000',
  problems: [{ a: 2, b: 6, ms: 2200, ok: true }, { a: 9, b: 4, ms: 4200, ok: true }, { a: 1, b: 8, ms: 1800, ok: true }],
};

async function loadAnalysis(page, context) {
  await routeCdns(context);
  const errors = trackPageErrors(page);
  await page.goto('/math_analysis.html');
  await page.waitForSelector('#choose-load-file', { timeout: 30_000 });
  // wait until controls are wired (sql.js + plotly loaded, populateControls ran)
  await expect(page.locator('#choose-load-file')).toBeEnabled();
  await page.waitForTimeout(500);
  // The "Session data" panel starts collapsed; expand it so its controls (load/save
  // SQLite) are clickable rather than covered by the collapsed header/heatmap. Toggle
  // via class directly — clicking the header fires a heatmap relayout on the still-empty
  // plot, which Plotly logs as a benign _guiEditing error that would fail the strict
  // page-error assertion. The class change makes the same controls reachable cleanly.
  await page.evaluate(() => {
    const s = document.getElementById('file-upload-section');
    if (s) { s.classList.remove('collapsed'); s.classList.add('expanded'); }
  });
  await page.waitForTimeout(200);
  return errors;
}

async function loadFile(page, fixture) {
  // The hidden input auto-loads on change (real users click "Choose and load file", which
  // opens the OS picker — not drivable here).
  await page.setInputFiles('#sqlite-file-input', fixture);
  await expect(page.locator('#sqlite-status')).toContainText('Loaded', { timeout: 15_000 });
}

test('load a .sqlite: session appears, user locks to that one person', async ({ page, context }) => {
  const errors = await loadAnalysis(page, context);
  await loadFile(page, makeSqliteFixture(S1));

  // user selector locked to Kid1
  await expect(page.locator('#username-selection')).toBeDisabled();
  await expect(page.locator('#username-selection')).toHaveValue('Kid1');
  // mode select stays All/Last/Last N; checklist shows the loaded session
  const opts = await page.$$eval('#session-selection option', (os) => os.map((o) => o.textContent));
  expect(opts).toEqual(['All Sessions', 'Last Session', 'Last N Sessions']);
  const labels = await page.$$eval('#session-checklist .session-label', (els) => els.map((e) => e.textContent));
  expect(labels.some((t) => t.includes('anchor_K1_2026-06-17'))).toBe(true);
  // heatmap rendered
  await expect(page.locator('#heatmap .main-svg').first()).toBeVisible({ timeout: 15_000 });

  // App-wide fluency readout (next to "Reset all to default"): 1 green fact of the
  // 100-fact 0-9 addition universe (3+0 @900ms; 4+4/8+8 yellow, 7+6 red) -> 1%.
  await expect(page.locator('#current-fluency-percentage')).toHaveText('Current fluency percentage: 1%');
  // Changing a rubric parameter recomputes it: greenMs 6000 makes all 4 facts green -> 4%.
  await page.evaluate(() => {
    const el = document.getElementById('fluency-threshold');
    el.value = '6000';
    el.dispatchEvent(new Event('input', { bubbles: true }));
  });
  await expect(page.locator('#current-fluency-percentage')).toHaveText('Current fluency percentage: 4%');
  expect(errors).toEqual([]);
});

const flaggedCount = (page) => page.evaluate(() => {
  const db = window.__analysisDb && window.__analysisDb();
  if (!db) return -1;
  const r = db.exec('SELECT COUNT(*) FROM ProblemAttempts WHERE flags_json IS NOT NULL');
  return r.length ? r[0].values[0][0] : 0;
});

test('flagging a problem auto-saves to the working DB and persists across reload', async ({ page, context }) => {
  await loadAnalysis(page, context);
  await loadFile(page, makeSqliteFixture(S1));

  // open the list view, flag the first problem as "distracted", save
  await page.click('#toggle-problem-list');
  await page.locator('.flag-edit-toggle').first().click();
  await page.locator('.problem-item .flag-checkboxes input[value="distracted"]').first().check();
  await page.locator('.problem-item .flag-save-btn').first().click();
  await expect(page.locator('.problem-item .flag-indicator-list').first()).toBeVisible({ timeout: 10_000 });
  expect(await flaggedCount(page)).toBe(1); // written to the working DB (auto-persisted to IndexedDB)

  // survives a reload (no manual save / download needed)
  await page.waitForTimeout(800);
  await page.reload();
  await page.waitForSelector('#choose-load-file', { timeout: 30_000 });
  await page.waitForTimeout(1200);
  expect(await flaggedCount(page)).toBe(1);
});

test('Revert changes restores the file as loaded (discards flag edits)', async ({ page, context }) => {
  page.on('dialog', (d) => d.accept());   // accept the confirm
  await loadAnalysis(page, context);
  await loadFile(page, makeSqliteFixture(S1));

  await page.click('#toggle-problem-list');
  await page.locator('.flag-edit-toggle').first().click();
  await page.locator('.problem-item .flag-checkboxes input[value="distracted"]').first().check();
  await page.locator('.problem-item .flag-save-btn').first().click();
  expect(await flaggedCount(page)).toBe(1);

  await page.click('#revert-changes');
  await expect(page.locator('#sqlite-status')).toContainText('Reverted', { timeout: 10_000 });
  expect(await flaggedCount(page)).toBe(0);   // back to the file as loaded
});

test('loading a second raw file replaces the first (only the new file\'s sessions remain)', async ({ page, context }) => {
  await loadAnalysis(page, context);
  await loadFile(page, makeSqliteFixture(S1));
  await loadFile(page, makeSqliteFixture(S2));

  const sessionOpts = await page.$$eval('#session-checklist input[type="checkbox"]', (os) => os.length);
  expect(sessionOpts).toBe(1);
  const labels = await page.$$eval('#session-checklist .session-label', (els) => els.map((e) => e.textContent));
  expect(labels.some((t) => t.includes('2026-06-18'))).toBe(true);
  expect(labels.some((t) => t.includes('2026-06-17'))).toBe(false);

  // only the new file's data remains in the working DB
  const stats = await page.evaluate(() => {
    const db = window.__analysisDb();
    const scalar = (q) => { const r = db.exec(q); return r.length ? r[0].values[0][0] : 0; };
    return {
      sessions: scalar('SELECT COUNT(*) FROM Sessions'),
      attempts: scalar('SELECT COUNT(*) FROM ProblemAttempts'),
      users: db.exec('SELECT name FROM Users').flatMap((r) => r.values.map((v) => v[0])),
    };
  });
  expect(stats.sessions).toBe(1);
  expect(stats.attempts).toBe(3);
  expect(stats.users).toEqual(['Kid1']);
});

test('the loaded SQLite is retained across a page reload', async ({ page, context }) => {
  await loadAnalysis(page, context);
  await loadFile(page, makeSqliteFixture(S1));
  await page.waitForTimeout(800); // let the IndexedDB working-DB write commit

  await page.reload();
  await page.waitForSelector('#choose-load-file', { timeout: 30_000 });
  await page.waitForTimeout(1200);

  // session still present and user still locked, with no re-load
  await expect(page.locator('#username-selection')).toBeDisabled();
  await expect(page.locator('#username-selection')).toHaveValue('Kid1');
  const sessionOpts = await page.$$eval('#session-checklist input[type="checkbox"]', (os) => os.length);
  expect(sessionOpts).toBe(1);
});

test('top control selections (e.g. color scale) persist across reload', async ({ page, context }) => {
  await loadAnalysis(page, context);
  await loadFile(page, makeSqliteFixture(S1));
  await page.selectOption('#color-scale-selector', 'orange');
  await page.selectOption('#number-range', '0-20');
  await page.waitForTimeout(300);

  await page.reload();
  await page.waitForSelector('#color-scale-selector', { timeout: 30_000 });
  await page.waitForTimeout(800);

  await expect(page.locator('#color-scale-selector')).toHaveValue('orange');
  await expect(page.locator('#number-range')).toHaveValue('0-20');
});

test('Reset all to default resets render controls but keeps operation/flag filters', async ({ page, context }) => {
  await loadAnalysis(page, context);
  await loadFile(page, makeSqliteFixture(S1));
  await page.selectOption('#color-scale-selector', 'classic');
  await page.selectOption('#number-range', '0-5');
  await page.selectOption('#operation-filter', '+');
  await page.selectOption('#flag-filter', 'all');

  await page.click('#reset-controls');

  // render controls back to default
  await expect(page.locator('#color-scale-selector')).toHaveValue('classic');
  await expect(page.locator('#number-range')).toHaveValue('0-9');
  await expect(page.locator('#duplicate-aggregation')).toHaveValue('average');
  await expect(page.locator('#min-response-time-threshold')).toHaveValue('2000');
  await expect(page.locator('#max-response-time-threshold')).toHaveValue('10000');
  // operation + flag selections preserved
  await expect(page.locator('#operation-filter')).toHaveValue('+');
  await expect(page.locator('#flag-filter')).toHaveValue('all');
});

test('clicking a cell focuses the list on that problem and shows the session date', async ({ page, context }) => {
  await loadAnalysis(page, context);
  await loadFile(page, makeSqliteFixture(S1)); // S1 includes 7 + 6
  await expect(page.locator('#heatmap .main-svg').first()).toBeVisible({ timeout: 15_000 });

  // exercise the same path the heatmap cell-click invokes
  await page.evaluate(() => onCellClick(7, 6));

  await expect(page.locator('#problem-focus-bar')).toBeVisible();
  await expect(page.locator('#problem-focus-bar')).toContainText('7 + 6');
  const items = await page.$$('#problem-list-items .problem-item');
  expect(items.length).toBe(1);
  await expect(page.locator('#problem-list-items .problem-text').first()).toHaveText('7 + 6');
  await expect(page.locator('#problem-list-items .problem-session').first()).toContainText('2026'); // session date shown

  // "show all" clears the focus
  await page.click('#problem-focus-bar a');
  await expect(page.locator('#problem-focus-bar')).toBeHidden();
  const after = await page.$$('#problem-list-items .problem-item');
  expect(after.length).toBe(S1.problems.length);
});

test('the problem list shows each attempt\'s presented_at time (to the second), not the session start', async ({ page, context }) => {
  await loadAnalysis(page, context);
  // Two attempts of the SAME fact in one session: same start_time, different presented_at.
  const fixture = makeSqliteFixture({
    name: 'anchor_Kid_2026-06-21_103126.sqlite', user: 'Kid', sessionId: 'sess-kid', startTime: '2026-06-21_103126',
    problems: [
      { a: 3, b: 7, ms: 2847, ok: true, at: '2026-06-21T17:32:34.000Z' },
      { a: 3, b: 7, ms: 6296, ok: true, at: '2026-06-21T17:34:23.000Z' },
    ],
  });
  await loadFile(page, fixture);
  await expect(page.locator('#heatmap .main-svg').first()).toBeVisible({ timeout: 15_000 });
  const labels = await page.locator('#problem-list-items .problem-session').allTextContents();
  expect(labels.length).toBe(2);
  expect(labels[0]).not.toBe(labels[1]);              // per-attempt times differ (not both the session start)
  for (const l of labels) expect(l).toMatch(/\d{1,2}:\d{2}:\d{2}/); // down to the second
});

test('opening with ?folder=&user= auto-loads that person\'s latest file', async ({ page, context }) => {
  await routeCdns(context);
  const b64 = fs.readFileSync(makeSqliteFixture(S1)).toString('base64');
  await context.route(/\/api\/latest-user-db/, (route) => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({ ok: true, found: true, folder: 'tlkids', user: 'Kid1',
      filename: 'math-flu_K1_2026-06-17.sqlite', sessionCount: 1, base64: b64 }),
  }));
  await page.goto('/math_analysis.html?folder=tlkids&user=Kid1');
  await page.waitForSelector('#choose-load-file', { timeout: 30_000 });
  // auto-loaded from the URL params: the user selector locks to Kid1
  await expect(page.locator('#username-selection')).toHaveValue('Kid1', { timeout: 15_000 });
  await expect(page.locator('#username-selection')).toBeDisabled();
});

test('the problem-list editor is mounted on the analysis page (?folder=&user=)', async ({ page, context }) => {
  await routeCdns(context);
  await context.route(/\/api\/latest-user-db/, (route) => route.fulfill({
    contentType: 'application/json', body: JSON.stringify({ ok: true, found: false, folder: 'tlkids', user: 'K2' }),
  }));
  // Minimal in-memory /api/problem-lists stub (GET view + create) — the shared module's
  // behavior is covered thoroughly on the anchor page; here we just prove it's wired here too.
  let lists = [{ problem_list_id: 5, list_order: 1, list_name: 'Warm set', retain: 0, times_used: 0, item_count: 1,
    items: [{ item_order: 1, problem_text: '8 + 2', category: 'problem-list' }] }];
  await context.route(/\/api\/problem-lists(\?|$)/, async (route) => {
    const req = route.request();
    const send = (o) => route.fulfill({ contentType: 'application/json', body: JSON.stringify(o) });
    if (req.method() === 'GET') return send({ ok: true, found: true, file: 'f.sqlite', folder: 'tlkids', user: 'K2', problemLists: lists });
    const p = JSON.parse(req.postData() || '{}');
    if (p.action === 'create') lists = [...lists, { problem_list_id: 6, list_order: 2, list_name: p.listName || 'New list', retain: 1, times_used: 0, item_count: 0, items: [] }];
    return send({ ok: true, folder: 'tlkids', user: 'K2', file: 'f.sqlite', problemLists: lists });
  });
  await page.goto('/math_analysis.html?folder=tlkids&user=K2');
  await page.waitForSelector('#analysis-problem-list-editor .plp-header', { timeout: 30_000 });
  // startOpen: the panel auto-opens and fetches, so the seeded list renders without a click.
  const cards = page.locator('#analysis-problem-list-editor [data-plp="card"]');
  await expect(cards).toHaveCount(1);
  await expect(cards.first().locator('[data-plp="name"]')).toHaveValue('Warm set');
  await page.locator('#analysis-problem-list-editor [data-plp="new"]').click();   // create another
  await expect(cards).toHaveCount(2);
});

test('editor "Generate by fluency" adds a list from the loaded learner', async ({ page, context }) => {
  await routeCdns(context);
  const b64 = fs.readFileSync(makeSqliteFixture(S1)).toString('base64');
  await context.route(/\/api\/latest-user-db/, (route) => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({ ok: true, found: true, folder: 'tlkids', user: 'Kid1',
      filename: 'f.sqlite', sessionCount: 1, base64: b64 }),
  }));
  // In-memory /api/problem-lists stub that parses created text into items + handles reorder.
  let lists = [];
  let nextId = 100;
  await context.route(/\/api\/problem-lists(\?|$)/, async (route) => {
    const req = route.request();
    const send = (o) => route.fulfill({ contentType: 'application/json', body: JSON.stringify(o) });
    if (req.method() === 'GET') return send({ ok: true, found: true, file: 'f.sqlite', folder: 'tlkids', user: 'Kid1', problemLists: lists });
    const p = JSON.parse(req.postData() || '{}');
    if (p.action === 'create') {
      const items = (p.text || '').split('\n').map((t) => t.trim()).filter(Boolean)
        .map((t, i) => ({ item_order: i + 1, problem_text: t, category: '' }));
      lists = [...lists, { problem_list_id: ++nextId, list_order: lists.length + 1, list_name: p.listName || '',
        retain: p.retain ? 1 : 0, times_used: 0, item_count: items.length, items }];
    } else if (p.action === 'reorder') {
      const byId = new Map(lists.map((l) => [l.problem_list_id, l]));
      lists = p.order.map((id, i) => ({ ...byId.get(id), list_order: i + 1 }));
    }
    return send({ ok: true, folder: 'tlkids', user: 'Kid1', file: 'f.sqlite', problemLists: lists });
  });
  await page.goto('/math_analysis.html?folder=tlkids&user=Kid1');
  await page.waitForSelector('#analysis-problem-list-editor .plp-header', { timeout: 30_000 });
  await expect(page.locator('#username-selection')).toHaveValue('Kid1', { timeout: 15_000 }); // DB hydrated
  await page.selectOption('#operation-filter', '+');

  const ed = '#analysis-problem-list-editor ';
  await page.locator(ed + '[data-plp="gen-flu"]').click();             // open the by-fluency form
  await page.fill(ed + '[data-plp="genf-count"]', '6');
  for (const [k, v] of [['fluent', '0'], ['almost', '0'], ['needs-practice', '0'], ['incorrect', '0'], ['missing', '100']]) {
    await page.fill(`${ed}[data-flu="${k}"]`, v);
  }
  await page.locator(ed + '[data-plp="gen-add"]').click();            // generate + add
  const cards = page.locator(ed + '[data-plp="card"]');
  await expect(cards).toHaveCount(1);
  await expect(cards.first().locator('[data-plp="name"]')).toHaveValue('Fluency');
  const text = await cards.first().locator('[data-plp="text"]').inputValue();
  const lines = text.trim().split('\n').filter(Boolean);
  expect(lines.length).toBe(6);                                       // 6 unseen addition facts
  expect(lines.every((l) => /^\d+\s*\+\s*\d+$/.test(l))).toBe(true);
});

test('fluency thresholds: controls prefill from the file profile, Restore resets, Save posts them', async ({ page, context }) => {
  await routeCdns(context);
  const b64 = fs.readFileSync(makeSqliteFixture(S1)).toString('base64');
  await context.route(/\/api\/latest-user-db/, (route) => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({ ok: true, found: true, folder: 'tlkids', user: 'Kid1', filename: 'f.sqlite', sessionCount: 1, base64: b64 }),
  }));
  // resolveEditorContext asks the server which on-disk copy to target -> sets __analysisEditorCtx.
  await context.route(/\/api\/resolve-editor-target(\?|$)/, (r) => r.fulfill({ contentType: 'application/json',
    body: JSON.stringify({ ok: true, found: true, folder: 'tlkids', user: 'Kid1', file: 'f.sqlite', relativePath: 'tlkids/f.sqlite' }) }));
  // Profile GET serves saved thresholds (greenMs 1500); POST captures what Save sends.
  let lastProfilePost = null;
  await context.route(/\/api\/profile(\?|$)/, async (route) => {
    const req = route.request();
    const send = (o) => route.fulfill({ contentType: 'application/json', body: JSON.stringify(o) });
    if (req.method() === 'GET') {
      return send({ ok: true, found: true, folder: 'tlkids', user: 'Kid1', file: 'f.sqlite',
        profile: { showFluencyPercent: true, thresholds: { greenMs: 1500, redMs: 3500, windowSize: 4, minAccuracy: 0.9 } } });
    }
    lastProfilePost = JSON.parse(req.postData() || '{}');
    return send({ ok: true, folder: 'tlkids', user: 'Kid1', file: 'f.sqlite', profile: { showFluencyPercent: true, thresholds: lastProfilePost.thresholds } });
  });

  await page.goto('/math_analysis.html?folder=tlkids&user=Kid1');
  await expect(page.locator('#username-selection')).toHaveValue('Kid1', { timeout: 30_000 });
  // Prefilled from the saved profile.
  await expect(page.locator('#fluency-threshold')).toHaveValue('1500', { timeout: 15_000 });
  await expect(page.locator('#fluency-red-threshold')).toHaveValue('3500');
  await expect(page.locator('#fluency-window')).toHaveValue('4');
  await expect(page.locator('#fluency-min-accuracy')).toHaveValue('90');

  // Restore defaults resets the four controls to the system rubric (no save).
  await page.locator('#fluency-thresholds-restore').click();
  await expect(page.locator('#fluency-threshold')).toHaveValue('2000');
  await expect(page.locator('#fluency-min-accuracy')).toHaveValue('80');

  // Edit + Save to loaded file -> POST carries the thresholds (minAccuracy as a 0-1 fraction).
  await page.fill('#fluency-min-accuracy', '75');
  await page.locator('#fluency-thresholds-save').click();
  await expect.poll(() => lastProfilePost && lastProfilePost.thresholds && lastProfilePost.thresholds.greenMs).toBe(2000);
  expect(lastProfilePost.file).toBe('f.sqlite');
  expect(lastProfilePost.thresholds.minAccuracy).toBeCloseTo(0.75, 5);
});

test('editor "Add as first" inserts the generated list at position #1', async ({ page, context }) => {
  await routeCdns(context);
  const b64 = fs.readFileSync(makeSqliteFixture(S1)).toString('base64');
  await context.route(/\/api\/latest-user-db/, (route) => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({ ok: true, found: true, folder: 'tlkids', user: 'Kid1', filename: 'f.sqlite', sessionCount: 1, base64: b64 }),
  }));
  let lists = [{ problem_list_id: 1, list_order: 1, list_name: 'Existing', retain: 0, times_used: 0, item_count: 1,
    items: [{ item_order: 1, problem_text: '8 + 2', category: '' }] }];
  let nextId = 100;
  await context.route(/\/api\/problem-lists(\?|$)/, async (route) => {
    const req = route.request();
    const send = (o) => route.fulfill({ contentType: 'application/json', body: JSON.stringify(o) });
    if (req.method() === 'GET') return send({ ok: true, found: true, file: 'f.sqlite', folder: 'tlkids', user: 'Kid1', problemLists: lists });
    const p = JSON.parse(req.postData() || '{}');
    if (p.action === 'create') {
      const items = (p.text || '').split('\n').map((t) => t.trim()).filter(Boolean).map((t, i) => ({ item_order: i + 1, problem_text: t }));
      lists = [...lists, { problem_list_id: ++nextId, list_order: lists.length + 1, list_name: p.listName || '', retain: p.retain ? 1 : 0, times_used: 0, item_count: items.length, items }];
    } else if (p.action === 'reorder') {
      const byId = new Map(lists.map((l) => [l.problem_list_id, l]));
      lists = p.order.map((id, i) => ({ ...byId.get(id), list_order: i + 1 }));
    }
    return send({ ok: true, problemLists: lists });
  });
  await page.goto('/math_analysis.html?folder=tlkids&user=Kid1');
  await page.waitForSelector('#analysis-problem-list-editor .plp-header', { timeout: 30_000 });
  await expect(page.locator('#username-selection')).toHaveValue('Kid1', { timeout: 15_000 });
  await page.selectOption('#operation-filter', '+');

  const ed = '#analysis-problem-list-editor ';
  await expect(page.locator(ed + '[data-plp="card"]')).toHaveCount(1);  // the Existing list
  await page.locator(ed + '[data-plp="gen-flu"]').click();
  await page.fill(ed + '[data-plp="genf-count"]', '4');
  for (const [k, v] of [['fluent', '0'], ['almost', '0'], ['needs-practice', '0'], ['incorrect', '0'], ['missing', '100']]) {
    await page.fill(`${ed}[data-flu="${k}"]`, v);
  }
  await page.selectOption(ed + '[data-plp="gen-position"]', 'first');   // insert at the front
  await page.locator(ed + '[data-plp="gen-add"]').click();
  const cards = page.locator(ed + '[data-plp="card"]');
  await expect(cards).toHaveCount(2);
  // The new "Fluency" list is now first; "Existing" is second.
  await expect(cards.nth(0).locator('[data-plp="name"]')).toHaveValue('Fluency');
  await expect(cards.nth(1).locator('[data-plp="name"]')).toHaveValue('Existing');
});

test('editor auto-resolves the source folder after a local .sqlite load', async ({ page, context }) => {
  await routeCdns(context);
  const fixture = makeSqliteFixture(S1);                       // file basename === S1.name
  const b64 = fs.readFileSync(fixture).toString('base64');
  await context.route(/\/api\/resolve-editor-target(\?|$)/, (r) => r.fulfill({ contentType: 'application/json',
    body: JSON.stringify({ ok: true, found: true, folder: 'tlkids', user: 'Kid1', file: S1.name, relativePath: `tlkids/${S1.name}` }) }));
  await context.route(/\/api\/latest-user-db/, (r) => r.fulfill({ contentType: 'application/json',
    body: JSON.stringify({ ok: true, found: true, folder: 'tlkids', user: 'Kid1', filename: S1.name, sessionCount: 1, base64: b64 }) }));
  let lists = [];
  let postedFile = null;
  await context.route(/\/api\/problem-lists(\?|$)/, async (route) => {
    const req = route.request();
    const send = (o) => route.fulfill({ contentType: 'application/json', body: JSON.stringify(o) });
    if (req.method() === 'GET') return send({ ok: true, found: true, file: S1.name, folder: 'tlkids', user: 'Kid1', problemLists: lists });
    postedFile = JSON.parse(req.postData() || '{}').file;   // the exact file the editor targets
    return send({ ok: true, problemLists: lists });
  });
  await page.goto('/math_analysis.html');
  await page.waitForSelector('#choose-load-file', { timeout: 30_000 });
  await page.evaluate(() => { const s = document.getElementById('file-upload-section'); if (s) { s.classList.remove('collapsed'); s.classList.add('expanded'); } });
  // Before loading a file: no folder/user context, so the editor shows the hint.
  await expect(page.locator('#analysis-problem-list-editor .plp-note')).toContainText('Pick a learner');
  await page.setInputFiles('#sqlite-file-input', fixture);
  await expect(page.locator('#sqlite-status')).toContainText('Loaded', { timeout: 15_000 });
  // After loading: the folder is resolved from the dev server, so the editor enables.
  await expect(page.locator('#analysis-problem-list-editor [data-plp="new"]')).toBeEnabled({ timeout: 10_000 });
  // And a mutation targets the EXACT loaded file (not just "the latest in some folder").
  await page.locator('#analysis-problem-list-editor [data-plp="new"]').click();
  await expect.poll(() => postedFile).toBe(S1.name);
});

test('editor by-fluency requires the %s to total 100 (warning + disabled Add; 100 zeroes the rest)', async ({ page, context }) => {
  await routeCdns(context);
  const b64 = fs.readFileSync(makeSqliteFixture(S1)).toString('base64');
  await context.route(/\/api\/latest-user-db/, (r) => r.fulfill({ contentType: 'application/json',
    body: JSON.stringify({ ok: true, found: true, folder: 'tlkids', user: 'Kid1', filename: 'f.sqlite', sessionCount: 1, base64: b64 }) }));
  await context.route(/\/api\/problem-lists(\?|$)/, async (route) => route.fulfill({ contentType: 'application/json',
    body: JSON.stringify({ ok: true, found: true, file: 'f.sqlite', folder: 'tlkids', user: 'Kid1', problemLists: [] }) }));
  await page.goto('/math_analysis.html?folder=tlkids&user=Kid1');
  await page.waitForSelector('#analysis-problem-list-editor .plp-header', { timeout: 30_000 });
  await expect(page.locator('#username-selection')).toHaveValue('Kid1', { timeout: 15_000 });

  const ed = '#analysis-problem-list-editor ';
  await page.locator(ed + '[data-plp="gen-flu"]').click();
  // Defaults (25/50/25/0/0) total 100 -> Add enabled, no warning.
  await expect(page.locator(ed + '[data-plp="gen-add"]')).toBeEnabled();
  await expect(page.locator(ed + '[data-plp="genf-sumwarn"]')).toBeHidden();
  // Bump one over 100 -> red warning + Add disabled.
  await page.fill(ed + '[data-flu="fluent"]', '40');               // 40+50+25 = 115
  await expect(page.locator(ed + '[data-plp="genf-sumwarn"]')).toBeVisible();
  await expect(page.locator(ed + '[data-plp="gen-add"]')).toBeDisabled();
  // Entering 100 in one category zeroes the rest -> totals 100 -> Add enabled again.
  await page.fill(ed + '[data-flu="missing"]', '100');
  await expect(page.locator(ed + '[data-flu="fluent"]')).toHaveValue('0');
  await expect(page.locator(ed + '[data-plp="gen-add"]')).toBeEnabled();
});

// Shared setup: editor open on a learner, with a feast-config route whose GET returns
// `preset` (null = unsaved) and whose POST is captured into the returned `getPayload()`.
async function openEditorWithFeast(page, context, preset) {
  await routeCdns(context);
  const b64 = fs.readFileSync(makeSqliteFixture(S1)).toString('base64');
  await context.route(/\/api\/latest-user-db/, (r) => r.fulfill({ contentType: 'application/json',
    body: JSON.stringify({ ok: true, found: true, folder: 'tlkids', user: 'Kid1', filename: 'f.sqlite', sessionCount: 1, base64: b64 }) }));
  await context.route(/\/api\/problem-lists(\?|$)/, async (route) => route.fulfill({ contentType: 'application/json',
    body: JSON.stringify({ ok: true, found: true, file: 'f.sqlite', folder: 'tlkids', user: 'Kid1', problemLists: [] }) }));
  const box = { payload: null };
  await context.route(/\/api\/fluency-feast-config/, async (route) => {
    const req = route.request();
    if (req.method() === 'GET') return route.fulfill({ contentType: 'application/json', body: JSON.stringify({ ok: true, found: !!preset, fluencyFeast: preset || null }) });
    box.payload = JSON.parse(req.postData() || '{}');
    return route.fulfill({ contentType: 'application/json', body: JSON.stringify({ ok: true, fluencyFeast: box.payload }) });
  });
  await page.goto('/math_analysis.html?folder=tlkids&user=Kid1');
  await page.waitForSelector('#analysis-problem-list-editor .plp-header', { timeout: 30_000 });
  await expect(page.locator('#username-selection')).toHaveValue('Kid1', { timeout: 15_000 });
  return box;
}

test('editor by-fluency form prefills from the file\'s saved preset', async ({ page, context }) => {
  await openEditorWithFeast(page, context, { count: 9, session: { mode: 'all' }, mix: { missing: 80, incorrect: 20, almost: 0, 'needs-practice': 0, fluent: 0 } });
  const ed = '#analysis-problem-list-editor ';
  await page.locator(ed + '[data-plp="gen-flu"]').click();
  await expect(page.locator(ed + '[data-plp="genf-count"]')).toHaveValue('9');         // prefilled
  await expect(page.locator(ed + '[data-flu="missing"]')).toHaveValue('80');
  await expect(page.locator(ed + '[data-flu="incorrect"]')).toHaveValue('20');
});

test('editor by-fluency: first open with no saved preset writes the defaults to the file', async ({ page, context }) => {
  const box = await openEditorWithFeast(page, context, null);   // unsaved
  const ed = '#analysis-problem-list-editor ';
  await page.locator(ed + '[data-plp="gen-flu"]').click();
  await expect.poll(() => box.payload).not.toBeNull();          // auto-write fired
  expect(box.payload.count).toBe(20);                           // the defaults
  expect(box.payload.mix).toMatchObject({ missing: 40, incorrect: 40, almost: 10, 'needs-practice': 10, fluent: 0 });
});

test('editor "Save as feast preset" stores the form as the file\'s feast preset', async ({ page, context }) => {
  const box = await openEditorWithFeast(page, context, { count: 5, session: { mode: 'all' }, mix: { missing: 100, incorrect: 0, almost: 0, 'needs-practice': 0, fluent: 0 } });
  const ed = '#analysis-problem-list-editor ';
  await page.locator(ed + '[data-plp="gen-flu"]').click();
  await expect(page.locator(ed + '[data-plp="genf-count"]')).toHaveValue('5');          // prefilled, then edit
  await page.fill(ed + '[data-plp="genf-count"]', '14');
  await page.locator(ed + '[data-plp="genf-save-preset"]').click();
  await expect(page.locator(ed + '[data-plp="genf-preset-status"]')).toContainText('Saved');
  expect(box.payload.count).toBe(14);
  expect(box.payload.mix.missing).toBe(100);
  expect(box.payload.session.mode).toBe('all');
});
