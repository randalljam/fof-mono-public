package com.kidgames.mathquest.npc;

import com.kidgames.mathquest.config.MathQuestConfig;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Locale;

public final class NpcSpawnPlanner {
    private NpcSpawnPlanner() {}

    /**
     * Pure spawn-target selection: given online player names and config mode, return the names
     * that should receive a spawn attempt this interval.
     *
     * @param targetMode normalized mode (all/random/one)
     * @param candidateNames online player names (order preserved for "all")
     * @param targetPlayerName configured name for "one" mode (may be null)
     * @param randomIndex index into candidateNames for "random" mode (caller supplies RNG)
     */
    public static List<String> selectTargetNames(
        String targetMode,
        List<String> candidateNames,
        String targetPlayerName,
        int randomIndex
    ) {
        if (candidateNames == null || candidateNames.isEmpty()) {
            return List.of();
        }
        String mode = MathQuestConfig.normalizeNpcSpawnTargetMode(targetMode);
        if ("random".equals(mode)) {
            int idx = Math.floorMod(randomIndex, candidateNames.size());
            return List.of(candidateNames.get(idx));
        }
        if ("one".equals(mode)) {
            if (targetPlayerName == null || targetPlayerName.isBlank()) {
                return List.of();
            }
            String key = targetPlayerName.toLowerCase(Locale.ROOT);
            for (String name : candidateNames) {
                if (name.toLowerCase(Locale.ROOT).equals(key)) {
                    return List.of(name);
                }
            }
            return List.of();
        }
        return Collections.unmodifiableList(new ArrayList<>(candidateNames));
    }
}
