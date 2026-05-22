# mobile-mcp tool catalogue

Reference for the `mobile-mcp` MCP server tools used by `qa-android-mcp-test-runner`. Authoritative upstream source: <https://github.com/mobile-next/mobile-mcp> (`src/server.ts` has the parameter shapes).

This file is loaded on demand. The SKILL.md body should not duplicate it.

## Server install (one-time, project-owner)

```bash
claude mcp add mobile-mcp -- npx -y @mobilenext/mobile-mcp@latest
```

This adds the server to the user's MCP config. The skill itself never installs or restarts the server — that is operator setup.

Device prerequisites:

- **Android:** `adb` on `PATH`, an emulator running (`emulator -avd <name>`) or a USB device with debugging enabled.
- **iOS Simulator:** Xcode + a booted simulator (`xcrun simctl boot <udid>`).
- **iOS real device:** WebDriverAgent installed and trusted; outside the agent team's normal scope.

If `mobile_list_available_devices` returns an empty list, none of the above is satisfied. The skill stops there — it does not try to start an emulator.

## Tool catalogue

### Device management

| Tool | Purpose | Notes |
| :--- | :------ | :---- |
| `mobile_list_available_devices` | List every visible simulator, emulator, real device | Run first. If empty, stop. |
| `mobile_get_screen_size` | Pixel dimensions of the current device | Needed when computing percentages for swipes. |
| `mobile_get_orientation` | Read current portrait / landscape state | Most TCs assume portrait; assert before clicking. |
| `mobile_set_orientation` | Force portrait or landscape | Only set when the TC explicitly tests rotation. |

### App management

| Tool | Purpose | Notes |
| :--- | :------ | :---- |
| `mobile_list_apps` | Installed packages on the device | Use to confirm install succeeded or to find the package name. |
| `mobile_launch_app` | Start an app by package / bundle id | Use the project's locked `application_id`. Never hardcode. |
| `mobile_terminate_app` | Force-stop a running app | Use between TCs that need a cold start. |
| `mobile_install_app` | Install from `.apk`, `.ipa`, `.app`, `.zip` | On signing-conflict, **stop**; do not auto-uninstall. |
| `mobile_uninstall_app` | Remove the app | Only when explicitly authorised by the integration-lead. |

### Screen interaction

| Tool | Purpose | Notes |
| :--- | :------ | :---- |
| `mobile_take_screenshot` | Visual snapshot returned to the agent | Slow, large payload. Use as fallback evidence, not primary selector source. |
| `mobile_save_screenshot` | Persist screenshot to a path | Use to attach evidence to `qa/bugs/BUG-XXXX.md`. Save under `qa/evidence/`. |
| `mobile_list_elements_on_screen` | Accessibility tree of the current screen | **Primary selector source.** Returns text, accessibility id, coordinates, bounds for every interactable element. |
| `mobile_click_on_screen_at_coordinates` | Single tap at `(x, y)` | Always derive `(x, y)` from `mobile_list_elements_on_screen` element bounds — never guess. |
| `mobile_double_tap_on_screen` | Double-tap at `(x, y)` | Rare. Only when the TC explicitly tests a double-tap gesture (e.g. like, react). |
| `mobile_long_press_on_screen_at_coordinates` | Long press at `(x, y)` | Used for context menus, multi-select activation, drag-handle reveal. |
| `mobile_swipe_on_screen` | Directional swipe | Direction: `up | down | left | right`. Map "scroll down to load more" → swipe up; "open drawer" → swipe right from left edge. |

### Input & navigation

| Tool | Purpose | Notes |
| :--- | :------ | :---- |
| `mobile_type_keys` | Type a string into the focused element | Optional `submit: true` for fields whose enter key submits. |
| `mobile_press_button` | Hardware / system button | Valid Android values: `HOME`, `BACK`, `VOLUME_UP`, `VOLUME_DOWN`, `ENTER`, `POWER`. Use `BACK` to return between TCs. |
| `mobile_open_url` | Deep-link or browser URL | Useful for `intent://` deep links and for reaching the play-store / about screens. |

### Diagnostics & evidence

| Tool | Purpose | Notes |
| :--- | :------ | :---- |
| `mobile_get_crash` | Latest crash diagnostic since last call | Call on every TC failure — silent ANRs and crashes manifest as "element missing". |
| `mobile_list_crashes` | List crashes accumulated in the session | Useful in the post-run summary. |
| `mobile_start_screen_recording` | Begin recording to device storage | Use on TCs tagged `@flaky` in the markdown plan. |
| `mobile_stop_screen_recording` | Stop and save | Save under `qa/evidence/` with the BUG-ID and TC-ID in the filename. |

## Accessibility-first / screenshot-fallback rule

`mobile-mcp` exposes two interaction modes:

1. **Accessibility-tree snapshot** (`mobile_list_elements_on_screen`) — structured, deterministic, fast. Returns one record per interactable element with: visible text, `resource-id` (Android) / `accessibilityIdentifier` (iOS), `content-desc`, bounds, enabled state. **Use this for every selector resolution.**
2. **Screenshot + coordinate tap** (`mobile_take_screenshot` + `mobile_click_on_screen_at_coordinates`) — visual reasoning over a PNG. Slow, payload-heavy, ambiguous. **Use only when (1) returns nothing for an element the spec requires, and only as a fallback that triggers a missing-accessibility-id bug against UI dev.**

The accessibility tree is canonical because:

- Translated locales change visible text every release; the `resource-id` does not.
- Visual screenshots cannot disambiguate two buttons with the same icon at different positions when the layout changes.
- Compose `Modifier.testTag("foo")` becomes `resource-id = ":app/foo"` in the Android accessibility tree — directly addressable from the markdown plan's `testTag` references.

## Platform differences (Android vs iOS)

The agent team is Android-only by default. iOS notes for completeness:

| Concept | Android | iOS |
| :------ | :------ | :-- |
| App id | package name (`com.example.sms`) | bundle id (`com.example.SMS`) |
| Accessibility id | `Modifier.testTag` → `resource-id` | `accessibilityIdentifier` |
| Install artefact | `.apk` | `.ipa` (real device) / `.app` (simulator) |
| Permission grant | adb `pm grant` is unreliable from MCP — drive the system dialog | `xcrun simctl privacy` similar story — drive the dialog |
| Default-SMS-app role | Android system dialog only | Not applicable |

If the project's `app-overview.md` `locked_constraints` lists iOS, follow the iOS column. Otherwise stick to Android.

## Rate / cost considerations

- `mobile_take_screenshot` returns a base64 PNG — easily 200KB+ per call. Use sparingly; prefer `mobile_list_elements_on_screen`.
- `mobile_list_elements_on_screen` is the right "what's on screen?" call — it is cheap and structured.
- Screen recordings are large; only record `@flaky`-tagged TCs.
