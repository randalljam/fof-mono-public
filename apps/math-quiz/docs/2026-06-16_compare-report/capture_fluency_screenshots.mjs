// Capture screenshots of the CURRENT fluency tracker page (math_fluency.html)
// for the fluency report (fluency.html in this folder).
//
// Hermetic, same approach as capture_screenshots.mjs: serves apps/math-quiz over
// a local static server, routes the app's CDN libraries (sql.js, plotly) to the
// pinned copies in tests/node_modules, and uses the Playwright-bundled chromium
// if present, else the npm @sparticuz/chromium binary.
//
// The fluency page renders nothing without data, so this script SEEDS a small,
// engineered multi-session history into localStorage (same JSON shape the quiz
// saves) before loading the page. The seed is designed to surface every rubric
// status — blue/green/yellow/red/gray — plus a "needs re-check" fact.
//
// Run from apps/math-quiz/ (needs tests/ deps installed):
//   cd apps/math-quiz/tests && npm install            # one time
//   node docs/2026-06-16_compare-report/capture_fluency_screenshots.mjs
//
// Output: docs/2026-06-16_compare-report/screenshots/fluency_*.png

import { spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { existsSync } from 'node:fs';

const here = path.dirname(fileURLToPath(import.meta.url));
const appDir = path.resolve(here, '..', '..');          // apps/math-quiz
const testsDir = path.join(appDir, 'tests');
const nm = (...p) => path.join(testsDir, 'node_modules', ...p);
const shotDir = path.join(here, 'screenshots');
const PORT = 8918;
const BASE = `http://127.0.0.1:${PORT}`;

// Same pinned-CDN -> local-file map the e2e helpers use.
const CDN_FILES = [
  { pattern: /blueimp-md5.*md5(\.min)?\.js/, file: nm('blueimp-md5', 'js', 'md5.min.js'), type: 'text/javascript' },
  { pattern: /jszip.*jszip(\.min)?\.js/, file: nm('jszip', 'dist', 'jszip.min.js'), type: 'text/javascript' },
  { pattern: /canvas-confetti.*confetti\.browser(\.min)?\.js/, file: nm('canvas-confetti', 'dist', 'confetti.browser.js'), type: 'text/javascript' },
  { pattern: /sql\.js.*sql-wasm\.wasm/, file: nm('sql.js', 'dist', 'sql-wasm.wasm'), type: 'application/wasm' },
  { pattern: /sql\.js.*sql-wasm\.js/, file: nm('sql.js', 'dist', 'sql-wasm.js'), type: 'text/javascript' },
  { pattern: /cdn\.plot\.ly\/plotly-.*\.js/, file: nm('plotly.js-dist', 'plotly.js'), type: 'text/javascript' }
];

// ----- Seed data: an engineered multi-session addition history for one learner.
// Six sessions (oldest -> newest). Each fact's `in` lists the session indices it
// was attempted in; status emerges from response time + correctness + recurrence:
//   blue   = fast+correct in >=5 sessions (permanent)
//   green  = fast+correct in fewer sessions (fluent, not yet permanent)
//   yellow = correct but 2-4s
//   red    = correct but >=4s
//   gray   = low accuracy (wrong)
//   recheck = fast+correct but not seen in the last 3 sessions (blue border)
const DATES = ['2026-06-10', '2026-06-11', '2026-06-12', '2026-06-13', '2026-06-14', '2026-06-15'];
const FACTS = [
  // blue (permanent): fast + correct in all six sessions
  { text: '2 + 3', ans: 5, in: [0, 1, 2, 3, 4, 5], ms: 820 },
  { text: '1 + 4', ans: 5, in: [0, 1, 2, 3, 4, 5], ms: 760 },
  { text: '0 + 7', ans: 7, in: [0, 1, 2, 3, 4, 5], ms: 690 },
  { text: '3 + 3', ans: 6, in: [0, 1, 2, 3, 4, 5], ms: 900 },
  // green (fluent, not yet permanent): fast + correct, only recent sessions
  { text: '4 + 5', ans: 9, in: [4, 5], ms: 1500 },
  { text: '2 + 6', ans: 8, in: [3, 4, 5], ms: 1650 },
  // yellow (almost fluent): correct but slow (2-4s)
  { text: '6 + 7', ans: 13, in: [2, 3, 4, 5], ms: 3000 },
  { text: '7 + 8', ans: 15, in: [3, 4, 5], ms: 3300 },
  // red (needs practice): correct but very slow (>=4s)
  { text: '8 + 9', ans: 17, in: [2, 3, 4, 5], ms: 5200 },
  { text: '6 + 9', ans: 15, in: [3, 4, 5], ms: 4600 },
  // gray (missing / doesn't know): low accuracy
  { text: '7 + 9', ans: 16, in: [2, 3, 4, 5], ms: 3800, wrong: true },
  { text: '5 + 8', ans: 13, in: [3, 4, 5], ms: 4200, wrong: true },
  // needs re-check: fast + correct but only in the two oldest sessions
  { text: '9 + 1', ans: 10, in: [0, 1], ms: 780 }
];

function buildSeedSessions(name = 'Ada') {
  return DATES.map((date, idx) => {
    const start = `${date}_100000`;
    const problems = FACTS.filter(f => f.in.includes(idx)).map(f => {
      const correct = !f.wrong;
      return {
        id: `id_${f.text.replace(/[^0-9a-z+]/gi, '')}_${idx}`,
        problem_text: f.text,
        correct_answer: f.ans,
        user_answer_string: correct ? String(f.ans) : String(f.ans + 1),
        user_answer: correct ? f.ans : f.ans + 1,
        is_correct: correct,
        response_time_ms: f.ms,
        flags: []
      };
    });
    return {
      version: '1.1',
      user: { name },
      session: {
        id: `seed_${idx}`,
        start_time: start,
        end_time: start.slice(0, 11) + '110000',
        settings: {
          preset: 'custom', description: '', note: 'seeded for screenshots',
          num_problems: problems.length, number_range: [0, 9],
          numbers_include: [], numbers_exclude: [], num_numbers: 2,
          operations: ['+'], problem_list: []
        },
        summary: {
          total_problems: problems.length,
          correct_answers: problems.filter(p => p.is_correct).length,
          average_response_time_ms: 1800,
          total_test_time: '1:00'
        },
        problems
      }
    };
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
  const proc = spawn('python3', ['-m', 'http.server', String(PORT), '--bind', '127.0.0.1', '--directory', appDir], { stdio: 'ignore' });
  return proc;
}

async function waitForServer(url, tries = 40) {
  for (let i = 0; i < tries; i++) {
    try { const r = await fetch(url); if (r.ok) return; } catch { /* retry */ }
    await new Promise(r => setTimeout(r, 250));
  }
  throw new Error(`server not up at ${url}`);
}

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

async function shootEl(page, name, selector) {
  const file = path.join(shotDir, name);
  const el = await page.$(selector);
  if (el && await el.isVisible().catch(() => false)) {
    await el.screenshot({ path: file });
    console.log('  saved', name);
  } else {
    console.warn('  selector not visible, skipped', name, selector);
  }
}

async function shootClipToBottomOf(page, name, selector, viewportWidth) {
  const file = path.join(shotDir, name);
  const box = await (await page.$(selector))?.boundingBox();
  if (!box) { console.warn('  no box for', selector); return; }
  await page.screenshot({ path: file, clip: { x: 0, y: 0, width: viewportWidth, height: Math.ceil(box.y + box.height + 12) } });
  console.log('  saved', name);
}

async function main() {
  const { chromium } = (await import(nm('playwright-core', 'index.js'))).default;
  const executablePath = await resolveChromium();
  console.log('chromium:', executablePath);

  const VIEW = { width: 1120, height: 1500 };
  const server = startServer();
  try {
    await waitForServer(`${BASE}/math_fluency.html`);
    const browser = await chromium.launch({ executablePath, args: ['--no-sandbox', '--disable-dev-shm-usage'] });
    const context = await browser.newContext({ viewport: VIEW, deviceScaleFactor: 2 });
    await context.route(/(cdnjs\.cloudflare\.com|cdn\.jsdelivr\.net|cdn\.plot\.ly)/, async (route) => {
      const entry = CDN_FILES.find(e => e.pattern.test(route.request().url()));
      if (!entry) return route.abort();
      await route.fulfill({ path: entry.file, contentType: entry.type });
    });

    // Seed the learner history into localStorage before the page loads.
    const sessions = buildSeedSessions('Ada');
    await context.addInitScript((seeded) => {
      for (const s of seeded) {
        const key = `math_session_${s.user.name}_${s.session.start_time}.json`;
        if (!localStorage.getItem(key)) localStorage.setItem(key, JSON.stringify(s, null, 2));
      }
    }, sessions);

    const page = await context.newPage();
    page.on('dialog', d => d.accept().catch(() => {}));
    page.on('console', m => { if (m.type() === 'error') console.warn('  page error:', m.text()); });

    console.log('fluency tracker (math_fluency.html)');
    await page.goto(`${BASE}/math_fluency.html`);
    // Wait for the addition grids to render (Plotly container present).
    await page.waitForSelector('#addition-current .plot-container', { timeout: 30000 });
    await sleep(900);

    // 1) Controls + rubric legend (top of page through the status legend).
    await shootClipToBottomOf(page, 'fluency_01_controls_legend.png', '.status-legend', VIEW.width);

    // 1b) The overhauled overview dashboard (operation / 0-5·6-9 / category roll-ups).
    await shootEl(page, 'fluency_04_overview.png', '#fluency-overview');

    // 2) The addition section: percentage, current + historical grids, summary
    //    stats, and the "problems needing work" list.
    await shootEl(page, 'fluency_02_addition_section.png', '#addition-section');

    // 3) The per-fact manual-override edit dialog (click a needs-work problem).
    const item = await page.$('#addition-problem-grid .problem-item-clickable');
    if (item) {
      await item.click();
      await page.waitForSelector('.status-edit-dialog .dialog-content', { timeout: 8000 });
      await sleep(300);
      await shootEl(page, 'fluency_03_edit_dialog.png', '.dialog-content');
    } else {
      console.warn('  no clickable needs-work item found for edit dialog shot');
    }

    await browser.close();
  } finally {
    server.kill('SIGTERM');
  }
  console.log('done');
}

main().catch(e => { console.error(e); process.exit(1); });
