import { progressToNext, foreshadowFor } from '../sim/milestones.js';
import { nextObjectiveFor, formatDragonName } from '../sim/story.js';

// The HUD never shows the raw fluency-to-100 scale: the bar is progress within
// the current milestone segment, so every session visibly closes in on the NEXT
// surprise (which is teased but never named).
export function createHud({ getMaxPct, getState, onHelp, onJournal, onMap, onTransfer, canTransfer }) {
  const root = document.getElementById('hud-root');
  root.innerHTML = '';
  const panel = document.createElement('div');
  panel.className = 'hud-panel';
  const title = document.createElement('div');
  title.className = 'hud-title';
  const heart = document.createElement('div');
  heart.className = 'hud-heart';
  const fill = document.createElement('div');
  fill.className = 'hud-heart-fill';
  heart.append(fill);
  const pctLabel = document.createElement('div');
  pctLabel.className = 'hud-pct';
  const foreshadow = document.createElement('div');
  foreshadow.className = 'hud-foreshadow';
  const objective = document.createElement('div');
  objective.className = 'hud-objective';
  const burstLabel = document.createElement('div');
  burstLabel.className = 'hud-bursts';
  const gemLabel = document.createElement('div');
  gemLabel.className = 'hud-gems';
  const btnRow = document.createElement('div');
  btnRow.className = 'hud-btn-row';
  const helpBtn = document.createElement('button');
  helpBtn.className = 'hud-btn';
  helpBtn.textContent = '? How to play';
  helpBtn.addEventListener('click', () => { if (onHelp) onHelp(); });
  btnRow.appendChild(helpBtn);
  if (onJournal) {
    const journalBtn = document.createElement('button');
    journalBtn.className = 'hud-btn';
    journalBtn.textContent = '📜 Story';
    journalBtn.addEventListener('click', () => onJournal());
    btnRow.appendChild(journalBtn);
  }
  if (onMap) {
    const mapBtn = document.createElement('button');
    mapBtn.className = 'hud-btn';
    mapBtn.textContent = '🗺️ Map';
    mapBtn.addEventListener('click', () => onMap());
    btnRow.appendChild(mapBtn);
  }
  let transferBtn = null;
  if (onTransfer) {
    transferBtn = document.createElement('button');
    transferBtn.className = 'hud-btn handoff-transfer';
    transferBtn.textContent = onTransfer.label ? onTransfer.label() : 'Transfer';
    transferBtn.addEventListener('click', () => onTransfer());
    btnRow.appendChild(transferBtn);
  }
  panel.append(title, heart, pctLabel, foreshadow, objective, gemLabel, burstLabel, btnRow);
  root.appendChild(panel);
  function refresh() {
    const max = getMaxPct();
    const state = getState();
    title.textContent = state.hatched ? (formatDragonName(state.dragonName) || 'Your Dragon') : 'Dragon Egg';
    objective.textContent = `★ ${nextObjectiveFor(state).text}`;
    if (state.rideUnlocked) {
      fill.style.width = '100%';
      pctLabel.textContent = 'All grown up!';
      foreshadow.textContent = 'Your dragon loves flying with you!';
    } else {
      const { frac } = progressToNext(max);
      const segPct = Math.round(frac * 100);
      fill.style.width = `${segPct}%`;
      pctLabel.textContent = segPct >= 100
        ? 'The bar is FULL — something is about to happen!'
        : `${segPct}% of the way to the next surprise!`;
      foreshadow.textContent = foreshadowFor(max);
    }
    burstLabel.textContent = `Practice bursts: ${state.totalBursts || 0}`;
    gemLabel.textContent = `💎 Dragon Gems: ${state.gems || 0}`;
    if (transferBtn) {
      const show = canTransfer ? canTransfer() : true;
      transferBtn.disabled = !show;
      transferBtn.style.opacity = show ? '1' : '0.45';
      if (onTransfer.label) transferBtn.textContent = onTransfer.label();
    }
  }
  refresh();
  return { refresh };
}
