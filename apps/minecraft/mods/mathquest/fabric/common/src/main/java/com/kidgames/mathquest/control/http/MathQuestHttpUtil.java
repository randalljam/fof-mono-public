package com.kidgames.mathquest.control.http;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.kidgames.mathquest.platform.PlatformServer;
import com.sun.net.httpserver.HttpExchange;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;
import java.util.function.Supplier;

public final class MathQuestHttpUtil {
    public static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();

    private MathQuestHttpUtil() {}

    public static <T> T onServerThread(PlatformServer server, Supplier<T> supplier) {
        CompletableFuture<T> future = new CompletableFuture<>();
        server.runOnServerThread(() -> {
            try {
                future.complete(supplier.get());
            } catch (Exception e) {
                future.completeExceptionally(e);
            }
        });
        try {
            return future.get(5, TimeUnit.SECONDS);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    public static JsonObject readJson(HttpExchange ex) throws IOException {
        String text = new String(ex.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
        if (text.isBlank()) return new JsonObject();
        return JsonParser.parseString(text).getAsJsonObject();
    }

    public static void sendJson(HttpExchange ex, Object obj) throws IOException {
        sendBytes(ex, 200, GSON.toJson(obj).getBytes(StandardCharsets.UTF_8), "application/json; charset=utf-8");
    }

    public static void sendError(HttpExchange ex, int status, String message) throws IOException {
        sendBytes(ex, status, GSON.toJson(Map.of("ok", false, "error", message)).getBytes(StandardCharsets.UTF_8),
            "application/json; charset=utf-8");
    }

    public static void sendBytes(HttpExchange ex, int status, byte[] bytes, String contentType) throws IOException {
        ex.getResponseHeaders().set("Content-Type", contentType);
        ex.getResponseHeaders().set("Cache-Control", "no-store");
        ex.sendResponseHeaders(status, bytes.length);
        try (OutputStream out = ex.getResponseBody()) {
            out.write(bytes);
        }
    }

    public static void sendResource(HttpExchange ex, ClassLoader classLoader, String path, String contentType) throws IOException {
        try (InputStream in = classLoader.getResourceAsStream(path)) {
            if (in == null) {
                sendError(ex, 404, "Resource not found");
                return;
            }
            sendBytes(ex, 200, in.readAllBytes(), contentType);
        }
    }

    public static int clamp(int value, int min, int max) {
        return Math.max(min, Math.min(max, value));
    }
}
