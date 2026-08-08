package com.kidgames.mathquest.forge;

import com.kidgames.mathquest.forge.entity.MathQuestEntities;
import com.kidgames.mathquest.forge.entity.WanderingNerdEntityForge;
import com.kidgames.mathquest.forge.entity.WanderingNerdRendererForge;
import net.minecraft.client.KeyMapping;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.EntityRenderersEvent;
import net.minecraftforge.client.event.RegisterKeyMappingsEvent;
import net.minecraftforge.event.entity.EntityAttributeCreationEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import org.lwjgl.glfw.GLFW;

@Mod.EventBusSubscriber(modid = MathQuestForge.MOD_ID, bus = Mod.EventBusSubscriber.Bus.MOD)
public final class MathQuestForgeModEvents {
    private MathQuestForgeModEvents() {}

    @SubscribeEvent
    public static void registerAttributes(EntityAttributeCreationEvent event) {
        event.put(
            MathQuestEntities.WANDERING_NERD.get(),
            WanderingNerdEntityForge.createWanderingNerdAttributes().build()
        );
    }

    @Mod.EventBusSubscriber(modid = MathQuestForge.MOD_ID, bus = Mod.EventBusSubscriber.Bus.MOD, value = Dist.CLIENT)
    public static final class Client {
        public static final KeyMapping OPEN_PANEL_KEY = new KeyMapping(
            "key.mathquest.open_panel",
            GLFW.GLFW_KEY_K,
            "key.categories.mathquest"
        );

        private Client() {}

        @SubscribeEvent
        public static void registerRenderers(EntityRenderersEvent.RegisterRenderers event) {
            event.registerEntityRenderer(MathQuestEntities.WANDERING_NERD.get(), WanderingNerdRendererForge::new);
        }

        @SubscribeEvent
        public static void registerKeyMappings(RegisterKeyMappingsEvent event) {
            event.register(OPEN_PANEL_KEY);
        }
    }
}
