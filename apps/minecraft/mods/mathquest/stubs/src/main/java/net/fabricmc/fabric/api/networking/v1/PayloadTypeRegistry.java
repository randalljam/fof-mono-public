package net.fabricmc.fabric.api.networking.v1;

import net.minecraft.network.codec.PacketCodec;
import net.minecraft.network.packet.CustomPayload;

public class PayloadTypeRegistry<B> {
    private static final PayloadTypeRegistry<?> INSTANCE = new PayloadTypeRegistry<>();

    @SuppressWarnings("unchecked")
    public static <B> PayloadTypeRegistry<B> playC2S() {
        return (PayloadTypeRegistry<B>) INSTANCE;
    }

    @SuppressWarnings("unchecked")
    public static <B> PayloadTypeRegistry<B> playS2C() {
        return (PayloadTypeRegistry<B>) INSTANCE;
    }

    public <T extends CustomPayload> void register(CustomPayload.Id<T> id, PacketCodec<? super B, T> codec) {}
}
