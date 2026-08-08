// Volcano quest logic: DOM/THREE-free math shared by the world meshes
// (world/mountains.js, world/boulders.js), main.js, and the unit tests.
//
// Mount Ember was a decorative cone on the horizon; the quest turns it into a
// real climbable volcano — a truncated cone with a lava plateau on top — plus
// five boulder blockades up the south face. Each uncleared blockade gates how
// close to the summit axis the player can get (a "block radius"); finishing a
// quiz smashes the lowest boulder and lets the climb continue.

export const VOLCANO = {
  x: 0,
  z: -92,          // due north of the nest, past the old backdrop position
  baseR: 22,       // radius where the slope meets the ground
  topR: 3.5,       // plateau radius at the summit
  height: 26,      // plateau height above the ground plane
};
export const TOTAL_BOULDERS = 5;

// The distant mountain ring (previously backdrop-only triangles in ambient.js).
// Same deterministic formula, now shared so the terrain height includes them
// and every peak can be walked up.
export function ringMountainSpecs() {
  const specs = [];
  for (let i = 0; i < 12; i++) {
    const angle = (i / 12) * Math.PI * 2 + 0.26;
    const r = 78 + (i % 3) * 8;
    const h = 14 + ((i * 7) % 5) * 4;
    specs.push({
      x: Math.cos(angle) * r,
      z: Math.sin(angle) * r,
      radius: 9 + (i % 4) * 2,
      height: h,
    });
  }
  return specs;
}
const RING = ringMountainSpecs();

function volcanoHeightAt(x, z) {
  const d = Math.hypot(x - VOLCANO.x, z - VOLCANO.z);
  if (d >= VOLCANO.baseR) return 0;
  if (d <= VOLCANO.topR) return VOLCANO.height;
  return VOLCANO.height * (VOLCANO.baseR - d) / (VOLCANO.baseR - VOLCANO.topR);
}
// Walkable ground height at (x, z): the tallest of the volcano and the ring
// cones (ring cone bases sit 1 unit below ground, hence the -1).
export function terrainHeightAt(x, z) {
  let h = volcanoHeightAt(x, z);
  for (const m of RING) {
    const d = Math.hypot(x - m.x, z - m.z);
    if (d >= m.radius) continue;
    const ch = m.height * (1 - d / m.radius) - 1;
    if (ch > h) h = ch;
  }
  return Math.max(0, h);
}

// Boulder blockades up the south face (facing the nest): distance from the
// summit axis shrinks stage by stage, azimuth zigzags a little so the path
// reads as a trail instead of a straight line.
export const BOULDER_STAGES = [
  { az: 0.0, d: 20.0 },
  { az: 0.3, d: 16.3 },
  { az: -0.28, d: 12.6 },
  { az: 0.22, d: 8.9 },
  { az: -0.15, d: 5.6 },
];
export function boulderPos(k) {
  const s = BOULDER_STAGES[k];
  const x = VOLCANO.x + Math.sin(s.az) * s.d;
  const z = VOLCANO.z + Math.cos(s.az) * s.d;
  return { x, z, y: terrainHeightAt(x, z) };
}
// While `cleared` boulders are smashed, the player may not get closer to the
// summit axis than a couple of units outside the next boulder — close enough
// to click it (interact range 6), far enough back that it sits in view.
export function blockRadius(cleared) {
  if (cleared >= TOTAL_BOULDERS) return null;
  return BOULDER_STAGES[Math.max(0, cleared)].d + 2.5;
}
export function atSummit(x, z) {
  return Math.hypot(x - VOLCANO.x, z - VOLCANO.z) <= VOLCANO.topR + 0.8;
}
// Sparkle-trail destination: the next boulder to smash, then the summit.
export function trailTarget(cleared) {
  if (cleared < TOTAL_BOULDERS) return boulderPos(cleared);
  return { x: VOLCANO.x, z: VOLCANO.z, y: VOLCANO.height };
}
