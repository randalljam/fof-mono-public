package com.kidgames.mathquest.persistence;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.platform.MathQuestLog;
import com.kidgames.mathquest.quiz.QuizManager;

import java.io.BufferedReader;
import java.io.File;
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
import java.util.Optional;
import java.util.concurrent.TimeUnit;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Invokes the shared math-quiz Node fluency bridge for list generation and % fluent. */
public final class FluencyFeastBridge {
    private static final Duration TIMEOUT = Duration.ofSeconds(30);
    private static final Pattern PROBLEM_RE = Pattern.compile("\\s*(-?\\d+)\\s*([+\\-*/xX×÷−])\\s*(-?\\d+)\\s*");

    private FluencyFeastBridge() {}

    public record GenerateResult(List<QuizManager.Problem> problems, List<String> warnings, int requestedCount) {}
    public record PercentResult(int percent) {}

    public static boolean isEnabled() {
        return MathQuestConfig.INSTANCE != null && MathQuestConfig.INSTANCE.fluencyFeastEnabled;
    }

    public static Optional<GenerateResult> generate(
        List<MathQuizFluencyLoader.AttemptRow> attempts,
        MathQuizFluencyLoader.FeastConfig feast,
        MathQuizFluencyLoader.ProfileThresholds thresholds
    ) {
        JsonObject req = new JsonObject();
        req.addProperty("command", "generate");
        req.add("attempts", MathQuizFluencyLoader.attemptsToJson(attempts).get("attempts"));
        req.add("feast", MathQuizFluencyLoader.feastConfigToJson(feast).get("feast"));
        req.add("thresholds", MathQuizFluencyLoader.thresholdsToJson(thresholds).get("thresholds"));
        req.add("numberRange", numberRangeJson());
        req.add("operations", operationsJson(feast));
        req.addProperty("excludeFlagged", true);
        JsonObject resp = runBridge(req);
        if (resp == null || !resp.has("ok") || !resp.get("ok").getAsBoolean()) return Optional.empty();
        List<QuizManager.Problem> problems = parseProblems(resp.getAsJsonArray("problems"));
        if (problems.isEmpty()) return Optional.empty();
        List<String> warnings = new ArrayList<>();
        if (resp.has("warnings") && resp.get("warnings").isJsonArray()) {
            for (JsonElement el : resp.getAsJsonArray("warnings")) {
                warnings.add(el.getAsString());
            }
        }
        return Optional.of(new GenerateResult(problems, warnings, feast.count()));
    }

    public static Optional<PercentResult> percent(
        List<MathQuizFluencyLoader.AttemptRow> attempts,
        MathQuizFluencyLoader.ProfileThresholds thresholds,
        MathQuizFluencyLoader.FeastConfig feast
    ) {
        JsonObject req = new JsonObject();
        req.addProperty("command", "percent");
        req.add("attempts", MathQuizFluencyLoader.attemptsToJson(attempts).get("attempts"));
        req.add("thresholds", MathQuizFluencyLoader.thresholdsToJson(thresholds).get("thresholds"));
        req.add("feast", MathQuizFluencyLoader.feastConfigToJson(feast).get("feast"));
        req.add("numberRange", numberRangeJson());
        req.add("operations", operationsJson(feast));
        req.addProperty("excludeFlagged", true);
        JsonObject resp = runBridge(req);
        if (resp == null || !resp.has("ok") || !resp.get("ok").getAsBoolean()) return Optional.empty();
        if (!resp.has("percent")) return Optional.empty();
        return Optional.of(new PercentResult(resp.get("percent").getAsInt()));
    }

    public static Optional<GenerateResult> generateForRealName(String realName, Path activeDir) {
        if (!isEnabled()) return Optional.empty();
        SqliteDriver.ensureLoaded();
        Optional<Path> db = MathQuizFluencyLoader.latestDbForRealName(activeDir, realName);
        if (db.isEmpty()) return Optional.empty();
        try {
            List<MathQuizFluencyLoader.AttemptRow> attempts = MathQuizFluencyLoader.loadAttempts(db.get(), realName);
            MathQuizFluencyLoader.FeastConfig feast = MathQuizFluencyLoader.loadFeastConfig(db.get(), realName);
            MathQuizFluencyLoader.ProfileThresholds thresholds = MathQuizFluencyLoader.loadProfileThresholds(db.get(), realName);
            return generate(attempts, feast, thresholds);
        } catch (Exception e) {
            MathQuestLog.LOGGER.warn("[MathQuest] Fluency feast generate failed for {}: {}", realName, e.getMessage());
            return Optional.empty();
        }
    }

    public static Optional<PercentResult> percentForRealName(String realName, Path activeDir) {
        if (!isEnabled()) return Optional.empty();
        SqliteDriver.ensureLoaded();
        Optional<Path> db = MathQuizFluencyLoader.latestDbForRealName(activeDir, realName);
        if (db.isEmpty()) return Optional.empty();
        try {
            List<MathQuizFluencyLoader.AttemptRow> attempts = MathQuizFluencyLoader.loadAttempts(db.get(), realName);
            MathQuizFluencyLoader.FeastConfig feast = MathQuizFluencyLoader.loadFeastConfig(db.get(), realName);
            MathQuizFluencyLoader.ProfileThresholds thresholds = MathQuizFluencyLoader.loadProfileThresholds(db.get(), realName);
            return percent(attempts, thresholds, feast);
        } catch (Exception e) {
            MathQuestLog.LOGGER.warn("[MathQuest] Fluency percent failed for {}: {}", realName, e.getMessage());
            return Optional.empty();
        }
    }

    /** Runs a minimal bridge call during server startup; logs ERROR when misconfigured. */
    public static boolean verifyAtStartup() {
        if (!isEnabled()) {
            MathQuestLog.LOGGER.info("[MathQuest] Fluency feast bridge check skipped (fluencyFeastEnabled=false)");
            return true;
        }
        Path script = resolveBridgeScript();
        String node = resolveNodeExecutable();
        if (script == null) {
            MathQuestLog.LOGGER.error(
                "[MathQuest] Fluency feast bridge FAILED at startup: fluency_feast_bridge.mjs not found. "
                    + "internal_fluency_feast will fall back to generated arithmetic until fixed.");
            return false;
        }
        JsonObject req = new JsonObject();
        req.addProperty("command", "percent");
        req.add("attempts", new JsonArray());
        req.add("thresholds", MathQuizFluencyLoader.thresholdsToJson(MathQuizFluencyLoader.defaultThresholds()).get("thresholds"));
        req.add("numberRange", numberRangeJson());
        req.add("operations", operationsJson(MathQuizFluencyLoader.defaultFeastConfig()));
        req.addProperty("excludeFlagged", true);
        JsonObject resp = runBridge(req);
        if (resp != null && resp.has("ok") && resp.get("ok").getAsBoolean() && resp.has("percent")) {
            MathQuestLog.LOGGER.info(
                "[MathQuest] Fluency feast bridge OK (node={}, script={}, smoke percent={})",
                node, script, resp.get("percent").getAsInt());
            return true;
        }
        String detail = resp != null && resp.has("error") ? resp.get("error").getAsString() : "no ok response";
        MathQuestLog.LOGGER.error(
            "[MathQuest] Fluency feast bridge FAILED at startup (node={}, script={}): {}. "
                + "internal_fluency_feast will not work until node and the bundled bridge script are fixed.",
            node, script, detail);
        return false;
    }

    private static JsonArray numberRangeJson() {
        JsonArray arr = new JsonArray();
        arr.add(0);
        arr.add(9);
        return arr;
    }
    private static JsonArray operationsJson(MathQuizFluencyLoader.FeastConfig feast) {
        JsonArray arr = new JsonArray();
        arr.add(MathQuizFluencyLoader.operationToSymbol(feast.operation()));
        return arr;
    }
    private static List<QuizManager.Problem> parseProblems(JsonArray arr) {
        List<QuizManager.Problem> out = new ArrayList<>();
        if (arr == null) return out;
        for (JsonElement el : arr) {
            String text = el.getAsString();
            Matcher m = PROBLEM_RE.matcher(text);
            if (!m.matches()) continue;
            out.add(QuizManager.Problem.create(m.group(2), Integer.parseInt(m.group(1)), Integer.parseInt(m.group(3))));
        }
        return out;
    }
    private static JsonObject runBridge(JsonObject request) {
        Path script = resolveBridgeScriptForTest(request);
        if (script == null) {
            if (MathQuestConfig.INSTANCE != null) {
                MathQuestLog.LOGGER.warn("[MathQuest] Fluency feast bridge skipped: fluency_feast_bridge.mjs not found");
            }
            return null;
        }
        Path scriptDir = script.getParent();
        request.addProperty("scriptDir", scriptDir.toString());
        List<String> command = new ArrayList<>();
        command.add(resolveNodeExecutable(request));
        command.add(script.toString());
        ProcessBuilder pb = new ProcessBuilder(command);
        pb.redirectErrorStream(false);
        try {
            Process process = pb.start();
            try (var writer = process.getOutputStream()) {
                writer.write(request.toString().getBytes(StandardCharsets.UTF_8));
                writer.flush();
            }
            boolean finished = process.waitFor(TIMEOUT.toMillis(), TimeUnit.MILLISECONDS);
            if (!finished) {
                process.destroyForcibly();
                MathQuestLog.LOGGER.warn("[MathQuest] Fluency feast bridge timed out");
                return null;
            }
            String stdout = readStream(process.getInputStream());
            String stderr = readStream(process.getErrorStream());
            JsonObject resp = parseBridgeResponse(stdout);
            if (resp == null) {
                logBridgeWarn("Fluency feast bridge returned unparsable output (exit {}): stdout={} stderr={}",
                    process.exitValue(), stdout, stderr);
                return null;
            }
            if (process.exitValue() != 0 && (!resp.has("ok") || !resp.get("ok").getAsBoolean())) {
                logBridgeWarn("Fluency feast bridge exit {}: stdout={} stderr={}",
                    process.exitValue(), stdout, stderr);
            }
            return resp;
        } catch (Exception e) {
            logBridgeWarn("Fluency feast bridge failed: {}", e.getMessage());
            return null;
        }
    }

    static JsonObject parseBridgeResponse(String output) {
        String json = extractJsonPayload(output);
        if (json.isBlank()) return null;
        try {
            return JsonParser.parseString(json).getAsJsonObject();
        } catch (Exception e) {
            return null;
        }
    }

    static String extractJsonPayload(String output) {
        if (output == null || output.isBlank()) return "";
        String[] lines = output.split("\\R");
        for (int i = lines.length - 1; i >= 0; i--) {
            String line = lines[i].trim();
            if (line.startsWith("{")) return line;
        }
        int start = output.indexOf('{');
        if (start < 0) return output.trim();
        return extractBalancedJson(output, start);
    }

    private static String extractBalancedJson(String text, int start) {
        int depth = 0;
        for (int i = start; i < text.length(); i++) {
            char c = text.charAt(i);
            if (c == '{') depth++;
            else if (c == '}') {
                depth--;
                if (depth == 0) return text.substring(start, i + 1);
            }
        }
        return text.substring(start).trim();
    }
    private static Path resolveBridgeScriptForTest(JsonObject request) {
        if (request.has("bridgeScript")) {
            Path configured = Path.of(request.get("bridgeScript").getAsString());
            if (Files.isRegularFile(configured)) return configured.normalize();
        }
        return resolveBridgeScript();
    }
    private static void logBridgeWarn(String format, Object... args) {
        if (MathQuestConfig.INSTANCE != null) {
            MathQuestLog.LOGGER.warn(format, args);
        }
    }
    private static String resolveNodeExecutable(JsonObject request) {
        if (request.has("nodeExecutable")) {
            String configured = request.get("nodeExecutable").getAsString();
            if (configured != null && !configured.isBlank()) return configured.trim();
        }
        return resolveNodeExecutable();
    }
    private static String resolveNodeExecutable() {
        String env = System.getenv("MATHQUEST_NODE_EXECUTABLE");
        if (env != null && !env.isBlank()) return env.trim();
        String configured = "node";
        if (MathQuestConfig.INSTANCE != null && MathQuestConfig.INSTANCE.mathQuizNodeExecutable != null
            && !MathQuestConfig.INSTANCE.mathQuizNodeExecutable.isBlank()) {
            configured = MathQuestConfig.INSTANCE.mathQuizNodeExecutable.trim();
        }
        Path resolved = resolveExecutableOnPath(configured);
        if (resolved != null) return resolved.toString();
        return configured;
    }

    /**
     * Finds an executable on PATH or common install locations. Prism/GUI launches often
     * inherit a minimal PATH without {@code /usr/local/bin} or Homebrew.
     */
    static Path resolveExecutableOnPath(String name) {
        if (name == null || name.isBlank()) return null;
        String trimmed = name.trim();
        Path direct = Path.of(trimmed);
        if (direct.isAbsolute() && Files.isExecutable(direct)) return direct.normalize();
        if (Files.isExecutable(direct)) return direct.toAbsolutePath().normalize();
        for (String dir : executableSearchDirs()) {
            if (dir == null || dir.isBlank()) continue;
            Path candidate = Path.of(dir, trimmed);
            if (Files.isExecutable(candidate)) return candidate.normalize();
        }
        return null;
    }

    private static List<String> executableSearchDirs() {
        List<String> dirs = new ArrayList<>();
        String pathEnv = System.getenv("PATH");
        if (pathEnv != null && !pathEnv.isBlank()) {
            for (String part : pathEnv.split(File.pathSeparator)) {
                if (part != null && !part.isBlank()) dirs.add(part.trim());
            }
        }
        String home = System.getProperty("user.home");
        dirs.add("/usr/local/bin");
        dirs.add("/opt/homebrew/bin");
        if (home != null && !home.isBlank()) {
            dirs.add(home + "/.nvm/current/bin");
            dirs.add(home + "/.volta/bin");
        }
        return dirs;
    }

    private static Path resolveBridgeScript() {
        if (MathQuestConfig.INSTANCE == null) {
            for (Path checkout : checkoutBridgeScriptCandidates()) {
                if (Files.isRegularFile(checkout)) return checkout.normalize();
            }
            return null;
        }
        String configured = System.getenv("MATHQUEST_FLUENCY_BRIDGE_SCRIPT");
        if (configured != null && !configured.isBlank()) {
            Path p = Path.of(expandHome(configured.trim())).normalize();
            if (Files.isRegularFile(p)) return p;
        }
        Path exportDir = MathQuestConfig.INSTANCE.resolveMathQuizExportDir();
        Path activeDir = MathQuestConfig.INSTANCE.resolveMathQuizActiveDir();
        for (Path candidate : new Path[] {
            scriptFromDataDir(exportDir.getParent()),
            scriptFromDataDir(activeDir.getParent())
        }) {
            if (candidate != null && Files.isRegularFile(candidate)) return candidate.normalize();
        }
        for (Path checkout : checkoutBridgeScriptCandidates()) {
            if (Files.isRegularFile(checkout)) return checkout.normalize();
        }
        return extractBundledTools();
    }

    private static Path[] checkoutBridgeScriptCandidates() {
        String home = System.getProperty("user.home");
        return new Path[] {
            Path.of(home, "Documents/Code/feature-minecraft-mod-forge/apps/math-quiz/tools/fluency_feast_bridge.mjs"),
            Path.of(home, "Documents/Code/fof-mono/apps/math-quiz/tools/fluency_feast_bridge.mjs")
        };
    }
    private static Path extractBundledTools() {
        Path toolDir = MathQuestConfig.INSTANCE.resolveDataDir().resolve("mathquest_ingest_tools");
        try {
            Files.createDirectories(toolDir);
            copyResource("/mathquest-tools/anchor_store.py", toolDir.resolve("anchor_store.py"));
            copyResource("/mathquest-tools/session_ingest.py", toolDir.resolve("session_ingest.py"));
            copyResource("/mathquest-tools/fluency_feast_bridge.mjs", toolDir.resolve("fluency_feast_bridge.mjs"));
            copyResource("/mathquest-tools/fluency_core.js", toolDir.resolve("fluency_core.js"));
            copyResource("/mathquest-tools/math_utils.js", toolDir.resolve("math_utils.js"));
            Path script = toolDir.resolve("fluency_feast_bridge.mjs");
            return Files.isRegularFile(script) ? script.normalize() : null;
        } catch (IOException e) {
            MathQuestLog.LOGGER.warn("[MathQuest] Fluency bundled tools extraction failed: {}", e.getMessage());
            return null;
        }
    }
    private static void copyResource(String resourceName, Path dest) throws IOException {
        try (InputStream in = FluencyFeastBridge.class.getResourceAsStream(resourceName)) {
            if (in == null) return;
            Files.copy(in, dest, StandardCopyOption.REPLACE_EXISTING);
        }
    }
    private static Path scriptFromDataDir(Path dataDir) {
        if (dataDir == null) return null;
        return dataDir.getParent() == null ? null : dataDir.getParent().resolve("tools/fluency_feast_bridge.mjs");
    }
    private static String expandHome(String path) {
        if (path.startsWith("~")) {
            return System.getProperty("user.home") + path.substring(1);
        }
        return path;
    }
    private static String readStream(InputStream stream) throws IOException {
        StringBuilder out = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(
            new InputStreamReader(stream, StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                if (out.length() > 0) out.append('\n');
                out.append(line);
            }
        }
        return out.toString();
    }
}
