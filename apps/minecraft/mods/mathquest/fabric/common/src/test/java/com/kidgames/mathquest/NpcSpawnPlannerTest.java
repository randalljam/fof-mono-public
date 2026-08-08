package com.kidgames.mathquest;

import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.npc.NpcSpawnPlanner;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

public class NpcSpawnPlannerTest {
    @Test
    void allModeReturnsEveryCandidate() {
        List<String> names = List.of("Alice", "Bob");
        List<String> result = NpcSpawnPlanner.selectTargetNames("all", names, null, 0);
        assertEquals(names, result);
    }

    @Test
    void randomModeReturnsOneCandidate() {
        List<String> names = List.of("Alice", "Bob", "Carol");
        List<String> result = NpcSpawnPlanner.selectTargetNames("random", names, null, 1);
        assertEquals(List.of("Bob"), result);
    }

    @Test
    void oneModeReturnsMatchingOnlinePlayer() {
        List<String> names = List.of("Alice", "Bob");
        List<String> result = NpcSpawnPlanner.selectTargetNames("one", names, "bob", 0);
        assertEquals(List.of("Bob"), result);
    }

    @Test
    void oneModeReturnsEmptyWhenTargetOffline() {
        List<String> names = List.of("Alice");
        List<String> result = NpcSpawnPlanner.selectTargetNames("one", names, "bob", 0);
        assertTrue(result.isEmpty());
    }

    @Test
    void normalizeModeAlias() {
        List<String> names = List.of("Alice");
        List<String> result = NpcSpawnPlanner.selectTargetNames("only", names, "alice", 0);
        assertEquals(List.of("Alice"), result);
    }
}
