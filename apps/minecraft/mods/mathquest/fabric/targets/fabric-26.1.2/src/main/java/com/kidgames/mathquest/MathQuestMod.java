package com.kidgames.mathquest;

import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.control.FabricControlPanelLifecycle;
import com.kidgames.mathquest.entity.WanderingNerdEntity;
import com.kidgames.mathquest.entity.WanderingNerdSpawner;
import com.kidgames.mathquest.platform.MathQuestPaths;
import com.kidgames.mathquest.persistence.FluencyFeastBridge;
import com.kidgames.mathquest.persistence.MathQuizProblemListLoader;
import com.kidgames.mathquest.persistence.MathQuizSessionIngestor;
import com.kidgames.mathquest.persistence.QuizDatabase;
import com.kidgames.mathquest.persistence.SessionExporter;
import com.kidgames.mathquest.persistence.WrittenColumnSessionExporter;
import com.kidgames.mathquest.quest.CaveEscapeQuestService;
import com.kidgames.mathquest.network.DespawnNerdsPayload;
import com.kidgames.mathquest.network.EarnTpCreditsPayload;
import com.kidgames.mathquest.network.FluencyFeastResultPayload;
import com.kidgames.mathquest.network.GiveRewardPayload;
import com.kidgames.mathquest.network.OpenQuizPayload;
import com.kidgames.mathquest.network.QuestInvitationPayload;
import com.kidgames.mathquest.network.QuestInvitationResponsePayload;
import com.kidgames.mathquest.network.QuizPayloadBuilder;
import com.kidgames.mathquest.network.QuizResultPayload;
import com.kidgames.mathquest.quiz.QuizManager;
import com.kidgames.mathquest.reward.TpCreditBank;
import com.kidgames.mathquest.reward.TpCreditCompletionTracker;
import com.kidgames.mathquest.server.QuizResultProcessor;
import net.fabricmc.api.ModInitializer;
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
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.List;
import java.util.Optional;

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
    private static TpCreditBank tpCreditBank;

    @Override
    public void onInitialize() {
        MathQuestPaths.setConfigDir(net.fabricmc.loader.api.FabricLoader.getInstance().getConfigDir());
        net.fabricmc.loader.api.FabricLoader.getInstance().getModContainer(MOD_ID).ifPresent(container ->
            MathQuestPaths.setModVersion(container.getMetadata().getVersion().getFriendlyString()));
        CONFIG = MathQuestConfig.load();
        tpCreditBank = new TpCreditBank(CONFIG);

        // Register entity attributes
        FabricDefaultAttributeRegistry.register(WANDERING_NERD, WanderingNerdEntity.createWanderingNerdAttributes());

        // Register C2S packets
        PayloadTypeRegistry.serverboundPlay().register(GiveRewardPayload.ID, GiveRewardPayload.CODEC);
        PayloadTypeRegistry.serverboundPlay().register(QuizResultPayload.ID, QuizResultPayload.CODEC);
        PayloadTypeRegistry.serverboundPlay().register(DespawnNerdsPayload.ID, DespawnNerdsPayload.CODEC);
        PayloadTypeRegistry.serverboundPlay().register(EarnTpCreditsPayload.ID, EarnTpCreditsPayload.CODEC);
        PayloadTypeRegistry.serverboundPlay().register(QuestInvitationResponsePayload.ID, QuestInvitationResponsePayload.CODEC);

        // Register S2C packets
        PayloadTypeRegistry.clientboundPlay().register(OpenQuizPayload.ID, OpenQuizPayload.CODEC);
        PayloadTypeRegistry.clientboundPlay().register(FluencyFeastResultPayload.ID, FluencyFeastResultPayload.CODEC);
        PayloadTypeRegistry.clientboundPlay().register(QuestInvitationPayload.ID, QuestInvitationPayload.CODEC);

        ServerPlayNetworking.registerGlobalReceiver(GiveRewardPayload.ID, (payload, context) -> {
            ServerPlayer player = context.player();
            if (!QuizResultProcessor.itemRewardsAllowed(player.getName().getString())) {
                LOGGER.info("[MathQuest] Ignored item reward for {} because TP-credit earning is enabled",
                    player.getName().getString());
                return;
            }
            try {
                Identifier itemId = Identifier.parse(payload.itemId());
                Item item = BuiltInRegistries.ITEM.getValue(itemId);
                if (item != null) {
                    ItemStack stack = new ItemStack(item, payload.count());
                    player.getInventory().placeItemBackInInventory(stack);
                }
            } catch (Exception e) {
                LOGGER.error("[MathQuest] Failed to give reward item {}: {}", payload.itemId(), e.getMessage());
            }
        });

        ServerPlayNetworking.registerGlobalReceiver(QuizResultPayload.ID, (payload, context) -> {
            ServerPlayer player = context.player();
            handleQuizResult(payload.resultJson(), player);
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

    private static void handleQuizResult(String resultJson, ServerPlayer player) {
        try {
            com.google.gson.JsonObject root = com.google.gson.JsonParser.parseString(resultJson).getAsJsonObject();
            String quizType = root.has("quizType") ? MathQuestConfig.normalizeQuizType(root.get("quizType").getAsString()) : "standard_arithmetic";
            if ("written_column_arithmetic".equals(quizType)) {
                String minecraftUsername = player.getName().getString();
                String realName = CONFIG.resolveRealName(minecraftUsername);
                String enteredCode = root.has("evaluatorCode") ? root.get("evaluatorCode").getAsString() : "";
                root.addProperty("evaluatorCodeAccepted", enteredCode.equals(CONFIG.writtenColumnEvaluatorCode));
                WrittenColumnSessionExporter.export(root, realName, player.getUUID());
                LOGGER.info("[MathQuest] Server recorded written-column result for {} ({})",
                    minecraftUsername, root.has("evaluation") ? root.get("evaluation").getAsString() : "unknown");
                settleTpCreditSession(root, minecraftUsername);
                return;
            }
            String operation = root.get("operation").getAsString();
            int problemsTotal = root.get("problemsTotal").getAsInt();
            int problemsCorrect = root.get("problemsCorrect").getAsInt();
            boolean fluencyFeastMode = root.has("fluencyFeastMode") && root.get("fluencyFeastMode").getAsBoolean();
            String rewardGiven = root.has("rewardGiven") ? root.get("rewardGiven").getAsString() : "none";

            String username = player.getName().getString();
            String realName = CONFIG.resolveRealName(username);
            java.nio.file.Path activeDir = CONFIG.resolveMathQuizActiveDir();
            int fluencyBefore = fluencyFeastMode
                ? FluencyFeastBridge.percentForRealName(realName, activeDir).map(FluencyFeastBridge.PercentResult::percent).orElse(0)
                : 0;

            QuizDatabase db = QuizDatabase.getInstance();
            long sessionId = db.startSession(problemsTotal);

            com.google.gson.JsonArray problems = root.getAsJsonArray("problems");
            java.util.List<QuizManager.Problem> problemList = new java.util.ArrayList<>();
            for (int i = 0; i < problems.size(); i++) {
                com.google.gson.JsonObject p = problems.get(i).getAsJsonObject();
                int factorA = p.get("factorA").getAsInt();
                int factorB = p.get("factorB").getAsInt();
                long correctAnswer = p.get("correctAnswer").getAsLong();
                boolean isCorrect = p.get("isCorrect").getAsBoolean();
                long responseTimeMs = p.get("responseTimeMs").getAsLong();
                Long playerAnswer = p.has("playerAnswer") && !p.get("playerAnswer").isJsonNull()
                    ? p.get("playerAnswer").getAsLong() : null;

                String problemOperation = p.has("operation") && !p.get("operation").isJsonNull()
                    ? p.get("operation").getAsString()
                    : operation;
                QuizManager.Problem prob = QuizManager.Problem.create(problemOperation, factorA, factorB);
                prob.playerAnswer = playerAnswer;
                prob.isCorrect = isCorrect;
                prob.responseTimeMs = responseTimeMs;
                if (p.has("flags") && p.get("flags").isJsonArray()) {
                    for (com.google.gson.JsonElement flag : p.getAsJsonArray("flags")) {
                        prob.addFlag(flag.getAsString());
                    }
                }
                db.recordAnswer(sessionId, i + 1, prob);
                problemList.add(prob);
            }

            db.endSession(sessionId, problemsCorrect, rewardGiven);

            java.util.UUID playerUuid = player.getUUID();
            QuizManager quiz = QuizManager.fromCompletedProblems(operation, problemList, problemsCorrect);
            java.nio.file.Path sessionPath = SessionExporter.exportSession(quiz, realName, playerUuid);
            MathQuizSessionIngestor.ingest(sessionPath, realName);
            if (fluencyFeastMode) {
                int fluencyAfter = FluencyFeastBridge.percentForRealName(realName, activeDir)
                    .map(FluencyFeastBridge.PercentResult::percent)
                    .orElse(fluencyBefore);
                LOGGER.info("[MathQuest] Fluency feast for {}: {}% -> {}%", username, fluencyBefore, fluencyAfter);
                String fluencyRewardDescription = "";
                String fluencyRewardsJson = "[]";
                String fluencyRewardMode = "all";
                if (fluencyAfter - fluencyBefore >= 1 && problemsCorrect > 0) {
                    MathQuestConfig.RewardPlan fluencyPlan = CONFIG.resolveFluencyRewardPlanForPlayer(username);
                    List<MathQuestConfig.RewardEntry> fluencyRewards = fluencyPlan.entries();
                    fluencyRewardMode = MathQuestConfig.normalizeRewardGroupMode(fluencyPlan.mode());
                    if (!fluencyRewards.isEmpty()) {
                        if ("choose".equals(fluencyRewardMode) && fluencyRewards.size() > 1) {
                            fluencyRewardsJson = QuizPayloadBuilder.rewardsJson(fluencyRewards);
                            fluencyRewardDescription = "Choose your fluency reward:";
                        } else {
                            List<MathQuestConfig.RewardEntry> grantedRewards = CONFIG.resolveFluencyImprovementRewards(username);
                            for (MathQuestConfig.RewardEntry entry : grantedRewards) {
                                giveServerReward(player, entry);
                            }
                            fluencyRewardDescription = formatRewardDescriptions(grantedRewards);
                        }
                    } else {
                        fluencyRewardDescription = "Fluency improved!";
                    }
                } else if (problemsCorrect > 0) {
                    fluencyRewardDescription = "No fluency improvement reward this time.";
                }
                ServerPlayNetworking.send(
                    player,
                    new FluencyFeastResultPayload(
                        fluencyBefore,
                        fluencyAfter,
                        fluencyRewardDescription,
                        fluencyRewardsJson,
                        fluencyRewardMode
                    )
                );
            }
            CaveEscapeQuestService.runPostQuizActions(realName, player, problemList);
            MathQuizProblemListLoader.consumeActiveProblemList(username).ifPresent(consumed ->
                LOGGER.info("[MathQuest] Math-quiz internal list '{}' {} for {}",
                    consumed.listName(), consumed.action(), username)
            );
            LOGGER.info("[MathQuest] Server recorded quiz result for {} ({}/{} correct)",
                username, problemsCorrect, problemsTotal);
            settleTpCreditSession(root, username);
        } catch (Exception e) {
            LOGGER.error("[MathQuest] Failed to process quiz result from {}: {}",
                player.getName().getString(), e.getMessage());
        }
    }

    private static void settleTpCreditSession(com.google.gson.JsonObject root, String playerName) {
        if (!root.has("tpCreditCompletionToken") || root.get("tpCreditCompletionToken").isJsonNull()) return;
        String token = root.get("tpCreditCompletionToken").getAsString();
        if (token.isBlank()) return;
        boolean eligible = !root.has("tpCreditEligible") || root.get("tpCreditEligible").getAsBoolean();
        if (eligible) {
            TpCreditCompletionTracker.markCompleted(playerName, token);
        } else {
            TpCreditCompletionTracker.cancel(playerName, token);
        }
    }

    private static void giveServerReward(ServerPlayer player, MathQuestConfig.RewardEntry entry) {
        try {
            Identifier itemId = Identifier.parse(entry.item);
            Item item = BuiltInRegistries.ITEM.getValue(itemId);
            if (item != null) {
                ItemStack stack = new ItemStack(item, entry.count);
                player.getInventory().placeItemBackInInventory(stack);
            }
        } catch (Exception e) {
            LOGGER.error("[MathQuest] Failed to give server fluency reward {}: {}", entry.item, e.getMessage());
        }
    }

    private static String formatRewardDescription(MathQuestConfig.RewardEntry entry) {
        String name = entry.item;
        if (name.contains(":")) name = name.substring(name.indexOf(':') + 1);
        name = name.replace('_', ' ');
        StringBuilder sb = new StringBuilder();
        for (String word : name.split(" ")) {
            if (sb.length() > 0) sb.append(' ');
            if (!word.isEmpty()) {
                sb.append(Character.toUpperCase(word.charAt(0)));
                if (word.length() > 1) sb.append(word.substring(1));
            }
        }
        return sb + " x" + entry.count;
    }

    private static String formatRewardDescriptions(List<MathQuestConfig.RewardEntry> entries) {
        if (entries == null || entries.isEmpty()) return "";
        StringBuilder desc = new StringBuilder();
        for (MathQuestConfig.RewardEntry entry : entries) {
            if (desc.length() > 0) desc.append(", ");
            desc.append(formatRewardDescription(entry));
        }
        return desc.toString();
    }
}
