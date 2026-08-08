package com.kidgames.mathquest;

import com.kidgames.mathquest.persistence.MathQuizFluencyLoader;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.Statement;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class MathQuizFluencyLoaderTest {
    @TempDir
    Path tempDir;

    @Test
    void loadAttemptsJoinsSessionsForUser() throws Exception {
        Path db = tempDir.resolve("math-flu_Randy_2026-06-20.sqlite");
        createLearnerDb(db, "Randy");
        List<MathQuizFluencyLoader.AttemptRow> attempts = MathQuizFluencyLoader.loadAttempts(db, "Randy");
        assertEquals(2, attempts.size());
        assertEquals("1 + 1", attempts.get(0).problemText());
        assertEquals(1, attempts.get(0).isCorrect());
        assertEquals(500, attempts.get(0).responseTimeMs());
        assertEquals("s1", attempts.get(0).sessionId());
    }

    @Test
    void loadFeastConfigUsesDefaultsWhenTableMissing() throws Exception {
        Path db = tempDir.resolve("math-flu_Randy_2026-06-20.sqlite");
        createLearnerDb(db, "Randy");
        MathQuizFluencyLoader.FeastConfig feast = MathQuizFluencyLoader.loadFeastConfig(db, "Randy");
        assertEquals(20, feast.count());
        assertEquals("addition", feast.operation());
        assertEquals("all", feast.session().mode());
        assertEquals(3, feast.session().n());
        assertEquals(0, feast.mix().get("fluent"));
        assertEquals(40, feast.mix().get("missing"));
    }

    @Test
    void loadFeastConfigReadsSavedRow() throws Exception {
        Path db = tempDir.resolve("math-flu_Randy_2026-06-20.sqlite");
        createLearnerDb(db, "Randy");
        try (Connection conn = DriverManager.getConnection("jdbc:sqlite:" + db)) {
            try (Statement stmt = conn.createStatement()) {
                stmt.execute("""
                    CREATE TABLE FluencyFeastConfig (
                        user_name TEXT PRIMARY KEY,
                        num_problems INTEGER NOT NULL DEFAULT 20,
                        operation TEXT NOT NULL DEFAULT 'addition',
                        session_mode TEXT NOT NULL DEFAULT 'all',
                        session_n INTEGER NOT NULL DEFAULT 3,
                        session_since TEXT,
                        mix_json TEXT NOT NULL DEFAULT '{}',
                        updated_at TEXT
                    )
                    """);
                stmt.execute("""
                    INSERT INTO FluencyFeastConfig (user_name, num_problems, operation, session_mode, session_n, mix_json)
                    VALUES ('Randy', 12, 'subtraction', 'recentN', 5, '{"fluent":5,"almost":5,"needs-practice":10,"incorrect":40,"missing":40}')
                    """);
            }
        }
        MathQuizFluencyLoader.FeastConfig feast = MathQuizFluencyLoader.loadFeastConfig(db, "Randy");
        assertEquals(12, feast.count());
        assertEquals("subtraction", feast.operation());
        assertEquals("recentN", feast.session().mode());
        assertEquals(5, feast.session().n());
        assertEquals(5, feast.mix().get("fluent"));
    }

    @Test
    void loadFeastConfigDefaultsOperationWhenColumnMissing() throws Exception {
        Path db = tempDir.resolve("math-flu_Randy_2026-06-20.sqlite");
        createLearnerDb(db, "Randy");
        try (Connection conn = DriverManager.getConnection("jdbc:sqlite:" + db)) {
            try (Statement stmt = conn.createStatement()) {
                stmt.execute("""
                    CREATE TABLE FluencyFeastConfig (
                        user_name TEXT PRIMARY KEY,
                        num_problems INTEGER NOT NULL DEFAULT 20,
                        session_mode TEXT NOT NULL DEFAULT 'all',
                        session_n INTEGER NOT NULL DEFAULT 3,
                        session_since TEXT,
                        mix_json TEXT NOT NULL DEFAULT '{}',
                        updated_at TEXT
                    )
                    """);
                stmt.execute("""
                    INSERT INTO FluencyFeastConfig (user_name, num_problems, session_mode, session_n, mix_json)
                    VALUES ('Randy', 15, 'all', 3, '{}')
                    """);
            }
        }
        MathQuizFluencyLoader.FeastConfig feast = MathQuizFluencyLoader.loadFeastConfig(db, "Randy");
        assertEquals(15, feast.count());
        assertEquals("addition", feast.operation());
        try (Connection conn = DriverManager.getConnection("jdbc:sqlite:" + db);
             Statement stmt = conn.createStatement();
             ResultSet rs = stmt.executeQuery("PRAGMA table_info(FluencyFeastConfig)")) {
            boolean hasOperation = false;
            while (rs.next()) {
                if ("operation".equalsIgnoreCase(rs.getString("name"))) hasOperation = true;
            }
            assertTrue(hasOperation);
        }
    }

    @Test
    void operationToSymbolMapsNormalizedNames() {
        assertEquals("+", MathQuizFluencyLoader.operationToSymbol("addition"));
        assertEquals("-", MathQuizFluencyLoader.operationToSymbol("subtraction"));
        assertEquals("*", MathQuizFluencyLoader.operationToSymbol("multiplication"));
    }

    @Test
    void loadProfileThresholdsUsesDefaultsWhenMissing() throws Exception {
        Path db = tempDir.resolve("math-flu_Randy_2026-06-20.sqlite");
        createLearnerDb(db, "Randy");
        MathQuizFluencyLoader.ProfileThresholds thresholds = MathQuizFluencyLoader.loadProfileThresholds(db, "Randy");
        assertEquals(2000, thresholds.greenMs());
        assertEquals(4000, thresholds.redMs());
        assertEquals(5, thresholds.windowSize());
        assertEquals(0.8, thresholds.minAccuracy(), 0.001);
    }

    @Test
    void loadProfileThresholdsReadsSavedRow() throws Exception {
        Path db = tempDir.resolve("math-flu_Randy_2026-06-20.sqlite");
        createLearnerDb(db, "Randy");
        try (Connection conn = DriverManager.getConnection("jdbc:sqlite:" + db)) {
            try (Statement stmt = conn.createStatement()) {
                stmt.execute("""
                    CREATE TABLE Profile (
                        user_name TEXT PRIMARY KEY,
                        show_fluency_percent INTEGER NOT NULL DEFAULT 1,
                        green_ms INTEGER,
                        red_ms INTEGER,
                        window_size INTEGER,
                        min_accuracy REAL,
                        updated_at TEXT
                    )
                    """);
                stmt.execute("""
                    INSERT INTO Profile (user_name, show_fluency_percent, green_ms, red_ms, window_size, min_accuracy)
                    VALUES ('Randy', 1, 1500, 3500, 7, 0.75)
                    """);
            }
        }
        MathQuizFluencyLoader.ProfileThresholds thresholds = MathQuizFluencyLoader.loadProfileThresholds(db, "Randy");
        assertEquals(1500, thresholds.greenMs());
        assertEquals(3500, thresholds.redMs());
        assertEquals(7, thresholds.windowSize());
        assertEquals(0.75, thresholds.minAccuracy(), 0.001);
    }

    private static void createLearnerDb(Path db, String realName) throws Exception {
        Files.createDirectories(db.getParent());
        try (Connection conn = DriverManager.getConnection("jdbc:sqlite:" + db)) {
            try (Statement stmt = conn.createStatement()) {
                stmt.execute("CREATE TABLE Users (name TEXT PRIMARY KEY)");
                stmt.execute("INSERT INTO Users (name) VALUES ('" + realName + "')");
                stmt.execute("""
                    CREATE TABLE Sessions (
                        session_id TEXT PRIMARY KEY,
                        user_name TEXT,
                        start_time TEXT
                    )
                    """);
                stmt.execute("""
                    CREATE TABLE ProblemAttempts (
                        attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT,
                        problem_text TEXT,
                        is_correct INTEGER,
                        response_time_ms INTEGER,
                        flags_json TEXT
                    )
                    """);
                stmt.execute("INSERT INTO Sessions VALUES ('s1', '" + realName + "', '2026-06-20_120000')");
                stmt.execute("INSERT INTO ProblemAttempts (session_id, problem_text, is_correct, response_time_ms) VALUES ('s1', '1 + 1', 1, 500)");
                stmt.execute("INSERT INTO ProblemAttempts (session_id, problem_text, is_correct, response_time_ms) VALUES ('s1', '2 + 2', 1, 800)");
            }
        }
    }
}
