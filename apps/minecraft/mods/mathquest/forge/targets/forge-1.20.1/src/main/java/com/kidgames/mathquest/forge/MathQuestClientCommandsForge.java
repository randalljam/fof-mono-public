package com.kidgames.mathquest.forge;

import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.forge.entity.MathQuestNerdDespawnForge;
import com.kidgames.mathquest.forge.MathQuestClientForge;
import com.kidgames.mathquest.persistence.MathQuizDbPaths;
import com.kidgames.mathquest.server.QuizDeliveryPreview;
import com.kidgames.mathquest.util.MathQuestDurationFormat;
import com.kidgames.mathquest.forge.screen.QuizOfferScreenForge;
import com.mojang.brigadier.arguments.IntegerArgumentType;
import com.mojang.brigadier.arguments.StringArgumentType;
import net.minecraft.ChatFormatting;
import net.minecraft.client.Minecraft;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.RegisterClientCommandsEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

import java.util.LinkedHashMap;

/** Client-side /mathquest commands for Forge singleplayer (mirrors Fabric MathQuestCommands). */
@Mod.EventBusSubscriber(modid = MathQuestForge.MOD_ID, bus = Mod.EventBusSubscriber.Bus.FORGE, value = Dist.CLIENT)
public final class MathQuestClientCommandsForge {
    private MathQuestClientCommandsForge() {}

    @SubscribeEvent
    public static void onRegisterClientCommands(RegisterClientCommandsEvent event) {
        event.getDispatcher().register(Commands.literal("mathquest")
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
            .then(Commands.literal("group")
                .then(Commands.literal("clear").executes(ctx -> clearRewardGroup(ctx.getSource())))
                .then(Commands.argument("name", StringArgumentType.string())
                    .executes(ctx -> setRewardGroup(ctx.getSource(), StringArgumentType.getString(ctx, "name")))))
            .then(Commands.literal("start").executes(ctx -> startQuiz(ctx.getSource())))
            .then(Commands.literal("vanishnerds").executes(ctx -> vanishNerds(ctx.getSource())))
            .then(Commands.literal("status").executes(ctx -> showStatus(ctx.getSource())))
            .then(Commands.literal("enable").executes(ctx -> setEnabled(ctx.getSource(), true)))
            .then(Commands.literal("disable").executes(ctx -> setEnabled(ctx.getSource(), false)))
            .then(Commands.literal("multipartProjectileFix")
                .executes(ctx -> showMultipartProjectileFix(ctx.getSource()))
                .then(Commands.literal("on").executes(ctx -> setMultipartProjectileFix(ctx.getSource(), true)))
                .then(Commands.literal("off").executes(ctx -> setMultipartProjectileFix(ctx.getSource(), false)))
                .then(Commands.literal("status").executes(ctx -> showMultipartProjectileFix(ctx.getSource()))))
        );
    }

    private static boolean isRemoteMultiplayer() {
        return Minecraft.getInstance().getSingleplayerServer() == null;
    }

    private static int rejectIfMultiplayer(CommandSourceStack source) {
        source.sendFailure(Component.literal("[MathQuest] ")
            .withStyle(ChatFormatting.GOLD)
            .append(Component.literal("On a multiplayer server, use server-side /mathquest commands (op required). "
                + "Client commands only affect local config, which is ignored in multiplayer.")
                .withStyle(ChatFormatting.RED)));
        return 0;
    }

    private static int setInterval(CommandSourceStack source, int seconds) {
        if (isRemoteMultiplayer()) return rejectIfMultiplayer(source);
        MathQuestConfig.INSTANCE.quizIntervalSeconds = seconds;
        MathQuestConfig.INSTANCE.save();
        MathQuestClientForge.resetTimer();
        source.sendSuccess(() -> gold("Quiz interval set to " + MathQuestDurationFormat.forStatus(seconds) + ". Timer reset."), false);
        return 1;
    }

    private static int setProblems(CommandSourceStack source, int count) {
        if (isRemoteMultiplayer()) return rejectIfMultiplayer(source);
        MathQuestConfig.INSTANCE.problemsPerQuiz = count;
        MathQuestConfig.INSTANCE.save();
        source.sendSuccess(() -> gold("Problems per quiz set to " + count + "."), false);
        return 1;
    }

    private static int setMode(CommandSourceStack source, String mode) {
        if (isRemoteMultiplayer()) return rejectIfMultiplayer(source);
        MathQuestConfig.INSTANCE.quizMode = mode;
        MathQuestConfig.INSTANCE.save();
        MathQuestClientForge.resetTimer();
        String modeDesc = "popup".equals(mode) ? "Popup" : "NPC";
        source.sendSuccess(() -> gold("Quiz mode set to: " + modeDesc), false);
        return 1;
    }

    private static int setGlobalOperation(CommandSourceStack source, String op) {
        if (isRemoteMultiplayer()) return rejectIfMultiplayer(source);
        MathQuestConfig.INSTANCE.operation = MathQuestConfig.normalizeOperation(op);
        MathQuestConfig.INSTANCE.save();
        source.sendSuccess(() -> gold("Default operation set to " + MathQuestConfig.INSTANCE.operation + "."), false);
        return 1;
    }

    private static int setGlobalRange(CommandSourceStack source, int min, int max) {
        if (isRemoteMultiplayer()) return rejectIfMultiplayer(source);
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

    private static int setRewardGroup(CommandSourceStack source, String name) {
        if (isRemoteMultiplayer()) return rejectIfMultiplayer(source);
        ensureRewardGroups();
        String key = MathQuestConfig.normalizeGroupName(name);
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
        if (isRemoteMultiplayer()) return rejectIfMultiplayer(source);
        MathQuestConfig.INSTANCE.rewardGroup = null;
        MathQuestConfig.INSTANCE.save();
        source.sendSuccess(() -> gold("Using flat reward list."), false);
        return 1;
    }

    private static int vanishNerds(CommandSourceStack source) {
        Minecraft client = Minecraft.getInstance();
        if (client == null || client.getSingleplayerServer() == null) {
            source.sendFailure(Component.literal("[MathQuest] ")
                .withStyle(ChatFormatting.GOLD)
                .append(Component.literal(
                    "On a dedicated server, use mathquest vanishnerds in the server console (op required).")
                    .withStyle(ChatFormatting.RED)));
            return 0;
        }
        var server = client.getSingleplayerServer();
        server.execute(() -> {
            int count = MathQuestNerdDespawnForge.vanishAllInOverworld(server.overworld());
            int fCount = count;
            source.sendSuccess(() -> gold(
                "Removed " + fCount + " Wandering Nerd" + (fCount == 1 ? "" : "s") + " from the overworld."), false);
        });
        return 1;
    }

    private static int startQuiz(CommandSourceStack source) {
        Minecraft client = Minecraft.getInstance();
        if ("npc".equals(MathQuestConfig.INSTANCE.quizMode)) {
            if (client == null || client.getSingleplayerServer() == null || client.player == null) {
                source.sendFailure(Component.literal("[MathQuest] ")
                    .withStyle(ChatFormatting.GOLD)
                    .append(Component.literal(
                        "On a dedicated server, nerds spawn on the server. "
                            + "As an op, use /mathquest start (or ask the host to run "
                            + "mathquest start <yourname> in the server console).")
                        .withStyle(ChatFormatting.RED)));
                return 0;
            }
            var server = client.getSingleplayerServer();
            var serverPlayer = server.getPlayerList().getPlayer(client.player.getUUID());
            if (serverPlayer == null) {
                source.sendFailure(Component.literal("[MathQuest] ")
                    .withStyle(ChatFormatting.GOLD)
                    .append(Component.literal("Could not find server player.").withStyle(ChatFormatting.RED)));
                return 0;
            }
            server.execute(() -> MathQuestForge.getNerdSpawner().forceSpawn(server.overworld(), serverPlayer));
            source.sendSuccess(() -> gold("Spawning the Wandering Nerd nearby..."), false);
            return 1;
        }
        if (client != null) {
            client.execute(() -> client.setScreen(new QuizOfferScreenForge()));
        }
        source.sendSuccess(() -> gold("Opening quiz..."), false);
        return 1;
    }

    private static int setEnabled(CommandSourceStack source, boolean enabled) {
        if (isRemoteMultiplayer()) return rejectIfMultiplayer(source);
        MathQuestConfig.INSTANCE.enabled = enabled;
        MathQuestConfig.INSTANCE.save();
        if (enabled) {
            MathQuestClientForge.resetTimer();
        }
        source.sendSuccess(() -> gold(enabled ? "Quizzes enabled!" : "Quizzes disabled."), false);
        return 1;
    }

    /** Client-local freeze workaround; intentionally allowed in multiplayer. */
    private static int setMultipartProjectileFix(CommandSourceStack source, boolean enabled) {
        MathQuestConfig.INSTANCE.excludeMultipartFromClientProjectileHits = enabled;
        MathQuestConfig.INSTANCE.save();
        source.sendSuccess(() -> gold("Multipart projectile fix "
            + (enabled ? "ON" : "OFF")
            + " (client-only; skips dragon/part hitboxes for local projectile tests)."), false);
        return 1;
    }

    private static int showMultipartProjectileFix(CommandSourceStack source) {
        boolean on = MathQuestConfig.INSTANCE != null
            && MathQuestConfig.INSTANCE.excludeMultipartFromClientProjectileHits;
        source.sendSuccess(() -> gold("Multipart projectile fix is "
            + (on ? "ON" : "OFF")
            + ". Toggle: /mathquest multipartProjectileFix on|off"), false);
        return 1;
    }

    private static int showStatus(CommandSourceStack source) {
        if (isRemoteMultiplayer()) {
            source.sendSuccess(() -> Component.literal("[MathQuest] ")
                .withStyle(ChatFormatting.GOLD)
                .append(Component.literal(
                    "Connected to a multiplayer server. Run 'mathquest status' from the server "
                        + "console for active settings.")
                    .withStyle(ChatFormatting.YELLOW)), false);
            return 1;
        }
        MathQuestConfig config = MathQuestConfig.INSTANCE;
        source.sendSuccess(() -> Component.literal("--- MathQuest Status ---").withStyle(ChatFormatting.GOLD), false);
        source.sendSuccess(() -> line("Enabled", config.enabled ? "Yes" : "No"), false);
        source.sendSuccess(() -> line("Mode", "popup".equals(config.quizMode) ? "Popup" : "NPC"), false);
        source.sendSuccess(() -> line("Interval", MathQuestDurationFormat.forStatus(config.quizIntervalSeconds)), false);
        appendNextQuizStatus(source);
        source.sendSuccess(() -> line(MathQuizDbPaths.SINGLE_DB_DIR_LABEL, config.resolveMathQuizSingleDbDir().toString()), false);
        source.sendSuccess(() -> line(MathQuizDbPaths.ACTIVE_DB_DIR_LABEL, config.resolveMathQuizActiveDbDir().toString()), false);
        return 1;
    }

    private static void appendNextQuizStatus(CommandSourceStack source) {
        Minecraft client = Minecraft.getInstance();
        if (client == null || client.player == null) return;
        for (QuizDeliveryPreview.StatusLine line : QuizDeliveryPreview.statusLinesForPlayer(
            client.player.getName().getString())) {
            ChatFormatting valueColor = line.error() ? ChatFormatting.RED : ChatFormatting.WHITE;
            source.sendSuccess(() -> Component.literal("  " + line.label() + ": ").withStyle(ChatFormatting.GRAY)
                .append(Component.literal(line.value()).withStyle(valueColor)), false);
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
