package com.kidgames.mathquest;

import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.platform.MathQuestPaths;

import java.nio.file.Files;
import java.nio.file.Path;

final class MathQuestPathsTestHelper {
    private MathQuestPathsTestHelper() {}

    static void initConfig(Path configDir, Path exportDir) throws Exception {
        MathQuestConfig.resetConfigFileStateForTests();
        Files.createDirectories(configDir);
        Files.createDirectories(exportDir);
        MathQuestPaths.setConfigDir(configDir);
        MathQuestConfig config = new MathQuestConfig();
        config.mathQuizSingleDbDir = exportDir.toString();
        config.sharedDataDir = configDir.resolve("data").toString();
        config.save();
        MathQuestConfig.INSTANCE = MathQuestConfig.load();
    }
}
