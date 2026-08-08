// Pure logic for the Logic Gates applet: gate definitions, truth tables,
// half/full/ripple adder math, quiz sequences, and spoken-line inventory.
// Screen copy lives in copy/logic-gates.md → src/lib/logic-gates-copy.js (npm run sync:copy).

import { englishWords, digitWords } from "./counting-creatures.js";
import {
  SCREENS,
  STEP_INTROS,
  REVEAL_LINES,
  TABLE_DONE_LINES,
  QUIZ_LINES,
  fmt,
  mysteryCorrect,
} from "./logic-gates-copy.js";
export { utteranceId } from "./utterance-id.js";
export {
  SCREENS,
  STEP_INTROS,
  REVEAL_LINES,
  TABLE_DONE_LINES,
  QUIZ_LINES,
  SPOKEN_GATE_NAMES,
  fmt,
  screenTitle,
  screenCaption,
  mysteryCorrect,
} from "./logic-gates-copy.js";

export const GATES = {
  NOT: { inputs: 1, fn: (v) => (v[0] ? 0 : 1) },
  OR: { inputs: 2, fn: (v) => (v[0] || v[1] ? 1 : 0) },
  AND: { inputs: 2, fn: (v) => (v[0] && v[1] ? 1 : 0) },
  XOR: { inputs: 2, fn: (v) => (v[0] !== v[1] ? 1 : 0) },
  NAND: { inputs: 2, fn: (v) => (v[0] && v[1] ? 0 : 1) },
};
export const GATE_ORDER = ["NOT", "OR", "AND", "XOR", "NAND"];
export const gateOutput = (name, inputs) => GATES[name].fn(inputs);
export const gateCombos = (name) => (GATES[name].inputs === 1 ? [[0], [1]] : [[0, 0], [0, 1], [1, 0], [1, 1]]);
export const comboKey = (inputs) => inputs.join("");

export const halfAdd = (a, b) => ({ sum: a ^ b, carry: a & b });
export const fullAdd = (a, b, cin) => {
  const total = a + b + cin;
  return { sum: total & 1, cout: total >= 2 ? 1 : 0 };
};
// Add two 2-bit numbers (0..3) through a chained-adder view: per-bit sums and carries.
export function rippleAdd(a, b) {
  const a0 = a & 1, a1 = (a >> 1) & 1, b0 = b & 1, b1 = (b >> 1) & 1;
  const stage0 = fullAdd(a0, b0, 0);
  const stage1 = fullAdd(a1, b1, stage0.cout);
  return { sum: a + b, bits: [stage1.cout, stage1.sum, stage0.sum], carry0: stage0.cout, carry1: stage1.cout };
}

// Deterministic quiz sequences (every combo covered, orders varied per gate).
export const GATE_QUIZ_ROUNDS = {
  NOT: [[1], [0]],
  OR: [[1, 0], [0, 0], [1, 1], [0, 1]],
  AND: [[1, 1], [1, 0], [0, 1], [0, 0]],
  XOR: [[0, 1], [1, 1], [1, 0], [0, 0]],
};
export const MYSTERY_ROUNDS = ["AND", "XOR", "OR", "NAND"];
export const HALF_ADDER_QUIZ_ROUNDS = [[1, 0], [1, 1], [0, 1], [0, 0]];
export const FULL_ADDER_QUIZ_ROUNDS = [[1, 0, 0], [0, 1, 1], [1, 1, 1], [1, 0, 1], [0, 0, 0]];
export const SUM_TARGETS = [3, 1, 5, 2, 6, 4];
export const RIPPLE_MAX_INPUT = 3;

// Which screen index hosts which gate-explore / gate-quiz (single source for
// the applet and for step titles).
export const GATE_STEPS = { 2: "NOT", 5: "OR", 7: "AND", 9: "XOR", 11: "NAND" };
export const QUIZ_STEPS = { 3: "NOT", 6: "OR", 8: "AND", 10: "XOR" };
// Short step names for telemetry (applet-start + step-enter events) and dev tooling.
export const STEP_TITLES = SCREENS.map((s, i) => {
  const gate = GATE_STEPS[i] || QUIZ_STEPS[i] || "";
  if (s.title) return fmt(s.title, { gate });
  if (s.titleQuiz) return fmt(s.titleQuiz, { gate });
  return `Screen ${i + 1}`;
});

const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);
// Read binary padded to the number of digit lights on screen, so speech matches the display.
export const paddedBinaryWords = (n, width) => n.toString(2).padStart(width, "0").split("").map((d) => englishWords(Number(d))).join(" ");
export const halfAddLine = (a, b) => `${cap(englishWords(a))} plus ${englishWords(b)} is ${paddedBinaryWords(a + b, 2)} in binary, which is ${englishWords(a + b)} in our normal base ten.`;
export const fullAddLine = (a, b, cin) => {
  const total = a + b + cin;
  return `${cap(englishWords(a))} plus ${englishWords(b)} plus ${englishWords(cin)} is ${paddedBinaryWords(total, 2)} in binary, which is ${englishWords(total)} in base ten.`;
};
export const sumTargetLine = (t) => `Make ${englishWords(t)}.`;
export const sumSuccessLine = (a, b) => `Yes! ${cap(englishWords(a))} plus ${englishWords(b)} is ${englishWords(a + b)}. In binary, ${paddedBinaryWords(a + b, 3)}!`;

// Every line the applet can speak. Keep in sync with LogicGates.jsx;
// tests assert the pre-generated audio manifest covers all of these.
export function allUtterances() {
  const texts = new Set();
  STEP_INTROS.forEach((t) => texts.add(t));
  Object.values(REVEAL_LINES).forEach((t) => texts.add(t));
  Object.values(TABLE_DONE_LINES).forEach((t) => texts.add(t));
  Object.values(QUIZ_LINES).forEach((t) => texts.add(t));
  MYSTERY_ROUNDS.forEach((g) => texts.add(mysteryCorrect(g)));
  for (const [a, b] of [[0, 0], [0, 1], [1, 0], [1, 1]]) texts.add(halfAddLine(a, b));
  for (const a of [0, 1]) for (const b of [0, 1]) for (const c of [0, 1]) texts.add(fullAddLine(a, b, c));
  for (let t = 0; t <= RIPPLE_MAX_INPUT * 2; t++) texts.add(sumTargetLine(t));
  for (let a = 0; a <= RIPPLE_MAX_INPUT; a++) for (let b = 0; b <= RIPPLE_MAX_INPUT; b++) texts.add(sumSuccessLine(a, b));
  return [...texts];
}
