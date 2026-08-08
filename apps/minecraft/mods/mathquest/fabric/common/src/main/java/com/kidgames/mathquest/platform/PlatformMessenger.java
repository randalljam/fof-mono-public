package com.kidgames.mathquest.platform;

/** Loader-specific player chat messages from shared logic. */
public final class PlatformMessenger {
    public interface Sender {
        void send(PlayerContext player, String message);
    }

    private static Sender sender = (player, message) ->
        MathQuestLog.LOGGER.info("[MathQuest] (no chat sender) {}", message);

    private PlatformMessenger() {}

    public static void setSender(Sender newSender) {
        sender = newSender == null ? (player, message) -> {} : newSender;
    }

    public static void send(PlayerContext player, String message) {
        if (message == null || message.isBlank()) return;
        sender.send(player, message);
    }
}
