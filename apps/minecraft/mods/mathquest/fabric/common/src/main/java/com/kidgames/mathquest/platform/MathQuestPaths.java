package com.kidgames.mathquest.platform;

import java.nio.file.Path;

public final class MathQuestPaths {
    private static Path configDir;
    private static String modVersion = "unknown";

    private MathQuestPaths() {}

    public static void setConfigDir(Path dir) {
        configDir = dir;
    }

    public static void setModVersion(String version) {
        if (version != null && !version.isBlank()) {
            modVersion = version.trim();
        }
    }

    public static String modVersion() {
        return modVersion;
    }

    /** Bottom-left title-screen label, e.g. {@code MathQuest 1.18.6 + MC 1.20.1}. */
    public static String titleScreenVersionLabel(String minecraftVersion) {
        String label = "MathQuest " + modVersion;
        if (minecraftVersion != null && !minecraftVersion.isBlank()) {
            label += " + MC " + minecraftVersion.trim();
        }
        return label;
    }

    public static Path configDir() {
        if (configDir == null) {
            throw new IllegalStateException(
                "MathQuestPaths.configDir not set — call setConfigDir from the loader entrypoint first.");
        }
        return configDir;
    }

    public static Path sessionsDir() {
        return configDir().resolve("mathquest_sessions");
    }
}
