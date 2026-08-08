package com.kidgames.mathquest.server;

import com.kidgames.mathquest.persistence.MathQuizSessionIngestor;
import com.kidgames.mathquest.platform.FabricPlatformPlayers;
import com.kidgames.mathquest.platform.PlayerContext;
import com.kidgames.mathquest.quest.CaveEscapeQuestService;
import com.kidgames.mathquest.quiz.QuizManager;
import net.minecraft.server.level.ServerPlayer;

import java.nio.file.Path;
import java.util.List;

/** Fabric-specific hooks wired into shared QuizResultProcessor. */
public final class FabricQuizResultHooks implements QuizResultProcessor.Hooks {
    @Override
    public void runPostQuizActions(String realName, PlayerContext player, List<QuizManager.Problem> problems) {
        ServerPlayer serverPlayer = FabricPlatformPlayers.asServerPlayer(player);
        CaveEscapeQuestService.runPostQuizActions(realName, serverPlayer, problems);
    }

    @Override
    public Path ingestSession(Path sessionPath, String realName) {
        return MathQuizSessionIngestor.ingest(sessionPath, realName, FabricSessionIngestHooks.INSTANCE);
    }
}
