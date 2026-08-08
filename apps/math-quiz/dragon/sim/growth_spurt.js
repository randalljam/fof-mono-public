// Growth Spurt: DOM-free logic + dialogue for the post-fire size-up phase.
//
// After the 90% fire milestone, each fluency point from 91–100 makes Pipa
// 50% bigger than her adult baseline. A finished quiz in each band shows one
// funny growth letter (GM-editable, 91–100). Scale stops growing at 100% but
// letters continue until the flight-ride surprise is celebrated.

export const GROWTH_SPURT_START_PCT = 90;
export const GROWTH_SPURT_START_ID = 'fire';
export const GROWTH_SPURT_END_ID = 'flight-ride';

// Adult baseline at 90%; +0.5 scale per point above 90 (91% → 1.5×, 100% → 6×).
export function adultGrowthScale(maxPct) {
  const p = maxPct || 0;
  if (p < GROWTH_SPURT_START_PCT) return 1;
  return 1 + (p - GROWTH_SPURT_START_PCT) * 0.5;
}
// Camera/follow distance grows 25% as much as the dragon scale (1.5× dragon → 1.125× distance).
export function growthCameraMul(scale) {
  return 1 + ((scale || 1) - 1) * 0.25;
}

export const GROWTH_SPURT_BANDS = {
  91: [
    'Keeper… did I get BIGGER? I stood up and my head almost bonked a cloud. Mama says this is a growth spurt. Your math is literally making me enormous. I love it. Please keep going before I outgrow the nest.',
  ],
  92: [
    'I tried to curl up in my favorite sunny spot and my tail is hanging out BOTH sides now. Growing is inconvenient but VERY impressive. One more quiz — I want to see if I can block out the sun.',
  ],
  93: [
    'Fun fact: I am now large enough to use a hill as a pillow. Less fun fact: I accidentally sat on the fountain. It still works! It just works… sideways.',
  ],
  94: [
    'My wingspan is officially “please move your chair back” size. A butterfly landed on me and said “wow, YOU’RE the big one now.” I have never felt more majestic. And also more in the way.',
  ],
  95: [
    'Mama Dragon measured me with her tail and gasped. I think that’s good? I’m halfway to “legendary dragon” and all the way to “does this cave make my scales look big?”',
  ],
  96: [
    'I sneezed and three pine trees lost their hats. Sorry, trees! On the bright side, Mount Ember looks cute from up here. Like a little angry teapot.',
  ],
  97: [
    'I tried to do a dignified grown-up dragon walk and accidentally took the meadow WITH me. Dignified is hard when your feet are the size of dinner tables.',
  ],
  98: [
    'Keeper, I can see the whole valley from my nose. The Story Stones look like pebbles. I could carry the nest in ONE claw — but I won’t, because it’s home. (I might carry the fountain though.)',
  ],
  99: [
    'SO CLOSE TO MAXIMUM BIGNESS! My shadow has its own weather. Birds are nesting on my shoulder and honestly? Rent-free. One more push — grow me into legend!',
  ],
  100: [
    'ONE HUNDRED PERCENT! I am the biggest, smartest, most math-grown dragon in the whole wide world. I don’t fit in the nest anymore — I fit in the SKY. Thank you for every quiz that made me this magnificent. Now… what’s this “ride” thing Mama keeps whispering about?',
  ],
};

function fillName(text, dragonName) {
  return text.replaceAll('{name}', dragonName || 'your dragon');
}
export function growthSpurtBandFor(pct) {
  const bands = Object.keys(GROWTH_SPURT_BANDS).map(Number).sort((a, b) => a - b);
  const p = Math.floor(pct || 0);
  if (p <= bands[0]) return bands[0];
  if (p >= bands[bands.length - 1]) return bands[bands.length - 1];
  return p;
}
export function growthSpurtBandPool(band, overrides) {
  const o = overrides ? (overrides[band] || overrides[String(band)]) : null;
  return (Array.isArray(o) && o.length) ? o : GROWTH_SPURT_BANDS[band];
}
export function growthSpurtLineFor(pct, shownCount, dragonName, overrides = null) {
  const pool = growthSpurtBandPool(growthSpurtBandFor(pct), overrides);
  return fillName(pool[(shownCount || 0) % pool.length], dragonName);
}
export function ensureGrowthSpurt(state) {
  if (!state.growthSpurt) state.growthSpurt = { shown: 0 };
  if (state.growthSpurt.shown == null) state.growthSpurt.shown = 0;
  return state.growthSpurt;
}
export function growthSpurtEligible(state, pct) {
  const done = new Set(state.celebratedIds || []);
  if (!state.hatched || !done.has(GROWTH_SPURT_START_ID)) return false;
  return Math.floor(pct || 0) >= growthSpurtBandFor(pct);
}
export function growthSpurtPhaseActive(state) {
  const done = new Set(state.celebratedIds || []);
  return !!state.hatched && done.has(GROWTH_SPURT_START_ID);
}
export function zoomiesPhaseActive(state) {
  const done = new Set(state.celebratedIds || []);
  return !!state.hatched && done.has('jump') && !done.has('fire');
}
// A finished burst earns the staged growth line; early quits get nothing.
export function resolveGrowthSpurtQuiz(state, kind, pct, dragonName, overrides = null) {
  const g = ensureGrowthSpurt(state);
  if (kind !== 'list-complete') return { shown: false, text: null };
  if (!growthSpurtEligible(state, pct)) return { shown: false, text: null };
  const text = growthSpurtLineFor(pct, g.shown, dragonName, overrides);
  g.shown += 1;
  return { shown: true, text };
}
