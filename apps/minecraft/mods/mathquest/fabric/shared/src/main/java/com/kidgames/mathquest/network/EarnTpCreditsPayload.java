package com.kidgames.mathquest.network;

import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.ByteBufCodecs;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.resources.Identifier;

/**
 * One-use quiz-completion request. The server resolves whether earning is enabled and
 * how many TP credits the requesting player earns; the client never supplies an amount.
 */
public record EarnTpCreditsPayload(String completionToken) implements CustomPacketPayload {
    public static final CustomPacketPayload.Type<EarnTpCreditsPayload> ID =
        new CustomPacketPayload.Type<>(Identifier.fromNamespaceAndPath("mathquest", "earn_tp_credits"));

    public static final StreamCodec<RegistryFriendlyByteBuf, EarnTpCreditsPayload> CODEC =
        StreamCodec.composite(
            ByteBufCodecs.STRING_UTF8, EarnTpCreditsPayload::completionToken,
            EarnTpCreditsPayload::new
        );

    @Override
    public Type<? extends CustomPacketPayload> type() {
        return ID;
    }
}
