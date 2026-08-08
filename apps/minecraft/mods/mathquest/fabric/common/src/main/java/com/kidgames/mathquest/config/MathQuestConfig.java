package com.kidgames.mathquest.config;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.kidgames.mathquest.platform.MathQuestPaths;

import java.io.IOException;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;

public class MathQuestConfig {
    public static MathQuestConfig INSTANCE;
    private static Path loadedConfigFile;
    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();
    private static final String CONFIG_FILE = "mathquest.json";

    public int quizIntervalSeconds = 30;
    public int problemsPerQuiz = 5;
    /** Global default operand range when a player has no preset (inclusive). */
    public int minNumber = 0;
    public int maxNumber = 9;
    /** Default quiz operation when a player has no per-player preset. */
    public String operation = "multiplication";
    /**
     * Per-player overrides keyed by lowercase player name (e.g. "wildpetal").
     * Any field left null inherits from the global defaults above.
     */
    public Map<String, PlayerQuizPreset> playerPresets = defaultFamilyPresets();
    public List<RewardEntry> rewards = List.of(
        new RewardEntry("minecraft:diamond", 1),
        new RewardEntry("minecraft:golden_apple", 2),
        new RewardEntry("minecraft:enchanted_golden_apple", 1)
    );
    /**
     * Named reward groups: each maps a lowercase id (e.g. {@code jtree}) to entries plus a mode.
     * When {@link #rewardGroup} is set, {@link #resolveActiveRewardPlan()} uses that group;
     * otherwise the flat {@link #rewards} list is used.
     */
    public Map<String, RewardGroup> rewardGroups = null;
    public Map<String, String> playerRealNames = defaultPlayerRealNames();
    public Map<String, RewardEntry> playerRewards = defaultPlayerRewards();
    /** Per-player reward group override (lowercase player -> group name). Takes precedence over {@link #playerRewards}. */
    public Map<String, String> playerRewardGroups = new LinkedHashMap<>();
    public Map<String, String> playerQuizTypes = defaultPlayerQuizTypes();
    public Map<String, String> playerInternalQuizSources = defaultPlayerInternalQuizSources();
    public Map<String, Boolean> playerUseInternalProblemLists = defaultPlayerUseInternalProblemLists();
    public Map<String, String> playerNpcSelections = defaultPlayerNpcSelections();
    public Map<String, Boolean> playerNpcLocks = defaultPlayerNpcLocks();
    /** Per-player switch for earning teleport credits on completed quizzes. Missing players default to false. */
    public Map<String, Boolean> playerTpCreditEarningEnabled = new LinkedHashMap<>();
    /** Per-player number of teleport credits awarded per completed quiz. Missing players default to one. */
    public Map<String, Integer> playerTpCreditsPerQuiz = new LinkedHashMap<>();
    /** Persistent per-player teleport-credit balances. Missing players default to zero. */
    public Map<String, Integer> playerTpCreditBalances = new LinkedHashMap<>();
    /** Per-player credit reward selection. Teleport is the initial and currently only supported choice. */
    public Map<String, String> playerTpCreditRewardChoices = new LinkedHashMap<>();
    public Map<String, List<String>> npcDialogueOverrides = new LinkedHashMap<>();
    public String writtenColumnEvaluatorCode = "paper";
    /**
     * Active group id (lowercase), e.g. {@code jtree}. When null or blank, {@link #rewards} is used.
     */
    public String rewardGroup = "jtree";
    public String rewardMode = "random"; // "random" or "all" for flat {@link #rewards} only
    public boolean enabled = true;
    /**
     * Forge client workaround for Ice and Fire / multipart bosses: when true, client-side
     * projectile hit tests ignore Forge {@code PartEntity} and Ice and Fire
     * {@code EntityMutlipartPart} hitboxes (dragon parts, etc.) so tridents do not freeze
     * the client. Server-side collision is unchanged. Set false to disable.
     */
    public boolean excludeMultipartFromClientProjectileHits = true;
    public String quizMode = "popup"; // "popup" (timed screen overlay) or "npc" (wandering nerd)
    public int npcSpawnRadiusBlocks = 10;
    public int npcDespawnSeconds = 120;
    public boolean logNerdSpawn = true;
    public boolean logNerdLocation = true;
    public boolean npcAllowMultipleNerds = false;
    /**
     * When false, Wandering Nerd only spawns via the web control panel, server console, or
     * in-game manual commands — not on the {@link #quizIntervalSeconds} world tick.
     */
    public boolean npcAutomaticSpawnEnabled = false;
    public boolean controlPanelEnabled = true;
    public String controlPanelHost = "127.0.0.1";
    public int controlPanelPort = 8765;
    /**
     * Optional directory for live control-panel assets. Point this at
     * {@code assets/mathquest}; static files are served from disk first with jar fallback.
     */
    public String controlPanelAssetsDir = null;
    /**
     * Automatic Wandering Nerd spawn targeting (server world tick): {@code all} = try to spawn for every
     * online player each interval; {@code random} = pick one random online player per interval;
     * {@code one} = only {@link #npcSpawnTargetPlayer} when they are online.
     */
    public String npcSpawnTargetMode = "all";
    /**
     * When {@link #npcSpawnTargetMode} is {@code one}: lowercase Minecraft username to spawn near.
     * Ignored for other modes.
     */
    public String npcSpawnTargetPlayer = null;

    /**
     * Optional absolute path (leading {@code ~} is expanded to the user home). When set, the
     * legacy MathQuest SQLite database is written under this directory instead
     * of the Fabric config dir. Used to consolidate singleplayer data into the dedicated
     * server's config dir so all sessions land in one place for analysis.
     */
    public String sharedDataDir = DEFAULT_SHARED_DATA_DIR;
    /**
     * Optional absolute path for MathQuest's canonical single-session SQLite exports.
     * Files written here are compatible with the math-quiz app's SQLite intake format.
     */
    public String mathQuizSingleDbDir = DEFAULT_MATH_QUIZ_SINGLE_DB_DIR;
    /**
     * Optional absolute path for the active accumulated per-user Math Quiz SQLite files.
     * MathQuest appends standard arithmetic sessions here after writing the raw
     * single-session export.
     */
    public String mathQuizActiveDbDir = DEFAULT_MATH_QUIZ_ACTIVE_DB_DIR;
    /** Enables the local Python ingest bridge that appends sessions to {@link #mathQuizActiveDbDir}. */
    public boolean mathQuizIngestEnabled = true;
    /** Python executable used for the local ingest bridge. */
    public String mathQuizIngestPython = "python3";
    /** Node executable used for the fluency feast bridge. */
    public String mathQuizNodeExecutable = "node";
    /** When false, internal_fluency_feast falls back to generated arithmetic. */
    public boolean fluencyFeastEnabled = true;
    /** Per-player reward when end-of-quiz % fluent improves by at least one point. */
    public Map<String, RewardEntry> playerFluencyRewards = defaultPlayerFluencyRewards();
    /** Per-player fluency reward group override (lowercase player -> group name). */
    public Map<String, String> playerFluencyRewardGroups = new LinkedHashMap<>();

    /** Default for {@link #sharedDataDir} on a fresh install: the local dedicated server's config dir. */
    public static final String DEFAULT_SHARED_DATA_DIR = "~/Documents/Code/mathquest-server/config";
    public static final String DEFAULT_MATH_QUIZ_SINGLE_DB_DIR = defaultMathQuizSingleDbDir();
    public static final String DEFAULT_MATH_QUIZ_ACTIVE_DB_DIR = defaultMathQuizActiveDbDir();
    public static final Path DEFAULT_MATH_QUIZ_SINGLE_DB_DIR_PATH = resolveDefaultPath(DEFAULT_MATH_QUIZ_SINGLE_DB_DIR);
    public static final Path DEFAULT_MATH_QUIZ_ACTIVE_DB_DIR_PATH = resolveDefaultPath(DEFAULT_MATH_QUIZ_ACTIVE_DB_DIR);
    @Deprecated
    public static final String DEFAULT_MATH_QUIZ_EXPORT_DIR = DEFAULT_MATH_QUIZ_SINGLE_DB_DIR;
    @Deprecated
    public static final String DEFAULT_MATH_QUIZ_ACTIVE_DIR = DEFAULT_MATH_QUIZ_ACTIVE_DB_DIR;
    private static final String LEGACY_MATH_QUIZ_EXPORT_DIR = "~/Documents/Code/fof-mono/apps/math-quiz/_data/mathquest";
    private static final String LEGACY_DASHED_TLKIDS_SUFFIX = "/apps/math-quiz/_data/tl-kids";

    private static String defaultMathQuizDataRoot() {
        String home = System.getProperty("user.home");
        Path worktree = Path.of(home, "Documents/Code/feature-minecraft-mod-forge/apps/math-quiz/_data");
        if (Files.isDirectory(worktree)) {
            return "~/Documents/Code/feature-minecraft-mod-forge/apps/math-quiz/_data";
        }
        return "~/Documents/Code/fof-mono/apps/math-quiz/_data";
    }

    private static String defaultMathQuizSingleDbDir() {
        return defaultMathQuizDataRoot() + "/_single-session-sqlite-files";
    }

    private static String defaultMathQuizActiveDbDir() {
        return defaultMathQuizDataRoot() + "/tlkids";
    }

    private static Path resolveDefaultPath(String configured) {
        String path = configured;
        if (path.startsWith("~")) {
            String home = System.getProperty("user.home");
            if (home != null && !home.isEmpty()) {
                path = home + path.substring(1);
            }
        }
        return Path.of(path).normalize();
    }

    public static class RewardEntry {
        public String item;
        public int count;

        public RewardEntry() {}

        public RewardEntry(String item, int count) {
            this.item = item;
            this.count = count;
        }
    }

    public static class RewardGroup {
        public String mode = "all";
        public List<RewardEntry> entries = new ArrayList<>();

        public RewardGroup() {}

        public RewardGroup(String mode, List<RewardEntry> entries) {
            this.mode = mode;
            this.entries = entries == null ? new ArrayList<>() : new ArrayList<>(entries);
        }
    }

    public record RewardPlan(List<RewardEntry> entries, String mode) {}

    public static class PlayerQuizPreset {
        public Integer minNumber;
        public Integer maxNumber;
        public String operation;
        public Integer problemsPerQuiz;

        public PlayerQuizPreset() {}

        public PlayerQuizPreset(Integer minNumber, Integer maxNumber, String operation) {
            this(minNumber, maxNumber, operation, null);
        }
        public PlayerQuizPreset(Integer minNumber, Integer maxNumber, String operation, Integer problemsPerQuiz) {
            this.minNumber = minNumber;
            this.maxNumber = maxNumber;
            this.operation = operation;
            this.problemsPerQuiz = problemsPerQuiz;
        }
    }

    public record EffectiveQuizParams(int minNumber, int maxNumber, String operation, int problemsPerQuiz) {}

    private static List<RewardEntry> jtreeRewardEntries() {
        return List.of(
            new RewardEntry("minecraft:diamond", 1),
            new RewardEntry("minecraft:cooked_beef", 8),
            new RewardEntry("minecraft:golden_apple", 1),
            new RewardEntry("minecraft:cactus", 1)
        );
    }

    private static Map<String, RewardGroup> defaultRewardGroups() {
        Map<String, RewardGroup> m = new LinkedHashMap<>();
        m.put("jtree", new RewardGroup("random", new ArrayList<>(jtreeRewardEntries())));
        return m;
    }
    private static Map<String, RewardEntry> defaultPlayerRewards() {
        Map<String, RewardEntry> m = new LinkedHashMap<>();
        m.put("rjcomp", new RewardEntry("minecraft:diamond", 1));
        m.put("treasurehunterm", new RewardEntry("minecraft:polished_deepslate", 1));
        m.put("pumajockey", new RewardEntry("minecraft:golden_apple", 1));
        m.put("skulkscraper", new RewardEntry("minecraft:diamond", 1));
        m.put("wildpetal", new RewardEntry("minecraft:cherry_sapling", 8));
        return m;
    }
    private static Map<String, RewardEntry> defaultPlayerFluencyRewards() {
        Map<String, RewardEntry> m = new LinkedHashMap<>();
        m.put("rjcomp", new RewardEntry("minecraft:emerald", 1));
        m.put("treasurehunterm", new RewardEntry("minecraft:emerald", 8));
        m.put("pumajockey", new RewardEntry("minecraft:emerald", 1));
        m.put("skulkscraper", new RewardEntry("minecraft:emerald", 1));
        m.put("wildpetal", new RewardEntry("minecraft:emerald", 4));
        return m;
    }
    public static Map<String, String> defaultPlayerRealNames() {
        Map<String, String> m = new LinkedHashMap<>();
        m.put("rjcomp", "Randy");
        m.put("treasurehunterm", "K2");
        m.put("pumajockey", "TL");
        m.put("skulkscraper", "Guest");
        m.put("wildpetal", "Kid1");
        return m;
    }
    private static Map<String, String> defaultPlayerQuizTypes() {
        Map<String, String> m = new LinkedHashMap<>();
        m.put("rjcomp", "standard_arithmetic");
        m.put("treasurehunterm", "standard_arithmetic");
        m.put("pumajockey", "standard_arithmetic");
        m.put("skulkscraper", "standard_arithmetic");
        m.put("wildpetal", "standard_arithmetic");
        return m;
    }
    private static Map<String, Boolean> defaultPlayerUseInternalProblemLists() {
        Map<String, Boolean> m = new LinkedHashMap<>();
        m.put("rjcomp", false);
        m.put("treasurehunterm", false);
        m.put("pumajockey", false);
        m.put("skulkscraper", false);
        m.put("wildpetal", false);
        return m;
    }
    private static Map<String, String> defaultPlayerInternalQuizSources() {
        Map<String, String> m = new LinkedHashMap<>();
        m.put("rjcomp", "internal_quick_quiz");
        m.put("treasurehunterm", "internal_quick_quiz");
        m.put("pumajockey", "internal_quick_quiz");
        m.put("skulkscraper", "internal_quick_quiz");
        m.put("wildpetal", "internal_quick_quiz");
        return m;
    }
    private static Map<String, String> defaultPlayerNpcSelections() {
        Map<String, String> m = new LinkedHashMap<>();
        m.put("rjcomp", "wandering_nerd");
        m.put("treasurehunterm", "wandering_nerd");
        m.put("pumajockey", "wandering_nerd");
        m.put("skulkscraper", "wandering_nerd");
        m.put("wildpetal", "wandering_nerd");
        return m;
    }
    private static Map<String, Boolean> defaultPlayerNpcLocks() {
        Map<String, Boolean> m = new LinkedHashMap<>();
        m.put("rjcomp", true);
        m.put("treasurehunterm", true);
        m.put("pumajockey", true);
        m.put("skulkscraper", true);
        m.put("wildpetal", true);
        return m;
    }
    public static void ensurePlayerRealNames(Map<String, String> map) {
        if (map == null) return;
        for (Map.Entry<String, String> e : defaultPlayerRealNames().entrySet()) {
            map.putIfAbsent(e.getKey(), e.getValue());
        }
    }
    public static void ensurePlayerRewards(Map<String, RewardEntry> map) {
        if (map == null) return;
        for (Map.Entry<String, RewardEntry> e : defaultPlayerRewards().entrySet()) {
            map.putIfAbsent(e.getKey(), e.getValue());
        }
    }
    public static void ensurePlayerFluencyRewards(Map<String, RewardEntry> map) {
        if (map == null) return;
        for (Map.Entry<String, RewardEntry> e : defaultPlayerFluencyRewards().entrySet()) {
            map.putIfAbsent(e.getKey(), e.getValue());
        }
    }
    public Optional<RewardEntry> resolveFluencyImprovementReward(String playerName) {
        List<RewardEntry> entries = resolveFluencyImprovementRewards(playerName);
        if (entries.isEmpty()) return Optional.empty();
        return Optional.of(entries.get(0));
    }

    public List<RewardEntry> resolveFluencyImprovementRewards(String playerName) {
        RewardPlan plan = resolveFluencyRewardPlanForPlayer(playerName);
        if (plan.entries().isEmpty()) return List.of();
        String mode = normalizeRewardGroupMode(plan.mode());
        if ("random".equals(mode) || "choose".equals(mode)) {
            java.util.Random random = new java.util.Random();
            return List.of(plan.entries().get(random.nextInt(plan.entries().size())));
        }
        return plan.entries();
    }

    public String resolvePlayerFluencyRewardGroup(String playerName) {
        if (playerName == null || playerName.isBlank() || playerFluencyRewardGroups == null) return null;
        String groupName = playerFluencyRewardGroups.get(playerName.toLowerCase(Locale.ROOT));
        if (groupName == null || groupName.isBlank()) return null;
        return isKnownRewardGroupName(groupName) ? normalizeGroupName(groupName) : null;
    }

    public RewardPlan resolveFluencyRewardPlanForPlayer(String playerName) {
        if (resolveTpCreditEarningEnabled(playerName)) {
            return new RewardPlan(List.of(), "all");
        }
        String groupName = resolvePlayerFluencyRewardGroup(playerName);
        if (groupName != null && rewardGroups != null) {
            RewardGroup group = rewardGroups.get(groupName);
            if (group != null && group.entries != null && !group.entries.isEmpty()) {
                return new RewardPlan(copyEntries(group.entries), normalizeRewardGroupMode(group.mode));
            }
        }
        if (playerName != null && !playerName.isBlank() && playerFluencyRewards != null) {
            RewardEntry entry = playerFluencyRewards.get(playerName.toLowerCase(Locale.ROOT));
            if (entry != null && entry.item != null && !entry.item.isBlank() && entry.count > 0) {
                return new RewardPlan(List.of(new RewardEntry(entry.item, entry.count)), "all");
            }
        }
        RewardEntry fallback = defaultPlayerFluencyRewards().get(
            playerName == null ? "" : playerName.toLowerCase(Locale.ROOT)
        );
        if (fallback != null && fallback.item != null && !fallback.item.isBlank() && fallback.count > 0) {
            return new RewardPlan(List.of(new RewardEntry(fallback.item, fallback.count)), "all");
        }
        return new RewardPlan(List.of(), "all");
    }

    /** Ensures the {@code jtree} group exists (for config load / hand-edited JSON). */
    public static void ensureJtreeGroup(Map<String, RewardGroup> map) {
        if (map == null) return;
        if (!map.containsKey("jtree")) {
            map.put("jtree", new RewardGroup("random", new ArrayList<>(jtreeRewardEntries())));
        }
    }

    public static String normalizeRewardGroupMode(String raw) {
        if (raw == null || raw.isBlank()) return "all";
        String s = raw.trim().toLowerCase(Locale.ROOT).replace('-', '_').replace(' ', '_');
        return switch (s) {
            case "all", "give_all", "everything" -> "all";
            case "random", "one", "pick_one", "pick_random" -> "random";
            case "choose", "player_choose", "pick", "select" -> "choose";
            default -> "all";
        };
    }

    public static String normalizeGroupName(String raw) {
        if (raw == null || raw.isBlank()) return "";
        return raw.trim().toLowerCase(Locale.ROOT).replace('-', '_').replace(' ', '_');
    }

    public RewardGroup resolveRewardGroupByName(String name) {
        if (name == null || name.isBlank() || rewardGroups == null) return null;
        return rewardGroups.get(normalizeGroupName(name));
    }

    public boolean isKnownRewardGroupName(String raw) {
        if (raw == null || raw.isBlank() || rewardGroups == null) return false;
        RewardGroup group = rewardGroups.get(normalizeGroupName(raw));
        return group != null && group.entries != null && !group.entries.isEmpty();
    }

    public String resolvePlayerRewardGroup(String playerName) {
        if (playerName == null || playerName.isBlank() || playerRewardGroups == null) return null;
        String groupName = playerRewardGroups.get(playerName.toLowerCase(Locale.ROOT));
        if (groupName == null || groupName.isBlank()) return null;
        return isKnownRewardGroupName(groupName) ? normalizeGroupName(groupName) : null;
    }

    public RewardPlan resolveActiveRewardPlan() {
        if (rewardGroup != null && !rewardGroup.isBlank() && rewardGroups != null) {
            String key = normalizeGroupName(rewardGroup);
            RewardGroup group = rewardGroups.get(key);
            if (group != null && group.entries != null && !group.entries.isEmpty()) {
                return new RewardPlan(copyEntries(group.entries), normalizeRewardGroupMode(group.mode));
            }
        }
        List<RewardEntry> flat = rewards != null ? rewards : List.of();
        String mode = "all".equals(rewardMode) ? "all" : "random";
        return new RewardPlan(copyEntries(flat), mode);
    }

    public RewardPlan resolveRewardPlanForPlayer(String playerName) {
        if (resolveTpCreditEarningEnabled(playerName)) {
            return new RewardPlan(List.of(), "all");
        }
        String groupName = resolvePlayerRewardGroup(playerName);
        if (groupName != null) {
            RewardGroup group = rewardGroups.get(groupName);
            return new RewardPlan(copyEntries(group.entries), normalizeRewardGroupMode(group.mode));
        }
        if (playerName != null && !playerName.isBlank() && playerRewards != null) {
            RewardEntry entry = playerRewards.get(playerName.toLowerCase(Locale.ROOT));
            if (entry != null && entry.item != null && !entry.item.isBlank() && entry.count > 0) {
                return new RewardPlan(List.of(new RewardEntry(entry.item, entry.count)), "all");
            }
        }
        return resolveActiveRewardPlan();
    }

    /**
     * Returns the list used for quiz rewards: active group entries or flat {@link #rewards}.
     * Never null (may be empty).
     */
    public List<RewardEntry> resolveActiveRewardEntries() {
        return resolveActiveRewardPlan().entries();
    }

    public List<RewardEntry> resolveRewardsForPlayer(String playerName) {
        return resolveRewardPlanForPlayer(playerName).entries();
    }

    public boolean hasPlayerReward(String playerName) {
        if (playerName == null || playerName.isBlank()) return false;
        if (resolvePlayerRewardGroup(playerName) != null) return true;
        return playerRewards != null && playerRewards.containsKey(playerName.toLowerCase(Locale.ROOT));
    }

    private static List<RewardEntry> copyEntries(List<RewardEntry> source) {
        if (source == null || source.isEmpty()) return List.of();
        List<RewardEntry> out = new ArrayList<>();
        for (RewardEntry entry : source) {
            if (entry == null || entry.item == null || entry.item.isBlank() || entry.count <= 0) continue;
            out.add(new RewardEntry(entry.item, entry.count));
        }
        return out;
    }
    public String resolveRealName(String playerName) {
        if (playerName != null && !playerName.isBlank() && playerRealNames != null) {
            String key = playerName.toLowerCase(Locale.ROOT);
            String realName = playerRealNames.get(key);
            if (realName == null) {
                for (Map.Entry<String, String> e : playerRealNames.entrySet()) {
                    if (e.getKey() != null && e.getKey().equalsIgnoreCase(playerName)) {
                        realName = e.getValue();
                        break;
                    }
                }
            }
            if (realName != null && !realName.isBlank()) return realName.trim();
        }
        return playerName == null || playerName.isBlank() ? "unknown" : playerName;
    }
    public Map<String, String> resolvePlayerRealNames() {
        if (playerRealNames == null) playerRealNames = new LinkedHashMap<>();
        ensurePlayerRealNames(playerRealNames);
        Map<String, String> out = new LinkedHashMap<>();
        for (Map.Entry<String, String> e : playerRealNames.entrySet()) {
            String key = e.getKey() == null ? "" : e.getKey().toLowerCase(Locale.ROOT).trim();
            String value = e.getValue() == null ? "" : e.getValue().trim();
            if (!key.isBlank() && !value.isBlank()) out.put(key, value);
        }
        return out;
    }
    public String resolveQuizType(String playerName) {
        if (playerName != null && !playerName.isBlank() && playerQuizTypes != null) {
            return normalizeQuizType(playerQuizTypes.get(playerName.toLowerCase(Locale.ROOT)));
        }
        return "standard_arithmetic";
    }
    public boolean resolveUseInternalProblemList(String playerName) {
        return "internal_problem_list".equals(resolveInternalQuizSource(playerName));
    }
    public String resolveInternalQuizSource(String playerName) {
        if (playerName != null && !playerName.isBlank() && playerInternalQuizSources != null) {
            String source = playerInternalQuizSources.get(playerName.toLowerCase(Locale.ROOT));
            if (source != null && !source.isBlank()) return normalizeInternalQuizSource(source);
        }
        return "internal_quick_quiz";
    }
    public String resolveNpcSelection(String playerName) {
        if (playerName != null && !playerName.isBlank() && playerNpcSelections != null) {
            String npcId = playerNpcSelections.get(playerName.toLowerCase(Locale.ROOT));
            if (npcId != null && !npcId.isBlank()) return npcId;
        }
        return "wandering_nerd";
    }
    public boolean resolveNpcLock(String playerName) {
        if (playerName != null && !playerName.isBlank() && playerNpcLocks != null) {
            Boolean locked = playerNpcLocks.get(playerName.toLowerCase(Locale.ROOT));
            if (locked != null) return locked;
        }
        return true;
    }

    public boolean resolveTpCreditEarningEnabled(String playerName) {
        return Boolean.TRUE.equals(playerMapValue(playerTpCreditEarningEnabled, playerName));
    }

    public int resolveTpCreditsPerQuiz(String playerName) {
        Integer configured = playerMapValue(playerTpCreditsPerQuiz, playerName);
        return clampTpCreditsPerQuiz(configured == null ? 1 : configured);
    }

    public int resolveTpCreditBalance(String playerName) {
        Integer configured = playerMapValue(playerTpCreditBalances, playerName);
        return Math.max(0, configured == null ? 0 : configured);
    }

    public String resolveTpCreditRewardChoice(String playerName) {
        return normalizeTpCreditRewardChoice(playerMapValue(playerTpCreditRewardChoices, playerName));
    }

    public void setTpCreditEarningEnabled(String playerName, boolean enabled) {
        if (playerTpCreditEarningEnabled == null) playerTpCreditEarningEnabled = new LinkedHashMap<>();
        putPlayerValue(playerTpCreditEarningEnabled, playerName, enabled);
    }

    public void setTpCreditsPerQuiz(String playerName, int creditsPerQuiz) {
        if (playerTpCreditsPerQuiz == null) playerTpCreditsPerQuiz = new LinkedHashMap<>();
        putPlayerValue(playerTpCreditsPerQuiz, playerName, clampTpCreditsPerQuiz(creditsPerQuiz));
    }

    public void setTpCreditBalance(String playerName, int balance) {
        if (playerTpCreditBalances == null) playerTpCreditBalances = new LinkedHashMap<>();
        putPlayerValue(playerTpCreditBalances, playerName, Math.max(0, balance));
    }

    public void setTpCreditRewardChoice(String playerName, String rewardChoice) {
        if (playerTpCreditRewardChoices == null) playerTpCreditRewardChoices = new LinkedHashMap<>();
        putPlayerValue(playerTpCreditRewardChoices, playerName, normalizeTpCreditRewardChoice(rewardChoice));
    }

    public static int clampTpCreditsPerQuiz(int creditsPerQuiz) {
        return Math.max(1, Math.min(100, creditsPerQuiz));
    }

    /** Teleport is the initial and currently only supported TP-credit reward. */
    public static String normalizeTpCreditRewardChoice(String raw) {
        return "teleport";
    }

    private static <T> T playerMapValue(Map<String, T> map, String playerName) {
        if (map == null || playerName == null || playerName.isBlank()) return null;
        String normalized = playerName.trim().toLowerCase(Locale.ROOT);
        T direct = map.get(normalized);
        if (direct != null || map.containsKey(normalized)) return direct;
        for (Map.Entry<String, T> entry : map.entrySet()) {
            if (entry.getKey() != null && entry.getKey().equalsIgnoreCase(normalized)) {
                return entry.getValue();
            }
        }
        return null;
    }

    private static <T> void putPlayerValue(Map<String, T> map, String playerName, T value) {
        if (playerName == null || playerName.isBlank()) {
            throw new IllegalArgumentException("playerName must not be blank");
        }
        String normalized = playerName.trim().toLowerCase(Locale.ROOT);
        map.keySet().removeIf(key -> key != null && !key.equals(normalized) && key.equalsIgnoreCase(normalized));
        map.put(normalized, value);
    }
    public List<String> resolveNpcDialogueLines(String npcId, List<String> defaults) {
        if (npcId != null && npcDialogueOverrides != null) {
            List<String> lines = npcDialogueOverrides.get(npcId);
            if (lines != null && !lines.isEmpty()) {
                List<String> clean = new ArrayList<>();
                for (String line : lines) {
                    if (line != null && !line.isBlank()) {
                        clean.add(line.replace('\n', ' ').replace('\r', ' ').trim());
                    }
                }
                if (!clean.isEmpty()) return clean;
            }
        }
        return defaults;
    }

    private static Map<String, PlayerQuizPreset> defaultFamilyPresets() {
        Map<String, PlayerQuizPreset> m = new LinkedHashMap<>();
        m.put("wildpetal", new PlayerQuizPreset(5, 9, "multiplication"));
        m.put("treasurehunterm", new PlayerQuizPreset(0, 3, "addition"));
        m.put("pumajockey", new PlayerQuizPreset(0, 4, "exponentiation"));
        return m;
    }

    /**
     * Resolves min/max/operation for a player name. Presets use lowercase keys; {@code playerName}
     * is matched case-insensitively. Null or blank {@code playerName} uses only global defaults.
     */
    public EffectiveQuizParams resolveForPlayer(String playerName) {
        String op = (operation != null && !operation.isBlank()) ? operation : "multiplication";
        int min = minNumber;
        int max = maxNumber;
        int count = problemsPerQuiz;
        if (playerName != null && !playerName.isBlank() && playerPresets != null) {
            PlayerQuizPreset preset = playerPresets.get(playerName.toLowerCase(Locale.ROOT));
            if (preset != null) {
                if (preset.minNumber != null) min = preset.minNumber;
                if (preset.maxNumber != null) max = preset.maxNumber;
                if (preset.operation != null && !preset.operation.isBlank()) op = preset.operation;
                if (preset.problemsPerQuiz != null) count = Math.max(1, Math.min(50, preset.problemsPerQuiz));
            }
        }
        if (min > max) {
            int t = min;
            min = max;
            max = t;
        }
        return new EffectiveQuizParams(min, max, normalizeOperation(op), count);
    }

    /** Returns one of {@code all}, {@code random}, or {@code one}. */
    public static String normalizeNpcSpawnTargetMode(String raw) {
        if (raw == null || raw.isBlank()) return "all";
        String s = raw.trim().toLowerCase(Locale.ROOT);
        return switch (s) {
            case "all", "everyone", "each" -> "all";
            case "random", "any" -> "random";
            case "one", "single", "only" -> "one";
            default -> "all";
        };
    }

    /** Accepts common aliases; returns one of addition, subtraction, multiplication, division, exponentiation. */
    public static String normalizeOperation(String raw) {
        if (raw == null || raw.isBlank()) return "multiplication";
        String s = raw.trim().toLowerCase(Locale.ROOT);
        return switch (s) {
            case "add", "addition", "+" -> "addition";
            case "sub", "subtract", "subtraction", "minus", "-" -> "subtraction";
            case "mul", "multiply", "multiplication", "times", "x" -> "multiplication";
            case "div", "divide", "division", "/" -> "division";
            case "exp", "pow", "power", "exponent", "exponentiation", "^" -> "exponentiation";
            default -> "multiplication";
        };
    }
    public static String normalizeMathQuizSingleDbDir(String configured) {
        if (configured == null || configured.isBlank()) return defaultMathQuizSingleDbDir();
        if (configured.trim().equals(LEGACY_MATH_QUIZ_EXPORT_DIR)) return defaultMathQuizSingleDbDir();
        if (configured.trim().equals("~/Documents/Code/fof-mono/apps/math-quiz/_data/_single-session-sqlite-files")) {
            return defaultMathQuizSingleDbDir();
        }
        return configured;
    }

    public static String normalizeMathQuizActiveDbDir(String configured) {
        if (configured == null || configured.isBlank()) return defaultMathQuizActiveDbDir();
        String trimmed = configured.trim();
        if (trimmed.equals("~/Documents/Code/fof-mono/apps/math-quiz/_data/tlkids")) {
            return defaultMathQuizActiveDbDir();
        }
        String normalizedSeparators = trimmed.replace('\\', '/');
        if (normalizedSeparators.endsWith(LEGACY_DASHED_TLKIDS_SUFFIX)) {
            String migrated = trimmed.substring(0, trimmed.length() - "tl-kids".length()) + "tlkids";
            if (migrated.equals("~/Documents/Code/fof-mono/apps/math-quiz/_data/tlkids")) {
                return defaultMathQuizActiveDbDir();
            }
            return migrated;
        }
        return configured;
    }

    @Deprecated
    public static String normalizeMathQuizExportDir(String configured) {
        return normalizeMathQuizSingleDbDir(configured);
    }

    @Deprecated
    public static String normalizeMathQuizActiveDir(String configured) {
        return normalizeMathQuizActiveDbDir(configured);
    }
    public static String normalizeQuizType(String raw) {
        if (raw == null || raw.isBlank()) return "standard_arithmetic";
        String s = raw.trim().toLowerCase(Locale.ROOT).replace('-', '_');
        return switch (s) {
            case "written", "paper", "paper_column", "column", "column_arithmetic", "written_column", "written_column_arithmetic" -> "written_column_arithmetic";
            default -> "standard_arithmetic";
        };
    }
    public static String normalizeInternalQuizSource(String raw) {
        if (raw == null || raw.isBlank()) return "internal_quick_quiz";
        String s = raw.trim().toLowerCase(Locale.ROOT).replace('-', '_').replace(' ', '_');
        return switch (s) {
            case "generated", "settings", "normal", "standard" -> "generated";
            case "internal", "problem_list", "internal_problem_list" -> "internal_problem_list";
            case "quick", "quick_quiz", "internal_quick", "internal_quick_quiz" -> "internal_quick_quiz";
            case "feast", "fluency_feast", "internal_feast", "internal_fluency", "internal_fluency_feast" -> "internal_fluency_feast";
            default -> "internal_quick_quiz";
        };
    }
    public static String normalizeItemId(String raw) {
        if (raw == null || raw.isBlank()) return "minecraft:diamond";
        String s = raw.trim().toLowerCase(Locale.ROOT).replace('-', '_').replace(' ', '_');
        return s.contains(":") ? s : "minecraft:" + s;
    }
    public static Path resolveOptionalPath(String configured) {
        if (configured == null || configured.isBlank()) return null;
        String path = configured.trim();
        if (path.startsWith("~")) {
            String home = System.getProperty("user.home");
            if (home != null && !home.isEmpty()) {
                path = home + path.substring(1);
            }
        }
        return Path.of(path).normalize();
    }
    public Path resolveControlPanelAssetsDir() {
        Path p = resolveOptionalPath(controlPanelAssetsDir);
        return p != null && Files.isDirectory(p) ? p : null;
    }

    /**
     * Returns the directory where MathQuest should write the SQLite DB and session JSON files.
     * If {@link #sharedDataDir} is set, that path is used (with leading {@code ~} expanded).
     * Otherwise falls back to the Fabric config dir. Never returns null.
     */
    public Path resolveDataDir() {
        Path p = resolveConfiguredDir(sharedDataDir, "sharedDataDir");
        if (p != null) {
            return p;
        }
        return MathQuestPaths.configDir();
    }
    /**
     * Returns the directory where canonical single-session SQLite files are written.
     * Falls back to {@link #resolveDataDir()}/mathquest_sessions if the configured
     * math-quiz export folder is not writable.
     */
    public Path resolveMathQuizSingleDbDir() {
        Path p = resolveConfiguredDir(mathQuizSingleDbDir, "mathQuizSingleDbDir");
        if (p != null) {
            return p;
        }
        Path fallback = resolveDataDir().resolve("mathquest_sessions");
        try {
            Files.createDirectories(fallback);
        } catch (IOException e) {
            System.err.println("[MathQuest] fallback single DB dir " + fallback + " not writable: " + e.getMessage());
        }
        return fallback;
    }

    public Path resolveMathQuizActiveDbDir() {
        Path p = resolveConfiguredDir(mathQuizActiveDbDir, "mathQuizActiveDbDir");
        if (p != null) {
            return p;
        }
        Path fallback = resolveDataDir().resolve("mathquiz_active");
        try {
            Files.createDirectories(fallback);
        } catch (IOException e) {
            System.err.println("[MathQuest] fallback active DB dir " + fallback + " not writable: " + e.getMessage());
        }
        return fallback;
    }

    @Deprecated
    public Path resolveMathQuizExportDir() {
        return resolveMathQuizSingleDbDir();
    }

    @Deprecated
    public Path resolveMathQuizActiveDir() {
        return resolveMathQuizActiveDbDir();
    }
    private static Path resolveConfiguredDir(String configured, String label) {
        if (configured == null || configured.isBlank()) {
            return null;
        }
        String path = configured.trim();
        if (path.startsWith("~")) {
            String home = System.getProperty("user.home");
            if (home != null && !home.isEmpty()) {
                path = home + path.substring(1);
            }
        }
        Path p = Path.of(path);
        try {
            Files.createDirectories(p);
            return p;
        } catch (IOException e) {
            System.err.println("[MathQuest] " + label + " " + p + " not writable: " + e.getMessage()
                + " — falling back.");
            return null;
        }
    }

    /** Clears cached config path state between unit tests. */
    public static void resetConfigFileStateForTests() {
        loadedConfigFile = null;
        INSTANCE = null;
    }

    /** Path of the config file last loaded or saved; falls back to the loader config dir. */
    public static Path loadedConfigFile() {
        if (loadedConfigFile != null) return loadedConfigFile;
        return MathQuestPaths.configDir().resolve(CONFIG_FILE);
    }

    /**
     * When the instance config sets {@link #sharedDataDir} and that directory contains
     * {@code mathquest.json}, load from the shared file so Forge SP matches the dedicated server.
     */
    static Path resolveConfigFileToLoad() {
        Path localFile = MathQuestPaths.configDir().resolve(CONFIG_FILE);
        if (!Files.isRegularFile(localFile)) {
            return localFile;
        }
        try {
            JsonObject raw = JsonParser.parseString(Files.readString(localFile)).getAsJsonObject();
            if (raw.has("sharedDataDir") && !raw.get("sharedDataDir").isJsonNull()) {
                String sharedRaw = raw.get("sharedDataDir").getAsString();
                if (sharedRaw != null && !sharedRaw.isBlank()) {
                    Path sharedDir = resolveOptionalPath(sharedRaw);
                    if (sharedDir != null) {
                        Path sharedFile = sharedDir.resolve(CONFIG_FILE);
                        if (Files.isRegularFile(sharedFile)) {
                            return sharedFile;
                        }
                    }
                }
            }
        } catch (Exception e) {
            System.err.println("[MathQuest] Could not resolve sharedDataDir config: " + e.getMessage());
        }
        return localFile;
    }

    public static MathQuestConfig load() {
        Path configFile = resolveConfigFileToLoad();
        loadedConfigFile = configFile;

        if (Files.exists(configFile)) {
            try {
                String json = Files.readString(configFile);
                JsonObject raw = JsonParser.parseString(json).getAsJsonObject();
                MathQuestConfig config = GSON.fromJson(json, MathQuestConfig.class);
                migrateLegacyMathQuizDbDirKeys(config, raw);
                if (config != null) {
                    // Gson defaults missing booleans to false; this fix should stay on unless opted out.
                    if (!raw.has("excludeMultipartFromClientProjectileHits")) {
                        config.excludeMultipartFromClientProjectileHits = true;
                    }
                    if (config.playerPresets == null) {
                        config.playerPresets = new LinkedHashMap<>();
                    }
                    if (config.operation == null || config.operation.isBlank()) {
                        config.operation = "multiplication";
                    }
                    config.npcSpawnTargetMode = normalizeNpcSpawnTargetMode(config.npcSpawnTargetMode);
                    if (config.rewardGroups == null) {
                        config.rewardGroups = new LinkedHashMap<>();
                    }
                    if (config.playerRewardGroups == null) {
                        config.playerRewardGroups = new LinkedHashMap<>();
                    }
                    if (config.playerFluencyRewardGroups == null) {
                        config.playerFluencyRewardGroups = new LinkedHashMap<>();
                    }
                    migrateLegacyRewardBundles(config, json);
                    if (config.rewardGroups == null || config.rewardGroups.isEmpty()) {
                        config.rewardGroups = defaultRewardGroups();
                    }
                    if (config.playerRealNames == null) {
                        config.playerRealNames = defaultPlayerRealNames();
                    } else {
                        ensurePlayerRealNames(config.playerRealNames);
                    }
                    if (config.playerRewards == null) {
                        config.playerRewards = defaultPlayerRewards();
                    }
                    if (config.playerFluencyRewards == null) {
                        config.playerFluencyRewards = defaultPlayerFluencyRewards();
                    } else {
                        ensurePlayerFluencyRewards(config.playerFluencyRewards);
                    }
                    if (config.mathQuizNodeExecutable == null || config.mathQuizNodeExecutable.isBlank()) {
                        config.mathQuizNodeExecutable = "node";
                    }
                    if (config.playerQuizTypes == null) {
                        config.playerQuizTypes = defaultPlayerQuizTypes();
                    } else {
                        for (Map.Entry<String, String> e : defaultPlayerQuizTypes().entrySet()) {
                            config.playerQuizTypes.putIfAbsent(e.getKey(), e.getValue());
                        }
                        config.playerQuizTypes.replaceAll((key, value) -> normalizeQuizType(value));
                    }
                    if (config.playerInternalQuizSources == null) {
                        config.playerInternalQuizSources = defaultPlayerInternalQuizSources();
                    } else {
                        for (Map.Entry<String, String> e : defaultPlayerInternalQuizSources().entrySet()) {
                            config.playerInternalQuizSources.putIfAbsent(e.getKey(), e.getValue());
                        }
                        config.playerInternalQuizSources.replaceAll((key, value) -> normalizeInternalQuizSource(value));
                    }
                    if (config.playerUseInternalProblemLists == null) {
                        config.playerUseInternalProblemLists = defaultPlayerUseInternalProblemLists();
                    } else {
                        for (Map.Entry<String, Boolean> e : defaultPlayerUseInternalProblemLists().entrySet()) {
                            config.playerUseInternalProblemLists.putIfAbsent(e.getKey(), e.getValue());
                        }
                    }
                    if (config.playerNpcSelections == null) {
                        config.playerNpcSelections = defaultPlayerNpcSelections();
                    } else {
                        for (Map.Entry<String, String> e : defaultPlayerNpcSelections().entrySet()) {
                            config.playerNpcSelections.putIfAbsent(e.getKey(), e.getValue());
                        }
                    }
                    if (config.playerNpcLocks == null) {
                        config.playerNpcLocks = defaultPlayerNpcLocks();
                    } else {
                        for (Map.Entry<String, Boolean> e : defaultPlayerNpcLocks().entrySet()) {
                            config.playerNpcLocks.putIfAbsent(e.getKey(), e.getValue());
                        }
                    }
                    if (config.playerTpCreditEarningEnabled == null) {
                        config.playerTpCreditEarningEnabled = new LinkedHashMap<>();
                    }
                    if (config.playerTpCreditsPerQuiz == null) {
                        config.playerTpCreditsPerQuiz = new LinkedHashMap<>();
                    } else {
                        config.playerTpCreditsPerQuiz.replaceAll(
                            (key, value) -> clampTpCreditsPerQuiz(value == null ? 1 : value)
                        );
                    }
                    if (config.playerTpCreditBalances == null) {
                        config.playerTpCreditBalances = new LinkedHashMap<>();
                    } else {
                        config.playerTpCreditBalances.replaceAll(
                            (key, value) -> Math.max(0, value == null ? 0 : value)
                        );
                    }
                    if (config.playerTpCreditRewardChoices == null) {
                        config.playerTpCreditRewardChoices = new LinkedHashMap<>();
                    } else {
                        config.playerTpCreditRewardChoices.replaceAll(
                            (key, value) -> normalizeTpCreditRewardChoice(value)
                        );
                    }
                    if (config.npcDialogueOverrides == null) {
                        config.npcDialogueOverrides = new LinkedHashMap<>();
                    }
                    if (config.writtenColumnEvaluatorCode == null || config.writtenColumnEvaluatorCode.isBlank()) {
                        config.writtenColumnEvaluatorCode = "paper";
                    }
                    ensurePlayerRewards(config.playerRewards);
                    ensurePlayerFluencyRewards(config.playerFluencyRewards);
                    if (config.controlPanelHost == null || config.controlPanelHost.isBlank()) {
                        config.controlPanelHost = "127.0.0.1";
                    }
                    if (config.controlPanelPort <= 0) {
                        config.controlPanelPort = 8765;
                    }
                    ensureJtreeGroup(config.rewardGroups);
                    // Upgrade legacy shipped default 2–9 to 0–9 for players without a preset
                    if (config.minNumber == 2 && config.maxNumber == 9) {
                        config.minNumber = 0;
                    }
                    // Migration: pre-1.4 configs are missing sharedDataDir. Fill it in with the
                    // default so singleplayer DB and session writes go to the shared server dir.
                    if (config.sharedDataDir == null) {
                        config.sharedDataDir = DEFAULT_SHARED_DATA_DIR;
                        try {
                            config.save();
                        } catch (Exception ignored) {}
                    }
                    String singleDbDir = normalizeMathQuizSingleDbDir(config.mathQuizSingleDbDir);
                    if (!singleDbDir.equals(config.mathQuizSingleDbDir)) {
                        config.mathQuizSingleDbDir = singleDbDir;
                        try {
                            config.save();
                        } catch (Exception ignored) {}
                    }
                    String activeDbDir = normalizeMathQuizActiveDbDir(config.mathQuizActiveDbDir);
                    if (!activeDbDir.equals(config.mathQuizActiveDbDir)) {
                        config.mathQuizActiveDbDir = activeDbDir;
                        try {
                            config.save();
                        } catch (Exception ignored) {}
                    }
                    if (config.mathQuizIngestPython == null || config.mathQuizIngestPython.isBlank()) {
                        config.mathQuizIngestPython = "python3";
                    }
                    return activated(config);
                }
            } catch (IOException e) {
                System.err.println("[MathQuest] Failed to load config: " + e.getMessage());
            }
        }

        MathQuestConfig config = new MathQuestConfig();
        if (config.rewardGroups == null || config.rewardGroups.isEmpty()) {
            config.rewardGroups = defaultRewardGroups();
        }
        config.save();
        return activated(config);
    }

    private static MathQuestConfig activated(MathQuestConfig config) {
        INSTANCE = config;
        return config;
    }

    private static void migrateLegacyMathQuizDbDirKeys(MathQuestConfig config, JsonObject raw) {
        if (!raw.has("mathQuizSingleDbDir") && raw.has("mathQuizExportDir")) {
            config.mathQuizSingleDbDir = raw.get("mathQuizExportDir").getAsString();
        }
        if (!raw.has("mathQuizActiveDbDir") && raw.has("mathQuizActiveDir")) {
            config.mathQuizActiveDbDir = raw.get("mathQuizActiveDir").getAsString();
        }
    }

    private static void migrateLegacyRewardBundles(MathQuestConfig config, String json) {
        try {
            JsonObject root = JsonParser.parseString(json).getAsJsonObject();
            if (root.has("rewardGroups")) return;
            boolean migrated = false;
            if (root.has("rewardBundles") && root.get("rewardBundles").isJsonObject()) {
                JsonObject bundles = root.getAsJsonObject("rewardBundles");
                Map<String, RewardGroup> groups = new LinkedHashMap<>();
                for (String key : bundles.keySet()) {
                    JsonElement el = bundles.get(key);
                    if (!el.isJsonArray()) continue;
                    List<RewardEntry> entries = parseRewardEntryArray(el.getAsJsonArray());
                    if (!entries.isEmpty()) {
                        groups.put(normalizeGroupName(key), new RewardGroup("random", entries));
                    }
                }
                if (!groups.isEmpty()) {
                    config.rewardGroups = groups;
                    migrated = true;
                }
            }
            if (root.has("rewardBundle") && !root.get("rewardBundle").isJsonNull()) {
                String legacy = root.get("rewardBundle").getAsString();
                if (legacy != null && !legacy.isBlank()) {
                    config.rewardGroup = normalizeGroupName(legacy);
                    migrated = true;
                }
            }
            if (migrated) {
                config.save();
            }
        } catch (Exception e) {
            System.err.println("[MathQuest] Failed to migrate legacy reward bundles: " + e.getMessage());
        }
    }

    private static List<RewardEntry> parseRewardEntryArray(JsonArray arr) {
        List<RewardEntry> out = new ArrayList<>();
        for (JsonElement el : arr) {
            if (!el.isJsonObject()) continue;
            JsonObject obj = el.getAsJsonObject();
            if (!obj.has("item") || !obj.has("count")) continue;
            String item = normalizeItemId(obj.get("item").getAsString());
            int count = Math.max(1, obj.get("count").getAsInt());
            out.add(new RewardEntry(item, count));
        }
        return out;
    }

    public void save() {
        saveChecked();
    }

    /** Saves the config and reports whether the write reached disk successfully. */
    public boolean saveChecked() {
        Path configFile = loadedConfigFile();
        Path tempFile = null;
        try {
            Files.createDirectories(configFile.getParent());
            tempFile = Files.createTempFile(configFile.getParent(), CONFIG_FILE + ".", ".tmp");
            Files.writeString(tempFile, GSON.toJson(this));
            try {
                Files.move(
                    tempFile,
                    configFile,
                    StandardCopyOption.ATOMIC_MOVE,
                    StandardCopyOption.REPLACE_EXISTING
                );
            } catch (AtomicMoveNotSupportedException e) {
                Files.move(tempFile, configFile, StandardCopyOption.REPLACE_EXISTING);
            }
            return true;
        } catch (Exception e) {
            System.err.println("[MathQuest] Failed to save config: " + e.getMessage());
            return false;
        } finally {
            if (tempFile != null) {
                try {
                    Files.deleteIfExists(tempFile);
                } catch (IOException ignored) {}
            }
        }
    }
}
