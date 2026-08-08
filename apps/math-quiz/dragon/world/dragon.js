import * as THREE from 'three';
import { adultGrowthScale } from '../sim/growth_spurt.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const TARGET_GLB_HEIGHT = 0.85;
const LOOP_CLIPS = new Set(['idle', 'walk', 'fly']);
const ONE_SHOT_CLIPS = new Set(['hatch', 'play', 'wing-stretch', 'jump', 'fire']);
const HEAD_NODE_RE = /head|jaw|neck/i;
const FORM_PATHS = {
  baby: 'assets/models/dragon.glb',
  juvenile: 'assets/models/dragon-juvenile.glb',
  adult: 'assets/models/dragon-adult.glb',
};

function nextIdleVarietyDelay() {
  return 6 + Math.random() * 6;
}
function fitModelHeight(model) {
  model.updateMatrixWorld(true);
  const size = new THREE.Vector3();
  new THREE.Box3().setFromObject(model).getSize(size);
  if (Number.isFinite(size.y) && size.y > 0) model.scale.setScalar(TARGET_GLB_HEIGHT / size.y);
}
function buildActions(mixer, clips) {
  const actions = {};
  clips.forEach((clip) => {
    const key = clip.name.toLowerCase();
    const action = mixer.clipAction(clip);
    if (ONE_SHOT_CLIPS.has(key)) {
      action.setLoop(THREE.LoopOnce, 1);
      action.clampWhenFinished = true;
    } else if (LOOP_CLIPS.has(key)) {
      action.setLoop(THREE.LoopRepeat, Infinity);
      action.clampWhenFinished = false;
    }
    actions[key] = action;
  });
  return actions;
}
function buildProceduralDragon() {
  const group = new THREE.Group();
  const bodyMat = new THREE.MeshStandardMaterial({ color: 0x7b5ea7, roughness: 0.6 });
  const bellyMat = new THREE.MeshStandardMaterial({ color: 0xffccbc, roughness: 0.7 });
  const wingMat = new THREE.MeshStandardMaterial({ color: 0x9575cd, side: THREE.DoubleSide });
  const hornMat = new THREE.MeshStandardMaterial({ color: 0xffe082, roughness: 0.5 });
  const body = new THREE.Mesh(new THREE.SphereGeometry(0.35, 16, 12), bodyMat);
  body.scale.set(1, 0.9, 1.2);
  body.position.y = 0.35;
  body.castShadow = true;
  const belly = new THREE.Mesh(new THREE.SphereGeometry(0.28, 12, 10), bellyMat);
  belly.scale.set(0.9, 0.8, 1);
  belly.position.set(0, 0.3, 0.12);
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.24, 12, 10), bodyMat);
  head.position.set(0, 0.62, 0.35);
  head.castShadow = true;
  const snout = new THREE.Mesh(new THREE.SphereGeometry(0.11, 8, 8), bellyMat);
  snout.position.set(0, 0.55, 0.55);
  const eyeMat = new THREE.MeshStandardMaterial({ color: 0x111111 });
  const glintMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
  const eyeL = new THREE.Mesh(new THREE.SphereGeometry(0.055, 8, 8), eyeMat);
  eyeL.position.set(-0.1, 0.7, 0.5);
  const eyeR = eyeL.clone();
  eyeR.position.x = 0.1;
  const glintL = new THREE.Mesh(new THREE.SphereGeometry(0.018, 6, 6), glintMat);
  glintL.position.set(-0.085, 0.72, 0.545);
  const glintR = glintL.clone();
  glintR.position.x = 0.115;
  const hornL = new THREE.Mesh(new THREE.ConeGeometry(0.045, 0.16, 6), hornMat);
  hornL.position.set(-0.11, 0.86, 0.3);
  hornL.rotation.z = 0.25;
  const hornR = hornL.clone();
  hornR.position.x = 0.11;
  hornR.rotation.z = -0.25;
  const wingShape = new THREE.Shape();
  wingShape.moveTo(0, 0);
  wingShape.quadraticCurveTo(-0.28, 0.3, -0.58, 0.18);
  wingShape.quadraticCurveTo(-0.46, 0.04, -0.52, -0.08);
  wingShape.quadraticCurveTo(-0.32, -0.06, -0.3, -0.16);
  wingShape.quadraticCurveTo(-0.14, -0.1, 0, 0);
  const wingGeo = new THREE.ShapeGeometry(wingShape, 6);
  const wingL = new THREE.Mesh(wingGeo, wingMat);
  wingL.position.set(-0.18, 0.58, 0);
  wingL.rotation.y = 0.4;
  const wingR = new THREE.Mesh(wingGeo, wingMat);
  wingR.scale.x = -1;
  wingR.position.set(0.18, 0.58, 0);
  wingR.rotation.y = -0.4;
  const tail = new THREE.Mesh(new THREE.ConeGeometry(0.12, 0.55, 8), bodyMat);
  tail.rotation.x = Math.PI / 2 + 0.35;
  tail.position.set(0, 0.28, -0.48);
  group.add(body, belly, head, snout, eyeL, eyeR, glintL, glintR, hornL, hornR, wingL, wingR, tail);
  group.userData.wings = [wingL, wingR];
  group.userData.tail = tail;
  group.userData.head = head;
  wingL.scale.set(0.45, 0.45, 0.45);
  wingR.scale.set(-0.45, 0.45, 0.45);
  return group;
}

export async function createDragon(scene) {
  const root = new THREE.Group();
  root.visible = false;
  scene.add(root);
  const loader = new GLTFLoader();
  const rigs = {};
  let currentForm = 'baby';
  let model = null;
  let mixer = null;
  let actions = {};
  let baseState = 'idle';
  let currentAction = null;
  let activeOneShot = null;
  let idleRepertoire = [];
  let idleVarietyTimer = nextIdleVarietyDelay();
  let headNode = null;
  let proceduralOnly = false;
  async function loadGlbRig(form, path) {
    try {
      const gltf = await loader.loadAsync(path);
      if (!gltf.animations || !gltf.animations.length) return null;
      const rigModel = gltf.scene;
      fitModelHeight(rigModel);
      rigModel.traverse((c) => { if (c.isMesh) { c.castShadow = true; c.receiveShadow = true; } });
      rigModel.visible = false;
      root.add(rigModel);
      const rigMixer = new THREE.AnimationMixer(rigModel);
      const rigActions = buildActions(rigMixer, gltf.animations);
      console.log(`[dragon] ${form} GLB clips:`, Object.keys(rigActions).join(', '));
      return { model: rigModel, mixer: rigMixer, actions: rigActions, procedural: false };
    } catch (e) {
      console.info(`[dragon] no ${form} GLB (${path})`, e && e.message);
      return null;
    }
  }
  const loaded = await Promise.all(
    Object.entries(FORM_PATHS).map(async ([form, path]) => [form, await loadGlbRig(form, path)]),
  );
  for (const [form, rig] of loaded) {
    if (rig) rigs[form] = rig;
  }
  if (!rigs.baby) {
    proceduralOnly = true;
    const proc = buildProceduralDragon();
    root.add(proc);
    rigs.baby = { model: proc, mixer: null, actions: {}, procedural: true };
    rigs.juvenile = rigs.baby;
    rigs.adult = rigs.baby;
    console.info('[dragon] using procedural dragon for all life stages');
  }
  function bindRig(form) {
    const rig = rigs[form] || rigs.baby;
    currentForm = form in rigs ? form : 'baby';
    model = rig.model;
    mixer = rig.mixer;
    actions = rig.actions;
    headNode = null;
    for (const key of Object.keys(rigs)) rigs[key].model.visible = (key === currentForm);
  }
  bindRig('baby');
  for (const rig of Object.values(rigs)) {
    if (rig.mixer) rig.mixer.addEventListener('finished', onMixerFinished);
  }
  function setProceduralState(key) {
    if (model.userData.wings) model.userData.animState = key === 'hatch' ? 'idle' : key;
  }
  function clearOneShot({ resolve = true, stop = false } = {}) {
    if (!activeOneShot) return;
    const shot = activeOneShot;
    activeOneShot = null;
    if (stop) shot.action.stop();
    else shot.action.fadeOut(0.18);
    if (resolve) shot.resolve();
  }
  function playLoop(key) {
    const action = actions[key];
    baseState = key;
    if (activeOneShot) clearOneShot({ stop: activeOneShot.action === action });
    if (currentAction === action) return undefined;
    if (currentAction) currentAction.fadeOut(0.25);
    currentAction = action;
    action.reset().fadeIn(0.25).play();
    return undefined;
  }
  function returnToBase(fromAction) {
    if (fromAction) fromAction.fadeOut(0.25);
    const action = actions[baseState] || actions.idle;
    if (!action) {
      currentAction = null;
      return;
    }
    currentAction = action;
    action.reset().fadeIn(0.25).play();
  }
  function onMixerFinished(e) {
    if (!activeOneShot || e.action !== activeOneShot.action) return;
    const shot = activeOneShot;
    activeOneShot = null;
    shot.resolve();
    returnToBase(shot.action);
  }
  function playOnce(name) {
    const key = String(name).toLowerCase();
    if (mixer && actions[key] && !ONE_SHOT_CLIPS.has(key)) {
      playLoop(key);
      return Promise.resolve();
    }
    if (mixer && !actions[key]) return Promise.resolve();
    if (!mixer) {
      setProceduralState(key);
      return new Promise((resolve) => setTimeout(resolve, 1500));
    }
    const action = actions[key];
    return new Promise((resolve) => {
      if (activeOneShot) clearOneShot({ stop: activeOneShot.action === action });
      if (currentAction && currentAction !== action) currentAction.fadeOut(0.18);
      activeOneShot = { action, resolve };
      currentAction = action;
      action.enabled = true;
      action.setLoop(THREE.LoopOnce, 1);
      action.clampWhenFinished = true;
      action.reset().fadeIn(0.18).play();
    });
  }
  function playState(name) {
    const key = String(name).toLowerCase();
    if (mixer && actions[key]) {
      if (ONE_SHOT_CLIPS.has(key)) return playOnce(key);
      return playLoop(key);
    }
    setProceduralState(key);
    return undefined;
  }
  function setRepertoire(names) {
    idleRepertoire = Array.from(new Set((names || []).map((n) => String(n).toLowerCase())))
      .filter((name) => ONE_SHOT_CLIPS.has(name));
    idleVarietyTimer = nextIdleVarietyDelay();
  }
  function setForm(form) {
    const next = rigs[form] ? form : 'baby';
    if (next === currentForm) return;
    const resume = baseState;
    bindRig(next);
    if (proceduralOnly) applyProceduralStage(next);
    playState(resume);
  }
  function applyProceduralStage(form) {
    if (!model.userData.wings) return;
    const wings = model.userData.wings;
    if (form === 'baby') {
      wings[0].scale.set(0.45, 0.45, 0.45);
      wings[1].scale.set(-0.45, 0.45, 0.45);
    } else if (form === 'juvenile') {
      wings[0].scale.set(1.25, 1.25, 1.25);
      wings[1].scale.set(-1.25, 1.25, 1.25);
    } else {
      wings[0].scale.set(1.45, 1.45, 1.45);
      wings[1].scale.set(-1.45, 1.45, 1.45);
    }
  }
  function setGrowthScale(maxPct) {
    if (currentForm === 'baby') {
      const t = Math.max(0, Math.min(1, (maxPct - 60) / 10));
      root.scale.setScalar(0.55 + t * 0.4);
    } else if (currentForm === 'juvenile') {
      const t = Math.max(0, Math.min(1, (maxPct - 70) / 10));
      root.scale.setScalar(0.92 + t * 0.08);
    } else {
      root.scale.setScalar(adultGrowthScale(maxPct));
    }
  }
  function growWings() {
    setForm('juvenile');
  }
  function update(delta) {
    if (mixer) mixer.update(delta);
    if (mixer && root.visible && baseState === 'idle' && !activeOneShot && idleRepertoire.length) {
      idleVarietyTimer -= delta;
      if (idleVarietyTimer <= 0) {
        const choices = idleRepertoire.filter((name) => actions[name]);
        if (choices.length) playOnce(choices[Math.floor(Math.random() * choices.length)]);
        idleVarietyTimer = nextIdleVarietyDelay();
      }
    }
    if (model.userData.wings) {
      const state = model.userData.animState || 'idle';
      const t = performance.now() * 0.003;
      const flap = (state === 'fly' || state === 'wing-stretch') ? Math.sin(t * 8) * 0.55 : Math.sin(t * 2) * 0.08;
      model.userData.wings[0].rotation.z = flap;
      model.userData.wings[1].rotation.z = -flap;
      if (model.userData.tail) model.userData.tail.rotation.y = Math.sin(t * 3) * 0.25;
      if (state === 'walk') model.position.y = Math.abs(Math.sin(t * 6)) * 0.04;
      else if (state === 'play') model.position.y = Math.abs(Math.sin(t * 5)) * 0.12;
      else if (state === 'jump') model.position.y = Math.abs(Math.sin(t * 4)) * 0.5;
      else if (state === 'fire') model.position.y = Math.abs(Math.sin(t * 2.5)) * 0.05;
      else model.position.y = Math.sin(t * 1.5) * 0.015;
    }
  }
  function headPosition() {
    if (!headNode && !model.userData.head) {
      model.traverse((node) => {
        if (!headNode && HEAD_NODE_RE.test(node.name || '')) headNode = node;
      });
    }
    const head = model.userData.head || headNode;
    if (!head) return root.position.clone().add(new THREE.Vector3(0, 0.6, 0));
    return head.getWorldPosition(new THREE.Vector3());
  }
  return {
    root,
    show: () => { root.visible = true; },
    hide: () => { root.visible = false; },
    playState,
    playOnce,
    setRepertoire,
    setForm,
    setGrowthScale,
    growWings,
    headPosition,
    update,
    getRoot: () => root,
    getForm: () => currentForm,
    isVisible: () => root.visible,
  };
}
