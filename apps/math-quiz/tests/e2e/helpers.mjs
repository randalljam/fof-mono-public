// Shared E2E helpers: hermetic CDN routing, session-data builders, quiz drivers.
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect } from '@playwright/test';

const testsDir = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const nm = (...p) => path.join(testsDir, 'node_modules', ...p);

// The app loads its third-party libs from CDNs, which are blocked in sandboxed
// environments and flaky in CI. Serve the same pinned versions from
// node_modules instead so the suite is fully hermetic.
const CDN_FILES = [
  { pattern: /blueimp-md5.*md5(\.min)?\.js/, file: nm('blueimp-md5', 'js', 'md5.min.js'), type: 'text/javascript' },
  { pattern: /jszip.*jszip(\.min)?\.js/, file: nm('jszip', 'dist', 'jszip.min.js'), type: 'text/javascript' },
  { pattern: /canvas-confetti.*confetti\.browser(\.min)?\.js/, file: nm('canvas-confetti', 'dist', 'confetti.browser.js'), type: 'text/javascript' },
  { pattern: /sql\.js.*sql-wasm\.wasm/, file: nm('sql.js', 'dist', 'sql-wasm.wasm'), type: 'application/wasm' },
  { pattern: /sql\.js.*sql-wasm\.js/, file: nm('sql.js', 'dist', 'sql-wasm.js'), type: 'text/javascript' },
  { pattern: /cdn\.plot\.ly\/plotly-.*\.js/, file: nm('plotly.js-dist', 'plotly.js'), type: 'text/javascript' }
];

export async function routeCdns(context) {
  await context.route(/(cdnjs\.cloudflare\.com|cdn\.jsdelivr\.net|cdn\.plot\.ly)/, async (route) => {
    const url = route.request().url();
    const entry = CDN_FILES.find(e => e.pattern.test(url));
    if (!entry) {
      // Dragon (and other Three.js pages) load three from jsdelivr via import map —
      // let those through. Only abort truly unknown CDN URLs the hermetic suite
      // is not prepared to serve.
      if (/\/npm\/three@/.test(url)) return route.continue();
      console.warn(`Unmapped CDN request aborted: ${url}`);
      return route.abort();
    }
    await route.fulfill({ path: entry.file, contentType: entry.type });
  });
}

// Collect uncaught page errors so tests can assert none occurred
export function trackPageErrors(page) {
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  return errors;
}

// ----- Session JSON builders (same shape the quiz saves) -----
export function problemEntry(text, { correct = true, ms = 1500, flags = [], answer = 8 } = {}) {
  return {
    id: `id_${text.replace(/[^0-9a-z+*/^-]/gi, '')}_${Math.random().toString(16).slice(2, 8)}`,
    problem_text: text,
    correct_answer: answer,
    user_answer_string: correct ? String(answer) : String(answer + 1),
    user_answer: correct ? answer : answer + 1,
    is_correct: correct,
    response_time_ms: ms,
    flags
  };
}

export function flag(reason, notes = '') {
  return { reason, label: reason, timestamp: new Date().toISOString(), notes };
}

export function makeSession({ id, name = 'Kid1', startTime = '2026-06-01_100000', note = 'seeded', problems }) {
  return {
    version: '1.1',
    user: { name },
    session: {
      id,
      start_time: startTime,
      end_time: startTime.slice(0, 11) + '110000',
      settings: {
        preset: 'custom', description: '', note,
        num_problems: problems.length, number_range: [0, 9],
        numbers_include: [7], numbers_exclude: [], num_numbers: 2,
        operations: ['+', '-', '*', '/'], problem_list: []
      },
      summary: {
        total_problems: problems.length,
        correct_answers: problems.filter(p => p.is_correct).length,
        average_response_time_ms: 1500,
        total_test_time: '1:00'
      },
      problems
    }
  };
}

export async function seedSessions(context, sessions) {
  await context.addInitScript((seeded) => {
    for (const s of seeded) {
      const key = `math_session_${s.user.name}_${s.session.start_time}.json`;
      if (!localStorage.getItem(key)) {
        localStorage.setItem(key, JSON.stringify(s, null, 2));
      }
    }
  }, sessions);
}

// ----- Quiz drivers -----
export async function enterName(page, name = 'Tester') {
  await page.fill('#username-input', name);
  await page.click('#continue-button');
}

export async function startToggles(page, { audio = false, speech = false, autoSubmit = false } = {}) {
  if (!audio) await page.uncheck('#audio-enabled');
  if (!speech) await page.uncheck('#speech-detection-enabled');
  if (!autoSubmit) await page.uncheck('#auto-submit-enabled');
  await page.click('#start-assessment');
}

export async function startPresetQuiz(page, { name = 'Tester', preset = 't5', ...toggles } = {}) {
  await page.goto('/math_quiz.html');
  await enterName(page, name);
  await page.selectOption('#preset-select', preset);
  await page.click('#continue-button');
  await startToggles(page, toggles);
}

const OPS = {
  '+': (a, b) => a + b,
  '-': (a, b) => a - b,
  '*': (a, b) => a * b,
  '×': (a, b) => a * b,
  '/': (a, b) => a / b,
  '÷': (a, b) => a / b,
  '^': (a, b) => Math.pow(a, b)
};

export async function readProblem(page) {
  await expect(page.locator('#problem-text')).toBeVisible();
  const text = (await page.textContent('#problem-text')) || '';
  const match = text.match(/(-?[\d.]+)\s*([+\-×÷*/^])\s*(-?[\d.]+)/);
  if (!match) throw new Error(`Could not parse problem text: "${text}"`);
  const a = parseFloat(match[1]);
  const op = match[2];
  const b = parseFloat(match[3]);
  return { a, op, b, answer: OPS[op](a, b) };
}

export async function answerCurrentProblem(page, value) {
  const answer = value === undefined ? (await readProblem(page)).answer : value;
  await page.fill('#answer-input', String(answer));
  await page.press('#answer-input', 'Enter');
}

export async function completeQuiz(page, numProblems, { wrongOn = [] } = {}) {
  for (let i = 1; i <= numProblems; i++) {
    await expect(page.locator('.problem-count')).toHaveText(`Problem ${i} of ${numProblems}`, { timeout: 15_000 });
    const { answer } = await readProblem(page);
    await answerCurrentProblem(page, wrongOn.includes(i) ? answer + 1 : answer);
  }
  await expect(page.locator('#summary')).toBeVisible({ timeout: 15_000 });
}

export async function finishToDownload(page, additionalNote = '') {
  if (additionalNote) await page.fill('#additional-note-input', additionalNote);
  await page.click('#submit-additional-note');
  await expect(page.locator('#download-section')).toBeVisible();
}

// The analysis page's problem list starts collapsed (width 0, covered by the
// heatmap); expand it before interacting with sort buttons or list items
export async function openProblemList(page) {
  await page.click('#toggle-problem-list');
  await expect(page.locator('.problem-list-wrapper')).not.toHaveClass(/collapsed/);
}

export async function getSavedSessions(page) {
  return page.evaluate(() => {
    const sessions = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key.startsWith('math_session_') && key.endsWith('.json')) {
        sessions.push({ key, data: JSON.parse(localStorage.getItem(key)) });
      }
    }
    return sessions;
  });
}

// Tap the Go gate overlay on anchor.html before the first quiz problem.
export async function clickAnchorGo(page) {
  const overlay = page.locator('#anchor-go-overlay');
  await expect(overlay).toBeVisible({ timeout: 30_000 });
  await expect(page.locator('#anchor-go')).toBeVisible();
  await page.click('#anchor-go');
  await expect(overlay).toBeHidden();
}

// Stub /api/folder-users so typed learner names count as "known" in the anchor
// username combobox (the app forces start-new-file mode for unknown names and
// skips the continue-latest lookup entirely). Passing every name a spec types
// restores the pre-combobox semantics the specs assert. `target` may be a page
// or a context.
export async function stubFolderUsers(target, users) {
  // Accept plain name strings or full {name,label,filename} entries (kid landing API shape).
  const normalized = (users || []).map((u) => (
    typeof u === 'string'
      ? { name: u, label: u, filename: `math-flu_${u}.sqlite` }
      : u
  ));
  await target.route(/\/api\/folder-users/, (route) => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({ ok: true, users: normalized }),
  }));
}

// The username field starts readonly (combobox); click/focus unlocks typing for e2e.
export async function fillAnchorUsername(page, name) {
  const inp = page.locator('#anchor-username');
  await inp.click();
  await inp.fill(name);
  await inp.press('Escape'); // close the learner dropdown so it doesn't steal later clicks
  await inp.blur();
}
