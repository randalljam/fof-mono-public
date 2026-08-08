// Nest quiz stations: five clickable "make it yours" projects around the nest —
// two writable signs plus three growable elements (fountain, nest, trees).
// A finished quiz at a sign lets the player write (or rewrite) its words; a
// finished quiz at a grow station levels it up. DOM/THREE-free so tests and
// the sim can run it in Node.
import { NEST_UPGRADES } from './rewards.js';

export const SIGN_IDS = ['sign-welcome', 'sign-dragon'];
export const SIGN_MAX_LEN = 40;
export const GROW_IDS = ['fountain', 'nest', 'trees'];
export const MAX_LEVEL = 3;
const FOUNTAIN_GEM_COST = NEST_UPGRADES.find((u) => u.id === 'fountain').cost;

export const GROW_INFO = {
  fountain: {
    title: 'fountain',
    reveals: [
      '⛲ The old spring bubbles to life — your nest has a fountain!',
      '⛲ Your fountain grows a second tier. So splashy!',
      '🌈 A rainbow arches over your fountain. Magical!',
    ],
  },
  nest: {
    title: 'nest',
    reveals: [
      '🛏️ Cozy cushions and fresh straw — the nest is comfier than ever!',
      '⛱️ A canopy rises over the nest — shade for sleepy dragons!',
      '✨ Golden straw and twinkle-orbs — the fanciest nest in the valley!',
    ],
  },
  trees: {
    title: 'trees',
    reveals: [
      '🌸 The trees around your home burst into blossom!',
      '🍊 Fruit grows on every branch — dragon snacks!',
      '🏮 Little lanterns glow in the branches. So pretty at night!',
    ],
  },
};

// Backfill the nested stations object on old saves (Object.assign in
// game_state.load is shallow, so inner keys need their own defaulting).
export function ensureStations(state) {
  if (!state.stations) state.stations = {};
  const st = state.stations;
  if (!st.signs) st.signs = {};
  for (const id of SIGN_IDS) if (typeof st.signs[id] !== 'string') st.signs[id] = '';
  if (!st.levels) st.levels = {};
  for (const id of GROW_IDS) if (!Number.isInteger(st.levels[id])) st.levels[id] = 0;
  if (typeof st.intro !== 'boolean') st.intro = false;
  return st;
}
export function cleanSignText(text) {
  return String(text || '').replace(/\s+/g, ' ').trim().slice(0, SIGN_MAX_LEN);
}
export function setSignText(state, id, text) {
  if (!SIGN_IDS.includes(id)) return null;
  const st = ensureStations(state);
  st.signs[id] = cleanSignText(text);
  return st.signs[id];
}
export function signText(state, id) {
  return ensureStations(state).signs[id] || '';
}
export function stationLevel(state, id) {
  return ensureStations(state).levels[id] || 0;
}
// The fountain can also arrive via the 140-gem nest upgrade; that reveal counts
// as tier 1 (a running fountain), so station quizzes always change something.
export function fountainTier(state) {
  const gemBase = (state.gems || 0) >= FOUNTAIN_GEM_COST ? 1 : 0;
  return Math.max(stationLevel(state, 'fountain'), gemBase);
}
export function growTier(state, id) {
  return id === 'fountain' ? fountainTier(state) : stationLevel(state, id);
}
// Resolve a finished burst that was started by clicking a station. Signs
// succeed on every completed quiz (the prize is writing the sign); grow
// stations advance one level until MAX_LEVEL.
export function resolveStationQuiz(state, id, kind) {
  if (kind !== 'list-complete') return { ok: false, reason: 'incomplete' };
  if (SIGN_IDS.includes(id)) return { ok: true, kind: 'sign', id };
  if (!GROW_IDS.includes(id)) return { ok: false, reason: 'unknown' };
  const st = ensureStations(state);
  const current = growTier(state, id);
  if (current >= MAX_LEVEL) return { ok: false, reason: 'maxed' };
  st.levels[id] = current + 1;
  return { ok: true, kind: 'level', id, level: st.levels[id], reveal: GROW_INFO[id].reveals[st.levels[id] - 1] };
}
export function stationLabel(state, id) {
  if (SIGN_IDS.includes(id)) {
    return signText(state, id)
      ? '🪧 Do a quiz to change your sign!'
      : '🪧 Do a quiz to write on this sign!';
  }
  const info = GROW_INFO[id];
  if (!info) return 'Click to interact';
  const tier = growTier(state, id);
  if (tier >= MAX_LEVEL) return `⭐ Your ${info.title} is fully grown!`;
  if (id === 'fountain' && tier === 0) return '⛲ A dry old fountain… do a quiz to fix it!';
  return `✨ Do a quiz to grow the ${info.title} (${tier}/${MAX_LEVEL})`;
}
export const STATIONS_INTRO = 'My little Keeper — the nest is YOURS to decorate now! I planted two blank signs: one by the meadow path, one by the grove path. Do a quiz at a sign and you can paint ANY words you want on it — and change them whenever you like. And look closely: the old dry fountain, the nest itself, and the trees around our home will all GROW when you do a quiz right at them. Five projects, five ways to make our home beautiful. Show me what you build! — Mama D.';
