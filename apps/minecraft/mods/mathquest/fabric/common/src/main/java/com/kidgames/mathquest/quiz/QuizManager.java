package com.kidgames.mathquest.quiz;

import com.kidgames.mathquest.config.MathQuestConfig;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;

public class QuizManager {
    private static final Random RANDOM = new Random();

    private final String operation;
    private final int minNumber;
    private final int maxNumber;
    private final List<Problem> problems = new ArrayList<>();
    private int currentIndex = 0;
    private int correctCount = 0;
    private QuizSessionOptions sessionOptions = QuizSessionOptions.standard();
    private final Map<String, Integer> currentFastStreakByProblem = new HashMap<>();
    private final Map<String, Integer> maxFastStreakByProblem = new HashMap<>();

    /** Uses global defaults only (no per-player preset). For tests and legacy callers. */
    public QuizManager(MathQuestConfig config) {
        this(config.resolveForPlayer(null));
    }

    public QuizManager(MathQuestConfig config, String playerName) {
        this(config.resolveForPlayer(playerName));
    }

    public QuizManager(MathQuestConfig.EffectiveQuizParams params) {
        this.operation = params.operation();
        this.minNumber = params.minNumber();
        this.maxNumber = params.maxNumber();
        generateProblems(params.problemsPerQuiz());
    }
    public QuizManager(MathQuestConfig.EffectiveQuizParams params, List<Problem> problemList) {
        if (problemList != null && !problemList.isEmpty()) {
            this.operation = problemList.get(0).operation;
            this.minNumber = minFactor(problemList);
            this.maxNumber = maxFactor(problemList);
            this.problems.addAll(problemList);
            this.currentIndex = 0;
            this.correctCount = 0;
        } else {
            this.operation = params.operation();
            this.minNumber = params.minNumber();
            this.maxNumber = params.maxNumber();
            generateProblems(params.problemsPerQuiz());
        }
    }

    private void generateProblems(int count) {
        problems.clear();
        for (int i = 0; i < count; i++) {
            int a = randomInRange(minNumber, maxNumber);
            int b = randomInRange(minNumber, maxNumber);
            problems.add(Problem.create(operation, a, b));
        }
        currentIndex = 0;
        correctCount = 0;
    }

    private int randomInRange(int min, int max) {
        return min + RANDOM.nextInt(max - min + 1);
    }

    public String getOperation() {
        return operation;
    }
    public int getMinNumber() {
        return minNumber;
    }
    public int getMaxNumber() {
        return maxNumber;
    }

    public Problem getCurrentProblem() {
        if (currentIndex < problems.size()) {
            return problems.get(currentIndex);
        }
        return null;
    }

    public boolean submitAnswer(long answer) {
        Problem current = getCurrentProblem();
        if (current == null) return false;

        current.playerAnswer = answer;
        current.isCorrect = (answer == current.correctAnswer);
        if (current.isCorrect) {
            correctCount++;
        }
        return current.isCorrect;
    }

    public void setSessionOptions(QuizSessionOptions options) {
        this.sessionOptions = options == null ? QuizSessionOptions.standard() : options;
    }

    public QuizSessionOptions getSessionOptions() {
        return sessionOptions;
    }

    public void applyPostAnswerPolicy(Problem problem) {
        if (problem == null || !sessionOptions.repeatUntilFluent()) return;
        boolean fastCorrect = problem.isCorrect
            && problem.responseTimeMs > 0
            && problem.responseTimeMs <= sessionOptions.fluencyMs();
        String key = problem.key();
        int currentStreak = fastCorrect
            ? currentFastStreakByProblem.getOrDefault(key, 0) + 1
            : 0;
        currentFastStreakByProblem.put(key, currentStreak);
        maxFastStreakByProblem.put(key, Math.max(
            maxFastStreakByProblem.getOrDefault(key, 0),
            currentStreak
        ));
        if (maxFastStreakByProblem.getOrDefault(key, 0) < sessionOptions.fastCorrectRequired()) {
            problems.add(Problem.create(problem.operation, problem.factorA, problem.factorB));
        }
    }

    public void skipCurrent(long responseTimeMs) {
        Problem current = getCurrentProblem();
        if (current == null) return;
        current.playerAnswer = null;
        current.isCorrect = false;
        current.responseTimeMs = responseTimeMs;
        applyPostAnswerPolicy(current);
    }

    public void advanceToNext() {
        currentIndex++;
    }
    public void insertCurrentProblemLater(int gap) {
        insertProblemLater(getCurrentProblem(), gap);
    }
    public void insertProblemLater(Problem source, int gap) {
        if (source == null) return;
        int offset = Math.max(1, gap);
        int insertIndex = Math.min(problems.size(), currentIndex + offset + 1);
        problems.add(insertIndex, Problem.create(source.operation, source.factorA, source.factorB));
    }

    public boolean isQuizComplete() {
        return currentIndex >= problems.size();
    }

    public int getCurrentIndex() {
        return currentIndex;
    }

    public int getTotalProblems() {
        return problems.size();
    }

    public int getCorrectCount() {
        return correctCount;
    }
    public int getAnsweredCount() {
        int count = 0;
        for (Problem problem : problems) {
            if (problem.wasAnswered()) count++;
        }
        return count;
    }
    public void keepAnsweredProblemsOnly() {
        int answered = getAnsweredCount();
        if (answered < problems.size()) {
            problems.subList(answered, problems.size()).clear();
        }
        currentIndex = problems.size();
    }

    public List<Problem> getProblems() {
        return problems;
    }

    public static QuizManager fromCompletedProblems(String operation, List<Problem> completedProblems, int correctCount) {
        QuizManager quiz = new QuizManager(operation, completedProblems, correctCount);
        return quiz;
    }

    private QuizManager(String operation, List<Problem> completedProblems, int correctCount) {
        this.operation = operation;
        this.minNumber = minFactor(completedProblems);
        this.maxNumber = maxFactor(completedProblems);
        this.problems.addAll(completedProblems);
        this.currentIndex = completedProblems.size();
        this.correctCount = correctCount;
    }
    private static int minFactor(List<Problem> problems) {
        if (problems == null || problems.isEmpty()) return 0;
        int min = Integer.MAX_VALUE;
        for (Problem problem : problems) {
            min = Math.min(min, Math.min(problem.factorA, problem.factorB));
        }
        return min;
    }
    private static int maxFactor(List<Problem> problems) {
        if (problems == null || problems.isEmpty()) return 0;
        int max = Integer.MIN_VALUE;
        for (Problem problem : problems) {
            max = Math.max(max, Math.max(problem.factorA, problem.factorB));
        }
        return max;
    }

    public static class Problem {
        public final String operation;
        public final int factorA;
        public final int factorB;
        public final long correctAnswer;
        public Long playerAnswer;
        public boolean isCorrect = false;
        public long responseTimeMs = 0;
        public final List<String> flags = new ArrayList<>();

        private Problem(String operation, int factorA, int factorB, long correctAnswer) {
            this.operation = operation;
            this.factorA = factorA;
            this.factorB = factorB;
            this.correctAnswer = correctAnswer;
        }

        public static Problem create(String operation, int a, int b) {
            String op = MathQuestConfig.normalizeOperation(operation);
            return switch (op) {
                case "addition" -> new Problem("addition", a, b, (long) a + b);
                case "subtraction" -> new Problem("subtraction", a, b, (long) a - b);
                case "division" -> new Problem("division", a, b, b == 0 ? 0 : (long) a / b);
                case "exponentiation" -> new Problem("exponentiation", a, b, intPow(a, b));
                default -> new Problem("multiplication", a, b, (long) a * b);
            };
        }

        /** a^b for non-negative integers; fits in long for kid-sized ranges. */
        private static long intPow(int base, int exp) {
            if (exp < 0) return 0;
            long result = 1;
            for (int i = 0; i < exp; i++) {
                result *= base;
            }
            return result;
        }

        public String getQuestionText() {
            return switch (operation) {
                case "addition" -> factorA + " + " + factorB + " = ?";
                case "subtraction" -> factorA + " - " + factorB + " = ?";
                case "division" -> factorA + " / " + factorB + " = ?";
                case "exponentiation" -> factorA + " ^ " + factorB + " = ?";
                default -> factorA + " x " + factorB + " = ?";
            };
        }

        public String getProblemTextForExport() {
            return switch (operation) {
                case "addition" -> factorA + " + " + factorB;
                case "subtraction" -> factorA + " - " + factorB;
                case "division" -> factorA + " / " + factorB;
                case "exponentiation" -> factorA + " ^ " + factorB;
                default -> factorA + " * " + factorB;
            };
        }
        public boolean wasAnswered() {
            return playerAnswer != null || responseTimeMs > 0;
        }
        public void addFlag(String flag) {
            if (flag == null || flag.isBlank()) return;
            if (!flags.contains(flag)) flags.add(flag);
        }

        public String key() {
            return operation + ":" + factorA + ":" + factorB;
        }
    }
}
