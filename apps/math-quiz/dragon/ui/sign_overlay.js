// Sign-writing dialog: after a finished quiz at a sign station, the player
// paints their own words onto the sign. Pure DOM, styled like the story cards.
// ask() resolves with the new text, or null when the player keeps the old one.
import { SIGN_MAX_LEN } from '../sim/stations.js';

export function createSignOverlay() {
  const root = document.createElement('div');
  root.id = 'sign-root';
  root.className = 'hidden';
  document.body.appendChild(root);
  function close() {
    root.innerHTML = '';
    root.classList.add('hidden');
  }
  function ask({ current = '', dragonName = '', user = '' } = {}) {
    return new Promise((resolve) => {
      root.innerHTML = '';
      const c = document.createElement('div');
      c.className = 'story-card story-naming';
      const kicker = document.createElement('div');
      kicker.className = 'story-kicker';
      kicker.textContent = '🪧 Quiz power earned!';
      const title = document.createElement('h2');
      title.className = 'story-title';
      title.textContent = current ? 'Change your sign' : 'What should the sign say?';
      const body = document.createElement('p');
      body.className = 'story-text';
      body.textContent = current
        ? `Right now it says “${current}”. Paint new words, or keep it just the way it is.`
        : 'This sign is all yours — paint any words you want on it!';
      const input = document.createElement('input');
      input.className = 'story-name-input';
      input.maxLength = SIGN_MAX_LEN;
      input.placeholder = 'Type your sign words…';
      input.value = current;
      const ideas = document.createElement('div');
      ideas.className = 'story-name-ideas';
      const suggestions = [
        user ? `${user}'s Dragon Valley` : 'Dragon Valley',
        dragonName ? `${dragonName} lives here!` : 'A dragon lives here!',
        'Welcome, friends!',
        'Beware: tickle dragon!',
      ];
      for (const s of suggestions) {
        const chip = document.createElement('button');
        chip.className = 'story-name-chip';
        chip.textContent = s;
        chip.addEventListener('click', () => { input.value = s; input.focus(); });
        ideas.appendChild(chip);
      }
      const btn = document.createElement('button');
      btn.className = 'story-btn';
      btn.textContent = 'Paint it on!';
      btn.addEventListener('click', () => {
        const text = input.value.trim();
        if (!text) { input.focus(); return; }
        close();
        resolve(text);
      });
      const keep = document.createElement('button');
      keep.className = 'story-name-chip sign-keep-btn';
      keep.textContent = current ? 'Keep it as is' : 'Not right now';
      keep.addEventListener('click', () => { close(); resolve(null); });
      input.addEventListener('keydown', (e) => { if (e.key === 'Enter') btn.click(); e.stopPropagation(); });
      c.append(kicker, title, body, input, ideas, btn, keep);
      root.appendChild(c);
      root.classList.remove('hidden');
      setTimeout(() => input.focus(), 50);
    });
  }
  function isOpen() { return !root.classList.contains('hidden'); }
  return { ask, isOpen };
}
