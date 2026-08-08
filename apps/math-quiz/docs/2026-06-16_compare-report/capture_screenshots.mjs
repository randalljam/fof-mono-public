// Capture screenshots of the OLD quiz (math_quiz.html) and the NEW anchor page
// (anchor.html) for the version-comparison report (index.html in this folder).
//
// Hermetic: serves apps/math-quiz over a local static server and routes the
// app's CDN libraries (sql.js etc.) to the pinned copies in tests/node_modules,
// exactly like the e2e suite (tests/e2e/helpers.mjs -> routeCdns). Uses the
// Playwright-bundled chromium if present, else the npm @sparticuz/chromium
// binary (works where Playwright's browser CDN is blocked).
//
// Run from apps/math-quiz/ (needs tests/ deps installed):
//   cd apps/math-quiz/tests && npm install            # one time
//   node docs/2026-06-16_compare-report/capture_screenshots.mjs
//
// Output: docs/2026-06-16_compare-report/screenshots/*.png

import { spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { existsSync } from 'node:fs';

const here = path.dirname(fileURLToPath(import.meta.url));
const appDir = path.resolve(here, '..', '..');          // apps/math-quiz
const testsDir = path.join(appDir, 'tests');
const nm = (...p) => path.join(testsDir, 'node_modules', ...p);
const shotDir = path.join(here, 'screenshots');
const PORT = 8917;
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

async function shoot(page, name, selector) {
  const file = path.join(shotDir, name);
  let target = null;
  if (selector) {
    const el = await page.$(selector);
    if (el && await el.isVisible().catch(() => false)) target = el;
  }
  if (target) await target.screenshot({ path: file });
  else await page.screenshot({ path: file });
  console.log('  saved', name);
}

function parseProblem(text) {
  const m = (text || '').match(/(-?\d+)\s*([+\-×÷*/])\s*(-?\d+)/);
  if (!m) return null;
  const a = Number(m[1]), b = Number(m[3]);
  const op = m[2];
  const ans = op === '+' ? a + b : op === '-' ? a - b : (op === '×' || op === '*') ? a * b : a / b;
  return { a, b, op, ans };
}

async function main() {
  const { chromium } = (await import(nm('playwright-core', 'index.js'))).default;
  const executablePath = await resolveChromium();
  console.log('chromium:', executablePath);

  const server = startServer();
  try {
    await waitForServer(`${BASE}/math_quiz.html`);
    const browser = await chromium.launch({ executablePath, args: ['--no-sandbox', '--disable-dev-shm-usage'] });
    const context = await browser.newContext({ viewport: { width: 720, height: 1180 }, deviceScaleFactor: 2 });
    await context.route(/(cdnjs\.cloudflare\.com|cdn\.jsdelivr\.net|cdn\.plot\.ly)/, async (route) => {
      const entry = CDN_FILES.find(e => e.pattern.test(route.request().url()));
      if (!entry) return route.abort();
      await route.fulfill({ path: entry.file, contentType: entry.type });
    });
    // auto-accept confirm() dialogs (anchor Quit buttons)
    context.on('page', p => p.on('dialog', d => d.accept().catch(() => {})));

    const page = await context.newPage();
    page.on('dialog', d => d.accept().catch(() => {}));

    // ---------- OLD: math_quiz.html ----------
    console.log('OLD math_quiz.html');
    await page.goto(`${BASE}/math_quiz.html`);
    await page.waitForSelector('#username-input, #continue-button', { timeout: 15000 });
    await sleep(400);
    await shoot(page, '01_old_welcome.png', '#container');

    try {
      await page.fill('#username-input', 'Kid1');
      await page.click('#continue-button');
      await page.waitForSelector('#preset-select', { timeout: 8000 });
      await sleep(300);
      await shoot(page, '02_old_presets.png', '#container');
      // pick the 20-problem assessment preset if present, else first option
      const presetVals = await page.$$eval('#preset-select option', os => os.map(o => o.value));
      const preset = presetVals.includes('t20') ? 't20' : presetVals.includes('t5') ? 't5' : presetVals[0];
      await page.selectOption('#preset-select', preset);
      await page.click('#continue-button');
      await page.waitForSelector('#start-assessment', { timeout: 8000 });
      await sleep(300);
      await shoot(page, '03_old_settings.png', '#container');
      // turn off audio/speech/auto-submit if present, then start
      for (const id of ['#audio-enabled', '#speech-detection-enabled', '#auto-submit-enabled']) {
        const el = await page.$(id);
        if (el && await el.isChecked()) await el.uncheck();
      }
      await page.click('#start-assessment');
      await page.waitForSelector('#problem-text', { timeout: 8000 });
      await sleep(500);
      await shoot(page, '04_old_problem.png', '#container');
    } catch (e) {
      console.warn('  old-quiz deep nav stopped:', e.message);
    }

    // ---------- NEW: anchor.html ----------
    console.log('NEW anchor.html');
    const ap = await context.newPage();
    ap.on('dialog', d => d.accept().catch(() => {}));
    await ap.goto(`${BASE}/anchor.html`);
    await ap.waitForSelector('#anchor-setup', { timeout: 15000 });
    await sleep(500);
    await shoot(ap, '05_anchor_setup.png', '.wrap');

    try {
      await ap.fill('#anchor-username', 'Kid1');
      await ap.click('#anchor-start');
      // Warm-up (practice entering numbers) is on by default -> keypad appears
      await ap.waitForSelector('#anchor-quiz:not(.hidden)', { timeout: 8000 });
      await sleep(600);
      await shoot(ap, '06_anchor_warmup.png', '.wrap');

      // Skip the warm-up into the real quiz
      const skip = await ap.$('#anchor-practice-skip');
      if (skip) { await skip.click(); await sleep(500); }
      await ap.waitForSelector('#anchor-problem', { timeout: 8000 });
      await sleep(500);
      await shoot(ap, '07_anchor_quiz.png', '.wrap');

      // Solve the curated plan fast+correct so it concludes "fluent",
      // then Stop here at the predictive-mastery prompt -> summary.
      for (let i = 0; i < 120; i++) {
        if (await ap.$('#anchor-summary:not(.hidden)')) break;
        const promptVisible = await ap.$('#anchor-prompt:not(.hidden)');
        if (promptVisible) { await ap.click('#anchor-stop'); await sleep(500); break; }
        const guard = await ap.$('#anchor-guardrail:not(.hidden)');
        if (guard) { await ap.click('#anchor-guardrail-continue'); await sleep(150); continue; }
        const txt = await ap.textContent('#anchor-problem').catch(() => null);
        const p = parseProblem(txt);
        if (!p) { await sleep(120); continue; }
        await ap.fill('#anchor-answer', '');
        await ap.locator('#anchor-answer').pressSequentially(String(p.ans), { delay: 15 });
        // auto-submit advances once digit count is reached; nudge with Enter otherwise
        await ap.press('#anchor-answer', 'Enter').catch(() => {});
        await sleep(140);
      }
      // if a prompt is up, stop here for the fluent summary
      if (await ap.$('#anchor-prompt:not(.hidden)')) { await ap.click('#anchor-stop'); await sleep(500); }
      if (await ap.$('#anchor-summary:not(.hidden)')) {
        await sleep(400);
        await shoot(ap, '08_anchor_summary.png', '.wrap');
      } else {
        console.warn('  anchor summary not reached');
      }
    } catch (e) {
      console.warn('  anchor deep nav stopped:', e.message);
    }

    await browser.close();
  } finally {
    server.kill('SIGTERM');
  }
  console.log('done');
}

main().catch(e => { console.error(e); process.exit(1); });
