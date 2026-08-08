// Browser-driving helpers for the dragon playthrough spec: hermetic CDN routing
// (incl. three.js), pointer-lock control, crosshair aiming via synthetic
// mousemove (PointerLockControls reads movementX/movementY off document
// mousemove events), and quiz-overlay interaction.
import path from 'node:path';
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { expect } from '@playwright/test';
import { routeCdns } from '../e2e/helpers.mjs';

const testsDir = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const nm = (...p) => path.join(testsDir, 'node_modules', ...p);

// PointerLockControls sensitivity: yaw/pitch change = movement * 0.002 rad/px.
const RAD_PER_PX = 0.002;

// The dragon page additionally pulls three.js (module + addons) from jsdelivr.
// Serve the same pinned version from node_modules; later-registered routes win,
// so this takes precedence over routeCdns' abort for unmapped jsdelivr URLs.
export async function routeDragonCdns(context) {
  await routeCdns(context);
  await context.route(/cdn\.jsdelivr\.net\/npm\/three@[\d.]+\//, async (route) => {
    const url = new URL(route.request().url());
    const rel = url.pathname.replace(/^\/npm\/three@[\d.]+\//, '');
    const file = nm('three', ...rel.split('/'));
    if (!existsSync(file)) return route.abort();
    await route.fulfill({ body: readFileSync(file), contentType: 'text/javascript' });
  });
}

// Controllable performance.now() offset: the driver "spends" the simulated
// learner's think time by bumping the offset instead of waiting wall-clock, so
// the game records the model's response_time_ms while the run stays fast.
// Purely an init-script wrapper — no game code changes.
export async function installSimClock(context) {
  await context.addInitScript(() => {
    const orig = performance.now.bind(performance);
    let offset = 0;
    window.__simClockAdvance = (ms) => { offset += ms; };
    window.__simClockOffset = () => offset;
    performance.now = () => orig() + offset;
  });
}

// Headless Chromium does not grant real pointer lock; shim the Pointer Lock API
// (init script, no game code change) so the game's PointerLockControls sees the
// normal lock/unlock lifecycle. Synthetic mousemove events (see look()) supply
// movementX/movementY exactly as a locked pointer would.
export async function installPointerLockShim(context) {
  await context.addInitScript(() => {
    let lockedEl = null;
    Object.defineProperty(Document.prototype, 'pointerLockElement', {
      configurable: true,
      get() { return lockedEl; },
    });
    Element.prototype.requestPointerLock = function () {
      lockedEl = this;
      document.dispatchEvent(new Event('pointerlockchange'));
    };
    Document.prototype.exitPointerLock = function () {
      if (!lockedEl) return;
      lockedEl = null;
      document.dispatchEvent(new Event('pointerlockchange'));
    };
  });
}

export async function pumpFrames(page, n = 2) {
  await page.evaluate((count) => new Promise((res) => {
    let i = 0;
    const step = () => { i += 1; if (i >= count) res(); else requestAnimationFrame(step); };
    requestAnimationFrame(step);
  }), n);
}

export async function look(page, dx, dy) {
  await page.evaluate(({ mx, my }) => {
    document.dispatchEvent(new MouseEvent('mousemove', { movementX: mx, movementY: my, bubbles: true }));
  }, { mx: dx, my: dy });
}

export async function isPointerLocked(page) {
  return page.evaluate(() => document.pointerLockElement != null);
}

// Click the canvas to request pointer lock (needs the game's controls enabled).
export async function lockPointer(page, { timeoutMs = 3000 } = {}) {
  if (await isPointerLocked(page)) return true;
  const canvas = page.locator('#game-container canvas');
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    await canvas.click({ position: { x: 400, y: 300 }, force: true }).catch(() => {});
    await page.waitForTimeout(150);
    if (await isPointerLocked(page)) return true;
  }
  return false;
}

// Wait until the game re-enables controls after a cutscene/celebration and the
// pointer can be locked again.
export async function waitLockable(page, { timeoutMs = 40000 } = {}) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (await lockPointer(page, { timeoutMs: 1200 })) return true;
    await page.waitForTimeout(400);
  }
  return false;
}

export async function interactPrompt(page) {
  return page.evaluate(() => {
    const p = document.getElementById('interact-prompt');
    if (!p || p.classList.contains('hidden')) return null;
    return p.textContent || null;
  });
}

// Set an absolute downward pitch: slam the pitch to its up-clamp, then rotate
// down by (PI/2 + pitchDownRad).
export async function setPitchDown(page, pitchDownRad) {
  await look(page, 0, -Math.round((Math.PI) / RAD_PER_PX));
  await look(page, 0, Math.round((Math.PI / 2 + pitchDownRad) / RAD_PER_PX));
  await pumpFrames(page, 2);
}

// Sweep the view until the interact prompt matches one of `substrings`
// (case-insensitive). Tries several downward pitches; between full sweeps,
// takes a step (`moveKey`: 'w' to approach a fixed target like the egg, 's' to
// back away from one that follows the player, like the hatched dragon — the
// raycast has a 6-unit range and misses targets that are almost underfoot).
// Returns the matched prompt text or null.
export async function aimAtLabel(page, substrings, { walks = 4, pitches = [0.10, 0.28, 0.5, 0.75], stepPx = 30, moveKey = 'w' } = {}) {
  const wanted = substrings.map((s) => s.toLowerCase());
  const matches = (text) => {
    if (!text) return false;
    const t = text.toLowerCase();
    return wanted.some((w) => t.includes(w));
  };
  const stepsPerCircle = Math.ceil((2 * Math.PI) / (stepPx * RAD_PER_PX)) + 2;
  for (let walk = 0; walk <= walks; walk++) {
    for (const pitch of pitches) {
      await setPitchDown(page, pitch);
      for (let i = 0; i < stepsPerCircle; i++) {
        const text = await interactPrompt(page);
        if (matches(text)) return text;
        await look(page, stepPx, 0);
        await pumpFrames(page, 2);
      }
    }
    if (walk < walks) await walkKey(page, moveKey, 220);
  }
  return null;
}

export async function walkKey(page, key, ms) {
  await page.keyboard.down(key);
  await page.waitForTimeout(ms);
  await page.keyboard.up(key);
  await pumpFrames(page, 2);
}
export async function walkForward(page, ms) { await walkKey(page, 'w', ms); }

// Interact click while pointer-locked (synthetic click on the canvas — the
// game's click handler interacts with whatever the crosshair highlights).
export async function synthClick(page) {
  await page.evaluate(() => {
    const canvas = document.querySelector('#game-container canvas');
    if (canvas) canvas.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  });
}

export async function quizVisible(page) {
  return page.evaluate(() => {
    const root = document.getElementById('quiz-root');
    return !!root && !root.classList.contains('hidden');
  });
}

// Tap the Go gate overlay before the first quiz problem (same as anchor's clickAnchorGo).
// The button ignores clicks for ~400ms after open (pointer-lock unlock ghost click).
export async function clickQuizGo(page) {
  const overlay = page.locator('#quiz-go-overlay');
  await expect(overlay).toBeVisible({ timeout: 30_000 });
  const go = page.locator('#quiz-go');
  await expect(go).toBeVisible();
  await page.waitForFunction(() => {
    const btn = document.getElementById('quiz-go');
    return btn && !btn.disabled && getComputedStyle(btn).pointerEvents !== 'none';
  }, null, { timeout: 5000 });
  const deadline = Date.now() + 30_000;
  for (;;) {
    // A timed story (for example, the first zoomies letter) can appear after
    // the synthetic canvas interaction. Real clicks cannot pass through that
    // overlay, so dismiss it before retrying the Go button.
    await dismissStory(page, { waitMs: 0 });
    try {
      await go.click({ timeout: 2000 });
      break;
    } catch (err) {
      if (!(await readStoryCard(page)) || Date.now() >= deadline) throw err;
    }
  }
  await expect(overlay).toBeHidden();
}

export async function readQuizState(page) {
  return page.evaluate(() => {
    const root = document.getElementById('quiz-root');
    if (!root || root.classList.contains('hidden')) return { open: false };
    const go = document.getElementById('quiz-go-overlay');
    const waitingForGo = !!(go && !go.classList.contains('hidden'));
    const problem = document.querySelector('.quiz-problem');
    const progress = document.querySelector('.quiz-progress');
    const correction = document.querySelector('.quiz-correction');
    return {
      open: true,
      waitingForGo,
      problem: problem ? problem.textContent.trim() : '',
      progress: progress ? progress.textContent.trim() : '',
      waitingForCorrection: !!(correction && !correction.classList.contains('hidden')),
    };
  });
}

export async function readHud(page) {
  return page.evaluate(() => {
    const q = (sel) => {
      const el = document.querySelector(sel);
      return el ? el.textContent.trim() : null;
    };
    return {
      title: q('.hud-title'),
      pctLabel: q('.hud-pct'),
      foreshadow: q('.hud-foreshadow'),
      bursts: q('.hud-bursts'),
    };
  });
}

export async function readGameState(page, user) {
  return page.evaluate((u) => {
    const raw = localStorage.getItem(`dragon-game::${u}`);
    return raw ? JSON.parse(raw) : null;
  }, user);
}

// Collect currently-visible toast texts (milestone reveals, burst summaries).
export async function readToasts(page) {
  return page.evaluate(() => Array.from(document.querySelectorAll('.milestone-toast')).map((t) => t.textContent.trim()));
}

// Story overlay: read the currently-shown card (null when hidden).
export async function readStoryCard(page) {
  return page.evaluate(() => {
    const root = document.getElementById('story-root');
    if (!root || root.classList.contains('hidden')) return null;
    const q = (sel) => {
      const el = root.querySelector(sel);
      return el ? el.textContent.trim() : null;
    };
    return {
      kicker: q('.story-kicker'),
      title: q('.story-title'),
      text: q('.story-text'),
      naming: !!root.querySelector('.story-name-input'),
    };
  });
}
// Click through the post-burst story sequence (reaction card, story beat, GM
// letters). Types `dragonName` into the naming dialog when it appears. Returns
// the cards seen, for the playthrough report. `waitMs` covers the gap while a
// milestone cutscene still runs before the story shows; 0 dismisses only what
// is already open.
export async function dismissStory(page, { dragonName = 'Sparkle', waitMs = 25000 } = {}) {
  const cards = [];
  const deadline = Date.now() + waitMs;
  for (;;) {
    let card = await readStoryCard(page);
    while (!card && Date.now() < deadline) {
      await page.waitForTimeout(300);
      card = await readStoryCard(page);
    }
    if (!card) return cards;
    // Snapshot AFTER settling: a click mid-typewriter completes the text.
    await page.evaluate(() => document.querySelector('#story-root .story-card')?.click());
    cards.push(await readStoryCard(page) || card);
    if (card.naming) {
      await page.locator('.story-name-input').fill(dragonName);
    }
    await page.locator('#story-root .story-btn').click();
    await page.waitForTimeout(200);
    if (!(await readStoryCard(page))) {
      // Give a possible next card in the sequence a moment to render.
      await page.waitForTimeout(400);
      if (!(await readStoryCard(page))) return cards;
    }
  }
}
