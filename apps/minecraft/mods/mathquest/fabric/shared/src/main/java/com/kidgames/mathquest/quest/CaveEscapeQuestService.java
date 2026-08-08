package com.kidgames.mathquest.quest;

import com.google.gson.JsonNull;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.mojang.brigadier.ParseResults;
import com.mojang.brigadier.suggestion.Suggestion;
import com.mojang.brigadier.suggestion.Suggestions;
import com.mojang.serialization.DataResult;
import com.mojang.serialization.JsonOps;
import com.kidgames.mathquest.MathQuestMod;
import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.network.OpenQuizPayload;
import com.kidgames.mathquest.network.QuizPayloadBuilder;
import com.kidgames.mathquest.network.QuestInvitationPayload;
import com.kidgames.mathquest.quiz.QuizManager;
import com.kidgames.mathquest.quiz.QuizSessionOptions;
import net.fabricmc.fabric.api.networking.v1.ServerPlayNetworking;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntitySpawnReason;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.gamerules.GameRules;
import net.minecraft.world.phys.AABB;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.Statement;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.Random;
import java.util.Set;
import java.util.concurrent.TimeUnit;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** File-backed Quest 01 state, problem generation, and progress tracking. */
public final class CaveEscapeQuestService {
    public static final String QUEST_ID = "quest1-caveescape";
    public static final String DISPLAY_NAME = "Cave Escape";
    public static final String DEFAULT_PLAYER_NAME = "WildPetal";
    public static final String DEFAULT_REAL_NAME = "Kid1";
    public static final String QUEST_INVITATION_CHAT =
        "In the well of darkness, you have been offered an invitation of knowledge. Do you accept?";
    public static final String QUEST_INVITATION_TITLE =
        "To leave this well, practice and master the deepest numbers: zero and one.";
    public static final int QUEST_INVITATION_RETRY_SECONDS = 22;
    private static final String M2_INVITATION_CHAT =
        "Three stones have fallen. You can earn building blocks by learning the next building-block addition problems. Do you accept?";
    private static final String M2_INVITATION_TITLE =
        "Fast answers become the blocks beneath your feet.";
    private static final String M2_REWARD_ITEM_ID = "minecraft:deepslate";
    private static final int M2_TRIGGER_BLOCK_BREAKS = 3;
    private static final int M1_AMBIENCE_INTERVAL_TICKS = 18 * 20;

    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();
    private static final Random RANDOM = new Random();
    private static final DateTimeFormatter VERSION_STAMP = DateTimeFormatter.ofPattern("yyyy-MM-dd_HHmmss");
    private static final Pattern TRY_PATTERN = Pattern.compile("^quest1_try(\\d+)_([^_]+)_\\d{4}-\\d{2}-\\d{2}\\.sqlite$");
    private static final List<ScheduledQuestAction> SCHEDULED_ACTIONS = new ArrayList<>();
    private static final int MAX_ACTION_LOG_ENTRIES = 120;
    private static long schedulerTick = 0;
    private static long nextM1AmbienceTick = 0;

    private static final List<Fact> ADD_ZERO = facts(0, 0, 9);
    private static final List<Fact> ADD_ONE = facts(1, 1, 9);
    private static final List<Fact> ADD_TWO = facts(2, 2, 9);
    private static final List<Fact> DOUBLES = doubles(3, 9);
    private static final List<Fact> TOUGH_21 = facts(
        "3+4", "3+5", "3+6", "3+7", "3+8", "3+9",
        "4+5", "4+6", "4+7", "4+8", "4+9",
        "5+6", "5+7", "5+8", "5+9",
        "6+7", "6+8", "6+9",
        "7+8", "7+9",
        "8+9"
    );
    private static final List<Fact> HARDEST_SIX = facts("6+7", "6+8", "6+9", "7+8", "7+9", "8+9");

    private record ScheduledQuestAction(long runAtTick, String playerName, String milestoneId, String line) {}

    private CaveEscapeQuestService() {}

    public static synchronized Map<String, Object> status(MinecraftServer server) {
        JsonObject quest = readQuest();
        JsonObject world = readWorld(server);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("ok", true);
        out.put("quest", jsonToObject(quest));
        out.put("world", jsonToObject(world));
        out.put("paths", pathsJson());
        out.put("versions", savedVersions());
        out.put("progress", progress(quest));
        out.put("onlinePlayers", onlinePlayers(server));
        out.put("playerRealNames", MathQuestMod.CONFIG.resolvePlayerRealNames());
        out.put("commandSuggestions", defaultCommandSuggestions(quest));
        out.put("latestBackup", latestBackupJson(quest));
        out.put("nextTryNumber", nextTryNumber(learnerRealName(quest)));
        out.put("server", serverJson(server));
        return out;
    }

    public static synchronized Map<String, Object> start(JsonObject body, MinecraftServer server) {
        JsonObject quest = readQuest();
        ensureQuestShape(quest);
        JsonObject learner = quest.getAsJsonObject("learner");
        String playerName = cleanName(stringOr(body, "playerName", stringOr(learner, "playerName", DEFAULT_PLAYER_NAME)));
        String realName = resolveLearnerRealName(playerName, stringOr(body, "realName", ""));
        int tryNumber = body.has("tryNumber") ? Math.max(1, body.get("tryNumber").getAsInt()) : nextTryNumber(realName);
        learner.addProperty("playerName", playerName);
        learner.addProperty("realName", realName);
        quest.addProperty("enabled", true);
        quest.addProperty("active", true);
        quest.addProperty("tryNumber", tryNumber);
        quest.addProperty("activeSqlitePath", activeSqlitePath(realName, tryNumber).toString());
        quest.addProperty("startedAt", java.time.OffsetDateTime.now().toString());
        quest.remove("m2");
        resetMilestones(quest, false);
        questPath().getParent().toFile().mkdirs();
        JsonObject world = readWorld(server);
        List<Map<String, Object>> actions = runSetupForMilestone(quest, world, server, "m1_cave_start", "start");
        ServerLevel overworld = server == null ? null : server.overworld();
        if (overworld != null && MathQuestMod.getNerdSpawner() != null) {
            int removed = MathQuestMod.getNerdSpawner().removeAssignedNerds(overworld, playerName);
            if (removed > 0) {
                actions.add(actionResult("remove_assigned_nerds", playerName, true, "removed=" + removed));
            }
        }
        quest.add("lastActionResult", GSON.toJsonTree(actions));
        recordActionResults(quest, "start-run", actions);
        saveQuest(quest);
        Map<String, Object> response = new LinkedHashMap<>(status(server));
        response.put("actionResult", actions);
        return response;
    }

    public static synchronized Map<String, Object> save(JsonObject body, MinecraftServer server) {
        if (body.has("quest") && body.get("quest").isJsonObject()) {
            JsonObject quest = body.getAsJsonObject("quest");
            ensureQuestShape(quest);
            normalizeLearner(quest, false);
            saveQuest(quest);
        }
        if (body.has("world") && body.get("world").isJsonObject()) {
            JsonObject world = body.getAsJsonObject("world");
            ensureWorldShape(world, server);
            saveWorld(world);
        }
        return status(server);
    }

    public static synchronized Map<String, Object> action(JsonObject body, MinecraftServer server) {
        String action = stringOr(body, "action", "");
        JsonObject quest = readQuest();
        ensureQuestShape(quest);
        switch (action) {
            case "reset" -> {
                quest.addProperty("active", false);
                quest.addProperty("activeSqlitePath", "");
                quest.remove("m2");
                resetMilestones(quest, false);
                Map<String, Object> result = actionResult("reset", "reset", true, "run reset");
                quest.add("lastActionResult", GSON.toJsonTree(List.of(result)));
                recordActionResult(quest, "reset", result);
                saveQuest(quest);
            }
            case "clear-log" -> {
                quest.add("actionLog", new JsonArray());
                quest.add("lastActionResult", new JsonArray());
                saveQuest(quest);
            }
            case "continue-run" -> {
                JsonObject world = readWorld(server);
                String milestoneId = canonicalMilestoneId(stringOr(body, "milestoneId", currentMilestoneId(quest)));
                List<Map<String, Object>> actions = runSetupForMilestone(quest, world, server, milestoneId, "start");
                quest.add("lastActionResult", GSON.toJsonTree(actions));
                recordActionResults(quest, "continue-run", actions);
                saveQuest(quest);
                Map<String, Object> response = new LinkedHashMap<>(status(server));
                response.put("actionResult", actions);
                return response;
            }
            case "advance-milestone" -> {
                int index = currentMilestoneIndex(quest);
                setMilestoneStatus(quest, index, "completed");
                setMilestoneStatus(quest, Math.min(index + 1, quest.getAsJsonArray("milestones").size() - 1), "active");
                saveQuest(quest);
            }
            case "save-version" -> {
                JsonObject world = readWorld(server);
                Path versionPath = saveSetupVersion(quest, world, stringOr(body, "label", ""));
                Map<String, Object> response = new LinkedHashMap<>(status(server));
                response.put("versionPath", versionPath.toString());
                return response;
            }
            case "run-command" -> {
                String command = stringOr(body, "command", "");
                JsonObject world = readWorld(server);
                JsonArray lines = linesArray(command);
                List<Map<String, Object>> results = runActionLines(lines, quest, world, server, currentMilestoneId(quest));
                quest.add("lastActionResult", GSON.toJsonTree(results));
                recordActionResults(quest, "command", results);
                saveQuest(quest);
                Map<String, Object> response = new LinkedHashMap<>(status(server));
                response.put("commandResult", results.isEmpty() ? actionResult("command", command, false, "blank-command") : results.get(results.size() - 1));
                response.put("commandResults", results);
                return response;
            }
            case "restore-player" -> {
                Map<String, Object> result = restorePlayerBackup(quest, server);
                quest.add("lastActionResult", GSON.toJsonTree(List.of(result)));
                recordActionResult(quest, "restore-player", result);
                saveQuest(quest);
                Map<String, Object> response = new LinkedHashMap<>(status(server));
                response.put("restoreResult", result);
                return response;
            }
            case "run-milestone-actions" -> {
                JsonObject world = readWorld(server);
                String milestoneId = canonicalMilestoneId(stringOr(body, "milestoneId", currentMilestoneId(quest)));
                String phase = stringOr(body, "phase", "start");
                List<Map<String, Object>> actions = runSetupForMilestone(quest, world, server, milestoneId, phase);
                quest.add("lastActionResult", GSON.toJsonTree(actions));
                recordActionResults(quest, "milestone-" + phase, actions);
                saveQuest(quest);
                Map<String, Object> response = new LinkedHashMap<>(status(server));
                response.put("actionResult", actions);
                return response;
            }
            case "set-current-milestone" -> {
                String id = canonicalMilestoneId(stringOr(body, "milestoneId", "m1_cave_start"));
                JsonArray milestones = quest.getAsJsonArray("milestones");
                boolean before = true;
                for (JsonElement el : milestones) {
                    JsonObject m = el.getAsJsonObject();
                    if (id.equals(stringOr(m, "id", ""))) {
                        m.addProperty("status", "active");
                        before = false;
                    } else {
                        m.addProperty("status", before ? "completed" : "locked");
                    }
                }
                saveQuest(quest);
            }
            case "force-complete-mechanic", "force-respawn-mechanic", "open-mechanic-quiz" -> {
                String mechanicId = stringOr(body, "mechanicId", "");
                JsonObject mechanic = mechanicById(quest, mechanicId);
                int affected = 0;
                if (mechanic != null) {
                    if ("force-complete-mechanic".equals(action)) {
                        affected = clearMechanic(mechanic, server);
                    } else if ("force-respawn-mechanic".equals(action)) {
                        affected = respawnMechanic(mechanic, server);
                    } else if ("open-mechanic-quiz".equals(action)) {
                        affected = openQuestQuizForLearner(quest, server) ? 1 : 0;
                    }
                }
                Map<String, Object> result = actionResult(action, mechanicId, affected > 0, "affected=" + affected);
                updateMechanicStatus(quest, mechanicId, action);
                quest.add("lastActionResult", GSON.toJsonTree(List.of(result)));
                recordActionResult(quest, action, result);
                saveQuest(quest);
                Map<String, Object> response = new LinkedHashMap<>(status(server));
                response.put("mechanicAffected", affected);
                return response;
            }
            default -> {
                if (action.isBlank()) {
                    return Map.of("ok", false, "error", "missing-action", "status", status(server));
                }
                return Map.of("ok", false, "error", "unknown-action", "action", action, "status", status(server));
            }
        }
        return status(server);
    }

    public static synchronized Map<String, Object> commandSuggestions(JsonObject body, MinecraftServer server) {
        String raw = stringOr(body, "command", "");
        String command = raw == null ? "" : raw.trim();
        while (command.startsWith("/")) command = command.substring(1).trim();
        List<String> values = new ArrayList<>();
        if (server != null) {
            try {
                CommandSourceStack source = server.createCommandSourceStack();
                ParseResults<CommandSourceStack> parsed = server.getCommands().getDispatcher().parse(command, source);
                Suggestions suggestions = server.getCommands().getDispatcher()
                    .getCompletionSuggestions(parsed, command.length())
                    .get(1, TimeUnit.SECONDS);
                for (Suggestion suggestion : suggestions.getList()) {
                    values.add(suggestion.apply(command));
                    if (values.size() >= 30) break;
                }
            } catch (Exception e) {
                return Map.of("ok", false, "error", e.getMessage(), "suggestions", values);
            }
        }
        return Map.of("ok", true, "suggestions", values);
    }

    public static synchronized void handleInvitationResponse(ServerPlayer player, boolean accepted) {
        if (player == null || player.level() == null) return;
        MinecraftServer server = player.level().getServer();
        if (server == null) return;
        JsonObject quest = readQuestIfExists().orElse(null);
        if (quest == null) return;
        ensureQuestShape(quest);
        if (!boolOr(quest, "active", false)) return;
        if (!learnerPlayerName(quest).equalsIgnoreCase(player.getName().getString())) return;
        if (accepted) {
            cancelPendingScheduledActionsFor(player.getName().getString());
            Map<String, Object> result = actionResult(
                "quest_invitation_accept",
                player.getName().getString(),
                true,
                "client accepted; client opens embedded quiz payload"
            );
            quest.add("lastActionResult", GSON.toJsonTree(List.of(result)));
            recordActionResult(quest, "quest-invitation", result);
            saveQuest(quest);
            return;
        }
        if (!"m1_cave_start".equals(currentMilestoneId(quest))) {
            Map<String, Object> result = actionResult(
                "quest_invitation_decline",
                player.getName().getString(),
                true,
                "declined; no automatic retry for " + currentMilestoneId(quest)
            );
            quest.add("lastActionResult", GSON.toJsonTree(List.of(result)));
            recordActionResult(quest, "quest-invitation-decline", result);
            saveQuest(quest);
            return;
        }
        JsonObject world = readWorld(server);
        List<Map<String, Object>> actions = scheduleInvitationRetry(quest, world, server, currentMilestoneId(quest));
        if (!actions.isEmpty()) {
            quest.add("lastActionResult", GSON.toJsonTree(actions));
            recordActionResults(quest, "quest-invitation-decline", actions);
            saveQuest(quest);
        }
    }

    public static synchronized void tick(MinecraftServer server) {
        schedulerTick++;
        if (schedulerTick % 20 == 0) {
            tickQuestRuntime(server);
        }
        if (SCHEDULED_ACTIONS.isEmpty()) return;
        JsonObject quest = readQuest();
        JsonObject world = readWorld(server);
        List<Map<String, Object>> ran = new ArrayList<>();
        SCHEDULED_ACTIONS.removeIf(action -> {
            if (action.runAtTick() > schedulerTick) return false;
            Map<String, Object> result = runActionLine(action.line(), quest, world, server, action.milestoneId());
            ran.add(result);
            return true;
        });
        if (!ran.isEmpty()) {
            quest.add("lastActionResult", GSON.toJsonTree(ran));
            recordActionResults(quest, "scheduled", ran);
            saveQuest(quest);
        }
    }

    private static void tickQuestRuntime(MinecraftServer server) {
        JsonObject quest = readQuestIfExists().orElse(null);
        if (quest == null) return;
        ensureQuestShape(quest);
        if (!boolOr(quest, "active", false)) return;
        String milestoneId = currentMilestoneId(quest);
        if ("m1_cave_start".equals(milestoneId)) {
            playM1Ambience(server, quest);
        } else if ("m2_deep_passage".equals(milestoneId)) {
            maybePromptM2WhenInventoryEmpty(server, quest);
        }
    }

    private static void playM1Ambience(MinecraftServer server, JsonObject quest) {
        if (server == null || schedulerTick < nextM1AmbienceTick) return;
        ServerPlayer player = targetPlayer(quest, server);
        if (player == null) return;
        performSilentServerCommand(server, "playsound minecraft:ambient.cave ambient " + player.getName().getString());
        nextM1AmbienceTick = schedulerTick + M1_AMBIENCE_INTERVAL_TICKS;
    }

    private static void maybePromptM2WhenInventoryEmpty(MinecraftServer server, JsonObject quest) {
        JsonObject m2 = m2State(quest);
        if (!boolOr(m2, "awaitingInventoryEmpty", false)) return;
        ServerPlayer player = targetPlayer(quest, server);
        if (player == null || hasItem(player, M2_REWARD_ITEM_ID)) return;
        m2.addProperty("awaitingInventoryEmpty", false);
        m2.addProperty("lastInventoryEmptyPromptAt", OffsetDateTime.now().toString());
        boolean opened = openM2QuizInvitationForLearner(quest, server);
        Map<String, Object> result = actionResult(
            "m2_inventory_empty_prompt",
            M2_REWARD_ITEM_ID,
            opened,
            opened ? "opened" : "player-offline"
        );
        quest.add("lastActionResult", GSON.toJsonTree(List.of(result)));
        recordActionResult(quest, "m2-inventory-empty", result);
        saveQuest(quest);
    }

    public static synchronized void handleBlockBreak(ServerPlayer player, BlockPos pos) {
        if (player == null || player.level() == null) return;
        MinecraftServer server = player.level().getServer();
        if (server == null) return;
        JsonObject quest = readQuestIfExists().orElse(null);
        if (quest == null) return;
        ensureQuestShape(quest);
        if (!boolOr(quest, "active", false)) return;
        if (!"m2_deep_passage".equals(currentMilestoneId(quest))) return;
        if (!learnerPlayerName(quest).equalsIgnoreCase(player.getName().getString())) return;

        JsonObject m2 = m2State(quest);
        int broken = intOr(m2, "blocksBroken", 0) + 1;
        m2.addProperty("blocksBroken", broken);
        m2.addProperty("lastBlockBreakAt", OffsetDateTime.now().toString());
        List<Map<String, Object>> results = new ArrayList<>();
        results.add(actionResult("m2_block_break", player.getName().getString(), true, "count=" + broken));

        if (broken >= M2_TRIGGER_BLOCK_BREAKS && !boolOr(m2, "initialPromptOpened", false)) {
            performSilentServerCommand(server, "playsound minecraft:block.amethyst_block.chime master " + player.getName().getString());
            m2.addProperty("initialPromptOpened", true);
            boolean opened = openM2QuizInvitationForLearner(quest, server);
            results.add(actionResult("open_m2_quiz_invitation", "block-break-trigger", opened,
                opened ? "opened after third block" : "player-offline"));
        }

        quest.add("lastActionResult", GSON.toJsonTree(results));
        recordActionResults(quest, "m2-block-break", results);
        saveQuest(quest);
    }

    public static synchronized void handlePlayerRespawn(ServerPlayer oldPlayer, ServerPlayer newPlayer, boolean alive) {
        if (newPlayer == null || newPlayer.level().getServer() == null) return;
        MinecraftServer server = newPlayer.level().getServer();
        JsonObject quest = readQuestIfExists().orElse(null);
        if (quest == null) return;
        ensureQuestShape(quest);
        if (!boolOr(quest, "active", false)) return;
        if (!learnerPlayerName(quest).equalsIgnoreCase(newPlayer.getName().getString())) return;
        JsonObject world = readWorld(server);
        Map<String, Object> result = runTeleportAction("teleport " + currentMilestoneId(quest), quest, world, server, currentMilestoneId(quest));
        newPlayer.sendSystemMessage(Component.literal("Returned to the current Quest 01 milestone."));
        quest.add("lastActionResult", GSON.toJsonTree(List.of(result)));
        recordActionResult(quest, "respawn", result);
        saveQuest(quest);
    }

    public static synchronized void runPostQuizActions(String realName, MinecraftServer server) {
        runPostQuizActions(realName, null, List.of());
    }

    public static synchronized void runPostQuizActions(
        String realName,
        ServerPlayer player,
        List<QuizManager.Problem> completedProblems
    ) {
        MinecraftServer server = player == null || player.level() == null ? null : player.level().getServer();
        JsonObject quest = readQuestIfExists().orElse(null);
        if (quest == null) return;
        ensureQuestShape(quest);
        if (!boolOr(quest, "active", false)) return;
        if (!learnerRealName(quest).equalsIgnoreCase(realName)) return;
        String beforeMilestoneId = currentMilestoneId(quest);
        QuestProgress progress = computeProgress(quest);
        applyMilestoneProgress(quest, progress);
        JsonObject world = readWorld(server);
        List<Map<String, Object>> actions = new ArrayList<>();
        if ("m2_deep_passage".equals(beforeMilestoneId) && player != null) {
            boolean m2Complete = QuestQuizDefinitions.caveEscapeM2Complete(progress.orientedStats());
            actions.add(awardM2Blocks(quest, player, completedProblems, !m2Complete));
        }
        actions.addAll(runCompletedMilestoneEndActions(quest, world, server));
        if (!actions.isEmpty()) {
            quest.add("lastActionResult", GSON.toJsonTree(actions));
            recordActionResults(quest, "post-quiz", actions);
        }
        saveQuest(quest);
    }

    public static synchronized Optional<Path> activeSqliteForRealName(String realName) {
        if (realName == null || realName.isBlank()) return Optional.empty();
        JsonObject quest = readQuestIfExists().orElse(null);
        if (quest == null) return Optional.empty();
        ensureQuestShape(quest);
        if (!boolOr(quest, "enabled", true) || !boolOr(quest, "active", false)) return Optional.empty();
        JsonObject learner = quest.getAsJsonObject("learner");
        if (!realName.equalsIgnoreCase(learnerRealName(quest))) return Optional.empty();
        String path = stringOr(quest, "activeSqlitePath", "");
        if (path.isBlank()) return Optional.empty();
        return Optional.of(Path.of(path).normalize());
    }

    public static synchronized Map<String, Object> questStatusForPlayer(String playerName) {
        JsonObject quest = readQuestIfExists().orElse(null);
        if (quest == null) return Map.of("active", false);
        ensureQuestShape(quest);
        boolean active = boolOr(quest, "active", false);
        boolean learnerMatches = active && learnerPlayerName(quest).equalsIgnoreCase(cleanName(playerName));
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("active", learnerMatches);
        if (learnerMatches) {
            out.put("questId", QUEST_ID);
            out.put("displayName", DISPLAY_NAME);
            out.put("playerName", learnerPlayerName(quest));
            out.put("realName", learnerRealName(quest));
            out.put("tryNumber", intOr(quest, "tryNumber", 0));
            out.put("currentMilestoneId", currentMilestoneId(quest));
            out.put("currentMilestoneName", currentMilestoneName(quest));
            out.put("activeSqlitePath", stringOr(quest, "activeSqlitePath", ""));
        }
        return out;
    }

    public static synchronized boolean isActiveQuestLearner(String playerName) {
        if (playerName == null || playerName.isBlank()) return false;
        JsonObject quest = readQuestIfExists().orElse(null);
        if (quest == null) return false;
        ensureQuestShape(quest);
        return boolOr(quest, "enabled", true)
            && boolOr(quest, "active", false)
            && learnerPlayerName(quest).equalsIgnoreCase(cleanName(playerName));
    }

    public static synchronized Optional<List<QuizManager.Problem>> problemsForPlayer(
        String playerName,
        MathQuestConfig.EffectiveQuizParams params,
        Map<String, String> realNames
    ) {
        JsonObject quest = readQuestIfExists().orElse(null);
        if (quest == null) return Optional.empty();
        ensureQuestShape(quest);
        if (!boolOr(quest, "enabled", true) || !boolOr(quest, "active", false)) return Optional.empty();
        JsonObject learner = quest.getAsJsonObject("learner");
        String configuredPlayer = learnerPlayerName(quest);
        String configuredReal = learnerRealName(quest);
        String resolvedReal = resolveRealName(playerName, realNames);
        if (!configuredPlayer.equalsIgnoreCase(playerName) && !configuredReal.equalsIgnoreCase(resolvedReal)) {
            return Optional.empty();
        }
        QuestProgress progress = computeProgress(quest);
        int count = intAt(quest, "quiz", "problemsPerQuiz", Math.max(1, params.problemsPerQuiz()));
        return Optional.of(generateProblems(quest, progress, count));
    }

    public static synchronized Optional<OpenQuizPayload> quizPayloadForPlayer(ServerPlayer player, boolean directToQuiz) {
        if (player == null) return Optional.empty();
        JsonObject quest = readQuestIfExists().orElse(null);
        if (quest == null) return Optional.empty();
        ensureQuestShape(quest);
        if (!boolOr(quest, "enabled", true) || !boolOr(quest, "active", false)) return Optional.empty();
        String playerName = player.getName().getString();
        if (!learnerPlayerName(quest).equalsIgnoreCase(playerName)) return Optional.empty();

        QuestProgress progress = computeProgress(quest);
        int fallbackCount = intAt(quest, "quiz", "problemsPerQuiz", 7);
        List<QuizManager.Problem> problems = generateProblems(quest, progress, fallbackCount);
        if (problems.isEmpty()) return Optional.empty();
        String milestoneId = currentMilestoneId(quest);
        String optionsJson = questQuizOptionsJson(quest, milestoneId);
        return Optional.of(new OpenQuizPayload(
            "addition",
            minProblemFactor(problems),
            maxProblemFactor(problems),
            problems.size(),
            QuizPayloadBuilder.problemsJson(problems),
            "[]",
            "all",
            "standard_arithmetic",
            optionsJson,
            false,
            directToQuiz
        ));
    }

    public static synchronized void refreshAfterIngest(String realName, Path activeFile) {
        Optional<Path> questActive = activeSqliteForRealName(realName);
        if (questActive.isEmpty()) return;
        if (activeFile != null && !questActive.get().normalize().equals(activeFile.normalize())) return;
        JsonObject quest = readQuest();
        QuestProgress progress = computeProgress(quest);
        applyMilestoneProgress(quest, progress);
        saveQuest(quest);
    }

    private static List<QuizManager.Problem> generateProblems(JsonObject quest, QuestProgress progress, int count) {
        String milestoneId = currentMilestoneId(quest);
        if ("m1_cave_start".equals(milestoneId)) {
            List<QuestQuizDefinitions.ProblemSpec> remaining =
                QuestQuizDefinitions.caveEscapeM1RemainingProblems(progress.orientedStats());
            if (remaining.isEmpty()) {
                remaining = QuestQuizDefinitions.caveEscapeM1Problems();
            }
            return shuffledFixedProblems(remaining);
        }
        if ("m2_deep_passage".equals(milestoneId)) {
            List<QuestQuizDefinitions.ProblemSpec> remaining =
                QuestQuizDefinitions.caveEscapeM2RemainingProblems(progress.orientedStats());
            if (remaining.isEmpty()) {
                remaining = QuestQuizDefinitions.caveEscapeM2Problems();
            }
            return shuffledFixedProblems(m2BatchProblems(remaining, Math.max(1, count)));
        }
        List<Fact> pool = new ArrayList<>();
        pool.addAll(prioritized(TOUGH_21, progress));
        pool.addAll(prioritized(addAll(ADD_ZERO, ADD_ONE, ADD_TWO, DOUBLES), progress));
        if (pool.isEmpty()) {
            pool.addAll(addAll(ADD_ZERO, ADD_ONE));
        }
        List<Fact> prioritized = prioritized(pool, progress);
        List<QuizManager.Problem> out = new ArrayList<>();
        for (int i = 0; i < count; i++) {
            Fact fact = prioritized.get(i % prioritized.size()).randomOrientation();
            out.add(QuizManager.Problem.create("addition", fact.a, fact.b));
        }
        return out;
    }

    private static List<QuestQuizDefinitions.ProblemSpec> m2BatchProblems(
        List<QuestQuizDefinitions.ProblemSpec> remaining,
        int count
    ) {
        List<QuestQuizDefinitions.ProblemSpec> selected = new ArrayList<>();
        List<QuestQuizDefinitions.ProblemSpec> remainingPool = new ArrayList<>(remaining);
        Collections.shuffle(remainingPool, RANDOM);
        for (QuestQuizDefinitions.ProblemSpec problem : remainingPool) {
            if (selected.size() >= count) break;
            selected.add(problem);
        }
        if (selected.size() < count) {
            List<QuestQuizDefinitions.ProblemSpec> filler = new ArrayList<>(QuestQuizDefinitions.caveEscapeM2Problems());
            filler.removeAll(selected);
            Collections.shuffle(filler, RANDOM);
            for (QuestQuizDefinitions.ProblemSpec problem : filler) {
                if (selected.size() >= count) break;
                selected.add(problem);
            }
        }
        return selected;
    }

    private static List<QuizManager.Problem> shuffledFixedProblems(List<QuestQuizDefinitions.ProblemSpec> specs) {
        List<QuizManager.Problem> out = new ArrayList<>();
        for (QuestQuizDefinitions.ProblemSpec problem : specs) {
            out.add(QuizManager.Problem.create(problem.operation(), problem.factorA(), problem.factorB()));
        }
        Collections.shuffle(out, RANDOM);
        return out;
    }

    private static String questQuizOptionsJson(JsonObject quest, String milestoneId) {
        int fluencyMs = intAt(quest, "quiz", "fluencyMs", QuestQuizDefinitions.CAVE_ESCAPE_M1_FLUENCY_MS);
        String canonical = canonicalMilestoneId(milestoneId);
        boolean m1 = "m1_cave_start".equals(canonical);
        int required = "m2_deep_passage".equals(canonical)
            ? QuestQuizDefinitions.CAVE_ESCAPE_M2_FAST_CORRECT_REQUIRED
            : QuestQuizDefinitions.CAVE_ESCAPE_M1_FAST_CORRECT_REQUIRED;
        return QuizSessionOptions.questFixed(fluencyMs, required, m1).toJson();
    }


    private static List<Fact> prioritized(List<Fact> facts, QuestProgress progress) {
        List<Fact> out = new ArrayList<>(new LinkedHashSet<>(facts));
        out.sort(Comparator
            .comparing((Fact f) -> progress.statsFor(f).fluent())
            .thenComparingInt(f -> progress.statsFor(f).attempts)
            .thenComparingInt(f -> progress.statsFor(f).fastCorrect)
            .thenComparing(Fact::key));
        return out;
    }

    private static QuestProgress computeProgress(JsonObject quest) {
        int greenMs = intAt(quest, "quiz", "greenMs", 3500);
        int m1FluencyMs = intAt(quest, "quiz", "fluencyMs", QuestQuizDefinitions.CAVE_ESCAPE_M1_FLUENCY_MS);
        double minAccuracy = doubleAt(quest, "quiz", "minAccuracy", 0.90);
        Map<String, FactStats> stats = new LinkedHashMap<>();
        for (Fact f : allFacts()) stats.put(f.key(), new FactStats(greenMs, minAccuracy));
        List<QuestQuizDefinitions.Attempt> orientedAttempts = new ArrayList<>();
        Path sqlite = Path.of(stringOr(quest, "activeSqlitePath", ""));
        if (Files.isRegularFile(sqlite)) {
            try (Connection conn = DriverManager.getConnection("jdbc:sqlite:" + sqlite.toAbsolutePath());
                 Statement stmt = conn.createStatement();
                 ResultSet rs = stmt.executeQuery("""
                     SELECT num1, num2, operation, is_correct, response_time_ms
                     FROM ProblemAttempts
                     """)) {
                while (rs.next()) {
                    String op = rs.getString("operation");
                    if (!isAddition(op)) continue;
                    int a = rs.getInt("num1");
                    int b = rs.getInt("num2");
                    if (a < 0 || a > 9 || b < 0 || b > 9) continue;
                    boolean isCorrect = rs.getInt("is_correct") == 1;
                    long responseTimeMs = rs.getLong("response_time_ms");
                    orientedAttempts.add(new QuestQuizDefinitions.Attempt(op, a, b, isCorrect, responseTimeMs));
                    Fact canonical = new Fact(Math.min(a, b), Math.max(a, b));
                    FactStats s = stats.computeIfAbsent(canonical.key(), key -> new FactStats(greenMs, minAccuracy));
                    s.record(isCorrect, responseTimeMs);
                }
            } catch (Exception e) {
                MathQuestMod.LOGGER.warn("[MathQuest] Quest 01 progress read failed: {}", e.getMessage());
            }
        }
        return new QuestProgress(stats, QuestQuizDefinitions.orientedStats(orientedAttempts, m1FluencyMs));
    }

    private static Map<String, Object> progress(JsonObject quest) {
        QuestProgress progress = computeProgress(quest);
        applyMilestoneProgress(quest, progress);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("activeSqlitePath", stringOr(quest, "activeSqlitePath", ""));
        out.put("currentMilestoneId", currentMilestoneId(quest));
        out.put("fixedQuiz", Map.of(
            "id", fixedQuizId(currentMilestoneId(quest)),
            "name", fixedQuizName(currentMilestoneId(quest)),
            "fluencyMs", intAt(quest, "quiz", "fluencyMs", QuestQuizDefinitions.CAVE_ESCAPE_M1_FLUENCY_MS),
            "fastCorrectRequired", fixedQuizFastCorrectRequired(currentMilestoneId(quest)),
            "requiredProblems", fixedQuizProblemCount(currentMilestoneId(quest)),
            "remainingProblems", fixedQuizRemainingCount(currentMilestoneId(quest), progress)
        ));
        out.put("categories", List.of(
            orientedCategoryStatus("M1 Add Zero + Add One", "m1_zero_one_fixed",
                QuestQuizDefinitions.caveEscapeM1Problems(), progress,
                QuestQuizDefinitions.CAVE_ESCAPE_M1_FAST_CORRECT_REQUIRED),
            orientedCategoryStatus("M2 Add Two + Doubles", "m2_two_doubles_fixed",
                QuestQuizDefinitions.caveEscapeM2Problems(), progress,
                QuestQuizDefinitions.CAVE_ESCAPE_M2_FAST_CORRECT_REQUIRED),
            categoryStatus("Tough 21", "tough_21", TOUGH_21, progress),
            categoryStatus("Hardest Six", "hardest_six", HARDEST_SIX, progress)
        ));
        out.put("milestones", jsonToObject(quest.getAsJsonArray("milestones")));
        return out;
    }

    private static String fixedQuizId(String milestoneId) {
        return "m2_deep_passage".equals(milestoneId)
            ? QuestQuizDefinitions.CAVE_ESCAPE_M2_QUIZ_ID
            : QuestQuizDefinitions.CAVE_ESCAPE_M1_QUIZ_ID;
    }

    private static String fixedQuizName(String milestoneId) {
        return "m2_deep_passage".equals(milestoneId)
            ? "M2 Add Two + Doubles"
            : "M1 Add Zero + Add One";
    }

    private static int fixedQuizProblemCount(String milestoneId) {
        return "m2_deep_passage".equals(milestoneId)
            ? QuestQuizDefinitions.caveEscapeM2Problems().size()
            : QuestQuizDefinitions.caveEscapeM1Problems().size();
    }

    private static int fixedQuizFastCorrectRequired(String milestoneId) {
        return "m2_deep_passage".equals(milestoneId)
            ? QuestQuizDefinitions.CAVE_ESCAPE_M2_FAST_CORRECT_REQUIRED
            : QuestQuizDefinitions.CAVE_ESCAPE_M1_FAST_CORRECT_REQUIRED;
    }

    private static int fixedQuizRemainingCount(String milestoneId, QuestProgress progress) {
        return "m2_deep_passage".equals(milestoneId)
            ? QuestQuizDefinitions.caveEscapeM2RemainingProblems(progress.orientedStats()).size()
            : QuestQuizDefinitions.caveEscapeM1RemainingProblems(progress.orientedStats()).size();
    }

    private static Map<String, Object> orientedCategoryStatus(
        String name,
        String id,
        List<QuestQuizDefinitions.ProblemSpec> problems,
        QuestProgress progress,
        int fastCorrectRequired
    ) {
        int attempts = 0;
        int fluent = 0;
        List<Map<String, Object>> factRows = new ArrayList<>();
        for (QuestQuizDefinitions.ProblemSpec problem : problems) {
            QuestQuizDefinitions.OrientedStats s = progress.orientedStatsFor(problem);
            attempts += s.attempts();
            if (s.fluent(fastCorrectRequired)) fluent++;
            factRows.add(Map.of(
                "fact", problem.label(),
                "attempts", s.attempts(),
                "correct", s.correct(),
                "fastCorrect", s.fastCorrect(),
                "maxFastCorrectStreak", s.maxFastCorrectStreak(),
                "fluent", s.fluent(fastCorrectRequired)
            ));
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("id", id);
        out.put("name", name);
        out.put("canonicalCount", problems.size());
        out.put("fluentCount", fluent);
        out.put("attempts", attempts);
        out.put("facts", factRows);
        return out;
    }

    private static Map<String, Object> categoryStatus(String name, String id, List<Fact> facts, QuestProgress progress) {
        int attempts = 0;
        int fluent = 0;
        List<Map<String, Object>> factRows = new ArrayList<>();
        for (Fact f : facts) {
            FactStats s = progress.statsFor(f);
            attempts += s.attempts;
            if (s.fluent()) fluent++;
            factRows.add(Map.of(
                "fact", f.label(),
                "attempts", s.attempts,
                "correct", s.correct,
                "fastCorrect", s.fastCorrect,
                "fluent", s.fluent()
            ));
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("id", id);
        out.put("name", name);
        out.put("canonicalCount", facts.size());
        out.put("fluentCount", fluent);
        out.put("attempts", attempts);
        out.put("facts", factRows);
        return out;
    }

    private static void applyMilestoneProgress(JsonObject quest, QuestProgress progress) {
        JsonArray milestones = quest.getAsJsonArray("milestones");
        for (JsonElement el : milestones) {
            JsonObject m = el.getAsJsonObject();
            String id = stringOr(m, "id", "");
            boolean complete = switch (id) {
                case "m1_cave_start" -> QuestQuizDefinitions.caveEscapeM1Complete(progress.orientedStats());
                case "m2_deep_passage" -> QuestQuizDefinitions.caveEscapeM2Complete(progress.orientedStats());
                case "m3_winding_tunnel" -> progress.fluentCount(TOUGH_21) >= 10;
                case "m4_chamber" -> progress.fluentCount(TOUGH_21) >= 15;
                case "m5_connector" -> progress.fluentCount(TOUGH_21) >= 18;
                case "m6_surface_break" -> progress.fluentCount(TOUGH_21) >= 21;
                default -> false;
            };
            if (complete) m.addProperty("status", "completed");
        }
        boolean activated = false;
        for (JsonElement el : milestones) {
            JsonObject m = el.getAsJsonObject();
            String status = stringOr(m, "status", "locked");
            if (!"completed".equals(status) && !activated) {
                m.addProperty("status", "active");
                activated = true;
            } else if (!"completed".equals(status)) {
                m.addProperty("status", "locked");
            }
        }
    }

    private static Map<String, Object> pathsJson() {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("questDir", questDir().toString());
        out.put("questConfig", questPath().toString());
        out.put("worldConfig", worldPath().toString());
        out.put("versionsDir", versionsDir().toString());
        out.put("backupsDir", backupsDir().toString());
        out.put("mathQuizActiveDir", MathQuestMod.CONFIG.resolveMathQuizActiveDir().toString());
        return out;
    }

    private static List<Map<String, Object>> onlinePlayers(MinecraftServer server) {
        List<Map<String, Object>> out = new ArrayList<>();
        if (server == null) return out;
        for (ServerPlayer player : server.getPlayerList().getPlayers()) {
            BlockPos pos = player.blockPosition();
            out.add(Map.of(
                "playerName", player.getName().getString(),
                "realName", MathQuestMod.CONFIG.resolveRealName(player.getName().getString()),
                "x", pos.getX(),
                "y", pos.getY(),
                "z", pos.getZ(),
                "dimension", player.level().dimension().identifier().toString()
            ));
        }
        return out;
    }

    private static Map<String, Object> serverJson(MinecraftServer server) {
        Map<String, Object> out = new LinkedHashMap<>();
        if (server != null) {
            out.put("onlineCount", server.getPlayerCount());
        }
        return out;
    }

    private static List<String> defaultCommandSuggestions(JsonObject quest) {
        String player = learnerPlayerName(quest);
        return List.of(
            "tp " + player + " 1375 -18 1311",
            "clear_inventory",
            "gamerule keepInventory true",
            "gamemode adventure " + player,
            "gamemode survival " + player,
            "effect clear " + player,
            "start_quiz",
            "open_quiz",
            "open_quiz_invitation",
            "title " + player + " title {\"text\":\"Quest begins\",\"color\":\"gold\"}",
            "playsound minecraft:block.amethyst_block.chime master " + player
        );
    }

    private static JsonArray linesArray(String text) {
        JsonArray arr = new JsonArray();
        for (String line : (text == null ? "" : text).split("\\R")) {
            String clean = line.trim();
            if (!clean.isBlank()) arr.add(clean);
        }
        return arr;
    }

    private static Map<String, Object> latestBackupJson(JsonObject quest) {
        JsonObject backup = quest.has("playerBackup") && quest.get("playerBackup").isJsonObject()
            ? quest.getAsJsonObject("playerBackup")
            : null;
        if (backup == null) return Map.of("exists", false);
        String path = stringOr(backup, "path", "");
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("exists", !path.isBlank() && Files.isRegularFile(Path.of(path)));
        out.put("path", path);
        out.put("savedAt", stringOr(backup, "savedAt", ""));
        out.put("playerName", stringOr(backup, "playerName", ""));
        out.put("restored", boolOr(backup, "restored", false));
        return out;
    }

    private static Path activeSqlitePath(String realName, int tryNumber) {
        String safe = safeName(realName);
        String date = LocalDate.now().toString();
        return MathQuestMod.CONFIG.resolveMathQuizActiveDir().resolve("quest1_try" + tryNumber + "_" + safe + "_" + date + ".sqlite");
    }

    private static int minProblemFactor(List<QuizManager.Problem> problems) {
        int min = Integer.MAX_VALUE;
        for (QuizManager.Problem problem : problems) {
            min = Math.min(min, Math.min(problem.factorA, problem.factorB));
        }
        return min == Integer.MAX_VALUE ? 0 : min;
    }

    private static int maxProblemFactor(List<QuizManager.Problem> problems) {
        int max = Integer.MIN_VALUE;
        for (QuizManager.Problem problem : problems) {
            max = Math.max(max, Math.max(problem.factorA, problem.factorB));
        }
        return max == Integer.MIN_VALUE ? 0 : max;
    }

    private static int nextTryNumber(String realName) {
        Path dir = MathQuestMod.CONFIG.resolveMathQuizActiveDir();
        String safe = safeName(realName);
        int max = 0;
        try {
            Files.createDirectories(dir);
            try (var stream = Files.list(dir)) {
                for (Path path : stream.toList()) {
                    Matcher m = TRY_PATTERN.matcher(path.getFileName().toString());
                    if (m.matches() && safe.equals(m.group(2))) {
                        max = Math.max(max, Integer.parseInt(m.group(1)));
                    }
                }
            }
        } catch (IOException e) {
            MathQuestMod.LOGGER.warn("[MathQuest] Quest 01 try scan failed: {}", e.getMessage());
        }
        return max + 1;
    }

    private static String safeName(String raw) {
        String s = raw == null || raw.isBlank() ? "unknown" : raw.trim();
        return s.replaceAll("[^A-Za-z0-9_-]", "_");
    }

    private static JsonObject readQuest() {
        JsonObject quest = readQuestIfExists().orElseGet(CaveEscapeQuestService::defaultQuest);
        ensureQuestShape(quest);
        if (!Files.isRegularFile(questPath())) saveQuest(quest);
        return quest;
    }

    private static Optional<JsonObject> readQuestIfExists() {
        Path path = questPath();
        if (!Files.isRegularFile(path)) return Optional.empty();
        try {
            JsonObject obj = JsonParser.parseString(Files.readString(path)).getAsJsonObject();
            ensureQuestShape(obj);
            return Optional.of(obj);
        } catch (Exception e) {
            MathQuestMod.LOGGER.warn("[MathQuest] Quest 01 config read failed, using defaults: {}", e.getMessage());
            return Optional.empty();
        }
    }

    private static JsonObject readWorld(MinecraftServer server) {
        Path path = worldPath();
        if (Files.isRegularFile(path)) {
            try {
                JsonObject obj = JsonParser.parseString(Files.readString(path)).getAsJsonObject();
                ensureWorldShape(obj, server);
                saveWorld(obj);
                return obj;
            } catch (Exception e) {
                MathQuestMod.LOGGER.warn("[MathQuest] Quest 01 world config read failed, using defaults: {}", e.getMessage());
            }
        }
        JsonObject world = defaultWorld(server);
        saveWorld(world);
        return world;
    }

    private static void saveQuest(JsonObject quest) {
        try {
            Files.createDirectories(questDir());
            Files.writeString(questPath(), GSON.toJson(quest));
        } catch (IOException e) {
            MathQuestMod.LOGGER.warn("[MathQuest] Quest 01 config save failed: {}", e.getMessage());
        }
    }

    private static void saveWorld(JsonObject world) {
        try {
            Files.createDirectories(questDir());
            Files.writeString(worldPath(), GSON.toJson(world));
        } catch (IOException e) {
            MathQuestMod.LOGGER.warn("[MathQuest] Quest 01 world save failed: {}", e.getMessage());
        }
    }

    private static Path questDir() {
        return MathQuestMod.CONFIG.resolveDataDir().resolve("quests").resolve(QUEST_ID);
    }

    private static Path questPath() {
        return questDir().resolve("quest.json");
    }

    private static Path worldPath() {
        return questDir().resolve("world.json");
    }

    private static Path versionsDir() {
        return questDir().resolve("versions");
    }

    private static Path backupsDir() {
        return questDir().resolve("backups");
    }

    private static Path saveSetupVersion(JsonObject quest, JsonObject world, String label) {
        String cleanLabel = safeName(label == null || label.isBlank() ? "setup" : label).toLowerCase(Locale.ROOT);
        String stamp = OffsetDateTime.now().format(VERSION_STAMP);
        Path out = versionsDir().resolve(stamp + "_" + cleanLabel + ".json");
        JsonObject root = new JsonObject();
        root.addProperty("questId", QUEST_ID);
        root.addProperty("savedAt", OffsetDateTime.now().toString());
        root.addProperty("label", label == null ? "" : label.trim());
        root.add("quest", quest.deepCopy());
        root.add("world", world.deepCopy());
        try {
            Files.createDirectories(versionsDir());
            Files.writeString(out, GSON.toJson(root));
        } catch (IOException e) {
            MathQuestMod.LOGGER.warn("[MathQuest] Quest 01 setup version save failed: {}", e.getMessage());
        }
        return out;
    }

    private static List<Map<String, Object>> savedVersions() {
        List<Map<String, Object>> out = new ArrayList<>();
        if (!Files.isDirectory(versionsDir())) return out;
        try (var stream = Files.list(versionsDir())) {
            stream
                .filter(path -> path.getFileName().toString().endsWith(".json"))
                .sorted(Comparator.reverseOrder())
                .limit(20)
                .forEach(path -> out.add(Map.of(
                    "filename", path.getFileName().toString(),
                    "path", path.toString()
                )));
        } catch (IOException e) {
            MathQuestMod.LOGGER.warn("[MathQuest] Quest 01 setup versions scan failed: {}", e.getMessage());
        }
        return out;
    }

    private static JsonObject defaultQuest() {
        JsonObject root = new JsonObject();
        root.addProperty("questId", QUEST_ID);
        root.addProperty("displayName", DISPLAY_NAME);
        root.addProperty("enabled", true);
        root.addProperty("active", false);
        root.addProperty("tryNumber", 0);
        root.addProperty("activeSqlitePath", "");
        JsonObject learner = new JsonObject();
        learner.addProperty("playerName", DEFAULT_PLAYER_NAME);
        learner.addProperty("realName", DEFAULT_REAL_NAME);
        root.add("learner", learner);
        JsonObject quiz = new JsonObject();
        quiz.addProperty("operation", "addition");
        quiz.addProperty("problemsPerQuiz", 7);
        quiz.addProperty("greenMs", QuestQuizDefinitions.CAVE_ESCAPE_M1_FLUENCY_MS);
        quiz.addProperty("fluencyMs", QuestQuizDefinitions.CAVE_ESCAPE_M1_FLUENCY_MS);
        quiz.addProperty("fastCorrectRequired", QuestQuizDefinitions.CAVE_ESCAPE_M1_FAST_CORRECT_REQUIRED);
        quiz.addProperty("redMs", 7000);
        quiz.addProperty("minAccuracy", 0.90);
        quiz.addProperty("selectionMode", "fixed_milestone_quiz");
        quiz.addProperty("currentFixedQuizId", QuestQuizDefinitions.CAVE_ESCAPE_M1_QUIZ_ID);
        root.add("quiz", quiz);
        root.add("milestones", defaultMilestones());
        root.add("contentCues", defaultContentCues());
        root.add("mechanics", defaultMechanics());
        root.add("actionLog", new JsonArray());
        return root;
    }

    private static void normalizeLearner(JsonObject quest, boolean forceRealNameLookup) {
        JsonObject learner = quest.getAsJsonObject("learner");
        String playerName = cleanName(stringOr(learner, "playerName", DEFAULT_PLAYER_NAME));
        String currentRealName = stringOr(learner, "realName", "");
        learner.addProperty("playerName", playerName);
        if (forceRealNameLookup || currentRealName.isBlank()) {
            learner.addProperty("realName", resolveLearnerRealName(playerName, ""));
        }
    }

    private static JsonObject defaultWorld(MinecraftServer server) {
        JsonObject root = new JsonObject();
        root.add("spawn", location(1375, -18, 1311, "minecraft:overworld", "Start"));
        JsonObject locations = new JsonObject();
        locations.add("m1_cave_start", location(1375, -18, 1311, "minecraft:overworld", "Start"));
        locations.add("m2_deep_passage", location(1378, -13, 1312, "minecraft:overworld", "Deep passage"));
        locations.add("m3_winding_tunnel", location(null, null, null, "minecraft:overworld", "Winding tunnel"));
        locations.add("m4_chamber", location(null, null, null, "minecraft:overworld", "Chamber"));
        locations.add("m5_connector", location(null, null, null, "minecraft:overworld", "Connector"));
        locations.add("m6_surface_break", location(1401, 86, 1293, "minecraft:overworld", "Breakthrough"));
        root.add("locations", locations);
        return root;
    }

    private static JsonObject location(Integer x, Integer y, Integer z, String dimension, String label) {
        JsonObject obj = new JsonObject();
        if (x != null) obj.addProperty("x", x);
        if (y != null) obj.addProperty("y", y);
        if (z != null) obj.addProperty("z", z);
        obj.addProperty("dimension", dimension);
        obj.addProperty("label", label);
        return obj;
    }

    private static JsonArray defaultMilestones() {
        JsonArray arr = new JsonArray();
        milestone(arr, "m1_cave_start", "Cave Start", "The path begins in the starting cave. Use Add Zero and Add One to get moving.", "Add Zero + Add One fluent", "active");
        milestone(arr, "m2_deep_passage", "Deep Passage", "Move through the deep passage by strengthening Add Two and Doubles.", "Add Two + Doubles fluent", "locked");
        milestone(arr, "m3_winding_tunnel", "Winding Tunnel", "The tunnel bends and narrows. Start working through the Tough 21 facts.", "10 Tough 21 facts fluent", "locked");
        milestone(arr, "m4_chamber", "Chamber", "The route opens into a larger chamber. Keep building Tough 21 fluency.", "15 Tough 21 facts fluent", "locked");
        milestone(arr, "m5_connector", "Connector", "A connector passage links the chamber to the final stretch.", "18 Tough 21 facts fluent", "locked");
        milestone(arr, "m6_surface_break", "Surface Break", "Finish the Tough 21 and open the final way out.", "21 Tough 21 facts fluent", "locked");
        return arr;
    }

    private static void milestone(JsonArray arr, String id, String name, String story, String exit, String status) {
        JsonObject obj = new JsonObject();
        obj.addProperty("id", id);
        obj.addProperty("name", name);
        obj.addProperty("storyText", story);
        obj.addProperty("exitRule", exit);
        obj.addProperty("status", status);
        obj.addProperty("audioPath", "");
        obj.addProperty("musicPath", "");
        obj.add("startActions", defaultStartActions(id));
        obj.add("endActions", defaultEndActions(id));
        arr.add(obj);
    }

    private static JsonArray defaultStartActions(String id) {
        return jsonArray(defaultStartActionLines(id));
    }

    static List<String> defaultStartActionLines(String id) {
        List<String> arr = new ArrayList<>();
        if ("m1_cave_start".equals(id)) {
            arr.add("gamerule keepInventory true");
            arr.add("gamemode survival {player}");
            arr.add("teleport m1_cave_start");
            arr.add("clear_inventory");
            arr.add("title A rumble seals the cave behind you.");
            arr.add("wait 20");
            arr.add("chat " + QUEST_INVITATION_CHAT);
            arr.add("open_quiz_invitation");
        }
        return arr;
    }

    private static JsonArray jsonArray(List<String> lines) {
        JsonArray arr = new JsonArray();
        for (String line : lines) {
            arr.add(line);
        }
        return arr;
    }

    private static JsonArray defaultEndActions(String id) {
        JsonArray arr = new JsonArray();
        if ("m1_cave_start".equals(id)) {
            arr.add("give {player} minecraft:torch 1");
            arr.add("title Let there be light.");
        } else if ("m6_surface_break".equals(id)) {
            arr.add("title The cave breaks open into daylight.");
        }
        return arr;
    }

    private static JsonArray defaultContentCues() {
        JsonArray arr = new JsonArray();
        cue(arr, "quest_start", "A rumble seals the cave behind you. Solve the glowing math runes to find the way forward.", "title");
        cue(arr, "quiz_offer", "The stone warms under your hand. A short addition challenge appears.", "chat");
        cue(arr, "milestone_clear", "A hidden seam opens. The path ahead shifts into place.", "chat");
        cue(arr, "finale", "The last wall breaks open. Something impossible is waiting outside.", "title");
        return arr;
    }

    private static void cue(JsonArray arr, String id, String text, String delivery) {
        JsonObject obj = new JsonObject();
        obj.addProperty("id", id);
        obj.addProperty("text", text);
        obj.addProperty("delivery", delivery);
        obj.addProperty("audioPath", "");
        obj.addProperty("musicPath", "");
        arr.add(obj);
    }

    private static JsonArray defaultMechanics() {
        JsonArray arr = new JsonArray();
        mechanic(arr, "m1_spider_gate", "combat_quiz_gate", "m1_cave_start", "minecraft:cave_spider",
            "Spider Gate", "fixed_pass_fail", "dormant");
        mechanic(arr, "m2_button_gate", "explore_button_gate", "m2_deep_passage", "minecraft:stone_button",
            "Stone Button Gate", "mastery_loop", "dormant");
        mechanic(arr, "m6_finale_gate", "explore_button_gate", "m6_surface_break", "minecraft:amethyst_cluster",
            "Surface Break Gate", "mastery_loop", "dormant");
        return arr;
    }

    private static void mechanic(JsonArray arr, String id, String type, String locationId, String entityOrBlock,
                                 String label, String successMode, String status) {
        JsonObject obj = new JsonObject();
        obj.addProperty("id", id);
        obj.addProperty("type", type);
        obj.addProperty("locationId", locationId);
        obj.addProperty("entityOrBlock", entityOrBlock);
        obj.addProperty("label", label);
        obj.addProperty("successMode", successMode);
        obj.addProperty("status", status);
        obj.addProperty("respawnDelaySeconds", 45);
        arr.add(obj);
    }

    private static void ensureQuestShape(JsonObject quest) {
        JsonObject defaults = defaultQuest();
        for (String key : defaults.keySet()) {
            if (!quest.has(key) || quest.get(key).isJsonNull()) quest.add(key, defaults.get(key).deepCopy());
        }
        if (!quest.get("learner").isJsonObject()) quest.add("learner", defaults.get("learner").deepCopy());
        if (!quest.get("quiz").isJsonObject()) quest.add("quiz", defaults.get("quiz").deepCopy());
        if (!quest.get("milestones").isJsonArray()) quest.add("milestones", defaults.get("milestones").deepCopy());
        if (!quest.get("contentCues").isJsonArray()) quest.add("contentCues", defaults.get("contentCues").deepCopy());
        if (!quest.get("mechanics").isJsonArray()) quest.add("mechanics", defaults.get("mechanics").deepCopy());
        if (!quest.has("actionLog") || !quest.get("actionLog").isJsonArray()) quest.add("actionLog", new JsonArray());
        ensureQuestQuizShape(quest.getAsJsonObject("quiz"));
        migrateQuestLocationIds(quest);
    }

    private static void ensureQuestQuizShape(JsonObject quiz) {
        if (quiz == null) return;
        if (!quiz.has("fluencyMs") || quiz.get("fluencyMs").isJsonNull()) {
            int existingGreenMs = intOr(quiz, "greenMs", QuestQuizDefinitions.CAVE_ESCAPE_M1_FLUENCY_MS);
            quiz.addProperty("fluencyMs", existingGreenMs == 3500
                ? QuestQuizDefinitions.CAVE_ESCAPE_M1_FLUENCY_MS
                : existingGreenMs);
        }
        if (!quiz.has("fastCorrectRequired") || quiz.get("fastCorrectRequired").isJsonNull()) {
            quiz.addProperty("fastCorrectRequired", QuestQuizDefinitions.CAVE_ESCAPE_M1_FAST_CORRECT_REQUIRED);
        }
        if (!quiz.has("selectionMode") || quiz.get("selectionMode").isJsonNull()
            || "milestone_priority".equals(stringOr(quiz, "selectionMode", ""))) {
            quiz.addProperty("selectionMode", "fixed_milestone_quiz");
        }
        if (!quiz.has("currentFixedQuizId") || quiz.get("currentFixedQuizId").isJsonNull()) {
            quiz.addProperty("currentFixedQuizId", QuestQuizDefinitions.CAVE_ESCAPE_M1_QUIZ_ID);
        }
    }

    private static void ensureWorldShape(JsonObject world, MinecraftServer server) {
        JsonObject defaults = defaultWorld(server);
        for (String key : defaults.keySet()) {
            if (!world.has(key) || world.get(key).isJsonNull()) world.add(key, defaults.get(key).deepCopy());
        }
        if (!world.get("locations").isJsonObject()) world.add("locations", defaults.get("locations").deepCopy());
        world.remove("worldSeed");
        migrateWorldLocationIds(world, defaults);
        applyKnownEndpointDefaults(world);
    }

    private static void migrateQuestLocationIds(JsonObject quest) {
        for (JsonElement el : quest.getAsJsonArray("milestones")) {
            JsonObject milestone = el.getAsJsonObject();
            String oldId = stringOr(milestone, "id", "");
            String newId = canonicalMilestoneId(oldId);
            boolean renamed = !newId.equals(oldId);
            milestone.addProperty("id", newId);
            if (renamed || isOldMilestoneText(milestone)) {
                applyDefaultMilestoneText(milestone, newId);
            }
            if (!milestone.has("startActions") || !milestone.get("startActions").isJsonArray()) {
                milestone.add("startActions", defaultStartActions(newId));
            } else if ("m1_cave_start".equals(newId) && usesLegacyM1Invitation(milestone.getAsJsonArray("startActions"))) {
                milestone.add("startActions", defaultStartActions(newId));
            } else if (!"m1_cave_start".equals(newId) && isActionList(milestone.getAsJsonArray("startActions"),
                List.of("teleport " + newId))) {
                milestone.add("startActions", defaultStartActions(newId));
            }
            if (!milestone.has("endActions") || !milestone.get("endActions").isJsonArray()) {
                milestone.add("endActions", defaultEndActions(newId));
            } else if ("m1_cave_start".equals(newId) && isActionList(milestone.getAsJsonArray("endActions"),
                List.of("chat A hidden route opens deeper into the cave."))) {
                milestone.add("endActions", defaultEndActions(newId));
            }
        }
        for (JsonElement el : quest.getAsJsonArray("mechanics")) {
            JsonObject mechanic = el.getAsJsonObject();
            mechanic.addProperty("locationId", canonicalMilestoneId(stringOr(mechanic, "locationId", "")));
            String label = stringOr(mechanic, "label", "");
            if ("Surface Break Finale".equals(label)) {
                mechanic.addProperty("label", "Surface Break Gate");
            }
        }
    }

    private static void migrateWorldLocationIds(JsonObject world, JsonObject defaults) {
        JsonObject locations = world.getAsJsonObject("locations");
        JsonObject defaultLocations = defaults.getAsJsonObject("locations");
        for (String oldId : List.of(
            "m1_cave_mouth",
            "m2_deeper_passage",
            "m3_first_glimmer",
            "m4_winding_tunnel",
            "m5_almost_daylight"
        )) {
            if (!locations.has(oldId)) continue;
            String newId = canonicalMilestoneId(oldId);
            if (!locations.has(newId)) {
                JsonObject migrated = locations.getAsJsonObject(oldId).deepCopy();
                if (defaultLocations.has(newId)) {
                    migrated.addProperty("label", stringOr(defaultLocations.getAsJsonObject(newId), "label", newId));
                }
                locations.add(newId, migrated);
            }
            locations.remove(oldId);
        }
        for (String id : defaultLocations.keySet()) {
            if (!locations.has(id)) {
                locations.add(id, defaultLocations.get(id).deepCopy());
            } else if (isOldLocationLabel(stringOr(locations.getAsJsonObject(id), "label", ""))) {
                locations.getAsJsonObject(id).addProperty("label", stringOr(defaultLocations.getAsJsonObject(id), "label", id));
            }
        }
    }

    private static String canonicalMilestoneId(String raw) {
        String id = raw == null ? "" : raw.trim();
        return switch (id) {
            case "m1_cave_mouth" -> "m1_cave_start";
            case "m2_deeper_passage" -> "m2_deep_passage";
            case "m3_first_glimmer" -> "m3_winding_tunnel";
            case "m4_winding_tunnel" -> "m4_chamber";
            case "m5_almost_daylight" -> "m5_connector";
            case "" -> "m1_cave_start";
            default -> id;
        };
    }

    private static void applyDefaultMilestoneText(JsonObject milestone, String id) {
        switch (id) {
            case "m1_cave_start" -> {
                milestone.addProperty("name", "Cave Start");
                milestone.addProperty("storyText", "The path begins in the starting cave. Use Add Zero and Add One to get moving.");
                milestone.addProperty("exitRule", "Add Zero + Add One fluent");
            }
            case "m2_deep_passage" -> {
                milestone.addProperty("name", "Deep Passage");
                milestone.addProperty("storyText", "Move through the deep passage by strengthening Add Two and Doubles.");
                milestone.addProperty("exitRule", "Add Two + Doubles fluent");
            }
            case "m3_winding_tunnel" -> {
                milestone.addProperty("name", "Winding Tunnel");
                milestone.addProperty("storyText", "The tunnel bends and narrows. Start working through the Tough 21 facts.");
                milestone.addProperty("exitRule", "10 Tough 21 facts fluent");
            }
            case "m4_chamber" -> {
                milestone.addProperty("name", "Chamber");
                milestone.addProperty("storyText", "The route opens into a larger chamber. Keep building Tough 21 fluency.");
                milestone.addProperty("exitRule", "15 Tough 21 facts fluent");
            }
            case "m5_connector" -> {
                milestone.addProperty("name", "Connector");
                milestone.addProperty("storyText", "A connector passage links the chamber to the final stretch.");
                milestone.addProperty("exitRule", "18 Tough 21 facts fluent");
            }
            case "m6_surface_break" -> {
                milestone.addProperty("name", "Surface Break");
                milestone.addProperty("storyText", "Finish the Tough 21 and open the final way out.");
                milestone.addProperty("exitRule", "21 Tough 21 facts fluent");
            }
            default -> {}
        }
    }

    private static boolean isOldMilestoneText(JsonObject milestone) {
        String name = stringOr(milestone, "name", "");
        String story = stringOr(milestone, "storyText", "");
        return List.of("Cave Mouth", "Deeper Passage", "First Glimmer", "Almost Daylight").contains(name)
            || story.toLowerCase(Locale.ROOT).contains("glimmer")
            || story.toLowerCase(Locale.ROOT).contains("daylight");
    }

    private static boolean isOldLocationLabel(String label) {
        return List.of("Cave mouth", "Deeper passage", "First daylight glimmer", "Almost daylight").contains(label);
    }

    private static boolean usesLegacyM1Invitation(JsonArray arr) {
        if (arr == null) return false;
        boolean hasInvitation = false;
        boolean hasDuplicateInvitationTitle = false;
        String duplicateTitle = ("title " + QUEST_INVITATION_TITLE).toLowerCase(Locale.ROOT);
        for (JsonElement el : arr) {
            if (el == null || el.isJsonNull()) continue;
            String line = el.getAsString().trim().toLowerCase(Locale.ROOT);
            if ("open_quiz".equals(line)) return true;
            if ("open_quiz_invitation".equals(line)) hasInvitation = true;
            if (duplicateTitle.equals(line)) hasDuplicateInvitationTitle = true;
        }
        if (hasInvitation && hasDuplicateInvitationTitle) return true;
        return isActionList(arr, List.of("teleport m1_cave_start", "clear_inventory", "title A rumble seals the cave behind you."));
    }

    private static boolean isActionList(JsonArray arr, List<String> expected) {
        if (arr == null || arr.size() != expected.size()) return false;
        for (int i = 0; i < expected.size(); i++) {
            if (!expected.get(i).equals(arr.get(i).getAsString())) return false;
        }
        return true;
    }

    private static void applyKnownEndpointDefaults(JsonObject world) {
        JsonObject spawn = world.getAsJsonObject("spawn");
        if (spawn == null || isCoords(spawn, 0, 64, 0) || missingCoords(spawn)) {
            world.add("spawn", location(1375, -18, 1311, "minecraft:overworld", "Start"));
        }
        JsonObject locations = world.getAsJsonObject("locations");
        if (locations == null) return;
        JsonObject start = locations.has("m1_cave_start") && locations.get("m1_cave_start").isJsonObject()
            ? locations.getAsJsonObject("m1_cave_start")
            : new JsonObject();
        if (isCoords(start, 0, 64, 16) || missingCoords(start)) {
            locations.add("m1_cave_start", location(1375, -18, 1311, "minecraft:overworld", "Start"));
        }
        JsonObject deepPassage = locations.has("m2_deep_passage") && locations.get("m2_deep_passage").isJsonObject()
            ? locations.getAsJsonObject("m2_deep_passage")
            : new JsonObject();
        if (isCoords(deepPassage, 0, 58, 44) || missingCoords(deepPassage)) {
            locations.add("m2_deep_passage", location(1378, -13, 1312, "minecraft:overworld", "Deep passage"));
        }
        JsonObject breakthrough = locations.has("m6_surface_break") && locations.get("m6_surface_break").isJsonObject()
            ? locations.getAsJsonObject("m6_surface_break")
            : new JsonObject();
        if (isCoords(breakthrough, 28, 72, 168) || missingCoords(breakthrough)) {
            locations.add("m6_surface_break", location(1401, 86, 1293, "minecraft:overworld", "Breakthrough"));
        }
    }

    private static boolean missingCoords(JsonObject obj) {
        return obj == null || !obj.has("x") || !obj.has("y") || !obj.has("z");
    }

    private static boolean isCoords(JsonObject obj, int x, int y, int z) {
        return obj != null
            && obj.has("x") && obj.has("y") && obj.has("z")
            && obj.get("x").getAsInt() == x
            && obj.get("y").getAsInt() == y
            && obj.get("z").getAsInt() == z;
    }

    private static void resetMilestones(JsonObject quest, boolean keepCompleted) {
        JsonArray milestones = quest.getAsJsonArray("milestones");
        for (int i = 0; i < milestones.size(); i++) {
            JsonObject m = milestones.get(i).getAsJsonObject();
            if (keepCompleted && "completed".equals(stringOr(m, "status", ""))) continue;
            m.addProperty("status", i == 0 ? "active" : "locked");
            m.remove("endActionsRunAt");
        }
    }

    private static int currentMilestoneIndex(JsonObject quest) {
        JsonArray milestones = quest.getAsJsonArray("milestones");
        for (int i = 0; i < milestones.size(); i++) {
            if ("active".equals(stringOr(milestones.get(i).getAsJsonObject(), "status", ""))) return i;
        }
        for (int i = 0; i < milestones.size(); i++) {
            if (!"completed".equals(stringOr(milestones.get(i).getAsJsonObject(), "status", ""))) return i;
        }
        return Math.max(0, milestones.size() - 1);
    }

    private static String currentMilestoneId(JsonObject quest) {
        JsonArray milestones = quest.getAsJsonArray("milestones");
        if (milestones.size() == 0) return "m1_cave_start";
        return canonicalMilestoneId(stringOr(milestones.get(currentMilestoneIndex(quest)).getAsJsonObject(), "id", "m1_cave_start"));
    }

    private static String currentMilestoneName(JsonObject quest) {
        JsonArray milestones = quest.getAsJsonArray("milestones");
        if (milestones.size() == 0) return "Cave Start";
        JsonObject milestone = milestones.get(currentMilestoneIndex(quest)).getAsJsonObject();
        return stringOr(milestone, "name", currentMilestoneId(quest));
    }

    private static void setMilestoneStatus(JsonObject quest, int index, String status) {
        JsonArray milestones = quest.getAsJsonArray("milestones");
        if (index < 0 || index >= milestones.size()) return;
        milestones.get(index).getAsJsonObject().addProperty("status", status);
    }

    private static List<Map<String, Object>> runSetupForMilestone(
        JsonObject quest,
        JsonObject world,
        MinecraftServer server,
        String milestoneId,
        String phase
    ) {
        String canonicalPhase = "end".equalsIgnoreCase(phase) ? "end" : "start";
        String canonicalId = canonicalMilestoneId(milestoneId);
        List<Map<String, Object>> out = new ArrayList<>();
        ServerPlayer player = targetPlayer(quest, server);
        if (player != null && "start".equals(canonicalPhase)) {
            out.add(backupPlayerStateIfNeeded(quest, player, server));
        }
        JsonObject milestone = milestoneById(quest, canonicalId);
        JsonArray actions = milestoneActions(milestone, canonicalPhase);
        out.addAll(runActionLines(actions, quest, world, server, canonicalId));
        return out;
    }

    private static List<Map<String, Object>> runCompletedMilestoneEndActions(JsonObject quest, JsonObject world, MinecraftServer server) {
        List<Map<String, Object>> out = new ArrayList<>();
        for (JsonElement el : quest.getAsJsonArray("milestones")) {
            JsonObject milestone = el.getAsJsonObject();
            if (!"completed".equals(stringOr(milestone, "status", ""))) continue;
            if (milestone.has("endActionsRunAt") && !milestone.get("endActionsRunAt").isJsonNull()) continue;
            String milestoneId = canonicalMilestoneId(stringOr(milestone, "id", ""));
            out.addAll(runActionLines(milestoneActions(milestone, "end"), quest, world, server, milestoneId));
            milestone.addProperty("endActionsRunAt", OffsetDateTime.now().toString());
        }
        return out;
    }

    private static JsonObject milestoneById(JsonObject quest, String milestoneId) {
        for (JsonElement el : quest.getAsJsonArray("milestones")) {
            JsonObject milestone = el.getAsJsonObject();
            if (milestoneId.equals(stringOr(milestone, "id", ""))) return milestone;
        }
        return null;
    }

    private static JsonArray milestoneActions(JsonObject milestone, String phase) {
        String key = "end".equals(phase) ? "endActions" : "startActions";
        if (milestone != null && milestone.has(key) && milestone.get(key).isJsonArray()) {
            return milestone.getAsJsonArray(key);
        }
        return new JsonArray();
    }

    private static List<Map<String, Object>> runActionLines(
        JsonArray actions,
        JsonObject quest,
        JsonObject world,
        MinecraftServer server,
        String milestoneId
    ) {
        List<Map<String, Object>> out = new ArrayList<>();
        long delayTicks = 0;
        for (JsonElement el : actions) {
            String line = el == null || el.isJsonNull() ? "" : el.getAsString();
            int waitSeconds = waitSeconds(line);
            if (waitSeconds >= 0) {
                delayTicks += waitSeconds * 20L;
                out.add(actionResult("wait", line, true, waitSeconds + "s"));
                continue;
            }
            if (delayTicks > 0) {
                SCHEDULED_ACTIONS.add(new ScheduledQuestAction(
                    schedulerTick + delayTicks,
                    learnerPlayerName(quest),
                    canonicalMilestoneId(milestoneId),
                    line
                ));
                out.add(actionResult("schedule", line, true, "in " + (delayTicks / 20L) + "s"));
            } else {
                out.add(runActionLine(line, quest, world, server, milestoneId));
            }
        }
        return out;
    }

    private static int waitSeconds(String rawLine) {
        String line = rawLine == null ? "" : rawLine.trim().toLowerCase(Locale.ROOT);
        if (!line.startsWith("wait ") && !line.startsWith("delay ")) return -1;
        String value = line.substring(line.indexOf(' ') + 1).trim();
        try {
            return Math.max(0, Math.min(300, (int) Math.round(Double.parseDouble(value))));
        } catch (NumberFormatException e) {
            return 0;
        }
    }

    private static Map<String, Object> runActionLine(
        String rawLine,
        JsonObject quest,
        JsonObject world,
        MinecraftServer server,
        String milestoneId
    ) {
        String line = rawLine == null ? "" : rawLine.trim();
        if (line.isBlank() || line.startsWith("#")) return actionResult("skip", line, true, "blank/comment");
        String resolved = substitute(line, quest, milestoneId);
        String lower = resolved.toLowerCase(Locale.ROOT);
        if (resolved.startsWith("/") || lower.startsWith("command ")) {
            String command = resolved.startsWith("/") ? resolved.substring(1) : resolved.substring("command ".length()).trim();
            return runServerCommand(command, quest, server);
        }
        if (lower.equals("gamerule keepinventory true") || lower.equals("gamerule keepinventory false")) {
            return setKeepInventory(server, lower.endsWith(" true"), resolved);
        }
        if (lower.equals("clear_inventory")) {
            ServerPlayer player = targetPlayer(quest, server);
            if (player == null) return actionResult("clear_inventory", resolved, false, "player-offline");
            player.setGameMode(GameType.SURVIVAL);
            player.getInventory().clearContent();
            player.getInventory().setChanged();
            player.inventoryMenu.broadcastChanges();
            return actionResult("clear_inventory", resolved, true, "survival + cleared");
        }
        if (lower.equals("restore_player")) {
            return restorePlayerBackup(quest, server);
        }
        if (lower.equals("open_quiz")) {
            boolean opened = openQuestQuizForLearner(quest, server);
            return actionResult("open_quiz", resolved, opened, opened ? "opened" : "player-offline");
        }
        if (lower.equals("start_quiz")) {
            boolean opened = startQuestQuizForLearner(quest, server);
            return actionResult("start_quiz", resolved, opened, opened ? "sent direct quiz payload" : "player-offline");
        }
        if (lower.equals("open_quiz_invitation")) {
            boolean opened = openQuestInvitationForLearner(quest, server);
            return actionResult("open_quiz_invitation", resolved, opened, opened ? "opened" : "player-offline");
        }
        if (lower.startsWith("teleport")) {
            return runTeleportAction(resolved, quest, world, server, milestoneId);
        }
        if (lower.startsWith("title ")) {
            return sendTitleAction(resolved.substring("title ".length()).trim(), quest, server);
        }
        if (lower.startsWith("chat ")) {
            return sendChatAction(resolved.substring("chat ".length()).trim(), quest, server);
        }
        if (lower.startsWith("audio ") || lower.startsWith("music ")) {
            String sound = resolved.substring(resolved.indexOf(' ') + 1).trim();
            String category = lower.startsWith("music ") ? "music" : "master";
            return runServerCommand("playsound " + sound + " " + category + " " + learnerPlayerName(quest), quest, server);
        }
        return runServerCommand(resolved, quest, server);
    }

    private static Map<String, Object> setKeepInventory(MinecraftServer server, boolean value, String input) {
        if (server == null) return actionResult("gamerule", input, false, "server-unavailable");
        try {
            performSilentServerCommand(server, "gamerule keepInventory " + value);
            return actionResult("gamerule", input, true, "keepInventory=" + value);
        } catch (Exception e) {
            return actionResult("gamerule", input, false, e.getMessage());
        }
    }

    private static Map<String, Object> runTeleportAction(
        String line,
        JsonObject quest,
        JsonObject world,
        MinecraftServer server,
        String fallbackMilestoneId
    ) {
        ServerPlayer player = targetPlayer(quest, server);
        if (player == null) return actionResult("teleport", line, false, "player-offline");
        String arg = line.length() <= "teleport".length() ? fallbackMilestoneId : line.substring("teleport".length()).trim();
        JsonObject location = locationForAction(world, arg.isBlank() ? fallbackMilestoneId : arg);
        if (location == null || missingCoords(location)) return actionResult("teleport", line, false, "missing-coordinates");
        ServerLevel level = levelForLocation(location, server);
        if (level == null) return actionResult("teleport", line, false, "dimension-not-loaded");
        boolean ok = player.teleportTo(
            level,
            intOr(location, "x", 0) + 0.5,
            intOr(location, "y", 64),
            intOr(location, "z", 0) + 0.5,
            Set.of(),
            player.getYRot(),
            player.getXRot(),
            true
        );
        return actionResult("teleport", line, ok, coordsLabel(location));
    }

    private static JsonObject locationForAction(JsonObject world, String raw) {
        String value = raw == null ? "" : raw.trim();
        if (value.isBlank() || "spawn".equalsIgnoreCase(value) || "start".equalsIgnoreCase(value)) {
            return world.getAsJsonObject("spawn");
        }
        String[] parts = value.split("\\s+");
        if (parts.length == 3) {
            try {
                return location(
                    Integer.parseInt(parts[0]),
                    Integer.parseInt(parts[1]),
                    Integer.parseInt(parts[2]),
                    "minecraft:overworld",
                    "inline"
                );
            } catch (NumberFormatException ignored) {
                return null;
            }
        }
        JsonObject locations = world.getAsJsonObject("locations");
        String id = canonicalMilestoneId(value);
        if (locations != null && locations.has(id) && locations.get(id).isJsonObject()) {
            return locations.getAsJsonObject(id);
        }
        return null;
    }

    private static ServerLevel levelForLocation(JsonObject location, MinecraftServer server) {
        if (server == null) return null;
        String dimension = stringOr(location, "dimension", "minecraft:overworld");
        try {
            ResourceKey<Level> key = ResourceKey.create(Registries.DIMENSION, Identifier.parse(normalizeMinecraftId(dimension)));
            ServerLevel level = server.getLevel(key);
            return level != null ? level : server.overworld();
        } catch (Exception e) {
            return server.overworld();
        }
    }

    private static Map<String, Object> runServerCommand(String command, JsonObject quest, MinecraftServer server) {
        String clean = command == null ? "" : command.trim();
        while (clean.startsWith("/")) clean = clean.substring(1).trim();
        clean = substitute(clean, quest, currentMilestoneId(quest));
        if (clean.isBlank()) return actionResult("command", command, false, "blank-command");
        if (server == null) return actionResult("command", clean, false, "server-unavailable");
        try {
            CommandSourceStack source = server.createCommandSourceStack();
            ParseResults<CommandSourceStack> parsed = server.getCommands().getDispatcher().parse(clean, source);
            if (!parsed.getExceptions().isEmpty()) {
                String message = parsed.getExceptions().values().stream()
                    .findFirst()
                    .map(Exception::getMessage)
                    .orElse("command parse failed");
                return actionResult("command", clean, false, message);
            }
            server.getCommands().performCommand(parsed, clean);
            return actionResult("command", clean, true, "sent");
        } catch (Exception e) {
            return actionResult("command", clean, false, e.getMessage());
        }
    }

    private static void performSilentServerCommand(MinecraftServer server, String command) {
        String clean = command == null ? "" : command.trim();
        if (clean.isBlank() || server == null) return;
        try {
            CommandSourceStack source = server.createCommandSourceStack();
            ParseResults<CommandSourceStack> parsed = server.getCommands().getDispatcher().parse(clean, source);
            if (!parsed.getExceptions().isEmpty()) return;
            server.getCommands().performCommand(parsed, clean);
        } catch (Exception ignored) {
            // Optional ambience/cue sounds should never interrupt quest flow.
        }
    }

    private static Map<String, Object> sendTitleAction(String text, JsonObject quest, MinecraftServer server) {
        String player = learnerPlayerName(quest);
        String escaped = GSON.toJson(text == null ? "" : text);
        return runServerCommand("title " + player + " title {\"text\":" + escaped + ",\"color\":\"gold\"}", quest, server);
    }

    private static Map<String, Object> sendChatAction(String text, JsonObject quest, MinecraftServer server) {
        ServerPlayer player = targetPlayer(quest, server);
        if (player == null) return actionResult("chat", text, false, "player-offline");
        player.sendSystemMessage(Component.literal(text == null ? "" : text));
        return actionResult("chat", text, true, "sent");
    }

    private static Map<String, Object> awardM2Blocks(
        JsonObject quest,
        ServerPlayer player,
        List<QuizManager.Problem> completedProblems,
        boolean awaitInventoryEmpty
    ) {
        int fluencyMs = intAt(quest, "quiz", "fluencyMs", QuestQuizDefinitions.CAVE_ESCAPE_M1_FLUENCY_MS);
        int earned = 0;
        if (completedProblems != null) {
            for (QuizManager.Problem problem : completedProblems) {
                if (problem != null && problem.isCorrect && problem.responseTimeMs > 0 && problem.responseTimeMs <= fluencyMs) {
                    earned++;
                }
            }
        }
        if (earned <= 0) {
            return actionResult("m2_award_blocks", M2_REWARD_ITEM_ID, true, "earned=0");
        }
        boolean given = giveQuestItem(player, M2_REWARD_ITEM_ID, earned);
        if (given) {
            JsonObject m2 = m2State(quest);
            m2.addProperty("awaitingInventoryEmpty", awaitInventoryEmpty);
            m2.addProperty("lastBlocksAwarded", earned);
            m2.addProperty("lastBlocksAwardedAt", OffsetDateTime.now().toString());
        }
        return actionResult("m2_award_blocks", M2_REWARD_ITEM_ID, given, "earned=" + earned);
    }

    private static boolean giveQuestItem(ServerPlayer player, String itemId, int count) {
        if (player == null || itemId == null || itemId.isBlank() || count <= 0) return false;
        try {
            var item = BuiltInRegistries.ITEM.getValue(Identifier.parse(itemId));
            if (item == null) return false;
            player.getInventory().placeItemBackInInventory(new ItemStack(item, Math.min(64, count)));
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    private static boolean hasItem(ServerPlayer player, String itemId) {
        if (player == null || itemId == null || itemId.isBlank()) return false;
        Identifier want;
        try {
            want = Identifier.parse(itemId);
        } catch (Exception e) {
            return false;
        }
        Inventory inventory = player.getInventory();
        for (int i = 0; i < inventory.getContainerSize(); i++) {
            ItemStack stack = inventory.getItem(i);
            if (stack == null || stack.isEmpty()) continue;
            Identifier id = BuiltInRegistries.ITEM.getKey(stack.getItem());
            if (want.equals(id)) return true;
        }
        return false;
    }

    private static JsonObject m2State(JsonObject quest) {
        JsonObject state = quest.has("m2") && quest.get("m2").isJsonObject()
            ? quest.getAsJsonObject("m2")
            : new JsonObject();
        quest.add("m2", state);
        return state;
    }

    private static Map<String, Object> actionResult(String type, String input, boolean ok, String message) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("type", type);
        out.put("input", input == null ? "" : input);
        out.put("ok", ok);
        out.put("message", message == null ? "" : message);
        MathQuestMod.LOGGER.info(
            "[MathQuest] Quest 01 action {} {}: {}{}",
            ok ? "ok" : "fail",
            type,
            message == null ? "" : message,
            input == null || input.isBlank() ? "" : " | " + input
        );
        return out;
    }

    private static void recordActionResults(JsonObject quest, String source, List<Map<String, Object>> results) {
        if (quest == null || results == null || results.isEmpty()) return;
        JsonArray log = quest.has("actionLog") && quest.get("actionLog").isJsonArray()
            ? quest.getAsJsonArray("actionLog")
            : new JsonArray();
        String now = OffsetDateTime.now().toString();
        for (Map<String, Object> result : results) {
            JsonObject row = GSON.toJsonTree(result).getAsJsonObject();
            row.addProperty("time", now);
            row.addProperty("source", source == null || source.isBlank() ? "unknown" : source);
            log.add(row);
        }
        while (log.size() > MAX_ACTION_LOG_ENTRIES) {
            log.remove(0);
        }
        quest.add("actionLog", log);
    }

    private static void recordActionResult(JsonObject quest, String source, Map<String, Object> result) {
        recordActionResults(quest, source, List.of(result));
    }

    private static String substitute(String text, JsonObject quest, String milestoneId) {
        return (text == null ? "" : text)
            .replace("{player}", learnerPlayerName(quest))
            .replace("{real}", learnerRealName(quest))
            .replace("{milestone}", canonicalMilestoneId(milestoneId));
    }

    private static String coordsLabel(JsonObject location) {
        if (location == null || missingCoords(location)) return "(missing)";
        return intOr(location, "x", 0) + " " + intOr(location, "y", 0) + " " + intOr(location, "z", 0);
    }

    private static ServerPlayer targetPlayer(JsonObject quest, MinecraftServer server) {
        if (server == null) return null;
        String playerName = learnerPlayerName(quest);
        for (ServerPlayer player : server.getPlayerList().getPlayers()) {
            if (player.getName().getString().equalsIgnoreCase(playerName)) return player;
        }
        return null;
    }

    private static Map<String, Object> backupPlayerStateIfNeeded(JsonObject quest, ServerPlayer player, MinecraftServer server) {
        JsonObject existing = quest.has("playerBackup") && quest.get("playerBackup").isJsonObject()
            ? quest.getAsJsonObject("playerBackup")
            : null;
        if (existing != null) {
            String path = stringOr(existing, "path", "");
            if (!path.isBlank() && Files.isRegularFile(Path.of(path)) && !boolOr(existing, "restored", false)) {
                return actionResult("backup_player", path, true, "existing-backup-preserved");
            }
        }
        String stamp = OffsetDateTime.now().format(VERSION_STAMP);
        String safePlayer = safeName(player.getName().getString());
        Path path = backupsDir().resolve(safePlayer + "_" + stamp + ".json");
        JsonObject backup = new JsonObject();
        backup.addProperty("playerName", player.getName().getString());
        backup.addProperty("savedAt", OffsetDateTime.now().toString());
        backup.add("location", playerLocationJson(player));
        backup.addProperty("health", player.getHealth());
        backup.addProperty("food", player.getFoodData().getFoodLevel());
        backup.addProperty("saturation", player.getFoodData().getSaturationLevel());
        backup.addProperty("experienceLevel", player.experienceLevel);
        backup.addProperty("totalExperience", player.totalExperience);
        backup.addProperty("experienceProgress", player.experienceProgress);
        backup.addProperty("gameMode", player.gameMode().getName());
        backup.addProperty("selectedSlot", player.getInventory().getSelectedSlot());
        backup.add("inventory", inventoryJson(player.getInventory(), server));
        try {
            Files.createDirectories(backupsDir());
            Files.writeString(path, GSON.toJson(backup));
            JsonObject ref = new JsonObject();
            ref.addProperty("path", path.toString());
            ref.addProperty("playerName", player.getName().getString());
            ref.addProperty("savedAt", stringOr(backup, "savedAt", ""));
            ref.addProperty("restored", false);
            quest.add("playerBackup", ref);
            return actionResult("backup_player", path.toString(), true, "saved");
        } catch (IOException e) {
            return actionResult("backup_player", path.toString(), false, e.getMessage());
        }
    }

    private static Map<String, Object> restorePlayerBackup(JsonObject quest, MinecraftServer server) {
        ServerPlayer player = targetPlayer(quest, server);
        if (player == null) return actionResult("restore_player", learnerPlayerName(quest), false, "player-offline");
        JsonObject ref = quest.has("playerBackup") && quest.get("playerBackup").isJsonObject()
            ? quest.getAsJsonObject("playerBackup")
            : null;
        if (ref == null) return actionResult("restore_player", learnerPlayerName(quest), false, "no-backup");
        String pathText = stringOr(ref, "path", "");
        if (pathText.isBlank()) return actionResult("restore_player", learnerPlayerName(quest), false, "no-backup-path");
        Path path = Path.of(pathText);
        if (!Files.isRegularFile(path)) return actionResult("restore_player", pathText, false, "backup-file-missing");
        try {
            JsonObject backup = JsonParser.parseString(Files.readString(path)).getAsJsonObject();
            restoreInventory(player, backup.getAsJsonArray("inventory"), server);
            player.getInventory().setSelectedSlot(intOr(backup, "selectedSlot", player.getInventory().getSelectedSlot()));
            if (backup.has("health")) player.setHealth((float) doubleOr(backup, "health", player.getHealth()));
            if (backup.has("food")) player.getFoodData().setFoodLevel(intOr(backup, "food", player.getFoodData().getFoodLevel()));
            if (backup.has("saturation")) player.getFoodData().setSaturation((float) doubleOr(backup, "saturation", player.getFoodData().getSaturationLevel()));
            player.experienceLevel = intOr(backup, "experienceLevel", player.experienceLevel);
            player.totalExperience = intOr(backup, "totalExperience", player.totalExperience);
            player.experienceProgress = (float) doubleOr(backup, "experienceProgress", player.experienceProgress);
            if (backup.has("gameMode")) {
                player.setGameMode(GameType.byName(stringOr(backup, "gameMode", player.gameMode().getName()), player.gameMode()));
            }
            JsonObject loc = backup.getAsJsonObject("location");
            ServerLevel level = levelForLocation(loc, server);
            if (level != null) {
                player.teleportTo(
                    level,
                    doubleOr(loc, "x", player.getX()),
                    doubleOr(loc, "y", player.getY()),
                    doubleOr(loc, "z", player.getZ()),
                    Set.of(),
                    (float) doubleOr(loc, "yaw", player.getYRot()),
                    (float) doubleOr(loc, "pitch", player.getXRot()),
                    true
                );
            }
            ref.addProperty("restored", true);
            ref.addProperty("restoredAt", OffsetDateTime.now().toString());
            return actionResult("restore_player", pathText, true, "restored");
        } catch (Exception e) {
            return actionResult("restore_player", pathText, false, e.getMessage());
        }
    }

    private static JsonObject playerLocationJson(ServerPlayer player) {
        JsonObject loc = new JsonObject();
        loc.addProperty("x", player.getX());
        loc.addProperty("y", player.getY());
        loc.addProperty("z", player.getZ());
        loc.addProperty("yaw", player.getYRot());
        loc.addProperty("pitch", player.getXRot());
        loc.addProperty("dimension", player.level().dimension().identifier().toString());
        return loc;
    }

    private static JsonArray inventoryJson(Inventory inventory, MinecraftServer server) {
        JsonArray arr = new JsonArray();
        for (int slot = 0; slot < inventory.getContainerSize(); slot++) {
            ItemStack stack = inventory.getItem(slot);
            if (stack == null || stack.isEmpty()) continue;
            JsonObject row = new JsonObject();
            row.addProperty("slot", slot);
            row.add("stack", itemStackJson(stack, server));
            arr.add(row);
        }
        return arr;
    }

    private static JsonElement itemStackJson(ItemStack stack, MinecraftServer server) {
        if (server == null) return JsonNull.INSTANCE;
        DataResult<JsonElement> result = ItemStack.CODEC.encodeStart(
            server.registryAccess().createSerializationContext(JsonOps.INSTANCE),
            stack
        );
        return result.resultOrPartial(msg -> MathQuestMod.LOGGER.warn("[MathQuest] Item backup encode failed: {}", msg))
            .orElse(JsonNull.INSTANCE);
    }

    private static ItemStack itemStackFromJson(JsonElement json, MinecraftServer server) {
        if (server == null || json == null || json.isJsonNull()) return ItemStack.EMPTY;
        DataResult<ItemStack> result = ItemStack.CODEC.parse(
            server.registryAccess().createSerializationContext(JsonOps.INSTANCE),
            json
        );
        return result.resultOrPartial(msg -> MathQuestMod.LOGGER.warn("[MathQuest] Item backup decode failed: {}", msg))
            .orElse(ItemStack.EMPTY);
    }

    private static void restoreInventory(ServerPlayer player, JsonArray saved, MinecraftServer server) {
        Inventory inventory = player.getInventory();
        inventory.clearContent();
        if (saved != null) {
            for (JsonElement el : saved) {
                if (!el.isJsonObject()) continue;
                JsonObject row = el.getAsJsonObject();
                int slot = intOr(row, "slot", -1);
                if (slot < 0 || slot >= inventory.getContainerSize()) continue;
                ItemStack stack = itemStackFromJson(row.get("stack"), server);
                if (!stack.isEmpty()) inventory.setItem(slot, stack);
            }
        }
        inventory.setChanged();
        player.inventoryMenu.broadcastChanges();
    }

    private static void updateMechanicStatus(JsonObject quest, String mechanicId, String action) {
        if (mechanicId.isBlank()) return;
        for (JsonElement el : quest.getAsJsonArray("mechanics")) {
            JsonObject m = el.getAsJsonObject();
            if (!mechanicId.equals(stringOr(m, "id", ""))) continue;
            switch (action) {
                case "force-complete-mechanic" -> m.addProperty("status", "cleared");
                case "force-respawn-mechanic" -> m.addProperty("status", "ready");
                case "open-mechanic-quiz" -> m.addProperty("status", "quiz_opened_by_gm");
                default -> {}
            }
        }
    }

    private static JsonObject mechanicById(JsonObject quest, String mechanicId) {
        if (mechanicId == null || mechanicId.isBlank()) return null;
        for (JsonElement el : quest.getAsJsonArray("mechanics")) {
            JsonObject m = el.getAsJsonObject();
            if (mechanicId.equals(stringOr(m, "id", ""))) return m;
        }
        return null;
    }

    private static boolean openQuestQuizForLearner(JsonObject quest, MinecraftServer server) {
        if (server == null) return false;
        String playerName = learnerPlayerName(quest);
        for (ServerPlayer player : server.getPlayerList().getPlayers()) {
            if (player.getName().getString().equalsIgnoreCase(playerName)) {
                ServerPlayNetworking.send(player, QuizPayloadBuilder.create(player));
                return true;
            }
        }
        return false;
    }

    private static boolean startQuestQuizForLearner(JsonObject quest, MinecraftServer server) {
        if (server == null) return false;
        String playerName = learnerPlayerName(quest);
        for (ServerPlayer player : server.getPlayerList().getPlayers()) {
            if (player.getName().getString().equalsIgnoreCase(playerName)) {
                ServerPlayNetworking.send(player, QuizPayloadBuilder.createDirect(player));
                return true;
            }
        }
        return false;
    }

    private static boolean openQuestInvitationForLearner(JsonObject quest, MinecraftServer server) {
        return openQuestInvitationForLearner(quest, server, QUEST_INVITATION_CHAT, QUEST_INVITATION_TITLE);
    }

    private static boolean openM2QuizInvitationForLearner(JsonObject quest, MinecraftServer server) {
        return openQuestInvitationForLearner(quest, server, M2_INVITATION_CHAT, M2_INVITATION_TITLE);
    }

    private static boolean openQuestInvitationForLearner(
        JsonObject quest,
        MinecraftServer server,
        String message,
        String title
    ) {
        if (server == null) return false;
        String playerName = learnerPlayerName(quest);
        for (ServerPlayer player : server.getPlayerList().getPlayers()) {
            if (player.getName().getString().equalsIgnoreCase(playerName)) {
                var quizPayload = QuizPayloadBuilder.createDirect(player);
                ServerPlayNetworking.send(player, new QuestInvitationPayload(
                    message,
                    title,
                    quizPayload.operation(),
                    quizPayload.minNumber(),
                    quizPayload.maxNumber(),
                    quizPayload.problemsPerQuiz(),
                    quizPayload.problemsJson(),
                    quizPayload.rewardsJson(),
                    quizPayload.rewardMode(),
                    quizPayload.quizType(),
                    quizPayload.optionsJson()
                ));
                return true;
            }
        }
        return false;
    }

    private static List<Map<String, Object>> scheduleInvitationRetry(
        JsonObject quest,
        JsonObject world,
        MinecraftServer server,
        String milestoneId
    ) {
        return runActionLines(jsonArray(invitationRetryActionLines()), quest, world, server, milestoneId);
    }

    static List<String> invitationRetryActionLines() {
        return List.of(
            "wait " + QUEST_INVITATION_RETRY_SECONDS,
            "chat " + QUEST_INVITATION_CHAT,
            "open_quiz_invitation"
        );
    }

    private static void cancelPendingScheduledActionsFor(String playerName) {
        if (playerName == null || playerName.isBlank()) return;
        SCHEDULED_ACTIONS.removeIf(action -> action.playerName().equalsIgnoreCase(playerName));
    }

    private static int respawnMechanic(JsonObject mechanic, MinecraftServer server) {
        String type = stringOr(mechanic, "type", "");
        if (type.startsWith("combat")) return spawnMechanicEntity(mechanic, server);
        if (type.startsWith("explore")) return placeMechanicBlock(mechanic, server, false);
        return 0;
    }

    private static int clearMechanic(JsonObject mechanic, MinecraftServer server) {
        String type = stringOr(mechanic, "type", "");
        if (type.startsWith("combat")) return killMechanicEntities(mechanic, server);
        if (type.startsWith("explore")) return placeMechanicBlock(mechanic, server, true);
        return 0;
    }

    private static int spawnMechanicEntity(JsonObject mechanic, MinecraftServer server) {
        ServerLevel level = mechanicLevel(mechanic, server);
        BlockPos pos = mechanicPos(mechanic, server);
        EntityType<?> type = entityType(stringOr(mechanic, "entityOrBlock", "minecraft:cave_spider"));
        if (level == null || pos == null || type == null || type == EntityType.PLAYER || !type.canSummon()) return 0;
        return type.spawn(level, pos, EntitySpawnReason.COMMAND) == null ? 0 : 1;
    }

    private static int killMechanicEntities(JsonObject mechanic, MinecraftServer server) {
        ServerLevel level = mechanicLevel(mechanic, server);
        BlockPos pos = mechanicPos(mechanic, server);
        EntityType<?> type = entityType(stringOr(mechanic, "entityOrBlock", "minecraft:cave_spider"));
        if (level == null || pos == null || type == null || type == EntityType.PLAYER) return 0;
        int radius = Math.max(4, intOr(mechanic, "clearRadiusBlocks", 12));
        AABB box = new AABB(
            pos.getX() - radius, pos.getY() - radius, pos.getZ() - radius,
            pos.getX() + radius, pos.getY() + radius, pos.getZ() + radius
        );
        int removed = 0;
        for (Entity entity : level.getEntities((Entity) null, box, entity -> entity.getType() == type)) {
            entity.discard();
            removed++;
        }
        return removed;
    }

    private static int placeMechanicBlock(JsonObject mechanic, MinecraftServer server, boolean clear) {
        ServerLevel level = mechanicLevel(mechanic, server);
        BlockPos pos = mechanicPos(mechanic, server);
        if (level == null || pos == null) return 0;
        if (clear) {
            level.setBlock(pos, Blocks.AIR.defaultBlockState(), 3);
            return 1;
        }
        Block block = block(stringOr(mechanic, "entityOrBlock", "minecraft:stone_button"));
        if (block == null) return 0;
        level.setBlock(pos, block.defaultBlockState(), 3);
        return 1;
    }

    private static ServerLevel mechanicLevel(JsonObject mechanic, MinecraftServer server) {
        if (server == null) return null;
        JsonObject location = mechanicLocation(mechanic, server);
        String dimension = location == null ? "minecraft:overworld" : stringOr(location, "dimension", "minecraft:overworld");
        try {
            ResourceKey<Level> key = ResourceKey.create(Registries.DIMENSION, Identifier.parse(normalizeMinecraftId(dimension)));
            ServerLevel level = server.getLevel(key);
            return level != null ? level : server.overworld();
        } catch (Exception e) {
            return server.overworld();
        }
    }

    private static BlockPos mechanicPos(JsonObject mechanic, MinecraftServer server) {
        JsonObject location = mechanicLocation(mechanic, server);
        if (location == null) return null;
        if (missingCoords(location)) return null;
        return new BlockPos(
            intOr(location, "x", 0),
            intOr(location, "y", 64),
            intOr(location, "z", 0)
        );
    }

    private static JsonObject mechanicLocation(JsonObject mechanic, MinecraftServer server) {
        JsonObject world = readWorld(server);
        JsonObject locations = world.getAsJsonObject("locations");
        String locationId = canonicalMilestoneId(stringOr(mechanic, "locationId", "m1_cave_start"));
        if (locations.has(locationId) && locations.get(locationId).isJsonObject()) {
            return locations.getAsJsonObject(locationId);
        }
        return world.getAsJsonObject("spawn");
    }

    private static EntityType<?> entityType(String raw) {
        try {
            Identifier id = Identifier.parse(normalizeMinecraftId(raw));
            if (!BuiltInRegistries.ENTITY_TYPE.containsKey(id)) return null;
            return BuiltInRegistries.ENTITY_TYPE.getValue(id);
        } catch (Exception e) {
            return null;
        }
    }

    private static Block block(String raw) {
        try {
            Identifier id = Identifier.parse(normalizeMinecraftId(raw));
            if (!BuiltInRegistries.BLOCK.containsKey(id)) return null;
            return BuiltInRegistries.BLOCK.getValue(id);
        } catch (Exception e) {
            return null;
        }
    }

    private static String normalizeMinecraftId(String raw) {
        if (raw == null || raw.isBlank()) return "minecraft:air";
        String s = raw.trim().toLowerCase(Locale.ROOT).replace('-', '_').replace(' ', '_');
        return s.contains(":") ? s : "minecraft:" + s;
    }

    private static String resolveRealName(String playerName, Map<String, String> realNames) {
        if (playerName == null) return "";
        if (realNames != null) {
            String direct = realNames.get(playerName.toLowerCase(Locale.ROOT));
            if (direct != null) return direct;
        }
        return MathQuestMod.CONFIG.resolveRealName(playerName);
    }

    private static String learnerPlayerName(JsonObject quest) {
        JsonObject learner = quest.getAsJsonObject("learner");
        return cleanName(stringOr(learner, "playerName", DEFAULT_PLAYER_NAME));
    }

    private static String learnerRealName(JsonObject quest) {
        JsonObject learner = quest.getAsJsonObject("learner");
        return resolveLearnerRealName(learnerPlayerName(quest), stringOr(learner, "realName", ""));
    }

    private static String resolveLearnerRealName(String playerName, String requestedRealName) {
        String cleanedRequested = cleanName(requestedRealName);
        if (!cleanedRequested.isBlank()) return cleanedRequested;
        String cleanedPlayer = cleanName(playerName);
        if (cleanedPlayer.isBlank()) return "unknown";
        return MathQuestMod.CONFIG.resolveRealName(cleanedPlayer);
    }

    private static String cleanName(String raw) {
        return raw == null ? "" : raw.trim();
    }

    private static boolean isAddition(String op) {
        if (op == null) return false;
        String s = op.trim().toLowerCase(Locale.ROOT);
        return "+".equals(s) || "addition".equals(s) || "add".equals(s);
    }

    private static int intAt(JsonObject obj, String child, String key, int fallback) {
        if (!obj.has(child) || !obj.get(child).isJsonObject()) return fallback;
        return intOr(obj.getAsJsonObject(child), key, fallback);
    }

    private static double doubleAt(JsonObject obj, String child, String key, double fallback) {
        if (!obj.has(child) || !obj.get(child).isJsonObject()) return fallback;
        JsonObject c = obj.getAsJsonObject(child);
        return c.has(key) && !c.get(key).isJsonNull() ? c.get(key).getAsDouble() : fallback;
    }

    private static int intOr(JsonObject obj, String key, int fallback) {
        return obj.has(key) && !obj.get(key).isJsonNull() ? obj.get(key).getAsInt() : fallback;
    }

    private static double doubleOr(JsonObject obj, String key, double fallback) {
        return obj != null && obj.has(key) && !obj.get(key).isJsonNull() ? obj.get(key).getAsDouble() : fallback;
    }

    private static boolean boolOr(JsonObject obj, String key, boolean fallback) {
        return obj.has(key) && !obj.get(key).isJsonNull() ? obj.get(key).getAsBoolean() : fallback;
    }

    private static String stringOr(JsonObject obj, String key, String fallback) {
        return obj != null && obj.has(key) && !obj.get(key).isJsonNull() ? obj.get(key).getAsString() : fallback;
    }

    private static Object jsonToObject(JsonElement el) {
        return GSON.fromJson(el, Object.class);
    }

    private static List<Fact> facts(int fixed, int start, int end) {
        List<Fact> out = new ArrayList<>();
        for (int n = start; n <= end; n++) out.add(new Fact(Math.min(fixed, n), Math.max(fixed, n)));
        return out;
    }

    private static List<Fact> facts(String... labels) {
        List<Fact> out = new ArrayList<>();
        for (String label : labels) {
            String[] parts = label.split("\\+");
            int a = Integer.parseInt(parts[0]);
            int b = Integer.parseInt(parts[1]);
            out.add(new Fact(Math.min(a, b), Math.max(a, b)));
        }
        return out;
    }

    private static List<Fact> doubles(int start, int end) {
        List<Fact> out = new ArrayList<>();
        for (int n = start; n <= end; n++) out.add(new Fact(n, n));
        return out;
    }

    @SafeVarargs
    private static List<Fact> addAll(List<Fact>... lists) {
        List<Fact> out = new ArrayList<>();
        for (List<Fact> list : lists) out.addAll(list);
        return out;
    }

    private static List<Fact> repeat(List<Fact> facts, int minCount) {
        List<Fact> out = new ArrayList<>();
        for (int i = 0; i < minCount && !facts.isEmpty(); i++) out.add(facts.get(i % facts.size()));
        return out;
    }

    private static Set<Fact> allFacts() {
        Set<Fact> all = new LinkedHashSet<>();
        all.addAll(ADD_ZERO);
        all.addAll(ADD_ONE);
        all.addAll(ADD_TWO);
        all.addAll(DOUBLES);
        all.addAll(TOUGH_21);
        return all;
    }

    private record Fact(int a, int b) {
        String key() {
            return a + "+" + b;
        }
        String label() {
            return a + " + " + b;
        }
        Fact randomOrientation() {
            if (a == b || RANDOM.nextBoolean()) return this;
            return new Fact(b, a);
        }
    }

    private static final class FactStats {
        private final int greenMs;
        private final double minAccuracy;
        int attempts;
        int correct;
        int fastCorrect;

        FactStats(int greenMs, double minAccuracy) {
            this.greenMs = greenMs;
            this.minAccuracy = minAccuracy;
        }

        void record(boolean isCorrect, long responseTimeMs) {
            attempts++;
            if (isCorrect) {
                correct++;
                if (responseTimeMs > 0 && responseTimeMs <= greenMs) fastCorrect++;
            }
        }

        boolean fluent() {
            if (attempts < 2 || fastCorrect < 2) return false;
            return ((double) correct / attempts) >= minAccuracy;
        }
    }

    private record QuestProgress(Map<String, FactStats> stats, Map<String, QuestQuizDefinitions.OrientedStats> orientedStats) {
        FactStats statsFor(Fact fact) {
            return stats.computeIfAbsent(fact.key(), key -> new FactStats(3500, 0.90));
        }
        QuestQuizDefinitions.OrientedStats orientedStatsFor(QuestQuizDefinitions.ProblemSpec problem) {
            if (orientedStats == null) return new QuestQuizDefinitions.OrientedStats(0, 0, 0, 0);
            return orientedStats.getOrDefault(problem.key(), new QuestQuizDefinitions.OrientedStats(0, 0, 0, 0));
        }
        int fluentCount(List<Fact> facts) {
            int count = 0;
            for (Fact fact : facts) {
                if (statsFor(fact).fluent()) count++;
            }
            return count;
        }
    }
}
