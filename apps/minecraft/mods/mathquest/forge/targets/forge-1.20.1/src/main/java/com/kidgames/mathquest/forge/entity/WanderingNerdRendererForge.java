package com.kidgames.mathquest.forge.entity;

import com.kidgames.mathquest.npc.MathQuestNpcCatalog;
import net.minecraft.client.model.VillagerModel;
import net.minecraft.client.model.geom.ModelLayers;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.entity.MobRenderer;
import net.minecraft.resources.ResourceLocation;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.api.distmarker.OnlyIn;

@OnlyIn(Dist.CLIENT)
public class WanderingNerdRendererForge extends MobRenderer<WanderingNerdEntityForge, VillagerModel<WanderingNerdEntityForge>> {
    public WanderingNerdRendererForge(EntityRendererProvider.Context context) {
        super(context, new VillagerModel<>(context.bakeLayer(ModelLayers.VILLAGER)), 0.5f);
    }

    @Override
    public ResourceLocation getTextureLocation(WanderingNerdEntityForge entity) {
        String path = MathQuestNpcCatalog.byId(entity.getNpcId()).texturePath();
        return new ResourceLocation("mathquest", path);
    }
}
