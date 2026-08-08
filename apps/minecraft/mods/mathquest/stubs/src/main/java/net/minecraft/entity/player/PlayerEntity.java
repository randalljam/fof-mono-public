package net.minecraft.entity.player;

import net.minecraft.sound.SoundEvent;
import net.minecraft.text.Text;

public class PlayerEntity {
    public PlayerInventory getInventory() { return new PlayerInventory(); }
    public void playSound(SoundEvent event, float volume, float pitch) {}
    public Text getName() { return Text.literal("Player"); }
}
