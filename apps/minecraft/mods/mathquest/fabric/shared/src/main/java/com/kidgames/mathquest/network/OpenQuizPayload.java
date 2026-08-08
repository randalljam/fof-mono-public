package com.kidgames.mathquest.network;

import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.ByteBufCodecs;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.resources.Identifier;

public record OpenQuizPayload(
    String operation,
    int minNumber,
    int maxNumber,
    int problemsPerQuiz,
    String problemsJson,
    String rewardsJson,
    String rewardMode,
    String quizType,
    String optionsJson,
    boolean fluencyFeastMode,
    boolean directToQuiz
) implements CustomPacketPayload {
    public static final CustomPacketPayload.Type<OpenQuizPayload> ID =
        new CustomPacketPayload.Type<>(Identifier.fromNamespaceAndPath("mathquest", "open_quiz"));

    public static final StreamCodec<RegistryFriendlyByteBuf, OpenQuizPayload> CODEC =
        StreamCodec.composite(
            ByteBufCodecs.STRING_UTF8, OpenQuizPayload::operation,
            ByteBufCodecs.VAR_INT, OpenQuizPayload::minNumber,
            ByteBufCodecs.VAR_INT, OpenQuizPayload::maxNumber,
            ByteBufCodecs.VAR_INT, OpenQuizPayload::problemsPerQuiz,
            ByteBufCodecs.STRING_UTF8, OpenQuizPayload::problemsJson,
            ByteBufCodecs.STRING_UTF8, OpenQuizPayload::rewardsJson,
            ByteBufCodecs.STRING_UTF8, OpenQuizPayload::rewardMode,
            ByteBufCodecs.STRING_UTF8, OpenQuizPayload::quizType,
            ByteBufCodecs.STRING_UTF8, OpenQuizPayload::optionsJson,
            ByteBufCodecs.BOOL, OpenQuizPayload::fluencyFeastMode,
            ByteBufCodecs.BOOL, OpenQuizPayload::directToQuiz,
            OpenQuizPayload::new
        );

    @Override
    public Type<? extends CustomPacketPayload> type() {
        return ID;
    }
}
