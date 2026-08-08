import { test, expect } from '@playwright/test';
import {
  routeCdns, trackPageErrors, seedSessions, makeSession, problemEntry,
  enterName, startToggles, completeQuiz, finishToDownload, getSavedSessions
} from './helpers.mjs';

// Two sessions for Kid1: a fast addition fact (green, seen in both sessions),
// a slow one (red), a missed one (gray), and a legacy-format multiplication.
const SESSIONS = [
  makeSession({
    id: 'sf1', name: 'Kid1', startTime: '2026-06-01_100000',
    problems: [
      problemEntry('2 + 3', { ms: 900, answer: 5 }),
      problemEntry('7 + 1', { ms: 5000, answer: 8 }),
      problemEntry('9 + 9', { ms: 3000, answer: 18, correct: false }),
      problemEntry('5 &times; 3', { ms: 1200, answer: 15 })
    ]
  }),
  makeSession({
    id: 'sf2', name: 'Kid1', startTime: '2026-06-02_100000',
    problems: [problemEntry('2 + 3', { ms: 800, answer: 5 })]
  })
];

let pageErrors;
test.beforeEach(async ({ context, page }) => {
  await routeCdns(context);
  await seedSessions(context, SESSIONS);
  pageErrors = trackPageErrors(page);
  await page.goto('/math_fluency.html');
  await expect(page.locator('#addition-current .plot-container')).toBeVisible({ timeout: 30_000 });
});

test.afterEach(() => {
  expect(pageErrors).toEqual([]);
});

test('tracker builds datasets including legacy-format multiplication', async ({ page }) => {
  const datasets = await page.evaluate(() => ({
    addition: Object.fromEntries(Object.entries(fluencyDatasets.addition.combined).map(([k, v]) => [k, v.status])),
    multiplication: Object.fromEntries(Object.entries(fluencyDatasets.multiplication.combined).map(([k, v]) => [k, v.status]))
  }));
  expect(datasets.addition).toEqual({ '+|2|3': 'green', '+|1|7': 'red', '+|9|9': 'gray' });
  // P1 regression: '5 &times; 3' must reach the multiplication dataset
  expect(datasets.multiplication).toEqual({ '*|3|5': 'green' });

  // App-wide fluencyPercent: fluent share of the FULL 0-9 universe (100 ordered facts),
  // so one green fact = 1% — same number as the anchor readout and Fluency feast.
  await expect(page.locator('#addition-percentage')).toHaveText('1%');
  await expect(page.locator('#multiplication-percentage')).toHaveText('1%');
  // needs-work grid: gray and red problems listed
  await expect(page.locator('#addition-problem-grid .problem-item')).toHaveCount(2);
});

test('rubric parameter changes recompute the app-wide percentage', async ({ page }) => {
  // greenMs 6000: '7 + 1' (median 5000 ms) turns green alongside '2 + 3' -> 2 of 100 facts.
  await page.fill('#fluency-green-ms', '6000');
  await page.dispatchEvent('#fluency-green-ms', 'change');
  await expect(page.locator('#addition-percentage')).toHaveText('2%');
});

test('manual status override via the edit dialog', async ({ page }) => {
  await page.locator('#addition-problem-grid .problem-item-clickable', { hasText: '1 + 7' }).click();
  await expect(page.locator('.status-edit-dialog')).toBeVisible();
  await page.selectOption('#edit-status', 'green');
  await page.fill('#edit-reason', 'knows it, was distracted');
  await page.click('[data-action="save-edit"]');

  await expect(page.locator('.status-edit-dialog')).toHaveCount(0);
  const overridden = await page.evaluate(() => fluencyDatasets.addition.combined['+|1|7']);
  expect(overridden.status).toBe('green');
  expect(overridden.manualOverride).toBe(true);
  expect(overridden.calculatedStatus).toBe('red');
  // The app-wide % is computed from raw attempts via the shared rubric, so a manual
  // dashboard override does not move it.
  await expect(page.locator('#addition-percentage')).toHaveText('1%');

  const stored = await page.evaluate(() => JSON.parse(localStorage.getItem('math_fluency_manual_overrides')));
  expect(stored.default['+|1|7'].status).toBe('green');
  expect(stored.default['+|1|7'].reason).toBe('knows it, was distracted');
});

test('permanent (blue) status appears after N consecutive green sessions', async ({ page }) => {
  // '2 + 3' was green in both sessions; with the threshold at 1 it becomes permanent
  await page.fill('#fluency-permanent-sessions', '1');
  await page.dispatchEvent('#fluency-permanent-sessions', 'change');
  const status = await page.evaluate(() => fluencyDatasets.addition.combined['+|2|3'].status);
  expect(status).toBe('blue');
  // the app-wide % counts the fact as fluent either way (green or blue)
  await expect(page.locator('#addition-percentage')).toHaveText('1%');
});

test('generated problem list flows into the quiz and back to a session file', async ({ page }) => {
  await page.click('#generate-problem-list-btn');
  await expect(page.locator('#problem-list-generator-modal')).toBeVisible();
  await page.fill('#gen-total-problems', '2');
  for (const [status, pct] of [['blue', '0'], ['green', '50'], ['yellow', '0'], ['red', '50'], ['gray', '0']]) {
    await page.fill(`#gen-pct-${status}`, pct);
  }
  await page.click('#gen-use-in-quiz');

  await page.waitForURL('**/math_quiz.html');
  await enterName(page, 'Kid1');
  // generated list auto-selects the problem-list preset
  await expect(page.locator('#preset-select')).toHaveValue('problem-list');
  await page.click('#continue-button');
  await startToggles(page);
  await completeQuiz(page, 2);
  await finishToDownload(page);

  const sessions = await getSavedSessions(page);
  const quizSession = sessions.find(s => s.data.session.settings.preset === 'problem_list');
  expect(quizSession).toBeTruthy();
  expect(quizSession.data.session.settings.problem_list_metadata.source).toBe('fluency-tracker');
  expect(quizSession.data.session.problems.length).toBe(2);
  for (const problem of quizSession.data.session.problems) {
    expect(problem.problem_text).toMatch(/^\d+ [+*] \d+$/);
  }
});
