package com.kidgames.mathquest.network;

import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.net.OpenQuizData;
import com.kidgames.mathquest.platform.FabricPlatformNetwork;
import com.kidgames.mathquest.quest.CaveEscapeQuestService;
import com.kidgames.mathquest.quiz.QuizManager;
import com.kidgames.mathquest.server.OpenQuizPayloadBuilder;
import net.minecraft.server.level.ServerPlayer;

import java.util.List;
import java.util.Optional;

public class QuizPayloadBuilder {
    private static final OpenQuizPayloadBuilder.QuestHook FABRIC_QUEST_HOOK = new OpenQuizPayloadBuilder.QuestHook() {
        @Override
        public Optional<OpenQuizData> questPayloadForPlayer(String playerName, boolean directToQuiz) {
            return Optional.empty();
        }

        @Override
        public Optional<List<QuizManager.Problem>> questProblemsForPlayer(
            String playerName,
            MathQuestConfig.EffectiveQuizParams params
        ) {
            return CaveEscapeQuestService.problemsForPlayer(
                playerName,
                params,
                MathQuestConfig.INSTANCE.resolvePlayerRealNames()
            );
        }
    };

    public static OpenQuizPayload create(ServerPlayer player) {
        return create(player, false);
    }

    public static OpenQuizPayload createDirect(ServerPlayer player) {
        return create(player, true);
    }

    private static OpenQuizPayload create(ServerPlayer player, boolean directToQuiz) {
        var questPayload = CaveEscapeQuestService.quizPayloadForPlayer(player, directToQuiz);
        if (questPayload.isPresent()) {
            OpenQuizPayload payload = questPayload.get();
            OpenQuizData data = OpenQuizPayloadBuilder.withTpCreditSession(
                new OpenQuizData(
                    payload.operation(),
                    payload.minNumber(),
                    payload.maxNumber(),
                    payload.problemsPerQuiz(),
                    payload.problemsJson(),
                    payload.rewardsJson(),
                    payload.rewardMode(),
                    payload.quizType(),
                    payload.optionsJson(),
                    payload.fluencyFeastMode(),
                    payload.directToQuiz()
                ),
                player.getName().getString()
            );
            return FabricPlatformNetwork.toOpenQuizPayload(data);
        }
        OpenQuizData data = OpenQuizPayloadBuilder.create(
            player.getName().getString(),
            directToQuiz,
            FABRIC_QUEST_HOOK
        );
        return FabricPlatformNetwork.toOpenQuizPayload(data);
    }

    public static String problemsJson(List<QuizManager.Problem> problems) {
        return OpenQuizPayloadBuilder.problemsJson(problems);
    }

    public static String rewardsJson(List<MathQuestConfig.RewardEntry> rewards) {
        return OpenQuizPayloadBuilder.rewardsJson(rewards);
    }
}
