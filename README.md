# dmb-plugins

Personal [Claude Code](https://claude.com/claude-code) plugin marketplace. Two plugins:

| Plugin | Contents |
|--------|----------|
| **android-cook** | 6 skills + 2 agents + `mobile-mcp` server — end-to-end Android task orchestration with on-device QA |
| **productivity** | 4 skills — brainstorming and skill-authoring helpers |

## Install on any machine

```bash
# 1. Add this marketplace (once per machine)
claude plugin marketplace add hungnv-dmobin/claude-plugins

# 2. Install the plugins you want
claude plugin install android-cook@dmb-plugins
claude plugin install productivity@dmb-plugins
```

Installed plugins are **user-scoped** — available in every project/session on that machine.
Run `claude plugin list` to verify, and `/plugin` inside a session to manage them.

To pick up updates later: `claude plugin marketplace update dmb-plugins`.

## android-cook

End-to-end Android task orchestrator. The `dmb-android-cook` skill clarifies
requirements via targeted Q&A, breaks work into testable subtasks, then drives a
sequential dev→build→test→fix loop using the `dmb-android-dev` and
`dmb-android-qa` subagents until every subtask passes on a real device.

Trigger it with: **"cook this task: &lt;Android task&gt;"**

**Skills:** `dmb-android-cook`, `qa-android-mcp-test-runner`, `qa-bug-tracker`,
`android-clean-architecture`, `create-android-module`, `android-platform-components`
**Agents:** `dmb-android-dev`, `dmb-android-qa`
**MCP:** `mobile-mcp` (auto-registered when the plugin is enabled)

### Prerequisites for the QA part

The on-device QA stage needs, on each machine:

- **Node.js** — `mobile-mcp` runs via `npx`
- **Android SDK + `adb`** on `PATH`
- A running **emulator or connected device**

Without these, the dev/planning side still works; only the device QA stage is blocked.

## productivity

- `grill-me` — interviews you relentlessly to stress-test a plan or design
- `grill-with-docs` — same, but challenges the plan against your project's docs/ADRs
- `skill-handler` — author, edit, audit, and debug Claude Code skills
- `handoff` — compact the current conversation into a handoff document

## Notes

- The `android-cook` plugin namespaces its agents as `android-cook:dmb-android-dev`
  and `android-cook:dmb-android-qa`; the `dmb-android-cook` skill already invokes
  them by their namespaced names.
- The `dmb-android-dev` agent optionally references a `compose-expert` skill that
  is **not** bundled here — Jetpack Compose guidance will simply be unavailable
  unless you add that skill separately.
