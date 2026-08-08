package com.kidgames.mathquest;

import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.reward.TpCreditBank;
import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.DoubleArgumentType;
import com.mojang.brigadier.arguments.StringArgumentType;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;

import java.util.Set;

/** Player-accessible, credit-backed teleport commands. Vanilla {@code /tp} is untouched. */
public final class TpCreditCommands {
    private TpCreditCommands() {}

    public static void register(CommandDispatcher<CommandSourceStack> dispatcher) {
        dispatcher.register(Commands.literal("tpc")
            .requires(CommandSourceStack::isPlayer)
            .then(Commands.argument("target", StringArgumentType.word())
                .executes(ctx -> teleportToNamedPlayer(
                    ctx.getSource(),
                    StringArgumentType.getString(ctx, "target")
                )))
            .then(Commands.argument("x", DoubleArgumentType.doubleArg())
                .then(Commands.argument("y", DoubleArgumentType.doubleArg())
                    .then(Commands.argument("z", DoubleArgumentType.doubleArg())
                        .executes(ctx -> teleportToCoordinates(
                            ctx.getSource(),
                            DoubleArgumentType.getDouble(ctx, "x"),
                            DoubleArgumentType.getDouble(ctx, "y"),
                            DoubleArgumentType.getDouble(ctx, "z")
                        ))))));

        registerShortcut(dispatcher, "tpt", "TreasureHunterM");
        registerShortcut(dispatcher, "tpp", "PumaJockey");
        registerShortcut(dispatcher, "tpr", "RJComp");
        registerShortcut(dispatcher, "tpw", "WildPetal");
    }

    private static void registerShortcut(
        CommandDispatcher<CommandSourceStack> dispatcher,
        String command,
        String targetName
    ) {
        dispatcher.register(Commands.literal(command)
            .requires(CommandSourceStack::isPlayer)
            .executes(ctx -> teleportToNamedPlayer(ctx.getSource(), targetName)));
    }

    private static int teleportToNamedPlayer(CommandSourceStack source, String requestedName) {
        ServerPlayer player = source.getPlayer();
        if (player == null) return 0;
        ServerPlayer target = source.getServer().getPlayerList().getPlayers().stream()
            .filter(candidate -> candidate.getName().getString().equalsIgnoreCase(requestedName))
            .findFirst()
            .orElse(null);
        if (target == null) {
            source.sendFailure(Component.literal("[MathQuest] Player \"" + requestedName + "\" is not online. No TP credit spent."));
            return 0;
        }
        if (target == player) {
            source.sendFailure(Component.literal("[MathQuest] Choose another online player. No TP credit spent."));
            return 0;
        }

        ServerLevel destinationLevel = (ServerLevel) target.level();
        return teleportAndSpend(
            source,
            player,
            destinationLevel,
            target.getX(),
            target.getY(),
            target.getZ(),
            target.getYRot(),
            target.getXRot(),
            target.getName().getString()
        );
    }

    private static int teleportToCoordinates(CommandSourceStack source, double x, double y, double z) {
        ServerPlayer player = source.getPlayer();
        if (player == null) return 0;
        ServerLevel level = (ServerLevel) player.level();
        if (!validDestination(level, x, y, z)) {
            source.sendFailure(Component.literal("[MathQuest] Those coordinates are outside the valid world bounds. No TP credit spent."));
            return 0;
        }
        return teleportAndSpend(
            source,
            player,
            level,
            x,
            y,
            z,
            player.getYRot(),
            player.getXRot(),
            formatCoordinates(x, y, z)
        );
    }

    private static int teleportAndSpend(
        CommandSourceStack source,
        ServerPlayer player,
        ServerLevel level,
        double x,
        double y,
        double z,
        float yaw,
        float pitch,
        String destinationLabel
    ) {
        MathQuestConfig config = MathQuestMod.CONFIG;
        String playerName = player.getName().getString();
        synchronized (config) {
            if (!"teleport".equals(config.resolveTpCreditRewardChoice(playerName))) {
                source.sendFailure(Component.literal("[MathQuest] Your selected TP-credit reward is not teleport. No credit spent."));
                return 0;
            }

            TpCreditBank bank = new TpCreditBank(config);
            int balance = bank.balance(playerName);
            if (balance < 1) {
                source.sendFailure(Component.literal("[MathQuest] You need 1 TP credit to teleport. Balance: " + balance + "."));
                return 0;
            }

            boolean teleported = player.teleportTo(level, x, y, z, Set.of(), yaw, pitch, true);
            if (!teleported) {
                source.sendFailure(Component.literal("[MathQuest] Teleport failed. No TP credit spent."));
                return 0;
            }

            TpCreditBank.SpendResult spent = bank.spendTeleportCredit(playerName);
            if (!spent.spent()) {
                String reason = spent.persistenceFailed()
                    ? "the updated balance could not be saved; balance was restored to "
                    : "the TP credit could not be deducted; balance is ";
                source.sendFailure(Component.literal("[MathQuest] Teleport completed, but " + reason
                    + spent.balance() + "."));
                return 0;
            }
            source.sendSuccess(() -> Component.literal("[MathQuest] Teleported to " + destinationLabel
                + ". Spent 1 TP credit. Remaining: " + spent.balance() + "."), false);
            return 1;
        }
    }

    private static boolean validDestination(ServerLevel level, double x, double y, double z) {
        if (!Double.isFinite(x) || !Double.isFinite(y) || !Double.isFinite(z)) return false;
        if (Math.abs(x) > 29_999_984 || Math.abs(z) > 29_999_984) return false;
        return level.isInWorldBounds(BlockPos.containing(x, y, z));
    }

    private static String formatCoordinates(double x, double y, double z) {
        return String.format(java.util.Locale.ROOT, "%.1f, %.1f, %.1f", x, y, z);
    }
}
