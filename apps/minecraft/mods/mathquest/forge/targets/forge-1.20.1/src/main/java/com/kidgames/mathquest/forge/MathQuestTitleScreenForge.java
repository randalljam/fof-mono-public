package com.kidgames.mathquest.forge;

import com.kidgames.mathquest.platform.MathQuestPaths;
import net.minecraft.SharedConstants;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.TitleScreen;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.ScreenEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

@Mod.EventBusSubscriber(modid = MathQuestForge.MOD_ID, bus = Mod.EventBusSubscriber.Bus.FORGE, value = Dist.CLIENT)
public final class MathQuestTitleScreenForge {
    private static final int COLOR = 0xFFC0C0C0;
    private static final int Y_OFFSET = 10;

    private MathQuestTitleScreenForge() {}

    @SubscribeEvent
    public static void onTitleScreenRender(ScreenEvent.Render.Post event) {
        if (!(event.getScreen() instanceof TitleScreen screen)) return;
        var font = Minecraft.getInstance().font;
        String text = MathQuestPaths.titleScreenVersionLabel(
            SharedConstants.getCurrentVersion().getName());
        int textWidth = font.width(text);
        int x = (screen.width - textWidth) / 2;
        event.getGuiGraphics().drawString(font, text, x, screen.height - Y_OFFSET, COLOR, false);
    }
}
