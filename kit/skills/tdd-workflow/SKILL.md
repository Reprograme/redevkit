---
name: tdd-workflow
description: Test-driven development (RED-GREEN-REFACTOR), the REDEVKIT default; use when implementing features or fixes test first.
---

# TDD Workflow

> Write tests first, code second. The test is the specification.

## 1. TDD in REDEVKIT

- **TDD is the default.** The project constitution (`.redevkit/memory/constitution.md`) starts
  with a Test-First principle; only a constitution amendment can waive it.
- **Tasks:** in `specs/NNN-name/tasks.md`, every user story starts with the tasks that write
  failing tests, then the implementation tasks (`{{SKILL:redevkit-tasks}}`).
- **Implementation:** `{{SKILL:redevkit-implement}}` runs the test tasks first and confirms they
  fail before writing production code.
- **Bugs:** the regression test that reproduces the bug comes before the fix
  (`{{SKILL:systematic-debugging}}`, artifacts in `.redevkit/bugs/<slug>/`).
- **Test runs:** `{{CMD:redevkit-test}}` fills the gaps between acceptance scenarios and tests,
  runs the full suite and appends the run to `specs/NNN-name/test-report.md`.

If the constitution waives TDD for this project, still write tests for each user story, but
the order is free.

## 2. The Cycle

```text
🔴 RED      → write a failing test and watch it fail
    ↓
🟢 GREEN    → write the minimal code to pass
    ↓
🔵 REFACTOR → improve the code, tests stay green
    ↓
   repeat
```

## 3. The Three Laws of TDD

1. Write production code only to make a failing test pass.
2. Write only enough test to demonstrate a failure.
3. Write only enough code to make the test pass.

## 4. RED Phase

| Focus | Example |
| --- | --- |
| Behavior | "should add two numbers" |
| Edge cases | "should handle empty input" |
| Error states | "should throw for invalid data" |

Rules:

- Run the test and see it fail **for the expected reason** (an assertion, not a typo or an
  import error).
- The test name describes the expected behavior.
- One behavior per test.
- Derive tests from the acceptance scenarios in `spec.md` when they exist.

## 5. GREEN Phase

| Principle | Meaning |
| --- | --- |
| **YAGNI** | You Aren't Gonna Need It |
| **Simplest thing** | Write the minimum to pass |
| **No optimization** | Just make it work |

Rules:

- Don't write code no test asks for.
- Don't optimize yet.
- Run the test again and record that it passes.

## 6. REFACTOR Phase

| Area | Action |
| --- | --- |
| Duplication | Extract common code |
| Naming | Make intent clear |
| Structure | Improve organization |
| Complexity | Simplify logic (see `{{SKILL:simplify-code}}`) |

Rules:

- All tests stay green after every step.
- Small, incremental changes.
- Re-run the suite before moving to the next test.

## 7. AAA Pattern

| Step | Purpose |
| --- | --- |
| **Arrange** | Set up test data |
| **Act** | Execute the code under test |
| **Assert** | Verify the expected outcome |

## 8. When TDD Pays Off Most

| Scenario | TDD value |
| --- | --- |
| New feature | High |
| Bug fix | High (regression test first) |
| Complex logic | High |
| Exploratory spike | Low: spike, throw it away, then rebuild test first |
| Pure layout / styling | Low: prefer visual or e2e checks (`{{SKILL:webapp-testing}}`) |

## 9. Test Prioritization

| Priority | Test type |
| --- | --- |
| 1 | Happy path |
| 2 | Error cases |
| 3 | Edge cases |
| 4 | Performance |

## 10. Anti-Patterns

| ❌ Don't | ✅ Do |
| --- | --- |
| Skip the RED phase | Watch the test fail first |
| Write tests after the code | Write tests before |
| Over-engineer the first version | Keep it simple |
| Test several behaviors at once | One behavior per test |
| Test implementation details | Test behavior |
| Claim "tests pass" without running them | Show the command and its output |

## 11. Splitting RED and GREEN Across Agents

When work is delegated, one agent can write the failing tests and another implement against
them. The implementer must not edit the tests to make them pass; a test that seems wrong goes
back to the orchestrator as a question. The test tasks finish (and fail) before the
implementation tasks start; `[P]` applies only to tasks in the same phase whose files are
disjoint.

> **Remember:** If you can't write a test, you don't understand the requirement yet.
