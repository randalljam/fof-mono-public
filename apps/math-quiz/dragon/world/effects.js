import * as THREE from 'three';

export function createEffects(scene) {
  const particles = [];
  function burstSparkles(position, color = 0xffd54f, count = 24) {
    for (let i = 0; i < count; i++) {
      const mesh = new THREE.Mesh(
        new THREE.SphereGeometry(0.04, 4, 4),
        new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.9 })
      );
      mesh.position.copy(position);
      mesh.userData.vel = new THREE.Vector3(
        (Math.random() - 0.5) * 2,
        Math.random() * 2,
        (Math.random() - 0.5) * 2
      );
      mesh.userData.life = 1;
      scene.add(mesh);
      particles.push(mesh);
    }
  }
  function confetti() {
    burstSparkles(new THREE.Vector3(0, 2, -2), 0xff6b9d, 40);
    burstSparkles(new THREE.Vector3(0.5, 2.2, -1.5), 0x7b5ea7, 30);
  }
  function update(delta) {
    for (let i = particles.length - 1; i >= 0; i--) {
      const p = particles[i];
      p.userData.life -= delta * 0.8;
      p.position.addScaledVector(p.userData.vel, delta);
      p.userData.vel.y -= delta * 2;
      p.material.opacity = Math.max(0, p.userData.life);
      if (p.userData.life <= 0) {
        scene.remove(p);
        p.geometry.dispose();
        p.material.dispose();
        particles.splice(i, 1);
      }
    }
  }
  return { burstSparkles, confetti, update };
}
