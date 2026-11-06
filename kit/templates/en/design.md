---
type: design
version: "[DESIGN_VERSION, e.g. 1.0.0]"
created: "[DATE]"
updated: "[DATE]"
---

# [PROJECT_NAME] Design System

<!--
  DESIGN.md is the single source of truth for the project's visual language, kept at the
  project root (one per project). It must exist before any UI is built; UI code uses the
  token names below, never ad-hoc values. Token names are normative; the prose explains the
  intent. Each feature's plan records its deltas to this file in "Design Source-of-Truth".
  Sections follow the DESIGN.md order (Overview, Colors, Typography, Layout, Elevation,
  Shapes, Motion, Components, Accessibility, Do's and Don'ts); delete what does not apply.
  Replace every [FIELD]; remove these comments once filled.
-->

## Overview

**Product**: [what it is and for whom]

**Personality**: [three adjectives, e.g. calm, precise, warm]

**Brand notes**: [logo usage, voice, imagery style, references that inspired the direction]

**Platforms**: [web | iOS | Android | desktop | game canvas]

**Color policy (Purple Ban)**: default ON. Purple and violet hues, and purple-blue "AI glow"
gradients, are not used unless the brand says otherwise.
Brand override: [none | "brand color is purple: ban lifted for colors.primary only"]

## Colors

| Token | Value | Role | Use for | Contrast pair |
| --- | --- | --- | --- | --- |
| `colors.primary` | [#RRGGBB] | Brand and main action | Primary buttons, key links | `colors.on-primary` |
| `colors.on-primary` | [#RRGGBB] | Text on primary | Button labels | - |
| `colors.secondary` | [#RRGGBB] | Supporting accent | Secondary actions, highlights | `colors.on-primary` |
| `colors.surface` | [#RRGGBB] | Base background | Pages, cards | `colors.on-surface` |
| `colors.on-surface` | [#RRGGBB] | Main text | Body text, icons | - |
| `colors.muted` | [#RRGGBB] | Secondary text | Captions, placeholders | `colors.surface` |
| `colors.border` | [#RRGGBB] | Dividers | Borders, separators | - |
| `colors.success` | [#RRGGBB] | Positive state | Confirmations | `colors.on-surface` |
| `colors.warning` | [#RRGGBB] | Caution state | Warnings | `colors.on-surface` |
| `colors.error` | [#RRGGBB] | Error state | Errors, destructive actions | `colors.on-primary` |

**Dark mode**: [not supported | token overrides listed below]

## Typography

**Font families**: [heading font], [body font], [mono font]; fallback: [system stack]

| Token | Size | Weight | Line height | Letter spacing | Use for |
| --- | --- | --- | --- | --- | --- |
| `typography.display` | [48px] | [700] | [1.1] | [-0.02em] | Hero titles |
| `typography.headline-lg` | [32px] | [600] | [1.2] | [-0.01em] | Page titles |
| `typography.headline-md` | [24px] | [600] | [1.3] | [0] | Section titles |
| `typography.body-lg` | [18px] | [400] | [1.6] | [0] | Lead paragraphs |
| `typography.body-md` | [16px] | [400] | [1.6] | [0] | Body text |
| `typography.body-sm` | [14px] | [400] | [1.5] | [0] | Secondary text |
| `typography.label-md` | [14px] | [600] | [1.2] | [0.01em] | Buttons, labels |
| `typography.label-sm` | [12px] | [600] | [1.2] | [0.02em] | Tags, captions |

## Layout

| Token | Value | Use for |
| --- | --- | --- |
| `spacing.xs` | [4px] | Icon gaps |
| `spacing.sm` | [8px] | Tight groups |
| `spacing.md` | [16px] | Default padding |
| `spacing.lg` | [24px] | Card padding, section gaps |
| `spacing.xl` | [48px] | Page sections |

**Grid**: [e.g. 12 columns, 24px gutter, max content width 1200px]

**Breakpoints**: [e.g. sm 640px, md 768px, lg 1024px, xl 1280px]

## Elevation and Depth

| Token | Value | Use for |
| --- | --- | --- |
| `elevation.none` | [none] | Flat surfaces |
| `elevation.sm` | [0 1px 2px rgba(0,0,0,0.08)] | Cards at rest |
| `elevation.md` | [0 4px 12px rgba(0,0,0,0.12)] | Dropdowns, hover |
| `elevation.lg` | [0 12px 32px rgba(0,0,0,0.16)] | Modals, dialogs |

**Flat alternative**: [borders, tonal layers or contrast used instead of shadows, if any]

## Shapes

| Token | Value | Use for |
| --- | --- | --- |
| `rounded.none` | [0] | Tables, full-bleed media |
| `rounded.sm` | [4px] | Inputs, tags |
| `rounded.md` | [8px] | Buttons, cards |
| `rounded.lg` | [16px] | Modals, large panels |
| `rounded.full` | [9999px] | Avatars, pills |

## Motion

| Token | Duration | Easing | Use for |
| --- | --- | --- | --- |
| `motion.fast` | [120ms] | [ease-out] | Hover, press feedback |
| `motion.base` | [200ms] | [ease-in-out] | Expand, collapse, fades |
| `motion.slow` | [320ms] | [cubic-bezier(0.2, 0, 0, 1)] | Page and modal transitions |

**Reduced motion**: when the user prefers reduced motion, [disable non-essential animation;
keep opacity changes under 120ms].

## Components

| Component | Tokens | Variants and states | Status |
| --- | --- | --- | --- |
| Button | `colors.primary`, `typography.label-md`, `rounded.md`, `spacing.md` | primary, secondary, ghost; hover, focus, disabled, loading | [planned / built] |
| Input | `colors.surface`, `colors.border`, `rounded.sm` | default, focus, error, disabled | [planned / built] |
| Card | `colors.surface`, `elevation.sm`, `rounded.md`, `spacing.lg` | default, interactive | [planned / built] |
| [Component] | [tokens] | [variants and states] | [planned / built] |

## Accessibility

- **Contrast**: [WCAG 2.2 AA: 4.5:1 for body text, 3:1 for large text and UI parts]
- **Focus**: [visible focus ring using `colors.primary`, at least 2px]
- **Touch targets**: [at least 44 × 44 px]
- **Keyboard**: [every action reachable and operable by keyboard]
- **Motion**: [respects reduced-motion preference]
- **Content**: [alt text for images, labels for every input, language set on the page]

## Do's and Don'ts

- Do use only the tokens in this file; add a token here before using a new value.
- Do keep one primary action per screen.
- Don't use purple or violet unless the Color policy above lifts the Purple Ban.
- Don't mix rounded and sharp corners in the same view.
- [Project-specific rule]

## Change Log

| Date | Feature | Change |
| --- | --- | --- |
| [DATE] | [###-feature-name] | [Created / tokens or components added or changed] |
