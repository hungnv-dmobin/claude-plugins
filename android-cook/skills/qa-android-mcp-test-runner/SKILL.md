---
name: qa-android-mcp-test-runner
argument-hint: <FEAT-ID | phase-N | "smoke">
description: Execute the qa/test-cases/<FEAT-ID>.md test plan on a real device or emulator via mobile-mcp; files each failure as its own qa/bugs/BUG-XXXX.md. Read-only on dev source. Use for device-side smoke, bug repro on hardware, or behaviour JVM tests cannot exercise; requires locale-report all_clear first. Triggers: "run the mcp test pass", "reproduce BUG-NNNN on device".
allowed-tools: >
  Read Grep Glob Write Edit
  Bash(./gradlew :app:installDebug)
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
  mcp__mobile-mcp__mobile_list_available_devices
  mcp__mobile-mcp__mobile_get_screen_size
  mcp__mobile-mcp__mobile_get_orientation
  mcp__mobile-mcp__mobile_set_orientation
  mcp__mobile-mcp__mobile_list_apps
  mcp__mobile-mcp__mobile_launch_app
  mcp__mobile-mcp__mobile_terminate_app
  mcp__mobile-mcp__mobile_install_app
  mcp__mobile-mcp__mobile_uninstall_app
  mcp__mobile-mcp__mobile_take_screenshot
  mcp__mobile-mcp__mobile_save_screenshot
  mcp__mobile-mcp__mobile_list_elements_on_screen
  mcp__mobile-mcp__mobile_click_on_screen_at_coordinates
  mcp__mobile-mcp__mobile_double_tap_on_screen
  mcp__mobile-mcp__mobile_long_press_on_screen_at_coordinates
  mcp__mobile-mcp__mobile_swipe_on_screen
  mcp__mobile-mcp__mobile_type_keys
  mcp__mobile-mcp__mobile_press_button
  mcp__mobile-mcp__mobile_open_url
  mcp__mobile-mcp__mobile_get_crash
  mcp__mobile-mcp__mobile_list_crashes
  mcp__mobile-mcp__mobile_start_screen_recording
  mcp__mobile-mcp__mobile_stop_screen_recording
---

## When to use

Execute the markdown test plan at `qa/test-cases/<FEAT-ID>.md` directly on a real device or emulator via the `mobile-mcp` server (https://github.com/mobile-next/mobile-mcp). Drives the device through each TC's steps using accessibility-tree snapshots + coordinate taps, asserts expected results, and files every failure as its own `qa/bugs/BUG-XXXX.md`. Read-only on dev source. Model-invocable: the `qa-agent-android` teammate fires this skill autonomously once locale-report is green and the phase reaches the execution gate, the same way it fires `qa-test-runner`. Trigger on "run the mcp test pass", "execute the test plan on device", "drive smoke on the emulator", or "reproduce BUG-NNNN on device".

When to use: Use as the device-side execution path for `qa/test-cases/<FEAT-ID>.md` plans — complementary to `qa-test-runner` (Gradle/JVM Compose journey tests). Pick this skill for quick smoke validation without compiling Kotlin, for cross-device parity checks, for bug repro on real hardware, or for behaviour the JVM/Robolectric path cannot exercise (telephony, SMS role, launcher, accessibility services). Do NOT use this skill to write Kotlin journey tests (that is `qa-test-runner`). Do NOT use before `qa/locale-report-phase-NN.md` shows `all_clear: true`. Do NOT modify dev source, build scripts, or tests. One bug per failure — never group.

# QA MCP Test Runner

## Mode gate

Read `requirements/app-overview.md` `locked_constraints` for the `qa_mode` entry. If `qa_mode == kotlin`, **stop with one line:** *"qa_mode=kotlin excludes the device-MCP channel; no device run for this project. The mirror skill `qa-test-runner` handles execution via Gradle."* Do not invoke any `mobile-mcp` tool. If the field is absent (legacy projects predating the qa_mode selector), treat it as `kotlin` and stop. If `qa_mode ∈ {mcp, both}`, proceed with the loop below.

Standing instructions for the **device-side** execution path of the QA layer. Reads the canonical markdown test plan (`qa/test-cases/<FEAT-ID>.md`), drives a real device or emulator through each test case using `mobile-mcp` tools, and files every failure as `qa/bugs/BUG-XXXX.md`.

This skill is the parallel of `qa-test-runner`. Both consume the **same** markdown plan; they differ only in the execution channel:

| Skill | Channel | Layer | Filename convention |
| :---- | :------ | :---- | :------------------ |
| `qa-test-runner` | `./gradlew connectedAndroidTest` | Layer-3 Compose journey, JVM-driven | `app/src/androidTest/.../*JourneyTest.kt` |
| `qa-android-mcp-test-runner` (this) | `mobile-mcp` MCP server | Device-driven, no Kotlin written | none — execution log only |

Pick this skill when you need real-device coverage (telephony, SMS-role hand-off, launcher, accessibility services, wallpapers, overlays), cross-platform parity, or bug reproduction without recompiling. Pick `qa-test-runner` for the hermetic CI-style pass. **Both can run for the same FEAT-ID** — they record results independently into `qa/bugs/`.

References (load only the one matching the work):

- [`references/mobile-mcp-tools.md`](references/mobile-mcp-tools.md) — full MCP tool catalogue (device discovery, app management, screen interaction, input/navigation, recording), platform notes (iOS vs Android), and the accessibility-tree-first / screenshot-fallback decision rule.
- [`references/execution-patterns.md`](references/execution-patterns.md) — patterns for translating a markdown TC step into MCP calls, element lookup by `testTag` / `content-desc` / text, the `waitUntil` analog (poll-and-retry on `mobile_list_elements_on_screen`), assertion mapping (visible / enabled / text), and crash detection via `mobile_get_crash`.
- [`references/adb-recipes.md`](references/adb-recipes.md) — `adb` command reference for everything **around** the app that `mobile-mcp` does not expose: fast state resets (`pm clear`, `am force-stop`), permission setup (`pm grant/revoke`), network toggles (`svc wifi/data`), full crash logs (`logcat -b crash`), deep-link firing (`am start -W -d`), screen wake / keyguard dismiss, time / locale notes, and the pre-approved adb command subset. Load this when a TC's precondition is "device in state X" rather than "app in state X".

## Four rules that override anything else

1. **Read-only on dev source.** This skill never edits application Kotlin, XML, build scripts, DI modules, or unit/instrumented tests. The artefact you write is the execution log + bug files; nothing else. If a behaviour cannot be exercised because the UI is missing a `Modifier.testTag` / `contentDescription`, file a `category: technical, severity: minor` bug to UI dev and continue with the next TC — do not edit the screen to make the test pass.

2. **Localization gate.** Before running, read `qa/locale-report-phase-NN.md` for the current phase. If `all_clear` is `false` or the file does not exist, **stop**. Notify the integration-lead. Same rule as `qa-test-runner`: the device must exercise the translated strings the user will see, not placeholders.

3. **Execution-gate before invocation.** Mobile-MCP execution has real device side effects (installs APKs, taps elements, types into fields, can dismiss system dialogs). The `qa-agent-android` teammate fires this skill autonomously — same as `qa-test-runner` — but only after the locale-report is green AND `qa_mode ∈ {mcp, both}` AND the phase is at the execution gate. Do not fire on ad-hoc "test this" phrasing; the QA teammate's standing instructions enforce the gate.

4. **One bug per file.** Every failure becomes its own `qa/bugs/BUG-XXXX.md` via the `qa-bug-tracker` schema. Never write a per-feature rollup; never merge two failures into one record. The bug body cites the TC-ID, AC-ID, and the MCP screenshot path (saved during the failure step).

## Inputs

Read, in order:

1. **`qa/test-cases/<FEAT-ID>.md`** — the canonical markdown test plan. Frontmatter `feat_ref`, `ac_refs[]`, `smoke`, `file_globs[]`, `spec_version`, `kt_path`. Body's TC-IDs and AC-ID references are the authoritative list. The Kotlin path (`kt_path`) is **not used** by this skill — we never write or run the Kotlin file — but the markdown body is identical to what `qa-test-runner` consumes.
2. **`specs/<FEAT-ID>-*.md`** — for exact `AC-<scope>-NNN` wording, string keys (`R.string.<key>`), and any specified `testTag` / `contentDescription` values. The spec is the authoritative source of expected copy and selectors; do not match against English literals — translated locales would break.
3. **Dev source** (read-only, via `Grep`) — locate the actual `testTag(...)`, `contentDescription = "..."`, or `text = stringResource(...)` values the screen uses. Used to resolve markdown selectors to on-device element identifiers.
4. **`qa/locale-report-phase-NN.md`** — verify `all_clear: true` before driving the device.
5. **App APK** — the `:app:installDebug` Gradle output (`app/build/outputs/apk/debug/app-debug.apk`) or whichever artefact the integration-lead has marked installable for the current phase.

## Workflow

### Step 1 — Validate inputs

- Confirm `qa/test-cases/<FEAT-ID>.md` exists and `spec_version` matches the spec's `version`. If stale, **stop** — `qa-test-case-generator` must regenerate the plan first; running against a stale plan files bugs against AC-IDs that may have been renumbered.
- Confirm `qa/locale-report-phase-NN.md` `all_clear: true`. If not, stop.
- Confirm the APK exists at the expected output path. If not, ask the integration-lead to run `./gradlew :app:installDebug` (do **not** run it yourself — build is dev's responsibility).

### Step 2 — Pick a device

```text
mobile_list_available_devices  →  pick one
```

Selection rule (in order):

1. If the user passed an explicit device name as an argument, use it.
2. Otherwise prefer an emulator over a real device (deterministic, disposable, no carrier costs for SMS features).
3. Otherwise pick the first device whose platform matches the FEAT-ID's target (Android for this project; iOS only if the project's `app-overview.md` lists iOS in `locked_constraints`).

If zero devices are visible, **stop** and report: the MCP server needs `adb` to see at least one emulator or USB-connected device. Do not attempt to start an emulator from this skill — that is environment setup, not a test responsibility.

### Step 3 — Install + launch the app

```text
mobile_install_app  →  path = app-debug.apk
mobile_launch_app   →  packageName from app-overview.md
```

Read the project's package name from `app-overview.md` `locked_constraints.application_id` (or wherever the constraint lives). Never hardcode `com.example.sms` — the package is project-specific.

If `mobile_install_app` returns an existing-package conflict (different signing key), **stop** and route to the integration-lead — uninstalling could destroy under-test state the user wants preserved. Do not auto-uninstall.

### Step 4 — Resolve selectors

Before driving any TC, build a **selector map** for the FEAT-ID's screens:

1. For each `SCR-*` ID in the spec's `screen_refs`, navigate to that screen (using the userflow's primary path) and call `mobile_list_elements_on_screen`.
2. Match each spec test-ID to an on-device element. Match priority: explicit accessibility id (`testTag` becomes `resource-id` on Android, `accessibilityIdentifier` on iOS) → `content-desc` → exact visible text (resolved through `stringResource` to the current locale).
3. Record the `(x, y)` centre and bounds for each resolved element in an in-memory map keyed by spec test-ID.

If a spec test-ID does not resolve on the device, file a `category: technical, severity: minor` bug ("UI element missing accessibility identifier — MCP test cannot interact with it") and mark the corresponding TCs `BLOCKED` in the execution log. Do not guess at coordinates; the next layout change would break the run silently.

See [`references/execution-patterns.md`](references/execution-patterns.md) for the full element-lookup algorithm and the screenshot-fallback rule for elements the accessibility tree does not expose.

### Step 5 — Run each test case

Iterate the markdown body in declared order. For each `### TC-<scope>-NNN — <title>` block:

1. **Reset to preconditions.** Most TCs assume the home screen of the feature; terminate and relaunch the app (or use `mobile_press_button BACK` until the home screen is visible) unless the previous TC's expected end-state matches the new TC's preconditions. Re-resolve any selectors that depend on dynamic state.
2. **Execute steps.** For each numbered step in the markdown, map the user action to MCP calls — see [`references/execution-patterns.md`](references/execution-patterns.md) for the full mapping. Common ones:
   - "Tap the Send button" → `mobile_click_on_screen_at_coordinates` at the resolved `send_button` element's centre.
   - "Type 'hello'" → `mobile_type_keys` with `text = "hello"`.
   - "Wait for the home screen to settle" → poll `mobile_list_elements_on_screen` until an expected anchor element appears, max 5s; on timeout, fail the TC with `category: technical, severity: minor` (flaky / slow), do not extend the timeout silently.
3. **Assert expected results.** For each bullet under **Expected result**, derive an assertion type and check it:
   - "X is visible" → element appears in the next `mobile_list_elements_on_screen` snapshot.
   - "Text shows string key `foo_bar`" → resolve `foo_bar` against `values/strings.xml` for the active locale, then assert that string appears in an element's `text` / `name` field.
   - "Navigates to SCR-…" → assert at least one element with a known anchor selector for that screen is visible.
   - "No error toast / snackbar" → assert no element whose text matches any `R.string.*error*` key (read the spec for the specific keys to negative-match against).
4. **Capture evidence on failure.** Before filing the bug:
   - `mobile_save_screenshot` to `qa/evidence/BUG-XXXX-step-NN.png`.
   - `mobile_get_crash` — if there is an unhandled crash since launch, attach the stack trace summary to the bug body.
   - Optionally `mobile_start_screen_recording` at TC start for any TC tagged `@flaky` in the plan; stop and save at TC end whether it passed or failed.

### Step 6 — File bugs

For each failing TC, invoke the `qa-bug-tracker` procedure (see that skill's SKILL.md). Frontmatter rules specific to MCP-discovered bugs:

- `category: technical` — for crashes (`mobile_get_crash` non-empty), unresolvable selectors, or timeouts.
- `category: flow` — for AC misses (wrong string, wrong navigation, wrong screen state).
- `category: both` — both technical and flow defects in the same TC (rare; usually means the TC is testing too many things).
- `severity` — use the standard ladder: `blocker` if main flow is broken or app crashes; `major` if an alternate flow or AC misses on the main path; `minor` for cosmetic / edge cases.
- `assignee` — default route: `software-architect-android` for `technical`, `ba-agent` for `flow`, both for `both` (integration-lead breaks ties).
- `spec_ref` — the FEAT-ID.
- `ac_ref` — the specific `AC-<scope>-NNN` that failed.

Cite the markdown TC ID, the MCP step number where the failure occurred, and the screenshot path in **Steps to Reproduce**. Example:

```
Steps to Reproduce:
1. qa/test-cases/FEAT-014.md TC-CONV-003 step 4: tap "send_button" at (540, 1820)
2. Expected: snackbar with R.string.conv_send_failed_retry visible
3. Actual: snackbar absent; screenshot qa/evidence/BUG-0123-step-04.png
4. Crash log: none
```

### Step 7 — Filter false positives

Same rules as `qa-test-runner`, restated for the MCP context:

- **Device-environment failures** (adb disconnect, emulator OOM, mobile-mcp server crash) — do not file as app bugs. Log in the execution summary and re-run.
- **Missing accessibility identifiers** — file as `category: technical, severity: minor`, assign to UI dev. Mark TC as `BLOCKED`, not `FAILED`.
- **Flaky timing** — if `waitUntil` succeeds on a retry within the standard 5s window, the TC passes; if it requires extending the window, note the flake in the bug body and tag the markdown TC `@flaky` for the next cycle (this is a markdown edit to `qa/test-cases/<FEAT-ID>.md` only, which is QA-owned, not dev source — allowed).

### Step 8 — Report back

One message:

1. Pass rate: `N passed / M total / K blocked` for this FEAT-ID (or phase, if a phase run).
2. Bugs filed: list of `BUG-XXXX` IDs with one-line titles and severities.
3. Any `blocker` or `major` bugs — these block the phase merge gate, same as Gradle-channel bugs.
4. Smoke status: did smoke pass on the device? (If running smoke-only for a prior-phase regression.)
5. Anything the integration-lead needs to see — device disconnects, server restarts, persistent flakes.

Do not paste screenshots or MCP element dumps in chat — they go to `qa/evidence/` and the bug files.

## Hard rules summary

- **Never modify dev source** — Kotlin, XML, build scripts, DI modules, instrumented tests.
- **Never fire outside the execution gate** — locale-report green AND `qa_mode ∈ {mcp, both}` AND phase at execution gate. The QA teammate owns the gate check before invoking this skill.
- **Never write `BUG_REPORT_<Feature>.md`** — one bug = one `qa/bugs/BUG-XXXX.md`.
- **Never use severity `Critical | High | Medium | Low`** — the ladder is `blocker | major | minor`.
- **Never run before the locale report is green** — `all_clear: true` is the gate.
- **Never write Kotlin journey tests** — that is `qa-test-runner`. This skill never produces `*JourneyTest.kt`.
- **Never hardcode coordinates** — always derive from `mobile_list_elements_on_screen`; record the resolved centre in the bug body if needed, but the source of truth is the live accessibility tree.
- **Never start, stop, or reset the emulator from this skill** — that is environment setup; ask the integration-lead.
- **Never auto-uninstall** the app on signing conflict — route to integration-lead.

## Common mistakes — re-check before running

- **Running against a stale plan.** Always diff `spec_version` first. The QA agent's diff-and-regenerate contract exists exactly to prevent this.
- **Asserting on English literals.** The app is i18n from Phase 1; resolve string keys against the **active locale's** `values-<locale>/strings.xml`, not English.
- **Treating a `BLOCKED` TC as a `FAILED` TC.** Blocked means the device cannot exercise the case (missing accessibility id, missing permission, app not installed); failed means the device exercised it and the result was wrong. The bug categories differ.
- **Tapping by coordinates that came from a screenshot AI guess.** If `mobile_list_elements_on_screen` returns an element, use its bounds. If it does not, use `mobile_take_screenshot` + visual reasoning **only** as a documented fallback in the bug body — and file a missing-accessibility-id bug against UI dev.
- **Forgetting `mobile_get_crash` on each failure.** A silent ANR or crash often manifests as "expected element missing"; the crash log gives the real cause.
- **Re-using a session across phases.** Terminate and reinstall between phase runs to avoid leaked state (drafts, permission grants, notification subscriptions).
