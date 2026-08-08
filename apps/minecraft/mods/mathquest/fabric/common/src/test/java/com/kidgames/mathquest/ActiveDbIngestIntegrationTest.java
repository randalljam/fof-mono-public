package com.kidgames.mathquest;

import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.persistence.MathQuizSessionIngestor;
import com.kidgames.mathquest.persistence.SessionExporter;
import com.kidgames.mathquest.persistence.SqliteDriver;
import com.kidgames.mathquest.quiz.QuizManager;
import org.junit.jupiter.api.Assumptions;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.TimeUnit;

import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** End-to-end active DB ingest via session_ingest.py (skipped when python3 unavailable). */
class ActiveDbIngestIntegrationTest {
    @Test
    void ingest_appendsSingleSessionIntoActiveDbFile(@TempDir Path configDir, @TempDir Path dataDir) throws Exception {
        Assumptions.assumeTrue(python3Available(), "python3 required for active DB ingest integration test");

        Path singleDbDir = dataDir.resolve("_single-session-sqlite-files");
        Path activeDbDir = dataDir.resolve("tlkids");
        Files.createDirectories(singleDbDir);
        Files.createDirectories(activeDbDir);
        MathQuestPathsTestHelper.initConfig(configDir, singleDbDir);
        MathQuestConfig.INSTANCE.mathQuizActiveDbDir = activeDbDir.toString();
        MathQuestConfig.INSTANCE.mathQuizIngestEnabled = true;
        MathQuestConfig.INSTANCE.mathQuizIngestPython = "python3";

        Path toolsDir = Path.of(System.getProperty("user.dir"))
            .resolve("../../../../../math-quiz/tools")
            .normalize();
        Assumptions.assumeTrue(Files.isRegularFile(toolsDir.resolve("session_ingest.py")),
            "session_ingest.py not found at " + toolsDir);

        SqliteDriver.requireLoaded();
        QuizManager.Problem problem = QuizManager.Problem.create("addition", 1, 2);
        problem.playerAnswer = 3L;
        problem.isCorrect = true;
        problem.responseTimeMs = 400;
        QuizManager quiz = QuizManager.fromCompletedProblems("addition", List.of(problem), 1);

        Path singleSession = SessionExporter.exportSession(quiz, "Randy", UUID.randomUUID(), singleDbDir);
        assertTrue(Files.isRegularFile(singleSession));

        Path activeDb = MathQuizSessionIngestor.ingest(singleSession, "Randy");
        assertNotNull(activeDb, "ingest should return active DB path");
        assertTrue(Files.isRegularFile(activeDb), "active DB file should exist at " + activeDb);
        assertTrue(activeDb.startsWith(activeDbDir.normalize()));
    }

    private static boolean python3Available() {
        try {
            Process process = new ProcessBuilder("python3", "--version").start();
            return process.waitFor(5, TimeUnit.SECONDS) && process.exitValue() == 0;
        } catch (Exception e) {
            return false;
        }
    }
}
