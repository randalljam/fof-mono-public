package com.kidgames.mathquest.control;

import com.kidgames.mathquest.control.http.ControlPanelBridge;
import com.kidgames.mathquest.control.http.MathQuestHttpControlPanelServer;
import com.kidgames.mathquest.control.http.MathQuestHttpRouter;
import net.minecraft.server.MinecraftServer;

/** Starts/stops the shared HTTP control panel on Fabric dedicated servers. */
public final class FabricControlPanelLifecycle {
    private final MathQuestHttpControlPanelServer httpServer = new MathQuestHttpControlPanelServer();
    private MathQuestHttpRouter router;

    public void start(MinecraftServer server) {
        ControlPanelBridge bridge = new FabricControlPanelBridge(server);
        router = new MathQuestHttpRouter(bridge, FabricControlPanelLifecycle.class.getClassLoader());
        // FROZEN: quest + terrain-map + mob admin routes deferred past M6 tooling decision — Fabric-only optional handlers.
        FabricControlPanelOptionalRoutes.register(router, bridge);
        httpServer.start(bridge.config(), router);
    }

    public void stop() {
        httpServer.stop();
        router = null;
    }
}
