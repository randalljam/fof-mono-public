package com.kidgames.mathquest.entity;

import com.kidgames.mathquest.MathQuestMod;
import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.control.MathQuestControlState;
import com.kidgames.mathquest.npc.NpcSpawnPlanner;
import com.kidgames.mathquest.npc.MathQuestNpcCatalog;
import com.kidgames.mathquest.quest.CaveEscapeQuestService;
import java.util.List;
import java.util.Locale;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.util.RandomSource;
import net.minecraft.world.entity.EntitySpawnReason;
import net.minecraft.world.level.levelgen.Heightmap;

public class WanderingNerdSpawner {
    private int tickCounter = 0;

    public void tick(ServerLevel world) {
        if (!MathQuestMod.CONFIG.enabled) return;
        if (!"npc".equals(MathQuestMod.CONFIG.quizMode)) return;
        if (!MathQuestMod.CONFIG.npcAutomaticSpawnEnabled) return;

        tickCounter++;
        int intervalTicks = MathQuestMod.CONFIG.quizIntervalSeconds * 20;

        if (tickCounter >= intervalTicks) {
            tickCounter = 0;
            List<ServerPlayer> players = world.players();
            if (players.isEmpty()) return;

            String targetMode = MathQuestConfig.normalizeNpcSpawnTargetMode(MathQuestMod.CONFIG.npcSpawnTargetMode);
            List<String> playerNames = players.stream()
                .map(p -> p.getName().getString())
                .toList();
            int randomIndex = world.getRandom().nextInt(Math.max(1, playerNames.size()));
            List<String> targets = NpcSpawnPlanner.selectTargetNames(
                targetMode,
                playerNames,
                MathQuestMod.CONFIG.npcSpawnTargetPlayer,
                randomIndex
            );

            for (String targetName : targets) {
                ServerPlayer player = findPlayerByName(players, targetName);
                if (player == null) continue;
                if (CaveEscapeQuestService.isActiveQuestLearner(player.getName().getString())) continue;
                if (!MathQuestMod.CONFIG.npcAllowMultipleNerds && isNerdNearPlayer(world, player)) continue;
                spawnNerdNearPlayer(world, player);
            }
        }
    }

    private static ServerPlayer findPlayerByName(List<ServerPlayer> players, String nameLower) {
        String key = nameLower.toLowerCase(Locale.ROOT);
        for (ServerPlayer p : players) {
            if (p.getName().getString().toLowerCase(Locale.ROOT).equals(key)) {
                return p;
            }
        }
        return null;
    }

    private boolean isNerdNearPlayer(ServerLevel world, ServerPlayer player) {
        int radius = MathQuestMod.CONFIG.npcSpawnRadiusBlocks;
        return !world.getEntities(
            MathQuestMod.WANDERING_NERD,
            player.getBoundingBox().inflate(radius),
            entity -> true
        ).isEmpty();
    }

    private void spawnNerdNearPlayer(ServerLevel world, ServerPlayer player) {
        int radius = MathQuestMod.CONFIG.npcSpawnRadiusBlocks;
        String npcId = MathQuestMod.CONFIG.resolveNpcSelection(player.getName().getString());
        spawnNerdAt(world, player, radius, npcId, MathQuestMod.CONFIG.resolveNpcLock(player.getName().getString()));
    }

    public boolean forceSpawn(ServerLevel world, ServerPlayer player) {
        int radius = MathQuestMod.CONFIG.npcSpawnRadiusBlocks;
        return forceSpawn(world, player, radius, "wandering_nerd", defaultForceSpawnLock(world, player));
    }
    public boolean forceSpawn(ServerLevel world, ServerPlayer player, int radius, String npcId, boolean lockedToTarget) {
        if (!MathQuestMod.CONFIG.npcAllowMultipleNerds) {
            removeAssignedNerds(world, player.getName().getString());
        }
        return spawnNerdAt(world, player, radius, npcId, lockedToTarget);
    }

    private boolean spawnNerdAt(ServerLevel world, ServerPlayer player, int radius) {
        String npcId = MathQuestMod.CONFIG.resolveNpcSelection(player.getName().getString());
        return spawnNerdAt(world, player, radius, npcId, MathQuestMod.CONFIG.resolveNpcLock(player.getName().getString()));
    }

    private boolean defaultForceSpawnLock(ServerLevel world, ServerPlayer player) {
        if (!world.getServer().isDedicatedServer()) return false;
        return MathQuestMod.CONFIG.resolveNpcLock(player.getName().getString());
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

            WanderingNerdEntity nerd = MathQuestMod.WANDERING_NERD.create(world, EntitySpawnReason.MOB_SUMMONED);
            if (nerd != null) {
                String playerName = player.getName().getString();
                String realName = MathQuestMod.CONFIG.resolveRealName(playerName);
                nerd.assignToPlayer(playerName, realName, npc.id(), lockedToTarget);
                nerd.snapTo(x + 0.5, y, z + 0.5, random.nextFloat() * 360, 0);
                world.addFreshEntity(nerd);
                MathQuestControlState.markSpawned(playerName, nerd.getUUID().toString());
                MathQuestMod.LOGGER.info("[MathQuest] Spawned {} at {}, {}, {} near {}",
                    npc.name(), x, y, z, playerName);

                if (MathQuestMod.CONFIG.logNerdSpawn) {
                    player.sendSystemMessage(
                        Component.literal("[MathQuest] " + npc.name() + " has spawned!").withStyle(ChatFormatting.GREEN),
                        false
                    );
                }
                if (MathQuestMod.CONFIG.logNerdLocation) {
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
            MathQuestMod.WANDERING_NERD,
            entity -> playerName != null && playerName.equalsIgnoreCase(entity.getTargetPlayerName())
        );
        int count = 0;
        for (WanderingNerdEntity nerd : nerds) {
            nerd.discard();
            count++;
        }
        if (count > 0) {
            MathQuestControlState.markRemoved(playerName);
        }
        return count;
    }
}
