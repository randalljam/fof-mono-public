package net.minecraft.client.gui;

import net.minecraft.client.font.TextRenderer;

public class DrawContext {
    public MatrixStack getMatrices() { return new MatrixStack(); }

    public void drawText(TextRenderer renderer, String text, int x, int y, int color, boolean shadow) {}

    public static class MatrixStack {
        public void pushMatrix() {}
        public void popMatrix() {}
        public void translate(float x, float y) {}
        public void translate(int x, int y) {}
        public void scale(float x, float y) {}
    }
}
