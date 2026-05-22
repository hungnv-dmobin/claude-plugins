# Execution patterns

How to translate a markdown test case from `qa/test-cases/<FEAT-ID>.md` into `mobile-mcp` calls. Loaded on demand by `qa-android-mcp-test-runner` SKILL.md.

## Pattern 0 — Element-lookup algorithm

Every interaction starts here. Given a spec selector (a `testTag` value, a `contentDescription`, or a string-key reference), resolve it to an on-device element:

```text
1. Call mobile_list_elements_on_screen → list of elements with
   { text, resource_id, content_desc, bounds, enabled, focused }

2. Try, in order:
   a. resource_id == "<package>:<spec.testTag>"     ← canonical (Compose testTag)
   b. content_desc == "<spec.contentDescription>"   ← accessibility label
   c. text == resolve(spec.stringKey, locale)       ← visible text in active locale

3. If a match is found:
   - center = midpoint of bounds
   - record { selector, element } in the selector map for the screen

4. If no match is found AFTER one retry (poll cycle of ~500ms), file
   a category:technical, severity:minor bug: "selector <X> unresolved
   on device — UI element missing accessibility identifier". Mark the
   TC BLOCKED, NOT FAILED. Continue with the next TC.
```

The `<package>:` prefix on Android is the app's package name from `app-overview.md` `locked_constraints.application_id`. On iOS the `resource_id` field is the `accessibilityIdentifier` directly (no prefix).

## Pattern 1 — Step-to-MCP mapping

The markdown plan uses imperative user-language steps. Map them to MCP calls:

| Markdown step                                  | MCP call(s) |
| :--------------------------------------------- | :---------- |
| "Launch the app"                               | `mobile_launch_app(packageName)` |
| "Tap the <X> button"                           | `mobile_click_on_screen_at_coordinates(center of resolved <X>)` |
| "Long-press the <X> row"                       | `mobile_long_press_on_screen_at_coordinates(center of resolved <X>)` |
| "Type 'hello' into the message field"          | resolve message field → tap → `mobile_type_keys(text="hello")` |
| "Send the message" / "Submit the form"         | `mobile_type_keys(text="...", submit=true)` OR tap the explicit Send button if one exists |
| "Scroll down to load more"                     | `mobile_swipe_on_screen(direction="up")` from the list's centre |
| "Open the navigation drawer"                   | `mobile_swipe_on_screen(direction="right")` from the left edge |
| "Press Back"                                   | `mobile_press_button("BACK")` |
| "Press Home"                                   | `mobile_press_button("HOME")` |
| "Rotate to landscape"                          | `mobile_set_orientation("landscape")` |
| "Wait for the home screen to settle"           | poll `mobile_list_elements_on_screen` for the home-screen anchor selector, max 5s; on timeout, FAIL the TC |
| "Wait for the loading spinner to disappear"    | poll for absence of `progress_indicator` selector, max 10s |
| "Grant the SMS permission"                     | resolve the system dialog's "Allow" button by `content_desc`, tap it; if dialog absent assume already granted (verify by reading next-screen anchor) |
| "Open the deep link <url>"                     | `mobile_open_url(url)` |

Compound steps must be split. A TC step "Tap Send and verify the message appears" is two MCP operations + one assertion — the verification belongs in **Expected result**, not in **Steps**. If the markdown plan baked them together, file the TC's plan as a `qa-test-case-generator` regen target and proceed with the obvious split.

## Pattern 2 — Wait-and-poll (the `waitUntil` analog)

Mobile-MCP has no built-in `waitUntil`. Implement it as a bounded retry loop:

```text
deadline = now + 5_000ms          # 5s default; 10s for network-driven waits
while now < deadline:
    elems = mobile_list_elements_on_screen
    if condition_holds(elems):
        return success
    sleep ~250ms
return timeout failure
```

Conditions worth polling for:

- **Element appears** — a specific selector resolves.
- **Element disappears** — a specific selector no longer resolves (loading spinner gone).
- **Text changes** — element resolved by `resource_id` now has a different `text` value.
- **Screen transition** — the previous screen's anchor element is no longer present AND the next screen's anchor element is present.

Default windows:

- UI state change (button enabled, error appears): 5s.
- Network-driven (after a Send tap, after a refresh swipe): 10s.
- Cold-launch settle (after `mobile_launch_app`): 8s.

If a wait succeeds only after extending the window, the TC still passes for this run, but tag the markdown TC `@flaky` in `qa/test-cases/<FEAT-ID>.md` (QA-owned, so this edit is allowed) and note the flake in the execution summary.

## Pattern 3 — Assertion mapping

Map each bullet under **Expected result** to one of these assertion shapes:

| Expected-result bullet                                          | Assertion |
| :-------------------------------------------------------------- | :-------- |
| "<element> is visible"                                          | resolve selector; pass if found, fail otherwise |
| "<element> is hidden / not present"                             | resolve selector; pass if NOT found |
| "<element> is enabled / clickable"                              | resolve selector AND check `enabled == true` |
| "<element> shows text from string key `<key>`"                  | resolve `<key>` in active-locale `values-<locale>/strings.xml`; compare against element's `text` field |
| "Navigates to SCR-<ID>"                                         | poll for that screen's anchor selector; max 5s |
| "Snackbar / toast with key `<key>` appears"                     | poll for an element whose `text` matches the resolved string; max 5s window (toasts auto-dismiss after ~3s — keep window tight) |
| "No error toast / no error message"                             | negative-match: assert NO element exists whose text matches any of the spec's error string keys |
| "Field <X> is cleared"                                          | resolve `<X>`; check `text == ""` |
| "Message count is N"                                            | resolve list container; count matching child elements (the spec must declare the child selector) |

Locale resolution: read `values-<locale>/strings.xml` for the device's current locale. The device locale can be read via `mobile_list_elements_on_screen` indirectly (system dialogs' button text), or, more reliably, by recording the locale you set during install. For the agent-team pipeline, the locale-report for the current phase declares the locale under test; trust that.

## Pattern 4 — Crash & ANR detection

Call `mobile_get_crash` at three points per TC:

1. **Immediately after `mobile_launch_app`** — to clear any prior-run crash from the buffer.
2. **On every assertion failure** — a missing-element failure often masks a crashed activity; attach the stack summary to the bug body.
3. **At TC end (passed TCs included)** — silent crashes between steps fail to mask as failed assertions; this catch-net flips the TC from `passed` to `failed` if the crash buffer is non-empty.

When `mobile_get_crash` returns empty but the TC failed in a way that suggests a crash (sudden activity disappearance, ANR-like delay), fall through to the **adb crash buffer**: `adb logcat -d -b crash` (and the app-PID-filtered logcat) often surface stack traces the MCP buffer truncated. See [`adb-recipes.md`](adb-recipes.md) §"Logcat — richer than `mobile_get_crash`". Save the full log under `qa/evidence/BUG-XXXX-crash.log` and reference it in the bug body.

If a crash is detected mid-run:

- Severity is **always `blocker`** if the crash is in the app under test (the user cannot use the app).
- Severity is **`major`** if the crash is in a system process the app triggered (e.g. SMS-app role hand-off crashed system UI).
- `category: technical`.
- `assignee: software-architect-android`.

## Pattern 5 — Permission dialogs

Permission flows are the most common source of false-positive failures because the system dialog steals focus.

Strategy:

1. Before any TC that the spec says requires a runtime permission, snapshot `mobile_list_elements_on_screen` once on the first screen after launch. If a system dialog is present (Android: package `com.google.android.permissioncontroller` or text matching `Allow|Deny|While using the app`), drive it per the TC's preconditions ("permission granted" → tap Allow; "permission denied" → tap Deny).
2. If the dialog is not present, the permission is already granted from a prior run — that is fine when the TC says "User has granted X permission"; it is a precondition mismatch if the TC says "User has not yet granted X permission". In the mismatch case, terminate + uninstall + reinstall to reset permission state, then re-run the TC.

The Default-SMS-app role flow on Android 10+ is a specialised case: the `RoleManager.createRequestRoleIntent(ROLE_SMS)` dialog is system UI and **cannot** be auto-driven without `WRITE_SECURE_SETTINGS`. Drive it the same way as a runtime permission dialog (resolve the "Set as default" button by `content_desc` and tap), and if it does not respond within the 8s window, file a `category: technical, severity: minor` bug noting the OS-version + manufacturer (manufacturers customise the role dialog).

## Pattern 6 — Reset between TCs

Most TCs assume a clean entry state. Five reset strategies, from cheapest to most thorough (see [`adb-recipes.md`](adb-recipes.md) §"App lifecycle — state resets" for command shapes):

1. **Back to home** — `mobile_press_button("BACK")` until the current FEAT-ID's home-screen anchor resolves. ~ms. Use when consecutive TCs share preconditions.
2. **Terminate + relaunch** — `mobile_terminate_app` then `mobile_launch_app`. ~1s. Use when in-memory state must clear but persisted data should stay.
3. **`adb shell am force-stop` + relaunch** — same effect as (2) at the device level; useful when MCP's terminate is flaky. ~1s.
4. **`adb shell pm clear <pkg>` + relaunch** — clears DataStore / Room / SharedPreferences / cache while keeping the install. ~2s. Use when persisted state must reset for the next TC's precondition but a full reinstall would be wasteful. **This replaces uninstall+install as the default thorough reset.**
5. **Uninstall + reinstall** — `mobile_uninstall_app` then `mobile_install_app` then `mobile_launch_app`. ~30s. Last resort — use only when signing-key state, install-time perms, or first-launch onboarding state need to start from zero.

Strategy 5 requires explicit authorization from the integration-lead if real-device permissions were manually granted that should not be wiped. Prefer 1 → 2 → 3 → 4 → 5 and stop at the first that satisfies the next TC's preconditions.

**Permission preconditions** — when a TC requires "user has already granted X" or "user has not yet granted X", set it directly with `adb shell pm grant/revoke <pkg> <permission>` before relaunching, rather than driving the system dialog. See [`adb-recipes.md`](adb-recipes.md) §"Permission state — preconditions for permission TCs". Special permissions (overlays, accessibility, default-SMS role) are NOT settable this way — drive the Settings flow via mobile-mcp.

## Pattern 7 — Evidence per failure

For every TC that fails:

```text
1. mobile_save_screenshot → qa/evidence/<BUG-ID>-step-<NN>.png
2. mobile_get_crash       → attach trimmed stack to bug body
3. record in bug body:
     - markdown TC ID + line in qa/test-cases/<FEAT-ID>.md
     - step number that failed
     - resolved selector + (x,y) where applicable
     - assertion type + expected vs actual
     - screenshot path
     - crash log presence (yes / no) and excerpt
```

Cite the screenshot path with a repo-relative path so reviewers can open it directly from the bug file.

## Pattern 8 — Smoke runs

When the argument is `smoke` (instead of a specific FEAT-ID or phase), iterate every `qa/test-cases/<FEAT-ID>.md` whose frontmatter `smoke: true`, and within each file execute only the test cases tagged `@smoke`. All other patterns above apply unchanged.

Smoke timing budget: the entire smoke pass should complete in under ~10 minutes on an emulator. If it exceeds that, the smoke set is too large — surface it in the report so `qa-test-case-generator` can prune low-value `@smoke` tags on the next regeneration.
