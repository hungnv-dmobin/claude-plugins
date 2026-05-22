# Launcher (Home) App

A launcher is an Activity declared with `CATEGORY_HOME`. The user picks the default via *Settings → Apps → Default apps → Home app*, or via `RoleManager.ROLE_HOME` on API 29+.

## Manifest shape

```xml
<activity
    android:name=".platform.launcher.LauncherActivity"
    android:exported="true"
    android:launchMode="singleTask"
    android:stateNotNeeded="true"
    android:windowSoftInputMode="adjustPan"
    android:theme="@style/Theme.Launcher">
    <intent-filter>
        <action android:name="android.intent.action.MAIN" />
        <category android:name="android.intent.category.HOME" />
        <category android:name="android.intent.category.DEFAULT" />
        <category android:name="android.intent.category.LAUNCHER_APP" />
    </intent-filter>
</activity>
```

Critical pieces:

- All three categories — `HOME`, `DEFAULT`, **and** `LAUNCHER_APP` (API 21+) — must be present. Missing `DEFAULT` means the system won't surface your app in the Home-app chooser even though `HOME` is filed.
- `launchMode="singleTask"` — pressing Home should bring the existing instance to front, not start a new one.
- `stateNotNeeded="true"` — the system can recreate the launcher without restoring its saved state. Avoids weird restore-after-kill bugs.
- Theme: typically no action bar, transparent or wallpaper-showthrough background. Use `?android:attr/windowShowWallpaper` if the launcher draws over the wallpaper.

A launcher app **must not** also declare the standard `LAUNCHER` category for the same activity (`android.intent.category.LAUNCHER`) — that's for app-drawer entries. Keep them separate: one Activity for `HOME`, optionally a different one for `LAUNCHER`.

## Querying installed apps for the app drawer

```kotlin
val pm = context.packageManager
val intent = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER)
val resolveInfos = pm.queryIntentActivities(intent, 0)
val apps = resolveInfos.map {
    AppEntry(
        label = it.loadLabel(pm).toString(),
        component = ComponentName(it.activityInfo.packageName, it.activityInfo.name),
        icon = it.loadIcon(pm),
    )
}
```

On API 30+ this requires the `QUERY_ALL_PACKAGES` permission **or** the `<queries>` manifest element. A launcher is one of the few legitimate `QUERY_ALL_PACKAGES` use cases — Play policy explicitly carves it out:

```xml
<uses-permission android:name="android.permission.QUERY_ALL_PACKAGES" />
```

Declare it and disclose in Play Console as "core launcher functionality."

## Launching an app

```kotlin
val intent = pm.getLaunchIntentForPackage(packageName) ?: return
intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_RESET_TASK_IF_NEEDED)
context.startActivity(intent)
```

Prefer `LauncherApps.startMainActivity(...)` on API 21+ when you have the user's profile (work profile, secondary user):

```kotlin
val launcherApps = context.getSystemService(LauncherApps::class.java)
val activity = launcherApps.getActivityList(packageName, user).firstOrNull() ?: return
launcherApps.startMainActivity(activity.componentName, user, sourceBounds, options)
```

`LauncherApps` correctly handles managed profiles; `getLaunchIntentForPackage` does not.

## Requesting the Home role

On API 29+:

```kotlin
val roleManager = getSystemService(RoleManager::class.java)
if (roleManager.isRoleAvailable(RoleManager.ROLE_HOME) &&
    !roleManager.isRoleHeld(RoleManager.ROLE_HOME)) {
    val intent = roleManager.createRequestRoleIntent(RoleManager.ROLE_HOME)
    homeRoleLauncher.launch(intent)
}
```

Register the result launcher:

```kotlin
private val homeRoleLauncher = registerForActivityResult(
    ActivityResultContracts.StartActivityForResult(),
) { result ->
    if (result.resultCode == Activity.RESULT_OK) {
        // user accepted; we're the new home app
    } else {
        // user declined — fall back to "tap Home, pick us" instructions
    }
}
```

On API 24–28, the role API is not available. Fall back to:

```kotlin
startActivity(Intent(Settings.ACTION_HOME_SETTINGS))
```

This drops the user at the Home-app picker; they pick manually.

Detect current home app:

```kotlin
val intent = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_HOME)
val info = pm.resolveActivity(intent, PackageManager.MATCH_DEFAULT_ONLY)
val currentHome = info?.activityInfo?.packageName
val isUsHome = currentHome == context.packageName
```

## LauncherApps callbacks

Subscribe to install / uninstall / package-change events without polling:

```kotlin
val launcherApps = context.getSystemService(LauncherApps::class.java)
launcherApps.registerCallback(object : LauncherApps.Callback() {
    override fun onPackageAdded(packageName: String, user: UserHandle) { /* ... */ }
    override fun onPackageRemoved(packageName: String, user: UserHandle) { /* ... */ }
    override fun onPackageChanged(packageName: String, user: UserHandle) { /* ... */ }
    override fun onPackagesAvailable(packageNames: Array<String>, user: UserHandle, replacing: Boolean) { /* ... */ }
    override fun onPackagesUnavailable(packageNames: Array<String>, user: UserHandle, replacing: Boolean) { /* ... */ }
})
```

Unregister on the host's lifecycle teardown — these callbacks live on the binder and leak if forgotten.

## Hard rules

- **Never** omit `CATEGORY_DEFAULT` alongside `CATEGORY_HOME`. The Home-app chooser uses `DEFAULT` to enumerate candidates.
- **Never** use `Activity.recreate()` on Home pressed — the system delivers a new `Intent` with `CATEGORY_HOME`; handle it in `onNewIntent`.
- **Never** request `QUERY_ALL_PACKAGES` without filling in the Play Console core-functionality disclosure. Listing fails review otherwise.
- **Never** call `pm.queryIntentActivities` on the main thread. On a device with 200+ apps it can take 100–300 ms.
- **Never** assume the user has a single profile. Use `LauncherApps` for cross-profile (work / personal) correctness.
- **Never** rely on the user discovering Settings → Home App. Use the `RoleManager` flow on API 29+ for an in-context prompt.
- **Never** persist `LauncherApps.Callback` references in static storage — leaks the binder.

## Audit checklist

- [ ] Launcher `<activity>` has `MAIN` + `HOME` + `DEFAULT` + `LAUNCHER_APP` categories.
- [ ] `launchMode="singleTask"`, `stateNotNeeded="true"`.
- [ ] `QUERY_ALL_PACKAGES` is declared **and** Play Console disclosure submitted (or `<queries>` is used instead if the launcher only resolves a known list).
- [ ] `RoleManager.ROLE_HOME` is requested on API 29+; `Settings.ACTION_HOME_SETTINGS` fallback on 24–28.
- [ ] App-drawer query runs off the main thread.
- [ ] `LauncherApps` is used for managed-profile correctness.
- [ ] `LauncherApps.Callback` is unregistered on host teardown.
- [ ] Home intent is handled in `onNewIntent` to avoid re-instantiation.
