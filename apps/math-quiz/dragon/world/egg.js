import * as THREE from 'three';

export function createEgg(scene, nestGroup) {
  const group = new THREE.Group();
  group.position.set(0, 0.55, 0);
  const eggGeo = new THREE.SphereGeometry(0.45, 24, 24);
  eggGeo.scale(1, 1.25, 1);
  const eggMat = new THREE.MeshStandardMaterial({
    color: 0xffe0b2,
    emissive: 0x332211,
    emissiveIntensity: 0.15,
    roughness: 0.4,
  });
  const mesh = new THREE.Mesh(eggGeo, eggMat);
  mesh.castShadow = true;
  group.add(mesh);
  // Speckles so the egg reads as a creature egg, not a plain ball.
  const speckleMat = new THREE.MeshStandardMaterial({ color: 0xbf8f5f, roughness: 0.6 });
  for (let i = 0; i < 7; i++) {
    const s = new THREE.Mesh(new THREE.SphereGeometry(0.035 + (i % 3) * 0.012, 5, 4), speckleMat);
    const theta = (i / 7) * Math.PI * 2 + 0.5;
    const phi = 0.6 + (i % 4) * 0.45;
    s.position.setFromSphericalCoords(0.455, phi, theta);
    s.position.y *= 1.25;
    s.scale.z = 0.3;
    s.lookAt(0, s.position.y, 0);
    mesh.add(s);
  }
  // Crack lines revealed in stages as fluency approaches the hatch (thin dark
  // slats laid on the shell): stage 0 = pristine … 3 = about to burst.
  const crackMat = new THREE.MeshBasicMaterial({ color: 0x4e342e });
  const crackStages = [[], [], []];
  const CRACK_SPECS = [
    [{ phi: 0.85, theta: 0.4, len: 0.22, rot: 0.7 }, { phi: 1.0, theta: 0.75, len: 0.16, rot: -0.5 }],
    [{ phi: 1.35, theta: 2.4, len: 0.26, rot: 0.2 }, { phi: 1.2, theta: 2.9, len: 0.18, rot: 1.1 }, { phi: 0.7, theta: 3.6, len: 0.2, rot: -0.9 }],
    [{ phi: 1.6, theta: 4.8, len: 0.3, rot: 0.5 }, { phi: 1.8, theta: 5.4, len: 0.22, rot: -0.4 }, { phi: 0.5, theta: 5.9, len: 0.24, rot: 0.9 }],
  ];
  CRACK_SPECS.forEach((specs, stageIdx) => {
    for (const spec of specs) {
      const crack = new THREE.Mesh(new THREE.BoxGeometry(spec.len, 0.014, 0.01), crackMat);
      crack.position.setFromSphericalCoords(0.452, spec.phi, spec.theta);
      crack.position.y *= 1.25;
      crack.lookAt(0, crack.position.y, 0);
      crack.rotateZ(spec.rot);
      crack.visible = false;
      mesh.add(crack);
      crackStages[stageIdx].push(crack);
    }
  });
  let crackStage = 0;
  function setCrackStage(stage) {
    crackStage = Math.max(0, Math.min(3, Math.round(stage)));
    crackStages.forEach((cracks, i) => {
      for (const c of cracks) c.visible = i < crackStage;
    });
  }
  // 0..1 how close the hatch is — drives wobble/pulse excitement.
  let closeness = 0;
  function setHatchCloseness(frac) {
    closeness = Math.max(0, Math.min(1, frac));
  }
  nestGroup.add(group);
  let wobbleT = 0;
  let hatched = false;
  function update(delta) {
    if (hatched) return;
    wobbleT += delta;
    const speed = 2 + closeness * 3;
    group.rotation.z = Math.sin(wobbleT * speed) * (0.03 + closeness * 0.05);
    // Inviting warm pulse so the egg reads as "click me" — faster near hatching.
    eggMat.emissiveIntensity = 0.15 + (Math.sin(wobbleT * (1.6 + closeness * 2.4)) + 1) * (0.12 + closeness * 0.08);
  }
  async function playHatch(onFlash) {
    hatched = true;
    setCrackStage(3);
    const steps = 30;
    for (let i = 0; i < steps; i++) {
      group.rotation.z = Math.sin(i * 0.8) * 0.12;
      mesh.scale.setScalar(1 + Math.sin(i * 0.5) * 0.05);
      await new Promise((r) => requestAnimationFrame(r));
    }
    if (onFlash) await onFlash();
    group.visible = false;
  }
  function hide() { group.visible = false; }
  function show() { if (!hatched) group.visible = true; }
  return { group, mesh, update, playHatch, hide, show, setCrackStage, setHatchCloseness, isHatched: () => hatched };
}
