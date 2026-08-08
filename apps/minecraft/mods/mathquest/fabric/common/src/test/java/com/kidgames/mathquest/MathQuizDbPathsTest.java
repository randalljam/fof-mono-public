package com.kidgames.mathquest;

import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.persistence.MathQuizDbPaths;
import com.kidgames.mathquest.persistence.SessionExporter;
import com.kidgames.mathquest.quiz.QuizManager;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertTrue;

class MathQuizDbPathsTest {
    @Test
    void probeWritable_createsDirAndAcceptsWrites(@TempDir Path tempDir) throws Exception {
        Path target = tempDir.resolve("single-db");
        MathQuizDbPaths.ProbeResult result = MathQuizDbPaths.probeWritable(target);
        assertTrue(result.ok(), result.error());
        assertTrue(Files.isDirectory(result.path()));
    }

    @Test
    void resolvedSingleDbDir_writesSessionFile(@TempDir Path configDir, @TempDir Path singleDbDir) throws Exception {
        MathQuestPathsTestHelper.initConfig(configDir, singleDbDir);
        MathQuizDbPaths.ProbeResult probe = MathQuizDbPaths.probeWritable(
            MathQuestConfig.INSTANCE.resolveMathQuizSingleDbDir());
        assertTrue(probe.ok(), probe.error());

        QuizManager.Problem problem = QuizManager.Problem.create("multiplication", 2, 3);
        problem.playerAnswer = 6L;
        problem.isCorrect = true;
        problem.responseTimeMs = 500;
        QuizManager quiz = QuizManager.fromCompletedProblems("multiplication", java.util.List.of(problem), 1);

        Path exported = SessionExporter.exportSession(quiz, "Randy", UUID.randomUUID());
        assertTrue(Files.isRegularFile(exported), "expected sqlite at " + exported);
        assertTrue(exported.startsWith(singleDbDir));
    }
}
