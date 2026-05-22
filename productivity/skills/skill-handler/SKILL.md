---
name: skill-handler
description: >
  Author, edit, audit, and debug Claude Code skills (`SKILL.md` under
  `.claude/skills/` or `~/.claude/skills/`). Covers the full frontmatter
  reference, string substitutions, dynamic context, invocation control,
  supporting files, and tool pre-approval. Trigger on "write a new skill",
  "edit a SKILL.md", "convert a custom command to a skill", "audit skill
  frontmatter", or "fix a skill that auto-triggers".
when_to_use: >
  Use to create, edit, debug, or audit a Claude Code skill. Do NOT use for
  built-in CLI commands (`/help`, `/compact`), subagents in `.claude/agents/`,
  or `settings.json` — for settings, use `update-config`.
---

# Skill Handler

Operating manual for authoring and maintaining Claude Code skills.

**Source of truth (always defer to these if they conflict with anything below):**

- Claude Code skills (Claude Code-specific frontmatter, `disable-model-invocation`, dynamic context, fork): <https://code.claude.com/docs/en/skills>
- Agent Skills overview (cross-surface model, progressive disclosure, security): <https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview>

For deeper reference (full frontmatter table, all string substitutions, authoring tips), load:

- [references/frontmatter.md](references/frontmatter.md) — every frontmatter field, every substitution variable
- [references/best-practices.md](references/best-practices.md) — description writing, sizing, debugging triggers, common mistakes

## Where skills live

| Location   | Path                                       | Scope                          |
| :--------- | :----------------------------------------- | :----------------------------- |
| Enterprise | managed settings                           | All users in the org           |
| Personal   | `~/.claude/skills/<name>/SKILL.md`         | Every project for the user     |
| Project    | `.claude/skills/<name>/SKILL.md`           | This repo only (commit it)     |
| Plugin     | `<plugin>/skills/<name>/SKILL.md`          | Wherever the plugin is enabled |

Precedence on name conflict: enterprise > personal > project. Plugin skills are namespaced (`plugin:name`) and never conflict.

**Live reload:** edits inside an existing top-level skills dir take effect mid-session. Creating a *new* top-level skills dir requires restarting Claude Code.

## Anatomy

```text
my-skill/
├── SKILL.md            # required — entrypoint
├── references/         # optional — markdown loaded on demand
│   └── deep-dive.md
└── scripts/            # optional — executed via bash, code never enters context
    └── helper.py
```

`SKILL.md` is required. Everything else is optional. Reference supporting files from `SKILL.md` so the model knows when to load them.

## Three loading levels

| Level | When loaded                | Cost                     | What                                     |
| :---- | :------------------------- | :----------------------- | :--------------------------------------- |
| 1     | Always (at session start)  | ~100 tokens / skill      | `name` + `description` + `when_to_use`   |
| 2     | When the skill is invoked  | < 5k tokens typically    | The full SKILL.md body                   |
| 3     | On demand from SKILL.md    | Effectively unlimited    | `references/`, `scripts/`, other files   |

Keep `SKILL.md` under 500 lines. Push detail into `references/`. Bundle deterministic logic into `scripts/`.

## Token budget — level 1 is hot

`description` + `when_to_use` load into **every** Claude Code session, multiplied across **every** skill installed. Treat the level-1 card as a tweet, not a brief: every word competes with every other skill's keywords for the auto-trigger match. A 2000-character card costs ~10× a 200-character one and rarely matches better.

Target ranges (combined `description` + `when_to_use`):

| Card size       | Combined chars | When it earns the budget                                    |
| :-------------- | :------------- | :---------------------------------------------------------- |
| Tight (default) | ≤ 500          | Single clear purpose, distinct trigger phrases              |
| Standard        | 500 – 1,000    | Multi-mode skill, several distinct trigger phrasings        |
| Wide            | 1,000 – 1,536  | Genuinely needs the keyword surface — multi-domain, complex disambiguation |

The hard ceiling is 1,536 chars (the harness truncates past it). Don't drift toward the ceiling by default — **halve before doubling.** Authoring rule: write the card long first, then cut to half; if a deletion breaks auto-triggering in a real test, restore *that line* only.

What to keep when cutting:

1. **Action verb + object** ("Drive a real browser through a frontend test plan").
2. **Distinctive trigger phrases** the user will actually say (3–5 quoted phrases beat 10 generic synonyms).
3. **The most important "Do NOT" line** — exclusions prevent over-triggering against neighbouring skills.

What to cut:

- Prose framing ("This skill operates in two modes:" → just state the two modes).
- Examples that the body covers ("(real CSS, network, cookies, iframes)" survives; "(real CSS layout, real network requests, real cookie state, real third-party iframes)" doesn't).
- Cross-references to other skills beyond the one closest sibling.
- Restating the action in `when_to_use` when `description` already nailed it.

The body of `SKILL.md` and the `references/` files are level-2 and level-3 — they pay no per-session cost. Push every nuance there. Audit existing skills with `wc -c <(awk '/^description:/,/^[a-z_-]+:/' SKILL.md)` when you suspect drift. See [references/best-practices.md](references/best-practices.md) §"Description writing" for the deeper rule set.

## Frontmatter — the short list

The fields you'll touch most. Full table in [references/frontmatter.md](references/frontmatter.md).

```yaml
---
name: my-skill                     # lowercase + numbers + hyphens, max 64 chars
description: >                     # combined with when_to_use, capped at 1,536 chars
  What this skill does and the trigger phrases the user is likely to say.
when_to_use: >                     # extra trigger context, appended to description
  Use when X. Do NOT use for Y.
argument-hint: <task-id>           # autocomplete hint
disable-model-invocation: true     # SLASH-ONLY: Claude can't auto-trigger; user types /name
user-invocable: false              # CLAUDE-ONLY: hide from / menu, background knowledge
allowed-tools: Read Edit Bash(git status *)   # pre-approved while skill is active
model: inherit                     # or claude-haiku-4-5, claude-sonnet-4-6, etc.
context: fork                      # run in a forked subagent
agent: Explore                     # which subagent type to fork (with context: fork)
paths: ["**/*.kt", "**/*.gradle.kts"]   # auto-activate only on matching files
---
```

**Required:** `name` (or inferred from dir) and a non-empty `description` (recommended; falls back to first paragraph).

## Decision flow — picking frontmatter

### 1. Who should invoke this skill?

| Goal                                     | Set                                           |
| :--------------------------------------- | :-------------------------------------------- |
| Both user and Claude (default)           | nothing                                       |
| Only the user, via `/name` (no auto)     | `disable-model-invocation: true`              |
| Only Claude (background knowledge)       | `user-invocable: false`                       |

Use `disable-model-invocation: true` for skills with **side effects or timing-sensitive workflows** (`/deploy`, `/commit`, `/send-slack-message`, team bootstrap). Don't let the model decide to deploy because the code "looks ready."

### 2. Where should this skill run?

| Goal                                     | Set                              |
| :--------------------------------------- | :------------------------------- |
| Inline in the current conversation       | nothing                          |
| In a forked subagent (isolated context)  | `context: fork` + `agent: <type>` |

Forked context only makes sense for skills with an **actionable task** in the body. Pure reference content (style guides, conventions) loses its purpose in a fork — there's nothing for the subagent to do.

### 3. What tools does the skill need?

If the skill calls a tool that would normally prompt for permission (e.g. `Bash(git push *)`, `WebFetch`, network tools), pre-approve them with `allowed-tools`. This grants permission *while the skill is active* — it does NOT restrict to only those tools. Use deny rules in permission settings to actually block.

### 4. Should auto-activation be scoped by file path?

Use `paths` (glob patterns) when a skill should only auto-load while the user is working on matching files — e.g. an Android-specific skill only fires when `*.kt` or `build.gradle.kts` is in scope. The user can still invoke it manually anywhere.

## Workflows

### Create a new skill

1. **Pick the location** (project = `.claude/skills/` if shared with the team; personal = `~/.claude/skills/`).
2. **Pick the name** — lowercase + hyphens, descriptive verb-noun (`fix-issue`, `summarize-changes`).
3. **Write the description first.** This is what Claude matches on. Lead with the action, then trigger phrases the user would naturally say. Combined `description` + `when_to_use` is capped at 1,536 chars in the listing — put the key use case first.
4. **Decide invocation mode** using the decision flow above.
5. **Write the body** — clear, imperative, step-by-step. Reference supporting files when content gets long.
6. **Test both ways:** invoke directly with `/name` AND let it auto-trigger by phrasing a request that matches `description`.

If you keep pasting the same instructions into chat, or a section of CLAUDE.md has grown into a procedure, that's the signal to extract a skill.

### Edit an existing skill

Before editing, read the current `SKILL.md` and identify which class of change you're making:

| Change                                         | Where                                   |
| :--------------------------------------------- | :-------------------------------------- |
| Trigger phrasing — fix over/under-triggering   | `description` and `when_to_use`         |
| Lock to slash-only / unlock                    | `disable-model-invocation`              |
| Add/remove pre-approved tool                   | `allowed-tools`                         |
| Add a step / change procedure                  | Markdown body                           |
| Add deep reference / examples                  | New file in `references/`, link from body |
| Bundle deterministic logic                     | Script in `scripts/`, call via `${CLAUDE_SKILL_DIR}` |

### Convert a custom command (`.claude/commands/foo.md`) to a skill

Custom commands and skills are now unified. A file at `.claude/commands/deploy.md` and a skill at `.claude/skills/deploy/SKILL.md` both create `/deploy`. Move when you need supporting files, frontmatter beyond the basics, or auto-invocation. The conversion:

1. `mkdir .claude/skills/deploy/` and move/rename the command file to `.claude/skills/deploy/SKILL.md`.
2. Add or update frontmatter — at minimum `description`. Add `disable-model-invocation: true` if it should stay slash-only.
3. Test `/deploy` still works; if the original command had `$ARGUMENTS`, it carries over unchanged.

### Audit / debug a skill

| Symptom                                | Check                                                                 |
| :------------------------------------- | :-------------------------------------------------------------------- |
| Doesn't auto-trigger when expected     | `description` keywords match user phrasing? Listed in skills index?   |
| Auto-triggers too aggressively         | Tighten `description`, add "Do NOT use for…" lines, or set `disable-model-invocation` |
| Description appears truncated          | Combined cap is 1,536 chars; trim, or raise `SLASH_COMMAND_TOOL_CHAR_BUDGET` |
| Tool prompts despite `allowed-tools`   | Project skills require workspace trust before allow-rules apply       |
| Skill body stops influencing output    | Content is still in context; model is choosing other tools — strengthen description, or use hooks |
| `/name` works but auto-trigger doesn't | Likely `disable-model-invocation: true` is set                        |

## Dynamic context (advanced)

Use `` !\`command\` `` (inline) or a fenced block whose opening fence is three backticks immediately followed by `!` to pre-execute shell commands; the output replaces the placeholder before Claude reads the skill. This is preprocessing, not a tool call. **Important:** the preprocessor scans the whole SKILL.md including fenced examples and inline-code spans — escape the backticks of inline forms as `` !\`...\` `` (shown throughout this section), and never write the literal triple-backtick-plus-`!` opener anywhere in docs, even inside an inline code span, or this skill itself will fail to load with `(eval):1: unmatched`` `.

```
---
name: pr-summary
description: Summarize an open PR
allowed-tools: Bash(gh *)
---

PR diff: !\`gh pr diff\`
PR comments: !\`gh pr view --comments\`

Summarize the PR above…
```

Disable globally with `"disableSkillShellExecution": true` in settings — useful in managed/enterprise contexts.

## String substitutions (cheat sheet)

| Variable               | Expands to                                                |
| :--------------------- | :-------------------------------------------------------- |
| `$ARGUMENTS`           | Full argument string as typed                             |
| `$ARGUMENTS[N]` / `$N` | Nth shell-quoted argument (0-based)                       |
| `$name`                | Named argument from `arguments:` frontmatter              |
| `${CLAUDE_SKILL_DIR}`  | Directory containing this `SKILL.md` (use to find scripts) |
| `${CLAUDE_SESSION_ID}` | Current session id                                        |
| `${CLAUDE_EFFORT}`     | `low` / `medium` / `high` / `xhigh` / `max`               |

Always reference bundled scripts via `${CLAUDE_SKILL_DIR}/scripts/foo.py`, never relative paths — `cwd` is the user's project, not the skill directory.

## Repo conventions (this project)

CLAUDE.md pins these for skills under `.claude/skills/` here. Honor them when authoring inside this repo:

- **Frontmatter keys observed**: `name`, `description`, `when_to_use`, optional `argument-hint`. Add new top-level keys (like `disable-model-invocation`, `paths`) only when they earn it — match the existing shape first.
- **Layout patterns to copy**:
  - Flat (`SKILL.md` only) — `agent-team-creator`, `spec-writing`
  - With `references/` — `android-clean-architecture`, `android-ui-test`, `android-unit-test`
  - With `scripts/` — `create-android-module`
- **Model pinning**: only `localization-agent` is pinned (to `claude-haiku-4-5`) per `complete-flow.md` §1.4.1. If you pin a model on a new skill, document it both in the skill's frontmatter AND in the agent's row in `complete-flow.md` §3.
- **Skill priority**: `complete-flow.md` §4 lists 11 skills with sequencing rationale. When adding a new pipeline skill from scratch, build `phase-breakdown` first.

## Security checklist (when accepting a skill from elsewhere)

Skills can run code and call tools. Treat third-party skills like installing software:

- Read every file: `SKILL.md`, `references/`, `scripts/`, images.
- Look for unexpected network calls, broad `allowed-tools` (e.g. `Bash` unrestricted), or operations unrelated to the stated purpose.
- Skills that fetch external URLs are a particular risk — fetched content can carry instructions.
- Be especially careful in production / sensitive-data contexts.
