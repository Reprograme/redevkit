---
type: tasks
feature: "[###-feature-name]"
created: "[DATE]"
updated: "[DATE]"
---

# Tasks: [FEATURE NAME]

**Input**: design documents in `specs/[###-feature-name]/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/, DESIGN.md (when there is UI)

**Tests**: Test-First is the default (constitution). In every user story, the tests come
first and must FAIL before the implementation. Test tasks are optional only when the
constitution says `**TDD**: waived`.

**Organization**: tasks are grouped by user story so each story can be built, tested and
delivered on its own.

## Format

`- [ ] T001 [P] [US1] description — path — @persona — VERIFY: criterion`

- **[P]**: can run in parallel (files disjoint from the other tasks of the phase, no
  dependency on an unfinished task of the phase)
- **[US1]**: the user story the task belongs to (only in user story phases)
- **path**: the file or directory the task touches
- **@persona**: who executes the task
- **VERIFY**: the observable check that proves the task is done
- Done tasks are marked `- [X]`
- A task that could not be finished within the retry budget is marked `- [!]`, with an
  indented line below it: `- BLOCKED YYYY-MM-DD: reason; needs: what unblocks it`

<!--
  ============================================================================
  The tasks below are SAMPLES. The tasks phase replaces them with real tasks from:
  - user stories and priorities in spec.md
  - stack, structure and Domain Routing in plan.md
  - entities in data-model.md and interfaces in contracts/
  Do not keep sample tasks in the generated file.
  ============================================================================
-->

## Phase 1: Setup

**Purpose**: project initialization and shared tooling

- [ ] T001 Create project structure per plan — src/, tests/ — @backend-specialist — VERIFY: directories exist and the test command runs with 0 tests
- [ ] T002 Initialize [language] project with [framework] dependencies — package.json — @backend-specialist — VERIFY: install finishes without errors
- [ ] T003 [P] Configure linting and formatting — eslint.config.js — @backend-specialist — VERIFY: lint command exits 0 on the empty project

---

## Phase 2: Foundational

**Purpose**: blocking prerequisites for every user story

**Critical**: no user story work starts before this phase is complete.

- [ ] T004 Set up schema and migrations framework — src/db/ — @database-architect — VERIFY: migration command applies an empty migration
- [ ] T005 [P] Set up error handling and logging — src/lib/errors.ts — @backend-specialist — VERIFY: unit test for the error formatter passes
- [ ] T006 [P] Set up environment configuration — src/config.ts — @backend-specialist — VERIFY: app starts with `.env.example` values

**Checkpoint**: foundation ready; user stories can start.

---

## Phase 3: US1 - [Title] (Priority: P1) MVP

**Goal**: [what this story delivers]

**Independent Test**: [how to verify this story on its own]

### Tests (write first, must fail)

- [ ] T007 [P] [US1] Write failing contract test for [endpoint] — tests/contract/[name].test.ts — @test-engineer — VERIFY: `[test command] tests/contract/[name].test.ts` fails because [endpoint] does not exist yet
- [ ] T008 [P] [US1] Write failing integration test for [user journey] — tests/integration/[name].test.ts — @test-engineer — VERIFY: `[test command] tests/integration/[name].test.ts` fails on the first assertion

### Implementation

- [ ] T009 [P] [US1] Create [Entity1] model — src/models/[entity1].ts — @backend-specialist — VERIFY: type check passes
- [ ] T010 [US1] Implement [Service] (depends on T009) — src/services/[service].ts — @backend-specialist — VERIFY: unit tests for [Service] pass
- [ ] T011 [US1] Implement [endpoint or screen] — src/[location]/[file].ts — @[persona] — VERIFY: T007 and T008 tests pass

**Checkpoint**: US1 works and is tested on its own.

---

## Phase 4: US2 - [Title] (Priority: P2)

**Goal**: [what this story delivers]

**Independent Test**: [how to verify this story on its own]

### Tests (write first, must fail)

- [ ] T012 [P] [US2] Write failing integration test for [user journey] — tests/integration/[name].test.ts — @test-engineer — VERIFY: the test fails before the implementation

### Implementation

- [ ] T013 [P] [US2] Create [Entity] model — src/models/[entity].ts — @backend-specialist — VERIFY: type check passes
- [ ] T014 [US2] Implement [feature] — src/[location]/[file].ts — @[persona] — VERIFY: T012 passes

**Checkpoint**: US1 and US2 both work on their own.

---

[Add one phase per remaining user story, same pattern, in priority order]

---

## Phase N: Polish

**Purpose**: improvements that affect several stories

- [ ] TXXX [P] Update documentation — docs/ — @documentation-writer — VERIFY: README describes the new behavior
- [ ] TXXX Clean up and refactor touched code — src/ — @[persona] — VERIFY: full test suite passes and lint exits 0
- [ ] TXXX Validate quickstart scenarios — specs/[###-feature-name]/quickstart.md — @qa-automation-engineer — VERIFY: every quickstart step runs as written

---

## Dependencies and Execution Order

### Phase Dependencies

- **Setup**: no dependencies.
- **Foundational**: after Setup; blocks every user story.
- **User stories**: after Foundational; then in parallel or in priority order (P1 → P2 → P3).
- **Polish**: after the desired user stories.

### User Story Dependencies

- **US1 (P1)**: starts after Foundational; no dependency on other stories.
- **US2 (P2)**: starts after Foundational; may integrate with US1 but stays testable alone.

### Within Each User Story

- Tests first, and they FAIL before the implementation.
- Models before services, services before endpoints or screens, core before integration.
- The story is complete before moving to the next priority.

### Parallel Opportunities

- `[P]` tasks of the same phase can run together.
- After Foundational, different stories can run in parallel.

## Parallel Example: US1

```text
Together (tests):  T007, T008
Together (models): T009
Then in order:     T010 → T011
```

## Implementation Strategy

### MVP First

1. Phase 1 Setup, then Phase 2 Foundational.
2. US1: failing tests, implementation, tests green.
3. Stop and validate US1 on its own; demo if ready.

### Incremental Delivery

Add one story at a time: failing tests, implementation, tests green, validate. Each story
adds value without breaking the previous ones.

## Notes

- `[P]` = disjoint files and no dependency inside the phase.
- Mark a task `[X]` only after its VERIFY was observed.
- A blocked task `[!]` is skipped until what it needs is resolved; it is never deleted.
- Never renumber tasks; new work is appended as a new phase.
- Commits only when the user asks.
