// Pure logic for the Counting Creatures applet: number words, digit words,
// and spoken-line inventory. Screen copy lives in copy/counting-creatures.md
// → src/lib/counting-creatures-copy.js (npm run sync:copy).

import {
  STEP_INTROS,
  REVEAL_LINES,
  PRACTICE_LINES,
  slothAnswer as _slothAnswer,
  computerAnswer as _computerAnswer,
} from "./counting-creatures-copy.js";

export {
  SCREENS,
  STEP_INTROS,
  REVEAL_LINES,
  PRACTICE_LINES,
} from "./counting-creatures-copy.js";

export const WORDS = ["zero","one","two","three","four","five","six","seven","eight","nine","ten","eleven","twelve","thirteen","fourteen","fifteen","sixteen","seventeen","eighteen","nineteen","twenty"];
export const englishWords = (n) => WORDS[n] || String(n);
export const digitWords = (n, base) => n.toString(base).split("").map((d) => WORDS[Number(d)]).join(" ");

// Counting ceiling used by the reveal charts and final chart.
export const MAX_COUNT = 13;
// Converter practice ceilings (base 6 and base 2 rounds).
export const SLOTH_MAX = 8;
export const COMPUTER_MAX = 7;

export const PRACTICE_TARGET_PATTERNS = {
  6: ["single", "single", "double", "double", "single", "double", "double"],
  2: ["single", "double", "triple", "double", "triple", "single", "triple", "double"],
};

export const slothAnswer = (target) => _slothAnswer(target, englishWords);
export const computerAnswer = (target) => _computerAnswer(target, englishWords);

export function practiceTargetKind(value, base) {
  const digits = value.toString(base).length;
  if (digits === 1) return "single";
  if (digits === 2) return "double";
  return "triple";
}

export function practiceTargetOptions(base, maxVal, kind) {
  const options = [];
  for (let value = 1; value <= maxVal; value++) {
    if (!kind || practiceTargetKind(value, base) === kind) options.push(value);
  }
  return options;
}

function choosePracticeTarget(options, previousTarget, random) {
  const choices = options.filter((value) => value !== previousTarget);
  const pool = choices.length > 0 ? choices : options;
  if (pool.length === 0) return previousTarget || 1;
  return pool[Math.floor(random() * pool.length)];
}

export function nextPracticeTarget({ base, maxVal, roundIndex = 0, previousTarget = null, random = Math.random }) {
  const pattern = PRACTICE_TARGET_PATTERNS[base];
  const kind = pattern ? pattern[roundIndex % pattern.length] : null;
  const preferred = practiceTargetOptions(base, maxVal, kind);
  if (preferred.length > 0 && !(preferred.length === 1 && preferred[0] === previousTarget)) {
    return choosePracticeTarget(preferred, previousTarget, random);
  }
  return choosePracticeTarget(practiceTargetOptions(base, maxVal), previousTarget, random);
}

// Stable spoken-line id lives in utterance-id.js (shared across applets);
// re-exported here so existing imports keep working.
export { utteranceId } from "./utterance-id.js";

// Every line the applet can speak. Keep in sync with CountingCreatures.jsx;
// tests assert the pre-generated audio manifest covers all of these.
export function allUtterances() {
  const texts = new Set();
  STEP_INTROS.forEach((t) => texts.add(t));
  for (let n = 0; n <= MAX_COUNT; n++) texts.add(englishWords(n));
  for (let n = 0; n <= MAX_COUNT; n++) texts.add(digitWords(n, 6));
  for (let n = 0; n <= COMPUTER_MAX; n++) texts.add(digitWords(n, 2));
  Object.values(REVEAL_LINES).forEach((t) => texts.add(t));
  Object.values(PRACTICE_LINES).forEach((t) => texts.add(t));
  for (let t = 6; t <= SLOTH_MAX; t++) texts.add(slothAnswer(t));
  for (let t = 2; t <= COMPUTER_MAX; t++) texts.add(computerAnswer(t));
  return [...texts];
}
