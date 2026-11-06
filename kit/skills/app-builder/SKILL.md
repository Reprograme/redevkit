---
name: app-builder
description: Choose project type, stack, template and structure for a new app. Use when planning or scaffolding an app from scratch.
---

# App Builder

> Analyzes the request, detects the project type, chooses the stack and template, and plans
> the structure. Execution follows the REDEVKIT pipeline: `{{CMD:redevkit-plan}}` decides,
> `{{CMD:redevkit-create}}` scaffolds and builds.

## Selective Reading Rule

Read ONLY the references relevant to the request. Check the content map and open what you need.

| Reference | Description | When to read |
| --- | --- | --- |
| [project-detection](references/project-detection.md) | Keyword matrix, project type detection | Starting a new project |
| [tech-stack](references/tech-stack.md) | Default stack and alternatives | Choosing technologies |
| [agent-coordination](references/agent-coordination.md) | Persona pipeline and execution order | Coordinating multi-persona work |
| [scaffolding](references/scaffolding.md) | Directory structure, core files | Creating the project structure |
| [feature-building](references/feature-building.md) | Feature analysis, error handling | Adding features to an existing project |
| [templates](references/templates.md) | Template index | Scaffolding a new project |

## Templates

Quick-start scaffolding for new projects. **Read the matching template only.**

| Template | Tech stack | When to use |
| --- | --- | --- |
| [nextjs-fullstack](references/template-nextjs-fullstack.md) | Next.js + Prisma | Full-stack web app |
| [nextjs-saas](references/template-nextjs-saas.md) | Next.js + Stripe | SaaS product |
| [nextjs-static](references/template-nextjs-static.md) | Next.js + Framer Motion | Landing page |
| [nuxt-app](references/template-nuxt-app.md) | Nuxt 4 + Pinia | Vue full-stack app |
| [express-api](references/template-express-api.md) | Express + JWT | REST API |
| [python-fastapi](references/template-python-fastapi.md) | FastAPI | Python API |
| [react-native-app](references/template-react-native-app.md) | Expo + Zustand | Mobile app |
| [flutter-app](references/template-flutter-app.md) | Flutter + Riverpod | Cross-platform mobile |
| [electron-desktop](references/template-electron-desktop.md) | Electron + React | Desktop app |
| [chrome-extension](references/template-chrome-extension.md) | Chrome MV3 | Browser extension |
| [cli-tool](references/template-cli-tool.md) | Node.js + Commander | CLI app |
| [monorepo-turborepo](references/template-monorepo-turborepo.md) | Turborepo + pnpm | Monorepo |
| [astro-static](references/template-astro-static.md) | Astro + MDX | Blog / documentation |

## Where This Skill Fits

| Step | Owner | What app-builder contributes |
| --- | --- | --- |
| Questions | `{{CMD:redevkit-new}}` / `{{CMD:redevkit-plan}}` | Only what changes stack or architecture (shared question protocol) |
| Plan | `{{CMD:redevkit-plan}}` | Project type, stack, template, structure in `specs/NNN-short-name/plan.md` |
| Design gate | `{{SKILL:design-spec}}` | Projects with UI need `DESIGN.md` at the root before UI tasks |
| Scaffold | `{{CMD:redevkit-create}}` (Setup tasks) | The chosen template's setup steps |
| Build | `redevkit-orchestrate` | Tasks delegated to the personas below |
| Preview | `{{CMD:redevkit-preview}}` | Dev command and port from the template |

## Related Personas

| Persona | Role |
| --- | --- |
| `project-planner` | Task breakdown, dependency order |
| `frontend-specialist` | UI components, pages |
| `backend-specialist` | API, business logic |
| `database-architect` | Schema, migrations |
| `devops-engineer` | Environment, deployment |

## Usage Example

```text
User: "Make an Instagram clone with photo sharing and likes"

App Builder process:
1. Project type: social media app
2. Stack: Next.js + Prisma + Cloudinary + Clerk
3. Plan (specs/NNN-photo-sharing/plan.md):
   ├─ Database schema (users, posts, likes, follows)
   ├─ API routes (auth, posts, likes, follows)
   ├─ Pages (feed, profile, upload)
   └─ Components (PostCard, Feed, LikeButton)
4. DESIGN.md gate (UI project)
5. Tasks per persona, approved at the plan gate
6. Build with redevkit-create, then preview with redevkit-preview
```
