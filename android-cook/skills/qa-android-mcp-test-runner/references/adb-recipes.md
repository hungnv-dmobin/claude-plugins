# adb recipes for MCP test runs

Reference for `qa-android-mcp-test-runner`. Loaded on demand. Covers the `adb` (Android Debug Bridge) commands that fill gaps `mobile-mcp` does not expose — fast state resets, permission setup, locale switching, network toggles, crash log capture, deep-link firing, screen unlock.

The MCP tool surface in [`mobile-mcp-tools.md`](mobile-mcp-tools.md) covers everything that happens *inside* the app once it is in a known state. `adb` is the right tool for everything that happens *around* the app — putting the device into the state the next test case requires.

This file documents commands; the calling skill enforces when/whether to use them.

## When to reach for adb instead of mobile-mcp

| Goal                                         | adb (faster / lower-level)                | mobile-mcp (UI-level)                 |
| :------------------------------------------- | :---------------------------------------- | :------------------------------------ |
| Reset app data without uninstalling          | `adb shell pm clear <pkg>` (~1s)          | `mobile_uninstall_app` + `_install_app` (~30s) |
| Set permission state for a precondition      | `adb shell pm grant/revoke <pkg> <perm>`  | drive the system permission dialog    |
| Switch device locale for the next TC         | `adb shell am broadcast …LOCALE_CHANGED`  | — not exposed                         |
| Toggle wifi / mobile data                    | `adb shell svc wifi/data enable/disable`  | — not exposed                         |
| Get the full crash stack with native frames  | `adb logcat -d -b crash`                  | `mobile_get_crash` (summary only)     |
| Fire a deep link bypassing the launcher      | `adb shell am start -W -a … -d <uri>`     | `mobile_open_url`                     |
| Force-stop the app (kill, no state change)   | `adb shell am force-stop <pkg>`           | `mobile_terminate_app` (equivalent)   |
| Wake screen + dismiss keyguard               | `adb shell input keyevent 224` + `wm …`   | — not exposed                         |
| Mock device time / timezone                  | `adb shell date / setprop persist.…tz`    | — not exposed                         |

Rule of thumb: **mobile-mcp drives the user-visible app; adb drives the device around the app.** Use the cheapest tool that achieves the precondition.

## Prerequisites

- `adb` on `PATH` (host machine).
- Device authorised: `adb devices` shows the target device with state `device` (not `unauthorized` or `offline`).
- For real devices: developer-mode + USB debugging enabled and authorised.
- Multi-device: every recipe below assumes a single device. With more than one, prefix `-s <serial>` after `adb` (e.g. `adb -s emulator-5554 shell pm clear …`).

## Device selection

```bash
adb devices                    # list all visible devices
adb -s <serial> <command>      # target a specific device
adb shell getprop ro.build.version.release   # Android version on the target
adb shell getprop ro.product.model           # device model name
adb shell wm size              # screen dimensions in px (paired with mobile_get_screen_size)
```

## App lifecycle — state resets

```bash
# Reset app state without uninstalling. Preferred between TCs that need a fresh start
# but should not pay the install/uninstall cost. Clears preferences, databases, caches.
adb shell pm clear <pkg>

# Kill the process without wiping state. Useful for cold-launch TCs where prior in-memory
# state should disappear but persisted data (DataStore, Room) should remain.
adb shell am force-stop <pkg>

# Disable / enable an installed app (rare; useful for testing "what if the app is disabled?").
adb shell pm disable-user <pkg>
adb shell pm enable      <pkg>

# Install / reinstall over the existing build, preserving data.
adb install -r <path-to-apk>

# Install a fresh build, replacing data and signature if necessary (DESTRUCTIVE — wipes state).
adb install -r -d -t -g <path-to-apk>      # -g = grant all manifest perms at install time
```

**Reset-strategy ladder** for `qa-android-mcp-test-runner` between TCs (cheapest → most thorough):

1. `mobile_press_button BACK` until at the feature home screen. ~ms.
2. `mobile_terminate_app` + `mobile_launch_app`. ~1s.
3. `adb shell pm clear <pkg>` + `mobile_launch_app`. ~2s.
4. `adb shell am force-stop <pkg>` + `mobile_launch_app`. ~1s (preserves persisted data).
5. `mobile_uninstall_app` + `mobile_install_app`. ~30s (last resort).

Pick the lowest-numbered strategy that gets to the next TC's preconditions.

## Permission state — preconditions for permission TCs

```bash
# Grant a runtime permission silently (the user-perspective state is "already granted").
adb shell pm grant <pkg> <permission>

# Revoke a runtime permission (the user-perspective state is "not yet granted" — system
# dialog will fire on next request). Use for the negative-path branch of permission TCs.
adb shell pm revoke <pkg> <permission>

# List currently-granted permissions for an app.
adb shell dumpsys package <pkg> | grep -E "granted=true|requested permissions"
```

Common runtime permissions for SMS/messaging apps:

```text
android.permission.READ_SMS
android.permission.SEND_SMS
android.permission.RECEIVE_SMS
android.permission.READ_CONTACTS
android.permission.WRITE_CONTACTS
android.permission.POST_NOTIFICATIONS   # API 33+
android.permission.READ_EXTERNAL_STORAGE
android.permission.CAMERA
android.permission.RECORD_AUDIO
```

**Special permissions** (NOT settable via `pm grant`):

- `SYSTEM_ALERT_WINDOW`, `SCHEDULE_EXACT_ALARM`, accessibility access, notification-listener access, Default-SMS-app role, Default-Launcher role.

These require driving the Settings UI or `RoleManager` flow via mobile-mcp; adb cannot grant them directly. (One exception: API 23+ allows `adb shell appops set <pkg> SYSTEM_ALERT_WINDOW allow` on some OEMs — fragile, do not rely on it.)

## Locale switching

```bash
# API 24+ — set system locale (requires CHANGE_CONFIGURATION grant, which adb has).
adb shell "su 0 setprop persist.sys.locale <bcp-47>"        # rooted only
# Reliable cross-API approach: use 'am broadcast' to switch and 'wm' to redisplay,
# but the most stable trick is the Android-tools 'adb shell setprop' + reboot — rarely
# needed because emulators can be created per-locale.

# Per-app locale (Android 13 / API 33+ AppLocale API):
adb shell cmd locale set-app-locales <pkg> --locales <bcp-47>

# Read the device's current locale:
adb shell getprop persist.sys.locale
adb shell settings get system system_locales
```

For `qa-android-mcp-test-runner`, the preferred pattern is **one emulator AVD per target locale**, not runtime locale switching — switching mid-run is fragile across API levels.

## Network state — for offline/online TCs

```bash
# Toggle wifi.
adb shell svc wifi enable
adb shell svc wifi disable

# Toggle mobile data.
adb shell svc data enable
adb shell svc data disable

# Airplane mode (toggles both; broadcast triggers system listeners).
adb shell settings put global airplane_mode_on 1
adb shell am broadcast -a android.intent.action.AIRPLANE_MODE
adb shell settings put global airplane_mode_on 0
adb shell am broadcast -a android.intent.action.AIRPLANE_MODE

# Read connectivity state.
adb shell dumpsys connectivity | grep -E "NetworkAgentInfo|Validated"
```

Use these for TCs whose precondition is "user is offline" or whose expected result is "network-error snackbar appears". Restore connectivity at TC end so the next TC starts in a known-good state.

## Logcat — richer than `mobile_get_crash`

`mobile_get_crash` returns a summarised crash. `adb logcat` returns the full stack, native frames, and surrounding events. Use it when the MCP crash buffer is empty but the test failed in a way that suggests a crash.

```bash
# Read the dedicated crash buffer (ANRs, fatal native, fatal exceptions). Most useful.
adb logcat -d -b crash

# Read everything since boot, filtered to the app under test.
adb logcat -d --pid=$(adb shell pidof -s <pkg>)

# Clear the log buffer before the next TC (otherwise prior-TC noise contaminates the dump).
adb logcat -c

# Stream live (rarely used in automation — for interactive debugging only).
adb logcat | grep <pkg>
```

Pattern for a TC that fails with a missing-element symptom: `adb logcat -c` at TC start, run the TC, on failure `adb logcat -d -b crash > qa/evidence/BUG-XXXX-crash.log` and attach the path to the bug body.

## Deep-link firing

When a TC's precondition is "user opened the app from a deep link", drive it via `am start` instead of pasting the URL in the system browser:

```bash
# Generic deep-link
adb shell am start -W -a android.intent.action.VIEW -d "<uri>"

# Targeted at the app under test (forces resolution to your component):
adb shell am start -W -a android.intent.action.VIEW \
  -d "myapp://conversation/42" \
  -n <pkg>/<.MainActivity>
```

`-W` blocks until the activity is up — useful so the next `mobile_list_elements_on_screen` snapshot is meaningful.

## Screen state — wake + unlock

For TCs that follow a sleep / lock state (notifications, reminders, alarms):

```bash
adb shell input keyevent 224      # KEYCODE_WAKEUP — wake the screen
adb shell wm dismiss-keyguard      # dismiss the lock screen (no PIN device only)
adb shell input keyevent 26        # KEYCODE_POWER — toggle screen state
```

If the device has a PIN/pattern, prefer `wm dismiss-keyguard` from a privileged adb shell; for protected devices, the test setup must use a no-lock-screen AVD.

## Input fallback — when mobile-mcp's typing is flaky

Rarely needed, but `adb shell input` provides a deterministic fallback if `mobile_type_keys` struggles with IME-mediated text:

```bash
adb shell input text "hello"              # types into the focused field
adb shell input keyevent KEYCODE_ENTER    # send Enter
adb shell input tap <x> <y>               # alternative to mobile_click_on_screen_at_coordinates
adb shell input swipe <x1> <y1> <x2> <y2> <duration-ms>
```

These bypass the accessibility-tree path entirely; prefer mobile-mcp for selector resolution and use `input` only on documented fallback.

## Time / date mocking

For features whose behaviour depends on date or timezone (alarms, "today/yesterday" labels, expiry):

```bash
# Set device time (requires root on most devices).
adb shell "date <MMDDHHMMYYYY>"     # rooted emulators only
adb shell "setprop persist.sys.timezone Asia/Tokyo"

# AVDs accept this via the emulator console:
#   telnet localhost 5554 ; auth <auth-token> ; geo fix … ; quit
```

If the host is unrooted, the only reliable approach is to set the time on the emulator at boot and design TCs around the chosen time.

## Screenshots via adb (fallback)

`mobile_save_screenshot` is the primary path. The adb equivalent is occasionally useful when the device is unresponsive to MCP:

```bash
adb shell screencap -p /sdcard/screen.png
adb pull /sdcard/screen.png qa/evidence/BUG-XXXX-step-NN.png
adb shell rm /sdcard/screen.png
```

## Activity / Service introspection

When a TC fails with "navigated to wrong screen", confirm which Activity is actually on top:

```bash
adb shell dumpsys activity activities | grep -E "mResumedActivity|topResumedActivity"
adb shell dumpsys activity recents | head -40
```

For service-driven features (foreground services, sync workers):

```bash
adb shell dumpsys activity services <pkg>
adb shell cmd jobscheduler get-job-state <pkg> <job-id>
```

## Common-pitfall checklist

- **`adb devices` shows `unauthorized`** — accept the host's RSA key fingerprint on the device. Until then no other adb command works.
- **`pm clear` killed the keystore for a TC that needs the user "already logged in"** — clear was too aggressive; downgrade to `am force-stop` or `pm clear-data --user 0 <pkg>` with care.
- **`pm grant` rejects a permission that was never declared in the manifest** — check `dumpsys package <pkg> | grep "requested permissions"`. You cannot grant unrequested perms.
- **`svc wifi disable` returns immediately but wifi is still on** — broadcast hasn't propagated; sleep 1s and re-check with `dumpsys connectivity`.
- **`adb logcat -b crash` is empty when the test definitely crashed** — the buffer was cleared earlier in the run. Either drop the `-c` step or capture before clearing.
- **Multi-user devices (work profiles)** — every `pm` and `am` command needs `--user 0` (or the relevant user-id); commands without it target user 0 by default, which may not be the test user.

## Pre-approved adb subset

The skill's `allowed-tools` pre-approves these adb command shapes so the QA teammate does not prompt for each invocation:

```
Bash(adb devices)
Bash(adb -s *)
Bash(adb logcat *)
Bash(adb shell pm clear *)
Bash(adb shell pm grant *)
Bash(adb shell pm revoke *)
Bash(adb shell pm disable-user *)
Bash(adb shell pm enable *)
Bash(adb shell am force-stop *)
Bash(adb shell am start *)
Bash(adb shell am broadcast *)
Bash(adb shell svc *)
Bash(adb shell settings put *)
Bash(adb shell settings get *)
Bash(adb shell input *)
Bash(adb shell wm *)
Bash(adb shell dumpsys *)
Bash(adb shell getprop *)
Bash(adb shell screencap *)
Bash(adb pull *)
Bash(adb install *)
```

Anything outside this set will prompt — that is by design. Adding new shapes requires editing SKILL.md `allowed-tools` and updating this recipe file.
