package net.minecraft.text;

import net.minecraft.util.Formatting;

public class MutableText implements Text {
    private final String content;

    public MutableText(String content) {
        this.content = content;
    }

    public MutableText formatted(Formatting formatting) {
        return this;
    }

    public MutableText append(Text text) {
        return this;
    }

    @Override
    public String getString() {
        return content;
    }
}
