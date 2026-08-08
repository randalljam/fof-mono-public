import { isTouchDevice } from '../device.js';

const STEPS_DESKTOP = [
  { icon: '🖱️', text: 'Click the screen, then move with W A S D. Press Space to jump.' },
  { icon: '👀', text: 'Move the mouse to look around — just like Minecraft!' },
  { icon: '🥚', text: 'Walk to the egg in the nest and click it.' },
  { icon: '🔢', text: 'Answer math problems to feed your egg. Try to answer fast!' },
  { icon: '📜', text: 'After every quiz the story continues — collect the scrolls! (The 📜 Story button re-reads them.)' },
  { icon: '✨', text: 'If a sparkle trail appears, follow it! It leads somewhere important.' },
  { icon: '💜', text: 'Watch the bar fill up — when it is FULL, something new happens!' },
];
const STEPS_TOUCH = [
  { icon: '🕹️', text: 'Use the Move stick (lower right) to walk — just like Minecraft on a tablet!' },
  { icon: '👀', text: 'Drag the Look pad (lower left) to look around. Tap Jump to hop.' },
  { icon: '🥚', text: 'Walk to the egg in the nest, then tap the Tap button when it appears.' },
  { icon: '🔢', text: 'Answer math problems to feed your egg. Try to answer fast!' },
  { icon: '📜', text: 'After every quiz the story continues — collect the scrolls! (The 📜 Story button re-reads them.)' },
  { icon: '✨', text: 'If a sparkle trail appears, follow it! It leads somewhere important.' },
  { icon: '💜', text: 'Watch the bar fill up — when it is FULL, something new happens!' },
];

export function createHowTo() {
  const root = document.getElementById('howto-root');
  root.innerHTML = '';
  root.classList.add('hidden');
  const card = document.createElement('div');
  card.className = 'howto-card';
  const h2 = document.createElement('h2');
  h2.textContent = 'How to Play';
  card.appendChild(h2);
  const touch = isTouchDevice();
  const steps = touch ? STEPS_TOUCH : STEPS_DESKTOP;
  steps.forEach((s) => {
    const row = document.createElement('div');
    row.className = 'howto-step';
    row.innerHTML = `<span class="howto-icon">${s.icon}</span>${s.text}`;
    card.appendChild(row);
  });
  const close = document.createElement('button');
  close.className = 'hud-btn';
  close.textContent = 'Got it!';
  close.style.marginTop = '12px';
  close.addEventListener('click', () => hide());
  card.appendChild(close);
  root.appendChild(card);
  function show() { root.classList.remove('hidden'); }
  function hide() { root.classList.add('hidden'); }
  return { show, hide };
}
