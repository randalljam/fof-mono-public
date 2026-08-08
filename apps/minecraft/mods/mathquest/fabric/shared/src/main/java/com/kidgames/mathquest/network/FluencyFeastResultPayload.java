package com.kidgames.mathquest.network;

import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.ByteBufCodecs;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.resources.Identifier;

/** S2C: fluency before/after readout and reward summary for fluency-feast quizzes. */
public record FluencyFeastResultPayload(
    int beforePercent,
    int afterPercent,
    String rewardDescription,
    String rewardsJson,
    String rewardMode
) implements CustomPacketPayload {
    public static final CustomPacketPayload.Type<FluencyFeastResultPayload> ID =
        new CustomPacketPayload.Type<>(Identifier.fromNamespaceAndPath("mathquest", "fluency_feast_result"));

    public static final StreamCodec<RegistryFriendlyByteBuf, FluencyFeastResultPayload> CODEC =
        StreamCodec.composite(
            ByteBufCodecs.VAR_INT, FluencyFeastResultPayload::beforePercent,
            ByteBufCodecs.VAR_INT, FluencyFeastResultPayload::afterPercent,
            ByteBufCodecs.STRING_UTF8, FluencyFeastResultPayload::rewardDescription,
            ByteBufCodecs.STRING_UTF8, FluencyFeastResultPayload::rewardsJson,
            ByteBufCodecs.STRING_UTF8, FluencyFeastResultPayload::rewardMode,
            FluencyFeastResultPayload::new
        );

    public FluencyFeastResultPayload(int beforePercent, int afterPercent, String rewardDescription) {
        this(beforePercent, afterPercent, rewardDescription, "[]", "all");
    }

    @Override
    public Type<? extends CustomPacketPayload> type() {
        return ID;
    }
}
