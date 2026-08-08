package com.kidgames.mathquest.persistence;

import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.quiz.QuizManager;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Stream;

/**
 * Loads per-learner problem lists from the math-quiz SQLite store.
 *
 * Mirrors math-quiz tools/anchor_store.py pick_latest(): choose the learner's most
 * recently modified math-flu SQLite file. The internal queue uses the lowest
 * ProblemLists.list_order, matching tools/problem_list_store.py next_problem_list().
 */
public class MathQuizProblemListLoader {
    public static final String DEFAULT_TLKIDS_DIR = "~/Documents/Code/fof-mono/apps/math-quiz/_data/tlkids";
    private static final Map<String, String> PLAYER_TO_REAL_NAME = playerMap();
    private static final Map<String, LoadedProblemList> ACTIVE_LISTS = new ConcurrentHashMap<>();
    private static final Pattern FILENAME_RE = Pattern.compile("^math-flu_(.+)_(\\d{4}-\\d{2}-\\d{2})(?:_(\\d{6}|\\d+|[A-Za-z0-9-]+))?\\.sqlite$");
    private static final Pattern PROBLEM_RE = Pattern.compile("\\s*(-?\\d+)\\s*([+\\-*/xX×÷−])\\s*(-?\\d+)\\s*");
    public record LoadedProblemList(
        Path sourceFile,
        long problemListId,
        int listOrder,
        String minecraftPlayerName,
        String realName,
        String listName,
        boolean retain,
        List<QuizManager.Problem> problems
    ) {}
    public record LoadedQuickQuiz(
        Path sourceFile,
        String minecraftPlayerName,
        String realName,
        String operation,
        List<QuizManager.Problem> problems
    ) {}
    public record ConsumeResult(
        long problemListId,
        String listName,
        String action,
        int timesUsed
    ) {}
    public static Optional<LoadedProblemList> loadForMinecraftPlayer(String minecraftPlayerName) {
        return loadForMinecraftPlayer(minecraftPlayerName, defaultTlkidsDir());
    }
    public static Optional<LoadedProblemList> loadForMinecraftPlayer(String minecraftPlayerName, Path folder) {
        return loadForMinecraftPlayer(minecraftPlayerName, folder, PLAYER_TO_REAL_NAME);
    }
    public static Optional<LoadedProblemList> loadForMinecraftPlayer(String minecraftPlayerName, Map<String, String> playerRealNames) {
        return loadForMinecraftPlayer(minecraftPlayerName, defaultTlkidsDir(), playerRealNames);
    }
    public static Optional<LoadedProblemList> loadForMinecraftPlayer(String minecraftPlayerName, Path folder, Map<String, String> playerRealNames) {
        String realName = realNameForMinecraftPlayer(minecraftPlayerName, playerRealNames).orElse(null);
        if (realName == null) return Optional.empty();
        Optional<Path> dbPath = latestDbForRealName(folder, realName);
        if (dbPath.isEmpty()) return Optional.empty();
        try {
            return loadNewestProblemList(dbPath.get(), minecraftPlayerName, realName);
        } catch (SQLException e) {
            System.err.println("[MathQuest] Failed to load math-quiz problem list from " + dbPath.get() + ": " + e.getMessage());
            return Optional.empty();
        }
    }
    public static Optional<LoadedQuickQuiz> loadQuickQuizForMinecraftPlayer(String minecraftPlayerName, String operation, Map<String, String> playerRealNames) {
        return loadQuickQuizForMinecraftPlayer(minecraftPlayerName, operation, defaultTlkidsDir(), playerRealNames);
    }
    public static Optional<LoadedQuickQuiz> loadQuickQuizForMinecraftPlayer(String minecraftPlayerName, String operation, Path folder, Map<String, String> playerRealNames) {
        String realName = realNameForMinecraftPlayer(minecraftPlayerName, playerRealNames).orElse(null);
        if (realName == null) return Optional.empty();
        Optional<Path> dbPath = latestDbForRealName(folder, realName);
        if (dbPath.isEmpty()) return Optional.empty();
        try {
            return loadQuickQuiz(dbPath.get(), minecraftPlayerName, realName, operation);
        } catch (SQLException e) {
            System.err.println("[MathQuest] Failed to load math-quiz quick quiz from " + dbPath.get() + ": " + e.getMessage());
            return Optional.empty();
        }
    }
    public static Optional<String> realNameForMinecraftPlayer(String minecraftPlayerName) {
        return realNameForMinecraftPlayer(minecraftPlayerName, PLAYER_TO_REAL_NAME);
    }
    public static Optional<String> realNameForMinecraftPlayer(String minecraftPlayerName, Map<String, String> playerRealNames) {
        if (minecraftPlayerName == null || minecraftPlayerName.isBlank()) return Optional.empty();
        Map<String, String> source = playerRealNames == null ? PLAYER_TO_REAL_NAME : playerRealNames;
        String realName = source.get(minecraftPlayerName.toLowerCase(Locale.ROOT));
        if (realName == null || realName.isBlank()) return Optional.empty();
        return Optional.of(realName.trim());
    }
    public static Map<String, String> minecraftToRealNameMap() {
        return Collections.unmodifiableMap(PLAYER_TO_REAL_NAME);
    }
    public static Map<String, String> controlPanelPlayers() {
        return Collections.unmodifiableMap(PLAYER_TO_REAL_NAME);
    }
    public static void rememberActiveProblemList(String minecraftPlayerName, LoadedProblemList list) {
        if (minecraftPlayerName == null || minecraftPlayerName.isBlank() || list == null) return;
        ACTIVE_LISTS.put(minecraftPlayerName.toLowerCase(Locale.ROOT), list);
    }
    public static void clearActiveProblemList(String minecraftPlayerName) {
        if (minecraftPlayerName == null || minecraftPlayerName.isBlank()) return;
        ACTIVE_LISTS.remove(minecraftPlayerName.toLowerCase(Locale.ROOT));
    }
    public static Optional<ConsumeResult> consumeActiveProblemList(String minecraftPlayerName) {
        if (minecraftPlayerName == null || minecraftPlayerName.isBlank()) return Optional.empty();
        LoadedProblemList list = ACTIVE_LISTS.remove(minecraftPlayerName.toLowerCase(Locale.ROOT));
        if (list == null) return Optional.empty();
        try {
            return Optional.of(consumeProblemList(list));
        } catch (SQLException e) {
            System.err.println("[MathQuest] Failed to consume math-quiz problem list " + list.problemListId()
                + " from " + list.sourceFile() + ": " + e.getMessage());
            return Optional.empty();
        }
    }
    static Path defaultTlkidsDir() {
        return expandHome(DEFAULT_TLKIDS_DIR);
    }
    static Optional<Path> latestDbForRealName(Path folder, String realName) {
        if (folder == null || realName == null || !Files.isDirectory(folder)) return Optional.empty();
        try (Stream<Path> stream = Files.list(folder)) {
            return stream
                .filter(Files::isRegularFile)
                .filter(p -> filenameParts(p)
                    .map(parts -> parts.realName().equals(realName))
                    .orElse(false))
                .max(Comparator
                    .comparingLong(MathQuizProblemListLoader::modifiedMillis)
                    .thenComparing(p -> filenameParts(p).map(FilenameParts::date).orElse(""))
                    .thenComparing(p -> filenameParts(p).map(FilenameParts::timeForSort).orElse("")));
        } catch (IOException e) {
            System.err.println("[MathQuest] Failed to scan math-quiz folder " + folder + ": " + e.getMessage());
            return Optional.empty();
        }
    }
    private static Optional<LoadedProblemList> loadNewestProblemList(Path dbPath, String minecraftPlayerName, String realName) throws SQLException {
        try (Connection conn = DriverManager.getConnection("jdbc:sqlite:" + dbPath.toAbsolutePath())) {
            if (!hasTable(conn, "ProblemLists") || !hasTable(conn, "ProblemListItems")) {
                return Optional.empty();
            }
            boolean hasRetain = hasColumn(conn, "ProblemLists", "retain");
            long listId;
            int listOrder;
            String listName;
            boolean retain;
            String sql = hasRetain ? """
                SELECT problem_list_id, list_order, list_name, retain
                FROM ProblemLists
                WHERE user_name = ?
                ORDER BY list_order, problem_list_id
                LIMIT 1
                """ : """
                SELECT problem_list_id, list_order, list_name
                FROM ProblemLists
                WHERE user_name = ?
                ORDER BY list_order, problem_list_id
                LIMIT 1
                """;
            try (PreparedStatement ps = conn.prepareStatement(sql)) {
                ps.setString(1, realName);
                try (ResultSet rs = ps.executeQuery()) {
                    if (!rs.next()) return Optional.empty();
                    listId = rs.getLong("problem_list_id");
                    listOrder = rs.getInt("list_order");
                    listName = rs.getString("list_name");
                    retain = !hasRetain || rs.getInt("retain") != 0;
                }
            }
            List<QuizManager.Problem> problems = new ArrayList<>();
            try (PreparedStatement ps = conn.prepareStatement("""
                SELECT problem_text, num1, operation, num2
                FROM ProblemListItems
                WHERE problem_list_id = ?
                ORDER BY item_order, problem_list_item_id
                """)) {
                ps.setLong(1, listId);
                try (ResultSet rs = ps.executeQuery()) {
                    while (rs.next()) {
                        QuizManager.Problem problem = problemFromRow(rs);
                        if (problem != null) {
                            problems.add(problem);
                        }
                    }
                }
            }
            if (problems.isEmpty()) return Optional.empty();
            return Optional.of(new LoadedProblemList(
                dbPath, listId, listOrder, minecraftPlayerName, realName, listName, retain, List.copyOf(problems)
            ));
        }
    }
    private static Optional<LoadedQuickQuiz> loadQuickQuiz(Path dbPath, String minecraftPlayerName, String realName, String operation) throws SQLException {
        String op = quickPracticeOperationSymbol(operation);
        if (op == null) return Optional.empty();
        try (Connection conn = DriverManager.getConnection("jdbc:sqlite:" + dbPath.toAbsolutePath())) {
            if (!hasTable(conn, "QuickPracticeItems")) {
                return Optional.empty();
            }
            List<QuizManager.Problem> problems = new ArrayList<>();
            try (PreparedStatement ps = conn.prepareStatement("""
                SELECT problem_text, num1, operation, num2
                FROM QuickPracticeItems
                WHERE user_name = ? AND operation = ?
                ORDER BY item_order
                """)) {
                ps.setString(1, realName);
                ps.setString(2, op);
                try (ResultSet rs = ps.executeQuery()) {
                    while (rs.next()) {
                        QuizManager.Problem problem = problemFromRow(rs);
                        if (problem != null) {
                            problems.add(problem);
                        }
                    }
                }
            }
            if (problems.isEmpty()) return Optional.empty();
            return Optional.of(new LoadedQuickQuiz(
                dbPath, minecraftPlayerName, realName, MathQuestConfig.normalizeOperation(operation), List.copyOf(problems)
            ));
        }
    }
    private static ConsumeResult consumeProblemList(LoadedProblemList list) throws SQLException {
        try (Connection conn = DriverManager.getConnection("jdbc:sqlite:" + list.sourceFile().toAbsolutePath())) {
            ensureConsumeColumns(conn);
            long id = list.problemListId();
            try (PreparedStatement ps = conn.prepareStatement("""
                SELECT problem_list_id, list_name, retain, times_used
                FROM ProblemLists
                WHERE problem_list_id = ?
                """)) {
                ps.setLong(1, id);
                try (ResultSet rs = ps.executeQuery()) {
                    if (!rs.next()) return new ConsumeResult(id, list.listName(), "missing", 0);
                    String listName = rs.getString("list_name");
                    boolean retain = rs.getInt("retain") != 0;
                    int timesUsed = rs.getInt("times_used");
                    if (retain) {
                        int nextTimesUsed = timesUsed + 1;
                        try (PreparedStatement update = conn.prepareStatement("""
                            UPDATE ProblemLists
                            SET times_used = ?, last_used_at = ?
                            WHERE problem_list_id = ?
                            """)) {
                            update.setInt(1, nextTimesUsed);
                            update.setString(2, LocalDateTime.now().toString());
                            update.setLong(3, id);
                            update.executeUpdate();
                        }
                        return new ConsumeResult(id, listName, "retained", nextTimesUsed);
                    }
                    try (PreparedStatement deleteItems = conn.prepareStatement("DELETE FROM ProblemListItems WHERE problem_list_id = ?")) {
                        deleteItems.setLong(1, id);
                        deleteItems.executeUpdate();
                    }
                    try (PreparedStatement deleteList = conn.prepareStatement("DELETE FROM ProblemLists WHERE problem_list_id = ?")) {
                        deleteList.setLong(1, id);
                        deleteList.executeUpdate();
                    }
                    reindexProblemLists(conn, list.realName());
                    return new ConsumeResult(id, listName, "deleted", timesUsed);
                }
            }
        }
    }
    private static QuizManager.Problem problemFromRow(ResultSet rs) throws SQLException {
        Integer num1 = nullableInt(rs, "num1");
        Integer num2 = nullableInt(rs, "num2");
        String op = rs.getString("operation");
        if (num1 != null && num2 != null && op != null && !op.isBlank()) {
            return QuizManager.Problem.create(op, num1, num2);
        }
        String text = rs.getString("problem_text");
        if (text == null || text.isBlank()) return null;
        Matcher m = PROBLEM_RE.matcher(text);
        if (!m.matches()) return null;
        return QuizManager.Problem.create(m.group(2), Integer.parseInt(m.group(1)), Integer.parseInt(m.group(3)));
    }
    private static String quickPracticeOperationSymbol(String operation) {
        return switch (MathQuestConfig.normalizeOperation(operation)) {
            case "addition" -> "+";
            case "subtraction" -> "-";
            case "multiplication" -> "*";
            default -> null;
        };
    }
    private static Integer nullableInt(ResultSet rs, String column) throws SQLException {
        int value = rs.getInt(column);
        return rs.wasNull() ? null : value;
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
    private static boolean hasColumn(Connection conn, String table, String column) throws SQLException {
        try (PreparedStatement ps = conn.prepareStatement("PRAGMA table_info(" + table + ")");
             ResultSet rs = ps.executeQuery()) {
            while (rs.next()) {
                if (column.equalsIgnoreCase(rs.getString("name"))) return true;
            }
        }
        return false;
    }
    private static void ensureConsumeColumns(Connection conn) throws SQLException {
        try (Statement stmt = conn.createStatement()) {
            if (!hasColumn(conn, "ProblemLists", "retain")) {
                stmt.executeUpdate("ALTER TABLE ProblemLists ADD COLUMN retain INTEGER NOT NULL DEFAULT 1");
            }
            if (!hasColumn(conn, "ProblemLists", "times_used")) {
                stmt.executeUpdate("ALTER TABLE ProblemLists ADD COLUMN times_used INTEGER NOT NULL DEFAULT 0");
            }
            if (!hasColumn(conn, "ProblemLists", "last_used_at")) {
                stmt.executeUpdate("ALTER TABLE ProblemLists ADD COLUMN last_used_at TEXT");
            }
        }
    }
    private static void reindexProblemLists(Connection conn, String realName) throws SQLException {
        List<Long> ids = new ArrayList<>();
        try (PreparedStatement ps = conn.prepareStatement("""
            SELECT problem_list_id
            FROM ProblemLists
            WHERE user_name = ?
            ORDER BY list_order, problem_list_id
            """)) {
            ps.setString(1, realName);
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) ids.add(rs.getLong("problem_list_id"));
            }
        }
        try (PreparedStatement ps = conn.prepareStatement("UPDATE ProblemLists SET list_order = ? WHERE problem_list_id = ?")) {
            for (int i = 0; i < ids.size(); i++) {
                ps.setInt(1, i + 1);
                ps.setLong(2, ids.get(i));
                ps.executeUpdate();
            }
        }
    }
    private static long modifiedMillis(Path path) {
        try {
            return Files.getLastModifiedTime(path).toMillis();
        } catch (IOException e) {
            return 0L;
        }
    }
    private static Optional<FilenameParts> filenameParts(Path path) {
        Matcher m = FILENAME_RE.matcher(path.getFileName().toString());
        if (!m.matches()) return Optional.empty();
        return Optional.of(new FilenameParts(m.group(1), m.group(2), m.group(3)));
    }
    private record FilenameParts(String realName, String date, String time) {
        String timeForSort() {
            return time == null ? "999999" : time;
        }
    }
    private static Path expandHome(String path) {
        if (path == null || path.isBlank()) return Path.of("");
        String out = path;
        if (out.startsWith("~")) {
            String home = System.getProperty("user.home");
            if (home != null && !home.isEmpty()) {
                out = home + out.substring(1);
            }
        }
        return Path.of(out);
    }
    private static Map<String, String> playerMap() {
        Map<String, String> out = new LinkedHashMap<>();
        out.put("rjcomp", "Randy");
        out.put("treasurehunterm", "K2");
        out.put("pumajockey", "TL");
        out.put("skulkscraper", "Guest");
        out.put("wildpetal", "Kid1");
        return Collections.unmodifiableMap(out);
    }
}
