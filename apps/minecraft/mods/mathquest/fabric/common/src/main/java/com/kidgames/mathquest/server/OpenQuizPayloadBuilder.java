package com.kidgames.mathquest.server;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.net.FluencyFeastResultData;
import com.kidgames.mathquest.net.OpenQuizData;
import com.kidgames.mathquest.persistence.FluencyFeastBridge;
import com.kidgames.mathquest.persistence.MathQuizFluencyLoader;
import com.kidgames.mathquest.persistence.MathQuizProblemListLoader;
import com.kidgames.mathquest.platform.MathQuestLog;
import com.kidgames.mathquest.platform.PlatformInventory;
import com.kidgames.mathquest.platform.PlatformNetwork;
import com.kidgames.mathquest.platform.PlayerContext;
import com.kidgames.mathquest.quiz.QuizManager;
import com.kidgames.mathquest.quiz.QuizSessionOptions;
import com.kidgames.mathquest.reward.TpCreditCompletionTracker;

import java.io.IOException;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

/** Loader-agnostic quiz-open payload assembly from config + problem lists. */
public final class OpenQuizPayloadBuilder {
    public interface QuestHook {
        Optional<OpenQuizData> questPayloadForPlayer(String playerName, boolean directToQuiz);
        Optional<List<QuizManager.Problem>> questProblemsForPlayer(
            String playerName,
            MathQuestConfig.EffectiveQuizParams params
        );
    }

    private static final QuestHook NO_QUEST = new QuestHook() {
        @Override
        public Optional<OpenQuizData> questPayloadForPlayer(String playerName, boolean directToQuiz) {
            return Optional.empty();
        }
        @Override
        public Optional<List<QuizManager.Problem>> questProblemsForPlayer(
            String playerName,
            MathQuestConfig.EffectiveQuizParams params
        ) {
            return Optional.empty();
        }
    };

    private OpenQuizPayloadBuilder() {}

    public static OpenQuizData create(String playerName) {
        return create(playerName, false, NO_QUEST, true);
    }

    public static OpenQuizData createDirect(String playerName) {
        return create(playerName, true, NO_QUEST, true);
    }

    /** Builds status/diagnostic preview data without issuing a redeemable completion session. */
    public static OpenQuizData createPreview(String playerName) {
        return create(playerName, false, NO_QUEST, false);
    }

    public static OpenQuizData create(String playerName, boolean directToQuiz, QuestHook questHook) {
        return create(playerName, directToQuiz, questHook, true);
    }

    private static OpenQuizData create(
        String playerName,
        boolean directToQuiz,
        QuestHook questHook,
        boolean issueTpCreditSession
    ) {
        QuestHook hook = questHook == null ? NO_QUEST : questHook;
        Optional<OpenQuizData> questPayload = hook.questPayloadForPlayer(playerName, directToQuiz);
        if (questPayload.isPresent()) {
            MathQuestLog.LOGGER.info("[MathQuest] Loaded quest quiz payload for {}", playerName);
            return issueTpCreditSession
                ? withTpCreditSession(questPayload.get(), playerName)
                : questPayload.get();
        }
        MathQuestConfig config = MathQuestConfig.INSTANCE;
        MathQuestConfig.EffectiveQuizParams params = config.resolveForPlayer(playerName);
        String problemsJson = "[]";
        String source = config.resolveInternalQuizSource(playerName);
        Optional<List<QuizManager.Problem>> questProblems = hook.questProblemsForPlayer(playerName, params);
        if (questProblems.isPresent()) {
            MathQuizProblemListLoader.clearActiveProblemList(playerName);
            MathQuestLog.LOGGER.info("[MathQuest] Loaded {} quest problems for {}", questProblems.get().size(), playerName);
            problemsJson = problemsJson(questProblems.get());
        } else if ("internal_problem_list".equals(source)) {
            var loaded = MathQuizProblemListLoader.loadForMinecraftPlayer(
                playerName,
                config.resolvePlayerRealNames()
            );
            if (loaded.isPresent()) {
                MathQuizProblemListLoader.rememberActiveProblemList(playerName, loaded.get());
                MathQuestLog.LOGGER.info("[MathQuest] Loaded {} problems from math-quiz list '{}' for {} ({})",
                    loaded.get().problems().size(), loaded.get().listName(), playerName, loaded.get().realName());
                problemsJson = problemsJson(loaded.get().problems());
            } else {
                MathQuizProblemListLoader.clearActiveProblemList(playerName);
            }
        } else if ("internal_quick_quiz".equals(source)) {
            MathQuizProblemListLoader.clearActiveProblemList(playerName);
            var loaded = MathQuizProblemListLoader.loadQuickQuizForMinecraftPlayer(
                playerName,
                params.operation(),
                config.resolvePlayerRealNames()
            );
            if (loaded.isPresent()) {
                MathQuestLog.LOGGER.info("[MathQuest] Loaded {} quick-quiz problems for {} ({}) operation {}",
                    loaded.get().problems().size(), playerName, loaded.get().realName(), loaded.get().operation());
                problemsJson = problemsJson(loaded.get().problems());
            }
        } else if ("internal_fluency_feast".equals(source)) {
            MathQuizProblemListLoader.clearActiveProblemList(playerName);
            String realName = config.resolveRealName(playerName);
            var generated = FluencyFeastBridge.generateForRealName(realName, config.resolveMathQuizActiveDir());
            if (generated.isPresent()) {
                int requestedCount = generated.get().requestedCount();
                int actualCount = generated.get().problems().size();
                MathQuestLog.LOGGER.info(
                    "[MathQuest] Generated {} fluency-feast problems (requested {}) for {} ({})",
                    actualCount, requestedCount > 0 ? requestedCount : actualCount, playerName, realName);
                for (String warning : generated.get().warnings()) {
                    MathQuestLog.LOGGER.info("[MathQuest] Fluency feast note for {}: {}", playerName, warning);
                }
                problemsJson = problemsJson(generated.get().problems());
            } else {
                MathQuestLog.LOGGER.error(
                    "[MathQuest] Fluency feast generation failed for {} ({}) — check node executable (mathQuizNodeExecutable) and latest.log",
                    playerName, realName);
            }
        } else {
            MathQuizProblemListLoader.clearActiveProblemList(playerName);
        }
        MathQuestConfig.RewardPlan rewardPlan = config.resolveRewardPlanForPlayer(playerName);
        String quizType = config.resolveQuizType(playerName);
        boolean fluencyFeast = "internal_fluency_feast".equals(source);
        QuizSessionOptions options = fluencyFeast ? QuizSessionOptions.fluencyFeast() : QuizSessionOptions.standard();
        if (issueTpCreditSession) {
            options = options.withTpCreditCompletionToken(TpCreditCompletionTracker.issue(playerName));
        }
        int payloadProblemCount = params.problemsPerQuiz();
        if (fluencyFeast) {
            payloadProblemCount = feastProblemCount(config, playerName);
            if (!"[]".equals(problemsJson)) {
                try {
                    payloadProblemCount = com.google.gson.JsonParser.parseString(problemsJson).getAsJsonArray().size();
                } catch (Exception ignored) {}
            }
        }
        return new OpenQuizData(
            params.operation(),
            params.minNumber(),
            params.maxNumber(),
            payloadProblemCount,
            problemsJson,
            rewardsJson(rewardPlan.entries()),
            rewardPlan.mode(),
            quizType,
            options.toJson(),
            fluencyFeast,
            directToQuiz
        );
    }

    /** Adds a fresh one-use TP-credit session to an already assembled quiz payload. */
    public static OpenQuizData withTpCreditSession(OpenQuizData data, String playerName) {
        QuizSessionOptions options = QuizSessionOptions.fromJson(data.optionsJson())
            .withTpCreditCompletionToken(TpCreditCompletionTracker.issue(playerName));
        return new OpenQuizData(
            data.operation(),
            data.minNumber(),
            data.maxNumber(),
            data.problemsPerQuiz(),
            data.problemsJson(),
            data.rewardsJson(),
            data.rewardMode(),
            data.quizType(),
            options.toJson(),
            data.fluencyFeastMode(),
            data.directToQuiz()
        );
    }

    public static String problemsJson(List<QuizManager.Problem> problems) {
        JsonArray arr = new JsonArray();
        if (problems == null) return "[]";
        for (QuizManager.Problem p : problems) {
            JsonObject obj = new JsonObject();
            obj.addProperty("operation", p.operation);
            obj.addProperty("factorA", p.factorA);
            obj.addProperty("factorB", p.factorB);
            arr.add(obj);
        }
        return arr.toString();
    }

    private static int feastProblemCount(MathQuestConfig config, String playerName) {
        try {
            String realName = config.resolveRealName(playerName);
            var db = MathQuizFluencyLoader.latestDbForRealName(config.resolveMathQuizActiveDbDir(), realName);
            if (db.isPresent()) {
                return MathQuizFluencyLoader.loadFeastConfig(db.get(), realName).count();
            }
        } catch (Exception ignored) {}
        return MathQuizFluencyLoader.DEFAULT_COUNT;
    }

    public static String rewardsJson(List<MathQuestConfig.RewardEntry> rewards) {
        JsonArray arr = new JsonArray();
        if (rewards == null) return "[]";
        for (MathQuestConfig.RewardEntry entry : rewards) {
            if (entry == null || entry.item == null || entry.item.isBlank() || entry.count <= 0) continue;
            JsonObject obj = new JsonObject();
            obj.addProperty("item", entry.item);
            obj.addProperty("count", entry.count);
            arr.add(obj);
        }
        return arr.toString();
    }
}
