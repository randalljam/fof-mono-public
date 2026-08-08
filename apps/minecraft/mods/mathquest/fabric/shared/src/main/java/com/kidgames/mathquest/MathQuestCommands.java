package com.kidgames.mathquest;

import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.screen.QuizOfferScreen;
import com.kidgames.mathquest.server.QuizDeliveryPreview;
import com.kidgames.mathquest.util.MathQuestDurationFormat;
import com.mojang.brigadier.arguments.IntegerArgumentType;
import com.mojang.brigadier.arguments.StringArgumentType;
import net.fabricmc.fabric.api.client.command.v2.ClientCommandManager;
import net.fabricmc.fabric.api.client.command.v2.ClientCommandRegistrationCallback;
import net.fabricmc.fabric.api.client.command.v2.FabricClientCommandSource;
import net.minecraft.ChatFormatting;
import net.minecraft.client.Minecraft;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.Identifier;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.item.Item;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

public class MathQuestCommands {

    public static void register() {
        ClientCommandRegistrationCallback.EVENT.register((dispatcher, registryAccess) -> {
            dispatcher.register(ClientCommandManager.literal("mathquest")
                .then(ClientCommandManager.literal("interval")
                    .then(ClientCommandManager.argument("seconds", IntegerArgumentType.integer(5))
                        .executes(context -> setInterval(context.getSource(),
                            IntegerArgumentType.getInteger(context, "seconds")))
                    )
                )
                .then(ClientCommandManager.literal("problems")
                    .then(ClientCommandManager.argument("count", IntegerArgumentType.integer(1, 50))
                        .executes(context -> setProblems(context.getSource(),
                            IntegerArgumentType.getInteger(context, "count")))
                    )
                )
                .then(ClientCommandManager.literal("reward")
                    .then(ClientCommandManager.argument("item", StringArgumentType.string())
                        .executes(context -> setReward(context.getSource(),
                            StringArgumentType.getString(context, "item"), 1))
                        .then(ClientCommandManager.argument("count", IntegerArgumentType.integer(1, 64))
                            .executes(context -> setReward(context.getSource(),
                                StringArgumentType.getString(context, "item"),
                                IntegerArgumentType.getInteger(context, "count")))
                        )
                    )
                )
                .then(ClientCommandManager.literal("status")
                    .executes(context -> showStatus(context.getSource()))
                )
                .then(ClientCommandManager.literal("enable")
                    .executes(context -> setEnabled(context.getSource(), true))
                )
                .then(ClientCommandManager.literal("disable")
                    .executes(context -> setEnabled(context.getSource(), false))
                )
                .then(ClientCommandManager.literal("mode")
                    .then(ClientCommandManager.literal("popup")
                        .executes(context -> setMode(context.getSource(), "popup"))
                    )
                    .then(ClientCommandManager.literal("npc")
                        .executes(context -> setMode(context.getSource(), "npc"))
                    )
                )
                .then(ClientCommandManager.literal("start")
                    .executes(context -> startQuiz(context.getSource()))
                )
                .then(ClientCommandManager.literal("operation")
                    .then(ClientCommandManager.literal("addition")
                        .executes(context -> setGlobalOperation(context.getSource(), "addition")))
                    .then(ClientCommandManager.literal("subtraction")
                        .executes(context -> setGlobalOperation(context.getSource(), "subtraction")))
                    .then(ClientCommandManager.literal("multiplication")
                        .executes(context -> setGlobalOperation(context.getSource(), "multiplication")))
                    .then(ClientCommandManager.literal("exponentiation")
                        .executes(context -> setGlobalOperation(context.getSource(), "exponentiation")))
                )
                .then(ClientCommandManager.literal("range")
                    .then(ClientCommandManager.argument("min", IntegerArgumentType.integer())
                        .then(ClientCommandManager.argument("max", IntegerArgumentType.integer())
                            .executes(context -> setGlobalRange(context.getSource(),
                                IntegerArgumentType.getInteger(context, "min"),
                                IntegerArgumentType.getInteger(context, "max")))
                        )
                    )
                )
                .then(ClientCommandManager.literal("player")
                    .then(ClientCommandManager.argument("name", StringArgumentType.string())
                        .then(ClientCommandManager.literal("operation")
                            .then(ClientCommandManager.literal("addition")
                                .executes(context -> setPlayerOperation(context.getSource(),
                                    StringArgumentType.getString(context, "name"), "addition")))
                            .then(ClientCommandManager.literal("subtraction")
                                .executes(context -> setPlayerOperation(context.getSource(),
                                    StringArgumentType.getString(context, "name"), "subtraction")))
                            .then(ClientCommandManager.literal("multiplication")
                                .executes(context -> setPlayerOperation(context.getSource(),
                                    StringArgumentType.getString(context, "name"), "multiplication")))
                            .then(ClientCommandManager.literal("exponentiation")
                                .executes(context -> setPlayerOperation(context.getSource(),
                                    StringArgumentType.getString(context, "name"), "exponentiation")))
                        )
                        .then(ClientCommandManager.literal("range")
                            .then(ClientCommandManager.argument("min", IntegerArgumentType.integer())
                                .then(ClientCommandManager.argument("max", IntegerArgumentType.integer())
                                    .executes(context -> setPlayerRange(context.getSource(),
                                        StringArgumentType.getString(context, "name"),
                                        IntegerArgumentType.getInteger(context, "min"),
                                        IntegerArgumentType.getInteger(context, "max")))
                                )
                            )
                        )
                        .then(ClientCommandManager.literal("clear")
                            .executes(context -> clearPlayerPreset(context.getSource(),
                                StringArgumentType.getString(context, "name")))
                        )
                    )
                )
                .then(ClientCommandManager.literal("npcspawn")
                    .then(ClientCommandManager.literal("all")
                        .executes(context -> setNpcSpawnTarget(context.getSource(), "all", null)))
                    .then(ClientCommandManager.literal("random")
                        .executes(context -> setNpcSpawnTarget(context.getSource(), "random", null)))
                    .then(ClientCommandManager.literal("only")
                        .then(ClientCommandManager.argument("name", StringArgumentType.string())
                            .executes(context -> setNpcSpawnTarget(context.getSource(), "one",
                                StringArgumentType.getString(context, "name")))))
                )
                .then(ClientCommandManager.literal("group")
                    .then(ClientCommandManager.literal("clear")
                        .executes(context -> clearRewardGroup(context.getSource())))
                    .then(ClientCommandManager.argument("name", StringArgumentType.string())
                        .executes(context -> setRewardGroup(context.getSource(),
                            StringArgumentType.getString(context, "name"))))
                )
            );
        });
    }

    private static boolean isRemoteMultiplayer() {
        return Minecraft.getInstance().getSingleplayerServer() == null;
    }

    private static int rejectIfMultiplayer(FabricClientCommandSource source) {
        source.sendFeedback(Component.literal("[MathQuest] ")
            .withStyle(ChatFormatting.GOLD)
            .append(Component.literal("On a multiplayer server, use server-side /mathquest commands (op required). "
                + "Client commands only affect local config, which is ignored in multiplayer.")
                .withStyle(ChatFormatting.RED)));
        return 0;
    }

    private static int setRewardGroup(FabricClientCommandSource source, String name) {
        if (isRemoteMultiplayer()) return rejectIfMultiplayer(source);
        ensureRewardGroups();
        String key = MathQuestConfig.normalizeGroupName(name);
        if (key.isEmpty()) {
            source.sendFeedback(Component.literal("[MathQuest] ")
                .withStyle(ChatFormatting.GOLD)
                .append(Component.literal("Group name cannot be empty.").withStyle(ChatFormatting.RED)));
            return 0;
        }
        if (!MathQuestMod.CONFIG.rewardGroups.containsKey(key)) {
            source.sendFeedback(Component.literal("[MathQuest] ")
                .withStyle(ChatFormatting.GOLD)
                .append(Component.literal("Unknown reward group: " + key + ". Known: "
                    + String.join(", ", MathQuestMod.CONFIG.rewardGroups.keySet())).withStyle(ChatFormatting.RED)));
            return 0;
        }
        MathQuestMod.CONFIG.rewardGroup = key;
        MathQuestMod.CONFIG.save();
        source.sendFeedback(Component.literal("[MathQuest] ")
            .withStyle(ChatFormatting.GOLD)
            .append(Component.literal("Active reward group set to \"" + key + "\".")
                .withStyle(ChatFormatting.GREEN)));
        return 1;
    }

    private static int clearRewardGroup(FabricClientCommandSource source) {
        if (isRemoteMultiplayer()) return rejectIfMultiplayer(source);
        MathQuestMod.CONFIG.rewardGroup = null;
        MathQuestMod.CONFIG.save();
        source.sendFeedback(Component.literal("[MathQuest] ")
            .withStyle(ChatFormatting.GOLD)
            .append(Component.literal("Using flat reward list (rewards). Set a group with /mathquest group <name>.")
                .withStyle(ChatFormatting.GREEN)));
        return 1;
    }

    private static void ensureRewardGroups() {
        if (MathQuestMod.CONFIG.rewardGroups == null) {
            MathQuestMod.CONFIG.rewardGroups = new LinkedHashMap<>();
        }
        MathQuestConfig.ensureJtreeGroup(MathQuestMod.CONFIG.rewardGroups);
    }

    private static int setNpcSpawnTarget(FabricClientCommandSource source, String modeKey, String targetName) {
        if (isRemoteMultiplayer()) return rejectIfMultiplayer(source);
        String mode = MathQuestConfig.normalizeNpcSpawnTargetMode(modeKey);
        MathQuestMod.CONFIG.npcSpawnTargetMode = mode;
        if ("one".equals(mode)) {
            if (targetName == null || targetName.isBlank()) {
                source.sendFeedback(Component.literal("[MathQuest] ")
                    .withStyle(ChatFormatting.GOLD)
                    .append(Component.literal("Use /mathquest npcspawn only <playerName>.").withStyle(ChatFormatting.RED)));
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
        source.sendFeedback(Component.literal("[MathQuest] ")
            .withStyle(ChatFormatting.GOLD)
            .append(Component.literal("NPC auto-spawn: " + desc).withStyle(ChatFormatting.GREEN)));
        return 1;
    }

    private static void ensurePlayerPresets() {
        if (MathQuestMod.CONFIG.playerPresets == null) {
            MathQuestMod.CONFIG.playerPresets = new LinkedHashMap<>();
        }
    }

    private static int setGlobalOperation(FabricClientCommandSource source, String op) {
        if (isRemoteMultiplayer()) return rejectIfMultiplayer(source);
        MathQuestMod.CONFIG.operation = MathQuestConfig.normalizeOperation(op);
        MathQuestMod.CONFIG.save();
        source.sendFeedback(Component.literal("[MathQuest] ")
            .withStyle(ChatFormatting.GOLD)
            .append(Component.literal("Default operation set to " + MathQuestMod.CONFIG.operation + ".")
                .withStyle(ChatFormatting.GREEN)));
        return 1;
    }

    private static int setGlobalRange(FabricClientCommandSource source, int min, int max) {
        if (isRemoteMultiplayer()) return rejectIfMultiplayer(source);
        if (min > max) {
            int t = min;
            min = max;
            max = t;
        }
        MathQuestMod.CONFIG.minNumber = min;
        MathQuestMod.CONFIG.maxNumber = max;
        MathQuestMod.CONFIG.save();
        source.sendFeedback(Component.literal("[MathQuest] ")
            .withStyle(ChatFormatting.GOLD)
            .append(Component.literal("Default number range set to " + min + " - " + max + ".")
                .withStyle(ChatFormatting.GREEN)));
        return 1;
    }

    private static int setPlayerOperation(FabricClientCommandSource source, String name, String op) {
        if (isRemoteMultiplayer()) return rejectIfMultiplayer(source);
        ensurePlayerPresets();
        String key = name.toLowerCase(Locale.ROOT);
        MathQuestConfig.PlayerQuizPreset preset = MathQuestMod.CONFIG.playerPresets.computeIfAbsent(
            key, k -> new MathQuestConfig.PlayerQuizPreset());
        preset.operation = MathQuestConfig.normalizeOperation(op);
        MathQuestMod.CONFIG.save();
        source.sendFeedback(Component.literal("[MathQuest] ")
            .withStyle(ChatFormatting.GOLD)
            .append(Component.literal("Preset for \"" + name + "\": operation = " + preset.operation + ".")
                .withStyle(ChatFormatting.GREEN)));
        return 1;
    }

    private static int setPlayerRange(FabricClientCommandSource source, String name, int min, int max) {
        if (isRemoteMultiplayer()) return rejectIfMultiplayer(source);
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
        source.sendFeedback(Component.literal("[MathQuest] ")
            .withStyle(ChatFormatting.GOLD)
            .append(Component.literal("Preset for \"" + name + "\": range = " + min + " - " + max + ".")
                .withStyle(ChatFormatting.GREEN)));
        return 1;
    }

    private static int clearPlayerPreset(FabricClientCommandSource source, String name) {
        if (isRemoteMultiplayer()) return rejectIfMultiplayer(source);
        ensurePlayerPresets();
        String key = name.toLowerCase(Locale.ROOT);
        if (MathQuestMod.CONFIG.playerPresets.remove(key) != null) {
            MathQuestMod.CONFIG.save();
            source.sendFeedback(Component.literal("[MathQuest] ")
                .withStyle(ChatFormatting.GOLD)
                .append(Component.literal("Removed preset for \"" + name + "\" (uses global defaults).")
                    .withStyle(ChatFormatting.GREEN)));
        } else {
            source.sendFeedback(Component.literal("[MathQuest] ")
                .withStyle(ChatFormatting.GOLD)
                .append(Component.literal("No preset found for \"" + name + "\".")
                    .withStyle(ChatFormatting.YELLOW)));
        }
        return 1;
    }

    private static int setProblems(FabricClientCommandSource source, int count) {
        if (isRemoteMultiplayer()) return rejectIfMultiplayer(source);
        MathQuestMod.CONFIG.problemsPerQuiz = count;
        MathQuestMod.CONFIG.save();

        source.sendFeedback(Component.literal("[MathQuest] ")
            .withStyle(ChatFormatting.GOLD)
            .append(Component.literal("Problems per quiz set to " + count + ".")
                .withStyle(ChatFormatting.GREEN)));
        return 1;
    }

    private static int setInterval(FabricClientCommandSource source, int seconds) {
        if (isRemoteMultiplayer()) return rejectIfMultiplayer(source);
        MathQuestMod.CONFIG.quizIntervalSeconds = seconds;
        MathQuestMod.CONFIG.save();
        MathQuestClient.resetTimer();

        source.sendFeedback(Component.literal("[MathQuest] ")
            .withStyle(ChatFormatting.GOLD)
            .append(Component.literal("Quiz interval set to " + MathQuestDurationFormat.forStatus(seconds) + ". Timer reset.")
                .withStyle(ChatFormatting.GREEN)));
        return 1;
    }

    private static int setMode(FabricClientCommandSource source, String mode) {
        if (isRemoteMultiplayer()) return rejectIfMultiplayer(source);
        MathQuestMod.CONFIG.quizMode = mode;
        MathQuestMod.CONFIG.save();
        MathQuestClient.resetTimer();

        String modeDesc = "popup".equals(mode) ? "Popup (timed screen overlay)" : "NPC (Wandering Nerd)";
        source.sendFeedback(Component.literal("[MathQuest] ")
            .withStyle(ChatFormatting.GOLD)
            .append(Component.literal("Quiz mode set to: " + modeDesc)
                .withStyle(ChatFormatting.GREEN)));

        if ("npc".equals(mode)) {
            source.sendFeedback(Component.literal("  The Wandering Nerd will spawn within ")
                .withStyle(ChatFormatting.GRAY)
                .append(Component.literal(MathQuestMod.CONFIG.npcSpawnRadiusBlocks + " blocks")
                    .withStyle(ChatFormatting.AQUA))
                .append(Component.literal(" of you every ")
                    .withStyle(ChatFormatting.GRAY))
                .append(Component.literal(MathQuestDurationFormat.forStatus(MathQuestMod.CONFIG.quizIntervalSeconds))
                    .withStyle(ChatFormatting.AQUA)));
        }
        return 1;
    }

    private static int showStatus(FabricClientCommandSource source) {
        if (isRemoteMultiplayer()) {
            source.sendFeedback(Component.literal("[MathQuest] ")
                .withStyle(ChatFormatting.GOLD)
                .append(Component.literal(
                    "Connected to a multiplayer server. Run 'mathquest status' from the server "
                        + "console for active settings.")
                    .withStyle(ChatFormatting.YELLOW)));
            return 1;
        }
        var config = MathQuestMod.CONFIG;

        source.sendFeedback(Component.literal("--- MathQuest Status ---").withStyle(ChatFormatting.GOLD));
        source.sendFeedback(Component.literal("  Enabled: ").withStyle(ChatFormatting.GRAY)
            .append(Component.literal(config.enabled ? "Yes" : "No")
                .withStyle(config.enabled ? ChatFormatting.GREEN : ChatFormatting.RED)));
        String modeDesc = "popup".equals(config.quizMode) ? "Popup" : "NPC (Wandering Nerd)";
        source.sendFeedback(Component.literal("  Mode: ").withStyle(ChatFormatting.GRAY)
            .append(Component.literal(modeDesc).withStyle(ChatFormatting.WHITE)));
        source.sendFeedback(Component.literal("  Interval: ").withStyle(ChatFormatting.GRAY)
            .append(Component.literal(MathQuestDurationFormat.forStatus(config.quizIntervalSeconds)).withStyle(ChatFormatting.WHITE)));
        if ("npc".equals(config.quizMode)) {
            source.sendFeedback(Component.literal("  NPC spawn radius: ").withStyle(ChatFormatting.GRAY)
                .append(Component.literal(config.npcSpawnRadiusBlocks + " blocks").withStyle(ChatFormatting.WHITE)));
            source.sendFeedback(Component.literal("  NPC despawn time: ").withStyle(ChatFormatting.GRAY)
                .append(Component.literal(MathQuestDurationFormat.forStatus(config.npcDespawnSeconds)).withStyle(ChatFormatting.WHITE)));
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
        source.sendFeedback(Component.literal("  NPC auto-spawn target: ").withStyle(ChatFormatting.GRAY)
            .append(Component.literal(spawnDesc).withStyle(ChatFormatting.WHITE)));
        appendNextQuizStatus(source);
        String defaultOp = (config.operation != null && !config.operation.isBlank())
            ? config.operation : "multiplication";
        source.sendFeedback(Component.literal("  Default operation: ").withStyle(ChatFormatting.GRAY)
            .append(Component.literal(defaultOp).withStyle(ChatFormatting.WHITE)));
        source.sendFeedback(Component.literal("  Default number range: ").withStyle(ChatFormatting.GRAY)
            .append(Component.literal(config.minNumber + " - " + config.maxNumber).withStyle(ChatFormatting.WHITE)));
        if (config.playerPresets != null && !config.playerPresets.isEmpty()) {
            source.sendFeedback(Component.literal("  Player presets:").withStyle(ChatFormatting.GRAY));
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
                source.sendFeedback(Component.literal(line.toString()).withStyle(ChatFormatting.AQUA));
            }
        }
        source.sendFeedback(Component.literal("  Reward mode: ").withStyle(ChatFormatting.GRAY)
            .append(Component.literal(config.rewardMode).withStyle(ChatFormatting.WHITE)));
        String rg = config.rewardGroup;
        boolean groupActive = rg != null && !rg.isBlank()
            && config.rewardGroups != null
            && config.rewardGroups.containsKey(MathQuestConfig.normalizeGroupName(rg));
        if (groupActive) {
            MathQuestConfig.RewardGroup activeGroup = config.rewardGroups.get(MathQuestConfig.normalizeGroupName(rg));
            String mode = activeGroup == null ? "all" : MathQuestConfig.normalizeRewardGroupMode(activeGroup.mode);
            source.sendFeedback(Component.literal("  Reward pool: ").withStyle(ChatFormatting.GRAY)
                .append(Component.literal("group \"" + MathQuestConfig.normalizeGroupName(rg) + "\" (" + mode + ")")
                    .withStyle(ChatFormatting.WHITE)));
        } else {
            source.sendFeedback(Component.literal("  Reward pool: ").withStyle(ChatFormatting.GRAY)
                .append(Component.literal("flat list (rewards)").withStyle(ChatFormatting.WHITE)));
        }
        List<MathQuestConfig.RewardEntry> activeRewards = config.resolveActiveRewardEntries();
        if (activeRewards != null && !activeRewards.isEmpty()) {
            for (MathQuestConfig.RewardEntry entry : activeRewards) {
                String name = entry.item.contains(":") ? entry.item.substring(entry.item.indexOf(':') + 1) : entry.item;
                name = name.replace('_', ' ');
                source.sendFeedback(Component.literal("    - ").withStyle(ChatFormatting.GRAY)
                    .append(Component.literal(name + " x" + entry.count).withStyle(ChatFormatting.AQUA)));
            }
        }
        return 1;
    }

    private static void appendNextQuizStatus(FabricClientCommandSource source) {
        Minecraft client = Minecraft.getInstance();
        if (client == null || client.player == null) return;
        for (QuizDeliveryPreview.StatusLine line : QuizDeliveryPreview.statusLinesForPlayer(
            client.player.getName().getString())) {
            ChatFormatting valueColor = line.error() ? ChatFormatting.RED : ChatFormatting.WHITE;
            source.sendFeedback(Component.literal("  " + line.label() + ": ").withStyle(ChatFormatting.GRAY)
                .append(Component.literal(line.value()).withStyle(valueColor)));
        }
    }

    private static int setReward(FabricClientCommandSource source, String itemId, int count) {
        if (isRemoteMultiplayer()) return rejectIfMultiplayer(source);
        if (!itemId.contains(":")) {
            itemId = "minecraft:" + itemId;
        }

        try {
            Identifier id = Identifier.parse(itemId);
            Item item = BuiltInRegistries.ITEM.getValue(id);
            if (item == null) {
                source.sendFeedback(Component.literal("[MathQuest] ")
                    .withStyle(ChatFormatting.GOLD)
                    .append(Component.literal("Unknown item: " + itemId).withStyle(ChatFormatting.RED)));
                return 0;
            }
        } catch (Exception e) {
            source.sendFeedback(Component.literal("[MathQuest] ")
                .withStyle(ChatFormatting.GOLD)
                .append(Component.literal("Invalid item ID: " + itemId).withStyle(ChatFormatting.RED)));
            return 0;
        }

        List<MathQuestConfig.RewardEntry> newRewards = new ArrayList<>();
        newRewards.add(new MathQuestConfig.RewardEntry(itemId, count));
        MathQuestMod.CONFIG.rewards = newRewards;
        MathQuestMod.CONFIG.rewardMode = "all";
        MathQuestMod.CONFIG.rewardGroup = null;
        MathQuestMod.CONFIG.save();

        String displayName = itemId.contains(":") ? itemId.substring(itemId.indexOf(':') + 1) : itemId;
        displayName = displayName.replace('_', ' ');
        source.sendFeedback(Component.literal("[MathQuest] ")
            .withStyle(ChatFormatting.GOLD)
            .append(Component.literal("Reward set to " + count + "x " + displayName + ".")
                .withStyle(ChatFormatting.GREEN)));
        return 1;
    }

    private static int startQuiz(FabricClientCommandSource source) {
        if ("npc".equals(MathQuestMod.CONFIG.quizMode)) {
            Minecraft client = Minecraft.getInstance();
            var server = client.getSingleplayerServer();
            if (server != null && client.player != null) {
                ServerPlayer serverPlayer = server.getPlayerList().getPlayer(client.player.getUUID());
                if (serverPlayer != null) {
                    ServerLevel serverWorld = server.overworld();
                    server.execute(() -> {
                        MathQuestMod.getNerdSpawner().forceSpawn(serverWorld, serverPlayer);
                    });
                    source.sendFeedback(Component.literal("[MathQuest] ")
                        .withStyle(ChatFormatting.GOLD)
                        .append(Component.literal("Spawning the Wandering Nerd nearby...")
                            .withStyle(ChatFormatting.GREEN)));
                } else {
                    source.sendFeedback(Component.literal("[MathQuest] ")
                        .withStyle(ChatFormatting.GOLD)
                        .append(Component.literal("Could not find server player.").withStyle(ChatFormatting.RED)));
                }
            } else {
                source.sendFeedback(Component.literal("[MathQuest] ")
                    .withStyle(ChatFormatting.GOLD)
                    .append(Component.literal(
                        "On a dedicated server, nerds spawn on the server. "
                            + "As an op, use /mathquest start (or ask the host to run "
                            + "mathquest start <yourname> in the server console)."
                    ).withStyle(ChatFormatting.RED)));
            }
        } else {
            Minecraft client = Minecraft.getInstance();
            client.execute(() -> client.setScreen(new QuizOfferScreen()));
            source.sendFeedback(Component.literal("[MathQuest] ")
                .withStyle(ChatFormatting.GOLD)
                .append(Component.literal("Opening quiz...").withStyle(ChatFormatting.GREEN)));
        }
        return 1;
    }

    private static int setEnabled(FabricClientCommandSource source, boolean enabled) {
        if (isRemoteMultiplayer()) return rejectIfMultiplayer(source);
        MathQuestMod.CONFIG.enabled = enabled;
        MathQuestMod.CONFIG.save();
        if (enabled) {
            MathQuestClient.resetTimer();
        }

        source.sendFeedback(Component.literal("[MathQuest] ")
            .withStyle(ChatFormatting.GOLD)
            .append(Component.literal(enabled ? "Quizzes enabled!" : "Quizzes disabled.")
                .withStyle(enabled ? ChatFormatting.GREEN : ChatFormatting.RED)));
        return 1;
    }
}
