package com.kidgames.mathquest.forge;

import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.forge.entity.MathQuestNerdDespawnForge;
import com.kidgames.mathquest.forge.net.MathQuestNetworkForge;
import com.kidgames.mathquest.forge.platform.ForgePlatformPlayers;
import com.kidgames.mathquest.server.OpenQuizPayloadBuilder;
import com.kidgames.mathquest.server.QuizDeliveryPreview;
import com.kidgames.mathquest.util.MathQuestDurationFormat;
import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.IntegerArgumentType;
import com.mojang.brigadier.arguments.StringArgumentType;
import net.minecraft.ChatFormatting;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

public final class MathQuestServerCommandsForge {
    private MathQuestServerCommandsForge() {}

    public static void register(CommandDispatcher<CommandSourceStack> dispatcher) {
        TpCreditCommandsForge.register(dispatcher);
        dispatcher.register(Commands.literal("mathquest")
            .requires(source -> source.hasPermission(2))
            .then(Commands.literal("interval")
                .then(Commands.argument("seconds", IntegerArgumentType.integer(5))
                    .executes(ctx -> setInterval(ctx.getSource(), IntegerArgumentType.getInteger(ctx, "seconds")))))
            .then(Commands.literal("problems")
                .then(Commands.argument("count", IntegerArgumentType.integer(1, 50))
                    .executes(ctx -> setProblems(ctx.getSource(), IntegerArgumentType.getInteger(ctx, "count")))))
            .then(Commands.literal("mode")
                .then(Commands.literal("popup").executes(ctx -> setMode(ctx.getSource(), "popup")))
                .then(Commands.literal("npc").executes(ctx -> setMode(ctx.getSource(), "npc"))))
            .then(Commands.literal("operation")
                .then(Commands.literal("addition").executes(ctx -> setGlobalOperation(ctx.getSource(), "addition")))
                .then(Commands.literal("subtraction").executes(ctx -> setGlobalOperation(ctx.getSource(), "subtraction")))
                .then(Commands.literal("multiplication").executes(ctx -> setGlobalOperation(ctx.getSource(), "multiplication")))
                .then(Commands.literal("exponentiation").executes(ctx -> setGlobalOperation(ctx.getSource(), "exponentiation"))))
            .then(Commands.literal("range")
                .then(Commands.argument("min", IntegerArgumentType.integer())
                    .then(Commands.argument("max", IntegerArgumentType.integer())
                        .executes(ctx -> setGlobalRange(ctx.getSource(),
                            IntegerArgumentType.getInteger(ctx, "min"),
                            IntegerArgumentType.getInteger(ctx, "max"))))))
            .then(Commands.literal("player")
                .then(Commands.argument("name", StringArgumentType.string())
                    .then(Commands.literal("operation")
                        .then(Commands.literal("addition").executes(ctx -> setPlayerOperation(ctx.getSource(),
                            StringArgumentType.getString(ctx, "name"), "addition")))
                        .then(Commands.literal("subtraction").executes(ctx -> setPlayerOperation(ctx.getSource(),
                            StringArgumentType.getString(ctx, "name"), "subtraction")))
                        .then(Commands.literal("multiplication").executes(ctx -> setPlayerOperation(ctx.getSource(),
                            StringArgumentType.getString(ctx, "name"), "multiplication")))
                        .then(Commands.literal("exponentiation").executes(ctx -> setPlayerOperation(ctx.getSource(),
                            StringArgumentType.getString(ctx, "name"), "exponentiation"))))
                    .then(Commands.literal("range")
                        .then(Commands.argument("min", IntegerArgumentType.integer())
                            .then(Commands.argument("max", IntegerArgumentType.integer())
                                .executes(ctx -> setPlayerRange(ctx.getSource(),
                                    StringArgumentType.getString(ctx, "name"),
                                    IntegerArgumentType.getInteger(ctx, "min"),
                                    IntegerArgumentType.getInteger(ctx, "max"))))))
                    .then(Commands.literal("clear")
                        .executes(ctx -> clearPlayerPreset(ctx.getSource(), StringArgumentType.getString(ctx, "name"))))))
            .then(Commands.literal("npcspawn")
                .then(Commands.literal("all").executes(ctx -> setNpcSpawnTarget(ctx.getSource(), "all", null)))
                .then(Commands.literal("random").executes(ctx -> setNpcSpawnTarget(ctx.getSource(), "random", null)))
                .then(Commands.literal("only")
                    .then(Commands.argument("name", StringArgumentType.string())
                        .executes(ctx -> setNpcSpawnTarget(
                            ctx.getSource(),
                            "one",
                            StringArgumentType.getString(ctx, "name"))))))
            .then(Commands.literal("group")
                .then(Commands.literal("clear").executes(ctx -> clearRewardGroup(ctx.getSource())))
                .then(Commands.argument("name", StringArgumentType.string())
                    .executes(ctx -> setRewardGroup(ctx.getSource(), StringArgumentType.getString(ctx, "name")))))
            .then(Commands.literal("start")
                .executes(ctx -> startQuiz(ctx.getSource()))
                .then(Commands.literal("all").executes(ctx -> startQuizAll(ctx.getSource())))
                .then(Commands.argument("player", StringArgumentType.word())
                    .executes(ctx -> startQuizPlayer(ctx.getSource(), StringArgumentType.getString(ctx, "player")))))
            .then(Commands.literal("status").executes(ctx -> showStatus(ctx.getSource())))
            .then(Commands.literal("enable").executes(ctx -> setEnabled(ctx.getSource(), true)))
            .then(Commands.literal("disable").executes(ctx -> setEnabled(ctx.getSource(), false)))
            .then(Commands.literal("vanishnerds").executes(ctx -> vanishNerds(ctx.getSource())))
        );
    }

    private static int setNpcSpawnTarget(CommandSourceStack source, String modeKey, String targetName) {
        String mode = MathQuestConfig.normalizeNpcSpawnTargetMode(modeKey);
        MathQuestConfig.INSTANCE.npcSpawnTargetMode = mode;
        if ("one".equals(mode)) {
            if (targetName == null || targetName.isBlank()) {
                source.sendFailure(Component.literal("[MathQuest] Use /mathquest npcspawn only <playerName>."));
                return 0;
            }
            MathQuestConfig.INSTANCE.npcSpawnTargetPlayer = targetName.toLowerCase(Locale.ROOT);
        } else {
            MathQuestConfig.INSTANCE.npcSpawnTargetPlayer = null;
        }
        MathQuestConfig.INSTANCE.save();
        MathQuestForge.getNerdSpawner().resetTimer();

        String desc = switch (mode) {
            case "random" -> "one random online player per interval";
            case "one" -> "only " + MathQuestConfig.INSTANCE.npcSpawnTargetPlayer;
            default -> "every online player (each gets a spawn attempt)";
        };
        source.sendSuccess(() -> gold("NPC auto-spawn: " + desc), false);
        return 1;
    }

    private static int setProblems(CommandSourceStack source, int count) {
        MathQuestConfig.INSTANCE.problemsPerQuiz = count;
        MathQuestConfig.INSTANCE.save();
        source.sendSuccess(() -> gold("Problems per quiz set to " + count + "."), false);
        return 1;
    }

    private static int setInterval(CommandSourceStack source, int seconds) {
        MathQuestConfig.INSTANCE.quizIntervalSeconds = seconds;
        MathQuestConfig.INSTANCE.save();
        MathQuestForge.getNerdSpawner().resetTimer();
        source.sendSuccess(() -> gold("Quiz interval set to " + MathQuestDurationFormat.forStatus(seconds) + ". Timer reset."), false);
        return 1;
    }

    private static int setMode(CommandSourceStack source, String mode) {
        MathQuestConfig.INSTANCE.quizMode = mode;
        MathQuestConfig.INSTANCE.save();
        if ("npc".equals(mode)) {
            MathQuestForge.getNerdSpawner().resetTimer();
        }
        String modeDesc = "popup".equals(mode) ? "Popup (timed screen overlay)" : "NPC (Wandering Nerd)";
        source.sendSuccess(() -> gold("Quiz mode set to: " + modeDesc), false);
        return 1;
    }

    private static int setGlobalOperation(CommandSourceStack source, String op) {
        MathQuestConfig.INSTANCE.operation = MathQuestConfig.normalizeOperation(op);
        MathQuestConfig.INSTANCE.save();
        source.sendSuccess(() -> gold("Default operation set to " + MathQuestConfig.INSTANCE.operation + "."), false);
        return 1;
    }

    private static int setGlobalRange(CommandSourceStack source, int min, int max) {
        if (min > max) {
            int t = min;
            min = max;
            max = t;
        }
        MathQuestConfig.INSTANCE.minNumber = min;
        MathQuestConfig.INSTANCE.maxNumber = max;
        MathQuestConfig.INSTANCE.save();
        int fMin = min;
        int fMax = max;
        source.sendSuccess(() -> gold("Default number range set to " + fMin + " - " + fMax + "."), false);
        return 1;
    }

    private static int setPlayerOperation(CommandSourceStack source, String name, String op) {
        ensurePlayerPresets();
        String key = name.toLowerCase(Locale.ROOT);
        MathQuestConfig.PlayerQuizPreset preset = MathQuestConfig.INSTANCE.playerPresets.computeIfAbsent(
            key, k -> new MathQuestConfig.PlayerQuizPreset());
        preset.operation = MathQuestConfig.normalizeOperation(op);
        MathQuestConfig.INSTANCE.save();
        source.sendSuccess(() -> gold("Preset for \"" + name + "\": operation = " + preset.operation + "."), false);
        return 1;
    }

    private static int setPlayerRange(CommandSourceStack source, String name, int min, int max) {
        if (min > max) {
            int t = min;
            min = max;
            max = t;
        }
        ensurePlayerPresets();
        String key = name.toLowerCase(Locale.ROOT);
        MathQuestConfig.PlayerQuizPreset preset = MathQuestConfig.INSTANCE.playerPresets.computeIfAbsent(
            key, k -> new MathQuestConfig.PlayerQuizPreset());
        preset.minNumber = min;
        preset.maxNumber = max;
        MathQuestConfig.INSTANCE.save();
        int fMin = min;
        int fMax = max;
        source.sendSuccess(() -> gold("Preset for \"" + name + "\": range = " + fMin + " - " + fMax + "."), false);
        return 1;
    }

    private static int clearPlayerPreset(CommandSourceStack source, String name) {
        ensurePlayerPresets();
        String key = name.toLowerCase(Locale.ROOT);
        if (MathQuestConfig.INSTANCE.playerPresets.remove(key) != null) {
            MathQuestConfig.INSTANCE.save();
            source.sendSuccess(() -> gold("Removed preset for \"" + name + "\" (uses global defaults)."), false);
        } else {
            source.sendSuccess(() -> gold("No preset found for \"" + name + "\"."), false);
        }
        return 1;
    }

    private static int setRewardGroup(CommandSourceStack source, String name) {
        ensureRewardGroups();
        String key = MathQuestConfig.normalizeGroupName(name);
        if (key.isEmpty()) {
            source.sendFailure(Component.literal("[MathQuest] Group name cannot be empty."));
            return 0;
        }
        if (!MathQuestConfig.INSTANCE.rewardGroups.containsKey(key)) {
            source.sendFailure(Component.literal("[MathQuest] Unknown reward group: " + key));
            return 0;
        }
        MathQuestConfig.INSTANCE.rewardGroup = key;
        MathQuestConfig.INSTANCE.save();
        source.sendSuccess(() -> gold("Active reward group set to \"" + key + "\"."), false);
        return 1;
    }

    private static int clearRewardGroup(CommandSourceStack source) {
        MathQuestConfig.INSTANCE.rewardGroup = null;
        MathQuestConfig.INSTANCE.save();
        source.sendSuccess(() -> gold("Using flat reward list. Set a group with /mathquest group <name>."), false);
        return 1;
    }

    private static int startQuiz(CommandSourceStack source) {
        ServerPlayer player = source.getPlayer();
        if (player == null) {
            source.sendFailure(Component.literal("[MathQuest] Console/RCON: use /mathquest start <player>."));
            return 0;
        }
        if ("npc".equals(MathQuestConfig.INSTANCE.quizMode)) {
            ServerLevel world = source.getServer().overworld();
            MathQuestForge.getNerdSpawner().forceSpawn(world, player);
            source.sendSuccess(() -> gold("Spawning the Wandering Nerd nearby..."), false);
        } else {
            openQuizFor(player);
            source.sendSuccess(() -> gold("Opening quiz..."), false);
        }
        return 1;
    }

    private static int startQuizPlayer(CommandSourceStack source, String playerName) {
        ServerPlayer target = source.getServer().getPlayerList().getPlayerByName(playerName);
        if (target == null) {
            source.sendFailure(Component.literal("[MathQuest] Player \"" + playerName + "\" is not online."));
            return 0;
        }
        if ("npc".equals(MathQuestConfig.INSTANCE.quizMode)) {
            ServerLevel world = source.getServer().overworld();
            MathQuestForge.getNerdSpawner().forceSpawn(world, target);
            source.sendSuccess(() -> gold("Spawning the Wandering Nerd near " + target.getName().getString() + "..."), false);
        } else {
            openQuizFor(target);
            source.sendSuccess(() -> gold("Opening quiz for " + target.getName().getString() + "..."), false);
        }
        return 1;
    }

    private static int startQuizAll(CommandSourceStack source) {
        List<ServerPlayer> players = source.getServer().getPlayerList().getPlayers();
        if (players.isEmpty()) {
            source.sendFailure(Component.literal("[MathQuest] No players online."));
            return 0;
        }
        if ("npc".equals(MathQuestConfig.INSTANCE.quizMode)) {
            ServerLevel world = source.getServer().overworld();
            for (ServerPlayer player : players) {
                MathQuestForge.getNerdSpawner().forceSpawn(world, player);
            }
            source.sendSuccess(() -> gold("Spawning the Wandering Nerd near " + players.size() + " online player(s)..."), false);
        } else {
            for (ServerPlayer player : players) {
                openQuizFor(player);
            }
            source.sendSuccess(() -> gold("Opening quiz for all " + players.size() + " online player(s)..."), false);
        }
        return players.size();
    }

    private static int vanishNerds(CommandSourceStack source) {
        ServerLevel world = source.getServer().overworld();
        int count = MathQuestNerdDespawnForge.vanishAllInOverworld(world);
        int fCount = count;
        source.sendSuccess(() -> gold("Removed " + fCount + " Wandering Nerd" + (fCount == 1 ? "" : "s") + " from the overworld."), false);
        return count;
    }

    private static void openQuizFor(ServerPlayer player) {
        ForgePlatformPlayers.fromServerPlayer(player);
        var data = OpenQuizPayloadBuilder.create(player.getName().getString());
        MathQuestNetworkForge.sendOpenQuiz(player, data);
    }

    private static int setEnabled(CommandSourceStack source, boolean enabled) {
        MathQuestConfig.INSTANCE.enabled = enabled;
        MathQuestConfig.INSTANCE.save();
        source.sendSuccess(() -> gold(enabled ? "Quizzes enabled!" : "Quizzes disabled."), false);
        return 1;
    }

    private static int showStatus(CommandSourceStack source) {
        MathQuestConfig config = MathQuestConfig.INSTANCE;
        source.sendSuccess(() -> Component.literal("--- MathQuest Status ---").withStyle(ChatFormatting.GOLD), false);
        source.sendSuccess(() -> line("Enabled", config.enabled ? "Yes" : "No"), false);
        source.sendSuccess(() -> line("Mode", "popup".equals(config.quizMode) ? "Popup" : "NPC"), false);
        source.sendSuccess(() -> line("Interval", MathQuestDurationFormat.forStatus(config.quizIntervalSeconds)), false);
        appendNextQuizStatus(source);
        source.sendSuccess(() -> line("Default operation", config.operation), false);
        source.sendSuccess(() -> line("Default range", config.minNumber + " - " + config.maxNumber), false);
        if ("npc".equals(config.quizMode)) {
            source.sendSuccess(() -> line("NPC spawn radius", config.npcSpawnRadiusBlocks + " blocks"), false);
            source.sendSuccess(() -> line("NPC despawn", config.npcDespawnSeconds + " seconds"), false);
            String targetMode = MathQuestConfig.normalizeNpcSpawnTargetMode(config.npcSpawnTargetMode);
            String targetDesc = switch (targetMode) {
                case "random" -> "one random online player per interval";
                case "one" -> "only " + (config.npcSpawnTargetPlayer != null ? config.npcSpawnTargetPlayer : "(not set)");
                default -> "every online player";
            };
            source.sendSuccess(() -> line("NPC spawn target", targetDesc), false);
        }
        if (config.playerPresets != null && !config.playerPresets.isEmpty()) {
            source.sendSuccess(() -> Component.literal("  Player presets:").withStyle(ChatFormatting.GRAY), false);
            for (Map.Entry<String, MathQuestConfig.PlayerQuizPreset> e : config.playerPresets.entrySet()) {
                String line = "    - " + e.getKey();
                source.sendSuccess(() -> Component.literal(line).withStyle(ChatFormatting.AQUA), false);
            }
        }
        source.sendSuccess(() -> line("Online players", String.valueOf(source.getServer().getPlayerCount())), false);
        return 1;
    }

    private static void appendNextQuizStatus(CommandSourceStack source) {
        ServerPlayer player = source.getPlayer();
        if (player == null) return;
        for (QuizDeliveryPreview.StatusLine line : QuizDeliveryPreview.statusLinesForPlayer(
            player.getName().getString())) {
            ChatFormatting valueColor = line.error() ? ChatFormatting.RED : ChatFormatting.WHITE;
            source.sendSuccess(() -> Component.literal("  " + line.label() + ": ").withStyle(ChatFormatting.GRAY)
                .append(Component.literal(line.value()).withStyle(valueColor)), false);
        }
    }

    private static void ensurePlayerPresets() {
        if (MathQuestConfig.INSTANCE.playerPresets == null) {
            MathQuestConfig.INSTANCE.playerPresets = new LinkedHashMap<>();
        }
    }

    private static void ensureRewardGroups() {
        if (MathQuestConfig.INSTANCE.rewardGroups == null) {
            MathQuestConfig.INSTANCE.rewardGroups = new LinkedHashMap<>();
        }
        MathQuestConfig.ensureJtreeGroup(MathQuestConfig.INSTANCE.rewardGroups);
    }

    private static Component gold(String text) {
        return Component.literal("[MathQuest] ").withStyle(ChatFormatting.GOLD)
            .append(Component.literal(text).withStyle(ChatFormatting.GREEN));
    }

    private static Component line(String label, String value) {
        return Component.literal("  " + label + ": ").withStyle(ChatFormatting.GRAY)
            .append(Component.literal(value).withStyle(ChatFormatting.WHITE));
    }
}
