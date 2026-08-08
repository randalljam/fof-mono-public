package com.kidgames.mathquest.screen;

import com.kidgames.mathquest.MathQuestClient;
import com.kidgames.mathquest.network.OpenQuizPayload;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayNetworking;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;

/** Quest 01 knowledge invitation — Accept starts the quiz; Decline re-prompts after 22 seconds. */
public class QuestInvitationScreen extends Screen {
    private final String message;
    private final String subtitle;
    private final OpenQuizPayload quizPayload;
    private final QuestInvitationResponseFlow.ResponseSender responseSender;

    public QuestInvitationScreen(String message, String subtitle) {
        this(message, subtitle, null);
    }

    public QuestInvitationScreen(String message, String subtitle, OpenQuizPayload quizPayload) {
        this(message, subtitle, quizPayload, payload -> ClientPlayNetworking.send(payload));
    }

    QuestInvitationScreen(
        String message,
        String subtitle,
        OpenQuizPayload quizPayload,
        QuestInvitationResponseFlow.ResponseSender responseSender
    ) {
        super(Component.literal("Knowledge Invitation"));
        this.message = message == null ? "" : message;
        this.subtitle = subtitle == null ? "" : subtitle;
        this.quizPayload = quizPayload;
        this.responseSender = responseSender == null ? (payload -> {}) : responseSender;
    }

    @Override
    protected void init() {
        int centerX = this.width / 2;
        int centerY = this.height / 2;

        this.addRenderableWidget(Button.builder(
            Component.literal("Accept"),
            button -> respond(true)
        ).bounds(centerX - 105, centerY + 30, 100, 20).build());

        this.addRenderableWidget(Button.builder(
            Component.literal("Decline"),
            button -> respond(false)
        ).bounds(centerX + 5, centerY + 30, 100, 20).build());
    }

    void respond(boolean accepted) {
        try {
            QuestInvitationResponseFlow.respond(
                accepted,
                this::closeForResponse,
                () -> MathQuestClient.openQuizPayload(Minecraft.getInstance(), quizPayload),
                responseSender
            );
        } catch (Exception e) {
            com.kidgames.mathquest.MathQuestMod.LOGGER.error(
                "[MathQuest] Failed to send quest invitation response: {}", e.getMessage());
        }
    }

    protected void closeForResponse() {
        if (this.minecraft != null) {
            this.minecraft.setScreen(null);
        }
    }

    @Override
    public void extractRenderState(GuiGraphicsExtractor context, int mouseX, int mouseY, float delta) {
        super.extractRenderState(context, mouseX, mouseY, delta);

        int centerX = this.width / 2;
        int centerY = this.height / 2;

        if (!subtitle.isBlank()) {
            int subtitleWidth = this.font.width(subtitle);
            context.text(this.font, subtitle, centerX - subtitleWidth / 2, centerY - 40, 0xFFFFFFAA, true);
        }

        int y = centerY - 20;
        for (String line : wrap(message, 46)) {
            int lineWidth = this.font.width(line);
            context.text(this.font, line, centerX - lineWidth / 2, y, 0xFFFFFFFF, true);
            y += 12;
        }
    }

    private static java.util.List<String> wrap(String text, int maxChars) {
        java.util.List<String> lines = new java.util.ArrayList<>();
        String clean = text == null ? "" : text.trim();
        if (clean.isBlank()) return lines;
        String[] words = clean.split("\\s+");
        StringBuilder current = new StringBuilder();
        for (String word : words) {
            if (current.length() + word.length() + 1 > maxChars && current.length() > 0) {
                lines.add(current.toString());
                current = new StringBuilder(word);
            } else if (current.length() == 0) {
                current.append(word);
            } else {
                current.append(' ').append(word);
            }
        }
        if (current.length() > 0) lines.add(current.toString());
        return lines;
    }

    @Override
    public boolean isPauseScreen() {
        return true;
    }
}
