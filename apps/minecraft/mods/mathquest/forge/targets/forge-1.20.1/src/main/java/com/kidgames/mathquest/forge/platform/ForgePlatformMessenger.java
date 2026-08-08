package com.kidgames.mathquest.forge.platform;

import com.kidgames.mathquest.platform.PlatformMessenger;
import com.kidgames.mathquest.platform.PlayerContext;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;

public final class ForgePlatformMessenger {
    private ForgePlatformMessenger() {}

    public static void register() {
        PlatformMessenger.setSender(ForgePlatformMessenger::send);
    }

    private static void send(PlayerContext player, String message) {
        ServerPlayer serverPlayer = ForgePlatformPlayers.asServerPlayer(player);
        if (serverPlayer == null && player != null) {
            serverPlayer = ForgePlatformPlayers.lookupOnline(player.username());
        }
        if (serverPlayer != null) {
            serverPlayer.sendSystemMessage(Component.literal(message));
        }
    }
}
