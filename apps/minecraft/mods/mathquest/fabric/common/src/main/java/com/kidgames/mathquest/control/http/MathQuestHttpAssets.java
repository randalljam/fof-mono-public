package com.kidgames.mathquest.control.http;

import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.npc.MathQuestNpcCatalog;
import com.sun.net.httpserver.HttpExchange;

import java.io.IOException;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Locale;

public final class MathQuestHttpAssets {
    public static final String ASSET_CLASSPATH_ROOT = "assets/mathquest";

    private MathQuestHttpAssets() {}

    public record StaticAsset(String relativePath, String contentType) {}

    public static StaticAsset staticAsset(String urlPath) {
        if (urlPath == null || urlPath.isBlank()) return null;
        String path = URLDecoder.decode(urlPath, StandardCharsets.UTF_8);
        if (path.contains("..") || path.contains("\\") || path.startsWith("//")) return null;
        if ("/".equals(path) || "/index.html".equals(path)) {
            return new StaticAsset("control_panel/index.html", "text/html; charset=utf-8");
        }
        if (path.startsWith("/npc/") && path.endsWith(".png")) {
            String id = path.substring("/npc/".length(), path.length() - ".png".length());
            if (!id.matches("[a-z0-9_\\-]+")) return null;
            MathQuestNpcCatalog.NpcDef npc = MathQuestNpcCatalog.byId(id);
            return new StaticAsset(npc.texturePath(), "image/png");
        }
        if (!path.startsWith("/") || path.indexOf('/', 1) >= 0) return null;
        String name = path.substring(1);
        if (!name.matches("[A-Za-z0-9_.-]+")) return null;
        return switch (extension(name)) {
            case "html" -> new StaticAsset("control_panel/" + name, "text/html; charset=utf-8");
            case "css" -> new StaticAsset("control_panel/" + name, "text/css; charset=utf-8");
            case "js" -> new StaticAsset("control_panel/" + name, "application/javascript; charset=utf-8");
            case "png" -> new StaticAsset("control_panel/" + name, "image/png");
            case "svg" -> new StaticAsset("control_panel/" + name, "image/svg+xml");
            default -> null;
        };
    }

    public static Path safeResolve(Path root, String relativePath) {
        if (root == null || relativePath == null || relativePath.isBlank()) return null;
        Path base = root.toAbsolutePath().normalize();
        Path resolved = base.resolve(relativePath).normalize();
        return resolved.startsWith(base) ? resolved : null;
    }

    public static void sendStatic(HttpExchange ex, MathQuestConfig config, ClassLoader classLoader, String urlPath) throws IOException {
        StaticAsset asset = staticAsset(urlPath);
        if (asset == null) {
            MathQuestHttpUtil.sendError(ex, 404, "Not found");
            return;
        }
        Path assetsDir = config.resolveControlPanelAssetsDir();
        if (assetsDir != null) {
            Path diskPath = safeResolve(assetsDir, asset.relativePath());
            if (diskPath != null && Files.isRegularFile(diskPath)) {
                MathQuestHttpUtil.sendBytes(ex, 200, Files.readAllBytes(diskPath), asset.contentType());
                return;
            }
        }
        MathQuestHttpUtil.sendResource(ex, classLoader, ASSET_CLASSPATH_ROOT + "/" + asset.relativePath(), asset.contentType());
    }

    private static String extension(String name) {
        int idx = name.lastIndexOf('.');
        return idx < 0 ? "" : name.substring(idx + 1).toLowerCase(Locale.ROOT);
    }
}
