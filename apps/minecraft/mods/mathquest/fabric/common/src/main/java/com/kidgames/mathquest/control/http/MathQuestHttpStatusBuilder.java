package com.kidgames.mathquest.control.http;

import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.control.MathQuestControlState;
import com.kidgames.mathquest.npc.MathQuestNpcCatalog;
import com.kidgames.mathquest.platform.PlatformServer;
import com.kidgames.mathquest.platform.PlayerContext;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/** Builds /api/status JSON from config + bridge-provided game state. */
public final class MathQuestHttpStatusBuilder {
    private MathQuestHttpStatusBuilder() {}

    public static Map<String, Object> statusJson(ControlPanelBridge bridge) {
        Map<String, Object> root = new LinkedHashMap<>();
        MathQuestConfig config = bridge.config();
        Map<String, Object> cfg = new LinkedHashMap<>();
        cfg.put("enabled", config.enabled);
        cfg.put("quizMode", config.quizMode);
        cfg.put("npcSpawnRadiusBlocks", config.npcSpawnRadiusBlocks);
        cfg.put("npcDespawnSeconds", config.npcDespawnSeconds);
        cfg.put("npcAllowMultipleNerds", config.npcAllowMultipleNerds);
        cfg.put("writtenColumnEvaluatorCode", config.writtenColumnEvaluatorCode);
        cfg.put("controlPanelUrl", "http://" + config.controlPanelHost + ":" + config.controlPanelPort + "/");
        root.put("config", cfg);
        root.put("worldSeed", bridge.worldSeed());
        root.put("onlinePlayers", onlinePlayerNames(bridge.platformServer()));
        root.put("playerLocations", bridge.playerLocations());
        root.put("players", playerCards(bridge));
        root.put("npcs", npcGallery(config));
        root.put("rewardGroups", rewardGroupsJson(config));
        return root;
    }

    public static List<Map<String, Object>> rewardGroupsJson(MathQuestConfig config) {
        List<Map<String, Object>> out = new ArrayList<>();
        if (config.rewardGroups == null) return out;
        for (Map.Entry<String, MathQuestConfig.RewardGroup> e : config.rewardGroups.entrySet()) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("name", e.getKey());
            MathQuestConfig.RewardGroup group = e.getValue();
            row.put("mode", group == null || group.mode == null
                ? "all"
                : MathQuestConfig.normalizeRewardGroupMode(group.mode));
            List<Map<String, Object>> entries = new ArrayList<>();
            if (group != null && group.entries != null) {
                for (MathQuestConfig.RewardEntry entry : group.entries) {
                    if (entry == null || entry.item == null || entry.item.isBlank() || entry.count <= 0) continue;
                    entries.add(Map.of("item", entry.item, "count", entry.count));
                }
            }
            row.put("entries", entries);
            out.add(row);
        }
        return out;
    }

    public static List<Map<String, Object>> playerCards(ControlPanelBridge bridge) {
        List<Map<String, Object>> out = new ArrayList<>();
        MathQuestConfig config = bridge.config();
        ControlPanelPlayerCardContributor contributor = bridge.playerCardContributor();
        for (Map.Entry<String, String> e : config.resolvePlayerRealNames().entrySet()) {
            String key = e.getKey();
            String playerName = displayName(key);
            MathQuestConfig.EffectiveQuizParams params = config.resolveForPlayer(playerName);
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("key", key);
            row.put("playerName", playerName);
            row.put("realName", e.getValue());
            row.put("online", bridge.platformServer().findOnlinePlayer(playerName) != null);
            row.put("params", Map.of(
                "operation", params.operation(),
                "minNumber", params.minNumber(),
                "maxNumber", params.maxNumber(),
                "problemsPerQuiz", params.problemsPerQuiz(),
                "quizType", config.resolveQuizType(playerName),
                "internalQuizSource", config.resolveInternalQuizSource(playerName),
                "useInternalProblemList", config.resolveUseInternalProblemList(playerName)
            ));
            row.put("npcId", config.resolveNpcSelection(playerName));
            row.put("npcLocked", config.resolveNpcLock(playerName));
            Map<String, Object> tpCredits = new LinkedHashMap<>();
            tpCredits.put("earningEnabled", config.resolveTpCreditEarningEnabled(playerName));
            tpCredits.put("creditsPerQuiz", config.resolveTpCreditsPerQuiz(playerName));
            tpCredits.put("balance", config.resolveTpCreditBalance(playerName));
            tpCredits.put("rewardChoice", config.resolveTpCreditRewardChoice(playerName));
            row.put("tpCredits", tpCredits);
            Map<String, Object> quest = contributor.questStatusForPlayer(playerName);
            if (quest != null && !quest.isEmpty()) {
                row.put("quest", quest);
            }
            MathQuestConfig.RewardEntry reward = playerReward(config, key);
            row.put("reward", Map.of("item", reward.item, "count", reward.count));
            String rewardGroup = config.resolvePlayerRewardGroup(playerName);
            row.put("rewardGroup", rewardGroup == null ? "" : rewardGroup);
            MathQuestConfig.RewardEntry fluencyReward = playerFluencyReward(config, key);
            row.put("fluencyReward", Map.of("item", fluencyReward.item, "count", fluencyReward.count));
            String fluencyRewardGroup = config.resolvePlayerFluencyRewardGroup(playerName);
            row.put("fluencyRewardGroup", fluencyRewardGroup == null ? "" : fluencyRewardGroup);
            row.put("activeNerds", bridge.activeNerdsFor(playerName));
            MathQuestControlState.PlayerNpcState state = MathQuestControlState.get(playerName);
            row.put("lastNpcState", state);
            out.add(row);
        }
        return out;
    }

    public static List<Map<String, Object>> npcGallery(MathQuestConfig config) {
        List<Map<String, Object>> out = new ArrayList<>();
        for (MathQuestNpcCatalog.NpcDef npc : MathQuestNpcCatalog.all()) {
            out.add(Map.of(
                "id", npc.id(),
                "name", npc.name(),
                "entity", npc.entity(),
                "textureUrl", "/npc/" + npc.id() + ".png",
                "dialogueLines", MathQuestNpcCatalog.dialogueLines(config, npc.id())
            ));
        }
        return out;
    }

    public static List<String> onlinePlayerNames(PlatformServer server) {
        List<String> out = new ArrayList<>();
        for (PlayerContext player : server.onlinePlayers()) {
            out.add(player.username());
        }
        return out;
    }

    public static String displayName(String key) {
        return switch (key.toLowerCase(Locale.ROOT)) {
            case "treasurehunterm" -> "TreasureHunterM";
            case "pumajockey" -> "PumaJockey";
            case "skulkscraper" -> "SkulkScraper";
            case "wildpetal" -> "WildPetal";
            default -> key;
        };
    }

    public static MathQuestConfig.RewardEntry playerReward(MathQuestConfig config, String key) {
        String playerName = displayName(key);
        String groupName = config.resolvePlayerRewardGroup(playerName);
        if (groupName != null && config.rewardGroups != null) {
            MathQuestConfig.RewardGroup group = config.rewardGroups.get(groupName);
            if (group != null && group.entries != null && !group.entries.isEmpty()) {
                return group.entries.get(0);
            }
        }
        if (config.playerRewards != null) {
            MathQuestConfig.RewardEntry entry = config.playerRewards.get(key.toLowerCase(Locale.ROOT));
            if (entry != null) return entry;
        }
        List<MathQuestConfig.RewardEntry> active = config.resolveActiveRewardEntries();
        return active.isEmpty() ? new MathQuestConfig.RewardEntry("minecraft:diamond", 1) : active.get(0);
    }

    public static MathQuestConfig.RewardEntry playerFluencyReward(MathQuestConfig config, String key) {
        String playerName = displayName(key);
        String groupName = config.resolvePlayerFluencyRewardGroup(playerName);
        if (groupName != null && config.rewardGroups != null) {
            MathQuestConfig.RewardGroup group = config.rewardGroups.get(groupName);
            if (group != null && group.entries != null && !group.entries.isEmpty()) {
                return group.entries.get(0);
            }
        }
        if (config.playerFluencyRewards != null) {
            MathQuestConfig.RewardEntry entry = config.playerFluencyRewards.get(key.toLowerCase(Locale.ROOT));
            if (entry != null) return entry;
        }
        return playerReward(config, key);
    }
}
