package com.kidgames.mathquest.control.http;

import com.google.gson.JsonObject;
import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.npc.MathQuestNpcCatalog;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/** Applies per-player control-panel POST body fields to MathQuestConfig. */
public final class MathQuestHttpPlayerBodyApplier {
    private MathQuestHttpPlayerBodyApplier() {}

    public static void applyRewardFromBody(MathQuestConfig config, String playerName, JsonObject body) {
        boolean changed = false;
        if (body.has("rewardItem") && body.has("rewardCount")) {
            applyPlayerRewardSelection(config, playerName, body.get("rewardItem").getAsString(), body.get("rewardCount").getAsInt());
            changed = true;
        }
        if (body.has("fluencyRewardItem") && body.has("fluencyRewardCount")) {
            applyPlayerFluencyRewardSelection(
                config,
                playerName,
                body.get("fluencyRewardItem").getAsString(),
                body.get("fluencyRewardCount").getAsInt()
            );
            changed = true;
        }
        if (changed) config.save();
    }

    public static void applyRealNameFromBody(MathQuestConfig config, String playerName, JsonObject body) {
        if (!body.has("realName")) return;
        String realName = body.get("realName").getAsString().trim();
        if (realName.isBlank()) return;
        if (config.playerRealNames == null) {
            config.playerRealNames = new LinkedHashMap<>();
        }
        config.playerRealNames.put(playerName.toLowerCase(Locale.ROOT), realName);
    }

    public static void applyQuizTypeFromBody(MathQuestConfig config, String playerName, JsonObject body) {
        if (!body.has("quizType")) return;
        if (config.playerQuizTypes == null) {
            config.playerQuizTypes = new LinkedHashMap<>();
        }
        config.playerQuizTypes.put(
            playerName.toLowerCase(Locale.ROOT),
            MathQuestConfig.normalizeQuizType(body.get("quizType").getAsString())
        );
    }

    public static void applyUseInternalProblemListFromBody(MathQuestConfig config, String playerName, JsonObject body) {
        if (body.has("internalQuizSource")) {
            if (config.playerInternalQuizSources == null) {
                config.playerInternalQuizSources = new LinkedHashMap<>();
            }
            if (config.playerUseInternalProblemLists == null) {
                config.playerUseInternalProblemLists = new LinkedHashMap<>();
            }
            String source = MathQuestConfig.normalizeInternalQuizSource(body.get("internalQuizSource").getAsString());
            config.playerInternalQuizSources.put(playerName.toLowerCase(Locale.ROOT), source);
            config.playerUseInternalProblemLists.put(
                playerName.toLowerCase(Locale.ROOT),
                "internal_problem_list".equals(source)
            );
            return;
        }
        if (!body.has("useInternalProblemList")) return;
        if (config.playerUseInternalProblemLists == null) {
            config.playerUseInternalProblemLists = new LinkedHashMap<>();
        }
        if (config.playerInternalQuizSources == null) {
            config.playerInternalQuizSources = new LinkedHashMap<>();
        }
        boolean useProblemList = body.get("useInternalProblemList").getAsBoolean();
        config.playerUseInternalProblemLists.put(playerName.toLowerCase(Locale.ROOT), useProblemList);
        config.playerInternalQuizSources.put(
            playerName.toLowerCase(Locale.ROOT),
            useProblemList ? "internal_problem_list" : "generated"
        );
    }

    public static void applyNpcSelectionFromBody(MathQuestConfig config, String playerName, JsonObject body) {
        if (!body.has("npcId")) return;
        if (config.playerNpcSelections == null) {
            config.playerNpcSelections = new LinkedHashMap<>();
        }
        config.playerNpcSelections.put(
            playerName.toLowerCase(Locale.ROOT),
            MathQuestNpcCatalog.byId(body.get("npcId").getAsString()).id()
        );
    }

    public static void applyNpcLockFromBody(MathQuestConfig config, String playerName, JsonObject body) {
        if (!body.has("locked")) return;
        if (config.playerNpcLocks == null) {
            config.playerNpcLocks = new LinkedHashMap<>();
        }
        config.playerNpcLocks.put(
            playerName.toLowerCase(Locale.ROOT),
            body.get("locked").getAsBoolean()
        );
    }

    public static void applyPresetFromBody(MathQuestConfig config, String playerName, JsonObject body) {
        if (!body.has("operation") && !body.has("minNumber") && !body.has("maxNumber") && !body.has("problemsPerQuiz")) return;
        if (config.playerPresets == null) {
            config.playerPresets = new LinkedHashMap<>();
        }
        MathQuestConfig.EffectiveQuizParams existing = config.resolveForPlayer(playerName);
        config.playerPresets.put(
            playerName.toLowerCase(Locale.ROOT),
            new MathQuestConfig.PlayerQuizPreset(
                body.has("minNumber") ? body.get("minNumber").getAsInt() : existing.minNumber(),
                body.has("maxNumber") ? body.get("maxNumber").getAsInt() : existing.maxNumber(),
                body.has("operation") ? MathQuestConfig.normalizeOperation(body.get("operation").getAsString()) : existing.operation(),
                body.has("problemsPerQuiz") ? MathQuestHttpUtil.clamp(body.get("problemsPerQuiz").getAsInt(), 1, 50) : existing.problemsPerQuiz()
            )
        );
    }

    public static void applyAllFromBody(MathQuestConfig config, String playerName, JsonObject body) {
        applyRewardFromBody(config, playerName, body);
        applyRealNameFromBody(config, playerName, body);
        applyQuizTypeFromBody(config, playerName, body);
        applyUseInternalProblemListFromBody(config, playerName, body);
        applyNpcSelectionFromBody(config, playerName, body);
        applyNpcLockFromBody(config, playerName, body);
        applyPresetFromBody(config, playerName, body);
    }

    public static void applyPlayerRewardSelection(MathQuestConfig config, String playerName, String rawValue, int count) {
        String key = playerName.toLowerCase(Locale.ROOT);
        if (config.isKnownRewardGroupName(rawValue)) {
            if (config.playerRewardGroups == null) {
                config.playerRewardGroups = new LinkedHashMap<>();
            }
            config.playerRewardGroups.put(key, MathQuestConfig.normalizeGroupName(rawValue));
            if (config.playerRewards != null) {
                config.playerRewards.remove(key);
            }
            return;
        }
        if (config.playerRewardGroups != null) {
            config.playerRewardGroups.remove(key);
        }
        setPlayerReward(config, playerName, rawValue, count);
    }

    public static void setPlayerReward(MathQuestConfig config, String playerName, String item, int count) {
        if (config.playerRewards == null) {
            config.playerRewards = new LinkedHashMap<>();
        }
        config.playerRewards.put(
            playerName.toLowerCase(Locale.ROOT),
            new MathQuestConfig.RewardEntry(MathQuestConfig.normalizeItemId(item), Math.max(1, count))
        );
    }

    public static void applyPlayerFluencyRewardSelection(MathQuestConfig config, String playerName, String rawValue, int count) {
        String key = playerName.toLowerCase(Locale.ROOT);
        if (config.isKnownRewardGroupName(rawValue)) {
            if (config.playerFluencyRewardGroups == null) {
                config.playerFluencyRewardGroups = new LinkedHashMap<>();
            }
            config.playerFluencyRewardGroups.put(key, MathQuestConfig.normalizeGroupName(rawValue));
            if (config.playerFluencyRewards != null) {
                config.playerFluencyRewards.remove(key);
            }
            return;
        }
        if (config.playerFluencyRewardGroups != null) {
            config.playerFluencyRewardGroups.remove(key);
        }
        setPlayerFluencyReward(config, playerName, rawValue, count);
    }

    public static void setPlayerFluencyReward(MathQuestConfig config, String playerName, String item, int count) {
        if (config.playerFluencyRewards == null) {
            config.playerFluencyRewards = new LinkedHashMap<>();
        }
        config.playerFluencyRewards.put(
            playerName.toLowerCase(Locale.ROOT),
            new MathQuestConfig.RewardEntry(MathQuestConfig.normalizeItemId(item), Math.max(1, count))
        );
    }
}
