package com.kidgames.mathquest;

import com.kidgames.mathquest.control.http.MathQuestHttpAssets;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.*;

class ControlPanelStaticRoutesTest {
    @TempDir
    Path tempDir;
    @Test
    void mapsControlPanelUrlsToAssetPaths() {
        assertAsset("/", "control_panel/index.html", "text/html; charset=utf-8");
        assertAsset("/index.html", "control_panel/index.html", "text/html; charset=utf-8");
        assertAsset("/mob-spawn.html", "control_panel/mob-spawn.html", "text/html; charset=utf-8");
        assertAsset("/quest.html", "control_panel/quest.html", "text/html; charset=utf-8");
        assertAsset("/control-panel.js", "control_panel/control-panel.js", "application/javascript; charset=utf-8");
        assertAsset("/quest.js", "control_panel/quest.js", "application/javascript; charset=utf-8");
        assertAsset("/control-panel.css", "control_panel/control-panel.css", "text/css; charset=utf-8");
        assertAsset("/npc/wandering_nerd.png", "textures/entity/wandering_nerd.png", "image/png");
    }
    @Test
    void rejectsTraversalAndNestedUnexpectedUrls() {
        assertNull(MathQuestHttpAssets.staticAsset("/../control-panel.js"));
        assertNull(MathQuestHttpAssets.staticAsset("/control_panel/control-panel.js"));
        assertNull(MathQuestHttpAssets.staticAsset("/npc/../../secret.png"));
        assertNull(MathQuestHttpAssets.staticAsset("//control-panel.js"));
        assertNull(MathQuestHttpAssets.staticAsset("/control-panel.exe"));
    }
    @Test
    void safeResolveKeepsPathsInsideAssetRoot() {
        Path inside = MathQuestHttpAssets.safeResolve(tempDir, "control_panel/index.html");
        assertNotNull(inside);
        assertTrue(inside.startsWith(tempDir.toAbsolutePath().normalize()));
        assertNull(MathQuestHttpAssets.safeResolve(tempDir, "../secret.txt"));
    }
    private void assertAsset(String url, String expectedPath, String expectedType) {
        MathQuestHttpAssets.StaticAsset asset = MathQuestHttpAssets.staticAsset(url);
        assertNotNull(asset);
        assertEquals(expectedPath, asset.relativePath());
        assertEquals(expectedType, asset.contentType());
    }
}
