package com.kidgames.mathquest.quiz;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

/** Client-side quiz behavior/display options carried by server quiz payloads. */
public record QuizSessionOptions(
    boolean questMode,
    boolean showFlagControls,
    boolean showQuitControls,
    boolean showProgress,
    boolean showSourceLabel,
    boolean showPauseButton,
    boolean suppressRewards,
    boolean repeatUntilFluent,
    int fluencyMs,
    int fastCorrectRequired,
    boolean fluencyFeastMode,
    boolean tpCreditEligible,
    String tpCreditCompletionToken
) {
    public static QuizSessionOptions standard() {
        return new QuizSessionOptions(
            false,
            true,
            true,
            true,
            true,
            true,
            false,
            false,
            2000,
            1,
            false,
            true,
            ""
        );
    }
    public static QuizSessionOptions fluencyFeast() {
        return new QuizSessionOptions(
            false,
            true,
            true,
            true,
            true,
            true,
            false,
            false,
            2000,
            1,
            true,
            true,
            ""
        );
    }

    public static QuizSessionOptions questFixed(int fluencyMs, int fastCorrectRequired, boolean repeatUntilFluent) {
        return new QuizSessionOptions(
            true,
            false,
            false,
            false,
            false,
            false,
            true,
            repeatUntilFluent,
            Math.max(1, fluencyMs),
            Math.max(1, fastCorrectRequired),
            false,
            true,
            ""
        );
    }

    public QuizSessionOptions withTpCreditCompletionToken(String token) {
        return copy(true, token == null ? "" : token);
    }

    /** Marks an abandoned/partial quiz as ineligible even if it later opens a result screen. */
    public QuizSessionOptions withoutTpCreditAward() {
        return copy(false, tpCreditCompletionToken);
    }

    private QuizSessionOptions copy(boolean eligible, String token) {
        return new QuizSessionOptions(
            questMode,
            showFlagControls,
            showQuitControls,
            showProgress,
            showSourceLabel,
            showPauseButton,
            suppressRewards,
            repeatUntilFluent,
            fluencyMs,
            fastCorrectRequired,
            fluencyFeastMode,
            eligible,
            token
        );
    }

    public static QuizSessionOptions fromJson(String json) {
        if (json == null || json.isBlank()) return standard();
        try {
            JsonObject obj = JsonParser.parseString(json).getAsJsonObject();
            QuizSessionOptions defaults = standard();
            return new QuizSessionOptions(
                boolOr(obj, "questMode", defaults.questMode()),
                boolOr(obj, "showFlagControls", defaults.showFlagControls()),
                boolOr(obj, "showQuitControls", defaults.showQuitControls()),
                boolOr(obj, "showProgress", defaults.showProgress()),
                boolOr(obj, "showSourceLabel", defaults.showSourceLabel()),
                boolOr(obj, "showPauseButton", defaults.showPauseButton()),
                boolOr(obj, "suppressRewards", defaults.suppressRewards()),
                boolOr(obj, "repeatUntilFluent", defaults.repeatUntilFluent()),
                intOr(obj, "fluencyMs", defaults.fluencyMs()),
                intOr(obj, "fastCorrectRequired", defaults.fastCorrectRequired()),
                boolOr(obj, "fluencyFeastMode", defaults.fluencyFeastMode()),
                boolOr(obj, "tpCreditEligible", defaults.tpCreditEligible()),
                stringOr(obj, "tpCreditCompletionToken", defaults.tpCreditCompletionToken())
            );
        } catch (Exception e) {
            return standard();
        }
    }

    public String toJson() {
        JsonObject obj = new JsonObject();
        obj.addProperty("questMode", questMode);
        obj.addProperty("showFlagControls", showFlagControls);
        obj.addProperty("showQuitControls", showQuitControls);
        obj.addProperty("showProgress", showProgress);
        obj.addProperty("showSourceLabel", showSourceLabel);
        obj.addProperty("showPauseButton", showPauseButton);
        obj.addProperty("suppressRewards", suppressRewards);
        obj.addProperty("repeatUntilFluent", repeatUntilFluent);
        obj.addProperty("fluencyMs", fluencyMs);
        obj.addProperty("fastCorrectRequired", fastCorrectRequired);
        obj.addProperty("fluencyFeastMode", fluencyFeastMode);
        obj.addProperty("tpCreditEligible", tpCreditEligible);
        obj.addProperty("tpCreditCompletionToken", tpCreditCompletionToken == null ? "" : tpCreditCompletionToken);
        return obj.toString();
    }

    private static boolean boolOr(JsonObject obj, String key, boolean fallback) {
        return obj.has(key) && !obj.get(key).isJsonNull() ? obj.get(key).getAsBoolean() : fallback;
    }

    private static int intOr(JsonObject obj, String key, int fallback) {
        return obj.has(key) && !obj.get(key).isJsonNull() ? obj.get(key).getAsInt() : fallback;
    }

    private static String stringOr(JsonObject obj, String key, String fallback) {
        return obj.has(key) && !obj.get(key).isJsonNull() ? obj.get(key).getAsString() : fallback;
    }
}
