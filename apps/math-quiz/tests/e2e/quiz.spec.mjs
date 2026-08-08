import { test, expect } from '@playwright/test';
import {
  routeCdns, trackPageErrors, startPresetQuiz, enterName, startToggles,
  readProblem, answerCurrentProblem, completeQuiz, finishToDownload, getSavedSessions
} from './helpers.mjs';

test.beforeEach(async ({ context }) => {
  await routeCdns(context);
});

test('complete a preset quiz with all correct answers', async ({ page }) => {
  const errors = trackPageErrors(page);
  await startPresetQuiz(page, { name: 'E2E Tester', preset: 't5' });
  await completeQuiz(page, 5);

  await expect(page.locator('#summary')).toContainText('Total problems attempted: 5');
  await expect(page.locator('#summary')).toContainText('Number of correct answers: 5');
  await finishToDownload(page, 'e2e run');

  const sessions = await getSavedSessions(page);
  expect(sessions.length).toBe(1);
  const session = sessions[0].data;
  expect(session.user.name).toBe('E2E Tester');
  expect(session.session.problems.length).toBe(5);
  expect(session.session.summary.correct_answers).toBe(5);
  expect(session.session.settings.note).toContain('POST QUIZ: e2e run');
  for (const problem of session.session.problems) {
    expect(problem.is_correct).toBe(true);
    // canonical problem_text: no display entities
    expect(problem.problem_text).toMatch(/^\d+ [+\-*/^] \d+$/);
  }
  expect(errors).toEqual([]);
});

test('custom multiplication quiz records canonical problem_text and shows × on screen', async ({ page }) => {
  const errors = trackPageErrors(page);
  await page.goto('/math_quiz.html');
  await enterName(page);
  // empty value = Custom
  await page.selectOption('#preset-select', '');
  await page.click('#continue-button');
  await page.fill('#num-problems-input', '3');
  await page.fill('#min-range-input', '2');
  await page.fill('#max-range-input', '5');
  await page.fill('#operations-input', '*');
  await page.click('#submit-custom-settings');
  await startToggles(page);

  // on-screen problem uses the × display symbol
  await expect(page.locator('#problem-text')).toContainText('×');
  await completeQuiz(page, 3);
  await finishToDownload(page);

  const [saved] = await getSavedSessions(page);
  for (const problem of saved.data.session.problems) {
    expect(problem.problem_text).toMatch(/^\d+ \* \d+$/);
  }
  expect(errors).toEqual([]);
});

test('wrong answer shows the correct answer and override marks it correct', async ({ page }) => {
  await startPresetQuiz(page, { preset: 't1' });
  const { answer } = await readProblem(page);
  await answerCurrentProblem(page, answer + 1);

  await expect(page.locator('.feedback-message')).toContainText(`Incorrect. The correct answer is ${answer}`);
  await page.click('#override-button');
  await expect(page.locator('.feedback-message')).toContainText('Override applied');

  await expect(page.locator('#summary')).toBeVisible({ timeout: 15_000 });
  await expect(page.locator('#summary')).toContainText('Number of correct answers: 1');
  await finishToDownload(page);
  const [saved] = await getSavedSessions(page);
  expect(saved.data.session.problems[0].is_correct).toBe(true);
  expect(saved.data.session.problems[0].user_answer).toBe(answer);
});

test('"I don\'t know" records a dontknow flag with an empty answer', async ({ page }) => {
  await startPresetQuiz(page, { preset: 't1' });
  await readProblem(page);
  await page.click('#dont-know-btn');
  await expect(page.locator('.feedback-message')).toContainText('Incorrect');

  await expect(page.locator('#summary')).toBeVisible({ timeout: 15_000 });
  await finishToDownload(page);
  const [saved] = await getSavedSessions(page);
  const problem = saved.data.session.problems[0];
  expect(problem.is_correct).toBe(false);
  expect(problem.flags.length).toBe(1);
  expect(problem.flags[0].reason).toBe('dontknow');
});

test('flag dropdown with comment is saved on the attempt', async ({ page }) => {
  await startPresetQuiz(page, { preset: 't1' });
  await page.selectOption('#flag-select', 'distracted');
  await expect(page.locator('#flag-comment')).toBeVisible();
  await page.fill('#flag-comment', 'sibling walked in');
  await answerCurrentProblem(page);

  await expect(page.locator('#summary')).toBeVisible({ timeout: 15_000 });
  await finishToDownload(page);
  const [saved] = await getSavedSessions(page);
  const problem = saved.data.session.problems[0];
  expect(problem.flags[0].reason).toBe('distracted');
  expect(problem.flags[0].notes).toBe('sibling walked in');
});

test('End Quiz button ends early and saves partial progress', async ({ page }) => {
  await startPresetQuiz(page, { preset: 'a9' }); // 20 problems
  for (let i = 1; i <= 2; i++) {
    await expect(page.locator('.problem-count')).toHaveText(`Problem ${i} of 20`, { timeout: 15_000 });
    await answerCurrentProblem(page);
  }
  await expect(page.locator('.problem-count')).toHaveText('Problem 3 of 20', { timeout: 15_000 });
  page.on('dialog', (dialog) => dialog.accept());
  await page.click('#end-quiz-btn');

  await expect(page.locator('#summary')).toBeVisible({ timeout: 15_000 });
  await expect(page.locator('#summary')).toContainText('Total problems attempted: 2');
  await finishToDownload(page);
  const [saved] = await getSavedSessions(page);
  expect(saved.data.session.problems.length).toBe(2);
});

test('auto-submit fires when the typed answer length matches', async ({ page }) => {
  await startPresetQuiz(page, { preset: 't1', autoSubmit: true });
  const { answer } = await readProblem(page);
  // type the answer without pressing Enter; submission happens on length match
  await page.locator('#answer-input').pressSequentially(String(answer));
  await expect(page.locator('.feedback-message')).toContainText('Correct!', { timeout: 5_000 });
});
