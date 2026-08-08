package com.kidgames.mathquest.forge;

import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.jar.JarFile;
import java.util.stream.Collectors;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** Verifies the Forge release jar bundles sqlite-jdbc via jarJar (the -all artifact). */
class ForgeReleaseJarIncludesSqliteTest {
    @Test
    void releaseJarBundlesSqliteJdbc() throws IOException {
        Path libsDir = Path.of("build/libs").toAbsolutePath().normalize();
        Path releaseJar = Files.list(libsDir)
            .filter(p -> p.getFileName().toString().endsWith("-all.jar"))
            .filter(p -> p.getFileName().toString().startsWith("mathquest-forge-"))
            .sorted()
            .reduce((first, second) -> second)
            .orElseThrow(() -> new AssertionError("No mathquest-forge-*-all.jar under " + libsDir));

        try (JarFile jar = new JarFile(releaseJar.toFile())) {
            var jarJarEntries = jar.stream()
                .map(entry -> entry.getName())
                .filter(name -> name.startsWith("META-INF/jarjar/"))
                .collect(Collectors.toList());
            assertFalse(jarJarEntries.isEmpty(), "expected META-INF/jarjar entries in " + releaseJar.getFileName());
            assertTrue(
                jarJarEntries.stream().anyMatch(name -> name.contains("sqlite-jdbc")),
                "expected sqlite-jdbc under META-INF/jarjar in " + releaseJar.getFileName() + " but found: " + jarJarEntries
            );
        }
    }

    @Test
    void slimReobfJarDoesNotBundleSqliteJdbc() throws IOException {
        Path libsDir = Path.of("build/libs").toAbsolutePath().normalize();
        Path slimJar = Files.list(libsDir)
            .filter(p -> {
                String name = p.getFileName().toString();
                return name.startsWith("mathquest-forge-") && name.endsWith(".jar") && !name.contains("-all")
                    && !name.contains("-sources");
            })
            .findFirst()
            .orElseThrow(() -> new AssertionError("No slim mathquest-forge jar under " + libsDir));

        try (JarFile jar = new JarFile(slimJar.toFile())) {
            boolean hasJarJarSqlite = jar.stream()
                .map(entry -> entry.getName())
                .anyMatch(name -> name.startsWith("META-INF/jarjar/") && name.contains("sqlite-jdbc"));
            assertFalse(hasJarJarSqlite,
                "slim jar must not be deployed; use -all.jar (see build-and-deploy.py): " + slimJar.getFileName());
        }
    }
}
