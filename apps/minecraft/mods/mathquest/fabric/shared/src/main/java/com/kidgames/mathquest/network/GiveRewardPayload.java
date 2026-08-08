package com.kidgames.mathquest.network;

import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.ByteBufCodecs;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.resources.Identifier;

public record GiveRewardPayload(String itemId, int count) implements CustomPacketPayload {
    public static final CustomPacketPayload.Type<GiveRewardPayload> ID =
        new CustomPacketPayload.Type<>(Identifier.fromNamespaceAndPath("mathquest", "give_reward"));

    public static final StreamCodec<RegistryFriendlyByteBuf, GiveRewardPayload> CODEC =
        StreamCodec.composite(
            ByteBufCodecs.STRING_UTF8, GiveRewardPayload::itemId,
            ByteBufCodecs.VAR_INT, GiveRewardPayload::count,
            GiveRewardPayload::new
        );

    @Override
    public Type<? extends CustomPacketPayload> type() {
        return ID;
    }
}
