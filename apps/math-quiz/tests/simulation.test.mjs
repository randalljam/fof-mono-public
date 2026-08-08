// Integration tests: SC2 (session JSON), SC3 (per-profile end state),
// SC4/SC5 (mastery), SC6 (hard coverage), SC7 (hole targeting)
import test from 'node:test';
import assert from 'node:assert/strict';
import { runSimulation } from '../simulation/simulation.mjs';
import { checkPredictiveMastery, checkThoroughMastery } from '../simulation/adaptive_selector.mjs';
import { PROFILE_01, PROFILE_02, PROFILE_03 } from '../simulation/profiles.mjs';
import { createAppContext } from './load_app.mjs';

function makeFluencyFns() {
  const ctx = createAppContext(['math_utils.js', 'fluency_core.js', 'math_fluency.js']);
  return {
    evaluateFluencyStatus: (attempts, thresholds) =>
      ctx.__evalJson(`evaluateFluencyStatus(${JSON.stringify(attempts)}${thresholds ? ', ' + JSON.stringify(thresholds) : ''})`),
    checkPermanentStatus: (history, n) =>
      ctx.__eval(`checkPermanentStatus(${JSON.stringify(history)}, ${n ?? 5})`),
  };
}

// SC2: session JSON is in the correct canonical shape for importSessionData
test('SC2: simulation emits importable session JSON', async () => {
  const fns = makeFluencyFns();
  const result = runSimulation(PROFILE_01, {}, fns);
  assert.ok(result.sessions.length > 0);

  for (const session of result.sessions) {
    assert.ok(session.version, 'version');
    assert.ok(session.user?.name, 'user.name');
    const s = session.session;
    assert.ok(s.id, 'session.id');
    assert.ok(s.start_time, 'start_time');
    assert.ok(s.end_time, 'end_time');
    assert.ok(Array.isArray(s.settings?.operations), 'settings.operations');
    assert.ok(typeof s.summary?.total_problems === 'number', 'summary');
    assert.ok(Array.isArray(s.problems), 'problems');
    for (const p of s.problems) {
      assert.ok(p.id && typeof p.problem_text === 'string', 'problem fields');
      assert.ok(typeof p.is_correct === 'boolean' && typeof p.response_time_ms === 'number', 'attempt fields');
    }
  }

  // If sql.js available, verify real import works
  let SQL = null;
  try {
    const { readFileSync } = await import('node:fs');
    const initSqlJs = (await import('sql.js')).default;
    const wasmBinary = readFileSync(new URL('./node_modules/sql.js/dist/sql-wasm.wasm', import.meta.url));
    SQL = await initSqlJs({ wasmBinary });
  } catch { /* not installed */ }

  if (SQL) {
    const { createAppContext: cac } = await import('./load_app.mjs');
    const ctx = cac(['math_utils.js']);
    const db = new SQL.Database();
    ctx.__get('createTables')(db);
    const importFn = ctx.__get('importSessionData');
    for (const session of result.sessions.slice(0, 3)) importFn(db, session, 'sim.json');
    const count = (sql) => db.exec(sql)[0].values[0][0];
    assert.ok(count('SELECT COUNT(*) FROM Sessions') >= 1);
    assert.ok(count('SELECT COUNT(*) FROM ProblemAttempts') >= 1);
  }
});

// SC3: beginner ends >=70% green, >=3 blue, no red
test('SC3: profile_01 addition-beginner reaches >=70% green with >=3 blue and no red', () => {
  const fns = makeFluencyFns();
  const result = runSimulation(PROFILE_01, {}, fns);
  const { finalStatus, factMatrix } = result;

  let greenCount = 0, blueCount = 0, redCount = 0;
  for (const [key] of factMatrix) {
    const s = finalStatus.get(key) || 'nodata';
    if (s === 'green') greenCount++;
    else if (s === 'blue') blueCount++;
    else if (s === 'red') redCount++;
  }

  const pct = (greenCount + blueCount) / factMatrix.size;
  assert.ok(pct >= 0.70, `green+blue = ${(pct*100).toFixed(1)}% should be >=70%. green=${greenCount} blue=${blueCount} total=${factMatrix.size}`);
  assert.ok(blueCount >= 3, `blue count ${blueCount} should be >=3`);
  assert.equal(redCount, 0, `red count ${redCount} should be 0`);
});

// SC3: holes profile closes >=90% of seeded holes
test('SC3: profile_02 mixed-with-holes closes >=90% of seeded multiplication holes', () => {
  const fns = makeFluencyFns();
  const result = runSimulation(PROFILE_02, {}, fns);
  const { finalStatus, factMatrix } = result;

  const holes = [...factMatrix.keys()].filter(key => {
    const f = factMatrix.get(key);
    return f.operation === '*' && (f.num1 >= 6 || f.num2 >= 6);
  });

  const closed = holes.filter(key => {
    const s = finalStatus.get(key) || 'nodata';
    return s === 'green' || s === 'blue';
  }).length;

  const pct = holes.length > 0 ? closed / holes.length : 0;
  assert.ok(pct >= 0.90, `hole closure ${(pct*100).toFixed(1)}% should be >=90%. closed=${closed}/${holes.length}`);
});

// SC7: hole facts get >= 3x presentations vs fluent facts
test('SC7: profile_02 seeded holes get >= 3x presentations versus fluent facts', () => {
  const fns = makeFluencyFns();
  const result = runSimulation(PROFILE_02, {}, fns);
  const { perFactPresentations, factMatrix } = result;

  let holePres = [], fluentPres = [];
  for (const [key, fact] of factMatrix) {
    const p = perFactPresentations.get(key) || 0;
    if (fact.operation === '*' && (fact.num1 >= 6 || fact.num2 >= 6)) holePres.push(p);
    else if (fact.operation === '+') fluentPres.push(p); // + facts start fluent
  }

  const avg = (arr) => arr.length > 0 ? arr.reduce((a,b)=>a+b,0)/arr.length : 0;
  const ratio = avg(holePres) / Math.max(avg(fluentPres), 1);
  assert.ok(ratio >= 3, `hole/fluent ratio ${ratio.toFixed(2)} should be >= 3`);
});

// SC4: predictive mastery fires from partial sample with high hard coverage
test('SC4: profile_03 predictive-short achieves predictive mastery', () => {
  const fns = makeFluencyFns();
  const result = runSimulation(PROFILE_03, { name: 'predictive-short' }, fns);
  const { sampledFacts, perFactAttempts, factMatrix } = result;

  const params = { predictive_min_coverage: 0.45, predictive_hard_min_coverage: 0.75, minAccuracy: 0.8 };
  const r = checkPredictiveMastery(sampledFacts, factMatrix, perFactAttempts, fns, params);
  assert.ok(r.passes, `predictive mastery failed: ${r.reason}. coverage=${r.coverage?.toFixed(2)} hardFraction=${r.hardFraction?.toFixed(2)}`);
  assert.ok(sampledFacts.size < factMatrix.size, 'sample should be partial');
});

// SC5: thorough mastery certifies every fact
test('SC5: profile_03 thorough-complete achieves thorough mastery', () => {
  const fns = makeFluencyFns();
  const result = runSimulation(PROFILE_03, { name: 'thorough-complete', schedule: { sessions: 1, problems_per_session: 'full-matrix' } }, fns);
  const { perFactAttempts, factMatrix } = result;

  const r = checkThoroughMastery(factMatrix, perFactAttempts, 2000);
  assert.ok(r.passes, `thorough mastery failed: ${r.reason}`);
});

// SC6: in predictive run, hard coverage > easy coverage and hard fraction >= 0.75
test('SC6: predictive-short hard coverage exceeds easy coverage', () => {
  const fns = makeFluencyFns();
  const result = runSimulation(PROFILE_03, { name: 'predictive-short' }, fns);
  const { sampledFacts, factMatrix } = result;

  let hardSeen=0, easySeen=0, hardTotal=0, easyTotal=0;
  for (const [key, fact] of factMatrix) {
    if (fact.isHard) { hardTotal++; if (sampledFacts.has(key)) hardSeen++; }
    else { easyTotal++; if (sampledFacts.has(key)) easySeen++; }
  }

  const hardCov = hardTotal > 0 ? hardSeen/hardTotal : 0;
  const easyCov = easyTotal > 0 ? easySeen/easyTotal : 0;
  assert.ok(hardCov > easyCov, `hard cov ${hardCov.toFixed(2)} should exceed easy cov ${easyCov.toFixed(2)}`);

  const hardFraction = sampledFacts.size > 0 ? hardSeen/sampledFacts.size : 0;
  assert.ok(hardFraction >= 0.75, `hard fraction ${hardFraction.toFixed(2)} should be >= 0.75`);
});
