// E2E: cross-device handoff with mocked /api/dragon-handoff (hermetic; no dev_server required).
import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { routeCdns } from './helpers.mjs';

let VALID_DB_B64 = '';
try {
  const initSqlJs = (await import('sql.js')).default;
  const wasmBinary = readFileSync(new URL('../node_modules/sql.js/dist/sql-wasm.wasm', import.meta.url));
  const SQL = await initSqlJs({ wasmBinary });
  const db = new SQL.Database();
  VALID_DB_B64 = Buffer.from(db.export()).toString('base64');
  db.close();
} catch { /* sql.js absent */ }

function createHandoffMock() {
  let record = { revision: 0, owner: null, pendingTransfer: null, checkpoint: null };
  return {
    handle(body) {
      const action = body.action;
      if (action === 'initialize') {
        record.revision = 1;
        record.owner = {
          deviceId: body.deviceId, deviceType: body.deviceType,
          token: 'tok-init', lastSeenAt: new Date().toISOString(),
        };
        record.checkpoint = body.checkpoint;
        record.pendingTransfer = null;
        return { ok: true, revision: 1, ownerToken: 'tok-init', isOwner: true, checkpoint: body.checkpoint };
      }
      if (action === 'transfer') {
        if (!record.owner || record.owner.deviceId !== body.deviceId) {
          return { ok: false, error: 'stale owner or wrong token' };
        }
        record.revision += 1;
        record.checkpoint = body.checkpoint;
        record.pendingTransfer = { targetDeviceType: body.targetDeviceType, requestedAt: new Date().toISOString() };
        record.owner = null;
        return { ok: true, revision: record.revision, pendingTransfer: record.pendingTransfer, inactiveReason: 'transferred' };
      }
      if (action === 'claim') {
        if (!record.pendingTransfer || record.pendingTransfer.targetDeviceType !== body.deviceType) {
          return { ok: false, error: 'wrong device type for pending transfer' };
        }
        record.revision += 1;
        record.owner = {
          deviceId: body.deviceId, deviceType: body.deviceType,
          token: 'tok-claim', lastSeenAt: new Date().toISOString(),
        };
        record.pendingTransfer = null;
        return { ok: true, revision: record.revision, ownerToken: 'tok-claim', isOwner: true, checkpoint: record.checkpoint };
      }
      return { ok: false, error: 'unknown action' };
    },
    status(query) {
      const deviceId = query.get('deviceId') || '';
      const deviceType = query.get('deviceType') || 'desktop';
      const isOwner = !!(record.owner && record.owner.deviceId === deviceId);
      const canClaim = !!(record.pendingTransfer && record.pendingTransfer.targetDeviceType === deviceType && !isOwner);
      return {
        ok: true,
        found: !!record.checkpoint,
        revision: record.revision,
        owner: record.owner,
        pendingTransfer: record.pendingTransfer,
        isOwner,
        canClaim,
        inactiveReason: record.pendingTransfer && !isOwner ? 'transferred' : null,
      };
    },
  };
}

async function stubDragonApis(context, handoff) {
  await context.route(/\/api\/dragon-display-names/, (route) => route.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, names: {} }),
  }));
  await context.route(/\/api\/dragon-world/, (route) => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({ ok: true, found: false, gameState: null }),
  }));
  await context.route(/\/api\/latest-user-db/, (route) => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({
      ok: true, found: true, filename: 'math-flu_Randy.sqlite', sessionCount: 1,
      base64: VALID_DB_B64, problemLists: [], quickPractice: {}, targetedConfig: null,
    }),
  }));
  await context.route(/\/api\/dragon-state/, (route) => route.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }),
  }));
  await context.route(/\/api\/dragon-messages/, (route) => route.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, messages: [] }),
  }));
  await context.route(/\/api\/dragon-handoff/, async (route) => {
    const req = route.request();
    if (req.method() === 'GET') {
      const q = new URL(req.url()).searchParams;
      return route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify(handoff.status(q)),
      });
    }
    const body = JSON.parse(req.postData() || '{}');
    return route.fulfill({
      status: body.action && handoff.handle(body).ok ? 200 : 400,
      contentType: 'application/json',
      body: JSON.stringify(handoff.handle(body)),
    });
  });
  await context.route(/\/api\/save-run/, (route) => route.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, saved: true }),
  }));
}

test('desktop transfers to touch and touch claims on refresh', async ({ browser }) => {
  const handoff = createHandoffMock();
  const desktop = await browser.newContext({ viewport: { width: 1280, height: 720 } });
  const mobile = await browser.newContext({
    viewport: { width: 390, height: 844 },
    hasTouch: true,
    isMobile: true,
  });
  await routeCdns(desktop);
  await routeCdns(mobile);
  await stubDragonApis(desktop, handoff);
  await stubDragonApis(mobile, handoff);

  const dPage = await desktop.newPage();
  await dPage.addInitScript(() => {
    localStorage.setItem('dragon-handoff-device-id', 'desktop-e2e');
    localStorage.setItem('dragon-game::Randy', JSON.stringify({
      version: 3, learner: 'Randy', eggFound: true, totalBursts: 2, maxPct: 40,
      celebratedIds: ['egg-found'], gems: 10, volcano: { intro: false, cleared: 0, summited: false },
      lava: { intro: false, startPct: null, stopped: [], won: false },
      stations: { signs: {}, levels: {}, intro: false },
    }));
  });
  await dPage.goto('/dragon/index.html');
  await expect(dPage.locator('#player-picker')).toBeVisible({ timeout: 15000 });
  await dPage.getByRole('button', { name: 'Randy' }).click();
  await dPage.getByRole('button', { name: 'Continue my game' }).click();
  await expect(dPage.locator('#hud-root')).toBeVisible({ timeout: 20000 });
  // Boot can surface an unseen story/quest letter, which intentionally locks
  // HUD actions until the learner acknowledges it.
  const storyContinue = dPage.locator('#story-root .story-btn', { hasText: 'Continue' });
  if (await storyContinue.isVisible()) await storyContinue.click();
  const transferBtn = dPage.locator('.handoff-transfer').first();
  await expect(transferBtn).toBeVisible({ timeout: 15000 });
  await expect(transferBtn).toBeEnabled({ timeout: 15000 });
  await transferBtn.click();
  await expect(dPage.locator('#handoff-overlay')).toBeVisible();
  await expect(dPage.locator('#handoff-overlay')).toContainText('Transferred');
  await expect(dPage.locator('#handoff-takeover')).toBeVisible();
  await expect(dPage.locator('#handoff-takeover')).toHaveText('Take over here');
  await expect(dPage.locator('#handoff-refresh')).toBeHidden();

  const mPage = await mobile.newPage();
  await mPage.addInitScript(() => {
    localStorage.setItem('dragon-handoff-device-id', 'touch-e2e');
  });
  await mPage.goto('/dragon/index.html');
  await expect(mPage.locator('#player-picker')).toBeVisible({ timeout: 15000 });
  await mPage.getByRole('button', { name: 'Randy' }).click();
  await expect(mPage.locator('#hud-root')).toBeVisible({ timeout: 20000 });
  await expect(mPage.locator('#handoff-overlay')).toBeHidden({ timeout: 15000 });

  await desktop.close();
  await mobile.close();
});
