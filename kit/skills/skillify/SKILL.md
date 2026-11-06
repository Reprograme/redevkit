---
name: skillify
description: Turn a repeated multi-step workflow into a user skill for Claude Code and Codex; use when asked to make it a skill.
---

# Skillify - Create User Skills from Workflows

> Turn repetitive patterns into reusable skills. If you have done it three times, it should be
> a skill.

The skills you create here belong to the **user**, not to REDEVKIT. They live next to the
REDEVKIT skills but outside the managed tree, so `redevkit` updates never touch them.

## When to Skillify

✅ **Good candidates:**

- The user asked for the same kind of work 3+ times
- The workflow has 5+ consistent steps
- The pattern works across features (or across projects)
- Another agent or teammate could follow it cold

❌ **Bad candidates:**

- One-off tasks (just do them)
- Project facts or decisions (save them to `.redevkit/memory/` with
  `{{SKILL:redevkit-memanager}}` instead)
- Work already covered by an installed skill (check first)

## Protocol

### Step 1: Identify the Pattern

```text
What triggers this workflow? (user says X, file type Y, domain Z)
Which steps are always the same?
Which parts vary between uses?
What is the expected output, and how is it verified?
```

### Step 2: Choose Name and Description

- **Name:** kebab-case, 2-3 words, descriptive, at most 64 characters. Never start with
  `redevkit-` (reserved for managed skills). It must not match any skill that already exists
  in `.claude/skills/` or `.agents/skills/`: a name that matches a REDEVKIT-managed skill would
  be overwritten on the next update.
- **Description:** one sentence, "what it does + when to use it", at most 160 characters, no
  Markdown. Agents choose skills from this line alone, so name the triggers.

| Pattern | Skill name | Example |
| --- | --- | --- |
| Action-based | `[verb]-[noun]` | `release-notes`, `seed-database` |
| Domain-based | `[domain]-[aspect]` | `billing-rules`, `api-versioning` |
| Tool-based | `[tool]-patterns` | `prisma-patterns`, `stripe-webhooks` |

Confirm the name, the description and the targets with the user before writing:

{{ASK}}

### Step 3: Write the Skill for Each Installed Target

Write the same body for every target the project uses (look for `.claude/` and `.agents/` or
`.codex/` at the project root; when unsure, write both).

| Target | Path |
| --- | --- |
| Claude Code | `.claude/skills/<name>/SKILL.md` |
| Codex | `.agents/skills/<name>/SKILL.md` |

Frontmatter per target (one `key: value` per line; quote values that contain a colon followed by a space, or `#`):

```markdown
---
name: <name>
description: <one sentence, what + when, <= 160 chars>
---
```

- **Claude Code** also understands optional fields such as `argument-hint` (shown in the menu),
  `paths` (glob patterns that limit automatic activation) and `disable-model-invocation: true`
  (only the user can invoke it). Add them to the Claude copy only.
- **Codex** reads only `name`, `description` and an optional short label:

```markdown
---
name: <name>
description: <one sentence, what + when, <= 160 chars>
metadata:
  short-description: <label, <= 60 chars>
---
```

Body template:

```markdown
# <Skill Name> - <Short Subtitle>

> <One-line principle>

## When to Use

- Good for: <list>
- Not for: <list>

## Steps

1. <First action>
2. <Next action>
3. <Verification: the command to run and the result that proves success>

## Rules

- <3-5 key rules>
```

Keep `SKILL.md` short. Long material goes to `references/<topic>.md` inside the skill folder,
linked from `SKILL.md` with a relative Markdown link. Keep the body free of
target-specific tool names so both copies stay identical.

### Step 4: Verify

- [ ] `name` equals the folder name in every copy, and does not start with `redevkit-`
- [ ] Description is one sentence of 160 characters or fewer and names the triggers
- [ ] Steps are actionable and end with a verification step
- [ ] Every relative link resolves
- [ ] No secrets, no absolute machine-specific paths
- [ ] The Claude and Codex copies have the same body

Tell the user where the files were written and how to invoke the skill (`/<name>` in Claude
Code, `$<name>` in Codex).

## Quality Checklist

| Check | Criteria |
| --- | --- |
| **Uniqueness** | No installed skill covers this (search `.claude/skills/` and `.agents/skills/`) |
| **Reusability** | Useful across features, not a single task |
| **Completeness** | When to use, steps, verification, rules |
| **Clarity** | A new agent could follow it cold |
