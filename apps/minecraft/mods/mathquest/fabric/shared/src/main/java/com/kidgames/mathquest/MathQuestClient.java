package com.kidgames.mathquest;

import com.kidgames.mathquest.client.MathQuestTitleScreenOverlay;
import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.persistence.QuizDatabase;
import com.kidgames.mathquest.entity.WanderingNerdEntity;
import com.kidgames.mathquest.entity.WanderingNerdRenderer;
import com.kidgames.mathquest.network.DespawnNerdsPayload;
import com.kidgames.mathquest.network.FluencyFeastResultPayload;
import com.kidgames.mathquest.network.OpenQuizPayload;
import com.kidgames.mathquest.network.QuestInvitationPayload;
import com.kidgames.mathquest.screen.ControlPanelScreen;
import com.kidgames.mathquest.screen.QuestInvitationScreen;
import com.kidgames.mathquest.screen.QuizOfferScreen;
import com.kidgames.mathquest.screen.QuizResultScreen;
import com.kidgames.mathquest.screen.QuizScreen;
import com.kidgames.mathquest.screen.WrittenColumnQuizScreen;
import com.kidgames.mathquest.quiz.QuizManager;
import com.kidgames.mathquest.quiz.QuizSessionOptions;
import com.mojang.blaze3d.platform.InputConstants;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.client.keybinding.v1.KeyBindingHelper;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayNetworking;
import net.fabricmc.fabric.api.client.rendering.v1.EntityRendererRegistry;
import net.fabricmc.loader.api.FabricLoader;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.Identifier;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import org.lwjgl.glfw.GLFW;

public class MathQuestClient implements ClientModInitializer {
    private static int tickCounter = 0;
    private static int quizOpenDelayTicks = -1;
    private static MathQuestConfig.EffectiveQuizParams pendingQuizParams = null;
    private static String pendingProblemsJson = "[]";
    private static String pendingRewardsJson = "[]";
    private static String pendingRewardMode = "random";
    private static String pendingQuizType = "standard_arithmetic";
    private static String pendingOptionsJson = QuizSessionOptions.standard().toJson();
    private static boolean pendingFluencyFeastMode = false;
    private static String activeRewardsJson = "[]";
    private static String activeRewardMode = "random";
    private static boolean versionAnnounced = false;

    /** Hotkey that opens the in-game settings panel. Defaults to {@code K}. */
    public static KeyMapping openControlPanelKey;

    @Override
    public void onInitializeClient() {
        MathQuestCommands.register();
        MathQuestTitleScreenOverlay.register();

        EntityRendererRegistry.register(MathQuestMod.WANDERING_NERD, WanderingNerdRenderer::new);

        // Register a custom keybind category so the binding shows up under "MathQuest"
        // in vanilla Options -> Controls (rather than under "Misc"). In MC 1.21.11
        // mojmap, KeyMapping's 4-arg constructor takes a KeyMapping.Category instance,
        // not the legacy String key. Fabric's KeyMappingCategoryMixin makes
        // KeyMapping.Category.register(Identifier) discoverable so custom categories
        // sort correctly in the controls UI.
        KeyMapping.Category category = KeyMapping.Category.register(
            Identifier.fromNamespaceAndPath(MathQuestMod.MOD_ID, "main"));

        openControlPanelKey = KeyBindingHelper.registerKeyBinding(new KeyMapping(
            "key.mathquest.open_panel",
            InputConstants.Type.KEYSYM,
            GLFW.GLFW_KEY_K,
            category));

        ClientPlayNetworking.registerGlobalReceiver(FluencyFeastResultPayload.ID, (payload, context) -> {
            context.client().execute(() -> QuizResultScreen.applyServerFluencyResult(
                payload.beforePercent(),
                payload.afterPercent(),
                payload.rewardDescription(),
                payload.rewardsJson(),
                payload.rewardMode()
            ));
        });

        ClientPlayNetworking.registerGlobalReceiver(OpenQuizPayload.ID, (payload, context) -> {
            context.client().execute(() -> {
                pendingQuizParams = new MathQuestConfig.EffectiveQuizParams(
                    payload.minNumber(), payload.maxNumber(),
                    payload.operation(), payload.problemsPerQuiz());
                pendingProblemsJson = payload.problemsJson();
                pendingRewardsJson = payload.rewardsJson();
                pendingRewardMode = payload.rewardMode();
                pendingQuizType = payload.quizType();
                pendingOptionsJson = payload.optionsJson();
                pendingFluencyFeastMode = payload.fluencyFeastMode();
                if (payload.directToQuiz()) {
                    openQuizPayload(context.client(), payload);
                    pendingQuizParams = null;
                    pendingProblemsJson = "[]";
                    pendingRewardsJson = "[]";
                    pendingRewardMode = "random";
                    pendingQuizType = "standard_arithmetic";
                    pendingOptionsJson = QuizSessionOptions.standard().toJson();
                    pendingFluencyFeastMode = false;
                    return;
                }
                quizOpenDelayTicks = 100; // 5 seconds (100 ticks)
            });
        });

        ClientPlayNetworking.registerGlobalReceiver(QuestInvitationPayload.ID, (payload, context) -> {
            context.client().execute(() -> {
                if (context.client().screen == null) {
                    context.client().setScreen(new QuestInvitationScreen(
                        payload.message(),
                        payload.subtitle(),
                        payload.openQuizPayload()
                    ));
                }
            });
        });

        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            if (client.player == null) {
                versionAnnounced = false;
                return;
            }
            if (!versionAnnounced) {
                announceVersion(client);
                versionAnnounced = true;
            }

            // Hotkey: open the in-game control panel from gameplay (no menu open).
            // Hidden on remote multiplayer — edits only affect local config, not the
            // server's. Use server-side /mathquest commands instead.
            while (openControlPanelKey != null && openControlPanelKey.consumeClick()) {
                if (client.screen == null && client.getSingleplayerServer() != null) {
                    client.setScreen(new ControlPanelScreen(null));
                }
            }

            // NPC mode: delayed quiz opening after nerd interaction
            if (quizOpenDelayTicks > 0) {
                quizOpenDelayTicks--;
                if (quizOpenDelayTicks == 0) {
                    quizOpenDelayTicks = -1;
                    if (client.screen == null) {
                        client.setScreen(new QuizOfferScreen(
                            pendingQuizParams,
                            pendingProblemsJson,
                            pendingRewardsJson,
                            pendingRewardMode,
                            pendingQuizType,
                            pendingOptionsJson,
                            pendingFluencyFeastMode));
                    }
                    pendingQuizParams = null;
                    pendingProblemsJson = "[]";
                    pendingRewardsJson = "[]";
                    pendingRewardMode = "random";
                    pendingQuizType = "standard_arithmetic";
                    pendingOptionsJson = QuizSessionOptions.standard().toJson();
                    pendingFluencyFeastMode = false;
                }
            }

            // Popup mode timer — only in singleplayer (integrated server). On a remote multiplayer
            // connection, getServer() is null; running the timer here would make every player with
            // the mod get timed popups independently (not synced to the Wandering Nerd). Use NPC
            // mode on the server for shared-world quizzes instead.
            if (!MathQuestMod.CONFIG.enabled) return;
            if (!"popup".equals(MathQuestMod.CONFIG.quizMode)) return;
            if (client.getSingleplayerServer() == null) return;
            if (client.screen != null) return;

            tickCounter++;

            int intervalTicks = MathQuestMod.CONFIG.quizIntervalSeconds * 20;
            if (tickCounter >= intervalTicks) {
                tickCounter = 0;
                client.setScreen(new QuizOfferScreen());
            }
        });

        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            QuizDatabase.getInstance().close();
        }));

        MathQuestMod.LOGGER.info("[MathQuest] Client initialized - mode: {}", MathQuestMod.CONFIG.quizMode);
    }

    private static void announceVersion(Minecraft client) {
        Component message = Component.literal("MathQuest " + loadedVersion() + " loaded");
        Object chat = client.gui.getChat();
        try {
            chat.getClass().getMethod("addClientSystemMessage", Component.class).invoke(chat, message);
            return;
        } catch (ReflectiveOperationException ignored) {}
        try {
            chat.getClass().getMethod("addMessage", Component.class).invoke(chat, message);
        } catch (ReflectiveOperationException e) {
            MathQuestMod.LOGGER.warn("[MathQuest] Could not add version message to chat: {}", e.getMessage());
        }
    }

    private static String loadedVersion() {
        return FabricLoader.getInstance()
            .getModContainer(MathQuestMod.MOD_ID)
            .map(container -> container.getMetadata().getVersion().getFriendlyString())
            .orElse("unknown");
    }

    public static void resetTimer() {
        tickCounter = 0;
    }
    public static void setActiveRewardPlan(String rewardsJson, String rewardMode) {
        activeRewardsJson = (rewardsJson == null || rewardsJson.isBlank()) ? "[]" : rewardsJson;
        activeRewardMode = (rewardMode == null || rewardMode.isBlank()) ? "random" : rewardMode;
    }
    public static String getActiveRewardsJson() {
        return activeRewardsJson;
    }
    public static String getActiveRewardMode() {
        return activeRewardMode;
    }
    public static void clearActiveRewardPlan() {
        activeRewardsJson = "[]";
        activeRewardMode = "random";
    }

    public static void openQuizPayload(Minecraft client, OpenQuizPayload payload) {
        if (payload == null) return;
        openQuizDirectly(
            client,
            new MathQuestConfig.EffectiveQuizParams(
                payload.minNumber(),
                payload.maxNumber(),
                payload.operation(),
                payload.problemsPerQuiz()
            ),
            payload.problemsJson(),
            payload.rewardsJson(),
            payload.rewardMode(),
            payload.quizType(),
            payload.optionsJson(),
            payload.fluencyFeastMode()
        );
    }

    private static void openQuizDirectly(Minecraft client) {
        if (client == null || pendingQuizParams == null) return;
        openQuizDirectly(
            client,
            pendingQuizParams,
            pendingProblemsJson,
            pendingRewardsJson,
            pendingRewardMode,
            pendingQuizType,
            pendingOptionsJson,
            pendingFluencyFeastMode
        );
    }

    private static void openQuizDirectly(
        Minecraft client,
        MathQuestConfig.EffectiveQuizParams params,
        String problemsJson,
        String rewardsJson,
        String rewardMode,
        String quizTypeValue,
        String optionsJson,
        boolean fluencyFeastMode
    ) {
        if (client == null || params == null) return;
        setActiveRewardPlan(rewardsJson, rewardMode);
        QuizSessionOptions options = resolveSessionOptions(optionsJson, fluencyFeastMode);
        String quizType = MathQuestConfig.normalizeQuizType(quizTypeValue);
        if ("written_column_arithmetic".equals(quizType)) {
            client.setScreen(new WrittenColumnQuizScreen(
                params,
                rewardsJson,
                rewardMode,
                options.tpCreditCompletionToken()
            ));
            return;
        }
        java.util.List<QuizManager.Problem> serverProblems = parseServerProblems(problemsJson);
        QuizManager quiz = serverProblems.isEmpty()
            ? new QuizManager(params)
            : new QuizManager(params, serverProblems);
        quiz.setSessionOptions(options);
        String sourceLabel = fluencyFeastMode
            ? "fluency feast"
            : (serverProblems.isEmpty() ? "generated" : "external list");
        client.setScreen(new QuizScreen(quiz, sourceLabel, options));
    }

    private static QuizSessionOptions resolveSessionOptions(String optionsJson, boolean fluencyFeastMode) {
        if (fluencyFeastMode && (optionsJson == null || optionsJson.isBlank())) {
            return QuizSessionOptions.fluencyFeast();
        }
        return QuizSessionOptions.fromJson(optionsJson);
    }

    private static java.util.List<QuizManager.Problem> parseServerProblems(String problemsJson) {
        java.util.List<QuizManager.Problem> out = new java.util.ArrayList<>();
        try {
            com.google.gson.JsonArray arr = com.google.gson.JsonParser.parseString(problemsJson).getAsJsonArray();
            for (com.google.gson.JsonElement el : arr) {
                com.google.gson.JsonObject obj = el.getAsJsonObject();
                out.add(QuizManager.Problem.create(
                    obj.get("operation").getAsString(),
                    obj.get("factorA").getAsInt(),
                    obj.get("factorB").getAsInt()
                ));
            }
        } catch (Exception e) {
            MathQuestMod.LOGGER.error("[MathQuest] Failed to parse server problem list: {}", e.getMessage());
        }
        return out;
    }

    public static void despawnNearbyNerds() {
        Minecraft client = Minecraft.getInstance();
        var server = client.getSingleplayerServer();
        if (server != null && client.player != null) {
            ServerPlayer serverPlayer = server.getPlayerList().getPlayer(client.player.getUUID());
            if (serverPlayer != null) {
                ServerLevel world = server.overworld();
                server.execute(() -> {
                    var nerds = world.getEntities(
                        MathQuestMod.WANDERING_NERD,
                        serverPlayer.getBoundingBox().inflate(50),
                        entity -> true
                    );
                    for (WanderingNerdEntity nerd : nerds) {
                        nerd.discard();
                    }
                });
            }
        } else if (client.player != null) {
            try {
                ClientPlayNetworking.send(new DespawnNerdsPayload());
            } catch (Exception e) {
                MathQuestMod.LOGGER.error("[MathQuest] Failed to send despawn nerds payload: {}", e.getMessage());
            }
        }
    }
}
