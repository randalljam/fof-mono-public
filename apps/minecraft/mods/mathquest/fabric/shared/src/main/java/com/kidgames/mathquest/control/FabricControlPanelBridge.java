package com.kidgames.mathquest.control;

import com.kidgames.mathquest.MathQuestMod;
import com.kidgames.mathquest.control.http.ControlPanelBridge;
import com.kidgames.mathquest.control.http.ControlPanelPlayerCardContributor;
import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.entity.WanderingNerdEntity;
import com.kidgames.mathquest.platform.FabricPlatformNetwork;
import com.kidgames.mathquest.platform.FabricPlatformPlayers;
import com.kidgames.mathquest.platform.PlatformNetwork;
import com.kidgames.mathquest.platform.PlatformServer;
import com.kidgames.mathquest.platform.PlayerContext;
import com.kidgames.mathquest.quest.CaveEscapeQuestService;
import com.kidgames.mathquest.server.OpenQuizPayloadBuilder;
import net.minecraft.core.BlockPos;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class FabricControlPanelBridge implements ControlPanelBridge {
    private final MinecraftServer server;
    private final PlatformServer platformServer;
    private final PlatformNetwork platformNetwork = new FabricPlatformNetwork.Server();
    private final ControlPanelPlayerCardContributor questContributor = new ControlPanelPlayerCardContributor() {
        @Override
        public Map<String, Object> questStatusForPlayer(String playerName) {
            return CaveEscapeQuestService.questStatusForPlayer(playerName);
        }
    };

    public FabricControlPanelBridge(MinecraftServer server) {
        this.server = server;
        this.platformServer = new FabricPlatformPlayers.FabricPlatformServer(server);
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
        return MathQuestMod.CONFIG;
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
                "dimension", player.level().dimension().identifier().toString()
            ));
        }
        return out;
    }

    @Override
    public List<Map<String, Object>> activeNerdsFor(String playerName) {
        List<Map<String, Object>> out = new ArrayList<>();
        ServerLevel world = server.overworld();
        for (WanderingNerdEntity nerd : world.getEntities(
            MathQuestMod.WANDERING_NERD,
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
        return MathQuestMod.getNerdSpawner().forceSpawn(server.overworld(), player, radius, npcId, locked);
    }

    @Override
    public int vanishNerds(String playerNameOrBlank) {
        if (playerNameOrBlank != null && !playerNameOrBlank.isBlank()) {
            return MathQuestMod.getNerdSpawner().removeAssignedNerds(server.overworld(), playerNameOrBlank);
        }
        int removed = 0;
        var nerds = server.overworld().getEntities(MathQuestMod.WANDERING_NERD, entity -> true);
        for (WanderingNerdEntity nerd : nerds) {
            nerd.discard();
            removed++;
        }
        return removed;
    }

    @Override
    public void openQuiz(PlayerContext player) {
        ServerPlayer serverPlayer = server.getPlayerList().getPlayerByName(player.username());
        if (serverPlayer != null) {
            PlayerContext ctx = FabricPlatformPlayers.fromServerPlayer(serverPlayer);
            platformNetwork.sendOpenQuiz(ctx, OpenQuizPayloadBuilder.create(player.username()));
        }
    }

    @Override
    public ControlPanelPlayerCardContributor playerCardContributor() {
        return questContributor;
    }

    public MinecraftServer minecraftServer() {
        return server;
    }
}
