package net.fabricmc.fabric.api.client.command.v2;

import com.mojang.brigadier.CommandDispatcher;

public class ClientCommandRegistrationCallback {
    public static final ClientCommandRegistrationCallback EVENT = new ClientCommandRegistrationCallback();

    public void register(Handler handler) {}

    @FunctionalInterface
    public interface Handler {
        void register(CommandDispatcher<FabricClientCommandSource> dispatcher, Object registryAccess);
    }
}
