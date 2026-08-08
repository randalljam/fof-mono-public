package com.kidgames.mathquest.platform;

import com.kidgames.mathquest.net.FluencyFeastResultData;
import com.kidgames.mathquest.net.OpenQuizData;

/** Loader-specific network send hooks. Server impl sends S2C; client impl sends C2S. */
public interface PlatformNetwork {
    void sendOpenQuiz(PlayerContext player, OpenQuizData data);
    void sendFluencyFeastResult(PlayerContext player, FluencyFeastResultData data);
    void sendGiveRewardToServer(String itemId, int count);
    void sendQuizResultToServer(String resultJson);
    void sendDespawnNerdsToServer();
}
