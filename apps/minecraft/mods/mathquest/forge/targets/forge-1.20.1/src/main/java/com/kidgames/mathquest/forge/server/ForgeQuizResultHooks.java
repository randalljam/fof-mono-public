package com.kidgames.mathquest.forge.server;

import com.kidgames.mathquest.persistence.MathQuizSessionIngestor;
import com.kidgames.mathquest.platform.PlayerContext;
import com.kidgames.mathquest.quiz.QuizManager;
import com.kidgames.mathquest.server.QuizResultProcessor;

import java.nio.file.Path;
import java.util.List;

/** Forge hooks wired into shared QuizResultProcessor (ingest only; quest hooks deferred). */
public final class ForgeQuizResultHooks implements QuizResultProcessor.Hooks {
    public static final ForgeQuizResultHooks INSTANCE = new ForgeQuizResultHooks();

    private ForgeQuizResultHooks() {}

    @Override
    public void runPostQuizActions(String realName, PlayerContext player, List<QuizManager.Problem> problems) {}

    @Override
    public Path ingestSession(Path sessionPath, String realName) {
        return MathQuizSessionIngestor.ingest(sessionPath, realName);
    }
}
