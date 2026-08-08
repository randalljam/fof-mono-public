package com.mojang.brigadier.arguments;

import com.mojang.brigadier.context.CommandContext;

public class IntegerArgumentType implements ArgumentType<Integer> {
    public static IntegerArgumentType integer(int min) { return new IntegerArgumentType(); }
    public static IntegerArgumentType integer(int min, int max) { return new IntegerArgumentType(); }

    public static int getInteger(CommandContext<?> context, String name) { return 0; }
}
