package com.kidgames.mathquest.quest;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class QuestQuizDefinitionsTest {
    @Test
    void m1ProblemSetKeepsOperandDirectionsSeparate() {
        List<QuestQuizDefinitions.ProblemSpec> problems = QuestQuizDefinitions.caveEscapeM1Problems();

        assertEquals(36, problems.size());
        assertTrue(contains(problems, 0, 7));
        assertTrue(contains(problems, 7, 0));
        assertTrue(contains(problems, 1, 9));
        assertTrue(contains(problems, 9, 1));
    }

    @Test
    void m1CompletionRequiresOneFastCorrectForEveryOrientedProblem() {
        List<QuestQuizDefinitions.Attempt> attempts = fastCorrectAttempts();
        attempts.remove(attempts.size() - 1);

        Map<String, QuestQuizDefinitions.OrientedStats> incomplete =
            QuestQuizDefinitions.orientedStats(attempts, QuestQuizDefinitions.CAVE_ESCAPE_M1_FLUENCY_MS);
        assertFalse(QuestQuizDefinitions.caveEscapeM1Complete(incomplete));
        assertEquals(1, QuestQuizDefinitions.caveEscapeM1RemainingProblems(incomplete).size());

        attempts.add(new QuestQuizDefinitions.Attempt("addition", 9, 1, false, 500));
        Map<String, QuestQuizDefinitions.OrientedStats> wrong =
            QuestQuizDefinitions.orientedStats(attempts, QuestQuizDefinitions.CAVE_ESCAPE_M1_FLUENCY_MS);
        assertFalse(QuestQuizDefinitions.caveEscapeM1Complete(wrong));

        attempts.add(new QuestQuizDefinitions.Attempt("addition", 9, 1, true, 1999));
        Map<String, QuestQuizDefinitions.OrientedStats> complete =
            QuestQuizDefinitions.orientedStats(attempts, QuestQuizDefinitions.CAVE_ESCAPE_M1_FLUENCY_MS);
        assertTrue(QuestQuizDefinitions.caveEscapeM1Complete(complete));
        assertEquals(0, QuestQuizDefinitions.caveEscapeM1RemainingProblems(complete).size());
    }

    @Test
    void m1CompletionDoesNotCountSlowCorrectAnswersAsFluent() {
        List<QuestQuizDefinitions.Attempt> attempts = fastCorrectAttempts();
        attempts.removeIf(attempt -> attempt.factorA() == 7 && attempt.factorB() == 0);
        attempts.add(new QuestQuizDefinitions.Attempt("addition", 7, 0, true, 2001));

        Map<String, QuestQuizDefinitions.OrientedStats> stats =
            QuestQuizDefinitions.orientedStats(attempts, QuestQuizDefinitions.CAVE_ESCAPE_M1_FLUENCY_MS);

        assertFalse(QuestQuizDefinitions.caveEscapeM1Complete(stats));
        assertEquals(List.of(new QuestQuizDefinitions.ProblemSpec("addition", 7, 0)),
            QuestQuizDefinitions.caveEscapeM1RemainingProblems(stats));
    }

    @Test
    void m2ProblemSetUsesAddTwoDirectionsAndDoubles() {
        List<QuestQuizDefinitions.ProblemSpec> problems = QuestQuizDefinitions.caveEscapeM2Problems();

        assertEquals(21, problems.size());
        assertTrue(contains(problems, 2, 3));
        assertTrue(contains(problems, 3, 2));
        assertTrue(contains(problems, 9, 2));
        assertTrue(contains(problems, 9, 9));
        assertFalse(contains(problems, 2, 2));
    }

    @Test
    void m2CompletionRequiresTwoConsecutiveFastCorrectForEveryOrientedProblem() {
        List<QuestQuizDefinitions.Attempt> attempts = new ArrayList<>();
        for (QuestQuizDefinitions.ProblemSpec problem : QuestQuizDefinitions.caveEscapeM2Problems()) {
            attempts.add(new QuestQuizDefinitions.Attempt(
                problem.operation(), problem.factorA(), problem.factorB(), true, 1500));
            attempts.add(new QuestQuizDefinitions.Attempt(
                problem.operation(), problem.factorA(), problem.factorB(), true, 1500));
        }
        attempts.removeIf(attempt -> attempt.factorA() == 2 && attempt.factorB() == 9);
        attempts.add(new QuestQuizDefinitions.Attempt("addition", 2, 9, true, 2001));
        attempts.add(new QuestQuizDefinitions.Attempt("addition", 2, 9, true, 1999));

        Map<String, QuestQuizDefinitions.OrientedStats> incomplete =
            QuestQuizDefinitions.orientedStats(attempts, QuestQuizDefinitions.CAVE_ESCAPE_M2_FLUENCY_MS);
        assertFalse(QuestQuizDefinitions.caveEscapeM2Complete(incomplete));
        assertEquals(List.of(new QuestQuizDefinitions.ProblemSpec("addition", 2, 9)),
            QuestQuizDefinitions.caveEscapeM2RemainingProblems(incomplete));

        attempts.add(new QuestQuizDefinitions.Attempt("addition", 2, 9, true, 1999));
        Map<String, QuestQuizDefinitions.OrientedStats> complete =
            QuestQuizDefinitions.orientedStats(attempts, QuestQuizDefinitions.CAVE_ESCAPE_M2_FLUENCY_MS);
        assertTrue(QuestQuizDefinitions.caveEscapeM2Complete(complete));
        assertEquals(0, QuestQuizDefinitions.caveEscapeM2RemainingProblems(complete).size());
    }

    private static List<QuestQuizDefinitions.Attempt> fastCorrectAttempts() {
        List<QuestQuizDefinitions.Attempt> attempts = new ArrayList<>();
        for (QuestQuizDefinitions.ProblemSpec problem : QuestQuizDefinitions.caveEscapeM1Problems()) {
            attempts.add(new QuestQuizDefinitions.Attempt(
                problem.operation(), problem.factorA(), problem.factorB(), true, 1500));
        }
        return attempts;
    }

    private static boolean contains(List<QuestQuizDefinitions.ProblemSpec> problems, int a, int b) {
        return problems.contains(new QuestQuizDefinitions.ProblemSpec("addition", a, b));
    }
}
