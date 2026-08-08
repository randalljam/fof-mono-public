package com.kidgames.mathquest.persistence;

import java.nio.file.Path;
import java.util.Optional;

/** Optional loader hooks for MathQuizSessionIngestor (quest active-file lookup, post-ingest refresh). */
public interface SessionIngestHooks {
    Optional<Path> exactActiveFile(String realName);
    void afterIngest(String realName, Path activePath);

    SessionIngestHooks NONE = new SessionIngestHooks() {
        @Override
        public Optional<Path> exactActiveFile(String realName) {
            return Optional.empty();
        }

        @Override
        public void afterIngest(String realName, Path activePath) {}
    };
}
