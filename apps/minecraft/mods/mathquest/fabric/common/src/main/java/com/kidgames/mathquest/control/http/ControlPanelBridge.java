package com.kidgames.mathquest.control.http;

import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.platform.PlatformNetwork;
import com.kidgames.mathquest.platform.PlatformServer;
import com.kidgames.mathquest.platform.PlayerContext;

import java.util.List;
import java.util.Map;

/** Loader-specific game hooks for the shared HTTP control panel core. */
public interface ControlPanelBridge {
    PlatformServer platformServer();
    PlatformNetwork platformNetwork();
    MathQuestConfig config();
    long worldSeed();
    List<Map<String, Object>> playerLocations();
    List<Map<String, Object>> activeNerdsFor(String playerName);
    boolean spawnNerd(String playerName, int radius, String npcId, boolean locked);
    int vanishNerds(String playerNameOrBlank);
    void openQuiz(PlayerContext player);
    default ControlPanelPlayerCardContributor playerCardContributor() {
        return new ControlPanelPlayerCardContributor() {};
    }
}
