package com.kidgames.mathquest;

import com.kidgames.mathquest.persistence.SqliteDriver;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class SqliteDriverTest {
    @Test
    void requireLoaded_succeedsWhenDriverPresent() {
        SqliteDriver.resetForTests();
        SqliteDriver.requireLoaded();
        assertTrue(SqliteDriver.isAvailable());
    }

    @Test
    void requireLoaded_failsWhenDriverMissing() {
        SqliteDriver.resetForTests();
        Thread.currentThread().setContextClassLoader(new ClassLoader(null) {
            @Override
            protected Class<?> loadClass(String name, boolean resolve) throws ClassNotFoundException {
                if ("org.sqlite.JDBC".equals(name)) {
                    throw new ClassNotFoundException(name);
                }
                return super.loadClass(name, resolve);
            }
        });
        try {
            assertThrows(IllegalStateException.class, SqliteDriver::requireLoaded);
        } finally {
            SqliteDriver.resetForTests();
            Thread.currentThread().setContextClassLoader(SqliteDriverTest.class.getClassLoader());
        }
    }
}
