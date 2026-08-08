// Zoomies: DOM/THREE-free logic + dialogue for the juvenile restlessness quest.
//
// Once the 80% growth milestone is celebrated, Pipa hits the "zoomie age":
// every ZOOMIE_INTERVAL_S of calm play she erupts into a tornado sprint that
// only a FINISHED quiz can calm. Each calmed zoomie shows a Pipa line staged
// by fluency percent (3 lines per percent, 81-89, cycling within the band so
// a stalled percent never runs dry). The zoomies end for good at the 90% fire
// milestone with a one-time graduation message.

export const ZOOMIE_INTERVAL_S = 15;
export const ZOOMIE_START_ID = 'jump'; // 80% "almost grown" milestone begins the zoomie age
export const ZOOMIE_END_ID = 'fire'; // 90% milestone = fully grown, zoomies over

// Pipa's calmed-zoomie lines, 3 per percent band.
export const ZOOMIE_BANDS = {
  81: [
    'WHEW! Sorry about that. I don’t know what happens — my tail says GO and my legs say YES and suddenly I’m a tornado. Your math makes my brain feel quiet again.',
    'Did you SEE how fast I was?! Mama says all young dragons get the zoomies. I can’t wait to be big and calm like her. Well… big, anyway.',
    'Zoomie stopped! My legs are still buzzing though. Mama Dragon says when I’m fully grown they’ll go away. Keep practicing so I can grow up!',
  ],
  82: [
    'I almost knocked over the fountain that time! Being a teenager dragon is EMBARRASSING. Your math is the only thing that calms me down.',
    'Fun fact: dragons don’t get dizzy. Not-fun fact: I definitely get dizzy. Thank you for stopping me.',
    'My wings itch, my tail twitches, and my feet want to RUN. Growing pains, Mama calls it. Growing MATH is the cure!',
  ],
  83: [
    'You’re getting faster at math and I’m getting faster at… spinning. One of these is useful. (It’s yours.)',
    'I dreamed I was a big grown-up dragon with fire breath. Then I woke up and zoomed straight into a tree. Help me grow up soon!',
    'Whew — that was a triple-spin tornado! Only the smartest Keepers can stop those. Lucky me, I have one.',
  ],
  84: [
    'I tried to stop that zoomie all by myself. I counted to three. Then my legs said “THREE MEANS GO!” Math works better when YOU do it.',
    'I can feel it — my wings get steadier every single time you practice. You’re literally growing me up!',
    'A butterfly landed on my nose and I zoomed for five whole minutes. FIVE. Please never tell the critters.',
  ],
  85: [
    'Halfway through the zoomie age! When I’m big I’m going to be SO dignified. No more zoomies. Probably. Mostly.',
    'My zoomies are getting smaller — did you notice? That’s YOUR math doing that. Keeper magic!',
    'Mama Dragon says she had zoomies too when she was my age. She knocked over a MOUNTAIN. Suddenly I feel very well-behaved.',
  ],
  86: [
    'I feel something warm in my tummy when I zoom now. Mama says that’s my fire growing. FIRE! Keep going!!',
    'Only a little more until I’m fully grown! I might miss the zoomies a tiny bit. But don’t stop the math. Do NOT stop the math.',
    'That zoomie was slower, right? Right?! I’m getting so grown up. Practically a dignified dragon already. (I fell over twice.)',
  ],
  87: [
    'Hiccup! Did you see that little puff of smoke?! It’s coming, it’s coming — my fire is almost ready!',
    'Almost there, Keeper. I’ve been practicing my serious grown-up dragon face. How’s this? …Why are you laughing?',
    'I zoomed past the Story Stones and they said “slow down, little one.” LITTLE?! Tell your math to hurry — I have a point to prove.',
  ],
  88: [
    'SO CLOSE! My scales feel warm and my wings feel strong and my zoomies are almost out of zoom!',
    'I made a list of grown-up dragon things: 1. Breathe fire. 2. Be majestic. 3. Nap in the sun. I am EXTREMELY ready for number 3.',
    'When I grow up, the very first fire I breathe is going to spell your name. Okay, maybe just one letter. Fire is hard.',
  ],
  89: [
    'ONE MORE TO GO! I can barely hold still — wait, no, that’s just another zoomie warming up. HURRY, KEEPER!',
    'This is it — the LAST little bit of little-dragon me. Next time you finish your math, something BIG happens. I can feel it. GO GO GO!',
    'My tummy is rumbling like Mount Ember. Mama says that means it’s almost time. One more push, Keeper — grow me up!',
  ],
};
// Rotating "a zoomie started" toasts — the oh-no announcement.
export const ZOOMIE_ALERTS = [
  '🌀 Oh no — another ZOOMIE! Click {name} to calm her with math!',
  '🌀 {name} has the zoomies again! Quick — click her and quiz!',
  '🌀 Here she goes — zoom zoom ZOOM! Click {name} to help her settle!',
  '🌀 Uh-oh, tornado tail! Click {name} before she digs a moat!',
  '🌀 ZOOMIES! {name} can’t stop spinning — only math can stop this!',
  '🌀 Wheee— I mean, oh no! Click {name} to calm the zoomies!',
];
// Shown when a zoomie quiz is quit early — the spin keeps going.
export const ZOOMIE_ESCAPES = [
  'The zoomie is still going — finish a whole quiz to calm {name}!',
  '{name} is still spinning! A finished quiz is the only cure.',
  'So dizzy! Finish the quiz all the way to stop the zoomie!',
];
export const ZOOMIES_INTRO = 'My dear Keeper — a warning about {name}: she has reached the ZOOMIE age. Young dragons her age get so restless they spin like little tornadoes — it means she is growing, and she truly cannot help it. When a zoomie strikes, click her and do your math: nothing settles a young dragon like watching her Keeper think hard. The zoomies stop for good the day she is fully grown… and between you and me, that day is close. — Mama D.';
export const ZOOMIE_GRADUATION = 'Keeper… do you feel that? The buzzing is gone. My legs are calm, my wings are steady, and my tummy is FULL OF FIRE! You mathed me all the way to grown-up. The zoomies are over — from now on, when I spin, it’s because I WANT to. Thank you for growing me up. 🔥';

function fillName(text, dragonName) {
  return text.replaceAll('{name}', dragonName || 'your dragon');
}
export function zoomieBandFor(pct) {
  const bands = Object.keys(ZOOMIE_BANDS).map(Number).sort((a, b) => a - b);
  const p = Math.floor(pct || 0);
  if (p <= bands[0]) return bands[0];
  if (p >= bands[bands.length - 1]) return bands[bands.length - 1];
  return p;
}
// GM-edited lines arrive as { "81": [...], ... } (JSON string keys). A band's
// override replaces its default pool entirely; empty/missing bands fall back.
export function zoomieBandPool(band, overrides) {
  const o = overrides ? (overrides[band] || overrides[String(band)]) : null;
  return (Array.isArray(o) && o.length) ? o : ZOOMIE_BANDS[band];
}
export function zoomieLineFor(pct, calmedCount, dragonName, overrides = null) {
  const pool = zoomieBandPool(zoomieBandFor(pct), overrides);
  return fillName(pool[(calmedCount || 0) % pool.length], dragonName);
}
export function zoomieAlertFor(count, dragonName) {
  return fillName(ZOOMIE_ALERTS[(count || 0) % ZOOMIE_ALERTS.length], dragonName);
}
export function zoomieEscapeFor(count, dragonName) {
  return fillName(ZOOMIE_ESCAPES[(count || 0) % ZOOMIE_ESCAPES.length], dragonName);
}
export function zoomiesIntroText(dragonName) {
  return fillName(ZOOMIES_INTRO, dragonName);
}

export function ensureZoomies(state) {
  if (!state.zoomies) state.zoomies = { intro: false, calmed: 0, alerts: 0, graduated: false };
  if (state.zoomies.calmed == null) state.zoomies.calmed = 0;
  if (state.zoomies.alerts == null) state.zoomies.alerts = 0;
  return state.zoomies;
}
export function zoomiesEligible(state) {
  const done = new Set(state.celebratedIds || []);
  return !!state.hatched && done.has(ZOOMIE_START_ID) && !done.has(ZOOMIE_END_ID);
}
// A finished burst calms the zoomie and earns the staged Pipa line; any early
// quit leaves her spinning and returns the escape toast instead.
export function resolveZoomieQuiz(state, kind, pct, dragonName, overrides = null) {
  const z = ensureZoomies(state);
  if (kind !== 'list-complete') {
    return { calmed: false, text: zoomieEscapeFor(z.calmed, dragonName) };
  }
  const text = zoomieLineFor(pct, z.calmed, dragonName, overrides);
  z.calmed += 1;
  return { calmed: true, text };
}
