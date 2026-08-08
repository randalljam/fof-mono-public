package com.kidgames.mathquest.net;

public record FluencyFeastResultData(
    int beforePercent,
    int afterPercent,
    String rewardDescription,
    String rewardsJson,
    String rewardMode
) {
    public FluencyFeastResultData(int beforePercent, int afterPercent, String rewardDescription) {
        this(beforePercent, afterPercent, rewardDescription, "[]", "all");
    }
}
