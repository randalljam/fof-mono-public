// Milestone ladder: one surprise every 10% from 60 to 100. Reveal texts fire at
// celebration; foreshadow texts tease the NEXT step without naming it (the hatch
// and the 100% flight/ride stay surprises).
export const MILESTONES = [
  { id: 'egg-found', pct: 0, title: 'Dragon Egg', revealText: 'You found a mysterious egg!', foreshadowText: 'Something special is waiting…', dragonAnim: 'idle', worldChange: null },
  { id: 'hatch', pct: 60, title: 'Hatch!', revealText: 'Your dragon hatched! It already loves you.', foreshadowText: 'Feed your egg with math quizzes… something is stirring inside!', dragonAnim: 'idle', worldChange: 'follow' },
  { id: 'wings', pct: 70, title: 'Juvenile Dragon!', revealText: 'Your dragon grew into a big juvenile with strong wings!', foreshadowText: 'Your dragon is getting stronger with every quiz…', dragonAnim: 'wing-stretch', worldChange: 'wings' },
  { id: 'jump', pct: 80, title: 'Grown-Up Dragon!', revealText: 'Your dragon is almost fully grown — and can jump super high!', foreshadowText: 'Those new wings are itching to try something…', dragonAnim: 'jump', worldChange: 'jump' },
  { id: 'fire', pct: 90, title: 'Fire Breath', revealText: 'Your dragon breathes fire! Whoa!', foreshadowText: 'You hear a little rumble in your dragon\u2019s tummy…', dragonAnim: 'fire', worldChange: 'fire' },
  { id: 'flight-ride', pct: 100, title: '???', revealText: 'Your dragon can FLY!', foreshadowText: 'Something AMAZING happens when your practice is perfect…', dragonAnim: 'fly', worldChange: 'flight' },
];
export function getNextMilestone(maxPct) {
  for (const m of MILESTONES) {
    if (m.id === 'egg-found') continue;
    if (m.pct > maxPct) return m;
  }
  return null;
}
export function resolveMilestones(maxPct, celebratedIds) {
  const queue = [];
  const done = new Set(celebratedIds || []);
  for (const m of MILESTONES) {
    if (m.id === 'egg-found') continue;
    if (maxPct >= m.pct && !done.has(m.id)) queue.push(m);
  }
  return queue;
}
// Life-stage model: baby (hatch) → juvenile at 70% → adult at 80%; no new form at 90%.
export function dragonFormFor(celebratedIds) {
  const done = new Set(celebratedIds || []);
  if (done.has('jump')) return 'adult';
  if (done.has('wings')) return 'juvenile';
  return 'baby';
}
export function animRepertoireFor(celebratedIds) {
  const done = new Set(celebratedIds || []);
  if (!done.has('hatch')) return [];
  const names = ['play'];
  if (done.has('wings')) names.push('wing-stretch');
  if (done.has('jump')) names.push('jump');
  if (done.has('fire')) names.push('fire');
  return names;
}
// Progress within the current 10%-segment: the HUD bar shows this (never the raw
// fluency-to-100 scale) so every session visibly moves toward the NEXT surprise.
export function progressToNext(maxPct) {
  let prevPct = 0;
  for (const m of MILESTONES) {
    if (m.id === 'egg-found') continue;
    if (maxPct < m.pct) {
      const frac = Math.max(0, Math.min(1, (maxPct - prevPct) / (m.pct - prevPct)));
      return { next: m, prevPct, frac };
    }
    prevPct = m.pct;
  }
  return { next: null, prevPct, frac: 1 };
}
export function foreshadowFor(maxPct) {
  const { next } = progressToNext(maxPct);
  if (!next) return '';
  return next.foreshadowText || `Keep going toward ${next.title}!`;
}
