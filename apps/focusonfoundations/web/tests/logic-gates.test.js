import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  GATES,
  FULL_ADDER_QUIZ_ROUNDS,
  STEP_TITLES,
  GATE_ORDER,
  gateOutput,
  gateCombos,
  comboKey,
  halfAdd,
  fullAdd,
  rippleAdd,
  GATE_QUIZ_ROUNDS,
  MYSTERY_ROUNDS,
  HALF_ADDER_QUIZ_ROUNDS,
  SUM_TARGETS,
  RIPPLE_MAX_INPUT,
  STEP_INTROS,
  REVEAL_LINES,
  TABLE_DONE_LINES,
  QUIZ_LINES,
  mysteryCorrect,
  halfAddLine,
  fullAddLine,
  sumTargetLine,
  sumSuccessLine,
  allUtterances,
  utteranceId,
} from '../src/lib/logic-gates.js';
import { AUDIO_CLIP_IDS } from '../src/lib/logic-gates-audio-manifest.js';

// Audio clips are gitignored; run `npm run audio:pull` (or generate-tts) before npm test.
const webRoot = path.resolve(fileURLToPath(new URL('.', import.meta.url)), '..');
const audioDir = path.join(webRoot, 'public', 'audio', 'logic-gates');

test('gate truth tables are correct', () => {
  assert.deepEqual(gateCombos('NOT').map((c) => gateOutput('NOT', c)), [1, 0]);
  assert.deepEqual(gateCombos('OR').map((c) => gateOutput('OR', c)), [0, 1, 1, 1]);
  assert.deepEqual(gateCombos('AND').map((c) => gateOutput('AND', c)), [0, 0, 0, 1]);
  assert.deepEqual(gateCombos('XOR').map((c) => gateOutput('XOR', c)), [0, 1, 1, 0]);
  assert.deepEqual(gateCombos('NAND').map((c) => gateOutput('NAND', c)), [1, 1, 1, 0]);
});

test('gate outputs are always 0 or 1 and NAND inverts AND', () => {
  for (const gate of GATE_ORDER) {
    for (const combo of gateCombos(gate)) {
      const out = gateOutput(gate, combo);
      assert.ok(out === 0 || out === 1, `${gate}(${combo}) = ${out}`);
    }
  }
  for (const combo of gateCombos('AND')) {
    assert.equal(gateOutput('NAND', combo), 1 - gateOutput('AND', combo));
  }
});

test('half adder matches binary addition of two bits', () => {
  for (const a of [0, 1]) for (const b of [0, 1]) {
    const { sum, carry } = halfAdd(a, b);
    assert.equal(carry * 2 + sum, a + b, `halfAdd(${a},${b})`);
  }
});

test('full adder matches binary addition of three bits and composes from half adders', () => {
  for (const a of [0, 1]) for (const b of [0, 1]) for (const cin of [0, 1]) {
    const { sum, cout } = fullAdd(a, b, cin);
    assert.equal(cout * 2 + sum, a + b + cin, `fullAdd(${a},${b},${cin})`);
    // structural identity used by the circuit drawing: two half adders + OR
    const ha1 = halfAdd(a, b);
    const ha2 = halfAdd(ha1.sum, cin);
    assert.equal(sum, ha2.sum);
    assert.equal(cout, ha1.carry | ha2.carry);
  }
});

test('rippleAdd adds all 2-bit pairs with correct bits and carries', () => {
  for (let a = 0; a <= RIPPLE_MAX_INPUT; a++) {
    for (let b = 0; b <= RIPPLE_MAX_INPUT; b++) {
      const r = rippleAdd(a, b);
      assert.equal(r.sum, a + b);
      assert.equal(r.bits[0] * 4 + r.bits[1] * 2 + r.bits[2], a + b, `bits for ${a}+${b}`);
    }
  }
});

test('quiz rounds cover every input combination of their gate', () => {
  for (const [gate, rounds] of Object.entries(GATE_QUIZ_ROUNDS)) {
    const seen = new Set(rounds.map(comboKey));
    for (const combo of gateCombos(gate)) {
      assert.ok(seen.has(comboKey(combo)), `${gate} quiz misses ${comboKey(combo)}`);
    }
    assert.equal(rounds.length, gateCombos(gate).length, `${gate} quiz has duplicate rounds`);
  }
  const haSeen = new Set(HALF_ADDER_QUIZ_ROUNDS.map(comboKey));
  assert.equal(haSeen.size, 4, 'half adder quiz covers all four combos');
});

test('full adder quiz rounds cover every possible total and are valid bits', () => {
  const totals = new Set(FULL_ADDER_QUIZ_ROUNDS.map(([a, b, c]) => a + b + c));
  for (let t = 0; t <= 3; t++) assert.ok(totals.has(t), `no round adds up to ${t}`);
  for (const round of FULL_ADDER_QUIZ_ROUNDS) {
    assert.equal(round.length, 3);
    for (const bit of round) assert.ok(bit === 0 || bit === 1);
  }
});

test('step titles cover every screen', () => {
  const { STEP_INTROS: intros } = { STEP_INTROS };
  assert.equal(STEP_TITLES.length, intros.length);
  for (const title of STEP_TITLES) assert.ok(title && !/^Screen \d+$/.test(title), `untitled step: ${title}`);
});

test('mystery rounds are distinct two-input gates', () => {
  assert.equal(new Set(MYSTERY_ROUNDS).size, MYSTERY_ROUNDS.length);
  for (const gate of MYSTERY_ROUNDS) assert.equal(GATES[gate].inputs, 2, `${gate} must be two-input`);
});

test('sum targets are reachable with two 2-bit numbers', () => {
  for (const t of SUM_TARGETS) {
    assert.ok(t >= 0 && t <= RIPPLE_MAX_INPUT * 2, `target ${t} out of range`);
    assert.ok(SUM_TARGETS.filter((x) => x === t).length === 1, `duplicate target ${t}`);
  }
});

test('spoken sentence builders read naturally', () => {
  assert.equal(halfAddLine(1, 1), 'One plus one is one zero in binary, which is two in our normal base ten.');
  assert.equal(fullAddLine(1, 1, 1), 'One plus one plus one is one one in binary, which is three in base ten.');
  assert.equal(fullAddLine(1, 0, 0), 'One plus zero plus zero is zero one in binary, which is one in base ten.');
  assert.equal(sumTargetLine(5), 'Make five.');
  assert.equal(sumSuccessLine(2, 3), 'Yes! Two plus three is five. In binary, one zero one!');
  assert.equal(sumSuccessLine(2, 1), 'Yes! Two plus one is three. In binary, zero one one!');
  assert.match(mysteryCorrect('XOR'), /ex-or/);
});

test('utterance ids are stable and unique across all utterances', () => {
  const ids = allUtterances().map(utteranceId);
  assert.equal(new Set(ids).size, ids.length, 'utterance ids must not collide');
});

test('allUtterances covers every line the applet can speak', () => {
  const texts = new Set(allUtterances());
  assert.equal(STEP_INTROS.length, 21);
  for (const intro of STEP_INTROS) assert.ok(texts.has(intro), `missing intro: ${intro}`);
  for (const line of Object.values(REVEAL_LINES)) assert.ok(texts.has(line), `missing reveal line: ${line}`);
  for (const gate of GATE_ORDER) assert.ok(texts.has(TABLE_DONE_LINES[gate]), `missing table-done line for ${gate}`);
  for (const line of Object.values(QUIZ_LINES)) assert.ok(texts.has(line), `missing quiz line: ${line}`);
  for (const gate of MYSTERY_ROUNDS) assert.ok(texts.has(mysteryCorrect(gate)), `missing mystery line for ${gate}`);
  for (const a of [0, 1]) for (const b of [0, 1]) {
    assert.ok(texts.has(halfAddLine(a, b)), `missing half-add line ${a}+${b}`);
    for (const c of [0, 1]) assert.ok(texts.has(fullAddLine(a, b, c)), `missing full-add line ${a}+${b}+${c}`);
  }
  for (let t = 0; t <= RIPPLE_MAX_INPUT * 2; t++) assert.ok(texts.has(sumTargetLine(t)), `missing target line ${t}`);
  for (let a = 0; a <= RIPPLE_MAX_INPUT; a++) for (let b = 0; b <= RIPPLE_MAX_INPUT; b++) {
    assert.ok(texts.has(sumSuccessLine(a, b)), `missing success line ${a}+${b}`);
  }
});

test('audio manifest covers every utterance', () => {
  const clipIds = new Set(AUDIO_CLIP_IDS);
  for (const text of allUtterances()) {
    assert.ok(clipIds.has(utteranceId(text)), `no audio clip for: "${text}"`);
  }
});

test('every manifest clip exists on disk and is a real mp3', () => {
  for (const id of AUDIO_CLIP_IDS) {
    const p = path.join(audioDir, `${id}.mp3`);
    assert.ok(fs.existsSync(p), `missing file: ${p}`);
    const stat = fs.statSync(p);
    assert.ok(stat.size > 1000, `suspiciously small clip: ${p} (${stat.size} bytes)`);
    assert.ok(stat.size < 512 * 1024, `clip exceeds pre-commit size cap: ${p}`);
  }
});

test('applet page is built as an unlisted (noindex) route', () => {
  const page = fs.readFileSync(path.join(webRoot, 'src', 'pages', 'applets', 'logic-gates.astro'), 'utf8');
  assert.match(page, /noindex/);
  assert.match(page, /client:load/);
});
