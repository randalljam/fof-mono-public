package com.kidgames.mathquest.forge.platform;

import com.kidgames.mathquest.platform.MathQuestLog;
import com.kidgames.mathquest.platform.PlatformInventory;
import com.kidgames.mathquest.platform.PlayerContext;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.registries.ForgeRegistries;

public final class ForgePlatformInventory implements PlatformInventory {
    @Override
    public void grantReward(PlayerContext player, String itemId, int count) {
        ServerPlayer serverPlayer = ForgePlatformPlayers.asServerPlayer(player);
        if (serverPlayer == null) return;
        ResourceLocation id = ResourceLocation.tryParse(itemId);
        if (id == null) {
            MathQuestLog.LOGGER.warn("[MathQuest/Forge] Invalid reward item id: {}", itemId);
            return;
        }
        Item item = ForgeRegistries.ITEMS.getValue(id);
        if (item == null) {
            MathQuestLog.LOGGER.warn("[MathQuest/Forge] Unknown reward item: {}", itemId);
            return;
        }
        ItemStack stack = new ItemStack(item, Math.max(1, count));
        serverPlayer.getInventory().add(stack);
    }
}
