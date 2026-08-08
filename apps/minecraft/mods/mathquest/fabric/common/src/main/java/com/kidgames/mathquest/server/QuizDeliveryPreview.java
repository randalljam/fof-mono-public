package com.kidgames.mathquest.server;

import com.google.gson.JsonArray;
import com.google.gson.JsonParser;
import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.net.OpenQuizData;
import com.kidgames.mathquest.persistence.MathQuizFluencyLoader;
import com.kidgames.mathquest.quiz.QuizManager;

import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/** Resolves the quiz a player would receive without issuing a completion session. */
public final class QuizDeliveryPreview {
    public record StatusLine(String label, String value, boolean error) {}

    public record Result(
        String playerName,
        String sourceLabel,
        int questionCount,
        String operation,
        String rangeLabel,
        boolean deliverable,
        String failureReason
    ) {
        /** e.g. {@code fluency feast, 20 questions, addition} */
        public String formatSummaryLine() {
            if (!deliverable) {
                return sourceLabel + " — generation failed (quiz will not open)";
            }
            return sourceLabel + ", " + questionCount + " question" + (questionCount == 1 ? "" : "s")
                + ", " + operation;
        }
    }

    private QuizDeliveryPreview() {}

    public static Result forPlayer(String playerName) {
        if (playerName == null || playerName.isBlank()) {
            return new Result("?", "unknown", 0, "?", "?", false, "no player name");
        }
        OpenQuizData data = OpenQuizPayloadBuilder.createPreview(playerName);
        return fromOpenQuizData(playerName, data);
    }

    public static List<StatusLine> statusLinesForPlayer(String playerName) {
        Result preview = forPlayer(playerName);
        java.util.ArrayList<StatusLine> lines = new java.util.ArrayList<>();
        lines.add(new StatusLine("Next quiz", preview.formatSummaryLine(), !preview.deliverable()));
        if (!preview.deliverable() && preview.failureReason() != null && !preview.failureReason().isBlank()) {
            lines.add(new StatusLine("Next quiz note", preview.failureReason(), true));
        }
        return lines;
    }

    public static Result fromOpenQuizData(String playerName, OpenQuizData data) {
        List<QuizManager.Problem> problems = parseProblems(data.problemsJson());
        String sourceLabel = resolveSourceLabel(playerName, data, problems);
        if (isFluencyFeast(playerName, data)) {
            MathQuizFluencyLoader.FeastConfig feast = feastConfigForPlayer(playerName);
            String operation = MathQuestConfig.normalizeOperation(feast.operation());
            int questionCount = feast.count();
            if (problems.isEmpty()) {
                return new Result(
                    playerName,
                    sourceLabel,
                    questionCount,
                    operation,
                    "0-9",
                    false,
                    "fluency feast generation failed (check node executable and latest.log)"
                );
            }
            return new Result(
                playerName,
                sourceLabel,
                questionCount,
                operation,
                rangeFromProblems(problems),
                true,
                null
            );
        }
        if (!problems.isEmpty()) {
            return new Result(
                playerName,
                sourceLabel,
                problems.size(),
                dominantOperation(problems),
                rangeFromProblems(problems),
                true,
                null
            );
        }
        return new Result(
            playerName,
            sourceLabel,
            data.problemsPerQuiz(),
            data.operation(),
            data.minNumber() + "-" + data.maxNumber(),
            true,
            null
        );
    }

    private static boolean isFluencyFeast(String playerName, OpenQuizData data) {
        if (data.fluencyFeastMode()) return true;
        return MathQuestConfig.INSTANCE != null
            && "internal_fluency_feast".equals(MathQuestConfig.INSTANCE.resolveInternalQuizSource(playerName));
    }

    private static MathQuizFluencyLoader.FeastConfig feastConfigForPlayer(String playerName) {
        if (MathQuestConfig.INSTANCE == null) {
            return MathQuizFluencyLoader.defaultFeastConfig();
        }
        try {
            String realName = MathQuestConfig.INSTANCE.resolveRealName(playerName);
            java.nio.file.Path activeDir = MathQuestConfig.INSTANCE.resolveMathQuizActiveDbDir();
            return MathQuizFluencyLoader.latestDbForRealName(activeDir, realName)
                .map(db -> {
                    try {
                        return MathQuizFluencyLoader.loadFeastConfig(db, realName);
                    } catch (java.sql.SQLException e) {
                        return MathQuizFluencyLoader.defaultFeastConfig();
                    }
                })
                .orElse(MathQuizFluencyLoader.defaultFeastConfig());
        } catch (Exception ignored) {
            return MathQuizFluencyLoader.defaultFeastConfig();
        }
    }

    private static String resolveSourceLabel(String playerName, OpenQuizData data, List<QuizManager.Problem> problems) {
        if (data.fluencyFeastMode()) return "fluency feast";
        if (MathQuestConfig.INSTANCE != null) {
            return switch (MathQuestConfig.INSTANCE.resolveInternalQuizSource(playerName)) {
                case "internal_problem_list" -> problems.isEmpty() ? "internal problem list (none loaded)" : "internal problem list";
                case "internal_quick_quiz" -> problems.isEmpty() ? "quick quiz (none loaded)" : "quick quiz";
                case "internal_fluency_feast" -> "fluency feast";
                default -> "generated";
            };
        }
        if (!problems.isEmpty()) return "external list";
        return "generated";
    }

    private static List<QuizManager.Problem> parseProblems(String problemsJson) {
        List<QuizManager.Problem> out = new java.util.ArrayList<>();
        if (problemsJson == null || "[]".equals(problemsJson)) return out;
        try {
            JsonArray arr = JsonParser.parseString(problemsJson).getAsJsonArray();
            for (var el : arr) {
                var obj = el.getAsJsonObject();
                out.add(QuizManager.Problem.create(
                    obj.get("operation").getAsString(),
                    obj.get("factorA").getAsInt(),
                    obj.get("factorB").getAsInt()
                ));
            }
        } catch (Exception ignored) {
        }
        return out;
    }

    private static String dominantOperation(List<QuizManager.Problem> problems) {
        Map<String, Integer> counts = new HashMap<>();
        for (QuizManager.Problem p : problems) {
            String op = MathQuestConfig.normalizeOperation(p.operation);
            counts.merge(op, 1, Integer::sum);
        }
        String best = "multiplication";
        int bestCount = 0;
        for (Map.Entry<String, Integer> e : counts.entrySet()) {
            if (e.getValue() > bestCount) {
                bestCount = e.getValue();
                best = e.getKey();
            }
        }
        return counts.size() > 1 ? best + " (+mixed)" : best;
    }

    private static String rangeFromProblems(List<QuizManager.Problem> problems) {
        int min = Integer.MAX_VALUE;
        int max = Integer.MIN_VALUE;
        for (QuizManager.Problem p : problems) {
            min = Math.min(min, Math.min(p.factorA, p.factorB));
            max = Math.max(max, Math.max(p.factorA, p.factorB));
        }
        if (min == Integer.MAX_VALUE) return "?";
        return min + "-" + max;
    }
}
