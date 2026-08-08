package com.kidgames.mathquest.platform;

/** Loader-specific inventory grant hook used by shared server logic. */
public interface PlatformInventory {
    void grantReward(PlayerContext player, String itemId, int count);
}
