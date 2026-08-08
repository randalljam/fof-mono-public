package com.kidgames.mathquest.client;

import com.kidgames.mathquest.platform.MathQuestPaths;
import net.fabricmc.fabric.api.client.screen.v1.ScreenEvents;
import net.minecraft.SharedConstants;
import net.minecraft.client.gui.screens.TitleScreen;

/** 26.1 title-screen overlay ({@link net.minecraft.client.gui.GuiGraphicsExtractor} API). */
public final class MathQuestTitleScreenOverlay {
    private static final int COLOR = 0xFFC0C0C0;
    private static final int Y_OFFSET = 10;

    private MathQuestTitleScreenOverlay() {}

    public static void register() {
        ScreenEvents.AFTER_INIT.register((client, screen, scaledWidth, scaledHeight) -> {
            if (!(screen instanceof TitleScreen)) return;
            ScreenEvents.afterExtract(screen).register((scr, graphics, mouseX, mouseY, delta) -> {
                String text = MathQuestPaths.titleScreenVersionLabel(
                    SharedConstants.getCurrentVersion().id());
                int textWidth = client.font.width(text);
                int x = (scr.width - textWidth) / 2;
                graphics.text(client.font, text, x, scr.height - Y_OFFSET, COLOR, false);
            });
        });
    }
}
