package com.kidgames.mathquest.persistence;

import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.platform.PlatformMessenger;
import com.kidgames.mathquest.platform.PlayerContext;
import com.kidgames.mathquest.quiz.QuizManager;

import java.io.IOException;
import java.nio.file.Path;
import java.util.UUID;
import java.util.function.Consumer;

/** Shared single-session export + active DB ingest with player chat feedback. */
public final class MathQuizSessionPersistence {
    private MathQuizSessionPersistence() {}

    public record Result(Path singleSessionFile, Path activeDbFile) {}

    public static Result persistCompletedQuiz(QuizManager quiz, String realName, UUID playerUuid, PlayerContext player) {
        return persistCompletedQuiz(quiz, realName, playerUuid, player, SessionIngestHooks.NONE, null);
    }

    public static Result persistCompletedQuiz(
        QuizManager quiz,
        String realName,
        UUID playerUuid,
        PlayerContext player,
        SessionIngestHooks hooks,
        Consumer<String> chatSink
    ) {
        Consumer<String> chat = chatSink != null ? chatSink : msg -> PlatformMessenger.send(player, msg);
        try {
            Path sessionPath = SessionExporter.exportSession(quiz, realName, playerUuid);
            chat.accept("Wrote single session to: " + sessionPath.toAbsolutePath().normalize());
            Path activeDbPath = MathQuizSessionIngestor.ingest(sessionPath, realName, hooks);
            announceActiveDb(chat, activeDbPath);
            return new Result(sessionPath.toAbsolutePath().normalize(), activeDbPath);
        } catch (IOException e) {
            chat.accept("[MathQuest] Failed to write single session DB: " + e.getMessage());
            throw new RuntimeException(e);
        }
    }

    public static void announceSingleSession(PlayerContext player, Path sessionPath) {
        PlatformMessenger.send(player, "Wrote single session to: " + sessionPath.toAbsolutePath().normalize());
    }

    public static void announceActiveDb(PlayerContext player, Path activeDbPath) {
        announceActiveDb(msg -> PlatformMessenger.send(player, msg), activeDbPath);
    }

    public static void announceActiveDb(Consumer<String> chat, Path activeDbPath) {
        if (activeDbPath != null) {
            chat.accept("Updated active DB file: " + activeDbPath.toAbsolutePath().normalize());
            return;
        }
        MathQuestConfig config = MathQuestConfig.INSTANCE;
        if (config != null && !config.mathQuizIngestEnabled) {
            chat.accept("Active DB ingest is disabled in config.");
        } else {
            chat.accept("Active DB ingest did not update a file (see latest.log).");
        }
    }

    public static void announceFailure(PlayerContext player, String message) {
        PlatformMessenger.send(player, "[MathQuest] " + message);
    }
}
