package com.kidgames.mathquest.reward;

import java.time.Duration;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;

/**
 * Server-issued, one-use quiz completion sessions used to prevent replayed TP-credit awards.
 *
 * <p>Sessions are intentionally in-memory: a server restart invalidates unfinished quizzes instead
 * of making old completion credentials reusable. Entries expire and are bounded per player.
 */
public final class TpCreditCompletionTracker {
    private static final long SESSION_TTL_MILLIS = Duration.ofHours(4).toMillis();
    private static final int MAX_SESSIONS_PER_PLAYER = 16;
    private static final Map<String, Session> SESSIONS = new LinkedHashMap<>();

    private TpCreditCompletionTracker() {}

    /** Issues a new opaque session token for a quiz opened for {@code playerName}. */
    public static synchronized String issue(String playerName) {
        long now = System.currentTimeMillis();
        String normalizedPlayer = normalizePlayer(playerName);
        removeExpired(now);
        trimPlayerSessions(normalizedPlayer);
        String token = UUID.randomUUID().toString();
        SESSIONS.put(token, new Session(normalizedPlayer, now + SESSION_TTL_MILLIS, State.PENDING));
        return token;
    }

    /** Marks an issued session complete after its quiz result has been processed successfully. */
    public static synchronized boolean markCompleted(String playerName, String token) {
        if (token == null || token.isBlank()) return false;
        long now = System.currentTimeMillis();
        removeExpired(now);
        Session session = SESSIONS.get(token);
        if (session == null || !session.playerName().equals(normalizePlayer(playerName))) {
            return false;
        }
        SESSIONS.put(token, new Session(session.playerName(), session.expiresAtMillis(), State.COMPLETED));
        return true;
    }

    /** Cancels a pending session without awarding it, such as when a partial quiz is saved. */
    public static synchronized boolean cancel(String playerName, String token) {
        if (token == null || token.isBlank()) return false;
        removeExpired(System.currentTimeMillis());
        Session session = SESSIONS.get(token);
        if (session == null || !session.playerName().equals(normalizePlayer(playerName))) {
            return false;
        }
        SESSIONS.remove(token);
        return true;
    }

    /** Atomically consumes a completed session. Pending, cancelled, and replayed tokens fail. */
    public static synchronized boolean consumeCompleted(String playerName, String token) {
        if (token == null || token.isBlank()) return false;
        removeExpired(System.currentTimeMillis());
        Session session = SESSIONS.get(token);
        if (session == null
            || session.state() != State.COMPLETED
            || !session.playerName().equals(normalizePlayer(playerName))) {
            return false;
        }
        SESSIONS.remove(token);
        return true;
    }

    public static synchronized void resetForTests() {
        SESSIONS.clear();
    }

    private static void removeExpired(long now) {
        SESSIONS.entrySet().removeIf(entry -> entry.getValue().expiresAtMillis() <= now);
    }

    private static void trimPlayerSessions(String playerName) {
        int count = 0;
        for (Session session : SESSIONS.values()) {
            if (session.playerName().equals(playerName)) count++;
        }
        int toRemove = count - MAX_SESSIONS_PER_PLAYER + 1;
        if (toRemove <= 0) return;
        Iterator<Map.Entry<String, Session>> iterator = SESSIONS.entrySet().iterator();
        while (iterator.hasNext() && toRemove > 0) {
            if (iterator.next().getValue().playerName().equals(playerName)) {
                iterator.remove();
                toRemove--;
            }
        }
    }

    private static String normalizePlayer(String playerName) {
        return playerName == null ? "" : playerName.trim().toLowerCase(Locale.ROOT);
    }

    private enum State { PENDING, COMPLETED }

    private record Session(String playerName, long expiresAtMillis, State state) {}
}
