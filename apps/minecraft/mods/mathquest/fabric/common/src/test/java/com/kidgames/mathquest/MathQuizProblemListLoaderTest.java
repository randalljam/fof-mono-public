package com.kidgames.mathquest;

import com.kidgames.mathquest.persistence.MathQuizProblemListLoader;
import com.kidgames.mathquest.quiz.QuizManager;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.attribute.FileTime;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;

class MathQuizProblemListLoaderTest {
    @TempDir
    Path tempDir;
    @Test
    void mapsMinecraftNamesToRealNames() {
        assertEquals("Randy", MathQuizProblemListLoader.realNameForMinecraftPlayer("rjcomp").orElseThrow());
        assertEquals("K2", MathQuizProblemListLoader.realNameForMinecraftPlayer("TreasureHunterM").orElseThrow());
        assertEquals("TL", MathQuizProblemListLoader.realNameForMinecraftPlayer("PumaJockey").orElseThrow());
        assertEquals("Guest", MathQuizProblemListLoader.realNameForMinecraftPlayer("SkulkScraper").orElseThrow());
        assertEquals("Kid1", MathQuizProblemListLoader.realNameForMinecraftPlayer("WildPetal").orElseThrow());
        assertTrue(MathQuizProblemListLoader.realNameForMinecraftPlayer("SomeoneElse").isEmpty());
    }
    @Test
    void controlPanelPlayersIncludeGuestPlaceholder() {
        assertTrue(MathQuizProblemListLoader.controlPanelPlayers().containsKey("rjcomp"));
        assertTrue(MathQuizProblemListLoader.controlPanelPlayers().containsKey("treasurehunterm"));
        assertTrue(MathQuizProblemListLoader.controlPanelPlayers().containsKey("pumajockey"));
        assertTrue(MathQuizProblemListLoader.controlPanelPlayers().containsKey("wildpetal"));
        assertEquals("Guest", MathQuizProblemListLoader.controlPanelPlayers().get("skulkscraper"));
    }
    @Test
    void configuredRealNameMapOverridesDefaultLookup() {
        java.util.Map<String, String> map = new java.util.LinkedHashMap<>();
        map.put("treasurehunterm", "Maximum");
        assertEquals("Maximum", MathQuizProblemListLoader.realNameForMinecraftPlayer("TreasureHunterM", map).orElseThrow());
    }
    @Test
    void loadsNewestProblemListFromMostRecentlyModifiedLearnerDb() throws Exception {
        Path oldDb = tempDir.resolve("math-flu_K2_2026-06-19.sqlite");
        Path latestDb = tempDir.resolve("math-flu_K2_2026-06-20.sqlite");
        Path sameMtimeSingleDb = tempDir.resolve("math-flu_K2_2026-06-20_120000.sqlite");
        Path otherDb = tempDir.resolve("math-flu_K1_2026-06-20.sqlite");
        createDb(oldDb, "K2", "Old List", new String[][] {{"1", "1 + 1", "1", "+", "1"}});
        createDb(latestDb, "K2", "New List", new String[][] {
            {"1", "8 + 2", "8", "+", "2"},
            {"2", "9 * 7", "9", "*", "7"},
            {"3", "12 / 3", "12", "/", "3"}
        });
        createDb(sameMtimeSingleDb, "K2", "Single List", new String[][] {{"1", "4 + 4", "4", "+", "4"}});
        createDb(otherDb, "Kid1", "Kid1 List", new String[][] {{"1", "3 + 4", "3", "+", "4"}});
        Files.setLastModifiedTime(oldDb, FileTime.fromMillis(1000));
        Files.setLastModifiedTime(latestDb, FileTime.fromMillis(3000));
        Files.setLastModifiedTime(sameMtimeSingleDb, FileTime.fromMillis(3000));
        Files.setLastModifiedTime(otherDb, FileTime.fromMillis(4000));
        Optional<MathQuizProblemListLoader.LoadedProblemList> loaded =
            MathQuizProblemListLoader.loadForMinecraftPlayer("TreasureHunterM", tempDir);
        assertTrue(loaded.isPresent());
        assertEquals(latestDb, loaded.get().sourceFile());
        assertEquals("K2", loaded.get().realName());
        assertEquals("New List", loaded.get().listName());
        assertEquals(3, loaded.get().problems().size());
        QuizManager.Problem first = loaded.get().problems().get(0);
        assertEquals("addition", first.operation);
        assertEquals(8, first.factorA);
        assertEquals(2, first.factorB);
        assertEquals(10, first.correctAnswer);
        QuizManager.Problem division = loaded.get().problems().get(2);
        assertEquals("division", division.operation);
        assertEquals(4, division.correctAnswer);
    }
    @Test
    void fallsBackToProblemTextWhenOperandColumnsAreNull() throws Exception {
        Path db = tempDir.resolve("math-flu_K1_2026-06-20.sqlite");
        createDb(db, "Kid1", "Text List", new String[][] {{"1", "6 x 7", null, null, null}});
        Optional<MathQuizProblemListLoader.LoadedProblemList> loaded =
            MathQuizProblemListLoader.loadForMinecraftPlayer("WildPetal", tempDir);
        assertTrue(loaded.isPresent());
        QuizManager.Problem p = loaded.get().problems().get(0);
        assertEquals("multiplication", p.operation);
        assertEquals(42, p.correctAnswer);
    }
    @Test
    void loadsQuickPracticeItemsForSelectedOperation() throws Exception {
        Path db = tempDir.resolve("math-flu_K1_2026-06-20.sqlite");
        createQuickPracticeDb(db, "Kid1");
        Optional<MathQuizProblemListLoader.LoadedQuickQuiz> loaded =
            MathQuizProblemListLoader.loadQuickQuizForMinecraftPlayer(
                "WildPetal",
                "multiplication",
                tempDir,
                java.util.Map.of("wildpetal", "Kid1")
            );
        assertTrue(loaded.isPresent());
        assertEquals("Kid1", loaded.get().realName());
        assertEquals("multiplication", loaded.get().operation());
        assertEquals(2, loaded.get().problems().size());
        QuizManager.Problem first = loaded.get().problems().get(0);
        assertEquals("multiplication", first.operation);
        assertEquals(2, first.factorA);
        assertEquals(5, first.factorB);
        assertEquals(10, first.correctAnswer);
    }
    @Test
    void quickPracticeIgnoresUnsupportedOperations() throws Exception {
        Path db = tempDir.resolve("math-flu_K1_2026-06-20.sqlite");
        createQuickPracticeDb(db, "Kid1");
        Optional<MathQuizProblemListLoader.LoadedQuickQuiz> loaded =
            MathQuizProblemListLoader.loadQuickQuizForMinecraftPlayer(
                "WildPetal",
                "division",
                tempDir,
                java.util.Map.of("wildpetal", "Kid1")
            );
        assertTrue(loaded.isEmpty());
    }
    @Test
    void loadsLowestOrderedProblemListFromInternalQueue() throws Exception {
        Path db = tempDir.resolve("math-flu_K1_2026-06-20.sqlite");
        createQueuedDb(db);
        Optional<MathQuizProblemListLoader.LoadedProblemList> loaded =
            MathQuizProblemListLoader.loadForMinecraftPlayer("WildPetal", tempDir);
        assertTrue(loaded.isPresent());
        assertEquals("First Queue List", loaded.get().listName());
        assertEquals(1, loaded.get().listOrder());
        assertFalse(loaded.get().retain());
        assertEquals(3, loaded.get().problems().get(0).factorA);
    }
    @Test
    void consumeRetainedProblemListIncrementsUsage() throws Exception {
        Path db = tempDir.resolve("math-flu_K2_2026-06-20.sqlite");
        createDb(db, "K2", "Keep List", new String[][] {{"1", "8 + 2", "8", "+", "2"}});
        MathQuizProblemListLoader.LoadedProblemList loaded =
            MathQuizProblemListLoader.loadForMinecraftPlayer("TreasureHunterM", tempDir).orElseThrow();
        MathQuizProblemListLoader.rememberActiveProblemList("TreasureHunterM", loaded);
        MathQuizProblemListLoader.ConsumeResult consumed =
            MathQuizProblemListLoader.consumeActiveProblemList("TreasureHunterM").orElseThrow();
        assertEquals("retained", consumed.action());
        assertEquals(1, consumed.timesUsed());
        assertEquals("Keep List", MathQuizProblemListLoader.loadForMinecraftPlayer("TreasureHunterM", tempDir).orElseThrow().listName());
    }
    @Test
    void consumeDeleteProblemListRemovesItAndReindexesQueue() throws Exception {
        Path db = tempDir.resolve("math-flu_K1_2026-06-20.sqlite");
        createQueuedDb(db);
        MathQuizProblemListLoader.LoadedProblemList loaded =
            MathQuizProblemListLoader.loadForMinecraftPlayer("WildPetal", tempDir).orElseThrow();
        MathQuizProblemListLoader.rememberActiveProblemList("WildPetal", loaded);
        MathQuizProblemListLoader.ConsumeResult consumed =
            MathQuizProblemListLoader.consumeActiveProblemList("WildPetal").orElseThrow();
        assertEquals("deleted", consumed.action());
        MathQuizProblemListLoader.LoadedProblemList next =
            MathQuizProblemListLoader.loadForMinecraftPlayer("WildPetal", tempDir).orElseThrow();
        assertEquals("Second Queue List", next.listName());
        assertEquals(1, next.listOrder());
    }
    private void createDb(Path path, String user, String listName, String[][] rows) throws SQLException {
        try (Connection conn = DriverManager.getConnection("jdbc:sqlite:" + path.toAbsolutePath());
             Statement stmt = conn.createStatement()) {
            stmt.executeUpdate("CREATE TABLE Users (name TEXT PRIMARY KEY)");
            stmt.executeUpdate("""
                CREATE TABLE ProblemLists (
                    problem_list_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_name TEXT NOT NULL,
                    list_order INTEGER NOT NULL DEFAULT 0,
                    list_name TEXT NOT NULL,
                    added_at TEXT NOT NULL,
                    source TEXT,
                    retain INTEGER NOT NULL DEFAULT 1,
                    times_used INTEGER NOT NULL DEFAULT 0,
                    last_used_at TEXT
                )
                """);
            stmt.executeUpdate("""
                CREATE TABLE ProblemListItems (
                    problem_list_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    problem_list_id INTEGER NOT NULL,
                    item_order INTEGER NOT NULL,
                    problem_text TEXT NOT NULL,
                    num1 INTEGER NULL,
                    operation TEXT NULL,
                    num2 INTEGER NULL,
                    category TEXT,
                    notes TEXT
                )
                """);
            stmt.executeUpdate("INSERT INTO Users(name) VALUES ('" + user + "')");
            stmt.executeUpdate("INSERT INTO ProblemLists(user_name, list_order, list_name, added_at, source, retain) VALUES ('"
                + user + "', 1, '" + listName + "', '2026-06-20T12:00:00', 'test', 1)");
            for (String[] row : rows) {
                String num1 = row[2] == null ? "NULL" : row[2];
                String op = row[3] == null ? "NULL" : "'" + row[3] + "'";
                String num2 = row[4] == null ? "NULL" : row[4];
                stmt.executeUpdate("INSERT INTO ProblemListItems(problem_list_id, item_order, problem_text, num1, operation, num2) VALUES (1, "
                    + row[0] + ", '" + row[1] + "', " + num1 + ", " + op + ", " + num2 + ")");
            }
        }
    }
    private void createQueuedDb(Path path) throws SQLException {
        try (Connection conn = DriverManager.getConnection("jdbc:sqlite:" + path.toAbsolutePath());
             Statement stmt = conn.createStatement()) {
            stmt.executeUpdate("CREATE TABLE Users (name TEXT PRIMARY KEY)");
            stmt.executeUpdate("""
                CREATE TABLE ProblemLists (
                    problem_list_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_name TEXT NOT NULL,
                    list_order INTEGER NOT NULL DEFAULT 0,
                    list_name TEXT NOT NULL,
                    added_at TEXT NOT NULL,
                    source TEXT,
                    retain INTEGER NOT NULL DEFAULT 1,
                    times_used INTEGER NOT NULL DEFAULT 0,
                    last_used_at TEXT
                )
                """);
            stmt.executeUpdate("""
                CREATE TABLE ProblemListItems (
                    problem_list_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    problem_list_id INTEGER NOT NULL,
                    item_order INTEGER NOT NULL,
                    problem_text TEXT NOT NULL,
                    num1 INTEGER NULL,
                    operation TEXT NULL,
                    num2 INTEGER NULL,
                    category TEXT,
                    notes TEXT
                )
                """);
            stmt.executeUpdate("INSERT INTO Users(name) VALUES ('Kid1')");
            stmt.executeUpdate("INSERT INTO ProblemLists(user_name, list_order, list_name, added_at, source, retain) VALUES ('Kid1', 2, 'Second Queue List', '2026-06-20T12:00:00', 'test', 1)");
            stmt.executeUpdate("INSERT INTO ProblemLists(user_name, list_order, list_name, added_at, source, retain) VALUES ('Kid1', 1, 'First Queue List', '2026-06-20T12:00:00', 'test', 0)");
            stmt.executeUpdate("INSERT INTO ProblemListItems(problem_list_id, item_order, problem_text, num1, operation, num2) VALUES (1, 1, '9 + 1', 9, '+', 1)");
            stmt.executeUpdate("INSERT INTO ProblemListItems(problem_list_id, item_order, problem_text, num1, operation, num2) VALUES (2, 1, '3 + 4', 3, '+', 4)");
        }
    }
    private void createQuickPracticeDb(Path path, String user) throws SQLException {
        try (Connection conn = DriverManager.getConnection("jdbc:sqlite:" + path.toAbsolutePath());
             Statement stmt = conn.createStatement()) {
            stmt.executeUpdate("CREATE TABLE Users (name TEXT PRIMARY KEY)");
            stmt.executeUpdate("""
                CREATE TABLE QuickPracticeItems (
                    user_name TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    item_order INTEGER NOT NULL,
                    problem_text TEXT NOT NULL,
                    num1 INTEGER NOT NULL,
                    num2 INTEGER NOT NULL,
                    slot_status TEXT NOT NULL,
                    fact_status TEXT,
                    origin TEXT NOT NULL,
                    computed_at TEXT NOT NULL,
                    PRIMARY KEY (user_name, operation, item_order)
                )
                """);
            stmt.executeUpdate("INSERT INTO Users(name) VALUES ('" + user + "')");
            stmt.executeUpdate("INSERT INTO QuickPracticeItems(user_name, operation, item_order, problem_text, num1, num2, slot_status, origin, computed_at) VALUES ('"
                + user + "', '*', 1, '2 * 5', 2, 5, 'green', 'data', '2026-06-25_120000')");
            stmt.executeUpdate("INSERT INTO QuickPracticeItems(user_name, operation, item_order, problem_text, num1, num2, slot_status, origin, computed_at) VALUES ('"
                + user + "', '*', 2, '6 * 7', 6, 7, 'red', 'algorithm', '2026-06-25_120000')");
            stmt.executeUpdate("INSERT INTO QuickPracticeItems(user_name, operation, item_order, problem_text, num1, num2, slot_status, origin, computed_at) VALUES ('"
                + user + "', '+', 1, '1 + 2', 1, 2, 'green', 'algorithm', '2026-06-25_120000')");
        }
    }
}
