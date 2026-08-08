package com.kidgames.mathquest.forge.platform;

import com.kidgames.mathquest.forge.net.MathQuestNetworkForge;
import com.kidgames.mathquest.net.FluencyFeastResultData;
import com.kidgames.mathquest.net.OpenQuizData;
import com.kidgames.mathquest.platform.PlatformNetwork;
import com.kidgames.mathquest.platform.PlayerContext;
import net.minecraft.server.level.ServerPlayer;

public final class ForgePlatformNetwork {
    private ForgePlatformNetwork() {}

    public static final class Server implements PlatformNetwork {
        @Override
        public void sendOpenQuiz(PlayerContext player, OpenQuizData data) {
            ServerPlayer serverPlayer = ForgePlatformPlayers.asServerPlayer(player);
            if (serverPlayer != null) {
                MathQuestNetworkForge.sendOpenQuiz(serverPlayer, data);
            }
        }

        @Override
        public void sendFluencyFeastResult(PlayerContext player, FluencyFeastResultData data) {
            ServerPlayer serverPlayer = ForgePlatformPlayers.asServerPlayer(player);
            if (serverPlayer != null) {
                MathQuestNetworkForge.sendFluencyFeastResult(serverPlayer, data);
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
            MathQuestNetworkForge.sendToServer(new MathQuestNetworkForge.GiveRewardPacket(itemId, count));
        }

        @Override
        public void sendQuizResultToServer(String resultJson) {
            MathQuestNetworkForge.sendToServer(new MathQuestNetworkForge.QuizResultPacket(resultJson));
        }

        @Override
        public void sendDespawnNerdsToServer() {
            MathQuestNetworkForge.sendToServer(new MathQuestNetworkForge.DespawnNerdsPacket());
        }
    }
}
