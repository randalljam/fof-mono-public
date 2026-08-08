package com.kidgames.mathquest.platform;

import com.kidgames.mathquest.net.FluencyFeastResultData;
import com.kidgames.mathquest.net.OpenQuizData;
import com.kidgames.mathquest.network.FluencyFeastResultPayload;
import com.kidgames.mathquest.network.GiveRewardPayload;
import com.kidgames.mathquest.network.OpenQuizPayload;
import com.kidgames.mathquest.network.QuizResultPayload;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayNetworking;
import net.fabricmc.fabric.api.networking.v1.ServerPlayNetworking;
import net.minecraft.server.level.ServerPlayer;

public final class FabricPlatformNetwork {
    private FabricPlatformNetwork() {}

    public static final class Server implements PlatformNetwork {
        @Override
        public void sendOpenQuiz(PlayerContext player, OpenQuizData data) {
            ServerPlayer serverPlayer = FabricPlatformPlayers.asServerPlayer(player);
            if (serverPlayer != null) {
                ServerPlayNetworking.send(serverPlayer, toOpenQuizPayload(data));
            }
        }

        @Override
        public void sendFluencyFeastResult(PlayerContext player, FluencyFeastResultData data) {
            ServerPlayer serverPlayer = FabricPlatformPlayers.asServerPlayer(player);
            if (serverPlayer != null) {
                ServerPlayNetworking.send(serverPlayer, toFluencyPayload(data));
            }
        }

        @Override
        public void sendGiveRewardToServer(String itemId, int count) {
            throw new UnsupportedOperationException("Server cannot send C2S give-reward");
        }

        @Override
        public void sendQuizResultToServer(String resultJson) {
            throw new UnsupportedOperationException("Server cannot send C2S quiz-result");
        }

        @Override
        public void sendDespawnNerdsToServer() {
            throw new UnsupportedOperationException("Server cannot send C2S despawn-nerds");
        }
    }

    public static final class Client implements PlatformNetwork {
        @Override
        public void sendOpenQuiz(PlayerContext player, OpenQuizData data) {
            throw new UnsupportedOperationException("Client cannot send S2C open-quiz");
        }

        @Override
        public void sendFluencyFeastResult(PlayerContext player, FluencyFeastResultData data) {
            throw new UnsupportedOperationException("Client cannot send S2C fluency result");
        }

        @Override
        public void sendGiveRewardToServer(String itemId, int count) {
            ClientPlayNetworking.send(new GiveRewardPayload(itemId, count));
        }

        @Override
        public void sendQuizResultToServer(String resultJson) {
            ClientPlayNetworking.send(new QuizResultPayload(resultJson));
        }

        @Override
        public void sendDespawnNerdsToServer() {
            ClientPlayNetworking.send(new com.kidgames.mathquest.network.DespawnNerdsPayload());
        }
    }

    public static OpenQuizPayload toOpenQuizPayload(OpenQuizData data) {
        return new OpenQuizPayload(
            data.operation(),
            data.minNumber(),
            data.maxNumber(),
            data.problemsPerQuiz(),
            data.problemsJson(),
            data.rewardsJson(),
            data.rewardMode(),
            data.quizType(),
            data.optionsJson(),
            data.fluencyFeastMode(),
            data.directToQuiz()
        );
    }

    public static FluencyFeastResultPayload toFluencyPayload(FluencyFeastResultData data) {
        return new FluencyFeastResultPayload(
            data.beforePercent(),
            data.afterPercent(),
            data.rewardDescription(),
            data.rewardsJson(),
            data.rewardMode()
        );
    }
}
