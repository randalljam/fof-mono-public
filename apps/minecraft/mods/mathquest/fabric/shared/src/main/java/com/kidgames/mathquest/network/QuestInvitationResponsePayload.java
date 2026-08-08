package com.kidgames.mathquest.network;

import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.ByteBufCodecs;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.resources.Identifier;

/** C2S: learner accepted or declined a Quest 01 knowledge invitation. */
public record QuestInvitationResponsePayload(boolean accepted) implements CustomPacketPayload {
    public static final CustomPacketPayload.Type<QuestInvitationResponsePayload> ID =
        new CustomPacketPayload.Type<>(Identifier.fromNamespaceAndPath("mathquest", "quest_invitation_response"));

    public static final StreamCodec<RegistryFriendlyByteBuf, QuestInvitationResponsePayload> CODEC =
        StreamCodec.composite(
            ByteBufCodecs.BOOL, QuestInvitationResponsePayload::accepted,
            QuestInvitationResponsePayload::new
        );

    @Override
    public Type<? extends CustomPacketPayload> type() {
        return ID;
    }
}
