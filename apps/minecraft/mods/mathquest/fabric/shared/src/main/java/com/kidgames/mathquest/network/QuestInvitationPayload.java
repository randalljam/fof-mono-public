package com.kidgames.mathquest.network;

import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.ByteBufCodecs;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.resources.Identifier;

/** S2C: show Quest 01 knowledge invitation with Accept / Decline buttons. */
public record QuestInvitationPayload(
    String message,
    String subtitle,
    String operation,
    int minNumber,
    int maxNumber,
    int problemsPerQuiz,
    String problemsJson,
    String rewardsJson,
    String rewardMode,
    String quizType,
    String optionsJson
) implements CustomPacketPayload {
    public static final CustomPacketPayload.Type<QuestInvitationPayload> ID =
        new CustomPacketPayload.Type<>(Identifier.fromNamespaceAndPath("mathquest", "quest_invitation"));

    public static final StreamCodec<RegistryFriendlyByteBuf, QuestInvitationPayload> CODEC =
        StreamCodec.composite(
            ByteBufCodecs.STRING_UTF8, QuestInvitationPayload::message,
            ByteBufCodecs.STRING_UTF8, QuestInvitationPayload::subtitle,
            ByteBufCodecs.STRING_UTF8, QuestInvitationPayload::operation,
            ByteBufCodecs.VAR_INT, QuestInvitationPayload::minNumber,
            ByteBufCodecs.VAR_INT, QuestInvitationPayload::maxNumber,
            ByteBufCodecs.VAR_INT, QuestInvitationPayload::problemsPerQuiz,
            ByteBufCodecs.STRING_UTF8, QuestInvitationPayload::problemsJson,
            ByteBufCodecs.STRING_UTF8, QuestInvitationPayload::rewardsJson,
            ByteBufCodecs.STRING_UTF8, QuestInvitationPayload::rewardMode,
            ByteBufCodecs.STRING_UTF8, QuestInvitationPayload::quizType,
            ByteBufCodecs.STRING_UTF8, QuestInvitationPayload::optionsJson,
            QuestInvitationPayload::new
        );

    public OpenQuizPayload openQuizPayload() {
        return new OpenQuizPayload(
            operation,
            minNumber,
            maxNumber,
            problemsPerQuiz,
            problemsJson,
            rewardsJson,
            rewardMode,
            quizType,
            optionsJson,
            false,
            true
        );
    }

    @Override
    public Type<? extends CustomPacketPayload> type() {
        return ID;
    }
}
