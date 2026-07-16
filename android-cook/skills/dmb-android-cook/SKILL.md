---
name: dmb-android-cook
description: End-to-end Android task orchestrator — clarifies requirements, splits into testable subtasks, runs a dev-build-test-fix loop with dmb-android-dev/dmb-android-qa subagents until all pass on device, then a regression sweep. Use for Android features/bug-fixes needing code plus real-device QA; not for CI/Gradle-only or non-Android work. Trigger: "cook this task".
argument-hint: "<task description>"
allowed-tools: >
  Read Write Edit Glob Grep Bash
  AskUserQuestion Agent
  TaskCreate TaskUpdate TaskList
---

## When to use

End-to-end Android task orchestrator: clarifies requirements via targeted Q&A, breaks work into testable subtasks, then drives a sequential dev→build→test→fix loop using dmb-android-dev and dmb-android-qa subagents until all subtasks pass on device. Runs a final regression sweep and reports effort and rework hotspots. Trigger when the user says "cook this task", "implement and test this Android feature", or gives an Android dev task to build and verify on device.

When to use: Use for any Android feature, bug-fix, or screen-level enhancement that needs both code implementation and real-device QA verification via mobile-mcp. Covers single-screen changes and multi-screen flows. Not for infrastructure-only work (CI, Gradle config), pure documentation, or non-Android tasks.

# DMB Android Cook

Orchestrates Android development tasks from raw requirement to device-verified delivery. The current session is the **lead** — it scouts, plans, calls subagents in sequence, and reports. Subagents are short-lived; the lead holds all state across the cook loop.

---

## Stage 1 — Receive and scout

1. Accept the task description (argument or free-text user message).
2. Read project context in parallel (use `$ANDROID_PROJECT_PATH` or cwd if unset):
   - `app/src/main/AndroidManifest.xml` — package name, activities, declared permissions.
   - `app/src/main/java/<pkg>/` — top-level structure, main screens and entry points.
   - `README.md` or `docs/` — any existing feature or navigation docs.
   - `git log --oneline -10` — recent changes; avoid conflicts with in-flight work.
3. Identify **unclear domains** — areas where the description leaves open questions:
   - Exact UI behavior (what does the user see after tapping X?)
   - Navigation path to reach the affected screen
   - API contracts, data sources, or Room entities involved
   - Permissions required
   - Error states and edge cases

Collect gaps internally. Do not ask yet.

---

## Stage 2 — Clarify with the user

This stage borrows the discipline of the `grill-me` and `grill-with-docs` skills: interview relentlessly until shared understanding, but resolve every cheap branch in the codebase first so you only spend the user's attention on what code cannot answer.

### 2a — Sharpen before asking (preflight, no user contact)

Run this loop over the gaps from Stage 1 before drafting any question:

1. **Answer from the codebase first.** If a gap can be resolved by reading source, the manifest, a Room schema, navigation graph, or `git log`, read it — do **not** turn it into a user question. (grill-me principle: "if a question can be answered by exploring the codebase, explore the codebase instead".)
2. **Sharpen fuzzy language.** Replace vague verbs and overloaded nouns from the user's brief with precise terms grounded in the code (`Activity` vs `Composable` vs `screen`, `account` vs `user` vs `profile`, "save" vs "persist" vs "sync"). If the user used a term that conflicts with what the code already calls the same thing, flag it as a sharpening question.
3. **Stress-test relationships with concrete scenarios.** For each domain relationship the brief touches, invent one happy-path scenario and one edge-case scenario (empty list, no network, permission denied, back-stack interrupted, low memory, locale RTL). A relationship that breaks in either is not yet clarified.
4. **Cross-reference contradictions.** If the brief says "X already works" but the code shows otherwise (no such screen, route missing, dependency absent), promote the contradiction to a question — do not silently assume the brief is right or wrong.
5. **Walk the decision tree depth-first.** Order remaining gaps so each later question depends on earlier answers. Resolve roots before leaves — answering "which screen?" before "which interaction on that screen?" prevents wasted clarifications.

After preflight, only the gaps that genuinely require user input remain.

### 2b — Ask in batched rounds

Ask the remaining gaps in **one** `AskUserQuestion` call (max 4 questions, batched). Each question must:

- Name the precise ambiguity (no "what about X?" hand-waving).
- Offer 2–4 options with explicit trade-offs.
- Include a **recommended default** — never neutral. The recommendation is your judgement after preflight, and the user can redirect.
- Reference code or scenarios from preflight when relevant ("…the existing `SettingsScreen` already does it via Y — should the new screen mirror that, or…?").

If the task is fully unambiguous after preflight, skip to Stage 3.

### 2c — Deep-grill mode (optional, complex tasks only)

If the task spans multiple unfamiliar domains or the first batched round surfaces dependent follow-ups, switch to single-question grill-me style: ask one question, wait for the answer, branch on it, then ask the next. Use this when batching would force the user to answer downstream questions before knowing the upstream answer.

### 2d — Round limit

Maximum two rounds of questions (batched **or** grill-style — count each `AskUserQuestion` call as one round). After two rounds, mark remaining gaps `TBD` in the plan and flag as risks.

---

## Stage 3 — Plan subtasks

Derive testable subtasks from the clarified task.

**Keep as 1 subtask when:**
- Single screen, single interaction, verifiable in under 5 minutes.

**Split into 2–5 subtasks when:**
- Multiple screens or flows involved.
- Data layer must be wired before UI can be tested.
- Each slice is independently buildable and verifiable.

**Format each subtask:**

```
### TASK-NN — <short title>

**Goal:** One sentence — what "done" looks like from the user's perspective.

**Navigation to screen:**
Exact steps from app launch to the affected screen. dmb-android-qa follows these
verbatim to drive the device — use visible UI labels, not code identifiers.
  1. Launch the app (<package name>)
  2. Tap "<Button label>"
  3. ...

**Acceptance criteria:**
- [ ] AC-NN-01: <binary, testable — e.g. "Save button is enabled only when all required fields are non-empty">
- [ ] AC-NN-02: <...>

**Rework budget:** Pause and ask the user if dev+QA cycles exceed 3.
```

### Plan approval gate (mandatory)

Show the full plan inline. End with exactly: **"Approve this plan, or share feedback to revise?"**

Apply feedback as focused edits. Re-show only changed parts. Re-ask until the user explicitly approves ("approved", "looks good", "lgtm", "ship it").

**Do not invoke any subagent or create tasks before the user approves.**

---

## Stage 4 — Create task tracking

After plan approval, call `TaskCreate` for each TASK-NN:
- `title`: "TASK-NN — <short title>"
- `description`: full task spec (goal + navigation + ACs)
- `status`: pending

---

## Stage 5 — Cook loop

For each subtask in order (TASK-01, TASK-02, …):

### 5a — Implement (dmb-android-dev subagent)

Mark task `in_progress` via `TaskUpdate`, then invoke the `dmb-android-dev` subagent:

```
Agent(
  subagent_type = "android-cook:dmb-android-dev",
  description   = "Implement TASK-NN: <short title>",
  prompt        = """
    Task: TASK-NN — <goal>
    Project path: <ANDROID_PROJECT_PATH>
    Package: <package name from Manifest>

    Context — screen involved (navigation path):
    <navigation steps verbatim>

    Acceptance criteria to satisfy:
    <ACs verbatim>

    Implement the required changes. Confirm
    `./gradlew :app:assembleDebug` passes before reporting done.
  """
)
```

Wait for the subagent to complete and return its result. The result must include "assembleDebug PASSED" — if the subagent reports a compile error or blocker, note it and spawn `dmb-android-dev` again with the error context before moving to QA.

### 5b — Test (dmb-android-qa subagent)

Once the build is confirmed passing, invoke the `dmb-android-qa` subagent:

```
Agent(
  subagent_type = "android-cook:dmb-android-qa",
  description   = "Test TASK-NN: <short title>",
  prompt        = """
    Task: TASK-NN — <goal>
    Project path: <ANDROID_PROJECT_PATH>
    Package: <package name from Manifest>
    APK path: <ANDROID_PROJECT_PATH>/app/build/outputs/apk/debug/app-debug.apk

    Navigation to screen (follow exactly):
    <navigation steps verbatim>

    Acceptance criteria (report PASS or FAIL per AC):
    <ACs verbatim>

    Report: PASS (all ACs met) or FAIL (which ACs failed, actual observed
    behavior, expected behavior, screenshot path for each failure).
  """
)
```

### 5c — Fix loop

**If result contains FAIL:**
1. Record the failure note in the lead's context:
   ```
   TASK-NN cycle <N>: ACs [list] failed
   - Actual: <observed>  Expected: <required>  Screenshot: <path>
   ```
2. Increment cycle counter for this task.
3. If cycle counter ≥ 3: call `AskUserQuestion` — present the failure history and ask whether to continue, revise the AC, or skip.
4. Spawn `dmb-android-dev` again (Step 5a) with the failure note appended to the prompt:
   ```
   Previous QA result — fix required:
   <failure note verbatim>
   ```
5. After dev fix confirmed, return to Step 5b.

**If result contains PASS:**
1. Record `TASK-NN: PASSED in <N> cycle(s)`.
2. Mark task `completed` via `TaskUpdate`.
3. Continue to next subtask.

---

## Stage 6 — Final regression sweep

After all subtasks pass, invoke `dmb-android-qa` one more time:

```
Agent(
  subagent_type = "android-cook:dmb-android-qa",
  description   = "Final smoke sweep",
  prompt        = """
    Final smoke: navigate through every screen implemented during this cook
    session using the navigation paths below. For each screen, verify it
    loads, core interactions respond, and no crash or ANR occurs. Also check
    that screens not part of this task are unaffected.

    Screens to cover:
    <list each TASK-NN navigation path>

    Report: CLEAN or ISSUES FOUND (with actual vs expected and screenshot
    path per issue).
  """
)
```

If issues found: spawn `dmb-android-dev` with the findings for a fix, then re-run the smoke once. If the second smoke also fails, call `AskUserQuestion` before a third attempt.

---

## Stage 7 — Report

No shutdown needed — subagents terminate after returning their result.

Print the completion report:

```
## Cook Report

**Task:** <original task description>
**Status:** Complete

### Subtask results

| # | Title | Cycles | Result |
|---|-------|--------|--------|
| TASK-01 | ... | 1 | PASS |
| TASK-02 | ... | 3 | PASS (rework flagged) |

### Rework hotspots
Tasks needing >1 cycle and root cause:
- TASK-02 (3 cycles): Navigation path missed the permission dialog on first
  launch — QA was blocked until the grant step was added to the plan.

### Memory candidates
Non-obvious facts worth saving for faster resolution next time:
1. ...

### Open questions
<Anything deferred as TBD or unresolved.>
```

---

## Hard rules

- **Never invoke a subagent before Stage 3 plan is user-approved.** The gate is mandatory.
- **Never invoke dmb-android-qa before dmb-android-dev's result confirms assembleDebug passed.** Testing a broken build wastes a QA cycle.
- **Never skip the final smoke.** Subtask-level passes miss cross-task regressions.
- **Never silently exceed 3 cycles.** Pause and ask the user — silent rework is a planning gap, not a QA quirk.
- **Navigation steps are law for dmb-android-qa.** If the steps are wrong, revise the plan (with user awareness) and pass corrected steps in the next subagent prompt.
- **One subtask at a time.** Never invoke TASK-NN+1's dev subagent while TASK-NN is still in the fix loop.
- **Lead holds all state.** Each subagent starts cold — pass the full task context in every prompt. Never assume the subagent remembers a prior invocation.

---

## Common mistakes — re-check before each stage

- **Vague ACs.** "Works correctly" fails. Each AC must be binary: visible / not visible, text matches, navigation occurs.
- **Navigation steps using test IDs.** dmb-android-qa reads visible labels from the accessibility tree, not Kotlin identifiers.
- **Omitting the APK path from the dmb-android-qa prompt.** dmb-android-qa needs it to install the app before driving the device.
- **Forgetting to pass the full task context on fix cycles.** The dmb-android-dev subagent starts cold — include the original goal, ACs, and the failure note in the same prompt.
- **Calling Stage 6 before all tasks are `completed`.** The smoke covers the fully integrated feature, not a partial build.
