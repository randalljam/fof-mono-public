package com.kidgames.mathquest.forge.net;

import com.kidgames.mathquest.forge.screen.QuizOfferScreenForge;
import com.kidgames.mathquest.forge.screen.QuizResultScreenForge;
import net.minecraft.client.Minecraft;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.api.distmarker.OnlyIn;

@OnlyIn(Dist.CLIENT)
public final class MathQuestNetworkClientHandlers {
    private MathQuestNetworkClientHandlers() {}

    static void handleOpenQuiz(MathQuestNetworkForge.OpenQuizPacket msg) {
        Minecraft client = Minecraft.getInstance();
        if (client == null) return;
        client.setScreen(new QuizOfferScreenForge(msg));
    }

    static void handleFluencyFeastResult(MathQuestNetworkForge.FluencyFeastResultPacket msg) {
        QuizResultScreenForge.applyServerFluencyResult(
            msg.before(),
            msg.after(),
            msg.rewardDescription(),
            msg.rewardsJson(),
            msg.rewardMode()
        );
    }
}
