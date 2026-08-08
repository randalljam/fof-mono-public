package com.kidgames.mathquest.forge.entity;

import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.phys.AABB;

public final class MathQuestNerdDespawnForge {
    private static final double DESPAWN_RADIUS = 50.0;

    private MathQuestNerdDespawnForge() {}

    public static void despawnNerdsNear(ServerPlayer player) {
        ServerLevel world = (ServerLevel) player.level();
        AABB box = player.getBoundingBox().inflate(DESPAWN_RADIUS);
        var nerds = world.getEntities(MathQuestEntities.WANDERING_NERD.get(), box, entity -> true);
        for (WanderingNerdEntityForge nerd : nerds) {
            nerd.discard();
        }
    }

    public static int vanishAllInOverworld(ServerLevel world) {
        var nerds = world.getEntities(MathQuestEntities.WANDERING_NERD.get(), entity -> true);
        int count = 0;
        for (WanderingNerdEntityForge nerd : nerds) {
            nerd.discard();
            count++;
        }
        return count;
    }
}
