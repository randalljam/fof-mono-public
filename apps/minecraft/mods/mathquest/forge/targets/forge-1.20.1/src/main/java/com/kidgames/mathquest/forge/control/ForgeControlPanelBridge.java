package com.kidgames.mathquest.forge.control;

import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.control.http.ControlPanelBridge;
import com.kidgames.mathquest.control.http.MathQuestHttpControlPanelServer;
import com.kidgames.mathquest.control.http.MathQuestHttpRouter;
import com.kidgames.mathquest.forge.MathQuestForge;
import com.kidgames.mathquest.forge.entity.MathQuestEntities;
import com.kidgames.mathquest.forge.entity.WanderingNerdEntityForge;
import com.kidgames.mathquest.forge.platform.ForgePlatformNetwork;
import com.kidgames.mathquest.forge.platform.ForgePlatformPlayers;
import com.kidgames.mathquest.platform.PlatformNetwork;
import com.kidgames.mathquest.platform.PlatformServer;
import com.kidgames.mathquest.platform.PlayerContext;
import com.kidgames.mathquest.forge.net.MathQuestNetworkForge;
import com.kidgames.mathquest.server.OpenQuizPayloadBuilder;
import net.minecraft.core.BlockPos;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class ForgeControlPanelBridge implements ControlPanelBridge {
    private final MinecraftServer server;
    private final PlatformServer platformServer;
    private final PlatformNetwork platformNetwork = new ForgePlatformNetwork.Server();

    public ForgeControlPanelBridge(MinecraftServer server) {
        this.server = server;
        this.platformServer = new ForgePlatformPlayers.ForgePlatformServer(server);
    }

    @Override
    public PlatformServer platformServer() {
        return platformServer;
    }

    @Override
    public PlatformNetwork platformNetwork() {
        return platformNetwork;
    }

    @Override
    public MathQuestConfig config() {
        return MathQuestConfig.INSTANCE;
    }

    @Override
    public long worldSeed() {
        return server.overworld().getSeed();
    }

    @Override
    public List<Map<String, Object>> playerLocations() {
        List<Map<String, Object>> out = new ArrayList<>();
        for (ServerPlayer player : server.getPlayerList().getPlayers()) {
            BlockPos pos = player.blockPosition();
            out.add(Map.of(
                "playerName", player.getName().getString(),
                "x", pos.getX(),
                "y", pos.getY(),
                "z", pos.getZ(),
                "dimension", player.level().dimension().location().toString()
            ));
        }
        return out;
    }

    @Override
    public List<Map<String, Object>> activeNerdsFor(String playerName) {
        List<Map<String, Object>> out = new ArrayList<>();
        ServerLevel world = server.overworld();
        for (WanderingNerdEntityForge nerd : world.getEntities(
            MathQuestEntities.WANDERING_NERD.get(),
            entity -> playerName.equalsIgnoreCase(entity.getTargetPlayerName())
        )) {
            Map<String, Object> n = new LinkedHashMap<>();
            n.put("uuid", nerd.getUUID().toString());
            n.put("npcId", nerd.getNpcId());
            n.put("locked", nerd.isLockedToTarget());
            n.put("clicked", nerd.hasBeenInteracted());
            n.put("spawnedAtMillis", nerd.getSpawnedAtMillis());
            n.put("clickedAtMillis", nerd.getClickedAtMillis());
            out.add(n);
        }
        return out;
    }

    @Override
    public boolean spawnNerd(String playerName, int radius, String npcId, boolean locked) {
        ServerPlayer player = server.getPlayerList().getPlayerByName(playerName);
        if (player == null) return false;
        return MathQuestForge.getNerdSpawner().forceSpawn(server.overworld(), player, radius, npcId, locked);
    }

    @Override
    public int vanishNerds(String playerNameOrBlank) {
        if (playerNameOrBlank != null && !playerNameOrBlank.isBlank()) {
            return MathQuestForge.getNerdSpawner().removeAssignedNerds(server.overworld(), playerNameOrBlank);
        }
        int removed = 0;
        var nerds = server.overworld().getEntities(MathQuestEntities.WANDERING_NERD.get(), entity -> true);
        for (WanderingNerdEntityForge nerd : nerds) {
            nerd.discard();
            removed++;
        }
        return removed;
    }

    @Override
    public void openQuiz(PlayerContext player) {
        ServerPlayer serverPlayer = server.getPlayerList().getPlayerByName(player.username());
        if (serverPlayer != null) {
            MathQuestNetworkForge.sendOpenQuiz(serverPlayer, OpenQuizPayloadBuilder.create(player.username()));
        }
    }
}
