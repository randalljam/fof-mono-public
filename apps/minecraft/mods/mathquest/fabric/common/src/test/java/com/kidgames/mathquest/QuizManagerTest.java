package com.kidgames.mathquest;

import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.quiz.QuizManager;
import com.kidgames.mathquest.quiz.QuizSessionOptions;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.RepeatedTest;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for MathQuest core logic.
 * These test pure Java logic without Minecraft dependencies.
 * Run with: ./gradlew test
 */
public class QuizManagerTest {

    private MathQuestConfig makeConfig(int min, int max, int problems) {
        MathQuestConfig config = new MathQuestConfig();
        config.minNumber = min;
        config.maxNumber = max;
        config.problemsPerQuiz = problems;
        config.operation = "multiplication";
        return config;
    }

    @Test
    void testProblemCountMatchesConfig() {
        MathQuestConfig config = makeConfig(2, 9, 5);
        QuizManager quiz = new QuizManager(config);
        assertEquals(5, quiz.getTotalProblems());
        assertEquals(5, quiz.getProblems().size());
    }

    @Test
    void testSingleProblemQuiz() {
        MathQuestConfig config = makeConfig(2, 9, 1);
        QuizManager quiz = new QuizManager(config);
        assertEquals(1, quiz.getTotalProblems());
        assertFalse(quiz.isQuizComplete());

        QuizManager.Problem p = quiz.getCurrentProblem();
        assertNotNull(p);
        quiz.submitAnswer(p.correctAnswer);
        quiz.advanceToNext();
        assertTrue(quiz.isQuizComplete());
    }

    @RepeatedTest(20)
    void testProblemsInConfiguredRange() {
        MathQuestConfig config = makeConfig(5, 9, 10);
        QuizManager quiz = new QuizManager(config);

        for (QuizManager.Problem p : quiz.getProblems()) {
            assertTrue(p.factorA >= 5 && p.factorA <= 9,
                "factorA " + p.factorA + " should be in [5,9]");
            assertTrue(p.factorB >= 5 && p.factorB <= 9,
                "factorB " + p.factorB + " should be in [5,9]");
            assertEquals((long) p.factorA * p.factorB, p.correctAnswer,
                "correctAnswer should be factorA * factorB");
        }
    }

    @Test
    void testCorrectAnswerDetection() {
        MathQuestConfig config = makeConfig(2, 9, 3);
        QuizManager quiz = new QuizManager(config);

        QuizManager.Problem p = quiz.getCurrentProblem();
        boolean result = quiz.submitAnswer(p.correctAnswer);
        assertTrue(result);
        assertTrue(p.isCorrect);
        assertEquals(p.correctAnswer, p.playerAnswer.longValue());
        assertEquals(1, quiz.getCorrectCount());
    }

    @Test
    void testWrongAnswerDetection() {
        MathQuestConfig config = makeConfig(2, 9, 3);
        QuizManager quiz = new QuizManager(config);

        QuizManager.Problem p = quiz.getCurrentProblem();
        long wrongAnswer = p.correctAnswer + 1;
        boolean result = quiz.submitAnswer(wrongAnswer);
        assertFalse(result);
        assertFalse(p.isCorrect);
        assertEquals(wrongAnswer, p.playerAnswer.longValue());
        assertEquals(0, quiz.getCorrectCount());
    }

    @Test
    void testFullQuizFlow() {
        MathQuestConfig config = makeConfig(2, 5, 3);
        QuizManager quiz = new QuizManager(config);

        assertEquals(0, quiz.getCurrentIndex());
        assertFalse(quiz.isQuizComplete());

        // Answer all 3 questions correctly
        for (int i = 0; i < 3; i++) {
            assertFalse(quiz.isQuizComplete());
            QuizManager.Problem p = quiz.getCurrentProblem();
            assertNotNull(p);
            quiz.submitAnswer(p.correctAnswer);
            quiz.advanceToNext();
        }

        assertTrue(quiz.isQuizComplete());
        assertEquals(3, quiz.getCorrectCount());
        assertNull(quiz.getCurrentProblem());
    }

    @Test
    void testMixedCorrectAndWrong() {
        MathQuestConfig config = makeConfig(2, 9, 4);
        QuizManager quiz = new QuizManager(config);

        // Q1: correct
        quiz.submitAnswer(quiz.getCurrentProblem().correctAnswer);
        quiz.advanceToNext();

        // Q2: wrong
        quiz.submitAnswer(quiz.getCurrentProblem().correctAnswer + 99L);
        quiz.advanceToNext();

        // Q3: correct
        quiz.submitAnswer(quiz.getCurrentProblem().correctAnswer);
        quiz.advanceToNext();

        // Q4: wrong
        quiz.submitAnswer(0);
        quiz.advanceToNext();

        assertTrue(quiz.isQuizComplete());
        assertEquals(2, quiz.getCorrectCount());
    }

    @Test
    void testResponseTimeTracking() {
        MathQuestConfig config = makeConfig(2, 9, 1);
        QuizManager quiz = new QuizManager(config);

        QuizManager.Problem p = quiz.getCurrentProblem();
        assertEquals(0, p.responseTimeMs);

        p.responseTimeMs = 2500;
        quiz.submitAnswer(p.correctAnswer);

        assertEquals(2500, p.responseTimeMs);
    }

    @Test
    void testMinEqualsMax() {
        // Edge case: only one possible number
        MathQuestConfig config = makeConfig(7, 7, 5);
        QuizManager quiz = new QuizManager(config);

        for (QuizManager.Problem p : quiz.getProblems()) {
            assertEquals(7, p.factorA);
            assertEquals(7, p.factorB);
            assertEquals(49, p.correctAnswer);
        }
    }

    @Test
    void testSubmitAnswerOnCompletedQuiz() {
        MathQuestConfig config = makeConfig(2, 9, 1);
        QuizManager quiz = new QuizManager(config);

        quiz.submitAnswer(quiz.getCurrentProblem().correctAnswer);
        quiz.advanceToNext();
        assertTrue(quiz.isQuizComplete());

        // Submitting after completion should return false
        assertFalse(quiz.submitAnswer(42));
    }

    @Test
    void testZeroAnswer() {
        MathQuestConfig config = makeConfig(2, 9, 1);
        QuizManager quiz = new QuizManager(config);

        QuizManager.Problem p = quiz.getCurrentProblem();
        boolean result = quiz.submitAnswer(0);
        // 0 is wrong for any product of 2-9
        assertFalse(result);
        assertEquals(0L, p.playerAnswer.longValue());
    }

    @Test
    void repeatUntilFluentRequeuesSlowOrWrongAnswers() {
        QuizManager quiz = new QuizManager(
            new MathQuestConfig.EffectiveQuizParams(0, 1, "addition", 1),
            java.util.List.of(QuizManager.Problem.create("addition", 0, 1))
        );
        quiz.setSessionOptions(QuizSessionOptions.questFixed(2000, 1, true));

        QuizManager.Problem slow = quiz.getCurrentProblem();
        slow.responseTimeMs = 2500;
        assertTrue(quiz.submitAnswer(slow.correctAnswer));
        quiz.applyPostAnswerPolicy(slow);
        assertEquals(2, quiz.getTotalProblems());

        quiz.advanceToNext();
        QuizManager.Problem retry = quiz.getCurrentProblem();
        retry.responseTimeMs = 1500;
        assertTrue(quiz.submitAnswer(retry.correctAnswer));
        quiz.applyPostAnswerPolicy(retry);
        assertEquals(2, quiz.getTotalProblems());
    }

    @Test
    void repeatUntilFluentHonorsRequiredFastStreak() {
        QuizManager quiz = new QuizManager(
            new MathQuestConfig.EffectiveQuizParams(0, 1, "addition", 1),
            java.util.List.of(QuizManager.Problem.create("addition", 1, 1))
        );
        quiz.setSessionOptions(QuizSessionOptions.questFixed(2000, 2, true));

        QuizManager.Problem firstFast = quiz.getCurrentProblem();
        firstFast.responseTimeMs = 1500;
        assertTrue(quiz.submitAnswer(firstFast.correctAnswer));
        quiz.applyPostAnswerPolicy(firstFast);
        assertEquals(2, quiz.getTotalProblems());

        quiz.advanceToNext();
        QuizManager.Problem secondFast = quiz.getCurrentProblem();
        secondFast.responseTimeMs = 1500;
        assertTrue(quiz.submitAnswer(secondFast.correctAnswer));
        quiz.applyPostAnswerPolicy(secondFast);
        assertEquals(2, quiz.getTotalProblems());
    }

    @Test
    void testNegativeAnswer() {
        MathQuestConfig config = makeConfig(2, 9, 1);
        QuizManager quiz = new QuizManager(config);

        boolean result = quiz.submitAnswer(-5);
        assertFalse(result);
    }

    @RepeatedTest(20)
    void testAdditionProblemsInRange() {
        MathQuestConfig config = new MathQuestConfig();
        config.minNumber = 0;
        config.maxNumber = 3;
        config.problemsPerQuiz = 8;
        config.operation = "addition";
        QuizManager quiz = new QuizManager(config);

        for (QuizManager.Problem p : quiz.getProblems()) {
            assertEquals("addition", p.operation);
            assertTrue(p.factorA >= 0 && p.factorA <= 3);
            assertTrue(p.factorB >= 0 && p.factorB <= 3);
            assertEquals((long) p.factorA + p.factorB, p.correctAnswer);
        }
    }

    @RepeatedTest(20)
    void testSubtractionProblemsInRange() {
        MathQuestConfig config = new MathQuestConfig();
        config.minNumber = 0;
        config.maxNumber = 5;
        config.problemsPerQuiz = 8;
        config.operation = "subtraction";
        QuizManager quiz = new QuizManager(config);

        for (QuizManager.Problem p : quiz.getProblems()) {
            assertEquals("subtraction", p.operation);
            assertTrue(p.factorA >= 0 && p.factorA <= 5);
            assertTrue(p.factorB >= 0 && p.factorB <= 5);
            assertEquals((long) p.factorA - p.factorB, p.correctAnswer);
        }
    }

    @RepeatedTest(20)
    void testExponentiationProblems() {
        MathQuestConfig config = new MathQuestConfig();
        config.minNumber = 0;
        config.maxNumber = 4;
        config.problemsPerQuiz = 6;
        config.operation = "exponentiation";
        QuizManager quiz = new QuizManager(config);

        for (QuizManager.Problem p : quiz.getProblems()) {
            assertEquals("exponentiation", p.operation);
            long expected = 1;
            for (int i = 0; i < p.factorB; i++) {
                expected *= p.factorA;
            }
            assertEquals(expected, p.correctAnswer);
        }
    }

    @Test
    void testPerPlayerPresetOverrides() {
        MathQuestConfig config = new MathQuestConfig();
        config.minNumber = 2;
        config.maxNumber = 9;
        config.operation = "multiplication";
        config.playerPresets.put("wildpetal", new MathQuestConfig.PlayerQuizPreset(5, 9, "multiplication", 7));

        MathQuestConfig.EffectiveQuizParams wild = config.resolveForPlayer("WildPetal");
        assertEquals(5, wild.minNumber());
        assertEquals(9, wild.maxNumber());
        assertEquals("multiplication", wild.operation());
        assertEquals(7, wild.problemsPerQuiz());

        MathQuestConfig.EffectiveQuizParams other = config.resolveForPlayer("SomeoneElse");
        assertEquals(2, other.minNumber());
        assertEquals(9, other.maxNumber());
    }
    @Test
    void testExplicitProblemListPreservesOrderAndOperations() {
        MathQuestConfig.EffectiveQuizParams fallback =
            new MathQuestConfig.EffectiveQuizParams(0, 9, "multiplication", 5);
        java.util.List<QuizManager.Problem> problems = java.util.List.of(
            QuizManager.Problem.create("+", 2, 3),
            QuizManager.Problem.create("*", 6, 7),
            QuizManager.Problem.create("/", 12, 3)
        );
        QuizManager quiz = new QuizManager(fallback, problems);
        assertEquals(3, quiz.getTotalProblems());
        assertEquals("addition", quiz.getProblems().get(0).operation);
        assertEquals(5, quiz.getProblems().get(0).correctAnswer);
        assertEquals("multiplication", quiz.getProblems().get(1).operation);
        assertEquals(42, quiz.getProblems().get(1).correctAnswer);
        assertEquals("division", quiz.getProblems().get(2).operation);
        assertEquals(4, quiz.getProblems().get(2).correctAnswer);
    }
    @Test
    void testInsertCurrentProblemLaterRequeuesSameFact() {
        MathQuestConfig.EffectiveQuizParams fallback =
            new MathQuestConfig.EffectiveQuizParams(0, 9, "multiplication", 2);
        QuizManager.Problem first = QuizManager.Problem.create("+", 1, 2);
        QuizManager.Problem second = QuizManager.Problem.create("*", 3, 4);
        QuizManager quiz = new QuizManager(fallback, java.util.List.of(first, second));

        quiz.insertCurrentProblemLater(5);

        assertEquals(3, quiz.getTotalProblems());
        QuizManager.Problem inserted = quiz.getProblems().get(2);
        assertEquals(first.operation, inserted.operation);
        assertEquals(first.factorA, inserted.factorA);
        assertEquals(first.factorB, inserted.factorB);
        assertNull(inserted.playerAnswer);
        assertTrue(inserted.flags.isEmpty());
    }
}
