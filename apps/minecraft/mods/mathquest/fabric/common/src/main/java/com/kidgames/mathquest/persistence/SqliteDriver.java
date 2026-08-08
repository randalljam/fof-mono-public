package com.kidgames.mathquest.persistence;

import com.kidgames.mathquest.platform.MathQuestLog;

/** Ensures sqlite-jdbc is loadable before QuizDatabase / SessionExporter use JDBC. */
public final class SqliteDriver {
    private static boolean loaded;
    private static String loadError;

    private SqliteDriver() {}

    public static boolean isAvailable() {
        ensureLoaded();
        return loaded;
    }

    public static void requireLoaded() {
        ensureLoaded();
        if (!loaded) {
            throw new IllegalStateException(
                "sqlite-jdbc driver is not on the classpath"
                + (loadError != null ? ": " + loadError : "")
                + ". Forge builds must deploy the jarJar artifact (-all.jar) that bundles org.xerial:sqlite-jdbc.");
        }
    }

    public static void ensureLoaded() {
        if (loaded) return;
        loadError = null;
        try {
            ClassLoader loader = Thread.currentThread().getContextClassLoader();
            if (loader == null) {
                loader = SqliteDriver.class.getClassLoader();
            }
            Class.forName("org.sqlite.JDBC", true, loader);
            loaded = true;
        } catch (ClassNotFoundException e) {
            loadError = e.getMessage();
            MathQuestLog.LOGGER.error("[MathQuest] sqlite-jdbc driver not found on classpath: {}", e.getMessage());
        }
    }

    /** Resets cached driver state (tests only). */
    public static void resetForTests() {
        loaded = false;
        loadError = null;
    }
}
