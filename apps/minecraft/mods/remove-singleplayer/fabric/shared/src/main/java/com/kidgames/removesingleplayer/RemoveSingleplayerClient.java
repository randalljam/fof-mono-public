package com.kidgames.removesingleplayer;

import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.screen.v1.ScreenEvents;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.screens.TitleScreen;
import net.minecraft.network.chat.contents.TranslatableContents;

/**
 * Hides the Singleplayer button on the main-menu TitleScreen. Pure client-side mod: no
 * server-side entrypoint, no payloads, no entities. Hooks the Fabric ScreenEvents
 * AFTER_INIT callback so the button list is already populated and the offending widget
 * can be removed before the first render.
 *
 * Walks {@code screen.children()} (vanilla Minecraft API, stable across versions)
 * rather than the Fabric API helper {@code Screens.getButtons()}, which was dropped
 * from Fabric API somewhere between the 1.21.x and 26.x release lines. The vanilla
 * children() list has always contained every {@code GuiEventListener} the screen
 * added via {@code addRenderableWidget}, so the buttons we want are reachable
 * without any Fabric API-specific helper.
 */
public class RemoveSingleplayerClient implements ClientModInitializer {

    private static final String SINGLEPLAYER_TRANSLATION_KEY = "menu.singleplayer";

    @Override
    public void onInitializeClient() {
        ScreenEvents.AFTER_INIT.register((client, screen, scaledWidth, scaledHeight) -> {
            if (!(screen instanceof TitleScreen)) {
                return;
            }
            for (var child : screen.children()) {
                if (child instanceof Button button && isSingleplayerButton(button)) {
                    button.visible = false;
                    button.active = false;
                }
            }
        });
    }

    private static boolean isSingleplayerButton(Button button) {
        var contents = button.getMessage().getContents();
        return contents instanceof TranslatableContents tc
            && SINGLEPLAYER_TRANSLATION_KEY.equals(tc.getKey());
    }
}
