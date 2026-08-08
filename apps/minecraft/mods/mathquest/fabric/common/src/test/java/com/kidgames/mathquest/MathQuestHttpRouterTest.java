package com.kidgames.mathquest;

import com.google.gson.JsonParser;
import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.control.http.ControlPanelBridge;
import com.kidgames.mathquest.control.http.MathQuestHttpAssets;
import com.kidgames.mathquest.control.http.MathQuestHttpConfigUpdater;
import com.kidgames.mathquest.control.http.MathQuestHttpRouter;
import com.kidgames.mathquest.control.http.MathQuestHttpStatusBuilder;
import com.kidgames.mathquest.platform.PlatformNetwork;
import com.kidgames.mathquest.platform.PlatformServer;
import com.kidgames.mathquest.platform.PlayerContext;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class MathQuestHttpRouterTest {
    @Test
    void routeKeyMatchesMethodAndPath() {
        assertEquals("GET /api/status", MathQuestHttpRouter.routeKey("GET", "/api/status"));
        assertEquals("POST /api/spawn-mobs", MathQuestHttpRouter.routeKey("POST", "/api/spawn-mobs"));
    }

    @Test
    void optionalRouteRegistrationDoesNotReplaceCoreStaticAssetMapping() {
        assertNotNull(MathQuestHttpAssets.staticAsset("/"));
        assertNotNull(MathQuestHttpAssets.staticAsset("/control-panel.js"));
    }

    @Test
    void configUpdateNormalizesEditableTpCreditMapsAndIgnoresDisplayedBalance() {
        CountingConfig config = new CountingConfig();

        Map<String, Object> result = MathQuestHttpConfigUpdater.updateConfig(config, JsonParser.parseString("""
            {
              "playerTpCreditEarningEnabled": {"WildPetal": true},
              "playerTpCreditsPerQuiz": {"WildPetal": 500},
              "playerTpCreditBalances": {"WildPetal": 99},
              "playerTpCreditRewardChoices": {"WildPetal": "future-choice"}
            }
            """).getAsJsonObject());

        assertEquals(Map.of("ok", true), result);
        assertTrue(config.resolveTpCreditEarningEnabled("wildpetal"));
        assertEquals(100, config.resolveTpCreditsPerQuiz("WILDPETAL"));
        assertEquals(0, config.resolveTpCreditBalance("WildPetal"));
        assertEquals("teleport", config.resolveTpCreditRewardChoice("wildpetal"));
        assertEquals(1, config.saveCalls);
    }

    @Test
    void tpCreditModeRetainsPanelItemSelectionWithoutAwardingIt() {
        CountingConfig config = new CountingConfig();

        MathQuestHttpConfigUpdater.updateConfig(config, JsonParser.parseString("""
            {
              "playerRewards": {
                "TreasureHunterM": {"item": "polished_deepslate", "count": 1}
              },
              "playerTpCreditEarningEnabled": {"TreasureHunterM": true}
            }
            """).getAsJsonObject());

        assertEquals("minecraft:polished_deepslate", config.playerRewards.get("treasurehunterm").item);
        assertEquals(1, config.playerRewards.get("treasurehunterm").count);
        assertTrue(config.resolveRewardPlanForPlayer("TreasureHunterM").entries().isEmpty());
    }

    @Test
    @SuppressWarnings("unchecked")
    void statusPlayerCardIncludesTpCreditObject() {
        MathQuestConfig config = new MathQuestConfig();
        config.setTpCreditEarningEnabled("WildPetal", true);
        config.setTpCreditsPerQuiz("WildPetal", 3);
        config.setTpCreditBalance("WildPetal", 8);
        config.setTpCreditRewardChoice("WildPetal", "teleport");

        Map<String, Object> wildPetal = MathQuestHttpStatusBuilder.playerCards(new TestBridge(config)).stream()
            .filter(row -> "wildpetal".equals(row.get("key")))
            .findFirst()
            .orElseThrow();
        Map<String, Object> tpCredits = (Map<String, Object>) wildPetal.get("tpCredits");

        assertEquals(true, tpCredits.get("earningEnabled"));
        assertEquals(3, tpCredits.get("creditsPerQuiz"));
        assertEquals(8, tpCredits.get("balance"));
        assertEquals("teleport", tpCredits.get("rewardChoice"));
    }

    private static final class CountingConfig extends MathQuestConfig {
        private int saveCalls;

        @Override
        public boolean saveChecked() {
            saveCalls++;
            return true;
        }
    }

    private record TestBridge(MathQuestConfig config) implements ControlPanelBridge {
        @Override
        public PlatformServer platformServer() {
            return new PlatformServer() {
                @Override
                public void runOnServerThread(Runnable task) {
                    task.run();
                }

                @Override
                public List<PlayerContext> onlinePlayers() {
                    return List.of();
                }

                @Override
                public PlayerContext findOnlinePlayer(String name) {
                    return null;
                }
            };
        }

        @Override
        public PlatformNetwork platformNetwork() {
            return null;
        }

        @Override
        public long worldSeed() {
            return 0;
        }

        @Override
        public List<Map<String, Object>> playerLocations() {
            return List.of();
        }

        @Override
        public List<Map<String, Object>> activeNerdsFor(String playerName) {
            return List.of();
        }

        @Override
        public boolean spawnNerd(String playerName, int radius, String npcId, boolean locked) {
            return false;
        }

        @Override
        public int vanishNerds(String playerNameOrBlank) {
            return 0;
        }

        @Override
        public void openQuiz(PlayerContext player) {}
    }
}
