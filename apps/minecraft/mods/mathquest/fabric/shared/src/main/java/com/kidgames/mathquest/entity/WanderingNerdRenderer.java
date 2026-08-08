package com.kidgames.mathquest.entity;

import com.kidgames.mathquest.npc.MathQuestNpcCatalog;
import net.fabricmc.api.EnvType;
import net.fabricmc.api.Environment;
import net.minecraft.client.model.geom.ModelLayers;
import net.minecraft.client.model.npc.VillagerModel;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.entity.MobRenderer;
import net.minecraft.resources.Identifier;

@Environment(EnvType.CLIENT)
public class WanderingNerdRenderer extends MobRenderer<WanderingNerdEntity, MathQuestVillagerRenderState, VillagerModel> {
    public WanderingNerdRenderer(EntityRendererProvider.Context context) {
        super(context, new VillagerModel(context.bakeLayer(ModelLayers.VILLAGER)), 0.5f);
    }

    @Override
    public Identifier getTextureLocation(MathQuestVillagerRenderState state) {
        String path = MathQuestNpcCatalog.byId(state.npcId).texturePath();
        return Identifier.fromNamespaceAndPath("mathquest", path);
    }

    @Override
    public MathQuestVillagerRenderState createRenderState() {
        return new MathQuestVillagerRenderState();
    }

    @Override
    public void extractRenderState(WanderingNerdEntity entity, MathQuestVillagerRenderState state, float tickDelta) {
        super.extractRenderState(entity, state, tickDelta);
        state.npcId = entity.getNpcId();
    }
}
