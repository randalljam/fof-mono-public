// E2E for the kid landing: the default page loads name buttons from /api/folder-users
// (the active source folder's SQLite files) plus a Targeted-practice / Problem-list pop-up,
// so a learner can land on the iPad and just pick themselves. "Other…" (and ?setup=1)
// reveal the full setup card. Picking a learner Continues their latest file; the pop-up
// starts the chosen mode, or says to ask Baba when that mode isn't set up in their file.
// Hermetic via routeCdns.
import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { routeCdns, trackPageErrors, clickAnchorGo, stubFolderUsers } from './helpers.mjs';

// Landing paints name buttons from an async /api/folder-users fetch; run these serially so
// parallel workers don't race the static server / route stubs.
test.describe.configure({ mode: 'serial' });

// A valid (empty) SQLite db, base64'd, so the Continue hydrate opens a real cache on Start.
let VALID_DB_B64 = '';
try {
  const initSqlJs = (await import('sql.js')).default;
  const wasmBinary = readFileSync(new URL('../node_modules/sql.js/dist/sql-wasm.wasm', import.meta.url));
  const SQL = await initSqlJs({ wasmBinary });
  const db = new SQL.Database();
  VALID_DB_B64 = Buffer.from(db.export()).toString('base64');
  db.close();
} catch { /* sql.js absent */ }

const INTERNAL_LISTS = [
  { problem_list_id: 5, list_order: 1, list_name: 'Warm set', retain: 0, times_used: 0, item_count: 2,
    items: [{ item_order: 1, problem_text: '8 + 2', num1: 8, operation: '+', num2: 2 },
            { item_order: 2, problem_text: '3 + 4', num1: 3, operation: '+', num2: 4 }] },
];
const TARGETED_CFG = { targets: ['3+6'], filler: [], graduationStreak: 1, fastMs: 4000, percentTarget: 100 };
// An auto-generated quick-quiz set: 7 addition problems in item_order (first is 3 + 4).
const QUICK_PRACTICE = {
  '+': [
    { item_order: 1, problem_text: '3 + 4', num1: 3, operation: '+', num2: 4, slot_status: 'green', origin: 'data' },
    { item_order: 2, problem_text: '2 + 5', num1: 2, operation: '+', num2: 5, slot_status: 'green', origin: 'data' },
    { item_order: 3, problem_text: '1 + 6', num1: 1, operation: '+', num2: 6, slot_status: 'green', origin: 'data' },
    { item_order: 4, problem_text: '5 + 6', num1: 5, operation: '+', num2: 6, slot_status: 'yellow', origin: 'data' },
    { item_order: 5, problem_text: '4 + 7', num1: 4, operation: '+', num2: 7, slot_status: 'yellow', origin: 'data' },
    { item_order: 6, problem_text: '3 + 8', num1: 3, operation: '+', num2: 8, slot_status: 'yellow', origin: 'data' },
    { item_order: 7, problem_text: '8 + 9', num1: 8, operation: '+', num2: 9, slot_status: 'red', origin: 'data' },
  ],
};

const DEFAULT_LANDING_USERS = [
  { name: 'Kid1', label: 'Kid1', filename: 'math-flu_K1_2026-06-17.sqlite' },
  { name: 'K2', label: 'K2', filename: 'math-flu_K2_2026-06-16.sqlite' },
  { name: 'Randy', label: 'Randy', filename: 'math-flu_Randy_2026-06-10.sqlite' },
  { name: 'Tester', label: 'Tester', filename: 'math-flu_Tester_2026-06-11.sqlite' },
];

// Landing name button by exact label text (filled from /api/folder-users).
function landingBtn(page, label) {
  return page.locator('#landing-names .landing-name', { hasText: new RegExp(`^${label}$`) });
}

function folderUsersBody(users) {
  return JSON.stringify({ ok: true, folder: 'tlkids', users });
}

// Open the kid landing and wait until name buttons are painted from /api/folder-users.
async function openLanding(page) {
  await page.goto('/anchor.html?fb=0');
  await expect(page.locator('#landing-names .landing-name').first()).toBeVisible({ timeout: 15_000 });
}

// /api/latest-user-db keyed by user: returns that learner's file content (or found:false).
function mockLatest(page, byUser, onRequest = null) {
  return page.route(/\/api\/latest-user-db/, (route) => {
    const url = new URL(route.request().url());
    const user = url.searchParams.get('user') || '';
    if (onRequest) onRequest({ user, file: url.searchParams.get('file') });
    const r = byUser[user];
    const body = r
      ? { ok: true, found: true, filename: `math-flu_${user}.sqlite`, sessionCount: 1,
          problemLists: r.problemLists || [], targetedConfig: r.targetedConfig || null,
          quickPractice: r.quickPractice || {}, base64: VALID_DB_B64 }
      : { ok: true, found: false };
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
  });
}

let pageErrors;
test.beforeEach(async ({ context, page }) => {
  await routeCdns(context);
  // Default stub for the targeted-config writes (Start-time flush) so they don't hit the server.
  await context.route(/\/api\/targeted-config/, (route) => route.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, targetedConfig: {} }) }));
  // Always stub folder-users on the context so the landing fetch is intercepted before paint.
  // Body is closed over as a string so parallel tests can't race a shared users array.
  // Use the full DEFAULT_LANDING_USERS (incl. filenames) — not a bare name list — so
  // Continue-with-my-file can pin the exact Randy/Tester source file.
  const body = folderUsersBody(DEFAULT_LANDING_USERS);
  await context.route(/\/api\/folder-users/, (route) => route.fulfill({
    status: 200, contentType: 'application/json', body,
  }));
  pageErrors = trackPageErrors(page);
});
test.afterEach(() => { expect(pageErrors).toEqual([]); });

test('the default page shows the kid landing (folder names), setup hidden', async ({ page }) => {
  await openLanding(page);
  await expect(page.locator('#anchor-landing')).toBeVisible();
  await expect(landingBtn(page, 'Kid1')).toBeVisible();
  await expect(landingBtn(page, 'K2')).toBeVisible();
  await expect(page.locator('#anchor-setup')).toBeHidden();
});

test('?setup=1 skips the landing and shows the full setup', async ({ page }) => {
  await page.goto('/anchor.html?setup=1&fb=0');
  await expect(page.locator('#anchor-setup')).toBeVisible();
  await expect(page.locator('#anchor-landing')).toBeHidden();
});

test('Other… reveals the full setup (and the problem-list editor)', async ({ page }) => {
  await openLanding(page);
  await expect(page.locator('#anchor-problem-list-editor')).toBeHidden();   // hidden on the landing
  await page.click('#landing-other');
  await expect(page.locator('#anchor-setup')).toBeVisible();
  await expect(page.locator('#anchor-landing')).toBeHidden();
  await expect(page.locator('#anchor-problem-list-editor')).toBeVisible();  // shown with the setup
});

test('picking Kid1 opens the pop-up and Targeted practice starts the run', async ({ page }) => {
  await mockLatest(page, { Kid1: { targetedConfig: TARGETED_CFG } });
  await openLanding(page);
  await landingBtn(page, 'Kid1').click();
  await expect(page.locator('#anchor-kid-modal')).toBeVisible();
  await expect(page.locator('#kid-modal-title')).toContainText('Hi Kid1');
  await page.click('#kid-mode-targeted');
  await clickAnchorGo(page);
  await expect(page.locator('#anchor-problem')).toHaveText(/\d\s*[+−×]\s*\d/, { timeout: 30_000 });
  await expect(page.locator('#anchor-landing')).toBeHidden();
  await expect(page.locator('#anchor-kid-modal')).toBeHidden();
});

test('picking Problem list runs the learner\'s internal list',
  { skip: VALID_DB_B64 ? false : 'sql.js not installed (run npm install in apps/math-quiz/tests)' },
  async ({ page }) => {
    await mockLatest(page, { K2: { problemLists: INTERNAL_LISTS } });
    await openLanding(page);
    await landingBtn(page, 'K2').click();
    await expect(page.locator('#anchor-kid-modal')).toBeVisible();
    await page.click('#kid-mode-list');
    await clickAnchorGo(page);
    await expect(page.locator('#anchor-problem')).toHaveText(/\s*8\s*\+\s*2\s*/);   // first internal item
  });

test('Quick quiz + starts the auto-generated 7-problem addition set',
  { skip: VALID_DB_B64 ? false : 'sql.js not installed (run npm install in apps/math-quiz/tests)' },
  async ({ page }) => {
    await mockLatest(page, { Kid1: { quickPractice: QUICK_PRACTICE } });
    await openLanding(page);
    await landingBtn(page, 'Kid1').click();
    await expect(page.locator('#anchor-kid-modal')).toBeVisible();
    await expect(page.locator('#kid-quick-add')).toBeEnabled();    // + has a set
    await expect(page.locator('#kid-quick-sub')).toBeDisabled();   // - / * do not
    await expect(page.locator('#kid-quick-mul')).toBeDisabled();
    await page.click('#kid-quick-add');
    await clickAnchorGo(page);
    await expect(page.locator('#anchor-problem')).toHaveText(/\s*3\s*\+\s*4\s*/);   // first quick item
    await expect(page.locator('#anchor-kid-modal')).toBeHidden();
  });

test('Quick-quiz buttons are disabled when the file has no quick set', async ({ page }) => {
  await mockLatest(page, { K2: { problemLists: INTERNAL_LISTS } });   // a list, but no quickPractice
  await openLanding(page);
  await landingBtn(page, 'K2').click();
  await expect(page.locator('#anchor-kid-modal')).toBeVisible();
  await expect(page.locator('#kid-quick-add')).toBeDisabled();
  await expect(page.locator('#kid-quick-sub')).toBeDisabled();
  await expect(page.locator('#kid-quick-mul')).toBeDisabled();
});

test('a mode that is not set up tells you to ask Baba (stays on the pop-up)', async ({ page }) => {
  await mockLatest(page, { K2: { problemLists: INTERNAL_LISTS } });   // a list, but no targeted config
  await openLanding(page);
  await landingBtn(page, 'K2').click();
  await expect(page.locator('#anchor-kid-modal')).toBeVisible();
  await page.click('#kid-mode-targeted');                              // not set up for K2
  await expect(page.locator('#kid-modal-status')).toContainText('ask Baba');
  await expect(page.locator('#anchor-kid-modal')).toBeVisible();
  await expect(page.locator('#anchor-problem')).toBeHidden();          // never started
});

test('no file for a learner says to ask Baba (no pop-up)', async ({ page }) => {
  await mockLatest(page, {});   // nobody has a file yet
  await openLanding(page);
  await landingBtn(page, 'Kid1').click();
  await expect(page.locator('#landing-status')).toContainText('ask Baba');
  await expect(page.locator('#anchor-kid-modal')).toBeHidden();
});

test('duplicate names show the file date on the button', async ({ context, page }) => {
  // Override the default folder-users stub for this test only.
  await context.unroute(/\/api\/folder-users/);
  const body = folderUsersBody([
    { name: 'Kid1', label: 'Kid1 2026-06-17', filename: 'math-flu_Izzy_2026-06-17.sqlite' },
    { name: 'Kid1', label: 'Kid1 2026-07-01', filename: 'math-flu_Izzy_2026-07-01.sqlite' },
  ]);
  await context.route(/\/api\/folder-users/, (route) => route.fulfill({
    status: 200, contentType: 'application/json', body,
  }));
  await openLanding(page);
  await expect(landingBtn(page, 'Kid1 2026-06-17')).toBeVisible();
  await expect(landingBtn(page, 'Kid1 2026-07-01')).toBeVisible();
});
test('landing Continue requests the exact top-level file represented by the button', async ({ page }) => {
  let requestedFile = null;
  await page.route(/\/api\/latest-user-db/, (route) => {
    const url = new URL(route.request().url());
    requestedFile = url.searchParams.get('file');
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ok: true, found: true, filename: requestedFile, sessionCount: 1,
        problemLists: [], targetedConfig: TARGETED_CFG, quickPractice: {}, base64: VALID_DB_B64,
      }),
    });
  });
  await openLanding(page);
  await landingBtn(page, 'Kid1').click();
  await expect(page.locator('#anchor-kid-modal')).toBeVisible();
  expect(requestedFile).toBe('math-flu_K1_2026-06-17.sqlite');
});

test('Randy opens a clone panel; name buttons stay usable to pick a source', async ({ page }) => {
  await mockLatest(page, { Randy: { targetedConfig: TARGETED_CFG }, Kid1: { targetedConfig: TARGETED_CFG } });
  await openLanding(page);
  await landingBtn(page, 'Randy').click();
  await expect(page.locator('#landing-clone-panel')).toBeVisible();
  await expect(page.locator('#landing-clone-msg')).toContainText('Playing as Randy');
  await expect(page.locator('#landing-clone-run')).toBeDisabled();
  await expect(page.locator('#anchor-kid-modal')).toBeHidden();
  // Name buttons remain on the landing so the operator can pick who to clone from.
  await expect(landingBtn(page, 'Kid1')).toBeVisible();
  await landingBtn(page, 'Kid1').click();
  await expect(page.locator('#landing-clone-run')).toBeEnabled();
  await expect(page.locator('#landing-clone-run')).toHaveText(/Clone Kid1/);
  await expect(page.locator('#anchor-kid-modal')).toBeHidden();
});

test('Continue with my file skips cloning and opens the mode pop-up', async ({ page }) => {
  const requestedFiles = [];
  await mockLatest(page, { Randy: { targetedConfig: TARGETED_CFG } }, (request) => {
    if (request.user === 'Randy') requestedFiles.push(request.file);
  });
  await openLanding(page);
  await landingBtn(page, 'Randy').click();
  await expect(page.locator('#landing-clone-panel')).toBeVisible();
  await page.click('#landing-clone-continue');
  await expect(page.locator('#anchor-kid-modal')).toBeVisible();
  await expect(page.locator('#kid-modal-title')).toContainText('Hi Randy');
  await expect(page.locator('#landing-clone-panel')).toBeHidden();
  expect(requestedFiles).toContain('math-flu_Randy_2026-06-10.sqlite');
});

test('Clone selected file posts /api/clone-user-file then opens the mode pop-up', async ({ page }) => {
  await mockLatest(page, { Randy: { targetedConfig: TARGETED_CFG }, Kid1: { targetedConfig: TARGETED_CFG } });
  let cloneBody = null;
  await page.route(/\/api\/clone-user-file/, async (route) => {
    cloneBody = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ok: true,
        source_file: 'math-flu_K1_2026-06-17.sqlite',
        new_file: 'math-flu_Randy_2026-06-17.sqlite',
        deleted: ['math-flu_Randy_2026-06-10.sqlite'],
      }),
    });
  });
  await openLanding(page);
  await landingBtn(page, 'Randy').click();
  await landingBtn(page, 'Kid1').click();
  await page.click('#landing-clone-run');
  await expect.poll(() => cloneBody).toMatchObject({
    sourceUser: 'Kid1',
    targetUser: 'Randy',
    sourceFile: 'math-flu_K1_2026-06-17.sqlite',
  });
  await expect(page.locator('#anchor-kid-modal')).toBeVisible();
  await expect(page.locator('#kid-modal-title')).toContainText('Hi Randy');
});

test('Tester also gets the clone panel; Kid1 does not', async ({ page }) => {
  await mockLatest(page, {
    Tester: { targetedConfig: TARGETED_CFG },
    Kid1: { targetedConfig: TARGETED_CFG },
  });
  await openLanding(page);
  await landingBtn(page, 'Tester').click();
  await expect(page.locator('#landing-clone-panel')).toBeVisible();
  await page.click('#landing-clone-cancel');
  await expect(page.locator('#landing-clone-panel')).toBeHidden();
  await landingBtn(page, 'Kid1').click();
  await expect(page.locator('#landing-clone-panel')).toBeHidden();
  await expect(page.locator('#anchor-kid-modal')).toBeVisible();
  await expect(page.locator('#kid-modal-title')).toContainText('Hi Kid1');
});
