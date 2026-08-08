// E2E for the anchor dev-server wiring with a MOCKED dev server (the real save runs on
// the laptop). Verifies: name entry auto-loads the learner's latest per-person DB from the
// selected source folder (GET /api/latest-user-db) — Continue with no file shows an error;
// a finished run POSTs the right /api/save-run payload (sourceFolder/destination/name/stamp/
// base64/forceNew); and "Start new file" sets forceNew. Continue's hydrate opens
// the returned bytes, so the "found" mock returns a real (sql.js-built) empty DB.
import { test, expect } from '@playwright/test';
import { createRequire } from 'node:module';
import fs from 'node:fs';
import { routeCdns, trackPageErrors, clickAnchorGo, stubFolderUsers } from './helpers.mjs';

// These tests share module-level broker state; keep this file serial even though the
// repository config enables full parallelism across independent specs.
test.describe.configure({ mode: 'serial' });

const require = createRequire(import.meta.url);
let VALID_B64 = '';
test.beforeAll(async () => {
  const initSqlJs = require('sql.js');
  const SQL = await initSqlJs({ wasmBinary: fs.readFileSync(require.resolve('sql.js/dist/sql-wasm.wasm')) });
  const db = new SQL.Database();
  // Only a non-colliding placeholder table — so the app's createTables() builds the full
  // Users/Sessions/ProblemAttempts schema on load (a partial Sessions here would shadow it).
  db.run('CREATE TABLE _seed (x);');
  VALID_B64 = Buffer.from(db.export()).toString('base64');   // a real, openable SQLite DB
  db.close();
});

let saveBody = null;
async function mockBroker(context, { latest = null } = {}) {
  saveBody = null;
  await stubFolderUsers(context, ['Randy', 'NewKid', 'Fresh', 'Ghost']);
  await context.route(/\/api\/health/, (route) =>
    route.fulfill({ contentType: 'application/json', body: JSON.stringify({ ok: true, bucket: '[S3-BUCKET]', singleSessionBase: 'math-quiz/single-sessions/', backupBase: 'math-quiz/_backup-s3/' }) }));
  await context.route(/\/api\/data-folders/, (route) =>
    route.fulfill({ contentType: 'application/json', body: JSON.stringify({ ok: true, folders: ['real', 'test'] }) }));
  // latest(user) -> response object, or null/undefined -> found:false (no file to continue).
  await context.route(/\/api\/latest-user-db/, (route) => {
    const user = new URL(route.request().url()).searchParams.get('user') || '';
    const body = (latest && latest(user)) || { ok: true, found: false };
    route.fulfill({ contentType: 'application/json', body: JSON.stringify(body) });
  });
  await context.route(/\/api\/save-run/, async (route) => {
    saveBody = JSON.parse(route.request().postData() || '{}');
    route.fulfill({ contentType: 'application/json', body: JSON.stringify({
      ok: true, action: 'append', filename: 'math-flu_Randy_2026-06-19.sqlite',
      target: 'math-flu_Randy_2026-06-19_120000.sqlite',
      localPath: '/x/_data/real/math-flu_Randy_2026-06-19.sqlite',
      backup: '/x/_BACKUP/math-quiz/sqlite-snapshots/math-flu_Randy_2026-06-19_120000_backup_2026-06-20_120000.sqlite',
      backupS3Uri: 's3://[S3-BUCKET]/math-quiz/_backup-s3/math-flu_Randy_2026-06-19_120000_backup_2026-06-20_120000.sqlite',
      singleSessionFile: 'math-flu_Randy_2026-06-20_120000.sqlite',
      singleSessionPath: '/x/_data/_single-session-sqlite-files/math-flu_Randy_2026-06-20_120000.sqlite',
      singleSessionS3Uri: 's3://[S3-BUCKET]/math-quiz/single-sessions/math-flu_Randy_2026-06-20_120000.sqlite',
    }) });
  });
}

const foundRandy = (user) => user === 'Randy'
  ? { ok: true, found: true, folder: 'real', user, filename: 'math-flu_Randy_2026-06-19.sqlite', sessionCount: 3, base64: VALID_B64 }
  : { ok: true, found: false };

test('Continue latest auto-loads the found file; a name with no file shows an error', async ({ page, context }) => {
  const errs = trackPageErrors(page);
  await routeCdns(context);
  await mockBroker(context, { latest: foundRandy });
  await page.goto('/anchor.html?setup=1&fb=0&practice=0');
  await page.fill('#anchor-source-folder', 'real');

  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'Randy');
  await page.keyboard.press('Escape');
  await page.locator('#anchor-username').blur();
  await expect(page.locator('#anchor-name-status')).toContainText('Continuing math-flu_Randy_2026-06-19.sqlite — 3 prior session(s)');

  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'NewKid');
  await page.keyboard.press('Escape');
  await page.locator('#anchor-username').blur();
  await expect(page.locator('#anchor-name-status')).toContainText('No file for "NewKid" in source folder "real" to continue');
  expect(errs).toEqual([]);
});

test('Start new file shows the new-file note and does not auto-load', async ({ page, context }) => {
  await routeCdns(context);
  let latestCalls = 0;
  await mockBroker(context, { latest: (user) => { latestCalls++; return foundRandy(user); } });
  await page.goto('/anchor.html?setup=1&fb=0&practice=0');
  await page.fill('#anchor-source-folder', 'real');
  await page.check('#anchor-mode-new');
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'Randy');
  await page.keyboard.press('Escape');
  await page.locator('#anchor-username').blur();
  await expect(page.locator('#anchor-name-status')).toContainText('Start new — a fresh file will be created for "Randy"');
  expect(latestCalls).toBe(0);   // Start New must not hit the load endpoint
});

test('finishing a Continue run posts sourceFolder/destination/forceNew=false', async ({ page, context }) => {
  await routeCdns(context);
  await mockBroker(context, { latest: foundRandy });   // Continue needs a found file
  page.on('dialog', (d) => d.accept()); // Quit & save confirm
  await page.goto('/anchor.html?setup=1&fb=0&practice=0');
  await page.fill('#anchor-source-folder', 'real');
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'Randy');
  await page.keyboard.press('Escape');
  await page.click('#anchor-start');
  await clickAnchorGo(page);

  for (let i = 0; i < 2; i++) {
    const m = ((await page.textContent('#anchor-problem')) || '').match(/(-?\d+)\s*\+\s*(-?\d+)/);
    if (!m) break;
    await page.locator('#anchor-answer').pressSequentially(String(Number(m[1]) + Number(m[2])));
  }
  await page.click('#anchor-quit-save');
  await expect(page.locator('#anchor-summary')).toBeVisible();
  await expect(page.locator('#anchor-upload')).toContainText('Added to math-flu_Randy_2026-06-19.sqlite', { timeout: 10_000 });
  await expect(page.locator('#anchor-upload')).toContainText('Single-session archived to s3://[S3-BUCKET]/math-quiz/single-sessions/');
  await expect(page.locator('#anchor-upload')).toContainText('Snapshot backed up to s3://[S3-BUCKET]/math-quiz/_backup-s3/');
  // The single-session file path (from the server) is shown; the old Download button is gone.
  await expect(page.locator('#anchor-file-info')).toContainText('Archived single-session copy:');
  await expect(page.locator('#anchor-file-info')).toContainText('_single-session-sqlite-files/math-flu_Randy_2026-06-20_120000.sqlite');
  expect(await page.locator('#anchor-download').count()).toBe(0);

  expect(saveBody).toBeTruthy();
  expect(saveBody.sourceFolder).toBe('real');
  expect(saveBody.destination).toBe('source');
  expect(saveBody.name).toBe('Randy');
  expect(saveBody.forceNew).toBe(false);
  expect(saveBody.sourceFile).toBe('math-flu_Randy_2026-06-19.sqlite');
  expect(saveBody.uploadS3).toBeUndefined();
  expect(typeof saveBody.stamp).toBe('string');
  expect((saveBody.base64 || '').length).toBeGreaterThan(0);
});

test('Continue with no source file is blocked at Start with an error', async ({ page, context }) => {
  await routeCdns(context);
  await mockBroker(context);   // latest -> found:false for everyone
  await page.goto('/anchor.html?setup=1&fb=0&practice=0');
  await page.fill('#anchor-source-folder', 'real');
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'Ghost');
  await page.keyboard.press('Escape');
  await page.click('#anchor-start');
  await expect(page.locator('#anchor-error')).toContainText('No file for "Ghost" in source folder "real" to continue');
  await expect(page.locator('#anchor-quiz')).toBeHidden();   // never started
  expect(saveBody).toBeNull();
});

test('Start new file posts forceNew=true on save', async ({ page, context }) => {
  await routeCdns(context);
  await mockBroker(context);
  page.on('dialog', (d) => d.accept());
  await page.goto('/anchor.html?setup=1&fb=0&practice=0');
  await page.fill('#anchor-source-folder', 'real');
  await page.check('#anchor-mode-new');
  await page.click('#anchor-username');
  await page.fill('#anchor-username', 'Randy');
  await page.keyboard.press('Escape');
  await page.click('#anchor-start');
  await clickAnchorGo(page);
  for (let i = 0; i < 2; i++) {
    const m = ((await page.textContent('#anchor-problem')) || '').match(/(-?\d+)\s*\+\s*(-?\d+)/);
    if (!m) break;
    await page.locator('#anchor-answer').pressSequentially(String(Number(m[1]) + Number(m[2])));
  }
  await page.click('#anchor-quit-save');
  await expect(page.locator('#anchor-summary')).toBeVisible();
  await expect(page.locator('#anchor-upload')).toContainText('Added to', { timeout: 10_000 }); // wait for the POST
  expect(saveBody).toBeTruthy();
  expect(saveBody.forceNew).toBe(true);
});
