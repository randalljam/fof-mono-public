package com.kidgames.mathquest.control;

import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;

public class MathQuestControlState {
    private static final Map<String, PlayerNpcState> PLAYER_STATES = new LinkedHashMap<>();
    public record PlayerNpcState(
        String playerName,
        String entityUuid,
        long lastSpawnedAtMillis,
        long lastClickedAtMillis,
        String status
    ) {}
    public static synchronized void markSpawned(String playerName, String entityUuid) {
        String key = key(playerName);
        PLAYER_STATES.put(key, new PlayerNpcState(playerName, entityUuid, System.currentTimeMillis(), 0L, "spawned"));
    }
    public static synchronized void markClicked(String playerName, String entityUuid) {
        String key = key(playerName);
        PlayerNpcState old = PLAYER_STATES.get(key);
        long spawned = old != null ? old.lastSpawnedAtMillis() : 0L;
        PLAYER_STATES.put(key, new PlayerNpcState(playerName, entityUuid, spawned, System.currentTimeMillis(), "clicked"));
    }
    public static synchronized void markRemoved(String playerName) {
        String key = key(playerName);
        PlayerNpcState old = PLAYER_STATES.get(key);
        long spawned = old != null ? old.lastSpawnedAtMillis() : 0L;
        long clicked = old != null ? old.lastClickedAtMillis() : 0L;
        PLAYER_STATES.put(key, new PlayerNpcState(playerName, old != null ? old.entityUuid() : null, spawned, clicked, "removed"));
    }
    public static synchronized PlayerNpcState get(String playerName) {
        return PLAYER_STATES.get(key(playerName));
    }
    private static String key(String playerName) {
        return playerName == null ? "" : playerName.toLowerCase(Locale.ROOT);
    }
}
