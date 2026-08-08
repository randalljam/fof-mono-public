package com.kidgames.mathquest.network;

import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.ByteBufCodecs;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.resources.Identifier;

public record QuizResultPayload(String resultJson) implements CustomPacketPayload {
    public static final CustomPacketPayload.Type<QuizResultPayload> ID =
        new CustomPacketPayload.Type<>(Identifier.fromNamespaceAndPath("mathquest", "quiz_result"));

    public static final StreamCodec<RegistryFriendlyByteBuf, QuizResultPayload> CODEC =
        StreamCodec.composite(
            ByteBufCodecs.STRING_UTF8, QuizResultPayload::resultJson,
            QuizResultPayload::new
        );

    @Override
    public Type<? extends CustomPacketPayload> type() {
        return ID;
    }
}
