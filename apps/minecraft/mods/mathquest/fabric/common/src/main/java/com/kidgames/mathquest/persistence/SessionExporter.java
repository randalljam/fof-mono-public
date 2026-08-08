package com.kidgames.mathquest.persistence;

import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.platform.MathQuestPaths;
import com.kidgames.mathquest.quiz.QuizManager;

import java.io.IOException;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.sql.Statement;
import java.sql.Types;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.LinkedHashSet;
import java.util.UUID;

/**
 * Exports one completed MathQuest quiz as one math-quiz-compatible SQLite file.
 * Contract: apps/math-quiz/docs/2026-06-20_minecraft-mod-single-session-sqlite-spec.md
 *
 * File naming: mathquest_{real-name}_{YYYY-MM-DD_HHMMSS}.sqlite
 */
public class SessionExporter {
    private static final DateTimeFormatter TIMESTAMP_FORMAT =
        DateTimeFormatter.ofPattern("yyyy-MM-dd_HHmmss");
    private static final DateTimeFormatter ISO_FORMAT = DateTimeFormatter.ISO_LOCAL_DATE_TIME;
    public static Path exportSession(QuizManager quiz, String username, UUID playerUuid) throws IOException {
        Path outputDir = (MathQuestConfig.INSTANCE != null)
            ? MathQuestConfig.INSTANCE.resolveMathQuizSingleDbDir()
            : MathQuestPaths.sessionsDir();
        return exportSession(quiz, username, playerUuid, outputDir);
    }
    public static Path exportSession(QuizManager quiz, String username, UUID playerUuid, Path outputDir) throws IOException {
        Files.createDirectories(outputDir);
        LocalDateTime now = LocalDateTime.now();
        String timestamp = now.format(TIMESTAMP_FORMAT);
        String sessionId = UUID.randomUUID().toString();
        String safeUsername = sanitizeUsername(username);
        String filename = "mathquest_" + safeUsername + "_" + timestamp + ".sqlite";
        Path outputPath = outputDir.resolve(filename);
        Path tempPath = outputDir.resolve(filename + ".tmp");
        Files.deleteIfExists(tempPath);
        try {
            writeSqliteFile(tempPath, filename, sessionId, quiz, username, playerUuid, timestamp, now.format(ISO_FORMAT));
            moveAtomically(tempPath, outputPath);
            return outputPath;
        } catch (SQLException e) {
            try {
                Files.deleteIfExists(tempPath);
            } catch (IOException ignored) {}
            throw new IOException("Failed to export MathQuest SQLite session", e);
        }
    }
    private static void writeSqliteFile(
        Path path,
        String filename,
        String sessionId,
        QuizManager quiz,
        String username,
        UUID playerUuid,
        String timestamp,
        String isoTimestamp
    ) throws SQLException {
        SqliteDriver.requireLoaded();
        try (Connection conn = DriverManager.getConnection("jdbc:sqlite:" + path.toAbsolutePath())) {
            conn.setAutoCommit(false);
            createTables(conn);
            insertUser(conn, username);
            insertSession(conn, filename, sessionId, quiz, username, playerUuid, timestamp);
            insertProblems(conn, sessionId, quiz);
            insertModeEvent(conn, sessionId, username, isoTimestamp);
            conn.commit();
        }
    }
    private static void createTables(Connection conn) throws SQLException {
        try (Statement stmt = conn.createStatement()) {
            stmt.executeUpdate("""
                CREATE TABLE Users (
                  name TEXT PRIMARY KEY
                )
                """);
            stmt.executeUpdate("""
                CREATE TABLE Sessions (
                  session_id TEXT PRIMARY KEY,
                  session_filename TEXT,
                  user_name TEXT,
                  start_time TEXT,
                  end_time TEXT,
                  num_problems INTEGER,
                  number_range_start INTEGER,
                  number_range_end INTEGER,
                  numbers_include TEXT,
                  numbers_exclude TEXT,
                  num_numbers INTEGER,
                  operations TEXT,
                  total_problems INTEGER,
                  correct_answers INTEGER,
                  average_response_time_ms INTEGER,
                  FOREIGN KEY (user_name) REFERENCES Users(name)
                )
                """);
            stmt.executeUpdate("""
                CREATE TABLE ProblemAttempts (
                  attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  session_id TEXT,
                  problem_id TEXT,
                  problem_text TEXT,
                  num1 INTEGER,
                  num2 INTEGER,
                  operation TEXT,
                  correct_answer REAL,
                  user_answer_string TEXT,
                  user_answer REAL,
                  is_correct INTEGER,
                  response_time_ms INTEGER,
                  flags_json TEXT,
                  presented_at TEXT,
                  FOREIGN KEY (session_id) REFERENCES Sessions(session_id)
                )
                """);
            stmt.executeUpdate("""
                CREATE TABLE ModeEvents (
                  event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_name TEXT,
                  session_id TEXT NULL,
                  from_mode TEXT NULL,
                  to_mode TEXT,
                  trigger TEXT,
                  timestamp TEXT
                )
                """);
        }
    }
    private static void insertUser(Connection conn, String username) throws SQLException {
        try (PreparedStatement ps = conn.prepareStatement("INSERT INTO Users (name) VALUES (?)")) {
            ps.setString(1, usernameOrUnknown(username));
            ps.executeUpdate();
        }
    }
    private static void insertSession(
        Connection conn,
        String filename,
        String sessionId,
        QuizManager quiz,
        String username,
        UUID playerUuid,
        String timestamp
    ) throws SQLException {
        try (PreparedStatement ps = conn.prepareStatement("""
            INSERT INTO Sessions (
              session_id, session_filename, user_name, start_time, end_time,
              num_problems, number_range_start, number_range_end, numbers_include,
              numbers_exclude, num_numbers, operations, total_problems, correct_answers,
              average_response_time_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """)) {
            ps.setString(1, sessionId);
            ps.setString(2, filename);
            ps.setString(3, usernameOrUnknown(username));
            ps.setString(4, timestamp);
            ps.setString(5, timestamp);
            ps.setInt(6, quiz.getTotalProblems());
            ps.setInt(7, quiz.getMinNumber());
            ps.setInt(8, quiz.getMaxNumber());
            ps.setString(9, playerUuid != null ? "[\"player_uuid:" + escapeJson(playerUuid.toString()) + "\"]" : "[]");
            ps.setString(10, "[]");
            ps.setInt(11, 2);
            ps.setString(12, operationsJson(quiz));
            ps.setInt(13, quiz.getProblems().size());
            ps.setInt(14, quiz.getCorrectCount());
            ps.setLong(15, averageResponseTime(quiz.getProblems()));
            ps.executeUpdate();
        }
    }
    private static void insertProblems(Connection conn, String sessionId, QuizManager quiz) throws SQLException {
        try (PreparedStatement ps = conn.prepareStatement("""
            INSERT INTO ProblemAttempts (
              session_id, problem_id, problem_text, num1, num2, operation, correct_answer,
              user_answer_string, user_answer, is_correct, response_time_ms, flags_json,
              presented_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """)) {
            List<QuizManager.Problem> problems = quiz.getProblems();
            for (int i = 0; i < problems.size(); i++) {
                QuizManager.Problem p = problems.get(i);
                ps.setString(1, sessionId);
                ps.setString(2, String.valueOf(i + 1));
                ps.setString(3, p.getProblemTextForExport());
                ps.setInt(4, p.factorA);
                ps.setInt(5, p.factorB);
                ps.setString(6, operationSymbol(p.operation));
                ps.setLong(7, p.correctAnswer);
                ps.setString(8, p.playerAnswer != null ? String.valueOf(p.playerAnswer) : "");
                if (p.playerAnswer != null) {
                    ps.setLong(9, p.playerAnswer);
                } else {
                    ps.setNull(9, Types.REAL);
                }
                ps.setInt(10, p.isCorrect ? 1 : 0);
                ps.setLong(11, p.responseTimeMs);
                ps.setString(12, flagsJson(p));
                ps.setNull(13, Types.VARCHAR);
                ps.addBatch();
            }
            ps.executeBatch();
        }
    }
    private static void insertModeEvent(Connection conn, String sessionId, String username, String isoTimestamp) throws SQLException {
        try (PreparedStatement ps = conn.prepareStatement("""
            INSERT INTO ModeEvents (user_name, session_id, from_mode, to_mode, trigger, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """)) {
            ps.setString(1, usernameOrUnknown(username));
            ps.setString(2, sessionId);
            ps.setNull(3, Types.VARCHAR);
            ps.setString(4, "assess");
            ps.setString(5, "mathquest-quiz");
            ps.setString(6, isoTimestamp);
            ps.executeUpdate();
        }
    }
    private static long averageResponseTime(List<QuizManager.Problem> problems) {
        if (problems.isEmpty()) return 0;
        long totalTime = 0;
        for (QuizManager.Problem p : problems) {
            totalTime += p.responseTimeMs;
        }
        return Math.round((double) totalTime / problems.size());
    }
    private static String operationSymbol(String operation) {
        return switch (operation) {
            case "addition" -> "+";
            case "subtraction" -> "-";
            case "division" -> "/";
            case "exponentiation" -> "^";
            default -> "*";
        };
    }
    private static String operationsJson(QuizManager quiz) {
        LinkedHashSet<String> symbols = new LinkedHashSet<>();
        for (QuizManager.Problem problem : quiz.getProblems()) {
            symbols.add(operationSymbol(problem.operation));
        }
        if (symbols.isEmpty()) {
            symbols.add(operationSymbol(quiz.getOperation()));
        }
        StringBuilder out = new StringBuilder("[");
        int i = 0;
        for (String symbol : symbols) {
            if (i++ > 0) out.append(',');
            out.append('"').append(symbol).append('"');
        }
        out.append(']');
        return out.toString();
    }
    private static String flagsJson(QuizManager.Problem problem) {
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
    private static String flagNotes(QuizManager.Problem problem) {
        StringBuilder notes = new StringBuilder();
        for (String flag : problem.flags) {
            if (flag != null && flag.startsWith("note:")) {
                if (notes.length() > 0) notes.append(' ');
                notes.append(flag.substring("note:".length()).trim());
            }
        }
        return notes.toString().trim();
    }
    private static void appendFlagObject(StringBuilder out, String reason, String notes) {
        out.append('{')
            .append("\"reason\":\"").append(escapeJson(reason)).append("\",")
            .append("\"label\":\"").append(escapeJson(flagLabel(reason))).append("\",")
            .append("\"timestamp\":\"\",")
            .append("\"notes\":\"").append(escapeJson(notes)).append("\"")
            .append('}');
    }
    private static String flagLabel(String reason) {
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
    private static String sanitizeUsername(String username) {
        return usernameOrUnknown(username).replaceAll("[^a-zA-Z0-9_-]", "_");
    }
    private static String usernameOrUnknown(String username) {
        if (username == null || username.isBlank()) return "unknown";
        return username;
    }
    private static String escapeJson(String value) {
        return value.replace("\\", "\\\\").replace("\"", "\\\"");
    }
    private static void moveAtomically(Path source, Path target) throws IOException {
        try {
            Files.move(source, target, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
        } catch (AtomicMoveNotSupportedException e) {
            Files.move(source, target, StandardCopyOption.REPLACE_EXISTING);
        }
    }
}
