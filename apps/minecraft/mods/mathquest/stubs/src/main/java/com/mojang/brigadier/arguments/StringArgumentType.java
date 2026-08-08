package com.mojang.brigadier.arguments;

import com.mojang.brigadier.context.CommandContext;

public class StringArgumentType implements ArgumentType<String> {
    public static StringArgumentType string() { return new StringArgumentType(); }

    public static String getString(CommandContext<?> context, String name) { return ""; }
}
