package com.kidgames.mathquest;

import com.kidgames.mathquest.quiz.QuizManager;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Path;
import java.sql.*;
import java.time.Instant;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for quiz database recording.
 * Uses a standalone SQLite connection (no Fabric dependencies).
 * Run with: ./gradlew test
 */
public class DatabaseTest {

    private Connection connection;

    @BeforeEach
    void setUp(@TempDir Path tempDir) throws SQLException {
        String dbPath = tempDir.resolve("test_mathquest.db").toAbsolutePath().toString();
        connection = DriverManager.getConnection("jdbc:sqlite:" + dbPath);

        try (Statement stmt = connection.createStatement()) {
            stmt.executeUpdate("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    problems_total INTEGER,
                    problems_correct INTEGER,
                    reward_given TEXT
                )
                """);

            stmt.executeUpdate("""
                CREATE TABLE IF NOT EXISTS answers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL REFERENCES sessions(id),
                    question_index INTEGER NOT NULL,
                    factor_a INTEGER NOT NULL,
                    factor_b INTEGER NOT NULL,
                    correct_answer INTEGER NOT NULL,
                    player_answer INTEGER,
                    is_correct BOOLEAN NOT NULL,
                    response_time_ms INTEGER NOT NULL,
                    answered_at TEXT NOT NULL
                )
                """);
        }
    }

    @AfterEach
    void tearDown() throws SQLException {
        if (connection != null && !connection.isClosed()) {
            connection.close();
        }
    }

    @Test
    void testCreateSession() throws SQLException {
        long sessionId = insertSession(5);
        assertTrue(sessionId > 0);

        try (Statement stmt = connection.createStatement()) {
            ResultSet rs = stmt.executeQuery("SELECT * FROM sessions WHERE id = " + sessionId);
            assertTrue(rs.next());
            assertEquals(5, rs.getInt("problems_total"));
            assertNotNull(rs.getString("started_at"));
            assertNull(rs.getString("ended_at"));
        }
    }

    @Test
    void testEndSession() throws SQLException {
        long sessionId = insertSession(5);
        endSession(sessionId, 4, "minecraft:diamond:1");

        try (Statement stmt = connection.createStatement()) {
            ResultSet rs = stmt.executeQuery("SELECT * FROM sessions WHERE id = " + sessionId);
            assertTrue(rs.next());
            assertEquals(4, rs.getInt("problems_correct"));
            assertNotNull(rs.getString("ended_at"));
            assertEquals("minecraft:diamond:1", rs.getString("reward_given"));
        }
    }

    @Test
    void testRecordAnswer() throws SQLException {
        long sessionId = insertSession(5);

        QuizManager.Problem problem = QuizManager.Problem.create("multiplication", 7, 8);
        problem.playerAnswer = 56L;
        problem.isCorrect = true;
        problem.responseTimeMs = 2340;

        recordAnswer(sessionId, 1, problem);

        try (Statement stmt = connection.createStatement()) {
            ResultSet rs = stmt.executeQuery("SELECT * FROM answers WHERE session_id = " + sessionId);
            assertTrue(rs.next());
            assertEquals(1, rs.getInt("question_index"));
            assertEquals(7, rs.getInt("factor_a"));
            assertEquals(8, rs.getInt("factor_b"));
            assertEquals(56, rs.getLong("correct_answer"));
            assertEquals(56, rs.getLong("player_answer"));
            assertTrue(rs.getBoolean("is_correct"));
            assertEquals(2340, rs.getLong("response_time_ms"));
            assertNotNull(rs.getString("answered_at"));
        }
    }

    @Test
    void testRecordWrongAnswer() throws SQLException {
        long sessionId = insertSession(5);

        QuizManager.Problem problem = QuizManager.Problem.create("multiplication", 6, 9);
        problem.playerAnswer = 52L;
        problem.isCorrect = false;
        problem.responseTimeMs = 4100;

        recordAnswer(sessionId, 1, problem);

        try (Statement stmt = connection.createStatement()) {
            ResultSet rs = stmt.executeQuery("SELECT * FROM answers WHERE session_id = " + sessionId);
            assertTrue(rs.next());
            assertEquals(54, rs.getLong("correct_answer"));
            assertEquals(52, rs.getLong("player_answer"));
            assertFalse(rs.getBoolean("is_correct"));
            assertEquals(4100, rs.getLong("response_time_ms"));
        }
    }

    @Test
    void testMultipleAnswersPerSession() throws SQLException {
        long sessionId = insertSession(3);

        for (int i = 1; i <= 3; i++) {
            QuizManager.Problem p = QuizManager.Problem.create("multiplication", i + 1, i + 2);
            p.playerAnswer = p.correctAnswer;
            p.isCorrect = true;
            p.responseTimeMs = 1000 * i;
            recordAnswer(sessionId, i, p);
        }

        try (Statement stmt = connection.createStatement()) {
            ResultSet rs = stmt.executeQuery(
                "SELECT COUNT(*) as cnt FROM answers WHERE session_id = " + sessionId);
            assertTrue(rs.next());
            assertEquals(3, rs.getInt("cnt"));
        }
    }

    @Test
    void testResponseTimeIsPositive() throws SQLException {
        long sessionId = insertSession(1);

        QuizManager.Problem problem = QuizManager.Problem.create("multiplication", 3, 4);
        problem.playerAnswer = 12L;
        problem.isCorrect = true;
        problem.responseTimeMs = 1500;

        recordAnswer(sessionId, 1, problem);

        try (Statement stmt = connection.createStatement()) {
            ResultSet rs = stmt.executeQuery(
                "SELECT response_time_ms FROM answers WHERE session_id = " + sessionId);
            assertTrue(rs.next());
            assertTrue(rs.getLong("response_time_ms") > 0);
        }
    }

    @Test
    void testMasteryQuery() throws SQLException {
        long sessionId = insertSession(4);

        // 7x8 correct twice
        recordProblem(sessionId, 1, 7, 8, 56, true, 2000);
        recordProblem(sessionId, 2, 7, 8, 56, true, 1800);
        // 6x9 wrong once, then correct
        recordProblem(sessionId, 3, 6, 9, 54, false, 5000);
        recordProblem(sessionId, 4, 6, 9, 54, true, 3000);

        // Mastery query: accuracy and avg time by factor pair
        try (Statement stmt = connection.createStatement()) {
            ResultSet rs = stmt.executeQuery("""
                SELECT factor_a, factor_b,
                  COUNT(*) as attempts,
                  SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct,
                  AVG(response_time_ms) as avg_time_ms
                FROM answers WHERE session_id = %d
                GROUP BY factor_a, factor_b
                ORDER BY factor_a, factor_b
                """.formatted(sessionId));

            // 6x9: 2 attempts, 1 correct
            assertTrue(rs.next());
            assertEquals(6, rs.getInt("factor_a"));
            assertEquals(9, rs.getInt("factor_b"));
            assertEquals(2, rs.getInt("attempts"));
            assertEquals(1, rs.getInt("correct"));

            // 7x8: 2 attempts, 2 correct
            assertTrue(rs.next());
            assertEquals(7, rs.getInt("factor_a"));
            assertEquals(8, rs.getInt("factor_b"));
            assertEquals(2, rs.getInt("attempts"));
            assertEquals(2, rs.getInt("correct"));
        }
    }

    // Helper methods that mirror QuizDatabase logic without Fabric dependencies

    private long insertSession(int problemsTotal) throws SQLException {
        PreparedStatement ps = connection.prepareStatement(
            "INSERT INTO sessions (started_at, problems_total) VALUES (?, ?)",
            Statement.RETURN_GENERATED_KEYS
        );
        ps.setString(1, Instant.now().toString());
        ps.setInt(2, problemsTotal);
        ps.executeUpdate();
        ResultSet rs = ps.getGeneratedKeys();
        return rs.next() ? rs.getLong(1) : -1;
    }

    private void endSession(long sessionId, int correctCount, String rewardGiven) throws SQLException {
        PreparedStatement ps = connection.prepareStatement(
            "UPDATE sessions SET ended_at = ?, problems_correct = ?, reward_given = ? WHERE id = ?"
        );
        ps.setString(1, Instant.now().toString());
        ps.setInt(2, correctCount);
        ps.setString(3, rewardGiven);
        ps.setLong(4, sessionId);
        ps.executeUpdate();
    }

    private void recordAnswer(long sessionId, int questionIndex, QuizManager.Problem problem) throws SQLException {
        PreparedStatement ps = connection.prepareStatement(
            "INSERT INTO answers (session_id, question_index, factor_a, factor_b, correct_answer, player_answer, is_correct, response_time_ms, answered_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
        );
        ps.setLong(1, sessionId);
        ps.setInt(2, questionIndex);
        ps.setInt(3, problem.factorA);
        ps.setInt(4, problem.factorB);
        ps.setLong(5, problem.correctAnswer);
        if (problem.playerAnswer != null) {
            ps.setLong(6, problem.playerAnswer);
        } else {
            ps.setNull(6, Types.BIGINT);
        }
        ps.setBoolean(7, problem.isCorrect);
        ps.setLong(8, problem.responseTimeMs);
        ps.setString(9, Instant.now().toString());
        ps.executeUpdate();
    }

    private void recordProblem(long sessionId, int idx, int a, int b, int answer, boolean correct, long timeMs) throws SQLException {
        QuizManager.Problem p = QuizManager.Problem.create("multiplication", a, b);
        p.playerAnswer = (long) (correct ? answer : answer - 2);
        p.isCorrect = correct;
        p.responseTimeMs = timeMs;
        recordAnswer(sessionId, idx, p);
    }
}
