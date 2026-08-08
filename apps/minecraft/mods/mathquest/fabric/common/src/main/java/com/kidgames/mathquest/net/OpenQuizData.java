package com.kidgames.mathquest.net;

public record OpenQuizData(
    String operation,
    int minNumber,
    int maxNumber,
    int problemsPerQuiz,
    String problemsJson,
    String rewardsJson,
    String rewardMode,
    String quizType,
    String optionsJson,
    boolean fluencyFeastMode,
    boolean directToQuiz
) {}
