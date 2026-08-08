package com.kidgames.mathquest;

import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.platform.PlatformInventory;
import com.kidgames.mathquest.platform.PlayerContext;
import com.kidgames.mathquest.server.QuizResultProcessor;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class QuizResultProcessorTest {
    @TempDir
    Path tempDir;

    @Test
    void formatRewardDescription_prettyPrintsItemId() {
        var entry = new MathQuestConfig.RewardEntry("minecraft:golden_apple", 2);
        assertEquals("Golden Apple x2", QuizResultProcessor.formatRewardDescription(entry));
    }

    @Test
    void process_standardQuiz_recordsSessionAndExports(@TempDir Path exportDir) throws Exception {
        MathQuestPathsTestHelper.initConfig(tempDir, exportDir);
        CapturingInventory inventory = new CapturingInventory();
        String resultJson = """
            {
              "operation": "multiplication",
              "problemsTotal": 1,
              "problemsCorrect": 1,
              "rewardGiven": "minecraft:diamond:1",
              "problems": [
                {
                  "operation": "multiplication",
                  "factorA": 2,
                  "factorB": 3,
                  "correctAnswer": 6,
                  "playerAnswer": 6,
                  "isCorrect": true,
                  "responseTimeMs": 1000,
                  "flags": []
                }
              ]
            }
            """;
        QuizResultProcessor.process(
            resultJson,
            new PlayerContext("wildpetal", UUID.randomUUID()),
            inventory,
            null,
            null
        );
        assertTrue(inventory.grants.isEmpty());
    }

    @Test
    void grantReward_rejectsItemsWhenTpCreditEarningIsEnabled() {
        MathQuestConfig previous = MathQuestConfig.INSTANCE;
        MathQuestConfig config = new MathQuestConfig();
        MathQuestConfig.INSTANCE = config;
        try {
            PlayerContext player = new PlayerContext("PumaJockey", UUID.randomUUID());
            CapturingInventory inventory = new CapturingInventory();
            MathQuestConfig.RewardEntry reward = new MathQuestConfig.RewardEntry("minecraft:golden_apple", 1);

            config.setTpCreditEarningEnabled(player.username(), true);
            QuizResultProcessor.grantReward(inventory, player, reward);
            assertTrue(inventory.grants.isEmpty());

            config.setTpCreditEarningEnabled(player.username(), false);
            QuizResultProcessor.grantReward(inventory, player, reward);
            assertEquals(List.of("minecraft:golden_apple:1"), inventory.grants);
        } finally {
            MathQuestConfig.INSTANCE = previous;
        }
    }

    private static final class CapturingInventory implements PlatformInventory {
        private final List<String> grants = new ArrayList<>();

        @Override
        public void grantReward(PlayerContext player, String itemId, int count) {
            grants.add(itemId + ":" + count);
        }
    }
}
