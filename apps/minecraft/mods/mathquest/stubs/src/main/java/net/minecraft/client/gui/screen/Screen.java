package net.minecraft.client.gui.screen;

import net.minecraft.client.MinecraftClient;
import net.minecraft.client.font.TextRenderer;
import net.minecraft.client.gui.widget.ButtonWidget;
import net.minecraft.client.input.KeyInput;
import net.minecraft.text.Text;

public class Screen {
    protected int width;
    protected int height;
    protected MinecraftClient client;
    protected TextRenderer textRenderer = new TextRenderer();

    protected Screen(Text title) {}

    protected void init() {}

    public void render(net.minecraft.client.gui.DrawContext context, int mouseX, int mouseY, float delta) {}

    public void tick() {}

    public boolean keyPressed(KeyInput input) { return false; }

    public boolean shouldPause() { return false; }

    public boolean shouldCloseOnEsc() { return true; }

    protected <T extends ButtonWidget> T addDrawableChild(T widget) { return widget; }

    protected void clearChildren() {}

    public void close() {}
}
