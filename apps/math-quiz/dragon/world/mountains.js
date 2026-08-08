import * as THREE from 'three';
import { VOLCANO, ringMountainSpecs, terrainHeightAt } from '../sim/volcano_quest.js';

// The mountain ring + Mount Ember, moved out of ambient.js and made real:
// geometry matches sim/volcano_quest.js terrainHeightAt so every peak can be
// walked up. Mount Ember is a truncated cone with a lava plateau, a summit
// flag, and the smoke column that anchors the story.
const PALETTE = {
  // ember is lighter than the old backdrop cone — the player now stands on it.
  peak: 0x8d99ae, snow: 0xf5f7fa, ember: 0x7a5560, emberGlow: 0xff7043,
  lava: 0xff5722, smoke: 0xcfd8dc,
};

export function createMountains(scene) {
  const root = new THREE.Group();
  scene.add(root);

  // --- Mountain ring (climbable, still the horizon backdrop) ---
  for (const [i, m] of ringMountainSpecs().entries()) {
    const peak = new THREE.Mesh(
      new THREE.ConeGeometry(m.radius, m.height, 6),
      new THREE.MeshStandardMaterial({ color: PALETTE.peak, roughness: 1, flatShading: true })
    );
    peak.position.set(m.x, m.height / 2 - 1, m.z);
    const snow = new THREE.Mesh(
      new THREE.ConeGeometry(3.2, m.height * 0.28, 6),
      new THREE.MeshStandardMaterial({ color: PALETTE.snow, roughness: 0.9, flatShading: true })
    );
    snow.position.set(m.x, m.height - m.height * 0.14 - 1, m.z);
    snow.rotation.y = i * 0.5;
    root.add(peak, snow);
  }

  // --- Mount Ember: truncated cone + lava plateau + flag + smoke ---
  const ember = new THREE.Group();
  ember.name = 'mount-ember';
  const body = new THREE.Mesh(
    new THREE.CylinderGeometry(VOLCANO.topR, VOLCANO.baseR, VOLCANO.height, 9),
    new THREE.MeshStandardMaterial({ color: PALETTE.ember, roughness: 1, flatShading: true })
  );
  body.position.y = VOLCANO.height / 2 - 0.1;
  const lava = new THREE.Mesh(
    new THREE.CircleGeometry(VOLCANO.topR * 0.72, 12),
    new THREE.MeshBasicMaterial({ color: PALETTE.lava })
  );
  lava.rotation.x = -Math.PI / 2;
  lava.position.y = VOLCANO.height + 0.03;
  const glow = new THREE.Mesh(
    new THREE.SphereGeometry(0.7, 8, 6),
    new THREE.MeshBasicMaterial({ color: PALETTE.emberGlow })
  );
  glow.position.y = VOLCANO.height + 0.35;
  const glowLight = new THREE.PointLight(0xff7043, 1.4, 14, 2);
  glowLight.position.y = VOLCANO.height + 1.2;
  ember.add(body, lava, glow, glowLight);
  // Summit flag: the visible goal at the top of the climb.
  const flag = new THREE.Group();
  const pole = new THREE.Mesh(
    new THREE.CylinderGeometry(0.05, 0.07, 2.4, 6),
    new THREE.MeshStandardMaterial({ color: 0x8d6e63, roughness: 1 })
  );
  pole.position.y = 1.2;
  const pennant = new THREE.Mesh(
    new THREE.PlaneGeometry(1.1, 0.55),
    new THREE.MeshBasicMaterial({ color: 0xffc107, side: THREE.DoubleSide })
  );
  pennant.position.set(0.55, 2.05, 0);
  flag.add(pole, pennant);
  flag.position.set(2.2, VOLCANO.height, 1.6);
  ember.add(flag);
  ember.position.set(VOLCANO.x, 0, VOLCANO.z);
  root.add(ember);

  const emberSmoke = [];
  const smokeMat = new THREE.MeshBasicMaterial({ color: PALETTE.smoke, transparent: true, opacity: 0.5 });
  for (let i = 0; i < 4; i++) {
    const puff = new THREE.Mesh(new THREE.SphereGeometry(1.6, 6, 5), smokeMat.clone());
    puff.userData.phase = i / 4;
    ember.add(puff);
    emberSmoke.push(puff);
  }

  function update(delta) {
    const t = performance.now() * 0.001;
    for (const puff of emberSmoke) {
      const p = ((t * 0.06) + puff.userData.phase) % 1;
      puff.position.set(Math.sin(p * 9) * 1.5, VOLCANO.height + 1 + p * 14, Math.cos(p * 7));
      puff.scale.setScalar(0.6 + p * 2.2);
      puff.material.opacity = 0.5 * (1 - p);
    }
    pennant.rotation.y = Math.sin(t * 2.2) * 0.35;
    glow.scale.setScalar(1 + Math.sin(t * 3.1) * 0.12);
  }
  return { root, update, heightAt: terrainHeightAt };
}
