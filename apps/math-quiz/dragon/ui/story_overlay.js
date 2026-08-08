// Story overlay: parchment scroll cards shown at burst end (reaction line, the
// next story beat, any Game Master letters) plus the naming dialog and the
// journal of collected scrolls. Pure DOM — beat selection lives in sim/story.js.
import { formatDragonName } from '../sim/story.js';

const NAME_IDEAS = ['Ember', 'Sparkle', 'Luna', 'Pip', 'Zippy', 'Rosie'];

export function createStoryOverlay({ onName }) {
  const root = document.getElementById('story-root');
  root.innerHTML = '';
  root.classList.add('hidden');
  let typer = null;
  function clear() {
    if (typer) { clearInterval(typer); typer = null; }
    root.innerHTML = '';
  }
  function typeText(el, text) {
    // Gentle typewriter; clicking the card finishes it instantly.
    let i = 0;
    el.textContent = '';
    if (typer) clearInterval(typer);
    typer = setInterval(() => {
      i += 2;
      el.textContent = text.slice(0, i);
      if (i >= text.length) { clearInterval(typer); typer = null; }
    }, 18);
    return () => {
      if (typer) { clearInterval(typer); typer = null; }
      el.textContent = text;
    };
  }
  function card(className) {
    clear();
    const c = document.createElement('div');
    c.className = `story-card ${className || ''}`;
    root.appendChild(c);
    root.classList.remove('hidden');
    return c;
  }
  function showItem(item) {
    return new Promise((resolve) => {
      if (item.kind === 'beat' && item.beat.kind === 'name') return resolve(showNaming(item));
      const c = card(item.kind === 'gm-message' ? 'story-letter' : '');
      const kicker = document.createElement('div');
      kicker.className = 'story-kicker';
      const title = document.createElement('h2');
      title.className = 'story-title';
      const body = document.createElement('p');
      body.className = 'story-text';
      let text = '';
      if (item.kind === 'reaction') {
        kicker.textContent = '✨ Quiz complete';
        title.textContent = 'Nice practicing!';
        text = item.text;
      } else if (item.kind === 'gm-message') {
        kicker.textContent = '💌 A letter arrives…';
        title.textContent = item.from ? `From ${item.from}` : 'From the Dragon Keeper';
        text = item.text;
      } else {
        kicker.textContent = `📜 ${item.phase.title}`;
        title.textContent = item.beat.title;
        text = item.beat.text;
      }
      const finish = typeText(body, text);
      const btn = document.createElement('button');
      btn.className = 'story-btn';
      btn.textContent = 'Continue';
      btn.addEventListener('click', () => { clear(); root.classList.add('hidden'); resolve(); });
      c.addEventListener('click', (e) => { if (e.target !== btn) finish(); });
      c.append(kicker, title, body, btn);
    });
  }
  function showNaming(item) {
    return new Promise((resolve) => {
      const c = card('story-naming');
      const kicker = document.createElement('div');
      kicker.className = 'story-kicker';
      kicker.textContent = `📜 ${item.phase.title}`;
      const title = document.createElement('h2');
      title.className = 'story-title';
      title.textContent = item.beat.title;
      const body = document.createElement('p');
      body.className = 'story-text';
      body.textContent = item.beat.text;
      const input = document.createElement('input');
      input.className = 'story-name-input';
      input.maxLength = 16;
      input.placeholder = 'Type a name…';
      const ideas = document.createElement('div');
      ideas.className = 'story-name-ideas';
      for (const n of NAME_IDEAS) {
        const chip = document.createElement('button');
        chip.className = 'story-name-chip';
        chip.textContent = n;
        chip.addEventListener('click', () => { input.value = n; input.focus(); });
        ideas.appendChild(chip);
      }
      const btn = document.createElement('button');
      btn.className = 'story-btn';
      btn.textContent = 'That’s the name!';
      btn.addEventListener('click', () => {
        const name = input.value.trim();
        if (!name) { input.focus(); return; }
        if (onName) onName(name);
        clear();
        root.classList.add('hidden');
        resolve();
      });
      input.addEventListener('keydown', (e) => { if (e.key === 'Enter') btn.click(); e.stopPropagation(); });
      c.append(kicker, title, body, input, ideas, btn);
      setTimeout(() => input.focus(), 50);
    });
  }
  async function showSequence(items) {
    for (const item of items) {
      if (item) await showItem(item);
    }
  }
  function showJournal(entries, dragonName) {
    return new Promise((resolve) => {
      const c = card('story-journal');
      const title = document.createElement('h2');
      title.className = 'story-title';
      const displayName = formatDragonName(dragonName);
      title.textContent = displayName ? `${displayName}’s Story` : 'Your Story So Far';
      c.appendChild(title);
      const list = document.createElement('div');
      list.className = 'story-journal-list';
      if (!entries.length) {
        const p = document.createElement('p');
        p.className = 'story-text';
        p.textContent = 'No scrolls collected yet — finish a quiz to earn your first one!';
        list.appendChild(p);
      }
      let lastPhase = '';
      for (const e of entries) {
        if (e.phaseTitle !== lastPhase) {
          lastPhase = e.phaseTitle;
          const ph = document.createElement('div');
          ph.className = 'story-journal-phase';
          ph.textContent = e.phaseTitle;
          list.appendChild(ph);
        }
        const item = document.createElement('details');
        item.className = 'story-journal-entry';
        const s = document.createElement('summary');
        s.textContent = `📜 ${e.title}`;
        const p = document.createElement('p');
        p.textContent = e.text;
        item.append(s, p);
        list.appendChild(item);
      }
      c.appendChild(list);
      const btn = document.createElement('button');
      btn.className = 'story-btn';
      btn.textContent = 'Close';
      btn.addEventListener('click', () => { clear(); root.classList.add('hidden'); resolve(); });
      c.appendChild(btn);
    });
  }
  function isOpen() { return !root.classList.contains('hidden'); }
  return { showSequence, showJournal, isOpen };
}
