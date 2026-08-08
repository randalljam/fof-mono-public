package com.kidgames.mathquest.entity;

import net.fabricmc.api.EnvType;
import net.fabricmc.api.Environment;
import net.minecraft.client.renderer.entity.state.VillagerRenderState;

@Environment(EnvType.CLIENT)
public class MathQuestVillagerRenderState extends VillagerRenderState {
    public String npcId = "wandering_nerd";
}
