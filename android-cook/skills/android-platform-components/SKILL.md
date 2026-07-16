---
name: android-platform-components
argument-hint: <component-type | "default-sms" | "smsmms" | "permissions" | "widget" | "wallpaper" | "a11y" | "notif-listener" | "launcher" | "overlay" | "shortcuts">
description: Implement Android system integrations at the manifest layer — receivers, services, providers, widgets, wallpaper, accessibility, notification listener, launcher, overlays, shortcuts, default-SMS role, permission flows (API 29+). Not for Compose UI, Room/DataStore, or test authoring. Triggers: "add a widget", "integrate smsmms", "make the app a launcher", "draw an overlay".
---

## When to use

Implement Android platform components and system integrations: BroadcastReceiver, Service, ContentProvider, AppWidgetProvider, WallpaperService, AccessibilityService, NotificationListenerService, launcher (home) apps, SYSTEM_ALERT_WINDOW overlays, ShortcutManager static/dynamic/pinned shortcuts, SMS-stack handling (Default-SMS role + smsmms integration), and runtime + special permission flows. Trigger when the user says "wire the SMS receiver", "integrate smsmms", "add a home-screen widget", "build a live wallpaper", "register an accessibility service", "listen to notifications", "make the app a launcher", "draw a floating overlay", "pin a shortcut", or "request default SMS role".

When to use: Use for any Android system integration at the manifest `<service>`/`<receiver>`/`<provider>`/`<activity>` layer that talks to a framework-owned subsystem (telephony, launcher, wallpaper, accessibility, notifications, window manager, shortcuts) on API 29+. Do NOT use for Compose UI (use android-clean-architecture + android-ui-test), Room/DataStore (data layer), or test authoring (android-unit-test).

# Android Platform Components

Procedure and code-pattern library for the **platform-dev-android** agent. Covers every concern that lives at the manifest / system-integration boundary — the layer between framework services and the app's domain logic.

The skill is split into two concern groups, each backed by one or more reference docs in `references/`. Load only the reference that matches the request.

## Concern groups

**Group A — Cross-cutting platform fundamentals.** Apply to every system component the app declares.

1. BroadcastReceiver / Service / ContentProvider patterns — the three platform components most features touch.
2. Runtime permission flow — dangerous permissions, special permissions (overlay, exact alarm, accessibility / notification-listener access), the rationale UX.

**Group B — Specific framework integrations.** Each is a self-contained component type with its own manifest shape, lifecycle, and Play-policy considerations.

3. SMS stack — Default-SMS-app role and (when MMS is in scope) the smsmms library.
4. App widgets — `AppWidgetProvider` + `RemoteViews` / Glance.
5. Live wallpapers — `WallpaperService` + `Engine`.
6. Accessibility services — `AccessibilityService` + accessibility-service-config.
7. Notification listeners — `NotificationListenerService` + access flow.
8. Launcher (home) apps — `CATEGORY_HOME` + `RoleManager.ROLE_HOME`.
9. Overlays — `TYPE_APPLICATION_OVERLAY` + `SYSTEM_ALERT_WINDOW`.
10. Shortcuts — `ShortcutManager` static / dynamic / pinned + Sharing Shortcuts.

This skill teaches the **correct platform code patterns**, not how to build any one of these features end-to-end. Every reference file is written so it transfers to any project that needs the same component.

## References (load only the one matching the request)

The procedure below points at these. Do not read them eagerly.

### Group A — fundamentals

- [`references/broadcast-receivers.md`](references/broadcast-receivers.md) — manifest-declared vs context-registered receivers, the canonical incoming-SMS receiver (`SMS_DELIVER` for the default SMS app vs `SMS_RECEIVED` for non-default), `goAsync()` for >5s work, ordered broadcasts and `abortBroadcast()`.
- [`references/services.md`](references/services.md) — when to pick foreground service vs `JobIntentService`/WorkManager, the canonical SMS-send service shape, `<service>` manifest entries the Default-SMS role requires (`android.intent.action.RESPOND_VIA_MESSAGE`), foreground-service-type rules on API 29+/34+.
- [`references/permissions.md`](references/permissions.md) — runtime-permission request pattern (`ActivityResultContracts.RequestMultiplePermissions`), the rationale screen, which permissions a role grants implicitly vs which still need a runtime ask, the special-permission category (overlay, exact alarm, notification listener — granted via Settings, not the runtime dialog).

### Group B — specific integrations

- [`references/contentprovider-sms.md`](references/contentprovider-sms.md) — reading `content://sms` and `content://mms`, projection / selection / sortOrder patterns, ContentObserver registration, paging large telephony tables, when (and when not) to add a Room cache.
- [`references/default-sms-role.md`](references/default-sms-role.md) — `RoleManager.createRequestRoleIntent(ROLE_SMS)` flow on API 29+, the four mandatory `<intent-filter>` + `<service>` manifest blocks the system checks, detecting the role state, denial handling, fallback for API 24–28 (`Telephony.Sms.getDefaultSmsPackage` + `ACTION_CHANGE_DEFAULT`).
- [`references/smsmms-overview.md`](references/smsmms-overview.md) — overview of integrating `klinker41/android-smsmms` for MMS-capable SMS apps: when to add it, depending on the locked fork hash from `app-overview.md`, the send flow (`Transaction.sendNewMessage`), receive wiring, and a short gotchas list. Read when the app sends MMS or is a Default-SMS-app candidate; skip for SMS-only apps.
- [`references/app-widget-provider.md`](references/app-widget-provider.md) — `AppWidgetProvider` manifest shape (`APPWIDGET_UPDATE` intent filter + `<meta-data>` XML), `RemoteViews` + `BIND_REMOTEVIEWS` for list widgets, `updatePeriodMillis="0"` rule, configure-activity flow, Glance (Compose) alternative on API 33+.
- [`references/live-wallpaper-service.md`](references/live-wallpaper-service.md) — `WallpaperService` + `Engine`, `BIND_WALLPAPER` permission gate, the visibility/teardown contract, `ACTION_CHANGE_LIVE_WALLPAPER` deep-link to the picker, frame-rate capping.
- [`references/accessibility-service.md`](references/accessibility-service.md) — `BIND_ACCESSIBILITY_SERVICE` permission, `accessibility-service-config.xml` (event types, `packageNames` scoping, `canRetrieveWindowContent`), Settings-driven enable flow, `AccessibilityNodeInfo` recycle rule, Play-policy red flags.
- [`references/notification-listener-service.md`](references/notification-listener-service.md) — `BIND_NOTIFICATION_LISTENER_SERVICE` permission, `ACTION_NOTIFICATION_LISTENER_SETTINGS` (and the API 30+ per-component deep-link), `onListenerConnected` initial sync, `cancelNotification` / `snoozeNotification`, separation from `POST_NOTIFICATIONS` (API 33+).
- [`references/launcher-app.md`](references/launcher-app.md) — `CATEGORY_HOME` + `CATEGORY_DEFAULT` + `CATEGORY_LAUNCHER_APP` triple, `launchMode="singleTask"`, `RoleManager.ROLE_HOME` flow on API 29+ (with `Settings.ACTION_HOME_SETTINGS` fallback for 24–28), `QUERY_ALL_PACKAGES` Play disclosure, `LauncherApps` for managed-profile correctness.
- [`references/overlay-service.md`](references/overlay-service.md) — `SYSTEM_ALERT_WINDOW` special permission, `Settings.canDrawOverlays(...)` pre-check, `TYPE_APPLICATION_OVERLAY` window type (API 26+), `foregroundServiceType="specialUse"` + `PROPERTY_SPECIAL_USE_FGS_SUBTYPE` (API 34+), tap-jacking policy, configuration-change handling.
- [`references/shortcuts.md`](references/shortcuts.md) — static (`res/xml/shortcuts.xml`) vs dynamic (`ShortcutManager.setDynamicShortcuts`) vs pinned (`requestPinShortcut`), the 5-shortcut combined limit, `isRequestPinShortcutSupported` guard, `disableShortcuts(..., reason)` for stale targets, Sharing-Shortcut (Direct Share) declaration on API 29+, `setLongLived` rule.

## Stack assumptions (verify against the project before generating)

- `compileSdk` >= 31. Several Group B references have their own min-API floors (`ShortcutManager` 25/26, `RoleManager` 29, `TYPE_APPLICATION_OVERLAY` 26, Glance widgets 33) — each reference states its own floor.
- `minSdk` >= 24 unless the project pin says otherwise (Android 7+ is the practical floor for runtime permissions + role-style flows).
- The project's app-overview file (whatever it is called locally — `requirements/app-overview.md` is the conventional path) has a `locked_constraints` block. Library fork commit hashes (e.g. smsmms) are locked there. Treat those hashes as immutable: never bump them inside this skill — bumps go through the project's update workflow.
- Kotlin + AndroidX. Compose may or may not be present — these patterns are framework-agnostic and run from regular `Activity` / `ComponentActivity` / DI-injected service classes alike. Glance widgets specifically require Compose; the widget reference notes the pin.

If any assumption fails (e.g. project uses Java only, or `compileSdk` is 28), stop and ask before generating code.

## Procedure

### Step 0 — Identify which concern the request hits

| User asks | Concern | Read |
|---|---|---|
| "wire the incoming SMS receiver", "RECEIVE_SMS", "SMS_DELIVER", "broadcast receiver for X" | BroadcastReceiver | `references/broadcast-receivers.md` |
| "send SMS in a service", "background MMS upload", "RESPOND_VIA_MESSAGE", "foreground service for X" | Service | `references/services.md` |
| "read the telephony provider", "load conversations from content://sms", "ContentObserver", "paginate messages" | ContentProvider | `references/contentprovider-sms.md` |
| "make app the default SMS handler", "RoleManager", "ROLE_SMS", "request default SMS role", "denied default" | Default-SMS role | `references/default-sms-role.md` |
| "integrate smsmms", "send MMS", "Transaction.sendNewMessage", "smsmms fork" | smsmms | `references/smsmms-overview.md` |
| "request SMS permissions", "READ_SMS denied", "rationale", "READ_CONTACTS for names", "POST_NOTIFICATIONS", "SCHEDULE_EXACT_ALARM" | Permissions | `references/permissions.md` |
| "add a home-screen widget", "AppWidgetProvider", "RemoteViews list widget", "Glance widget", "widget configure activity" | App widget | `references/app-widget-provider.md` |
| "build a live wallpaper", "WallpaperService", "WallpaperService.Engine", "wallpaper picker deep link" | Live wallpaper | `references/live-wallpaper-service.md` |
| "register an accessibility service", "AccessibilityService", "TYPE_VIEW_CLICKED", "accessibility-service-config" | Accessibility | `references/accessibility-service.md` |
| "listen to notifications", "NotificationListenerService", "cancelNotification", "notification access settings" | Notification listener | `references/notification-listener-service.md` |
| "make the app a launcher", "CATEGORY_HOME", "ROLE_HOME", "default home app", "app drawer query" | Launcher | `references/launcher-app.md` |
| "floating overlay", "SYSTEM_ALERT_WINDOW", "draw over other apps", "TYPE_APPLICATION_OVERLAY", "chat head" | Overlay | `references/overlay-service.md` |
| "add a shortcut", "ShortcutManager", "pinned shortcut", "dynamic shortcut", "Sharing Shortcut", "Direct Share" | Shortcuts | `references/shortcuts.md` |

A single feature often touches several concerns at once (e.g. an overlay service needs `SYSTEM_ALERT_WINDOW` permission **and** a foreground service). Order the work as follows so manifest changes happen once and the runtime flow comes up cleanly:

1. **Permissions + role / special-permission declarations** (`references/permissions.md`, plus the role file for the specific concern: `default-sms-role.md`, `launcher-app.md`, `accessibility-service.md`, `notification-listener-service.md`, `overlay-service.md`) — manifest declarations and Settings deep-link Activities.
2. **Components** (`references/broadcast-receivers.md`, `references/services.md`, `references/contentprovider-sms.md`, plus the Group B component file for the concern: `app-widget-provider.md`, `live-wallpaper-service.md`, etc.) — `<receiver>`, `<service>`, `<provider>` blocks + Kotlin classes.
3. **Role + permission runtime flow** — Activity-side request / Settings deep-link code, re-check on `onResume`.

### Step 1 — Pre-flight

Before generating code, confirm:

1. Target SDK + min SDK match the assumptions above **and** the per-reference min-API floor for the concern in play.
2. The project's `AndroidManifest.xml` already lists `<uses-permission>` for any permission you're about to use at runtime — runtime-permission requests fail silently for permissions not declared in the manifest. Add `<uses-permission>` first, then code the request.
3. Special permissions (`SYSTEM_ALERT_WINDOW`, `SCHEDULE_EXACT_ALARM`, notification-listener access, accessibility-service access) are **not granted by the runtime dialog**. The user grants them via a Settings deep-link. Plan the UI flow for the deep-link round-trip and the `onResume` re-check.
4. If touching a vendored / forked library (smsmms is the canonical case): check the project's `app-overview` `locked_constraints` for the fork commit hash. If absent, **stop** — pinning the fork is the architect's call, not this skill's.
5. If adding a `<receiver>`, `<service>`, `<provider>`, or `<activity>` that the system binds to: it must have `android:exported` set explicitly on API 31+. Implicit `exported` is a build-time error. System-binding components also require their guarding permission (`BIND_*`) declared on the component, not just on the app.

### Step 2 — Generate code from the matching reference

- One reference file per concern. Do not paste patterns from multiple references into a single file unless the feature genuinely spans them (the SMS-send path does — receiver + service + telephony provider in one feature; the overlay-service path does — service + special-permission flow).
- Manifest edits are **additive**. Do not rewrite the whole `<application>` block — `Edit` the specific entries you own.
- DI: where this skill creates a `BroadcastReceiver` / `Service` that must be injected, follow the project's existing DI shape (Hilt / Dagger / Koin / pure). This skill does not own DI conventions — it only writes the platform-component class.
- On API 31+, every `PendingIntent.get*(...)` call you write must pass `FLAG_IMMUTABLE` (or `FLAG_MUTABLE` if a system feature like `RemoteInput` reply requires it). This is a framework rule, not a per-component concern — apply it inline wherever you construct PendingIntents.

### Step 3 — Manifest sanity pass

After the generated `<receiver>` / `<service>` / `<provider>` / `<activity>` lands:

- Every component has `android:exported="true|false"` set explicitly.
- System-binding components have the guarding permission set on the component itself: `BIND_WALLPAPER`, `BIND_ACCESSIBILITY_SERVICE`, `BIND_NOTIFICATION_LISTENER_SERVICE`, `BIND_REMOTEVIEWS` (for list-widget services), etc. Missing the bind permission means the system silently refuses to bind.
- Default-SMS-app role: the four required `<intent-filter>` / `<service>` blocks are all present (`SMS_DELIVER` receiver, `WAP_PUSH_DELIVER` receiver, `RESPOND_VIA_MESSAGE` service, send-to activity). Missing any of the four → role request will silently fail to even show the chooser. Checklist in `references/default-sms-role.md`.
- Launcher: `CATEGORY_HOME` + `CATEGORY_DEFAULT` + `CATEGORY_LAUNCHER_APP` triple is intact. Missing `DEFAULT` hides the app from the Home-app chooser.
- App widget: `APPWIDGET_UPDATE` filter + `<meta-data android:name="android.appwidget.provider">` both point at an existing `res/xml/` resource.
- Live wallpaper: `<service>` action is exactly `android.service.wallpaper.WallpaperService` and `<meta-data android:name="android.service.wallpaper">` resource exists.
- Accessibility: `<meta-data android:name="android.accessibilityservice">` resource exists; the config declares only the event types the feature needs (no `typeAllMask`).
- Foreground services that bear overlays / play media / take pictures / etc. declare `android:foregroundServiceType` matching the actual workload, and (for `specialUse` on API 34+) the `<property android:name="android.app.PROPERTY_SPECIAL_USE_FGS_SUBTYPE">` is filled in.
- All `<uses-permission>` referenced by runtime requests or by manifest-declared component guards are declared.

### Step 4 — Compile + smoke

- Run `./gradlew :app:assembleDebug` (or the project's compile task) before reporting done.
- If a real device or emulator is available and the change touches a role / special-permission flow, install and verify the app appears in the relevant Settings screen:
  - Default SMS app → *Settings → Apps → Default apps → SMS app*
  - Home app → *Settings → Apps → Default apps → Home app*
  - Accessibility → *Settings → Accessibility → Installed services*
  - Notification listener → *Settings → Notifications → Device & app notifications → (your app)*
  - Overlay → *Settings → Apps → Special app access → Display over other apps*
  - Live wallpaper → *Settings → Wallpaper → Live Wallpapers*
  - App widget → long-press home screen → Widgets
  If your component is missing from the relevant list, the `<intent-filter>` / `<meta-data>` set is incomplete — go back to Step 3.
- For a runtime permission change: cold-launch on a device with all permissions revoked and confirm the rationale screen renders before the system prompt. Do not skip this — it is the only way to catch the "permission declared but never requested" silent-fail mode.
- For a special-permission change: cold-launch, trigger the flow, confirm the Settings deep-link opens, grant, return — confirm the `onResume` re-check picks up the new state without a kill-restart.

### Step 5 — Report

State:

- Files created or modified, grouped by concern (manifest, component class, runtime flow).
- Permissions declared and the runtime entry point (or Settings deep-link) that requests them.
- For role / Default-app flows: which manifest blocks were added vs were already present.
- For Group B components: the specific Play-policy disclosure (if any) the release needs — accessibility services, notification listeners, overlays, launchers with `QUERY_ALL_PACKAGES`, SMS-handler apps all require a Play Console disclosure form.
- Compile result.
- Anything skipped + why.

## Hard rules

- **Never** edit a third-party library's source in place. If smsmms (or any other) library needs a patch, the project must depend on a forked artifact whose commit hash is pinned in `locked_constraints` — bumping the hash goes through the project's update workflow.
- **Never** declare a `<receiver>` / `<service>` / `<provider>` / `<activity>` that the system binds to without (a) explicit `android:exported`, and (b) the matching `BIND_*` permission on the component. Implicit `exported` is a build error on API 31+; missing the bind permission lets any app bind to the component, which is a security finding.
- **Never** do >5 seconds of work in `BroadcastReceiver.onReceive` (including `AppWidgetProvider.onUpdate`). Use `goAsync()` or hand off to a `Service` / WorkManager.
- **Never** put telephony / system-provider reads or any I/O on the main thread. Telephony providers can stall on devices with 10k+ messages; package-manager scans on launchers stall on devices with 200+ apps — use a coroutine on `Dispatchers.IO` (or the project's repository-layer dispatcher).
- **Never** assume the app holds a system role at runtime. Always check via the role's API (`Telephony.Sms.getDefaultSmsPackage`, `RoleManager.isRoleHeld`, `Settings.canDrawOverlays`, `enabled_notification_listeners` string, `enabled_accessibility_services` string) before invoking a role-gated API. The system silently drops calls from non-role-holders.
- **Never** skip the rationale screen for dangerous permissions, and never skip the Settings deep-link for special permissions. Both are user-facing requirements; both have silent-fail modes if you get the order wrong.
- **Never** request a role / special permission from a context that cannot observe the result. Use `registerForActivityResult(...)` (or the legacy `startActivityForResult` + `onActivityResult`) and re-check the role/permission state in the callback **and** on `onResume`.
- **Never** start a foreground service for a system integration without declaring `android:foregroundServiceType` matching the workload on API 29+. On API 34+, `specialUse` additionally requires `PROPERTY_SPECIAL_USE_FGS_SUBTYPE`.
- **Never** construct a `PendingIntent` on `compileSdk >= 31` without `FLAG_IMMUTABLE` or `FLAG_MUTABLE`. This is a framework rule, not a per-component concern; apply it inline.
- **Never** ship a wallpaper / accessibility / notification-listener / overlay-bearing / launcher-with-`QUERY_ALL_PACKAGES` / SMS-handler app without filling in the matching Play Console disclosure.

## Output format when done

Report per the Step 5 checklist. If the change touches `locked_constraints` (e.g. you discovered a vendored library's fork hash needs a bump), do **not** modify it inside this skill — surface the finding and route to the project's update workflow.
