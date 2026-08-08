package com.kidgames.mathquest.screen;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.kidgames.mathquest.MathQuestClient;
import com.kidgames.mathquest.MathQuestMod;
import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.network.EarnTpCreditsPayload;
import com.kidgames.mathquest.network.GiveRewardPayload;
import com.kidgames.mathquest.network.QuizResultPayload;
import com.kidgames.mathquest.persistence.WrittenColumnSessionExporter;
import com.kidgames.mathquest.reward.TpCreditCompletionTracker;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayNetworking;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.components.EditBox;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;
import net.minecraft.sounds.SoundEvents;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import java.util.UUID;

public class WrittenColumnQuizScreen extends Screen {
    private final MathQuestConfig.EffectiveQuizParams params;
    private final String rewardsJson;
    private final String rewardMode;
    private final String tpCreditCompletionToken;
    private final boolean isMultiplayer;
    private final long shownAtMillis = System.currentTimeMillis();
    private final String operation;
    private final int factorA;
    private final int factorB;
    private final long correctAnswer;
    private EditBox evaluatorCode;
    private EditBox studentAnswer;
    private EditBox notes;
    private String statusMessage = "";
    private boolean submitted = false;
    public WrittenColumnQuizScreen(
        MathQuestConfig.EffectiveQuizParams params,
        String rewardsJson,
        String rewardMode,
        String tpCreditCompletionToken
    ) {
        super(Component.literal("Written Column Math"));
        this.params = params;
        this.rewardsJson = rewardsJson == null ? "[]" : rewardsJson;
        this.rewardMode = rewardMode == null ? "random" : rewardMode;
        this.tpCreditCompletionToken = tpCreditCompletionToken == null ? "" : tpCreditCompletionToken;
        this.isMultiplayer = Minecraft.getInstance().getSingleplayerServer() == null;
        this.operation = writtenOperation(params.operation());
        int[] factors = generateFactors(params, operation);
        this.factorA = factors[0];
        this.factorB = factors[1];
        this.correctAnswer = calculate(operation, factorA, factorB);
    }
    @Override
    protected void init() {
        int centerX = this.width / 2;
        int top = Math.max(36, this.height / 2 - 92);
        evaluatorCode = new EditBox(this.font, centerX - 120, top + 92, 240, 20, Component.literal("Evaluator code"));
        evaluatorCode.setMaxLength(64);
        studentAnswer = new EditBox(this.font, centerX - 120, top + 126, 240, 20, Component.literal("Student answer"));
        studentAnswer.setMaxLength(80);
        notes = new EditBox(this.font, centerX - 120, top + 160, 240, 20, Component.literal("Notes"));
        notes.setMaxLength(160);
        this.addRenderableWidget(evaluatorCode);
        this.addRenderableWidget(studentAnswer);
        this.addRenderableWidget(notes);
        this.addRenderableWidget(Button.builder(Component.literal("Correct"), button -> submit("correct"))
            .bounds(centerX - 160, top + 196, 96, 20).build());
        this.addRenderableWidget(Button.builder(Component.literal("Partial"), button -> submit("partial"))
            .bounds(centerX - 48, top + 196, 96, 20).build());
        this.addRenderableWidget(Button.builder(Component.literal("Needs Work"), button -> submit("needs_work"))
            .bounds(centerX + 64, top + 196, 96, 20).build());
        this.addRenderableWidget(Button.builder(Component.literal("Back"), button -> {
            MathQuestClient.despawnNearbyNerds();
            this.onClose();
        }).bounds(centerX - 50, top + 226, 100, 20).build());
    }
    private void submit(String evaluation) {
        if (submitted) return;
        String code = evaluatorCode.getValue().trim();
        if (code.isBlank()) {
            statusMessage = "Enter the evaluator code before recording the paper result.";
            return;
        }
        boolean codeAccepted = code.equals(MathQuestMod.CONFIG.writtenColumnEvaluatorCode);
        JsonObject result = resultJson(evaluation, codeAccepted, code);
        String rewardGiven = "none";
        if ("correct".equals(evaluation) && codeAccepted) {
            rewardGiven = giveReward();
        }
        result.addProperty("rewardGiven", rewardGiven);
        boolean completionRecorded = true;
        if (isMultiplayer) {
            ClientPlayNetworking.send(new QuizResultPayload(result.toString()));
        } else {
            completionRecorded = exportLocal(result);
            if (completionRecorded && !tpCreditCompletionToken.isBlank()
                && this.minecraft != null && this.minecraft.player != null) {
                TpCreditCompletionTracker.markCompleted(
                    this.minecraft.player.getName().getString(),
                    tpCreditCompletionToken
                );
            }
        }
        if (completionRecorded && !tpCreditCompletionToken.isBlank()) {
            ClientPlayNetworking.send(new EarnTpCreditsPayload(tpCreditCompletionToken));
        }
        submitted = true;
        statusMessage = "Recorded: " + labelFor(evaluation) + (codeAccepted ? "" : " (code did not match)");
    }
    private JsonObject resultJson(String evaluation, boolean codeAccepted, String code) {
        JsonObject root = new JsonObject();
        root.addProperty("quizType", "written_column_arithmetic");
        root.addProperty("operation", operation);
        root.addProperty("factorA", factorA);
        root.addProperty("factorB", factorB);
        root.addProperty("correctAnswer", correctAnswer);
        root.addProperty("promptText", promptText());
        root.addProperty("studentAnswer", studentAnswer.getValue().trim());
        root.addProperty("evaluation", evaluation);
        root.addProperty("evaluatorCode", code);
        root.addProperty("evaluatorCodeAccepted", codeAccepted);
        root.addProperty("notes", notes.getValue().trim());
        root.addProperty("responseTimeMs", System.currentTimeMillis() - shownAtMillis);
        root.addProperty("problemsTotal", 1);
        root.addProperty("problemsCorrect", "correct".equals(evaluation) ? 1 : 0);
        root.addProperty("tpCreditEligible", true);
        root.addProperty("tpCreditCompletionToken", tpCreditCompletionToken);
        return root;
    }
    private String giveReward() {
        String playerName = (this.minecraft != null && this.minecraft.player != null)
            ? this.minecraft.player.getName().getString()
            : "unknown";
        List<MathQuestConfig.RewardEntry> rewards = isMultiplayer
            ? parseRewards(rewardsJson)
            : MathQuestMod.CONFIG.resolveRewardPlanForPlayer(playerName).entries();
        if (rewards.isEmpty()) return "none";
        List<MathQuestConfig.RewardEntry> toGive = new ArrayList<>();
        if ("all".equals(rewardMode)) {
            toGive.addAll(rewards);
        } else {
            toGive.add(rewards.get(new Random().nextInt(rewards.size())));
        }
        StringBuilder out = new StringBuilder();
        for (MathQuestConfig.RewardEntry entry : toGive) {
            ClientPlayNetworking.send(new GiveRewardPayload(entry.item, entry.count));
            if (out.length() > 0) out.append(",");
            out.append(entry.item).append(":").append(entry.count);
        }
        if (this.minecraft != null && this.minecraft.player != null) {
            this.minecraft.player.playSound(SoundEvents.PLAYER_LEVELUP, 1.0f, 1.0f);
        }
        return out.toString();
    }
    private boolean exportLocal(JsonObject result) {
        try {
            String username = (this.minecraft != null && this.minecraft.player != null)
                ? this.minecraft.player.getName().getString()
                : "unknown";
            String realName = MathQuestMod.CONFIG.resolveRealName(username);
            UUID playerUuid = (this.minecraft != null && this.minecraft.player != null)
                ? this.minecraft.player.getUUID()
                : null;
            WrittenColumnSessionExporter.export(result, realName, playerUuid);
            return true;
        } catch (Exception e) {
            MathQuestMod.LOGGER.error("[MathQuest] Failed to export written-column result: {}", e.getMessage());
            return false;
        }
    }
    private List<MathQuestConfig.RewardEntry> parseRewards(String json) {
        List<MathQuestConfig.RewardEntry> out = new ArrayList<>();
        try {
            JsonArray arr = JsonParser.parseString(json).getAsJsonArray();
            for (var el : arr) {
                JsonObject obj = el.getAsJsonObject();
                out.add(new MathQuestConfig.RewardEntry(obj.get("item").getAsString(), obj.get("count").getAsInt()));
            }
        } catch (Exception e) {
            MathQuestMod.LOGGER.error("[MathQuest] Failed to parse written-column rewards: {}", e.getMessage());
        }
        return out;
    }
    @Override
    public void render(GuiGraphics context, int mouseX, int mouseY, float delta) {
        super.render(context, mouseX, mouseY, delta);
        renderContent(new TextSink() {
            public void draw(String text, int x, int y, int color) {
                context.drawString(font, text, x, y, color, true);
            }
        });
    }
    private void renderContent(TextSink sink) {
        int centerX = this.width / 2;
        int top = Math.max(36, this.height / 2 - 92);
        drawCentered(sink, "Written Column Math", centerX, top, 0xFFFFFF00);
        drawCentered(sink, "Solve on paper, then have an evaluator record the result.", centerX, top + 22, 0xFFFFFFFF);
        drawCentered(sink, "Line up the columns and show the work.", centerX, top + 38, 0xFFAAAAAA);
        drawCentered(sink, verticalLine(factorA), centerX, top + 58, 0xFFFFFFFF);
        drawCentered(sink, symbol(operation) + " " + verticalLine(factorB), centerX, top + 72, 0xFFFFFFFF);
        drawCentered(sink, "Evaluator code", centerX, top + 82, 0xFFAAAAAA);
        drawCentered(sink, "Student answer", centerX, top + 116, 0xFFAAAAAA);
        drawCentered(sink, "Notes", centerX, top + 150, 0xFFAAAAAA);
        if (!statusMessage.isBlank()) {
            drawCentered(sink, statusMessage, centerX, top + 254, submitted ? 0xFF55FF55 : 0xFFFFAA55);
        }
    }
    private void drawCentered(TextSink sink, String text, int centerX, int y, int color) {
        int textWidth = this.font.width(text);
        sink.draw(text, centerX - textWidth / 2, y, color);
    }
    private String promptText() {
        return "Solve on paper: " + factorA + " " + symbol(operation) + " " + factorB;
    }
    private static String verticalLine(int value) {
        return String.format("%4d", value);
    }
    private static String writtenOperation(String raw) {
        String op = MathQuestConfig.normalizeOperation(raw);
        return switch (op) {
            case "addition", "subtraction" -> op;
            default -> "multiplication";
        };
    }
    private static int[] generateFactors(MathQuestConfig.EffectiveQuizParams params, String operation) {
        Random random = new Random();
        int a = 20 + random.nextInt(780);
        int b = "multiplication".equals(operation) ? 2 + random.nextInt(10) : 20 + random.nextInt(780);
        if ("subtraction".equals(operation) && b > a) {
            int t = a;
            a = b;
            b = t;
        }
        return new int[] { a, b };
    }
    private static long calculate(String operation, int a, int b) {
        return switch (operation) {
            case "addition" -> (long) a + b;
            case "subtraction" -> (long) a - b;
            default -> (long) a * b;
        };
    }
    private static String symbol(String operation) {
        return switch (operation) {
            case "addition" -> "+";
            case "subtraction" -> "-";
            default -> "x";
        };
    }
    private static String labelFor(String evaluation) {
        return switch (evaluation) {
            case "correct" -> "Correct";
            case "partial" -> "Partial";
            default -> "Needs Work";
        };
    }
    private interface TextSink {
        void draw(String text, int x, int y, int color);
    }
    @Override
    public boolean isPauseScreen() {
        return true;
    }
}
