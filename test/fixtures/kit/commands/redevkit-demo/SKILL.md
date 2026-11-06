---
name: redevkit-demo
description: "Demo command: does things."
short-description: Demo
argument-hint: "[--auto] <x>"
version: 9.9.9
allowed-tools: Bash
---
# Demo

**Input:** {{ARGS}}

Follow `{{SKILL:redevkit-step}}`, then {{DELEGATE:helper}}.

{{ASK}}

{{#claude}}
Claude only.
{{/claude}}
{{#codex}}
Codex only.
{{/codex}}
Next: `{{CMD:redevkit-deploy}}` in {{LANG}} v{{VERSION}}.
