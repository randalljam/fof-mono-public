package com.kidgames.mathquest.server;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.net.FluencyFeastResultData;
import com.kidgames.mathquest.persistence.FluencyFeastBridge;
import com.kidgames.mathquest.persistence.MathQuizProblemListLoader;
import com.kidgames.mathquest.persistence.MathQuizSessionPersistence;
import com.kidgames.mathquest.persistence.MathQuizSessionIngestor;
import com.kidgames.mathquest.persistence.QuizDatabase;
import com.kidgames.mathquest.persistence.SessionExporter;
import com.kidgames.mathquest.persistence.WrittenColumnSessionExporter;
import com.kidgames.mathquest.platform.MathQuestLog;
import com.kidgames.mathquest.platform.PlatformInventory;
import com.kidgames.mathquest.platform.PlatformNetwork;
import com.kidgames.mathquest.platform.PlayerContext;
import com.kidgames.mathquest.quiz.QuizManager;
import com.kidgames.mathquest.reward.TpCreditCompletionTracker;

import java.io.IOException;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

/** Shared server-side quiz result processing (DB, export, fluency feast). */
public final class QuizResultProcessor {
    public interface Hooks {
        void runPostQuizActions(String realName, PlayerContext player, List<QuizManager.Problem> problems);
        Path ingestSession(Path sessionPath, String realName);
    }

    private static final Hooks NO_HOOKS = new Hooks() {
        @Override
        public void runPostQuizActions(String realName, PlayerContext player, List<QuizManager.Problem> problems) {}
        @Override
        public Path ingestSession(Path sessionPath, String realName) {
            return MathQuizSessionIngestor.ingest(sessionPath, realName);
        }
    };

    private QuizResultProcessor() {}

    public static void process(
        String resultJson,
        PlayerContext player,
        PlatformInventory inventory,
        PlatformNetwork network,
        Hooks hooks
    ) {
        Hooks activeHooks = hooks == null ? NO_HOOKS : hooks;
        MathQuestConfig config = MathQuestConfig.INSTANCE;
        if (config == null) {
            MathQuestLog.LOGGER.error("[MathQuest] Config not loaded; cannot process quiz result");
            return;
        }
        try {
            JsonObject root = JsonParser.parseString(resultJson).getAsJsonObject();
            String quizType = root.has("quizType")
                ? MathQuestConfig.normalizeQuizType(root.get("quizType").getAsString())
                : "standard_arithmetic";
            if ("written_column_arithmetic".equals(quizType)) {
                if (processWrittenColumn(root, player)) {
                    settleTpCreditSession(root, player.username());
                }
                return;
            }
            String operation = root.get("operation").getAsString();
            int problemsTotal = root.get("problemsTotal").getAsInt();
            int problemsCorrect = root.get("problemsCorrect").getAsInt();
            boolean fluencyFeastMode = root.has("fluencyFeastMode") && root.get("fluencyFeastMode").getAsBoolean();
            String rewardGiven = root.has("rewardGiven") ? root.get("rewardGiven").getAsString() : "none";
            String username = player.username();
            String realName = config.resolveRealName(username);
            Path activeDir = config.resolveMathQuizActiveDbDir();
            int fluencyBefore = fluencyFeastMode
                ? FluencyFeastBridge.percentForRealName(realName, activeDir)
                    .map(FluencyFeastBridge.PercentResult::percent).orElse(0)
                : 0;
            QuizDatabase db = QuizDatabase.getInstance();
            long sessionId = db.startSession(problemsTotal);
            JsonArray problems = root.getAsJsonArray("problems");
            List<QuizManager.Problem> problemList = new ArrayList<>();
            for (int i = 0; i < problems.size(); i++) {
                JsonObject p = problems.get(i).getAsJsonObject();
                int factorA = p.get("factorA").getAsInt();
                int factorB = p.get("factorB").getAsInt();
                boolean isCorrect = p.get("isCorrect").getAsBoolean();
                long responseTimeMs = p.get("responseTimeMs").getAsLong();
                Long playerAnswer = p.has("playerAnswer") && !p.get("playerAnswer").isJsonNull()
                    ? p.get("playerAnswer").getAsLong() : null;
                String problemOperation = p.has("operation") && !p.get("operation").isJsonNull()
                    ? p.get("operation").getAsString()
                    : operation;
                QuizManager.Problem prob = QuizManager.Problem.create(problemOperation, factorA, factorB);
                prob.playerAnswer = playerAnswer;
                prob.isCorrect = isCorrect;
                prob.responseTimeMs = responseTimeMs;
                if (p.has("flags") && p.get("flags").isJsonArray()) {
                    for (var flag : p.getAsJsonArray("flags")) {
                        prob.addFlag(flag.getAsString());
                    }
                }
                db.recordAnswer(sessionId, i + 1, prob);
                problemList.add(prob);
            }
            db.endSession(sessionId, problemsCorrect, rewardGiven);
            QuizManager quiz = QuizManager.fromCompletedProblems(operation, problemList, problemsCorrect);
            Path sessionPath = SessionExporter.exportSession(quiz, realName, player.playerUuid());
            MathQuestLog.LOGGER.info("[MathQuest] Session exported to {}", sessionPath);
            MathQuizSessionPersistence.announceSingleSession(player, sessionPath);
            Path activeDbPath = activeHooks.ingestSession(sessionPath, realName);
            MathQuizSessionPersistence.announceActiveDb(player, activeDbPath);
            if (fluencyFeastMode) {
                int fluencyAfter = FluencyFeastBridge.percentForRealName(realName, activeDir)
                    .map(FluencyFeastBridge.PercentResult::percent)
                    .orElse(fluencyBefore);
                MathQuestLog.LOGGER.info("[MathQuest] Fluency feast for {}: {}% -> {}%", username, fluencyBefore, fluencyAfter);
                String fluencyRewardDescription = "";
                String fluencyRewardsJson = "[]";
                String fluencyRewardMode = "all";
                if (fluencyAfter - fluencyBefore >= 1 && problemsCorrect > 0) {
                    MathQuestConfig.RewardPlan fluencyPlan = config.resolveFluencyRewardPlanForPlayer(username);
                    List<MathQuestConfig.RewardEntry> fluencyRewards = fluencyPlan.entries();
                    fluencyRewardMode = MathQuestConfig.normalizeRewardGroupMode(fluencyPlan.mode());
                    if (!fluencyRewards.isEmpty()) {
                        if ("choose".equals(fluencyRewardMode) && fluencyRewards.size() > 1) {
                            fluencyRewardsJson = OpenQuizPayloadBuilder.rewardsJson(fluencyRewards);
                            fluencyRewardDescription = "Choose your fluency reward:";
                        } else {
                            List<MathQuestConfig.RewardEntry> grantedRewards = config.resolveFluencyImprovementRewards(username);
                            for (MathQuestConfig.RewardEntry entry : grantedRewards) {
                                inventory.grantReward(player, entry.item, entry.count);
                            }
                            fluencyRewardDescription = formatRewardDescriptions(grantedRewards);
                        }
                    } else {
                        fluencyRewardDescription = "Fluency improved!";
                    }
                } else if (problemsCorrect > 0) {
                    fluencyRewardDescription = "No fluency improvement reward this time.";
                }
                if (network != null) {
                    network.sendFluencyFeastResult(
                        player,
                        new FluencyFeastResultData(
                            fluencyBefore,
                            fluencyAfter,
                            fluencyRewardDescription,
                            fluencyRewardsJson,
                            fluencyRewardMode
                        )
                    );
                }
            }
            activeHooks.runPostQuizActions(realName, player, problemList);
            MathQuizProblemListLoader.consumeActiveProblemList(username).ifPresent(consumed ->
                MathQuestLog.LOGGER.info("[MathQuest] Math-quiz internal list '{}' {} for {}",
                    consumed.listName(), consumed.action(), username)
            );
            MathQuestLog.LOGGER.info("[MathQuest] Server recorded quiz result for {} ({}/{} correct)",
                username, problemsCorrect, problemsTotal);
            settleTpCreditSession(root, username);
        } catch (Exception e) {
            MathQuestLog.LOGGER.error("[MathQuest] Failed to process quiz result from {}: {}",
                player.username(), e.getMessage(), e);
            MathQuizSessionPersistence.announceFailure(player,
                "Failed to process quiz result: " + e.getMessage());
        }
    }

    public static void grantReward(PlatformInventory inventory, PlayerContext player, MathQuestConfig.RewardEntry entry) {
        if (inventory == null
            || player == null
            || !itemRewardsAllowed(player.username())
            || entry == null
            || entry.item == null
            || entry.item.isBlank()
            || entry.count <= 0) {
            return;
        }
        inventory.grantReward(player, entry.item, entry.count);
    }

    /** Server-side guard so TP-credit mode cannot also grant a client-requested item reward. */
    public static boolean itemRewardsAllowed(String playerName) {
        MathQuestConfig config = MathQuestConfig.INSTANCE;
        return config == null || !config.resolveTpCreditEarningEnabled(playerName);
    }

    private static boolean processWrittenColumn(JsonObject root, PlayerContext player) {
        MathQuestConfig config = MathQuestConfig.INSTANCE;
        String minecraftUsername = player.username();
        String realName = config.resolveRealName(minecraftUsername);
        String enteredCode = root.has("evaluatorCode") ? root.get("evaluatorCode").getAsString() : "";
        root.addProperty("evaluatorCodeAccepted", enteredCode.equals(config.writtenColumnEvaluatorCode));
        try {
            WrittenColumnSessionExporter.export(root, realName, player.playerUuid());
            MathQuestLog.LOGGER.info("[MathQuest] Server recorded written-column result for {} ({})",
                minecraftUsername, root.has("evaluation") ? root.get("evaluation").getAsString() : "unknown");
            return true;
        } catch (IOException e) {
            MathQuestLog.LOGGER.error("[MathQuest] Failed to export written-column result for {}: {}",
                minecraftUsername, e.getMessage());
            return false;
        }
    }

    /** Completes or cancels the player-bound TP session carried by a processed result. */
    private static void settleTpCreditSession(JsonObject root, String playerName) {
        if (!root.has("tpCreditCompletionToken") || root.get("tpCreditCompletionToken").isJsonNull()) return;
        String token = root.get("tpCreditCompletionToken").getAsString();
        if (token.isBlank()) return;
        boolean eligible = !root.has("tpCreditEligible") || root.get("tpCreditEligible").getAsBoolean();
        if (eligible) {
            TpCreditCompletionTracker.markCompleted(playerName, token);
        } else {
            TpCreditCompletionTracker.cancel(playerName, token);
        }
    }

    public static String formatRewardDescription(MathQuestConfig.RewardEntry entry) {
        String name = entry.item;
        if (name.contains(":")) name = name.substring(name.indexOf(':') + 1);
        name = name.replace('_', ' ');
        StringBuilder sb = new StringBuilder();
        for (String word : name.split(" ")) {
            if (sb.length() > 0) sb.append(' ');
            if (!word.isEmpty()) {
                sb.append(Character.toUpperCase(word.charAt(0)));
                if (word.length() > 1) sb.append(word.substring(1));
            }
        }
        return sb + " x" + entry.count;
    }

    public static String formatRewardDescriptions(List<MathQuestConfig.RewardEntry> entries) {
        if (entries == null || entries.isEmpty()) return "";
        StringBuilder desc = new StringBuilder();
        for (MathQuestConfig.RewardEntry entry : entries) {
            if (desc.length() > 0) desc.append(", ");
            desc.append(formatRewardDescription(entry));
        }
        return desc.toString();
    }
}
