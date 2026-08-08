// Live anchor-case page: the fast fluency demonstration. Drives the engine's
// assess flow against real keyboard input, persists everything to a per-user
// SQLite store (IndexedDB) AND a separate per-run SQLite file, and surfaces the
// "continue to 100% / stop here" decision when predictive mastery fires.
// DOM-free logic lives in engine/ and simulation/; this file is the controller.
// See 2026-06-15_assess-practice-modes-spec-and-plan.md (Part C / live UI).
import { buildFactMatrix, makeRng } from './simulation/adaptive_selector.mjs';
import { createAssessRun, createThoroughRun } from './engine/assess_flow.mjs';
import { buildAnchorAdditionPlan } from './engine/addition_segmentation.mjs';
import { openUserStore } from './engine/user_store.mjs';
import { createIndexedDbPersistence } from './engine/persistence.mjs';
import { createSessionWriter } from './engine/write_mode.mjs';
import { bytesToBase64, loadLatestUserDb, countSessions, chooseHydrationBytes } from './engine/sqlite_io.mjs';
import { expandProblemListItems, internalListBaseItems } from './engine/problem_list.mjs';
import { mountProblemListPanel } from './engine/problem_list_panel.mjs';
import { parseTargets, parseTargetSpec, parseFillerFacts, factToText, createTargetedRun } from './engine/targeted_practice.mjs';
import { createVisualRun } from './engine/visual_practice.mjs';
import { tenFrameTeachStates } from './engine/ten_frame.mjs';
import { teachableProblem, showLightbulbOnRender, autoTeachOnWrong, showLightbulbInFlagPanel } from './engine/teach_policy.mjs';

const qs = new URLSearchParams(location.search);
const teachHoldParam = Number(qs.get('teachms'));
// Curated plans guarantee hard-fact coverage by construction, so the conclusion
// rests on accuracy/speed over the administered set (hard-fraction gate off).
const PREDICTIVE = {
  predictive_min_coverage: Number(qs.get('cov')) || 0.7,
  predictive_hard_min_coverage: 0,
  minAccuracy: 0.8,
};
const FAST_MS = 2000;
// Brief confirmation flash (show the entered number + ✓) before the next problem.
// The response time is captured BEFORE this, so it never affects fluency timing.
// Brief confirmation flash before the next problem, in ms. Default 0.3s; surfaced
// as a seconds control on the setup card (dev mode); ?fb= overrides (e2e).
let feedbackMs = qs.has('fb') ? Number(qs.get('fb')) : 300;
// Wrong-answer correction flow: on a wrong typed answer, pause and show the correct
// answer + Flag / Continue / Continue&insert. Hard-coded ON; ?correct=0 disables (e2e/dev).
const CORRECTION_FLOW = qs.get('correct') !== '0';
const INSERT_GAP = 5;   // "Continue & insert" re-asks the fact this many problems later
const FLAG_REASON_LABELS = { 'skip-noreason': 'Skip - no reason', lightbulb: '💡 Show ten-frames', distracted: 'Distracted', interrupted: 'Interrupted', error: 'Input Error', stall: 'Stall', dontknow: "I Don't Know", other: 'Other' };
const SHOW_BIG_KEYS = qs.get('bigkeys') === '1'; // off by default; ?bigkeys=1 enables (e2e/dev)
const WRITE_MODE = qs.get('write') || 'sqlite-only'; // dev default: SQLite only, no JSON
const RANGE = [0, 9];
const USER_DB = 'mathQuizUserStores';
const RUN_DB = 'mathQuizAnchorRuns';
// Auto-revert HF -> EF: switch to easy-first after this many "struggle" responses
// (wrong/skip, or slower than several seconds) while hard-first is active.
const REVERT_SLOW_MS = 4000;
const REVERT_THRESHOLD = 3;
const EASY_RANK = { 'add-zero': 0, 'add-one': 1, 'add-two': 2, doubles: 3, 'tough-21': 4 };
const PROBLEM_LIST_DIRS = ['problem-lists'];
const PROBLEM_LIST_MAX_REPLICATES = 4;
const PROBLEM_LIST_FALLBACK_FILES = ['0to9_75problems.txt', '2026-06-18_addition_28problems.txt'];
// Problem-source sentinel: run the learner's own stored lists ("Use internal", from this file).
const INTERNAL_LIST_VALUE = '__internal__';
// Problem-source sentinel: targeted fluency practice on 1-5 typed target problems.
const TARGETED_VALUE = '__targeted__';
// Problem-source sentinel: strategy-supported visual practice on 1-5 target problems.
const VISUAL_VALUE = '__visual__';
// Quick quiz: the auto-generated 7-problem set for one operation (QuickPracticeItems table,
// regenerated server-side after each quiz). Keyed by canonical operator.
const QUICK_OP_LABELS = { '+': 'Addition', '-': 'Subtraction', '*': 'Multiplication' };
const TARGETED_MAX_TARGETS = 5;     // up to 5 target problems
const TARGETED_GRAD_STREAK = 3;     // default fast-correct-in-a-row to graduate a target
const TARGETED_FAST_MS = 2000;      // default "fast" threshold (ms)
const TARGETED_PERCENT = 50;        // default % of problems that are the current target (rest = filler)
const TARGETED_FIELD_IDS = ['anchor-target-1', 'anchor-target-2', 'anchor-target-3', 'anchor-target-4', 'anchor-target-5'];
const VISUAL_MAX_TARGETS = 5;       // up to 5 visual-practice target problems
const VISUAL_FAST_MS = 2000;        // default visual retrieval "fast" threshold (ms)
const VISUAL_CLEARS = 2;            // default fast retrievals needed to clear a target
const TEACH_HOLD_MS = qs.has('teachms') && Number.isFinite(teachHoldParam) && teachHoldParam >= 0 ? teachHoldParam : 2000;
const VISUAL_FIELD_IDS = ['anchor-vtarget-1', 'anchor-vtarget-2', 'anchor-vtarget-3', 'anchor-vtarget-4', 'anchor-vtarget-5'];
// Per-learner prefill defaults — used to seed the fields/filler until the per-user file
// stores its own config (the file wins once saved). Targets are compact; filler is spaced
// (the problem-list "a + b" form).
const TARGETED_DEFAULTS = {
  Kid1: {
    targets: ['6+3', '6+8', '4+9', '3+7', '3+4'],
    filler: ['0 + 0', '0 + 1', '1 + 0', '0 + 2', '2 + 0', '0 + 3', '3 + 0', '0 + 4', '4 + 0',
             '0 + 5', '5 + 0', '0 + 6', '6 + 0', '0 + 7', '7 + 0', '0 + 8', '8 + 0', '0 + 9', '9 + 0',
             '1 + 1', '1 + 2', '2 + 1', '1 + 3', '3 + 1', '1 + 4', '4 + 1', '1 + 5', '5 + 1',
             '1 + 6', '6 + 1', '1 + 7', '7 + 1', '1 + 8', '8 + 1', '1 + 9', '9 + 1',
             '2 + 2', '2 + 3', '3 + 2', '2 + 4', '4 + 2', '2 + 5', '5 + 2', '2 + 6', '6 + 2',
             '2 + 7', '7 + 2', '2 + 8', '8 + 2', '2 + 9', '9 + 2',
             '3 + 3', '4 + 4', '5 + 5', '6 + 6', '7 + 7', '8 + 8', '9 + 9'],
  },
  K2: {
    targets: ['1+8', '2+7', '2+5', '2+8', '4+7'],
    filler: ['0 + 1', '0 + 9', '6 + 0', '0 + 6', '8 + 0', '1 + 5', '5 + 1', '1 + 8', '3 + 3', '6 + 6'],
    graduationStreak: 5, fastMs: 4000, percentTarget: 30,
  },
};
// Starter targeted-ten-frame set (research-recommended make-ten facts). Shared by Kid1 and the
// Randy/Tester clone-landing users so Targeted ten frames works after cloning a kid file that
// has no VisualPracticeConfig of its own yet — a saved file config still wins when present.
const VISUAL_STARTER = {
  targets: ['8+3', '4+9', '6+8'],
  filler: ['0 + 8', '1 + 6', '2 + 7', '5 + 5', '6 + 6', '8 + 9', '0 + 3', '1 + 2'],
  // Practice bar, not the assessment bar: two-digit iPad answers at ~2.5s are real
  // retrievals — 2000ms made correct answers earn no credit and the session drag.
  fastMs: 3000,
};
const VISUAL_DEFAULTS = {
  Kid1: VISUAL_STARTER,
  Kid1: VISUAL_STARTER,
  Randy: VISUAL_STARTER,
  Tester: VISUAL_STARTER,
};
// Per-student graduation reward — the right-side animation. Two images, both set
// per-learner via a path in the SQLite file's TargetedConfig (rewardImage /
// completionImage), so they can be customized without code changes (the coach
// edits the file directly). `rewardImage` shows on EACH target graduation;
// `completionImage` shows only on the LAST graduation that completes the whole
// session. When a learner's file specifies neither, both fall back to the single
// path below. A missing/failed image falls back to the 🎉 placeholder. Assets live
// under apps/math-quiz/_assets/ (local-only, mounted from _LOCAL_FILES).
const TARGETED_REWARD_FALLBACK = '_assets/pipa-dance.webp';
// Session-completion fallback — deliberately a DIFFERENT animation from the per-target
// reward, so finishing the whole session reads as a bigger deal (targeted + visual).
const TARGETED_COMPLETION_FALLBACK = '_assets/pipa_no_wand_clap_jump_fixed.webp';

const $ = (id) => document.getElementById(id);
const escapeHtml = (s) => String(s == null ? '' : s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const show = (id) => $(id).classList.remove('hidden');
const hide = (id) => $(id).classList.add('hidden');
function showQuiz() {
  show('anchor-quiz');
  document.body.classList.add('in-quiz');
  // The keypad has no Enter key; when auto-submit is off, the Enter button below the
  // problem box is how the learner submits. With auto-submit on it stays hidden.
  (autoSubmit ? hide : show)('anchor-enter');
}
function hideQuiz() {
  hide('anchor-quiz');
  document.body.classList.remove('in-quiz');
}

// Save the per-run .sqlite via the local dev server (tools/dev_server.py), which
// holds the .env AWS creds for automatic append-snapshot backup. Saving is allowed whenever
// /api/health responds (localhost or LAN IP on the same Wi-Fi); a plain static
// server or deployed site has no sidecar, so disk save is skipped with a note.
// One-line note about what happened to the internal list this run used (server "consume").
function describeConsumed(c) {
  if (!c) return '';
  if (c.action === 'deleted') return `\nUsed internal list #${c.list_order} "${c.list_name}" — removed from the file.`;
  if (c.action === 'retained') return `\nUsed internal list #${c.list_order} "${c.list_name}" — kept (used ${c.times_used}×).`;
  if (c.action === 'missing') return '\n(Internal list was already gone — nothing to remove.)';
  if (c.action === 'error') return `\nNote: could not update the internal list (${c.error}).`;
  return '';
}
async function uploadRun(bytes) {
  let health = null;
  try { const h = await fetch('/api/health'); if (h.ok) health = await h.json(); } catch { /* no sidecar */ }
  if (!health) {
    return {
      kind: 'error',
      text: 'Could not reach the dev server on your laptop, so this session was not written to disk.\n'
        + 'Common causes: the Mac slept, the server was stopped, or this device lost Wi‑Fi.\n'
        + 'The session is safe in this browser — wake the Mac, run tools/dev_server.py, then tap Retry.',
    };
  }
  try {
    // The dev server archives the single-session file, appends server-side into the source
    // folder, and saves under _data/. Append snapshots are backed up automatically.
    const r = await fetch('/api/save-run', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sourceFolder, destination, name: username, stamp: startTime,
        testDescription, forceNew: sourceMode === 'new', base64: bytesToBase64(bytes),
        sourceFile: sourceMode === 'continue' ? (selectedSourceFile || loadedServerFile || undefined) : undefined,
        consumedProblemListId,
        targetedConfig: targetedMode ? buildTargetedPersist() : undefined,
        visualConfig: visualMode ? buildVisualPersist() : undefined,
      }),
    });
    const j = await r.json();
    const single = j.singleSessionPath;
    const base = j.action === 'append' ? `Added to ${j.filename}`
      : j.action === 'test-run' ? `Saved test run ${j.subfolder}/${j.filename}`
        : `Created ${j.filename}`;
    const did = base + describeConsumed(j.consumedProblemList);
    const localPath = j.localPath || '';
    if (j.ok) {
      let text = `${did}\nSaved locally: ${localPath}`;
      if (j.singleSessionS3Uri) text += `\nSingle-session archived to ${j.singleSessionS3Uri}`;
      else if (j.singleSessionS3Error) text += `\nSingle-session saved locally, but S3 archive failed: ${j.singleSessionS3Error}`;
      if (j.backup) text += `\nSnapshot backup: ${j.backup}`;
      if (j.backupS3Uri) text += `\nSnapshot backed up to ${j.backupS3Uri}`;
      else if (j.backupS3Error) text += `\nSnapshot saved locally, but S3 backup failed: ${j.backupS3Error}`;
      else if (j.backupError) text += `\nNote: snapshot backup failed: ${j.backupError}`;
      if (j.targetedConfig && j.targetedConfig.error) {
        text += `\nNote: targeted settings were not updated: ${j.targetedConfig.error}`;
      }
      if (j.visualConfig && j.visualConfig.error) {
        text += `\nNote: visual settings were not updated: ${j.visualConfig.error}`;
      }
      return { kind: 'ok', single, accumulated: buildAccumulatedTarget(j), text };
    }
    return { kind: 'error', single, text: j.message || `Save failed: ${j.error || 'unknown error'}` };
  } catch (e) {
    return {
      kind: 'error',
      text: `Save failed: ${String(e.message || e)}\nThe session is still in this browser — tap Retry once the dev server is back.`,
    };
  }
}
function buildAccumulatedTarget(j) {
  if (!j || !j.ok || !j.filename) return null;
  return {
    folder: j.destination === 'test' ? 'test' : (j.sourceFolder || sourceFolder),
    user: username,
    file: j.filename,
    subfolder: j.destination === 'test' ? (j.subfolder || null) : null,
  };
}
function hideDevTools() { hide('anchor-dev-tools'); }
function showDevTools() { show('anchor-dev-tools'); }
function showUploadResult(r) {
  const el = $('anchor-upload');
  el.textContent = r.text;
  el.style.color = r.kind === 'ok' ? '#666' : '#c62828';
  let info = '';
  if (r.accumulated && r.accumulated.file) {
    info = `Accumulated file:\n  ${r.accumulated.file}`;
    if (r.accumulated.subfolder) info += `\n  (in ${r.accumulated.folder}/${r.accumulated.subfolder}/)`;
    else info += `\n  (in ${r.accumulated.folder}/)`;
  }
  if (r.single) info += `${info ? '\n\n' : ''}Archived single-session copy:\n  ${r.single}`;
  $('anchor-file-info').textContent = info;
  if (r.kind === 'ok' || !lastRunBytes) hide('anchor-retry-upload');
  else show('anchor-retry-upload');
}
async function runUpload() {
  if (!lastRunBytes || !lastRunFilename) return;
  $('anchor-upload').textContent = 'Saving…';
  $('anchor-upload').style.color = '#666';
  hideDevTools();
  $('anchor-retry-upload').disabled = true;
  try {
    const r = await uploadRun(lastRunBytes);
    showUploadResult(r);
    if (r.kind === 'ok') {
      lastAnalysisTarget = r.accumulated || null;
      consumedProblemListId = null;
      refreshListPanel();
      showDevTools();
    }
  } finally {
    $('anchor-retry-upload').disabled = false;
  }
}
async function onRetryUpload() {
  if (!lastRunBytes) return;
  await runUpload();
}

// "Load for analysis": open the analysis page on the accumulated file from this finished
// run (explicit filename from /api/save-run). Falls back to latest-user-db when no run has
// been saved yet in this session.
function onLoadForAnalysis() {
  const name = ($('anchor-username').value || '').trim();
  const params = new URLSearchParams();
  if (lastAnalysisTarget && lastAnalysisTarget.user === name) {
    params.set('folder', lastAnalysisTarget.folder);
    params.set('user', lastAnalysisTarget.user);
    params.set('file', lastAnalysisTarget.file);
    if (lastAnalysisTarget.subfolder) params.set('subfolder', lastAnalysisTarget.subfolder);
  } else {
    params.set('folder', currentFolder());
    if (name) params.set('user', name);
  }
  window.open(`math_analysis.html?${params.toString()}`, '_blank');
}

// ----- fact / display helpers -----
function parseKey(key) {
  const [operation, a, b] = key.split('|');
  return { operation, num1: Number(a), num2: Number(b) };
}
function canonicalKey(operation, num1, num2) {
  if (operation === '+' || operation === '*') return `${operation}|${Math.min(num1, num2)}|${Math.max(num1, num2)}`;
  return `${operation}|${num1}|${num2}`;
}
function answerFor(operation, num1, num2) {
  if (operation === '+') return num1 + num2;
  if (operation === '-') return num1 - num2;
  return num1 * num2;
}
const DISPLAY = { '+': '+', '-': '−', '*': '×' };
// Parse an integer from a setup field, clamped to [lo, hi]; falls back to dflt when blank/NaN.
function clampInt(raw, lo, hi, dflt) {
  const n = parseInt(raw, 10);
  if (!Number.isFinite(n)) return dflt;
  return Math.min(hi, Math.max(lo, n));
}
function timestamp(d = new Date()) {
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}_${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`;
}
function fmtDuration(ms) {
  const s = Math.round(ms / 1000);
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${String(s % 60).padStart(2, '0')}s`;
}
function extractTxtFilesFromDirectoryHtml(html) {
  const names = [];
  const re = /href="([^"]+)"/gi;
  let m = re.exec(html);
  while (m) {
    const raw = m[1] || '';
    const decoded = decodeURIComponent(raw);
    const name = decoded.replace(/\/+$/, '').split('/').pop();
    if (name && name !== '..' && /\.txt$/i.test(name)) names.push(name);
    m = re.exec(html);
  }
  return [...new Set(names)];
}
async function discoverProblemListFiles() {
  const files = [];
  const seen = new Set();
  for (const folder of PROBLEM_LIST_DIRS) {
    try {
      const r = await fetch(`${folder}/`, { cache: 'no-store' });
      if (!r.ok) continue;
      const html = await r.text();
      for (const name of extractTxtFilesFromDirectoryHtml(html)) {
        const id = name.toLowerCase();
        if (seen.has(id)) continue;
        seen.add(id);
        files.push({ label: name, value: `${folder}/${name}` });
      }
    } catch {
      // Ignore missing directory listings; we'll leave only the default option.
    }
  }
  return files;
}
function updateProblemListControlState() {
  const hasSelection = !!$('anchor-problem-list-file').value;
  $('anchor-problem-list-replicates').disabled = !hasSelection;
  $('anchor-problem-list-randomize').disabled = !hasSelection;
}
function appendProblemListOptions(select, files) {
  const seenLabels = new Set([...select.options].map((opt) => String(opt.textContent || '').trim().toLowerCase()));
  for (const file of files) {
    const label = String(file.label || '').trim();
    if (!label) continue;
    const key = label.toLowerCase();
    if (seenLabels.has(key)) continue;
    seenLabels.add(key);
    const option = document.createElement('option');
    option.value = file.value;
    option.textContent = label;
    select.appendChild(option);
  }
}
async function initProblemListControls() {
  const select = $('anchor-problem-list-file');
  const status = $('anchor-problem-list-status');
  status.textContent = 'Loading problem-list files...';
  appendProblemListOptions(select, PROBLEM_LIST_FALLBACK_FILES.map((name) => ({ label: name, value: `problem-lists/${name}` })));
  const discoveredFiles = await discoverProblemListFiles();
  appendProblemListOptions(select, discoveredFiles);
  const available = [...select.options].filter((o) => o.value && o.value !== INTERNAL_LIST_VALUE && o.value !== TARGETED_VALUE && o.value !== VISUAL_VALUE).length;
  if (available === 0) status.textContent = 'No .txt files discovered in problem-lists/. Using default adaptive plan.';
  else status.textContent = `Found ${available} problem-list file${available === 1 ? '' : 's'}.`;
  updateProblemListControlState();
}
function parseProblemListLine(line) {
  const normalized = String(line || '')
    .replace(/^\s*(?:[-*+]\s+|\d+\.\s+)/, '')
    .replace(/=/g, ' ')
    .replace(/[xX×]/g, '*')
    .replace(/[÷]/g, '/')
    .replace(/[−]/g, '-')
    .replace(/\s+/g, ' ')
    .trim();
  if (!normalized) return null;
  const parsed = typeof globalThis.parseProblemText === 'function' ? globalThis.parseProblemText(normalized) : { num1: null, operation: null, num2: null };
  const { num1, operation, num2 } = parsed;
  if (!Number.isFinite(num1) || !Number.isFinite(num2) || !['+', '-', '*'].includes(operation)) {
    throw new Error(`Could not parse "${line}". Use lines like "3 + 4" with +, -, or *.`);
  }
  return { num1, num2, operation };
}
function parseProblemListText(text) {
  const lines = String(text || '').split(/\r?\n/);
  const items = [];
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const parsed = parseProblemListLine(trimmed);
    if (parsed) items.push({ ...parsed, category: 'problem-list' });
  }
  if (items.length === 0) throw new Error('Selected list file has no valid problems.');
  return items;
}
async function buildProblemListConfig(pathname, replicates, randomize) {
  const r = await fetch(pathname, { cache: 'no-store' });
  if (!r.ok) throw new Error(`Could not load problem list file "${pathname}".`);
  const baseItems = parseProblemListText(await r.text());
  const { reps, sequence } = expandProblemListItems(baseItems, {
    replicates, randomize, maxReplicates: PROBLEM_LIST_MAX_REPLICATES, rng: Math.random,
  });
  return {
    sourcePath: pathname,
    sourceName: pathname.split('/').pop() || pathname,
    randomize: !!randomize,
    replicates: reps,
    baseCount: baseItems.length,
    sequence,
  };
}
// Build a run config from one of THIS learner's stored lists (the top of the queue). Items
// carry stored num1/operation/num2 (from the server); problem_text is the parse fallback.
function buildProblemListConfigFromInternal(list, replicates, randomize) {
  const baseItems = internalListBaseItems(list, (text) => {
    try { return parseProblemListLine(text); } catch { return null; }
  });
  const { reps, sequence } = expandProblemListItems(baseItems, {
    replicates, randomize, maxReplicates: PROBLEM_LIST_MAX_REPLICATES, rng: Math.random,
  });
  return {
    sourcePath: `internal:${list.problem_list_id}`,
    sourceName: `internal #${list.list_order}: ${list.list_name}`,
    randomize: !!randomize,
    replicates: reps,
    baseCount: baseItems.length,
    sequence,
    internalProblemListId: list.problem_list_id,
  };
}
// Build a run config from the learner's auto-generated quick-quiz set for one operation
// (the 7 QuickPracticeItems rows for that op). Presented once each, in stored item_order.
function buildQuickPracticeConfig(operation, items) {
  const baseItems = internalListBaseItems(
    { items: items || [], list_name: `Quick quiz (${operation})` },
    (text) => { try { return parseProblemListLine(text); } catch { return null; } }
  );
  const { reps, sequence } = expandProblemListItems(baseItems, {
    replicates: 1, randomize: false, maxReplicates: 1, rng: Math.random,
  });
  return {
    sourcePath: `quick:${operation}`,
    sourceName: `Quick quiz: ${QUICK_OP_LABELS[operation] || operation}`,
    randomize: false,
    replicates: reps,
    baseCount: baseItems.length,
    sequence,
  };
}

// ----- module state -----
let SQL = null;
let store = null;
let username = 'Guest';
let sourceFolder = 'real';      // source folder under local _data/ ('real' | 'test' | custom)
let destination = 'source';     // where the run is saved: 'source' (accumulate) | 'test' (trial)
let sourceMode = 'continue';    // 'continue' (auto-load latest) | 'new' (Start New lineage)
let testDescription = '';       // short label appended to the test run's folder name
let operations = ['+'];
let autoSubmit = true;
let continueIfFluent = false;
let factMatrix = null;
let run = null;
let phase = 'predictive';      // 'predictive' | 'thorough' | 'targeted' | 'visual'
let currentItem = null;
let shownAt = 0;
let shownAtWall = '';   // wall-clock (ISO) time the current problem was presented
let startMs = 0;
let startTime = '';
let submitting = false;
let sessionProblems = [];
let thoroughRun = null;
let lastRunBytes = null;
let lastRunFilename = '';
let guardrailShown = false;
let anomalyHit = null;
let correctionProblem = null;  // the sessionProblems entry the flag panel is editing
let correctionMode = null;     // null | 'answer' (wrong/skip — Continue advances) | 'previous' (Flag previous — Continue resumes the current problem)
let prevFlagItem = null;       // the fact "Flag previous & insert" re-asks (the previous problem's fact)
let correctionLightbulbItem = null; // flag-panel problem whose teach visual can be reviewed
let guardrailEnabled = false;  // realism guardrail: off by default (no UI toggle); ?guardrail=1 enables it
let orderHardFirst = true;     // checkbox: hard-first (default) vs easy-first
let autoRevert = true;         // switch: HF -> EF when struggling
let orderMode = 'HF';          // 'HF' | 'EF' (shown at the bottom)
let struggleCount = 0;
let reverted = false;
let orderJustTransitioned = false;
let practiceQueue = [];
let practiceIdx = 0;
let practiceTarget = null;
let practiceRound = 1;
let practiceLog = []; // warm-up entries: { round, target, entered, isCorrect, responseTime }
let problemListConfig = null;
let problemListInitPromise = null;
let internalLists = [];            // this learner's stored lists from the loaded file (ordered 1..N)
let consumedProblemListId = null;  // the internal list this run ran (popped server-side on save)
let loadedQuickPractice = {};      // auto-generated quick-quiz sets from the loaded file ({op: [items]})
let pendingQuickQuizOp = null;     // set by the kid "Quick quiz" buttons; consumed by onStart
let listPanel = null;              // the shared collapsible problem-list editor
let lastAnalysisTarget = null;     // accumulated file from the last successful save-run (for analysis)
// ----- targeted practice (phase 'targeted') -----
let targetedMode = false;          // true when this run is targeted practice (vs assess)
let targetedRun = null;            // engine/targeted_practice run controller
let targetedStart = null;          // config captured at Start: { targets, fillerFacts, graduationStreak, fastMs, percentTarget }
let loadedTargetedConfig = null;   // targeted config read from the per-user file (or null)
let loadedFluencyFeast = null;     // saved Fluency-feast preset from the per-user file (or null)
let loadedProfile = null;          // per-file profile flags from the per-user file (or null = code defaults)
let targetedGraduationPending = false;  // a target just graduated — wait for the Continue button
// ----- visual practice (phase 'visual') -----
let visualMode = false;            // true when this run is visual practice (vs assess)
let visualRun = null;              // engine/visual_practice run controller
let visualStart = null;            // config captured at Start: { targets, fillerFacts, fastMs, retrievalsToClear }
let loadedVisualConfig = null;     // visual config read from the per-user file (or null)
let teachState = null;             // current ten-frame setup/result SVG pair
let teachItem = null;
let teachTargetKey = null;
let teachRevealTimer = null;
let teachContext = null;            // null | 'help' | 'wrong' | 'review'
let pendingTeach = null;           // target trial waiting for teach after flags/continue
let visualClearPending = false;    // a target just cleared — wait for the Continue button
// Keep the editor in sync when it's open and the name/folder changes (or after a consume).
function refreshListPanel() { if (listPanel && listPanel.element.classList.contains('plp-open')) listPanel.refresh(); }

async function ensureSql() {
  if (SQL) return SQL;
  if (typeof initSqlJs !== 'function') throw new Error('sql.js failed to load (check your connection).');
  SQL = await initSqlJs({ locateFile: (f) => 'https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.6.2/' + f });
  return SQL;
}
function storeDeps() {
  return {
    SQL,
    createTables: globalThis.createTables,
    importSession: globalThis.importSessionData,
    deleteSession: globalThis.deleteSessionFromDb,
    deriveFluency: null, // fluency grid is a later phase; the conclusion comes from the run
  };
}

// Build the ordered presentation plan for the selected operations. Addition uses
// the curated segmentation plan; other operations fall back to a shuffled,
// hard-first list (segmentation for −/× is a later phase).
function buildPlan(ops, order) {
  const items = [];
  if (ops.includes('+')) items.push(...buildAnchorAdditionPlan({ seed: `anchor-${Date.now()}`, order }));
  for (const op of ops.filter((o) => o !== '+')) {
    const fm = buildFactMatrix([op], RANGE);
    const keys = [...fm.keys()];
    const rng = makeRng(`${op}-${Date.now()}`);
    keys.map((k) => ({ k, w: (fm.get(k).isHard ? 0 : 1) + rng() })).sort((a, b) => a.w - b.w)
      .forEach(({ k }) => { const f = fm.get(k); items.push({ key: k, operation: op, num1: f.num1, num2: f.num2 }); });
  }
  return items;
}
function buildFactMatrixFromSequence(sequence) {
  const matrix = new Map();
  for (const item of sequence) {
    matrix.set(item.key, {
      operation: item.operation,
      num1: item.num1,
      num2: item.num2,
      isHard: false,
      category: item.category || 'problem-list',
    });
  }
  return matrix;
}

async function onStart() {
  $('anchor-error').textContent = '';
  lastAnalysisTarget = null;
  hideDevTools();
  username = ($('anchor-username').value || '').trim() || 'Guest';
  sourceFolder = currentFolder();
  destination = currentDestination();
  sourceMode = currentSourceMode();   // 'continue' vs 'new' (Start New) — sent to the server as forceNew
  testDescription = $('anchor-test-description') ? ($('anchor-test-description').value || '').trim() : '';

  // Continue latest needs an existing source file; refresh the lookup and block early with a
  // clear message rather than running a whole quiz the server can't file.
  if (sourceMode === 'continue') {
    await refreshNameStatus();
    if (lastLoadFound === false) {
      $('anchor-error').textContent =
        `No file for "${username}" in source folder "${sourceFolder}" to continue. `
        + `Pick "Start new file" to begin one, or choose a different source folder.`;
      return;
    }
  }
  autoSubmit = $('anchor-autosubmit').checked;
  continueIfFluent = $('anchor-continue-if-fluent').checked;
  // Feedback delay is surfaced in seconds on the setup card (dev control); ?fb= (ms) overrides for e2e.
  if (!qs.has('fb')) {
    const secs = parseFloat(($('anchor-feedback-delay') && $('anchor-feedback-delay').value) || '0.3');
    feedbackMs = Number.isFinite(secs) && secs >= 0 ? Math.round(secs * 1000) : 300;
  }
  orderHardFirst = $('anchor-hardfirst').checked;
  autoRevert = $('anchor-autorevert').checked;
  guardrailEnabled = qs.get('guardrail') === '1';   // off by default; ?guardrail=1 enables it (e2e/dev)
  problemListConfig = null;
  consumedProblemListId = null;
  targetedMode = false;
  targetedStart = null;
  targetedGraduationPending = false;
  visualMode = false;
  visualRun = null;
  visualStart = null;
  visualClearPending = false;
  pendingTeach = null;
  closeTeachPanel();
  // The kid "Quick quiz" buttons set this just before calling onStart; capture + clear it so a
  // later plain Start (anchor-start button) doesn't accidentally re-run the quick set.
  const quickQuizOp = pendingQuickQuizOp;
  pendingQuickQuizOp = null;

  const selectedProblemList = $('anchor-problem-list-file').value;
  const listReplicates = $('anchor-problem-list-replicates').value;
  const listRandomize = $('anchor-problem-list-randomize').checked;
  if (quickQuizOp) {
    // Quick quiz: run the auto-generated 7-problem set for one operation, in order.
    try {
      problemListConfig = buildQuickPracticeConfig(quickQuizOp, loadedQuickPractice[quickQuizOp]);
    } catch (e) {
      $('anchor-error').textContent = String(e.message || e);
      return;
    }
    operations = [quickQuizOp];
    orderHardFirst = false;
    autoRevert = false;
  } else if (selectedProblemList === TARGETED_VALUE) {
    // Targeted practice: up to 5 typed target facts (each covers both orientations).
    const inputs = TARGETED_FIELD_IDS.map((id) => ($(id) ? $(id).value : ''));
    const { targets, errors } = parseTargets(inputs, { max: TARGETED_MAX_TARGETS });
    if (errors.length) {
      $('anchor-error').textContent = `Couldn't read target problem(s): ${errors.join(', ')}. Use a form like 3+6 or 8+7.`;
      return;
    }
    if (!targets.length) { $('anchor-error').textContent = 'Type at least one target problem (e.g. 3+6).'; return; }
    const { facts: fillerFacts } = parseFillerFacts(fillerLines());
    const graduationStreak = clampInt($('anchor-target-streak') && $('anchor-target-streak').value, 1, 9, TARGETED_GRAD_STREAK);
    const fastMs = clampInt($('anchor-target-fastms') && $('anchor-target-fastms').value, 200, 60000, TARGETED_FAST_MS);
    const percentTarget = clampInt($('anchor-target-percent') && $('anchor-target-percent').value, 1, 100, TARGETED_PERCENT);
    // Reward animation paths come from the learner's file config (set by the coach),
    // not from any UI field; snapshot them at Start so the run uses a stable value.
    const lc = loadedTargetedConfig || {};
    targetedStart = { targets, fillerFacts, graduationStreak, fastMs, percentTarget,
      rewardImage: lc.rewardImage || null, completionImage: lc.completionImage || null };
    targetedMode = true;
    operations = [...new Set(targets.map((t) => t.operation))];
    orderHardFirst = false;
    autoRevert = false;
    flushTargetedSave();   // persist the current settings to the source file right away (config only, no session)
  } else if (selectedProblemList === VISUAL_VALUE) {
    // Visual practice: serial target facts with optional ten-frame teaching.
    const inputs = VISUAL_FIELD_IDS.map((id) => ($(id) ? $(id).value : ''));
    const { targets, errors } = parseTargets(inputs, { max: VISUAL_MAX_TARGETS });
    if (errors.length) {
      $('anchor-error').textContent = `Couldn't read target problem(s): ${errors.join(', ')}. Use a form like 8+3 or 4+9.`;
      return;
    }
    if (!targets.length) { $('anchor-error').textContent = 'Type at least one target problem (e.g. 8+3).'; return; }
    const unsupported = targets.filter((target) => !teachableProblem(target));
    if (unsupported.length) {
      $('anchor-error').textContent =
        `Visual practice supports addition facts with totals up to 20. Change: ${unsupported.map(factToText).join(', ')}.`;
      return;
    }
    const { facts: fillerFacts } = parseFillerFacts(visualFillerLines());
    const fastMs = clampInt($('anchor-visual-fastms') && $('anchor-visual-fastms').value, 200, 60000, VISUAL_FAST_MS);
    const retrievalsToClear = clampInt($('anchor-visual-clears') && $('anchor-visual-clears').value, 1, 5, VISUAL_CLEARS);
    // Reward animations reuse the learner's targeted-practice images (same file config).
    const vlc = loadedTargetedConfig || {};
    visualStart = { targets, fillerFacts, fastMs, retrievalsToClear,
      rewardImage: vlc.rewardImage || null, completionImage: vlc.completionImage || null };
    visualMode = true;
    operations = [...new Set(targets.map((t) => t.operation))];
    orderHardFirst = false;
    autoRevert = false;
    flushVisualSave();     // persist the current settings to the source file right away (config only, no session)
  } else if (selectedProblemList === INTERNAL_LIST_VALUE) {
    // "Use internal": run the top of this learner's stored-list queue (lowest list_order).
    if (!internalLists.length) {
      $('anchor-error').textContent =
        `No internal problem lists for "${username}" in "${sourceFolder}". Internal lists come from the `
        + `learner's existing file — use "Continue latest" on a file that has lists (add them with `
        + `tools/problem_list_store.py), or pick another problem source.`;
      return;
    }
    try {
      problemListConfig = buildProblemListConfigFromInternal(internalLists[0], listReplicates, listRandomize);
    } catch (e) {
      $('anchor-error').textContent = String(e.message || e);
      return;
    }
    consumedProblemListId = internalLists[0].problem_list_id;
    operations = [...new Set(problemListConfig.sequence.map((item) => item.operation))];
    orderHardFirst = false;
    autoRevert = false;
  } else if (selectedProblemList) {
    try {
      problemListConfig = await buildProblemListConfig(selectedProblemList, listReplicates, listRandomize);
    } catch (e) {
      $('anchor-error').textContent = String(e.message || e);
      return;
    }
    operations = [...new Set(problemListConfig.sequence.map((item) => item.operation))];
    // List-mode ordering is controlled by the selected file options (label via orderLabel()).
    orderHardFirst = false;
    autoRevert = false;
  } else {
    operations = [['op-add', '+'], ['op-sub', '-'], ['op-mul', '*']].filter(([id]) => $(id).checked).map(([, op]) => op);
    if (operations.length === 0) { $('anchor-error').textContent = 'Pick at least one operation.'; return; }
    orderMode = orderHardFirst ? 'HF' : 'EF';
  }

  buildKeypad(SHOW_BIG_KEYS);

  try {
    await ensureSql();
    store = await openUserStore({ username, deps: storeDeps(), persistence: createIndexedDbPersistence({ dbName: USER_DB }) });
    globalThis.__anchorStore = store; // exposed for e2e assertions
    globalThis.__anchorSession = () => sessionProblems; // ditto
    const practiceMode = targetedMode || visualMode;
    const trigger = visualMode ? 'visual-practice-start' : (targetedMode ? 'targeted-practice-start' : 'session-start');
    store.logModeEvent({ to: practiceMode ? 'practice' : 'assess', trigger });
  } catch (e) {
    $('anchor-error').textContent = String(e.message || e);
    return;
  }

  hide('anchor-setup'); hide('anchor-prompt'); hide('anchor-summary'); hide('anchor-practice-done');
  hide('anchor-landing'); closeKidModal();   // clear the kid landing/pop-up once a run starts
  hide('anchor-filler-editor'); hide('anchor-visual-filler-editor');   // setup-only lists — gone once the quiz/warm-up starts
  hide('anchor-pause-panel'); hide('anchor-target-rings'); hide('anchor-reward-burst'); hide('anchor-grad-continue');
  hideVisualTrialControls(); closeTeachPanel();
  if ($('anchor-practice-enabled').checked) startPractice();
  else startQuiz();
}

// Show only the controls relevant to the current phase.
function setPhaseControls(p) {
  const practice = p === 'practice';
  // Skip & flag and Flag previous are available in every quiz phase (incl. targeted) so the
  // coach can annotate during the run; only the warm-up hides them.
  for (const id of ['anchor-skip-flag', 'anchor-flag-previous', 'anchor-pause', 'anchor-quit-save', 'anchor-quit-abandon', 'anchor-order']) (practice ? hide : show)(id);
  (practice ? show : hide)('anchor-practice-skip');
}

function startQuiz() {
  if (visualMode) { startVisual(); return; }
  if (targetedMode) { startTargeted(); return; }
  setPhaseControls('predictive');
  hide('anchor-practice-done');
  const sequence = problemListConfig
    ? problemListConfig.sequence
    : buildPlan(operations, orderHardFirst ? 'hard-first' : 'easy-first');
  factMatrix = problemListConfig ? buildFactMatrixFromSequence(sequence) : buildFactMatrix(operations, RANGE);
  run = createAssessRun(factMatrix, {
    sequence,
    predictiveParams: PREDICTIVE,
    fastMs: FAST_MS,
    warmupDiscard: 2,
    truncateOnMastery: false, // administer the full curated plan, then judge
    // A fixed problem list is presented exactly once each (× replicates); don't let the
    // adaptive glitch re-ask inflate it past its length. Auto mode keeps the re-ask.
    autoRedeliver: !problemListConfig,
  });
  globalThis.__anchorRun = () => run; // exposed for e2e assertions
  globalThis.__anchorProblemListConfig = () => problemListConfig; // exposed for e2e assertions
  phase = 'predictive';
  struggleCount = 0;
  reverted = false;
  orderJustTransitioned = false;
  sessionProblems = [];
  guardrailShown = false;
  anomalyHit = null;
  showGoGate();
}

// ----- targeted practice: serial targets + filler, graduate on N (cumulative) fast-correct -----
function startTargeted() {
  setPhaseControls('targeted');
  hide('anchor-practice-done');
  factMatrix = buildFactMatrix(operations, RANGE);
  targetedRun = createTargetedRun({
    targets: targetedStart.targets,
    factMatrix,
    fillerFacts: targetedStart.fillerFacts,
    percentTarget: targetedStart.percentTarget,
    graduationStreak: targetedStart.graduationStreak,
    fastMs: targetedStart.fastMs,
    rng: makeRng(`targeted-${username}-${Date.now()}`),
  });
  globalThis.__anchorTargetedRun = () => targetedRun; // exposed for e2e assertions
  phase = 'targeted';
  sessionProblems = [];
  targetedGraduationPending = false;
  hide('anchor-grad-continue');
  showGoGate();
}
// ----- visual practice: cold probe + teach visual + filler-spaced retrieval -----
function startVisual() {
  setPhaseControls('visual');
  hide('anchor-practice-done');
  factMatrix = buildFactMatrix(operations, RANGE);
  visualRun = createVisualRun({
    targets: visualStart.targets,
    factMatrix,
    fillerFacts: visualStart.fillerFacts,
    fastMs: visualStart.fastMs,
    retrievalsToClear: visualStart.retrievalsToClear,
    rng: makeRng(`visual-${username}-${Date.now()}`),
  });
  globalThis.__anchorVisualRun = () => visualRun; // exposed for e2e assertions
  phase = 'visual';
  sessionProblems = [];
  visualClearPending = false;
  pendingTeach = null;
  hide('anchor-grad-continue');
  hideVisualTrialControls();
  closeTeachPanel();
  showGoGate();
}
// The filler editor's current lines (one fact per line).
function fillerLines() { const t = $('anchor-filler-text'); return t ? t.value.split('\n') : []; }
function visualFillerLines() { const t = $('anchor-visual-filler-text'); return t ? t.value.split('\n') : []; }
// The targeted config to PERSIST into the per-user file (sent with the save-run).
function buildTargetedPersist() {
  if (!targetedStart) return null;
  return {
    targets: targetedStart.targets.map(factToText),
    filler: targetedStart.fillerFacts.map(factToText),
    graduationStreak: targetedStart.graduationStreak,
    fastMs: targetedStart.fastMs,
    percentTarget: targetedStart.percentTarget,
  };
}
// The visual config to PERSIST into the per-user file (sent with the save-run).
function buildVisualPersist() {
  if (!visualStart) return null;
  return {
    targets: visualStart.targets.map(factToText),
    filler: visualStart.fillerFacts.map(factToText),
    fastMs: visualStart.fastMs,
    retrievalsToClear: visualStart.retrievalsToClear,
  };
}
// Prefill the target fields + params + filler editor from the loaded file config, else the
// per-learner code defaults. force=false won't clobber fields the coach has already typed.
function applyTargetedPrefill(force = false) {
  if (!force && $('anchor-target-1') && $('anchor-target-1').value.trim() !== '') return;
  const user = ($('anchor-username').value || '').trim();
  const cfg = loadedTargetedConfig || TARGETED_DEFAULTS[user] || null;
  const targets = (cfg && cfg.targets) || [];
  TARGETED_FIELD_IDS.forEach((id, i) => { if ($(id)) $(id).value = targets[i] || ''; });
  if (cfg && cfg.graduationStreak != null && $('anchor-target-streak')) $('anchor-target-streak').value = cfg.graduationStreak;
  if (cfg && cfg.fastMs != null && $('anchor-target-fastms')) $('anchor-target-fastms').value = cfg.fastMs;
  if (cfg && cfg.percentTarget != null && $('anchor-target-percent')) $('anchor-target-percent').value = cfg.percentTarget;
  const fillerEl = $('anchor-filler-text');
  if (fillerEl) { fillerEl.value = ((cfg && cfg.filler) || []).join('\n'); autoGrowFiller(); }
}
// Grow the filler textarea to show every problem (no inner scroll).
function autoGrowFiller() {
  const ta = $('anchor-filler-text');
  if (!ta) return;
  ta.style.height = 'auto';
  ta.style.height = `${ta.scrollHeight + 4}px`;
}
function autoGrowVisualFiller() {
  const ta = $('anchor-visual-filler-text');
  if (!ta) return;
  ta.style.height = 'auto';
  ta.style.height = `${ta.scrollHeight + 4}px`;
}
// Called by the loader with the file's targetedConfig (or null); refresh the prefill.
function setTargetedConfig(cfg) {
  loadedTargetedConfig = cfg || null;
  if ($('anchor-problem-list-file') && $('anchor-problem-list-file').value === TARGETED_VALUE) applyTargetedPrefill(true);
}
// Prefill the visual fields + params + filler editor from the loaded file config, else
// the per-learner code defaults. force=false won't clobber fields the coach has typed.
function applyVisualPrefill(force = false) {
  if (!force && $('anchor-vtarget-1') && $('anchor-vtarget-1').value.trim() !== '') return;
  const user = ($('anchor-username').value || '').trim();
  const cfg = loadedVisualConfig || VISUAL_DEFAULTS[user] || null;
  const targets = (cfg && cfg.targets) || [];
  VISUAL_FIELD_IDS.forEach((id, i) => { if ($(id)) $(id).value = targets[i] || ''; });
  if (cfg && cfg.fastMs != null && $('anchor-visual-fastms')) $('anchor-visual-fastms').value = cfg.fastMs;
  if (cfg && cfg.retrievalsToClear != null && $('anchor-visual-clears')) $('anchor-visual-clears').value = cfg.retrievalsToClear;
  const fillerEl = $('anchor-visual-filler-text');
  if (fillerEl) { fillerEl.value = ((cfg && cfg.filler) || []).join('\n'); autoGrowVisualFiller(); }
}
// Called by the loader with the file's visualConfig (or null); refresh the prefill.
function setVisualConfig(cfg) {
  loadedVisualConfig = cfg || null;
  if ($('anchor-problem-list-file') && $('anchor-problem-list-file').value === VISUAL_VALUE) applyVisualPrefill(true);
}
// Compact "a+b" form of one typed value, or null if it doesn't parse (for field normalize).
function factToText0(value) { const s = parseTargetSpec(value); return s ? factToText(s) : null; }
// Persist the FULL targeted config (targets + params + filler) to the per-user file right
// away on any change — so deleting/editing a target, or changing a setting, sticks
// immediately (same /api/targeted-config the prefill reads back). Needs an existing file
// (made by a quiz / Start New); for a brand-new learner the config is filed at save-run.
let targetedSaveTimer = null;
function setTargetedStatus(text) {
  for (const id of ['anchor-targeted-status', 'anchor-filler-status']) { const el = $(id); if (el) el.textContent = text; }
}
async function saveTargetedConfig() {
  const user = ($('anchor-username').value || '').trim();
  if (!user) { setTargetedStatus('Enter a name to save targeted settings.'); return; }
  const payload = {
    folder: currentFolder(), user,
    file: selectedSourceFile || loadedServerFile || undefined,
    targets: TARGETED_FIELD_IDS.map((id) => ($(id) ? $(id).value : '')),
    filler: $('anchor-filler-text') ? $('anchor-filler-text').value : undefined,
    graduationStreak: $('anchor-target-streak') ? $('anchor-target-streak').value : undefined,
    fastMs: $('anchor-target-fastms') ? $('anchor-target-fastms').value : undefined,
    percentTarget: $('anchor-target-percent') ? $('anchor-target-percent').value : undefined,
  };
  setTargetedStatus('Saving…');
  try {
    const r = await fetch('/api/targeted-config', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    const j = await r.json();
    const cfg = j.targetedConfig || {};
    setTargetedStatus(j.ok
      ? `Saved · ${(cfg.targets || []).length} target(s), ${(cfg.filler || []).length} filler.`
      : (j.message || `Save failed: ${j.error || 'error'}`));
  } catch (e) { setTargetedStatus(`Save failed: ${String(e.message || e)}`); }
}
function scheduleTargetedSave() { clearTimeout(targetedSaveTimer); targetedSaveTimer = setTimeout(saveTargetedConfig, 600); }
function flushTargetedSave() { clearTimeout(targetedSaveTimer); saveTargetedConfig(); }
let visualSaveTimer = null;
function setVisualStatus(text) {
  for (const id of ['anchor-visual-status', 'anchor-visual-filler-status']) { const el = $(id); if (el) el.textContent = text; }
}
async function saveVisualConfig() {
  const user = ($('anchor-username').value || '').trim();
  if (!user) { setVisualStatus('Enter a name to save visual settings.'); return; }
  const payload = {
    folder: currentFolder(), user,
    file: selectedSourceFile || loadedServerFile || undefined,
    targets: VISUAL_FIELD_IDS.map((id) => ($(id) ? $(id).value : '')),
    filler: $('anchor-visual-filler-text') ? $('anchor-visual-filler-text').value : undefined,
    fastMs: $('anchor-visual-fastms') ? $('anchor-visual-fastms').value : undefined,
    retrievalsToClear: $('anchor-visual-clears') ? $('anchor-visual-clears').value : undefined,
  };
  setVisualStatus('Saving…');
  try {
    const r = await fetch('/api/visual-config', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    const j = await r.json();
    const cfg = j.visualConfig || {};
    setVisualStatus(j.ok
      ? `Saved · ${(cfg.targets || []).length} target(s), ${(cfg.filler || []).length} filler.`
      : (j.message || `Save failed: ${j.error || 'error'}`));
  } catch (e) { setVisualStatus(`Save failed: ${String(e.message || e)}`); }
}
function scheduleVisualSave() { clearTimeout(visualSaveTimer); visualSaveTimer = setTimeout(saveVisualConfig, 600); }
function flushVisualSave() { clearTimeout(visualSaveTimer); saveVisualConfig(); }
// Wire the targeted setup controls so edits persist immediately (debounced; flushed on blur).
function setupTargetedAutoSave() {
  for (const id of TARGETED_FIELD_IDS) {
    const el = $(id);
    if (!el) continue;
    el.addEventListener('input', scheduleTargetedSave);
    el.addEventListener('blur', () => { const t = factToText0(el.value); if (t) el.value = t; flushTargetedSave(); });  // normalize + save
  }
  for (const id of ['anchor-target-streak', 'anchor-target-fastms', 'anchor-target-percent']) {
    const el = $(id);
    if (!el) continue;
    el.addEventListener('input', scheduleTargetedSave);   // debounced
    el.addEventListener('change', flushTargetedSave);      // commit
    el.addEventListener('blur', flushTargetedSave);        // touch devices: change can be flaky, blur isn't
  }
  const ta = $('anchor-filler-text');
  if (ta) {
    ta.addEventListener('input', () => { autoGrowFiller(); scheduleTargetedSave(); });
    ta.addEventListener('blur', flushTargetedSave);
  }
}
function setupVisualAutoSave() {
  for (const id of VISUAL_FIELD_IDS) {
    const el = $(id);
    if (!el) continue;
    el.addEventListener('input', scheduleVisualSave);
    el.addEventListener('blur', () => { const t = factToText0(el.value); if (t) el.value = t; flushVisualSave(); });  // normalize + save
  }
  for (const id of ['anchor-visual-fastms', 'anchor-visual-clears']) {
    const el = $(id);
    if (!el) continue;
    el.addEventListener('input', scheduleVisualSave);
    el.addEventListener('change', flushVisualSave);
    el.addEventListener('blur', flushVisualSave);
  }
  const ta = $('anchor-visual-filler-text');
  if (ta) {
    ta.addEventListener('input', () => { autoGrowVisualFiller(); scheduleVisualSave(); });
    ta.addEventListener('blur', flushVisualSave);
  }
}
// Streaming presentation: one problem at a time (the current target or a random
// filler). Ends only when every target has graduated.
function presentTargetedNext() {
  hide('anchor-reward-burst');                 // clear any graduation reward before the next problem
  const item = targetedRun.nextProblem();
  if (item === null) { finishTargeted(); return; }
  render(item);
  updateTargetedProgress();
}
function updateTargetedProgress() {
  const p = targetedRun.progress();
  renderTargetRings(p);
  $('anchor-progress').innerHTML = targetedProgressHtml(p);
  $('anchor-order').textContent = p.current
    ? `targeted · target ${p.current.index + 1} of ${p.totalTargets}`
    : 'targeted';
}
// Live progress text: "% of targets graduated" plus a per-target chip (streak n/N, or ✅).
function targetedProgressHtml(p) {
  const pct = Math.round(p.fraction * 100);
  const chips = p.perTarget.map((t) => {
    const face = `${t.num1} ${DISPLAY[t.operation]} ${t.num2}`;
    return t.graduated ? `<strong>${face} ✅</strong>` : `${face} ${t.streak}/${t.graduationStreak}`;
  }).join(' &nbsp; ');
  return `Targets fluent: ${p.graduatedTargets}/${p.totalTargets} · ${pct}%<br><span class="muted">${chips}</span>`;
}
// The target-rings graphic (left of the problem): graduationStreak concentric rings,
// filled OUTER-IN as the current target's fast-correct count grows (rings are kept,
// never lost): the center is
// green (the goal, filled last), the outer rings are the other colors (red -> green
// toward the center). Basic placeholder; refine the art later.
function drawTargetRings(n, filled) {
  const el = $('anchor-target-rings');
  if (!el) return;
  n = Math.max(1, n || 1);
  filled = Math.min(n, Math.max(0, filled || 0));
  const size = 92, c = size / 2, R = size / 2 - 5;
  let rings = '';
  for (let k = 1; k <= n; k++) {                      // k=1 outermost (largest), k=n innermost (center)
    const r = (R * (n - k + 1) / n).toFixed(1);       // outer first so inner rings paint on top
    const on = k <= filled;                            // fill outer-in
    const hue = n === 1 ? 120 : Math.round(120 * (k - 1) / (n - 1));   // outer=red(0) -> center=green(120)
    const color = on ? `hsl(${hue}, 85%, 47%)` : '#dcdcdc';
    const w = Math.max(3, (R / n) * 0.82).toFixed(1);
    rings += `<circle cx="${c}" cy="${c}" r="${r}" fill="none" stroke="${color}" stroke-width="${w}"/>`;
  }
  el.innerHTML = `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" role="img" aria-label="target progress ${filled} of ${n}">${rings}</svg>`;
  show('anchor-target-rings');
}
function renderTargetRings(p) {
  const el = $('anchor-target-rings');
  if (!el) return;
  const cur = p && p.current;
  if (phase !== 'targeted' || !cur) { el.innerHTML = ''; hide('anchor-target-rings'); return; }
  drawTargetRings(cur.graduationStreak, cur.streak);
}
function presentVisualNext() {
  hide('anchor-reward-burst');                 // clear any target-clear reward before the next problem
  hideVisualTrialControls();
  closeTeachPanel();
  pendingTeach = null;
  const item = visualRun.nextProblem();
  if (item === null) { finishVisual(); return; }
  render(item);
  updateVisualProgress();
  armVisualTrialControls(item);
}
function updateVisualProgress() {
  const p = visualRun.progress();
  renderVisualRings(p);
  $('anchor-progress').innerHTML = visualProgressHtml(p);
  $('anchor-order').textContent = p.current
    ? `visual · target ${p.current.index + 1} of ${p.totalTargets}`
    : 'visual';
}
function visualProgressHtml(p) {
  const chips = p.perTarget.map((t) => {
    const face = `${t.num1} ${DISPLAY[t.operation]} ${t.num2}`;
    return t.cleared ? `<strong>${face} ✅</strong>` : `${face} ${t.successes}/${p.retrievalsToClear}`;
  }).join(' &nbsp; ');
  return `Cleared ${p.clearedTargets}/${p.totalTargets}<br><span class="muted">${chips}</span>`;
}
function renderVisualRings(p) {
  const el = $('anchor-target-rings');
  if (!el) return;
  const cur = p && p.current;
  if (phase !== 'visual' || !cur) { el.innerHTML = ''; hide('anchor-target-rings'); return; }
  drawTargetRings(cur.retrievalsToClear, cur.successes);
}
function hideLightbulb() {
  hide('anchor-lightbulb');
}
function showLightbulbForItem(item) {
  (showLightbulbOnRender(item) ? show : hide)('anchor-lightbulb');
}
function showLightbulbForFlagItem(item) {
  (showLightbulbInFlagPanel(item) ? show : hide)('anchor-lightbulb');
}
function hideVisualTrialControls() {
  hideLightbulb();
}
function armVisualTrialControls(item) {
  showLightbulbForItem(item);
}
function isTeachOpen() {
  const panel = $('anchor-teach');
  return !!(teachContext && panel && !panel.classList.contains('hidden'));
}
function openTeach(item, context = 'help') {
  if (!teachableProblem(item)) return false;
  if (visualMode) {
    const attempt = context === 'review' ? correctionProblem : sessionProblems[sessionProblems.length - 1];
    if (attempt && attempt.visual_practice
        && attempt.fact_key === (item.targetKey || item.key)) {
      attempt.visual_practice.visual_shown = true;
    }
  }
  hideVisualTrialControls();
  clearFeedback();
  if (context === 'help') {
    hide('anchor-correction');
    resetCorrectionUi();
  }
  submitting = true;             // freeze input while the visual is open
  teachContext = context;
  teachItem = item;
  teachTargetKey = item.targetKey || (phase === 'visual' ? item.key : null);
  teachState = tenFrameTeachStates(item.num1, item.num2);
  $('anchor-teach-visual').innerHTML = `<div id="anchor-teach-setup">${teachState.setupSvg}</div>`;
  hide('anchor-teach-done');
  hide('anchor-quiz-main');
  hide('anchor-keypad');
  show('anchor-teach');
  if (teachRevealTimer) clearTimeout(teachRevealTimer);
  if (TEACH_HOLD_MS <= 0) revealTeachResult();
  else teachRevealTimer = setTimeout(revealTeachResult, TEACH_HOLD_MS);
  return true;
}
function revealTeachResult() {
  teachRevealTimer = null;
  if (!teachState || $('anchor-teach-result')) return;
  // The setup line gains its answer ("8 + 3 = 11") as the make-ten result appears below.
  const setup = $('anchor-teach-setup');
  if (setup) setup.innerHTML = teachState.setupAnswerSvg;
  $('anchor-teach-visual').insertAdjacentHTML(
    'beforeend',
    `<div class="anchor-teach-divider"></div><div id="anchor-teach-result">${teachState.resultSvg}</div>`,
  );
  if (teachContext !== 'wrong') show('anchor-teach-done');
}
function closeTeachPanel({ restoreReviewLightbulb = false } = {}) {
  const wasReview = teachContext === 'review';
  if (teachRevealTimer) clearTimeout(teachRevealTimer);
  teachRevealTimer = null;
  hide('anchor-teach');
  $('anchor-teach-visual').innerHTML = '';
  hide('anchor-teach-done');
  show('anchor-quiz-main');
  show('anchor-keypad');
  teachState = null;
  teachItem = null;
  teachTargetKey = null;
  teachContext = null;
  if (restoreReviewLightbulb && wasReview && correctionLightbulbItem) {
    showLightbulbForFlagItem(correctionLightbulbItem);
  }
}
function onTeachDone() {
  const context = teachContext;
  const item = teachItem;
  const targetKey = teachTargetKey;
  if (!context) return;
  if (context === 'review') {
    closeTeachPanel({ restoreReviewLightbulb: true });
    return;
  }
  if (context === 'wrong') return;
  if (phase === 'visual' && visualRun && targetKey) {
    visualRun.teachShown(targetKey);
  } else if (phase === 'predictive' && !problemListConfig && run && run.insert) {
    run.insert(INSERT_GAP);
  } else if (phase === 'targeted' && item) {
    insertTargetedRedeliver(item, INSERT_GAP);
  }
  pendingTeach = null;
  closeTeachPanel();
  advance();
}
// Celebrate a graduation: confetti + the math-quiz "correct" sound + a right-side
// animation. Fires only on hitting a target; the reward stays up until the learner
// taps Continue. `isCompletion` true => the graduation that finished the whole
// session, so show the completion animation instead of the per-target one.
// The reward images are local-only assets (gitignored): if the file isn't present
// the image load fails and we show NOTHING (no broken image, no placeholder) —
// confetti + sound still play.
function celebrateTarget(isCompletion = false) {
  if (typeof confetti !== 'undefined') { try { confetti({ particleCount: 100, spread: 70, origin: { y: 0.6 } }); } catch { /* ignore */ } }
  const audio = $('correct-sound');
  if (audio) { try { audio.currentTime = 0; audio.play().catch(() => {}); } catch { /* ignore */ } }
  const burst = $('anchor-reward-burst');
  if (!burst) return;
  burst.innerHTML = '';
  hide('anchor-reward-burst');            // stay hidden unless the asset actually loads
  const cfg = targetedStart || visualStart || {};
  const image = isCompletion
    ? (cfg.completionImage || TARGETED_COMPLETION_FALLBACK)
    : (cfg.rewardImage || TARGETED_REWARD_FALLBACK);
  if (!image) return;
  const img = new Image();               // load it first; only reveal it if it exists
  img.alt = 'reward';
  img.style.maxWidth = '140px';
  img.style.maxHeight = '160px';
  img.onload = () => {
    if (img.naturalWidth === 0) return;  // decoded but empty -> treat as missing
    burst.innerHTML = '';
    burst.appendChild(img);
    show('anchor-reward-burst');
  };
  img.onerror = () => { /* missing/failed asset: show nothing */ };
  img.src = image;
}
// After a target graduates (rings full + confetti + sound), pause on a Continue button
// below the problem so the learner moves on when ready, rather than auto-advancing.
function showGraduationContinue(goal = null) {
  const n = goal || targetedRun.progress().graduationStreak;
  drawTargetRings(n, n);        // show the just-graduated target's rings fully filled (green center)
  show('anchor-grad-continue');
}
function onGraduationContinue() {
  hide('anchor-grad-continue');
  advance();                    // -> presentTargetedNext (next target's problem, or finish)
}

// ----- pause -----
// Pause hides the current problem and offers: Continue (same problem) or Continue & skip
// (targeted: discard the current problem) / Continue & insert (assess: re-ask it later).
function onPause() {
  if (!(phase === 'targeted' || phase === 'visual' || phase === 'predictive' || phase === 'thorough')) return;
  if (!currentItem || submitting || correctionMode !== null || isTeachOpen()) return;
  submitting = true;            // freeze input while paused
  clearFeedback();
  hideVisualTrialControls();
  hideQuiz();
  const skipBtn = $('anchor-pause-skip');
  if (skipBtn) skipBtn.textContent = (phase === 'targeted' || phase === 'visual') ? 'Continue & skip' : 'Continue & insert';
  show('anchor-pause-panel');
}
function onPauseContinue() {
  hide('anchor-pause-panel');
  showQuiz();
  render(currentItem);          // same problem, fresh timer (render resets submitting + shownAt)
  if (phase === 'targeted') updateTargetedProgress();
  if (phase === 'visual') { updateVisualProgress(); armVisualTrialControls(currentItem); }
}
function onPauseSkip() {
  hide('anchor-pause-panel');
  showQuiz();
  if (phase === 'targeted') { presentTargetedNext(); return; }              // discard the current problem
  if (phase === 'visual') { presentVisualNext(); return; }                  // discard the current problem
  if (phase === 'predictive' && run && run.insert) run.insert(INSERT_GAP);  // re-ask the current one later
  advance();
}

// ----- Go gate: keypad visible, learner taps Go before the first quiz problem -----
function showGoGate() {
  currentItem = null;
  clearFeedback();
  hide('anchor-correction');
  resetCorrectionUi();
  hideVisualTrialControls();
  closeTeachPanel();
  $('anchor-problem').textContent = '\u00a0';   // invisible placeholder — reserves the line, no layout jump at Go
  $('anchor-order').textContent = '';
  $('anchor-progress').textContent = '';
  $('anchor-answer').value = '';
  showQuiz();
  hide('anchor-enter');
  show('anchor-go-overlay');
}
function onGoClick() {
  hide('anchor-go-overlay');
  startTime = timestamp();
  startMs = performance.now();   // total time measures the quiz, not warm-up or the Go pause
  (autoSubmit ? hide : show)('anchor-enter');
  if (phase === 'visual') presentVisualNext();
  else if (phase === 'targeted') presentTargetedNext();
  else presentNext();
}

// ----- warm-up: practice entering numbers on the keypad -----
const PRACTICE_FIRST = [3, 8, 6, 12, 19, 15]; // round 1 fixed; later rounds random
function randomPracticeRound() {
  const single = () => Math.floor(Math.random() * 10);       // 0–9
  const two = () => 10 + Math.floor(Math.random() * 90);     // 10–99
  return [single(), single(), single(), two(), two(), two()];
}
function startPractice() {
  phase = 'practice';
  practiceQueue = [...PRACTICE_FIRST];
  practiceIdx = 0;
  practiceRound = 1;
  practiceLog = [];
  setPhaseControls('practice');
  hide('anchor-practice-done');
  showQuiz();
  presentPractice();
}
function presentPractice() {
  clearFeedback();
  if (practiceIdx >= practiceQueue.length) { hideQuiz(); show('anchor-practice-done'); return; }
  practiceTarget = practiceQueue[practiceIdx];
  $('anchor-problem').textContent = String(practiceTarget);
  $('anchor-order').textContent = '';
  $('anchor-progress').textContent = `Warm-up — tap this number (${practiceIdx + 1} of ${practiceQueue.length})`;
  const a = $('anchor-answer'); a.value = ''; a.focus();
  submitting = false;
  shownAt = performance.now();
}
function onPracticeAnswer() {
  const raw = $('anchor-answer').value;
  if (raw === '') return;
  const entered = Number(raw);
  const isCorrect = entered === practiceTarget;
  // Log every warm-up entry (correct and wrong) — stored separately from problems.
  practiceLog.push({ round: practiceRound, target: practiceTarget, entered, isCorrect, responseTime: performance.now() - shownAt });
  if (isCorrect) {
    submitting = true;
    showFeedback(true);
    practiceIdx++;
    if (feedbackMs > 0) setTimeout(presentPractice, feedbackMs); else presentPractice();
  } else {
    showFeedback(false);            // wrong: clear and let them try the same number again
    $('anchor-answer').value = '';
    shownAt = performance.now();    // time the retry fresh
  }
}
function onPracticeContinue() {
  practiceQueue = randomPracticeRound();
  practiceIdx = 0;
  practiceRound += 1;
  hide('anchor-practice-done');
  setPhaseControls('practice');
  showQuiz();
  presentPractice();
}

function render(item) {
  currentItem = item;
  showLightbulbForItem(item);
  $('anchor-problem').textContent = `${item.num1} ${DISPLAY[item.operation]} ${item.num2}`;
  // Bottom indicator: HF/EF for auto mode, or the list kind for a list run.
  if (orderJustTransitioned) { $('anchor-order').textContent = 'HF→EF'; orderJustTransitioned = false; }
  else $('anchor-order').textContent = orderLabel();
  const a = $('anchor-answer');
  a.value = '';
  a.focus();
  submitting = false;
  shownAt = performance.now();
  shownAtWall = new Date().toISOString();   // wall-clock present time for this problem
  hide('anchor-correction');               // a fresh problem starts with no flag panel
  resetCorrectionUi();
}
// Bottom-of-quiz mode label. Auto runs show the hard/easy order; list runs name the source.
function orderLabel() {
  if (problemListConfig) {
    const kind = problemListConfig.internalProblemListId != null ? 'internal list' : 'external list';
    return problemListConfig.randomize ? `${kind} - random` : kind;
  }
  return orderMode;   // 'HF' | 'EF'
}
// Total problems in the run = the planned presentation count (the run's sequence). Grows to
// the answered count if an explicit "Continue & insert" re-asks beyond the plan, so the
// progress never reads "N of fewer-than-N" or over 100%.
function runTotal() {
  const planned = (run && run.sequence) ? run.sequence.length
    : (problemListConfig ? problemListConfig.sequence.length : (factMatrix ? factMatrix.size : 0));
  return Math.max(planned, sessionProblems.length);
}

function presentNext() {
  const key = run.next();
  if (key === null) { onPlanComplete(); return; }
  render(run.currentItem());
  const total = runTotal();
  const pct = total ? Math.min(100, Math.round((sessionProblems.length / total) * 100)) : 0;
  $('anchor-progress').textContent = `${sessionProblems.length} of ${total} answered · ${pct}% complete`;
}

function presentThoroughNext() {
  const key = thoroughRun.next();
  if (key === null) { finishThorough(); return; }
  render({ key, ...parseKey(key) });
  const r = thoroughRun.result();
  $('anchor-progress').textContent = `Covering the rest · ${r.certified}/${r.total} certified`;
}

function recordProblem(item, userValue, isCorrect, rt, flags = [], opts = {}) {
  const entry = {
    id: `${startTime}-${sessionProblems.length}`,
    fact_key: item.key,
    problem_text: `${item.num1} ${item.operation} ${item.num2}`,
    correct_answer: answerFor(item.operation, item.num1, item.num2),
    user_answer_string: userValue === null ? '' : String(userValue),
    user_answer: userValue,
    is_correct: isCorrect,
    response_time_ms: Math.round(rt),
    presented_at: shownAtWall,
    flags,
  };
  if (targetedMode && targetedRun) {
    const p = targetedRun.progress();
    const targetIndex = p.perTarget.findIndex((t) => t.key === item.key);
    entry.targeted_practice = {
      role: item.role || (targetIndex >= 0 ? 'target' : 'filler'),
      target_key: targetIndex >= 0 ? item.key : null,
      current_target_key: p.current ? p.current.key : null,
      target_order: targetIndex >= 0 ? targetIndex + 1 : null,
      fast_correct: targetIndex >= 0 && isCorrect && rt <= targetedStart.fastMs,
    };
  }
  if (visualMode && visualRun) {
    entry.visual_practice = {
      trial_role: item.role || (item.targetKey ? 'delayed-retrieval' : 'filler'),
      target_key: item.targetKey || null,
      visual_shown: false,
      passed: !!opts.visualPassed,
    };
  }
  sessionProblems.push(entry);
}

function showFeedback(isCorrect) {
  const f = $('anchor-feedback');
  if (!isCorrect) { clearFeedback(); return; }
  f.textContent = '✓';
  f.className = 'correct';
}
function clearFeedback() { const f = $('anchor-feedback'); f.textContent = ''; f.className = ''; }

function resetCorrectionUi() {
  correctionProblem = null;
  correctionMode = null;
  prevFlagItem = null;
  correctionLightbulbItem = null;
  hide('anchor-correction-answer');
  hide('anchor-flag-menu');
  $('anchor-correction-answer').textContent = '';
}
function advance() {
  clearFeedback();
  closeTeachPanel();
  hide('anchor-correction');
  resetCorrectionUi();
  if (phase === 'thorough') presentThoroughNext();
  else if (phase === 'targeted') presentTargetedNext();
  else if (phase === 'visual') presentVisualNext();
  else presentNext();
}

// Record one response (a typed answer or a Skip) and move on, with the brief
// feedback flash and the realism guardrail check. When the wrong-answer
// correction flow is on (CORRECTION_FLOW), a wrong typed answer pauses instead of
// auto-advancing: the correct answer stays up with Flag / Continue / Continue&insert.
function submitResponse(userValue, isCorrect, rt, flags, opts = {}) {
  // Wrong typed answers pause on the correction flow (show the correct answer + Flag /
  // Continue / Continue & insert) except visual target trials, which open the teach panel.
  const visualTargetTrial = phase === 'visual' && currentItem && currentItem.targetKey;
  const pause = CORRECTION_FLOW && !isCorrect && !opts.skip && !visualTargetTrial;
  hideVisualTrialControls();
  recordProblem(currentItem, userValue, isCorrect, rt, flags, { visualPassed: !!opts.visualPassed });
  if (phase === 'predictive') {
    // noRecheck: in the correction flow the controller drives re-asks (Continue&insert),
    // so the engine counts the miss now instead of auto-scheduling a glitch re-ask.
    run.record(currentItem.key, { isCorrect, responseTime: rt }, { noRecheck: pause });
    maybeRevertToEasy(isCorrect, rt);
  } else if (phase === 'thorough') {
    thoroughRun.record(currentItem.key, { isCorrect, responseTime: rt });
  } else if (phase === 'targeted') {
    const res = targetedRun.record(currentItem, { isCorrect, responseTime: rt });
    if (res.graduated) {                          // confetti + sound only when a target is hit
      const p = targetedRun.progress();
      const sessionComplete = p.graduatedTargets >= p.totalTargets;   // last target just graduated
      celebrateTarget(sessionComplete);           // completion animation on the final graduation
      targetedGraduationPending = true;
    }
  } else if (phase === 'visual') {
    const res = visualRun.record(currentItem, { isCorrect, responseTime: rt, passed: !!opts.visualPassed });
    if (res.needsTeach && openTeach(currentItem, 'help')) return;
    if (res.cleared) {
      celebrateTarget(res.sessionComplete);
      visualClearPending = true;
    }
  }

  // Keep the full entered number visible; flash a ✓ on correct, then advance fast.
  showFeedback(isCorrect);

  // Realism guardrail: too many slow/missed easy facts → suggest ending (once).
  // Gated by the setup switch (default OFF); detection code below is untouched.
  if (phase === 'predictive' && guardrailEnabled && !guardrailShown) {
    const a = run.anomaly();
    if (a) {
      guardrailShown = true;
      if (feedbackMs > 0) setTimeout(() => showGuardrail(a), feedbackMs);
      else showGuardrail(a);
      return;
    }
  }

  // Wrong-answer correction flow: pause and wait for the user's choice (Continue advances).
  if (pause) {
    showCorrectionPanel('answer', { showAnswer: true });
    if (phase !== 'visual' && autoTeachOnWrong(currentItem)) openTeach(currentItem, 'wrong');
    return;
  }

  // Targeted graduation: after the reward, wait on the Continue button instead of auto-advancing.
  if (phase === 'targeted' && targetedGraduationPending) {
    targetedGraduationPending = false;
    if (feedbackMs > 0) setTimeout(showGraduationContinue, feedbackMs);
    else showGraduationContinue();
    return;
  }
  if (phase === 'visual' && visualClearPending) {
    visualClearPending = false;
    const goal = visualStart ? visualStart.retrievalsToClear : VISUAL_CLEARS;
    if (feedbackMs > 0) setTimeout(() => showGraduationContinue(goal), feedbackMs);
    else showGraduationContinue(goal);
    return;
  }

  if (feedbackMs > 0) setTimeout(advance, feedbackMs);
  else advance();
}

// ----- flag / continue panel -----
// One panel drives three triggers: a wrong answer, "Skip & flag", and "Flag previous".
// It shows (optionally) the correct-answer line, the flag reasons, and Continue /
// Continue & insert (always available). `mode` decides what Continue does ('answer'
// advances; 'previous' returns to the on-screen problem). openFlags shows the reasons
// inline; defaultReason pre-checks one (e.g. 'skip-noreason' for a reasonless skip).
function showCorrectionPanel(mode, { showAnswer = false, openFlags = false, defaultReason = null, problem = null, lightbulbItem = null } = {}) {
  correctionMode = mode;
  correctionProblem = problem || sessionProblems[sessionProblems.length - 1] || null;
  correctionLightbulbItem = lightbulbItem && showLightbulbInFlagPanel(lightbulbItem) ? lightbulbItem : null;
  if (showAnswer && correctionProblem) {
    $('anchor-correction-answer').textContent = `Correct answer: ${correctionProblem.correct_answer}`;
    show('anchor-correction-answer');
  } else {
    $('anchor-correction-answer').textContent = '';
    hide('anchor-correction-answer');
  }
  // Reflect any existing flags in the checkboxes; pre-check the default reason if asked.
  const existing = (correctionProblem && correctionProblem.flags) || [];
  const reasons = new Set(existing.map((f) => f.reason));
  if (defaultReason) reasons.add(defaultReason);
  for (const cb of $('anchor-flag-reasons').querySelectorAll('input[type=checkbox]')) cb.checked = reasons.has(cb.value);
  $('anchor-flag-comment').value = existing.length ? (existing[0].notes || '') : '';
  if (defaultReason) syncCorrectionFlags();   // record the default flag right away
  if (openFlags) { show('anchor-flag-menu'); hide('anchor-correct-flag'); }
  else { hide('anchor-flag-menu'); show('anchor-correct-flag'); }
  show('anchor-correct-continue');
  show('anchor-correct-insert');
  show('anchor-correction');
  if (correctionLightbulbItem) showLightbulbForFlagItem(correctionLightbulbItem);
  else hideLightbulb();
}
function dismissFlagMenu() {
  const menu = $('anchor-flag-menu');
  if (menu.classList.contains('hidden')) return;
  syncCorrectionFlags();
  hide('anchor-flag-menu');
}
function onCorrectContinue() {
  dismissFlagMenu();                                   // persist any flags from the menu
  if (isTeachOpen()) closeTeachPanel();
  if (correctionMode === 'previous') { resumeCurrentAfterFlag(); return; }
  if (phase === 'visual' && pendingTeach) { openTeach(pendingTeach); return; }
  advance();
}
function onCorrectInsert() {
  dismissFlagMenu();
  if (isTeachOpen()) closeTeachPanel();
  // Re-ask the flagged problem INSERT_GAP problems later (or flushed at the end). The
  // predictive assess run has a re-deliver queue; targeted practice re-inserts into the
  // current burst; thorough/other phases just Continue.
  if (correctionMode === 'previous') {
    if (phase === 'predictive' && run && run.insertItem && prevFlagItem) run.insertItem(prevFlagItem, INSERT_GAP);
    else if (phase === 'targeted' && prevFlagItem) insertTargetedRedeliver(prevFlagItem, INSERT_GAP);
    else if (phase === 'visual' && prevFlagItem) insertVisualRedeliver(prevFlagItem, INSERT_GAP);
    resumeCurrentAfterFlag();
    return;
  }
  if (phase === 'predictive' && run && run.insert) run.insert(INSERT_GAP);
  else if (phase === 'targeted' && currentItem) insertTargetedRedeliver(currentItem, INSERT_GAP);  // "Continue & insert" on a skip
  else if (phase === 'visual' && currentItem) insertVisualRedeliver(currentItem, INSERT_GAP);
  if (phase === 'visual' && pendingTeach) { openTeach(pendingTeach); return; }
  advance();
}
// Re-ask one problem ~gap problems later in the targeted stream (the targeted analog of
// the assess run's insert queue). A re-asked target still advances its streak via record().
function insertTargetedRedeliver(item, gap = INSERT_GAP) {
  if (!targetedRun || !item || item.num1 == null) return;
  const isTarget = targetedRun.targets.some((t) => t.key === item.key);
  targetedRun.requeue({ key: item.key, num1: item.num1, num2: item.num2, operation: item.operation, role: isTarget ? 'target' : 'filler' }, gap);
}
function insertVisualRedeliver(item, gap = INSERT_GAP) {
  if (!visualRun || !item || item.num1 == null) return;
  const isTarget = visualRun.targets.some((t) => t.key === item.key);
  visualRun.requeue({
    key: item.key,
    num1: item.num1,
    num2: item.num2,
    operation: item.operation,
    role: item.role || (isTarget ? 'delayed-retrieval' : 'filler'),
    targetKey: isTarget ? item.key : null,
  }, gap);
}
// "Flag previous": after annotating the prior problem, re-present the on-screen problem
// (do NOT advance) so the learner answers it next as if nothing changed. render() restores
// its text + answer box + focus and clears the flag panel.
function resumeCurrentAfterFlag() {
  render(currentItem);
  if (phase === 'targeted') updateTargetedProgress();
  if (phase === 'visual') { updateVisualProgress(); armVisualTrialControls(currentItem); }
}
// Build the flag reason checkboxes once (same reasons as the session-list editor).
function buildFlagMenu() {
  const box = $('anchor-flag-reasons');
  box.innerHTML = '';
  for (const [reason, label] of Object.entries(FLAG_REASON_LABELS)) {
    const lab = document.createElement('label');
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.value = reason;
    cb.addEventListener('change', syncCorrectionFlags);
    lab.appendChild(cb);
    lab.appendChild(document.createTextNode(' ' + label));
    box.appendChild(lab);
  }
}
// Mirror the session-list editor's shape: { reason, label, timestamp, notes }.
function syncCorrectionFlags() {
  if (!correctionProblem) return;
  const checked = [...$('anchor-flag-reasons').querySelectorAll('input[type=checkbox]:checked')].map((cb) => cb.value);
  const notes = ($('anchor-flag-comment').value || '').trim();
  const stamp = new Date().toISOString();
  let flags = checked.map((reason) => ({ reason, label: FLAG_REASON_LABELS[reason] || reason, timestamp: stamp, notes }));
  if (!flags.length && notes) flags = [{ reason: 'other', label: FLAG_REASON_LABELS.other, timestamp: stamp, notes }];
  correctionProblem.flags = flags;
}
function lightbulbFlag() {
  return { reason: 'lightbulb', label: FLAG_REASON_LABELS.lightbulb, timestamp: new Date().toISOString(), notes: '' };
}
function onFlagCommentInput() {
  if ($('anchor-flag-reasons').querySelector('input[type=checkbox]:checked')) syncCorrectionFlags();
}
// "⚑ Flag" (the wrong-answer case): reveal the reason checkboxes inline, pre-filled from
// any flags already on this problem. Continue / Continue & insert are already visible.
function onCorrectFlag(e) {
  if (e) e.stopPropagation();
  if (!correctionProblem) return;
  const existing = correctionProblem.flags || [];
  const reasons = new Set(existing.map((f) => f.reason));
  for (const cb of $('anchor-flag-reasons').querySelectorAll('input[type=checkbox]')) cb.checked = reasons.has(cb.value);
  $('anchor-flag-comment').value = existing.length ? (existing[0].notes || '') : '';
  show('anchor-flag-menu');
  hide('anchor-correct-flag');
}

function onAnswer() {
  if (submitting) return;
  if (phase === 'practice') { onPracticeAnswer(); return; }
  if (!currentItem) return;
  const raw = $('anchor-answer').value;
  if (raw === '') return;
  submitting = true;
  const userValue = Number(raw);
  const rt = performance.now() - shownAt;           // captured before any feedback
  const isCorrect = userValue === answerFor(currentItem.operation, currentItem.num1, currentItem.num2);
  submitResponse(userValue, isCorrect, rt, []);
}

// Auto-revert: if hard-first and the learner is struggling (wrong/skip, or slower
// than several seconds), switch the remaining facts to easy-first.
function maybeRevertToEasy(isCorrect, rt) {
  if (!orderHardFirst || !autoRevert || reverted) return;
  if (!isCorrect || rt > REVERT_SLOW_MS) struggleCount++;
  if (struggleCount >= REVERT_THRESHOLD) {
    run.reorderRemaining((it) => (EASY_RANK[it.category] ?? 5));
    orderMode = 'EF';
    reverted = true;
    orderJustTransitioned = true;
  }
}

// "Skip & flag": the learner didn't answer (user_answer = NA). Counts as not-known
// (incorrect), then opens the flag panel exactly like a wrong answer — with the correct
// answer shown and the reasons open, defaulting to "Skip - no reason" so a reasonless
// skip is still recorded. Continue advances; Continue & insert re-asks it later.
function onSkipFlag() {
  if (!currentItem || submitting || correctionMode !== null) return;
  submitting = true;
  hideVisualTrialControls();
  const rt = performance.now() - shownAt;
  recordProblem(currentItem, null, false, rt, []);   // NA answer; flags set by the panel default
  if (phase === 'predictive') {
    run.record(currentItem.key, { isCorrect: false, responseTime: rt }, { noRecheck: true });
    maybeRevertToEasy(false, rt);
  } else if (phase === 'thorough') {
    thoroughRun.record(currentItem.key, { isCorrect: false, responseTime: rt });
  } else if (phase === 'targeted') {
    targetedRun.record(currentItem, { isCorrect: false, responseTime: rt });  // skip breaks the streak
  } else if (phase === 'visual') {
    const res = visualRun.record(currentItem, { isCorrect: false, responseTime: rt });
    pendingTeach = res.needsTeach ? currentItem : null;
  }
  showCorrectionPanel('answer', { showAnswer: true, openFlags: true, defaultReason: 'skip-noreason', lightbulbItem: currentItem });
}

function onLightbulb() {
  if (correctionMode !== null) {
    if (!correctionLightbulbItem || !showLightbulbInFlagPanel(correctionLightbulbItem) || isTeachOpen()) return;
    openTeach(correctionLightbulbItem, 'review');
    return;
  }
  if (!currentItem || submitting || !showLightbulbOnRender(currentItem)) return;
  submitting = true;
  hideVisualTrialControls();
  const rt = performance.now() - shownAt;
  if (phase === 'visual') {
    recordProblem(currentItem, null, false, rt, [], { visualPassed: true });
    visualRun.record(currentItem, { isCorrect: false, responseTime: rt, passed: true });
    openTeach(currentItem, 'help');
    return;
  }
  recordProblem(currentItem, null, false, rt, [lightbulbFlag()]);
  if (phase === 'predictive') {
    run.record(currentItem.key, { isCorrect: false, responseTime: rt }, { noRecheck: true });
  } else if (phase === 'thorough') {
    thoroughRun.record(currentItem.key, { isCorrect: false, responseTime: rt });
  } else if (phase === 'targeted') {
    targetedRun.record(currentItem, { isCorrect: false, responseTime: rt });
  }
  openTeach(currentItem, 'help');
}

// "Flag previous": annotate the PREVIOUS (already-answered) problem without losing the
// one on screen. Shows that problem's correct answer (if it was wrong) and the flag
// choices; Continue returns to the current problem, Continue & insert also re-asks the
// previous fact later.
function onFlagPrevious() {
  if (correctionMode !== null || !currentItem || submitting) return;   // a panel is open / not awaiting an answer
  const prev = sessionProblems[sessionProblems.length - 1];
  if (!prev) return;                                                   // nothing answered yet
  submitting = true;                                                   // block answering while the panel is open
  hideVisualTrialControls();
  // Re-deliver the prior fact in its ORIGINAL orientation (from problem_text), not the
  // canonical fact_key order, so a re-asked "1 + 8" doesn't flip to "8 + 1".
  const [a, op, b] = String(prev.problem_text).split(' ');
  prevFlagItem = { key: prev.fact_key, operation: op, num1: Number(a), num2: Number(b) };
  // Rewind the DISPLAY to the prior problem: show its text + the answer the learner entered
  // (empty for a skip). Continue re-presents the current problem (resumeCurrentAfterFlag).
  $('anchor-problem').textContent = `${prevFlagItem.num1} ${DISPLAY[prevFlagItem.operation]} ${prevFlagItem.num2}`;
  $('anchor-answer').value = prev.user_answer_string || '';
  showCorrectionPanel('previous', { showAnswer: !prev.is_correct, openFlags: true, problem: prev, lightbulbItem: prevFlagItem });
}

function showGuardrail(a) {
  clearFeedback();
  hideQuiz();
  const facts = a.facts.map((k) => { const { operation, num1, num2 } = parseKey(k); return `${num1} ${DISPLAY[operation]} ${num2}`; });
  $('anchor-guardrail-text').textContent =
    `Something looks off — several of the easier problems (${facts.join(', ')}) are coming back slow. ` +
    `That's usually a technical glitch or a distraction rather than a real result. We suggest ending this session and starting fresh.`;
  show('anchor-guardrail');
}
function onGuardrailEnd() {
  anomalyHit = 'slow-on-easy';
  finalize('anomaly-stopped', '', []);
}
function onGuardrailContinue() {
  hide('anchor-guardrail');
  showQuiz();
  presentNext(); // guardrailShown stays true, so it won't nag again this run
}

// Digit count of the current correct answer / of what's been entered.
const digitCount = (val) => String(Math.abs(Math.round(val))).replace(/[^0-9]/g, '').length;
const enteredDigits = () => ($('anchor-answer').value || '').replace(/[^0-9]/g, '').length;

// Auto-submit once the entry has at least as many digits as the correct answer.
// Single-digit answers (and single-press value keys) submit on one entry; two-
// digit answers (e.g. multiplication 8×9=72) need two key presses.
function expectedAnswer() {
  if (phase === 'practice') return practiceTarget;
  return currentItem ? answerFor(currentItem.operation, currentItem.num1, currentItem.num2) : null;
}
function maybeAutoSubmit() {
  if (!autoSubmit || submitting) return;
  const ans = expectedAnswer();
  if (ans === null || ans === undefined) return;
  if (enteredDigits() > 0 && enteredDigits() >= digitCount(ans)) onAnswer();
}
function onInput() { maybeAutoSubmit(); }

// ----- on-screen calculator keypad -----
// Standard calculator block (7 8 9 / 4 5 6 / 1 2 3) with a bottom row of
// ± (sign toggle) / 0 / C (clear all). There is no Enter key on the keypad:
// auto-submit is the norm, and when it's off the Enter button below the problem
// box submits instead. Optional "big number keys" stack extra rows above for the
// two-digit sums; off by default (no setup checkbox); ?bigkeys=1 to enable (e2e/dev).
// Value keys >= 10 are whole answers (submit on one press); digit keys 0–9 build
// a number, so multiplication answers > 9 take two presses.
const STD_ROWS = [[7, 8, 9], [4, 5, 6], [1, 2, 3], ['negate', 0, 'clear']];
const TEEN_ROWS = [[19, 20, 21], [16, 17, 18], [13, 14, 15], [10, 11, 12]];
function pressKey(token) {
  if (submitting) return;
  if (phase !== 'practice' && !currentItem) return;
  const input = $('anchor-answer');
  if (token === 'clear') { input.value = ''; return; }   // C: erase everything
  if (token === 'negate') {   // ±: toggle the negative sign on the current entry
    if (input.value.startsWith('-')) input.value = input.value.slice(1);
    else if (input.value !== '') input.value = '-' + input.value;   // (type=number rejects a lone '-')
    maybeAutoSubmit();
    return;
  }
  if (token === 'enter') { onAnswer(); return; }
  if (token >= 10) { input.value = String(token); if (autoSubmit) onAnswer(); return; } // whole-answer key
  input.value += String(token);
  maybeAutoSubmit();
}
function buildKeypad(showBigKeys) {
  const pad = $('anchor-keypad');
  pad.innerHTML = '';
  const rows = showBigKeys ? [...TEEN_ROWS, ...STD_ROWS] : STD_ROWS;
  for (const row of rows) {
    for (const token of row) {
      const b = document.createElement('button');
      b.type = 'button';
      b.dataset.key = String(token);
      b.textContent = token === 'clear' ? 'C' : token === 'negate' ? '±' : token === 'enter' ? '↵' : String(token);
      if (token === 'clear' || token === 'enter' || token === 'negate') b.classList.add('op');
      else if (token >= 10) b.classList.add('big');
      b.addEventListener('click', () => pressKey(token));
      pad.appendChild(b);
    }
  }
}

function onPlanComplete() {
  const res = run.result();
  // Problem lists (internal/external, fluency feast, quick quiz) finish with a plain summary —
  // the continue/stop predictive-mastery prompt is auto-mode only.
  if (problemListConfig) { finishProblemList(res); return; }
  if (res.status === 'predictive-mastery') {
    if (continueIfFluent) { startThorough(); return; }
    hideQuiz();
    const pct = Math.round(res.coverage * 100);
    const glitchNote = res.glitches > 0 ? ` (${res.glitches} momentary slip${res.glitches === 1 ? '' : 's'} ignored)` : '';
    $('anchor-prompt-text').textContent =
      `It looks like you're fluent — demonstrated reliably on ${pct}% of the facts (${res.sampled} of ${res.total})${glitchNote}. Continue to 100% coverage, or stop here?`;
    show('anchor-prompt');
  } else {
    finishNotFluent(res);
  }
}
async function finishProblemList(res) {
  if (res.status === 'predictive-mastery') {
    const name = problemListConfig.sourceName || 'problem list';
    const correct = sessionProblems.filter((p) => p.is_correct).length;
    const total = sessionProblems.length;
    await finalize('list-complete', `Finished ${name} — ${correct} of ${total} correct.`, []);
    return;
  }
  finishNotFluent(res);
}

function startThorough() {
  phase = 'thorough';
  // Glitch-tolerant: re-ask every fact not yet answered fast+correct (incl. ones
  // that were slow in the assess phase), giving each a clean retry before flagging.
  thoroughRun = createThoroughRun(factMatrix, { fastMs: FAST_MS, priorAttempts: attemptsByFact(sessionProblems) });
  hide('anchor-prompt');
  showQuiz();
  presentThoroughNext();
}

function attemptsByFact(problems) {
  const m = new Map();
  for (const p of problems) {
    const key = p.fact_key || (() => {
      const parts = p.problem_text.split(' ');
      return canonicalKey(parts[1], Number(parts[0]), Number(parts[2]));
    })();
    const a = m.get(key) || [];
    a.push({ isCorrect: p.is_correct, responseTime: p.response_time_ms });
    m.set(key, a);
  }
  return m;
}

async function finishStop() {
  const res = run.result();
  await finalize('predictive-mastery', `Fluency demonstrated on a ${Math.round(res.coverage * 100)}% sample.`, []);
}

async function finishThorough() {
  const res = thoroughRun.result();
  if (res.passes) { await finalize('thorough-mastery', '', []); return; }
  const weak = res.needsWork.map((w) => { const { operation, num1, num2 } = parseKey(w.key); return `${num1} ${DISPLAY[operation]} ${num2}`; });
  await finalize('incomplete', '', weak);
}

function finishNotFluent(res) {
  hideQuiz();
  const weak = (res.confirmedWeak || []).map((k) => { const { operation, num1, num2 } = parseKey(k); return `${num1} ${DISPLAY[operation]} ${num2}`; });
  return finalize('weak-facts-found', `Not fully fluent yet — ${weak.length} fact(s) to practice.`, weak);
}

// Targeted practice has its own conclusion + summary (the assess `finalize` is
// built around the predictive/thorough run.result()). Reuses the same save path
// (per-user store + per-run .sqlite + dev-server filing) and the summary card.
function finishTargeted() { return finalizeTargeted(); }
async function finalizeTargeted(kindOverride) {
  const meta = targetedRun.metadata();
  const allDone = meta.completionReason === 'all-graduated';
  const kind = kindOverride || (allDone ? 'targeted-complete' : 'targeted-partial');
  const sessionJson = buildSessionJson(kind);
  const elapsedMs = performance.now() - startMs;

  const initialFluencyPct = await anchorFluencyPercentNow();
  const writer = createSessionWriter({
    mode: WRITE_MODE,
    writeSqlite: async (s) => { store.ingest(s); store.recordWarmup(practiceLog, s.session.id); await store.save(); },
    writeJson: (s) => downloadJson(s),
  });
  try {
    await writer.writeSession(sessionJson, `anchor_${username}_${startTime}.json`);
    await savePerRunFile(sessionJson);
  } catch (e) { console.error('save failed', e); }
  const finalFluencyPct = await anchorFluencyPercentNow();

  hideQuiz(); hide('anchor-pause-panel'); hide('anchor-target-rings'); hide('anchor-reward-burst'); hide('anchor-grad-continue');
  hideVisualTrialControls(); closeTeachPanel();
  const graduated = meta.graduated.length;
  const total = meta.targetCount;
  $('anchor-summary-title').textContent = allDone ? 'Targets fluent ✅' : 'Good practice 💪';
  const faces = meta.perTarget.map((t) => {
    const { operation, num1, num2 } = parseKey(t.key);
    return `${num1} ${DISPLAY[operation]} ${num2}${t.graduated ? ' ✅' : ` (${t.fastCorrect} fast)`}`;
  });
  const headline = allDone
    ? `All ${total} target problem${total === 1 ? '' : 's'} reached fluency — ${meta.graduationStreak} fast-correct each.`
    : `${graduated} of ${total} target problem${total === 1 ? '' : 's'} reached fluency in ${meta.burstsDelivered} burst${meta.burstsDelivered === 1 ? '' : 's'}.`;
  $('anchor-summary-body').innerHTML =
    `${headline}<br>Total time: ${fmtDuration(elapsedMs)}<br><span class="muted">${escapeHtml(faces.join('   '))}</span>`;
  $('anchor-weak').textContent = '';
  renderFluencyReadout(initialFluencyPct, finalFluencyPct);
  $('anchor-file-info').textContent = '';
  show('anchor-summary');

  hide('anchor-retry-upload');
  if (lastRunBytes) await runUpload();
  else { $('anchor-upload').textContent = 'Saved in this browser only (no dev server to write the file).'; hideDevTools(); }
}

function finishVisual() { return finalizeVisual(); }
async function finalizeVisual(kindOverride) {
  const meta = visualRun.metadata();
  const allDone = meta.completionReason === 'all-cleared';
  const kind = kindOverride || (allDone ? 'visual-complete' : 'visual-partial');
  const sessionJson = buildSessionJson(kind);
  const elapsedMs = performance.now() - startMs;

  const initialFluencyPct = await anchorFluencyPercentNow();
  const writer = createSessionWriter({
    mode: WRITE_MODE,
    writeSqlite: async (s) => { store.ingest(s); store.recordWarmup(practiceLog, s.session.id); await store.save(); },
    writeJson: (s) => downloadJson(s),
  });
  try {
    await writer.writeSession(sessionJson, `anchor_${username}_${startTime}.json`);
    await savePerRunFile(sessionJson);
  } catch (e) { console.error('save failed', e); }
  const finalFluencyPct = await anchorFluencyPercentNow();

  hideQuiz(); hide('anchor-pause-panel'); hide('anchor-target-rings'); hide('anchor-reward-burst'); hide('anchor-grad-continue');
  hideVisualTrialControls(); closeTeachPanel();
  const cleared = meta.cleared.length;
  const total = meta.targetCount;
  const lines = meta.perTarget.map((t) => {
    const face = `${t.num1} ${DISPLAY[t.operation]} ${t.num2}`;
    const cold = t.coldProbe || 'not tried';
    const teaches = `${t.teachCount} teach${t.teachCount === 1 ? '' : 'es'}`;
    const retrievals = `${t.retrievalSuccesses}/${meta.retrievalsToClear} retrievals${t.cleared ? ' ✅' : ''}`;
    return `${face} — cold: ${cold} · ${teaches} · ${retrievals}`;
  });
  $('anchor-summary-title').textContent = 'Pictures practiced 🖼️';
  $('anchor-summary-body').innerHTML =
    `${cleared} of ${total} picture target${total === 1 ? '' : 's'} cleared.<br>Total time: ${fmtDuration(elapsedMs)}<br>`
    + `<span class="muted">${lines.map(escapeHtml).join('<br>')}</span>`;
  $('anchor-weak').textContent = '';
  renderFluencyReadout(initialFluencyPct, finalFluencyPct);
  $('anchor-file-info').textContent = '';
  show('anchor-summary');

  hide('anchor-retry-upload');
  if (lastRunBytes) await runUpload();
  else { $('anchor-upload').textContent = 'Saved in this browser only (no dev server to write the file).'; hideDevTools(); }
}

function buildSessionJson(kind) {
  const correct = sessionProblems.filter((p) => p.is_correct).length;
  const avg = sessionProblems.length ? Math.round(sessionProblems.reduce((s, p) => s + p.response_time_ms, 0) / sessionProblems.length) : 0;
  const noteSuffix = problemListConfig
    ? `;problem-list:${problemListConfig.sourceName};replicates:${problemListConfig.replicates};randomize:${problemListConfig.randomize ? 1 : 0}`
    : '';
  const modeName = visualMode ? 'visual-practice' : (targetedMode ? 'targeted-practice' : (problemListConfig ? 'problem-list' : 'assess'));
  const settings = {
    preset: visualMode ? 'anchor-visual' : (targetedMode ? 'anchor-targeted' : (problemListConfig ? 'anchor-problem-list' : 'anchor')),
    note: `mode:${modeName};outcome:${kind}${anomalyHit ? ';anomaly:' + anomalyHit : ''}${noteSuffix}`,
    session_type: modeName,
    num_problems: sessionProblems.length,
    number_range: RANGE,
    numbers_include: [],
    numbers_exclude: [],
    num_numbers: 2,
    operations,
    source_folder: sourceFolder,                            // local _data/ source folder
    destination: destination,                               // 'source' (accumulate) | 'test' (trial)
    test_description: destination === 'test' ? testDescription : '',
  };
  if (problemListConfig) {
    settings.problem_list_metadata = {
      source: problemListConfig.sourcePath,
      source_name: problemListConfig.sourceName,
      base_count: problemListConfig.baseCount,
      replicates: problemListConfig.replicates,
      randomize: problemListConfig.randomize,
    };
  }
  // Targeted-practice metadata persisted into the session (SPEC §6/§8): targets,
  // burst/streak config, graduation outcome, per-target streak/attempt tallies.
  if (targetedMode && targetedRun) settings.targeted_practice_metadata = targetedRun.metadata();
  if (visualMode && visualRun) settings.visual_practice_metadata = visualRun.metadata();
  return {
    version: '1.1',
    user: { name: username },
    session: {
      id: (crypto.randomUUID && crypto.randomUUID()) || `${startTime}-${Math.random().toString(16).slice(2)}`,
      start_time: startTime,
      end_time: timestamp(),
      settings,
      summary: { total_problems: sessionProblems.length, correct_answers: correct, average_response_time_ms: avg },
      problems: sessionProblems,
    },
  };
}

// Save this run as its OWN SQLite file (separate per run) in IndexedDB, and keep
// its bytes for the Download button.
async function savePerRunFile(sessionJson) {
  lastRunFilename = `math-flu_${username}_${startTime}.sqlite`;
  const runStore = await openUserStore({ username: lastRunFilename, deps: storeDeps(), persistence: createIndexedDbPersistence({ dbName: RUN_DB }) });
  runStore.logModeEvent({
    to: (targetedMode || visualMode) ? 'practice' : 'assess',
    trigger: visualMode ? 'visual-anchor-run' : (targetedMode ? 'targeted-anchor-run' : 'anchor-run'),
    sessionId: sessionJson.session.id,
  });
  runStore.ingest(sessionJson, lastRunFilename);
  runStore.recordWarmup(practiceLog, sessionJson.session.id);
  await runStore.save();
  lastRunBytes = runStore.exportBytes();
  runStore.close();
}

async function finalize(kind, body, weak) {
  const sessionJson = buildSessionJson(kind);
  const elapsedMs = performance.now() - startMs;

  // Fluency entering this quiz, read before the session is written into the store. Read here
  // (regardless of mode) so the summary can show start → end below.
  const initialFluencyPct = await anchorFluencyPercentNow();

  // Cumulative per-user store (write-mode switch: sqlite-only by default).
  const writer = createSessionWriter({
    mode: WRITE_MODE,
    writeSqlite: async (s) => { store.ingest(s); store.recordWarmup(practiceLog, s.session.id); await store.save(); },
    writeJson: (s) => downloadJson(s),
  });
  try {
    await writer.writeSession(sessionJson, `anchor_${username}_${startTime}.json`);
    await savePerRunFile(sessionJson);
  } catch (e) { console.error('save failed', e); }

  // Fluency after this quiz's results are recorded (store.db now includes this session).
  const finalFluencyPct = await anchorFluencyPercentNow();

  hideQuiz(); hide('anchor-prompt'); hide('anchor-guardrail');
  hideVisualTrialControls(); closeTeachPanel();
  const titles = { 'predictive-mastery': 'Fluent ✅', 'thorough-mastery': 'Fully certified ✅', 'list-complete': 'Done ✅', incomplete: 'Nearly there', 'weak-facts-found': 'Some facts to practice', 'quit-saved': 'Saved (partial)', 'anomaly-stopped': 'Session ended (unusual pattern)' };
  $('anchor-summary-title').textContent = titles[kind] || 'Done';

  const res = run.result();
  const pct = Math.round((res.coverage || 0) * 100);
  const slips = res.glitches || 0;
  const problems = sessionProblems.length;
  const opLabel = operations.length === 1 ? { '+': 'addition', '-': 'subtraction', '*': 'multiplication' }[operations[0]] : 'arithmetic';
  let headline, note;
  if (kind === 'predictive-mastery') {
    headline = `Fluency demonstrated on ${pct}% coverage — you answered ${res.sampled} of ${res.total} single-digit ${opLabel} facts fast and correct (the rest are inferred).`;
    note = `${problems} problems in all. ${slips} momentary slip${slips === 1 ? '' : 's'} (a slow or mistyped first try) ${slips === 1 ? 'was' : 'were'} re-asked and cleared — slips don't count against fluency.`;
  } else if (kind === 'thorough-mastery') {
    headline = `100% certified — every single-digit ${opLabel} fact answered correctly and fast.`;
    note = `${problems} problems in all (slow first tries were re-asked and cleared).`;
  } else if (kind === 'incomplete') {
    const n = (weak || []).length;
    headline = `Almost there — ${res.sampled} of ${res.total} facts are certified fluent; ${n} still ${n === 1 ? 'comes' : 'come'} in over ${FAST_MS / 1000}s even after a re-try.`;
    note = `Those ${n === 1 ? 'one is' : 'ones are'} correct, just not yet automatic — good targets for a little practice.`;
  } else if (kind === 'quit-saved') {
    headline = `Saved this session early (${problems} problems answered).`;
    note = `Quit & save — the partial session was stored.`;
  } else if (kind === 'anomaly-stopped') {
    headline = `Ended early — several easy facts came back slow, which usually means a glitch or distraction, not a real result.`;
    note = `Flagged anomaly:slow-on-easy. Saved with the marker so it's visible to whatever evaluates this run. Try a fresh session.`;
  } else {
    headline = body;
    note = `${problems} problems in all.`;
  }
  $('anchor-summary-body').innerHTML = `${headline}<br>Total time: ${fmtDuration(elapsedMs)}<br><span class="muted">${note}</span>`;
  $('anchor-weak').textContent = weak && weak.length ? `Still slow: ${weak.join('   ')}` : '';
  renderFluencyReadout(initialFluencyPct, finalFluencyPct);
  $('anchor-file-info').textContent = '';   // set from the server's singleSessionPath after the save
  console.log('[anchor] saved session', lastRunFilename, '— IndexedDB db', RUN_DB, '; cumulative store db', USER_DB, 'key', username);
  show('anchor-summary');

  // Save to the local _data/ folder via the dev-server sidecar.
  hide('anchor-retry-upload');
  if (lastRunBytes) await runUpload();
  else {
    $('anchor-upload').textContent = 'Saved in this browser only (no dev server to write the file).';
    hideDevTools();
  }
}

function downloadBytes(bytes, filename, type) {
  const blob = new Blob([bytes], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click(); a.remove();
  URL.revokeObjectURL(url);
}
function downloadJson(sessionJson) { downloadBytes(JSON.stringify(sessionJson, null, 2), `anchor_${username}_${startTime}.json`, 'application/json'); }

// Dev helpers: quit early. "Save" finalizes + files the partial run; "Abandon" saves nothing and dumps dev
// info. (Dev-mode UI — to be hidden/logged for real users later.)
async function onQuitSave() {
  if (submitting) return;
  if (!window.confirm('Quit now and save your progress so far?')) return;
  submitting = true;
  hideVisualTrialControls();
  closeTeachPanel();
  if (visualMode) { await finalizeVisual('visual-partial'); return; }
  if (targetedMode) { await finalizeTargeted('targeted-partial'); return; }
  await finalize('quit-saved', '', []);
}
function onQuitAbandon() {
  if (!window.confirm('Quit and discard this session? Nothing will be saved.')) return;
  const r = run ? run.result() : {};
  const s = run ? run.stats() : {};
  hideQuiz(); hide('anchor-prompt');
  hideVisualTrialControls(); closeTeachPanel();
  $('anchor-summary-title').textContent = 'Abandoned (not saved)';
  $('anchor-summary-body').innerHTML =
    `Session abandoned — nothing saved.<br>Total time: ${fmtDuration(performance.now() - startMs)}` +
    `<br><span class="muted">${sessionProblems.length} answered · status ${r.status || '—'} · ${JSON.stringify(s)}</span>`;
  $('anchor-weak').textContent = '';
  renderFluencyReadout(null, null);   // nothing saved — no start→end readout
  $('anchor-file-info').textContent = '';
  $('anchor-upload').textContent = '';
  hide('anchor-retry-upload');
  show('anchor-summary');
}

// Show returning users a quick note once they enter a name they've used before.
async function checkReturning() {
  const name = ($('anchor-username').value || '').trim();
  if (!name) { hide('anchor-returning'); return; }
  try {
    await ensureSql();
    const probe = await openUserStore({ username: name, deps: storeDeps(), persistence: createIndexedDbPersistence({ dbName: USER_DB }) });
    const n = probe.sessionCount();
    probe.close();
    if (n > 0) { $('anchor-returning').textContent = `Welcome back — ${n} previous session(s) on this device.`; show('anchor-returning'); }
    else hide('anchor-returning');
  } catch { /* ignore probe errors */ }
}

// ----- name entry: auto-load the learner's latest file (Continue latest) -----
// On name blur/Enter (or folder/mode change), pull the most-recent per-person DB from
// the dev server and make it this browser's working copy, so a returning learner just
// picks their name and continues their one file. The dev-server file is the source of
// truth (SPEC §8); the browser cache is a read-back, overwritten on each load. With no
// dev server we fall back to this device's IndexedDB (checkReturning). "Start new file"
// skips the load and tells the server to file a fresh lineage (forceNew on save).
let loadedServerFile = null;   // filename last hydrated from the server (display only)
let lastLoadFound = null;      // true/false from the last Continue lookup; null = Start New / unknown

// The Source folder field shows a path like "_data/TL kids"; the dev server resolves source
// folders under its local _data/, so send just the final path segment (the folder name).
function currentFolder() {
  const raw = $('anchor-source-folder') ? $('anchor-source-folder').value : '';
  const seg = String(raw).replace(/[\\/]+$/, '').split(/[\\/]/).pop();
  return (seg || 'real').trim();
}
const CLONE_TARGET_USERS = ['Randy', 'Tester', 'TL'];
const CLONE_FOLDER = 'tlkids';
const CLONE_DEFAULT_SOURCE = 'Kid1';
let cachedFolderUsers = [];
let usernameMenuOpen = false;
let usernameMenuShowAll = false;
function currentUsername() { return ($('anchor-username').value || '').trim(); }
function folderUserName(entry) {
  if (entry && typeof entry === 'object') return String(entry.name || '').trim();
  return String(entry || '').trim();
}
function isKnownFolderUser(name) {
  const n = String(name || '').trim().toLowerCase();
  if (!n) return false;
  return cachedFolderUsers.some((u) => folderUserName(u).toLowerCase() === n);
}
function canonicalFolderUser(name) {
  const n = String(name || '').trim().toLowerCase();
  if (!n) return '';
  const hit = cachedFolderUsers.find((u) => folderUserName(u).toLowerCase() === n);
  return hit ? folderUserName(hit) : String(name).trim();
}
async function loadFolderUsers() {
  try {
    const resp = await fetch(`/api/folder-users?folder=${encodeURIComponent(currentFolder())}`);
    const j = await resp.json();
    if (j && j.ok && Array.isArray(j.users)) {
      const names = [...new Set(j.users.map(folderUserName).filter(Boolean))];
      cachedFolderUsers = names.sort((a, b) => a.localeCompare(b));
      return cachedFolderUsers;
    }
  } catch { /* dev server unreachable */ }
  return cachedFolderUsers;
}
function renderUsernameMenuItems(showAll) {
  const menu = $('anchor-username-menu');
  if (!menu) return;
  if (!cachedFolderUsers.length) {
    menu.innerHTML = '<li class="muted">No learners in this folder (is the dev server running?)</li>';
    return;
  }
  const query = (currentUsername() || '').trim().toLowerCase();
  let users = cachedFolderUsers;
  if (!showAll && query) {
    users = users.filter((u) => folderUserName(u).toLowerCase().startsWith(query));
  }
  if (!users.length) {
    menu.innerHTML = '<li class="muted">No matches</li>';
    return;
  }
  menu.innerHTML = users.map((u) => {
    const name = folderUserName(u);
    return `<li role="option" data-user="${escapeHtml(name)}">${escapeHtml(name)}</li>`;
  }).join('');
}
function showUsernameMenuLoading() {
  const menu = $('anchor-username-menu');
  if (menu) menu.innerHTML = '<li class="muted">Loading learners…</li>';
}
async function ensureFolderUsersLoaded() {
  if (cachedFolderUsers.length) return cachedFolderUsers;
  showUsernameMenuLoading();
  return loadFolderUsers();
}
function openUsernameMenu(showAll = false) {
  const menu = $('anchor-username-menu');
  const inp = $('anchor-username');
  if (!menu || !inp) return;
  usernameMenuOpen = true;
  usernameMenuShowAll = showAll;
  renderUsernameMenuItems(showAll);
  menu.classList.remove('hidden');
  inp.setAttribute('aria-expanded', 'true');
}
function closeUsernameMenu() {
  const menu = $('anchor-username-menu');
  const inp = $('anchor-username');
  usernameMenuOpen = false;
  if (menu) menu.classList.add('hidden');
  if (inp) inp.setAttribute('aria-expanded', 'false');
}
async function pickUsernameFromMenu(name) {
  if (!name) return;
  $('anchor-username').value = name;
  closeUsernameMenu();
  const cont = $('anchor-mode-continue');
  if (cont && isKnownFolderUser(name)) cont.checked = true;
  $('anchor-error').textContent = '';
  await refreshNameStatus();
  if (listPanel) listPanel.refresh();
}
function eventTargetElement(e) {
  const t = e.target;
  if (t instanceof Element) return t;
  if (t && t.parentElement instanceof Element) return t.parentElement;
  return null;
}
function setupUsernameCombobox() {
  const box = document.querySelector('.anchor-name-combobox');
  const inp = $('anchor-username');
  const toggle = $('anchor-username-toggle');
  const menu = $('anchor-username-menu');
  if (!box || !inp || !toggle || !menu) return;
  inp.addEventListener('focus', () => {
    inp.removeAttribute('readonly');
    if (!cachedFolderUsers.length) loadFolderUsers();
  });
  async function openAllMenu() {
    const inpEl = $('anchor-username');
    const menuEl = $('anchor-username-menu');
    usernameMenuOpen = true;
    usernameMenuShowAll = true;
    if (menuEl) menuEl.classList.remove('hidden');
    if (inpEl) inpEl.setAttribute('aria-expanded', 'true');
    await ensureFolderUsersLoaded();
    if (usernameMenuOpen) renderUsernameMenuItems(true);
  }
  async function openFilteredMenu() {
    const inpEl = $('anchor-username');
    const menuEl = $('anchor-username-menu');
    usernameMenuOpen = true;
    usernameMenuShowAll = false;
    if (menuEl) menuEl.classList.remove('hidden');
    if (inpEl) inpEl.setAttribute('aria-expanded', 'true');
    await ensureFolderUsersLoaded();
    if (usernameMenuOpen) renderUsernameMenuItems(false);
  }
  toggle.addEventListener('pointerdown', (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (usernameMenuOpen && usernameMenuShowAll) closeUsernameMenu();
    else void openAllMenu();
  });
  inp.addEventListener('input', () => { void openFilteredMenu(); });
  menu.addEventListener('mousedown', (e) => e.preventDefault());
  box.addEventListener('click', (e) => {
    const el = eventTargetElement(e);
    const li = el && el.closest('li[data-user]');
    if (li) {
      e.preventDefault();
      void pickUsernameFromMenu(li.getAttribute('data-user'));
    }
  });
  document.addEventListener('pointerdown', (e) => {
    const el = eventTargetElement(e);
    if (el && el.closest('.anchor-name-combobox')) return;
    closeUsernameMenu();
  }, true);
  inp.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') { closeUsernameMenu(); return; }
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      void openAllMenu();
      return;
    }
    if (e.key === 'Enter') { e.preventDefault(); closeUsernameMenu(); inp.blur(); }
  });
}
async function refreshUsernamePicker() {
  await loadFolderUsers();
  if (usernameMenuOpen) renderUsernameMenuItems(usernameMenuShowAll);
}
function forceStartNewFileMode() {
  const neu = $('anchor-mode-new');
  if (neu) neu.checked = true;
}
function applyUsernameModeRules() {
  const name = currentUsername();
  const cont = $('anchor-mode-continue');
  if (!name) {
    if (cont) cont.disabled = false;
    return;
  }
  if (isKnownFolderUser(name)) {
    if (cont) cont.disabled = false;
    return;
  }
  forceStartNewFileMode();
  if (cont) cont.disabled = true;
}
// Tester personas + Randy in tlkids, source destination, Continue latest: clone from another learner.
function isCloneTargetUi() {
  const name = currentUsername().toLowerCase();
  return CLONE_TARGET_USERS.some((u) => u.toLowerCase() === name)
    && currentDestination() === 'source'
    && currentFolder().toLowerCase() === CLONE_FOLDER
    && currentSourceMode() === 'continue';
}
async function refreshCloneFromDropdown() {
  const row = $('anchor-clone-from-row');
  const sel = $('anchor-clone-from');
  const preview = $('anchor-clone-preview');
  const status = $('anchor-clone-status');
  if (!row || !sel) return;
  if (!isCloneTargetUi()) {
    row.classList.add('hidden');
    if (preview) preview.classList.add('hidden');
    if (status) { status.classList.add('hidden'); status.textContent = ''; }
    return;
  }
  row.classList.remove('hidden');
  const prev = sel.value;
  const users = cachedFolderUsers.length ? cachedFolderUsers : await loadFolderUsers();
  const me = currentUsername().toLowerCase();
  const others = users.filter((u) => String(u).toLowerCase() !== me);
  sel.innerHTML = others.map((u) => `<option value="${escapeHtml(u)}">${escapeHtml(u)}</option>`).join('');
  const defaultPick = others.includes(CLONE_DEFAULT_SOURCE) ? CLONE_DEFAULT_SOURCE : (others[0] || '');
  if (prev && others.includes(prev)) sel.value = prev;
  else if (defaultPick) sel.value = defaultPick;
  await refreshClonePreview();
}
async function refreshClonePreview() {
  const preview = $('anchor-clone-preview');
  if (!preview) return;
  if (!isCloneTargetUi()) { preview.classList.add('hidden'); return; }
  const sourceUser = ($('anchor-clone-from') && $('anchor-clone-from').value) || '';
  if (!sourceUser) { preview.classList.add('hidden'); return; }
  preview.classList.remove('hidden');
  preview.textContent = 'Clone …';
  const folder = currentFolder();
  const targetUser = currentUsername();
  let sourceFile = '(no file)';
  let targetFile = '(no file yet)';
  try {
    const [srcRes, tgtRes] = await Promise.all([
      loadLatestUserDb({ folder, user: sourceUser }),
      loadLatestUserDb({ folder, user: targetUser }),
    ]);
    if (srcRes.found && srcRes.filename) sourceFile = srcRes.filename;
    if (tgtRes.found && tgtRes.filename) targetFile = tgtRes.filename;
  } catch { /* offline */ }
  preview.textContent = `Clone ${sourceFile} → ${targetFile}`;
}
async function cloneFromSelectedUser() {
  const sel = $('anchor-clone-from');
  const source = (sel && sel.value) || '';
  if (!source || !isCloneTargetUi()) return { ok: false, error: 'pick a learner to clone from' };
  const target = currentUsername();
  try {
    const resp = await fetch('/api/clone-user-file', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ folder: currentFolder(), sourceUser: source, targetUser: target }),
    });
    const j = await resp.json();
    if (!j || !j.ok) return { ok: false, error: (j && j.error) || 'clone failed' };
    // Mirror the dragon game's browser save so Clone also picks up world progress
    // (boulders, signs, nest) — same keys as dragon/sim/game_state.js.
    try {
      const sourceKey = `dragon-game::${source}`;
      const targetKey = `dragon-game::${target}`;
      const raw = localStorage.getItem(sourceKey);
      if (!raw) localStorage.removeItem(targetKey);
      else {
        const data = JSON.parse(raw);
        data.learner = target;
        localStorage.setItem(targetKey, JSON.stringify(data));
      }
    } catch { /* game save is best-effort */ }
    return { ok: true, source, sourceFile: j.source_file, newFile: j.new_file, deleted: j.deleted || [] };
  } catch (e) {
    return { ok: false, error: String(e.message || e) };
  }
}
async function onCloneRun() {
  $('anchor-error').textContent = '';
  const statusEl = $('anchor-clone-status');
  if (statusEl) { statusEl.classList.remove('hidden'); statusEl.style.color = ''; statusEl.textContent = 'Cloning…'; }
  const result = await cloneFromSelectedUser();
  if (!result.ok) {
    if (statusEl) { statusEl.textContent = result.error; statusEl.style.color = '#c62828'; }
    return;
  }
  if (statusEl) {
    statusEl.textContent = `Cloned ${result.sourceFile || result.source} → ${result.newFile}`;
    statusEl.style.color = '#2e7d32';
  }
  await refreshNameStatus();
  await refreshClonePreview();
}
function currentDestination() { return $('anchor-destination') ? $('anchor-destination').value : 'source'; }
function currentSourceMode() {
  const r = document.querySelector('input[name="anchor-source-mode"]:checked');
  return r ? r.value : 'continue';
}
function setNameStatus(text, isError = false) {
  const el = $('anchor-name-status');
  if (!el) return;
  el.textContent = text;
  el.style.color = isError ? '#c62828' : '';
}

// The test-description row shows only when the destination is the test folder; otherwise
// just refresh the source-file lookup.
function updateFolderUi() {
  const row = $('anchor-test-description-row');
  if (row) row.style.display = currentDestination() === 'test' ? '' : 'none';
  refreshUsernamePicker().then(() => refreshCloneFromDropdown()).then(() => refreshNameStatus());
}

// "Select source folder" — open the OS folder picker and put the chosen folder in the field.
// The browser only exposes the folder's name (not its full path), and the dev server reads
// source folders under its local _data/, so we store it as "_data/<name>".
async function onSelectSourceFolder() {
  const field = $('anchor-source-folder');
  if (!field) return;
  if (!window.showDirectoryPicker) {
    setNameStatus('This browser can’t open a folder picker — type the source folder path instead.', true);
    return;
  }
  try {
    const handle = await window.showDirectoryPicker();
    field.value = `_data/${handle.name}`;
    updateFolderUi();
  } catch { /* picker cancelled */ }
}

async function refreshNameStatus() {
  let name = ($('anchor-username').value || '').trim();
  loadedServerFile = null;
  lastLoadFound = null;
  if (!name) {
    setNameStatus('');
    hide('anchor-returning');
    setInternalLists([]);
    setVisualConfig(null);
    loadedQuickPractice = {};
    applyUsernameModeRules();
    await refreshCloneFromDropdown();
    return;
  }
  if (!cachedFolderUsers.length) await loadFolderUsers();
  const canonical = canonicalFolderUser(name);
  if (canonical && canonical !== name) {
    $('anchor-username').value = canonical;
    name = canonical;
  }
  applyUsernameModeRules();
  if (!isKnownFolderUser(name)) {
    forceStartNewFileMode();
    setNameStatus(`"${name}" is not in "${currentFolder()}" — will start a new file.`);
    hide('anchor-returning');
    setInternalLists([]);
    setTargetedConfig(null);
    setVisualConfig(null);
    loadedFluencyFeast = null;
    loadedProfile = null;
    loadedQuickPractice = {};
    syncFluencyPercentCheckbox();
    await refreshCloneFromDropdown();
    return;
  }
  if (currentSourceMode() === 'new') {
    // Start New begins a fresh lineage, so the existing file's internal lists don't apply.
    setNameStatus(`Start new — a fresh file will be created for "${name}" in "${currentFolder()}".`);
    hide('anchor-returning');
    setInternalLists([]);
    setTargetedConfig(null);   // prefill targeted fields from code defaults for this learner
    setVisualConfig(null);     // prefill visual fields from code defaults for this learner
    loadedQuickPractice = {};  // no accumulated fluency yet on a brand-new file
    await refreshCloneFromDropdown();
    return;
  }
  setNameStatus(`Looking up ${name}'s latest file in "${currentFolder()}"…`);
  const res = await loadLatestUserDb({
    folder: currentFolder(), user: name,
    file: selectedSourceFile || undefined,
  });
  if (res.ok && res.found) {
    try {
      // Prefer the server's file, but never replace a newer local copy with a stale
      // fetch (cached latest-user-db after a quiz save was wiping the just-saved session
      // and the next quiz's start→end % looked like the prior baseline again).
      const persistence = createIndexedDbPersistence({ dbName: USER_DB });
      const localBytes = await persistence.load(name);
      let localSessionCount = 0;
      if (localBytes) {
        try {
          await ensureSql();
          const tmp = new SQL.Database(localBytes);
          localSessionCount = countSessions(tmp, name);
          if (typeof tmp.close === 'function') tmp.close();
        } catch { localSessionCount = 0; }
      }
      const pick = chooseHydrationBytes({
        serverBytes: res.bytes,
        serverSessionCount: res.sessionCount,
        localBytes,
        localSessionCount,
      });
      if (pick.bytes) await persistence.save(name, pick.bytes);
      loadedServerFile = res.filename;
      lastLoadFound = true;
      const n = pick.sessionCount || (res.sessionCount == null ? '?' : res.sessionCount);
      const keptLocal = pick.source === 'local-newer'
        ? ' (kept newer browser copy — server response looked behind)'
        : '';
      setNameStatus(`Continuing ${res.filename} — ${n} prior session(s)${keptLocal}. New quizzes add to this file.`);
      hide('anchor-returning');
    } catch (e) {
      setNameStatus(`Loaded ${res.filename}, but could not cache it locally (${String(e.message || e)}).`, true);
    }
    setInternalLists(res.problemLists || []);   // surface the learner's stored lists ("Use internal")
    setTargetedConfig(res.targetedConfig || null);
    setVisualConfig(res.visualConfig || null);
    loadedFluencyFeast = res.fluencyFeast || null;   // per-file feast preset (falls back to defaults)
    loadedProfile = res.profile || null;             // per-file profile flags (e.g. showFluencyPercent)
    loadedQuickPractice = res.quickPractice || {};   // auto-generated quick-quiz sets for the kid modal
    syncFluencyPercentCheckbox();
    await refreshCloneFromDropdown();
    return;
  }
  setInternalLists([]);
  setTargetedConfig(null);
  setVisualConfig(null);
  loadedFluencyFeast = null;
  loadedProfile = null;
  loadedQuickPractice = {};
  syncFluencyPercentCheckbox();
  if (res.ok && !res.found) {
    // Continue latest needs an existing file — surface it as an error (not a silent "new").
    lastLoadFound = false;
    setNameStatus(`No file for "${name}" in source folder "${currentFolder()}" to continue. `
      + `Pick "Start new file" to begin one, or choose a different source folder.`, true);
    hide('anchor-returning');
    await refreshCloneFromDropdown();
    return;
  }
  // No dev server reachable — fall back to whatever this device has saved.
  setNameStatus(`Dev server not reachable — using this device's saved data for "${name}".`);
  checkReturning();
  await refreshCloneFromDropdown();
}

// Update the cached internal lists and re-render the display box + the "Use internal" option,
// and keep the (open) editor panel in sync with the current learner/folder.
function setInternalLists(lists) {
  internalLists = Array.isArray(lists) ? lists : [];
  renderInternalLists();
  refreshListPanel();
}
function renderInternalLists() {
  const box = $('anchor-internal-lists');
  const select = $('anchor-problem-list-file');
  const opt = select ? [...select.options].find((o) => o.value === INTERNAL_LIST_VALUE) : null;
  const count = internalLists.length;
  if (opt) {
    opt.disabled = count === 0;
    opt.textContent = count ? `Use internal (${count} in this file)` : 'Use internal (none in this file)';
  }
  // If "Use internal" was selected but the current file has none, fall back to Auto.
  if (select && select.value === INTERNAL_LIST_VALUE && count === 0) {
    select.value = '';
    onProblemListSelectionChange();
  } else if (select && count > 0) {
    // Default to the learner's internal queue when lists exist (unless a .txt list is chosen).
    const cur = select.value;
    if (cur === '' || cur === INTERNAL_LIST_VALUE) {
      select.value = INTERNAL_LIST_VALUE;
      onProblemListSelectionChange();
    }
  }
  if (!box) return;
  if (count === 0) { box.innerHTML = ''; hide('anchor-internal-lists'); return; }
  const rows = internalLists.map((l, i) => {
    const n = l.item_count != null ? l.item_count : (l.items ? l.items.length : 0);
    const keep = Number(l.retain) ? 'keep' : 'consume after use';
    const used = l.times_used ? ` · used ${l.times_used}×` : '';
    const next = i === 0 ? ' <strong>◀ runs next</strong>' : '';
    return `<li>#${l.list_order} ${escapeHtml(l.list_name)} — ${n} problem${n === 1 ? '' : 's'} · ${keep}${used}${next}</li>`;
  }).join('');
  box.innerHTML = `<div style="font-weight:600">Internal problem lists in this file (${count}):</div>`
    + `<ul style="margin:6px 0 0;padding-left:18px">${rows}</ul>`;
  show('anchor-internal-lists');
}
// The hard-first / auto-revert / continue-if-fluent controls only apply to the Auto problem
// source; hide them when a problem-list file is chosen.
function updateAutoOnlyControls() {
  const box = $('anchor-auto-only');
  if (box) box.style.display = $('anchor-problem-list-file').value ? 'none' : '';
}
function onProblemListSelectionChange() {
  updateProblemListControlState();
  updateAutoOnlyControls();
  const select = $('anchor-problem-list-file');
  const status = $('anchor-problem-list-status');
  // Targeted/visual practice show their own config (target fields + filler editor); reveal/hide here.
  const targetedSel = select.value === TARGETED_VALUE;
  const visualSel = select.value === VISUAL_VALUE;
  if ($('anchor-targeted-config')) (targetedSel ? show : hide)('anchor-targeted-config');
  if ($('anchor-filler-editor')) (targetedSel ? show : hide)('anchor-filler-editor');
  if ($('anchor-visual-config')) (visualSel ? show : hide)('anchor-visual-config');
  if ($('anchor-visual-filler-editor')) (visualSel ? show : hide)('anchor-visual-filler-editor');
  if (targetedSel) {
    applyTargetedPrefill(false);   // seed fields/filler from the file config or code defaults
    status.textContent = '';       // the targeted-config box already explains it
    return;
  }
  if (visualSel) {
    applyVisualPrefill(false);     // seed fields/filler from the file config or code defaults
    status.textContent = '';       // the visual-config box already explains it
    return;
  }
  // Count discoverable .txt lists only — exclude the "Auto", "Use internal", and practice sentinels.
  const available = [...select.options].filter((o) => o.value && o.value !== INTERNAL_LIST_VALUE && o.value !== TARGETED_VALUE && o.value !== VISUAL_VALUE).length;
  if (!select.value) {
    status.textContent = available > 0
      ? `Found ${available} problem-list file${available === 1 ? '' : 's'}.`
      : 'No .txt files discovered in problem-lists/. Using default adaptive plan.';
    return;
  }
  if (select.value === INTERNAL_LIST_VALUE) {
    const top = internalLists[0];
    status.textContent = top
      ? `Using internal list #${top.list_order}: ${top.list_name} (runs next; ${top.item_count != null ? top.item_count : (top.items ? top.items.length : 0)} problems).`
      : 'No internal problem lists in this file.';
    return;
  }
  const label = select.options[select.selectedIndex] ? select.options[select.selectedIndex].textContent : select.value;
  status.textContent = `Using list: ${label}`;
}

// ----- kid landing: name buttons from the source folder's SQLite files, then a mode pop-up -----
// The default view is a clean landing (big name buttons) so a learner can land on the iPad and
// just pick themselves. Names come from /api/folder-users for the active source folder
// (the Source folder field — default `_data/tlkids`). When a name isn't unique in that folder,
// the button label includes the file date. "Other…" reveals the full setup card; ?setup=1
// skips the landing entirely (used by the operator and e2e tests). Picking a name Continues
// that learner's file, then the pop-up starts Targeted practice / Problem list / etc. —
// or says to ask Baba if that mode isn't set up in their file.
//
// Randy / Tester get a non-blocking clone panel first: keep the name buttons clickable to
// pick who to clone from, or "Continue with my file" to skip cloning. Clone copies that
// learner's latest .sqlite and renames the user everywhere inside (see /api/clone-user-file).
const CLONE_LANDING_USERS = ['Randy', 'Tester'];
let selectedSourceFile = null;   // exact top-level filename selected on the landing (kept through save)
let landingCloneTarget = null;   // Randy/Tester currently choosing a clone source (or null)
let landingCloneTargetFile = null; // target's existing exact file for "Continue with my file"
let landingCloneSource = null;   // selected source learner name while the clone panel is open
let landingCloneSourceFile = null; // exact source file selected for cloning
function clearSelectedSourceFile() { selectedSourceFile = null; }
function setLandingStatus(text) { const el = $('landing-status'); if (el) el.textContent = text || ''; }
function setKidModalStatus(text) { const el = $('kid-modal-status'); if (el) el.textContent = text || ''; }
function closeKidModal() { hide('anchor-kid-modal'); setKidModalStatus(''); }
function isCloneLandingUser(name) {
  const n = String(name || '').trim().toLowerCase();
  return CLONE_LANDING_USERS.some((u) => u.toLowerCase() === n);
}
function clearLandingCloneMode() {
  landingCloneTarget = null;
  landingCloneTargetFile = null;
  landingCloneSource = null;
  landingCloneSourceFile = null;
  const panel = $('landing-clone-panel');
  if (panel) panel.classList.add('hidden');
  const run = $('landing-clone-run');
  if (run) { run.disabled = true; run.textContent = 'Clone selected file'; }
  document.querySelectorAll('#landing-names .landing-name').forEach((btn) => {
    btn.classList.remove('landing-clone-target', 'landing-clone-source');
  });
}
function showSetupView() {
  clearLandingCloneMode();
  hide('anchor-landing'); closeKidModal(); show('anchor-setup'); show('anchor-problem-list-editor');
}
function showLandingView() {
  clearLandingCloneMode();
  closeKidModal(); hide('anchor-setup'); hide('anchor-problem-list-editor'); setLandingStatus(''); show('anchor-landing');
  loadLandingUsers();
}
function landingButtonId(name, filename) {
  const raw = `${name}__${filename || ''}`.replace(/[^A-Za-z0-9_-]+/g, '-');
  return `landing-${raw}`.replace(/-+$/g, '');
}
function updateLandingClonePanel() {
  const panel = $('landing-clone-panel');
  const msg = $('landing-clone-msg');
  const run = $('landing-clone-run');
  if (!panel || !landingCloneTarget) return;
  panel.classList.remove('hidden');
  document.querySelectorAll('#landing-names .landing-name').forEach((btn) => {
    const n = btn.dataset.name || '';
    btn.classList.toggle('landing-clone-target', n === landingCloneTarget);
    btn.classList.toggle('landing-clone-source', !!landingCloneSource && n === landingCloneSource);
  });
  if (landingCloneSource) {
    if (msg) {
      msg.textContent = `Playing as ${landingCloneTarget}. Clone ${landingCloneSource}'s file into yours `
        + `(same state, your name inside), or continue with your current file.`;
    }
    if (run) { run.disabled = false; run.textContent = `Clone ${landingCloneSource}'s file`; }
  } else {
    if (msg) {
      msg.textContent = `Playing as ${landingCloneTarget}. Clone another learner's file into yours, `
        + `or continue with your current file. Tap a name above to choose who to clone from.`;
    }
    if (run) { run.disabled = true; run.textContent = 'Clone selected file'; }
  }
}
function beginLandingClonePick(name, filename = null) {
  landingCloneTarget = name;
  landingCloneTargetFile = filename;
  landingCloneSource = null;
  landingCloneSourceFile = null;
  setLandingStatus('');
  updateLandingClonePanel();
}
async function loadLandingUsers() {
  const host = $('landing-names');
  if (!host) return;
  host.innerHTML = '';
  clearLandingCloneMode();
  setLandingStatus('Loading names…');
  let resp;
  try {
    resp = await fetch(`/api/folder-users?folder=${encodeURIComponent(currentFolder())}`);
  } catch {
    setLandingStatus('Can’t reach the local server — start it (run tools/dev_server.py), then reload.');
    return;
  }
  if (!resp || !resp.ok) {
    setLandingStatus('Can’t reach the local server — start it (run tools/dev_server.py), then reload.');
    return;
  }
  let j;
  try { j = await resp.json(); } catch { j = null; }
  if (!j || !j.ok || !Array.isArray(j.users)) {
    setLandingStatus('Couldn’t load names from the source folder.');
    return;
  }
  // Always offer Randy/Tester for the clone-from workflow, even when they have no file yet
  // (Continue then says "ask Baba"; Clone creates their file from the chosen source).
  const users = Array.isArray(j.users) ? j.users.slice() : [];
  const present = new Set(users.map((u) => String(u.name || '').toLowerCase()));
  for (const name of CLONE_LANDING_USERS) {
    if (!present.has(name.toLowerCase())) users.push({ name, label: name, filename: '' });
  }
  if (!users.length) {
    setLandingStatus(`No learner files in "${currentFolder()}" yet — ask Baba to set one up.`);
    return;
  }
  setLandingStatus('');
  for (const u of users) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'landing-name';
    btn.id = landingButtonId(u.name, u.filename);
    btn.textContent = u.label || u.name;
    btn.dataset.name = u.name;
    if (u.filename) btn.dataset.filename = u.filename;
    // Pin every landing choice to the exact top-level file represented by its button.
    btn.addEventListener('click', () => onLandingNameClick(u.name, u.filename || null));
    host.appendChild(btn);
  }
  // Keep the setup datalist in sync with the same folder names (unique only).
  const dl = $('anchor-name-options');
  if (dl) {
    const seen = new Set();
    dl.innerHTML = '';
    for (const u of users) {
      if (seen.has(u.name)) continue;
      seen.add(u.name);
      const opt = document.createElement('option');
      opt.value = u.name;
      dl.appendChild(opt);
    }
  }
}
function onLandingNameClick(name, filename) {
  // While Randy/Tester are choosing a clone source, other name buttons select the source
  // without leaving the landing. Tapping Randy/Tester (same or other) restarts that pick.
  if (landingCloneTarget) {
    if (isCloneLandingUser(name)) {
      beginLandingClonePick(name, filename);
      return;
    }
    landingCloneSource = name;
    landingCloneSourceFile = filename || null;
    setLandingStatus('');
    updateLandingClonePanel();
    return;
  }
  if (isCloneLandingUser(name)) {
    beginLandingClonePick(name, filename);
    return;
  }
  onKidPick(name, filename);
}
async function onKidPick(name, filename) {
  // Drive the existing setup controls under the hood: Continue this learner's latest file
  // and pin it to the exact top-level file represented by the landing button.
  clearLandingCloneMode();
  $('anchor-username').value = name;
  selectedSourceFile = filename || null;
  const cont = $('anchor-mode-continue'); if (cont) cont.checked = true;
  setLandingStatus(`Loading ${name}'s file…`);
  await refreshNameStatus();   // populates lastLoadFound + internalLists + loadedTargetedConfig
  if (lastLoadFound === false) {              // server reachable, but this learner has no file
    setLandingStatus(`No file for ${name} yet — ask Baba to set one up.`);
    return;
  }
  if (lastLoadFound !== true) {               // load didn't complete -> the local server is down
    setLandingStatus('Can’t reach the local server — start it (run tools/dev_server.py), then try again.');
    return;
  }
  setLandingStatus('');
  const title = $('kid-modal-title');
  if (title) title.textContent = `Hi ${name}! What do you want to do?`;
  setKidModalStatus('');
  updateKidQuickButtons();   // enable only the operations this file has a quick set for
  show('anchor-kid-modal');
}
async function onLandingCloneContinue() {
  if (!landingCloneTarget) return;
  const target = landingCloneTarget;
  const targetFile = landingCloneTargetFile;
  await onKidPick(target, targetFile);
}
async function onLandingCloneRun() {
  if (!landingCloneTarget || !landingCloneSource) return;
  const target = landingCloneTarget;
  const source = landingCloneSource;
  const run = $('landing-clone-run');
  if (run) run.disabled = true;
  setLandingStatus(`Cloning ${source}'s file as ${target}…`);
  let result;
  try {
    const resp = await fetch('/api/clone-user-file', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        folder: currentFolder(), sourceUser: source, targetUser: target,
        sourceFile: landingCloneSourceFile || undefined,
      }),
    });
    result = await resp.json();
  } catch (e) {
    result = { ok: false, error: String(e.message || e) };
  }
  if (!result || !result.ok) {
    setLandingStatus(result && result.error
      ? `Clone failed: ${result.error}`
      : 'Clone failed — is tools/dev_server.py running?');
    if (run) run.disabled = false;
    return;
  }
  setLandingStatus(`Cloned ${result.source_file || source} → ${result.new_file || target}`);
  await onKidPick(target, null);
}
function onLandingCloneCancel() {
  clearLandingCloneMode();
  setLandingStatus('');
}
// Fluency feast preset (the params used to build the one-click list). Weights, not strict
// percentages — the generator normalizes them and reallocates any empty category's share.
const FLUENCY_FEAST_PRESET = {
  count: 20,
  sessionSelection: { mode: 'all' },
  mix: { missing: 40, incorrect: 40, almost: 10, 'needs-practice': 10, fluent: 0 },
};
// Optional: prepend two easy warm-ups (fluent add-0/1/2/doubles: single-digit sum, then two-digit).
// Default on; Fluency feast + dragon bursts (not the problem-list editor).
const FLUENCY_FEAST_EASY_START = true;
// Kid "Fluency feast": build a list from the learner's fluency (flagged answers excluded),
// add it to the FRONT of the queue without retain (so it runs next, then is removed), and run
// it. Existing problem lists stay queued behind it.
async function onKidFluencyFeast() {
  if (typeof globalThis.generateFluencyProblemList !== 'function') { setKidModalStatus('Fluency generator not loaded.'); return; }
  setKidModalStatus('Building your fluency feast…');
  const attempts = await anchorAttemptsForFluency();
  if (!attempts.length) { setKidModalStatus('No history yet — finish a quiz first so a feast can be built.'); return; }
  // Use this file's saved preset when present, else the code defaults.
  const saved = loadedFluencyFeast;
  const count = (saved && saved.count) || FLUENCY_FEAST_PRESET.count;
  const sessionSelection = (saved && saved.session && saved.session.mode)
    ? { mode: saved.session.mode, n: saved.session.n, since: saved.session.since }
    : FLUENCY_FEAST_PRESET.sessionSelection;
  const mix = (saved && saved.mix) || FLUENCY_FEAST_PRESET.mix;
  const feastOpts = {
    attempts, sessionSelection, numberRange: [0, 9], operations: ['+'],
    excludeFlagged: true, thresholds: anchorThresholds(),
  };
  const res = globalThis.generateFluencyProblemList({
    ...feastOpts, numProblems: count, distribution: mix,
  });
  if (!res || !res.problems || !res.problems.length) { setKidModalStatus('Couldn’t build a fluency feast from this file.'); return; }
  let problems = res.problems.slice();
  if (FLUENCY_FEAST_EASY_START && typeof globalThis.pickFluencyFeastEasyStart === 'function') {
    const easy = globalThis.pickFluencyFeastEasyStart(feastOpts);
    if (easy && easy.problems && easy.problems.length === 2) problems = easy.problems.concat(problems);
  }
  if (!listPanel || !listPanel.addGenerated) { setKidModalStatus('Need the local server to save the feast — start tools/dev_server.py.'); return; }
  const ok = await listPanel.addGenerated(problems.join('\n'), 'Fluency feast', true, false);   // add as first, retain off
  if (!ok) { setKidModalStatus('Couldn’t save the feast list (is the local server running?).'); return; }
  const select = $('anchor-problem-list-file');
  if (select) { select.value = INTERNAL_LIST_VALUE; onProblemListSelectionChange(); }   // run the queue (feast is #1)
  closeKidModal();
  hide('anchor-landing');
  onStart();
}
function onKidMode(mode) {
  const select = $('anchor-problem-list-file');
  if (mode === 'targeted') {
    const cfg = loadedTargetedConfig;
    const hasTargets = cfg && Array.isArray(cfg.targets) && cfg.targets.length > 0;
    if (!hasTargets) { setKidModalStatus('No targeted practice set up — ask Baba to update your file.'); return; }
    if (select) { select.value = TARGETED_VALUE; onProblemListSelectionChange(); }
  } else if (mode === 'visual') {
    const user = ($('anchor-username').value || '').trim();
    const cfg = loadedVisualConfig;
    const dflt = VISUAL_DEFAULTS[user];
    const hasTargets = (cfg && Array.isArray(cfg.targets) && cfg.targets.length > 0)
      || (dflt && Array.isArray(dflt.targets) && dflt.targets.length > 0);
    if (!hasTargets) { setKidModalStatus('No ten-frames practice set up — ask Baba to update your file.'); return; }
    if (select) { select.value = VISUAL_VALUE; onProblemListSelectionChange(); applyVisualPrefill(true); }
  } else {   // 'list' — the learner's internal problem-list queue (runs the next list)
    if (!internalLists.length) { setKidModalStatus('No problem list in your file — ask Baba to update your file.'); return; }
    if (select) { select.value = INTERNAL_LIST_VALUE; onProblemListSelectionChange(); }
  }
  closeKidModal();
  hide('anchor-landing');
  onStart();
}
function quickQuizAvailable(op) {
  const items = loadedQuickPractice && loadedQuickPractice[op];
  return Array.isArray(items) && items.length > 0;
}
// Enable/disable the three Quick-quiz operation buttons by what the loaded file actually has.
function updateKidQuickButtons() {
  for (const [id, op] of [['kid-quick-add', '+'], ['kid-quick-sub', '-'], ['kid-quick-mul', '*']]) {
    if ($(id)) $(id).disabled = !quickQuizAvailable(op);
  }
}
// Kid "Quick quiz" button: launch the 7-problem set for one operation straight away.
function onKidQuickQuiz(op) {
  if (!quickQuizAvailable(op)) {
    setKidModalStatus(`No ${QUICK_OP_LABELS[op] || op} quick quiz yet — finish a quiz first so it can build one.`);
    return;
  }
  pendingQuickQuizOp = op;
  closeKidModal();
  hide('anchor-landing');
  onStart();
}
function setupKidLanding() {
  (qs.get('setup') === '1' ? showSetupView : showLandingView)();
  if ($('landing-other')) $('landing-other').addEventListener('click', showSetupView);
  if ($('landing-clone-continue')) $('landing-clone-continue').addEventListener('click', onLandingCloneContinue);
  if ($('landing-clone-run')) $('landing-clone-run').addEventListener('click', onLandingCloneRun);
  if ($('landing-clone-cancel')) $('landing-clone-cancel').addEventListener('click', onLandingCloneCancel);
  if ($('kid-mode-feast')) $('kid-mode-feast').addEventListener('click', onKidFluencyFeast);
  if ($('kid-mode-targeted')) $('kid-mode-targeted').addEventListener('click', () => onKidMode('targeted'));
  if ($('kid-mode-visual')) $('kid-mode-visual').addEventListener('click', () => onKidMode('visual'));
  if ($('kid-mode-list')) $('kid-mode-list').addEventListener('click', () => onKidMode('list'));
  if ($('kid-quick-add')) $('kid-quick-add').addEventListener('click', () => onKidQuickQuiz('+'));
  if ($('kid-quick-sub')) $('kid-quick-sub').addEventListener('click', () => onKidQuickQuiz('-'));
  if ($('kid-quick-mul')) $('kid-quick-mul').addEventListener('click', () => onKidQuickQuiz('*'));
  if ($('kid-modal-back')) $('kid-modal-back').addEventListener('click', closeKidModal);
}

// Pull the picked learner's attempts (joined to their sessions) for the editor's
// "Generate by fluency" classification. Uses the live run store when present, else the
// IndexedDB copy that refreshNameStatus caches when a learner is picked (Continue). Empty
// until a learner with a file is selected.
async function anchorAttemptsForFluency() {
  try {
    const username = ($('anchor-username').value || '').trim();
    if (!username) return [];
    await ensureSql();
    let db = store && store.db && store.username === username ? store.db : null;
    let temp = null;
    if (!db) {
      const bytes = await createIndexedDbPersistence({ dbName: USER_DB }).load(username);
      if (!bytes) return [];
      db = temp = new SQL.Database(bytes);
    }
    const res = db.exec(
      `SELECT pa.problem_text AS problem_text, pa.is_correct AS is_correct, pa.response_time_ms AS response_time_ms,
              pa.attempt_id AS attempt_id, pa.session_id AS session_id, pa.flags_json AS flags_json, s.start_time AS start_time
       FROM ProblemAttempts pa JOIN Sessions s ON pa.session_id = s.session_id
       WHERE s.user_name = ?${sessionTypeExclusionSql(db, 's')} ORDER BY s.start_time, pa.attempt_id`,
      [username]
    );
    const out = res.length ? res[0].values.map((row) => { const o = {}; res[0].columns.forEach((c, i) => { o[c] = row[i]; }); return o; }) : [];
    if (temp && typeof temp.close === 'function') temp.close();
    return out;
  } catch (e) { return []; }
}

// The fluency rubric for this learner: the per-file thresholds saved in their profile, or the
// system defaults. Used for the end-of-quiz % and the generate-by-fluency classification, so
// both honor the parameters the operator saved on the analysis page.
function anchorThresholds() {
  const t = loadedProfile && loadedProfile.thresholds;
  if (t && typeof t === 'object') {
    return Object.assign({}, defaultFluencyThresholds, t);
  }
  return defaultFluencyThresholds;
}
// Overall fluency right now (integer %), classified over the quiz's operations from the
// learner's stored attempts (store.db, which finalize mutates as it writes the session). Read
// once before the session is written (start) and once after (end) for the summary readout.
async function anchorFluencyPercentNow() {
  try {
    if (typeof fluencyPercent !== 'function') return null;
    const attempts = await anchorAttemptsForFluency();
    return fluencyPercent(attempts, anchorThresholds(), { numberRange: RANGE, operations, excludeFlagged: true });
  } catch (e) { return null; }
}
// Whether to show the start→end %-fluent readout for the loaded learner (per-file profile flag,
// default true when no file/flag is loaded).
function showFluencyPercentEnabled() {
  if (loadedProfile && typeof loadedProfile.showFluencyPercent === 'boolean') return loadedProfile.showFluencyPercent;
  return true;
}
// Reflect the loaded learner's flag in the setup checkbox (default checked).
function syncFluencyPercentCheckbox() {
  const cb = $('anchor-show-fluency-percent');
  if (cb) cb.checked = showFluencyPercentEnabled();
}
// Unchecking (or re-checking) the setup checkbox auto-saves the flag to the learner's file, so
// from then on it stays as set. No-op without a loaded learner/dev server.
async function onShowFluencyPercentChange() {
  const cb = $('anchor-show-fluency-percent');
  if (!cb) return;
  const value = !!cb.checked;
  loadedProfile = Object.assign({}, loadedProfile, { showFluencyPercent: value });
  const user = ($('anchor-username').value || '').trim();
  if (!user || currentSourceMode() === 'new') return;   // nothing to write to yet
  try {
    await fetch('/api/profile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ folder: currentFolder(), user, file: loadedServerFile || undefined, showFluencyPercent: value }),
    });
  } catch (e) { /* dev server not reachable — the in-memory flag still applies this session */ }
}

// Render the start → end %-fluent readout on the summary, or hide it when the learner's profile
// disables it or the values couldn't be read.
function renderFluencyReadout(initialPct, finalPct) {
  const el = $('anchor-fluency-readout');
  if (!el) return;
  if (!showFluencyPercentEnabled() || initialPct == null || finalPct == null) {
    el.textContent = '';
    el.classList.add('hidden');
    return;
  }
  el.innerHTML = `Fluent: <strong>${initialPct}%</strong> &rarr; <strong>${finalPct}%</strong>`;
  el.classList.remove('hidden');
}

function init() {
  buildKeypad(SHOW_BIG_KEYS);
  buildFlagMenu();
  // iOS Safari can interpret very fast double taps as zoom gestures.
  // Block default dblclick on the keypad so repeated number taps (e.g. "11")
  // register as input instead of triggering page zoom.
  $('anchor-keypad').addEventListener('dblclick', (e) => e.preventDefault());
  $('anchor-start').addEventListener('click', onStart);
  if ($('anchor-show-fluency-percent')) $('anchor-show-fluency-percent').addEventListener('change', onShowFluencyPercentChange);
  // Auto-load the learner's latest file on blur (menu pick), or Enter.
  setupUsernameCombobox();
  $('anchor-username').addEventListener('blur', refreshNameStatus);
  $('anchor-username').addEventListener('change', refreshNameStatus);
  $('anchor-username').addEventListener('input', clearSelectedSourceFile);
  // The editor opens by default; reload it when the learner/source changes so it shows that
  // person's lists (and the fluency generator classifies their history).
  const refreshEditor = () => { if (listPanel) listPanel.refresh(); };
  $('anchor-username').addEventListener('blur', refreshEditor);
  $('anchor-username').addEventListener('change', refreshEditor);
  if ($('anchor-source-folder')) $('anchor-source-folder').addEventListener('change', refreshEditor);
  $('anchor-username').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { e.preventDefault(); $('anchor-username').blur(); }
  });
  if ($('anchor-source-folder')) {
    $('anchor-source-folder').addEventListener('change', () => {
      clearSelectedSourceFile();
      updateFolderUi();
    });
  }
  if ($('anchor-select-source-folder')) $('anchor-select-source-folder').addEventListener('click', onSelectSourceFolder);
  if ($('anchor-destination')) $('anchor-destination').addEventListener('change', updateFolderUi);
  if ($('anchor-clone-run')) $('anchor-clone-run').addEventListener('click', onCloneRun);
  if ($('anchor-clone-from')) $('anchor-clone-from').addEventListener('change', refreshClonePreview);
  for (const id of ['anchor-mode-continue', 'anchor-mode-new']) {
    if ($(id)) $(id).addEventListener('change', () => {
      clearSelectedSourceFile();
      refreshNameStatus();
    });
  }
  updateFolderUi();   // set the test-description-row visibility + status
  $('anchor-answer').addEventListener('input', onInput);
  $('anchor-answer').addEventListener('keydown', (e) => { if (e.key === 'Enter') onAnswer(); });
  if ($('anchor-enter')) $('anchor-enter').addEventListener('click', onAnswer);
  $('anchor-skip-flag').addEventListener('click', onSkipFlag);
  $('anchor-flag-previous').addEventListener('click', onFlagPrevious);
  if ($('anchor-lightbulb')) $('anchor-lightbulb').addEventListener('click', onLightbulb);
  if ($('anchor-teach-done')) $('anchor-teach-done').addEventListener('click', onTeachDone);
  $('anchor-correct-continue').addEventListener('click', onCorrectContinue);
  $('anchor-correct-insert').addEventListener('click', onCorrectInsert);
  $('anchor-correct-flag').addEventListener('click', onCorrectFlag);
  $('anchor-flag-comment').addEventListener('input', onFlagCommentInput);
  $('anchor-continue').addEventListener('click', startThorough);
  $('anchor-stop').addEventListener('click', finishStop);
  $('anchor-quit-save').addEventListener('click', onQuitSave);
  $('anchor-quit-abandon').addEventListener('click', onQuitAbandon);
  $('anchor-guardrail-end').addEventListener('click', onGuardrailEnd);
  $('anchor-guardrail-continue').addEventListener('click', onGuardrailContinue);
  $('anchor-practice-skip').addEventListener('click', startQuiz);
  $('anchor-practice-ready').addEventListener('click', startQuiz);
  if ($('anchor-go')) $('anchor-go').addEventListener('click', onGoClick);
  if ($('anchor-pause')) $('anchor-pause').addEventListener('click', onPause);
  if ($('anchor-pause-continue')) $('anchor-pause-continue').addEventListener('click', onPauseContinue);
  if ($('anchor-pause-skip')) $('anchor-pause-skip').addEventListener('click', onPauseSkip);
  if ($('anchor-grad-continue')) $('anchor-grad-continue').addEventListener('click', onGraduationContinue);
  $('anchor-practice-continue').addEventListener('click', onPracticeContinue);
  $('anchor-retry-upload').addEventListener('click', onRetryUpload);
  // "Do another quiz" — reload the page without query params, back to the kid landing.
  if ($('anchor-do-another')) $('anchor-do-another').addEventListener('click', () => { window.location.href = window.location.pathname; });
  if ($('anchor-load-analysis')) $('anchor-load-analysis').addEventListener('click', onLoadForAnalysis);
  hideDevTools();
  $('anchor-problem-list-file').addEventListener('change', onProblemListSelectionChange);
  setupTargetedAutoSave();   // target fields + params + filler auto-save to /api/targeted-config
  setupVisualAutoSave();     // visual target fields + params + filler auto-save to /api/visual-config
  // Collapsible problem-list editor (shared with the analysis page), keyed by the current
  // name + source folder so edits land on the same file "Use internal" runs.
  const editorHost = $('anchor-problem-list-editor');
  if (editorHost) {
    listPanel = mountProblemListPanel({
      container: editorHost,
      title: 'Problem Lists (editor)',
      startOpen: true,
      getContext: () => {
        const user = ($('anchor-username').value || '').trim();
        return user ? {
          folder: currentFolder(),
          user,
          file: selectedSourceFile || loadedServerFile || undefined,
        } : null;
      },
      // "Generate by fluency" classifies the picked learner's attempts (addition, 0-9) with
      // their saved per-file rubric (or the system default) and builds the list client-side.
      generateFluency: async (spec) => {
        if (typeof globalThis.generateFluencyProblemList !== 'function') return null;
        const attempts = await anchorAttemptsForFluency();
        if (!attempts.length) return null;
        return globalThis.generateFluencyProblemList({
          attempts, numProblems: spec.numProblems, distribution: spec.distribution,
          sessionSelection: spec.sessionSelection, numberRange: [0, 9], operations: ['+'],
          excludeFlagged: true,   // flagged answers don't count toward the fluency classification
          thresholds: anchorThresholds(),
        });
      },
      // When the editor adds/edits/removes a list, refresh the "Use internal" option + the
      // display box right away (so it un-greys after the first list is created) — without
      // re-fetching the panel (it already re-rendered itself).
      onChange: (lists) => { internalLists = Array.isArray(lists) ? lists : []; renderInternalLists(); },
    });
  }
  // Warm-up is off by default; ?practice=1 enables it, ?practice=0 forces it off (e2e/dev).
  if (qs.get('practice') === '1') $('anchor-practice-enabled').checked = true;
  else if (qs.get('practice') === '0') $('anchor-practice-enabled').checked = false;
  setupKidLanding();   // default landing (folder names / Other…); ?setup=1 shows the full setup
  problemListInitPromise = initProblemListControls().then(onProblemListSelectionChange);
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
else init();
