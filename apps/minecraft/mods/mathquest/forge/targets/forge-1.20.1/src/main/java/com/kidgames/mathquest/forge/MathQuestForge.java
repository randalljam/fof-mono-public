package com.kidgames.mathquest.forge;

import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.forge.entity.MathQuestEntities;
import com.kidgames.mathquest.forge.entity.WanderingNerdSpawnerForge;
import com.kidgames.mathquest.forge.net.MathQuestNetworkForge;
import com.kidgames.mathquest.platform.MathQuestPaths;
import net.minecraftforge.fml.ModList;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.event.lifecycle.FMLClientSetupEvent;
import net.minecraftforge.fml.event.lifecycle.FMLCommonSetupEvent;
import net.minecraftforge.fml.javafmlmod.FMLJavaModLoadingContext;
import net.minecraftforge.fml.loading.FMLPaths;

@Mod(MathQuestForge.MOD_ID)
public class MathQuestForge {
    public static final String MOD_ID = "mathquest";
    private static final WanderingNerdSpawnerForge NERD_SPAWNER = new WanderingNerdSpawnerForge();

    public MathQuestForge() {
        MathQuestPaths.setConfigDir(FMLPaths.CONFIGDIR.get());
        MathQuestConfig.load();

        var modBus = FMLJavaModLoadingContext.get().getModEventBus();
        MathQuestEntities.ENTITY_TYPES.register(modBus);
        modBus.addListener(this::onCommonSetup);
        modBus.addListener(this::onClientSetup);
    }

    public static WanderingNerdSpawnerForge getNerdSpawner() {
        return NERD_SPAWNER;
    }

    private void onCommonSetup(FMLCommonSetupEvent event) {
        ModList.get().getModContainerById(MOD_ID).ifPresent(container ->
            MathQuestPaths.setModVersion(container.getModInfo().getVersion().toString()));
        event.enqueueWork(MathQuestNetworkForge::register);
    }

    private void onClientSetup(FMLClientSetupEvent event) {
        event.enqueueWork(MathQuestClientForge::initClient);
    }
}
