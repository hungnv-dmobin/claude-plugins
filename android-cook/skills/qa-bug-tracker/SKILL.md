---
name: qa-bug-tracker
description: File and track one Android bug per qa/bugs/<BUG-ID>.md with fixed frontmatter, severity ladder (blocker|major|minor), state machine open/in-fix/in-verify/closed, and the zero-blocker-major merge gate. Use for QA-found defects and status updates; not for TODOs or feature requests. Triggers: "file a bug", "log a defect".
---

## When to use

File and track an Android-app bug as `qa/bugs/<BUG-ID>.md` with fixed frontmatter (status, severity, category, assignee, phase_found, phase_fixed?, spec_ref, ac_ref). Encodes the severity ladder (`blocker|major|minor`), the state machine (`open → in-fix → in-verify → closed`), and the merge gate (zero blocker + zero major to tag a phase). Trigger on "file a bug", "open a bug", "log a defect", "track this failure", or when `qa-test-runner` parses a Gradle failure.

When to use: Use for any AC miss, crash, or behavior deviation found by QA (Layer-3 `*JourneyTest.kt` or manual). Also use to update an existing bug's status. One bug per file — never group. Do NOT close as wontfix/duplicate (not in the state machine) — close as `closed` with the reason in the body. Do NOT use for ad-hoc TODOs, refactor backlogs, or feature requests.

# QA Bug Tracker

Standing instructions for filing and updating a single bug record under `qa/bugs/<BUG-ID>.md`. Invoked by `qa-agent-android` when authoring a new bug, and referenced by `qa-test-runner` when it parses Gradle failures into bug files. The schema is the same in both cases — there is only one bug-file format in this project.

The bug file is the only signal the dev team and the integration-lead read for "what's blocking the phase". Get the frontmatter right; it drives the merge gate.

## Three rules that override anything else

1. **One bug per file. No rollups.** Path is `qa/bugs/<BUG-ID>.md`. Never combine multiple defects into a single file, even when they share a feature. The feature linkage is the `spec_ref` field, not the filename.
2. **Bug IDs are monotonic and globally unique across the whole project.** Format: `BUG-XXXX` — uppercase `BUG`, single hyphen, four-digit zero-padded number (e.g. `BUG-0042`). Allocate the next unused integer; never re-use a retired ID; never renumber. The ID is permanent across the project's lifetime.
3. **Frontmatter is the contract.** The fields below are what the merge gate, the routing rule, and the regression-tracker all read. Add nothing outside the listed keys. If a field doesn't apply yet (e.g. `phase_fixed` while the bug is open), keep the key and set it to `null` — do not omit it.

## Output schema — `qa/bugs/<BUG-ID>.md`

```yaml
---
status: open                 # open | in-fix | in-verify | closed
severity: major              # blocker | major | minor
category: technical          # technical | flow | both
assignee: <agent-name>       # who owns the fix (architect | ba-agent | ui-dev | data-dev | platform-dev)
phase_found: 2               # phase number when QA filed it
phase_fixed: null            # null until status=closed
spec_ref: FEAT-005           # the FEAT-ID this bug touches
ac_ref: AC-MSG-007           # specific acceptance criterion that failed
---
```

Body sections, in this order. Keep it tight — the executable journey test (`*JourneyTest.kt`) carries the canonical reproduction; this file is the index, not the long-form report.

1. **Title** — one-line `# ` heading naming the failure. Specific, not generic ("Send button stays disabled after typing message" — not "send broken").
2. **Steps to Reproduce** — numbered list. Cite the journey test path (`app/src/androidTest/.../<FeatureName>JourneyTest.kt`) and the `@Test` method name when one exists. Don't restate the test body; reference it.
3. **Expected Result** — what the spec / acceptance criterion says should happen. Quote the relevant `AC-<scope>-NNN` line from the spec.
4. **Actual Result** — what happened. Include the Gradle/test failure snippet or stack trace fragment if useful; trim to the load-bearing lines.
5. **Root Cause Hypothesis** — QA's best guess (one short paragraph). Optional but encouraged so the assignee starts with context.
6. **Suggested Fix** — optional. Skip if QA has no view; do not invent one.

The body is allowed to be terse. Do not pad.

## Frontmatter field rules

### `status` — the state machine (strict)

```
filed by QA
   │
   ▼
[open] ──assignee picks it up──▶ [in-fix] ──assignee marks fix-ready──▶ [in-verify]
                                                                          │
                                                                  ┌───────┴───────┐
                                                          QA re-runs       QA re-runs
                                                          and passes       and fails
                                                                  │               │
                                                                  ▼               ▼
                                                              [closed]        [open]
```

- `open` — filed by `qa-agent-android`. Awaiting an assignee to pick it up.
- `in-fix` — assignee has started work. The assignee field is now binding.
- `in-verify` — assignee has pushed a fix and asked QA to re-run the journey test. QA owns the next transition.
- `closed` — QA re-ran the journey test (and any related smoke) and it passes.

Hard rules:

- No skipping states. `open → in-verify` is invalid. `open → closed` is invalid. Always pass through `in-fix`.
- `in-verify → open` is the only backward transition (re-verify failed; bug stays open under the same `BUG-ID`).
- No `wontfix`, `duplicate`, `deferred` states. If a bug is genuinely not going to be fixed, close it as `closed` with a one-paragraph explanation in the body. If it's a duplicate, close it as `closed` referencing the surviving `BUG-ID` in the body and leave that survivor open.
- Once `closed`, the bug stays closed. A regression of the same behavior is a **new** `BUG-ID` (cite the prior one in the body).

### `severity` — the ladder

The ladder determines whether a bug blocks the phase merge.

| Severity | Definition | Merge impact |
|---|---|---|
| `blocker` | Feature unusable, app crash, data loss, main user flow broken. | Phase cannot tag complete with any open. |
| `major` | Feature partially broken — alt flow fails, error message missing/wrong, AC miss not on the main flow. | Phase cannot tag complete with any open. |
| `minor` | Cosmetic, edge case, low-impact. | Can be deferred to the next phase with explicit user OK at the optional gate; otherwise carries into the next phase's bug list. |

QA proposes severity at filing time. Disagreements are resolved by the routing rule below.

### `category` — `technical | flow | both`

Drives the severity-routing rule. Pick exactly one:

- `technical` — crashes, performance regressions, build/test infra failures, architecture violations, threading bugs, leaked resources. The fix is in code, not in the spec.
- `flow` — acceptance-criterion misses, userflow deviations, spec ambiguity, wrong copy, wrong navigation order. The fix may need a spec edit (and therefore a BA decision) before code can move.
- `both` — touches code **and** an unclear spec/userflow rule. Reserve this for genuine joint cases; do not default here.

### `assignee` — who owns the fix

Use the agent's canonical name without hat suffixes. Allowed values during a phase: `software-architect-android`, `ui-dev-android`, `data-dev-android`, `platform-dev-android`, `ba-agent` (when the fix is a spec edit, not code). When QA proposes the assignee but is not sure, leave it as the routing-decided owner from the rule below — the integration-lead may reassign on intake.

### `phase_found` and `phase_fixed`

- `phase_found` — integer, the phase the bug was filed in. Set on creation, never changed.
- `phase_fixed` — `null` while the bug is anything other than `closed`. Set to the integer phase when transitioning to `closed`. If a fix lands in a later phase than the one it was found in, that's a `phase_found` < `phase_fixed` record — keep both honest, do not back-date.

### `spec_ref` and `ac_ref`

- `spec_ref` — a single `FEAT-NNN` ID. The bug must trace to a feature; if QA cannot identify one, the bug is probably out-of-scope (file as a feedback-loop note instead of a bug).
- `ac_ref` — a single `AC-<scope>-NNN` ID. The acceptance criterion that failed. If the failure is broader than one AC (e.g. a crash with no specific AC), pick the AC closest to the failing flow and explain in the body — do not leave the field empty.

## Severity-disagreement routing

QA proposes severity at filing time. The dev team or the integration-lead may disagree (e.g. "this looks `major` to me, not `blocker`"). When that happens, route by the bug's `category`:

| `category` | Decider | Notes |
|---|---|---|
| `technical` | The architect (`software-architect-android`). | Crashes, perf, build/test infra, architecture violations — the architect knows the cost surface. |
| `flow` | `ba-agent`. | AC misses, userflow deviations, spec ambiguity — the BA owns the acceptance bar. |
| `both` | Joint between the architect and `ba-agent`, with the integration-lead breaking ties. | The integration-lead is the same agent in its `(integration-lead)` hat; this guarantees the merge gate has a single owner when the two disagree. |

The routing rule is the same routing rule the team-bootstrap encodes; document it here so QA, dev, and the integration-lead read identical wording.

After the deciding agent updates the severity, QA edits the file in place — do not allocate a new `BUG-ID` and do not write a separate "severity-changed" note. Git history records the change.

## Merge-blocking semantics

The integration-lead enforces the phase merge gate. The rule is one line:

> A phase tags complete only when **zero `blocker`** AND **zero `major`** bugs are open against any FEAT-ID in the phase's `included_feat_ids[]`.

"Open" means `status` is anything other than `closed` — i.e. `open`, `in-fix`, and `in-verify` all count as open. A bug in `in-verify` does not unblock the merge until QA has flipped it to `closed`.

`minor` bugs do not block. They can be deferred to the next phase with explicit user OK at the optional gate; otherwise they carry into the next phase's bug list (the integration-lead surfaces them in the phase summary).

The locale report from the project's translation step has the same merge-blocking semantics as a `major` bug: zero missing/stale keys for the phase's FEAT-IDs before the integration-lead tags the phase complete. That contract lives with the translation skill — cross-reference it from this file's bug records when a translation issue is filed as a bug, but do not restate the locale skill's rules here.

## Interop — `i18n-translator` overflow auto-stubs

`i18n-translator` automatically writes `qa/bugs/<BUG-ID>.md` when its length-overflow heuristic fires (translated string >130% source character count). These auto-stubs use this skill's exact schema: `status: open`, `severity: minor`, `category: technical`, `assignee: ui-dev-android`. The `bug_id` for each is recorded in `qa/locale-report-phase-NN.md`'s layout-warnings table.

**QA action rules:**
- Do NOT re-file an overflow bug that `i18n-translator` already stubbed. Before filing a new bug for a layout-overflow symptom, check the locale report's layout-warnings table for an existing BUG-ID.
- The auto-stubbed bug body notes "Auto-stubbed by `i18n-translator`" and flags that the overflow is heuristic — `ui-dev-android` must confirm visually before fixing.
- Severity may be escalated from `minor` if `ui-dev-android` confirms the overflow clips a CTA or a primary content string (route as `technical` per the routing rule).
- The integration-lead surfaces auto-stubbed overflow BUG-IDs to `ui-dev-android` after each localization pass; they do not block the phase merge gate (they are `minor`) but should be triaged before Gate C.

## Workflow — filing a new bug

1. **Confirm the bug is in scope.** A bug is a deviation from a spec/AC, a crash, or a regression. Feature requests, refactor TODOs, and "I think this could be nicer" notes are not bugs — route them to the project's update workflow.
2. **Allocate the next `BUG-ID`.** Read `qa/bugs/` and find the highest numeric suffix; the new ID is `BUG-` plus `prior + 1`, zero-padded to four digits. Two QA passes filing in parallel must coordinate (the integration-lead arbitrates) — never reuse an ID.
3. **Pick severity.** Use the ladder. Default to the lower severity when borderline; the routing rule will escalate if needed.
4. **Pick category.** Use `technical` / `flow` / `both` as defined. Reserve `both` for genuinely joint cases.
5. **Identify `spec_ref` and `ac_ref`.** From the failing journey test, follow back to the spec. The journey test carries a two-line comment block above each `@Test` (`// TC-…` then `// AC-…`); read the AC-ID from there. If the comment block is missing, that's a separate bug against the test suite — do not bury it.
6. **Set `phase_found`** to the current phase. Set `phase_fixed: null`.
7. **Pick an `assignee`.** Use the routing rule as a default if uncertain.
8. **Write the body** in the section order above. Keep it tight; the journey test is the canonical reproduction.
9. **Save** as `qa/bugs/<BUG-ID>.md`. Do not modify any other file.

## Workflow — updating an existing bug

1. **Read the file first.** Validate the existing frontmatter against the schema. If it doesn't match, surface the drift to the integration-lead before editing.
2. **Apply exactly one state transition** per update. Allowed transitions: `open → in-fix`, `in-fix → in-verify`, `in-verify → closed`, `in-verify → open`. Anything else is a bug in the workflow itself.
3. **On `closed`,** set `phase_fixed` to the current phase. Append a one-line note in the body under a `## Resolution` heading citing the fix commit/PR (or "spec edit" if the resolution was a spec change).
4. **On `in-verify → open`,** append a one-line note under `## Re-verify failure` with what regressed. Severity and category may be re-proposed (route per the rule); do not silently downgrade.
5. **Do not add new top-level frontmatter keys** to "track" anything extra. Use the body.

## Validation checklist (run before saving)

- File path is `qa/bugs/<BUG-ID>.md` with `BUG-XXXX` four-digit format.
- Every frontmatter key from the schema is present (use `null` for `phase_fixed` while open).
- `status` is one of the four values; transition (if updating) follows the state machine.
- `severity` is one of the three values.
- `category` is one of the three values.
- `spec_ref` matches an existing `FEAT-NNN` from the userflow registry.
- `ac_ref` matches an existing `AC-<scope>-NNN` from that feature's spec.
- Body has Title, Steps to Reproduce, Expected, Actual at minimum.

If any check fails, fix it in place — do not save a partial record.

## Common mistakes — re-check before saving

- **Per-feature rollups.** One file per bug, always. A file named `qa/bugs/FEAT-005.md` is wrong; it should be `qa/bugs/BUG-0042.md`.
- **Reusing a `BUG-ID`.** A regression of an old behavior is a new bug. The retired ID stays retired.
- **Skipping `in-fix`.** Even a one-line patch transitions through `in-fix`; the state machine does not allow `open → in-verify`.
- **`wontfix` or `duplicate` as a status.** Not in the state machine. Close as `closed` with the reason in the body.
- **Defaulting to `category: both`.** Only use when the bug genuinely needs joint architect+BA judgement. Most bugs are `technical` or `flow`.
- **Silently downgrading severity** to clear the merge gate. The routing rule exists so the dev team and the BA can disagree on the record — use it.
- **Forgetting to set `phase_fixed` on close.** The integration-lead's regression tracker reads this field.

## Reporting back

After filing or updating a bug, return one short message:

1. The path written: `qa/bugs/<BUG-ID>.md`.
2. The transition (e.g. "filed at `open`", "moved to `in-verify`", "closed in phase 3").
3. Anything that needs the integration-lead's attention: a severity disagreement to route, a `blocker` opened against the current phase, or a `minor` flagged for the next phase's carry-over list.

Do not summarize the body in chat — the file is the artifact.
