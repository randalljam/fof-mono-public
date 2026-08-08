package com.kidgames.mathquest.forge.screen;

import com.google.gson.JsonArray;
import com.google.gson.JsonNull;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.forge.MathQuestClientForge;
import com.kidgames.mathquest.forge.net.MathQuestNetworkForge;
import com.kidgames.mathquest.forge.platform.ForgePlatformNetwork;
import com.kidgames.mathquest.persistence.MathQuizSessionPersistence;
import com.kidgames.mathquest.platform.PlatformNetwork;
import com.kidgames.mathquest.platform.PlayerContext;
import com.kidgames.mathquest.quiz.QuizManager;
import com.kidgames.mathquest.quiz.QuizSessionOptions;
import com.kidgames.mathquest.reward.TpCreditCompletionTracker;
import com.kidgames.mathquest.server.QuizResultProcessor;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;
import net.minecraft.sounds.SoundEvents;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import java.util.UUID;

public class QuizResultScreenForge extends Screen {
    private static final int QUEST_GOLD = 0xFFFFAA00;
    private static final int QUEST_GOLD_DIM = 0xFFFFFFAA;
    private static final PlatformNetwork CLIENT_NETWORK = new ForgePlatformNetwork.Client();
    private static QuizResultScreenForge activeFluencyResultScreen;

    private final QuizManager quiz;
    private final QuizSessionOptions sessionOptions;
    private final String deliveredRewardsJson;
    private final String deliveredRewardMode;
    private String rewardDescription = "";
    private String fluencyReadout = "";
    private boolean fluencyCalculating = false;
    private boolean rewardsGiven = false;
    private boolean tpCreditsRequested = false;
    private final List<Button> rewardChoiceButtons = new ArrayList<>();

    public QuizResultScreenForge(QuizManager quiz) {
        this(quiz, QuizSessionOptions.standard());
    }

    public QuizResultScreenForge(QuizManager quiz, QuizSessionOptions sessionOptions) {
        this(quiz, sessionOptions, null, null);
    }

    public QuizResultScreenForge(
        QuizManager quiz,
        QuizSessionOptions sessionOptions,
        String deliveredRewardsJson,
        String deliveredRewardMode
    ) {
        super(Component.literal("Quiz Complete!"));
        this.quiz = quiz;
        this.sessionOptions = sessionOptions == null ? QuizSessionOptions.standard() : sessionOptions;
        this.deliveredRewardsJson = deliveredRewardsJson;
        this.deliveredRewardMode = deliveredRewardMode;
    }

    @Override
    protected void init() {
        int centerX = this.width / 2;
        this.addRenderableWidget(Button.builder(
            Component.literal("Back to Adventure!"),
            button -> {
                if ("npc".equals(MathQuestConfig.INSTANCE.quizMode)) {
                    MathQuestClientForge.despawnNearbyNerds();
                }
                this.onClose();
            }
        ).bounds(centerX - 60, this.height - 40, 120, 20).build());

        if (!rewardsGiven) {
            if (sessionOptions.fluencyFeastMode()) {
                activeFluencyResultScreen = this;
                fluencyCalculating = true;
                fluencyReadout = "Calculating fluency...";
                rewardDescription = "";
                sendFluencyFeastResult();
                rewardsGiven = true;
            } else {
                giveRewards();
            }
        }
    }

    private void requestTpCreditsOnce() {
        if (tpCreditsRequested
            || !sessionOptions.tpCreditEligible()
            || sessionOptions.tpCreditCompletionToken().isBlank()) return;
        tpCreditsRequested = true;
        try {
            MathQuestNetworkForge.sendToServer(
                new MathQuestNetworkForge.EarnTpCreditsPacket(sessionOptions.tpCreditCompletionToken())
            );
        } catch (Exception e) {
            com.kidgames.mathquest.platform.MathQuestLog.LOGGER.error(
                "[MathQuest/Forge] Failed to request TP credits: {}", e.getMessage());
        }
    }

    public static void applyServerFluencyResult(
        int before,
        int after,
        String rewardDescriptionText,
        String rewardsJson,
        String rewardMode
    ) {
        QuizResultScreenForge screen = activeFluencyResultScreen;
        if (screen == null || screen.minecraft == null) return;
        String readout = "Fluent: " + before + "% -> " + after + "%";
        screen.minecraft.execute(() -> {
            screen.fluencyCalculating = false;
            screen.fluencyReadout = readout;
            List<MathQuestConfig.RewardEntry> choiceRewards = screen.parseServerRewards(rewardsJson);
            if ("choose".equals(MathQuestConfig.normalizeRewardGroupMode(rewardMode)) && choiceRewards.size() > 1) {
                screen.showRewardChoiceButtons(choiceRewards);
                screen.rewardDescription = "Choose your fluency reward:";
                return;
            }
            if (screen.quiz.getCorrectCount() == 0) {
                screen.rewardDescription = "Keep practicing to earn rewards!";
            } else if (rewardDescriptionText == null || rewardDescriptionText.isBlank()) {
                screen.rewardDescription = after - before >= 1
                    ? "Fluency improved!"
                    : "No fluency improvement reward this time.";
            } else {
                screen.rewardDescription = rewardDescriptionText;
            }
            activeFluencyResultScreen = null;
        });
    }

    @Override
    public void removed() {
        if (activeFluencyResultScreen == this) {
            activeFluencyResultScreen = null;
        }
        clearRewardChoiceButtons();
        super.removed();
    }

    private void sendFluencyFeastResult() {
        try {
            JsonObject root = buildResultRoot("server");
            root.addProperty("fluencyFeastMode", true);
            CLIENT_NETWORK.sendQuizResultToServer(root.toString());
            requestTpCreditsOnce();
        } catch (Exception e) {
            com.kidgames.mathquest.platform.MathQuestLog.LOGGER.error(
                "[MathQuest/Forge] Failed to send fluency feast result: {}", e.getMessage());
            notifyChat("[MathQuest] Failed to send fluency feast result: " + e.getMessage());
        }
    }

    private void giveRewards() {
        String username = (this.minecraft != null && this.minecraft.player != null)
            ? this.minecraft.player.getName().getString()
            : "unknown";
        if (quiz.getCorrectCount() == 0) {
            rewardDescription = "Keep practicing to earn rewards!";
            recordResult("none");
            rewardsGiven = true;
            return;
        }

        List<MathQuestConfig.RewardEntry> rewards;
        String rewardMode;
        if (deliveredRewardsJson != null) {
            rewards = parseServerRewards(deliveredRewardsJson);
            rewardMode = MathQuestConfig.normalizeRewardGroupMode(deliveredRewardMode);
        } else {
            MathQuestConfig.RewardPlan plan = MathQuestConfig.INSTANCE.resolveRewardPlanForPlayer(username);
            rewards = plan.entries();
            rewardMode = MathQuestConfig.normalizeRewardGroupMode(plan.mode());
        }
        String rewardLog = "none";

        if (rewards != null && !rewards.isEmpty()) {
            if ("choose".equals(rewardMode) && rewards.size() > 1) {
                showRewardChoiceButtons(rewards);
                rewardDescription = "Choose your reward:";
                rewardsGiven = false;
                return;
            }
            if ("random".equals(rewardMode)) {
                MathQuestConfig.RewardEntry entry = rewards.get(new Random().nextInt(rewards.size()));
                CLIENT_NETWORK.sendGiveRewardToServer(entry.item, entry.count);
                rewardDescription = QuizResultProcessor.formatRewardDescription(entry);
                rewardLog = entry.item + ":" + entry.count;
            } else {
                StringBuilder desc = new StringBuilder();
                StringBuilder log = new StringBuilder();
                for (MathQuestConfig.RewardEntry entry : rewards) {
                    CLIENT_NETWORK.sendGiveRewardToServer(entry.item, entry.count);
                    if (desc.length() > 0) desc.append(", ");
                    desc.append(QuizResultProcessor.formatRewardDescription(entry));
                    if (log.length() > 0) log.append(",");
                    log.append(entry.item).append(":").append(entry.count);
                }
                rewardDescription = desc.toString();
                rewardLog = log.toString();
            }
            if (this.minecraft != null && this.minecraft.player != null) {
                this.minecraft.player.playSound(SoundEvents.PLAYER_LEVELUP, 1.0f, 1.0f);
            }
        } else {
            rewardDescription = "Great job!";
        }

        recordResult(rewardLog);
        rewardsGiven = true;
    }

    private void showRewardChoiceButtons(List<MathQuestConfig.RewardEntry> entries) {
        clearRewardChoiceButtons();
        int centerX = this.width / 2;
        int y = this.height / 2 + 76;
        int index = 0;
        for (MathQuestConfig.RewardEntry entry : entries) {
            String label = QuizResultProcessor.formatRewardDescription(entry);
            Button button = Button.builder(Component.literal(label), btn -> pickChosenReward(entry))
                .bounds(centerX - 110, y + index * 24, 220, 20)
                .build();
            rewardChoiceButtons.add(button);
            addRenderableWidget(button);
            index++;
        }
    }

    private void pickChosenReward(MathQuestConfig.RewardEntry entry) {
        CLIENT_NETWORK.sendGiveRewardToServer(entry.item, entry.count);
        if (this.minecraft != null && this.minecraft.player != null) {
            this.minecraft.player.playSound(SoundEvents.PLAYER_LEVELUP, 1.0f, 1.0f);
        }
        rewardDescription = QuizResultProcessor.formatRewardDescription(entry);
        String rewardLog = entry.item + ":" + entry.count;
        clearRewardChoiceButtons();
        if (!sessionOptions.fluencyFeastMode()) {
            recordResult(rewardLog);
        }
        rewardsGiven = true;
        activeFluencyResultScreen = null;
    }

    private void clearRewardChoiceButtons() {
        for (Button button : rewardChoiceButtons) {
            removeWidget(button);
        }
        rewardChoiceButtons.clear();
    }

    private void recordResult(String rewardGiven) {
        if (isIntegratedSingleplayer()) {
            if (exportSessionLocally()) {
                settleLocalTpCreditSession();
                requestTpCreditsOnce();
            }
            return;
        }
        sendResultToServer(rewardGiven);
        requestTpCreditsOnce();
    }

    private boolean isIntegratedSingleplayer() {
        return this.minecraft != null && this.minecraft.getSingleplayerServer() != null;
    }

    private boolean exportSessionLocally() {
        if (this.minecraft == null || this.minecraft.player == null) return false;
        try {
            String username = this.minecraft.player.getName().getString();
            UUID playerUuid = this.minecraft.player.getUUID();
            String realName = MathQuestConfig.INSTANCE.resolveRealName(username);
            String mode = MathQuestConfig.INSTANCE.quizMode;
            com.kidgames.mathquest.platform.MathQuestLog.LOGGER.info(
                "[MathQuest/Forge] Exporting completed quiz for {} (mode={}, {} correct/{} total)",
                username, mode, quiz.getCorrectCount(), quiz.getTotalProblems());
            PlayerContext player = new PlayerContext(username, playerUuid);
            MathQuizSessionPersistence.persistCompletedQuiz(
                quiz,
                realName,
                playerUuid,
                player,
                null,
                this::notifyChat
            );
            return true;
        } catch (RuntimeException e) {
            notifyChat("[MathQuest] Failed to export session: " + e.getMessage());
            com.kidgames.mathquest.platform.MathQuestLog.LOGGER.error(
                "[MathQuest/Forge] Failed to export session locally: {}", e.getMessage(), e);
            return false;
        }
    }

    private void settleLocalTpCreditSession() {
        String token = sessionOptions.tpCreditCompletionToken();
        if (token == null || token.isBlank() || this.minecraft == null || this.minecraft.player == null) return;
        String playerName = this.minecraft.player.getName().getString();
        if (sessionOptions.tpCreditEligible()) {
            TpCreditCompletionTracker.markCompleted(playerName, token);
        } else {
            TpCreditCompletionTracker.cancel(playerName, token);
        }
    }

    private void sendResultToServer(String rewardGiven) {
        try {
            CLIENT_NETWORK.sendQuizResultToServer(buildResultRoot(rewardGiven).toString());
        } catch (Exception e) {
            com.kidgames.mathquest.platform.MathQuestLog.LOGGER.error(
                "[MathQuest/Forge] Failed to send quiz result to server: {}", e.getMessage());
            notifyChat("[MathQuest] Failed to send quiz result to server: " + e.getMessage());
        }
    }

    private void notifyChat(String message) {
        if (this.minecraft != null && this.minecraft.player != null) {
            this.minecraft.player.displayClientMessage(Component.literal(message), false);
        }
    }

    private JsonObject buildResultRoot(String rewardGiven) {
        JsonObject root = new JsonObject();
        root.addProperty("operation", quiz.getOperation());
        root.addProperty("problemsTotal", quiz.getTotalProblems());
        root.addProperty("problemsCorrect", quiz.getCorrectCount());
        root.addProperty("rewardGiven", rewardGiven);
        root.addProperty("tpCreditEligible", sessionOptions.tpCreditEligible());
        root.addProperty("tpCreditCompletionToken", sessionOptions.tpCreditCompletionToken());
        JsonArray problemsArray = new JsonArray();
        for (QuizManager.Problem p : quiz.getProblems()) {
            JsonObject pObj = new JsonObject();
            pObj.addProperty("operation", p.operation);
            pObj.addProperty("factorA", p.factorA);
            pObj.addProperty("factorB", p.factorB);
            pObj.addProperty("correctAnswer", p.correctAnswer);
            if (p.playerAnswer != null) {
                pObj.addProperty("playerAnswer", p.playerAnswer);
            } else {
                pObj.add("playerAnswer", JsonNull.INSTANCE);
            }
            pObj.addProperty("isCorrect", p.isCorrect);
            pObj.addProperty("responseTimeMs", p.responseTimeMs);
            JsonArray flags = new JsonArray();
            for (String flag : p.flags) {
                flags.add(flag);
            }
            pObj.add("flags", flags);
            problemsArray.add(pObj);
        }
        root.add("problems", problemsArray);
        return root;
    }

    private List<MathQuestConfig.RewardEntry> parseServerRewards(String rewardsJson) {
        List<MathQuestConfig.RewardEntry> out = new ArrayList<>();
        if (rewardsJson == null || rewardsJson.isBlank()) return out;
        try {
            JsonArray arr = JsonParser.parseString(rewardsJson).getAsJsonArray();
            for (var el : arr) {
                JsonObject obj = el.getAsJsonObject();
                out.add(new MathQuestConfig.RewardEntry(
                    obj.get("item").getAsString(),
                    obj.get("count").getAsInt()
                ));
            }
        } catch (Exception e) {
            com.kidgames.mathquest.platform.MathQuestLog.LOGGER.error(
                "[MathQuest/Forge] Failed to parse server rewards: {}", e.getMessage());
        }
        return out;
    }

    @Override
    public void render(GuiGraphics graphics, int mouseX, int mouseY, float partialTick) {
        this.renderBackground(graphics);
        super.render(graphics, mouseX, mouseY, partialTick);

        int centerX = this.width / 2;
        int y = 40;

        String titleStr = "Quiz Complete!";
        graphics.pose().pushPose();
        graphics.pose().translate(centerX, y, 0);
        graphics.pose().scale(2.0f, 2.0f, 1.0f);
        int titleWidth = this.font.width(titleStr);
        graphics.drawString(this.font, titleStr, -titleWidth / 2, 0, 0xFFFFFF00, true);
        graphics.pose().popPose();
        y += 40;

        String scoreText = "You got " + quiz.getCorrectCount() + " out of " + quiz.getTotalProblems() + " correct!";
        drawCenteredText(graphics, scoreText, centerX, y, 0xFFFFFFFF);
        y += 20;

        String encouragement;
        int encourageColor;
        if (quiz.getCorrectCount() == quiz.getTotalProblems()) {
            encouragement = "PERFECT SCORE!";
            encourageColor = 0xFFFFD700;
        } else if (quiz.getCorrectCount() >= quiz.getTotalProblems() * 0.7) {
            encouragement = "Great job!";
            encourageColor = 0xFF55FF55;
        } else {
            encouragement = "Nice try! Keep practicing!";
            encourageColor = 0xFF55AAFF;
        }
        drawCenteredText(graphics, encouragement, centerX, y, encourageColor);

        if (sessionOptions.fluencyFeastMode()) {
            int centerY = this.height / 2;
            if (!fluencyReadout.isEmpty()) {
                drawScaledCenteredText(graphics, fluencyReadout, centerX, centerY - 28, 2.5f, QUEST_GOLD);
            } else if (fluencyCalculating) {
                drawScaledCenteredText(graphics, "Calculating fluency...", centerX, centerY - 28, 2.0f, QUEST_GOLD_DIM);
            }
            if (!rewardDescription.isEmpty()) {
                drawScaledCenteredText(
                    graphics,
                    "You earned: " + rewardDescription,
                    centerX,
                    centerY + 32,
                    2.0f,
                    QUEST_GOLD
                );
            }
        } else {
            y += 30;
            if (!rewardDescription.isEmpty()) {
                drawCenteredText(graphics, "You earned: " + rewardDescription, centerX, y + 20, 0xFF55FF55);
            }
        }
    }

    private void drawCenteredText(GuiGraphics graphics, String text, int centerX, int y, int color) {
        int textWidth = this.font.width(text);
        graphics.drawString(this.font, text, centerX - textWidth / 2, y, color, true);
    }

    private void drawScaledCenteredText(
        GuiGraphics graphics,
        String text,
        int centerX,
        int centerY,
        float scale,
        int color
    ) {
        graphics.pose().pushPose();
        graphics.pose().translate(centerX, centerY, 0);
        graphics.pose().scale(scale, scale, 1.0f);
        int textWidth = this.font.width(text);
        graphics.drawString(this.font, text, -textWidth / 2, 0, color, true);
        graphics.pose().popPose();
    }

    @Override
    public boolean isPauseScreen() {
        return true;
    }
}
