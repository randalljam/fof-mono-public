package com.kidgames.mathquest;

import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.entity.WanderingNerdEntity;
import com.kidgames.mathquest.network.QuizPayloadBuilder;
import com.kidgames.mathquest.server.QuizDeliveryPreview;
import com.kidgames.mathquest.util.MathQuestDurationFormat;
import com.mojang.brigadier.arguments.IntegerArgumentType;
import com.mojang.brigadier.arguments.StringArgumentType;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.fabricmc.fabric.api.networking.v1.ServerPlayNetworking;
import net.minecraft.ChatFormatting;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.permissions.Permissions;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

public class MathQuestServerCommands {

    public static void register() {
        CommandRegistrationCallback.EVENT.register((dispatcher, registryAccess, environment) -> {
            TpCreditCommands.register(dispatcher);
            dispatcher.register(Commands.literal("mathquest")
                .requires(src -> src.permissions().hasPermission(Permissions.COMMANDS_GAMEMASTER))
                .then(Commands.literal("interval")
                    .then(Commands.argument("seconds", IntegerArgumentType.integer(5))
                        .executes(ctx -> setInterval(ctx.getSource(),
                            IntegerArgumentType.getInteger(ctx, "seconds")))
                    )
                )
                .then(Commands.literal("problems")
                    .then(Commands.argument("count", IntegerArgumentType.integer(1, 50))
                        .executes(ctx -> setProblems(ctx.getSource(),
                            IntegerArgumentType.getInteger(ctx, "count")))
                    )
                )
                .then(Commands.literal("mode")
                    .then(Commands.literal("popup")
                        .executes(ctx -> setMode(ctx.getSource(), "popup")))
                    .then(Commands.literal("npc")
                        .executes(ctx -> setMode(ctx.getSource(), "npc")))
                )
                .then(Commands.literal("operation")
                    .then(Commands.literal("addition")
                        .executes(ctx -> setGlobalOperation(ctx.getSource(), "addition")))
                    .then(Commands.literal("subtraction")
                        .executes(ctx -> setGlobalOperation(ctx.getSource(), "subtraction")))
                    .then(Commands.literal("multiplication")
                        .executes(ctx -> setGlobalOperation(ctx.getSource(), "multiplication")))
                    .then(Commands.literal("exponentiation")
                        .executes(ctx -> setGlobalOperation(ctx.getSource(), "exponentiation")))
                )
                .then(Commands.literal("range")
                    .then(Commands.argument("min", IntegerArgumentType.integer())
                        .then(Commands.argument("max", IntegerArgumentType.integer())
                            .executes(ctx -> setGlobalRange(ctx.getSource(),
                                IntegerArgumentType.getInteger(ctx, "min"),
                                IntegerArgumentType.getInteger(ctx, "max")))
                        )
                    )
                )
                .then(Commands.literal("player")
                    .then(Commands.argument("name", StringArgumentType.string())
                        .then(Commands.literal("operation")
                            .then(Commands.literal("addition")
                                .executes(ctx -> setPlayerOperation(ctx.getSource(),
                                    StringArgumentType.getString(ctx, "name"), "addition")))
                            .then(Commands.literal("subtraction")
                                .executes(ctx -> setPlayerOperation(ctx.getSource(),
                                    StringArgumentType.getString(ctx, "name"), "subtraction")))
                            .then(Commands.literal("multiplication")
                                .executes(ctx -> setPlayerOperation(ctx.getSource(),
                                    StringArgumentType.getString(ctx, "name"), "multiplication")))
                            .then(Commands.literal("exponentiation")
                                .executes(ctx -> setPlayerOperation(ctx.getSource(),
                                    StringArgumentType.getString(ctx, "name"), "exponentiation")))
                        )
                        .then(Commands.literal("range")
                            .then(Commands.argument("min", IntegerArgumentType.integer())
                                .then(Commands.argument("max", IntegerArgumentType.integer())
                                    .executes(ctx -> setPlayerRange(ctx.getSource(),
                                        StringArgumentType.getString(ctx, "name"),
                                        IntegerArgumentType.getInteger(ctx, "min"),
                                        IntegerArgumentType.getInteger(ctx, "max")))
                                )
                            )
                        )
                        .then(Commands.literal("clear")
                            .executes(ctx -> clearPlayerPreset(ctx.getSource(),
                                StringArgumentType.getString(ctx, "name")))
                        )
                    )
                )
                .then(Commands.literal("npcspawn")
                    .then(Commands.literal("all")
                        .executes(ctx -> setNpcSpawnTarget(ctx.getSource(), "all", null)))
                    .then(Commands.literal("random")
                        .executes(ctx -> setNpcSpawnTarget(ctx.getSource(), "random", null)))
                    .then(Commands.literal("only")
                        .then(Commands.argument("name", StringArgumentType.string())
                            .executes(ctx -> setNpcSpawnTarget(ctx.getSource(), "one",
                                StringArgumentType.getString(ctx, "name")))))
                )
                .then(Commands.literal("group")
                    .then(Commands.literal("clear")
                        .executes(ctx -> clearRewardGroup(ctx.getSource())))
                    .then(Commands.argument("name", StringArgumentType.string())
                        .executes(ctx -> setRewardGroup(ctx.getSource(),
                            StringArgumentType.getString(ctx, "name"))))
                )
                .then(Commands.literal("start")
                    .executes(ctx -> startQuiz(ctx.getSource()))
                    .then(Commands.literal("all")
                        .executes(ctx -> startQuizAll(ctx.getSource())))
                    .then(Commands.argument("player", StringArgumentType.word())
                        .executes(ctx -> startQuizPlayer(ctx.getSource(),
                            StringArgumentType.getString(ctx, "player"))))
                )
                .then(Commands.literal("status")
                    .executes(ctx -> showStatus(ctx.getSource()))
                )
                .then(Commands.literal("enable")
                    .executes(ctx -> setEnabled(ctx.getSource(), true))
                )
                .then(Commands.literal("disable")
                    .executes(ctx -> setEnabled(ctx.getSource(), false))
                )
                .then(Commands.literal("vanishnerds")
                    .executes(ctx -> vanishNerds(ctx.getSource()))
                )
            );
        });
    }

    private static int setProblems(CommandSourceStack source, int count) {
        MathQuestMod.CONFIG.problemsPerQuiz = count;
        MathQuestMod.CONFIG.save();
        source.sendSuccess(() -> Component.literal("[MathQuest] ")
            .withStyle(ChatFormatting.GOLD)
            .append(Component.literal("Problems per quiz set to " + count + ".")
                .withStyle(ChatFormatting.GREEN)), false);
        return 1;
    }

    private static int setInterval(CommandSourceStack source, int seconds) {
        MathQuestMod.CONFIG.quizIntervalSeconds = seconds;
        MathQuestMod.CONFIG.save();
        MathQuestMod.getNerdSpawner().resetTimer();

        source.sendSuccess(() -> Component.literal("[MathQuest] ")
            .withStyle(ChatFormatting.GOLD)
            .append(Component.literal("Quiz interval set to " + MathQuestDurationFormat.forStatus(seconds) + ". Timer reset.")
                .withStyle(ChatFormatting.GREEN)), false);
        return 1;
    }

    private static int setMode(CommandSourceStack source, String mode) {
        MathQuestMod.CONFIG.quizMode = mode;
        MathQuestMod.CONFIG.save();
        MathQuestMod.getNerdSpawner().resetTimer();

        String modeDesc = "popup".equals(mode) ? "Popup (timed screen overlay)" : "NPC (Wandering Nerd)";
        source.sendSuccess(() -> Component.literal("[MathQuest] ")
            .withStyle(ChatFormatting.GOLD)
            .append(Component.literal("Quiz mode set to: " + modeDesc)
                .withStyle(ChatFormatting.GREEN)), false);

        if ("npc".equals(mode)) {
            source.sendSuccess(() -> Component.literal("  The Wandering Nerd will spawn within ")
                .withStyle(ChatFormatting.GRAY)
                .append(Component.literal(MathQuestMod.CONFIG.npcSpawnRadiusBlocks + " blocks")
                    .withStyle(ChatFormatting.AQUA))
                .append(Component.literal(" of players every ")
                    .withStyle(ChatFormatting.GRAY))
                .append(Component.literal(MathQuestDurationFormat.forStatus(MathQuestMod.CONFIG.quizIntervalSeconds))
                    .withStyle(ChatFormatting.AQUA)), false);
        }
        return 1;
    }

    private static int setGlobalOperation(CommandSourceStack source, String op) {
        MathQuestMod.CONFIG.operation = MathQuestConfig.normalizeOperation(op);
        MathQuestMod.CONFIG.save();
        source.sendSuccess(() -> Component.literal("[MathQuest] ")
            .withStyle(ChatFormatting.GOLD)
            .append(Component.literal("Default operation set to " + MathQuestMod.CONFIG.operation + ".")
                .withStyle(ChatFormatting.GREEN)), false);
        return 1;
    }

    private static int setGlobalRange(CommandSourceStack source, int min, int max) {
        if (min > max) {
            int t = min;
            min = max;
            max = t;
        }
        MathQuestMod.CONFIG.minNumber = min;
        MathQuestMod.CONFIG.maxNumber = max;
        MathQuestMod.CONFIG.save();
        int fMin = min, fMax = max;
        source.sendSuccess(() -> Component.literal("[MathQuest] ")
            .withStyle(ChatFormatting.GOLD)
            .append(Component.literal("Default number range set to " + fMin + " - " + fMax + ".")
                .withStyle(ChatFormatting.GREEN)), false);
        return 1;
    }

    private static int setPlayerOperation(CommandSourceStack source, String name, String op) {
        ensurePlayerPresets();
        String key = name.toLowerCase(Locale.ROOT);
        MathQuestConfig.PlayerQuizPreset preset = MathQuestMod.CONFIG.playerPresets.computeIfAbsent(
            key, k -> new MathQuestConfig.PlayerQuizPreset());
        preset.operation = MathQuestConfig.normalizeOperation(op);
        MathQuestMod.CONFIG.save();
        source.sendSuccess(() -> Component.literal("[MathQuest] ")
            .withStyle(ChatFormatting.GOLD)
            .append(Component.literal("Preset for \"" + name + "\": operation = " + preset.operation + ".")
                .withStyle(ChatFormatting.GREEN)), false);
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
        MathQuestConfig.PlayerQuizPreset preset = MathQuestMod.CONFIG.playerPresets.computeIfAbsent(
            key, k -> new MathQuestConfig.PlayerQuizPreset());
        preset.minNumber = min;
        preset.maxNumber = max;
        MathQuestMod.CONFIG.save();
        int fMin = min, fMax = max;
        source.sendSuccess(() -> Component.literal("[MathQuest] ")
            .withStyle(ChatFormatting.GOLD)
            .append(Component.literal("Preset for \"" + name + "\": range = " + fMin + " - " + fMax + ".")
                .withStyle(ChatFormatting.GREEN)), false);
        return 1;
    }

    private static int clearPlayerPreset(CommandSourceStack source, String name) {
        ensurePlayerPresets();
        String key = name.toLowerCase(Locale.ROOT);
        if (MathQuestMod.CONFIG.playerPresets.remove(key) != null) {
            MathQuestMod.CONFIG.save();
            source.sendSuccess(() -> Component.literal("[MathQuest] ")
                .withStyle(ChatFormatting.GOLD)
                .append(Component.literal("Removed preset for \"" + name + "\" (uses global defaults).")
                    .withStyle(ChatFormatting.GREEN)), false);
        } else {
            source.sendSuccess(() -> Component.literal("[MathQuest] ")
                .withStyle(ChatFormatting.GOLD)
                .append(Component.literal("No preset found for \"" + name + "\".")
                    .withStyle(ChatFormatting.YELLOW)), false);
        }
        return 1;
    }

    private static int setNpcSpawnTarget(CommandSourceStack source, String modeKey, String targetName) {
        String mode = MathQuestConfig.normalizeNpcSpawnTargetMode(modeKey);
        MathQuestMod.CONFIG.npcSpawnTargetMode = mode;
        if ("one".equals(mode)) {
            if (targetName == null || targetName.isBlank()) {
                source.sendFailure(Component.literal("[MathQuest] Use /mathquest npcspawn only <playerName>."));
                return 0;
            }
            MathQuestMod.CONFIG.npcSpawnTargetPlayer = targetName.toLowerCase(Locale.ROOT);
        } else {
            MathQuestMod.CONFIG.npcSpawnTargetPlayer = null;
        }
        MathQuestMod.CONFIG.save();

        String desc = switch (mode) {
            case "random" -> "one random online player per interval";
            case "one" -> "only " + MathQuestMod.CONFIG.npcSpawnTargetPlayer;
            default -> "every online player (each gets a spawn attempt)";
        };
        source.sendSuccess(() -> Component.literal("[MathQuest] ")
            .withStyle(ChatFormatting.GOLD)
            .append(Component.literal("NPC auto-spawn: " + desc).withStyle(ChatFormatting.GREEN)), false);
        return 1;
    }

    private static int setRewardGroup(CommandSourceStack source, String name) {
        ensureRewardGroups();
        String key = MathQuestConfig.normalizeGroupName(name);
        if (key.isEmpty()) {
            source.sendFailure(Component.literal("[MathQuest] Group name cannot be empty."));
            return 0;
        }
        if (!MathQuestMod.CONFIG.rewardGroups.containsKey(key)) {
            source.sendFailure(Component.literal("[MathQuest] Unknown reward group: " + key + ". Known: "
                + String.join(", ", MathQuestMod.CONFIG.rewardGroups.keySet())));
            return 0;
        }
        MathQuestMod.CONFIG.rewardGroup = key;
        MathQuestMod.CONFIG.save();
        source.sendSuccess(() -> Component.literal("[MathQuest] ")
            .withStyle(ChatFormatting.GOLD)
            .append(Component.literal("Active reward group set to \"" + key + "\".")
                .withStyle(ChatFormatting.GREEN)), false);
        return 1;
    }

    private static int clearRewardGroup(CommandSourceStack source) {
        MathQuestMod.CONFIG.rewardGroup = null;
        MathQuestMod.CONFIG.save();
        source.sendSuccess(() -> Component.literal("[MathQuest] ")
            .withStyle(ChatFormatting.GOLD)
            .append(Component.literal("Using flat reward list. Set a group with /mathquest group <name>.")
                .withStyle(ChatFormatting.GREEN)), false);
        return 1;
    }

    private static int startQuiz(CommandSourceStack source) {
        ServerPlayer player = source.getPlayer();
        if (player == null) {
            source.sendFailure(Component.literal(
                "[MathQuest] Console/RCON: use /mathquest start <player> to target a specific player."));
            return 0;
        }

        if ("npc".equals(MathQuestMod.CONFIG.quizMode)) {
            ServerLevel world = source.getServer().overworld();
            MathQuestMod.getNerdSpawner().forceSpawn(world, player);
            source.sendSuccess(() -> Component.literal("[MathQuest] ")
                .withStyle(ChatFormatting.GOLD)
                .append(Component.literal("Spawning the Wandering Nerd nearby...")
                    .withStyle(ChatFormatting.GREEN)), false);
        } else {
            ServerPlayNetworking.send(player, QuizPayloadBuilder.create(player));
            source.sendSuccess(() -> Component.literal("[MathQuest] ")
                .withStyle(ChatFormatting.GOLD)
                .append(Component.literal("Opening quiz...")
                    .withStyle(ChatFormatting.GREEN)), false);
        }
        return 1;
    }

    private static int startQuizPlayer(CommandSourceStack source, String playerName) {
        ServerPlayer target = source.getServer().getPlayerList()
            .getPlayerByName(playerName);
        if (target == null) {
            source.sendFailure(Component.literal("[MathQuest] Player \"" + playerName + "\" is not online."));
            return 0;
        }
        if ("npc".equals(MathQuestMod.CONFIG.quizMode)) {
            ServerLevel world = source.getServer().overworld();
            MathQuestMod.getNerdSpawner().forceSpawn(world, target);
            source.sendSuccess(() -> Component.literal("[MathQuest] ")
                .withStyle(ChatFormatting.GOLD)
                .append(Component.literal("Spawning the Wandering Nerd near "
                    + target.getName().getString() + "...")
                    .withStyle(ChatFormatting.GREEN)), false);
        } else {
            ServerPlayNetworking.send(target, QuizPayloadBuilder.create(target));
            source.sendSuccess(() -> Component.literal("[MathQuest] ")
                .withStyle(ChatFormatting.GOLD)
                .append(Component.literal("Opening quiz for " + target.getName().getString() + "...")
                    .withStyle(ChatFormatting.GREEN)), false);
        }
        return 1;
    }

    private static int startQuizAll(CommandSourceStack source) {
        List<ServerPlayer> players = source.getServer().getPlayerList().getPlayers();
        if (players.isEmpty()) {
            source.sendFailure(Component.literal("[MathQuest] No players online."));
            return 0;
        }
        if ("npc".equals(MathQuestMod.CONFIG.quizMode)) {
            ServerLevel world = source.getServer().overworld();
            for (ServerPlayer player : players) {
                MathQuestMod.getNerdSpawner().forceSpawn(world, player);
            }
            source.sendSuccess(() -> Component.literal("[MathQuest] ")
                .withStyle(ChatFormatting.GOLD)
                .append(Component.literal("Spawning the Wandering Nerd near "
                    + players.size() + " online player(s)...")
                    .withStyle(ChatFormatting.GREEN)), false);
        } else {
            for (ServerPlayer player : players) {
                ServerPlayNetworking.send(player, QuizPayloadBuilder.create(player));
            }
            source.sendSuccess(() -> Component.literal("[MathQuest] ")
                .withStyle(ChatFormatting.GOLD)
                .append(Component.literal("Opening quiz for all " + players.size()
                    + " online player(s)...")
                    .withStyle(ChatFormatting.GREEN)), false);
        }
        return players.size();
    }

    private static int vanishNerds(CommandSourceStack source) {
        ServerLevel world = source.getServer().overworld();
        var nerds = world.getEntities(
            MathQuestMod.WANDERING_NERD,
            entity -> true
        );
        int count = 0;
        for (WanderingNerdEntity nerd : nerds) {
            nerd.discard();
            count++;
        }
        int fCount = count;
        source.sendSuccess(() -> Component.literal("[MathQuest] ")
            .withStyle(ChatFormatting.GOLD)
            .append(Component.literal("Removed " + fCount + " Wandering Nerd"
                + (fCount == 1 ? "" : "s") + " from the overworld.")
                .withStyle(ChatFormatting.GREEN)), false);
        return count;
    }

    private static int setEnabled(CommandSourceStack source, boolean enabled) {
        MathQuestMod.CONFIG.enabled = enabled;
        MathQuestMod.CONFIG.save();
        if (enabled) {
            MathQuestMod.getNerdSpawner().resetTimer();
        }

        source.sendSuccess(() -> Component.literal("[MathQuest] ")
            .withStyle(ChatFormatting.GOLD)
            .append(Component.literal(enabled ? "Quizzes enabled!" : "Quizzes disabled.")
                .withStyle(enabled ? ChatFormatting.GREEN : ChatFormatting.RED)), false);
        return 1;
    }

    private static int showStatus(CommandSourceStack source) {
        var config = MathQuestMod.CONFIG;

        source.sendSuccess(() -> Component.literal("--- MathQuest Status ---").withStyle(ChatFormatting.GOLD), false);
        source.sendSuccess(() -> Component.literal("  Enabled: ").withStyle(ChatFormatting.GRAY)
            .append(Component.literal(config.enabled ? "Yes" : "No")
                .withStyle(config.enabled ? ChatFormatting.GREEN : ChatFormatting.RED)), false);
        String modeDesc = "popup".equals(config.quizMode) ? "Popup" : "NPC (Wandering Nerd)";
        source.sendSuccess(() -> Component.literal("  Mode: ").withStyle(ChatFormatting.GRAY)
            .append(Component.literal(modeDesc).withStyle(ChatFormatting.WHITE)), false);
        source.sendSuccess(() -> Component.literal("  Interval: ").withStyle(ChatFormatting.GRAY)
            .append(Component.literal(MathQuestDurationFormat.forStatus(config.quizIntervalSeconds)).withStyle(ChatFormatting.WHITE)), false);
        if ("npc".equals(config.quizMode)) {
            source.sendSuccess(() -> Component.literal("  NPC spawn radius: ").withStyle(ChatFormatting.GRAY)
                .append(Component.literal(config.npcSpawnRadiusBlocks + " blocks").withStyle(ChatFormatting.WHITE)), false);
            source.sendSuccess(() -> Component.literal("  NPC despawn time: ").withStyle(ChatFormatting.GRAY)
                .append(Component.literal(MathQuestDurationFormat.forStatus(config.npcDespawnSeconds)).withStyle(ChatFormatting.WHITE)), false);
        }
        String spawnMode = MathQuestConfig.normalizeNpcSpawnTargetMode(config.npcSpawnTargetMode);
        String spawnDesc = switch (spawnMode) {
            case "random" -> "random (one player per interval)";
            case "one" -> {
                String n = config.npcSpawnTargetPlayer;
                yield "only " + (n != null && !n.isBlank() ? n : "(unset)");
            }
            default -> "all (every online player)";
        };
        source.sendSuccess(() -> Component.literal("  NPC auto-spawn target: ").withStyle(ChatFormatting.GRAY)
            .append(Component.literal(spawnDesc).withStyle(ChatFormatting.WHITE)), false);
        appendNextQuizStatus(source);
        String defaultOp = (config.operation != null && !config.operation.isBlank())
            ? config.operation : "multiplication";
        source.sendSuccess(() -> Component.literal("  Default operation: ").withStyle(ChatFormatting.GRAY)
            .append(Component.literal(defaultOp).withStyle(ChatFormatting.WHITE)), false);
        source.sendSuccess(() -> Component.literal("  Default number range: ").withStyle(ChatFormatting.GRAY)
            .append(Component.literal(config.minNumber + " - " + config.maxNumber).withStyle(ChatFormatting.WHITE)), false);
        if (config.playerPresets != null && !config.playerPresets.isEmpty()) {
            source.sendSuccess(() -> Component.literal("  Player presets:").withStyle(ChatFormatting.GRAY), false);
            for (Map.Entry<String, MathQuestConfig.PlayerQuizPreset> e : config.playerPresets.entrySet()) {
                MathQuestConfig.PlayerQuizPreset p = e.getValue();
                StringBuilder line = new StringBuilder();
                line.append("    - ").append(e.getKey()).append(": ");
                boolean any = false;
                if (p.minNumber != null && p.maxNumber != null) {
                    line.append("range ").append(p.minNumber).append("-").append(p.maxNumber);
                    any = true;
                }
                if (p.operation != null && !p.operation.isBlank()) {
                    if (any) line.append(", ");
                    line.append("op ").append(p.operation);
                    any = true;
                }
                if (!any) line.append("(empty)");
                String lineStr = line.toString();
                source.sendSuccess(() -> Component.literal(lineStr).withStyle(ChatFormatting.AQUA), false);
            }
        }
        source.sendSuccess(() -> Component.literal("  Reward mode: ").withStyle(ChatFormatting.GRAY)
            .append(Component.literal(config.rewardMode).withStyle(ChatFormatting.WHITE)), false);
        String rg = config.rewardGroup;
        boolean groupActive = rg != null && !rg.isBlank()
            && config.rewardGroups != null
            && config.rewardGroups.containsKey(MathQuestConfig.normalizeGroupName(rg));
        if (groupActive) {
            MathQuestConfig.RewardGroup activeGroup = config.rewardGroups.get(MathQuestConfig.normalizeGroupName(rg));
            String mode = activeGroup == null ? "all" : MathQuestConfig.normalizeRewardGroupMode(activeGroup.mode);
            source.sendSuccess(() -> Component.literal("  Reward pool: ").withStyle(ChatFormatting.GRAY)
                .append(Component.literal("group \"" + MathQuestConfig.normalizeGroupName(rg) + "\" (" + mode + ")")
                    .withStyle(ChatFormatting.WHITE)), false);
        } else {
            source.sendSuccess(() -> Component.literal("  Reward pool: ").withStyle(ChatFormatting.GRAY)
                .append(Component.literal("flat list (rewards)").withStyle(ChatFormatting.WHITE)), false);
        }
        List<MathQuestConfig.RewardEntry> activeRewards = config.resolveActiveRewardEntries();
        if (activeRewards != null && !activeRewards.isEmpty()) {
            for (MathQuestConfig.RewardEntry entry : activeRewards) {
                String name = entry.item.contains(":") ? entry.item.substring(entry.item.indexOf(':') + 1) : entry.item;
                String prettyName = name.replace('_', ' ');
                source.sendSuccess(() -> Component.literal("    - ").withStyle(ChatFormatting.GRAY)
                    .append(Component.literal(prettyName + " x" + entry.count).withStyle(ChatFormatting.AQUA)), false);
            }
        }

        int onlinePlayers = source.getServer().getPlayerList().getPlayerCount();
        source.sendSuccess(() -> Component.literal("  Online players: ").withStyle(ChatFormatting.GRAY)
            .append(Component.literal(String.valueOf(onlinePlayers)).withStyle(ChatFormatting.WHITE)), false);

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
        if (MathQuestMod.CONFIG.playerPresets == null) {
            MathQuestMod.CONFIG.playerPresets = new LinkedHashMap<>();
        }
    }

    private static void ensureRewardGroups() {
        if (MathQuestMod.CONFIG.rewardGroups == null) {
            MathQuestMod.CONFIG.rewardGroups = new LinkedHashMap<>();
        }
        MathQuestConfig.ensureJtreeGroup(MathQuestMod.CONFIG.rewardGroups);
    }
}
