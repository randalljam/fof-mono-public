package com.kidgames.mathquest.forge.screen;

import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.util.MathQuestDurationFormat;
import com.kidgames.mathquest.forge.MathQuestClientForge;
import com.kidgames.mathquest.forge.MathQuestForge;
import net.minecraft.ChatFormatting;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.components.CycleButton;
import net.minecraft.client.gui.components.StringWidget;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;

public class ControlPanelScreenForge extends Screen {
    private static final List<Integer> PROBLEM_OPTIONS = List.of(5, 10, 15);
    private static final List<Integer> INTERVAL_OPTIONS = List.of(15, 30, 60, 120, 300);
    private static final List<String> OPERATION_OPTIONS = List.of("addition", "subtraction", "multiplication", "exponentiation");
    private static final List<String> MODE_OPTIONS = List.of("popup", "npc");
    private static final List<String> SPAWN_TARGET_OPTIONS = List.of("all", "random", "one");
    private static final List<String> QUIZ_SOURCE_OPTIONS = List.of(
        "generated", "internal_problem_list", "internal_quick_quiz", "internal_fluency_feast");

    private final Screen parent;
    private CycleButton<String> operationBtn;
    private CycleButton<Integer> problemsBtn;
    private Button minMinusBtn;
    private Button minPlusBtn;
    private Button maxMinusBtn;
    private Button maxPlusBtn;

    public ControlPanelScreenForge(Screen parent) {
        super(Component.literal("MathQuest Control Panel"));
        this.parent = parent;
    }

    @Override
    protected void init() {
        MathQuestConfig cfg = MathQuestConfig.INSTANCE;
        if (cfg.playerPresets == null) cfg.playerPresets = new LinkedHashMap<>();
        if (cfg.rewardGroups == null) cfg.rewardGroups = new LinkedHashMap<>();
        if (cfg.playerInternalQuizSources == null) cfg.playerInternalQuizSources = new LinkedHashMap<>();
        if (cfg.playerUseInternalProblemLists == null) cfg.playerUseInternalProblemLists = new LinkedHashMap<>();

        int centerX = this.width / 2;
        int btnW = 140;
        int gap = 6;
        int colSpan = btnW * 2 + gap;
        int rowH = 22;
        int y = 14;

        addRenderableWidget(centeredLabel(centerX, y, "MathQuest Control Panel",
            ChatFormatting.GOLD, ChatFormatting.BOLD));
        y += 18;

        addRenderableWidget(centeredLabel(centerX, y, "-- Global Settings --", ChatFormatting.GRAY));
        y += 14;

        String quizSource = resolveQuizSourceForPanel(cfg);
        addRenderableWidget(CycleButton.<String>builder(ControlPanelScreenForge::quizSourceLabel)
            .withInitialValue(quizSource)
            .withValues(QUIZ_SOURCE_OPTIONS)
            .create(centerX - btnW - gap / 2, y, colSpan, 20,
                Component.literal("Quiz Source"),
                (b, v) -> {
                    String pname = currentPlayerName();
                    if (pname != null && !pname.isBlank()) {
                        String key = pname.toLowerCase(Locale.ROOT);
                        cfg.playerInternalQuizSources.put(key, v);
                        cfg.playerUseInternalProblemLists.put(key, "internal_problem_list".equals(v));
                        cfg.save();
                        applyInternalSourceControls(v, operationBtn, problemsBtn,
                            minMinusBtn, minPlusBtn, maxMinusBtn, maxPlusBtn);
                    }
                }));
        y += rowH;

        addRenderableWidget(CycleButton.onOffBuilder(cfg.enabled)
            .create(centerX - btnW - gap / 2, y, btnW, 20,
                Component.literal("Quizzes Enabled"),
                (b, v) -> {
                    cfg.enabled = v;
                    cfg.save();
                    if (v) MathQuestClientForge.resetTimer();
                }));
        addRenderableWidget(CycleButton.<String>builder(
                s -> Component.literal("popup".equals(s) ? "Popup" : "Wandering Nerd"))
            .withInitialValue("npc".equals(cfg.quizMode) ? "npc" : "popup")
            .withValues(MODE_OPTIONS)
            .create(centerX + gap / 2, y, btnW, 20,
                Component.literal("Quiz Mode"),
                (b, v) -> {
                    cfg.quizMode = v;
                    cfg.save();
                    MathQuestClientForge.resetTimer();
                }));
        y += rowH;

        operationBtn = CycleButton.<String>builder(
                op -> Component.literal(prettyOp(op)))
            .withInitialValue(MathQuestConfig.normalizeOperation(cfg.operation))
            .withValues(OPERATION_OPTIONS)
            .create(centerX - btnW - gap / 2, y, btnW, 20,
                Component.literal("Operation"),
                (b, v) -> { cfg.operation = v; cfg.save(); });
        addRenderableWidget(operationBtn);
        problemsBtn = CycleButton.<Integer>builder(
                n -> Component.literal(n + " problems"))
            .withInitialValue(closestOption(cfg.problemsPerQuiz, PROBLEM_OPTIONS))
            .withValues(PROBLEM_OPTIONS)
            .create(centerX + gap / 2, y, btnW, 20,
                Component.literal("Problems"),
                (b, v) -> { cfg.problemsPerQuiz = v; cfg.save(); });
        addRenderableWidget(problemsBtn);
        y += rowH;

        addRenderableWidget(CycleButton.<Integer>builder(
                n -> Component.literal(MathQuestDurationFormat.forCompactUi(n)))
            .withInitialValue(closestOption(cfg.quizIntervalSeconds, INTERVAL_OPTIONS))
            .withValues(INTERVAL_OPTIONS)
            .create(centerX - btnW - gap / 2, y, btnW, 20,
                Component.literal("Interval"),
                (b, v) -> { cfg.quizIntervalSeconds = v; cfg.save(); MathQuestClientForge.resetTimer(); }));
        addRenderableWidget(CycleButton.<String>builder(
                s -> Component.literal(spawnTargetLabel(s)))
            .withInitialValue(MathQuestConfig.normalizeNpcSpawnTargetMode(cfg.npcSpawnTargetMode))
            .withValues(SPAWN_TARGET_OPTIONS)
            .create(centerX + gap / 2, y, btnW, 20,
                Component.literal("Nerd Spawn"),
                (b, v) -> {
                    cfg.npcSpawnTargetMode = v;
                    if (!"one".equals(v)) cfg.npcSpawnTargetPlayer = null;
                    cfg.save();
                }));
        y += rowH;

        int halfBtn = (btnW - 4) / 2;
        int leftRangeX = centerX - btnW - gap / 2;
        int rightRangeX = centerX + gap / 2;
        minMinusBtn = Button.builder(Component.literal("Min -"), b -> { cfg.minNumber--; cfg.save(); rebuild(); })
            .bounds(leftRangeX, y, halfBtn, 20).build();
        minPlusBtn = Button.builder(Component.literal("Min +"), b -> { cfg.minNumber++; cfg.save(); rebuild(); })
            .bounds(leftRangeX + halfBtn + 4, y, halfBtn, 20).build();
        maxMinusBtn = Button.builder(Component.literal("K2 -"), b -> { cfg.maxNumber--; cfg.save(); rebuild(); })
            .bounds(rightRangeX, y, halfBtn, 20).build();
        maxPlusBtn = Button.builder(Component.literal("K2 +"), b -> { cfg.maxNumber++; cfg.save(); rebuild(); })
            .bounds(rightRangeX + halfBtn + 4, y, halfBtn, 20).build();
        addRenderableWidget(minMinusBtn);
        addRenderableWidget(minPlusBtn);
        addRenderableWidget(maxMinusBtn);
        addRenderableWidget(maxPlusBtn);
        applyInternalSourceControls(quizSource, operationBtn, problemsBtn, minMinusBtn, minPlusBtn, maxMinusBtn, maxPlusBtn);
        y += rowH;
        addRenderableWidget(centeredLabel(centerX, y,
            "Default range: " + cfg.minNumber + " - " + cfg.maxNumber, ChatFormatting.WHITE));
        y += 14;

        List<String> groupOptions = new ArrayList<>();
        groupOptions.add("");
        if (cfg.rewardGroups != null) groupOptions.addAll(cfg.rewardGroups.keySet());
        String currentGroup = cfg.rewardGroup == null ? "" : cfg.rewardGroup.toLowerCase(Locale.ROOT);
        if (!groupOptions.contains(currentGroup)) currentGroup = "";
        addRenderableWidget(CycleButton.<String>builder(
                s -> Component.literal(s.isBlank() ? "(flat list)" : "group: " + s))
            .withInitialValue(currentGroup)
            .withValues(groupOptions)
            .create(centerX - btnW - gap / 2, y, colSpan, 20,
                Component.literal("Reward Pool"),
                (b, v) -> {
                    cfg.rewardGroup = v.isBlank() ? null : v;
                    cfg.save();
                    rebuild();
                }));
        y += rowH;

        addRenderableWidget(centeredLabel(centerX, y, summarizeRewards(cfg), ChatFormatting.AQUA));
        y += 16;

        addRenderableWidget(centeredLabel(centerX, y, "-- Player Presets --", ChatFormatting.GRAY));
        y += 14;

        if (cfg.playerPresets.isEmpty()) {
            addRenderableWidget(centeredLabel(centerX, y,
                "(no per-player presets - global defaults apply)", ChatFormatting.DARK_GRAY));
            y += 14;
        } else {
            int maxToShow = 4;
            int shown = 0;
            for (var entry : cfg.playerPresets.entrySet()) {
                if (shown >= maxToShow) break;
                addRenderableWidget(centeredLabel(centerX, y,
                    summarizePreset(entry.getKey(), entry.getValue(), cfg), ChatFormatting.AQUA));
                y += 12;
                shown++;
            }
            if (cfg.playerPresets.size() > maxToShow) {
                addRenderableWidget(centeredLabel(centerX, y,
                    "(+" + (cfg.playerPresets.size() - maxToShow) + " more...)",
                    ChatFormatting.DARK_GRAY));
                y += 12;
            }
        }

        int bottomY = this.height - 30;
        addRenderableWidget(Button.builder(Component.literal("Add Me as Preset"), b -> {
            String pname = currentPlayerName();
            if (pname != null && !pname.isBlank()) {
                String key = pname.toLowerCase(Locale.ROOT);
                cfg.playerPresets.computeIfAbsent(key, k -> new MathQuestConfig.PlayerQuizPreset());
                cfg.save();
                rebuild();
            }
        }).bounds(centerX - btnW - gap / 2, bottomY - 24, btnW, 20).build());

        addRenderableWidget(Button.builder(Component.literal("Edit Player Presets..."), b ->
            Minecraft.getInstance().setScreen(new PlayerSettingsScreenForge(this))
        ).bounds(centerX + gap / 2, bottomY - 24, btnW, 20).build());

        addRenderableWidget(Button.builder(Component.literal("Start Quiz Now"), b -> startQuizNow())
            .bounds(centerX - btnW - gap / 2, bottomY, btnW, 20).build());
        addRenderableWidget(Button.builder(Component.literal("Done"), b -> onClose())
            .bounds(centerX + gap / 2, bottomY, btnW, 20).build());
    }

    private void rebuild() {
        clearWidgets();
        init();
    }

    private void startQuizNow() {
        Minecraft client = Minecraft.getInstance();
        if ("npc".equals(MathQuestConfig.INSTANCE.quizMode)) {
            var server = client.getSingleplayerServer();
            if (server != null && client.player != null) {
                ServerPlayer serverPlayer = server.getPlayerList().getPlayer(client.player.getUUID());
                if (serverPlayer != null) {
                    ServerLevel overworld = server.overworld();
                    server.execute(() -> MathQuestForge.getNerdSpawner().forceSpawn(overworld, serverPlayer));
                }
            }
            onClose();
        } else {
            client.setScreen(new QuizOfferScreenForge());
        }
    }

    private static String currentPlayerName() {
        var c = Minecraft.getInstance();
        return (c.player == null) ? null : c.player.getName().getString();
    }

    private StringWidget centeredLabel(int centerX, int y, String text, ChatFormatting... fmt) {
        MutableComponent c = Component.literal(text);
        for (ChatFormatting f : fmt) c = c.withStyle(f);
        int w = this.font.width(text) + 2;
        return new StringWidget(centerX - w / 2, y, w, 12, c, this.font);
    }

    private static String resolveQuizSourceForPanel(MathQuestConfig cfg) {
        String source = MathQuestConfig.normalizeInternalQuizSource(
            cfg.resolveInternalQuizSource(currentPlayerName()));
        return QUIZ_SOURCE_OPTIONS.contains(source) ? source : QUIZ_SOURCE_OPTIONS.get(0);
    }

    private static void applyInternalSourceControls(String source,
            CycleButton<String> operationBtn, CycleButton<Integer> problemsBtn,
            Button minMinusBtn, Button minPlusBtn, Button maxMinusBtn, Button maxPlusBtn) {
        if (operationBtn == null || problemsBtn == null) return;
        boolean disableOp = "internal_problem_list".equals(source) || "internal_fluency_feast".equals(source);
        boolean disableRangeProblems = !"generated".equals(source);
        operationBtn.active = !disableOp;
        problemsBtn.active = !disableRangeProblems;
        minMinusBtn.active = !disableRangeProblems;
        minPlusBtn.active = !disableRangeProblems;
        maxMinusBtn.active = !disableRangeProblems;
        maxPlusBtn.active = !disableRangeProblems;
    }

    private static Component quizSourceLabel(String source) {
        return Component.literal(switch (source) {
            case "internal_problem_list" -> "Use internal problem list";
            case "internal_quick_quiz" -> "Use internal quick quiz";
            case "internal_fluency_feast" -> "Use internal fluency feast";
            default -> "Use settings below";
        });
    }

    private static String prettyOp(String op) {
        return switch (op) {
            case "addition" -> "Addition (+)";
            case "subtraction" -> "Subtraction (-)";
            case "exponentiation" -> "Exponent (^)";
            default -> "Multiplication (x)";
        };
    }

    private static String spawnTargetLabel(String mode) {
        return switch (mode) {
            case "random" -> "Random Player";
            case "one" -> "Only Named Player";
            default -> "All Players";
        };
    }

    private static String summarizeRewards(MathQuestConfig cfg) {
        List<MathQuestConfig.RewardEntry> active = cfg.resolveActiveRewardEntries();
        if (active == null || active.isEmpty()) return "Rewards: (none)";
        StringBuilder sb = new StringBuilder("Rewards: ");
        for (int i = 0; i < active.size(); i++) {
            if (i > 0) sb.append(", ");
            MathQuestConfig.RewardEntry e = active.get(i);
            String n = e.item.contains(":") ? e.item.substring(e.item.indexOf(':') + 1) : e.item;
            sb.append(n.replace('_', ' ')).append(" x").append(e.count);
        }
        return sb.toString();
    }

    private static String summarizePreset(String name, MathQuestConfig.PlayerQuizPreset p, MathQuestConfig cfg) {
        String op = (p.operation == null || p.operation.isBlank()) ? cfg.operation : p.operation;
        String range = (p.minNumber != null && p.maxNumber != null)
            ? (p.minNumber + "-" + p.maxNumber)
            : (cfg.minNumber + "-" + cfg.maxNumber + " (default)");
        return name + ": " + op + ", range " + range;
    }

    private static Integer closestOption(int actual, List<Integer> options) {
        Integer best = options.get(0);
        int bestDiff = Math.abs(actual - best);
        for (Integer v : options) {
            int d = Math.abs(actual - v);
            if (d < bestDiff) { best = v; bestDiff = d; }
        }
        return best;
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
