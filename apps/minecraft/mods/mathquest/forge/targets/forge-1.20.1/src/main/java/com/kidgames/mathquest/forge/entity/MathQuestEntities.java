package com.kidgames.mathquest.forge.entity;

import com.kidgames.mathquest.forge.MathQuestForge;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.MobCategory;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;

public final class MathQuestEntities {
    public static final DeferredRegister<EntityType<?>> ENTITY_TYPES =
        DeferredRegister.create(ForgeRegistries.ENTITY_TYPES, MathQuestForge.MOD_ID);

    public static final RegistryObject<EntityType<WanderingNerdEntityForge>> WANDERING_NERD =
        ENTITY_TYPES.register("wandering_nerd", () -> EntityType.Builder
            .of(WanderingNerdEntityForge::new, MobCategory.CREATURE)
            .sized(0.6f, 1.95f)
            .build("wandering_nerd"));

    private MathQuestEntities() {}
}
