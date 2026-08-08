package net.fabricmc.fabric.api.networking.v1;

import net.minecraft.network.packet.CustomPayload;
import net.minecraft.server.network.ServerPlayerEntity;

public class ServerPlayNetworking {
    public static <T extends CustomPayload> boolean registerGlobalReceiver(
            CustomPayload.Id<T> type, PlayPayloadHandler<T> handler) {
        return true;
    }

    @FunctionalInterface
    public interface PlayPayloadHandler<T extends CustomPayload> {
        void receive(T payload, Context context);
    }

    public interface Context {
        ServerPlayerEntity player();
    }
}
