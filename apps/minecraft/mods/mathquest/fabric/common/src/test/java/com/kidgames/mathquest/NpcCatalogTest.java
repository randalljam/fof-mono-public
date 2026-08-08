package com.kidgames.mathquest;

import com.kidgames.mathquest.npc.MathQuestNpcCatalog;
import org.junit.jupiter.api.Test;

import java.util.Set;
import java.util.stream.Collectors;

import static org.junit.jupiter.api.Assertions.*;

public class NpcCatalogTest {
    @Test
    void includesSelectableNpcGalleryEntries() {
        Set<String> ids = MathQuestNpcCatalog.all().stream()
            .map(MathQuestNpcCatalog.NpcDef::id)
            .collect(Collectors.toSet());
        assertEquals(Set.of("wandering_nerd", "professor_pi", "countess_calc", "geo_sage", "paper_coach"), ids);
    }
    @Test
    void everyNpcHasTextureAndSingleLineDialogue() {
        for (MathQuestNpcCatalog.NpcDef npc : MathQuestNpcCatalog.all()) {
            assertFalse(npc.name().isBlank());
            assertEquals(npc.name(), npc.entity());
            assertTrue(npc.texturePath().startsWith("textures/entity/"));
            assertTrue(npc.texturePath().endsWith(".png"));
            assertFalse(npc.dialogueLines().isEmpty());
            for (String line : npc.dialogueLines()) {
                assertFalse(line.isBlank());
                assertFalse(line.contains("\n"));
            }
        }
    }
    @Test
    void unknownNpcFallsBackToWanderingNerd() {
        assertEquals("wandering_nerd", MathQuestNpcCatalog.byId("missing").id());
        assertEquals("wandering_nerd", MathQuestNpcCatalog.byId(null).id());
    }
}
