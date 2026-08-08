package com.kidgames.mathquest.screen;

import com.kidgames.mathquest.MathQuestClient;
import com.kidgames.mathquest.persistence.QuizDatabase;
import com.kidgames.mathquest.quiz.QuizManager;
import com.kidgames.mathquest.quiz.QuizSessionOptions;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.components.EditBox;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.client.input.KeyEvent;
import net.minecraft.network.chat.Component;
import net.minecraft.sounds.SoundEvents;

public class QuizScreen extends Screen {
    private static final long FEEDBACK_DURATION_MS = 1500;
    private static final int INSERT_GAP = 5;
    private static final int FLAG_PANEL_HEIGHT = 194;
    private static final int FLAG_PANEL_WIDGET_OFFSET = 134;
    private static final String[] FLAG_REASON_KEYS = {
        "skip-noreason", "distracted", "interrupted", "error", "stall", "dontknow", "other"
    };
    private static final String[] FLAG_REASON_LABELS = {
        "Skip - no reason", "Distracted", "Interrupted", "Input Error", "Stall", "I Don't Know", "Other"
    };

    private final QuizManager quiz;
    private final long sessionId;
    private final boolean isMultiplayer;
    private final String sourceLabel;
    private final QuizSessionOptions sessionOptions;
    private String inputBuffer = "";
    private long questionShownTime;

    private String feedbackMessage = null;
    private int feedbackColor = 0xFFFFFFFF;
    private long feedbackStartTime = 0;
    private boolean waitingForAdvance = false;
    private boolean paused = false;
    private String statusMessage = null;
    private long statusStartTime = 0;
    private boolean flagPanelOpen = false;
    private final boolean[] flagReasonSelected = new boolean[FLAG_REASON_KEYS.length];
    private EditBox flagComment;
    private long flagPanelResponseTimeMs = 0;
    private QuizManager.Problem flagPanelTargetProblem = null;
    private int flagPanelTargetIndex = -1;
    private boolean flagPanelForPrevious = false;

    public QuizScreen(QuizManager quiz) {
        this(quiz, "external list");
    }

    public QuizScreen(QuizManager quiz, String sourceLabel) {
        this(quiz, sourceLabel, QuizSessionOptions.standard());
    }

    public QuizScreen(QuizManager quiz, String sourceLabel, QuizSessionOptions sessionOptions) {
        super(Component.literal("Math Quest"));
        this.quiz = quiz;
        this.sourceLabel = sourceLabel == null || sourceLabel.isBlank() ? "external list" : sourceLabel;
        this.sessionOptions = sessionOptions == null ? QuizSessionOptions.standard() : sessionOptions;
        this.quiz.setSessionOptions(this.sessionOptions);
        this.isMultiplayer = Minecraft.getInstance().getSingleplayerServer() == null;
        this.sessionId = isMultiplayer ? -1 : QuizDatabase.getInstance().startSession(quiz.getTotalProblems());
    }

    @Override
    protected void init() {
        buildQuizUi();
        questionShownTime = System.currentTimeMillis();
    }

    private void buildQuizUi() {
        this.clearWidgets();

        int keyW = Math.min(42, Math.max(32, this.width / 18));
        int keyH = Math.min(38, Math.max(24, this.height / 16));
        int gap = 8;
        int keypadHeight = 4 * keyH + 3 * gap;
        int flagPanelH = flagPanelOpen ? FLAG_PANEL_HEIGHT : 0;
        int totalHeight = 90 + flagPanelH + keypadHeight + 96;
        int top = Math.max(20, (this.height - totalHeight) / 2);
        int padStartY = top + 110 + flagPanelH;
        int padStartX = (this.width - (3 * keyW + 2 * gap)) / 2;

        if (flagPanelOpen) {
            addFlagPanelWidgets(top + FLAG_PANEL_WIDGET_OFFSET);
        }

        addNumButton(7, padStartX, padStartY, keyW, keyH);
        addNumButton(8, padStartX + keyW + gap, padStartY, keyW, keyH);
        addNumButton(9, padStartX + 2 * (keyW + gap), padStartY, keyW, keyH);

        int row2Y = padStartY + keyH + gap;
        addNumButton(4, padStartX, row2Y, keyW, keyH);
        addNumButton(5, padStartX + keyW + gap, row2Y, keyW, keyH);
        addNumButton(6, padStartX + 2 * (keyW + gap), row2Y, keyW, keyH);

        int row3Y = row2Y + keyH + gap;
        addNumButton(1, padStartX, row3Y, keyW, keyH);
        addNumButton(2, padStartX + keyW + gap, row3Y, keyW, keyH);
        addNumButton(3, padStartX + 2 * (keyW + gap), row3Y, keyW, keyH);

        int row4Y = row3Y + keyH + gap;
        this.addRenderableWidget(Button.builder(
            Component.literal("+/-"),
            button -> toggleSign()
        ).bounds(padStartX, row4Y, keyW, keyH).build());
        addNumButton(0, padStartX + keyW + gap, row4Y, keyW, keyH);
        this.addRenderableWidget(Button.builder(
            Component.literal("C"),
            button -> {
                if (canEditAnswer()) inputBuffer = "";
            }
        ).bounds(padStartX + 2 * (keyW + gap), row4Y, keyW, keyH).build());

        int actionY = row4Y + keyH + 14;
        int actionH = 24;
        int actionGap = 10;
        if (sessionOptions.showFlagControls() || sessionOptions.showPauseButton()) {
            int skipW = Math.min(112, Math.max(92, this.width / 8));
            int flagW = Math.min(132, Math.max(112, this.width / 7));
            int pauseW = Math.min(82, Math.max(68, this.width / 11));
            int totalW = 0;
            if (sessionOptions.showFlagControls()) totalW += skipW + flagW + actionGap;
            if (sessionOptions.showPauseButton()) totalW += pauseW + (totalW > 0 ? actionGap : 0);
            int actionX = (this.width - totalW) / 2;
            if (sessionOptions.showFlagControls()) {
                this.addRenderableWidget(Button.builder(
                    Component.literal("Skip & flag"),
                    button -> skipAndFlag()
                ).bounds(actionX, actionY, skipW, actionH).build());
                actionX += skipW + actionGap;
                this.addRenderableWidget(Button.builder(
                    Component.literal("Flag previous"),
                    button -> flagPrevious()
                ).bounds(actionX, actionY, flagW, actionH).build());
                actionX += flagW + actionGap;
            }
            if (sessionOptions.showPauseButton()) {
                this.addRenderableWidget(Button.builder(
                    Component.literal(paused ? "Resume" : "Pause"),
                    button -> {
                        paused = !paused;
                        buildQuizUi();
                    }
                ).bounds(actionX, actionY, pauseW, actionH).build());
            }
        }

        if (sessionOptions.showQuitControls()) {
            int quitY = actionY + actionH + 14;
            int quitW = Math.min(138, Math.max(106, this.width / 7));
            int quitGap = 12;
            int quitX = (this.width - (2 * quitW + quitGap)) / 2;
            this.addRenderableWidget(Button.builder(
                Component.literal("Quit & save"),
                button -> quitAndSave()
            ).bounds(quitX, quitY, quitW, actionH).build());
            this.addRenderableWidget(Button.builder(
                Component.literal("Quit & abandon"),
                button -> {
                    MathQuestClient.despawnNearbyNerds();
                    this.onClose();
                }
            ).bounds(quitX + quitW + quitGap, quitY, quitW, actionH).build());
        }
    }

    private void addFlagPanelWidgets(int panelY) {
        int panelW = Math.min(292, this.width - 28);
        int panelX = (this.width - panelW) / 2;
        int reasonW = (panelW - 10) / 2;
        for (int i = 0; i < FLAG_REASON_KEYS.length; i++) {
            int row = i / 2;
            int col = i % 2;
            int index = i;
            this.addRenderableWidget(Button.builder(
                Component.literal(flagReasonLabel(index)),
                button -> {
                    flagReasonSelected[index] = !flagReasonSelected[index];
                    button.setMessage(Component.literal(flagReasonLabel(index)));
                }
            ).bounds(panelX + col * (reasonW + 10), panelY + row * 18, reasonW, 16).build());
        }

        flagComment = new EditBox(this.font, panelX, panelY + 96, panelW, 20, Component.literal("Other / comment"));
        this.addRenderableWidget(flagComment);

        int continueW = 96;
        int insertW = 126;
        int actionGap = 8;
        int actionX = (this.width - (continueW + insertW + actionGap)) / 2;
        int actionY = panelY + 124;
        this.addRenderableWidget(Button.builder(
            Component.literal("Continue"),
            button -> completeSkipFlag(false)
        ).bounds(actionX, actionY, continueW, 22).build());
        this.addRenderableWidget(Button.builder(
            Component.literal("Continue & insert"),
            button -> completeSkipFlag(true)
        ).bounds(actionX + continueW + actionGap, actionY, insertW, 22).build());
    }

    private String flagReasonLabel(int index) {
        return (flagReasonSelected[index] ? "[x] " : "[ ] ") + FLAG_REASON_LABELS[index];
    }

    private void addNumButton(int num, int x, int y, int width, int height) {
        this.addRenderableWidget(Button.builder(
            Component.literal(String.valueOf(num)),
            button -> {
                if (canEditAnswer()) {
                    inputBuffer += String.valueOf(num);
                    maybeAutoSubmit();
                }
            }
        ).bounds(x, y, width, height).build());
    }

    private boolean canEditAnswer() {
        return !waitingForAdvance && !paused && !flagPanelOpen;
    }

    private void toggleSign() {
        if (!canEditAnswer()) return;
        if (inputBuffer.startsWith("-")) {
            inputBuffer = inputBuffer.substring(1);
        } else {
            inputBuffer = "-" + inputBuffer;
        }
        maybeAutoSubmit();
    }

    private void maybeAutoSubmit() {
        if (inputBuffer.isEmpty() || "-".equals(inputBuffer) || waitingForAdvance || paused) return;
        QuizManager.Problem problem = quiz.getCurrentProblem();
        if (problem == null) return;
        if (enteredDigits() >= digitCount(problem.correctAnswer)) {
            submitAnswer();
        }
    }

    private int enteredDigits() {
        int digits = 0;
        for (int i = 0; i < inputBuffer.length(); i++) {
            if (Character.isDigit(inputBuffer.charAt(i))) digits++;
        }
        return digits;
    }

    private int digitCount(long value) {
        return Long.toString(Math.abs(value)).length();
    }

    private void submitAnswer() {
        if (waitingForAdvance || paused || inputBuffer.isEmpty() || "-".equals(inputBuffer)) return;

        QuizManager.Problem problem = quiz.getCurrentProblem();
        if (problem == null) return;

        long responseTime = System.currentTimeMillis() - questionShownTime;
        long answer;
        try {
            answer = Long.parseLong(inputBuffer);
        } catch (NumberFormatException e) {
            inputBuffer = "";
            return;
        }

        problem.responseTimeMs = responseTime;
        boolean correct = quiz.submitAnswer(answer);
        recordLocalAnswer(problem);
        quiz.applyPostAnswerPolicy(problem);

        if (correct) {
            feedbackMessage = "Amazing!";
            feedbackColor = 0xFF55FF55;
            if (this.minecraft != null && this.minecraft.player != null) {
                this.minecraft.player.playSound(SoundEvents.EXPERIENCE_ORB_PICKUP, 1.0f, 1.0f);
            }
        } else {
            feedbackMessage = "The answer is " + problem.correctAnswer;
            feedbackColor = 0xFFFF5555;
            if (this.minecraft != null && this.minecraft.player != null) {
                this.minecraft.player.playSound(SoundEvents.VILLAGER_NO, 1.0f, 1.0f);
            }
        }
        feedbackStartTime = System.currentTimeMillis();
        waitingForAdvance = true;
    }

    private void skipAndFlag() {
        if (waitingForAdvance || paused || flagPanelOpen) return;
        QuizManager.Problem problem = quiz.getCurrentProblem();
        if (problem == null) return;
        openFlagPanel(problem, quiz.getCurrentIndex(), false, System.currentTimeMillis() - questionShownTime);
    }

    private void openFlagPanel(QuizManager.Problem target, int targetIndex, boolean forPrevious, long responseTimeMs) {
        for (int i = 0; i < flagReasonSelected.length; i++) {
            flagReasonSelected[i] = hasFlag(target, FLAG_REASON_KEYS[i]);
        }
        if (!forPrevious && noFlagReasonSelected()) {
            flagReasonSelected[0] = true;
        }
        flagPanelOpen = true;
        flagPanelResponseTimeMs = responseTimeMs;
        flagPanelTargetProblem = target;
        flagPanelTargetIndex = targetIndex;
        flagPanelForPrevious = forPrevious;
        inputBuffer = forPrevious && target.playerAnswer != null ? String.valueOf(target.playerAnswer) : "";
        feedbackMessage = "Correct answer: " + target.correctAnswer;
        feedbackColor = 0xFFFF5555;
        feedbackStartTime = System.currentTimeMillis();
        buildQuizUi();
    }

    private boolean hasFlag(QuizManager.Problem problem, String flag) {
        return problem != null && problem.flags.contains(flag);
    }

    private boolean noFlagReasonSelected() {
        for (boolean selected : flagReasonSelected) {
            if (selected) return false;
        }
        return true;
    }

    private void completeSkipFlag(boolean insertLater) {
        if (!flagPanelOpen) return;
        QuizManager.Problem problem = flagPanelTargetProblem != null ? flagPanelTargetProblem : quiz.getCurrentProblem();
        if (problem == null) return;
        applyFlagPanelSelections(problem);
        if (insertLater && flagPanelForPrevious) {
            quiz.insertProblemLater(problem, INSERT_GAP);
        } else if (insertLater) {
            quiz.insertCurrentProblemLater(INSERT_GAP);
        }
        if (flagPanelForPrevious) {
            updateLocalAnswerFlags(flagPanelTargetIndex, problem);
        } else {
            quiz.skipCurrent(flagPanelResponseTimeMs);
            recordLocalAnswer(problem);
        }
        flagPanelOpen = false;
        flagComment = null;
        flagPanelTargetProblem = null;
        flagPanelTargetIndex = -1;
        boolean wasPrevious = flagPanelForPrevious;
        flagPanelForPrevious = false;
        if (wasPrevious) {
            inputBuffer = "";
            feedbackMessage = null;
            waitingForAdvance = false;
            setStatus(insertLater ? "Previous flagged - will reappear later." : "Previous answer flagged.");
        } else {
            feedbackMessage = insertLater
                ? "Skipped - will reappear later"
                : "Skipped - the answer is " + problem.correctAnswer;
            feedbackColor = 0xFFFFAA00;
            feedbackStartTime = System.currentTimeMillis();
            waitingForAdvance = true;
        }
        buildQuizUi();
    }

    private void applyFlagPanelSelections(QuizManager.Problem problem) {
        boolean hasReason = false;
        for (int i = 0; i < FLAG_REASON_KEYS.length; i++) {
            if (flagReasonSelected[i]) {
                problem.addFlag(FLAG_REASON_KEYS[i]);
                hasReason = true;
            }
        }
        String comment = flagComment != null ? flagComment.getValue().trim() : "";
        if (!comment.isEmpty()) {
            if (!hasReason) {
                problem.addFlag("other");
            }
            problem.addFlag("note:" + comment);
        } else if (!hasReason && flagPanelForPrevious) {
            problem.addFlag("flag_previous");
        } else if (!hasReason) {
            problem.addFlag("skip-noreason");
        }
    }

    private void flagPrevious() {
        if (waitingForAdvance || paused || flagPanelOpen) return;
        int previousIndex = previousAnsweredProblemIndex();
        QuizManager.Problem previous = previousIndex >= 0 ? quiz.getProblems().get(previousIndex) : null;
        if (previous == null) {
            setStatus("No previous answer to flag yet.");
            return;
        }
        openFlagPanel(previous, previousIndex, true, previous.responseTimeMs);
    }

    private int previousAnsweredProblemIndex() {
        for (int i = Math.min(quiz.getProblems().size(), quiz.getCurrentIndex()) - 1; i >= 0; i--) {
            QuizManager.Problem problem = quiz.getProblems().get(i);
            if (problem.wasAnswered()) return i;
        }
        return -1;
    }

    private void quitAndSave() {
        if (quiz.getAnsweredCount() == 0) {
            setStatus("Answer or skip at least one problem before saving.");
            return;
        }
        quiz.keepAnsweredProblemsOnly();
        this.minecraft.setScreen(new QuizResultScreen(quiz, sessionId, sessionOptions.withoutTpCreditAward()));
    }

    private void recordLocalAnswer(QuizManager.Problem problem) {
        if (!isMultiplayer) {
            QuizDatabase.getInstance().recordAnswer(
                sessionId, quiz.getCurrentIndex() + 1, problem);
        }
    }

    private void updateLocalAnswerFlags(int problemIndex, QuizManager.Problem problem) {
        if (!isMultiplayer && problemIndex >= 0) {
            QuizDatabase.getInstance().updateAnswerFlags(sessionId, problemIndex + 1, problem);
        }
    }

    private void setStatus(String message) {
        statusMessage = message;
        statusStartTime = System.currentTimeMillis();
    }

    @Override
    public void tick() {
        super.tick();

        if (waitingForAdvance && System.currentTimeMillis() - feedbackStartTime >= FEEDBACK_DURATION_MS) {
            waitingForAdvance = false;
            feedbackMessage = null;
            inputBuffer = "";

            quiz.advanceToNext();

            if (quiz.isQuizComplete()) {
                this.minecraft.setScreen(new QuizResultScreen(quiz, sessionId, sessionOptions));
            } else {
                questionShownTime = System.currentTimeMillis();
            }
        }
        if (statusMessage != null && System.currentTimeMillis() - statusStartTime >= 2500) {
            statusMessage = null;
        }
    }

    @Override
    public void extractRenderState(GuiGraphicsExtractor context, int mouseX, int mouseY, float delta) {
        super.extractRenderState(context, mouseX, mouseY, delta);

        int centerX = this.width / 2;
        int keyH = Math.min(38, Math.max(24, this.height / 16));
        int keypadHeight = 4 * keyH + 3 * 8;
        int flagPanelH = flagPanelOpen ? FLAG_PANEL_HEIGHT : 0;
        int totalHeight = 90 + flagPanelH + keypadHeight + 96;
        int top = Math.max(20, (this.height - totalHeight) / 2);
        int problemY = top;
        int answerY = top + 44;
        int answerW = Math.min(105, Math.max(76, this.width / 10));
        int answerH = 42;

        QuizManager.Problem problem = flagPanelForPrevious && flagPanelTargetProblem != null
            ? flagPanelTargetProblem
            : quiz.getCurrentProblem();
        if (problem != null) {
            String questionText = displayQuestion(problem);
            context.pose().pushMatrix();
            context.pose().translate(centerX, problemY);
            context.pose().scale(3.0f, 3.0f);
            int textWidth = this.font.width(questionText);
            context.text(this.font, questionText, -textWidth / 2, 0, 0xFFFFFFFF, true);
            context.pose().popMatrix();
        }

        int answerX = centerX - answerW / 2;
        context.fill(answerX, answerY, answerX + answerW, answerY + answerH, 0xAA202020);
        context.fill(answerX + 1, answerY + 1, answerX + answerW - 1, answerY + answerH - 1, 0xAA101010);
        context.outline(answerX, answerY, answerW, answerH, 0xFFAAAAAA);
        String displayText = inputBuffer.isEmpty() ? "_" : inputBuffer;
        context.pose().pushMatrix();
        context.pose().translate(centerX, answerY + 9);
        context.pose().scale(2.0f, 2.0f);
        int answerTextWidth = this.font.width(displayText);
        context.text(this.font, displayText, -answerTextWidth / 2, 0, 0xFFFFFFFF, true);
        context.pose().popMatrix();

        if (feedbackMessage != null) {
            drawCenteredText(context, feedbackMessage, centerX, answerY + answerH + 8, feedbackColor);
        } else if (statusMessage != null) {
            drawCenteredText(context, statusMessage, centerX, answerY + answerH + 8, 0xFFAAAAAA);
        }

        if (flagPanelOpen) {
            int panelY = top + FLAG_PANEL_WIDGET_OFFSET;
            drawCenteredText(context, "Choose flag reasons", centerX, panelY - 26, 0xFFFFFFFF);
            context.text(this.font, "Other / comment", centerX - 145, panelY + 88, 0xFFAAAAAA, true);
        }

        if (sessionOptions.showProgress() || sessionOptions.showSourceLabel()) {
            int progressY = Math.min(this.height - 28, top + 90 + flagPanelH + keypadHeight + 110);
            int total = quiz.getTotalProblems();
            int answered = quiz.getAnsweredCount();
            int pct = total > 0 ? Math.min(100, Math.round(answered * 100.0f / total)) : 0;
            if (sessionOptions.showProgress()) {
                drawCenteredText(context, answered + " of " + total + " answered - " + pct + "% complete",
                    centerX, progressY, 0xFFCCCCCC);
            }
            if (sessionOptions.showSourceLabel()) {
                drawCenteredText(context, sourceLabel, centerX, Math.min(this.height - 14, progressY + 14), 0xFFAAAAAA);
            }
        }

        if (paused) {
            drawCenteredText(context, "Paused", centerX, this.height / 2 - 12, 0xFFFFFFFF);
            drawCenteredText(context, "Press Resume to continue.", centerX, this.height / 2 + 8, 0xFFCCCCCC);
        }
    }

    private String displayQuestion(QuizManager.Problem problem) {
        return problem.factorA + " " + symbol(problem.operation) + " " + problem.factorB;
    }

    private String symbol(String operation) {
        return switch (operation) {
            case "addition" -> "+";
            case "subtraction" -> "-";
            case "division" -> "/";
            case "exponentiation" -> "^";
            default -> "x";
        };
    }

    private void drawCenteredText(GuiGraphicsExtractor context, String text, int centerX, int y, int color) {
        int textWidth = this.font.width(text);
        context.text(this.font, text, centerX - textWidth / 2, y, color, true);
    }

    @Override
    public boolean keyPressed(KeyEvent input) {
        int keyCode = input.key();

        if (keyCode == 256) {
            paused = !paused;
            buildQuizUi();
            return true;
        }

        if (canEditAnswer()) {
            if (keyCode >= 48 && keyCode <= 57) {
                inputBuffer += String.valueOf(keyCode - 48);
                maybeAutoSubmit();
                return true;
            }
            if (keyCode >= 320 && keyCode <= 329) {
                inputBuffer += String.valueOf(keyCode - 320);
                maybeAutoSubmit();
                return true;
            }
            if (keyCode == 259 && !inputBuffer.isEmpty()) {
                inputBuffer = inputBuffer.substring(0, inputBuffer.length() - 1);
                return true;
            }
            if (keyCode == 257 || keyCode == 335) {
                submitAnswer();
                return true;
            }
        }
        return super.keyPressed(input);
    }

    @Override
    public boolean isPauseScreen() {
        return true;
    }

    @Override
    public boolean shouldCloseOnEsc() {
        return false;
    }
}
