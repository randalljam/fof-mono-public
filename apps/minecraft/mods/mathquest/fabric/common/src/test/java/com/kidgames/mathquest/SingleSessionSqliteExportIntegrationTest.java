package com.kidgames.mathquest;

import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.persistence.MathQuizSessionPersistence;
import com.kidgames.mathquest.persistence.SqliteDriver;
import com.kidgames.mathquest.platform.PlayerContext;
import com.kidgames.mathquest.quiz.QuizManager;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.Statement;
import java.util.List;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** End-to-end single-session SQLite export (requires sqlite-jdbc on test classpath). */
class SingleSessionSqliteExportIntegrationTest {
    @Test
    void persistCompletedQuiz_writesReadableSingleSessionFile(@TempDir Path configDir, @TempDir Path singleDbDir) throws Exception {
        MathQuestPathsTestHelper.initConfig(configDir, singleDbDir);
        SqliteDriver.requireLoaded();

        QuizManager.Problem problem = QuizManager.Problem.create("multiplication", 2, 3);
        problem.playerAnswer = 6L;
        problem.isCorrect = true;
        problem.responseTimeMs = 800;
        QuizManager quiz = QuizManager.fromCompletedProblems("multiplication", List.of(problem), 1);
        PlayerContext player = new PlayerContext("WildPetal", UUID.randomUUID());

        MathQuizSessionPersistence.Result result = MathQuizSessionPersistence.persistCompletedQuiz(
            quiz,
            "Randy",
            player.playerUuid(),
            player
        );

        assertNotNull(result.singleSessionFile());
        assertTrue(Files.isRegularFile(result.singleSessionFile()));
        assertTrue(result.singleSessionFile().startsWith(singleDbDir.normalize()));

        try (Connection conn = DriverManager.getConnection("jdbc:sqlite:" + result.singleSessionFile())) {
            assertEquals(1, tableCount(conn, "Sessions"));
            assertEquals(1, tableCount(conn, "ProblemAttempts"));
            try (Statement stmt = conn.createStatement();
                 ResultSet rs = stmt.executeQuery("SELECT user_name FROM Sessions")) {
                assertTrue(rs.next());
                assertEquals("Randy", rs.getString(1));
            }
        }
    }

    private static int tableCount(Connection conn, String table) throws Exception {
        try (Statement stmt = conn.createStatement();
             ResultSet rs = stmt.executeQuery("SELECT COUNT(*) FROM " + table)) {
            rs.next();
            return rs.getInt(1);
        }
    }
}
