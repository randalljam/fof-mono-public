package com.mojang.brigadier.builder;

import com.mojang.brigadier.Command;

@SuppressWarnings("unchecked")
public abstract class ArgumentBuilder<S, T extends ArgumentBuilder<S, T>> {
    public T then(ArgumentBuilder<S, ?> argument) { return (T) this; }
    public T executes(Command<S> command) { return (T) this; }
}
