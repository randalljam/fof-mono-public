#!/usr/bin/env node
// Parse applet copy markdown and generate src/lib/<applet>-copy.js for runtime + TTS.
//
// Usage:  node scripts/sync-applet-copy.js [--applet counting-creatures|logic-gates|all]
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const APPLETS = ['counting-creatures', 'logic-gates'];
const webRoot = path.resolve(fileURLToPath(new URL('.', import.meta.url)), '..');

const args = process.argv.slice(2);
const appletIdx = args.indexOf('--applet');
const target = appletIdx !== -1 ? args[appletIdx + 1] : 'all';
if (target !== 'all' && !APPLETS.includes(target)) {
  console.error(`Unknown applet "${target}". Known: ${APPLETS.join(', ')}, all`);
  process.exit(1);
}
const targets = target === 'all' ? APPLETS : [target];

function parseCopyMarkdown(text) {
  const screens = [];
  const shared = {};
  const templates = {};
  const parts = text.split(/^## /m).slice(1);
  for (const part of parts) {
    const nl = part.indexOf('\n');
    const heading = part.slice(0, nl).trim();
    const body = part.slice(nl + 1).trim();
    const fields = parseFields(body);
    if (/^Screen (\d+)$/i.test(heading)) {
      const n = Number(RegExp.$1);
      const screen = { reveals: {}, displays: {}, captions: {} };
      for (const [key, value] of Object.entries(fields)) {
        if (key === 'title') screen.title = value;
        else if (key === 'caption') screen.caption = value;
        else if (key === 'speak') screen.speak = value;
        else if (key === 'table-done') screen.tableDone = value;
        else if (key === 'title-quiz') screen.titleQuiz = value;
        else if (key === 'title-quiz-done') screen.titleQuizDone = value;
        else if (key === 'title-quiz-done-not') screen.titleQuizDoneNot = value;
        else if (key === 'banner') screen.banner = value;
        else if (key === 'button') screen.button = value;
        else if (key === 'footer') screen.footer = value;
        else if (key.startsWith('reveal-')) screen.reveals[key.slice(7)] = value;
        else if (key.startsWith('display-')) screen.displays[key.slice(8)] = value;
        else if (key.startsWith('caption-')) screen.captions[key.slice(8)] = value;
        else screen[key] = value;
      }
      screens[n - 1] = screen;
    } else if (/^Shared$/i.test(heading)) {
      Object.assign(shared, fields);
    } else if (/^Templates$/i.test(heading)) {
      Object.assign(templates, fields);
    }
  }
  for (let i = 0; i < screens.length; i++) {
    if (!screens[i]) throw new Error(`Missing ## Screen ${i + 1}`);
  }
  return { screens, shared, templates };
}

function parseFields(body) {
  const fields = {};
  const lines = body.split('\n');
  let key = null;
  let value = [];
  const flush = () => {
    if (!key) return;
    fields[key] = value.join('\n').trim();
    key = null;
    value = [];
  };
  for (const line of lines) {
    const m = line.match(/^([a-z][a-z0-9-]*):\s*(.*)$/i);
    if (m) {
      flush();
      key = m[1];
      value = [m[2]];
    } else if (key && (line.startsWith('  ') || line.startsWith('\t'))) {
      value.push(line.trimStart());
    } else if (key && line.trim() === '') {
      value.push('');
    } else if (key) {
      value.push(line);
    }
  }
  flush();
  return fields;
}

function jsString(s) {
  return JSON.stringify(s);
}

function camelCase(id) {
  return id.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
}

function buildRevealLines(screens) {
  const out = {};
  for (const screen of screens) {
    for (const [id, text] of Object.entries(screen.reveals)) {
      out[camelCase(id)] = text;
    }
  }
  return out;
}

function buildTableDoneLines(screens) {
  const out = {};
  const gateScreens = { 2: 'NOT', 5: 'OR', 7: 'AND', 9: 'XOR', 11: 'NAND' };
  for (const [idx, gate] of Object.entries(gateScreens)) {
    const td = screens[Number(idx)]?.tableDone;
    if (td) out[gate] = td;
  }
  return out;
}

function generateLogicGates({ screens, shared, templates }) {
  const revealLines = buildRevealLines(screens);
  const tableDoneLines = buildTableDoneLines(screens);
  const quizLines = {
    correct: shared['quiz-correct'],
    tryAgain: shared['quiz-tryAgain'],
    quizDone: shared['quiz-done'],
    gotIt: shared['quiz-gotIt'],
  };
  const spokenGateNames = { NOT: 'NOT', OR: 'OR', AND: 'AND', XOR: 'ex-or', NAND: 'NAND' };
  const screenBlocks = screens.map((s) => {
    const parts = ['title: ' + jsString(s.title || ''), 'speak: ' + jsString(s.speak || '')];
    if (s.caption) parts.push('caption: ' + jsString(s.caption));
    if (s.titleQuiz) parts.push('titleQuiz: ' + jsString(s.titleQuiz));
    if (s.titleQuizDone) parts.push('titleQuizDone: ' + jsString(s.titleQuizDone));
    if (s.titleQuizDoneNot) parts.push('titleQuizDoneNot: ' + jsString(s.titleQuizDoneNot));
    if (s.banner) parts.push('banner: ' + jsString(s.banner));
    if (s.footer) parts.push('footer: ' + jsString(s.footer));
    if (Object.keys(s.reveals).length) parts.push('reveals: ' + JSON.stringify(s.reveals));
    if (Object.keys(s.displays).length) parts.push('displays: ' + JSON.stringify(s.displays));
    if (Object.keys(s.captions).length) parts.push('captions: ' + JSON.stringify(s.captions));
    return '  {\n    ' + parts.join(',\n    ') + ',\n  }';
  });
  return `// GENERATED by scripts/sync-applet-copy.js — do not edit by hand.
// Source: copy/logic-gates.md — edit that file, then run: npm run sync:copy

export const SCREENS = [
${screenBlocks.join(',\n')}
];

export const STEP_INTROS = SCREENS.map((s) => s.speak);

export const REVEAL_LINES = ${JSON.stringify(revealLines, null, 2)};

export const TABLE_DONE_LINES = ${JSON.stringify(tableDoneLines, null, 2)};

export const QUIZ_LINES = ${JSON.stringify(quizLines, null, 2)};

export const SPOKEN_GATE_NAMES = ${JSON.stringify(spokenGateNames, null, 2)};

export function fmt(template, vars = {}) {
  let out = template || '';
  for (const [key, value] of Object.entries(vars)) out = out.split('{' + key + '}').join(String(value));
  return out;
}

export function screenTitle(step, vars = {}) {
  return fmt(SCREENS[step]?.title || '', vars);
}

export function screenCaption(step, gate) {
  const s = SCREENS[step];
  if (!s) return '';
  if (gate && s.captions?.[gate]) return s.captions[gate];
  return s.caption || '';
}

export const mysteryCorrectTemplate = ${jsString(templates.mysteryCorrect || '')};
export function mysteryCorrect(gate) {
  return fmt(mysteryCorrectTemplate, { gateName: SPOKEN_GATE_NAMES[gate] || gate });
}
`;
}

function generateCountingCreatures({ screens, shared, templates }) {
  const revealLines = buildRevealLines(screens);
  const practiceLines = {
    makePebbles: shared['practice-makePebbles'],
    makeNumber: shared['practice-makeNumber'],
    correct: shared['practice-correct'],
    tryAgain: shared['practice-tryAgain'],
  };
  const screenBlocks = screens.map((s) => {
    const parts = ['speak: ' + jsString(s.speak || '')];
    if (s.title) parts.push('title: ' + jsString(s.title));
    if (s.caption) parts.push('caption: ' + jsString(s.caption));
    if (s.banner) parts.push('banner: ' + jsString(s.banner));
    if (s.button) parts.push('button: ' + jsString(s.button));
    if (Object.keys(s.reveals).length) parts.push('reveals: ' + JSON.stringify(s.reveals));
    if (Object.keys(s.displays).length) parts.push('displays: ' + JSON.stringify(s.displays));
    return '  {\n    ' + parts.join(',\n    ') + ',\n  }';
  });
  return `// GENERATED by scripts/sync-applet-copy.js — do not edit by hand.
// Source: copy/counting-creatures.md — edit that file, then run: npm run sync:copy

export const SCREENS = [
${screenBlocks.join(',\n')}
];

export const STEP_INTROS = SCREENS.map((s) => s.speak);

export const REVEAL_LINES = ${JSON.stringify(revealLines, null, 2)};

export const PRACTICE_LINES = ${JSON.stringify(practiceLines, null, 2)};

export function fmt(template, vars = {}) {
  let out = template || '';
  for (const [key, value] of Object.entries(vars)) out = out.split('{' + key + '}').join(String(value));
  return out;
}

export const slothAnswerTemplate = ${jsString(templates.slothAnswer || '')};
export const computerAnswerTemplate = ${jsString(templates.computerAnswer || '')};

export function slothAnswer(target, englishWords) {
  return fmt(slothAnswerTemplate, { target: englishWords(target) });
}

export function computerAnswer(target, englishWords) {
  return fmt(computerAnswerTemplate, { target: englishWords(target) });
}
`;
}

const GENERATORS = {
  'logic-gates': generateLogicGates,
  'counting-creatures': generateCountingCreatures,
};

for (const applet of targets) {
  const mdPath = path.join(webRoot, 'copy', `${applet}.md`);
  const outPath = path.join(webRoot, 'src', 'lib', `${applet}-copy.js`);
  const text = fs.readFileSync(mdPath, 'utf8');
  const parsed = parseCopyMarkdown(text);
  const code = GENERATORS[applet](parsed);
  fs.writeFileSync(outPath, code);
  console.log(`Wrote ${path.relative(webRoot, outPath)} (${parsed.screens.length} screens)`);
}
