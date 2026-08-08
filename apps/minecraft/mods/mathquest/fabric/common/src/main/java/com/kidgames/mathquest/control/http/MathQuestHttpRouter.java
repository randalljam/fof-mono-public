package com.kidgames.mathquest.control.http;

import com.google.gson.JsonObject;
import com.kidgames.mathquest.platform.PlayerContext;
import com.sun.net.httpserver.HttpExchange;

import java.io.IOException;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/** HTTP route dispatch: core routes + loader-registered optional handlers. */
public final class MathQuestHttpRouter {
    @FunctionalInterface
    public interface RouteHandler {
        void handle(HttpExchange ex) throws IOException;
    }

    private final ControlPanelBridge bridge;
    private final ClassLoader assetClassLoader;
    private final Map<String, RouteHandler> optionalRoutes = new ConcurrentHashMap<>();

    public MathQuestHttpRouter(ControlPanelBridge bridge, ClassLoader assetClassLoader) {
        this.bridge = bridge;
        this.assetClassLoader = assetClassLoader;
    }

    public void register(String method, String path, RouteHandler handler) {
        optionalRoutes.put(routeKey(method, path), handler);
    }

    public void handle(HttpExchange ex) throws IOException {
        String method = ex.getRequestMethod();
        String path = ex.getRequestURI().getPath();
        RouteHandler optional = optionalRoutes.get(routeKey(method, path));
        if (optional != null) {
            optional.handle(ex);
            return;
        }
        if ("GET".equals(method) && "/api/status".equals(path)) {
            MathQuestHttpUtil.sendJson(ex, MathQuestHttpUtil.onServerThread(
                bridge.platformServer(),
                () -> MathQuestHttpStatusBuilder.statusJson(bridge)
            ));
        } else if ("POST".equals(method) && "/api/config".equals(path)) {
            JsonObject body = MathQuestHttpUtil.readJson(ex);
            MathQuestHttpUtil.sendJson(ex, MathQuestHttpUtil.onServerThread(bridge.platformServer(), () -> {
                Map<String, Object> result = new LinkedHashMap<>(MathQuestHttpConfigUpdater.updateConfig(bridge.config(), body));
                result.put("status", MathQuestHttpStatusBuilder.statusJson(bridge));
                return result;
            }));
        } else if ("POST".equals(method) && "/api/spawn".equals(path)) {
            JsonObject body = MathQuestHttpUtil.readJson(ex);
            MathQuestHttpUtil.sendJson(ex, MathQuestHttpUtil.onServerThread(bridge.platformServer(), () -> handleSpawn(body)));
        } else if ("POST".equals(method) && "/api/open".equals(path)) {
            JsonObject body = MathQuestHttpUtil.readJson(ex);
            MathQuestHttpUtil.sendJson(ex, MathQuestHttpUtil.onServerThread(bridge.platformServer(), () -> handleOpen(body)));
        } else if ("POST".equals(method) && "/api/vanish".equals(path)) {
            JsonObject body = MathQuestHttpUtil.readJson(ex);
            MathQuestHttpUtil.sendJson(ex, MathQuestHttpUtil.onServerThread(bridge.platformServer(), () -> handleVanish(body)));
        } else if ("GET".equals(method)) {
            MathQuestHttpAssets.sendStatic(ex, bridge.config(), assetClassLoader, path);
        } else {
            MathQuestHttpUtil.sendError(ex, 404, "Not found");
        }
    }

    private Map<String, Object> handleSpawn(JsonObject body) {
        String playerName = body.get("playerName").getAsString();
        PlayerContext player = bridge.platformServer().findOnlinePlayer(playerName);
        if (player == null) return Map.of("ok", false, "error", "player-offline");
        int radius = body.has("radius")
            ? MathQuestHttpUtil.clamp(body.get("radius").getAsInt(), 1, 64)
            : bridge.config().npcSpawnRadiusBlocks;
        boolean locked = !body.has("locked") || body.get("locked").getAsBoolean();
        String npcId = body.has("npcId") ? body.get("npcId").getAsString() : "wandering_nerd";
        MathQuestHttpPlayerBodyApplier.applyAllFromBody(bridge.config(), playerName, body);
        bridge.config().quizMode = "npc";
        bridge.config().npcSpawnRadiusBlocks = radius;
        bridge.config().save();
        boolean spawned = bridge.spawnNerd(playerName, radius, npcId, locked);
        return Map.of("ok", spawned, "status", MathQuestHttpStatusBuilder.statusJson(bridge));
    }

    private Map<String, Object> handleOpen(JsonObject body) {
        String playerName = body.get("playerName").getAsString();
        PlayerContext player = bridge.platformServer().findOnlinePlayer(playerName);
        if (player == null) return Map.of("ok", false, "error", "player-offline");
        MathQuestHttpPlayerBodyApplier.applyAllFromBody(bridge.config(), playerName, body);
        bridge.config().save();
        bridge.openQuiz(player);
        return Map.of("ok", true, "status", MathQuestHttpStatusBuilder.statusJson(bridge));
    }

    private Map<String, Object> handleVanish(JsonObject body) {
        String playerName = body.has("playerName") ? body.get("playerName").getAsString() : "";
        int removed = bridge.vanishNerds(playerName);
        return Map.of("ok", true, "removed", removed, "status", MathQuestHttpStatusBuilder.statusJson(bridge));
    }

    public static String routeKey(String method, String path) {
        return method + " " + path;
    }
}
