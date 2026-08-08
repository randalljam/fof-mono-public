#!/bin/bash
set -e

# MC 26.1.1 + Fabric Loom require JDK 25 for Gradle. Install with: brew install openjdk@25
# (Homebrew may show the formula as "openjdk" 25.x; keg-only — use JAVA_HOME below.)
# For MC 1.21.11, comment out the JDK 25 block and use the openjdk@21 line instead.

if [ -z "${JAVA_HOME:-}" ] || [ ! -x "${JAVA_HOME}/bin/java" ]; then
  if command -v brew >/dev/null 2>&1; then
    _BREW_PREFIX="$(brew --prefix openjdk@25 2>/dev/null || true)"
    if [ -n "${_BREW_PREFIX}" ] && [ -x "${_BREW_PREFIX}/libexec/openjdk.jdk/Contents/Home/bin/java" ]; then
      export JAVA_HOME="${_BREW_PREFIX}/libexec/openjdk.jdk/Contents/Home"
    fi
  fi
fi
if [ -z "${JAVA_HOME:-}" ] || [ ! -x "${JAVA_HOME}/bin/java" ]; then
  for _JHOME in \
    "/opt/homebrew/opt/openjdk/libexec/openjdk.jdk/Contents/Home" \
    "/usr/local/opt/openjdk/libexec/openjdk.jdk/Contents/Home"; do
    if [ -x "${_JHOME}/bin/java" ]; then
      export JAVA_HOME="${_JHOME}"
      break
    fi
  done
fi

if [ -z "${JAVA_HOME:-}" ] || [ ! -x "${JAVA_HOME}/bin/java" ]; then
  echo "ERROR: JDK 25 not found. Install with: brew install openjdk@25" >&2
  echo "Then ensure Homebrew links exist (Apple Silicon: /opt/homebrew, Intel: /usr/local)." >&2
  exit 1
fi

export PATH="$JAVA_HOME/bin:$PATH"

MODS_DIR="$HOME/Library/Application Support/minecraft/mods"
INACTIVE_DIR="$MODS_DIR/mathquest-inactive-mods"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

cd "$SCRIPT_DIR"

MOD_VERSION=$(grep '^mod_version=' gradle.properties | cut -d= -f2)
BASE_NAME=$(grep '^archives_base_name=' gradle.properties | cut -d= -f2)
MINECRAFT_VERSION=$(grep '^minecraft_version=' gradle.properties | cut -d= -f2)
JAR_NAME="${BASE_NAME}_${MINECRAFT_VERSION}_v${MOD_VERSION}.jar"

echo "=== Building MathQuest v${MOD_VERSION} (Java $(java -version 2>&1 | head -1)) ==="
./gradlew build "$@"

BUILD_JAR="build/libs/$JAR_NAME"
if [ ! -f "$BUILD_JAR" ]; then
    echo "ERROR: Build output not found at $BUILD_JAR"
    echo "Contents of build/libs/:"
    ls -la build/libs/ 2>/dev/null || echo "  (directory does not exist)"
    exit 1
fi

echo ""
echo "=== Deploying to Minecraft mods folder ==="

if [ -d "$INACTIVE_DIR" ]; then
    echo "Found existing inactive mods folder: $INACTIVE_DIR"
else
    mkdir -p "$INACTIVE_DIR"
    echo "Created inactive mods folder: $INACTIVE_DIR"
fi

TIMESTAMP=$(date +"%Y-%m-%d_%H%M")
for old_jar in "$MODS_DIR"/${BASE_NAME}*.jar; do
    [ -f "$old_jar" ] || continue
    old_name=$(basename "$old_jar" .jar)
    archived="${INACTIVE_DIR}/${old_name}_${TIMESTAMP}.jar"
    mv "$old_jar" "$archived"
    echo "Archived $(basename "$old_jar") -> mathquest-inactive-mods/$(basename "$archived")"
done

cp "$BUILD_JAR" "$MODS_DIR/$JAR_NAME"
echo "Deployed $JAR_NAME -> $MODS_DIR/"

echo ""
echo "=== Done! ==="
echo "Restart Minecraft for changes to take effect."
