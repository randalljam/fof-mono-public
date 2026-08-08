package com.kidgames.mathquest.forge.control;

import com.kidgames.mathquest.control.http.ControlPanelBridge;
import com.kidgames.mathquest.control.http.MathQuestHttpControlPanelServer;
import com.kidgames.mathquest.control.http.MathQuestHttpRouter;
import net.minecraft.server.MinecraftServer;

/** Starts/stops the shared HTTP control panel on Forge (core routes only — no quest/terrain/mob). */
public final class ForgeControlPanelLifecycle {
    private final MathQuestHttpControlPanelServer httpServer = new MathQuestHttpControlPanelServer();
    private MathQuestHttpRouter router;

    public void start(MinecraftServer server) {
        ControlPanelBridge bridge = new ForgeControlPanelBridge(server);
        router = new MathQuestHttpRouter(bridge, ForgeControlPanelLifecycle.class.getClassLoader());
        httpServer.start(bridge.config(), router);
    }

    public void stop() {
        httpServer.stop();
        router = null;
    }
}
