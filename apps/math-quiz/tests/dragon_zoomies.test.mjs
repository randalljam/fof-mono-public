import test from 'node:test';
import assert from 'node:assert/strict';
import {
  ZOOMIE_BANDS, ZOOMIE_ALERTS, ZOOMIE_ESCAPES, ZOOMIES_INTRO, ZOOMIE_GRADUATION,
  ZOOMIE_INTERVAL_S, zoomieBandFor, zoomieLineFor, zoomieAlertFor, zoomieEscapeFor,
  zoomiesIntroText, ensureZoomies, zoomiesEligible, resolveZoomieQuiz,
} from '../dragon/sim/zoomies.js';

function stateWith(celebratedIds, extra = {}) {
  return Object.assign({ hatched: true, celebratedIds }, extra);
}

test('every band from 81 to 89 has exactly 3 lines', () => {
  const bands = Object.keys(ZOOMIE_BANDS).map(Number).sort((a, b) => a - b);
  assert.deepEqual(bands, [81, 82, 83, 84, 85, 86, 87, 88, 89]);
  for (const b of bands) assert.equal(ZOOMIE_BANDS[b].length, 3, `band ${b}`);
});

test('zoomieBandFor clamps below, above, and floors within range', () => {
  assert.equal(zoomieBandFor(0), 81);
  assert.equal(zoomieBandFor(80.4), 81);
  assert.equal(zoomieBandFor(81), 81);
  assert.equal(zoomieBandFor(84.9), 84);
  assert.equal(zoomieBandFor(89.2), 89);
  assert.equal(zoomieBandFor(95), 89);
});

test('zoomieLineFor cycles the 3 band lines and fills the dragon name', () => {
  const seen = new Set();
  for (let i = 0; i < 6; i++) seen.add(zoomieLineFor(83, i, 'Pipa'));
  assert.equal(seen.size, 3);
  for (const line of ZOOMIE_BANDS[81]) assert.ok(!line.includes('{name}') || zoomieLineFor(81, 0, 'Pipa').includes('Pipa'));
});

test('alerts and escapes cycle and never leak the placeholder', () => {
  for (let i = 0; i < ZOOMIE_ALERTS.length + 2; i++) {
    assert.ok(!zoomieAlertFor(i, 'Pipa').includes('{name}'));
    assert.ok(!zoomieEscapeFor(i, 'Pipa').includes('{name}'));
  }
  assert.equal(zoomieAlertFor(0, 'Pipa'), zoomieAlertFor(ZOOMIE_ALERTS.length, 'Pipa'));
  assert.ok(zoomieAlertFor(0, null).includes('your dragon'));
});

test('intro and graduation content exist and intro fills name', () => {
  assert.ok(ZOOMIES_INTRO.length > 50);
  assert.ok(ZOOMIE_GRADUATION.length > 50);
  assert.ok(zoomiesIntroText('Pipa').includes('Pipa'));
  assert.ok(!zoomiesIntroText('Pipa').includes('{name}'));
  assert.ok(ZOOMIE_INTERVAL_S > 0);
});

test('ensureZoomies backfills old saves and preserves existing progress', () => {
  const state = {};
  const z = ensureZoomies(state);
  assert.deepEqual(z, { intro: false, calmed: 0, alerts: 0, graduated: false });
  state.zoomies.calmed = 5;
  assert.equal(ensureZoomies(state).calmed, 5);
});

test('zoomiesEligible: only hatched dragons in the jump-to-fire window', () => {
  assert.equal(zoomiesEligible(stateWith(['hatch', 'wings'])), false);
  assert.equal(zoomiesEligible(stateWith(['hatch', 'wings', 'jump'])), true);
  assert.equal(zoomiesEligible(stateWith(['hatch', 'wings', 'jump', 'fire'])), false);
  assert.equal(zoomiesEligible(stateWith(['jump'], { hatched: false })), false);
});

test('resolveZoomieQuiz calms only on list-complete and advances the counter', () => {
  const state = stateWith(['hatch', 'wings', 'jump']);
  const quit = resolveZoomieQuiz(state, 'quit-saved', 81, 'Pipa');
  assert.equal(quit.calmed, false);
  assert.equal(state.zoomies.calmed, 0);
  assert.ok(ZOOMIE_ESCAPES.some((l) => quit.text === l.replaceAll('{name}', 'Pipa')));
  const first = resolveZoomieQuiz(state, 'list-complete', 81, 'Pipa');
  const second = resolveZoomieQuiz(state, 'list-complete', 81, 'Pipa');
  const third = resolveZoomieQuiz(state, 'list-complete', 81, 'Pipa');
  const fourth = resolveZoomieQuiz(state, 'list-complete', 81, 'Pipa');
  assert.equal(state.zoomies.calmed, 4);
  assert.notEqual(first.text, second.text);
  assert.notEqual(second.text, third.text);
  assert.equal(first.text, fourth.text); // cycles after 3 within the same percent
});

test('GM overrides replace a band pool, cycle at its own length, and fall back when empty', () => {
  const overrides = { '83': ['Custom A {name}', 'Custom B', 'Custom C', 'Custom D'] };
  assert.equal(zoomieLineFor(83, 0, 'Pipa', overrides), 'Custom A Pipa');
  assert.equal(zoomieLineFor(83, 4, 'Pipa', overrides), 'Custom A Pipa'); // 4-line pool cycles at 4
  assert.equal(zoomieLineFor(83.7, 1, 'Pipa', overrides), 'Custom B');
  assert.equal(zoomieLineFor(84, 0, 'Pipa', overrides), zoomieLineFor(84, 0, 'Pipa')); // untouched band = default
  assert.equal(zoomieLineFor(83, 0, 'Pipa', { '83': [] }), zoomieLineFor(83, 0, 'Pipa')); // empty override falls back
  const state = stateWith(['hatch', 'wings', 'jump']);
  const r = resolveZoomieQuiz(state, 'list-complete', 83, 'Pipa', overrides);
  assert.equal(r.text, 'Custom A Pipa');
});

test('resolveZoomieQuiz lines follow the fluency percent as it rises', () => {
  const state = stateWith(['hatch', 'wings', 'jump']);
  const at81 = resolveZoomieQuiz(state, 'list-complete', 81.6, 'Pipa');
  const at85 = resolveZoomieQuiz(state, 'list-complete', 85.2, 'Pipa');
  assert.ok(ZOOMIE_BANDS[81].some((l) => at81.text === l.replaceAll('{name}', 'Pipa')));
  assert.ok(ZOOMIE_BANDS[85].some((l) => at85.text === l.replaceAll('{name}', 'Pipa')));
});
