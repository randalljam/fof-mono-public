import test from 'node:test';
import assert from 'node:assert/strict';
import {
  ensureStations, cleanSignText, setSignText, signText,
  stationLevel, fountainTier, growTier, resolveStationQuiz, stationLabel,
  SIGN_IDS, GROW_IDS, MAX_LEVEL, SIGN_MAX_LEN, STATIONS_INTRO, GROW_INFO,
} from '../dragon/sim/stations.js';
import { createGameState } from '../dragon/sim/game_state.js';
import { buildGmSnapshot } from '../dragon/sim/gm_state.js';

function baseState(over = {}) {
  return Object.assign({
    maxPct: 63, hatched: true, rideUnlocked: false, eggFound: true,
    dragonName: 'Ember', seenBeatIds: [], visitedStones: [], totalBursts: 5,
    celebratedIds: ['egg-found', 'hatch'], gems: 30,
    volcano: { intro: true, cleared: 5, summited: true },
  }, over);
}

test('ensureStations backfills empty and partial saves', () => {
  const s1 = baseState();
  const st = ensureStations(s1);
  assert.deepEqual(Object.keys(st.signs).sort(), [...SIGN_IDS].sort());
  for (const id of SIGN_IDS) assert.equal(st.signs[id], '');
  for (const id of GROW_IDS) assert.equal(st.levels[id], 0);
  assert.equal(st.intro, false);
  // Partial (a save from before a key existed) keeps what it has.
  const s2 = baseState({ stations: { signs: { 'sign-welcome': 'HI' }, levels: { nest: 2 } } });
  const st2 = ensureStations(s2);
  assert.equal(st2.signs['sign-welcome'], 'HI');
  assert.equal(st2.signs['sign-dragon'], '');
  assert.equal(st2.levels.nest, 2);
  assert.equal(st2.levels.trees, 0);
});

test('sign text: cleaned, capped, and round-trips; unknown sign rejected', () => {
  assert.equal(cleanSignText('  hello   dragon \n world '), 'hello dragon world');
  assert.equal(cleanSignText('x'.repeat(99)).length, SIGN_MAX_LEN);
  assert.equal(cleanSignText(null), '');
  const s = baseState();
  assert.equal(setSignText(s, 'sign-welcome', '  Kid1   rules!  '), 'Kid1 rules!');
  assert.equal(signText(s, 'sign-welcome'), 'Kid1 rules!');
  assert.equal(setSignText(s, 'sign-nope', 'x'), null);
});

test('grow stations level up once per finished quiz, stop at MAX_LEVEL', () => {
  const s = baseState();
  for (let expected = 1; expected <= MAX_LEVEL; expected++) {
    const r = resolveStationQuiz(s, 'nest', 'list-complete');
    assert.equal(r.ok, true);
    assert.equal(r.level, expected);
    assert.equal(r.reveal, GROW_INFO.nest.reveals[expected - 1]);
  }
  assert.equal(stationLevel(s, 'nest'), MAX_LEVEL);
  assert.deepEqual(resolveStationQuiz(s, 'nest', 'list-complete'), { ok: false, reason: 'maxed' });
});

test('quitting early or unknown stations change nothing', () => {
  const s = baseState();
  assert.deepEqual(resolveStationQuiz(s, 'trees', 'quit-saved'), { ok: false, reason: 'incomplete' });
  assert.equal(stationLevel(s, 'trees'), 0);
  assert.deepEqual(resolveStationQuiz(s, 'volcano', 'list-complete'), { ok: false, reason: 'unknown' });
});

test('signs succeed on every completed quiz (rewrite any time)', () => {
  const s = baseState();
  assert.deepEqual(resolveStationQuiz(s, 'sign-welcome', 'list-complete'), { ok: true, kind: 'sign', id: 'sign-welcome' });
  setSignText(s, 'sign-welcome', 'First words');
  assert.equal(resolveStationQuiz(s, 'sign-welcome', 'list-complete').ok, true);
});

test('fountain tier counts the 140-gem reveal as tier 1', () => {
  const poor = baseState({ gems: 30 });
  assert.equal(fountainTier(poor), 0);
  const rich = baseState({ gems: 150 });
  assert.equal(fountainTier(rich), 1);
  // First station quiz on a gem-revealed fountain jumps to tier 2, so the
  // player always sees a change.
  const r = resolveStationQuiz(rich, 'fountain', 'list-complete');
  assert.equal(r.level, 2);
  assert.equal(fountainTier(rich), 2);
  // Without gems it walks 0 -> 1 -> 2 -> 3.
  assert.equal(resolveStationQuiz(poor, 'fountain', 'list-complete').level, 1);
  assert.equal(growTier(poor, 'fountain'), 1);
});

test('station labels invite, report progress, and celebrate max', () => {
  const s = baseState();
  assert.match(stationLabel(s, 'sign-welcome'), /write on this sign/);
  setSignText(s, 'sign-welcome', 'Hi');
  assert.match(stationLabel(s, 'sign-welcome'), /change your sign/);
  assert.match(stationLabel(s, 'fountain'), /dry old fountain/);
  assert.match(stationLabel(s, 'nest'), /grow the nest \(0\/3\)/);
  s.stations.levels.trees = MAX_LEVEL;
  assert.match(stationLabel(s, 'trees'), /fully grown/);
});

test('fresh game state ships a stations block; GM snapshot carries it', () => {
  const fresh = createGameState('StationTester').load();
  assert.ok(fresh.stations);
  ensureStations(fresh);
  const snap = buildGmSnapshot({
    state: baseState({ stations: { signs: { 'sign-welcome': 'Yo' }, levels: { nest: 2 }, intro: true } }),
    pct: 63, user: 'T', folder: 'test',
  });
  assert.equal(snap.stations.signs['sign-welcome'], 'Yo');
  assert.equal(snap.stations.levels.nest, 2);
});

test('intro letter points at the signs and the growable spots', () => {
  assert.match(STATIONS_INTRO, /sign/i);
  assert.match(STATIONS_INTRO, /fountain/i);
  assert.match(STATIONS_INTRO, /trees/i);
});
