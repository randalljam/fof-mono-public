package com.kidgames.mathquest.forge.entity;

import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.control.MathQuestControlState;
import com.kidgames.mathquest.npc.MathQuestNpcCatalog;
import com.kidgames.mathquest.npc.NpcSpawnPlanner;
import com.kidgames.mathquest.platform.MathQuestLog;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.levelgen.Heightmap;

import java.util.List;
import java.util.Locale;

public class WanderingNerdSpawnerForge {
    private int tickCounter = 0;

    public void tick(ServerLevel world) {
        if (!MathQuestConfig.INSTANCE.enabled) return;
        if (!"npc".equals(MathQuestConfig.INSTANCE.quizMode)) return;
        if (!MathQuestConfig.INSTANCE.npcAutomaticSpawnEnabled) return;

        tickCounter++;
        int intervalTicks = MathQuestConfig.INSTANCE.quizIntervalSeconds * 20;

        if (tickCounter >= intervalTicks) {
            tickCounter = 0;
            List<ServerPlayer> players = world.players();
            if (players.isEmpty()) return;

            String targetMode = MathQuestConfig.normalizeNpcSpawnTargetMode(MathQuestConfig.INSTANCE.npcSpawnTargetMode);
            List<String> playerNames = players.stream()
                .map(p -> p.getName().getString())
                .toList();
            int randomIndex = world.getRandom().nextInt(Math.max(1, playerNames.size()));
            List<String> targets = NpcSpawnPlanner.selectTargetNames(
                targetMode,
                playerNames,
                MathQuestConfig.INSTANCE.npcSpawnTargetPlayer,
                randomIndex
            );

            for (String targetName : targets) {
                ServerPlayer player = findPlayerByName(players, targetName);
                if (player == null) continue;
                if (!MathQuestConfig.INSTANCE.npcAllowMultipleNerds && isNerdNearPlayer(world, player)) continue;
                spawnNerdNearPlayer(world, player);
            }
        }
    }

    private static ServerPlayer findPlayerByName(List<ServerPlayer> players, String name) {
        String key = name.toLowerCase(Locale.ROOT);
        for (ServerPlayer p : players) {
            if (p.getName().getString().toLowerCase(Locale.ROOT).equals(key)) {
                return p;
            }
        }
        return null;
    }

    private boolean isNerdNearPlayer(ServerLevel world, ServerPlayer player) {
        int radius = MathQuestConfig.INSTANCE.npcSpawnRadiusBlocks;
        return !world.getEntities(
            MathQuestEntities.WANDERING_NERD.get(),
            player.getBoundingBox().inflate(radius),
            entity -> true
        ).isEmpty();
    }

    private void spawnNerdNearPlayer(ServerLevel world, ServerPlayer player) {
        int radius = MathQuestConfig.INSTANCE.npcSpawnRadiusBlocks;
        String npcId = MathQuestConfig.INSTANCE.resolveNpcSelection(player.getName().getString());
        spawnNerdAt(world, player, radius, npcId, MathQuestConfig.INSTANCE.resolveNpcLock(player.getName().getString()));
    }

    public boolean forceSpawn(ServerLevel world, ServerPlayer player) {
        int radius = MathQuestConfig.INSTANCE.npcSpawnRadiusBlocks;
        return forceSpawn(world, player, radius, "wandering_nerd", defaultForceSpawnLock(world, player));
    }
    public boolean forceSpawn(ServerLevel world, ServerPlayer player, int radius, String npcId, boolean lockedToTarget) {
        if (!MathQuestConfig.INSTANCE.npcAllowMultipleNerds) {
            removeAssignedNerds(world, player.getName().getString());
        }
        return spawnNerdAt(world, player, radius, npcId, lockedToTarget);
    }

    private boolean defaultForceSpawnLock(ServerLevel world, ServerPlayer player) {
        if (!world.getServer().isDedicatedServer()) return false;
        return MathQuestConfig.INSTANCE.resolveNpcLock(player.getName().getString());
    }

    private boolean spawnNerdAt(ServerLevel world, ServerPlayer player, int radius, String npcId, boolean lockedToTarget) {
        MathQuestNpcCatalog.NpcDef npc = MathQuestNpcCatalog.byId(npcId);
        RandomSource random = world.getRandom();
        int minDist = Math.min(3, radius - 1);
        if (minDist < 1) minDist = 1;
        int range = radius - minDist;
        if (range < 1) range = 1;

        for (int attempt = 0; attempt < 10; attempt++) {
            int offsetX = random.nextInt(range) + minDist;
            int offsetZ = random.nextInt(range) + minDist;
            if (random.nextBoolean()) offsetX = -offsetX;
            if (random.nextBoolean()) offsetZ = -offsetZ;

            int x = (int) player.getX() + offsetX;
            int z = (int) player.getZ() + offsetZ;
            int y = world.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, x, z);

            BlockPos pos = new BlockPos(x, y, z);

            if (!world.getBlockState(pos.below()).isRedstoneConductor(world, pos.below())) {
                continue;
            }

            WanderingNerdEntityForge nerd = MathQuestEntities.WANDERING_NERD.get().create(world);
            if (nerd != null) {
                String playerName = player.getName().getString();
                String realName = MathQuestConfig.INSTANCE.resolveRealName(playerName);
                nerd.assignToPlayer(playerName, realName, npc.id(), lockedToTarget);
                nerd.moveTo(x + 0.5, y, z + 0.5, random.nextFloat() * 360, 0);
                world.addFreshEntity(nerd);
                MathQuestControlState.markSpawned(playerName, nerd.getUUID().toString());
                MathQuestLog.LOGGER.info("[MathQuest/Forge] Spawned {} at {}, {}, {} near {}",
                    npc.name(), x, y, z, playerName);

                if (MathQuestConfig.INSTANCE.logNerdSpawn) {
                    player.sendSystemMessage(
                        Component.literal("[MathQuest] " + npc.name() + " has spawned!").withStyle(ChatFormatting.GREEN),
                        false
                    );
                }
                if (MathQuestConfig.INSTANCE.logNerdLocation) {
                    player.sendSystemMessage(
                        Component.literal("[MathQuest] " + npc.name() + " location: " + x + ", " + y + ", " + z).withStyle(ChatFormatting.AQUA),
                        false
                    );
                }
                return true;
            }
        }

        player.sendSystemMessage(
            Component.literal("[MathQuest] Failed to find a valid spawn location for " + npc.name() + ".").withStyle(ChatFormatting.RED),
            false
        );
        return false;
    }

    public void resetTimer() {
        tickCounter = 0;
    }
    public int removeAssignedNerds(ServerLevel world, String playerName) {
        var nerds = world.getEntities(
            MathQuestEntities.WANDERING_NERD.get(),
            entity -> playerName != null && playerName.equalsIgnoreCase(((WanderingNerdEntityForge) entity).getTargetPlayerName())
        );
        int count = 0;
        for (WanderingNerdEntityForge nerd : nerds) {
            nerd.discard();
            count++;
        }
        if (count > 0) {
            MathQuestControlState.markRemoved(playerName);
        }
        return count;
    }
}
