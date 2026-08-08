package net.minecraft.client.gui.widget;

import net.minecraft.text.Text;

public class ButtonWidget {
    public static Builder builder(Text message, PressAction onPress) {
        return new Builder();
    }

    @FunctionalInterface
    public interface PressAction {
        void onPress(ButtonWidget button);
    }

    public static class Builder {
        public Builder dimensions(int x, int y, int width, int height) { return this; }
        public ButtonWidget build() { return new ButtonWidget(); }
    }
}
