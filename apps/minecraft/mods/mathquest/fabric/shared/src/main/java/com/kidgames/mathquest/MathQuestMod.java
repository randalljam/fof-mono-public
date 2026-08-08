package com.kidgames.mathquest;

import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.control.FabricControlPanelLifecycle;
import com.kidgames.mathquest.entity.WanderingNerdEntity;
import com.kidgames.mathquest.entity.WanderingNerdSpawner;
import com.kidgames.mathquest.platform.MathQuestPaths;
import com.kidgames.mathquest.platform.FabricPlatformInventory;
import com.kidgames.mathquest.platform.FabricPlatformNetwork;
import com.kidgames.mathquest.platform.FabricPlatformPlayers;
import com.kidgames.mathquest.server.FabricQuizResultHooks;
import com.kidgames.mathquest.server.QuizResultProcessor;
import com.kidgames.mathquest.network.DespawnNerdsPayload;
import com.kidgames.mathquest.network.EarnTpCreditsPayload;
import com.kidgames.mathquest.network.FluencyFeastResultPayload;
import com.kidgames.mathquest.network.GiveRewardPayload;
import com.kidgames.mathquest.network.OpenQuizPayload;
import com.kidgames.mathquest.network.QuestInvitationPayload;
import com.kidgames.mathquest.network.QuestInvitationResponsePayload;
import com.kidgames.mathquest.network.QuizResultPayload;
import com.kidgames.mathquest.persistence.FluencyFeastBridge;
import com.kidgames.mathquest.platform.PlayerContext;
import com.kidgames.mathquest.quest.CaveEscapeQuestService;
import com.kidgames.mathquest.reward.TpCreditBank;
import com.kidgames.mathquest.reward.TpCreditCompletionTracker;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.loader.api.FabricLoader;
import net.fabricmc.fabric.api.entity.event.v1.ServerPlayerEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.event.player.PlayerBlockBreakEvents;
import net.fabricmc.fabric.api.networking.v1.PayloadTypeRegistry;
import net.fabricmc.fabric.api.networking.v1.ServerPlayNetworking;
import net.fabricmc.fabric.api.object.builder.v1.entity.FabricDefaultAttributeRegistry;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.MobCategory;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class MathQuestMod implements ModInitializer {
    public static final String MOD_ID = "mathquest";
    public static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);
    public static MathQuestConfig CONFIG;

    public static final ResourceKey<EntityType<?>> WANDERING_NERD_KEY =
        ResourceKey.create(Registries.ENTITY_TYPE, Identifier.fromNamespaceAndPath(MOD_ID, "wandering_nerd"));

    public static final EntityType<WanderingNerdEntity> WANDERING_NERD = Registry.register(
        BuiltInRegistries.ENTITY_TYPE,
        Identifier.fromNamespaceAndPath(MOD_ID, "wandering_nerd"),
        EntityType.Builder.of(WanderingNerdEntity::new, MobCategory.CREATURE)
            .sized(0.6f, 1.95f)
            .build(WANDERING_NERD_KEY)
    );

    private static WanderingNerdSpawner nerdSpawner;
    private static FabricControlPanelLifecycle controlPanelServer;
    private static final FabricPlatformInventory PLATFORM_INVENTORY = new FabricPlatformInventory();
    private static final FabricQuizResultHooks QUIZ_RESULT_HOOKS = new FabricQuizResultHooks();
    private static final FabricPlatformNetwork.Server PLATFORM_NETWORK = new FabricPlatformNetwork.Server();
    private static TpCreditBank tpCreditBank;

    @Override
    public void onInitialize() {
        MathQuestPaths.setConfigDir(FabricLoader.getInstance().getConfigDir());
        FabricLoader.getInstance().getModContainer(MOD_ID).ifPresent(container ->
            MathQuestPaths.setModVersion(container.getMetadata().getVersion().getFriendlyString()));
        CONFIG = MathQuestConfig.load();
        tpCreditBank = new TpCreditBank(CONFIG);

        // Register entity attributes
        FabricDefaultAttributeRegistry.register(WANDERING_NERD, WanderingNerdEntity.createWanderingNerdAttributes());

        // Register C2S packets
        PayloadTypeRegistry.playC2S().register(GiveRewardPayload.ID, GiveRewardPayload.CODEC);
        PayloadTypeRegistry.playC2S().register(QuizResultPayload.ID, QuizResultPayload.CODEC);
        PayloadTypeRegistry.playC2S().register(DespawnNerdsPayload.ID, DespawnNerdsPayload.CODEC);
        PayloadTypeRegistry.playC2S().register(EarnTpCreditsPayload.ID, EarnTpCreditsPayload.CODEC);

        // Register S2C packet: server tells client to open quiz screen
        PayloadTypeRegistry.playS2C().register(OpenQuizPayload.ID, OpenQuizPayload.CODEC);
        PayloadTypeRegistry.playS2C().register(FluencyFeastResultPayload.ID, FluencyFeastResultPayload.CODEC);
        PayloadTypeRegistry.playS2C().register(QuestInvitationPayload.ID, QuestInvitationPayload.CODEC);
        PayloadTypeRegistry.playC2S().register(QuestInvitationResponsePayload.ID, QuestInvitationResponsePayload.CODEC);

        ServerPlayNetworking.registerGlobalReceiver(GiveRewardPayload.ID, (payload, context) -> {
            ServerPlayer player = context.player();
            PlayerContext playerContext = FabricPlatformPlayers.fromServerPlayer(player);
            QuizResultProcessor.grantReward(PLATFORM_INVENTORY, playerContext, new MathQuestConfig.RewardEntry(payload.itemId(), payload.count()));
        });

        ServerPlayNetworking.registerGlobalReceiver(QuizResultPayload.ID, (payload, context) -> {
            ServerPlayer player = context.player();
            PlayerContext playerContext = FabricPlatformPlayers.fromServerPlayer(player);
            QuizResultProcessor.process(payload.resultJson(), playerContext, PLATFORM_INVENTORY, PLATFORM_NETWORK, QUIZ_RESULT_HOOKS);
        });

        ServerPlayNetworking.registerGlobalReceiver(DespawnNerdsPayload.ID, (payload, context) -> {
            ServerPlayer player = context.player();
            context.server().execute(() -> despawnNerdsNear(context.server(), player));
        });

        ServerPlayNetworking.registerGlobalReceiver(EarnTpCreditsPayload.ID, (payload, context) -> {
            ServerPlayer player = context.player();
            context.server().execute(() -> awardTpCredits(player, payload.completionToken()));
        });

        // FROZEN: quest deferred past M6 (see docs/multi-version-tools + M5 plan) — Fabric-only; not ported to Forge.
        ServerPlayNetworking.registerGlobalReceiver(QuestInvitationResponsePayload.ID, (payload, context) -> {
            ServerPlayer player = context.player();
            context.server().execute(() -> CaveEscapeQuestService.handleInvitationResponse(player, payload.accepted()));
        });

        nerdSpawner = new WanderingNerdSpawner();
        ServerTickEvents.END_SERVER_TICK.register(server -> {
            ServerLevel overworld = server.overworld();
            nerdSpawner.tick(overworld);
            CaveEscapeQuestService.tick(server);
        });
        ServerPlayerEvents.AFTER_RESPAWN.register(CaveEscapeQuestService::handlePlayerRespawn);
        PlayerBlockBreakEvents.AFTER.register((world, player, pos, state, blockEntity) -> {
            if (player instanceof ServerPlayer serverPlayer) {
                CaveEscapeQuestService.handleBlockBreak(serverPlayer, pos);
            }
        });

        MathQuestServerCommands.register();
        controlPanelServer = new FabricControlPanelLifecycle();
        ServerLifecycleEvents.SERVER_STARTED.register(server -> {
            FluencyFeastBridge.verifyAtStartup();
            controlPanelServer.start(server);
        });
        ServerLifecycleEvents.SERVER_STOPPING.register(server -> controlPanelServer.stop());

        LOGGER.info("[MathQuest] Loaded! Mode: {}, quiz every {} seconds, {} problems, range {}-{}",
            CONFIG.quizMode, CONFIG.quizIntervalSeconds, CONFIG.problemsPerQuiz, CONFIG.minNumber, CONFIG.maxNumber);
    }

    public static WanderingNerdSpawner getNerdSpawner() {
        return nerdSpawner;
    }

    private static void awardTpCredits(ServerPlayer player, String completionToken) {
        String playerName = player.getName().getString();
        if (!TpCreditCompletionTracker.consumeCompleted(playerName, completionToken)) {
            player.sendSystemMessage(Component.literal(
                "[MathQuest] TP credits were not awarded: this quiz is incomplete, invalid, or already used."
            ));
            return;
        }
        TpCreditBank.AwardResult result = tpCreditBank.awardCompletedQuiz(playerName);
        if (result.persistenceFailed()) {
            player.sendSystemMessage(Component.literal("[MathQuest] TP credits could not be saved. Balance unchanged: "
                + result.balance() + "."));
        } else if (result.awarded()) {
            player.sendSystemMessage(Component.literal("[MathQuest] Quiz complete! Earned "
                + result.creditsAwarded() + " TP credit" + (result.creditsAwarded() == 1 ? "" : "s")
                + ". Balance: " + result.balance() + "."));
        } else if (CONFIG.resolveTpCreditEarningEnabled(playerName)) {
            player.sendSystemMessage(Component.literal("[MathQuest] No TP credits earned. Balance: "
                + result.balance() + "."));
        }
    }

    private static void despawnNerdsNear(net.minecraft.server.MinecraftServer server, ServerPlayer player) {
        ServerLevel world = server.overworld();
        var nerds = world.getEntities(
            WANDERING_NERD,
            player.getBoundingBox().inflate(50),
            entity -> true
        );
        for (WanderingNerdEntity nerd : nerds) {
            nerd.discard();
        }
    }
}
