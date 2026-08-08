package com.kidgames.mathquest.platform;

import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/** Tracks Fabric ServerPlayer handles on PlayerContext via a thread-local side map. */
public final class FabricPlatformPlayers {
    private static final ThreadLocal<PlayerHandle> CURRENT = new ThreadLocal<>();

    private FabricPlatformPlayers() {}

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

    public static final class FabricPlatformServer implements PlatformServer {
        private final MinecraftServer server;

        public FabricPlatformServer(MinecraftServer server) {
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
