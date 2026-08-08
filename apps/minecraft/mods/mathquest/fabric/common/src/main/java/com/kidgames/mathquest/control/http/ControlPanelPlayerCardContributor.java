package com.kidgames.mathquest.control.http;

import java.util.Map;

/** Optional loader-specific enrichment for control-panel player cards (e.g. quest status on Fabric). */
public interface ControlPanelPlayerCardContributor {
    default Map<String, Object> questStatusForPlayer(String playerName) {
        return Map.of();
    }
}
