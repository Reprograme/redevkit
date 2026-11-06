---
name: testing-patterns
description: Unit and integration test patterns - pyramid, AAA, mocking, test data, suite runs; use when writing or running tests.
---

# Testing Patterns

> Principles for reliable test suites. Tests are written first by default
> (`{{SKILL:tdd-workflow}}`); end-to-end browser tests are in `{{SKILL:webapp-testing}}`.

## 1. Running the Suite and Reporting

`{{CMD:redevkit-test}}` maps the acceptance scenarios of `specs/NNN-name/spec.md` to tests,
writes the missing ones, runs the full suite and **appends** a dated run to
`specs/NNN-name/test-report.md` (template `reports/test-report.md`: use
`.redevkit/templates/overrides/reports/test-report.md` if it exists, otherwise
`.redevkit/templates/reports/test-report.md`). Write the report in the project language
(`{{LANG}}`).

How to run:

1. Run `.redevkit/audits/test_runner.py <project_path>` (add `--coverage` for coverage) with
   the Python interpreter detected per `.redevkit/audits/README.md`. It detects the stack
   (npm test, Jest, Vitest, pytest, unittest) and runs it.
2. No Python: record the audit as `SKIPPED (no Python)` and run the project's own test command
   (from `.redevkit/memory/tech.md`, or `package.json`, `pyproject.toml`, `Cargo.toml`...).
3. Each run in the report records: the commands, the observed results (passed, failed,
   skipped), which acceptance scenarios are covered, the commit (`git rev-parse HEAD`) and
   whether the working tree was clean (`git status --porcelain`).

Never report a suite as passing without a run you observed. A red run hands off to
`{{CMD:redevkit-debug}}`.

## 2. Testing Pyramid

```text
        /\          E2E (few)
       /  \         critical flows
      /----\
     /      \       Integration (some)
    /--------\      API, DB queries
   /          \
  /------------\    Unit (many)
                    functions, classes
```

## 3. AAA Pattern

| Step | Purpose |
| --- | --- |
| **Arrange** | Set up test data |
| **Act** | Execute the code under test |
| **Assert** | Verify the outcome |

## 4. Test Type Selection

| Type | Best for | Speed |
| --- | --- | --- |
| **Unit** | Pure functions, logic | Fast (< 100 ms) |
| **Integration** | API, DB, services | Medium |
| **E2E** | Critical user flows | Slow |

## 5. Unit Test Principles

| Principle | Meaning |
| --- | --- |
| Fast | < 100 ms each |
| Isolated | No external dependencies |
| Repeatable | Same result always |
| Self-checking | No manual verification |
| Timely | Written before or with the code |

| Test | Don't test |
| --- | --- |
| Business logic | Framework code |
| Edge cases | Third-party libraries |
| Error handling | Trivial getters |

## 6. Integration Test Principles

| Area | Focus |
| --- | --- |
| API endpoints | Request/response, status codes, schema |
| Database | Queries, transactions, migrations |
| External services | Contracts |

| Phase | Action |
| --- | --- |
| Before all | Connect resources |
| Before each | Reset state |
| After each | Clean up |
| After all | Disconnect |

## 7. Mocking Principles

| Mock | Don't mock |
| --- | --- |
| External APIs | The code under test |
| Database (in unit tests) | Simple dependencies |
| Time / randomness | Pure functions |
| Network | In-memory stores |

| Type | Use |
| --- | --- |
| Stub | Return fixed values |
| Spy | Track calls |
| Mock | Set expectations |
| Fake | Simplified working implementation |

## 8. Test Organization

| Naming pattern | Example |
| --- | --- |
| Should behavior | "should return error when..." |
| When condition | "when user not found..." |
| Given-when-then | "given X, when Y, then Z" |

| Level | Use |
| --- | --- |
| `describe` | Group related tests |
| `it` / `test` | Individual case |
| `beforeEach` | Common setup |

Name tests after the acceptance scenario they cover (for example `US1 scenario 2`) so the
report can map scenarios to tests.

## 9. Test Data

| Approach | Use |
| --- | --- |
| Factories | Generate test data |
| Fixtures | Predefined datasets |
| Builders | Fluent object creation |

- Use realistic data; randomize only non-essential values (faker) with a fixed seed.
- Share common fixtures; keep data minimal.
- Never use production secrets or personal data.

## 10. Best Practices

| Practice | Why |
| --- | --- |
| One behavior per test | Clear failure reason |
| Independent tests | No order dependency |
| Fast tests | Run them often |
| Descriptive names | Self-documenting |
| Clean up | No side effects between tests |

## 11. Anti-Patterns

| ❌ Don't | ✅ Do |
| --- | --- |
| Test implementation | Test behavior |
| Duplicate test code | Use factories |
| Complex test setup | Simplify or split |
| Ignore flaky tests | Fix the root cause |
| Skip cleanup | Reset state |
| Weaken an assertion to go green | Fix the code or ask |

> **Remember:** Tests are documentation. If someone can't understand what the code does from
> the tests, rewrite them.
