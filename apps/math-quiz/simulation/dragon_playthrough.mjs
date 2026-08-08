// Headless full-playthrough harness for the dragon fluency game.
//
// Plays the game's exact progression loop end to end with a simulated learner
// (simulation/dragon_learner.mjs), using the REAL app code at every step:
//   load latest .sqlite -> attempts query -> fluencyPercent (fluency_core.js)
//   -> Fluency Feast burst (generateFluencyProblemList, same preset rules as
//      dragon/quiz_bridge.js buildBurst) -> answer problems -> session JSON in
//      the exact dragon-feast shape -> save (dev server /api/save-run, the
//      same pipeline the browser game uses) -> recompute fluency -> high-water
//      + milestone queue (the REAL dragon/sim modules) -> repeat to 100%.
//
// Every event is recorded to events.jsonl; playthrough_report.mjs turns the
// stream into a human-readable markdown report.
//
// CLI (from repo root, requires `npm install` in apps/math-quiz/tests):
//   node apps/math-quiz/simulation/dragon_playthrough.mjs \
//     [--run-dir <dir>] [--port 8931] [--folder playtest] [--user DragonSim] \
//     [--seed dragon-sim] [--rate 0.10] [--max-bursts 100] [--blank] \
//     [--report-out <tracked .md path>]
import { mkdirSync, appendFileSync, writeFileSync } from 'node:fs';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join, resolve } from 'node:path';
import { randomUUID } from 'node:crypto';
import { createAppContext } from '../tests/load_app.mjs';
import { loadSqlJs } from './sql_node.mjs';
import { hashSeed } from './adaptive_selector.mjs';
import { createSimLearner } from './dragon_learner.mjs';
import { statusSnapshot, medianRtByTier, buildReportMarkdown } from './playthrough_report.mjs';
import { openUserStore } from '../engine/user_store.mjs';
import { createMemoryPersistence } from '../engine/persistence.mjs';
import { createGameState } from '../dragon/sim/game_state.js';
import { resolveMilestones, MILESTONES } from '../dragon/sim/milestones.js';
import { nextStoryBeat, markBeatSeen, quizReaction } from '../dragon/sim/story.js';
import { writeSeedDb } from './dragon_seed.mjs';

const APP_DIR = resolve(dirname(fileURLToPath(import.meta.url)), '..');
// Same constants as dragon/quiz_bridge.js.
const RANGE = [0, 9];
const OPERATIONS = ['+'];
const FLUENCY_FEAST_PRESET = {
  count: 20,
  sessionSelection: { mode: 'all' },
  mix: { missing: 40, incorrect: 40, almost: 10, 'needs-practice': 10, fluent: 0 },
};
// Mirror of dragon/quiz_bridge.js — prepend two easy warm-ups when a feast list is built.
const FLUENCY_FEAST_EASY_START = true;
const ATTEMPTS_SQL = `SELECT pa.problem_text AS problem_text, pa.is_correct AS is_correct, pa.response_time_ms AS response_time_ms,
              pa.attempt_id AS attempt_id, pa.session_id AS session_id, pa.flags_json AS flags_json, s.start_time AS start_time
       FROM ProblemAttempts pa JOIN Sessions s ON pa.session_id = s.session_id
       WHERE s.user_name = ? ORDER BY s.start_time, pa.attempt_id`;

// Real app functions from the browser scripts, evaluated in a Node vm.
export function createAppFns() {
  const ctx = createAppContext(['math_utils.js', 'fluency_core.js']);
  return {
    ctx,
    createTables: ctx.__get('createTables'),
    importSessionData: ctx.__get('importSessionData'),
    deleteSessionFromDb: ctx.__get('deleteSessionFromDb'),
    thresholds: ctx.__evalJson('defaultFluencyThresholds'),
    fluencyPercent: (attempts, thresholds, options) => ctx.__eval(
      `fluencyPercent(${JSON.stringify(attempts)}, ${JSON.stringify(thresholds)}, ${JSON.stringify(options)})`),
    evaluateFluencyStatus: (attempts, thresholds) => ctx.__evalJson(
      `evaluateFluencyStatus(${JSON.stringify(attempts)}, ${JSON.stringify(thresholds)})`),
    // Deterministic in-vm rng (same generator as adaptive_selector.makeRng).
    generateFluencyProblemList: (options, rngSeed) => ctx.__evalJson(
      `(() => {
        let s = ${hashSeed(String(rngSeed)) >>> 0};
        const rng = () => {
          s = (s + 0x6D2B79F5) | 0;
          let t = Math.imul(s ^ (s >>> 15), 1 | s);
          t = t + Math.imul(t ^ (t >>> 7), 61 | t) ^ t;
          return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
        };
        return generateFluencyProblemList(Object.assign(${JSON.stringify(options)}, { rng }));
      })()`),
    pickFluencyFeastEasyStart: (options, rngSeed) => ctx.__evalJson(
      `(() => {
        let s = ${hashSeed(String(rngSeed) + ':easy') >>> 0};
        const rng = () => {
          s = (s + 0x6D2B79F5) | 0;
          let t = Math.imul(s ^ (s >>> 15), 1 | s);
          t = t + Math.imul(t ^ (t >>> 7), 61 | t) ^ t;
          return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
        };
        return pickFluencyFeastEasyStart(Object.assign(${JSON.stringify(options)}, { rng }));
      })()`),
  };
}

function rowsFromExec(db, sql, params) {
  const res = db.exec(sql, params);
  if (!res.length) return [];
  return res[0].values.map((row) => {
    const o = {};
    res[0].columns.forEach((c, i) => { o[c] = row[i]; });
    return o;
  });
}
export function queryAttempts(SQL, bytes, user) {
  if (!bytes || !bytes.length) return [];
  const db = new SQL.Database(bytes);
  const rows = rowsFromExec(db, ATTEMPTS_SQL, [user]);
  db.close();
  return rows;
}
function stampOf(ms) {
  const d = new Date(ms);
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}_${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`;
}
function shuffleWith(rng, arr) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

// Mirror of dragon/quiz_bridge.js buildBurst (preset rules + blank-slate fallback).
export function buildBurstProblems({ fns, attempts, feastPreset, thresholds, rngSeed, fallbackRng }) {
  const saved = feastPreset || FLUENCY_FEAST_PRESET;
  const count = Math.max(10, Math.min(20, saved.count || FLUENCY_FEAST_PRESET.count));
  const sessionSelection = (saved.session && saved.session.mode)
    ? { mode: saved.session.mode, n: saved.session.n, since: saved.session.since }
    : FLUENCY_FEAST_PRESET.sessionSelection;
  const mix = saved.mix || FLUENCY_FEAST_PRESET.mix;
  let problems = [];
  if (attempts && attempts.length) {
    const feastOpts = {
      attempts, sessionSelection,
      numberRange: RANGE, operations: OPERATIONS, excludeFlagged: true, thresholds,
    };
    const res = fns.generateFluencyProblemList({
      ...feastOpts, numProblems: count, distribution: mix,
    }, rngSeed);
    problems = (res && res.problems) ? res.problems : [];
    if (problems.length && FLUENCY_FEAST_EASY_START && typeof fns.pickFluencyFeastEasyStart === 'function') {
      const easy = fns.pickFluencyFeastEasyStart(feastOpts, rngSeed);
      if (easy && easy.problems && easy.problems.length === 2) problems = easy.problems.concat(problems);
    }
  }
  if (!problems.length) {
    const all = [];
    for (let a = 0; a <= 9; a++) for (let b = a; b <= 9; b++) all.push(`${a} + ${b}`);
    problems = shuffleWith(fallbackRng || Math.random, all).slice(0, count);
  }
  return problems;
}

// Exact shape of dragon/quiz_bridge.js buildSessionJson.
export function buildDragonSessionJson({ user, folder, problems, kind, startTime, endTime }) {
  const correct = problems.filter((p) => p.is_correct).length;
  const avg = problems.length ? Math.round(problems.reduce((s, p) => s + p.response_time_ms, 0) / problems.length) : 0;
  return {
    version: '1.1',
    user: { name: user },
    session: {
      id: randomUUID(),
      start_time: startTime,
      end_time: endTime,
      settings: {
        preset: 'dragon-feast',
        note: `mode:dragon;outcome:${kind}`,
        num_problems: problems.length,
        number_range: RANGE,
        numbers_include: [],
        numbers_exclude: [],
        num_numbers: 2,
        operations: OPERATIONS,
        source_folder: folder,
        destination: 'source',
        test_description: '',
      },
      summary: { total_problems: problems.length, correct_answers: correct, average_response_time_ms: avg },
      problems,
    },
  };
}

async function sessionBytes({ SQL, fns, user, sessionJson, stamp }) {
  const runStore = await openUserStore({
    username: `math-flu_${user}_${stamp}`,
    deps: {
      SQL,
      createTables: fns.createTables,
      importSession: fns.importSessionData,
      deleteSession: fns.deleteSessionFromDb,
      deriveFluency: null,
    },
    persistence: createMemoryPersistence(),
  });
  runStore.ingest(sessionJson, `math-flu_${user}_${stamp}.sqlite`);
  const bytes = runStore.exportBytes();
  runStore.close();
  return bytes;
}

// Transport: the real dev-server HTTP pipeline (what the browser game uses).
export function createHttpTransport({ baseUrl, folder, user }) {
  return {
    async loadLatest() {
      const resp = await fetch(`${baseUrl}/api/latest-user-db?folder=${encodeURIComponent(folder)}&user=${encodeURIComponent(user)}`);
      const j = await resp.json();
      if (!j || !j.ok) throw new Error(`latest-user-db failed: ${(j && j.error) || resp.status}`);
      if (!j.found) return { found: false, bytes: null, fluencyFeast: null, profile: null };
      return {
        found: true,
        filename: j.filename,
        bytes: new Uint8Array(Buffer.from(j.base64, 'base64')),
        fluencyFeast: j.fluencyFeast || null,
        profile: j.profile || null,
      };
    },
    async saveRun({ bytes, stamp, forceNew }) {
      const resp = await fetch(`${baseUrl}/api/save-run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sourceFolder: folder,
          destination: 'source',
          name: user,
          stamp,
          testDescription: '',
          forceNew: !!forceNew,
          base64: Buffer.from(bytes).toString('base64'),
        }),
      });
      const j = await resp.json();
      if (!j || !j.ok) throw new Error(`save-run failed: ${(j && j.error) || resp.status}`);
      return { ok: true, filename: j.filename };
    },
  };
}

// Transport: pure in-memory accumulation (no server) — for the smoke test.
export function createMemoryTransport({ SQL, fns, user, seedBytes = null }) {
  let accumulated = seedBytes;
  return {
    async loadLatest() {
      if (!accumulated) return { found: false, bytes: null, fluencyFeast: null, profile: null };
      return { found: true, filename: `memory_${user}.sqlite`, bytes: accumulated, fluencyFeast: null, profile: null };
    },
    async saveRun({ sessionJson }) {
      const db = accumulated ? new SQL.Database(accumulated) : new SQL.Database();
      fns.createTables(db);
      fns.importSessionData(db, sessionJson, `memory_${user}.sqlite`);
      accumulated = db.export();
      db.close();
      return { ok: true, filename: `memory_${user}.sqlite` };
    },
  };
}

function makeLocalStorageStub() {
  const store = new Map();
  return {
    getItem: (k) => (store.has(k) ? store.get(k) : null),
    setItem: (k, v) => store.set(k, String(v)),
    removeItem: (k) => store.delete(k),
    clear: () => store.clear(),
  };
}

// The full game loop. Returns { events, state, bursts, finalPct }.
export async function runPlaythrough({
  SQL, fns, transport, learner, user = 'DragonSim', folder = 'playtest',
  maxBursts = 100, seed = 'dragon-sim', onEvent = null, startWallMs = Date.now(),
} = {}) {
  const events = [];
  const emit = (e) => { events.push(e); if (onEvent) onEvent(e); };
  const startedReal = Date.now();

  // dragon/sim/game_state.js reads the bare `localStorage` global; give Node one.
  const hadLs = 'localStorage' in globalThis;
  const prevLs = hadLs ? globalThis.localStorage : undefined;
  globalThis.localStorage = makeLocalStorageStub();
  try {
    const gs = createGameState(user);
    const state = gs.load();
    // The player walks to the nest and discovers the egg (the game's first beat).
    state.eggFound = true;
    gs.markCelebrated(state, 'egg-found');
    // Mirrors main.js: discovering the egg reveals Mama Dragon's first letter,
    // and each burst-end reveals the next story beat (naming the dragon when
    // the naming beat arrives — the sim child picks a name immediately).
    const showStoryBeat = (burst) => {
      const next = nextStoryBeat(state);
      if (!next) return null;
      if (!next.isRepeat) markBeatSeen(state, next.beat.id);
      if (next.beat.kind === 'name' && !state.dragonName) state.dragonName = 'SimSpark';
      emit({
        type: 'story-beat', burst, id: next.beat.id, title: next.beat.title,
        phase: next.phase.id, isRepeat: !!next.isRepeat,
      });
      gs.save(state);
      return next;
    };
    showStoryBeat(0);

    const first = await transport.loadLatest();
    let forceNewNextSave = !first.found;   // same rule as quiz_bridge
    const thresholds = (first.profile && first.profile.thresholds)
      ? Object.assign({}, fns.thresholds, first.profile.thresholds)
      : fns.thresholds;
    const feastPreset = first.fluencyFeast || null;
    const pctOpts = { numberRange: RANGE, operations: OPERATIONS, excludeFlagged: true };
    let attempts = queryAttempts(SQL, first.bytes, user);
    let pct = fns.fluencyPercent(attempts, thresholds, pctOpts);
    gs.updateHighWater(state, pct);
    gs.save(state);
    emit({
      type: 'run-start',
      meta: {
        user, folder, seed, startedAt: new Date(startedReal).toISOString(),
        learnerParams: learner.params, tierStart: learner.tierStart,
        startPct: pct, startFile: first.filename || null,
      },
    });

    const milestoneEvent = (id, burst) => {
      const m = MILESTONES.find((x) => x.id === id);
      emit({ type: 'milestone', id, title: (m && m.title) || id, thresholdPct: m ? m.pct : null, burst, maxPct: state.maxPct });
    };
    // Mirrors main.js processCelebrationQueue: queue all crossed milestones,
    // reveal ONE per burst-end.
    const processQueue = (burst) => {
      const pending = resolveMilestones(state.maxPct, state.celebratedIds);
      gs.queueCelebrations(state, pending.map((m) => m.id));
      const id = gs.popCelebration(state);
      if (id) {
        gs.markCelebrated(state, id);
        if (id === 'hatch') state.hatched = true;
        if (id === 'flight-ride') state.rideUnlocked = true;
        milestoneEvent(id, burst);
      }
      gs.save(state);
      return id;
    };
    processQueue(0);   // load-time catch-up reveal (main.js does this too)

    let wallMs = startWallMs;
    let burst = 0;
    while (burst < maxBursts) {
      if (state.rideUnlocked && !state.celebrationQueue.length) break;
      burst += 1;
      const startTime = stampOf(wallMs);
      const rngSeed = `${seed}-burst-${burst}`;
      const problemTexts = buildBurstProblems({
        fns, attempts, feastPreset, thresholds, rngSeed,
        fallbackRng: () => Math.random(),
      });
      emit({ type: 'burst-start', burst, pctBefore: pct, count: problemTexts.length });

      const answered = [];
      const problemEvents = [];
      for (let i = 0; i < problemTexts.length; i++) {
        const a = learner.answer(problemTexts[i]);
        wallMs += a.rtMs + 800;   // think time + feedback/advance overhead
        answered.push({
          id: `${startTime}-${i}`,
          fact_key: a.key,
          problem_text: a.problemText,
          correct_answer: a.correctAnswer,
          user_answer_string: a.userAnswerString,
          user_answer: a.userAnswer,
          is_correct: a.isCorrect,
          response_time_ms: Math.round(a.rtMs),
          presented_at: wallMs - a.rtMs,
          flags: [],
        });
        const pe = {
          type: 'problem', burst, index: i, problemText: a.problemText,
          category: a.category, tier: a.tier, exposure: a.exposure,
          isCorrect: a.isCorrect, rtMs: Math.round(a.rtMs),
        };
        problemEvents.push(pe);
        emit(pe);
      }
      const endTime = stampOf(wallMs);
      const sessionJson = buildDragonSessionJson({
        user, folder, problems: answered, kind: 'list-complete', startTime, endTime,
      });
      const bytes = await sessionBytes({ SQL, fns, user, sessionJson, stamp: startTime });
      const saveRes = await transport.saveRun({ bytes, sessionJson, stamp: startTime, forceNew: forceNewNextSave });
      forceNewNextSave = false;

      const reload = await transport.loadLatest();
      attempts = queryAttempts(SQL, reload.bytes, user);
      const newPct = fns.fluencyPercent(attempts, thresholds, pctOpts);
      gs.updateHighWater(state, newPct);
      state.totalBursts += 1;
      gs.save(state);

      const snap = statusSnapshot(attempts, fns.evaluateFluencyStatus, thresholds);
      const servedByCategory = {};
      for (const pe of problemEvents) servedByCategory[pe.category] = (servedByCategory[pe.category] || 0) + 1;
      const correct = answered.filter((p) => p.is_correct).length;
      emit({
        type: 'burst-end', burst,
        pctBefore: pct, pctAfter: newPct, maxPct: state.maxPct,
        correct, total: answered.length,
        medianRtByTier: medianRtByTier(problemEvents),
        servedByCategory,
        byCategory: snap.byCategory,
        greenCount: snap.greenCount,
        savedFilename: saveRes.filename,
      });
      pct = newPct;
      processQueue(burst);
      const reaction = quizReaction({
        correct, total: answered.length, totalBursts: state.totalBursts, dragonName: state.dragonName,
      });
      if (reaction) emit({ type: 'story-reaction', burst, text: reaction });
      showStoryBeat(burst);
      wallMs += 90000;   // breather between bursts
    }

    emit({
      type: 'run-end',
      bursts: burst,
      finalPct: pct,
      maxPct: state.maxPct,
      rideUnlocked: !!state.rideUnlocked,
      hatched: !!state.hatched,
      celebratedIds: state.celebratedIds.slice(),
      durationMs: Date.now() - startedReal,
    });
    return { events, state, bursts: burst, finalPct: pct };
  } finally {
    if (hadLs) globalThis.localStorage = prevLs;
    else delete globalThis.localStorage;
  }
}

// ---- Dev-server lifecycle (CLI) ----
export async function startDevServer({ port, dataDir, backupDir }) {
  const proc = spawn('python3', ['tools/dev_server.py'], {
    cwd: APP_DIR,
    env: Object.assign({}, process.env, {
      ANCHOR_PORT: String(port),
      ANCHOR_BIND: '127.0.0.1',
      ANCHOR_DATA_DIR: dataDir,
      ANCHOR_BACKUP_DIR: backupDir,
      ANCHOR_S3_DISABLE: '1',
      ANCHOR_PREVENT_SLEEP: '0',
    }),
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let log = '';
  proc.stdout.on('data', (d) => { log += d; });
  proc.stderr.on('data', (d) => { log += d; });
  const baseUrl = `http://127.0.0.1:${port}`;
  for (let i = 0; i < 60; i++) {
    if (proc.exitCode !== null) throw new Error(`dev server exited early:\n${log}`);
    try {
      const r = await fetch(`${baseUrl}/api/data-folders`);
      if (r.ok) return { proc, baseUrl, getLog: () => log };
    } catch { /* not up yet */ }
    await new Promise((res) => setTimeout(res, 250));
  }
  proc.kill();
  throw new Error(`dev server did not come up on ${baseUrl}:\n${log}`);
}

async function main() {
  const args = process.argv.slice(2);
  const opt = (name, dflt) => {
    const i = args.indexOf(`--${name}`);
    return i >= 0 ? args[i + 1] : dflt;
  };
  const has = (name) => args.includes(`--${name}`);
  const stamp = stampOf(Date.now());
  const runDir = resolve(opt('run-dir', join(APP_DIR, 'dragon', 'playtests', 'runs', `${stamp}_headless`)));
  const port = Number(opt('port', '8931'));
  const folder = opt('folder', 'playtest');
  const user = opt('user', 'DragonSim');
  const seed = opt('seed', 'dragon-sim');
  const rate = Number(opt('rate', '0.10'));
  const maxBursts = Number(opt('max-bursts', '100'));
  const reportOut = opt('report-out', null);

  const dataDir = join(runDir, 'data');
  mkdirSync(dataDir, { recursive: true });
  mkdirSync(join(runDir, 'backup'), { recursive: true });
  const eventsPath = join(runDir, 'events.jsonl');
  writeFileSync(eventsPath, '');
  const onEvent = (e) => appendFileSync(eventsPath, JSON.stringify(e) + '\n');

  console.log(`[playthrough] run dir: ${runDir}`);
  const SQL = await loadSqlJs();
  const fns = createAppFns();

  let seedEvent = null;
  if (!has('blank')) {
    const seeded = await writeSeedDb({ dataDir, folder, user, seed: `${seed}-seed` });
    seedEvent = {
      type: 'seed', filename: seeded.filename, startPct: seeded.startPct,
      greenCount: seeded.greenCount, byCategory: seeded.byCategory, sessions: seeded.sessions,
    };
    onEvent(seedEvent);
    console.log(`[playthrough] seeded ${seeded.filename} at ${Math.round(seeded.startPct)}% fluent (${seeded.greenCount}/55 green)`);
  }

  const server = await startDevServer({ port, dataDir, backupDir: join(runDir, 'backup') });
  console.log(`[playthrough] dev server up at ${server.baseUrl} (data: ${dataDir})`);
  let result;
  try {
    const learner = createSimLearner({ seed: `${seed}-learner`, ratePerExposure: rate });
    const transport = createHttpTransport({ baseUrl: server.baseUrl, folder, user });
    result = await runPlaythrough({
      SQL, fns, transport, learner, user, folder, maxBursts, seed,
      onEvent: (e) => {
        onEvent(e);
        if (e.type === 'burst-end') {
          console.log(`[burst ${String(e.burst).padStart(2)}] ${Math.round(e.pctBefore)}% -> ${Math.round(e.pctAfter)}%  score ${e.correct}/${e.total}  green ${e.greenCount}/55`);
        }
        if (e.type === 'milestone') console.log(`[milestone] ${e.title} (${e.id}) after burst ${e.burst} at high-water ${Math.round(e.maxPct)}%`);
      },
    });
  } finally {
    server.proc.kill();
  }

  const allEvents = seedEvent ? [seedEvent, ...result.events] : result.events;
  const md = buildReportMarkdown(allEvents, { mode: 'headless', user, folder, seed });
  writeFileSync(join(runDir, 'report.md'), md);
  if (reportOut) {
    const fileName = reportOut.split('/').pop();
    writeFileSync(resolve(reportOut), buildReportMarkdown(allEvents, { mode: 'headless', user, folder, seed, fileName }));
    console.log(`[playthrough] tracked report: ${reportOut}`);
  }
  console.log(`[playthrough] done: ${result.bursts} bursts, final ${Math.round(result.finalPct)}%, ride unlocked: ${result.state.rideUnlocked}`);
  console.log(`[playthrough] events: ${eventsPath}`);
  console.log(`[playthrough] report: ${join(runDir, 'report.md')}`);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  main().catch((e) => { console.error(e); process.exit(1); });
}
