package com.kidgames.mathquest.network;

import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.resources.Identifier;

public record DespawnNerdsPayload() implements CustomPacketPayload {
    public static final CustomPacketPayload.Type<DespawnNerdsPayload> ID =
        new CustomPacketPayload.Type<>(Identifier.fromNamespaceAndPath("mathquest", "despawn_nerds"));

    public static final StreamCodec<RegistryFriendlyByteBuf, DespawnNerdsPayload> CODEC =
        StreamCodec.unit(new DespawnNerdsPayload());

    @Override
    public Type<? extends CustomPacketPayload> type() {
        return ID;
    }
}
