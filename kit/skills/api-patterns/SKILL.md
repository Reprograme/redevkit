---
name: api-patterns
description: API design decisions - REST vs GraphQL vs tRPC, responses, versioning, auth, rate limits. Use when designing an API.
---

# API Patterns

> API design principles and decision-making.
> **Learn to THINK, not copy fixed patterns.**

## Selective Reading Rule

Read ONLY the references relevant to the request. Check the content map and open what you need.

## Content Map

| Reference | Description | When to read |
| --- | --- | --- |
| [api-style](references/api-style.md) | REST vs GraphQL vs tRPC decision tree | Choosing the API type |
| [rest](references/rest.md) | Resource naming, HTTP methods, status codes | Designing a REST API |
| [response](references/response.md) | Envelope pattern, error format, pagination | Response structure |
| [graphql](references/graphql.md) | Schema design, when to use, security | Considering GraphQL |
| [trpc](references/trpc.md) | TypeScript monorepo, type safety | TS full-stack projects |
| [versioning](references/versioning.md) | URI/Header/Query versioning | Planning API evolution |
| [auth](references/auth.md) | JWT, OAuth, Passkey, API keys | Choosing an auth pattern |
| [rate-limiting](references/rate-limiting.md) | Token bucket, sliding window | API protection |
| [documentation](references/documentation.md) | OpenAPI/Swagger best practices | Documentation |
| [security-testing](references/security-testing.md) | OWASP API Top 10, auth/authz testing | Security reviews |

## Related Skills

| Need | Skill |
| --- | --- |
| API implementation | `{{SKILL:nodejs-best-practices}}`, `{{SKILL:python-patterns}}` |
| Data structure | `{{SKILL:database-design}}` |
| Security details | `{{SKILL:vulnerability-scanner}}` |

## Decision Checklist

Before designing an API:

- [ ] **Asked about the API consumers?**
- [ ] **Chosen the API style for THIS context?** (REST/GraphQL/tRPC)
- [ ] **Defined a consistent response format?**
- [ ] **Planned the versioning strategy?**
- [ ] **Considered authentication needs?**
- [ ] **Planned rate limiting?**
- [ ] **Defined the documentation approach?**

## Anti-Patterns

**DON'T:**

- Default to REST for everything
- Use verbs in REST endpoints (`/getUsers`)
- Return inconsistent response formats
- Expose internal errors to clients
- Skip rate limiting

**DO:**

- Choose the API style based on context
- Ask about client requirements
- Document thoroughly
- Use appropriate status codes

## Audit

| Audit | Purpose |
| --- | --- |
| `api_validator.py` | API endpoint checks: OpenAPI specs, response formats, common issues |

Run `.redevkit/audits/api_validator.py <project_path>` with the Python interpreter detected
per `.redevkit/audits/README.md`. If no Python is available, the audit is
`SKIPPED (no Python)`: say so and fall back to the project's own commands (contract tests,
OpenAPI linting, the test suite). Never report a skipped audit as PASS.
