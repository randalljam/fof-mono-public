// Rewards layer: Dragon Gems, nest upgrades, the daily gift, and the Road Home
// map model. DOM/THREE-free so tests and the sim can run it in Node.
//
// Design: gems are a LIFETIME total (never spent) — the nest grows richer as
// they accumulate, so every quiz visibly builds the home. Thresholds are tuned
// so a typical burst (~10 gems) unlocks something new every 3-5 bursts.
import { MILESTONES } from './milestones.js';

export function gemsForBurst({ correct = 0, total = 0, kind = 'list-complete' } = {}) {
  if (!total) return 0;
  const base = 3;
  const forCorrect = Math.floor(correct / 3);
  const completion = kind === 'list-complete' ? 2 : 0;
  return base + forCorrect + completion;
}
export const DAILY_GIFT_GEMS = 5;
export const SUMMIT_BONUS_GEMS = 30;
export const LAVA_WIN_GEMS = 25;

export const NEST_UPGRADES = [
  { id: 'garden', cost: 20, title: 'Flower Garden', reveal: '🌸 Your gems grew a flower garden around the nest!' },
  { id: 'lights', cost: 50, title: 'String Lights', reveal: '✨ Twinkling lanterns light up your nest!' },
  { id: 'banners', cost: 90, title: 'Banner Flags', reveal: '🚩 Colorful banners fly over your home!' },
  { id: 'fountain', cost: 140, title: 'Bubbling Fountain', reveal: '⛲ A bubbling fountain appears — dragons love splashing!' },
  { id: 'statue', cost: 200, title: 'Golden Dragon Statue', reveal: '🏆 A GOLDEN dragon statue rises at your nest. Legendary!' },
];
export function unlockedUpgrades(gems) {
  return NEST_UPGRADES.filter((u) => (gems || 0) >= u.cost).map((u) => u.id);
}
export function nextUpgrade(gems) {
  return NEST_UPGRADES.find((u) => (gems || 0) < u.cost) || null;
}

// Daily gift: available on the first login of each LOCAL calendar day.
export function sameLocalDay(aISO, bISO) {
  if (!aISO || !bISO) return false;
  const a = new Date(aISO);
  const b = new Date(bISO);
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}
export function dailyGiftAvailable(lastGiftISO, nowISO) {
  if (!lastGiftISO) return true;
  return !sameLocalDay(lastGiftISO, nowISO);
}
export const GIFT_NOTES = [
  'Mama Dragon left you {gems} gems and a note: "Every day you practice, my baby grows stronger!"',
  'The Dragon Keeper sends {gems} gems: "A little math every day makes a mighty dragon."',
  '{gems} gems, tied with a ribbon: "Saw you from the clouds yesterday. So proud. — Mama D."',
  'A balloon crate with {gems} gems inside! The tag reads: "For the best dragon keeper in the valley."',
];
export function giftNote(count) {
  const note = GIFT_NOTES[Math.max(0, count) % GIFT_NOTES.length];
  return note.replaceAll('{gems}', String(DAILY_GIFT_GEMS));
}

// The Road Home: one map stop per story leg, so the whole journey to 100%
// (and the volcano side-quest) is visible as a path with "you are here".
export function roadStops(state) {
  const pct = state.maxPct || 0;
  const done = new Set(state.celebratedIds || []);
  const stops = [
    { id: 'egg', icon: '🥚', title: 'Find the Egg', done: !!state.eggFound },
    { id: 'hatch', icon: '🐣', title: 'The Hatch', done: done.has('hatch') || (state.hatched && pct >= 60) },
    { id: 'meadow', icon: '🦋', title: 'Butterfly Meadow', done: done.has('wings') },
    { id: 'hills', icon: '⛰️', title: 'Whispering Hills', done: done.has('jump') },
    { id: 'grove', icon: '🍄', title: 'Firefly Grove', done: done.has('fire') },
    { id: 'beacon', icon: '🔥', title: 'Light the Beacon', done: done.has('flight-ride') || !!state.rideUnlocked },
    { id: 'ember', icon: '🌋', title: 'Mount Ember Summit', done: !!(state.volcano && state.volcano.summited) },
    { id: 'lava', icon: '🔥', title: 'Lava Defense', done: !!(state.lava && state.lava.won) },
  ];
  let current = null;
  for (const s of stops) {
    if (!s.done && !current) { s.current = true; current = s.id; }
  }
  return stops;
}
// Percent-within-segment for the map's "almost there!" line, reusing the
// milestone ladder (never exposes raw fluency to the kid).
export function roadProgressLine(state) {
  const pct = state.maxPct || 0;
  let prev = 0;
  for (const m of MILESTONES) {
    if (m.id === 'egg-found') continue;
    if (pct < m.pct) {
      const frac = Math.max(0, Math.min(1, (pct - prev) / (m.pct - prev)));
      return `You are ${Math.round(frac * 100)}% of the way to the next stop!`;
    }
    prev = m.pct;
  }
  return state.volcano && state.volcano.summited
    ? 'You walked the whole road home. Every stop is yours!'
    : 'The road is open all the way — keep exploring!';
}
