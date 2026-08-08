package com.kidgames.mathquest.persistence;

import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.*;

class FluencyFeastBridgeTest {
    @Test
    void resolveExecutableOnPathFindsNodeInCommonMacLocations() {
        Path node = FluencyFeastBridge.resolveExecutableOnPath("node");
        assertNotNull(node, "expected node under /usr/local/bin or PATH");
        assertTrue(Files.isExecutable(node));
    }

    @Test
    void parseBridgeResponseReadsRootObjectWhenNestedObjectsPresent() {
        String stdout = """
            {"ok":true,"problems":["7 + 2"],"counts":{"yellow":2,"red":2},"poolSizes":{"green":27,"yellow":47,"red":18,"gray":1,"nodata":7},"warnings":["Only 3 of 8 \\"gray\\" slots filled."]}
            """;
        var resp = FluencyFeastBridge.parseBridgeResponse(stdout);
        assertNotNull(resp);
        assertTrue(resp.get("ok").getAsBoolean());
        assertEquals(1, resp.getAsJsonArray("problems").size());
        assertTrue(resp.getAsJsonObject("poolSizes").has("green"));
    }

    @Test
    void parseBridgeResponseUsesLastJsonLineWhenWarningsPrecedeIt() {
        String stdout = "(node:123) ExperimentalWarning: something\n{\"ok\":true,\"percent\":42}\n";
        var resp = FluencyFeastBridge.parseBridgeResponse(stdout);
        assertNotNull(resp);
        assertTrue(resp.get("ok").getAsBoolean());
        assertEquals(42, resp.get("percent").getAsInt());
    }
}
