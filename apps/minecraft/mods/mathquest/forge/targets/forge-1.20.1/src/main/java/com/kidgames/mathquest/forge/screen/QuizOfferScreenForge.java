package com.kidgames.mathquest.forge.screen;

import com.google.gson.JsonArray;
import com.google.gson.JsonParser;
import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.forge.MathQuestClientForge;
import com.kidgames.mathquest.forge.net.MathQuestNetworkForge;
import com.kidgames.mathquest.net.OpenQuizData;
import com.kidgames.mathquest.platform.MathQuestLog;
import com.kidgames.mathquest.quiz.QuizManager;
import com.kidgames.mathquest.quiz.QuizSessionOptions;
import com.kidgames.mathquest.server.OpenQuizPayloadBuilder;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;

import java.util.ArrayList;
import java.util.List;

public class QuizOfferScreenForge extends Screen {
    private final MathQuestNetworkForge.OpenQuizPacket payload;

    public QuizOfferScreenForge() {
        this(null);
    }

    public QuizOfferScreenForge(MathQuestNetworkForge.OpenQuizPacket payload) {
        super(Component.literal("Math Quest!"));
        this.payload = payload;
    }

    @Override
    protected void init() {
        int centerX = this.width / 2;
        int centerY = this.height / 2;
        this.addRenderableWidget(Button.builder(
            Component.literal("Let's Go!"),
            button -> {
                String playerName = (this.minecraft != null && this.minecraft.player != null)
                    ? this.minecraft.player.getName().getString()
                    : null;
                OpenQuizData data = resolveOpenQuizData(playerName);
                openQuizFromData(data, playerName);
            }
        ).bounds(centerX - 60, centerY, 120, 20).build());

        this.addRenderableWidget(Button.builder(
            Component.literal("Not Now"),
            button -> {
                if ("npc".equals(MathQuestConfig.INSTANCE.quizMode)) {
                    MathQuestClientForge.despawnNearbyNerds();
                }
                this.onClose();
            }
        ).bounds(centerX - 60, centerY + 30, 120, 20).build());
    }

    private OpenQuizData resolveOpenQuizData(String playerName) {
        if (payload != null) {
            return payload.toData();
        }
        if (playerName == null || playerName.isBlank()) {
            playerName = "unknown";
        }
        return OpenQuizPayloadBuilder.create(playerName);
    }

    private void openQuizFromData(OpenQuizData data, String playerName) {
        if ("written_column_arithmetic".equals(MathQuestConfig.normalizeQuizType(data.quizType()))) {
            MathQuestConfig.EffectiveQuizParams params = new MathQuestConfig.EffectiveQuizParams(
                data.minNumber(),
                data.maxNumber(),
                data.operation(),
                data.problemsPerQuiz()
            );
            QuizSessionOptions options = QuizSessionOptions.fromJson(data.optionsJson());
            this.minecraft.setScreen(new WrittenColumnQuizScreenForge(
                params,
                data.rewardsJson(),
                data.rewardMode(),
                options.tpCreditCompletionToken()
            ));
            return;
        }
        MathQuestConfig.EffectiveQuizParams params = new MathQuestConfig.EffectiveQuizParams(
            data.minNumber(),
            data.maxNumber(),
            data.operation(),
            data.problemsPerQuiz()
        );
        List<QuizManager.Problem> problems = parseProblems(data.problemsJson());
        if (data.fluencyFeastMode() && problems.isEmpty()) {
            MathQuestLog.LOGGER.error(
                "[MathQuest/Forge] Fluency feast produced no problems for {} — not falling back to control-panel preset",
                playerName);
            if (this.minecraft != null && this.minecraft.player != null) {
                this.minecraft.player.displayClientMessage(
                    Component.literal("[MathQuest] Fluency feast could not generate problems. Check latest.log (node executable)."),
                    false);
            }
            this.onClose();
            return;
        }
        QuizManager quiz = problems.isEmpty()
            ? new QuizManager(params)
            : new QuizManager(params, problems);
        QuizSessionOptions options = data.fluencyFeastMode() && (data.optionsJson() == null || data.optionsJson().isBlank())
            ? QuizSessionOptions.fluencyFeast()
            : QuizSessionOptions.fromJson(data.optionsJson());
        quiz.setSessionOptions(options);
        String sourceLabel = resolveSourceLabel(data, problems);
        this.minecraft.setScreen(new QuizScreenForge(
            quiz,
            sourceLabel,
            options,
            data.rewardsJson(),
            data.rewardMode()
        ));
    }

    private static String resolveSourceLabel(OpenQuizData data, List<QuizManager.Problem> problems) {
        if (data.fluencyFeastMode()) return "fluency feast";
        if (!problems.isEmpty()) return "external list";
        return "generated";
    }

    @Override
    public void render(GuiGraphics graphics, int mouseX, int mouseY, float partialTick) {
        this.renderBackground(graphics);
        super.render(graphics, mouseX, mouseY, partialTick);
        graphics.drawCenteredString(this.font, this.title, this.width / 2, this.height / 2 - 40, 0xFFFFFF);
        graphics.drawCenteredString(
            this.font,
            Component.literal("Ready for a math quiz?"),
            this.width / 2,
            this.height / 2 - 24,
            0xAAAAAA
        );
    }

    @Override
    public boolean isPauseScreen() {
        return true;
    }

    private List<QuizManager.Problem> parseProblems(String problemsJson) {
        List<QuizManager.Problem> out = new ArrayList<>();
        if (problemsJson == null || "[]".equals(problemsJson)) return out;
        try {
            JsonArray arr = JsonParser.parseString(problemsJson).getAsJsonArray();
            for (var el : arr) {
                var obj = el.getAsJsonObject();
                out.add(QuizManager.Problem.create(
                    obj.get("operation").getAsString(),
                    obj.get("factorA").getAsInt(),
                    obj.get("factorB").getAsInt()
                ));
            }
        } catch (Exception e) {
            MathQuestLog.LOGGER.error("[MathQuest/Forge] Failed to parse quiz problems: {}", e.getMessage());
        }
        return out;
    }
}
