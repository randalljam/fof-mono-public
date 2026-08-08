package com.kidgames.mathquest;

import com.google.gson.JsonObject;
import com.kidgames.mathquest.persistence.WrittenColumnSessionExporter;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.Statement;

import static org.junit.jupiter.api.Assertions.*;

public class WrittenColumnSessionExporterTest {
    @TempDir
    Path tempDir;
    @Test
    void exportsWrittenColumnSchema() throws Exception {
        JsonObject result = new JsonObject();
        result.addProperty("operation", "addition");
        result.addProperty("factorA", 327);
        result.addProperty("factorB", 486);
        result.addProperty("correctAnswer", 813);
        result.addProperty("promptText", "Solve on paper: 327 + 486");
        result.addProperty("studentAnswer", "813");
        result.addProperty("evaluation", "correct");
        result.addProperty("evaluatorCodeAccepted", true);
        result.addProperty("notes", "Aligned columns cleanly.");
        result.addProperty("responseTimeMs", 120000);
        Path file = WrittenColumnSessionExporter.export(result, "WildPetal", null, tempDir);
        assertTrue(Files.exists(file));
        assertTrue(file.getFileName().toString().startsWith("mathquest_written_column_WildPetal_"));
        try (Connection conn = DriverManager.getConnection("jdbc:sqlite:" + file.toAbsolutePath());
             Statement stmt = conn.createStatement()) {
            ResultSet session = stmt.executeQuery("SELECT user_name, quiz_type FROM WrittenColumnSessions");
            assertTrue(session.next());
            assertEquals("WildPetal", session.getString("user_name"));
            assertEquals("written_column_arithmetic", session.getString("quiz_type"));
            ResultSet attempt = stmt.executeQuery("SELECT operation, student_answer_text, evaluation, is_correct, evaluator_notes FROM WrittenColumnAttempts");
            assertTrue(attempt.next());
            assertEquals("addition", attempt.getString("operation"));
            assertEquals("813", attempt.getString("student_answer_text"));
            assertEquals("correct", attempt.getString("evaluation"));
            assertEquals(1, attempt.getInt("is_correct"));
            assertEquals("Aligned columns cleanly.", attempt.getString("evaluator_notes"));
        }
    }
}
