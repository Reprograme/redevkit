# Task format (shared contract)

`redevkit-tasks` writes this format; `redevkit-implement`, `redevkit-converge`,
`redevkit-analyze` and every command that appends tasks read and write the same format.

## Task line grammar

```text
- [ ] T012 [P] [US1] description — path — @persona — VERIFY: criterion
```

| Part | Rule |
| --- | --- |
| `- [ ]` | Checkbox. Done is `- [X]` (uppercase), set only after the VERIFY criterion was observed |
| `T012` | Sequential ID, zero-padded to 3 digits, in execution order; never reused or renumbered |
| `[P]` | Optional. Only when the task's files are disjoint from every other task in the same phase and it does not depend on an unfinished task of that phase |
| `[US1]` | Required in user story phases, absent in Setup, Foundational and Polish; optional in appended phases (Convergence, Enhancement) when the task traces to a story |
| description | Imperative, specific, one outcome; small (minutes, not hours); quote data-model constraints verbatim |
| path | Repo-relative file or directory the task touches; several paths separated by a comma and a space |
| `@persona` | Persona chosen with `{{SKILL:redevkit-route}}` |
| `VERIFY:` | Observable criterion: a command and its expected result, or a concrete check |

Separators are ` — ` (space, em dash, space). The tokens `T001`, `[P]`, `[US1]`, `@persona`
and `VERIFY:` are structural: they stay identical in every project language. Only the
description and the criterion are written in the project language.

Valid line pattern (for self-checks):

```text
^- \[( |X|x)\] T\d{3,} (\[P\] )?(\[US\d+\] )?.+ — .+ — @[a-z-]+ — VERIFY: .+$
```

Examples:

```markdown
- [ ] T001 Create project structure per plan — src/, tests/ — @backend-specialist — VERIFY: directories exist and `npm test` runs with 0 tests
- [ ] T010 [P] [US1] Write failing contract test for POST /scores — tests/contract/scores.test.ts — @test-engineer — VERIFY: `npx vitest run tests/contract/scores.test.ts` fails (route missing)
- [ ] T013 [US1] Implement score service — src/services/score.ts — @backend-specialist — VERIFY: `npx vitest run tests/contract/scores.test.ts` passes
```

Wrong: missing ID, missing path, missing `@persona`, missing `VERIFY:`, `[P]` on two tasks
that edit the same file, `[US1]` in Setup.

## Phase headings

Every phase is an H2 heading `## Phase N: <name>` (English artifacts) or `## Fase N: <nome>`
(pt-BR artifacts). Readers treat any heading matching either pattern as a phase, in file order.

| Phase | en | pt-BR |
| --- | --- | --- |
| Setup | `## Phase 1: Setup` | `## Fase 1: Setup` |
| Foundational | `## Phase 2: Foundational` | `## Fase 2: Fundação` |
| User story n | `## Phase 3: US1 - <title> (Priority: P1)` | `## Fase 3: US1 - <título> (Prioridade: P1)` |
| Polish | `## Phase N: Polish` | `## Fase N: Polimento` |
| Convergence (appended) | `## Phase N: Convergence` | `## Fase N: Convergência` |
| Enhancement (appended) | `## Phase N: Enhancement YYYY-MM-DD` | `## Fase N: Melhoria AAAA-MM-DD` |

Other appended phases (for example the Enhancement phase of `redevkit-enhance`) follow the
same `Phase N:` / `Fase N:` pattern. The order is always Setup, Foundational, US1..n
(priority order), Polish, then appended phases.

Inside a user story phase:

| Sub-section | en | pt-BR |
| --- | --- | --- |
| Tests first | `### Tests (write first, must fail)` | `### Testes (escrever primeiro, devem falhar)` |
| Implementation | `### Implementation` | `### Implementação` |

## TDD rule (D37)

TDD is the default. It is waived only when `.redevkit/memory/constitution.md` contains the
line `**TDD**: waived`, set by a recorded amendment (listed in
`.redevkit/memory/changelog.md`).

When TDD applies, in every user story phase:

1. The tests sub-section comes first and has at least one task that writes tests for the
   story's acceptance scenarios (and contracts, when present).
2. Each test task's VERIFY states that the test **fails** before the implementation, with
   the command that shows it.
3. Implementation tasks follow; the last one's VERIFY states that the story's tests
   **pass**.

When TDD is waived, the tests sub-section is optional, but every task still has a VERIFY.

## Parsing rules for readers

- A task is any line matching the grammar. Lines inside fenced code blocks and HTML
  comments are not tasks.
- Next free ID = highest existing `T` number + 1. Next phase number = highest existing phase
  number + 1.
- Progress per phase = `[X]` count / task count in that phase.
- Never reorder, renumber or delete existing tasks; append instead.
