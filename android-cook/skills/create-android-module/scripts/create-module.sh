#!/usr/bin/env bash
# Create an Android Studio module skeleton.
#
# Usage: create-module.sh <module_name> <namespace> [project_root]
#   <module_name>  Gradle module name (e.g. "data", "vpnservice")
#   <namespace>    Java/Kotlin package (e.g. "com.dmb.app.tools.vpn.data")
#   [project_root] Defaults to current working directory
#
# Creates:
#   <module>/src/main/java/<namespace-as-path>/    (empty package dir)
#   <module>/src/main/AndroidManifest.xml          (empty <manifest>)
#   <module>/build.gradle.kts                      (placeholder, filled by caller)
#   <module>/proguard-rules.pro                    (empty)
#   <module>/consumer-rules.pro                    (empty)
#   <module>/.gitignore                            (/build)
#
# Adds include("<module>") to settings.gradle.kts or settings.gradle.

set -euo pipefail

if [[ $# -lt 2 ]]; then
    echo "Usage: $0 <module_name> <namespace> [project_root]" >&2
    exit 1
fi

MODULE_NAME="$1"
NAMESPACE="$2"
PROJECT_ROOT="${3:-$(pwd)}"

NAMESPACE_PATH="${NAMESPACE//.//}"
MODULE_DIR="$PROJECT_ROOT/$MODULE_NAME"

if [[ -e "$MODULE_DIR" ]]; then
    echo "Error: $MODULE_DIR already exists" >&2
    exit 1
fi

mkdir -p "$MODULE_DIR/src/main/java/$NAMESPACE_PATH"

cat > "$MODULE_DIR/src/main/AndroidManifest.xml" <<'EOF'
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

</manifest>
EOF

# Placeholder build.gradle.kts; caller (Claude) overwrites with proper content
# derived from existing non-app modules (or the app module fallback rules).
cat > "$MODULE_DIR/build.gradle.kts" <<EOF
// TODO: build script will be generated based on existing modules.
// Module: $MODULE_NAME
// Namespace: $NAMESPACE
EOF

: > "$MODULE_DIR/proguard-rules.pro"
: > "$MODULE_DIR/consumer-rules.pro"

cat > "$MODULE_DIR/.gitignore" <<'EOF'
/build
EOF

# Add include to settings file (.kts preferred, fallback to groovy)
SETTINGS_KTS="$PROJECT_ROOT/settings.gradle.kts"
SETTINGS_GROOVY="$PROJECT_ROOT/settings.gradle"
INCLUDE_LINE_KTS="include(\":$MODULE_NAME\")"
INCLUDE_LINE_GROOVY="include ':$MODULE_NAME'"

if [[ -f "$SETTINGS_KTS" ]]; then
    if ! grep -qF "$INCLUDE_LINE_KTS" "$SETTINGS_KTS"; then
        printf '\n%s\n' "$INCLUDE_LINE_KTS" >> "$SETTINGS_KTS"
    fi
    SETTINGS_FILE="$SETTINGS_KTS"
elif [[ -f "$SETTINGS_GROOVY" ]]; then
    if ! grep -qF "$INCLUDE_LINE_GROOVY" "$SETTINGS_GROOVY"; then
        printf '\n%s\n' "$INCLUDE_LINE_GROOVY" >> "$SETTINGS_GROOVY"
    fi
    SETTINGS_FILE="$SETTINGS_GROOVY"
else
    echo "Warning: no settings.gradle(.kts) found at $PROJECT_ROOT" >&2
    SETTINGS_FILE="(none)"
fi

cat <<EOF
Created module: $MODULE_NAME
  Path:       $MODULE_DIR
  Namespace:  $NAMESPACE
  Package dir: $MODULE_DIR/src/main/java/$NAMESPACE_PATH
  Settings:   $SETTINGS_FILE
Next: populate $MODULE_DIR/build.gradle.kts based on existing modules.
EOF
