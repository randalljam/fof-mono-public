package com.kidgames.mathquest.util;

public final class MathQuestDurationFormat {
    private MathQuestDurationFormat() {}

    /** Full words for chat/status output (e.g. "5 minutes", "90 seconds"). */
    public static String forStatus(int totalSeconds) {
        if (totalSeconds >= 60 && totalSeconds % 60 == 0) {
            int minutes = totalSeconds / 60;
            return minutes + (minutes == 1 ? " minute" : " minutes");
        } else if (totalSeconds >= 60) {
            return (totalSeconds / 60) + "m " + (totalSeconds % 60) + "s";
        }
        return totalSeconds + (totalSeconds == 1 ? " second" : " seconds");
    }

    /** Compact labels for in-game control-panel sliders (e.g. "5 mins", "90s"). */
    public static String forCompactUi(int seconds) {
        if (seconds >= 60 && seconds % 60 == 0) {
            int minutes = seconds / 60;
            return minutes + (minutes == 1 ? " min" : " mins");
        }
        if (seconds >= 60) {
            return (seconds / 60) + "m " + (seconds % 60) + "s";
        }
        return seconds + "s";
    }
}
