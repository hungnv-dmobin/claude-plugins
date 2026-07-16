---
name: create-android-module
argument-hint: <module_name> [namespace] [--skip-verify]
description: Create a new Android library module in a Gradle project — infers namespace, scaffolds manifest, registers in settings.gradle, writes build.gradle.kts matching existing modules. Android Gradle projects only. Triggers: "add a module", "create a :data module".
---

## When to use

Create a new Android library module in a Gradle Android project. Infers namespace, scaffolds directory + manifest, registers in settings.gradle, and writes build.gradle.kts matching existing modules. Trigger when the user says "add a module", "create a new module", "scaffold an Android library", or names one (e.g. "create a :data module", "add a vpnservice module").

When to use: Use only for Android Gradle projects. Do NOT use for non-Gradle or non-Android projects.

# Create Android Module

Scaffolds an Android library module inside an existing Android Gradle project, then writes `build.gradle.kts` modeled after the project's existing modules.

The flow is **two phases**: a deterministic shell script lays down the skeleton, then you (Claude) generate `build.gradle.kts` content from the project's existing modules. The script runs *first* so the structure exists in context before you write the gradle file.

## Step 0 — Confirm the project is Android Gradle

Before anything, verify:
- Project root has `settings.gradle.kts` or `settings.gradle`.
- Project root has a top-level `build.gradle.kts` or `build.gradle`.
- An `app/` (or other) Android module exists with `android { ... }` block.

If not, abort and tell the user.

## Step 1 — Determine module name

Use the name the user gave (e.g. `data`, `vpnservice`, `network`). If unclear, ask. Use lowercase, no separators (matches Android convention).

## Step 2 — Determine namespace

Read `settings.gradle(.kts)` and the `android { namespace = "..." }` block of every existing module's `build.gradle(.kts)`.

Apply these rules **in order**:

1. **Only `app` module exists** → take app's namespace and append `.<module_name>`.
   Example: app namespace `com.dmb.app.tools.vpn` + new module `data` → `com.dmb.app.tools.vpn.data`.

2. **Multiple modules exist and they share a consistent style** (e.g. all non-app modules use `com.dmb.app.tools.vpn.<module>`) → follow that style with the new module name.

3. **Multiple modules with mixed styles** → pick the style that matches rule (1) (`<app-namespace>.<module>`); if none of the existing non-app modules use that style, ask the user which style to follow rather than guessing.

4. **User explicitly provided a namespace** → always use it as-is.

State the chosen namespace to the user before running the script.

## Step 3 — Run the scaffolding script

```bash
bash "${CLAUDE_PROJECT_DIR:-.}/.claude/skills/create-android-module/scripts/create-module.sh" <module_name> <namespace> [project_root]
```

The script lives inside this project at `.claude/skills/create-android-module/scripts/create-module.sh` (project-local skill, NOT under `~/.claude`). Always invoke it from the project root, or substitute the absolute project path. `project_root` defaults to the current working directory. The script:

- Creates `<module>/src/main/java/<namespace-as-path>/` (empty package dir).
- Writes `<module>/src/main/AndroidManifest.xml` with an empty `<manifest>` element:
  ```xml
  <?xml version="1.0" encoding="utf-8"?>
  <manifest xmlns:android="http://schemas.android.com/apk/res/android">

  </manifest>
  ```
- Writes a placeholder `<module>/build.gradle.kts` (you will overwrite it in Step 4).
- Writes empty `<module>/proguard-rules.pro` and `<module>/consumer-rules.pro`.
- Writes `<module>/.gitignore` containing `/build`.
- Appends `include(":<module_name>")` (or Groovy `include ':<module_name>'`) to the settings file if not already present.

The script aborts if `<module>/` already exists. **Remember the module structure after the script runs** — you'll need the namespace and module name when writing `build.gradle.kts` in the next step.

## Step 4 — Generate `build.gradle.kts`

Overwrite the placeholder using one of these two paths:

### Case A — There is at least one non-app module

Pick a representative non-app module (closest in role to the new one if obvious, otherwise any). Open its `build.gradle.kts` and:

1. Copy the **plugins** block verbatim.
2. Copy the **android** block, but change `namespace` to the new module's namespace. Keep everything else the same (`compileSdk`, `defaultConfig.minSdk`, `consumerProguardFiles`, `buildTypes`, `compileOptions`, `kotlinOptions`/`kotlin`, `buildFeatures`, etc.).
3. Copy the **dependencies** block verbatim, except drop `project(...)` lines that don't make sense for the new module (e.g. don't depend on yourself; if uncertain, drop module-to-module deps and let the user add them).

### Case B — Only the `app` module exists

Open `app/build.gradle.kts` and adapt:

1. **plugins block:** copy as-is, but replace the Android Application plugin with the Android Library plugin:
   - `id("com.android.application")` → `id("com.android.library")`
   - `alias(libs.plugins.android.application)` → `alias(libs.plugins.android.library)` (replace with corresponding plugin alias in toml if don't defined this module name in toml)
   - Leave all other plugins (Kotlin, Hilt, KSP, Compose, Parcelize, etc.) untouched.

2. **android block:** copy as-is, then:
   - Set `namespace` to the new module's namespace.
   - In `defaultConfig`, **remove** `applicationId`, `versionCode`, `versionName` (and `testInstrumentationRunner` if you want to be conservative — keep it if other modules typically keep it).
   - **Add** `consumerProguardFiles("consumer-rules.pro")` inside `defaultConfig`.
   - Keep `minSdk`, `compileSdk`, `targetSdk`, `compileOptions`, `kotlinOptions`/`kotlin { ... }`, `buildFeatures`, `packaging`, etc. as in app.

**Also update the root `build.gradle.kts`:** if you added a new plugin alias (e.g. `android-library`) to the version catalog, you MUST also register it in the **top-level** `build.gradle.kts` `plugins { ... }` block with `apply false`, alongside the existing `android.application` line. Example:

```kotlin
plugins {
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.android.library) apply false   // <-- add this
    alias(libs.plugins.kotlin.compose) apply false
}
```

Skipping this causes Gradle to fail with: `Error resolving plugin [id: 'com.android.library', version: 'X']  > The request for this plugin could not be satisfied because the plugin is already on the classpath with an unknown version, so compatibility cannot be checked.` — because the AGP jar is on the build classpath via `android.application`, but the `android.library` id is being resolved fresh from the plugin portal.

3. **dependencies block:** **do not copy app's dependencies wholesale.** Instead include only the baseline library deps:
   - `androidx.core:core-ktx` (use the version catalog alias if app uses one, e.g. `implementation(libs.androidx.core.ktx)`)
   - `androidx.appcompat:appcompat`
   - `com.google.android.material:material`
   - test deps if app has them: `junit`, `androidx.test.ext:junit`, `androidx.test.espresso:espresso-core`

   Match the syntax style app uses (version catalog `libs.*` vs. hard-coded coordinates).

After writing, briefly summarize to the user what namespace/style was chosen and what was copied vs. omitted.

## Step 5 — Verify

Run `./gradlew :<module_name>:tasks -q` (or at least `./gradlew projects`) to confirm Gradle recognizes the new module. If the user asked for a specific compile-check, run `./gradlew :<module_name>:assembleDebug` (or `:build`).

**Skip verification** when the user passes `--skip-verify` (or says "skip verify", "no verify", "don't run gradle", "skip gradle check"). In that case, do not run any `./gradlew` command — just report that the module was scaffolded and remind the user to sync/build in Android Studio themselves. Useful when Gradle sync is slow, the daemon is unavailable, or the user plans to make further edits before the first build.

## Notes / caveats

- **Don't** create source files (`.kt` classes) unless the user asked. The skill scaffolds the module, not its contents.
- **Don't** add `res/` directories unless the user asked — many library modules don't need them.
- **Don't** modify other modules' `build.gradle` files (e.g. don't auto-wire the new module as a dependency of `:app`). Tell the user to add `implementation(project(":<module>"))` where they want it.
- If the project uses Groovy (`build.gradle` instead of `.kts`), mirror the same logic but emit Groovy syntax.
