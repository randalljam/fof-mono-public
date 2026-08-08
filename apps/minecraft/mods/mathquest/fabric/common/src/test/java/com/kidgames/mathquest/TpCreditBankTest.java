package com.kidgames.mathquest;

import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.reward.TpCreditBank;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class TpCreditBankTest {
    @Test
    void completedQuizDoesNotAwardOrSaveWhenEarningIsDisabled() {
        CountingConfig config = new CountingConfig();
        TpCreditBank bank = new TpCreditBank(config);

        TpCreditBank.AwardResult result = bank.awardCompletedQuiz("WildPetal");

        assertFalse(result.awarded());
        assertEquals(0, result.creditsAwarded());
        assertEquals(0, result.balance());
        assertFalse(result.persistenceFailed());
        assertEquals(0, config.saveCalls);
    }

    @Test
    void completedQuizAwardsConfiguredCreditsAndPersistsOnce() {
        CountingConfig config = new CountingConfig();
        config.playerTpCreditEarningEnabled.put("WiLdPeTaL", true);
        config.playerTpCreditsPerQuiz.put("WILDPETAL", 4);
        config.playerTpCreditBalances.put("wildPETAL", 2);
        TpCreditBank bank = new TpCreditBank(config);

        TpCreditBank.AwardResult result = bank.awardCompletedQuiz("wildpetal");

        assertTrue(result.awarded());
        assertEquals(4, result.creditsAwarded());
        assertEquals(6, result.balance());
        assertFalse(result.persistenceFailed());
        assertEquals(6, bank.balance("WILDPETAL"));
        assertEquals(1, config.saveCalls);
        assertTrue(config.playerTpCreditBalances.containsKey("wildpetal"));
    }

    @Test
    void teleportSpendFailsWithoutCreditAndDoesNotSave() {
        CountingConfig config = new CountingConfig();
        TpCreditBank bank = new TpCreditBank(config);

        TpCreditBank.SpendResult result = bank.spendTeleportCredit("PumaJockey");

        assertFalse(result.spent());
        assertEquals(0, result.balance());
        assertFalse(result.persistenceFailed());
        assertEquals(0, config.saveCalls);
    }

    @Test
    void teleportSpendAtomicallyDeductsOneAndPersistsOnce() {
        CountingConfig config = new CountingConfig();
        config.setTpCreditBalance("PumaJockey", 2);
        TpCreditBank bank = new TpCreditBank(config);

        TpCreditBank.SpendResult result = bank.spendTeleportCredit("pumajockey");

        assertTrue(result.spent());
        assertEquals(1, result.balance());
        assertFalse(result.persistenceFailed());
        assertEquals(1, bank.balance("PUMAJOCKEY"));
        assertEquals(1, config.saveCalls);
    }

    private static final class CountingConfig extends MathQuestConfig {
        private int saveCalls;

        @Override
        public boolean saveChecked() {
            saveCalls++;
            return true;
        }
    }

    @Test
    void failedAwardSaveRollsBackBalanceAndReportsFailure() {
        FailingConfig config = new FailingConfig();
        config.setTpCreditEarningEnabled("WildPetal", true);
        config.setTpCreditBalance("WildPetal", 3);

        TpCreditBank.AwardResult result = new TpCreditBank(config).awardCompletedQuiz("WildPetal");

        assertFalse(result.awarded());
        assertTrue(result.persistenceFailed());
        assertEquals(3, result.balance());
        assertEquals(3, config.resolveTpCreditBalance("WildPetal"));
    }

    @Test
    void failedSpendSaveRollsBackBalanceAndReportsFailure() {
        FailingConfig config = new FailingConfig();
        config.setTpCreditBalance("PumaJockey", 2);

        TpCreditBank.SpendResult result = new TpCreditBank(config).spendTeleportCredit("PumaJockey");

        assertFalse(result.spent());
        assertTrue(result.persistenceFailed());
        assertEquals(2, result.balance());
        assertEquals(2, config.resolveTpCreditBalance("PumaJockey"));
    }

    private static final class FailingConfig extends MathQuestConfig {
        @Override
        public boolean saveChecked() {
            return false;
        }
    }
}
