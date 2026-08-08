package com.kidgames.mathquest;

import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.persistence.SessionExporter;
import com.kidgames.mathquest.quiz.QuizManager;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for the math-quiz-compatible single-session SQLite export format.
 */
class SessionExporterTest {
    @TempDir
    Path tempDir;
    private QuizManager createCompletedQuiz(String operation, int[][] answers) {
        MathQuestConfig config = new MathQuestConfig();
        config.operation = operation;
        config.problemsPerQuiz = answers.length;
        config.minNumber = 0;
        config.maxNumber = 9;
        QuizManager quiz = new QuizManager(config);
        for (int i = 0; i < answers.length; i++) {
            QuizManager.Problem p = quiz.getCurrentProblem();
            assertNotNull(p);
            p.responseTimeMs = answers[i][0];
            quiz.submitAnswer(answers[i][1] == Integer.MIN_VALUE ? p.correctAnswer : answers[i][1]);
            quiz.advanceToNext();
        }
        return quiz;
    }
    @Test
    void exportsSingleSessionSqliteFile() throws Exception {
        QuizManager quiz = createCompletedQuiz("multiplication", new int[][] {
            {1000, Integer.MIN_VALUE},
            {2500, -999}
        });
        UUID playerUuid = UUID.fromString("550e8400-e29b-41d4-a716-446655440000");
        Path output = SessionExporter.exportSession(quiz, "Player One", playerUuid, tempDir);
        assertTrue(Files.exists(output));
        assertTrue(output.getFileName().toString().startsWith("mathquest_Player_One_"));
        assertTrue(output.getFileName().toString().endsWith(".sqlite"));
        try (Connection conn = DriverManager.getConnection("jdbc:sqlite:" + output.toAbsolutePath())) {
            assertEquals(1, count(conn, "Users"));
            assertEquals(1, count(conn, "Sessions"));
            assertEquals(2, count(conn, "ProblemAttempts"));
            assertEquals(1, count(conn, "ModeEvents"));
            try (Statement stmt = conn.createStatement()) {
                ResultSet session = stmt.executeQuery("SELECT * FROM Sessions");
                assertTrue(session.next());
                assertEquals("Player One", session.getString("user_name"));
                assertEquals(output.getFileName().toString(), session.getString("session_filename"));
                assertEquals(2, session.getInt("num_problems"));
                assertEquals(2, session.getInt("total_problems"));
                assertEquals(1, session.getInt("correct_answers"));
                assertEquals(1750, session.getInt("average_response_time_ms"));
                assertEquals("[\"*\"]", session.getString("operations"));
                assertTrue(session.getString("numbers_include").contains("player_uuid:550e8400-e29b-41d4-a716-446655440000"));
            }
        }
    }
    @Test
    void problemRowsUseCanonicalOperatorsAndNullableAnswers() throws Exception {
        MathQuestConfig config = new MathQuestConfig();
        config.operation = "addition";
        config.problemsPerQuiz = 1;
        QuizManager quiz = new QuizManager(config);
        QuizManager.Problem p = quiz.getCurrentProblem();
        assertNotNull(p);
        p.responseTimeMs = 1234;
        quiz.submitAnswer(p.correctAnswer);
        quiz.advanceToNext();
        Path output = SessionExporter.exportSession(quiz, "Learner", null, tempDir);
        try (Connection conn = DriverManager.getConnection("jdbc:sqlite:" + output.toAbsolutePath());
             Statement stmt = conn.createStatement()) {
            ResultSet row = stmt.executeQuery("SELECT * FROM ProblemAttempts");
            assertTrue(row.next());
            assertEquals("1", row.getString("problem_id"));
            assertEquals("+", row.getString("operation"));
            assertEquals(p.factorA + " + " + p.factorB, row.getString("problem_text"));
            assertEquals(p.factorA, row.getInt("num1"));
            assertEquals(p.factorB, row.getInt("num2"));
            assertEquals(p.correctAnswer, row.getLong("correct_answer"));
            assertEquals(String.valueOf(p.correctAnswer), row.getString("user_answer_string"));
            assertEquals(1, row.getInt("is_correct"));
            assertEquals(1234, row.getInt("response_time_ms"));
            assertNull(row.getString("flags_json"));
            assertNull(row.getString("presented_at"));
        }
    }
    @Test
    void exportsProblemFlagsJson() throws Exception {
        QuizManager.Problem p = QuizManager.Problem.create("addition", 0, 0);
        p.responseTimeMs = 1500;
        p.addFlag("skip-noreason");
        p.addFlag("distracted");
        p.addFlag("note:needed help reading the problem");
        QuizManager quiz = QuizManager.fromCompletedProblems("addition", java.util.List.of(p), 0);
        Path output = SessionExporter.exportSession(quiz, "Flagged", null, tempDir);
        try (Connection conn = DriverManager.getConnection("jdbc:sqlite:" + output.toAbsolutePath());
             Statement stmt = conn.createStatement()) {
            ResultSet row = stmt.executeQuery("SELECT flags_json FROM ProblemAttempts");
            assertTrue(row.next());
            assertEquals(
                "[{\"reason\":\"skip-noreason\",\"label\":\"Skip - no reason\",\"timestamp\":\"\",\"notes\":\"needed help reading the problem\"},"
                    + "{\"reason\":\"distracted\",\"label\":\"Distracted\",\"timestamp\":\"\",\"notes\":\"needed help reading the problem\"}]",
                row.getString("flags_json")
            );
        }
    }
    @Test
    void handlesUnansweredProblems() throws Exception {
        QuizManager.Problem p = QuizManager.Problem.create("subtraction", 7, 3);
        p.responseTimeMs = 0;
        QuizManager quiz = QuizManager.fromCompletedProblems("subtraction", java.util.List.of(p), 0);
        Path output = SessionExporter.exportSession(quiz, "NoAnswer", null, tempDir);
        try (Connection conn = DriverManager.getConnection("jdbc:sqlite:" + output.toAbsolutePath());
             Statement stmt = conn.createStatement()) {
            ResultSet row = stmt.executeQuery("SELECT * FROM ProblemAttempts");
            assertTrue(row.next());
            assertEquals("-", row.getString("operation"));
            assertEquals("", row.getString("user_answer_string"));
            assertNull(row.getObject("user_answer"));
            assertEquals(0, row.getInt("is_correct"));
        }
    }
    @Test
    void exportsDistinctOperationSymbolsForMixedProblemLists() throws Exception {
        QuizManager quiz = new QuizManager(
            new MathQuestConfig.EffectiveQuizParams(0, 9, "multiplication", 2),
            java.util.List.of(
                QuizManager.Problem.create("+", 1, 2),
                QuizManager.Problem.create("*", 3, 4)
            )
        );
        Path output = SessionExporter.exportSession(quiz, "Mixed", null, tempDir);
        try (Connection conn = DriverManager.getConnection("jdbc:sqlite:" + output.toAbsolutePath());
             Statement stmt = conn.createStatement()) {
            ResultSet session = stmt.executeQuery("SELECT operations FROM Sessions");
            assertTrue(session.next());
            assertEquals("[\"+\",\"*\"]", session.getString("operations"));
        }
    }
    private int count(Connection conn, String table) throws SQLException {
        try (Statement stmt = conn.createStatement()) {
            ResultSet rs = stmt.executeQuery("SELECT COUNT(*) FROM " + table);
            assertTrue(rs.next());
            return rs.getInt(1);
        }
    }
}
