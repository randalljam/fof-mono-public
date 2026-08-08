// FULL browser playthrough of the dragon fluency game with a simulated learner.
//
// Drives the REAL game (dragon/index.html) in headless Chromium against the
// real dev server: discovers the egg with Minecraft-style controls, plays every
// Fluency Feast burst by typing answers on the keyboard, waits through hatch /
// milestone / flight cutscenes, and rides the dragon at 100%. The learner model
// (simulation/dragon_learner.mjs) supplies answers + response times; think time
// is injected through a performance.now() offset (see installSimClock) so the
// recorded response_time_ms matches the model without waiting wall-clock.
//
// Artifacts (events.jsonl, screenshots, report.md) land in a per-run folder
// under dragon/playtests/runs/ (gitignored). Set DRAGON_REPORT_OUT to also
// write the tracked markdown report.
//
// Run: cd apps/math-quiz/tests && npm run test:playthrough
import { test, expect } from '@playwright/test';
import { mkdirSync, rmSync, writeFileSync, appendFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { SERVER_DATA_DIR, PLAYTHROUGH_PORT } from '../playwright.playthrough.config.mjs';
import { writeSeedDb } from '../../simulation/dragon_seed.mjs';
import { createSimLearner } from '../../simulation/dragon_learner.mjs';
import { createAppFns, queryAttempts } from '../../simulation/dragon_playthrough.mjs';
import { statusSnapshot, medianRtByTier, buildReportMarkdown } from '../../simulation/playthrough_report.mjs';
import { MILESTONES } from '../../dragon/sim/milestones.js';
import { loadSqlJs } from '../../simulation/sql_node.mjs';
import {
  routeDragonCdns, installSimClock, installPointerLockShim, lockPointer,
  waitLockable, aimAtLabel, synthClick, clickQuizGo, readQuizState, readHud, readGameState,
  readToasts, pumpFrames, walkKey, dismissStory,
} from './playthrough_helpers.mjs';

const appDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const FOLDER = 'playtest';
const USER = 'DragonSim';
const SEED = process.env.DRAGON_SEED || 'dragon-browser';
const MAX_BURSTS = Number(process.env.DRAGON_MAX_BURSTS || '60');
const BASE_URL = `http://127.0.0.1:${PLAYTHROUGH_PORT}`;

function stampNow() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}_${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`;
}
const RUN_DIR = path.join(appDir, 'dragon', 'playtests', 'runs', `${stampNow()}_browser`);

let SQL, fns, seedInfo;
const events = [];
const eventsPath = path.join(RUN_DIR, 'events.jsonl');
function emit(e) {
  events.push(e);
  appendFileSync(eventsPath, JSON.stringify(e) + '\n');
}
let shotCount = 0;
async function shot(page, label, burst = null) {
  shotCount += 1;
  const file = `${String(shotCount).padStart(2, '0')}_${label.replace(/[^a-z0-9-]+/gi, '-')}.png`;
  await page.screenshot({ path: path.join(RUN_DIR, file) }).catch(() => {});
  emit({ type: 'screenshot', file, label, burst });
}

// Authoritative fluency + per-category snapshot from the server's saved file
// (exactly what the game recomputes after each save).
async function serverFluency() {
  const resp = await fetch(`${BASE_URL}/api/latest-user-db?folder=${FOLDER}&user=${USER}`);
  const j = await resp.json();
  if (!j.ok || !j.found) return { pct: 0, snap: null, filename: null };
  const bytes = new Uint8Array(Buffer.from(j.base64, 'base64'));
  const attempts = queryAttempts(SQL, bytes, USER);
  const pct = fns.fluencyPercent(attempts, fns.thresholds, { numberRange: [0, 9], operations: ['+'], excludeFlagged: true });
  const snap = statusSnapshot(attempts, fns.evaluateFluencyStatus, fns.thresholds);
  return { pct, snap, filename: j.filename };
}

test.beforeAll(async () => {
  mkdirSync(RUN_DIR, { recursive: true });
  writeFileSync(eventsPath, '');
  // Fresh sandbox lineage for every run (never touches real folders).
  rmSync(path.join(SERVER_DATA_DIR, FOLDER), { recursive: true, force: true });
  rmSync(path.join(SERVER_DATA_DIR, '_single-session-sqlite-files'), { recursive: true, force: true });
  SQL = await loadSqlJs();
  fns = createAppFns();
  seedInfo = await writeSeedDb({ dataDir: SERVER_DATA_DIR, folder: FOLDER, user: USER, seed: `${SEED}-seed` });
  emit({
    type: 'seed', filename: seedInfo.filename, startPct: seedInfo.startPct,
    greenCount: seedInfo.greenCount, byCategory: seedInfo.byCategory, sessions: seedInfo.sessions,
  });
});

test('full dragon playthrough: egg to flight-ride through the real UI', async ({ page, context }) => {
  const learner = createSimLearner({ seed: `${SEED}-learner` });
  const pageErrors = [];
  page.on('pageerror', (err) => pageErrors.push(String(err.message || err)));
  await routeDragonCdns(context);
  await installSimClock(context);
  await installPointerLockShim(context);

  emit({
    type: 'run-start',
    meta: {
      user: USER, folder: FOLDER, seed: SEED, startedAt: new Date().toISOString(),
      learnerParams: learner.params, tierStart: learner.tierStart,
      startPct: seedInfo.startPct,
    },
  });

  // Use the explicit one-shot resume entry so the isolated simulator can select
  // its synthetic learner without weakening the real cold-open player picker.
  await page.goto(`/dragon/index.html?folder=${FOLDER}&user=${USER}&resume=1`);
  await expect(page.locator('#loading-screen')).toHaveClass(/hidden/, { timeout: 60_000 });
  await expect(page.locator('.hud-panel')).toBeVisible({ timeout: 20_000 });
  emit({ type: 'ux', burst: 0, note: `game loaded; HUD: ${JSON.stringify(await readHud(page))}` });
  await shot(page, 'loaded', 0);

  // --- Egg discovery ---
  expect(await lockPointer(page)).toBe(true);
  const eggLabel = await aimAtLabel(page, ['egg']);
  expect(eggLabel, 'crosshair should find the egg').toBeTruthy();
  await synthClick(page);
  await expect(page.locator('#howto-root')).not.toHaveClass(/hidden/, { timeout: 8000 });
  emit({ type: 'ux', burst: 0, note: `egg discovered ("${eggLabel}"); how-to-play shown` });
  await shot(page, 'egg-found-howto', 0);
  await page.locator('#howto-root button', { hasText: 'Got it!' }).click();
  await expect(page.locator('#howto-root')).toHaveClass(/hidden/);
  // Mama Dragon's first letter renders beneath the how-to at discovery.
  await shot(page, 'first-story-letter', 0);
  const discoveryCards = await dismissStory(page, { waitMs: 4000 });
  if (discoveryCards.length) emit({ type: 'ux', burst: 0, note: `discovery story: ${discoveryCards.map((c) => c.title).join(' | ')}` });

  let celebrated = (await readGameState(page, USER))?.celebratedIds || [];
  let { pct } = await serverFluency();
  let burst = 0;
  let rideUnlocked = false;

  while (burst < MAX_BURSTS && !rideUnlocked) {
    burst += 1;
    const state = await readGameState(page, USER);
    const hatched = !!(state && state.hatched);

    // Re-lock (celebrations unlock the pointer) and aim at the practice target.
    // Post-hatch the dragon follows the player and can sit almost underfoot,
    // where the crosshair raycast misses it — back away instead of approaching.
    expect(await waitLockable(page), `pointer lockable before burst ${burst}`).toBe(true);
    const target = hatched ? ['practice'] : ['egg'];
    if (hatched) await walkKey(page, 's', 350);
    const label = await aimAtLabel(page, target, hatched ? { moveKey: 's', walks: 5 } : {});
    expect(label, `interactable ${target[0]} found before burst ${burst}`).toBeTruthy();
    await synthClick(page);
    await expect(page.locator('#quiz-root')).not.toHaveClass(/hidden/, { timeout: 8000 });
    await clickQuizGo(page);
    emit({ type: 'burst-start', burst, pctBefore: pct, via: target[0] });
    if (burst === 1) await shot(page, 'first-quiz', burst);

    // --- Answer the burst ---
    const problemEvents = [];
    let guard = 0;
    let lastProgress = '';
    while (guard++ < 150) {
      const q = await readQuizState(page);
      if (!q.open) break;
      if (q.waitingForCorrection) {
        await page.locator('.quiz-correction').getByRole('button', { name: 'Continue', exact: true }).click();
        await page.waitForFunction((prev) => {
          const root = document.getElementById('quiz-root');
          if (!root || root.classList.contains('hidden')) return true;
          const p = document.querySelector('.quiz-progress');
          return p && p.textContent.trim() !== prev;
        }, lastProgress, { timeout: 5000 });
        continue;
      }
      if (q.waitingForGo || !q.problem || q.progress === lastProgress) {
        await page.waitForTimeout(120);
        continue;
      }
      lastProgress = q.progress;
      const a = learner.answer(q.problem);
      // Spend the model's think time on the sim clock (minus real typing time).
      await page.evaluate((ms) => window.__simClockAdvance(ms), Math.max(50, Math.round(a.rtMs - 300)));
      await page.keyboard.type(a.userAnswerString, { delay: 40 });
      const advanced = await page.waitForFunction((prev) => {
        const root = document.getElementById('quiz-root');
        if (!root || root.classList.contains('hidden')) return true;
        const correction = document.querySelector('.quiz-correction');
        if (correction && !correction.classList.contains('hidden')) return true;
        const p = document.querySelector('.quiz-progress');
        return p && p.textContent.trim() !== prev;
      }, lastProgress, { timeout: 5000 }).catch(() => null);
      if (!advanced) {
        // Wrong answer with fewer digits than the correct one needs Enter.
        await page.keyboard.press('Enter');
        await page.waitForFunction((prev) => {
          const root = document.getElementById('quiz-root');
          if (!root || root.classList.contains('hidden')) return true;
          const correction = document.querySelector('.quiz-correction');
          if (correction && !correction.classList.contains('hidden')) return true;
          const p = document.querySelector('.quiz-progress');
          return p && p.textContent.trim() !== prev;
        }, lastProgress, { timeout: 5000 }).catch(() => null);
      }
      const pe = {
        type: 'problem', burst, problemText: q.problem, category: a.category,
        tier: a.tier, exposure: a.exposure, isCorrect: a.isCorrect, rtMs: Math.round(a.rtMs),
      };
      problemEvents.push(pe);
      emit(pe);
    }
    await expect(page.locator('#quiz-root')).toHaveClass(/hidden/, { timeout: 10_000 });

    // --- Save lands; collect toasts + (maybe) one milestone celebration ---
    const toasts = new Set();
    const before = celebrated.slice();
    const deadline = Date.now() + 30_000;
    let saveSeenAt = 0;
    while (Date.now() < deadline) {
      for (const t of await readToasts(page)) toasts.add(t);
      const s = await readGameState(page, USER);
      const ids = (s && s.celebratedIds) || [];
      if (ids.length > before.length) {
        // A celebration fired — give the cutscene a beat, then screenshot it.
        await page.waitForTimeout(1200);
        for (const t of await readToasts(page)) toasts.add(t);
        const newIds = ids.filter((id) => !before.includes(id));
        for (const id of newIds) {
          const m = MILESTONES.find((x) => x.id === id);
          emit({ type: 'milestone', id, title: (m && m.title) || id, thresholdPct: m ? m.pct : null, burst, maxPct: s.maxPct });
          await shot(page, `milestone-${id}`, burst);
        }
        celebrated = ids;
        break;
      }
      // handleBurstEnd bumps totalBursts right after the save; celebrations (if
      // any) queue immediately after. If none fires within a few seconds of the
      // save being recorded, this burst had no milestone.
      if (s && s.totalBursts >= burst) {
        if (!saveSeenAt) saveSeenAt = Date.now();
        else if (Date.now() - saveSeenAt > 6000) break;
      }
      await page.waitForTimeout(500);
    }

    // --- Story sequence after the burst (reaction + next scroll + naming) ---
    const storyCards = await dismissStory(page, { dragonName: 'Sparkle' });
    if (storyCards.length) {
      emit({ type: 'story', burst, cards: storyCards.map((c) => ({ kicker: c.kicker, title: c.title, naming: c.naming })) });
      if (burst === 1 || storyCards.some((c) => c.naming)) await shot(page, storyCards.some((c) => c.naming) ? 'story-naming' : 'first-story-card', burst);
    }
    const handoffOffer = page.locator('.quiz-handoff-offer');
    if (await handoffOffer.isVisible()) {
      await handoffOffer.getByRole('button', { name: 'Keep playing', exact: true }).click();
      await expect(page.locator('#quiz-root')).toHaveClass(/hidden/);
    }

    const after = await serverFluency();
    const stateAfter = await readGameState(page, USER);
    rideUnlocked = !!(stateAfter && stateAfter.rideUnlocked);
    const servedByCategory = {};
    for (const pe of problemEvents) servedByCategory[pe.category] = (servedByCategory[pe.category] || 0) + 1;
    emit({
      type: 'burst-end', burst,
      pctBefore: pct, pctAfter: after.pct, maxPct: stateAfter ? stateAfter.maxPct : null,
      correct: problemEvents.filter((p) => p.isCorrect).length, total: problemEvents.length,
      medianRtByTier: medianRtByTier(problemEvents),
      servedByCategory,
      byCategory: after.snap ? after.snap.byCategory : null,
      greenCount: after.snap ? after.snap.greenCount : null,
      savedFilename: after.filename,
      toasts: Array.from(toasts),
      hud: await readHud(page),
    });
    if (toasts.size) emit({ type: 'ux', burst, note: `toasts: ${Array.from(toasts).join(' | ')}` });
    pct = after.pct;
    console.log(`[browser burst ${burst}] -> ${Math.round(pct)}% (celebrated: ${celebrated.join(',') || 'none'})`);
  }

  // --- Finale: wait out the flight cinematic, then ride ---
  expect(rideUnlocked, 'flight-ride should unlock at 100%').toBe(true);
  await waitLockable(page, { timeoutMs: 60_000 });
  await shot(page, 'after-flight-cinematic', burst);
  await lockPointer(page);
  await walkKey(page, 's', 350);
  await aimAtLabel(page, ['practice', 'dragon'], { walks: 3, moveKey: 's' });   // face the dragon (E mounts within 8 units)
  await page.keyboard.press('e');
  await pumpFrames(page, 30);
  await shot(page, 'ride-mounted', burst);
  await page.keyboard.down('w');
  await page.waitForTimeout(1500);
  await page.keyboard.up('w');
  await shot(page, 'riding-flight', burst);
  emit({ type: 'ux', burst, note: 'pressed E near dragon after 100% cinematic; ride + forward flight screenshotted' });

  // --- Assertions on the arc ---
  const finalState = await readGameState(page, USER);
  const expectedOrder = ['hatch', 'wings', 'jump', 'fire', 'flight-ride'];
  const nonEgg = finalState.celebratedIds.filter((id) => id !== 'egg-found');
  expect(nonEgg).toEqual(expectedOrder);
  expect(new Set(nonEgg).size).toBe(nonEgg.length);   // each exactly once
  expect(finalState.rideUnlocked).toBe(true);
  expect(Math.round(pct)).toBe(100);
  // Story arc: the first letter was seen, the dragon got named, scrolls accrued.
  expect(finalState.seenBeatIds).toContain('egg-letter-1');
  expect(finalState.seenBeatIds).toContain('hatch-name');
  expect(finalState.dragonName).toBe('Sparkle');
  expect(new Set(finalState.seenBeatIds).size).toBe(finalState.seenBeatIds.length);

  emit({
    type: 'run-end',
    bursts: burst,
    finalPct: pct,
    maxPct: finalState.maxPct,
    rideUnlocked: finalState.rideUnlocked,
    hatched: finalState.hatched,
    celebratedIds: finalState.celebratedIds,
    pageErrors,
    durationMs: Date.now() - Date.parse(events.find((e) => e.type === 'run-start').meta.startedAt),
  });
  if (pageErrors.length) emit({ type: 'ux', burst, note: `page errors seen: ${pageErrors.join(' || ')}` });
});

test.afterAll(async () => {
  const md = buildReportMarkdown(events, {
    mode: 'browser (Playwright, real game UI)',
    user: USER, folder: FOLDER, seed: SEED,
    runDirNote: `Run artifacts: \`${path.relative(appDir, RUN_DIR)}\` (gitignored).`,
  });
  writeFileSync(path.join(RUN_DIR, 'report.md'), md);
  if (process.env.DRAGON_REPORT_OUT) {
    const out = path.resolve(process.env.DRAGON_REPORT_OUT);
    writeFileSync(out, buildReportMarkdown(events, {
      mode: 'browser (Playwright, real game UI)',
      user: USER, folder: FOLDER, seed: SEED, fileName: path.basename(out),
      runDirNote: `Run artifacts: \`${path.relative(appDir, RUN_DIR)}\` (gitignored).`,
    }));
    console.log(`[playthrough] tracked report: ${out}`);
  }
  console.log(`[playthrough] events + screenshots + report: ${RUN_DIR}`);
});
