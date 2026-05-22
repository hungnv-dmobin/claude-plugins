# App Widget Provider — home-screen widgets

`AppWidgetProvider` is a specialized `BroadcastReceiver` that the home-screen launcher calls when it needs to render, update, or configure an app widget. The widget UI is `RemoteViews` — a serializable subset of Android views the launcher process can inflate on the app's behalf. Compose is not available inside a widget on `compileSdk` < 33; on 33+ use Glance (`androidx.glance:glance-appwidget`) if the project pins it.

## Manifest shape

Three pieces must line up exactly or the widget never appears in the picker.

```xml
<!-- AndroidManifest.xml — under <application> -->
<receiver
    android:name=".platform.widget.MessageCountWidgetProvider"
    android:exported="true"
    android:label="@string/widget_label">
    <intent-filter>
        <action android:name="android.appwidget.action.APPWIDGET_UPDATE" />
    </intent-filter>
    <meta-data
        android:name="android.appwidget.provider"
        android:resource="@xml/message_count_widget_info" />
</receiver>
```

- `android:exported="true"` is **required** (the launcher is a separate process). Implicit-exported is a build error on API 31+.
- The `<intent-filter>` must include `APPWIDGET_UPDATE`. Other actions (`APPWIDGET_DELETED`, `APPWIDGET_ENABLED`, etc.) are delivered automatically — do not declare them.
- `meta-data` points at `res/xml/<name>.xml` containing the `<appwidget-provider>` configuration.

```xml
<!-- res/xml/message_count_widget_info.xml -->
<appwidget-provider xmlns:android="http://schemas.android.com/apk/res/android"
    android:minWidth="110dp"
    android:minHeight="40dp"
    android:targetCellWidth="2"
    android:targetCellHeight="1"
    android:updatePeriodMillis="0"
    android:initialLayout="@layout/widget_message_count"
    android:resizeMode="horizontal|vertical"
    android:widgetCategory="home_screen"
    android:previewLayout="@layout/widget_message_count_preview"
    android:configure=".platform.widget.MessageCountConfigureActivity" />
```

- `updatePeriodMillis="0"` — **always**. The system honors a minimum of 30 minutes and wakes the device to deliver, which is a battery footgun. Use `WorkManager` or `AlarmManager` (with `setExactAndAllowWhileIdle` + `SCHEDULE_EXACT_ALARM` if precision is required) instead.
- `targetCellWidth` / `targetCellHeight` are API 31+ — pair with `minWidth` / `minHeight` for backward compatibility.
- `previewLayout` (API 31+) replaces `previewImage` and renders at picker time. Provide both for backward compat.
- `configure` is optional. If set, the launcher launches that activity on first drop and the widget is **not** visible until the activity returns `RESULT_OK` with the `appWidgetId` extra.

## Provider class skeleton

```kotlin
class MessageCountWidgetProvider : AppWidgetProvider() {
    override fun onUpdate(
        context: Context,
        manager: AppWidgetManager,
        appWidgetIds: IntArray,
    ) {
        appWidgetIds.forEach { id -> updateOne(context, manager, id) }
    }

    override fun onAppWidgetOptionsChanged(
        context: Context,
        manager: AppWidgetManager,
        appWidgetId: Int,
        newOptions: Bundle,
    ) {
        updateOne(context, manager, appWidgetId)
    }

    override fun onDeleted(context: Context, appWidgetIds: IntArray) {
        // clean up per-widget DataStore / Room rows keyed by appWidgetId
    }

    private fun updateOne(context: Context, manager: AppWidgetManager, id: Int) {
        val views = RemoteViews(context.packageName, R.layout.widget_message_count)
        views.setTextViewText(R.id.count, "—") // placeholder; async load below

        val tapPi = PendingIntent.getActivity(
            context,
            id,
            Intent(context, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        views.setOnClickPendingIntent(R.id.widget_root, tapPi)
        manager.updateAppWidget(id, views)
    }
}
```

Use `FLAG_IMMUTABLE` on every PendingIntent — see `pendingintent-flags.md`.

## Updating from outside the provider

The provider runs only when the system calls it. To update on data change:

```kotlin
val manager = AppWidgetManager.getInstance(context)
val component = ComponentName(context, MessageCountWidgetProvider::class.java)
val ids = manager.getAppWidgetIds(component)
context.sendBroadcast(Intent(context, MessageCountWidgetProvider::class.java).apply {
    action = AppWidgetManager.ACTION_APPWIDGET_UPDATE
    putExtra(AppWidgetManager.EXTRA_APPWIDGET_IDS, ids)
})
```

Or, preferred: enqueue a `WorkManager` job that loads data on `Dispatchers.IO`, then calls `manager.updateAppWidget(id, views)` directly. Never read Room / Retrofit on the receiver's main-thread `onUpdate`.

## Collection widgets (ListView / GridView)

`RemoteViews` for a list-backed widget points at a `RemoteViewsService` whose factory returns one `RemoteViews` per item:

```xml
<service
    android:name=".platform.widget.MessageListRemoteViewsService"
    android:permission="android.permission.BIND_REMOTEVIEWS"
    android:exported="false" />
```

`android:permission="android.permission.BIND_REMOTEVIEWS"` is **mandatory** — it gates the service so only the system can bind. Without it, the list is empty and the launcher logs `Permission Denial`.

## Glance (Compose) alternative

When `compileSdk` >= 33 and the project pins `androidx.glance:glance-appwidget`:

```kotlin
class MessageCountWidget : GlanceAppWidget() {
    override suspend fun provideGlance(context: Context, id: GlanceId) {
        provideContent {
            Text(text = "12 unread")
        }
    }
}

class MessageCountWidgetReceiver : GlanceAppWidgetReceiver() {
    override val glanceAppWidget = MessageCountWidget()
}
```

Manifest still declares the `<receiver>` with the `APPWIDGET_UPDATE` intent filter — register `MessageCountWidgetReceiver`, not the Glance widget class. Glance handles `RemoteViews` translation internally.

## Hard rules

- **Never** set `updatePeriodMillis` > 0. Use `WorkManager` (periodic) or `AlarmManager` (exact). The system minimum of 30 min and the wake-up cost make the manifest-period path a battery anti-pattern.
- **Never** do I/O on the provider's main thread. `onUpdate` is a broadcast receiver — same >5s kill rule applies. Use `goAsync()` or hand off to a service / work request.
- **Never** persist per-widget state without the `appWidgetId` as the key. `onDeleted` is the only signal the user removed the widget; without per-id state, deletion leaves orphans.
- **Never** assume the widget host is the system launcher. Third-party launchers (Nova, Smart Launcher) work, but lock-screen widget hosts (API 17–21) and Wear hosts have different cell math — use `widgetCategory="home_screen"` to opt out unless you've tested.
- **Never** omit `BIND_REMOTEVIEWS` on a `RemoteViewsService` — silent empty list.

## Audit checklist

- [ ] `<receiver>` has `android:exported="true"` and the `APPWIDGET_UPDATE` filter.
- [ ] `<meta-data android:name="android.appwidget.provider">` points at an existing `res/xml/` file.
- [ ] `updatePeriodMillis="0"` in the provider XML.
- [ ] Every `PendingIntent` in `RemoteViews.setOnClickPendingIntent` uses `FLAG_IMMUTABLE`.
- [ ] `onDeleted` removes per-`appWidgetId` state.
- [ ] If a `RemoteViewsService` is used, its `<service>` has `android:permission="android.permission.BIND_REMOTEVIEWS"`.
- [ ] Configure activity (if declared) sets `RESULT_OK` with `EXTRA_APPWIDGET_ID` before `finish()`, else the widget never materializes.
