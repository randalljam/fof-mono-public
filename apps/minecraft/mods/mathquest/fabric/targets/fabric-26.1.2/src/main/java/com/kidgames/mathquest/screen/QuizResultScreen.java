package com.kidgames.mathquest.screen;

import com.kidgames.mathquest.MathQuestClient;
import com.kidgames.mathquest.MathQuestMod;
import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.persistence.FluencyFeastBridge;
import com.kidgames.mathquest.persistence.MathQuizSessionIngestor;
import com.kidgames.mathquest.persistence.QuizDatabase;
import com.kidgames.mathquest.persistence.SessionExporter;
import com.kidgames.mathquest.network.EarnTpCreditsPayload;
import com.kidgames.mathquest.network.GiveRewardPayload;
import com.kidgames.mathquest.network.QuizResultPayload;
import com.kidgames.mathquest.quiz.QuizManager;
import com.kidgames.mathquest.quiz.QuizSessionOptions;
import com.kidgames.mathquest.reward.TpCreditCompletionTracker;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayNetworking;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;
import net.minecraft.sounds.SoundEvents;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.Random;
import java.util.UUID;

public class QuizResultScreen extends Screen {
    /** Matches Minecraft quest title gold (`/title … {"color":"gold"}`). */
    private static final int QUEST_GOLD = 0xFFFFAA00;
    private static final int QUEST_GOLD_DIM = 0xFFFFFFAA;
    private static QuizResultScreen activeFluencyResultScreen;
    private final QuizManager quiz;
    private final long sessionId;
    private final boolean isMultiplayer;
    private final QuizSessionOptions sessionOptions;
    private String rewardDescription = "";
    private String fluencyReadout = "";
    private boolean fluencyCalculating = false;
    private boolean rewardsGiven = false;
    private boolean tpCreditsRequested = false;
    private final List<Button> rewardChoiceButtons = new ArrayList<>();

    public QuizResultScreen(QuizManager quiz, long sessionId) {
        this(quiz, sessionId, QuizSessionOptions.standard());
    }

    public QuizResultScreen(QuizManager quiz, long sessionId, QuizSessionOptions sessionOptions) {
        super(Component.literal("Quiz Complete!"));
        this.quiz = quiz;
        this.sessionId = sessionId;
        this.sessionOptions = sessionOptions == null ? QuizSessionOptions.standard() : sessionOptions;
        this.isMultiplayer = Minecraft.getInstance().getSingleplayerServer() == null;
    }

    @Override
    protected void init() {
        int centerX = this.width / 2;

        this.addRenderableWidget(Button.builder(
            Component.literal("Back to Adventure!"),
            button -> {
                MathQuestClient.despawnNearbyNerds();
                this.onClose();
            }
        ).bounds(centerX - 60, this.height - 40, 120, 20).build());

        if (!rewardsGiven) {
            if (sessionOptions.fluencyFeastMode() && !isMultiplayer) {
                fluencyCalculating = true;
                fluencyReadout = "Calculating fluency...";
                new Thread(this::finishFluencyFeastSingleplayer, "MathQuest-FluencyFeast").start();
            } else if (sessionOptions.fluencyFeastMode() && isMultiplayer) {
                activeFluencyResultScreen = this;
                fluencyCalculating = true;
                fluencyReadout = "Calculating fluency...";
                rewardDescription = "";
                sendFluencyFeastMultiplayerResult();
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
            ClientPlayNetworking.send(new EarnTpCreditsPayload(sessionOptions.tpCreditCompletionToken()));
        } catch (Exception e) {
            MathQuestMod.LOGGER.error("[MathQuest] Failed to request TP credits: {}", e.getMessage());
        }
    }

    public static void applyServerFluencyResult(
        int before,
        int after,
        String rewardDescriptionText,
        String rewardsJson,
        String rewardMode
    ) {
        QuizResultScreen screen = activeFluencyResultScreen;
        if (screen == null || screen.minecraft == null) return;
        String readout = "Fluent: " + before + "% -> " + after + "%";
        screen.minecraft.execute(() -> {
            screen.fluencyCalculating = false;
            screen.fluencyReadout = readout;
            List<MathQuestConfig.RewardEntry> choiceRewards = screen.parseServerRewards(rewardsJson);
            if ("choose".equals(MathQuestConfig.normalizeRewardGroupMode(rewardMode)) && choiceRewards.size() > 1) {
                screen.showRewardChoiceButtons(choiceRewards, false);
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
            MathQuestClient.clearActiveRewardPlan();
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

    private void finishFluencyFeastSingleplayer() {
        String username = (this.minecraft != null && this.minecraft.player != null)
            ? this.minecraft.player.getName().getString()
            : "unknown";
        String realName = MathQuestMod.CONFIG.resolveRealName(username);
        Path activeDir = MathQuestMod.CONFIG.resolveMathQuizActiveDir();
        int before = FluencyFeastBridge.percentForRealName(realName, activeDir)
            .map(FluencyFeastBridge.PercentResult::percent)
            .orElse(0);
        String rewardLog = "none";
        try {
            UUID playerUuid = (this.minecraft != null && this.minecraft.player != null)
                ? this.minecraft.player.getUUID()
                : null;
            Path path = SessionExporter.exportSession(quiz, realName, playerUuid);
            MathQuizSessionIngestor.ingest(path, realName);
            MathQuestMod.LOGGER.info("[MathQuest] Fluency feast session exported to {}", path);
        } catch (Exception e) {
            MathQuestMod.LOGGER.error("[MathQuest] Fluency feast export failed: {}", e.getMessage());
        }
        int after = FluencyFeastBridge.percentForRealName(realName, activeDir)
            .map(FluencyFeastBridge.PercentResult::percent)
            .orElse(before);
        boolean improved = after - before >= 1;
        RewardDecision decision = chooseReward(improved, username);
        String readout = "Fluent: " + before + "% -> " + after + "%";
        int finalBefore = before;
        int finalAfter = after;
        if (this.minecraft != null) {
            this.minecraft.execute(() -> applyFluencyFinish(finalBefore, finalAfter, readout, decision));
        }
    }

    private void applyFluencyFinish(int before, int after, String readout, RewardDecision decision) {
        fluencyCalculating = false;
        fluencyReadout = readout;
        if (quiz.getCorrectCount() == 0) {
            rewardDescription = "Keep practicing to earn rewards!";
            QuizDatabase.getInstance().endSession(sessionId, quiz.getCorrectCount(), "none");
            rewardsGiven = true;
            settleLocalTpCreditSession();
            requestTpCreditsOnce();
            return;
        }
        if (finishRewardDecision(decision)) {
            QuizDatabase.getInstance().endSession(sessionId, quiz.getCorrectCount(), decision.log());
            rewardsGiven = true;
            settleLocalTpCreditSession();
            requestTpCreditsOnce();
        }
    }

    private void sendFluencyFeastMultiplayerResult() {
        try {
            com.google.gson.JsonObject root = buildResultRoot("server");
            root.addProperty("fluencyFeastMode", true);
            ClientPlayNetworking.send(new QuizResultPayload(root.toString()));
            requestTpCreditsOnce();
        } catch (Exception e) {
            MathQuestMod.LOGGER.error("[MathQuest] Failed to send fluency feast result: {}", e.getMessage());
        }
        if (isMultiplayer) {
            MathQuestClient.clearActiveRewardPlan();
        }
    }

    private void giveRewards() {
        if (this.minecraft == null || this.minecraft.player == null) return;

        if (sessionOptions.suppressRewards()) {
            rewardDescription = "Quest rewards are handled by the quest.";
            recordResult("none");
            if (isMultiplayer) {
                MathQuestClient.clearActiveRewardPlan();
            }
            return;
        }

        if (quiz.getCorrectCount() == 0) {
            rewardDescription = "Keep practicing to earn rewards!";
            recordResult("none");
            return;
        }

        String username = this.minecraft.player.getName().getString();
        RewardDecision decision = chooseReward(false, username);
        if (decision.entries().isEmpty()) {
            rewardDescription = decision.description().isBlank() ? "Great job!" : decision.description();
            recordResult(decision.log());
            rewardsGiven = true;
            return;
        }
        if (finishRewardDecision(decision)) {
            recordResult(decision.log());
            if (isMultiplayer) {
                MathQuestClient.clearActiveRewardPlan();
            }
            rewardsGiven = true;
        }
    }

    private record RewardDecision(List<MathQuestConfig.RewardEntry> entries, String description, String log, boolean choose) {
        RewardDecision(List<MathQuestConfig.RewardEntry> entries, String description, String log) {
            this(entries, description, log, false);
        }
    }

    private boolean finishRewardDecision(RewardDecision decision) {
        if (decision.entries().isEmpty()) {
            rewardDescription = decision.description().isBlank() ? "Great job!" : decision.description();
            return true;
        }
        if (decision.choose() && decision.entries().size() > 1) {
            showRewardChoiceButtons(decision.entries(), true);
            rewardDescription = "Choose your reward:";
            return false;
        }
        rewardDescription = grantRewardDecision(decision);
        return true;
    }

    private void showRewardChoiceButtons(List<MathQuestConfig.RewardEntry> entries, boolean recordChoice) {
        clearRewardChoiceButtons();
        int centerX = this.width / 2;
        int y = this.height / 2 + 76;
        int index = 0;
        for (MathQuestConfig.RewardEntry entry : entries) {
            String label = formatItemName(entry.item) + " x" + entry.count;
            Button button = Button.builder(Component.literal(label), btn -> pickChosenReward(entry, recordChoice))
                .bounds(centerX - 110, y + index * 24, 220, 20)
                .build();
            rewardChoiceButtons.add(button);
            addRenderableWidget(button);
            index++;
        }
    }

    private void pickChosenReward(MathQuestConfig.RewardEntry entry, boolean recordChoice) {
        giveItem(entry);
        if (this.minecraft != null && this.minecraft.player != null) {
            this.minecraft.player.playSound(SoundEvents.PLAYER_LEVELUP, 1.0f, 1.0f);
        }
        rewardDescription = formatItemName(entry.item) + " x" + entry.count;
        String rewardLog = entry.item + ":" + entry.count;
        clearRewardChoiceButtons();
        if (recordChoice) {
            recordResult(rewardLog);
        }
        if (isMultiplayer) {
            MathQuestClient.clearActiveRewardPlan();
        }
        rewardsGiven = true;
    }

    private void clearRewardChoiceButtons() {
        for (Button button : rewardChoiceButtons) {
            removeWidget(button);
        }
        rewardChoiceButtons.clear();
    }

    private String grantRewardDecision(RewardDecision decision) {
        if (decision.entries().isEmpty()) return decision.description();
        for (MathQuestConfig.RewardEntry entry : decision.entries()) {
            giveItem(entry);
        }
        if (this.minecraft != null && this.minecraft.player != null) {
            this.minecraft.player.playSound(SoundEvents.PLAYER_LEVELUP, 1.0f, 1.0f);
        }
        return decision.description();
    }

    private RewardDecision chooseReward(boolean fluencyImproved, String username) {
        MathQuestConfig config = MathQuestMod.CONFIG;
        if (sessionOptions.fluencyFeastMode() && fluencyImproved) {
            MathQuestConfig.RewardPlan fluencyPlan = config.resolveFluencyRewardPlanForPlayer(username);
            List<MathQuestConfig.RewardEntry> fluencyRewards = fluencyPlan.entries();
            if (!fluencyRewards.isEmpty()) {
                String fluencyMode = MathQuestConfig.normalizeRewardGroupMode(fluencyPlan.mode());
                if ("choose".equals(fluencyMode) && fluencyRewards.size() > 1) {
                    return new RewardDecision(fluencyRewards, "Choose your fluency reward:", "pending", true);
                }
                if ("random".equals(fluencyMode)) {
                    MathQuestConfig.RewardEntry entry = fluencyRewards.get(new Random().nextInt(fluencyRewards.size()));
                    return new RewardDecision(
                        List.of(entry),
                        formatItemName(entry.item) + " x" + entry.count,
                        entry.item + ":" + entry.count
                    );
                }
                StringBuilder desc = new StringBuilder();
                StringBuilder rewardLog = new StringBuilder();
                for (MathQuestConfig.RewardEntry entry : fluencyRewards) {
                    if (desc.length() > 0) desc.append(", ");
                    desc.append(formatItemName(entry.item)).append(" x").append(entry.count);
                    if (rewardLog.length() > 0) rewardLog.append(",");
                    rewardLog.append(entry.item).append(":").append(entry.count);
                }
                return new RewardDecision(fluencyRewards, desc.toString(), rewardLog.toString());
            }
        }
        List<MathQuestConfig.RewardEntry> rewards;
        String rewardMode;
        if (isMultiplayer) {
            rewards = parseServerRewards(MathQuestClient.getActiveRewardsJson());
            rewardMode = MathQuestClient.getActiveRewardMode();
        } else {
            MathQuestConfig.RewardPlan plan = config.resolveRewardPlanForPlayer(username);
            rewards = plan.entries();
            rewardMode = plan.mode();
        }
        if (rewards == null || rewards.isEmpty()) {
            return new RewardDecision(List.of(), "Great job!", "none");
        }
        rewardMode = MathQuestConfig.normalizeRewardGroupMode(rewardMode);
        if (sessionOptions.fluencyFeastMode() && "choose".equals(rewardMode)) {
            rewardMode = "random";
        }
        if ("choose".equals(rewardMode)) {
            if (rewards.size() == 1) {
                MathQuestConfig.RewardEntry entry = rewards.get(0);
                return new RewardDecision(
                    List.of(entry),
                    formatItemName(entry.item) + " x" + entry.count,
                    entry.item + ":" + entry.count
                );
            }
            return new RewardDecision(rewards, "Choose your reward:", "pending", true);
        }
        Random random = new Random();
        if ("random".equals(rewardMode)) {
            MathQuestConfig.RewardEntry entry = rewards.get(random.nextInt(rewards.size()));
            return new RewardDecision(
                List.of(entry),
                formatItemName(entry.item) + " x" + entry.count,
                entry.item + ":" + entry.count
            );
        }
        StringBuilder desc = new StringBuilder();
        StringBuilder rewardLog = new StringBuilder();
        for (MathQuestConfig.RewardEntry entry : rewards) {
            if (desc.length() > 0) desc.append(", ");
            desc.append(formatItemName(entry.item)).append(" x").append(entry.count);
            if (rewardLog.length() > 0) rewardLog.append(",");
            rewardLog.append(entry.item).append(":").append(entry.count);
        }
        return new RewardDecision(rewards, desc.toString(), rewardLog.toString());
    }

    private void recordResult(String rewardGiven) {
        if (isMultiplayer) {
            sendResultToServer(rewardGiven);
        } else {
            QuizDatabase.getInstance().endSession(sessionId, quiz.getCorrectCount(), rewardGiven);
            exportSessionFile();
            settleLocalTpCreditSession();
        }
        requestTpCreditsOnce();
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
            ClientPlayNetworking.send(new QuizResultPayload(buildResultRoot(rewardGiven).toString()));
        } catch (Exception e) {
            MathQuestMod.LOGGER.error("[MathQuest] Failed to send quiz result to server: {}", e.getMessage());
        }
    }

    private com.google.gson.JsonObject buildResultRoot(String rewardGiven) {
        com.google.gson.JsonObject root = new com.google.gson.JsonObject();
        root.addProperty("operation", quiz.getOperation());
        root.addProperty("problemsTotal", quiz.getTotalProblems());
        root.addProperty("problemsCorrect", quiz.getCorrectCount());
        root.addProperty("rewardGiven", rewardGiven);
        root.addProperty("tpCreditEligible", sessionOptions.tpCreditEligible());
        root.addProperty("tpCreditCompletionToken", sessionOptions.tpCreditCompletionToken());
        com.google.gson.JsonArray problemsArray = new com.google.gson.JsonArray();
        for (QuizManager.Problem p : quiz.getProblems()) {
            com.google.gson.JsonObject pObj = new com.google.gson.JsonObject();
            pObj.addProperty("operation", p.operation);
            pObj.addProperty("factorA", p.factorA);
            pObj.addProperty("factorB", p.factorB);
            pObj.addProperty("correctAnswer", p.correctAnswer);
            if (p.playerAnswer != null) {
                pObj.addProperty("playerAnswer", p.playerAnswer);
            } else {
                pObj.add("playerAnswer", com.google.gson.JsonNull.INSTANCE);
            }
            pObj.addProperty("isCorrect", p.isCorrect);
            pObj.addProperty("responseTimeMs", p.responseTimeMs);
            com.google.gson.JsonArray flags = new com.google.gson.JsonArray();
            for (String flag : p.flags) {
                flags.add(flag);
            }
            pObj.add("flags", flags);
            problemsArray.add(pObj);
        }
        root.add("problems", problemsArray);
        return root;
    }

    private void exportSessionFile() {
        try {
            String username = (this.minecraft != null && this.minecraft.player != null)
                ? this.minecraft.player.getName().getString()
                : "unknown";
            String realName = MathQuestMod.CONFIG.resolveRealName(username);
            UUID playerUuid = (this.minecraft != null && this.minecraft.player != null)
                ? this.minecraft.player.getUUID()
                : null;
            java.nio.file.Path path = SessionExporter.exportSession(quiz, realName, playerUuid);
            MathQuizSessionIngestor.ingest(path, realName);
            MathQuestMod.LOGGER.info("[MathQuest] Session exported to {}", path);
        } catch (java.io.IOException e) {
            MathQuestMod.LOGGER.error("[MathQuest] Failed to export session: {}", e.getMessage());
        }
    }

    private void giveItem(MathQuestConfig.RewardEntry entry) {
        try {
            ClientPlayNetworking.send(new GiveRewardPayload(entry.item, entry.count));
        } catch (Exception e) {
            MathQuestMod.LOGGER.error("[MathQuest] Failed to give item {}: {}", entry.item, e.getMessage());
        }
    }
    private List<MathQuestConfig.RewardEntry> parseServerRewards(String rewardsJson) {
        java.util.List<MathQuestConfig.RewardEntry> out = new java.util.ArrayList<>();
        try {
            com.google.gson.JsonArray arr = com.google.gson.JsonParser.parseString(rewardsJson).getAsJsonArray();
            for (com.google.gson.JsonElement el : arr) {
                com.google.gson.JsonObject obj = el.getAsJsonObject();
                out.add(new MathQuestConfig.RewardEntry(
                    obj.get("item").getAsString(),
                    obj.get("count").getAsInt()
                ));
            }
        } catch (Exception e) {
            MathQuestMod.LOGGER.error("[MathQuest] Failed to parse server rewards: {}", e.getMessage());
        }
        return out;
    }

    private String formatItemName(String itemId) {
        String name = itemId;
        if (name.contains(":")) {
            name = name.substring(name.indexOf(':') + 1);
        }
        name = name.replace('_', ' ');
        StringBuilder sb = new StringBuilder();
        for (String word : name.split(" ")) {
            if (sb.length() > 0) sb.append(' ');
            if (!word.isEmpty()) {
                sb.append(Character.toUpperCase(word.charAt(0)));
                if (word.length() > 1) sb.append(word.substring(1));
            }
        }
        return sb.toString();
    }

    @Override
    public void extractRenderState(GuiGraphicsExtractor context, int mouseX, int mouseY, float delta) {
        super.extractRenderState(context, mouseX, mouseY, delta);

        int centerX = this.width / 2;
        int y = 40;

        String titleStr = "Quiz Complete!";
        context.pose().pushMatrix();
        context.pose().translate(centerX, y);
        context.pose().scale(2.0f, 2.0f);
        int titleWidth = this.font.width(titleStr);
        context.text(this.font, titleStr, -titleWidth / 2, 0, 0xFFFFFF00, true);
        context.pose().popMatrix();
        y += 40;

        String scoreText = "You got " + quiz.getCorrectCount() + " out of " + quiz.getTotalProblems() + " correct!";
        drawCenteredText(context, scoreText, centerX, y, 0xFFFFFFFF);
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
        drawCenteredText(context, encouragement, centerX, y, encourageColor);

        if (sessionOptions.fluencyFeastMode()) {
            int centerY = this.height / 2;
            if (!fluencyReadout.isEmpty()) {
                drawScaledCenteredText(context, fluencyReadout, centerX, centerY - 28, 2.5f, QUEST_GOLD);
            } else if (fluencyCalculating) {
                drawScaledCenteredText(context, "Calculating fluency...", centerX, centerY - 28, 2.0f, QUEST_GOLD_DIM);
            }
            if (!rewardDescription.isEmpty()) {
                drawScaledCenteredText(
                    context,
                    "You earned: " + rewardDescription,
                    centerX,
                    centerY + 32,
                    2.0f,
                    QUEST_GOLD
                );
            }
        } else {
            y += 30;
            if (!fluencyReadout.isEmpty()) {
                drawCenteredText(context, fluencyReadout, centerX, y, 0xFF55FF55);
            } else if (fluencyCalculating) {
                drawCenteredText(context, "Calculating fluency...", centerX, y, 0xFFAAAAAA);
            }
            if (!rewardDescription.isEmpty()) {
                drawCenteredText(context, "You earned: " + rewardDescription, centerX, y + 20, 0xFF55FF55);
            }
        }
    }

    private void drawCenteredText(GuiGraphicsExtractor context, String text, int centerX, int y, int color) {
        int textWidth = this.font.width(text);
        context.text(this.font, text, centerX - textWidth / 2, y, color, true);
    }

    private void drawScaledCenteredText(
        GuiGraphicsExtractor context,
        String text,
        int centerX,
        int centerY,
        float scale,
        int color
    ) {
        context.pose().pushMatrix();
        context.pose().translate(centerX, centerY);
        context.pose().scale(scale, scale);
        int textWidth = this.font.width(text);
        context.text(this.font, text, -textWidth / 2, 0, color, true);
        context.pose().popMatrix();
    }

    @Override
    public boolean isPauseScreen() {
        return true;
    }
}
