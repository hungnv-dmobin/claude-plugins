# App Shortcuts (Static, Dynamic, Pinned)

`ShortcutManager` exposes three kinds of shortcuts, all surfaced by the launcher's long-press menu and (for pinned) the home-screen icon grid.

| Kind | Source | Limit | Use for |
|---|---|---|---|
| **Static** | `res/xml/shortcuts.xml` referenced from manifest | 5 total static+dynamic | Compile-time-known entry points (Compose, Search, New message) |
| **Dynamic** | `ShortcutManager.setDynamicShortcuts(...)` at runtime | 5 total static+dynamic | Recent contacts, last-opened documents — runtime data |
| **Pinned** | User drags a long-press shortcut to home, or `requestPinShortcut(...)` | unlimited | User-curated home-screen icons |

The 5-shortcut limit is **combined** for static + dynamic. Pinned shortcuts are unlimited. API 26+ for all of it; static and pinned are present from 25 and 26 respectively.

## Static shortcuts

Manifest:

```xml
<activity android:name=".MainActivity" ...>
    <intent-filter>
        <action android:name="android.intent.action.MAIN" />
        <category android:name="android.intent.category.LAUNCHER" />
    </intent-filter>
    <meta-data
        android:name="android.app.shortcuts"
        android:resource="@xml/shortcuts" />
</activity>
```

```xml
<!-- res/xml/shortcuts.xml -->
<shortcuts xmlns:android="http://schemas.android.com/apk/res/android">
    <shortcut
        android:shortcutId="compose"
        android:enabled="true"
        android:icon="@drawable/ic_shortcut_compose"
        android:shortcutShortLabel="@string/shortcut_compose_short"
        android:shortcutLongLabel="@string/shortcut_compose_long">
        <intent
            android:action="android.intent.action.VIEW"
            android:targetPackage="com.example.app"
            android:targetClass="com.example.app.ComposeActivity" />
        <categories android:name="android.shortcut.conversation" />
        <capability-binding android:key="actions.intent.CREATE_MESSAGE" />
    </shortcut>
</shortcuts>
```

Field rules:

- `shortcutId` must be unique within the app and stable across releases (used by the launcher to track pinned shortcuts).
- `shortcutShortLabel` (≤10 chars target) shows in the long-press menu; `shortcutLongLabel` shows when there's room (≤25 chars target).
- `<intent>` must include `android:action` — `VIEW` is the safe default. `targetPackage` + `targetClass` keep the intent explicit; do not use implicit intents (security-sensitive).
- `<categories>` is optional but feeds Assistant and shortcut suggestion surfaces.

## Dynamic shortcuts

```kotlin
val sm = context.getSystemService(ShortcutManager::class.java)
val recents = recentContacts.take(4).map { contact ->
    ShortcutInfo.Builder(context, "contact_${contact.id}")
        .setShortLabel(contact.firstName)
        .setLongLabel(contact.fullName)
        .setIcon(Icon.createWithResource(context, R.drawable.ic_shortcut_chat))
        .setIntent(
            Intent(Intent.ACTION_VIEW, "app://chat/${contact.id}".toUri()).apply {
                setPackage(context.packageName)
            }
        )
        .setPerson(
            Person.Builder()
                .setName(contact.fullName)
                .setKey(contact.id)
                .build()
        )
        .setLongLived(true) // required for Sharing Shortcuts + cached pinned use
        .build()
}
sm.dynamicShortcuts = recents
```

- `setLongLived(true)` is required if the shortcut is used as a Sharing Shortcut target or if you want the launcher to keep the pinned version usable after the dynamic copy is removed.
- The `Intent` must be `setPackage(...)`'d or explicit — implicit intents are silently rejected.
- Re-set the full dynamic list rather than adding/removing one at a time; the API is idempotent and that pattern survives process death.

To update an existing shortcut's metadata without resetting the list:

```kotlin
sm.updateShortcuts(listOf(updatedInfo))
```

To remove dynamics:

```kotlin
sm.removeDynamicShortcuts(listOf("contact_42"))
sm.removeAllDynamicShortcuts()
```

## Pinned shortcuts (request from your UI)

API 26+:

```kotlin
val sm = context.getSystemService(ShortcutManager::class.java)
if (!sm.isRequestPinShortcutSupported) {
    // Some launchers don't support programmatic pin (older OEM launchers).
    // Fall back to instructing the user to long-press + drag.
    return
}

val info = ShortcutInfo.Builder(context, "pin_inbox")
    .setShortLabel("Inbox")
    .setIcon(Icon.createWithResource(context, R.drawable.ic_shortcut_inbox))
    .setIntent(
        Intent(Intent.ACTION_VIEW).setPackage(context.packageName).apply {
            data = "app://inbox".toUri()
        }
    )
    .build()

val callback = PendingIntent.getBroadcast(
    context,
    0,
    Intent(context, PinShortcutResultReceiver::class.java),
    PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
).intentSender

sm.requestPinShortcut(info, callback)
```

`isRequestPinShortcutSupported` is critical — third-party launchers without pinning support return `false` and `requestPinShortcut` silently does nothing.

## Pinned shortcut callback

When the user approves the pin dialog, the system fires the `callback` IntentSender. Use a `BroadcastReceiver` (declared in the manifest) to handle "shortcut pinned" — useful for analytics or to update internal state:

```xml
<receiver
    android:name=".platform.shortcuts.PinShortcutResultReceiver"
    android:exported="false" />
```

```kotlin
class PinShortcutResultReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        // user confirmed the pin
    }
}
```

## Disabling shortcuts

Pinned shortcuts whose target no longer makes sense (deleted contact, signed-out account) should be **disabled with a message**, not silently broken:

```kotlin
sm.disableShortcuts(
    listOf("contact_42"),
    context.getString(R.string.shortcut_disabled_contact_removed),
)
```

The launcher greys out the icon and shows the message on tap. Never let a pinned shortcut launch into a broken / blank screen — that is a Play quality flag.

## Sharing Shortcuts (Direct Share)

On API 29+, dynamic shortcuts with the `SHARE_TARGET` category and a `<share-target>` declaration in `shortcuts.xml` become Direct Share targets:

```xml
<shortcut android:shortcutId="contact_42" ...>
    <intent ... />
    <categories android:name="android.shortcut.conversation" />
</shortcut>
<share-target android:targetClass="com.example.app.ShareTargetActivity">
    <data android:mimeType="text/plain" />
    <category android:name="android.shortcut.conversation" />
</share-target>
```

Each share-target dynamic shortcut **must** be `setLongLived(true)` and **must** include `setPerson(...)` if it represents a person. The launcher uses these for ranking.

## Hard rules

- **Never** exceed `getMaxShortcutCountPerActivity()` (currently 5). Excess shortcuts are silently dropped.
- **Never** use implicit intents in a `ShortcutInfo`. `setPackage(...)` or `setComponent(...)`, always.
- **Never** rebuild dynamic shortcut IDs across releases — pinned shortcuts pointing at old IDs become un-updatable orphans.
- **Never** silently delete a pinned shortcut. Use `disableShortcuts(..., reason)`.
- **Never** call `requestPinShortcut(...)` without checking `isRequestPinShortcutSupported`.
- **Never** put non-`FLAG_IMMUTABLE` PendingIntents in the pin-result callback. The system rejects them on API 31+.
- **Never** assume dynamic shortcuts survive an app data clear — they don't. Rebuild on `Application.onCreate` if your feature needs them post-clear.

## Audit checklist

- [ ] Static + dynamic combined count ≤ 5.
- [ ] Every `ShortcutInfo` intent is explicit (`setPackage` or `setComponent`).
- [ ] `shortcutId` values are stable and documented.
- [ ] `requestPinShortcut` is guarded by `isRequestPinShortcutSupported`.
- [ ] Pin-result `PendingIntent` uses `FLAG_IMMUTABLE`.
- [ ] Broken / stale shortcuts are `disableShortcuts(..., reason)`, never silently removed.
- [ ] Sharing-Shortcut targets have `setLongLived(true)` and `<share-target>` is declared.
- [ ] Dynamic shortcuts are rebuilt on `Application.onCreate` if the feature relies on their presence at cold start.
