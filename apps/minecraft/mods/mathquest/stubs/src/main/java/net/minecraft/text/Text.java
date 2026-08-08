package net.minecraft.text;

public interface Text {
    static MutableText literal(String content) {
        return new MutableText(content);
    }

    String getString();
}
