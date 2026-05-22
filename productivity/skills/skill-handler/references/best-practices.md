# Skill Authoring Best Practices

Patterns that make skills reliably trigger, run efficiently, and stay maintainable. Sourced from <https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices> and <https://code.claude.com/docs/en/skills>.

## Writing the description

The `description` is the routing signal — Claude reads it at session start to decide when to auto-invoke the skill. Bad descriptions are why skills don't trigger.

**Lead with the action, then the trigger phrases:**

```yaml
# Good
description: >
  Summarize uncommitted changes and flag risky edits. Trigger when the user
  asks "what changed", wants a commit message, or asks to review their diff.

# Bad — generic, no triggers
description: A skill for working with git changes
```

**Include the phrases the user will actually type.** "What changed?" beats "review modifications". Concrete > abstract.

**Be explicit about what's NOT in scope.** Negative guidance prevents the skill from over-triggering and disambiguates from siblings:

```yaml
when_to_use: >
  Use for unit tests of ViewModel, repository, and DataSource code. Do NOT use
  for Compose UI tests — that's the android-ui-test skill.
```

**Keep the most important info first.** Combined `description` + `when_to_use` is capped at 1,536 chars in the skill listing. If you ramble, the trigger phrases get truncated.

### Token optimization — halve before you double

`description` + `when_to_use` are level-1 content: loaded into **every** session for **every** installed skill. A skill whose card is 1,500 chars costs ~6× a skill whose card is 250 chars, every session, for every user who has it installed. Aggregate cost across a 20-skill team is real money.

**Authoring rule:** write the card long first, then cut it in half. If a deletion breaks auto-triggering in a real test, restore *that line* only — don't restore the whole block.

Target ranges (combined `description` + `when_to_use`):

| Card size       | Combined chars | When it earns the budget |
| :-------------- | :------------- | :----------------------- |
| Tight (default) | ≤ 500          | Single clear purpose, distinct trigger phrases |
| Standard        | 500 – 1,000    | Multi-mode skill, several distinct trigger phrasings |
| Wide            | 1,000 – 1,536  | Genuinely multi-domain; needs broad keyword surface |

Default to **tight**. Drift into **standard** only when a real ambiguity surfaces (a sibling skill the auto-trigger keeps mis-matching against). **Wide** is rare — `decision-memory`'s three-mode card is the canonical example in this repo.

**What survives cutting:**

1. Action verb + object on the first line.
2. 3–5 quoted trigger phrases (the ones the user actually says).
3. The single most important "Do NOT" line that prevents over-triggering against the closest sibling.

**What gets cut:**

- Prose framing ("This skill operates in two modes:" → just state the two modes inline).
- Examples that the body already covers — keep one terse list, not two.
- Cross-references beyond the closest sibling skill.
- Restating the action in `when_to_use` when `description` already nailed it. The two fields are concatenated; redundancy doubles the cost.
- Adjectives ("real", "actual", "genuine"). The reader already assumes the skill does real work.

**Measure cards in CI / pre-commit if drift is a recurring problem:**

```bash
# Combined description + when_to_use byte count for a single SKILL.md
awk '/^description:/,/^[a-z_-]+:/' SKILL.md | head -n -1 | wc -c
```

A failing skill auto-trigger after a cut is the *only* signal to restore content. A vague worry about "what if I need it later" is not. Level-2 (body) and level-3 (references/) carry every nuance — push detail there, not into the level-1 card.

**Concrete example:** `qa-web-mcp-test-runner` was halved from ~1,800 combined chars to ~970 by:

- Replacing "Operates in two modes: (a) **inline-plan mode** — the caller (typically a web QA agent inside a cook loop) passes a markdown plan in the prompt; the skill returns results inline and writes NO `qa/bugs/` files; (b) **file-plan mode** — …" with "Two modes: **inline-plan** (cook loop — returns PASS/FAIL, no `qa/bugs/`) and **file-plan** (formal pipeline — reads `qa/test-cases/<FEAT-ID>.md`, files `qa/bugs/BUG-XXXX.md`)."
- Dropping the duplicate "Read-only on dev source" from `description` (kept it in `when_to_use`).
- Trimming the parenthetical example list in `when_to_use` from "real CSS layout, real network, real cookie state, real third-party iframes" to "real CSS, network, cookies, iframes".
- Removing one of two near-identical sentences that both said "do not write a Jest/Vitest/Playwright suite."

Auto-trigger still works — verified by phrasing requests with the surviving keywords.

## Sizing the body

Hard limit guideline: **keep `SKILL.md` under 500 lines.** Past that, skills lose focus and the model picks up irrelevant instructions.

**What stays in `SKILL.md`:**

- The procedural flow (numbered steps).
- Frontmatter and any standing rules ("never X", "always Y").
- Pointers to supporting files with one-line descriptions.

**What moves to `references/`:**

- Full API references, schemas, glossaries.
- Long examples or sample outputs.
- Detailed background ("how the legacy system works").
- Anything Claude only needs *sometimes*.

**What moves to `scripts/`:**

- Deterministic logic (validation, formatting, parsing, file generation).
- Anything that should produce identical output every time.
- Scripts execute via bash — the script's source code never enters context, only the output. This is far more efficient than asking Claude to generate equivalent code.

## When to use `disable-model-invocation: true`

Set it when the skill has **side effects** or **timing matters**:

- Sends a message (`/send-slack`, `/send-email`, `/comment-on-pr`).
- Mutates production (`/deploy`, `/release`, `/migrate`).
- Spawns long-running infrastructure (`/agent-team-creator`, `/spin-up-env`).
- Commits or pushes code (`/commit`, `/publish`).

The principle: don't let the model decide on your behalf for actions you wouldn't want to undo. Giving these slash-only invocation makes the trigger an explicit user act.

**Don't set it for:**

- Reference / knowledge skills (style guides, conventions).
- Read-only workflows (summarize, audit, explain).
- Skills where auto-invocation is the whole point.

## When to use `user-invocable: false`

Niche but useful: skills that are pure background context the user wouldn't type. Examples:

- `legacy-billing-quirks` — a Claude-only memory of how the old billing system encodes timezones.
- `internal-glossary` — domain terms the model should know but isn't a meaningful command.

If you find yourself wanting a skill that's "loaded automatically but never typed", that's the pattern.

## Tool pre-approval (`allowed-tools`)

Be specific. Granting `Bash` whole-cloth is a footgun — anyone reviewing the project skill is implicitly trusting it with your full shell. Prefer narrow patterns:

```yaml
# Good — least privilege
allowed-tools: Read Bash(git status *) Bash(git diff *) Bash(git log *)

# Bad — too broad
allowed-tools: Bash
```

Patterns:

- `Bash(git *)` — any git subcommand
- `Bash(npm test*)` — `npm test` and `npm test:watch` etc.
- `Bash(curl https://api.github.com/*)` — restricted host
- Tools without args: `Read`, `Edit`, `Grep`, `Glob`

For project skills, `allowed-tools` only takes effect after the workspace trust dialog is accepted. Audit project skills before trusting a repo, since a skill can grant itself broad access.

## When to fork (`context: fork`)

Forking gives the skill an isolated context — its own conversation, no carryover from the user's session. Use for:

- **Read-heavy investigation** that would bloat the main context (codebase exploration, log analysis). Use `agent: Explore`.
- **Multi-step planning** that produces a summary, not a stream of files. Use `agent: Plan`.
- **Independent task execution** where mid-task discoveries shouldn't pollute the user's conversation.

**Don't fork for:**

- Reference content (no actionable task → subagent has nothing to do).
- Anything that needs to mutate state the user can see (use inline).
- Quick lookups (overhead of spawning a subagent isn't worth it).

## Skill lifecycle (what happens after invocation)

When invoked, the rendered `SKILL.md` content enters the conversation as a single message and **stays for the session**. Claude does NOT re-read the file on later turns. Implications:

- Write standing instructions, not one-time setup steps. "Always X" works; "On the first turn, do X" can drift.
- Edits to `SKILL.md` won't apply to a skill already loaded in the current session — invoke again to refresh.
- After auto-compaction, the most recent invocation of each skill is re-attached (first 5,000 tokens, shared 25k budget across all skills). Older skills can be dropped — re-invoke critical ones after compaction.

If a skill seems to "stop working" mid-session, the content is usually still present and the model is choosing other tools. Strengthen the description, or use hooks to enforce behavior deterministically.

## Common mistakes

| Mistake                                                          | Fix                                                                |
| :--------------------------------------------------------------- | :----------------------------------------------------------------- |
| Description is abstract ("handles X stuff")                      | Add concrete trigger phrases the user would actually type          |
| Skill is 800 lines of how-tos                                    | Move detail into `references/`, link from SKILL.md                 |
| Tool prompts despite `allowed-tools`                             | Project skills require workspace trust before allow-rules apply    |
| Skill auto-triggers on unrelated requests                        | Tighten description; add "Do NOT use for…" lines                   |
| Skill is in `commands/` and missing supporting files             | Convert to `skills/<name>/SKILL.md` — same `/name`, more features  |
| `${CLAUDE_SKILL_DIR}` not used; relative path to script breaks   | Always anchor scripts via `${CLAUDE_SKILL_DIR}/scripts/foo.py`     |
| Forking a reference-only skill                                   | Don't `context: fork` without an actionable task                   |
| Pinning Opus for high-volume formatting                          | Pin Haiku for high-volume low-reasoning work                       |
| `description` truncated, trigger phrases lost                    | Combined cap is 1,536 chars; trim, or raise `SLASH_COMMAND_TOOL_CHAR_BUDGET` |
| Hardcoding deploy commands inside SKILL.md                       | Bundle as a script; SKILL.md just calls it                         |

## Debugging triggers

If a skill isn't auto-firing:

1. Run `/help` or ask "what skills are available?" to confirm it's registered.
2. Read the description out loud — does it mention the words the user is using?
3. Check if `disable-model-invocation: true` is set (intentional or not).
4. Check `paths:` — if scoped, you may not be in a matching file.
5. Try invoking explicitly with `/skill-name` to confirm the body works.
6. If multiple skills overlap, narrow descriptions or add disambiguating "Do NOT use for…" lines.

If a skill is auto-firing too eagerly:

1. Tighten the description — remove generic verbs ("manage", "handle").
2. Add explicit negative scope ("Do NOT use for X").
3. Consider `disable-model-invocation: true` if it's truly slash-only.
4. Consider `paths:` if it's only relevant to certain file types.

## Naming

- **Verb-noun**: `fix-issue`, `summarize-changes`, `create-android-module`. Avoid pure nouns ("git-helper") — they don't suggest a trigger.
- **Lowercase + hyphens** (required).
- **No `claude` or `anthropic`** in the name (reserved).
- **Match the slash command you'd want to type.** The directory name becomes `/name`.

## Composition with other surfaces

- **Subagents (`.claude/agents/`)** — different from skills. Subagents have system prompts and tool sets; skills are content + frontmatter. They compose via `context: fork` (skill calls a subagent) or via the subagent's `skills:` field (subagent preloads skills).
- **Hooks (`.claude/settings.json`)** — fire on tool events; skills are user/model-invoked. If you need "always run X before tool Y", that's a hook, not a skill.
- **CLAUDE.md** — always-loaded project context. Move long procedural sections out into skills so they only load on demand.
- **`.claude/commands/`** — superseded by skills but still works. Convert when you need supporting files or auto-invocation.
