---
name: lint-and-validate
description: Run linters, type checks and static analysis per ecosystem. Use after code changes, before calling work done.
---

# Lint and Validate

> **MANDATORY:** run the appropriate validation tools after EVERY code change. Do not finish a
> task until the code is error-free, and show the commands you ran with their results.

## Procedures by Ecosystem

Prefer the project's own scripts (`package.json`, `pyproject.toml`, `Makefile`) and the
commands recorded in `.redevkit/memory/tech.md`. The commands below are the usual defaults.

### Node.js / TypeScript

1. **Lint/Fix:** `npm run lint` or `npx eslint "path" --fix`
2. **Types:** `npx tsc --noEmit`
3. **Security:** `npm audit --audit-level=high`

### Python

1. **Linter (Ruff):** `ruff check "path" --fix`
2. **Security (Bandit):** `bandit -r "path" -ll`
3. **Types (MyPy):** `mypy "path"`

## The Quality Loop

1. **Write/Edit code**
2. **Run the checks:** for example `npm run lint && npx tsc --noEmit`
3. **Analyze the report:** errors first, then warnings
4. **Fix and repeat:** code with failing checks is not done

## Error Handling

- If `lint` fails: fix the style or syntax issues immediately.
- If `tsc` fails: correct type mismatches before proceeding.
- If no tool is configured: check the project root for `.eslintrc`/`eslint.config.*`,
  `tsconfig.json`, `pyproject.toml` and suggest adding one. Do not report "lint passed" when no
  linter ran.

**Strict rule:** no code is reported as "done" without passing these checks, with evidence.

## Audits

| Audit | Purpose |
| --- | --- |
| `lint_runner.py` | Unified lint and type check (detects Node.js or Python and runs the matching tools) |
| `type_coverage.py` | Type-safety check: compiler output when available, otherwise escape hatches such as `any` and `@ts-ignore` |

Run `.redevkit/audits/lint_runner.py <project_path>` and
`.redevkit/audits/type_coverage.py <project_path>` with the Python interpreter detected per
`.redevkit/audits/README.md`. If no Python is available, both audits are
`SKIPPED (no Python)`: say so and fall back to the project's own commands listed above. Never
report a skipped audit as PASS.
