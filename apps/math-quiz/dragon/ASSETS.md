# Dragon Fluency Game — Asset Manifest

All binary assets live in `assets/` (gitignored). This file is tracked and records provenance.


## 3D models

| File | Source | License | Notes |
|------|--------|---------|-------|
| `assets/models/dragon.glb` | `apps/content_studio/_data/profiles/math-quiz-dragon-baby/approved/dragon.glb`, copied to `apps/math-quiz/dragon/assets/models/dragon.glb` | Project-local generated asset | Rigged/animated **baby** dragon (hatch through 69%). Runtime auto-adopts when present with clips; falls back to procedural otherwise. Clips: `hatch` 2.5s, `idle` 2.0s, `walk` 1.0s, `play` 1.5s, `wing-stretch` 2.0s, `jump` 1.21s, `fire` 1.5s, `fly` 1.0s |
| `assets/models/dragon-juvenile.glb` | same approved profile dir | Project-local generated asset | **Juvenile** form — swaps in at the 70% milestone (`wings`). Same clip names as baby. |
| `assets/models/dragon-adult.glb` | same approved profile dir | Project-local generated asset | **Adult** form — swaps in at the 80% milestone (`jump`). Same clip names as baby. |
| *(procedural fallback)* | Generated in `world/dragon.js` | N/A (code) | Cute purple baby dragon (horns, eye glints, belly) with procedural wing-flap, tail-wag, walk-bob, jump-bob, play-bob, fire-bob, and breathing idle. Used automatically when `dragon.glb` is absent or has no animation clips |


## Environment

| File | Source | License | Notes |
|------|--------|---------|-------|
| `assets/hdri/sky.hdr` | [Poly Haven — venice_sunset 1k](https://polyhaven.com/a/venice_sunset) | CC0 | Optional environment lighting (loaded when present) |
| Nest/trees/meadow/grove/hills | Procedural geometry in `world/environment.js` | N/A (code) | Meadow flowers/grass, grove trees + glow mushrooms, Whispering Hills mounds |
| Mountains, Mount Ember, clouds, birds, campfire, pond, butterflies, fireflies | Procedural geometry in `world/ambient.js` | N/A (code) | Primitive-built ambient life (The Aviator-style groups of flat-shaded meshes) |
| Story Stones, sparkle trails, beacon | Procedural geometry in `world/journey.js` | N/A (code) | The dragon-road journey layer |


## Audio

| File | Source | License | Notes |
|------|--------|---------|-------|
| `assets/audio/click1.ogg` | [Kenney UI Audio](https://kenney.nl/assets/ui-audio) | CC0 | UI click |
| `assets/audio/confirmation_001.ogg` | Kenney UI Audio | CC0 | Correct-answer chime |
| `assets/audio/drop_001.ogg` | Kenney UI Audio | CC0 | Soft wrong-answer tone |
| *(synthesized fallback)* | Generated in `audio/audio.js` | N/A (code) | Web Audio oscillators when OGG files absent |
| `assets/audio/music_loop.ogg` | *(optional — add Kevin MacLeod CC-BY track locally)* | CC-BY if added | Background music; game runs without it |


## Animation mapping (`world/dragon.js`)

When GLB clips exist, names are matched case-insensitively. `idle`, `walk`, and `fly` loop as base states. `hatch`, `play`, `wing-stretch`, `jump`, and `fire` are one-shots that return to the current base state. Procedural fallback maps the same state names to wing motion, body bob, tail wag, and breathing idle where available.


## Provisioning

`assets/` is gitignored. Starting `tools/dev_server.py` auto-copies the three Pipa life-stage GLBs from the content_studio approved profile into `assets/models/` when they are missing (`tools/dragon_assets.py`). Manual copy still works for a static server:

```bash
mkdir -p apps/math-quiz/dragon/assets/{models,audio,hdri}
cp apps/content_studio/_data/profiles/math-quiz-dragon-baby/approved/dragon.glb apps/math-quiz/dragon/assets/models/dragon.glb
cp apps/content_studio/_data/profiles/math-quiz-dragon-baby/approved/dragon-juvenile.glb apps/math-quiz/dragon/assets/models/dragon-juvenile.glb
cp apps/content_studio/_data/profiles/math-quiz-dragon-baby/approved/dragon-adult.glb apps/math-quiz/dragon/assets/models/dragon-adult.glb
curl -fsSL -o apps/math-quiz/dragon/assets/hdri/sky.hdr \
  "https://dl.polyhaven.org/file/ph-assets/HDRIs/hdr/1k/venice_sunset_1k.hdr"
# Kenney UI Audio: download zip from https://kenney.nl/assets/ui-audio and extract Audio/*.ogg into assets/audio/
```
