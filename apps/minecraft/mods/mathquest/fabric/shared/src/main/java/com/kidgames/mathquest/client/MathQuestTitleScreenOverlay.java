package com.kidgames.mathquest.client;

import com.kidgames.mathquest.platform.MathQuestPaths;
import net.fabricmc.fabric.api.client.screen.v1.ScreenEvents;
import net.minecraft.SharedConstants;
import net.minecraft.client.gui.screens.TitleScreen;

/** Draws {@code MathQuest <version> + MC <mc>} on the title screen (bottom-center). */
public final class MathQuestTitleScreenOverlay {
    private static final int COLOR = 0xFFC0C0C0;
    private static final int Y_OFFSET = 10;

    private MathQuestTitleScreenOverlay() {}

    public static void register() {
        ScreenEvents.AFTER_INIT.register((client, screen, scaledWidth, scaledHeight) -> {
            if (!(screen instanceof TitleScreen)) return;
            ScreenEvents.afterRender(screen).register((scr, graphics, mouseX, mouseY, delta) -> {
                String text = MathQuestPaths.titleScreenVersionLabel(
                    SharedConstants.getCurrentVersion().id());
                int textWidth = client.font.width(text);
                int x = (scr.width - textWidth) / 2;
                graphics.drawString(client.font, text, x, scr.height - Y_OFFSET, COLOR, false);
            });
        });
    }
}
