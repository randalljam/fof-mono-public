import { test, expect } from '@playwright/test';
import { routeCdns, trackPageErrors, clickAnchorGo, fillAnchorUsername, stubFolderUsers } from './helpers.mjs';

async function startAssess(page, { name = 'TeachAny', multiply = false } = {}) {
  await page.goto('/anchor.html?setup=1&fb=0&teachms=0');
  await fillAnchorUsername(page, name);
  await page.check('#anchor-mode-new');
  if (multiply) {
    await page.uncheck('#op-add');
    await page.check('#op-mul');
  }
  await page.click('#anchor-start');
  await clickAnchorGo(page);
  await expect(page.locator('#anchor-problem')).toBeVisible({ timeout: 30_000 });
}

async function answerWrong(page) {
  const text = (await page.textContent('#anchor-problem')) || '';
  const m = text.match(/(-?\d+)\s*\+\s*(-?\d+)/);
  if (!m) throw new Error(`could not parse addition problem "${text}"`);
  const sum = Number(m[1]) + Number(m[2]);
  const wrong = sum >= 10 ? (sum < 18 ? sum + 1 : sum - 1) : (sum + 1) % 10;
  await page.locator('#anchor-answer').pressSequentially(String(wrong));
}

let pageErrors;
test.beforeEach(async ({ context, page }) => {
  await routeCdns(context);
  await stubFolderUsers(context, ['TeachHelp', 'TeachWrong', 'TeachSkip', 'TeachMul', 'TeachAny']);
  pageErrors = trackPageErrors(page);
});
test.afterEach(() => { expect(pageErrors).toEqual([]); });

test('assess lightbulb records a flagged pass and advances after teach', async ({ page }) => {
  await startAssess(page, { name: 'TeachHelp' });
  const firstProblem = await page.textContent('#anchor-problem');
  await expect(page.locator('#anchor-lightbulb')).toBeVisible();

  await page.click('#anchor-lightbulb');
  await expect(page.locator('#anchor-teach')).toBeVisible();
  await expect(page.locator('#anchor-teach svg[data-state="setup-answer"]')).toHaveCount(1);
  await expect(page.locator('#anchor-teach svg[data-state="result"]')).toHaveCount(1);
  await expect(page.locator('#anchor-teach-done')).toBeVisible();
  await page.click('#anchor-teach-done');

  await expect(page.locator('#anchor-teach')).toBeHidden();
  await expect(page.locator('#anchor-problem')).not.toHaveText(firstProblem || '');
  const first = await page.evaluate(() => window.__anchorSession()[0]);
  expect(first.is_correct).toBe(false);
  expect(first.user_answer).toBe(null);
  expect(first.flags).toHaveLength(1);
  expect(first.flags[0]).toMatchObject({ reason: 'lightbulb', label: '💡 Show ten-frames', notes: '' });
});

test('wrong assess answer shows teach visual above the correction panel', async ({ page }) => {
  await startAssess(page, { name: 'TeachWrong' });
  const firstProblem = await page.textContent('#anchor-problem');
  await answerWrong(page);

  await expect(page.locator('#anchor-teach')).toBeVisible();
  await expect(page.locator('#anchor-correction')).toBeVisible();
  await expect(page.locator('#anchor-correction-answer')).toContainText('Correct answer:');
  await expect(page.locator('#anchor-teach svg[data-state="setup-answer"]')).toHaveCount(1);
  await expect(page.locator('#anchor-teach svg[data-state="result"]')).toHaveCount(1);
  await expect(page.locator('#anchor-teach-done')).toBeHidden();
  const domOrder = await page.evaluate(() => {
    const quiz = document.getElementById('anchor-quiz');
    return [...quiz.children].map((el) => el.id).filter(Boolean);
  });
  expect(domOrder.indexOf('anchor-teach')).toBeLessThan(domOrder.indexOf('anchor-correction'));

  await page.click('#anchor-correct-continue');
  await expect(page.locator('#anchor-teach')).toBeHidden();
  await expect(page.locator('#anchor-correction')).toBeHidden();
  await expect(page.locator('#anchor-problem')).not.toHaveText(firstProblem || '');
});

test('Skip & flag panel keeps a review lightbulb without recording another attempt', async ({ page }) => {
  await startAssess(page, { name: 'TeachSkip' });
  await page.click('#anchor-skip-flag');
  await expect(page.locator('#anchor-correction')).toBeVisible();
  await expect(page.locator('#anchor-correction-answer')).toContainText('Correct answer:');
  await expect(page.locator('#anchor-flag-menu')).toBeVisible();
  await expect(page.locator('#anchor-lightbulb')).toBeVisible();

  await page.click('#anchor-lightbulb');
  await expect(page.locator('#anchor-teach')).toBeVisible();
  await expect(page.locator('#anchor-teach-done')).toBeVisible();
  await page.click('#anchor-teach-done');

  await expect(page.locator('#anchor-teach')).toBeHidden();
  await expect(page.locator('#anchor-correction')).toBeVisible();
  await expect(page.locator('#anchor-flag-menu')).toBeVisible();
  await expect(page.locator('#anchor-lightbulb')).toBeVisible();
  const count = await page.evaluate(() => window.__anchorSession().length);
  expect(count).toBe(1);

  await page.click('#anchor-correct-continue');
  await expect(page.locator('#anchor-correction')).toBeHidden();
  await expect(page.locator('#anchor-problem')).toBeVisible();
});

test('multiplication problems hide the teach lightbulb', async ({ page }) => {
  await startAssess(page, { name: 'TeachMultiply', multiply: true });
  await expect(page.locator('#anchor-problem')).toHaveText(/\d+\s*×\s*\d+/);
  await expect(page.locator('#anchor-lightbulb')).toBeHidden();
});
