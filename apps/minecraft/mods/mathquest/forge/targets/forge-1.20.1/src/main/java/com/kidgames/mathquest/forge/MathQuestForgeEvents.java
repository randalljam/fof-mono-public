package com.kidgames.mathquest.forge;

import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.forge.control.ForgeControlPanelLifecycle;
import com.kidgames.mathquest.forge.platform.ForgePlatformMessenger;
import com.kidgames.mathquest.forge.platform.ForgePlatformPlayers;
import com.kidgames.mathquest.persistence.FluencyFeastBridge;
import com.kidgames.mathquest.persistence.SqliteDriver;
import com.kidgames.mathquest.platform.MathQuestPaths;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.Level;
import net.minecraftforge.event.RegisterCommandsEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.event.server.ServerStartedEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.loading.FMLPaths;

@Mod.EventBusSubscriber(modid = MathQuestForge.MOD_ID, bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class MathQuestForgeEvents {
    private static ForgeControlPanelLifecycle controlPanelLifecycle;

    private MathQuestForgeEvents() {}

    @SubscribeEvent
    public static void onServerStarting(net.minecraftforge.event.server.ServerStartingEvent event) {
        MathQuestPaths.setConfigDir(FMLPaths.CONFIGDIR.get());
        MathQuestConfig.load();
        FluencyFeastBridge.verifyAtStartup();
        SqliteDriver.ensureLoaded();
        ForgePlatformMessenger.register();
    }

    @SubscribeEvent
    public static void onServerStarted(ServerStartedEvent event) {
        ForgePlatformPlayers.bindServer(event.getServer());
        if (MathQuestConfig.INSTANCE.controlPanelEnabled) {
            controlPanelLifecycle = new ForgeControlPanelLifecycle();
            controlPanelLifecycle.start(event.getServer());
        }
    }

    @SubscribeEvent
    public static void onServerStopping(ServerStoppingEvent event) {
        if (controlPanelLifecycle != null) {
            controlPanelLifecycle.stop();
            controlPanelLifecycle = null;
        }
    }

    @SubscribeEvent
    public static void onPlayerLoggedIn(PlayerEvent.PlayerLoggedInEvent event) {
        if (!(event.getEntity() instanceof ServerPlayer player)) return;
        player.sendSystemMessage(net.minecraft.network.chat.Component.literal(
            "MathQuest " + MathQuestPaths.modVersion()));
    }

    @SubscribeEvent
    public static void onRegisterCommands(RegisterCommandsEvent event) {
        MathQuestServerCommandsForge.register(event.getDispatcher());
    }

    @SubscribeEvent
    public static void onLevelTick(TickEvent.LevelTickEvent event) {
        if (event.phase != TickEvent.Phase.END) return;
        if (event.level.isClientSide()) return;
        if (event.level.dimension() != Level.OVERWORLD) return;
        MathQuestForge.getNerdSpawner().tick((ServerLevel) event.level);
    }
}
