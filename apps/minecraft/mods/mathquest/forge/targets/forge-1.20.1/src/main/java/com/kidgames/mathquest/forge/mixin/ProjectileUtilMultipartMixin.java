package com.kidgames.mathquest.forge.mixin;

import com.kidgames.mathquest.config.MathQuestConfig;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.AABB;
import net.minecraftforge.entity.PartEntity;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

import java.util.List;
import java.util.function.Predicate;

/**
 * Client-only mitigation for Ice and Fire (and other multipart) bosses: projectile
 * entity picking skips multipart hitboxes on the logical client so trident AABB
 * clips cannot wedge the render thread. Server-side collision is unchanged.
 *
 * Ice and Fire dragon parts extend {@code EntityMutlipartPart} (plain {@link Entity}),
 * not Forge {@link PartEntity} — both are filtered.
 *
 * Targets the two {@code ProjectileUtil.getEntityHitResult} overloads that actually
 * call {@link Level#getEntities}. The Level-only overload only delegates to the
 * float variant and must not be redirected (injection would fail at runtime).
 *
 * Toggle: {@link MathQuestConfig#excludeMultipartFromClientProjectileHits}
 * (default true; {@code /mathquest multipartProjectileFix off} to disable).
 */
@Mixin(net.minecraft.world.entity.projectile.ProjectileUtil.class)
public abstract class ProjectileUtilMultipartMixin {
    /** Soft-dep: Ice and Fire multipart base (typo "Mutlipart" is upstream). Lazy — resolved after mods load. */
    @Unique
    private static Class<?> mathquest$iafMultipartPart;
    @Unique
    private static boolean mathquest$iafMultipartResolved;

    @Redirect(
        method = "getEntityHitResult(Lnet/minecraft/world/entity/Entity;Lnet/minecraft/world/phys/Vec3;Lnet/minecraft/world/phys/Vec3;Lnet/minecraft/world/phys/AABB;Ljava/util/function/Predicate;D)Lnet/minecraft/world/phys/EntityHitResult;",
        at = @At(
            value = "INVOKE",
            target = "Lnet/minecraft/world/level/Level;getEntities(Lnet/minecraft/world/entity/Entity;Lnet/minecraft/world/phys/AABB;Ljava/util/function/Predicate;)Ljava/util/List;"
        )
    )
    private static List<Entity> mathquest$filterPartsEntityShooter(
        Level level,
        Entity except,
        AABB box,
        Predicate<Entity> predicate
    ) {
        return level.getEntities(except, box, mathquest$wrap(predicate, level.isClientSide));
    }

    @Redirect(
        method = "getEntityHitResult(Lnet/minecraft/world/level/Level;Lnet/minecraft/world/entity/Entity;Lnet/minecraft/world/phys/Vec3;Lnet/minecraft/world/phys/Vec3;Lnet/minecraft/world/phys/AABB;Ljava/util/function/Predicate;F)Lnet/minecraft/world/phys/EntityHitResult;",
        at = @At(
            value = "INVOKE",
            target = "Lnet/minecraft/world/level/Level;getEntities(Lnet/minecraft/world/entity/Entity;Lnet/minecraft/world/phys/AABB;Ljava/util/function/Predicate;)Ljava/util/List;"
        )
    )
    private static List<Entity> mathquest$filterPartsLevelFloat(
        Level level,
        Entity except,
        AABB box,
        Predicate<Entity> predicate
    ) {
        return level.getEntities(except, box, mathquest$wrap(predicate, level.isClientSide));
    }

    @Unique
    private static Predicate<Entity> mathquest$wrap(Predicate<Entity> original, boolean clientSide) {
        if (!clientSide) {
            return original;
        }
        MathQuestConfig config = MathQuestConfig.INSTANCE;
        if (config == null || !config.excludeMultipartFromClientProjectileHits) {
            return original;
        }
        return entity -> {
            if (mathquest$isMultipartHitbox(entity)) {
                return false;
            }
            return original == null || original.test(entity);
        };
    }

    @Unique
    private static boolean mathquest$isMultipartHitbox(Entity entity) {
        if (entity instanceof PartEntity) {
            return true;
        }
        Class<?> iafPart = mathquest$iafMultipartPartClass();
        return iafPart != null && iafPart.isInstance(entity);
    }

    @Unique
    private static Class<?> mathquest$iafMultipartPartClass() {
        if (!mathquest$iafMultipartResolved) {
            mathquest$iafMultipartResolved = true;
            try {
                mathquest$iafMultipartPart = Class.forName(
                    "com.github.alexthe666.iceandfire.entity.EntityMutlipartPart",
                    false,
                    ProjectileUtilMultipartMixin.class.getClassLoader()
                );
            } catch (ClassNotFoundException ignored) {
                mathquest$iafMultipartPart = null;
            }
        }
        return mathquest$iafMultipartPart;
    }
}
