#!/usr/bin/env node
// Zero-dependency CLI bridge: MathQuest (Java) passes JSON on stdin; this loads
// math_utils.js + fluency_core.js in a vm and returns generate/percent results as JSON.
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import vm from 'node:vm';

const toolsDir = path.dirname(fileURLToPath(import.meta.url));
const appDir = path.dirname(toolsDir);

function loadFluencyCore(scriptDir) {
  const base = scriptDir || appDir;
  const silentConsole = { log() {}, warn() {}, error() {}, info() {}, debug() {} };
  const context = { console: silentConsole, Math, JSON, Array, Object, String, Number, Boolean, parseInt, parseFloat, isNaN, isFinite, Date, Set, Map };
  vm.createContext(context);
  for (const file of ['math_utils.js', 'fluency_core.js']) {
    const candidates = [
      path.join(base, file),
      path.join(appDir, file),
    ];
    let code = null;
    for (const p of candidates) {
      try {
        code = readFileSync(p, 'utf8');
        break;
      } catch (_) {}
    }
    if (code == null) throw new Error(`missing ${file} (searched ${candidates.join(', ')})`);
    vm.runInContext(code, context, { filename: file });
  }
  return context;
}
function readStdin() {
  return new Promise((resolve, reject) => {
    let data = '';
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', (chunk) => { data += chunk; });
    process.stdin.on('end', () => resolve(data));
    process.stdin.on('error', reject);
  });
}
function mixToDistribution(mix) {
  const out = {};
  if (!mix || typeof mix !== 'object') return out;
  for (const [k, v] of Object.entries(mix)) {
    const n = Number(v);
    if (n > 0) out[k] = n;
  }
  return out;
}
function sessionSelectionFromConfig(session) {
  if (!session || !session.mode) return { mode: 'all' };
  const mode = String(session.mode);
  if (mode === 'recentN') return { mode: 'recentN', n: session.n || 3 };
  if (mode === 'sinceDate') return { mode: 'sinceDate', since: session.since || '' };
  return { mode: 'all' };
}
function operationToSymbol(op) {
  const s = String(op || 'addition').toLowerCase();
  if (s.includes('sub') || s === '-') return '-';
  if (s.includes('mul') || s === '*' || s === 'x' || s === '×') return '*';
  if (s.includes('div') || s === '/') return '/';
  if (s.includes('exp') || s === '^') return '^';
  return '+';
}
function operationsFromFeast(feast, fallback) {
  if (feast && feast.operation) return [operationToSymbol(feast.operation)];
  return fallback || ['+'];
}
function runGenerate(ctx, req) {
  const thresholds = req.thresholds || undefined;
  const feast = req.feast || {};
  const attempts = req.attempts || [];
  const numberRange = req.numberRange || [0, 9];
  const operations = operationsFromFeast(feast, req.operations);
  const numProblems = feast.count != null ? feast.count : 20;
  const distribution = mixToDistribution(feast.mix);
  const sessionSelection = sessionSelectionFromConfig(feast.session);
  const rng = Array.isArray(req.rngSequence) && req.rngSequence.length
    ? (() => { let idx = 0; const seq = req.rngSequence; return () => seq[idx++ % seq.length]; })()
    : undefined;
  const result = ctx.generateFluencyProblemList({
    attempts,
    numProblems,
    distribution,
    thresholds,
    sessionSelection,
    numberRange,
    operations,
    excludeFlagged: req.excludeFlagged !== false,
    rng,
  });
  return {
    ok: true,
    problems: result.problems || [],
    counts: result.counts || {},
    poolSizes: result.poolSizes || {},
    warnings: result.warnings || [],
  };
}
function runPercent(ctx, req) {
  const thresholds = req.thresholds || undefined;
  const attempts = req.attempts || [];
  const numberRange = req.numberRange || [0, 9];
  const feast = req.feast || {};
  const operations = operationsFromFeast(feast, req.operations);
  const percent = ctx.fluencyPercent(attempts, thresholds, {
    numberRange,
    operations,
    excludeFlagged: req.excludeFlagged !== false,
  });
  return { ok: true, percent };
}
async function main() {
  const raw = await readStdin();
  let req;
  try {
    req = JSON.parse(raw || '{}');
  } catch (e) {
    process.stdout.write(JSON.stringify({ ok: false, error: 'invalid JSON: ' + e.message }) + '\n');
    process.exit(1);
  }
  const scriptDir = req.scriptDir || process.env.MATHQUEST_FLUENCY_SCRIPT_DIR || toolsDir;
  let ctx;
  try {
    ctx = loadFluencyCore(scriptDir);
  } catch (e) {
    process.stdout.write(JSON.stringify({ ok: false, error: e.message }) + '\n');
    process.exit(1);
  }
  const command = req.command || 'generate';
  try {
    const out = command === 'percent' ? runPercent(ctx, req) : runGenerate(ctx, req);
    process.stdout.write(JSON.stringify(out) + '\n');
  } catch (e) {
    process.stdout.write(JSON.stringify({ ok: false, error: e.message || String(e) }) + '\n');
    process.exit(1);
  }
}
main();
