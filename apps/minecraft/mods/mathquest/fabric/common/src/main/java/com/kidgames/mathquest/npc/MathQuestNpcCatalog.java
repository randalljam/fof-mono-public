package com.kidgames.mathquest.npc;

import com.kidgames.mathquest.config.MathQuestConfig;

import java.util.List;

public class MathQuestNpcCatalog {
    public record NpcDef(String id, String name, String entity, String texturePath, List<String> dialogueLines) {}
    private static final List<NpcDef> NPCS = List.of(
        new NpcDef(
            "wandering_nerd",
            "The Wandering Nerd",
            "The Wandering Nerd",
            "textures/entity/wandering_nerd.png",
            List.of(
                "Why was 6 afraid of 7? Because 7 8 9! Anyway, want to do some math?",
                "I tried to teach my cat algebra, but she said it was too purr-plexing. You'll do better!",
                "Parallel lines have so much in common... it's a shame they'll never meet. Unlike us!",
                "What did the zero say to the eight? Nice belt! Now let's do some math!",
                "I'm not a regular nerd, I'm a WANDERING nerd. Got some problems for ya!",
                "Did you know octopi have three hearts? That's 3 x 1! Math is everywhere!"
            )
        ),
        new NpcDef(
            "professor_pi",
            "Professor Pi",
            "Professor Pi",
            "textures/entity/professor_pi.png",
            List.of(
                "I brought a slice of pi, but first let's solve a problem.",
                "Circumference, diameter, adventure... all excellent reasons to practice.",
                "A good estimate gets you close; a careful answer gets you treasure.",
                "Today I am rounding up courage and rounding down distractions.",
                "Every quest has a radius. Yours starts right here.",
                "Pi may go on forever, but this quiz is nicely finite."
            )
        ),
        new NpcDef(
            "countess_calc",
            "Countess Calc",
            "Countess Calc",
            "textures/entity/countess_calc.png",
            List.of(
                "I counted the stars and saved the best problems for you.",
                "Every correct answer adds a little sparkle to the kingdom.",
                "A tidy calculation is a kind of magic.",
                "Numbers behave beautifully when you ask them politely.",
                "Let us total your courage and multiply your treasure.",
                "No need to rush; even royalty checks their work."
            )
        ),
        new NpcDef(
            "geo_sage",
            "Geo Sage",
            "Geo Sage",
            "textures/entity/geo_sage.png",
            List.of(
                "The shortest path to treasure is often a straight line through practice.",
                "Triangles are strong, but your math brain is stronger.",
                "Measure twice, answer once, celebrate always.",
                "Every block has coordinates; every answer has a path.",
                "Angles, edges, and effort: that is the shape of success.",
                "Let us map this problem and find the solution."
            )
        ),
        new NpcDef(
            "paper_coach",
            "Paper Coach Penny",
            "Paper Coach Penny",
            "textures/entity/paper_coach.png",
            List.of(
                "Pencils ready. This one belongs on paper.",
                "Line up the columns, keep your place, and let the digits behave.",
                "Show your work like a math detective leaving clear clues.",
                "Carry carefully, borrow bravely, and check the answer twice.",
                "When the page is ready, call the evaluator for the code.",
                "Column math is slow magic: neat rows first, treasure second."
            )
        )
    );
    public static List<NpcDef> all() {
        return NPCS;
    }
    public static NpcDef byId(String id) {
        if (id != null) {
            for (NpcDef npc : NPCS) {
                if (npc.id().equals(id)) return npc;
            }
        }
        return NPCS.get(0);
    }
    public static List<String> dialogueLines(MathQuestConfig config, String id) {
        NpcDef npc = byId(id);
        return config == null ? npc.dialogueLines() : config.resolveNpcDialogueLines(npc.id(), npc.dialogueLines());
    }
}
