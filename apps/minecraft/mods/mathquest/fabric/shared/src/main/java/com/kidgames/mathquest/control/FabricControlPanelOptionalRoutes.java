package com.kidgames.mathquest.control;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.kidgames.mathquest.control.http.ControlPanelBridge;
import com.kidgames.mathquest.control.http.MathQuestHttpRouter;
import com.kidgames.mathquest.control.http.MathQuestHttpStatusBuilder;
import com.kidgames.mathquest.control.http.MathQuestHttpUtil;
import com.kidgames.mathquest.quest.CaveEscapeQuestService;
import com.sun.net.httpserver.HttpExchange;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntitySpawnReason;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.biome.Biome;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.phys.AABB;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * Fabric-only optional control-panel routes: terrain map, mob admin tools, quest API.
 * FROZEN: quest deferred past M6 (see docs/multi-version-tools + M5 plan). Not registered on Forge.
 */
public final class FabricControlPanelOptionalRoutes {
    private FabricControlPanelOptionalRoutes() {}

    public static void register(MathQuestHttpRouter router, ControlPanelBridge bridge) {
        FabricControlPanelBridge fabricBridge = (FabricControlPanelBridge) bridge;
        MinecraftServer server = fabricBridge.minecraftServer();
        router.register("GET", "/api/terrain-map.png", ex -> {
            byte[] png = MathQuestHttpUtil.onServerThread(bridge.platformServer(),
                () -> terrainMapPng(server, ex.getRequestURI().getRawQuery()));
            MathQuestHttpUtil.sendBytes(ex, 200, png, "image/png");
        });
        router.register("GET", "/api/quest/status", ex -> MathQuestHttpUtil.sendJson(ex,
            MathQuestHttpUtil.onServerThread(bridge.platformServer(),
                () -> CaveEscapeQuestService.status(server))));
        router.register("POST", "/api/quest/start", ex -> {
            try {
                JsonObject body = MathQuestHttpUtil.readJson(ex);
                MathQuestHttpUtil.sendJson(ex, MathQuestHttpUtil.onServerThread(bridge.platformServer(),
                    () -> CaveEscapeQuestService.start(body, server)));
            } catch (IOException e) {
                MathQuestHttpUtil.sendError(ex, 500, e.getMessage());
            }
        });
        router.register("POST", "/api/quest/save", ex -> {
            try {
                JsonObject body = MathQuestHttpUtil.readJson(ex);
                MathQuestHttpUtil.sendJson(ex, MathQuestHttpUtil.onServerThread(bridge.platformServer(),
                    () -> CaveEscapeQuestService.save(body, server)));
            } catch (IOException e) {
                MathQuestHttpUtil.sendError(ex, 500, e.getMessage());
            }
        });
        router.register("POST", "/api/quest/action", ex -> {
            try {
                JsonObject body = MathQuestHttpUtil.readJson(ex);
                MathQuestHttpUtil.sendJson(ex, MathQuestHttpUtil.onServerThread(bridge.platformServer(),
                    () -> CaveEscapeQuestService.action(body, server)));
            } catch (IOException e) {
                MathQuestHttpUtil.sendError(ex, 500, e.getMessage());
            }
        });
        router.register("POST", "/api/quest/command-suggestions", ex -> {
            try {
                JsonObject body = MathQuestHttpUtil.readJson(ex);
                MathQuestHttpUtil.sendJson(ex, MathQuestHttpUtil.onServerThread(bridge.platformServer(),
                    () -> CaveEscapeQuestService.commandSuggestions(body, server)));
            } catch (IOException e) {
                MathQuestHttpUtil.sendError(ex, 500, e.getMessage());
            }
        });
        router.register("POST", "/api/spawn-mobs", ex -> {
            try {
                JsonObject body = MathQuestHttpUtil.readJson(ex);
                MathQuestHttpUtil.sendJson(ex, MathQuestHttpUtil.onServerThread(bridge.platformServer(),
                    () -> spawnMobs(server, bridge, body)));
            } catch (IOException e) {
                MathQuestHttpUtil.sendError(ex, 500, e.getMessage());
            }
        });
        router.register("POST", "/api/spawn-mob-plan", ex -> {
            try {
                JsonObject body = MathQuestHttpUtil.readJson(ex);
                MathQuestHttpUtil.sendJson(ex, MathQuestHttpUtil.onServerThread(bridge.platformServer(),
                    () -> spawnMobPlan(server, bridge, body)));
            } catch (IOException e) {
                MathQuestHttpUtil.sendError(ex, 500, e.getMessage());
            }
        });
        router.register("POST", "/api/kill-mob-area", ex -> {
            try {
                JsonObject body = MathQuestHttpUtil.readJson(ex);
                MathQuestHttpUtil.sendJson(ex, MathQuestHttpUtil.onServerThread(bridge.platformServer(),
                    () -> killMobArea(server, bridge, body)));
            } catch (IOException e) {
                MathQuestHttpUtil.sendError(ex, 500, e.getMessage());
            }
        });
    }

    private static Map<String, Object> spawnMobs(MinecraftServer server, ControlPanelBridge bridge, JsonObject body) {
        String playerName = body.get("playerName").getAsString();
        ServerPlayer player = server.getPlayerList().getPlayerByName(playerName);
        if (player == null) return Map.of("ok", false, "error", "player-offline");
        String mobId = normalizeMinecraftId(body.has("mobId") ? body.get("mobId").getAsString() : "zombie");
        int count = body.has("count") ? MathQuestHttpUtil.clamp(body.get("count").getAsInt(), 1, 100) : 10;
        int radius = body.has("radius") ? MathQuestHttpUtil.clamp(body.get("radius").getAsInt(), 1, 128) : 20;
        EntityType<?> type;
        try {
            Identifier id = Identifier.parse(mobId);
            if (!BuiltInRegistries.ENTITY_TYPE.containsKey(id)) {
                return Map.of("ok", false, "error", "unknown-mob", "mobId", mobId, "status", MathQuestHttpStatusBuilder.statusJson(bridge));
            }
            type = BuiltInRegistries.ENTITY_TYPE.getValue(id);
        } catch (Exception e) {
            return Map.of("ok", false, "error", "invalid-mob-id", "mobId", mobId, "status", MathQuestHttpStatusBuilder.statusJson(bridge));
        }
        if (type == null || type == EntityType.PLAYER || !type.canSummon()) {
            return Map.of("ok", false, "error", "mob-not-summonable", "mobId", mobId, "status", MathQuestHttpStatusBuilder.statusJson(bridge));
        }
        ServerLevel world = player.level();
        int spawned = 0;
        BlockPos center = player.blockPosition();
        for (int i = 0; i < count; i++) {
            BlockPos pos = randomMobSpawnPos(world, center, radius);
            if (type.spawn(world, pos, EntitySpawnReason.COMMAND) != null) spawned++;
        }
        return Map.of("ok", spawned > 0, "mobId", mobId, "requested", count, "spawned", spawned, "radius", radius,
            "status", MathQuestHttpStatusBuilder.statusJson(bridge));
    }

    private static Map<String, Object> spawnMobPlan(MinecraftServer server, ControlPanelBridge bridge, JsonObject body) {
        String dimension = body.has("dimension") ? body.get("dimension").getAsString() : "minecraft:overworld";
        ServerLevel world = levelForDimension(server, dimension);
        if (world == null) {
            return Map.of("ok", false, "error", "dimension-not-loaded", "dimension", dimension, "status", MathQuestHttpStatusBuilder.statusJson(bridge));
        }
        JsonArray entries = body.has("entries") ? body.getAsJsonArray("entries") : new JsonArray();
        int requested = 0;
        int spawned = 0;
        List<Map<String, Object>> results = new ArrayList<>();
        for (com.google.gson.JsonElement el : entries) {
            if (!el.isJsonObject()) continue;
            JsonObject entry = el.getAsJsonObject();
            String mobId = normalizeMinecraftId(entry.has("mobId") ? entry.get("mobId").getAsString() : "zombie");
            EntityType<?> type = entityType(mobId);
            if (type == null || type == EntityType.PLAYER || !type.canSummon()) {
                results.add(Map.of("mobId", mobId, "requested", 0, "spawned", 0, "error", "mob-not-summonable"));
                continue;
            }
            String shape = normalizeShape(entry.has("shape") ? entry.get("shape").getAsString() : "circle");
            int count = entry.has("count") ? MathQuestHttpUtil.clamp(entry.get("count").getAsInt(), 1, 300) : 1;
            int radius = entry.has("radius") ? MathQuestHttpUtil.clamp(entry.get("radius").getAsInt(), 0, 256) : 20;
            int lineLength = entry.has("lineLength") ? MathQuestHttpUtil.clamp(entry.get("lineLength").getAsInt(), 1, 512) : 40;
            double angleDeg = entry.has("angleDeg") ? entry.get("angleDeg").getAsDouble() : 0.0;
            BlockPos target = new BlockPos(
                entry.has("x") ? entry.get("x").getAsInt() : 0,
                entry.has("y") ? entry.get("y").getAsInt() : world.getSeaLevel(),
                entry.has("z") ? entry.get("z").getAsInt() : 0
            );
            int entrySpawned = spawnMobEntry(world, type, shape, target, count, radius, lineLength, angleDeg);
            requested += count;
            spawned += entrySpawned;
            results.add(Map.of("mobId", mobId, "shape", shape, "requested", count, "spawned", entrySpawned));
        }
        Map<String, Object> response = new LinkedHashMap<>();
        response.put("ok", spawned > 0 || requested == 0);
        response.put("dimension", dimension);
        response.put("requested", requested);
        response.put("spawned", spawned);
        response.put("results", results);
        response.put("status", MathQuestHttpStatusBuilder.statusJson(bridge));
        return response;
    }

    private static Map<String, Object> killMobArea(MinecraftServer server, ControlPanelBridge bridge, JsonObject body) {
        String dimension = body.has("dimension") ? body.get("dimension").getAsString() : "minecraft:overworld";
        ServerLevel world = levelForDimension(server, dimension);
        if (world == null) {
            return Map.of("ok", false, "error", "dimension-not-loaded", "dimension", dimension, "status", MathQuestHttpStatusBuilder.statusJson(bridge));
        }
        String mobId = normalizeMinecraftId(body.has("mobId") ? body.get("mobId").getAsString() : "zombie");
        EntityType<?> type = entityType(mobId);
        if (type == null || type == EntityType.PLAYER) {
            return Map.of("ok", false, "error", "unknown-mob", "mobId", mobId, "status", MathQuestHttpStatusBuilder.statusJson(bridge));
        }
        String shape = body.has("shape") ? body.get("shape").getAsString().trim().toLowerCase(Locale.ROOT) : "circle";
        shape = "square".equals(shape) ? "square" : "circle";
        int radius = body.has("radius") ? MathQuestHttpUtil.clamp(body.get("radius").getAsInt(), 1, 512) : 30;
        double x = body.has("x") ? body.get("x").getAsDouble() : 0.0;
        double y = body.has("y") ? body.get("y").getAsDouble() : world.getSeaLevel();
        double z = body.has("z") ? body.get("z").getAsDouble() : 0.0;
        double radiusSq = radius * radius;
        AABB box = new AABB(x - radius, y - 128, z - radius, x + radius, y + 128, z + radius);
        int removed = 0;
        for (Entity entity : world.getEntities((Entity) null, box, entity -> entity.getType() == type)) {
            if ("circle".equals(shape)) {
                double dx = entity.getX() - x;
                double dz = entity.getZ() - z;
                if ((dx * dx) + (dz * dz) > radiusSq) continue;
            }
            entity.discard();
            removed++;
        }
        return Map.of("ok", true, "mobId", mobId, "shape", shape, "radius", radius, "removed", removed,
            "status", MathQuestHttpStatusBuilder.statusJson(bridge));
    }

    private static byte[] terrainMapPng(MinecraftServer server, String rawQuery) {
        Map<String, String> q = queryParams(rawQuery);
        ServerLevel world = levelForDimension(server, q.getOrDefault("dimension", "minecraft:overworld"));
        if (world == null) world = server.overworld();
        int centerX = parseInt(q.get("x"), 0);
        int centerZ = parseInt(q.get("z"), 0);
        int radius = MathQuestHttpUtil.clamp(parseInt(q.get("radius"), 128), 16, 1024);
        int size = MathQuestHttpUtil.clamp(parseInt(q.get("size"), 384), 128, 512);
        BufferedImage image = new BufferedImage(size, size, BufferedImage.TYPE_INT_RGB);
        double blocksPerPixel = (radius * 2.0) / size;
        for (int py = 0; py < size; py++) {
            for (int px = 0; px < size; px++) {
                int worldX = (int) Math.round(centerX - radius + (px + 0.5) * blocksPerPixel);
                int worldZ = (int) Math.round(centerZ - radius + (py + 0.5) * blocksPerPixel);
                int y = world.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, worldX, worldZ) - 1;
                BlockPos pos = new BlockPos(worldX, y, worldZ);
                BlockState state = world.getBlockState(pos);
                Biome biome = world.getBiomeManager().getBiome(pos).value();
                image.setRGB(px, py, terrainColor(world, state, biome, y));
            }
        }
        try {
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            ImageIO.write(image, "png", out);
            return out.toByteArray();
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }

    private static int terrainColor(ServerLevel world, BlockState state, Biome biome, int y) {
        Block block = state.getBlock();
        int color;
        if (block == Blocks.WATER) color = biome.getWaterColor();
        else if (block == Blocks.GRASS_BLOCK || block == Blocks.TALL_GRASS || block == Blocks.SHORT_GRASS) color = biome.getGrassColor(0.5, 0.5);
        else if (block == Blocks.OAK_LEAVES || block == Blocks.BIRCH_LEAVES || block == Blocks.SPRUCE_LEAVES
            || block == Blocks.JUNGLE_LEAVES || block == Blocks.ACACIA_LEAVES || block == Blocks.DARK_OAK_LEAVES
            || block == Blocks.MANGROVE_LEAVES || block == Blocks.CHERRY_LEAVES || block == Blocks.PALE_OAK_LEAVES) color = biome.getFoliageColor();
        else if (block == Blocks.SAND || block == Blocks.SANDSTONE) color = 0xd8c071;
        else if (block == Blocks.RED_SAND || block == Blocks.RED_SANDSTONE) color = 0xb96d32;
        else if (block == Blocks.SNOW || block == Blocks.SNOW_BLOCK || block == Blocks.POWDER_SNOW) color = 0xf4f8ff;
        else if (block == Blocks.ICE || block == Blocks.PACKED_ICE || block == Blocks.BLUE_ICE) color = 0x91c9e8;
        else if (block == Blocks.STONE || block == Blocks.COBBLESTONE || block == Blocks.GRAVEL) color = 0x87877f;
        else if (block == Blocks.DIRT || block == Blocks.COARSE_DIRT || block == Blocks.DIRT_PATH) color = 0x8a6b45;
        else if (block == Blocks.NETHERRACK) color = 0x733030;
        else if (block == Blocks.SOUL_SAND || block == Blocks.SOUL_SOIL) color = 0x564438;
        else if (block == Blocks.END_STONE) color = 0xd9d59b;
        else color = 0x7f9560;
        double shade = Math.max(0.72, Math.min(1.18, 0.92 + (y - world.getSeaLevel()) * 0.006));
        return shadeColor(color, shade);
    }

    private static int shadeColor(int color, double shade) {
        int r = (int) Math.max(0, Math.min(255, ((color >> 16) & 255) * shade));
        int g = (int) Math.max(0, Math.min(255, ((color >> 8) & 255) * shade));
        int b = (int) Math.max(0, Math.min(255, (color & 255) * shade));
        return (r << 16) | (g << 8) | b;
    }

    private static Map<String, String> queryParams(String rawQuery) {
        Map<String, String> out = new LinkedHashMap<>();
        if (rawQuery == null || rawQuery.isBlank()) return out;
        for (String part : rawQuery.split("&")) {
            int idx = part.indexOf('=');
            String key = idx >= 0 ? part.substring(0, idx) : part;
            String value = idx >= 0 ? part.substring(idx + 1) : "";
            out.put(URLDecoder.decode(key, StandardCharsets.UTF_8), URLDecoder.decode(value, StandardCharsets.UTF_8));
        }
        return out;
    }

    private static int parseInt(String raw, int fallback) {
        try {
            return raw == null || raw.isBlank() ? fallback : Integer.parseInt(raw);
        } catch (NumberFormatException e) {
            return fallback;
        }
    }

    private static EntityType<?> entityType(String mobId) {
        try {
            Identifier id = Identifier.parse(mobId);
            if (!BuiltInRegistries.ENTITY_TYPE.containsKey(id)) return null;
            return BuiltInRegistries.ENTITY_TYPE.getValue(id);
        } catch (Exception e) {
            return null;
        }
    }

    private static ServerLevel levelForDimension(MinecraftServer server, String dimension) {
        try {
            ResourceKey<Level> key = ResourceKey.create(Registries.DIMENSION, Identifier.parse(normalizeMinecraftId(dimension)));
            return server.getLevel(key);
        } catch (Exception e) {
            return null;
        }
    }

    private static String normalizeShape(String raw) {
        String s = raw == null ? "" : raw.trim().toLowerCase(Locale.ROOT).replace('-', '_').replace(' ', '_');
        return switch (s) {
            case "point", "circle", "rim", "line" -> s;
            case "circle_rim", "ring" -> "rim";
            default -> "circle";
        };
    }

    private static int spawnMobEntry(ServerLevel world, EntityType<?> type, String shape, BlockPos target, int count, int radius, int lineLength, double angleDeg) {
        int spawned = 0;
        for (int i = 0; i < count; i++) {
            BlockPos pos = mobPlanPos(world, shape, target, radius, lineLength, angleDeg);
            if (type.spawn(world, pos, EntitySpawnReason.COMMAND) != null) spawned++;
        }
        return spawned;
    }

    private static BlockPos mobPlanPos(ServerLevel world, String shape, BlockPos target, int radius, int lineLength, double angleDeg) {
        if ("point".equals(shape)) return target;
        double x = target.getX();
        double z = target.getZ();
        if ("line".equals(shape)) {
            double offset = (world.getRandom().nextDouble() - 0.5) * lineLength;
            double angle = Math.toRadians(angleDeg);
            x += Math.cos(angle) * offset;
            z += Math.sin(angle) * offset;
        } else {
            double angle = world.getRandom().nextDouble() * Math.PI * 2.0;
            double distance = "rim".equals(shape) ? radius : Math.sqrt(world.getRandom().nextDouble()) * radius;
            x += Math.cos(angle) * distance;
            z += Math.sin(angle) * distance;
        }
        return world.getHeightmapPos(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES,
            new BlockPos((int) Math.round(x), target.getY(), (int) Math.round(z)));
    }

    private static BlockPos randomMobSpawnPos(ServerLevel world, BlockPos center, int radius) {
        double angle = world.getRandom().nextDouble() * Math.PI * 2.0;
        double distance = Math.sqrt(world.getRandom().nextDouble()) * radius;
        int x = center.getX() + (int) Math.round(Math.cos(angle) * distance);
        int z = center.getZ() + (int) Math.round(Math.sin(angle) * distance);
        return world.getHeightmapPos(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, new BlockPos(x, center.getY(), z));
    }

    private static String normalizeMinecraftId(String raw) {
        if (raw == null || raw.isBlank()) return "minecraft:zombie";
        String s = raw.trim().toLowerCase(Locale.ROOT).replace('-', '_').replace(' ', '_');
        return s.contains(":") ? s : "minecraft:" + s;
    }
}
