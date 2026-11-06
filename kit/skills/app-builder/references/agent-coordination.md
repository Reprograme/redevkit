# Persona Coordination

> How a new app moves through the REDEVKIT pipeline and which persona owns each step.
> Delegation, parallelism and synthesis follow `{{SKILL:redevkit-orchestrate}}`.

## Pipeline

```text
┌─────────────────────────────────────────────────────────────┐
│              QUESTIONS (shared question protocol)            │
│  • Only what changes scope, stack or architecture            │
│  • One at a time, recommended option first                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  PROJECT PLANNER (redevkit-plan)             │
│  • spec.md, plan.md, tasks.md in specs/NNN-short-name/       │
│  • Stack + template chosen with app-builder                  │
│  • Dependency order, persona per task                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              CHECKPOINT: PLAN APPROVAL (gate G2)             │
│  • tasks.md exists and the user approved the plan?           │
│  • If NO → STOP, finish the plan first                       │
│  • If YES → proceed to the specialist personas               │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ DATABASE        │ │ BACKEND         │ │ DESIGN SOURCE   │
│ ARCHITECT       │ │ SPECIALIST      │ │ OF TRUTH        │
│                 │ │                 │ │                 │
│ • Schema design │ │ • API routes    │ │ • design-spec + │
│ • Migrations    │ │ • Controllers   │ │   collection    │
│ • Seed data     │ │ • Middleware    │ │ • DESIGN.md at  │
│                 │ │                 │ │   project root  │
└─────────────────┘ └─────────────────┘ └─────────────────┘
          │                   │                   │
          │                   │                   ▼
          │                   │         ┌─────────────────┐
          │                   │         │ FRONTEND        │
          │                   │         │ SPECIALIST      │
          │                   │         │                 │
          │                   │         │ • UI components │
          │                   │         │ • Pages         │
          │                   │         │ • Strict tokens │
          │                   │         └─────────────────┘
          │                   │                   │
          └───────────────────┼───────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│           QUALITY (redevkit-test / redevkit-verify)          │
│  • Test Engineer → test suite, acceptance scenarios          │
│  • Security Auditor → vulnerability check                    │
│  • Performance Optimizer → bundle analysis                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     DEVOPS ENGINEER                          │
│  • Environment setup                                         │
│  • Local preview via redevkit-preview                        │
│  • Deploy only when the user runs redevkit-deploy            │
└─────────────────────────────────────────────────────────────┘
```

## Execution Order

| Phase | Persona(s) / step | Parallel? | Prerequisite | Checkpoint |
| --- | --- | --- | --- | --- |
| 0 | Questions | No | - | Assumptions recorded |
| 1 | `project-planner` | No | Questions answered | `spec.md`, `plan.md`, `tasks.md` written |
| 1.5 | **Plan approval (G2)** | No | `tasks.md` exists | User approved the plan |
| 1.8 | **Design source of truth** | No | Plan approved (UI projects) | `DESIGN.md` at the project root |
| 2 | `database-architect` | No | Plan ready | Schema defined |
| 3 | `backend-specialist` | No | Schema ready | API routes created |
| 4 | `frontend-specialist` | Yes, `[P]` tasks only | `DESIGN.md` + API ready (partial) | UI components match tokens |
| 5 | `test-engineer`, `security-auditor` | Yes, read-only reviews | Code ready | Tests and audit pass, with evidence |
| 6 | `devops-engineer` | No | All code ready | Preview ready |

> **CRITICAL:** Phase 1.5 and Phase 1.8 are mandatory gates.
>
> - Phase 1.5: no specialist persona starts before the plan is approved (G2).
> - Phase 1.8: for any project with a UI (web, mobile, desktop), **`DESIGN.md` MUST exist at
>   the project root** before UI components or pages are written (see `{{SKILL:design-spec}}`).
>   Skip only for headless APIs or CLI tools.

## Parallelism

Tasks run in parallel only when they are marked `[P]` in `tasks.md` and touch disjoint files.
Each parallel task goes to its persona as a native subagent; the coordinator synthesizes the
results. Do not claim parallel work that did not happen.

Delegate a frontend task, for example: {{DELEGATE:frontend-specialist}}.
