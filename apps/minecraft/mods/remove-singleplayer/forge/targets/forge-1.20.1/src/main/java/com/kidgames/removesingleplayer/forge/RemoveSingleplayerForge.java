package com.kidgames.removesingleplayer.forge;

import net.minecraft.client.gui.components.AbstractWidget;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.screens.TitleScreen;
import net.minecraft.network.chat.contents.TranslatableContents;
import net.minecraftforge.client.event.ScreenEvent;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.loading.FMLEnvironment;

/**
 * Forge entrypoint for remove-singleplayer on Minecraft 1.20.1. Listens for the
 * post-init ScreenEvent and, when the constructed Screen is the TitleScreen, hides
 * the Singleplayer button. Client-only — guarded by {@code FMLEnvironment.dist} so
 * a dedicated server with this jar present does nothing.
 */
@Mod("removesingleplayer")
public class RemoveSingleplayerForge {

    private static final String SINGLEPLAYER_TRANSLATION_KEY = "menu.singleplayer";

    public RemoveSingleplayerForge() {
        if (FMLEnvironment.dist.isClient()) {
            MinecraftForge.EVENT_BUS.register(this);
        }
    }

    @SubscribeEvent
    public void onScreenInit(ScreenEvent.Init.Post event) {
        if (!(event.getScreen() instanceof TitleScreen)) {
            return;
        }
        for (var listener : event.getListenersList()) {
            if (listener instanceof Button button && isSingleplayerButton(button)) {
                button.visible = false;
                button.active = false;
            } else if (listener instanceof AbstractWidget widget && isSingleplayerLabel(widget)) {
                widget.visible = false;
                widget.active = false;
            }
        }
    }

    private static boolean isSingleplayerButton(Button button) {
        var contents = button.getMessage().getContents();
        return contents instanceof TranslatableContents tc
            && SINGLEPLAYER_TRANSLATION_KEY.equals(tc.getKey());
    }

    private static boolean isSingleplayerLabel(AbstractWidget widget) {
        var msg = widget.getMessage();
        if (msg == null) return false;
        var contents = msg.getContents();
        return contents instanceof TranslatableContents tc
            && SINGLEPLAYER_TRANSLATION_KEY.equals(tc.getKey());
    }
}
