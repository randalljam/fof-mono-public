// E2E for targeted fluency practice on the anchor page: pick "Targeted practice",
// type up to 5 target problems (prefilled from the file config or per-learner
// defaults), work targets SERIALLY (current target + filler streaming, no bursts),
// graduate on a fast-correct streak (confetti + sound + target rings), pause to
// Continue / Continue & skip, finish only when ALL targets graduate, and persist
// the config to the SQLite file. Hermetic via routeCdns.
import { test, expect } from '@playwright/test';
import { routeCdns, trackPageErrors, clickAnchorGo, stubFolderUsers } from './helpers.mjs';

const OP = { '+': (a, b) => a + b, '−': (a, b) => a - b, '×': (a, b) => a * b };

// Read the on-screen problem and type the correct answer fast (auto-submit, no Enter).
async function answerCurrent(page) {
  const text = (await page.textContent('#anchor-problem')) || '';
  const m = text.match(/(-?\d+)\s*([+−×])\s*(-?\d+)/);
  if (!m) throw new Error(`could not parse problem "${text}"`);
  const value = OP[m[2]](Number(m[1]), Number(m[3]));
  await page.locator('#anchor-answer').pressSequentially(String(value));
}

async function pickTargeted(page, name = 'Tester') {
  await page.goto('/anchor.html?setup=1&fb=0');
  await page.click('#anchor-username');
  await page.fill('#anchor-username', name);
  await page.keyboard.press('Escape');
  await page.check('#anchor-mode-new');
  await page.selectOption('#anchor-problem-list-file', '__targeted__');
  await expect(page.locator('#anchor-targeted-config')).toBeVisible();
}

// Clear the 5 target fields, type the given targets, set params, Start.
async function startTargeted(page, { name = 'Tester', targets = ['3+6'], streak = 3, percent = 50 } = {}) {
  await pickTargeted(page, name);
  for (let i = 1; i <= 5; i++) await page.fill(`#anchor-target-${i}`, targets[i - 1] || '');
  await page.fill('#anchor-target-streak', String(streak));
  await page.fill('#anchor-target-percent', String(percent));
  await page.click('#anchor-start');
  await clickAnchorGo(page);
  await expect(page.locator('#anchor-problem')).toBeVisible({ timeout: 30_000 });
}

let pageErrors;
test.beforeEach(async ({ context, page }) => {
  await routeCdns(context);
  await stubFolderUsers(context, ['Kid1', 'K2', 'Tester', 'Saved']);
  // Default stub for the targeted-config auto-save (the Start-time + on-change writes), so it
  // doesn't hit the static server; capture tests override this with their own page.route.
  await context.route(/\/api\/targeted-config/, (route) => route.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, targetedConfig: {} }),
  }));
  pageErrors = trackPageErrors(page);
});
test.afterEach(() => { expect(pageErrors).toEqual([]); });

test('selecting Targeted practice prefills Kid1 defaults (targets + filler) and shows the filler editor', async ({ page }) => {
  await pickTargeted(page, 'Kid1');
  await expect(page.locator('#anchor-target-1')).toHaveValue('6+3');
  await expect(page.locator('#anchor-target-5')).toHaveValue('3+4');
  await expect(page.locator('#anchor-filler-editor')).toBeVisible();
  await expect(page.locator('#anchor-filler-text')).toHaveValue(/0\s*\+\s*1/);
});

test('K2 defaults: targets 1+8 / 2+8 and params 5 / 4000 / 30', async ({ page }) => {
  await pickTargeted(page, 'K2');
  await expect(page.locator('#anchor-target-1')).toHaveValue('1+8');
  await expect(page.locator('#anchor-target-4')).toHaveValue('2+8');
  await expect(page.locator('#anchor-target-streak')).toHaveValue('5');
  await expect(page.locator('#anchor-target-fastms')).toHaveValue('4000');
  await expect(page.locator('#anchor-target-percent')).toHaveValue('30');
});

test('blank or unparseable targets are rejected with a clear message', async ({ page }) => {
  await pickTargeted(page, 'Tester');
  for (let i = 1; i <= 5; i++) await page.fill(`#anchor-target-${i}`, '');
  await page.click('#anchor-start');
  await expect(page.locator('#anchor-error')).toContainText('Type at least one target problem');
  await page.fill('#anchor-target-1', 'banana');
  await page.click('#anchor-start');
  await expect(page.locator('#anchor-error')).toContainText("Couldn't read target problem");
});

test('a target field normalizes whitespace to the compact form on blur', async ({ page }) => {
  await pickTargeted(page, 'Tester');
  await page.fill('#anchor-target-1', '  3 + 6 ');
  await page.locator('#anchor-target-1').blur();
  await expect(page.locator('#anchor-target-1')).toHaveValue('3+6');
});

test('targets are worked serially: only the first target shows until it graduates', async ({ page }) => {
  page.on('dialog', (d) => d.accept());
  await startTargeted(page, { name: 'Tester', targets: ['3+6', '8+7'], streak: 3, percent: 100 });
  // percent 100 -> every problem is the current target. The 2nd target must not
  // appear until the 1st graduates.
  for (let i = 0; i < 2; i++) {
    const t = (await page.textContent('#anchor-problem')) || '';
    expect(t.replace(/\s/g, '')).toMatch(/^(3\+6|6\+3)$/);
    await answerCurrent(page);
  }
  const cur = await page.evaluate(() => window.__anchorTargetedRun().currentTargetKey());
  expect(cur).toBe('+|3|6');
});

test('the target rings graphic shows during a targeted run', async ({ page }) => {
  page.on('dialog', (d) => d.accept());
  await startTargeted(page, { name: 'Tester', targets: ['3+6'], streak: 5 });
  await expect(page.locator('#anchor-target-rings')).toBeVisible();
  await expect(page.locator('#anchor-target-rings svg')).toBeVisible();
});

test('the filler editor is setup-only and disappears once the run starts', async ({ page }) => {
  page.on('dialog', (d) => d.accept());
  await pickTargeted(page, 'Tester');
  await expect(page.locator('#anchor-filler-editor')).toBeVisible();   // visible during setup
  await page.fill('#anchor-target-1', '3+6');
  await page.click('#anchor-start');
  await clickAnchorGo(page);
  await expect(page.locator('#anchor-problem')).toBeVisible({ timeout: 30_000 });
  await expect(page.locator('#anchor-filler-editor')).toBeHidden();    // gone once the quiz starts
});

test('a single target graduates after a fast-correct streak and finishes fluent', async ({ page }) => {
  page.on('dialog', (d) => d.accept());
  await startTargeted(page, { name: 'Tester', targets: ['3+6'], streak: 3, percent: 50 });
  for (let i = 0; i < 40; i++) {
    if (await page.locator('#anchor-summary').isVisible()) break;
    if (await page.locator('#anchor-grad-continue').isVisible()) { await page.click('#anchor-grad-continue'); continue; }
    await answerCurrent(page);
  }
  await expect(page.locator('#anchor-summary')).toBeVisible({ timeout: 30_000 });
  await expect(page.locator('#anchor-summary-title')).toContainText('Targets fluent');

  const meta = await page.evaluate(() => window.__anchorTargetedRun().metadata());
  expect(meta.mode).toBe('targeted-practice');
  expect(meta.targets).toEqual(['+|3|6']);
  expect(meta.percentTarget).toBe(50);
  expect(meta.maxBursts).toBeUndefined();
  expect(meta.completionReason).toBe('all-graduated');
});

test('on graduation, a Continue button gates the next problem (after confetti + sound)', async ({ page }) => {
  page.on('dialog', (d) => d.accept());
  // No file config -> the per-target reward falls back to the single default image.
  const gif1x1 = Buffer.from('R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7', 'base64');
  await page.route(/_assets\/pipa[^/]*\.webp/, (route) => route.fulfill({ contentType: 'image/gif', body: gif1x1 }));
  await startTargeted(page, { name: 'Tester', targets: ['3+6'], streak: 3, percent: 100 });
  await answerCurrent(page);
  await answerCurrent(page);
  await answerCurrent(page);                                   // 3rd fast-correct graduates the only target
  await expect(page.locator('#anchor-grad-continue')).toBeVisible();
  await expect(page.locator('#anchor-reward-burst img')).toHaveAttribute('src', /pipa_no_wand_clap_jump_fixed\.webp/);  // single target => session completion fallback
  await expect(page.locator('#anchor-summary')).toBeHidden();  // not finished until Continue
  await page.click('#anchor-grad-continue');
  await expect(page.locator('#anchor-summary')).toBeVisible({ timeout: 30_000 });
});

test('with no file image set, graduation shows the single fallback animation', async ({ page }) => {
  page.on('dialog', (d) => d.accept());
  // The fallback asset is local-only; serve a tiny valid image so it loads in the test.
  const gif1x1 = Buffer.from('R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7', 'base64');
  await page.route(/_assets\/pipa[^/]*\.webp/, (route) => route.fulfill({ contentType: 'image/gif', body: gif1x1 }));
  await startTargeted(page, { name: 'Tester', targets: ['3+6'], streak: 1, percent: 100 });
  await answerCurrent(page);                                   // streak 1 -> graduate immediately
  await expect(page.locator('#anchor-reward-burst img')).toBeVisible();
  await expect.poll(() => page.locator('#anchor-reward-burst img').evaluate((el) => el.naturalWidth)).toBeGreaterThan(0);
});

test('a missing reward asset shows nothing (no broken image, no placeholder)', async ({ page }) => {
  page.on('dialog', (d) => d.accept());
  // Simulate the asset not being present locally: the image request fails to load.
  await page.route(/_assets\/pipa[^/]*\.webp/, (route) => route.abort('failed'));
  await startTargeted(page, { name: 'Tester', targets: ['3+6'], streak: 1, percent: 100 });
  await answerCurrent(page);                                   // graduate -> celebrate, but asset is missing
  await expect(page.locator('#anchor-grad-continue')).toBeVisible();   // the flow still works
  await expect(page.locator('#anchor-reward-burst')).toBeHidden();     // nothing shown
  await expect(page.locator('#anchor-reward-burst img')).toHaveCount(0);
});

test('the completion animation replaces the per-target one only on the final graduation', async ({ page }) => {
  page.on('dialog', (d) => d.accept());
  // The learner's file sets BOTH a per-target reward image and a distinct completion image.
  await page.route(/\/api\/latest-user-db/, (route) => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({
      ok: true, found: true, filename: 'math-flu_K1_2026-06-23.sqlite', sessionCount: 1, problemLists: [],
      targetedConfig: {
        targets: ['3+6', '2+5'], filler: [], graduationStreak: 1, fastMs: 4000, percentTarget: 100,
        rewardImage: '_assets/reward-test.webp', completionImage: '_assets/complete-test.webp',
      },
      base64: '',
    }),
  }));
  const gif1x1 = Buffer.from('R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7', 'base64');
  await page.route(/_assets\/(reward|complete)-test\.webp/, (route) => route.fulfill({ contentType: 'image/gif', body: gif1x1 }));

  await page.goto('/anchor.html?setup=1&fb=0');
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'Kid1');
  await page.keyboard.press('Escape');
  await page.locator('#anchor-username').blur();               // Continue -> loads the file config
  await page.selectOption('#anchor-problem-list-file', '__targeted__');
  await expect(page.locator('#anchor-target-1')).toHaveValue('3+6');  // prefilled from the file
  await page.click('#anchor-start');
  await clickAnchorGo(page);
  await expect(page.locator('#anchor-problem')).toBeVisible({ timeout: 30_000 });

  await answerCurrent(page);                                   // graduates target 1 of 2 (NOT the last)
  await expect(page.locator('#anchor-grad-continue')).toBeVisible();
  await expect(page.locator('#anchor-reward-burst img')).toHaveAttribute('src', /reward-test\.webp/);  // per-target image
  await page.click('#anchor-grad-continue');

  await answerCurrent(page);                                   // graduates target 2 of 2 (the LAST -> completes)
  await expect(page.locator('#anchor-grad-continue')).toBeVisible();
  await expect(page.locator('#anchor-reward-burst img')).toHaveAttribute('src', /complete-test\.webp/);  // completion image
});

test('Pause hides the problem and offers Continue / Continue & skip', async ({ page }) => {
  page.on('dialog', (d) => d.accept());
  await startTargeted(page, { name: 'Tester', targets: ['3+6'], streak: 5 });
  await page.click('#anchor-pause');
  await expect(page.locator('#anchor-pause-panel')).toBeVisible();
  await expect(page.locator('#anchor-pause-skip')).toHaveText('Continue & skip');
  await page.click('#anchor-pause-continue');                  // resume same problem
  await expect(page.locator('#anchor-pause-panel')).toBeHidden();
  await expect(page.locator('#anchor-problem')).toBeVisible();
  await answerCurrent(page);
  await page.click('#anchor-pause');                           // pause again, then skip
  await page.click('#anchor-pause-skip');
  await expect(page.locator('#anchor-pause-panel')).toBeHidden();
  await expect(page.locator('#anchor-problem')).toBeVisible();
  await answerCurrent(page);
  expect(pageErrors).toEqual([]);
});

test('Flag previous is available in targeted practice: pause, flag the prior problem, continue', async ({ page }) => {
  page.on('dialog', (d) => d.accept());
  await startTargeted(page, { name: 'Tester', targets: ['3+6'], streak: 5 });
  await answerCurrent(page);
  await expect(page.locator('#anchor-flag-previous')).toBeVisible();
  await page.click('#anchor-flag-previous');
  await expect(page.locator('#anchor-correction')).toBeVisible();
  await expect(page.locator('#anchor-flag-menu')).toBeVisible();
  await page.locator('#anchor-flag-reasons input[type="checkbox"]').first().check();
  await page.click('#anchor-correct-continue');
  await expect(page.locator('#anchor-correction')).toBeHidden();
  await expect(page.locator('#anchor-problem')).toBeVisible();
  const session = await page.evaluate(() => window.__anchorSession());
  expect(session[session.length - 1].flags.length).toBeGreaterThan(0);
  await answerCurrent(page);
});

test('Continue & insert re-asks the flagged problem in targeted practice (no error)', async ({ page }) => {
  page.on('dialog', (d) => d.accept());
  await startTargeted(page, { name: 'Tester', targets: ['3+6'], streak: 9 });
  await answerCurrent(page);
  await page.click('#anchor-flag-previous');
  await expect(page.locator('#anchor-flag-menu')).toBeVisible();
  await page.click('#anchor-correct-insert');
  await expect(page.locator('#anchor-correction')).toBeHidden();
  for (let i = 0; i < 6; i++) await answerCurrent(page);
  expect(pageErrors).toEqual([]);
});

test('progress shows the targets-fluent count during the run', async ({ page }) => {
  page.on('dialog', (d) => d.accept());
  await startTargeted(page, { name: 'Tester', targets: ['3+6', '8+7'], streak: 3 });
  await answerCurrent(page);
  await expect(page.locator('#anchor-progress')).toContainText('Targets fluent:');
  await expect(page.locator('#anchor-progress')).toContainText('/2');
});

test('targeted config from the file prefills the fields (overriding code defaults)', async ({ page }) => {
  await page.route(/\/api\/latest-user-db/, (route) => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({
      ok: true, found: true, filename: 'math-flu_K1_2026-06-22.sqlite', sessionCount: 1,
      problemLists: [],
      targetedConfig: { targets: ['9+9', '2+3'], filler: ['1 + 1'], graduationStreak: 4, fastMs: 1500, percentTarget: 70 },
      base64: '',
    }),
  }));
  await page.goto('/anchor.html?setup=1&fb=0');
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'Kid1');
  await page.keyboard.press('Escape');
  await page.locator('#anchor-username').blur();
  await page.selectOption('#anchor-problem-list-file', '__targeted__');
  await expect(page.locator('#anchor-target-1')).toHaveValue('9+9');
  await expect(page.locator('#anchor-target-2')).toHaveValue('2+3');
  await expect(page.locator('#anchor-target-streak')).toHaveValue('4');
  await expect(page.locator('#anchor-target-percent')).toHaveValue('70');
  await expect(page.locator('#anchor-filler-text')).toHaveValue('1 + 1');
});

test('earned rings are kept after a wrong answer (cumulative, no reset)', async ({ page }) => {
  page.on('dialog', (d) => d.accept());
  await startTargeted(page, { name: 'Tester', targets: ['3+6'], streak: 5, percent: 100 });
  await answerCurrent(page);                                   // one fast-correct -> 1 ring earned
  expect(await page.evaluate(() => window.__anchorTargetedRun().progress().current.streak)).toBe(1);
  const text = (await page.textContent('#anchor-problem')) || '';
  const m = text.match(/(\d+)\s*\+\s*(\d+)/);
  const sum = Number(m[1]) + Number(m[2]);
  await page.locator('#anchor-answer').pressSequentially(String(sum > 0 ? sum - 1 : 1));  // wrong
  await expect(page.locator('#anchor-correction')).toBeVisible();
  await page.click('#anchor-correct-continue');
  expect(await page.evaluate(() => window.__anchorTargetedRun().progress().current.streak)).toBe(1);  // ring kept
});

test('a wrong answer in targeted practice shows the correction flow (correct answer + Continue)', async ({ page }) => {
  page.on('dialog', (d) => d.accept());
  await startTargeted(page, { name: 'Tester', targets: ['3+6'], streak: 5, percent: 100 });
  const text = (await page.textContent('#anchor-problem')) || '';
  const m = text.match(/(\d+)\s*\+\s*(\d+)/);
  const sum = Number(m[1]) + Number(m[2]);
  const wrong = sum > 0 ? sum - 1 : 1;                  // same digit count for single-digit sums
  await page.locator('#anchor-answer').pressSequentially(String(wrong));
  await expect(page.locator('#anchor-correction')).toBeVisible();
  await expect(page.locator('#anchor-correction-answer')).toBeVisible();   // the correct answer is shown
  await page.click('#anchor-correct-continue');
  await expect(page.locator('#anchor-correction')).toBeHidden();
  await expect(page.locator('#anchor-problem')).toBeVisible();
});

test('editing targets / settings auto-saves the config to /api/targeted-config', async ({ page }) => {
  let posted = null;
  await page.route(/\/api\/targeted-config/, (route) => {
    posted = JSON.parse(route.request().postData() || '{}');
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, targetedConfig: { targets: ['9+9'], filler: [] } }) });
  });
  await pickTargeted(page, 'Tester');
  await page.fill('#anchor-target-1', '9+9');
  await page.locator('#anchor-target-1').blur();                 // flush on blur
  await expect(page.locator('#anchor-targeted-status')).toContainText('Saved');
  expect(posted.targets).toContain('9+9');
  // changing the percent also writes right away (debounced input)
  await page.fill('#anchor-target-percent', '30');
  await expect.poll(() => (posted && String(posted.percentTarget))).toBe('30');
});

test('clicking Start persists the current settings to the source file (config only, no session)', async ({ page }) => {
  page.on('dialog', (d) => d.accept());
  const posts = [];
  await page.route(/\/api\/targeted-config/, (route) => {
    posts.push(JSON.parse(route.request().postData() || '{}'));
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, targetedConfig: { targets: ['3+6'], filler: [] } }) });
  });
  await startTargeted(page, { name: 'Tester', targets: ['3+6'], streak: 7, percent: 40 });
  const last = posts[posts.length - 1];                        // the Start-time save reflects the chosen settings
  expect(last).toBeTruthy();
  expect(String(last.graduationStreak)).toBe('7');
  expect(String(last.percentTarget)).toBe('40');
});

test('the filler editor auto-saves to /api/targeted-config on blur', async ({ page }) => {
  let posted = null;
  await page.route(/\/api\/targeted-config/, (route) => {
    posted = JSON.parse(route.request().postData() || '{}');
    route.fulfill({ status: 200, contentType: 'application/json',
      body: JSON.stringify({ ok: true, targetedConfig: { filler: ['0 + 1', '3 + 3'] } }) });
  });
  await pickTargeted(page, 'Tester');
  await page.fill('#anchor-filler-text', '0 + 1\n3 + 3');
  await page.locator('#anchor-filler-text').blur();
  await expect(page.locator('#anchor-filler-status')).toContainText('Saved');
  expect(posted.user).toBe('Tester');
  expect(posted.filler).toContain('0 + 1');
});

test('finishing persists the targeted config in the save-run payload', async ({ page }) => {
  page.on('dialog', (d) => d.accept());
  let savePayload = null;
  await page.route(/\/api\/health/, (route) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) }));
  await page.route(/\/api\/save-run/, (route) => {
    savePayload = JSON.parse(route.request().postData() || '{}');
    route.fulfill({ status: 200, contentType: 'application/json',
      body: JSON.stringify({ ok: true, action: 'create', filename: 'math-flu_Tester_x.sqlite', localPath: '/tmp/x' }) });
  });
  await startTargeted(page, { name: 'Tester', targets: ['3+6'], streak: 3, percent: 60 });
  for (let i = 0; i < 20; i++) {
    if (await page.locator('#anchor-summary').isVisible()) break;
    if (await page.locator('#anchor-grad-continue').isVisible()) { await page.click('#anchor-grad-continue'); continue; }
    await answerCurrent(page);
  }
  await expect(page.locator('#anchor-summary')).toBeVisible({ timeout: 30_000 });
  // The /api/save-run POST fires just AFTER the summary renders (finalizeTargeted shows the
  // summary, then runUpload awaits /api/health and /api/save-run), so poll for it rather than
  // assert synchronously on summary visibility — otherwise it's a race on slower/loaded machines.
  await expect.poll(() => savePayload, { timeout: 10_000 }).not.toBeNull();
  expect(savePayload.targetedConfig).toBeTruthy();
  expect(savePayload.targetedConfig.targets).toEqual(['3+6']);
  expect(savePayload.targetedConfig.percentTarget).toBe(60);
});
