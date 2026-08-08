package com.kidgames.mathquest.network;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class QuestInvitationPayloadTest {
    @Test
    void invitationCarriesDirectQuizLaunchPayload() {
        QuestInvitationPayload invitation = new QuestInvitationPayload(
            "message",
            "subtitle",
            "addition",
            0,
            9,
            7,
            "[{\"operation\":\"+\",\"factorA\":0,\"factorB\":1}]",
            "[{\"item\":\"minecraft:torch\",\"count\":1}]",
            "all",
            "standard_arithmetic",
            "{\"questMode\":true}"
        );

        OpenQuizPayload quiz = invitation.openQuizPayload();

        assertEquals("addition", quiz.operation());
        assertEquals(0, quiz.minNumber());
        assertEquals(9, quiz.maxNumber());
        assertEquals(7, quiz.problemsPerQuiz());
        assertEquals(invitation.problemsJson(), quiz.problemsJson());
        assertEquals(invitation.rewardsJson(), quiz.rewardsJson());
        assertEquals("all", quiz.rewardMode());
        assertEquals("standard_arithmetic", quiz.quizType());
        assertEquals(invitation.optionsJson(), quiz.optionsJson());
        assertTrue(quiz.directToQuiz());
        assertEquals(false, quiz.fluencyFeastMode());
    }
}
