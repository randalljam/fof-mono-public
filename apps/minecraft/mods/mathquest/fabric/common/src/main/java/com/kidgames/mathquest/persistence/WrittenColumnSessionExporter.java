package com.kidgames.mathquest.persistence;

import com.google.gson.JsonObject;
import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.platform.MathQuestPaths;

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
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.UUID;

public class WrittenColumnSessionExporter {
    private static final DateTimeFormatter TIMESTAMP_FORMAT =
        DateTimeFormatter.ofPattern("yyyy-MM-dd_HHmmss");
    private static final DateTimeFormatter ISO_FORMAT = DateTimeFormatter.ISO_LOCAL_DATE_TIME;
    public static Path export(JsonObject result, String username, UUID playerUuid) throws IOException {
        Path outputDir = (MathQuestConfig.INSTANCE != null)
            ? MathQuestConfig.INSTANCE.resolveMathQuizExportDir()
            : MathQuestPaths.sessionsDir();
        return export(result, username, playerUuid, outputDir);
    }
    public static Path export(JsonObject result, String username, UUID playerUuid, Path outputDir) throws IOException {
        Files.createDirectories(outputDir);
        LocalDateTime now = LocalDateTime.now();
        String timestamp = now.format(TIMESTAMP_FORMAT);
        String sessionId = UUID.randomUUID().toString();
        String safeUsername = sanitizeUsername(username);
        String filename = "mathquest_written_column_" + safeUsername + "_" + timestamp + ".sqlite";
        Path outputPath = outputDir.resolve(filename);
        Path tempPath = outputDir.resolve(filename + ".tmp");
        Files.deleteIfExists(tempPath);
        try {
            writeSqliteFile(tempPath, filename, sessionId, result, username, playerUuid, timestamp, now.format(ISO_FORMAT));
            moveAtomically(tempPath, outputPath);
            return outputPath;
        } catch (SQLException e) {
            try {
                Files.deleteIfExists(tempPath);
            } catch (IOException ignored) {}
            throw new IOException("Failed to export written-column SQLite session", e);
        }
    }
    private static void writeSqliteFile(
        Path path,
        String filename,
        String sessionId,
        JsonObject result,
        String username,
        UUID playerUuid,
        String timestamp,
        String isoTimestamp
    ) throws SQLException {
        try (Connection conn = DriverManager.getConnection("jdbc:sqlite:" + path.toAbsolutePath())) {
            conn.setAutoCommit(false);
            createTables(conn);
            insertSession(conn, filename, sessionId, result, username, playerUuid, timestamp, isoTimestamp);
            conn.commit();
        }
    }
    private static void createTables(Connection conn) throws SQLException {
        try (Statement stmt = conn.createStatement()) {
            stmt.executeUpdate("""
                CREATE TABLE WrittenColumnSessions (
                  session_id TEXT PRIMARY KEY,
                  session_filename TEXT,
                  user_name TEXT,
                  player_uuid TEXT,
                  created_at TEXT,
                  quiz_type TEXT,
                  source TEXT
                )
                """);
            stmt.executeUpdate("""
                CREATE TABLE WrittenColumnAttempts (
                  attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  session_id TEXT,
                  operation TEXT,
                  factor_a INTEGER,
                  factor_b INTEGER,
                  correct_answer INTEGER,
                  prompt_text TEXT,
                  student_answer_text TEXT,
                  evaluation TEXT,
                  is_correct INTEGER,
                  evaluator_code_accepted INTEGER,
                  evaluator_notes TEXT,
                  response_time_ms INTEGER,
                  recorded_at TEXT,
                  FOREIGN KEY (session_id) REFERENCES WrittenColumnSessions(session_id)
                )
                """);
        }
    }
    private static void insertSession(
        Connection conn,
        String filename,
        String sessionId,
        JsonObject result,
        String username,
        UUID playerUuid,
        String timestamp,
        String isoTimestamp
    ) throws SQLException {
        try (PreparedStatement ps = conn.prepareStatement("""
            INSERT INTO WrittenColumnSessions (
              session_id, session_filename, user_name, player_uuid, created_at, quiz_type, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """)) {
            ps.setString(1, sessionId);
            ps.setString(2, filename);
            ps.setString(3, usernameOrUnknown(username));
            ps.setString(4, playerUuid == null ? null : playerUuid.toString());
            ps.setString(5, timestamp);
            ps.setString(6, "written_column_arithmetic");
            ps.setString(7, "mathquest");
            ps.executeUpdate();
        }
        try (PreparedStatement ps = conn.prepareStatement("""
            INSERT INTO WrittenColumnAttempts (
              session_id, operation, factor_a, factor_b, correct_answer, prompt_text,
              student_answer_text, evaluation, is_correct, evaluator_code_accepted,
              evaluator_notes, response_time_ms, recorded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """)) {
            ps.setString(1, sessionId);
            ps.setString(2, stringValue(result, "operation", "addition"));
            ps.setInt(3, intValue(result, "factorA", 0));
            ps.setInt(4, intValue(result, "factorB", 0));
            ps.setLong(5, longValue(result, "correctAnswer", 0));
            ps.setString(6, stringValue(result, "promptText", ""));
            ps.setString(7, stringValue(result, "studentAnswer", ""));
            ps.setString(8, stringValue(result, "evaluation", "needs_work"));
            ps.setInt(9, "correct".equals(stringValue(result, "evaluation", "")) ? 1 : 0);
            ps.setInt(10, boolValue(result, "evaluatorCodeAccepted") ? 1 : 0);
            ps.setString(11, stringValue(result, "notes", ""));
            ps.setLong(12, longValue(result, "responseTimeMs", 0));
            ps.setString(13, isoTimestamp);
            ps.executeUpdate();
        }
    }
    private static String stringValue(JsonObject obj, String key, String fallback) {
        return obj.has(key) && !obj.get(key).isJsonNull() ? obj.get(key).getAsString() : fallback;
    }
    private static int intValue(JsonObject obj, String key, int fallback) {
        return obj.has(key) && !obj.get(key).isJsonNull() ? obj.get(key).getAsInt() : fallback;
    }
    private static long longValue(JsonObject obj, String key, long fallback) {
        return obj.has(key) && !obj.get(key).isJsonNull() ? obj.get(key).getAsLong() : fallback;
    }
    private static boolean boolValue(JsonObject obj, String key) {
        return obj.has(key) && !obj.get(key).isJsonNull() && obj.get(key).getAsBoolean();
    }
    private static String sanitizeUsername(String username) {
        return usernameOrUnknown(username).replaceAll("[^a-zA-Z0-9_-]", "_");
    }
    private static String usernameOrUnknown(String username) {
        if (username == null || username.isBlank()) return "unknown";
        return username;
    }
    private static void moveAtomically(Path source, Path target) throws IOException {
        try {
            Files.move(source, target, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
        } catch (AtomicMoveNotSupportedException e) {
            Files.move(source, target, StandardCopyOption.REPLACE_EXISTING);
        }
    }
}
