package com.kidgames.mathquest;

import com.kidgames.mathquest.reward.TpCreditCompletionTracker;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class TpCreditCompletionTrackerTest {
    @AfterEach
    void resetTracker() {
        TpCreditCompletionTracker.resetForTests();
    }

    @Test
    void completedSessionCanBeConsumedExactlyOnceCaseInsensitively() {
        String token = TpCreditCompletionTracker.issue("WildPetal");

        assertFalse(TpCreditCompletionTracker.consumeCompleted("wildpetal", token));
        assertTrue(TpCreditCompletionTracker.markCompleted("WILDPETAL", token));
        assertTrue(TpCreditCompletionTracker.consumeCompleted("wildpetal", token));
        assertFalse(TpCreditCompletionTracker.consumeCompleted("WILDPETAL", token));
    }

    @Test
    void sessionCannotBeConsumedByAnotherPlayer() {
        String token = TpCreditCompletionTracker.issue("WildPetal");

        assertFalse(TpCreditCompletionTracker.markCompleted("PumaJockey", token));
        assertTrue(TpCreditCompletionTracker.markCompleted("WildPetal", token));
        assertFalse(TpCreditCompletionTracker.consumeCompleted("PumaJockey", token));
        assertTrue(TpCreditCompletionTracker.consumeCompleted("WildPetal", token));
    }

    @Test
    void cancelledSessionCanNeverBeCompletedOrConsumed() {
        String token = TpCreditCompletionTracker.issue("WildPetal");

        assertTrue(TpCreditCompletionTracker.cancel("WildPetal", token));
        assertFalse(TpCreditCompletionTracker.markCompleted("WildPetal", token));
        assertFalse(TpCreditCompletionTracker.consumeCompleted("WildPetal", token));
    }
}
