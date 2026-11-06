---
name: nextjs-react-expert
description: React and Next.js performance rules by impact (waterfalls, bundles, re-renders, caching); use when writing React code.
paths: "**/*.jsx, **/*.tsx, **/next.config.*, **/app/**/*.ts, **/pages/**/*.ts"
---

# Next.js & React Performance Expert

> Based on Vercel Engineering's React best practices (Next.js 16 / React 19 era), prioritized
> by impact, plus Next.js 16 Cache Components.
> **Philosophy:** eliminate waterfalls first, optimize bundles second, then micro-optimize.

## Selective Reading Rule

Read **only** the sections relevant to the task. For performance reviews, start with the
CRITICAL sections (1-2), then move to HIGH and MEDIUM.

## Content Map

| Section | Impact | When to read |
| --- | --- | --- |
| [1-async-eliminating-waterfalls](references/1-async-eliminating-waterfalls.md) | 🔴 CRITICAL | Slow page loads, sequential API calls, data-fetching waterfalls |
| [2-bundle-bundle-size-optimization](references/2-bundle-bundle-size-optimization.md) | 🔴 CRITICAL | Large bundles, slow Time to Interactive, First Load issues |
| [3-server-server-side-performance](references/3-server-server-side-performance.md) | 🟠 HIGH | Slow SSR, API route optimization, server-side waterfalls |
| [4-client-client-side-data-fetching](references/4-client-client-side-data-fetching.md) | 🟡 MEDIUM-HIGH | Client data management, SWR patterns, deduplication |
| [5-rerender-re-render-optimization](references/5-rerender-re-render-optimization.md) | 🟡 MEDIUM | Excessive re-renders, memoization |
| [6-rendering-rendering-performance](references/6-rendering-rendering-performance.md) | 🟡 MEDIUM | Rendering bottlenecks, virtualization, images |
| [7-js-javascript-performance](references/7-js-javascript-performance.md) | ⚪ LOW-MEDIUM | Micro-optimizations, caching, hot loops |
| [8-advanced-advanced-patterns](references/8-advanced-advanced-patterns.md) | 🔵 VARIABLE | `useLatest`, init-once, event handler refs |
| [9-cache-components](references/9-cache-components.md) | 🔴 CRITICAL (Next.js 16+ only) | `use cache`, `cacheLife`, `cacheTag`, Partial Prerendering |

## Quick Decision Tree

```text
Slow page loads / long Time to Interactive  → sections 1, 2
Large bundle (> 200 KB)                      → section 2 (dynamic imports, barrel imports)
Slow server-side rendering                   → section 3 (parallel fetching, streaming)
Too many re-renders / UI lag                 → section 5 (memo, useMemo, useCallback)
Rendering bottlenecks                        → section 6 (virtualization, layout thrashing)
Client-side data fetching problems           → section 4 (SWR deduplication)
Advanced patterns                            → section 8
Next.js 16+ caching and PPR                  → section 9
```

## Impact Priority (comprehensive optimization)

1. **CRITICAL:** waterfalls (each one adds a full network round trip), bundle size (affects
   TTI and LCP), and Cache Components on Next.js 16+.
2. **HIGH:** server-side performance.
3. **MEDIUM:** client data fetching, re-renders, rendering.
4. **LOW:** JavaScript micro-optimizations, advanced patterns.

## Automated Check

Run `.redevkit/audits/react_performance_checker.py <project_path>` with the Python interpreter
detected per `.redevkit/audits/README.md` (`--fail-on-warnings` makes advisory warnings
blocking). Without Python, record `SKIPPED (no Python)` and review sections 1-2 by hand plus
the framework's build output (`next build` prints route sizes). Bundle and Lighthouse audits
are in `{{SKILL:performance-profiling}}`.

## Performance Review Checklist

**Critical (must fix):**

- [ ] No sequential data fetching for independent requests
- [ ] Main bundle under ~200 KB
- [ ] No barrel imports in app code
- [ ] Dynamic imports for large components
- [ ] Parallel data fetching where possible

**High:**

- [ ] Server Components used where appropriate
- [ ] API routes optimized (no N+1 queries)
- [ ] Suspense boundaries around data fetching
- [ ] Static generation or caching where possible

**Medium:**

- [ ] Expensive computations memoized
- [ ] Long lists virtualized (> 100 items)
- [ ] Images through `next/image`
- [ ] No unnecessary re-renders

**Low (polish):**

- [ ] Hot-path loops optimized
- [ ] RegExp literals hoisted
- [ ] Property access cached in loops

## Anti-Patterns

| ❌ Don't | ✅ Do |
| --- | --- |
| Sequential `await` for independent work | `Promise.all()` |
| Import a whole library for one function | Import the specific module |
| Barrel re-exports (`index.ts`) in app code | Direct imports |
| Load large components eagerly | `dynamic(() => import('./Heavy'))` |
| Fetch in `useEffect` without deduplication | SWR / React Query or server fetching |
| Client Components where Server Components work | Server Components by default |
| Optimize without measuring | React DevTools Profiler, Chrome DevTools first |

## How to Use This Skill

- **New features:** apply sections 1-2 while building, Server Components by default
  (section 3), memoize only expensive work (section 5).
- **Performance reviews:** section 1, then 2, then 3, then the rest as needed.
- **Slow page reported:** identify the symptom, use the decision tree, read that section,
  measure before and after.

## Related Skills

| Need | Skill |
| --- | --- |
| API design | `{{SKILL:api-patterns}}` |
| Database optimization | `{{SKILL:database-design}}` |
| Tests | `{{SKILL:testing-patterns}}` |
| UI/UX principles | `{{SKILL:frontend-design}}` |
| Styling with Tailwind | `{{SKILL:tailwind-patterns}}` |
| Deployment | `{{SKILL:deployment-procedures}}` |

> **Remember:** every sequential `await` is a potential waterfall, every `import` potential
> bundle bloat, every unnecessary re-render wasted work. Measure, don't guess.
