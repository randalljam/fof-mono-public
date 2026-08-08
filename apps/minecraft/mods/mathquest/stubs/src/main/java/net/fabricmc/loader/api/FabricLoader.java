package net.fabricmc.loader.api;

import java.nio.file.Path;
import java.nio.file.Paths;

public class FabricLoader {
    private static final FabricLoader INSTANCE = new FabricLoader();

    public static FabricLoader getInstance() {
        return INSTANCE;
    }

    public Path getConfigDir() {
        return Paths.get(System.getProperty("java.io.tmpdir"), "mathquest-config");
    }
}
