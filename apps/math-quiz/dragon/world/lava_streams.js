import * as THREE from 'three';
import {
  TOTAL_STREAMS, MAX_PROGRESS, streamPath, streamSpec, buildStreamProgress,
  advanceStreamProgress, isStreamStopped, lavaActive,
} from '../sim/lava_quest.js';

// Five glowing lava ribbons from Mount Ember toward the nest. Each tip is
// clickable — finish a quiz to cool that stream. Progress pauses while inQuiz.
export function createLavaStreams(scene, { nestPos = new THREE.Vector3(0, 0, -2) } = {}) {
  const root = new THREE.Group();
  scene.add(root);
  const hotMat = new THREE.MeshBasicMaterial({ color: 0xff5722, transparent: true, opacity: 0.92 });
  const tipMat = new THREE.MeshBasicMaterial({ color: 0xffeb3b });
  const coolMat = new THREE.MeshStandardMaterial({ color: 0x6d6d6d, roughness: 1, flatShading: true });
  const streams = [];
  for (let k = 0; k < TOTAL_STREAMS; k++) {
    const group = new THREE.Group();
    const segments = [];
    for (let i = 0; i < 14; i++) {
      const seg = new THREE.Mesh(new THREE.SphereGeometry(0.22 + (i % 3) * 0.04, 6, 5), hotMat.clone());
      seg.visible = false;
      group.add(seg);
      segments.push(seg);
    }
    const tip = new THREE.Mesh(new THREE.SphereGeometry(0.38, 8, 6), tipMat.clone());
    tip.visible = false;
    group.add(tip);
    const coolRock = new THREE.Mesh(new THREE.DodecahedronGeometry(0.55), coolMat.clone());
    coolRock.visible = false;
    coolRock.position.y = 0.35;
    group.add(coolRock);
    root.add(group);
    streams.push({ k, group, segments, tip, coolRock, progress: 0, stopped: false });
  }

  let visible = false;
  let paused = false;
  let startPct = 0;
  const stopped = new Set();

  function labelFor(k) {
    return `Hurry! Quiz to cool this lava stream (${k + 1} of ${TOTAL_STREAMS})`;
  }
  function sync(state) {
    const lava = state.lava || {};
    visible = lavaActive(lava);
    startPct = lava.startPct != null ? lava.startPct : 0;
    stopped.clear();
    for (const k of lava.stopped || []) stopped.add(Number(k));
    for (const s of streams) {
      s.stopped = stopped.has(s.k);
      if (s.stopped) {
        s.progress = MAX_PROGRESS;
      } else if (s.progress <= 0 || !visible) {
        const spec = streamSpec(s.k);
        s.progress = Math.min(MAX_PROGRESS, startPct / 100 + spec.startBias);
      }
      s.group.visible = visible;
    }
    root.visible = visible;
    layoutAll();
  }
  function stopStream(k) {
    const s = streams[k];
    if (!s || s.stopped) return null;
    s.stopped = true;
    stopped.add(k);
    layoutStream(s);
    return s.tip.position.clone().add(new THREE.Vector3(0, 0.5, 0));
  }
  function layoutStream(s) {
    s.group.visible = visible;
    if (!visible) return;
    if (s.stopped) {
      for (const seg of s.segments) seg.visible = false;
      s.tip.visible = false;
      s.coolRock.visible = true;
      const p = streamPath(s.k, s.progress);
      s.coolRock.position.set(p.x, p.y + 0.2, p.z);
      return;
    }
    s.coolRock.visible = false;
    const steps = s.segments.length;
    for (let i = 0; i < steps; i++) {
      const frac = (i + 1) / (steps + 1);
      const t = Math.min(s.progress, frac);
      if (t <= 0) { s.segments[i].visible = false; continue; }
      const p = streamPath(s.k, t);
      s.segments[i].visible = true;
      s.segments[i].position.set(p.x, p.y, p.z);
      s.segments[i].material.opacity = 0.55 + 0.4 * (t / Math.max(s.progress, 0.01));
    }
    const tipP = streamPath(s.k, s.progress);
    s.tip.visible = s.progress > 0.02;
    s.tip.position.set(tipP.x, tipP.y + 0.25, tipP.z);
  }
  function layoutAll() {
    for (const s of streams) layoutStream(s);
  }
  function interactables() {
    if (!visible) return [];
    return streams.filter((s) => !s.stopped).map((s) => ({
      k: s.k, mesh: s.tip, label: labelFor(s.k),
    }));
  }
  function update(delta, opts = {}) {
    paused = !!opts.paused;
    if (!visible) return;
    const t = performance.now() * 0.001;
    for (const s of streams) {
      if (s.stopped) {
        s.coolRock.rotation.y += delta * 0.4;
        continue;
      }
      const spec = streamSpec(s.k);
      s.progress = advanceStreamProgress(s.progress, spec.rate, delta, paused);
      layoutStream(s);
      if (s.tip.visible) {
        s.tip.scale.setScalar(1 + Math.sin(t * 5 + s.k) * 0.12);
        s.tip.material.color.setHSL(0.08 + Math.sin(t * 3 + s.k) * 0.03, 1, 0.55);
      }
    }
  }
  function restoreProgressFromSave(lava) {
    const built = buildStreamProgress(lava || {});
    for (const s of streams) {
      const row = built[s.k];
      if (row && !row.stopped) s.progress = row.progress;
    }
    layoutAll();
  }
  return {
    root, sync, update, stopStream, interactables, restoreProgressFromSave,
    isStreamActive: (k) => visible && !isStreamStopped([...stopped], k),
  };
}
