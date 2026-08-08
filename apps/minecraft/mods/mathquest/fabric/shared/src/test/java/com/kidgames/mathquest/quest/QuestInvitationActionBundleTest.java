package com.kidgames.mathquest.quest;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class QuestInvitationActionBundleTest {
    @Test
    void m1StartUsesInvitationScreenWithoutDuplicateTitleOverlay() {
        List<String> lines = CaveEscapeQuestService.defaultStartActionLines("m1_cave_start");

        assertTrue(lines.contains("chat " + CaveEscapeQuestService.QUEST_INVITATION_CHAT));
        assertTrue(lines.contains("open_quiz_invitation"));
        assertFalse(lines.contains("title " + CaveEscapeQuestService.QUEST_INVITATION_TITLE));
        assertEquals(
            lines.indexOf("chat " + CaveEscapeQuestService.QUEST_INVITATION_CHAT) + 1,
            lines.indexOf("open_quiz_invitation")
        );
    }

    @Test
    void declineRetryUsesSameTitleFreeInvitationFlow() {
        assertEquals(
            List.of(
                "wait " + CaveEscapeQuestService.QUEST_INVITATION_RETRY_SECONDS,
                "chat " + CaveEscapeQuestService.QUEST_INVITATION_CHAT,
                "open_quiz_invitation"
            ),
            CaveEscapeQuestService.invitationRetryActionLines()
        );
    }

    @Test
    void laterMilestonesDoNotStartWithDefaultTeleports() {
        assertEquals(List.of(), CaveEscapeQuestService.defaultStartActionLines("m2_deep_passage"));
        assertEquals(List.of(), CaveEscapeQuestService.defaultStartActionLines("m3_winding_tunnel"));
        assertEquals(List.of(), CaveEscapeQuestService.defaultStartActionLines("m4_chamber"));
        assertEquals(List.of(), CaveEscapeQuestService.defaultStartActionLines("m5_connector"));
        assertEquals(List.of(), CaveEscapeQuestService.defaultStartActionLines("m6_surface_break"));
    }
}
