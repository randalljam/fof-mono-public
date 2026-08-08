package com.kidgames.mathquest;

import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.platform.MathQuestPaths;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for MathQuestConfig.
 * Tests JSON serialization/deserialization without Fabric dependencies.
 * Run with: ./gradlew test
 */
public class ConfigTest {

    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();

    @Test
    void testDefaultValues() {
        MathQuestConfig config = new MathQuestConfig();
        assertEquals(30, config.quizIntervalSeconds);
        assertEquals(5, config.problemsPerQuiz);
        assertEquals(0, config.minNumber);
        assertEquals(9, config.maxNumber);
        assertEquals("multiplication", config.operation);
        assertNotNull(config.playerPresets);
        assertTrue(config.playerPresets.containsKey("wildpetal"));
        assertTrue(config.playerPresets.containsKey("treasurehunterm"));
        assertTrue(config.playerPresets.containsKey("pumajockey"));
        assertEquals("all", config.npcSpawnTargetMode);
        assertEquals(MathQuestConfig.DEFAULT_SHARED_DATA_DIR, config.sharedDataDir);
        assertEquals(MathQuestConfig.DEFAULT_MATH_QUIZ_SINGLE_DB_DIR, config.mathQuizSingleDbDir);
        assertEquals(MathQuestConfig.DEFAULT_MATH_QUIZ_ACTIVE_DB_DIR, config.mathQuizActiveDbDir);
        assertTrue(config.mathQuizIngestEnabled);
        assertEquals("python3", config.mathQuizIngestPython);
        assertEquals("node", config.mathQuizNodeExecutable);
        assertTrue(config.fluencyFeastEnabled);
        assertTrue(config.controlPanelEnabled);
        assertEquals("127.0.0.1", config.controlPanelHost);
        assertEquals(8765, config.controlPanelPort);
        assertEquals("paper", config.writtenColumnEvaluatorCode);
        assertEquals("Randy", config.resolveRealName("rjcomp"));
        assertEquals("Guest", config.resolveRealName("SkulkScraper"));
        assertEquals("standard_arithmetic", config.resolveQuizType("WildPetal"));
        assertEquals("internal_quick_quiz", config.resolveInternalQuizSource("WildPetal"));
        assertFalse(config.resolveUseInternalProblemList("WildPetal"));
        assertEquals("wandering_nerd", config.resolveNpcSelection("WildPetal"));
        assertTrue(config.resolveNpcLock("WildPetal"));
        assertFalse(config.resolveTpCreditEarningEnabled("WildPetal"));
        assertEquals(1, config.resolveTpCreditsPerQuiz("WildPetal"));
        assertEquals(0, config.resolveTpCreditBalance("WildPetal"));
        assertEquals("teleport", config.resolveTpCreditRewardChoice("WildPetal"));
        assertFalse(config.npcAllowMultipleNerds);
        assertEquals("jtree", config.rewardGroup);
        assertNull(config.rewardGroups);
        Map<String, MathQuestConfig.RewardGroup> defaultGroups = new LinkedHashMap<>();
        MathQuestConfig.ensureJtreeGroup(defaultGroups);
        assertTrue(defaultGroups.containsKey("jtree"));
        assertEquals(4, defaultGroups.get("jtree").entries.size());
        assertEquals("random", defaultGroups.get("jtree").mode);
        assertTrue(config.enabled);
        assertEquals("random", config.rewardMode);
        assertNotNull(config.rewards);
        assertFalse(config.rewards.isEmpty());
        assertNotNull(config.playerRewards);
        assertEquals("minecraft:diamond", config.playerRewards.get("rjcomp").item);
        assertEquals("minecraft:polished_deepslate", config.playerRewards.get("treasurehunterm").item);
        assertEquals(1, config.playerRewards.get("treasurehunterm").count);
        assertEquals("minecraft:golden_apple", config.playerRewards.get("pumajockey").item);
        assertEquals("Guest", config.playerRealNames.get("skulkscraper"));
    }
    @Test
    void loadsSharedConfigWhenLocalPointsAtSharedDataDir(@TempDir Path localDir, @TempDir Path sharedDir) throws IOException {
        MathQuestConfig.resetConfigFileStateForTests();
        Files.writeString(sharedDir.resolve("mathquest.json"), """
            {"playerInternalQuizSources":{"rjcomp":"internal_fluency_feast"}}
            """);
        Files.writeString(localDir.resolve("mathquest.json"), """
            {"sharedDataDir":"%s","playerInternalQuizSources":{"rjcomp":"internal_quick_quiz"}}
            """.formatted(sharedDir.toString().replace("\\", "\\\\")));
        MathQuestPaths.setConfigDir(localDir);
        MathQuestConfig loaded = MathQuestConfig.load();
        assertEquals("internal_fluency_feast", loaded.resolveInternalQuizSource("rjcomp"));
        assertEquals(sharedDir.resolve("mathquest.json"), MathQuestConfig.loadedConfigFile());
    }

    @Test
    void preservesExplicitTreasureHunterDiamondStack(@TempDir Path configDir) throws IOException {
        MathQuestConfig.resetConfigFileStateForTests();
        MathQuestPaths.setConfigDir(configDir);
        Files.writeString(configDir.resolve("mathquest.json"), """
            {
              "playerRewards": {
                "treasurehunterm": {"item": "minecraft:diamond", "count": 64}
              }
            }
            """);

        MathQuestConfig loaded = MathQuestConfig.load();

        assertEquals("minecraft:diamond", loaded.playerRewards.get("treasurehunterm").item);
        assertEquals(64, loaded.playerRewards.get("treasurehunterm").count);
    }

    @Test
    void migratesLegacyMathQuizExportDirToSingleSessionFolder() {
        assertEquals(
            MathQuestConfig.DEFAULT_MATH_QUIZ_SINGLE_DB_DIR,
            MathQuestConfig.normalizeMathQuizSingleDbDir("~/Documents/Code/fof-mono/apps/math-quiz/_data/mathquest")
        );
        assertEquals(
            "/custom/path",
            MathQuestConfig.normalizeMathQuizSingleDbDir("/custom/path")
        );
    }
    @Test
    void migratesDashedTlKidsActiveDirToTlkids() {
        assertEquals(
            MathQuestConfig.DEFAULT_MATH_QUIZ_ACTIVE_DB_DIR,
            MathQuestConfig.normalizeMathQuizActiveDbDir("~/Documents/Code/fof-mono/apps/math-quiz/_data/tl-kids")
        );
        assertEquals(
            "/Users/randytrue/.codex/worktrees/0013/fof-mono/apps/math-quiz/_data/tlkids",
            MathQuestConfig.normalizeMathQuizActiveDbDir("/Users/randytrue/.codex/worktrees/0013/fof-mono/apps/math-quiz/_data/tl-kids")
        );
        assertEquals(
            "/custom/path",
            MathQuestConfig.normalizeMathQuizActiveDbDir("/custom/path")
        );
    }
    @Test
    void migratesLegacyJsonKeysForMathQuizDbDirs() throws Exception {
        Path configDir = Files.createTempDirectory("mathquest-config");
        Path exportDir = Files.createTempDirectory("mathquest-export");
        Path activeDir = Files.createTempDirectory("mathquest-active");
        Path configFile = configDir.resolve("mathquest.json");
        Files.writeString(configFile, """
            {
              "mathQuizExportDir": "%s",
              "mathQuizActiveDir": "%s"
            }
            """.formatted(exportDir.toString(), activeDir.toString()));
        MathQuestPaths.setConfigDir(configDir);
        MathQuestConfig loaded = MathQuestConfig.load();
        assertEquals(exportDir.toString(), loaded.mathQuizSingleDbDir);
        assertEquals(activeDir.toString(), loaded.mathQuizActiveDbDir);
    }
    @Test
    void deprecatedExportDirAliasesStillResolve() {
        assertEquals(
            MathQuestConfig.DEFAULT_MATH_QUIZ_SINGLE_DB_DIR,
            MathQuestConfig.normalizeMathQuizExportDir("~/Documents/Code/fof-mono/apps/math-quiz/_data/mathquest")
        );
    }
    @Test
    void resolvesOptionalPathsWithoutCreatingDirectories() {
        String home = System.getProperty("user.home");
        assertNull(MathQuestConfig.resolveOptionalPath(null));
        assertNull(MathQuestConfig.resolveOptionalPath("  "));
        assertEquals(Path.of(home, "example-assets").normalize(), MathQuestConfig.resolveOptionalPath("~/example-assets"));
        assertEquals(Path.of("/tmp/mathquest-assets").normalize(), MathQuestConfig.resolveOptionalPath("/tmp/mathquest-assets"));
    }
    @Test
    void resolvesPlayerSpecificRewardBeforeGlobalGroup() {
        MathQuestConfig config = new MathQuestConfig();
        config.rewardGroups = new LinkedHashMap<>();
        MathQuestConfig.ensureJtreeGroup(config.rewardGroups);
        assertEquals("minecraft:diamond", config.resolveRewardsForPlayer("rjcomp").get(0).item);
        assertEquals("minecraft:cherry_sapling", config.resolveRewardsForPlayer("WildPetal").get(0).item);
        assertEquals("minecraft:polished_deepslate", config.resolveRewardsForPlayer("TreasureHunterM").get(0).item);
        assertEquals(1, config.resolveRewardsForPlayer("TreasureHunterM").get(0).count);
        assertEquals("minecraft:diamond", config.resolveRewardsForPlayer("UnknownPlayer").get(0).item);
        assertTrue(config.hasPlayerReward("PumaJockey"));
        assertFalse(config.hasPlayerReward("UnknownPlayer"));
    }

    @Test
    void tpCreditEarningReplacesStandardAndFluencyItemRewards() {
        MathQuestConfig config = new MathQuestConfig();
        config.setTpCreditEarningEnabled("PumaJockey", true);

        assertTrue(config.resolveRewardPlanForPlayer("PumaJockey").entries().isEmpty());
        assertTrue(config.resolveFluencyRewardPlanForPlayer("PumaJockey").entries().isEmpty());
        assertEquals("minecraft:golden_apple", config.playerRewards.get("pumajockey").item);
        assertEquals("minecraft:emerald", config.playerFluencyRewards.get("pumajockey").item);

        config.setTpCreditEarningEnabled("PumaJockey", false);
        assertEquals("minecraft:golden_apple", config.resolveRewardPlanForPlayer("PumaJockey").entries().get(0).item);
        assertEquals("minecraft:emerald", config.resolveFluencyRewardPlanForPlayer("PumaJockey").entries().get(0).item);
    }
    @Test
    void normalizesRewardGroupModeAliases() {
        assertEquals("all", MathQuestConfig.normalizeRewardGroupMode(null));
        assertEquals("all", MathQuestConfig.normalizeRewardGroupMode("give_all"));
        assertEquals("random", MathQuestConfig.normalizeRewardGroupMode("pick_one"));
        assertEquals("choose", MathQuestConfig.normalizeRewardGroupMode("player choose"));
    }
    @Test
    void resolveRewardPlanForPlayerUsesGroupRefAndMode() {
        MathQuestConfig config = new MathQuestConfig();
        config.rewardGroups = new LinkedHashMap<>();
        config.rewardGroups.put("prizes", new MathQuestConfig.RewardGroup("choose", List.of(
            new MathQuestConfig.RewardEntry("minecraft:emerald", 2),
            new MathQuestConfig.RewardEntry("minecraft:gold_ingot", 5)
        )));
        config.playerRewardGroups.put("wildpetal", "prizes");
        MathQuestConfig.RewardPlan plan = config.resolveRewardPlanForPlayer("WildPetal");
        assertEquals("choose", plan.mode());
        assertEquals(2, plan.entries().size());
        assertEquals("all", config.resolveRewardPlanForPlayer("rjcomp").mode());
    }
    @Test
    void resolveFluencyRewardPlanForPlayerUsesGroup() {
        MathQuestConfig config = new MathQuestConfig();
        config.rewardGroups = new LinkedHashMap<>();
        config.rewardGroups.put("ff", new MathQuestConfig.RewardGroup("choose", List.of(
            new MathQuestConfig.RewardEntry("minecraft:diamond", 1),
            new MathQuestConfig.RewardEntry("minecraft:iron_ingot", 2)
        )));
        config.playerFluencyRewardGroups.put("wildpetal", "ff");
        MathQuestConfig.RewardPlan plan = config.resolveFluencyRewardPlanForPlayer("WildPetal");
        assertEquals("choose", plan.mode());
        assertEquals(2, plan.entries().size());
        List<MathQuestConfig.RewardEntry> granted = config.resolveFluencyImprovementRewards("WildPetal");
        assertEquals(1, granted.size());
        assertEquals("ff", config.resolvePlayerFluencyRewardGroup("WildPetal"));
    }
    @Test
    void resolveActiveRewardPlanUsesGroupMode() {
        MathQuestConfig config = new MathQuestConfig();
        config.rewardGroups = new LinkedHashMap<>();
        config.rewardGroups.put("jtree", new MathQuestConfig.RewardGroup("random", List.of(
            new MathQuestConfig.RewardEntry("minecraft:diamond", 1),
            new MathQuestConfig.RewardEntry("minecraft:cactus", 1)
        )));
        config.rewardGroup = "jtree";
        MathQuestConfig.RewardPlan plan = config.resolveActiveRewardPlan();
        assertEquals("random", plan.mode());
        assertEquals(2, plan.entries().size());
    }
    @Test
    void rewardGroupJsonRoundTrip() {
        MathQuestConfig.RewardGroup group = new MathQuestConfig.RewardGroup("choose", List.of(
            new MathQuestConfig.RewardEntry("minecraft:diamond", 1),
            new MathQuestConfig.RewardEntry("minecraft:golden_apple", 2)
        ));
        MathQuestConfig.RewardGroup loaded = GSON.fromJson(GSON.toJson(group), MathQuestConfig.RewardGroup.class);
        assertEquals("choose", loaded.mode);
        assertEquals(2, loaded.entries.size());
        assertEquals("minecraft:golden_apple", loaded.entries.get(1).item);
    }
    @Test
    void migratesLegacyRewardBundleJsonShape() {
        String legacy = """
            {
              "rewardBundle": "jtree",
              "rewardBundles": {
                "jtree": [
                  {"item": "minecraft:diamond", "count": 1},
                  {"item": "minecraft:cactus", "count": 1}
                ]
              }
            }
            """;
        MathQuestConfig config = GSON.fromJson(legacy, MathQuestConfig.class);
        assertNull(config.rewardGroups);
        assertEquals("jtree", config.rewardGroup);
        if (config.rewardGroups == null) {
            config.rewardGroups = new LinkedHashMap<>();
        }
        com.google.gson.JsonObject root = com.google.gson.JsonParser.parseString(legacy).getAsJsonObject();
        assertTrue(root.has("rewardBundles"));
        assertFalse(root.has("rewardGroups"));
        com.google.gson.JsonObject bundles = root.getAsJsonObject("rewardBundles");
        for (String key : bundles.keySet()) {
            List<MathQuestConfig.RewardEntry> entries = new java.util.ArrayList<>();
            for (com.google.gson.JsonElement el : bundles.getAsJsonArray(key)) {
                com.google.gson.JsonObject obj = el.getAsJsonObject();
                entries.add(new MathQuestConfig.RewardEntry(
                    MathQuestConfig.normalizeItemId(obj.get("item").getAsString()),
                    obj.get("count").getAsInt()
                ));
            }
            config.rewardGroups.put(MathQuestConfig.normalizeGroupName(key), new MathQuestConfig.RewardGroup("random", entries));
        }
        assertEquals("random", config.rewardGroups.get("jtree").mode);
        assertEquals(2, config.rewardGroups.get("jtree").entries.size());
    }
    @Test
    void normalizesQuizTypeAliases() {
        assertEquals("standard_arithmetic", MathQuestConfig.normalizeQuizType(null));
        assertEquals("standard_arithmetic", MathQuestConfig.normalizeQuizType("standard"));
        assertEquals("written_column_arithmetic", MathQuestConfig.normalizeQuizType("paper"));
        assertEquals("written_column_arithmetic", MathQuestConfig.normalizeQuizType("written-column"));
        MathQuestConfig config = new MathQuestConfig();
        config.playerQuizTypes.put("wildpetal", "paper");
        assertEquals("written_column_arithmetic", config.resolveQuizType("WildPetal"));
    }
    @Test
    void normalizesInternalQuizSourceAliases() {
        assertEquals("internal_quick_quiz", MathQuestConfig.normalizeInternalQuizSource(null));
        assertEquals("internal_quick_quiz", MathQuestConfig.normalizeInternalQuizSource("quick"));
        assertEquals("internal_problem_list", MathQuestConfig.normalizeInternalQuizSource("problem list"));
        assertEquals("internal_fluency_feast", MathQuestConfig.normalizeInternalQuizSource("fluency feast"));
        assertEquals("generated", MathQuestConfig.normalizeInternalQuizSource("settings"));
        MathQuestConfig config = new MathQuestConfig();
        config.playerInternalQuizSources.put("wildpetal", "internal_problem_list");
        assertEquals("internal_problem_list", config.resolveInternalQuizSource("WildPetal"));
        assertTrue(config.resolveUseInternalProblemList("WildPetal"));
    }
    @Test
    void resolvesFluencyImprovementRewardPerPlayer() {
        MathQuestConfig config = new MathQuestConfig();
        assertTrue(config.resolveFluencyImprovementReward("WildPetal").isPresent());
        assertEquals("minecraft:emerald", config.resolveFluencyImprovementReward("WildPetal").get().item);
        assertFalse(config.resolveFluencyImprovementReward("UnknownPlayer").isPresent());
    }
    @Test
    void normalizesRewardItemIdsForControlPanelInput() {
        assertEquals("minecraft:diamond", MathQuestConfig.normalizeItemId(null));
        assertEquals("minecraft:diamond", MathQuestConfig.normalizeItemId("diamond"));
        assertEquals("minecraft:golden_apple", MathQuestConfig.normalizeItemId("Golden Apple"));
        assertEquals("minecraft:cooked_beef", MathQuestConfig.normalizeItemId("minecraft:cooked_beef"));
        assertEquals("othermod:math_prize", MathQuestConfig.normalizeItemId("othermod:math prize"));
    }
    @Test
    void resolvesPerPlayerNpcSelectionAndProblemCount() {
        MathQuestConfig config = new MathQuestConfig();
        config.playerNpcSelections.put("wildpetal", "paper_coach");
        config.playerNpcLocks.put("wildpetal", false);
        config.playerUseInternalProblemLists.put("wildpetal", false);
        config.playerRealNames.put("wildpetal", "Kid1");
        config.playerPresets.put("wildpetal", new MathQuestConfig.PlayerQuizPreset(2, 12, "addition", 8));
        assertEquals("paper_coach", config.resolveNpcSelection("WildPetal"));
        assertFalse(config.resolveNpcLock("WildPetal"));
        assertFalse(config.resolveUseInternalProblemList("WildPetal"));
        assertEquals("Kid1", config.resolveRealName("WildPetal"));
        MathQuestConfig.EffectiveQuizParams params = config.resolveForPlayer("WildPetal");
        assertEquals(2, params.minNumber());
        assertEquals(12, params.maxNumber());
        assertEquals("addition", params.operation());
        assertEquals(8, params.problemsPerQuiz());
    }

    @Test
    void resolvesAndMutatesTpCreditSettingsCaseInsensitivelyWithBounds() {
        MathQuestConfig config = new MathQuestConfig();
        config.playerTpCreditEarningEnabled.put("WiLdPeTaL", true);
        config.playerTpCreditsPerQuiz.put("WILDPETAL", 101);
        config.playerTpCreditBalances.put("wildPETAL", -7);
        config.playerTpCreditRewardChoices.put("WildPetal", "future_reward");

        assertTrue(config.resolveTpCreditEarningEnabled("wildpetal"));
        assertEquals(100, config.resolveTpCreditsPerQuiz("WildPetal"));
        assertEquals(0, config.resolveTpCreditBalance("WILDPETAL"));
        assertEquals("teleport", config.resolveTpCreditRewardChoice("wildpetal"));

        config.setTpCreditEarningEnabled("WILDPETAL", false);
        config.setTpCreditsPerQuiz("WildPetal", 0);
        config.setTpCreditBalance("wildpetal", -1);
        config.setTpCreditRewardChoice("WildPetal", "TELEPORT");
        assertFalse(config.resolveTpCreditEarningEnabled("wildpetal"));
        assertEquals(1, config.resolveTpCreditsPerQuiz("wildpetal"));
        assertEquals(0, config.resolveTpCreditBalance("wildpetal"));
        assertEquals("teleport", config.resolveTpCreditRewardChoice("wildpetal"));
        assertTrue(config.playerTpCreditBalances.containsKey("wildpetal"));
    }

    @Test
    void testJsonRoundTrip() {
        MathQuestConfig original = new MathQuestConfig();
        original.quizIntervalSeconds = 120;
        original.problemsPerQuiz = 10;
        original.minNumber = 5;
        original.maxNumber = 12;
        original.enabled = false;
        original.rewardMode = "all";
        original.setTpCreditEarningEnabled("WildPetal", true);
        original.setTpCreditsPerQuiz("WildPetal", 3);
        original.setTpCreditBalance("WildPetal", 9);
        original.setTpCreditRewardChoice("WildPetal", "teleport");

        String json = GSON.toJson(original);
        MathQuestConfig loaded = GSON.fromJson(json, MathQuestConfig.class);

        assertEquals(120, loaded.quizIntervalSeconds);
        assertEquals(10, loaded.problemsPerQuiz);
        assertEquals(5, loaded.minNumber);
        assertEquals(12, loaded.maxNumber);
        assertFalse(loaded.enabled);
        assertEquals("all", loaded.rewardMode);
        assertTrue(loaded.resolveTpCreditEarningEnabled("wildpetal"));
        assertEquals(3, loaded.resolveTpCreditsPerQuiz("WILDPETAL"));
        assertEquals(9, loaded.resolveTpCreditBalance("WildPetal"));
        assertEquals("teleport", loaded.resolveTpCreditRewardChoice("wildpetal"));
    }

    @Test
    void testRewardEntrySerialization() {
        MathQuestConfig.RewardEntry entry = new MathQuestConfig.RewardEntry("minecraft:diamond", 3);
        String json = GSON.toJson(entry);
        MathQuestConfig.RewardEntry loaded = GSON.fromJson(json, MathQuestConfig.RewardEntry.class);

        assertEquals("minecraft:diamond", loaded.item);
        assertEquals(3, loaded.count);
    }

    @Test
    void testJsonFileWriteAndRead(@TempDir Path tempDir) throws IOException {
        MathQuestConfig config = new MathQuestConfig();
        config.quizIntervalSeconds = 60;
        config.minNumber = 3;
        config.maxNumber = 8;

        Path configFile = tempDir.resolve("mathquest.json");
        Files.writeString(configFile, GSON.toJson(config));

        assertTrue(Files.exists(configFile));

        String json = Files.readString(configFile);
        MathQuestConfig loaded = GSON.fromJson(json, MathQuestConfig.class);

        assertEquals(60, loaded.quizIntervalSeconds);
        assertEquals(3, loaded.minNumber);
        assertEquals(8, loaded.maxNumber);
    }

    @Test
    void testPartialJsonLoadsDefaults() {
        // Simulates a config file with only some fields set
        String partialJson = """
            {
              "quizIntervalSeconds": 45,
              "minNumber": 4
            }
            """;
        MathQuestConfig loaded = GSON.fromJson(partialJson, MathQuestConfig.class);

        assertEquals(45, loaded.quizIntervalSeconds);
        assertEquals(4, loaded.minNumber);
        // Fields not in JSON retain their field initializer values
        assertEquals(9, loaded.maxNumber);
        assertEquals(5, loaded.problemsPerQuiz);
    }

    @Test
    void testEmptyJsonReturnsObject() {
        MathQuestConfig loaded = GSON.fromJson("{}", MathQuestConfig.class);
        assertNotNull(loaded);
    }
}
