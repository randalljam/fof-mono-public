package com.kidgames.mathquest.persistence;

import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.platform.MathQuestPaths;
import com.kidgames.mathquest.quiz.QuizManager;

import java.nio.file.Path;
import java.sql.*;
import java.time.Instant;
import java.util.List;

public class QuizDatabase {
    private static QuizDatabase instance;
    private Connection connection;

    private QuizDatabase() {}

    public static QuizDatabase getInstance() {
        if (instance == null) {
            instance = new QuizDatabase();
        }
        return instance;
    }

    private Connection getConnection() throws SQLException {
        SqliteDriver.ensureLoaded();
        if (connection == null || connection.isClosed()) {
            Path baseDir = (MathQuestConfig.INSTANCE != null)
                ? MathQuestConfig.INSTANCE.resolveDataDir()
                : MathQuestPaths.configDir();
            String dbPath = baseDir.resolve("mathquest_data.db").toAbsolutePath().toString();
            connection = DriverManager.getConnection("jdbc:sqlite:" + dbPath);
            createTables();
        }
        return connection;
    }

    private void createTables() throws SQLException {
        try (Statement stmt = getConnection().createStatement()) {
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
                    flags_json TEXT,
                    answered_at TEXT NOT NULL
                )
                """);
            ensureColumn(stmt, "answers", "flags_json", "TEXT");
        }
    }

    private void ensureColumn(Statement stmt, String tableName, String columnName, String definition) throws SQLException {
        try (ResultSet rs = stmt.executeQuery("PRAGMA table_info(" + tableName + ")")) {
            while (rs.next()) {
                if (columnName.equalsIgnoreCase(rs.getString("name"))) {
                    return;
                }
            }
        }
        stmt.executeUpdate("ALTER TABLE " + tableName + " ADD COLUMN " + columnName + " " + definition);
    }

    public long startSession(int problemsTotal) {
        try {
            PreparedStatement ps = getConnection().prepareStatement(
                "INSERT INTO sessions (started_at, problems_total) VALUES (?, ?)",
                Statement.RETURN_GENERATED_KEYS
            );
            ps.setString(1, Instant.now().toString());
            ps.setInt(2, problemsTotal);
            ps.executeUpdate();

            ResultSet rs = ps.getGeneratedKeys();
            if (rs.next()) {
                return rs.getLong(1);
            }
        } catch (SQLException e) {
            System.err.println("[MathQuest] Failed to start session: " + e.getMessage());
        }
        return -1;
    }

    public void recordAnswer(long sessionId, int questionIndex, QuizManager.Problem problem) {
        try {
            PreparedStatement ps = getConnection().prepareStatement(
                "INSERT INTO answers (session_id, question_index, factor_a, factor_b, correct_answer, player_answer, is_correct, response_time_ms, flags_json, answered_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            );
            ps.setLong(1, sessionId);
            ps.setInt(2, questionIndex);
            ps.setInt(3, problem.factorA);
            ps.setInt(4, problem.factorB);
            ps.setLong(5, problem.correctAnswer);
            if (problem.playerAnswer != null) {
                ps.setLong(6, problem.playerAnswer);
            } else {
                ps.setNull(6, java.sql.Types.BIGINT);
            }
            ps.setBoolean(7, problem.isCorrect);
            ps.setLong(8, problem.responseTimeMs);
            ps.setString(9, flagsJson(problem));
            ps.setString(10, Instant.now().toString());
            ps.executeUpdate();
        } catch (SQLException e) {
            System.err.println("[MathQuest] Failed to record answer: " + e.getMessage());
        }
    }

    public void updateAnswerFlags(long sessionId, int questionIndex, QuizManager.Problem problem) {
        try {
            PreparedStatement ps = getConnection().prepareStatement(
                "UPDATE answers SET flags_json = ? WHERE session_id = ? AND question_index = ?"
            );
            ps.setString(1, flagsJson(problem));
            ps.setLong(2, sessionId);
            ps.setInt(3, questionIndex);
            ps.executeUpdate();
        } catch (SQLException e) {
            System.err.println("[MathQuest] Failed to update answer flags: " + e.getMessage());
        }
    }

    private String flagsJson(QuizManager.Problem problem) {
        if (problem.flags == null || problem.flags.isEmpty()) return null;
        String notes = flagNotes(problem);
        StringBuilder out = new StringBuilder("[");
        int written = 0;
        for (String flag : problem.flags) {
            if (flag == null || flag.isBlank() || flag.startsWith("note:")) continue;
            if (written++ > 0) out.append(',');
            appendFlagObject(out, flag, notes);
        }
        if (written == 0 && !notes.isEmpty()) {
            appendFlagObject(out, "other", notes);
        }
        out.append(']');
        return out.toString();
    }

    private String flagNotes(QuizManager.Problem problem) {
        StringBuilder notes = new StringBuilder();
        for (String flag : problem.flags) {
            if (flag != null && flag.startsWith("note:")) {
                if (notes.length() > 0) notes.append(' ');
                notes.append(flag.substring("note:".length()).trim());
            }
        }
        return notes.toString().trim();
    }

    private void appendFlagObject(StringBuilder out, String reason, String notes) {
        out.append('{')
            .append("\"reason\":\"").append(escapeJson(reason)).append("\",")
            .append("\"label\":\"").append(escapeJson(flagLabel(reason))).append("\",")
            .append("\"timestamp\":\"\",")
            .append("\"notes\":\"").append(escapeJson(notes)).append("\"")
            .append('}');
    }

    private String flagLabel(String reason) {
        return switch (reason) {
            case "skip-noreason" -> "Skip - no reason";
            case "distracted" -> "Distracted";
            case "interrupted" -> "Interrupted";
            case "error" -> "Input Error";
            case "stall" -> "Stall";
            case "dontknow" -> "I Don't Know";
            case "other" -> "Other";
            case "flag_previous" -> "Flag previous";
            case "needs_practice" -> "Needs practice";
            default -> reason;
        };
    }

    private String escapeJson(String value) {
        return value
            .replace("\\", "\\\\")
            .replace("\"", "\\\"");
    }

    public void endSession(long sessionId, int correctCount, String rewardGiven) {
        try {
            PreparedStatement ps = getConnection().prepareStatement(
                "UPDATE sessions SET ended_at = ?, problems_correct = ?, reward_given = ? WHERE id = ?"
            );
            ps.setString(1, Instant.now().toString());
            ps.setInt(2, correctCount);
            ps.setString(3, rewardGiven);
            ps.setLong(4, sessionId);
            ps.executeUpdate();
        } catch (SQLException e) {
            System.err.println("[MathQuest] Failed to end session: " + e.getMessage());
        }
    }

    public void close() {
        try {
            if (connection != null && !connection.isClosed()) {
                connection.close();
            }
        } catch (SQLException e) {
            System.err.println("[MathQuest] Failed to close database: " + e.getMessage());
        }
    }
}
