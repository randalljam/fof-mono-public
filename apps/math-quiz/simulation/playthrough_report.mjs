// Playthrough reporting for the dragon-game test apparatus: turn the recorded
// event stream (events.jsonl) into a human-readable markdown report, plus the
// shared per-category fluency snapshot both drivers log at burst boundaries.
// Pure (no I/O) so it is unit-testable and usable from Node CLI and Playwright.
import { buildAdditionFacts, ADDITION_CATEGORIES } from '../engine/addition_segmentation.mjs';
import { parseAdditionProblem, TIER_OF_CATEGORY, TIERS } from './dragon_learner.mjs';

export const CATEGORY_LABELS = {
  'add-zero': 'Add 0', 'add-one': 'Add 1', 'add-two': 'Add 2',
  doubles: 'Doubles', 'tough-21': 'Tough 21',
};
export const CATEGORY_SIZES = (() => {
  const sizes = {};
  for (const f of buildAdditionFacts()) sizes[f.category] = (sizes[f.category] || 0) + 1;
  return sizes;   // add-zero 10, add-one 9, add-two 8, doubles 7, tough-21 21
})();

function isFlagged(flagsJson) {
  if (!flagsJson) return false;
  try {
    const flags = JSON.parse(flagsJson);
    return Array.isArray(flags) && flags.length > 0;
  } catch { return false; }
}

// Per-fact / per-category fluency snapshot from raw DB attempt rows
// (problem_text, is_correct, response_time_ms, flags_json — the bridge's
// attempts query shape). `evaluateFluencyStatus` is the REAL app function
// (injected from the vm context or browser global).
export function statusSnapshot(attemptRows, evaluateFluencyStatus, thresholds) {
  const perFactAttempts = new Map();
  for (const row of attemptRows || []) {
    if (isFlagged(row.flags_json)) continue;
    const parsed = parseAdditionProblem(row.problem_text);
    if (!parsed) continue;
    const [lo, hi] = [Math.min(parsed.num1, parsed.num2), Math.max(parsed.num1, parsed.num2)];
    if (lo < 0 || hi > 9) continue;
    const list = perFactAttempts.get(parsed.key) || [];
    list.push({ isCorrect: !!row.is_correct, responseTime: row.response_time_ms });
    perFactAttempts.set(parsed.key, list);
  }
  const perFact = {};
  const byCategory = {};
  for (const cat of ADDITION_CATEGORIES) {
    byCategory[cat] = { total: CATEGORY_SIZES[cat], green: 0, yellow: 0, red: 0, gray: 0, nodata: 0 };
  }
  for (const fact of buildAdditionFacts()) {
    const attempts = perFactAttempts.get(fact.key) || [];
    const status = attempts.length
      ? evaluateFluencyStatus(attempts, thresholds).status
      : 'nodata';
    perFact[fact.key] = status;
    const bucket = byCategory[fact.category];
    if (status === 'green' || status === 'blue') bucket.green += 1;
    else if (status === 'yellow') bucket.yellow += 1;
    else if (status === 'red') bucket.red += 1;
    else if (status === 'gray') bucket.gray += 1;
    else bucket.nodata += 1;
  }
  const greenCount = Object.values(byCategory).reduce((s, b) => s + b.green, 0);
  return { perFact, byCategory, greenCount, totalFacts: 55 };
}

export function medianRtByTier(problemEvents) {
  const byTier = {};
  for (const t of TIERS) byTier[t] = [];
  for (const p of problemEvents) {
    const tier = p.tier || TIER_OF_CATEGORY[p.category];
    if (tier) byTier[tier].push(p.rtMs ?? p.response_time_ms);
  }
  const out = {};
  for (const t of TIERS) {
    const arr = byTier[t].filter((v) => Number.isFinite(v)).sort((a, b) => a - b);
    out[t] = arr.length ? Math.round((arr[(arr.length - 1) >> 1] + arr[arr.length >> 1]) / 2) : null;
  }
  return out;
}

function fmtMs(v) { return v == null ? '—' : `${(v / 1000).toFixed(1)}s`; }
function fmtPct(v) { return v == null ? '—' : `${Math.round(v)}%`; }
function pad2(n) { return String(n).padStart(2, '0'); }
function nowStampPacific() {
  const d = new Date();
  const p = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Los_Angeles', year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hour12: false,
  }).formatToParts(d).reduce((o, x) => (o[x.type] = x.value, o), {});
  return { date: `${p.year}-${p.month}-${p.day}`, stamp: `${p.year}-${p.month}-${p.day}_${p.hour}${p.minute}` };
}

function categoryTable(byCategory) {
  const rows = [
    '| Category | Facts | Green | Yellow | Red | Gray | No data |',
    '|---|---|---|---|---|---|---|',
  ];
  for (const cat of ADDITION_CATEGORIES) {
    const b = byCategory[cat];
    if (!b) continue;
    rows.push(`| ${CATEGORY_LABELS[cat]} | ${b.total} | ${b.green} | ${b.yellow} | ${b.red} | ${b.gray} | ${b.nodata} |`);
  }
  return rows.join('\n');
}

// events: parsed objects from events.jsonl (in order). meta: run-level info
// (mode, user, learner params, game changes, screenshots dir note, etc.).
export function buildReportMarkdown(events, meta = {}) {
  const runStart = events.find((e) => e.type === 'run-start') || { meta: {} };
  const runMeta = Object.assign({}, runStart.meta, meta);
  const seed = events.find((e) => e.type === 'seed');
  const burstEnds = events.filter((e) => e.type === 'burst-end');
  const milestones = events.filter((e) => e.type === 'milestone');
  const uxNotes = events.filter((e) => e.type === 'ux');
  const shots = events.filter((e) => e.type === 'screenshot');
  const runEnd = events.find((e) => e.type === 'run-end') || {};
  const { date, stamp } = nowStampPacific();
  const title = runMeta.title || `Dragon game simulated playthrough (${runMeta.mode || 'headless'})`;
  const fileName = runMeta.fileName || `${date}_simulated-playthrough.md`;

  const lines = [];
  lines.push(`file: ${fileName}`);
  lines.push(`title: ${title}`);
  lines.push(`last-updated: ${stamp}`);
  lines.push(`ai: ${runMeta.ai || 'Cursor agent'}`);
  lines.push(`session: ${runMeta.session || ''}`);
  lines.push('');
  lines.push(`# ${title}`);
  lines.push('');
  lines.push('Generated by the dragon playthrough test apparatus '
    + '(`simulation/dragon_playthrough.mjs` / `tests/e2e_playthrough/`). A simulated learner '
    + 'plays the real game loop end to end from a seeded starting SQLite file: every burst is '
    + 'generated by the real Fluency Feast code, saved through the real dev-server pipeline, and '
    + 'fluency is recomputed from the file by the real rubric after every save.');
  lines.push('');
  lines.push('');
  lines.push('## Run parameters');
  lines.push(`- **Mode:** ${runMeta.mode || 'headless'}`);
  lines.push(`- **Learner:** \`${runMeta.user || '?'}\` in folder \`${runMeta.folder || '?'}\` (sandbox — never real learner data)`);
  lines.push(`- **RNG seed:** \`${runMeta.seed || 'default'}\``);
  const lp = runMeta.learnerParams || {};
  lines.push(`- **Learning model:** ${Math.round((lp.ratePerExposure ?? 0.1) * 100)}% faster per exposure, `
    + `+${Math.round((lp.accuracyGainPerExposure ?? 0.05) * 100)}pp accuracy per exposure, `
    + `floor ${lp.floorMs ?? 950} ms, max accuracy ${lp.maxAccuracy ?? 0.98}`);
  const ts = runMeta.tierStart || {};
  const tierLine = TIERS.map((t) => {
    const s = ts[t] || {};
    return `${t} ${s.medianMs ?? '?'} ms / ${Math.round((s.accuracy ?? 0) * 100)}%`;
  }).join(' · ');
  lines.push(`- **Tier baselines (median RT / accuracy):** ${tierLine}`);
  lines.push('- **Tiers:** easy = Add 0 + Add 1 · medium = Add 2 + Doubles · hard = Tough 21');
  if (runMeta.startedAt) lines.push(`- **Run started:** ${runMeta.startedAt}`);
  if (runEnd.durationMs != null) lines.push(`- **Wall time:** ${(runEnd.durationMs / 60000).toFixed(1)} min`);
  lines.push('');
  lines.push('');
  lines.push('## Starting state (seed SQLite file)');
  if (seed) {
    lines.push(`Seed file \`${seed.filename}\` — **${fmtPct(seed.startPct)} fluent** at start `
      + `(${seed.greenCount ?? '?'} of 55 facts green).`);
    lines.push('');
    lines.push(categoryTable(seed.byCategory || {}));
  } else {
    lines.push('Blank slate (no seed file — first burst used the all-facts fallback list).');
  }
  lines.push('');
  lines.push('');
  lines.push('## Burst-by-burst');
  lines.push('One row per quiz burst (Fluency Feast). Fluency % is the objective cross-session '
    + '`fluencyPercent` recomputed from the saved file after each save. Median RT columns cover '
    + 'only the problems served in that burst.');
  lines.push('');
  lines.push('| # | Fluency | Score | Med RT easy | Med RT med | Med RT hard | Served (0/1/2/Dbl/T21) | Milestone |');
  lines.push('|---|---|---|---|---|---|---|---|');
  const milestoneByBurst = new Map();
  for (const m of milestones) {
    const list = milestoneByBurst.get(m.burst) || [];
    list.push(m);
    milestoneByBurst.set(m.burst, list);
  }
  for (const b of burstEnds) {
    const med = b.medianRtByTier || {};
    const served = b.servedByCategory || {};
    const servedStr = ['add-zero', 'add-one', 'add-two', 'doubles', 'tough-21']
      .map((c) => served[c] || 0).join('/');
    const ms = (milestoneByBurst.get(b.burst) || []).map((m) => `**${m.title}**`).join(', ');
    lines.push(`| ${b.burst} | ${fmtPct(b.pctBefore)} → ${fmtPct(b.pctAfter)} | ${b.correct}/${b.total} `
      + `| ${fmtMs(med.easy)} | ${fmtMs(med.medium)} | ${fmtMs(med.hard)} | ${servedStr} | ${ms || ''} |`);
  }
  lines.push('');
  lines.push('');
  lines.push('## Milestone timeline');
  lines.push('| Milestone | Threshold | Revealed after burst | Fluency (high-water) at reveal |');
  lines.push('|---|---|---|---|');
  for (const m of milestones) {
    lines.push(`| ${m.title} (\`${m.id}\`) | ${m.thresholdPct != null ? fmtPct(m.thresholdPct) : '—'} `
      + `| ${m.burst} | ${fmtPct(m.maxPct)} |`);
  }
  const storyBeats = events.filter((e) => e.type === 'story-beat');
  const storyCards = events.filter((e) => e.type === 'story');
  if (storyBeats.length || storyCards.length) {
    lines.push('');
    lines.push('');
    lines.push('## Story timeline');
    lines.push('One story beat is revealed after every burst (sequential fresh beats, then the phase’s extras rotate).');
    lines.push('');
    lines.push('| Burst | Beat | Phase |');
    lines.push('|---|---|---|');
    for (const b of storyBeats) {
      lines.push(`| ${b.burst} | ${b.title}${b.isRepeat ? ' *(revisit)*' : ''} | ${b.phase} |`);
    }
    for (const s of storyCards) {
      for (const c of s.cards || []) {
        if (c.kicker && c.kicker.includes('Quiz complete')) continue;   // reaction lines are noise here
        lines.push(`| ${s.burst} | ${c.title}${c.naming ? ' *(named the dragon)*' : ''} | ${c.kicker || ''} |`);
      }
    }
  }
  lines.push('');
  lines.push('');
  lines.push('## Category progression');
  lines.push('Burst after which each category first reached fully green (all facts fluent).');
  lines.push('');
  lines.push('| Category | Facts | Fully green after burst |');
  lines.push('|---|---|---|');
  const firstAllGreen = {};
  for (const b of burstEnds) {
    for (const cat of ADDITION_CATEGORIES) {
      const bucket = b.byCategory && b.byCategory[cat];
      if (!bucket) continue;
      if (firstAllGreen[cat] === undefined && bucket.green >= bucket.total) firstAllGreen[cat] = b.burst;
    }
  }
  for (const cat of ADDITION_CATEGORIES) {
    lines.push(`| ${CATEGORY_LABELS[cat]} | ${CATEGORY_SIZES[cat]} | ${firstAllGreen[cat] ?? 'not reached'} |`);
  }
  lines.push('');
  lines.push('');
  lines.push('## Outcome');
  lines.push(`- **Bursts played:** ${runEnd.bursts ?? burstEnds.length}`);
  lines.push(`- **Final fluency:** ${fmtPct(runEnd.finalPct)} (high-water ${fmtPct(runEnd.maxPct)})`);
  lines.push(`- **Ride unlocked (100% flight-ride):** ${runEnd.rideUnlocked ? 'yes' : 'no'}`);
  const totalProblems = burstEnds.reduce((s, b) => s + (b.total || 0), 0);
  const totalCorrect = burstEnds.reduce((s, b) => s + (b.correct || 0), 0);
  lines.push(`- **Problems answered:** ${totalProblems} (${totalCorrect} correct)`);
  if (uxNotes.length || shots.length) {
    lines.push('');
    lines.push('');
    lines.push('## UX log (browser run)');
    if (runMeta.runDirNote) lines.push(runMeta.runDirNote);
    lines.push('');
    for (const n of uxNotes) lines.push(`- burst ${n.burst ?? '—'}: ${n.note}`);
    if (shots.length) {
      lines.push('');
      lines.push('Screenshots (gitignored, in the run folder):');
      for (const s of shots) lines.push(`- \`${s.file}\` — ${s.label}`);
    }
  }
  lines.push('');
  lines.push('');
  lines.push('## Game changes discovered');
  const changes = runMeta.gameChanges || [];
  if (!changes.length) {
    lines.push('None — the apparatus ran against unmodified game code (the test harness itself is purely additive).');
  } else {
    for (const c of changes) lines.push(`- ${c}`);
  }
  lines.push('');
  return lines.join('\n');
}
