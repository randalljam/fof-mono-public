package com.kidgames.mathquest.control.http;

import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.platform.MathQuestLog;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.file.Path;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Shared localhost HTTP control panel server (JDK HttpServer + common router). */
public final class MathQuestHttpControlPanelServer {
    private HttpServer httpServer;
    private ExecutorService executor;

    public void start(MathQuestConfig config, MathQuestHttpRouter router) {
        if (!config.controlPanelEnabled) return;
        if (httpServer != null) return;
        try {
            String host = config.controlPanelHost == null || config.controlPanelHost.isBlank()
                ? "127.0.0.1"
                : config.controlPanelHost;
            int port = config.controlPanelPort > 0 ? config.controlPanelPort : 8765;
            httpServer = HttpServer.create(new InetSocketAddress(host, port), 0);
            httpServer.createContext("/", ex -> {
                try {
                    router.handle(ex);
                } catch (Exception e) {
                    MathQuestHttpUtil.sendError(ex, 500, e.getMessage());
                }
            });
            executor = Executors.newCachedThreadPool();
            httpServer.setExecutor(executor);
            httpServer.start();
            MathQuestLog.LOGGER.info("[MathQuest] Local control panel: http://{}:{}/", host, port);
            Path assetsDir = config.resolveControlPanelAssetsDir();
            if (assetsDir != null) {
                MathQuestLog.LOGGER.info("[MathQuest] Control panel disk assets: {}", assetsDir);
            } else if (config.controlPanelAssetsDir != null && !config.controlPanelAssetsDir.isBlank()) {
                MathQuestLog.LOGGER.warn(
                    "[MathQuest] controlPanelAssetsDir '{}' is not a readable directory; using jar assets",
                    config.controlPanelAssetsDir);
            } else {
                MathQuestLog.LOGGER.info("[MathQuest] Control panel using bundled jar assets");
            }
        } catch (IOException e) {
            MathQuestLog.LOGGER.error("[MathQuest] Failed to start local control panel: {}", e.getMessage());
        }
    }

    public void stop() {
        if (httpServer != null) {
            httpServer.stop(0);
            httpServer = null;
        }
        if (executor != null) {
            executor.shutdownNow();
            executor = null;
        }
    }
}
