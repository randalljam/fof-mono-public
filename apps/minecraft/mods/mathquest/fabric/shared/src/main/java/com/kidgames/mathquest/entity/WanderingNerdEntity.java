package com.kidgames.mathquest.entity;

import com.kidgames.mathquest.MathQuestMod;
import com.kidgames.mathquest.control.MathQuestControlState;
import com.kidgames.mathquest.network.QuizPayloadBuilder;
import com.kidgames.mathquest.npc.MathQuestNpcCatalog;
import net.fabricmc.fabric.api.networking.v1.ServerPlayNetworking;
import net.minecraft.ChatFormatting;
import net.minecraft.network.chat.Component;
import net.minecraft.network.syncher.EntityDataAccessor;
import net.minecraft.network.syncher.EntityDataSerializers;
import net.minecraft.network.syncher.SynchedEntityData;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.PathfinderMob;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.ai.goal.FloatGoal;
import net.minecraft.world.entity.ai.goal.LookAtPlayerGoal;
import net.minecraft.world.entity.ai.goal.RandomLookAroundGoal;
import net.minecraft.world.entity.ai.goal.RandomStrollGoal;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.Level;

public class WanderingNerdEntity extends PathfinderMob {
    private static final EntityDataAccessor<String> NPC_ID =
        SynchedEntityData.defineId(WanderingNerdEntity.class, EntityDataSerializers.STRING);
    private int despawnTicksRemaining;
    private boolean hasBeenInteracted = false;
    private String targetPlayerName = null;
    private String targetRealName = null;
    private boolean lockedToTarget = false;
    private long spawnedAtMillis = System.currentTimeMillis();
    private long clickedAtMillis = 0L;

    public WanderingNerdEntity(EntityType<? extends WanderingNerdEntity> entityType, Level world) {
        super(entityType, world);
        this.despawnTicksRemaining = MathQuestMod.CONFIG.npcDespawnSeconds * 20;
        this.setCustomName(Component.literal(MathQuestNpcCatalog.byId(getNpcId()).name()).withStyle(ChatFormatting.GREEN));
        this.setCustomNameVisible(true);
        this.setInvulnerable(true);
        // Hold a book to look nerdy
        this.setItemSlot(EquipmentSlot.MAINHAND, new ItemStack(Items.WRITTEN_BOOK));
    }
    public void assignToPlayer(String playerName, String realName, String npcId, boolean lockedToTarget) {
        this.targetPlayerName = playerName;
        this.targetRealName = realName;
        MathQuestNpcCatalog.NpcDef npc = MathQuestNpcCatalog.byId(npcId);
        this.entityData.set(NPC_ID, npc.id());
        this.lockedToTarget = lockedToTarget;
        String suffix = lockedToTarget && playerName != null && !playerName.isBlank() ? " (" + playerName + ")" : "";
        this.setCustomName(Component.literal(npc.name() + suffix).withStyle(ChatFormatting.GREEN));
    }
    public String getTargetPlayerName() {
        return targetPlayerName;
    }
    public String getTargetRealName() {
        return targetRealName;
    }
    public String getNpcId() {
        return this.entityData.get(NPC_ID);
    }
    public boolean isLockedToTarget() {
        return lockedToTarget;
    }
    public boolean hasBeenInteracted() {
        return hasBeenInteracted;
    }
    public long getSpawnedAtMillis() {
        return spawnedAtMillis;
    }
    public long getClickedAtMillis() {
        return clickedAtMillis;
    }

    @Override
    protected void defineSynchedData(SynchedEntityData.Builder builder) {
        super.defineSynchedData(builder);
        builder.define(NPC_ID, "wandering_nerd");
    }

    @Override
    protected void registerGoals() {
        this.goalSelector.addGoal(0, new FloatGoal(this));
        this.goalSelector.addGoal(1, new LookAtPlayerGoal(this, Player.class, 8.0F));
        this.goalSelector.addGoal(2, new RandomStrollGoal(this, 0.35D));
        this.goalSelector.addGoal(3, new RandomLookAroundGoal(this));
    }

    public static AttributeSupplier.Builder createWanderingNerdAttributes() {
        return PathfinderMob.createMobAttributes()
            .add(Attributes.MAX_HEALTH, 20.0)
            .add(Attributes.MOVEMENT_SPEED, 0.35);
    }

    @Override
    public InteractionResult interact(Player player, InteractionHand hand) {
        if (hand != InteractionHand.MAIN_HAND) return InteractionResult.PASS;
        if (hasBeenInteracted) return InteractionResult.PASS;

        if (!this.level().isClientSide() && player instanceof ServerPlayer serverPlayer) {
            String clicker = serverPlayer.getName().getString();
            if (lockedToTarget && targetPlayerName != null
                && !targetPlayerName.equalsIgnoreCase(clicker)) {
                serverPlayer.sendSystemMessage(
                    Component.literal("[" + MathQuestNpcCatalog.byId(getNpcId()).name() + "] This quest is for " + targetPlayerName + ".")
                        .withStyle(ChatFormatting.YELLOW),
                    false
                );
                return InteractionResult.SUCCESS;
            }
            hasBeenInteracted = true;
            clickedAtMillis = System.currentTimeMillis();
            MathQuestControlState.markClicked(clicker, this.getUUID().toString());
            MathQuestNpcCatalog.NpcDef npc = MathQuestNpcCatalog.byId(getNpcId());
            java.util.List<String> lines = MathQuestNpcCatalog.dialogueLines(MathQuestMod.CONFIG, npc.id());
            String greeting = lines.get(this.level().getRandom().nextInt(lines.size()));
            serverPlayer.sendSystemMessage(
                Component.literal("[" + npc.name() + "] ").withStyle(ChatFormatting.GREEN)
                    .append(Component.literal(greeting).withStyle(ChatFormatting.YELLOW)),
                false
            );
            ServerPlayNetworking.send(serverPlayer, QuizPayloadBuilder.create(serverPlayer));
            // Do not discard here — the nerd stays until npcDespawnSeconds or client despawnNearbyNerds after quiz UI.
        }
        return InteractionResult.SUCCESS;
    }

    @Override
    public void tick() {
        super.tick();
        if (!this.level().isClientSide()) {
            despawnTicksRemaining--;
            if (despawnTicksRemaining <= 0) {
                this.discard();
            }
        }
    }

    @Override
    public boolean hurtServer(net.minecraft.server.level.ServerLevel world, net.minecraft.world.damagesource.DamageSource source, float amount) {
        // The Wandering Nerd cannot be harmed
        return false;
    }

    @Override
    public boolean canBeLeashed() {
        return false;
    }
}
