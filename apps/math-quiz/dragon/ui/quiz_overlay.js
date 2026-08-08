import { answerFor } from '../quiz_bridge.js';
import { createBurst } from '../sim/burst_session.js';
import { tenFrameTeachStates } from '../../engine/ten_frame.mjs';
import {
  showLightbulbOnRender, autoTeachOnWrong, showLightbulbInFlagPanel, teachableProblem,
} from '../../engine/teach_policy.mjs';

const INSERT_GAP = 5;
const TEACH_HOLD_MS = (() => {
  try {
    const search = (typeof location !== 'undefined' && location.search) || '';
    const raw = Number(new URLSearchParams(search).get('teachms'));
    return Number.isFinite(raw) && raw >= 0 ? raw : 2000;
  } catch {
    return 2000;
  }
})();
const FLAG_REASON_LABELS = {
  'skip-noreason': 'Skip - no reason',
  lightbulb: '💡 Show ten-frames',
  distracted: 'Distracted',
  interrupted: 'Interrupted',
  error: 'Input Error',
  stall: 'Stall',
  dontknow: "I Don't Know",
  other: 'Other',
};
const DISPLAY = { '+': '+', '-': '−', '*': '×', '/': '÷' };
const STREAK_CHEERS = ['', '', '', 'in a row!', 'on fire!', 'amazing!', 'unstoppable!'];

function digitCount(val) {
  return String(Math.abs(Math.round(val))).replace(/[^0-9]/g, '').length;
}
function stampNow() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}_${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`;
}
function itemFromEntry(entry) {
  if (!entry) return null;
  const [a, op, b] = String(entry.problem_text).split(' ');
  return { key: entry.fact_key, operation: op, num1: Number(a), num2: Number(b), problemText: entry.problem_text };
}
function formatProblem(item) {
  if (!item) return '';
  if (typeof formatProblemTextForDisplay === 'function') {
    return formatProblemTextForDisplay(item.problemText || `${item.num1} ${item.operation} ${item.num2}`);
  }
  const op = DISPLAY[item.operation] || item.operation;
  return `${item.num1} ${op} ${item.num2}`;
}

export function createQuizOverlay({ onComplete, onQuit, onCorrect, onWrong, onTransfer, canTransfer }) {
  const root = document.getElementById('quiz-root');
  root.innerHTML = '';
  root.classList.add('hidden');
  const card = document.createElement('div');
  card.className = 'quiz-card';
  const titleEl = document.createElement('div');
  titleEl.className = 'quiz-title';
  titleEl.textContent = 'Math quiz time!';
  const problemEl = document.createElement('div');
  problemEl.className = 'quiz-problem';
  const answerEl = document.createElement('div');
  answerEl.className = 'quiz-answer';
  answerEl.textContent = '?';
  const feedbackEl = document.createElement('div');
  feedbackEl.className = 'quiz-feedback';
  const dotsEl = document.createElement('div');
  dotsEl.className = 'quiz-dots';
  const progressEl = document.createElement('div');
  progressEl.className = 'quiz-progress';
  const correctionEl = document.createElement('div');
  correctionEl.className = 'quiz-correction hidden';
  const correctionAnswerEl = document.createElement('div');
  correctionAnswerEl.className = 'quiz-correction-answer hidden';
  const flagMenuEl = document.createElement('div');
  flagMenuEl.className = 'quiz-flag-menu hidden';
  const flagReasonsEl = document.createElement('div');
  flagReasonsEl.className = 'quiz-flag-reasons';
  const flagCommentEl = document.createElement('input');
  flagCommentEl.type = 'text';
  flagCommentEl.className = 'quiz-flag-comment';
  flagCommentEl.placeholder = 'Other / comment (optional)';
  flagCommentEl.autocomplete = 'off';
  flagMenuEl.append(flagReasonsEl, flagCommentEl);
  const correctFlagBtn = document.createElement('button');
  correctFlagBtn.type = 'button';
  correctFlagBtn.className = 'quiz-btn secondary';
  correctFlagBtn.textContent = '⚑ Flag';
  const correctContinueBtn = document.createElement('button');
  correctContinueBtn.type = 'button';
  correctContinueBtn.className = 'quiz-btn';
  correctContinueBtn.textContent = 'Continue';
  const correctInsertBtn = document.createElement('button');
  correctInsertBtn.type = 'button';
  correctInsertBtn.className = 'quiz-btn secondary';
  correctInsertBtn.textContent = 'Continue & insert';
  correctionEl.append(correctionAnswerEl, flagMenuEl, correctFlagBtn, correctContinueBtn, correctInsertBtn);
  const teachEl = document.createElement('div');
  teachEl.className = 'quiz-teach hidden';
  teachEl.id = 'quiz-teach';
  const teachVisualEl = document.createElement('div');
  teachVisualEl.className = 'quiz-teach-visual';
  const teachDoneBtn = document.createElement('button');
  teachDoneBtn.type = 'button';
  teachDoneBtn.className = 'quiz-btn quiz-teach-done hidden';
  teachDoneBtn.textContent = 'Got it';
  teachEl.append(teachVisualEl, teachDoneBtn);
  const keypad = document.createElement('div');
  keypad.className = 'quiz-keypad';
  const actionRow = document.createElement('div');
  actionRow.className = 'quiz-action-row';
  const lightbulbBtn = document.createElement('button');
  lightbulbBtn.type = 'button';
  lightbulbBtn.className = 'quiz-btn lightbulb hidden';
  lightbulbBtn.setAttribute('aria-label', 'Show ten-frames');
  lightbulbBtn.title = 'Show ten-frames';
  lightbulbBtn.textContent = '💡';
  const skipFlagBtn = document.createElement('button');
  skipFlagBtn.type = 'button';
  skipFlagBtn.className = 'quiz-btn skipflag';
  skipFlagBtn.textContent = 'Skip & flag';
  const flagPrevBtn = document.createElement('button');
  flagPrevBtn.type = 'button';
  flagPrevBtn.className = 'quiz-btn flagprev';
  flagPrevBtn.textContent = 'Flag previous';
  const pauseBtn = document.createElement('button');
  pauseBtn.type = 'button';
  pauseBtn.className = 'quiz-btn secondary';
  pauseBtn.textContent = 'Pause';
  actionRow.append(lightbulbBtn, skipFlagBtn, flagPrevBtn, pauseBtn);
  const quitRow = document.createElement('div');
  quitRow.className = 'quiz-quit-row';
  const quitSaveBtn = document.createElement('button');
  quitSaveBtn.type = 'button';
  quitSaveBtn.className = 'quiz-btn secondary';
  quitSaveBtn.textContent = 'Quit & save';
  const quitAbandonBtn = document.createElement('button');
  quitAbandonBtn.type = 'button';
  quitAbandonBtn.className = 'quiz-btn secondary';
  quitAbandonBtn.textContent = 'Quit & abandon';
  quitRow.append(quitSaveBtn, quitAbandonBtn);
  const actions = document.createElement('div');
  actions.className = 'quiz-actions';
  actions.append(actionRow, quitRow);
  const pausePanel = document.createElement('div');
  pausePanel.className = 'quiz-pause-panel hidden';
  const pauseTitle = document.createElement('p');
  pauseTitle.className = 'quiz-pause-title';
  pauseTitle.textContent = 'Paused';
  const pauseContinueBtn = document.createElement('button');
  pauseContinueBtn.type = 'button';
  pauseContinueBtn.className = 'quiz-btn';
  pauseContinueBtn.textContent = 'Continue (same problem)';
  const pauseInsertBtn = document.createElement('button');
  pauseInsertBtn.type = 'button';
  pauseInsertBtn.className = 'quiz-btn secondary';
  pauseInsertBtn.textContent = 'Continue & insert';
  pausePanel.append(pauseTitle, pauseContinueBtn, pauseInsertBtn);
  const goOverlay = document.createElement('div');
  goOverlay.className = 'quiz-go-overlay hidden';
  goOverlay.id = 'quiz-go-overlay';
  const goInner = document.createElement('div');
  goInner.className = 'quiz-go-inner';
  const goBtn = document.createElement('button');
  goBtn.type = 'button';
  goBtn.className = 'quiz-go';
  goBtn.id = 'quiz-go';
  goBtn.textContent = 'Go!';
  const transferBtn = document.createElement('button');
  transferBtn.type = 'button';
  transferBtn.className = 'quiz-btn handoff-transfer';
  transferBtn.textContent = 'Transfer…';
  const cancelQuizBtn = document.createElement('button');
  cancelQuizBtn.type = 'button';
  cancelQuizBtn.className = 'quiz-btn secondary quiz-go-cancel';
  cancelQuizBtn.textContent = 'Cancel quiz';
  goInner.append(goBtn, transferBtn, cancelQuizBtn);
  goOverlay.appendChild(goInner);
  card.append(titleEl, problemEl, answerEl, feedbackEl, dotsEl, progressEl, teachEl, correctionEl, keypad, actions, goOverlay);
  root.appendChild(card);
  root.appendChild(pausePanel);

  let burst = null;
  let shownAt = 0;
  let shownAtWall = 0;
  let startTime = '';
  let answerStr = '';
  let submitting = false;
  let streak = 0;
  let waitingForGo = false;
  let paused = false;
  let correctionMode = null;
  let correctionProblem = null;
  let correctionLightbulbItem = null;
  let prevFlagItem = null;
  let goReadyAt = 0;
  let teachState = null;
  let teachItem = null;
  let teachContext = null;
  let teachRevealTimer = null;
  const GO_ARM_MS = 400;

  function isBlocked() {
    return waitingForGo || submitting || paused || correctionMode !== null || isTeachOpen();
  }
  function hide(el) { el.classList.add('hidden'); }
  function show(el) { el.classList.remove('hidden'); }
  function isTeachOpen() {
    return !!(teachContext && !teachEl.classList.contains('hidden'));
  }
  function lightbulbFlag() {
    return {
      reason: 'lightbulb',
      label: FLAG_REASON_LABELS.lightbulb,
      timestamp: new Date().toISOString(),
      notes: '',
    };
  }
  function syncLightbulbForItem(item) {
    if (showLightbulbOnRender(item)) show(lightbulbBtn);
    else hide(lightbulbBtn);
  }
  function openTeach(item, context = 'help') {
    if (!teachableProblem(item)) return false;
    teachContext = context;
    teachItem = item;
    teachState = tenFrameTeachStates(item.num1, item.num2);
    teachVisualEl.innerHTML = `<div class="quiz-teach-setup">${teachState.setupSvg}</div>`;
    hide(teachDoneBtn);
    show(teachEl);
    if (teachRevealTimer) clearTimeout(teachRevealTimer);
    if (TEACH_HOLD_MS <= 0) revealTeachResult();
    else teachRevealTimer = setTimeout(revealTeachResult, TEACH_HOLD_MS);
    return true;
  }
  function revealTeachResult() {
    teachRevealTimer = null;
    if (!teachState || teachVisualEl.querySelector('.quiz-teach-result')) return;
    const setup = teachVisualEl.querySelector('.quiz-teach-setup');
    if (setup) setup.innerHTML = teachState.setupAnswerSvg;
    teachVisualEl.insertAdjacentHTML(
      'beforeend',
      `<div class="quiz-teach-divider"></div><div class="quiz-teach-result">${teachState.resultSvg}</div>`,
    );
    if (teachContext !== 'wrong') show(teachDoneBtn);
  }
  function closeTeachPanel({ restoreReviewLightbulb = false } = {}) {
    const wasReview = teachContext === 'review';
    if (teachRevealTimer) clearTimeout(teachRevealTimer);
    teachRevealTimer = null;
    hide(teachEl);
    teachVisualEl.innerHTML = '';
    hide(teachDoneBtn);
    teachState = null;
    teachItem = null;
    teachContext = null;
    if (restoreReviewLightbulb && wasReview && correctionLightbulbItem) show(lightbulbBtn);
  }
  function onTeachDone() {
    const item = teachItem;
    const context = teachContext;
    closeTeachPanel({ restoreReviewLightbulb: true });
    if (context === 'review') return;
    if (item) burst.insertItem(item, INSERT_GAP);
    advance();
  }
  function onLightbulb() {
    if (correctionMode !== null) {
      if (!correctionLightbulbItem || !showLightbulbInFlagPanel(correctionLightbulbItem) || isTeachOpen()) return;
      openTeach(correctionLightbulbItem, 'review');
      return;
    }
    if (!burst || !burst.current() || submitting || waitingForGo || paused) return;
    const item = burst.current();
    if (!showLightbulbOnRender(item)) return;
    submitting = true;
    const rt = performance.now() - shownAt;
    burst.record(null, false, rt, shownAtWall, startTime, [lightbulbFlag()]);
    openTeach(item, 'help');
  }
  function resetCorrectionUi() {
    correctionMode = null;
    correctionProblem = null;
    correctionLightbulbItem = null;
    prevFlagItem = null;
    hide(correctionEl);
    hide(correctionAnswerEl);
    hide(flagMenuEl);
    show(correctFlagBtn);
    correctionAnswerEl.textContent = '';
    flagCommentEl.value = '';
    for (const cb of flagReasonsEl.querySelectorAll('input[type=checkbox]')) cb.checked = false;
  }
  function buildFlagMenu() {
    flagReasonsEl.innerHTML = '';
    for (const [reason, label] of Object.entries(FLAG_REASON_LABELS)) {
      const lab = document.createElement('label');
      const cb = document.createElement('input');
      cb.type = 'checkbox';
      cb.value = reason;
      cb.addEventListener('change', syncCorrectionFlags);
      lab.appendChild(cb);
      lab.appendChild(document.createTextNode(' ' + label));
      flagReasonsEl.appendChild(lab);
    }
    flagCommentEl.addEventListener('input', onFlagCommentInput);
  }
  function syncCorrectionFlags() {
    if (!correctionProblem) return;
    const checked = [...flagReasonsEl.querySelectorAll('input[type=checkbox]:checked')].map((cb) => cb.value);
    const notes = (flagCommentEl.value || '').trim();
    const stamp = new Date().toISOString();
    let flags = checked.map((reason) => ({ reason, label: FLAG_REASON_LABELS[reason] || reason, timestamp: stamp, notes }));
    if (!flags.length && notes) flags = [{ reason: 'other', label: FLAG_REASON_LABELS.other, timestamp: stamp, notes }];
    correctionProblem.flags = flags;
    if (burst) burst.setFlags(correctionProblem, flags);
  }
  function onFlagCommentInput() {
    if (flagReasonsEl.querySelector('input[type=checkbox]:checked')) syncCorrectionFlags();
  }
  function dismissFlagMenu() {
    if (flagMenuEl.classList.contains('hidden')) return;
    syncCorrectionFlags();
    hide(flagMenuEl);
  }
  function showCorrectionPanel(mode, {
    showAnswer = false, openFlags = false, defaultReason = null, problem = null, lightbulbItem = null,
  } = {}) {
    correctionMode = mode;
    correctionProblem = problem || (burst ? burst.lastEntry() : null);
    correctionLightbulbItem = lightbulbItem && showLightbulbInFlagPanel(lightbulbItem) ? lightbulbItem : null;
    if (correctionLightbulbItem) show(lightbulbBtn);
    else if (!showLightbulbOnRender(burst && burst.current())) hide(lightbulbBtn);
    if (showAnswer && correctionProblem) {
      correctionAnswerEl.textContent = `Correct answer: ${correctionProblem.correct_answer}`;
      show(correctionAnswerEl);
    } else {
      correctionAnswerEl.textContent = '';
      hide(correctionAnswerEl);
    }
    const existing = (correctionProblem && correctionProblem.flags) || [];
    const reasons = new Set(existing.map((f) => f.reason));
    if (defaultReason) reasons.add(defaultReason);
    for (const cb of flagReasonsEl.querySelectorAll('input[type=checkbox]')) cb.checked = reasons.has(cb.value);
    flagCommentEl.value = existing.length ? (existing[0].notes || '') : '';
    if (defaultReason) syncCorrectionFlags();
    if (openFlags) { show(flagMenuEl); hide(correctFlagBtn); }
    else { hide(flagMenuEl); show(correctFlagBtn); }
    show(correctContinueBtn);
    show(correctInsertBtn);
    show(correctionEl);
  }
  function resumeCurrentAfterFlag() {
    submitting = false;
    closeTeachPanel();
    resetCorrectionUi();
    showItem();
  }
  function advance() {
    submitting = false;
    closeTeachPanel();
    resetCorrectionUi();
    if (burst.done()) finish('list-complete');
    else showItem();
  }
  function renderDots() {
    dotsEl.innerHTML = '';
    if (!burst) return;
    const { index, total } = burst.progress();
    for (let i = 0; i < total; i++) {
      const d = document.createElement('span');
      d.className = 'quiz-dot' + (i < index ? ' done' : '') + (i === index ? ' current' : '');
      dotsEl.appendChild(d);
    }
    progressEl.textContent = `${Math.min(index + 1, total)} of ${total}`;
  }
  function armGoButton() {
    goReadyAt = performance.now() + GO_ARM_MS;
    goBtn.disabled = true;
    goBtn.style.pointerEvents = 'none';
    setTimeout(() => {
      if (!waitingForGo) return;
      goBtn.disabled = false;
      goBtn.style.pointerEvents = '';
    }, GO_ARM_MS);
  }
  function refreshGoExtraButtons() {
    if (!onTransfer) {
      transferBtn.classList.add('hidden');
    } else {
      transferBtn.classList.remove('hidden');
      const label = (typeof onTransfer === 'function' && onTransfer.label)
        ? onTransfer.label()
        : (onTransfer.label ? onTransfer.label() : 'Transfer…');
      transferBtn.textContent = label;
      const ok = !canTransfer || canTransfer();
      transferBtn.disabled = !ok;
      transferBtn.style.opacity = ok ? '1' : '0.45';
    }
    cancelQuizBtn.classList.toggle('hidden', !waitingForGo);
  }
  function cancelQuizAtGo() {
    if (!waitingForGo || !burst) return;
    waitingForGo = false;
    paused = false;
    hide(goOverlay);
    hide(pausePanel);
    hide(root);
    if (onQuit) onQuit('quit-abandoned', []);
  }
  function showGoGate() {
    waitingForGo = true;
    paused = false;
    answerStr = '';
    answerEl.textContent = '?';
    feedbackEl.textContent = '';
    feedbackEl.className = 'quiz-feedback';
    closeTeachPanel();
    resetCorrectionUi();
    hide(lightbulbBtn);
    hide(pausePanel);
    problemEl.textContent = '\u00a0';
    progressEl.textContent = '';
    dotsEl.innerHTML = '';
    armGoButton();
    show(goOverlay);
    refreshGoExtraButtons();
  }
  function onGoClick(e) {
    if (!waitingForGo || !burst) return;
    if (goBtn.disabled || performance.now() < goReadyAt) {
      if (e) { e.preventDefault(); e.stopPropagation(); }
      return;
    }
    waitingForGo = false;
    hide(goOverlay);
    startTime = stampNow();
    showItem();
  }
  function showItem() {
    const item = burst.current();
    if (!item) return finish('list-complete');
    answerStr = '';
    answerEl.textContent = '?';
    feedbackEl.textContent = '';
    feedbackEl.className = 'quiz-feedback';
    problemEl.textContent = formatProblem(item);
    shownAt = performance.now();
    shownAtWall = Date.now();
    syncLightbulbForItem(item);
    renderDots();
  }
  function submitAnswer() {
    if (isBlocked() || !burst || burst.done()) return;
    const item = burst.current();
    if (!item || answerStr === '') return;
    submitting = true;
    const rt = performance.now() - shownAt;
    const userValue = Number(answerStr);
    const correct = answerFor(item.operation, item.num1, item.num2);
    const isCorrect = userValue === correct;
    burst.record(userValue, isCorrect, rt, shownAtWall, startTime);
    if (isCorrect) {
      streak += 1;
      const cheer = streak >= 3 ? ` ${streak} ${STREAK_CHEERS[Math.min(streak, 6)]}` : '';
      feedbackEl.textContent = `✓${cheer}`;
      feedbackEl.className = 'quiz-feedback correct';
      root.classList.add('flash-correct');
      if (onCorrect) onCorrect(streak);
      setTimeout(() => root.classList.remove('flash-correct'), 300);
      setTimeout(() => advance(), 400);
    } else {
      streak = 0;
      feedbackEl.textContent = '';
      feedbackEl.className = 'quiz-feedback';
      if (onWrong) onWrong();
      showCorrectionPanel('answer', { showAnswer: true, lightbulbItem: item });
      if (autoTeachOnWrong(item)) openTeach(item, 'wrong');
    }
  }
  function onSkipFlag() {
    if (!burst || !burst.current() || isBlocked()) return;
    submitting = true;
    const item = burst.current();
    const rt = performance.now() - shownAt;
    burst.record(null, false, rt, shownAtWall, startTime);
    showCorrectionPanel('answer', {
      showAnswer: true, openFlags: true, defaultReason: 'skip-noreason', lightbulbItem: item,
    });
  }
  function onFlagPrevious() {
    if (correctionMode !== null || !burst || !burst.current() || submitting || paused) return;
    const prev = burst.lastEntry();
    if (!prev) return;
    submitting = true;
    prevFlagItem = itemFromEntry(prev);
    problemEl.textContent = formatProblem(prevFlagItem);
    answerEl.textContent = prev.user_answer_string || '?';
    showCorrectionPanel('previous', {
      showAnswer: !prev.is_correct, openFlags: true, problem: prev, lightbulbItem: prevFlagItem,
    });
  }
  function onCorrectFlag(e) {
    if (e) e.stopPropagation();
    if (!correctionProblem) return;
    const existing = correctionProblem.flags || [];
    const reasons = new Set(existing.map((f) => f.reason));
    for (const cb of flagReasonsEl.querySelectorAll('input[type=checkbox]')) cb.checked = reasons.has(cb.value);
    flagCommentEl.value = existing.length ? (existing[0].notes || '') : '';
    show(flagMenuEl);
    hide(correctFlagBtn);
  }
  function onCorrectContinue() {
    dismissFlagMenu();
    closeTeachPanel();
    if (correctionMode === 'previous') { resumeCurrentAfterFlag(); return; }
    advance();
  }
  function onCorrectInsert() {
    dismissFlagMenu();
    closeTeachPanel();
    if (correctionMode === 'previous') {
      if (prevFlagItem) burst.insertItem(prevFlagItem, INSERT_GAP);
      resumeCurrentAfterFlag();
      return;
    }
    const item = itemFromEntry(correctionProblem);
    if (item) burst.insertItem(item, INSERT_GAP);
    advance();
  }
  function onPause() {
    if (!burst || !burst.current() || isBlocked()) return;
    submitting = true;
    paused = true;
    feedbackEl.textContent = '';
    feedbackEl.className = 'quiz-feedback';
    closeTeachPanel();
    hide(correctionEl);
    show(pausePanel);
  }
  function onPauseContinue() {
    paused = false;
    submitting = false;
    hide(pausePanel);
    showItem();
  }
  function onPauseInsert() {
    paused = false;
    submitting = false;
    hide(pausePanel);
    burst.skipCurrent(INSERT_GAP);
    if (burst.done()) finish('list-complete');
    else showItem();
  }
  function enteredDigits() {
    return answerStr.replace(/[^0-9]/g, '').length;
  }
  function maybeAutoSubmit() {
    const item = burst && burst.current();
    if (!item) return;
    const correct = answerFor(item.operation, item.num1, item.num2);
    if (enteredDigits() > 0 && enteredDigits() >= digitCount(correct)) submitAnswer();
  }
  function onDigit(d) {
    if (isBlocked() || !burst) return;
    answerStr += d;
    answerEl.textContent = answerStr;
    maybeAutoSubmit();
  }
  function finish(kind) {
    waitingForGo = false;
    paused = false;
    submitting = false;
    closeTeachPanel();
    resetCorrectionUi();
    hide(lightbulbBtn);
    hide(goOverlay);
    hide(pausePanel);
    const { entries: all } = burst.progress();
    hide(root);
    if (onComplete && kind === 'list-complete') onComplete(kind, all);
    else if (onQuit) onQuit(kind, all);
  }
  function buildKeypad() {
    keypad.innerHTML = '';
    const rows = [[7, 8, 9], [4, 5, 6], [1, 2, 3], ['negate', 0, 'clear']];
    for (const row of rows) {
      for (const token of row) {
        const btn = document.createElement('button');
        btn.className = 'quiz-key' + (token === 'negate' || token === 'clear' ? ' op' : '');
        btn.textContent = token === 'clear' ? 'C' : token === 'negate' ? '±' : String(token);
        btn.addEventListener('click', () => {
          if (isBlocked() || !burst) return;
          if (token === 'clear') { answerStr = ''; answerEl.textContent = '?'; return; }
          if (token === 'negate') {
            if (answerStr.startsWith('-')) answerStr = answerStr.slice(1);
            else if (answerStr !== '') answerStr = '-' + answerStr;
            answerEl.textContent = answerStr || '?';
            maybeAutoSubmit();
            return;
          }
          onDigit(String(token));
        });
        keypad.appendChild(btn);
      }
    }
  }

  buildFlagMenu();
  buildKeypad();
  transferBtn.addEventListener('click', async () => {
    if (!waitingForGo || !burst || !onTransfer) return;
    if (canTransfer && !canTransfer()) return;
    transferBtn.disabled = true;
    try {
      const snap = getPendingSnapshot();
      if (typeof onTransfer === 'function') await onTransfer(snap);
      else if (onTransfer.fn) await onTransfer.fn(snap);
    } finally {
      transferBtn.disabled = false;
      refreshGoExtraButtons();
    }
  });
  cancelQuizBtn.addEventListener('click', cancelQuizAtGo);
  goBtn.addEventListener('click', onGoClick);
  lightbulbBtn.addEventListener('click', onLightbulb);
  teachDoneBtn.addEventListener('click', onTeachDone);
  skipFlagBtn.addEventListener('click', onSkipFlag);
  flagPrevBtn.addEventListener('click', onFlagPrevious);
  pauseBtn.addEventListener('click', onPause);
  correctFlagBtn.addEventListener('click', onCorrectFlag);
  correctContinueBtn.addEventListener('click', onCorrectContinue);
  correctInsertBtn.addEventListener('click', onCorrectInsert);
  pauseContinueBtn.addEventListener('click', onPauseContinue);
  pauseInsertBtn.addEventListener('click', onPauseInsert);
  quitSaveBtn.addEventListener('click', () => {
    if (!burst) return;
    waitingForGo = false;
    paused = false;
    const { entries: partial } = burst.progress();
    hide(root);
    hide(pausePanel);
    if (onQuit) onQuit('quit-saved', partial);
  });
  quitAbandonBtn.addEventListener('click', () => {
    if (!burst) return;
    if (!window.confirm('Quit and discard this session? Nothing will be saved.')) return;
    waitingForGo = false;
    paused = false;
    hide(root);
    hide(pausePanel);
    if (onQuit) onQuit('quit-abandoned', []);
  });
  window.addEventListener('keydown', (e) => {
    if (root.classList.contains('hidden') || isBlocked()) return;
    if (e.key >= '0' && e.key <= '9') onDigit(e.key);
    else if (e.key === 'Backspace') { answerStr = answerStr.slice(0, -1); answerEl.textContent = answerStr || '?'; }
    else if (e.key === 'Enter') submitAnswer();
  });

  function getPendingSnapshot() {
    if (!waitingForGo || !burst) return null;
    return { items: burst.allItems(), atGoGate: true };
  }
  function isAtGoGate() { return waitingForGo; }
  function isOpen() { return !root.classList.contains('hidden'); }
  function showHandoffOffer({ label, onTransfer }) {
    return new Promise((resolve) => {
      waitingForGo = false;
      paused = false;
      hide(goOverlay);
      hide(pausePanel);
      resetCorrectionUi();
      problemEl.textContent = '';
      answerEl.textContent = '';
      feedbackEl.textContent = 'Quiz saved!';
      feedbackEl.className = 'quiz-feedback correct';
      progressEl.textContent = '';
      dotsEl.innerHTML = '';
      keypad.classList.add('hidden');
      actions.classList.add('hidden');
      root.classList.remove('hidden');
      const offer = document.createElement('div');
      offer.className = 'quiz-handoff-offer';
      const transferOfferBtn = document.createElement('button');
      transferOfferBtn.type = 'button';
      transferOfferBtn.className = 'quiz-btn handoff-transfer';
      transferOfferBtn.textContent = label || 'Transfer…';
      const keepBtn = document.createElement('button');
      keepBtn.type = 'button';
      keepBtn.className = 'quiz-btn secondary';
      keepBtn.textContent = 'Keep playing';
      offer.append(transferOfferBtn, keepBtn);
      card.appendChild(offer);
      const cleanup = () => {
        offer.remove();
        keypad.classList.remove('hidden');
        actions.classList.remove('hidden');
        feedbackEl.textContent = '';
        feedbackEl.className = 'quiz-feedback';
        hide(root);
      };
      transferOfferBtn.addEventListener('click', async () => {
        transferOfferBtn.disabled = true;
        keepBtn.disabled = true;
        try {
          if (onTransfer) await onTransfer();
        } finally {
          cleanup();
          resolve('transferred');
        }
      });
      keepBtn.addEventListener('click', () => {
        cleanup();
        resolve('keep');
      });
    });
  }

  return {
    start(sessionBurst, _stamp) {
      burst = sessionBurst;
      startTime = '';
      streak = 0;
      submitting = false;
      paused = false;
      resetCorrectionUi();
      hide(pausePanel);
      root.classList.remove('hidden');
      showGoGate();
    },
    startFromPending(pending) {
      if (!pending || !pending.items || !pending.items.length) return false;
      burst = createBurst(pending.items);
      startTime = '';
      streak = 0;
      submitting = false;
      paused = false;
      resetCorrectionUi();
      hide(pausePanel);
      root.classList.remove('hidden');
      showGoGate();
      return true;
    },
    hide() {
      waitingForGo = false;
      paused = false;
      hide(goOverlay);
      hide(pausePanel);
      hide(root);
    },
    isAtGoGate, isOpen, getPendingSnapshot, showHandoffOffer,
  };
}
