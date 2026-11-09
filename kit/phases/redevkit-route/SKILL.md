---
name: redevkit-route
description: Map a request to personas and skills by domain; ask when domains conflict.
---

# Route a request to personas and skills

Choose who does the work and which knowledge they load. The calling command (or the planner,
when it assigns `@persona` to each task) gives you the request, feature or task text; this skill
never reads the user's input on its own.

## Output

1. One announcement line, in the user's language:
   `Routing: @persona (+ @persona) · skills: a, b · reason: <domain>`.
2. The selection handed back to the caller: personas, skills, and any assumption you made.
3. The caller then delegates per `{{SKILL:redevkit-orchestrate}}`, or applies the persona file
   and reads the skills itself. Persona files and skills live at paths like
   `{{PERSONA:backend-specialist}}` and `{{SKILL:api-patterns}}` (same pattern for every name).

Analyze silently: no "I am analyzing your request" commentary, just the announcement line.

## Rules

1. **Explicit mention wins.** An `@persona` or a skill name written by the user (or fixed in the
   task line) is used as given, even if the table would choose differently.
2. **Classify the request first.**

   | Type | Signals | Routing |
   | --- | --- | --- |
   | Question | "what is", "how does", "explain" | No persona; answer directly |
   | Survey | "analyze", "map", "overview" | `explorer-agent` (read-only) |
   | Simple change | one file, clear fix | The single domain owner |
   | Feature or refactor | "build", "create", "implement", "refactor" | Domain owner(s) inside the pipeline (`{{CMD:redevkit-plan}}` first when no tasks exist) |
   | New app | "from scratch", "build me an app", multi-page | `project-planner` with `app-builder`, then `orchestrator`; never a lone specialist |

3. **Detect domains** with the table below. One domain: its persona and skills. A request
   spanning two or more domains is coordinated per `redevkit-orchestrate`, and each part keeps
   its own domain persona. In `tasks.md`, `@orchestrator` is never a task owner: a task that
   spans several domains is split into one task per owner.
4. **Smallest coherent set.** Pick the fewest personas that cover the work; one owner who can do
   it safely means one persona.
5. **Conflicting domains: ask, do not assume** (see below).
6. **Too vague to route** ("make it better"): do not guess; hand the request back to the caller
   for clarification (`{{SKILL:redevkit-clarify}}`).
7. **Precedence** when instructions collide (as in `AGENTS.md`): user request >
   `.redevkit/memory/constitution.md` > `AGENTS.md` > command skill > persona > knowledge
   skill. The user's request wins, but a request that conflicts with the constitution stops
   at gate G3, or becomes an amendment through gate G1; it never silently overrides it.

## Asking about a conflict

When signals point to different domains (for example "mobile" may mean responsive web or a
native app) and neither the spec, the plan nor `.redevkit/memory/` settles it, ask one question
with up to 3 options, the recommended one first and marked "(Recommended)", with the reason:

{{ASK}}

In `--auto` or non-interactive runs, adopt the recommendation and record it as an assumption.
When you run as a subagent, return the question to the orchestrator instead of asking. Then
announce the routing line.

## Domain table

Triggers are examples in English and Portuguese, not an exhaustive list.

| Domain | Triggers | Persona(s) | Skills (and references) |
| --- | --- | --- | --- |
| Games | game, jogo, Phaser, Godot, Unity, Three.js, multiplayer | `game-developer` | `game-development` (+ `{{SKILLDIR:game-development}}/references/2d-games.md`, `{{SKILLDIR:game-development}}/references/3d-games.md`, `{{SKILLDIR:game-development}}/references/web-games.md`, `{{SKILLDIR:game-development}}/references/mobile-games.md`, `{{SKILLDIR:game-development}}/references/pc-games.md`, `{{SKILLDIR:game-development}}/references/vr-ar.md`, `{{SKILLDIR:game-development}}/references/multiplayer.md`, `{{SKILLDIR:game-development}}/references/game-design.md`, `{{SKILLDIR:game-development}}/references/game-art.md`, `{{SKILLDIR:game-development}}/references/game-audio.md`) |
| New app | app from scratch, scaffolding, "create an app", app do zero, "crie um app" | `project-planner` (+ `orchestrator`) | `app-builder` (+ its template references), `architecture` |
| Frontend/UI | component, page, React, Vue, CSS, Tailwind, dashboard, componente, página | `frontend-specialist` | `frontend-design`, `design-spec`, `nextjs-react-expert`, `tailwind-patterns`, `web-design-guidelines`, `frontend-architecture` |
| Mobile | React Native, Flutter, iOS, Android, Expo | `mobile-developer` | `mobile-design` |
| Backend/API | API, endpoint, server, Express, FastAPI, servidor | `backend-specialist` | `api-patterns`, `nodejs-best-practices`, `python-patterns` |
| Database | schema, migration, SQL, Prisma, query, migração | `database-architect` | `database-design` |
| Security | auth, login, JWT, password, vulnerability, senha, vulnerabilidade | `security-auditor` | `vulnerability-scanner`, `api-patterns` |
| Offensive security | pentest, exploit, red team | `penetration-tester` | `red-team-tactics`, `vulnerability-scanner` |
| Testing | test, coverage, e2e, Playwright, teste, cobertura | `test-engineer`, `qa-automation-engineer` | `testing-patterns`, `tdd-workflow`, `webapp-testing` |
| Bugs | bug, error, crash, failure, erro, falha | `debugger` | `systematic-debugging` |
| DevOps/Deploy | Docker, CI/CD, deploy, nginx, server | `devops-engineer` | `deployment-procedures`, `server-management`, `bash-linux`, `powershell-windows` |
| Performance | slow, optimize, cache, bundle, lento, otimizar | `performance-optimizer` | `performance-profiling` |
| SEO/GEO | SEO, meta, sitemap, AI search, busca por IA | `seo-specialist` | `seo-fundamentals`, `geo-fundamentals` |
| i18n | translation, locale, i18n, tradução | `frontend-specialist` | `i18n-localization` |
| Legacy code | refactor, legacy, understand the code, refatorar, legado, entender o código | `code-archaeologist`, `explorer-agent` | `simplify-code`, `clean-code`, `code-review-checklist`, `code-review-graph` |
| Product | requirements, user story, MVP, backlog, requisitos | `product-owner` | (brainstorm/clarify: `redevkit-clarify`) |
| Documentation | docs, README, guide, guia | `documentation-writer` | `documentation-templates` |
| Rust | Rust, cargo | `backend-specialist` | `rust-pro` |
| MCP | MCP server, MCP tool, servidor MCP | `backend-specialist` | `mcp-builder` |
| Multi-domain | 2 or more domains in the same request | `orchestrator` (coordinates; never a task owner) | `redevkit-orchestrate`, `context-compression`, `batch-operations` |

Load only the skills the work needs: the table lists candidates, not a mandatory bundle. Pick
shell skills by the OS in `.redevkit/memory/tech.md` (`bash-linux` or `powershell-windows`).
`code-review-graph` is optional and only applies when a `.code-review-graph/` map exists.

## Assigning a persona to each task

When the planner writes `tasks.md`, each line gets exactly one `@persona`, never
`@orchestrator`; split a task that needs several owners into one task per owner:

| Files or work | Owner |
| --- | --- |
| Tests (`**/*.test.*`, `**/__tests__/**`, `tests/`) | `test-engineer` (E2E suites: `qa-automation-engineer`) |
| Web UI (`**/components/**`, pages, styles) | `frontend-specialist` |
| Mobile app code | `mobile-developer` (full stack inside a mobile project) |
| API and server (`**/api/**`, `**/server/**`) | `backend-specialist` |
| Schema and migrations | `database-architect` |
| CI, deploy and infrastructure config | `devops-engineer` |
| Game code | `game-developer` |
| Docs requested by the spec | `documentation-writer` |

Project type decides between web and mobile: a mobile project never routes app screens to
`frontend-specialist`, and a web project never routes to `mobile-developer`.

`security-auditor` and `explorer-agent` are read-only. Assign them review and discovery tasks;
the implementation of authentication or authorization goes to `backend-specialist`, with a
`security-auditor` review task after it.

## Examples

| Request | Routing |
| --- | --- |
| "Create a dark mode toggle button" | `@frontend-specialist` · `frontend-design`, `design-spec` |
| "Review the auth flow for vulnerabilities" | `@security-auditor` · `vulnerability-scanner` |
| "Login returns 401" | `@debugger` · `systematic-debugging` |
| "Chat app with real-time notifications" | `@orchestrator` (backend, frontend, tests) · `redevkit-orchestrate` |
| "Add mobile support to the web app" | Conflict: ask responsive web (recommended when a web app exists) or native app |
| "How does React work?" | Question: no persona |
