package com.kidgames.mathquest.network;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class EarnTpCreditsPayloadTest {
    @Test
    void completionRequestCarriesOnlyTheServerIssuedToken() {
        EarnTpCreditsPayload payload = new EarnTpCreditsPayload("session-token");

        assertEquals(EarnTpCreditsPayload.ID, payload.type());
        assertEquals("session-token", payload.completionToken());
        assertEquals(1, EarnTpCreditsPayload.class.getRecordComponents().length);
    }
}
