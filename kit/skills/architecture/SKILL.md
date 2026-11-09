---
name: architecture
description: Architecture decisions - requirements, trade-offs, patterns, ADRs. Use when designing a system or comparing approaches.
---

# Architecture Decision Framework

> "Requirements drive architecture. Trade-offs inform decisions. ADRs capture rationale."

## Selective Reading Rule

Read ONLY the references relevant to the request. Check the content map and open what you need.

| Reference | Description | When to read |
| --- | --- | --- |
| [context-discovery](references/context-discovery.md) | Questions to ask, project classification | Starting an architecture design |
| [trade-off-analysis](references/trade-off-analysis.md) | ADR templates, trade-off framework | Documenting decisions |
| [pattern-selection](references/pattern-selection.md) | Decision trees, anti-patterns | Choosing patterns |
| [examples](references/examples.md) | MVP, SaaS, enterprise examples | Reference designs |
| [patterns-reference](references/patterns-reference.md) | Quick lookup for patterns | Pattern comparison |

## Related Skills

| Skill | Use for |
| --- | --- |
| `{{SKILL:database-design}}` | Database schema design |
| `{{SKILL:api-patterns}}` | API design patterns |
| `{{SKILL:deployment-procedures}}` | Deployment architecture |

## Core Principle

**"Simplicity is the ultimate sophistication."**

- Start simple
- Add complexity ONLY when proven necessary
- You can always add patterns later
- Removing complexity is MUCH harder than adding it

## Where Decisions Live

- Feature-level decisions: `specs/NNN-short-name/research.md`, summarized in `plan.md`.
- Constraints from the project constitution (`.redevkit/memory/constitution.md`) win; a
  violation is justified under "Complexity Tracking" and still needs the user's acceptance;
  otherwise the plan stops at gate G3.
- Stable stack facts: `.redevkit/memory/tech.md`; system structure: `.redevkit/memory/system.md`.

## Validation Checklist

Before finalizing the architecture:

- [ ] Requirements clearly understood
- [ ] Constraints identified
- [ ] Each decision has a trade-off analysis
- [ ] Simpler alternatives considered
- [ ] ADRs written for significant decisions
- [ ] Team expertise matches the chosen patterns
