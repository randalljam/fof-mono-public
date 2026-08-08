file: apps/minecraft/flat-all-dimensions-world-preset.md
title: Flat All Dimensions world preset (Minecraft 26.2)
last-updated: 2026-07-04_0720
ai: Cursor - Composer 2.5 Fast
session: Flat all dimensions Prism instance setup


## Context
The screenshot Java code is from Minecraft's internal `WorldPresets` class — it shows how a **mod or datapack** could register a built-in "Flat All Dimensions" preset in the Create World UI. The video's shortcut skips that: create a normal superflat world, quit the game, and **direct-edit the world save NBT** so Nether and End (and optionally Overworld) use flat generators too.


## Source screenshot — OCR text
```java
public class WorldPresets {
    private static class Bootstrap {

        private void registerCustomOverworldPreset(final ResourceKey<WorldPreset> debug, final LevelStem overworld) {
            this.context.register(debug, this.createPresetWithCustomOverworld(overworld));
        }

        private void registerOverworlds(final BiomeSource biomeSource) {
            Holder<NoiseGeneratorSettings> overworldNoiseSettings = this.noiseSettings.getOrThrow(NoiseGeneratorSettings.OVERWORLD);
            this.registerCustomOverworldPreset(WorldPresets.NORMAL, this.makeNoiseBasedOverworld(biomeSource, overworldNoiseSettings));
            Holder<NoiseGeneratorSettings> largeBiomesNoiseSettings = this.noiseSettings.getOrThrow(NoiseGeneratorSettings.LARGE_BIOMES);
            this.registerCustomOverworldPreset(WorldPresets.LARGE_BIOMES, this.makeNoiseBasedOverworld(biomeSource, largeBiomesNoiseSettings));
            Holder<NoiseGeneratorSettings> amplifiedNoiseSettings = this.noiseSettings.getOrThrow(NoiseGeneratorSettings.AMPLIFIED);
            this.registerCustomOverworldPreset(WorldPresets.AMPLIFIED, this.makeNoiseBasedOverworld(biomeSource, amplifiedNoiseSettings));
        }

        public void bootstrap() {
            Holder.Reference<MultiNoiseBiomeSourceParameterList> overworldPreset = this.multiNoiseBiomeSourceParameterLists.getOrThrow(MultiNoiseBiomeSourceParameterLists.OVERWORLD);
            this.registerOverworlds(MultiNoiseBiomeSource.createFromPreset(overworldPreset));
            Holder<NoiseGeneratorSettings> overworldNoiseSettings = this.noiseSettings.getOrThrow(NoiseGeneratorSettings.OVERWORLD);
            Holder.Reference<Biome> plains = this.biomes.getOrThrow(Biomes.PLAINS);
            this.registerCustomOverworldPreset(WorldPresets.SINGLE_BIOME_SURFACE, this.makeNoiseBasedOverworld(new FixedBiomeSource(plains), overworldNoiseSettings));
            this.registerCustomOverworldPreset(WorldPresets.FLAT, this.makeOverworld(new FlatLevelSource(FlatLevelGeneratorSettings.getDefault(this.biomes, this.structureSets, this.placedFeatures))));
            this.context.register(WorldPresets.FLAT_ALL_DIMENSIONS, this.createFlatAllDimensionsPreset());
            this.registerCustomOverworldPreset(WorldPresets.DEBUG, this.makeOverworld(new DebugLevelSource(plains)));
        }

        private FlatLevelGeneratorSettings flatSettingsForBiomeAndLayers(final ResourceKey<Biome> biomeKey, final List<FlatLayerInfo> layers) {
            return FlatLevelGeneratorSettings.getDefault(this.biomes, this.structureSets, this.placedFeatures).withBiomeAndLayers(layers, Optional.empty(), this.biomes.getOrThrow(biomeKey));
        }

        private WorldPreset createFlatAllDimensionsPreset() {
            LevelStem overworldFlat = this.makeOverworld(new FlatLevelSource(this.flatSettingsForBiomeAndLayers(Biomes.DESERT, List.of(new FlatLayerInfo(1, Blocks.BEDROCK), new FlatLayerInfo(67, Blocks.SANDSTONE)))));
            LevelStem netherFlat = this.makeNether(new FlatLevelSource(this.flatSettingsForBiomeAndLayers(Biomes.BASALT_DELTAS, List.of(new FlatLayerInfo(1, Blocks.BEDROCK), new FlatLayerInfo(3, Blocks.BASALT)))));
            LevelStem endFlat = this.makeEnd(new FlatLevelSource(this.flatSettingsForBiomeAndLayers(Biomes.THE_END, List.of(new FlatLayerInfo(1, Blocks.BEDROCK), new FlatLayerInfo(3, Blocks.END_STONE)))));
            return new WorldPreset(Map.of(LevelStem.OVERWORLD, overworldFlat, LevelStem.NETHER, netherFlat, LevelStem.END, endFlat));
        }
    }
}
```


## Preset summary (from the Java code)
| Dimension | Biome | Layers (bottom → top) |
|-----------|-------|------------------------|
| Overworld | `minecraft:desert` | 1× bedrock, 67× sandstone |
| Nether | `minecraft:basalt_deltas` | 1× bedrock, 3× basalt |
| End | `minecraft:the_end` | 1× bedrock, 3× end_stone |


## Which file to edit (Minecraft 26.2)
In Minecraft **26.1+**, world generation settings live in a separate file — not in `level.dat`.

| Minecraft version | File to edit |
|-------------------|--------------|
| 1.16 – 26.0 | `saves/<WorldName>/level.dat` → `Data` → `WorldGenSettings` |
| **26.1 and later (including 26.2)** | `saves/<WorldName>/data/minecraft/world_gen_settings.dat` |

For each dimension under `data` → `dimensions`:

- Set `generator` → `type` to `minecraft:flat`
- Set `generator` → `settings` → `biome` and `layers` (remove noise `biome_source` / string `settings` if present)
- Layers are bottom-first: each entry is `{ block, height }`


## Applied edit — Flatworld (2026-07-04)
**Instance:** `26.2 Flat All Dimensions`
**Path:** `~/Library/Application Support/PrismLauncher/instances/26.2 Flat All Dimensions/`
**World:** `Flatworld` (created in-game as classic superflat, then edited offline)

### Starting state (from in-game superflat create)

| Dimension | Generator |
|-----------|-----------|
| Overworld | `minecraft:flat` — classic preset (bedrock + dirt + grass, plains) |
| Nether | `minecraft:noise` |
| End | `minecraft:noise` |

### File changed

| File | Action |
|------|--------|
| `minecraft/saves/Flatworld/data/minecraft/world_gen_settings.dat` | **Edited** — all three dimensions set to flat per preset table above |
| `minecraft/saves/Flatworld/data/minecraft/world_gen_settings.dat_before_flat_all_dimensions` | **Backup** of pre-edit file |

### Chunk cleanup (so new terrain generates)

Removed existing overworld region/entity/poi `.mca` files under `dimensions/minecraft/overworld/` — the world had already generated classic-flat chunks; deleting them forces regeneration with the new desert/sandstone layers. Nether and End had not been explored yet, so no region files to remove there.

### Deleted
The agent-created `minecraft/saves/Flat All Dimensions/` world folder was removed (no longer needed).


## Manual workflow (NBT editor, future worlds)
1. Create a **Superflat** world in the 26.2 instance (any flat preset is fine — you will edit all dimensions).
2. Quit Minecraft completely.
3. Open NBTExplorer and go to:
   `…/instances/26.2 Flat All Dimensions/minecraft/saves/<WorldName>/data/minecraft/world_gen_settings.dat`
4. Expand `data` → `dimensions`.
5. For `minecraft:overworld`, `minecraft:the_nether`, and `minecraft:the_end`:
   - Set `generator` → `type` = `minecraft:flat`
   - Replace `generator` → `settings` with a compound: `biome`, `layers` (and optionally `features`/`lakes` as byte 0)
   - Remove any `biome_source` sibling tag under `generator`
6. Save. If the world was already played, delete generated chunk files for affected dimensions under `dimensions/minecraft/<dim>/region/` (and `entities/`, `poi/` if present) so terrain regenerates.

### Example flat generator block (Nether)

```json
{
  "type": "minecraft:flat",
  "settings": {
    "biome": "minecraft:basalt_deltas",
    "layers": [
      { "block": "minecraft:bedrock", "height": 1 },
      { "block": "minecraft:basalt", "height": 3 }
    ]
  }
}
```

(NBT editors show compounds/lists, not JSON, but field names match.)
