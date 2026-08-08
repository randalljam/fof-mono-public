package com.kidgames.mathquest.screen;

import com.kidgames.mathquest.MathQuestMod;
import com.kidgames.mathquest.config.MathQuestConfig;
import net.minecraft.ChatFormatting;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.components.CycleButton;
import net.minecraft.client.gui.components.StringWidget;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * Per-player preset editor: one row per player with operation cycle and min/max
 * adjusters. Reachable from {@link ControlPanelScreen} via "Edit Player Presets".
 *
 * <p>Same 1.21.11 API constraints as {@link ControlPanelScreen}:
 * {@code CycleButton.builder} takes (stringifier, initialValue) and {@code StringWidget}
 * has no {@code alignCenter()/alignLeft()} methods, so labels are exact-fit and
 * positioned manually.
 */
public class PlayerSettingsScreen extends Screen {

    /** First entry is the "use global default" sentinel. */
    private static final List<String> OP_OPTIONS = List.of("(default)", "addition", "subtraction", "multiplication", "exponentiation");

    private final Screen parent;

    public PlayerSettingsScreen(Screen parent) {
        super(Component.literal("MathQuest - Player Presets"));
        this.parent = parent;
    }

    @Override
    protected void init() {
        MathQuestConfig cfg = MathQuestMod.CONFIG;
        if (cfg.playerPresets == null) cfg.playerPresets = new LinkedHashMap<>();

        int centerX = this.width / 2;
        int rowW = 420;
        int rowH = 22;
        int gap = 4;
        int y = 14;

        addRenderableWidget(centeredLabel(centerX, y, "MathQuest - Player Presets",
            ChatFormatting.GOLD, ChatFormatting.BOLD));
        y += 18;
        addRenderableWidget(centeredLabel(centerX, y,
            "Per-player overrides; (default) inherits from global settings",
            ChatFormatting.GRAY));
        y += 16;

        // Column header strip (purely informative).
        int rowX = centerX - rowW / 2;
        int nameW = 90;
        int opW = 130;
        int rangeBtnW = 30;
        int clearW = 60;
        int rangeLabelW = 60;

        addRenderableWidget(positionedLabel(rowX, y, "Player",
            ChatFormatting.GRAY, ChatFormatting.UNDERLINE));
        addRenderableWidget(positionedLabel(rowX + nameW + gap, y, "Operation",
            ChatFormatting.GRAY, ChatFormatting.UNDERLINE));
        addRenderableWidget(positionedLabel(rowX + nameW + gap + opW + gap, y, "Range (min / max)",
            ChatFormatting.GRAY, ChatFormatting.UNDERLINE));
        addRenderableWidget(positionedLabel(rowX + rowW - clearW, y, "Action",
            ChatFormatting.GRAY, ChatFormatting.UNDERLINE));
        y += 14;

        if (cfg.playerPresets.isEmpty()) {
            addRenderableWidget(centeredLabel(centerX, y,
                "(no per-player presets - every player uses global defaults)",
                ChatFormatting.DARK_GRAY));
            y += rowH;
        } else {
            // Snapshot keys to avoid concurrent modification when a row mutates the map.
            List<String> names = new ArrayList<>(cfg.playerPresets.keySet());
            for (String name : names) {
                MathQuestConfig.PlayerQuizPreset preset = cfg.playerPresets.get(name);
                if (preset == null) continue;
                buildRow(rowX, y, nameW, opW, rangeBtnW, rangeLabelW, clearW, gap,
                    name, preset, cfg);
                y += rowH;
            }
        }

        // Bottom action row
        int bottomY = this.height - 30;
        addRenderableWidget(Button.builder(Component.literal("Add Me"), b -> {
            String pname = currentPlayerName();
            if (pname != null && !pname.isBlank()) {
                String key = pname.toLowerCase(Locale.ROOT);
                cfg.playerPresets.computeIfAbsent(key, k -> new MathQuestConfig.PlayerQuizPreset());
                cfg.save();
                rebuild();
            }
        }).bounds(centerX - 200, bottomY, 120, 20).build());

        addRenderableWidget(Button.builder(Component.literal("Add Default Family"), b -> {
            ensureFamilyDefaults(cfg.playerPresets);
            cfg.save();
            rebuild();
        }).bounds(centerX - 70, bottomY, 140, 20).build());

        addRenderableWidget(Button.builder(Component.literal("Back"), b -> onClose())
            .bounds(centerX + 80, bottomY, 120, 20).build());
    }

    private void buildRow(int rowX, int y, int nameW, int opW, int rangeBtnW, int rangeLabelW,
                          int clearW, int gap, String name, MathQuestConfig.PlayerQuizPreset preset,
                          MathQuestConfig cfg) {
        // Name label
        addRenderableWidget(positionedLabel(rowX, y + 6, name, ChatFormatting.AQUA));

        // Operation cycle
        String currOp = (preset.operation == null || preset.operation.isBlank())
            ? "(default)"
            : MathQuestConfig.normalizeOperation(preset.operation);
        if (!OP_OPTIONS.contains(currOp)) currOp = "(default)";
        addRenderableWidget(CycleButton.<String>builder(
                s -> Component.literal(prettyOpShort(s)),
                currOp)
            .withValues(OP_OPTIONS)
            .displayOnlyValue()
            .create(rowX + nameW + gap, y, opW, 20,
                Component.literal("Operation"),
                (b, v) -> {
                    preset.operation = "(default)".equals(v) ? null : v;
                    cfg.save();
                }));

        // Range controls: [Min-][Min+]  (label)  [K2-][K2+]
        int rx = rowX + nameW + gap + opW + gap;
        addRenderableWidget(Button.builder(Component.literal("-"), b -> {
            ensureRange(preset, cfg);
            preset.minNumber = preset.minNumber - 1;
            cfg.save();
            rebuild();
        }).bounds(rx, y, rangeBtnW, 20).build());
        addRenderableWidget(Button.builder(Component.literal("+"), b -> {
            ensureRange(preset, cfg);
            preset.minNumber = preset.minNumber + 1;
            if (preset.minNumber > preset.maxNumber) preset.minNumber = preset.maxNumber;
            cfg.save();
            rebuild();
        }).bounds(rx + rangeBtnW + gap, y, rangeBtnW, 20).build());

        String rangeText = (preset.minNumber != null && preset.maxNumber != null)
            ? (preset.minNumber + " - " + preset.maxNumber)
            : "default";
        addRenderableWidget(positionedLabel(rx + (rangeBtnW + gap) * 2, y + 6,
            rangeText, ChatFormatting.WHITE));

        int rx2 = rx + (rangeBtnW + gap) * 2 + rangeLabelW + gap;
        addRenderableWidget(Button.builder(Component.literal("-"), b -> {
            ensureRange(preset, cfg);
            preset.maxNumber = preset.maxNumber - 1;
            if (preset.maxNumber < preset.minNumber) preset.maxNumber = preset.minNumber;
            cfg.save();
            rebuild();
        }).bounds(rx2, y, rangeBtnW, 20).build());
        addRenderableWidget(Button.builder(Component.literal("+"), b -> {
            ensureRange(preset, cfg);
            preset.maxNumber = preset.maxNumber + 1;
            cfg.save();
            rebuild();
        }).bounds(rx2 + rangeBtnW + gap, y, rangeBtnW, 20).build());

        // Clear (remove this preset entry)
        addRenderableWidget(Button.builder(Component.literal("Remove"), b -> {
            cfg.playerPresets.remove(name);
            cfg.save();
            rebuild();
        }).bounds(rowX + (nameW + gap + opW + gap + (rangeBtnW + gap) * 4 + rangeLabelW + gap),
            y, clearW, 20).build());
    }

    private static void ensureRange(MathQuestConfig.PlayerQuizPreset preset, MathQuestConfig cfg) {
        if (preset.minNumber == null) preset.minNumber = cfg.minNumber;
        if (preset.maxNumber == null) preset.maxNumber = cfg.maxNumber;
    }

    private static void ensureFamilyDefaults(Map<String, MathQuestConfig.PlayerQuizPreset> map) {
        map.computeIfAbsent("wildpetal", k -> new MathQuestConfig.PlayerQuizPreset(5, 9, "multiplication"));
        map.computeIfAbsent("treasurehunterm", k -> new MathQuestConfig.PlayerQuizPreset(0, 3, "addition"));
        map.computeIfAbsent("pumajockey", k -> new MathQuestConfig.PlayerQuizPreset(0, 4, "exponentiation"));
    }

    private void rebuild() {
        clearWidgets();
        init();
    }

    private static String currentPlayerName() {
        var c = Minecraft.getInstance();
        return (c.player == null) ? null : c.player.getName().getString();
    }

    private static String prettyOpShort(String op) {
        return switch (op) {
            case "addition" -> "Addition (+)";
            case "subtraction" -> "Subtraction (-)";
            case "multiplication" -> "Multiplication (x)";
            case "exponentiation" -> "Exponent (^)";
            default -> "(default)";
        };
    }

    /** Exact-fit StringWidget centered on {@code centerX}. See ControlPanelScreen for why. */
    private StringWidget centeredLabel(int centerX, int y, String text, ChatFormatting... fmt) {
        MutableComponent c = Component.literal(text);
        for (ChatFormatting f : fmt) c = c.withStyle(f);
        int w = this.font.width(text) + 2;
        return new StringWidget(centerX - w / 2, y, w, 12, c, this.font);
    }

    /** Exact-fit StringWidget anchored at left edge {@code x}. */
    private StringWidget positionedLabel(int x, int y, String text, ChatFormatting... fmt) {
        MutableComponent c = Component.literal(text);
        for (ChatFormatting f : fmt) c = c.withStyle(f);
        int w = this.font.width(text) + 2;
        return new StringWidget(x, y, w, 12, c, this.font);
    }

    @Override
    public void onClose() {
        Minecraft.getInstance().setScreen(parent);
    }

    @Override
    public boolean isPauseScreen() {
        return true;
    }
}
