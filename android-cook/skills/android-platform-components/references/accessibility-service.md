# Accessibility Service

`AccessibilityService` lets an app observe and act on the active window's view tree across **other apps**. Legitimate uses: screen readers, password managers (autofill predates this; some still use AccessibilityService for compat), automation / task launchers, kiosk apps. Misuses (UI scraping, overlay phishing) trigger Play Store policy review — declare the use case in `accessibility-service-config.xml` and Play Console.

User must enable it explicitly via *Settings → Accessibility → Installed services*. There is no `RoleManager` shortcut.

## Manifest shape

```xml
<service
    android:name=".platform.a11y.MyAccessibilityService"
    android:exported="false"
    android:label="@string/a11y_service_label"
    android:permission="android.permission.BIND_ACCESSIBILITY_SERVICE">
    <intent-filter>
        <action android:name="android.accessibilityservice.AccessibilityService" />
    </intent-filter>
    <meta-data
        android:name="android.accessibilityservice"
        android:resource="@xml/accessibility_service_config" />
</service>
```

- `android:permission="android.permission.BIND_ACCESSIBILITY_SERVICE"` is **mandatory** — only the system holds it, gating the bind path.
- `android:exported="false"` (the system binds via a special bridge, not the export route).
- Action must be exactly `android.accessibilityservice.AccessibilityService`.

```xml
<!-- res/xml/accessibility_service_config.xml -->
<accessibility-service xmlns:android="http://schemas.android.com/apk/res/android"
    android:accessibilityEventTypes="typeViewClicked|typeViewFocused|typeWindowStateChanged"
    android:packageNames="com.target.app1,com.target.app2"
    android:accessibilityFeedbackType="feedbackGeneric"
    android:notificationTimeout="100"
    android:canRetrieveWindowContent="true"
    android:canRequestTouchExplorationMode="false"
    android:canRequestFilterKeyEvents="false"
    android:description="@string/a11y_service_description"
    android:settingsActivity="com.example.app.platform.a11y.A11ySettingsActivity"
    android:summary="@string/a11y_service_summary" />
```

Field rules:

- `accessibilityEventTypes` — declare the **minimum** set the feature needs. `typeAllMask` is a Play policy red flag.
- `packageNames` — restrict to specific apps if possible. Omitting this means events from every app, which trips heuristic review.
- `canRetrieveWindowContent="true"` is required to call `getRootInActiveWindow()` or read `AccessibilityNodeInfo` children.
- `description` is mandatory on API 26+; without it, the service won't appear in Settings.

## Service skeleton

```kotlin
class MyAccessibilityService : AccessibilityService() {

    override fun onServiceConnected() {
        super.onServiceConnected()
        // optional: tweak AccessibilityServiceInfo at runtime
        serviceInfo = serviceInfo?.apply {
            eventTypes = AccessibilityEvent.TYPE_VIEW_CLICKED or
                         AccessibilityEvent.TYPE_VIEW_FOCUSED
            flags = AccessibilityServiceInfo.DEFAULT or
                    AccessibilityServiceInfo.FLAG_REPORT_VIEW_IDS
        }
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        event ?: return
        when (event.eventType) {
            AccessibilityEvent.TYPE_VIEW_CLICKED -> handleClick(event)
            AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED -> handleWindowChange(event)
        }
    }

    override fun onInterrupt() {
        // called when the system asks the service to stop providing feedback
    }
}
```

Performing actions back on the active window:

```kotlin
val root = rootInActiveWindow ?: return
val nodes = root.findAccessibilityNodeInfosByViewId("$targetPackage:id/submit")
nodes.firstOrNull()?.performAction(AccessibilityNodeInfo.ACTION_CLICK)
```

Always `recycle()` `AccessibilityNodeInfo` instances you obtain from `rootInActiveWindow`, `getChild(...)`, or `findAccessibilityNodeInfosByViewId` — leaks pin the system process memory.

## Sending the user to enable the service

```kotlin
startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS).apply {
    flags = Intent.FLAG_ACTIVITY_NEW_TASK
})
```

Then poll the service state:

```kotlin
fun isMyServiceEnabled(context: Context, cls: Class<out AccessibilityService>): Boolean {
    val expected = ComponentName(context, cls).flattenToString()
    val enabled = Settings.Secure.getString(
        context.contentResolver,
        Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES,
    ).orEmpty()
    return enabled.split(':').any { it.equals(expected, ignoreCase = true) }
}
```

Do not promise to "detect when the user enables it" — the only reliable signal is `onServiceConnected()` in the service itself. From the UI side, re-check on `onResume` after the settings round-trip.

## Hard rules

- **Never** declare `accessibilityEventTypes="typeAllMask"` unless the use case demonstrably requires every event. Play policy flags this for review.
- **Never** scrape passwords, credit cards, or banking-app fields. The Play Families & Accessibility policy bans this even for "automation" framing.
- **Never** display an overlay positioned on top of another app's UI from inside the accessibility service handler — that is `SYSTEM_ALERT_WINDOW`'s job, and combining the two is the canonical phishing pattern Play scans for.
- **Never** leak `AccessibilityNodeInfo`. Pair every fetch with `recycle()` (on API 33+ recycle is a no-op but still required for compat).
- **Never** rely on `packageNames="*"` (= empty). Always scope.
- **Never** call `disableSelf()` and immediately restart the service — the system blocks rapid re-enable.
- **Never** assume the service runs in the app's foreground process. It's a `Service` in the app process, but the system suspends it aggressively; cache nothing in static memory.

## Audit checklist

- [ ] `<service>` has `BIND_ACCESSIBILITY_SERVICE` permission.
- [ ] `accessibility-service-config.xml` declares the minimum event types the feature needs.
- [ ] `packageNames` is set (not `*`) unless the feature is genuinely cross-app.
- [ ] `description` resource exists (mandatory on API 26+).
- [ ] Every `AccessibilityNodeInfo` fetch path calls `recycle()` (or relies on `try { ... } finally { recycle() }`).
- [ ] No `typeAllMask` event-type declarations.
- [ ] UI side polls service state on `onResume`, not via a custom broadcast.
- [ ] Play Console "Use of accessibility services" form is filled in before release.
