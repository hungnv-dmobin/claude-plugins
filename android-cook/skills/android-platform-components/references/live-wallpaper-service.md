# Live Wallpaper Service

`WallpaperService` is a long-running `Service` whose `Engine` draws to a `SurfaceHolder` provided by the system. The user picks a wallpaper from *Settings → Wallpaper → Live Wallpapers* (or via `ACTION_CHANGE_LIVE_WALLPAPER`), and from that moment your engine draws behind every home screen and (optionally) the lock screen.

## Manifest shape

```xml
<service
    android:name=".platform.wallpaper.GalaxyWallpaperService"
    android:exported="true"
    android:label="@string/wallpaper_label"
    android:permission="android.permission.BIND_WALLPAPER">
    <intent-filter>
        <action android:name="android.service.wallpaper.WallpaperService" />
    </intent-filter>
    <meta-data
        android:name="android.service.wallpaper"
        android:resource="@xml/galaxy_wallpaper" />
</service>
```

- `android:permission="android.permission.BIND_WALLPAPER"` is **mandatory** — only the system has this permission, so this gates the service to the system process.
- `android:exported="true"` is required (system is a separate process).
- The `<intent-filter>` action must be exactly `android.service.wallpaper.WallpaperService` — no variations.
- The `<meta-data>` resource points to the wallpaper descriptor XML.

```xml
<!-- res/xml/galaxy_wallpaper.xml -->
<wallpaper xmlns:android="http://schemas.android.com/apk/res/android"
    android:thumbnail="@drawable/wallpaper_thumb"
    android:description="@string/wallpaper_description"
    android:author="@string/wallpaper_author"
    android:settingsActivity="com.example.app.platform.wallpaper.WallpaperSettingsActivity"
    android:showMetadataInPreview="true" />
```

- `settingsActivity` is optional. If declared, the picker shows a "Settings" button that launches it.

## Service + Engine skeleton

```kotlin
class GalaxyWallpaperService : WallpaperService() {
    override fun onCreateEngine(): Engine = GalaxyEngine()

    private inner class GalaxyEngine : Engine() {
        private val handler = Handler(Looper.getMainLooper())
        private val drawRunnable = Runnable { draw() }
        private var visible = false

        override fun onVisibilityChanged(visible: Boolean) {
            this.visible = visible
            if (visible) handler.post(drawRunnable)
            else handler.removeCallbacks(drawRunnable)
        }

        override fun onSurfaceDestroyed(holder: SurfaceHolder) {
            super.onSurfaceDestroyed(holder)
            visible = false
            handler.removeCallbacks(drawRunnable)
        }

        override fun onOffsetsChanged(
            xOffset: Float, yOffset: Float,
            xStep: Float, yStep: Float,
            xPixels: Int, yPixels: Int,
        ) {
            // re-draw the parallax layer in response to home-screen scroll
        }

        private fun draw() {
            val holder = surfaceHolder
            var canvas: Canvas? = null
            try {
                canvas = holder.lockCanvas()
                if (canvas != null) renderFrame(canvas)
            } finally {
                if (canvas != null) holder.unlockCanvasAndPost(canvas)
            }
            handler.removeCallbacks(drawRunnable)
            if (visible) handler.postDelayed(drawRunnable, 16L) // ~60 fps cap
        }

        private fun renderFrame(canvas: Canvas) {
            canvas.drawColor(Color.BLACK)
            // domain rendering here
        }
    }
}
```

Critical lifecycle:

- **Stop drawing when not visible.** `onVisibilityChanged(false)` is called whenever the user opens an app, locks the screen, or pulls down notifications. Draining battery while invisible is the #1 reason users uninstall a live wallpaper.
- `onSurfaceDestroyed` must remove all pending draw runnables — surface re-use after destroy crashes the system process.
- Cap frame rate. Continuous `postDelayed(..., 0)` will pin a CPU core; 16 ms is a 60 fps ceiling, 33 ms (30 fps) is fine for most parallax / particle effects.

## Launching the picker from your app

```kotlin
val intent = Intent(WallpaperManager.ACTION_CHANGE_LIVE_WALLPAPER).apply {
    putExtra(
        WallpaperManager.EXTRA_LIVE_WALLPAPER_COMPONENT,
        ComponentName(context, GalaxyWallpaperService::class.java),
    )
}
startActivity(intent)
```

This jumps the user straight into the preview for **your** wallpaper. Without the `EXTRA_LIVE_WALLPAPER_COMPONENT`, it opens the generic picker.

Detecting whether the user's current wallpaper is yours:

```kotlin
val wm = WallpaperManager.getInstance(context)
val info = wm.wallpaperInfo  // WallpaperInfo? — null for static wallpapers
val isMine = info?.packageName == context.packageName
```

## Hard rules

- **Never** draw while `visible == false`. The system does not throttle a misbehaving engine — it just lets the battery die.
- **Never** hold a long-lived reference to `Canvas` outside the `lockCanvas / unlockCanvasAndPost` pair. The surface is recycled.
- **Never** start a foreground service or schedule WorkManager from inside the engine. Wallpapers are not meant to do background work; the engine is alive only while the surface is.
- **Never** touch `SurfaceHolder` on a non-main thread without an explicit drawing thread (HandlerThread / dedicated `Thread`). If you do, pair the `lockCanvas` call with `try { ... } finally { unlockCanvasAndPost(...) }` to release on exceptions.
- **Never** ship a wallpaper that draws on the lock screen unless you've tested CPU + battery impact — many launchers display the wallpaper through lock too.

## Audit checklist

- [ ] `<service>` has `android:permission="android.permission.BIND_WALLPAPER"` and `android:exported="true"`.
- [ ] `<intent-filter>` action is exactly `android.service.wallpaper.WallpaperService`.
- [ ] `<meta-data android:name="android.service.wallpaper">` points at an existing XML file.
- [ ] `onVisibilityChanged(false)` cancels every pending draw callback.
- [ ] `onSurfaceDestroyed` cancels pending callbacks **and** resets `visible = false`.
- [ ] Frame rate is capped (postDelayed >= 16 ms).
- [ ] All `lockCanvas` calls are paired with `unlockCanvasAndPost` in a `finally` block.
- [ ] If a settings activity is declared, it exists and is exported as `false` (it's launched in-process from the picker).
