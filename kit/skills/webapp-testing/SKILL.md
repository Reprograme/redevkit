---
name: webapp-testing
description: End-to-end web testing with Playwright - route discovery, critical flows, visual and API checks; use for e2e tests.
---

# Web App Testing

> Discover and test everything that matters. Leave no critical route untested.
> Unit and integration patterns are in `{{SKILL:testing-patterns}}`.

## 1. Where Results Go

E2E runs are part of `{{CMD:redevkit-test}}`: the run (commands, results, covered acceptance
scenarios, commit and tree state) is appended to `specs/NNN-name/test-report.md`. Attach paths
to traces and screenshots instead of pasting them. Never report a flow as passing without an
observed run.

## 2. Smoke Audit Script

Run `.redevkit/audits/playwright_runner.py <url>` with the Python interpreter detected per
`.redevkit/audits/README.md`:

| Option | Purpose |
| --- | --- |
| (none) | Load the page and report status, title and console errors |
| `--screenshot` | Also save a screenshot |
| `--a11y` | Run lightweight accessibility checks |

- Requires the Python package and a browser: `pip install playwright` then
  `python -m playwright install chromium`.
- No Python or no Playwright: record `SKIPPED (no Python)` or `SKIPPED (Playwright not
  installed)` and use the project's own e2e command (`npx playwright test`, Cypress...).
- The app must be running; `{{CMD:redevkit-preview}}` starts it.

## 3. Deep Audit Approach

### Discovery first

| Target | How to find |
| --- | --- |
| Routes | Scan `app/`, `pages/`, router files |
| API endpoints | Search for HTTP method handlers |
| Components | Find component directories |
| Features | Read `spec.md` acceptance scenarios |

### Systematic testing

1. **Map:** list all routes and APIs.
2. **Scan:** verify they respond.
3. **Test:** cover the critical paths, scenario by scenario.

## 4. Testing Pyramid for Web

```text
        /\          E2E (few)
       /  \         critical user flows
      /----\
     /      \       Integration (some)
    /--------\      API, data flow
   /          \
  /------------\    Component (many)
                    individual UI pieces
```

## 5. E2E Test Principles

| Priority | Tests |
| --- | --- |
| 1 | Happy-path user flows |
| 2 | Authentication flows |
| 3 | Critical business actions |
| 4 | Error handling |

| Practice | Why |
| --- | --- |
| Role/label locators or `data-testid` | Stable selectors |
| Web-first assertions (auto-wait) | No flaky fixed sleeps |
| Clean state per test | Independent tests |
| Avoid implementation details | Test user behavior |

## 6. Playwright Principles

| Concept | Use |
| --- | --- |
| Page Object Model | Encapsulate page logic |
| Fixtures | Reusable test setup |
| Assertions | Built-in auto-wait |
| Trace Viewer | Debug failures |

| Setting | Recommendation |
| --- | --- |
| Retries | 2 on CI, 0 locally |
| Trace | `on-first-retry` |
| Screenshots | `only-on-failure` |
| Video | `retain-on-failure` |

A test that only passes on retry is flaky: record it in the report, do not count it as green.

## 7. Visual Testing

| Scenario | Value |
| --- | --- |
| Design system | High |
| Marketing pages | High |
| Component library | Medium |
| Dynamic content | Lower |

Strategy: baseline screenshots, compare on change, review the diffs, update baselines only
for intentional changes. Check results against `DESIGN.md`.

## 8. API Testing Principles

| Area | Tests |
| --- | --- |
| Status codes | 200, 400, 401/403, 404, 500 |
| Response shape | Matches schema or contract (`specs/NNN-name/contracts/`) |
| Error messages | User-friendly, no internals |
| Edge cases | Empty, large, special characters |

## 9. Test Organization

```text
tests/
├── e2e/           # full user flows
├── integration/   # API, data
├── component/     # UI units
└── fixtures/      # shared data
```

| Pattern | Example |
| --- | --- |
| Feature-based | `login.spec.ts` |
| Descriptive | `user-can-checkout.spec.ts` |

## 10. CI Integration

1. Install dependencies.
2. Install browsers (`npx playwright install --with-deps`).
3. Run tests.
4. Upload artifacts (traces, screenshots).

| Strategy | Use |
| --- | --- |
| Per file | Playwright default |
| Sharding | Large suites |
| Projects | Multiple browsers |

## 11. Anti-Patterns

| ❌ Don't | ✅ Do |
| --- | --- |
| Test implementation | Test behavior |
| Hard-coded waits | Auto-waiting assertions |
| Skip cleanup | Isolate tests |
| Ignore flaky tests | Fix the root cause |

> **Remember:** E2E tests are expensive. Use them for critical paths only.
