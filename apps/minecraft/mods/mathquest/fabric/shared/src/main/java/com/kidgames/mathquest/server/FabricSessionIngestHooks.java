package com.kidgames.mathquest.server;

import com.kidgames.mathquest.persistence.MathQuizSessionIngestor;
import com.kidgames.mathquest.persistence.SessionIngestHooks;
import com.kidgames.mathquest.platform.PlayerContext;
import com.kidgames.mathquest.quest.CaveEscapeQuestService;
import com.kidgames.mathquest.quiz.QuizManager;

import java.nio.file.Path;
import java.util.List;
import java.util.Optional;

/** Fabric quest hooks wired into shared QuizResultProcessor / session ingest. */
public final class FabricSessionIngestHooks implements SessionIngestHooks {
    public static final FabricSessionIngestHooks INSTANCE = new FabricSessionIngestHooks();

    private FabricSessionIngestHooks() {}

    @Override
    public Optional<Path> exactActiveFile(String realName) {
        return CaveEscapeQuestService.activeSqliteForRealName(realName);
    }

    @Override
    public void afterIngest(String realName, Path activePath) {
        CaveEscapeQuestService.refreshAfterIngest(realName, activePath);
    }
}
