// Web Audio manager. Loads OGG files when present; otherwise falls back to
// synthesized tones so every game event still has cozy feedback with zero assets.
const SYNTH_SEQUENCES = {
  correct: [[880, 0, 0.12], [1175, 0.09, 0.16]],
  'wrong-soft': [[290, 0, 0.22]],
  click: [[640, 0, 0.06]],
  milestone: [[523, 0, 0.14], [659, 0.12, 0.14], [784, 0.24, 0.26]],
  hatch: [[523, 0, 0.12], [659, 0.1, 0.12], [784, 0.2, 0.12], [1047, 0.3, 0.4]],
  'wing-flap': [[220, 0, 0.1], [180, 0.12, 0.14]],
};

export function createAudioManager() {
  let ctx = null;
  let master = null;
  let muted = false;
  let started = false;
  const buffers = {};
  function ensure() {
    if (ctx) return ctx;
    try {
      window.AudioContext = window.AudioContext || window.webkitAudioContext;
      ctx = new AudioContext();
      master = ctx.createGain();
      master.gain.value = 0.45;
      master.connect(ctx.destination);
    } catch (e) {
      console.warn('[audio] Web Audio unavailable', e);
    }
    return ctx;
  }
  async function unlock() {
    if (started) return;
    ensure();
    if (ctx && ctx.state === 'suspended') await ctx.resume();
    started = true;
  }
  async function load(name, path) {
    ensure();
    if (!ctx) return;
    try {
      const resp = await fetch(path);
      if (!resp.ok) throw new Error('missing');
      const arr = await resp.arrayBuffer();
      buffers[name] = await ctx.decodeAudioData(arr);
    } catch {
      buffers[name] = null;   // fall through to synth in play()
    }
  }
  function synthTone(freq, dur, at = 0, type = 'sine') {
    const t0 = ctx.currentTime + at;
    const osc = ctx.createOscillator();
    const g = ctx.createGain();
    osc.type = type;
    osc.frequency.value = freq;
    g.gain.setValueAtTime(0.1, t0);
    g.gain.exponentialRampToValueAtTime(0.001, t0 + dur);
    osc.connect(g);
    g.connect(master);
    osc.start(t0);
    osc.stop(t0 + dur + 0.02);
  }
  function play(name) {
    if (muted || !ctx) return;
    const buf = buffers[name];
    if (buf) {
      const src = ctx.createBufferSource();
      src.buffer = buf;
      src.connect(master);
      src.start();
      return;
    }
    const seq = SYNTH_SEQUENCES[name];
    if (!seq) return;
    const type = name === 'wrong-soft' ? 'triangle' : 'sine';
    for (const [freq, at, dur] of seq) synthTone(freq, dur, at, type);
  }
  function setMuted(on) {
    muted = on;
    if (master) master.gain.value = on ? 0 : 0.45;
  }
  return { unlock, load, play, setMuted, isMuted: () => muted };
}
