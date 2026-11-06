---
name: database-design
description: Database decisions - DB and ORM, schema, indexes, queries, migrations. Use when designing or changing a data model.
---

# Database Design

> **Learn to THINK, not copy SQL patterns.**

## Selective Reading Rule

Read ONLY the references relevant to the request. Check the content map and open what you need.

| Reference | Description | When to read |
| --- | --- | --- |
| [database-selection](references/database-selection.md) | PostgreSQL vs Neon vs Turso vs SQLite | Choosing a database |
| [orm-selection](references/orm-selection.md) | Drizzle vs Prisma vs Kysely | Choosing an ORM |
| [schema-design](references/schema-design.md) | Normalization, PKs, relationships | Designing a schema |
| [indexing](references/indexing.md) | Index types, composite indexes | Performance tuning |
| [optimization](references/optimization.md) | N+1, EXPLAIN ANALYZE | Query optimization |
| [migrations](references/migrations.md) | Safe migrations, serverless DBs | Schema changes |

## Core Principle

- ASK the user for database preferences when unclear and the choice changes the architecture
  (shared question protocol: one question, recommended option first)
- Choose database/ORM based on CONTEXT (check `.redevkit/memory/tech.md` first)
- Don't default to PostgreSQL for everything

## Decision Checklist

Before designing a schema:

- [ ] Asked about database preference (or found it in memory)?
- [ ] Chosen the database for THIS context?
- [ ] Considered the deployment environment?
- [ ] Planned the index strategy?
- [ ] Defined relationship types?
- [ ] Recorded the model in `specs/NNN-short-name/data-model.md`?

## Anti-Patterns

- ❌ Default to PostgreSQL for simple apps (SQLite may suffice)
- ❌ Skip indexing
- ❌ Use `SELECT *` in production
- ❌ Store JSON when structured data is better
- ❌ Ignore N+1 queries
- ❌ Run a destructive migration (drop, truncate, lossy change) without explicit confirmation
  (gate G4)

## Audit

| Audit | Purpose |
| --- | --- |
| `schema_validator.py` | Prisma schema checks: syntax, missing relations, index recommendations, naming |

Run `.redevkit/audits/schema_validator.py <project_path>` with the Python interpreter detected
per `.redevkit/audits/README.md`. If no Python is available, the audit is
`SKIPPED (no Python)`: say so and fall back to the project's own commands (for example
`npx prisma validate`, `npx drizzle-kit check`, the migration dry run, the test suite). Never
report a skipped audit as PASS.
