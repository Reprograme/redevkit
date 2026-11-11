# Persona Coordination

> How a new app moves through the REDEVKIT pipeline and which persona owns each step.
> Delegation, parallelism and synthesis follow `{{SKILL:redevkit-orchestrate}}`.

## Order of Work

The order is owned by the commands; do not keep a separate table here.

1. **Planning:** follow the steps of `{{CMD:redevkit-plan}}` in order (`{{SKILL:redevkit-plan}}`):
   specify, domain routing, plan (stack and template chosen with app-builder), the
   **DESIGN.md gate** for any project with a UI (before tasks and before G2), tasks, analyze,
   optional domain checklist, then **plan approval (G2)**. Nothing is implemented before G2.
2. **Implementation:** `{{CMD:redevkit-create}}` executes `tasks.md` in the phases defined by
   `{{SKILL:redevkit-tasks}}`: Setup, Foundational (schema, auth, shared infrastructure), then
   one phase per user story in which the **failing tests come first**, then Polish. Each task
   names its persona (`database-architect`, `backend-specialist`, `frontend-specialist`,
   `test-engineer`, ...).
3. **Quality:** `{{CMD:redevkit-test}}` runs the full suite; `{{CMD:redevkit-verify}}` runs
   it (or reuses a run on the same code), then the audits (test engineer, security auditor,
   performance optimizer).
4. **Operations:** local preview via `{{CMD:redevkit-preview}}`; deploy only when the user runs
   `{{CMD:redevkit-deploy}}` (G6).

For any project with a UI (web, mobile, desktop), `DESIGN.md` must exist at the project root
before UI components or pages are written (`{{SKILL:design-spec}}`). Skip only for headless
APIs or CLI tools.

## Parallelism

Tasks run in parallel only when they are marked `[P]` in `tasks.md` and touch disjoint files.
Each parallel task goes to its persona as a native subagent; the coordinator synthesizes the
results. Do not claim parallel work that did not happen.

Delegate a frontend task, for example: {{DELEGATE:frontend-specialist}}.
