package com.kidgames.mathquest;

import com.kidgames.mathquest.net.OpenQuizData;
import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.persistence.MathQuizFluencyLoader;
import com.kidgames.mathquest.quiz.QuizSessionOptions;
import com.kidgames.mathquest.server.OpenQuizPayloadBuilder;
import com.kidgames.mathquest.server.QuizDeliveryPreview;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class QuizDeliveryPreviewTest {
    private MathQuestConfig previousConfig;

    @BeforeEach
    void isolateConfig() {
        previousConfig = MathQuestConfig.INSTANCE;
        MathQuestConfig.INSTANCE = null;
    }

    @AfterEach
    void restoreConfig() {
        MathQuestConfig.INSTANCE = previousConfig;
    }

    @Test
    void previewDoesNotIssueRedeemableTpCreditSession() {
        MathQuestConfig.INSTANCE = new MathQuestConfig();
        OpenQuizData data = OpenQuizPayloadBuilder.createPreview("WildPetal");

        assertEquals("", QuizSessionOptions.fromJson(data.optionsJson()).tpCreditCompletionToken());
    }

    @Test
    void fluencyFeastWithProblemsReportsCountAndOperation() {
        String problemsJson = OpenQuizPayloadBuilder.problemsJson(java.util.List.of(
            com.kidgames.mathquest.quiz.QuizManager.Problem.create("addition", 3, 4),
            com.kidgames.mathquest.quiz.QuizManager.Problem.create("addition", 5, 6)
        ));
        OpenQuizData data = new OpenQuizData(
            "multiplication", 0, 9, 7, problemsJson, "[]", "random",
            "standard_arithmetic", "{}", true, false
        );
        QuizDeliveryPreview.Result result = QuizDeliveryPreview.fromOpenQuizData("rjcomp", data);
        assertEquals("fluency feast", result.sourceLabel());
        assertEquals(MathQuizFluencyLoader.DEFAULT_COUNT, result.questionCount());
        assertEquals("addition", result.operation());
        assertTrue(result.deliverable());
    }

    @Test
    void fluencyFeastWithoutProblemsUsesFeastConfigCountNotPlayerPreset() {
        OpenQuizData data = new OpenQuizData(
            "addition", 11, 39, 3, "[]", "[]", "random",
            "standard_arithmetic", "{}", true, false
        );
        QuizDeliveryPreview.Result result = QuizDeliveryPreview.fromOpenQuizData("rjcomp", data);
        assertEquals("fluency feast", result.sourceLabel());
        assertEquals(MathQuizFluencyLoader.DEFAULT_COUNT, result.questionCount());
        assertEquals("addition", result.operation());
        assertFalse(result.deliverable());
        assertTrue(result.formatSummaryLine().contains("generation failed"));
    }

    @Test
    void generatedFallbackUsesPayloadParamsWhenNoProblems() {
        OpenQuizData data = new OpenQuizData(
            "addition", 11, 39, 3, "[]", "[]", "random",
            "standard_arithmetic", "{}", false, false
        );
        QuizDeliveryPreview.Result result = QuizDeliveryPreview.fromOpenQuizData("rjcomp", data);
        assertEquals(3, result.questionCount());
        assertEquals("addition", result.operation());
        assertEquals("11-39", result.rangeLabel());
        assertTrue(result.deliverable());
    }
}
