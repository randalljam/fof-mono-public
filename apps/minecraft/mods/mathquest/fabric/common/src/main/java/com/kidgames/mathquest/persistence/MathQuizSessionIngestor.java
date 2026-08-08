package com.kidgames.mathquest.persistence;

import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.platform.MathQuestLog;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Invokes the shared Math Quiz Python ingest module for local active DB accumulation. */
public final class MathQuizSessionIngestor {
    private static final Duration TIMEOUT = Duration.ofSeconds(30);

    private MathQuizSessionIngestor() {}

    public static Path ingest(Path singleSessionPath, String realName) {
        return ingest(singleSessionPath, realName, SessionIngestHooks.NONE);
    }

    public static Path ingest(Path singleSessionPath, String realName, SessionIngestHooks hooks) {
        if (MathQuestConfig.INSTANCE == null || !MathQuestConfig.INSTANCE.mathQuizIngestEnabled) {
            return null;
        }
        SessionIngestHooks activeHooks = hooks == null ? SessionIngestHooks.NONE : hooks;
        MathQuestLog.LOGGER.info("[MathQuest] Math Quiz single-session SQLite written: {}", singleSessionPath);
        Path script = resolveScript();
        if (script == null) {
            MathQuestLog.LOGGER.warn("[MathQuest] Math Quiz session ingest skipped: session_ingest.py not found");
            return null;
        }
        MathQuestLog.LOGGER.info("[MathQuest] Math Quiz session ingest script: {}", script);
        Path activeDir = MathQuestConfig.INSTANCE.resolveMathQuizActiveDbDir();
        Path exactActiveFile = activeHooks.exactActiveFile(realName).orElse(null);
        Path archiveDir = MathQuestConfig.INSTANCE.resolveMathQuizSingleDbDir();
        List<String> command = new ArrayList<>();
        command.add(MathQuestConfig.INSTANCE.mathQuizIngestPython);
        command.add(script.toString());
        command.add("--single-session");
        command.add(singleSessionPath.toString());
        command.add("--user");
        command.add(realName);
        if (exactActiveFile != null) {
            command.add("--active-file");
            command.add(exactActiveFile.toString());
        } else {
            command.add("--active-dir");
            command.add(activeDir.toString());
        }
        command.add("--archive-dir");
        command.add(archiveDir.toString());
        command.add("--prefix");
        command.add("mathquest");
        if (exactActiveFile == null) {
            command.add("--match-any-prefix");
        }
        return run(command, activeDir, realName, activeHooks);
    }

    private static Path resolveScript() {
        String configured = System.getenv("MATHQUEST_SESSION_INGEST_SCRIPT");
        if (configured != null && !configured.isBlank()) {
            Path p = Path.of(expandHome(configured.trim())).normalize();
            if (Files.isRegularFile(p)) return p;
        }
        Path exportDir = MathQuestConfig.INSTANCE.resolveMathQuizSingleDbDir();
        Path activeDir = MathQuestConfig.INSTANCE.resolveMathQuizActiveDbDir();
        String home = System.getProperty("user.home");
        for (Path candidate : new Path[] {
            scriptFromDataDir(exportDir.getParent()),
            scriptFromDataDir(activeDir.getParent()),
            Path.of(home, "Documents/Code/fof-mono/apps/math-quiz/tools/session_ingest.py"),
            Path.of(home, "Documents/Code/feature-minecraft-mod-forge/apps/math-quiz/tools/session_ingest.py")
        }) {
            if (candidate != null && Files.isRegularFile(candidate)) return candidate.normalize();
        }
        return extractBundledScript();
    }

    private static Path extractBundledScript() {
        Path toolDir = MathQuestConfig.INSTANCE.resolveDataDir().resolve("mathquest_ingest_tools");
        try {
            Files.createDirectories(toolDir);
            copyResource("/mathquest-tools/anchor_store.py", toolDir.resolve("anchor_store.py"));
            Path script = toolDir.resolve("session_ingest.py");
            copyResource("/mathquest-tools/session_ingest.py", script);
            return Files.isRegularFile(script) ? script.normalize() : null;
        } catch (IOException e) {
            MathQuestLog.LOGGER.warn("[MathQuest] Math Quiz bundled ingest script extraction failed: {}", e.getMessage());
            return null;
        }
    }

    private static void copyResource(String resourceName, Path dest) throws IOException {
        try (InputStream in = MathQuizSessionIngestor.class.getResourceAsStream(resourceName)) {
            if (in == null) {
                throw new IOException("bundled resource missing: " + resourceName);
            }
            Files.copy(in, dest, StandardCopyOption.REPLACE_EXISTING);
        }
    }

    private static Path scriptFromDataDir(Path dataDir) {
        if (dataDir == null) return null;
        return dataDir.getParent() == null ? null : dataDir.getParent().resolve("tools/session_ingest.py");
    }

    private static String expandHome(String path) {
        if (path.startsWith("~")) {
            return System.getProperty("user.home") + path.substring(1);
        }
        return path;
    }

    private static Path run(List<String> command, Path activeDir, String realName, SessionIngestHooks hooks) {
        ProcessBuilder pb = new ProcessBuilder(command);
        pb.redirectErrorStream(true);
        try {
            Process process = pb.start();
            boolean finished = process.waitFor(TIMEOUT.toMillis(), TimeUnit.MILLISECONDS);
            if (!finished) {
                process.destroyForcibly();
                MathQuestLog.LOGGER.warn("[MathQuest] Math Quiz session ingest timed out");
                return null;
            }
            String output = readOutput(process);
            if (process.exitValue() == 0) {
                String activePath = jsonString(output, "path");
                String action = jsonString(output, "action");
                String added = jsonNumber(output, "added");
                if (activePath != null) {
                    MathQuestLog.LOGGER.info("[MathQuest] Math Quiz multi-session SQLite updated: {} (action={}, added={})",
                        activePath, action != null ? action : "unknown", added != null ? added : "unknown");
                    Path resolved = Path.of(activePath);
                    hooks.afterIngest(realName, resolved);
                    return resolved.toAbsolutePath().normalize();
                } else {
                    MathQuestLog.LOGGER.info("[MathQuest] Math Quiz session ingested into {}: {}", activeDir, output);
                }
            } else {
                MathQuestLog.LOGGER.warn("[MathQuest] Math Quiz session ingest failed with exit {}: {}",
                    process.exitValue(), output);
            }
        } catch (IOException e) {
            MathQuestLog.LOGGER.warn("[MathQuest] Math Quiz session ingest could not start: {}", e.getMessage());
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            MathQuestLog.LOGGER.warn("[MathQuest] Math Quiz session ingest interrupted");
        }
        return null;
    }

    private static String readOutput(Process process) throws IOException {
        StringBuilder out = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(
            new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                if (out.length() > 0) out.append(' ');
                out.append(line);
            }
        }
        return out.toString();
    }

    private static String jsonString(String json, String key) {
        Matcher m = Pattern.compile("\"" + Pattern.quote(key) + "\"\\s*:\\s*\"((?:\\\\.|[^\"])*)\"").matcher(json);
        if (!m.find()) return null;
        return m.group(1).replace("\\/", "/").replace("\\\"", "\"").replace("\\\\", "\\");
    }

    private static String jsonNumber(String json, String key) {
        Matcher m = Pattern.compile("\"" + Pattern.quote(key) + "\"\\s*:\\s*(-?\\d+)").matcher(json);
        return m.find() ? m.group(1) : null;
    }
}
