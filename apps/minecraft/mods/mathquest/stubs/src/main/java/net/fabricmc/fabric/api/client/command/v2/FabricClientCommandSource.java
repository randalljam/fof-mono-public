package net.fabricmc.fabric.api.client.command.v2;

import net.minecraft.text.Text;

public interface FabricClientCommandSource {
    void sendFeedback(Text message);
}
