# Notification Listener Service

`NotificationListenerService` receives every notification posted system-wide and can dismiss / snooze them programmatically. Use cases: cross-device notification mirroring, automation rules, smart-watch / car-head-unit pairing, do-not-disturb gates. The user enables access in *Settings → Notifications → Device & app notifications → (your app)*. There is no `RoleManager` flow.

## Manifest shape

```xml
<service
    android:name=".platform.notif.MyNotificationListener"
    android:exported="false"
    android:label="@string/notif_listener_label"
    android:permission="android.permission.BIND_NOTIFICATION_LISTENER_SERVICE">
    <intent-filter>
        <action android:name="android.service.notification.NotificationListenerService" />
    </intent-filter>
    <meta-data
        android:name="android.service.notification.default_filter_types"
        android:value="conversations|alerting" />
    <meta-data
        android:name="android.service.notification.disabled_filter_types"
        android:value="ongoing|silent" />
</service>
```

- `android:permission="android.permission.BIND_NOTIFICATION_LISTENER_SERVICE"` is **mandatory** — only the system holds this.
- `android:exported="false"`.
- Action must be exactly `android.service.notification.NotificationListenerService`.
- The two `meta-data` filter hints (API 33+) let the system pre-filter; on older APIs they're ignored.

No `<uses-permission>` is needed — the user grants access through Settings, not via a runtime permission dialog.

## Service skeleton

```kotlin
class MyNotificationListener : NotificationListenerService() {

    override fun onListenerConnected() {
        super.onListenerConnected()
        // initial sync of currently-active notifications
        activeNotifications?.forEach(::handlePosted)
    }

    override fun onListenerDisconnected() {
        super.onListenerDisconnected()
        // service is being torn down — flush pending state
    }

    override fun onNotificationPosted(sbn: StatusBarNotification?) {
        sbn ?: return
        handlePosted(sbn)
    }

    override fun onNotificationRemoved(
        sbn: StatusBarNotification?,
        rankingMap: RankingMap?,
        reason: Int,
    ) {
        sbn ?: return
        // reason values: REASON_APP_CANCEL, REASON_LISTENER_CANCEL, REASON_USER, ...
    }

    private fun handlePosted(sbn: StatusBarNotification) {
        val notif = sbn.notification ?: return
        val title = notif.extras.getCharSequence(Notification.EXTRA_TITLE)?.toString()
        val text = notif.extras.getCharSequence(Notification.EXTRA_TEXT)?.toString()
        // domain handling — push to repository, etc.
    }
}
```

Dismissing or snoozing:

```kotlin
cancelNotification(sbn.key)              // dismiss
snoozeNotification(sbn.key, 5 * 60_000L) // snooze 5 minutes
```

## Sending the user to grant access

```kotlin
startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS).apply {
    flags = Intent.FLAG_ACTIVITY_NEW_TASK
})
```

API 30+ supports a per-component deep link:

```kotlin
val component = ComponentName(context, MyNotificationListener::class.java)
startActivity(
    Intent(Settings.ACTION_NOTIFICATION_LISTENER_DETAIL_SETTINGS)
        .putExtra(Settings.EXTRA_NOTIFICATION_LISTENER_COMPONENT_NAME, component.flattenToString())
        .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
)
```

Detecting whether access is granted:

```kotlin
fun isListenerEnabled(context: Context, cls: Class<out NotificationListenerService>): Boolean {
    val pkg = context.packageName
    val flat = Settings.Secure.getString(
        context.contentResolver,
        "enabled_notification_listeners",
    ).orEmpty()
    val expected = ComponentName(context, cls).flattenToString()
    return flat.split(':').any { it.equals(expected, ignoreCase = true) }
        || flat.split(':').any { it.startsWith("$pkg/") && it.equals(expected, ignoreCase = true) }
}
```

Re-check on `onResume` after the Settings round-trip — there is no broadcast for "user just enabled the listener."

## Notification access on API 33+

Posting your own notifications still requires `POST_NOTIFICATIONS` runtime permission on API 33+; listening does not (the user grants via Settings). Do not confuse the two:

- **Listening** to others' notifications → `NotificationListenerService` + Settings access.
- **Posting** your own → `POST_NOTIFICATIONS` runtime permission.

Both can coexist; both need separate user gestures.

## Hard rules

- **Never** persist notification content without considering PII. Notification bodies routinely contain OTPs, banking transaction details, and private messages. If you store, encrypt at rest and document retention.
- **Never** call `cancelNotification(...)` without a user-facing reason. Silently dismissing other apps' notifications is a Play policy violation framed as "interfering with system functionality."
- **Never** rely on the listener being connected immediately after the user enables it. The system rebinds asynchronously — wait for `onListenerConnected()`.
- **Never** call `getActiveNotifications()` (the legacy synchronous form) from a UI thread. Use the listener callbacks instead.
- **Never** assume the user only enables one listener — multiple apps can listen concurrently.
- **Never** combine the listener with an accessibility service to read content unavailable through the notification API. That combo is a recognized abuse pattern.

## Audit checklist

- [ ] `<service>` has `BIND_NOTIFICATION_LISTENER_SERVICE` permission.
- [ ] `<intent-filter>` action is exactly `android.service.notification.NotificationListenerService`.
- [ ] `onListenerConnected()` is implemented for initial sync.
- [ ] UI flow sends the user to Settings (deep-linked on API 30+).
- [ ] Detection function checks `enabled_notification_listeners` on `onResume`.
- [ ] No persistent storage of notification content without encryption.
- [ ] Play Console "Notification access" disclosure is on file before release.
