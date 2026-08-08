package net.fabricmc.fabric.api.client.event.lifecycle.v1;

import net.minecraft.client.MinecraftClient;

public class ClientTickEvents {
    public static final Event END_CLIENT_TICK = new Event();

    public static class Event {
        public void register(ClientTickCallback callback) {}
    }

    @FunctionalInterface
    public interface ClientTickCallback {
        void onEndTick(MinecraftClient client);
    }
}
