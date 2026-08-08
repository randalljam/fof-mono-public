package com.kidgames.mathquest.reward;

import com.kidgames.mathquest.config.MathQuestConfig;

import java.util.Objects;

/**
 * Persistent, loader-neutral TP-credit economy.
 *
 * <p>Mutations synchronize on the config so separate loader services cannot award or spend the
 * same balance concurrently. The config is saved exactly once after a successful balance change.
 */
public final class TpCreditBank {
    private final MathQuestConfig config;

    public TpCreditBank(MathQuestConfig config) {
        this.config = Objects.requireNonNull(config, "config");
    }

    /** Awards the configured credits for a completed quiz when earning is enabled for the player. */
    public AwardResult awardCompletedQuiz(String playerName) {
        synchronized (config) {
            int currentBalance = config.resolveTpCreditBalance(playerName);
            if (!config.resolveTpCreditEarningEnabled(playerName)) {
                return new AwardResult(false, 0, currentBalance, false);
            }
            int requested = config.resolveTpCreditsPerQuiz(playerName);
            int updatedBalance = (int) Math.min(Integer.MAX_VALUE, (long) currentBalance + requested);
            int awarded = updatedBalance - currentBalance;
            if (awarded <= 0) {
                return new AwardResult(false, 0, currentBalance, false);
            }
            config.setTpCreditBalance(playerName, updatedBalance);
            if (!config.saveChecked()) {
                config.setTpCreditBalance(playerName, currentBalance);
                return new AwardResult(false, 0, currentBalance, true);
            }
            return new AwardResult(true, awarded, updatedBalance, false);
        }
    }

    /** Atomically spends one credit for the currently supported teleport reward. */
    public SpendResult spendTeleportCredit(String playerName) {
        synchronized (config) {
            int currentBalance = config.resolveTpCreditBalance(playerName);
            if (currentBalance < 1) {
                return new SpendResult(false, currentBalance, false);
            }
            int updatedBalance = currentBalance - 1;
            config.setTpCreditBalance(playerName, updatedBalance);
            if (!config.saveChecked()) {
                config.setTpCreditBalance(playerName, currentBalance);
                return new SpendResult(false, currentBalance, true);
            }
            return new SpendResult(true, updatedBalance, false);
        }
    }

    public int balance(String playerName) {
        synchronized (config) {
            return config.resolveTpCreditBalance(playerName);
        }
    }

    public record AwardResult(boolean awarded, int creditsAwarded, int balance, boolean persistenceFailed) {}

    public record SpendResult(boolean spent, int balance, boolean persistenceFailed) {}
}
