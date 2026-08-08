package net.minecraft.util;

public class Identifier {
    private final String namespace;
    private final String path;

    private Identifier(String namespace, String path) {
        this.namespace = namespace;
        this.path = path;
    }

    public static Identifier of(String id) {
        String[] parts = id.split(":", 2);
        if (parts.length == 2) {
            return new Identifier(parts[0], parts[1]);
        }
        return new Identifier("minecraft", id);
    }

    public String getNamespace() { return namespace; }
    public String getPath() { return path; }

    @Override
    public String toString() { return namespace + ":" + path; }
}
