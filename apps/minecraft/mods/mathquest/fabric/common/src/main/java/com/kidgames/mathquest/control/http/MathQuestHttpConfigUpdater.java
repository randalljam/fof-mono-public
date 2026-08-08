package com.kidgames.mathquest.control.http;

import com.google.gson.JsonObject;
import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.npc.MathQuestNpcCatalog;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/** POST /api/config mutation — loader-agnostic MathQuestConfig updates. */
public final class MathQuestHttpConfigUpdater {
    private MathQuestHttpConfigUpdater() {}

    public static Map<String, Object> updateConfig(MathQuestConfig config, JsonObject body) {
        if (body.has("enabled")) config.enabled = body.get("enabled").getAsBoolean();
        if (body.has("quizMode")) config.quizMode = body.get("quizMode").getAsString();
        if (body.has("npcAllowMultipleNerds")) config.npcAllowMultipleNerds = body.get("npcAllowMultipleNerds").getAsBoolean();
        if (body.has("npcSpawnRadiusBlocks")) {
            config.npcSpawnRadiusBlocks = MathQuestHttpUtil.clamp(body.get("npcSpawnRadiusBlocks").getAsInt(), 1, 64);
        }
        if (body.has("npcDespawnSeconds")) {
            config.npcDespawnSeconds = MathQuestHttpUtil.clamp(body.get("npcDespawnSeconds").getAsInt(), 10, 3600);
        }
        if (body.has("writtenColumnEvaluatorCode")) {
            String code = body.get("writtenColumnEvaluatorCode").getAsString().trim();
            if (!code.isBlank()) config.writtenColumnEvaluatorCode = code;
        }
        if (body.has("rewardGroups")) {
            JsonObject groups = body.getAsJsonObject("rewardGroups");
            Map<String, MathQuestConfig.RewardGroup> map = new LinkedHashMap<>();
            for (String name : groups.keySet()) {
                if (!groups.get(name).isJsonObject()) continue;
                JsonObject obj = groups.getAsJsonObject(name);
                String mode = obj.has("mode")
                    ? MathQuestConfig.normalizeRewardGroupMode(obj.get("mode").getAsString())
                    : "all";
                List<MathQuestConfig.RewardEntry> entries = new ArrayList<>();
                if (obj.has("entries") && obj.get("entries").isJsonArray()) {
                    for (com.google.gson.JsonElement el : obj.getAsJsonArray("entries")) {
                        if (!el.isJsonObject()) continue;
                        JsonObject entryObj = el.getAsJsonObject();
                        if (!entryObj.has("item") || !entryObj.has("count")) continue;
                        entries.add(new MathQuestConfig.RewardEntry(
                            MathQuestConfig.normalizeItemId(entryObj.get("item").getAsString()),
                            Math.max(1, entryObj.get("count").getAsInt())
                        ));
                    }
                }
                String normalizedName = MathQuestConfig.normalizeGroupName(name);
                if (!normalizedName.isBlank() && !entries.isEmpty()) {
                    map.put(normalizedName, new MathQuestConfig.RewardGroup(mode, entries));
                }
            }
            config.rewardGroups = map;
            MathQuestConfig.ensureJtreeGroup(config.rewardGroups);
        }
        if (body.has("rewardGroup")) {
            String active = body.get("rewardGroup").getAsString();
            config.rewardGroup = active == null || active.isBlank()
                ? null
                : MathQuestConfig.normalizeGroupName(active);
        }
        if (body.has("playerRewards")) {
            JsonObject rewards = body.getAsJsonObject("playerRewards");
            for (String key : rewards.keySet()) {
                JsonObject obj = rewards.getAsJsonObject(key);
                MathQuestHttpPlayerBodyApplier.applyPlayerRewardSelection(
                    config,
                    MathQuestHttpStatusBuilder.displayName(key),
                    obj.get("item").getAsString(),
                    obj.get("count").getAsInt()
                );
            }
        }
        if (body.has("playerFluencyRewards")) {
            JsonObject rewards = body.getAsJsonObject("playerFluencyRewards");
            for (String key : rewards.keySet()) {
                JsonObject obj = rewards.getAsJsonObject(key);
                MathQuestHttpPlayerBodyApplier.applyPlayerFluencyRewardSelection(
                    config,
                    MathQuestHttpStatusBuilder.displayName(key),
                    obj.get("item").getAsString(),
                    obj.get("count").getAsInt()
                );
            }
        }
        if (body.has("playerRealNames")) {
            JsonObject realNames = body.getAsJsonObject("playerRealNames");
            if (config.playerRealNames == null) config.playerRealNames = new LinkedHashMap<>();
            for (String key : realNames.keySet()) {
                String realName = realNames.get(key).getAsString().trim();
                if (!realName.isBlank()) {
                    config.playerRealNames.put(key.toLowerCase(Locale.ROOT), realName);
                }
            }
        }
        if (body.has("playerQuizTypes")) {
            JsonObject quizTypes = body.getAsJsonObject("playerQuizTypes");
            if (config.playerQuizTypes == null) config.playerQuizTypes = new LinkedHashMap<>();
            for (String key : quizTypes.keySet()) {
                config.playerQuizTypes.put(key.toLowerCase(Locale.ROOT),
                    MathQuestConfig.normalizeQuizType(quizTypes.get(key).getAsString()));
            }
        }
        if (body.has("playerInternalQuizSources")) {
            JsonObject sources = body.getAsJsonObject("playerInternalQuizSources");
            if (config.playerInternalQuizSources == null) config.playerInternalQuizSources = new LinkedHashMap<>();
            if (config.playerUseInternalProblemLists == null) config.playerUseInternalProblemLists = new LinkedHashMap<>();
            for (String key : sources.keySet()) {
                String source = MathQuestConfig.normalizeInternalQuizSource(sources.get(key).getAsString());
                String normalizedKey = key.toLowerCase(Locale.ROOT);
                config.playerInternalQuizSources.put(normalizedKey, source);
                config.playerUseInternalProblemLists.put(normalizedKey, "internal_problem_list".equals(source));
            }
        }
        if (body.has("playerUseInternalProblemLists") && !body.has("playerInternalQuizSources")) {
            JsonObject useInternal = body.getAsJsonObject("playerUseInternalProblemLists");
            if (config.playerUseInternalProblemLists == null) config.playerUseInternalProblemLists = new LinkedHashMap<>();
            if (config.playerInternalQuizSources == null) config.playerInternalQuizSources = new LinkedHashMap<>();
            for (String key : useInternal.keySet()) {
                String normalizedKey = key.toLowerCase(Locale.ROOT);
                boolean useProblemList = useInternal.get(key).getAsBoolean();
                config.playerUseInternalProblemLists.put(normalizedKey, useProblemList);
                config.playerInternalQuizSources.put(normalizedKey, useProblemList ? "internal_problem_list" : "generated");
            }
        }
        if (body.has("playerNpcSelections")) {
            JsonObject selections = body.getAsJsonObject("playerNpcSelections");
            if (config.playerNpcSelections == null) config.playerNpcSelections = new LinkedHashMap<>();
            for (String key : selections.keySet()) {
                config.playerNpcSelections.put(key.toLowerCase(Locale.ROOT),
                    MathQuestNpcCatalog.byId(selections.get(key).getAsString()).id());
            }
        }
        if (body.has("playerNpcLocks")) {
            JsonObject locks = body.getAsJsonObject("playerNpcLocks");
            if (config.playerNpcLocks == null) config.playerNpcLocks = new LinkedHashMap<>();
            for (String key : locks.keySet()) {
                config.playerNpcLocks.put(key.toLowerCase(Locale.ROOT), locks.get(key).getAsBoolean());
            }
        }
        if (body.has("playerTpCreditEarningEnabled")) {
            JsonObject earningEnabled = body.getAsJsonObject("playerTpCreditEarningEnabled");
            for (String key : earningEnabled.keySet()) {
                config.setTpCreditEarningEnabled(key, earningEnabled.get(key).getAsBoolean());
            }
        }
        if (body.has("playerTpCreditsPerQuiz")) {
            JsonObject creditsPerQuiz = body.getAsJsonObject("playerTpCreditsPerQuiz");
            for (String key : creditsPerQuiz.keySet()) {
                config.setTpCreditsPerQuiz(key, creditsPerQuiz.get(key).getAsInt());
            }
        }
        if (body.has("playerTpCreditRewardChoices")) {
            JsonObject choices = body.getAsJsonObject("playerTpCreditRewardChoices");
            for (String key : choices.keySet()) {
                config.setTpCreditRewardChoice(key, choices.get(key).getAsString());
            }
        }
        if (body.has("playerPresets")) {
            JsonObject presets = body.getAsJsonObject("playerPresets");
            if (config.playerPresets == null) config.playerPresets = new LinkedHashMap<>();
            for (String key : presets.keySet()) {
                JsonObject obj = presets.getAsJsonObject(key);
                config.playerPresets.put(key.toLowerCase(Locale.ROOT), new MathQuestConfig.PlayerQuizPreset(
                    obj.has("minNumber") ? obj.get("minNumber").getAsInt() : null,
                    obj.has("maxNumber") ? obj.get("maxNumber").getAsInt() : null,
                    obj.has("operation") ? MathQuestConfig.normalizeOperation(obj.get("operation").getAsString()) : null,
                    obj.has("problemsPerQuiz") ? MathQuestHttpUtil.clamp(obj.get("problemsPerQuiz").getAsInt(), 1, 50) : null
                ));
            }
        }
        if (body.has("npcDialogues")) {
            JsonObject dialogues = body.getAsJsonObject("npcDialogues");
            if (config.npcDialogueOverrides == null) config.npcDialogueOverrides = new LinkedHashMap<>();
            for (String id : dialogues.keySet()) {
                List<String> lines = new ArrayList<>();
                for (com.google.gson.JsonElement el : dialogues.getAsJsonArray(id)) {
                    String line = el.getAsString().replace('\n', ' ').replace('\r', ' ').trim();
                    if (!line.isBlank()) lines.add(line);
                }
                config.npcDialogueOverrides.put(id, lines);
            }
        }
        config.save();
        return Map.of("ok", true);
    }
}
