package com.kidgames.mathquest.screen;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;

class QuestInvitationScreenTest {
    @Test
    void acceptClosesInvitationBeforeSendingResponse() {
        List<String> events = new ArrayList<>();

        QuestInvitationResponseFlow.respond(
            true,
            () -> events.add("close"),
            () -> events.add("open-quiz"),
            payload -> events.add("send:" + payload.accepted())
        );

        assertEquals(List.of("close", "open-quiz", "send:true"), events);
    }

    @Test
    void declineClosesInvitationBeforeSendingResponse() {
        List<String> events = new ArrayList<>();

        QuestInvitationResponseFlow.respond(
            false,
            () -> events.add("close"),
            () -> events.add("open-quiz"),
            payload -> events.add("send:" + payload.accepted())
        );

        assertEquals(List.of("close", "send:false"), events);
    }
}
