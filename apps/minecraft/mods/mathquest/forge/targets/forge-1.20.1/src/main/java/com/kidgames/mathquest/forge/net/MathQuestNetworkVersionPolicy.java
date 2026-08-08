package com.kidgames.mathquest.forge.net;

import net.minecraftforge.network.NetworkRegistry;

import java.util.function.Predicate;

final class MathQuestNetworkVersionPolicy {
    private MathQuestNetworkVersionPolicy() {}

    static Predicate<String> serverAcceptedVersions(String protocol) {
        return NetworkRegistry.acceptMissingOr(protocol);
    }
}
