package com.kidgames.mathquest.forge;

import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.forge.entity.MathQuestNerdDespawnForge;
import com.kidgames.mathquest.forge.platform.ForgePlatformNetwork;
import com.kidgames.mathquest.forge.screen.ControlPanelScreenForge;
import com.kidgames.mathquest.forge.screen.QuizOfferScreenForge;
import com.kidgames.mathquest.persistence.QuizDatabase;
import com.kidgames.mathquest.platform.MathQuestLog;
import com.kidgames.mathquest.platform.MathQuestPaths;
import net.minecraft.client.Minecraft;
import net.minecraft.server.level.ServerPlayer;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.loading.FMLPaths;

@Mod.EventBusSubscriber(modid = MathQuestForge.MOD_ID, bus = Mod.EventBusSubscriber.Bus.FORGE, value = Dist.CLIENT)
public class MathQuestClientForge {
    private static int tickCounter = 0;

    static void initClient() {
        MathQuestPaths.setConfigDir(FMLPaths.CONFIGDIR.get());
        MathQuestConfig.load();
        Runtime.getRuntime().addShutdownHook(new Thread(() -> QuizDatabase.getInstance().close()));
        MathQuestLog.LOGGER.info("[MathQuest/Forge] Client initialized - mode: {}, version {}",
            MathQuestConfig.INSTANCE.quizMode, MathQuestPaths.modVersion());
    }

    public static void resetTimer() {
        tickCounter = 0;
    }

    public static void despawnNearbyNerds() {
        Minecraft client = Minecraft.getInstance();
        if (client == null) return;
        var server = client.getSingleplayerServer();
        if (server != null && client.player != null) {
            ServerPlayer serverPlayer = server.getPlayerList().getPlayer(client.player.getUUID());
            if (serverPlayer != null) {
                server.execute(() -> MathQuestNerdDespawnForge.despawnNerdsNear(serverPlayer));
            }
        } else if (client.player != null) {
            new ForgePlatformNetwork.Client().sendDespawnNerdsToServer();
        }
    }

    @SubscribeEvent
    static void onClientTick(TickEvent.ClientTickEvent event) {
        if (event.phase != TickEvent.Phase.END) return;
        Minecraft client = Minecraft.getInstance();
        if (client.player == null) return;

        while (MathQuestForgeModEvents.Client.OPEN_PANEL_KEY.consumeClick()) {
            if (client.screen == null && client.getSingleplayerServer() != null) {
                client.setScreen(new ControlPanelScreenForge(null));
            }
        }

        if (MathQuestConfig.INSTANCE == null || !MathQuestConfig.INSTANCE.enabled) return;
        if (!"popup".equals(MathQuestConfig.INSTANCE.quizMode)) return;
        if (client.getSingleplayerServer() == null) return;
        if (client.screen != null) return;

        tickCounter++;
        int intervalTicks = MathQuestConfig.INSTANCE.quizIntervalSeconds * 20;
        if (tickCounter >= intervalTicks) {
            tickCounter = 0;
            client.setScreen(new QuizOfferScreenForge());
        }
    }
}
