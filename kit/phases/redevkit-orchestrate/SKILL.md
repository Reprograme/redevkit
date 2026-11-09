---
name: redevkit-orchestrate
description: Coordinate personas: smallest set, parallel only for disjoint [P] tasks.
---

# Orchestrate task execution

You are the coordinator. You read, decide, brief, delegate, verify and integrate; the personas do
the domain work. The calling command (`{{CMD:redevkit-create}}`, `{{CMD:redevkit-enhance}}`,
`{{CMD:redevkit-debug}}`, usually through `{{SKILL:redevkit-implement}}`) gives you the work:
the feature folder `specs/NNN-name/` (or the bug folder `.redevkit/bugs/<slug>/`), the phases to
run and whether `--auto` is on. Memory recall, light verification, memory save and the handoff
stay with the caller.

## Principles

1. **Smallest coherent set.** Use as few personas as the work needs. There is no minimum number
   of agents; one owner who can do a task safely is the right answer.
2. **Never delegate understanding.** Read the spec, plan and task before delegating. Every brief
   is self-contained: paths, the decision already taken, what to change, how to verify. Never
   write "based on your findings, fix it".
3. **Parallel only when safe.** Only `[P]` tasks whose files are disjoint run at the same time.
   Everything else runs in order.
4. **Evidence or it did not happen.** A task is done when its VERIFY criterion is met with a
   command that ran and an observed result. A skipped check is `SKIPPED (reason)`, never `PASS`.
5. **Honest reporting.** Report exactly what ran in parallel, in sequence or inline. Never
   describe agents as running when they are not, and never predict a result you have not seen.
6. **Bounded.** Every run has a budget and stops on no progress.

## 1. Check the delegation mechanism

- Delegation to a persona:
  {{#claude}}the Agent tool with `subagent_type` set to the persona name; several Agent calls in
  one message run in parallel. Subagents cannot start further subagents, so delegation depth is
  one.{{/claude}}{{#codex}}`spawn_agent` with `agent_type` set to the persona name; spawn
  several before waiting to run them in parallel. Custom agents require a trusted project. When
  they are unavailable, read `.codex/agents/<persona>.toml` and apply its
  `developer_instructions` inline, one task at a time.{{/codex}}
- If no delegation is available at all, execute each task inline yourself after reading the
  persona file, strictly in order, and label every task "inline" in the report.
- Delegated personas never delegate further.

## 2. Understand before delegating

Read, in this order, and keep what each task needs:

1. `.redevkit/memory/constitution.md` and the invariants in `.redevkit/memory/system.md`.
2. `.redevkit/memory/tech.md`: OS, build, test and lint commands.
3. `spec.md` (user stories, acceptance scenarios), `plan.md` (decisions, structure, Design
   Source-of-Truth), and as relevant `data-model.md`, `contracts/`, `research.md`.
4. `DESIGN.md` at the root when any task touches UI.
5. `tasks.md`: phases, remaining `[ ]` tasks, their `@persona`, paths and VERIFY criteria.

For each task you must be able to say why it exists, which files it touches, which decision it
implements and how its VERIFY will be checked. If you cannot, resolve that first (read more, or
ask per step 6). A task without `@persona` is routed per `{{SKILL:redevkit-route}}`.

## 3. Set the budget

| Limit | Default |
| --- | --- |
| Subagents running at once | 3 |
| Attempts per task | 2 (the first try plus one corrected brief) |
| Delegation depth | 1 (personas never delegate) |
| No progress | Stop a task when an attempt produces no new change and no new evidence, or repeats the same failure |
| Blocked tasks | Mark blocked, skip its dependents in any phase, continue independent work (step 7) |

The constitution or the caller may set other limits; theirs win. Never allow open-ended retry or
self-delegation loops.

## 4. Build the batches for each phase

Process phases in order: Setup, Foundational, US1..n, Polish (and any appended Enhancement or
Convergence phases). Inside a phase, keep the listed task order and:

- **Test first.** In each user story, the test tasks run before the implementation tasks. After a
  test task, confirm the new tests fail for the expected reason before implementation starts
  (unless the constitution waives TDD).
- **Parallel batch.** Consecutive `[P]` tasks form one batch only if their paths do not overlap
  each other or any running task. Check the paths yourself: `[P]` is a claim, not a guarantee.
  Overlap or a hidden dependency (schema before types, API before client) means sequential, and
  you note why.
- **Read-only work** (discovery, review) writes nothing and may run alongside other read-only
  work.
- At most the budgeted number of subagents per batch; split larger batches.

## 5. Brief and delegate

Write each brief with the delegation contract in [briefs](references/briefs.md): goal and why,
the exact task line, allowed paths, out-of-scope areas owned by others, trusted decisions,
untrusted inputs, expected artifact, VERIFY command and criterion, stop conditions and the return
format. Personas never edit `tasks.md`; you do.

Delegate each task to the persona in its line. Example for a test task: {{DELEGATE:test-engineer}}.
Use the same mechanism for every persona (step 1). Launch every task of a parallel batch together,
then wait for all of them before integrating. Do not read a subagent's partial output while it
runs.

## 6. Answer subagent questions

Subagents never ask the user; they return questions to you. Answer each one from the spec, plan,
`DESIGN.md`, `.redevkit/memory/` or the code when they settle it, and re-brief the subagent.

Only a question that changes scope or architecture and that the artifacts do not settle goes to
the user: one at a time, up to 3 options with the recommended one first and marked
"(Recommended)" (the caller's limit of 5 questions per command applies):

{{ASK}}

In `--auto` or non-interactive runs, adopt the recommendation and record it as an assumption (the
spec's Assumptions section, or the report), except at gates. If you yourself run as a subagent,
return the question to your caller instead.

Gates always stop the run for the user, even with `--auto`: a constitution conflict (G3) and any
destructive or irreversible action (G4).

## 7. Review, verify, mark

For each returned result:

1. **Check the evidence.** Changed paths stay inside the allowed paths; commands and their output
   are present; the VERIFY criterion is addressed. Missing evidence means not done.
2. **Verify independently.** Re-run the task's VERIFY command yourself when it is cheap (tests,
   lint, build of the touched part). Do not trust the implementer's claim alone.
3. **Pass:** mark the task `[X]` in `tasks.md` right away.
4. **Fail:** write a corrected, more specific brief (what failed, the output, what to change) and
   try again within the budget, continuing the same subagent when the runtime supports it.
5. **No progress or budget spent:** leave the task `[ ]`, record it as blocked with the evidence,
   skip tasks that depend on it, and continue with independent work only.

After each parallel batch, run the affected tests once on the integrated tree: separate green
results do not prove the combination works. A conflict between outputs is resolved with the order
in [patterns](references/patterns.md), never silently.

## 8. Report to the caller

```markdown
## Orchestration result

| Task | Persona | Execution | Evidence | Status |
| --- | --- | --- | --- | --- |
| T012 | test-engineer | parallel (batch 2) | `npm test -- collision` → 1 failing as expected | [X] |

- Ran in parallel: [batches and task IDs, or "none"]
- Ran inline: [task IDs and why, or "none"]
- Blocked: [task, reason, evidence, what is needed]
- Assumptions: [adopted recommendations]
- Open questions: [with recommendation]
```

The caller runs its light verification, saves memory and writes the handoff.

## Anti-patterns

| Anti-pattern | Instead |
| --- | --- |
| "Look at the code and do what's needed" | File paths, the decision, the exact change, the VERIFY |
| Adding personas to look thorough | Smallest coherent set |
| Parallel writers on overlapping files | Sequential, or split the files |
| Marking `[X]` from a claim | Mark only after observed evidence |
| Retrying the same brief | Correct the brief or stop and report |
| Reporting "agents running" from memory | Report only what the runtime confirmed |
| Coordinator rewriting a persona's work silently | Re-brief the owner, or record why you intervened |
