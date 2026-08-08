import { roadStops, roadProgressLine, nextUpgrade } from '../sim/rewards.js';

// The Road Home map: a parchment card listing every stop on the journey to
// Mount Ember with done / you-are-here / still-ahead markers, plus the segment
// progress line and the next nest upgrade to look forward to. Pure DOM; the
// stop model lives in sim/rewards.js.
export function createMapOverlay() {
  const root = document.getElementById('story-root');
  function show(state) {
    return new Promise((resolve) => {
      root.innerHTML = '';
      const c = document.createElement('div');
      c.className = 'story-card story-map';
      const title = document.createElement('h2');
      title.className = 'story-title';
      title.textContent = '🗺️ The Road Home';
      const list = document.createElement('div');
      list.className = 'map-stops';
      for (const stop of roadStops(state)) {
        const row = document.createElement('div');
        row.className = 'map-stop' + (stop.done ? ' done' : stop.current ? ' current' : ' locked');
        const mark = stop.done ? '✅' : stop.current ? '⭐' : '·';
        row.innerHTML = `<span class="map-mark">${mark}</span><span class="map-icon">${stop.icon}</span><span class="map-name">${stop.title}</span>${stop.current ? '<span class="map-here">you are here!</span>' : ''}`;
        list.appendChild(row);
      }
      const progress = document.createElement('p');
      progress.className = 'story-text map-progress';
      progress.textContent = roadProgressLine(state);
      const gems = document.createElement('p');
      gems.className = 'story-text map-gems';
      const up = nextUpgrade(state.gems || 0);
      gems.textContent = up
        ? `💎 ${state.gems || 0} gems — at ${up.cost} your nest gets: ${up.title}!`
        : `💎 ${state.gems || 0} gems — your nest has EVERY upgrade!`;
      const btn = document.createElement('button');
      btn.className = 'story-btn';
      btn.textContent = 'Back to the game';
      btn.addEventListener('click', () => {
        root.innerHTML = '';
        root.classList.add('hidden');
        resolve();
      });
      c.append(title, list, progress, gems, btn);
      root.appendChild(c);
      root.classList.remove('hidden');
    });
  }
  return { show };
}
