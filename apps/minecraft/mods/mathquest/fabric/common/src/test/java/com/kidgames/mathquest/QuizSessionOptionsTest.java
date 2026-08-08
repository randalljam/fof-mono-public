package com.kidgames.mathquest;

import com.kidgames.mathquest.quiz.QuizSessionOptions;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class QuizSessionOptionsTest {
    @Test
    void tpCreditSessionRoundTripsAndPartialQuizClearsEligibility() {
        QuizSessionOptions issued = QuizSessionOptions.standard()
            .withTpCreditCompletionToken("one-use-token");
        QuizSessionOptions restored = QuizSessionOptions.fromJson(issued.toJson());

        assertTrue(restored.tpCreditEligible());
        assertEquals("one-use-token", restored.tpCreditCompletionToken());

        QuizSessionOptions partial = restored.withoutTpCreditAward();
        assertFalse(partial.tpCreditEligible());
        assertEquals("one-use-token", partial.tpCreditCompletionToken());
    }
}
