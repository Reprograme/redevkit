---
name: frontend-design
description: Distinctive web UI - brief read, design system, layout, color, motion, pre-flight. Use when building web pages or UI.
paths: "**/*.tsx, **/*.jsx, **/*.vue, **/*.svelte, **/*.astro, **/*.html, **/*.css, **/*.scss"
---

# Frontend Design — Anti-Slop Web UI

> Landing pages, portfolios, marketing/product sites, and redesigns. Not dashboards, not data
> tables, not multi-step product UI. Every rule is **contextual**: first read the brief, then
> pull only what fits. Mobile UI lives in `{{SKILL:mobile-design}}`.
>
> _Design rules adapted from [taste-skill](https://github.com/Leonxlnx/taste-skill) by
> Leonxlnx (MIT)._

## DESIGN.md First

`DESIGN.md` at the project root is the design source of truth (`{{SKILL:design-spec}}`).

- If it is missing on a UI task, create it before writing components or pages.
- Build strictly with its tokens (colors, typography, spacing, radii, components). No ad-hoc
  hex values, font sizes or radii that are not tokens; add a token first if one is missing.
- When this skill's defaults disagree with `DESIGN.md` or an explicit brand, `DESIGN.md` and the
  brand win.

### Purple Ban (Default, Overridable)

By default, do not reach for the "AI purple / violet / blue glow" look: no automatic purple
gradients, purple button glows or neon accents. Use neutral bases with one high-contrast accent
instead. This is a **default, not a law**: when `DESIGN.md` tokens, the brand or the brief
explicitly use purple, use it with intent (consistent palette, harmonized neutrals, restrained
gradients). Details: Section 4.2 in [directives](references/directives.md).

## Section Map

| Section | Topic | Where |
| --- | --- | --- |
| 0 | Brief inference | Below |
| 1 | The three dials | Below |
| 2, 3, 7 | Design system map, default stack and conventions, dial definitions | [foundations](references/foundations.md) |
| 4 | Typography, color, layout, states, images, content, theme lock | [directives](references/directives.md) |
| 5, 6, 8 | Motion patterns, performance and accessibility, dark mode | [motion-performance](references/motion-performance.md) |
| 9 | AI tells (forbidden patterns), em-dash ban | [ai-tells](references/ai-tells.md) |
| 10, 12 | Pattern vocabulary, block library schema | [vocabulary-blocks](references/vocabulary-blocks.md) |
| 11 | Redesign protocol and audit-first method | [redesign](references/redesign.md) |
| 13 | Out of scope | Below |
| 14 | Final pre-flight check | [preflight](references/preflight.md) |
| Appendices | Install commands, canonical docs, Liquid Glass approximation | [design-system-sources](references/design-system-sources.md) |

Style variants (read only when the brief calls for them):

| Reference | When to read |
| --- | --- |
| [style-minimalist](references/style-minimalist.md) | Clean, editorial, monochrome minimalism |
| [style-brutalist](references/style-brutalist.md) | Raw industrial / terminal, data-heavy |

## 0. BRIEF INFERENCE (Read the Room Before Anything Else)

Before touching code or tweaking dials, **infer what the user actually wants**. Most LLM design output is bad because the model jumps to a default aesthetic instead of reading the room.

### 0.A Read these signals first

1. **Page kind** - landing (SaaS / consumer / agency / event), portfolio (dev / designer / creative studio), redesign (preserve vs overhaul), editorial / blog.
2. **Vibe words** the user used - "minimalist", "calm", "Linear-style", "Awwwards", "brutalist", "premium consumer", "Apple-y", "playful", "serious B2B", "editorial", "agency-y", "glassy", "dark tech".
3. **Reference signals** - URLs they linked, screenshots they pasted, products they named, brands they're competing with.
4. **Audience** - B2B procurement panel vs. design-conscious consumer vs. recruiter scanning a portfolio. The audience picks the aesthetic, not your taste.
5. **Brand assets that already exist** - logo, color, type, photography. For redesigns, these are starting material, not optional input (see Section 11).
6. **Quiet constraints** - accessibility-first audiences, public-sector, regulated industries, trust-first commerce, kids' products. These constraints OVERRIDE aesthetic preference.

### 0.B Output a one-line "Design Read" before generating

Before any code, state in one line: **"Reading this as: \<page kind> for \<audience>, with a \<vibe> language, leaning toward \<design system or aesthetic family>."**

Example reads:

- _"Reading this as: B2B SaaS landing for technical buyers, with a Linear-style minimalist language, leaning toward Tailwind utilities + Geist + restrained motion."_
- _"Reading this as: solo designer portfolio for hiring managers, with an editorial / kinetic-type language, leaning toward native CSS + scroll-driven animation + custom typography."_
- _"Reading this as: redesign of a public-sector service site, with a trust-first language, leaning toward GOV.UK Frontend or USWDS."_

### 0.C If the brief is ambiguous, ask one question, do not guess

Ask exactly **one** clarifying question - never a multi-question dump - and only when the design read genuinely diverges. Example: _"Should this feel closer to Linear-clean or Awwwards-experimental?"_

If you can confidently infer from context, **do not ask**. Just declare the design read and proceed.

### 0.D Anti-Default Discipline

Do not default to: AI-purple gradients, centered hero over dark mesh, three equal feature cards, generic glassmorphism on everything, infinite-loop micro-animations everywhere, Inter + slate-900. These are the LLM defaults. Reach past them deliberately based on the design read.

## 1. THE THREE DIALS (Core Configuration)

After the design read, set three dials. Every layout, motion, and density decision below is gated by these.

- **`DESIGN_VARIANCE: 8`** - 1 = Perfect Symmetry, 10 = Artsy Chaos
- **`MOTION_INTENSITY: 6`** - 1 = Static, 10 = Cinematic / Physics
- **`VISUAL_DENSITY: 4`** - 1 = Art Gallery / Airy, 10 = Cockpit / Packed Data

**Baseline:** `8 / 6 / 4`. Use these unless the design read overrides them. Do not ask the user to edit this file - overrides happen conversationally.

### 1.A Dial Inference (design read → dial values)

| Signal | VARIANCE | MOTION | DENSITY |
|---|---|---|---|
| "minimalist / clean / calm / editorial / Linear-style" | 5-6 | 3-4 | 2-3 |
| "premium consumer / Apple-y / luxury / brand" | 7-8 | 5-7 | 3-4 |
| "playful / wild / Dribbble / Awwwards / experimental / agency" | 9-10 | 8-10 | 3-4 |
| "landing page / portfolio / marketing site (default)" | 7-9 | 6-8 | 3-5 |
| "trust-first / public-sector / regulated / accessibility-critical" | 3-4 | 2-3 | 4-5 |
| "redesign - preserve" | match existing | +1 | match existing |
| "redesign - overhaul" | +2 | +2 | match existing |

### 1.B Use-Case Presets

| Use case | VARIANCE | MOTION | DENSITY |
|---|---|---|---|
| Landing (SaaS, mainstream) | 7 | 6 | 4 |
| Landing (Agency / creative) | 9 | 8 | 3 |
| Landing (Premium consumer) | 7 | 6 | 3 |
| Portfolio (Designer / studio) | 8 | 7 | 3 |
| Portfolio (Developer) | 6 | 5 | 4 |
| Editorial / Blog | 6 | 4 | 3 |
| Public-sector service | 3 | 2 | 5 |
| Redesign - preserve | match | match+1 | match |
| Redesign - overhaul | +2 | +2 | match |

### 1.C How the Dials Drive Output

Use these (or user-overridden values) as global variables. Cross-references throughout this document refer to these exact variable names - never invent aliases like `LAYOUT_VARIANCE` or `ANIM_LEVEL`.

## 13. OUT OF SCOPE

This skill is NOT for:

- Dashboards / dense product UI / admin panels (use Fluent, Carbon, Atlassian, or Polaris from Section 2.A).
- Data tables (use TanStack Table or AG Grid).
- Multi-step forms / wizards (use Form-specific patterns; this skill won't make them better).
- Code editors (use Monaco / CodeMirror with their official skinning).
- Native mobile (use Apple HIG / Material directly).
- Realtime collab UIs (presence, cursors, OT-aware - different problem class).

If the brief is one of the above, **say so explicitly**, point to the right tool, and only apply this skill's marketing-page / about-page / landing-page parts to the surfaces where they apply.

## Pre-Flight

Before delivering a page, run every box of the [pre-flight check](references/preflight.md)
(Section 14). If a box cannot be honestly ticked, the page is not done.

## Audits

| Audit | Purpose |
| --- | --- |
| `ux_audit.py` | UX and design-psychology heuristics over the built UI |
| `accessibility_checker.py` | Static accessibility checks for HTML, JSX and TSX |

Run `.redevkit/audits/ux_audit.py <project_path>` and
`.redevkit/audits/accessibility_checker.py <project_path>` with the Python interpreter detected
per `.redevkit/audits/README.md`. If no Python is available, both audits are
`SKIPPED (no Python)`: say so and fall back to the project's own commands (lint with
accessibility rules, e2e/axe checks, Lighthouse via `{{SKILL:performance-profiling}}`). Never
report a skipped audit as PASS.
