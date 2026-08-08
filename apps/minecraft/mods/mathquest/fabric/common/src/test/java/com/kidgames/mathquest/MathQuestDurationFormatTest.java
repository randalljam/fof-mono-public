package com.kidgames.mathquest;

import com.kidgames.mathquest.util.MathQuestDurationFormat;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

public class MathQuestDurationFormatTest {
    @Test
    void forStatusUsesFullWords() {
        assertEquals("1 second", MathQuestDurationFormat.forStatus(1));
        assertEquals("45 seconds", MathQuestDurationFormat.forStatus(45));
        assertEquals("1m 30s", MathQuestDurationFormat.forStatus(90));
        assertEquals("1 minute", MathQuestDurationFormat.forStatus(60));
        assertEquals("5 minutes", MathQuestDurationFormat.forStatus(300));
        assertEquals("2m 30s", MathQuestDurationFormat.forStatus(150));
    }

    @Test
    void forCompactUiUsesAbbreviations() {
        assertEquals("45s", MathQuestDurationFormat.forCompactUi(45));
        assertEquals("1 min", MathQuestDurationFormat.forCompactUi(60));
        assertEquals("5 mins", MathQuestDurationFormat.forCompactUi(300));
        assertEquals("2m 30s", MathQuestDurationFormat.forCompactUi(150));
    }
}
