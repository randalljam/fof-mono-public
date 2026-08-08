package com.kidgames.mathquest.platform;

import java.util.List;

/** Loader-specific server-thread and player-list hooks for shared server logic. */
public interface PlatformServer {
    void runOnServerThread(Runnable task);
    List<PlayerContext> onlinePlayers();
    PlayerContext findOnlinePlayer(String name);
}
