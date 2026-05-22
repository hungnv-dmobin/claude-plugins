# Overlay (System Alert Window) Service

`TYPE_APPLICATION_OVERLAY` lets an app draw a window on top of all other apps. Use cases: floating chat heads, drawing assist tools, in-call controls, picture-in-picture-style controls before PiP was available. The permission (`SYSTEM_ALERT_WINDOW`) is a special permission — granted via *Settings → Apps → Special app access → Display over other apps*, never through the runtime-permission dialog.

Heavy Play policy scrutiny: the same primitive is used by tap-jacking malware. Disclose the use case at submission time.

## Permission declaration + check

```xml
<uses-permission android:name="android.permission.SYSTEM_ALERT_WINDOW" />
```

API 23+ requires a per-user grant via Settings. The app can never request it programmatically — only navigate the user to the right Settings screen.

```kotlin
fun ensureOverlayPermission(activity: Activity, requestCode: Int): Boolean {
    if (Settings.canDrawOverlays(activity)) return true
    val intent = Intent(
        Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
        Uri.parse("package:${activity.packageName}"),
    )
    activity.startActivityForResult(intent, requestCode)
    return false
}
```

On return, re-check `Settings.canDrawOverlays(...)` in `onActivityResult` / the `registerForActivityResult` callback — there is no per-permission result code.

API 31+ note: `SYSTEM_ALERT_WINDOW` is pre-granted to apps installed via Play with a `WRITE_SETTINGS`-adjacent claim only in special cases. Assume it is **always** revocable and re-check before every overlay add.

## Adding the overlay

```kotlin
class FloatingControlService : Service() {

    private lateinit var windowManager: WindowManager
    private var overlayView: View? = null

    override fun onCreate() {
        super.onCreate()
        windowManager = getSystemService(WINDOW_SERVICE) as WindowManager
        startForeground(
            NOTIFICATION_ID,
            buildForegroundNotification(),
            ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE,
        )
        addOverlay()
    }

    private fun addOverlay() {
        if (!Settings.canDrawOverlays(this)) {
            stopSelf()
            return
        }
        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN or
                WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,
            PixelFormat.TRANSLUCENT,
        ).apply {
            gravity = Gravity.TOP or Gravity.START
            x = 24.dp
            y = 200.dp
        }
        overlayView = LayoutInflater.from(this).inflate(R.layout.overlay_floating, null)
        windowManager.addView(overlayView, params)
    }

    override fun onDestroy() {
        overlayView?.let { windowManager.removeView(it); overlayView = null }
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
```

Manifest:

```xml
<service
    android:name=".platform.overlay.FloatingControlService"
    android:exported="false"
    android:foregroundServiceType="specialUse">
    <property
        android:name="android.app.PROPERTY_SPECIAL_USE_FGS_SUBTYPE"
        android:value="floating_overlay_controls" />
</service>
```

Foreground-service-type rules (API 34+):

- An overlay-bearing service typically pairs with `foregroundServiceType="specialUse"` and the `PROPERTY_SPECIAL_USE_FGS_SUBTYPE` declaration. Play review requires the subtype string to match a documented use case.
- Other valid pairings if the overlay is incidental: `mediaProjection` (screen capture overlay), `connectedDevice` (remote-device control), `phoneCall` (in-call overlay) — pick the one that matches the **primary** reason for the foreground service.

## Window type rules

| API | Type to use | Notes |
|---|---|---|
| < 26 | `TYPE_PHONE` or `TYPE_SYSTEM_ALERT` | Both are deprecated but still required for backward compat |
| >= 26 | `TYPE_APPLICATION_OVERLAY` | The only supported type — older types throw on API 26+ |

On API 26+, the system places `TYPE_APPLICATION_OVERLAY` windows **below** status bar and input method — that is intentional and not bypassable. Don't try to use deprecated types to get z-order above the status bar; they crash on API 26+.

## Touch + accessibility considerations

- `FLAG_NOT_FOCUSABLE` — required so key events still flow to the underlying app. Otherwise typing breaks.
- `FLAG_NOT_TOUCH_MODAL` — touches outside the overlay bounds still reach the underlying app. Almost always wanted.
- If the overlay shows interactive controls that the user might mistake for the underlying app's UI, Play tap-jacking policy applies: visually distinguish the overlay (border, shadow, label) and never request sensitive input through it.

## Removing on configuration change / rotation

Overlays do not auto-rotate. Listen for configuration change in the service and update `WindowManager.LayoutParams`:

```kotlin
override fun onConfigurationChanged(newConfig: Configuration) {
    super.onConfigurationChanged(newConfig)
    overlayView?.let { v ->
        val lp = v.layoutParams as WindowManager.LayoutParams
        // re-clamp coordinates against new screen bounds
        windowManager.updateViewLayout(v, lp)
    }
}
```

Add `android:configChanges="orientation|screenSize|screenLayout|smallestScreenSize"` to the `<service>` only if you actually handle the change — otherwise the service recycles and the overlay flickers.

## Hard rules

- **Never** call `windowManager.addView(...)` without first checking `Settings.canDrawOverlays(this)`. The call throws `BadTokenException` (or silently no-ops on some OEMs) when permission is missing.
- **Never** use `TYPE_PHONE`, `TYPE_SYSTEM_ALERT`, or `TYPE_TOAST` on API 26+ — they crash with `BadTokenException`.
- **Never** display the overlay over the keyguard / lock screen unless the use case is explicitly call-style. The keyguard treats most overlays as security-sensitive and hides them anyway.
- **Never** request sensitive input (password, OTP, payment) inside an overlay — Play tap-jacking policy violation.
- **Never** forget to `removeView` in `onDestroy`. The leaked overlay survives the service and pins the window manager.
- **Never** start the overlay service from a context that cannot legitimately start a foreground service. On API 31+ background-start restrictions apply unless you have a granted exception (visible activity, allow-listed receiver, etc.).
- **Never** ship without a clear visible "close overlay" affordance. Stuck overlays are the #1 user complaint and lead to uninstalls.

## Audit checklist

- [ ] `SYSTEM_ALERT_WINDOW` is declared.
- [ ] Pre-add check uses `Settings.canDrawOverlays(...)`.
- [ ] User-facing flow that needs the overlay first calls `ACTION_MANAGE_OVERLAY_PERMISSION` and re-checks on return.
- [ ] Window type is `TYPE_APPLICATION_OVERLAY` (with deprecated fallbacks only inside `if (Build.VERSION.SDK_INT < 26)`).
- [ ] Service is a foreground service with a matching `foregroundServiceType` (and `PROPERTY_SPECIAL_USE_FGS_SUBTYPE` if `specialUse`).
- [ ] `onDestroy` removes the view.
- [ ] Overlay has a visible close affordance.
- [ ] No password / OTP / payment input inside the overlay.
- [ ] Play Console "Display over other apps" disclosure submitted.
