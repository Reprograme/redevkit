---
name: performance-profiling
description: Measure-first performance work - Core Web Vitals, bundle and runtime profiling, Lighthouse; use when something is slow.
---

# Performance Profiling

> Measure, analyze, optimize - in that order. No optimization claim without a before and
> after measurement.

React and Next.js specific rules are in `{{SKILL:nextjs-react-expert}}`; mobile apps in
`{{SKILL:mobile-design}}`.

## 1. Automated Audits

Run these with the Python interpreter detected per `.redevkit/audits/README.md`. Without
Python, record each one as `SKIPPED (no Python)` and use the fallback.

| Audit | Command | Needs | Fallback |
| --- | --- | --- | --- |
| Bundle size | `.redevkit/audits/bundle_analyzer.py <project_path>` | A production build (`.next/static`, `dist`, `build`, `out`) | The framework's own build output or bundle analyzer plugin |
| Lighthouse | `.redevkit/audits/lighthouse_audit.py <url>` | Lighthouse CLI on the `PATH` (`npm install -g lighthouse`) and a running app | `npx lighthouse <url>` or Chrome DevTools > Lighthouse |

- Both accept thresholds; run them with `--help` to see the options.
- Build first for the bundle audit; start the app (`{{CMD:redevkit-preview}}`) for Lighthouse.
- A missing tool is `SKIPPED (<reason>)`, never a pass. Report commands and observed numbers.

## 2. Core Web Vitals

| Metric | Good | Poor | Measures |
| --- | --- | --- | --- |
| **LCP** | < 2.5 s | > 4.0 s | Loading |
| **INP** | < 200 ms | > 500 ms | Interactivity |
| **CLS** | < 0.1 | > 0.25 | Stability |

| Stage | Tool |
| --- | --- |
| Development | Local Lighthouse |
| CI/CD | Lighthouse CI |
| Production | RUM (real user monitoring) |

Lab tools (Lighthouse) cannot measure INP directly; use Total Blocking Time as the lab proxy
and field data for INP.

## 3. Profiling Workflow

```text
1. BASELINE → measure the current state, record the numbers
2. IDENTIFY → find the biggest bottleneck
3. FIX      → make one targeted change
4. VALIDATE → measure again under the same conditions
```

| Problem | Tool |
| --- | --- |
| Page load | Lighthouse |
| Bundle size | Bundle analyzer |
| Runtime | DevTools Performance panel |
| Memory | DevTools Memory panel |
| Network | DevTools Network panel |
| Node.js server | `node --cpu-prof`, `node --heap-prof`, clinic.js |
| Python | `cProfile`, `py-spy` |

## 4. Bundle Analysis

Budget: the one set in `plan.md` or `DESIGN.md`. Without one, `bundle_analyzer.py` defaults
apply: per file, warn above 250 KiB and fail above 750 KiB; total JavaScript, fail above
2048 KiB.

| Issue | Indicator |
| --- | --- |
| Large dependencies | Top of the bundle |
| Duplicate code | Same module in several chunks |
| Unused code | Low coverage in DevTools Coverage |
| Missing splits | One large chunk |

| Finding | Action |
| --- | --- |
| Big library | Import specific modules |
| Duplicate dependencies | Dedupe, align versions |
| Route in the main chunk | Code split |
| Unused exports | Tree shake |

## 5. Runtime Profiling

| Pattern (Performance panel) | Meaning |
| --- | --- |
| Long tasks (> 50 ms) | UI blocking |
| Many small tasks | Possible batching opportunity |
| Layout / paint | Rendering bottleneck |
| Script | JavaScript execution |

| Pattern (Memory panel) | Meaning |
| --- | --- |
| Growing heap | Possible leak |
| Large retained size | Check references |
| Detached DOM | Not cleaned up |

## 6. Common Bottlenecks

| Symptom | Likely cause |
| --- | --- |
| Slow initial load | Large JS, render-blocking resources |
| Slow interactions | Heavy event handlers |
| Jank during scroll | Layout thrashing |
| Growing memory | Leaks, retained references |
| Slow API | N+1 queries, missing indexes, no caching |

## 7. Quick Win Priorities

| Priority | Action | Impact |
| --- | --- | --- |
| 1 | Enable compression | High |
| 2 | Lazy load images | High |
| 3 | Code split routes | High |
| 4 | Cache static assets | Medium |
| 5 | Optimize images | Medium |

## 8. Anti-Patterns

| ❌ Don't | ✅ Do |
| --- | --- |
| Guess at problems | Profile first |
| Micro-optimize | Fix the biggest issue |
| Optimize early | Optimize when measured |
| Ignore real users | Use RUM data |
| Report "faster" without numbers | Show before/after measurements |

> **Remember:** The fastest code is code that doesn't run. Remove before optimizing.
