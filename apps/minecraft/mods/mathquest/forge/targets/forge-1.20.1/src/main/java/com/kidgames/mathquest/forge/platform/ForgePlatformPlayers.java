package com.kidgames.mathquest.forge.platform;

import com.kidgames.mathquest.platform.PlatformServer;
import com.kidgames.mathquest.platform.PlayerContext;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;

import java.util.ArrayList;
import java.util.List;

public final class ForgePlatformPlayers {
    private static final ThreadLocal<PlayerHandle> CURRENT = new ThreadLocal<>();
    private static MinecraftServer boundServer;

    private ForgePlatformPlayers() {}

    public static void bindServer(MinecraftServer server) {
        boundServer = server;
    }

    public static ServerPlayer lookupOnline(String username) {
        if (boundServer == null || username == null) return null;
        return boundServer.getPlayerList().getPlayerByName(username);
    }

    public static PlayerContext fromServerPlayer(ServerPlayer player) {
        if (player == null) return new PlayerContext("unknown");
        PlayerContext context = new PlayerContext(player.getName().getString(), player.getUUID());
        CURRENT.set(new PlayerHandle(context, player));
        return context;
    }

    public static ServerPlayer asServerPlayer(PlayerContext context) {
        PlayerHandle handle = CURRENT.get();
        if (handle != null && handle.context().equals(context)) {
            return handle.player();
        }
        return null;
    }

    public static PlayerContext contextFor(ServerPlayer player) {
        return new PlayerContext(player.getName().getString(), player.getUUID());
    }

    public static final class ForgePlatformServer implements PlatformServer {
        private final MinecraftServer server;

        public ForgePlatformServer(MinecraftServer server) {
            this.server = server;
        }

        @Override
        public void runOnServerThread(Runnable task) {
            server.execute(task);
        }

        @Override
        public List<PlayerContext> onlinePlayers() {
            List<PlayerContext> players = new ArrayList<>();
            for (ServerPlayer player : server.getPlayerList().getPlayers()) {
                players.add(contextFor(player));
            }
            return players;
        }

        @Override
        public PlayerContext findOnlinePlayer(String name) {
            ServerPlayer player = server.getPlayerList().getPlayerByName(name);
            return player == null ? null : contextFor(player);
        }
    }

    private record PlayerHandle(PlayerContext context, ServerPlayer player) {}
}
