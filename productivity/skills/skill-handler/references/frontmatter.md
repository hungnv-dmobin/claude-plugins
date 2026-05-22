# Frontmatter Reference

Complete reference for `SKILL.md` YAML frontmatter. Sourced from <https://code.claude.com/docs/en/skills> and <https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview>. When in doubt, the live docs win.

## Universal fields (work on every surface)

These are part of the cross-surface Agent Skills standard — Claude Code, Claude API, claude.ai.

### `name` — display name

- Optional in Claude Code (defaults to directory name); required on the API.
- Lowercase letters, numbers, hyphens only.
- Max 64 chars.
- No XML tags. Cannot include the reserved words `anthropic` or `claude`.

### `description` — what the skill does + when to use it

- Recommended on Claude Code (falls back to first paragraph of body); required on the API.
- Non-empty, max 1,024 chars on the API surface; combined with `when_to_use` capped at 1,536 chars in Claude Code's skill listing.
- No XML tags.
- **This is the routing signal.** It's how Claude decides to auto-invoke. Lead with the action and concrete trigger phrases the user is likely to say. Generic descriptions fail to match.

## Claude Code-specific fields

These are extensions Claude Code adds on top of the open standard.

### `when_to_use` — extra trigger context

Appended to `description` in the listing and counts toward the 1,536-char cap. Use this for:

- Trigger phrases that don't fit naturally in the description sentence.
- Negative guidance ("Do NOT use for X — that's the Y skill").
- Disambiguation between similar skills.

### `argument-hint` — autocomplete hint

Shown as you type `/skill-name `. Format examples:

```yaml
argument-hint: <task-id> (e.g. 1.1, 2.3)
argument-hint: [filename] [format]
```

### `arguments` — named positional args

Maps argument positions to names so the body can use `$name` instead of `$ARGUMENTS[0]`. Accepts a space-separated string or a YAML list:

```yaml
arguments: [issue, branch]
# now $issue == $ARGUMENTS[0], $branch == $ARGUMENTS[1]
```

### `disable-model-invocation` — slash-only

`true` prevents Claude from auto-loading the skill. The user must type `/name` (or invoke explicitly). Also prevents preloading into subagents. Default: `false`.

Use for:

- Side-effecting workflows (`/deploy`, `/commit`, `/send-slack-message`).
- Timing-sensitive operations.
- Bootstrap workflows the model shouldn't trigger reactively (e.g. `/agent-team-creator`).

When `true`, the description is NOT loaded into routing context — it only matters for `/`-menu autocomplete.

### `user-invocable` — hide from `/` menu

`false` removes the skill from the `/` autocomplete menu but Claude can still auto-invoke it. Default: `true`.

Use for **background knowledge skills** — context Claude should pull in automatically but that isn't a meaningful action for users to type. Example: a `legacy-system-context` skill with codebase quirks.

> **Note:** `user-invocable: false` only affects menu visibility. To block programmatic invocation, use `disable-model-invocation: true`.

### `allowed-tools` — pre-approve tools

Tools Claude can call without asking permission while this skill is active. Space-separated string or YAML list. Granular bash patterns supported:

```yaml
allowed-tools: Read Grep Bash(git status *) Bash(git diff *)
```

This **grants** permission. It does NOT restrict — every tool remains callable, governed by your existing permission settings. To block specific tools, use deny rules in `.claude/settings.json`.

For project skills (`.claude/skills/`), `allowed-tools` only takes effect after the user accepts the workspace trust dialog.

### `model` — model override for the turn

Same values as `/model` (e.g. `claude-haiku-4-5`, `claude-sonnet-4-6`, `claude-opus-4-7`), or `inherit` to keep the active model. Override applies only for the current turn — session model resumes next prompt; not saved to settings.

Common pattern: pin high-volume low-reasoning skills (translation, formatting) to Haiku.

### `effort` — effort level override

`low` / `medium` / `high` / `xhigh` / `max`. Available levels depend on the model. Inherits from session by default.

### `context: fork` — run in a forked subagent

When set to `fork`, the skill body runs as the prompt of a new subagent in isolation. The subagent gets its own context, doesn't see your conversation history, and returns a summary.

Required: an actionable task in the body. Pure reference content has nothing for the subagent to do.

### `agent` — subagent type for fork

Used with `context: fork`. Picks the subagent configuration:

- Built-ins: `Explore`, `Plan`, `general-purpose`
- Custom: any subagent name from `.claude/agents/`

Default if omitted: `general-purpose`.

### `hooks` — skill-scoped lifecycle hooks

Run hooks when this skill activates / completes. Same format as global hooks but scoped. See <https://code.claude.com/docs/en/hooks#hooks-in-skills-and-agents>.

### `paths` — auto-activate only on matching files

Glob patterns that limit when the skill is auto-loaded. Same syntax as path-specific CLAUDE.md rules. Comma-separated string or YAML list:

```yaml
paths: ["**/*.kt", "**/build.gradle.kts"]
```

When set, auto-loading is restricted to sessions where matching files are in scope. The user can still invoke manually anywhere via `/name`.

### `shell` — bash or powershell

`bash` (default) or `powershell`. Selects the shell for `` !`command` `` and ` ```! ` blocks. PowerShell requires `CLAUDE_CODE_USE_POWERSHELL_TOOL=1`.

## String substitutions

Substitutions are evaluated **before** the skill content is sent to Claude. Use them in the markdown body.

| Variable                | Expands to                                                                  |
| :---------------------- | :-------------------------------------------------------------------------- |
| `$ARGUMENTS`            | Full argument string as typed by the user                                   |
| `$ARGUMENTS[N]`         | Nth shell-quoted argument, 0-indexed                                        |
| `$N`                    | Shorthand for `$ARGUMENTS[N]` — `$0`, `$1`, …                              |
| `$name`                 | Named arg from `arguments:` frontmatter, in declared order                  |
| `${CLAUDE_SESSION_ID}`  | Current session id                                                          |
| `${CLAUDE_EFFORT}`      | `low` / `medium` / `high` / `xhigh` / `max`                                 |
| `${CLAUDE_SKILL_DIR}`   | Directory containing this SKILL.md (use to invoke bundled scripts)          |

**Quoting note:** indexed args use shell-style splitting. `/foo "hello world" second` makes `$0` = `hello world` and `$1` = `second`. `$ARGUMENTS` always expands to the raw string.

**Bundled-script pattern:** always anchor scripts via `${CLAUDE_SKILL_DIR}` so they resolve regardless of CWD:

```yaml
---
allowed-tools: Bash(python3 *)
---

Run: `python3 ${CLAUDE_SKILL_DIR}/scripts/visualize.py .`
```

## Dynamic context injection

Pre-execute shell commands and inline the output into the skill body before Claude reads it. Inline form:

```markdown
PR diff: !`gh pr diff`
```

Multi-line form:

````markdown
```!
node --version
npm --version
git status --short
```
````

These run **before** Claude sees the skill — they're preprocessing, not tool calls. Output replaces the placeholder. Failures are not retried.

Disable globally via `"disableSkillShellExecution": true` in settings (managed-settings friendly). Bundled and managed skills are exempt from the disable.

## Combinations cheat sheet

| Goal                                                       | Frontmatter combo                                                  |
| :--------------------------------------------------------- | :----------------------------------------------------------------- |
| Default — both you and Claude can invoke                   | none                                                               |
| Slash-only command (`/deploy`, `/commit`)                  | `disable-model-invocation: true`                                   |
| Background knowledge — Claude only                         | `user-invocable: false`                                            |
| Auto-load only on matching file types                      | `paths: [...]`                                                     |
| Run in isolated subagent with code-search tools            | `context: fork` + `agent: Explore`                                 |
| Pin to a cheaper model for high-volume work                | `model: claude-haiku-4-5`                                          |
| Pre-approve git ops without prompting                      | `allowed-tools: Bash(git add *) Bash(git commit *) ...`            |
