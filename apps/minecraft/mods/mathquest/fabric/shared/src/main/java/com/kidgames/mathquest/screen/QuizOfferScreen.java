package com.kidgames.mathquest.screen;

import com.kidgames.mathquest.MathQuestClient;
import com.kidgames.mathquest.MathQuestMod;
import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.persistence.FluencyFeastBridge;
import com.kidgames.mathquest.persistence.MathQuizProblemListLoader;
import com.kidgames.mathquest.quiz.QuizManager;
import com.kidgames.mathquest.quiz.QuizSessionOptions;
import com.kidgames.mathquest.reward.TpCreditCompletionTracker;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;

public class QuizOfferScreen extends Screen {
    private final MathQuestConfig.EffectiveQuizParams serverParams;
    private final String serverProblemsJson;
    private final String serverRewardsJson;
    private final String serverRewardMode;
    private final String serverQuizType;
    private final QuizSessionOptions serverOptions;
    private final boolean serverFluencyFeastMode;

    public QuizOfferScreen() {
        this(null, "[]", "[]", "random", "standard_arithmetic", QuizSessionOptions.standard().toJson(), false);
    }

    public QuizOfferScreen(MathQuestConfig.EffectiveQuizParams serverParams) {
        this(serverParams, "[]", "[]", "random", "standard_arithmetic", QuizSessionOptions.standard().toJson(), false);
    }
    public QuizOfferScreen(
        MathQuestConfig.EffectiveQuizParams serverParams,
        String serverProblemsJson,
        String serverRewardsJson,
        String serverRewardMode,
        String serverQuizType,
        String serverOptionsJson
    ) {
        this(serverParams, serverProblemsJson, serverRewardsJson, serverRewardMode, serverQuizType, serverOptionsJson, false);
    }
    public QuizOfferScreen(
        MathQuestConfig.EffectiveQuizParams serverParams,
        String serverProblemsJson,
        String serverRewardsJson,
        String serverRewardMode,
        String serverQuizType,
        String serverOptionsJson,
        boolean serverFluencyFeastMode
    ) {
        super(Component.literal("Math Quest!"));
        this.serverParams = serverParams;
        this.serverProblemsJson = serverProblemsJson == null ? "[]" : serverProblemsJson;
        this.serverRewardsJson = serverRewardsJson == null ? "[]" : serverRewardsJson;
        this.serverRewardMode = serverRewardMode == null ? "random" : serverRewardMode;
        this.serverQuizType = MathQuestConfig.normalizeQuizType(serverQuizType);
        this.serverFluencyFeastMode = serverFluencyFeastMode;
        this.serverOptions = serverFluencyFeastMode && (serverOptionsJson == null || serverOptionsJson.isBlank())
            ? QuizSessionOptions.fluencyFeast()
            : QuizSessionOptions.fromJson(serverOptionsJson);
    }

    @Override
    protected void init() {
        int centerX = this.width / 2;
        int centerY = this.height / 2;

        this.addRenderableWidget(Button.builder(
            Component.literal("Let's Go!"),
            button -> {
                QuizManager quiz;
                String[] sourceLabel = {"generated"};
                String playerName = (this.minecraft != null && this.minecraft.player != null)
                    ? this.minecraft.player.getName().getString()
                    : null;
                if (serverParams != null) {
                    MathQuestClient.setActiveRewardPlan(serverRewardsJson, serverRewardMode);
                    if ("written_column_arithmetic".equals(serverQuizType)) {
                        this.minecraft.setScreen(new WrittenColumnQuizScreen(
                            serverParams,
                            serverRewardsJson,
                            serverRewardMode,
                            serverOptions.tpCreditCompletionToken()
                        ));
                        return;
                    }
                    java.util.List<QuizManager.Problem> serverProblems = parseProblems(serverProblemsJson);
                    quiz = serverProblems.isEmpty()
                        ? new QuizManager(serverParams)
                        : new QuizManager(serverParams, serverProblems);
                    quiz.setSessionOptions(serverOptions);
                    if (serverFluencyFeastMode) {
                        sourceLabel[0] = "fluency feast";
                    } else if (!serverProblems.isEmpty()) {
                        sourceLabel[0] = "external list";
                    }
                } else {
                    MathQuestConfig.EffectiveQuizParams params = MathQuestMod.CONFIG.resolveForPlayer(playerName);
                    if ("written_column_arithmetic".equals(MathQuestMod.CONFIG.resolveQuizType(playerName))) {
                        MathQuestConfig.RewardPlan rewardPlan = MathQuestMod.CONFIG.resolveRewardPlanForPlayer(playerName);
                        this.minecraft.setScreen(new WrittenColumnQuizScreen(
                            params,
                            null,
                            rewardPlan.mode(),
                            TpCreditCompletionTracker.issue(playerName)
                        ));
                        return;
                    }
                    String source = MathQuestMod.CONFIG.resolveInternalQuizSource(playerName);
                    if ("internal_problem_list".equals(source)) {
                        quiz = MathQuizProblemListLoader.loadForMinecraftPlayer(
                            playerName,
                            MathQuestMod.CONFIG.resolvePlayerRealNames()
                        )
                            .map(list -> {
                                MathQuizProblemListLoader.rememberActiveProblemList(playerName, list);
                                MathQuestMod.LOGGER.info("[MathQuest] Loaded {} problems from math-quiz list '{}' for {} ({})",
                                    list.problems().size(), list.listName(), playerName, list.realName());
                                sourceLabel[0] = "internal list";
                                return new QuizManager(params, list.problems());
                            })
                            .orElseGet(() -> {
                                MathQuizProblemListLoader.clearActiveProblemList(playerName);
                                return new QuizManager(params);
                            });
                    } else if ("internal_quick_quiz".equals(source)) {
                        MathQuizProblemListLoader.clearActiveProblemList(playerName);
                        quiz = MathQuizProblemListLoader.loadQuickQuizForMinecraftPlayer(
                            playerName,
                            params.operation(),
                            MathQuestMod.CONFIG.resolvePlayerRealNames()
                        )
                            .map(list -> {
                                MathQuestMod.LOGGER.info("[MathQuest] Loaded {} quick-quiz problems for {} ({}) operation {}",
                                    list.problems().size(), playerName, list.realName(), list.operation());
                                sourceLabel[0] = "external list";
                                return new QuizManager(params, list.problems());
                            })
                            .orElseGet(() -> new QuizManager(params));
                    } else if ("internal_fluency_feast".equals(source)) {
                        MathQuizProblemListLoader.clearActiveProblemList(playerName);
                        String realName = MathQuestMod.CONFIG.resolveRealName(playerName);
                        var feastResult = FluencyFeastBridge.generateForRealName(
                            realName, MathQuestMod.CONFIG.resolveMathQuizActiveDir()
                        );
                        if (feastResult.isEmpty()) {
                            MathQuestMod.LOGGER.error(
                                "[MathQuest] Fluency feast produced no problems for {} ({}) — not falling back to control-panel preset",
                                playerName, realName);
                            if (this.minecraft != null && this.minecraft.player != null) {
                                this.minecraft.player.displayClientMessage(
                                    Component.literal("[MathQuest] Fluency feast could not generate problems. Check latest.log (node executable)."),
                                    false);
                            }
                            return;
                        }
                        var result = feastResult.get();
                        MathQuestMod.LOGGER.info("[MathQuest] Generated {} fluency-feast problems for {} ({})",
                            result.problems().size(), playerName, realName);
                        sourceLabel[0] = "fluency feast";
                        quiz = new QuizManager(params, result.problems());
                    } else {
                        MathQuizProblemListLoader.clearActiveProblemList(playerName);
                        quiz = new QuizManager(params);
                    }
                }
                QuizSessionOptions options = serverParams == null
                    ? ("internal_fluency_feast".equals(MathQuestMod.CONFIG.resolveInternalQuizSource(playerName))
                        ? QuizSessionOptions.fluencyFeast()
                        : QuizSessionOptions.standard())
                        .withTpCreditCompletionToken(TpCreditCompletionTracker.issue(playerName))
                    : serverOptions;
                this.minecraft.setScreen(new QuizScreen(quiz, sourceLabel[0], options));
            }
        ).bounds(centerX - 105, centerY + 20, 100, 20).build());

        this.addRenderableWidget(Button.builder(
            Component.literal("Not Now"),
            button -> {
                MathQuestClient.despawnNearbyNerds();
                this.onClose();
            }
        ).bounds(centerX + 5, centerY + 20, 100, 20).build());
    }

    @Override
    public void render(GuiGraphics context, int mouseX, int mouseY, float delta) {
        super.render(context, mouseX, mouseY, delta);

        int centerX = this.width / 2;
        int centerY = this.height / 2;

        String title = "Math Quest!";
        context.pose().pushMatrix();
        context.pose().translate(centerX, centerY - 50);
        context.pose().scale(2.0f, 2.0f);
        int titleWidth = this.font.width(title);
        context.drawString(this.font, title, -titleWidth / 2, 0, 0xFFFFFF00, true);
        context.pose().popMatrix();

        String prompt = "Want to try a Math Quest to earn some treasure?";
        int promptWidth = this.font.width(prompt);
        context.drawString(this.font, prompt, centerX - promptWidth / 2, centerY - 10, 0xFFFFFFFF, true);
    }

    @Override
    public boolean isPauseScreen() {
        return true;
    }
    private java.util.List<QuizManager.Problem> parseProblems(String problemsJson) {
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
}
