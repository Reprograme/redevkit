---
name: web-design-guidelines
description: Audit UI code against the Web Interface Guidelines (accessibility, UX, performance); use when reviewing a web UI.
---

# Web Interface Guidelines

Review files for compliance with the Web Interface Guidelines (by Vercel).

## How It Works

1. Fetch the latest guidelines from the source URL below.
2. Read the files to review (from the request, or ask which files or pattern).
3. Check them against every rule in the fetched guidelines and against `DESIGN.md` when it
   exists (the project's design source of truth wins on visual choices).
4. Report findings in the terse `file:line` format the guidelines specify.

## Guidelines Source

Fetch fresh guidelines before each review:

```text
https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md
```

{{#claude}}
Use WebFetch to retrieve it.
{{/claude}}
{{#codex}}
Retrieve it with web search if it is enabled, or with `curl -sL <url>` from the shell when
network access is allowed.
{{/codex}}
The fetched content contains the rules and the output format.

If the fetch fails (offline, sandbox without network), say so in the report and review
against the principles in `{{SKILL:frontend-design}}` instead. Never claim a full guidelines
audit without the fetched rules.

## Related Skills

| Skill | When to use |
| --- | --- |
| `{{SKILL:frontend-design}}` | Before coding: design principles (color, typography, UX psychology) |
| `{{SKILL:design-spec}}` | Writing or updating `DESIGN.md` |
| `web-design-guidelines` (this) | After coding: audit accessibility, performance and best practices |

## Design Workflow

```text
1. DESIGN → DESIGN.md and frontend-design principles
2. CODE   → implement the design
3. AUDIT  → web-design-guidelines review  ← YOU ARE HERE
4. FIX    → address the findings
```
