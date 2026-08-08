package com.kidgames.mathquest.quest;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/** Quest-owned quiz definitions and fluency predicates. */
public final class QuestQuizDefinitions {
    public static final String CAVE_ESCAPE_M1_QUIZ_ID = "quest1.m1.zero-one-fixed";
    public static final String CAVE_ESCAPE_M2_QUIZ_ID = "quest1.m2.two-doubles-fixed";
    public static final int CAVE_ESCAPE_M1_FLUENCY_MS = 2000;
    public static final int CAVE_ESCAPE_M1_FAST_CORRECT_REQUIRED = 1;
    public static final int CAVE_ESCAPE_M2_FLUENCY_MS = 2000;
    public static final int CAVE_ESCAPE_M2_FAST_CORRECT_REQUIRED = 2;

    private static final List<ProblemSpec> CAVE_ESCAPE_M1_PROBLEMS = buildCaveEscapeM1Problems();
    private static final List<ProblemSpec> CAVE_ESCAPE_M2_PROBLEMS = buildCaveEscapeM2Problems();

    private QuestQuizDefinitions() {}

    public static List<ProblemSpec> caveEscapeM1Problems() {
        return CAVE_ESCAPE_M1_PROBLEMS;
    }

    public static List<ProblemSpec> caveEscapeM2Problems() {
        return CAVE_ESCAPE_M2_PROBLEMS;
    }

    public static List<ProblemSpec> caveEscapeM1RemainingProblems(Map<String, OrientedStats> stats) {
        return remainingProblems(CAVE_ESCAPE_M1_PROBLEMS, stats, CAVE_ESCAPE_M1_FAST_CORRECT_REQUIRED);
    }

    public static List<ProblemSpec> caveEscapeM2RemainingProblems(Map<String, OrientedStats> stats) {
        return remainingProblems(CAVE_ESCAPE_M2_PROBLEMS, stats, CAVE_ESCAPE_M2_FAST_CORRECT_REQUIRED);
    }

    private static List<ProblemSpec> remainingProblems(
        List<ProblemSpec> problems,
        Map<String, OrientedStats> stats,
        int fastCorrectRequired
    ) {
        List<ProblemSpec> out = new ArrayList<>();
        for (ProblemSpec problem : problems) {
            OrientedStats s = stats == null ? null : stats.get(problem.key());
            if (s == null || !s.fluent(fastCorrectRequired)) {
                out.add(problem);
            }
        }
        return out;
    }

    public static int caveEscapeM1FluentCount(Map<String, OrientedStats> stats) {
        return fluentCount(CAVE_ESCAPE_M1_PROBLEMS, stats, CAVE_ESCAPE_M1_FAST_CORRECT_REQUIRED);
    }

    public static int caveEscapeM2FluentCount(Map<String, OrientedStats> stats) {
        return fluentCount(CAVE_ESCAPE_M2_PROBLEMS, stats, CAVE_ESCAPE_M2_FAST_CORRECT_REQUIRED);
    }

    private static int fluentCount(List<ProblemSpec> problems, Map<String, OrientedStats> stats, int fastCorrectRequired) {
        int count = 0;
        for (ProblemSpec problem : problems) {
            OrientedStats s = stats == null ? null : stats.get(problem.key());
            if (s != null && s.fluent(fastCorrectRequired)) count++;
        }
        return count;
    }

    public static boolean caveEscapeM1Complete(Map<String, OrientedStats> stats) {
        return caveEscapeM1FluentCount(stats) >= CAVE_ESCAPE_M1_PROBLEMS.size();
    }

    public static boolean caveEscapeM2Complete(Map<String, OrientedStats> stats) {
        return caveEscapeM2FluentCount(stats) >= CAVE_ESCAPE_M2_PROBLEMS.size();
    }

    public static Map<String, OrientedStats> orientedStats(List<Attempt> attempts, int fastMs) {
        Map<String, MutableStats> mutable = new LinkedHashMap<>();
        if (attempts != null) {
            for (Attempt attempt : attempts) {
                if (attempt == null || !isAddition(attempt.operation())) continue;
                String key = key(attempt.operation(), attempt.factorA(), attempt.factorB());
                MutableStats stats = mutable.computeIfAbsent(key, ignored -> new MutableStats());
                stats.record(attempt.correct(), attempt.responseTimeMs(), fastMs);
            }
        }
        Map<String, OrientedStats> out = new LinkedHashMap<>();
        for (Map.Entry<String, MutableStats> entry : mutable.entrySet()) {
            MutableStats s = entry.getValue();
            out.put(entry.getKey(), new OrientedStats(
                s.attempts,
                s.correct,
                s.fastCorrect,
                s.maxFastCorrectStreak
            ));
        }
        return out;
    }

    public static String key(String operation, int factorA, int factorB) {
        return normalizeOperation(operation) + ":" + factorA + "+" + factorB;
    }

    private static List<ProblemSpec> buildCaveEscapeM1Problems() {
        Map<String, ProblemSpec> out = new LinkedHashMap<>();
        for (int n = 0; n <= 9; n++) {
            add(out, 0, n);
            add(out, n, 0);
            add(out, 1, n);
            add(out, n, 1);
        }
        return List.copyOf(out.values());
    }

    private static List<ProblemSpec> buildCaveEscapeM2Problems() {
        Map<String, ProblemSpec> out = new LinkedHashMap<>();
        for (int n = 3; n <= 9; n++) {
            add(out, 2, n);
            add(out, n, 2);
            add(out, n, n);
        }
        return List.copyOf(out.values());
    }

    private static void add(Map<String, ProblemSpec> out, int a, int b) {
        ProblemSpec problem = new ProblemSpec("addition", a, b);
        out.putIfAbsent(problem.key(), problem);
    }

    private static boolean isAddition(String operation) {
        return "addition".equals(normalizeOperation(operation));
    }

    private static String normalizeOperation(String operation) {
        if (operation == null || operation.isBlank()) return "";
        String clean = operation.trim().toLowerCase(Locale.ROOT);
        return switch (clean) {
            case "+", "add", "addition" -> "addition";
            default -> clean;
        };
    }

    public record ProblemSpec(String operation, int factorA, int factorB) {
        public String key() {
            return QuestQuizDefinitions.key(operation, factorA, factorB);
        }

        public String label() {
            return factorA + " + " + factorB;
        }
    }

    public record Attempt(String operation, int factorA, int factorB, boolean correct, long responseTimeMs) {}

    public record OrientedStats(int attempts, int correct, int fastCorrect, int maxFastCorrectStreak) {
        public boolean fluent(int fastCorrectRequired) {
            return maxFastCorrectStreak >= Math.max(1, fastCorrectRequired);
        }
    }

    private static final class MutableStats {
        int attempts;
        int correct;
        int fastCorrect;
        int currentFastCorrectStreak;
        int maxFastCorrectStreak;

        void record(boolean isCorrect, long responseTimeMs, int fastMs) {
            attempts++;
            if (isCorrect) {
                correct++;
                if (responseTimeMs > 0 && responseTimeMs <= fastMs) {
                    fastCorrect++;
                    currentFastCorrectStreak++;
                    maxFastCorrectStreak = Math.max(maxFastCorrectStreak, currentFastCorrectStreak);
                    return;
                }
            }
            currentFastCorrectStreak = 0;
        }
    }
}
