package net.minecraft.network.codec;

import java.util.function.Function;

public interface PacketCodec<B, T> {
    @SuppressWarnings("unchecked")
    static <B, T, F1, F2> PacketCodec<B, T> tuple(
        PacketCodec<? super B, F1> c1, Function<T, F1> g1,
        PacketCodec<? super B, F2> c2, Function<T, F2> g2,
        java.util.function.BiFunction<F1, F2, T> factory
    ) {
        return (PacketCodec<B, T>) new PacketCodec<Object, Object>() {};
    }
}
