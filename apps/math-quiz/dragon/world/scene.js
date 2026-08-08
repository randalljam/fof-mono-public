import * as THREE from 'three';
import { RGBELoader } from 'three/addons/loaders/RGBELoader.js';

export function createScene(container) {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x87ceeb);
  scene.fog = new THREE.Fog(0x87ceeb, 40, 170);
  const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 200);
  camera.rotation.order = 'YXZ'; // match FPS look / handoff pose (yaw/pitch, no roll)
  camera.position.set(0, 1.6, 5);
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  container.appendChild(renderer.domElement);
  const ambient = new THREE.AmbientLight(0xffffff, 0.45);
  scene.add(ambient);
  const sun = new THREE.DirectionalLight(0xfff5e6, 1.1);
  sun.position.set(20, 35, 15);
  sun.castShadow = true;
  sun.shadow.mapSize.width = 2048;
  sun.shadow.mapSize.height = 2048;
  sun.shadow.camera.near = 0.5;
  sun.shadow.camera.far = 80;
  sun.shadow.camera.left = -30;
  sun.shadow.camera.right = 30;
  sun.shadow.camera.top = 30;
  sun.shadow.camera.bottom = -30;
  scene.add(sun);
  // Reaches under the mountain ring (r ~78-94 + cone radii) so the walk to
  // Mount Ember never steps off the edge of the world.
  const groundGeo = new THREE.PlaneGeometry(260, 260);
  const groundMat = new THREE.MeshStandardMaterial({ color: 0x5a8f4a, roughness: 0.9 });
  const ground = new THREE.Mesh(groundGeo, groundMat);
  ground.rotation.x = -Math.PI / 2;
  ground.receiveShadow = true;
  scene.add(ground);
  const clock = new THREE.Clock();
  loadHdri(scene, renderer);
  function onResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  }
  window.addEventListener('resize', onResize);
  return { scene, camera, renderer, clock, sun, ground, onResize };
}
async function loadHdri(scene, renderer) {
  try {
    const tex = await new RGBELoader().loadAsync('assets/hdri/sky.hdr');
    tex.mapping = THREE.EquirectangularReflectionMapping;
    scene.environment = tex;
    scene.background = tex;
  } catch (e) {
    console.warn('[dragon] HDRI not loaded', e);
  }
}
