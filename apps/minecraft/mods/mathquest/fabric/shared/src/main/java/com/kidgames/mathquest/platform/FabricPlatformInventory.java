package com.kidgames.mathquest.platform;

import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.Identifier;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;

public final class FabricPlatformInventory implements PlatformInventory {
    @Override
    public void grantReward(PlayerContext player, String itemId, int count) {
        ServerPlayer serverPlayer = FabricPlatformPlayers.asServerPlayer(player);
        if (serverPlayer == null) return;
        try {
            Identifier id = Identifier.parse(itemId);
            Item item = BuiltInRegistries.ITEM.getValue(id);
            if (item != null) {
                ItemStack stack = new ItemStack(item, count);
                serverPlayer.getInventory().placeItemBackInInventory(stack);
            }
        } catch (Exception e) {
            com.kidgames.mathquest.platform.MathQuestLog.LOGGER.error(
                "[MathQuest] Failed to give reward item {}: {}", itemId, e.getMessage());
        }
    }
}
