import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  englishWords,
  digitWords,
  utteranceId,
  allUtterances,
  STEP_INTROS,
  REVEAL_LINES,
  PRACTICE_LINES,
  slothAnswer,
  computerAnswer,
  practiceTargetKind,
  nextPracticeTarget,
  MAX_COUNT,
  SLOTH_MAX,
  COMPUTER_MAX,
} from '../src/lib/counting-creatures.js';
import { AUDIO_CLIP_IDS } from '../src/lib/counting-creatures-audio-manifest.js';

// Audio clips are gitignored; run `npm run audio:pull` (or generate-tts) before npm test.
const webRoot = path.resolve(fileURLToPath(new URL('.', import.meta.url)), '..');
const audioDir = path.join(webRoot, 'public', 'audio', 'counting-creatures');

test('englishWords maps counting range to words', () => {
  assert.equal(englishWords(0), 'zero');
  assert.equal(englishWords(6), 'six');
  assert.equal(englishWords(13), 'thirteen');
  assert.equal(englishWords(20), 'twenty');
  assert.equal(englishWords(21), '21'); // out of table -> digits as string
});

test('digitWords reads digits in the requested base', () => {
  assert.equal(digitWords(6, 6), 'one zero');
  assert.equal(digitWords(13, 6), 'two one');
  assert.equal(digitWords(5, 2), 'one zero one');
  assert.equal(digitWords(7, 2), 'one one one');
  assert.equal(digitWords(0, 2), 'zero');
});

test('sloth practice targets follow the single and double digit cadence without adjacent repeats', () => {
  const targets = [];
  let previousTarget = null;
  for (let roundIndex = 0; roundIndex < 7; roundIndex++) {
    const target = nextPracticeTarget({ base: 6, maxVal: SLOTH_MAX, roundIndex, previousTarget, random: () => 0 });
    targets.push(target);
    previousTarget = target;
  }
  assert.deepEqual(targets.map((target) => practiceTargetKind(target, 6)), [
    'single',
    'single',
    'double',
    'double',
    'single',
    'double',
    'double',
  ]);
  for (let i = 1; i < targets.length; i++) assert.notEqual(targets[i], targets[i - 1]);
});

test('computer practice targets mix digit lengths and avoid adjacent repeats', () => {
  const targets = [];
  let previousTarget = null;
  for (let roundIndex = 0; roundIndex < 8; roundIndex++) {
    const target = nextPracticeTarget({ base: 2, maxVal: COMPUTER_MAX, roundIndex, previousTarget, random: () => 0 });
    targets.push(target);
    previousTarget = target;
  }
  assert.deepEqual(targets.map((target) => practiceTargetKind(target, 2)), [
    'single',
    'double',
    'triple',
    'double',
    'triple',
    'single',
    'triple',
    'double',
  ]);
  for (let i = 1; i < targets.length; i++) assert.notEqual(targets[i], targets[i - 1]);
  assert.notEqual(nextPracticeTarget({ base: 2, maxVal: COMPUTER_MAX, roundIndex: 0, previousTarget: 1, random: () => 0 }), 1);
});

test('utteranceId is stable, readable, and unique across all utterances', () => {
  assert.equal(utteranceId('Yes! Correct!'), utteranceId('Yes! Correct!'));
  assert.match(utteranceId('Yes! Correct!'), /^yes-correct-[0-9a-f]+$/);
  const ids = allUtterances().map(utteranceId);
  assert.equal(new Set(ids).size, ids.length, 'utterance ids must not collide');
});

test('allUtterances covers every line the applet can speak', () => {
  const texts = new Set(allUtterances());
  for (const intro of STEP_INTROS) assert.ok(texts.has(intro), `missing intro: ${intro}`);
  assert.equal(STEP_INTROS.length, 13);
  for (let n = 0; n <= MAX_COUNT; n++) {
    assert.ok(texts.has(englishWords(n)), `missing count word ${n}`);
    assert.ok(texts.has(digitWords(n, 6)), `missing base-6 reading of ${n}`);
  }
  for (let n = 0; n <= COMPUTER_MAX; n++) assert.ok(texts.has(digitWords(n, 2)), `missing base-2 reading of ${n}`);
  for (const line of Object.values(REVEAL_LINES)) assert.ok(texts.has(line), `missing reveal line: ${line}`);
  for (const line of Object.values(PRACTICE_LINES)) assert.ok(texts.has(line), `missing practice line: ${line}`);
  for (let t = 6; t <= SLOTH_MAX; t++) assert.ok(texts.has(slothAnswer(t)));
  for (let t = 2; t <= COMPUTER_MAX; t++) assert.ok(texts.has(computerAnswer(t)));
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
  const page = fs.readFileSync(path.join(webRoot, 'src', 'pages', 'applets', 'counting-creatures.astro'), 'utf8');
  assert.match(page, /noindex/);
  assert.match(page, /client:load/);
});
