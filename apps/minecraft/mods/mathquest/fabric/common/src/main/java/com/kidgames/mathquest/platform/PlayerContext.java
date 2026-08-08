package com.kidgames.mathquest.platform;

import java.util.UUID;

/** Loader-neutral player identity passed into common server logic. */
public record PlayerContext(String username, UUID playerUuid) {
    public PlayerContext(String username) {
        this(username, null);
    }
}
