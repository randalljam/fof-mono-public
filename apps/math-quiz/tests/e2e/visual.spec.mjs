// E2E for visual practice on the anchor page: pick "Visual practice",
// prefill targets/filler, teach with two-state ten-frames after a miss/pass,
// then clear through filler-spaced retrieval while recording trial roles.
import { test, expect } from '@playwright/test';
import { routeCdns, trackPageErrors, clickAnchorGo, fillAnchorUsername, stubFolderUsers } from './helpers.mjs';

const OP = { '+': (a, b) => a + b, '−': (a, b) => a - b, '×': (a, b) => a * b };

async function answerCurrent(page, value) {
  const text = (await page.textContent('#anchor-problem')) || '';
  const m = text.match(/(-?\d+)\s*([+−×])\s*(-?\d+)/);
  if (!m) throw new Error(`could not parse problem "${text}"`);
  const answer = value === undefined ? OP[m[2]](Number(m[1]), Number(m[3])) : value;
  await page.locator('#anchor-answer').pressSequentially(String(answer));
}

async function compactProblem(page) {
  return ((await page.textContent('#anchor-problem')) || '').replace(/\s/g, '');
}

function isTargetProblem(text) {
  return /^(8\+3|3\+8)$/.test(text);
}

async function pickVisual(page, name = 'Tester') {
  await page.goto('/anchor.html?setup=1&fb=0&teachms=0');
  await fillAnchorUsername(page, name);
  await page.check('#anchor-mode-new');
  await page.selectOption('#anchor-problem-list-file', '__visual__');
  await expect(page.locator('#anchor-visual-config')).toBeVisible();
}

async function startVisual(page, { name = 'Tester', targets = ['8+3'], filler = ['0 + 8', '1 + 6', '2 + 7'], clears = 1 } = {}) {
  await pickVisual(page, name);
  for (let i = 1; i <= 5; i++) await page.fill(`#anchor-vtarget-${i}`, targets[i - 1] || '');
  await page.fill('#anchor-visual-filler-text', filler.join('\n'));
  await page.fill('#anchor-visual-clears', String(clears));
  await page.click('#anchor-start');
  await clickAnchorGo(page);
  await expect(page.locator('#anchor-problem')).toBeVisible({ timeout: 30_000 });
}

let pageErrors;
test.beforeEach(async ({ context, page }) => {
  await routeCdns(context);
  await stubFolderUsers(context, ['Kid1', 'Tester', 'TeachHelp', 'TeachWrong', 'TeachSkip', 'TeachMul']);
  await context.route(/\/api\/visual-config/, (route) => route.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, visualConfig: {} }),
  }));
  pageErrors = trackPageErrors(page);
});
test.afterEach(() => { expect(pageErrors).toEqual([]); });

test('selecting Visual practice prefills Kid1 defaults and shows the secure filler editor', async ({ page }) => {
  await pickVisual(page, 'Kid1');
  await expect(page.locator('#anchor-vtarget-1')).toHaveValue('8+3');
  await expect(page.locator('#anchor-vtarget-3')).toHaveValue('6+8');
  await expect(page.locator('#anchor-visual-filler-editor')).toBeVisible();
  await expect(page.locator('#anchor-visual-filler-text')).toHaveValue(/0\s*\+\s*8/);
  await expect(page.locator('#anchor-visual-hesitation')).toHaveCount(0);
});

test('visual practice rejects targets the ten-frame renderer cannot teach', async ({ page }) => {
  await pickVisual(page);
  await page.fill('#anchor-vtarget-1', '3*4');
  for (let i = 2; i <= 5; i++) await page.fill(`#anchor-vtarget-${i}`, '');
  await page.click('#anchor-start');
  await expect(page.locator('#anchor-error')).toContainText(
    'Visual practice supports addition facts with totals up to 20');
  await expect(page.locator('#anchor-setup')).toBeVisible();
});

test('wrong cold probe opens in-place teach, then fillers precede delayed retrieval clear', async ({ page }) => {
  page.on('dialog', (d) => d.accept());
  let savePayload = null;
  await page.route(/\/api\/health/, (route) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) }));
  await page.route(/\/api\/save-run/, (route) => {
    savePayload = JSON.parse(route.request().postData() || '{}');
    route.fulfill({ status: 200, contentType: 'application/json',
      body: JSON.stringify({ ok: true, action: 'create', filename: 'math-flu_Tester_x.sqlite', localPath: '/tmp/x' }) });
  });

  await startVisual(page, { targets: ['8+3'], clears: 1 });
  await expect(page.locator('#anchor-lightbulb')).toBeVisible();
  await answerCurrent(page, 10);                                  // wrong cold probe

  await expect(page.locator('#anchor-teach')).toBeVisible();
  await expect(page.locator('#anchor-quiz-main')).toBeHidden();
  await expect(page.locator('#anchor-keypad')).toBeHidden();
  await expect(page.locator('#anchor-teach svg[data-state="setup-answer"]')).toHaveCount(1);
  await expect(page.locator('#anchor-teach svg[data-state="result"]')).toHaveCount(1);
  await expect(page.locator('#anchor-teach-done')).toBeVisible();
  await page.click('#anchor-teach-done');

  await expect.poll(() => compactProblem(page)).not.toMatch(/^(8\+3|3\+8)$/);
  await expect(page.locator('#anchor-lightbulb')).toBeVisible();
  await answerCurrent(page);                                      // first filler after teach

  for (let i = 0; i < 12; i++) {
    if (isTargetProblem(await compactProblem(page))) break;
    await expect(page.locator('#anchor-lightbulb')).toBeVisible();
    await answerCurrent(page);
  }
  await expect.poll(() => compactProblem(page)).toMatch(/^(8\+3|3\+8)$/);
  await expect(page.locator('#anchor-lightbulb')).toBeVisible();
  await answerCurrent(page);                                      // delayed retrieval clears

  await expect(page.locator('#anchor-grad-continue')).toBeVisible({ timeout: 30_000 });
  await page.click('#anchor-grad-continue');
  // Session ends right on the final clear — no trailing questions.
  await expect(page.locator('#anchor-summary')).toBeVisible({ timeout: 30_000 });
  await expect(page.locator('#anchor-summary-title')).toContainText('Pictures practiced');
  await expect(page.locator('#anchor-summary-body')).toContainText('cold: wrong');

  const roles = await page.evaluate(() => window.__anchorSession().map((p) => p.visual_practice && p.visual_practice.trial_role));
  expect(roles).toContain('cold-probe');
  expect(roles).toContain('delayed-retrieval');
  expect(roles).toContain('filler');
  expect(roles).not.toContain('immediate-retrieval');

  const imported = await page.evaluate(() => {
    const db = window.__anchorStore.db;
    const sessionType = db.exec('SELECT session_type FROM Sessions ORDER BY rowid DESC LIMIT 1')[0].values[0][0];
    const visual = db.exec('SELECT outcome, complete, retrievals_to_clear FROM VisualPracticeSessions')[0].values[0];
    return { sessionType, visual };
  });
  expect(imported.sessionType).toBe('visual-practice');
  expect(imported.visual).toEqual(['visual-complete', 1, 1]);
  await expect.poll(() => savePayload, { timeout: 10_000 }).not.toBeNull();
  expect(savePayload.visualConfig).toMatchObject({ targets: ['8+3'], retrievalsToClear: 1 });
  expect(savePayload.visualConfig).not.toHaveProperty('hesitationMs');
});

test('lightbulb records a passed visual attempt and opens teach', async ({ page }) => {
  page.on('dialog', (d) => d.accept());
  await startVisual(page, { targets: ['8+3'], clears: 1 });
  await expect(page.locator('#anchor-lightbulb')).toBeVisible();
  await page.click('#anchor-lightbulb');
  await expect(page.locator('#anchor-teach')).toBeVisible();
  await expect(page.locator('#anchor-teach svg[data-state="setup-answer"]')).toHaveCount(1);
  await expect(page.locator('#anchor-teach svg[data-state="result"]')).toHaveCount(1);

  const first = await page.evaluate(() => window.__anchorSession()[0]);
  expect(first.is_correct).toBe(false);
  expect(first.visual_practice).toMatchObject({
    trial_role: 'cold-probe',
    target_key: '+|3|8',
    visual_shown: true,
    passed: true,
  });
});
