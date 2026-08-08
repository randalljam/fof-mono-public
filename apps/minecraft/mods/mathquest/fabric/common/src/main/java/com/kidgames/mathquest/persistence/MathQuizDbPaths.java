package com.kidgames.mathquest.persistence;

import com.kidgames.mathquest.config.MathQuestConfig;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

/** Resolves and validates Math Quiz SQLite directory paths. */
public final class MathQuizDbPaths {
    public static final String SINGLE_DB_DIR_LABEL = "Single DB directory";
    public static final String ACTIVE_DB_DIR_LABEL = "Active DB directory";

    private MathQuizDbPaths() {}

    public static Path resolveSingleDbDir(MathQuestConfig config) {
        return config == null ? MathQuestConfig.DEFAULT_MATH_QUIZ_SINGLE_DB_DIR_PATH
            : config.resolveMathQuizSingleDbDir();
    }

    public static Path resolveActiveDbDir(MathQuestConfig config) {
        return config == null ? MathQuestConfig.DEFAULT_MATH_QUIZ_ACTIVE_DB_DIR_PATH
            : config.resolveMathQuizActiveDbDir();
    }

    public static ProbeResult probeWritable(Path dir) {
        if (dir == null) {
            return ProbeResult.failure("path is null");
        }
        try {
            Files.createDirectories(dir);
            Path probe = Files.createTempFile(dir, ".mathquest_write_probe_", ".tmp");
            Files.writeString(probe, "ok");
            Files.deleteIfExists(probe);
            return ProbeResult.success(dir.toAbsolutePath().normalize());
        } catch (IOException e) {
            return ProbeResult.failure(dir.toAbsolutePath().normalize() + ": " + e.getMessage());
        }
    }

    public record ProbeResult(boolean ok, Path path, String error) {
        static ProbeResult success(Path path) {
            return new ProbeResult(true, path, null);
        }

        static ProbeResult failure(String error) {
            return new ProbeResult(false, null, error);
        }
    }
}
