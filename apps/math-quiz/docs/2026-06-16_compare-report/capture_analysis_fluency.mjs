// Capture screenshots of the analysis page's NEW fluency view (Proposal A):
//   - "Fluency rating" cell metric (the grid colored by the red/yellow/green/blue
//     rubric) + the operation / 0-5·6-9 / category roll-up strip
//   - "Fluency overlay" (response-time fill + per-cell fluency borders — see both)
//
// Hermetic, same approach as the other capture scripts: serves apps/math-quiz
// over a local static server, routes CDN libs (sql.js, plotly) to the pinned
// copies in tests/node_modules, and uses the bundled chromium. Builds a per-user
// .sqlite fixture (single addition session, engineered spread) and loads it
// through the page's file picker.
//
// Run from apps/math-quiz/ (needs tests/ deps installed):
//   cd apps/math-quiz/tests && npm install            # one time
//   node docs/2026-06-16_compare-report/capture_analysis_fluency.mjs
//
// Output: docs/2026-06-16_compare-report/screenshots/analysis_*.png

import { spawn } from 'node:child_process';
import path from 'node:path';
import fs from 'node:fs';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import { existsSync } from 'node:fs';
import { createRequire } from 'node:module';

const here = path.dirname(fileURLToPath(import.meta.url));
const appDir = path.resolve(here, '..', '..');          // apps/math-quiz
const testsDir = path.join(appDir, 'tests');
const nm = (...p) => path.join(testsDir, 'node_modules', ...p);
const shotDir = path.join(here, 'screenshots');
const require = createRequire(path.join(testsDir, '/'));
const PORT = 8920;
const BASE = `http://127.0.0.1:${PORT}`;

const CDN_FILES = [
  { pattern: /blueimp-md5.*md5(\.min)?\.js/, file: nm('blueimp-md5', 'js', 'md5.min.js'), type: 'text/javascript' },
  { pattern: /jszip.*jszip(\.min)?\.js/, file: nm('jszip', 'dist', 'jszip.min.js'), type: 'text/javascript' },
  { pattern: /canvas-confetti.*confetti\.browser(\.min)?\.js/, file: nm('canvas-confetti', 'dist', 'confetti.browser.js'), type: 'text/javascript' },
  { pattern: /sql\.js.*sql-wasm\.wasm/, file: nm('sql.js', 'dist', 'sql-wasm.wasm'), type: 'application/wasm' },
  { pattern: /sql\.js.*sql-wasm\.js/, file: nm('sql.js', 'dist', 'sql-wasm.js'), type: 'text/javascript' },
  { pattern: /cdn\.plot\.ly\/plotly-.*\.js/, file: nm('plotly.js-dist', 'plotly.js'), type: 'text/javascript' }
];

const SCHEMA = `
  CREATE TABLE IF NOT EXISTS Users (name TEXT PRIMARY KEY);
  CREATE TABLE IF NOT EXISTS Sessions (session_id TEXT PRIMARY KEY, session_filename TEXT, user_name TEXT,
    start_time TEXT, end_time TEXT, num_problems INTEGER, number_range_start INTEGER, number_range_end INTEGER,
    numbers_include TEXT, numbers_exclude TEXT, num_numbers INTEGER, operations TEXT,
    total_problems INTEGER, correct_answers INTEGER, average_response_time_ms INTEGER);
  CREATE TABLE IF NOT EXISTS ProblemAttempts (attempt_id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT,
    problem_id TEXT, problem_text TEXT, num1 INTEGER, num2 INTEGER, operation TEXT, correct_answer REAL,
    user_answer_string TEXT, user_answer REAL, is_correct INTEGER, response_time_ms INTEGER, flags_json TEXT);
`;

// [a, b, ms, ok] — engineered to surface every status the rubric emits here
// (green/yellow/red/gray) across several addition categories.
const FACTS = [
  [3, 0, 800, 1], [1, 4, 820, 1], [2, 3, 900, 1], [4, 4, 1100, 1], [0, 7, 760, 1], [2, 5, 1500, 1], // green
  [3, 7, 3000, 1], [6, 7, 3200, 1], [7, 8, 3300, 1],                                                 // yellow
  [8, 9, 5200, 1], [6, 9, 4600, 1],                                                                  // red
  [7, 9, 1200, 0], [5, 8, 1400, 0]                                                                   // gray (wrong)
];

function makeFixture() {
  const initSqlJs = require('sql.js');
  return initSqlJs({ wasmBinary: fs.readFileSync(require.resolve('sql.js/dist/sql-wasm.wasm')) }).then((SQL) => {
    const db = new SQL.Database();
    db.run(SCHEMA);
    db.run('INSERT OR IGNORE INTO Users (name) VALUES (?)', ['Ada']);
    db.run(`INSERT INTO Sessions (session_id, session_filename, user_name, start_time, operations, total_problems, correct_answers)
            VALUES (?,?,?,?,?,?,?)`,
      ['s1', 'math-flu_Ada_2026-06-19.sqlite', 'Ada', '2026-06-19_080000', '["+"]', FACTS.length, FACTS.filter((f) => f[3]).length]);
    FACTS.forEach(([a, b, ms, ok], i) => db.run(
      `INSERT INTO ProblemAttempts (session_id, problem_id, problem_text, num1, num2, operation, correct_answer,
        user_answer_string, user_answer, is_correct, response_time_ms, flags_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)`,
      ['s1', `p${i}`, `${a} + ${b}`, a, b, '+', a + b, String(a + b), a + b, ok, ms, null]));
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'mq-fixture-'));
    const file = path.join(dir, 'math-flu_Ada_2026-06-19.sqlite');
    fs.writeFileSync(file, Buffer.from(db.export()));
    db.close();
    return file;
  });
}

async function resolveChromium() {
  if (process.env.PLAYWRIGHT_CHROMIUM_PATH) return process.env.PLAYWRIGHT_CHROMIUM_PATH;
  try {
    const { chromium } = (await import(nm('playwright-core', 'index.js'))).default;
    const p = chromium.executablePath();
    if (p && existsSync(p)) return p;
  } catch { /* fall through */ }
  const sparticuz = (await import(nm('@sparticuz', 'chromium', 'build', 'esm', 'index.js'))).default;
  return await sparticuz.executablePath();
}

function startServer() {
  return spawn('python3', ['-m', 'http.server', String(PORT), '--bind', '127.0.0.1', '--directory', appDir], { stdio: 'ignore' });
}
async function waitForServer(url, tries = 40) {
  for (let i = 0; i < tries; i++) {
    try { const r = await fetch(url); if (r.ok) return; } catch { /* retry */ }
    await new Promise(r => setTimeout(r, 250));
  }
  throw new Error(`server not up at ${url}`);
}
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

async function main() {
  const file = await makeFixture();
  const { chromium } = (await import(nm('playwright-core', 'index.js'))).default;
  const executablePath = await resolveChromium();
  console.log('chromium:', executablePath);

  const server = startServer();
  try {
    await waitForServer(`${BASE}/math_analysis.html`);
    const browser = await chromium.launch({ executablePath, args: ['--no-sandbox', '--disable-dev-shm-usage'] });
    const context = await browser.newContext({ viewport: { width: 1100, height: 1000 }, deviceScaleFactor: 2 });
    await context.route(/(cdnjs\.cloudflare\.com|cdn\.jsdelivr\.net|cdn\.plot\.ly)/, async (route) => {
      const entry = CDN_FILES.find(e => e.pattern.test(route.request().url()));
      if (!entry) return route.abort();
      await route.fulfill({ path: entry.file, contentType: entry.type });
    });

    const page = await context.newPage();
    page.on('console', m => { if (m.type() === 'error') console.warn('  page error:', m.text()); });
    await page.goto(`${BASE}/math_analysis.html`);
    await page.waitForSelector('#choose-load-file');
    await page.setInputFiles('#sqlite-file-input', file);
    await page.waitForSelector('#heatmap .plot-container', { timeout: 30000 });
    await sleep(1200);

    // 1) Fluency rating mode (grid colored by rubric) + roll-up strip.
    await page.selectOption('#metric-mode', 'fluency');
    await sleep(1000);
    await page.screenshot({ path: path.join(shotDir, 'analysis_fluency_mode.png') });
    console.log('  saved analysis_fluency_mode.png');

    // 2) Response-time fill + fluency overlay borders (see both at once).
    await page.selectOption('#metric-mode', 'response-time');
    await page.check('#fluency-overlay');
    await sleep(1000);
    await page.screenshot({ path: path.join(shotDir, 'analysis_overlay_mode.png') });
    console.log('  saved analysis_overlay_mode.png');

    await browser.close();
  } finally {
    server.kill('SIGTERM');
  }
  console.log('done');
}

main().catch(e => { console.error(e); process.exit(1); });
