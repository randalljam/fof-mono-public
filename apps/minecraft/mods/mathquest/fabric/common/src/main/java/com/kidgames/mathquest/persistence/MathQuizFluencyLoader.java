package com.kidgames.mathquest.persistence;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import com.google.gson.reflect.TypeToken;
import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.platform.MathQuestLog;

import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/** Reads learner attempts and fluency-feast / profile config from math-quiz SQLite files. */
public final class MathQuizFluencyLoader {
    private static final Gson GSON = new Gson();
    public static final int DEFAULT_COUNT = 20;
    public static final String DEFAULT_OPERATION = "addition";
    public static final String DEFAULT_SESSION_MODE = "all";
    public static final int DEFAULT_SESSION_N = 3;
    public static final int DEFAULT_GREEN_MS = 2000;
    public static final int DEFAULT_RED_MS = 4000;
    public static final int DEFAULT_WINDOW_SIZE = 5;
    public static final double DEFAULT_MIN_ACCURACY = 0.8;
    public record AttemptRow(
        String problemText,
        int isCorrect,
        int responseTimeMs,
        String flagsJson,
        String startTime,
        String sessionId,
        long attemptId
    ) {}
    public record FeastSessionConfig(String mode, int n, String since) {}
    public record FeastConfig(int count, String operation, FeastSessionConfig session, Map<String, Integer> mix) {}
    public record ProfileThresholds(int greenMs, int redMs, int windowSize, double minAccuracy) {}
    private MathQuizFluencyLoader() {}
    public static Optional<Path> latestDbForRealName(Path folder, String realName) {
        return MathQuizProblemListLoader.latestDbForRealName(folder, realName);
    }
    public static Optional<Path> latestDbForRealName(String realName) {
        return latestDbForRealName(MathQuizProblemListLoader.defaultTlkidsDir(), realName);
    }
    public static List<AttemptRow> loadAttempts(Path dbPath, String realName) throws SQLException {
        List<AttemptRow> out = new ArrayList<>();
        try (Connection conn = DriverManager.getConnection("jdbc:sqlite:" + dbPath.toAbsolutePath())) {
            if (!hasTable(conn, "ProblemAttempts") || !hasTable(conn, "Sessions")) return out;
            try (PreparedStatement ps = conn.prepareStatement("""
                SELECT pa.problem_text, pa.is_correct, pa.response_time_ms, pa.flags_json,
                       s.start_time, pa.session_id, pa.attempt_id
                FROM ProblemAttempts pa
                JOIN Sessions s ON s.session_id = pa.session_id
                WHERE s.user_name = ?
                ORDER BY s.start_time, pa.attempt_id
                """)) {
                ps.setString(1, realName);
                try (ResultSet rs = ps.executeQuery()) {
                    while (rs.next()) {
                        out.add(new AttemptRow(
                            rs.getString("problem_text"),
                            rs.getInt("is_correct"),
                            rs.getInt("response_time_ms"),
                            rs.getString("flags_json"),
                            rs.getString("start_time"),
                            rs.getString("session_id"),
                            rs.getLong("attempt_id")
                        ));
                    }
                }
            }
        }
        return out;
    }
    public static FeastConfig loadFeastConfig(Path dbPath, String realName) throws SQLException {
        Map<String, Integer> defaultMix = defaultMix();
        try (Connection conn = DriverManager.getConnection("jdbc:sqlite:" + dbPath.toAbsolutePath())) {
            if (!hasTable(conn, "FluencyFeastConfig")) {
                return defaultFeastConfig();
            }
            ensureFeastSchema(conn, dbPath);
            try (PreparedStatement ps = conn.prepareStatement(
                "SELECT num_problems, operation, session_mode, session_n, session_since, mix_json "
                    + "FROM FluencyFeastConfig WHERE user_name = ?")) {
                ps.setString(1, realName);
                try (ResultSet rs = ps.executeQuery()) {
                    if (!rs.next()) return defaultFeastConfig();
                    int count = clamp(rs.getInt("num_problems"), 1, 500, DEFAULT_COUNT);
                    String operationRaw = rs.getString("operation");
                    String operation = normalizeFeastOperation(operationRaw);
                    if (operationRaw == null || operationRaw.isBlank()) {
                        MathQuestLog.LOGGER.info(
                            "[MathQuest] FluencyFeastConfig for {} missing operation; using {}",
                            realName, DEFAULT_OPERATION);
                    }
                    String mode = normalizeSessionMode(rs.getString("session_mode"));
                    int n = clamp(rs.getInt("session_n"), 1, 99, DEFAULT_SESSION_N);
                    String since = rs.getString("session_since");
                    Map<String, Integer> mix = parseMixJson(rs.getString("mix_json"), defaultMix);
                    return new FeastConfig(count, operation, new FeastSessionConfig(mode, n, since), mix);
                }
            }
        }
    }
    public static ProfileThresholds loadProfileThresholds(Path dbPath, String realName) throws SQLException {
        try (Connection conn = DriverManager.getConnection("jdbc:sqlite:" + dbPath.toAbsolutePath())) {
            if (!hasTable(conn, "Profile")) {
                return defaultThresholds();
            }
            try (PreparedStatement ps = conn.prepareStatement(
                "SELECT green_ms, red_ms, window_size, min_accuracy FROM Profile WHERE user_name = ?")) {
                ps.setString(1, realName);
                try (ResultSet rs = ps.executeQuery()) {
                    if (!rs.next()) return defaultThresholds();
                    int green = rs.getObject("green_ms") == null ? DEFAULT_GREEN_MS : rs.getInt("green_ms");
                    int red = rs.getObject("red_ms") == null ? DEFAULT_RED_MS : rs.getInt("red_ms");
                    int window = rs.getObject("window_size") == null ? DEFAULT_WINDOW_SIZE : rs.getInt("window_size");
                    double accuracy = rs.getObject("min_accuracy") == null
                        ? DEFAULT_MIN_ACCURACY
                        : rs.getDouble("min_accuracy");
                    return new ProfileThresholds(
                        clamp(green, 100, 60000, DEFAULT_GREEN_MS),
                        clamp(red, 100, 60000, DEFAULT_RED_MS),
                        clamp(window, 1, 100, DEFAULT_WINDOW_SIZE),
                        clampAccuracy(accuracy, DEFAULT_MIN_ACCURACY)
                    );
                }
            }
        }
    }
    public static JsonObject attemptsToJson(List<AttemptRow> attempts) {
        com.google.gson.JsonArray arr = new com.google.gson.JsonArray();
        for (AttemptRow row : attempts) {
            JsonObject obj = new JsonObject();
            obj.addProperty("problem_text", row.problemText());
            obj.addProperty("is_correct", row.isCorrect());
            obj.addProperty("response_time_ms", row.responseTimeMs());
            if (row.flagsJson() != null) obj.addProperty("flags_json", row.flagsJson());
            if (row.startTime() != null) obj.addProperty("start_time", row.startTime());
            if (row.sessionId() != null) obj.addProperty("session_id", row.sessionId());
            obj.addProperty("attempt_id", row.attemptId());
            arr.add(obj);
        }
        JsonObject out = new JsonObject();
        out.add("attempts", arr);
        return out;
    }
    public static JsonObject feastConfigToJson(FeastConfig feast) {
        JsonObject out = new JsonObject();
        JsonObject feastObj = new JsonObject();
        feastObj.addProperty("count", feast.count());
        feastObj.addProperty("operation", feast.operation());
        JsonObject session = new JsonObject();
        session.addProperty("mode", feast.session().mode());
        session.addProperty("n", feast.session().n());
        if (feast.session().since() != null) session.addProperty("since", feast.session().since());
        feastObj.add("session", session);
        feastObj.add("mix", GSON.toJsonTree(feast.mix()));
        out.add("feast", feastObj);
        return out;
    }
    public static JsonObject thresholdsToJson(ProfileThresholds thresholds) {
        JsonObject out = new JsonObject();
        JsonObject th = new JsonObject();
        th.addProperty("greenMs", thresholds.greenMs());
        th.addProperty("redMs", thresholds.redMs());
        th.addProperty("windowSize", thresholds.windowSize());
        th.addProperty("minAccuracy", thresholds.minAccuracy());
        out.add("thresholds", th);
        return out;
    }
    public static FeastConfig defaultFeastConfig() {
        return new FeastConfig(
            DEFAULT_COUNT,
            DEFAULT_OPERATION,
            new FeastSessionConfig(DEFAULT_SESSION_MODE, DEFAULT_SESSION_N, null),
            defaultMix());
    }

    /** Maps normalized feast operation names to symbols the fluency bridge expects. */
    public static String operationToSymbol(String operation) {
        return switch (normalizeFeastOperation(operation)) {
            case "subtraction" -> "-";
            case "multiplication" -> "*";
            case "division" -> "/";
            case "exponentiation" -> "^";
            default -> "+";
        };
    }

    public static String normalizeFeastOperation(String raw) {
        if (raw == null || raw.isBlank()) return DEFAULT_OPERATION;
        return MathQuestConfig.normalizeOperation(raw);
    }
    public static ProfileThresholds defaultThresholds() {
        return new ProfileThresholds(DEFAULT_GREEN_MS, DEFAULT_RED_MS, DEFAULT_WINDOW_SIZE, DEFAULT_MIN_ACCURACY);
    }
    private static Map<String, Integer> defaultMix() {
        Map<String, Integer> mix = new LinkedHashMap<>();
        mix.put("fluent", 0);
        mix.put("almost", 10);
        mix.put("needs-practice", 10);
        mix.put("incorrect", 40);
        mix.put("missing", 40);
        return mix;
    }
    private static Map<String, Integer> parseMixJson(String json, Map<String, Integer> defaults) {
        Map<String, Integer> out = new LinkedHashMap<>(defaults);
        if (json == null || json.isBlank()) return out;
        try {
            Map<String, Double> parsed = GSON.fromJson(json, new TypeToken<Map<String, Double>>() {}.getType());
            if (parsed == null) return out;
            for (String key : out.keySet()) {
                if (parsed.containsKey(key)) {
                    out.put(key, clamp(parsed.get(key).intValue(), 0, 100, out.get(key)));
                }
            }
        } catch (Exception ignored) {}
        return out;
    }
    private static String normalizeSessionMode(String raw) {
        if (raw == null || raw.isBlank()) return DEFAULT_SESSION_MODE;
        String s = raw.trim();
        if ("recentN".equals(s) || "sinceDate".equals(s)) return s;
        return DEFAULT_SESSION_MODE;
    }
    private static int clamp(int value, int lo, int hi, int fallback) {
        if (value < lo || value > hi) return fallback;
        return value;
    }
    private static double clampAccuracy(double value, double fallback) {
        if (Double.isNaN(value) || value <= 0) return fallback;
        if (value > 1) value = value / 100.0;
        return Math.max(0.01, Math.min(1.0, value));
    }
    private static void ensureFeastSchema(Connection conn, Path dbPath) throws SQLException {
        if (!hasColumn(conn, "FluencyFeastConfig", "operation")) {
            try (Statement stmt = conn.createStatement()) {
                stmt.execute(
                    "ALTER TABLE FluencyFeastConfig ADD COLUMN operation TEXT NOT NULL DEFAULT 'addition'");
            }
            MathQuestLog.LOGGER.info(
                "[MathQuest] FluencyFeastConfig in {} missing operation column; added default addition",
                dbPath.getFileName());
        }
    }

    private static boolean hasColumn(Connection conn, String table, String column) throws SQLException {
        try (Statement stmt = conn.createStatement();
             ResultSet rs = stmt.executeQuery("PRAGMA table_info(" + table + ")")) {
            while (rs.next()) {
                if (column.equalsIgnoreCase(rs.getString("name"))) return true;
            }
        }
        return false;
    }

    private static boolean hasTable(Connection conn, String table) throws SQLException {
        try (PreparedStatement ps = conn.prepareStatement(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?")) {
            ps.setString(1, table);
            try (ResultSet rs = ps.executeQuery()) {
                return rs.next();
            }
        }
    }
}
