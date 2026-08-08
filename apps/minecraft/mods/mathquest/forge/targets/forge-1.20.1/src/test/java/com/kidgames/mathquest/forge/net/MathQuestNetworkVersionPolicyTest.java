package com.kidgames.mathquest.forge.net;

import net.minecraftforge.network.NetworkRegistry;
import org.junit.jupiter.api.Test;

import java.util.function.Predicate;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class MathQuestNetworkVersionPolicyTest {
    @Test
    void serverAcceptsMissingOrVanillaClientsButKeepsModdedVersionsExact() {
        Predicate<String> accepts = MathQuestNetworkVersionPolicy.serverAcceptedVersions("2");

        assertTrue(accepts.test("2"));
        assertTrue(accepts.test(NetworkRegistry.ABSENT.version()));
        assertTrue(accepts.test(NetworkRegistry.ACCEPTVANILLA));
        assertFalse(accepts.test("1"));
    }
}
