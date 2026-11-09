---
name: code-review-graph
description: Optional pip tool that graphs a codebase to scope reviews to a change blast radius. Use only on large repos.
---

# Code Review Graph

> **Optional.** `code-review-graph` is an external tool installed with pip/pipx. It is not
> part of REDEVKIT and nothing in the pipeline depends on it. Without it, review and planning
> work as usual (read the files, use `{{SKILL:code-review-checklist}}`).

## Overview

`code-review-graph` is an MCP server that uses **Tree-sitter** to parse the codebase into an
AST graph stored in **SQLite**. When the agent needs context for a task, it queries the graph
first and gets only the files in the **blast radius** of the change, instead of reading every
file in the directory.

**Token impact (illustrative, varies by codebase):**

| Codebase type | Pattern |
| --- | --- |
| Large monorepo (10K+ files) | Biggest savings: the graph reads a small fraction of files |
| Mid-size app (1-5K files) | Meaningful reduction on multi-file changes |
| Small project (<200 files) | Little benefit: graph overhead can exceed savings |

> **Quality angle:** scoping the agent to the blast radius reduces noise, which tends to
> improve review focus. Measure on your own repo rather than relying on a fixed multiplier.

## Bootstrap Protocol (Opt-In)

When planning or reviewing on a mid-to-large project, check whether graph analysis is
available before relying on it:

1. Check if the tool is installed: `Get-Command code-review-graph` (Windows) or
   `command -v code-review-graph` (macOS/Linux).
2. Check if a `.code-review-graph/` directory exists in the workspace.
3. If installed but the index is missing, get the user's confirmation before running
   `code-review-graph build` (it scans the whole project).
4. If not installed and the project is large, propose installing it
   (`pipx install code-review-graph`) and building a local map. Installing packages is the
   user's call: never install or build without confirmation.

For steps 3–4 follow the shared question protocol; as a subagent, return the question to the
caller instead of asking the user.
5. If the user declines, or Python/pip is unavailable, continue without the graph and say so.

## When to Use vs When to Skip

### Install It If

- Codebase is **500+ files**
- You make **multi-file changes** with cross-module dependencies
- Token costs are a real concern for the team
- You work with **monorepos**, microservices, or cross-package TypeScript
- You want **better review focus** in addition to cost savings

### Skip It If

- Codebase is **under ~200 files** with isolated single-file changes
- Heavy use of **dynamic patterns** (reflection, runtime code gen, dynamic imports)
- You want **zero maintenance**: the graph needs to stay in sync

### Evaluate First If

- Codebase is **200-500 files**: benchmark before committing
- Mix of **static and dynamic patterns**: test on representative commits

## How It Works (4 Layers)

```text
Layer 1: PARSE    → Tree-sitter builds ASTs from 19 languages
Layer 2: STORE    → Nodes + edges saved in SQLite graph
Layer 3: TRACE    → BFS computes blast radius of changes
Layer 4: SERVE    → MCP exposes graph to the agent
```

### What the Graph Contains

- **Nodes:** files, functions, methods, classes, imports, tests
- **Edges:** "A calls B", "X imports Y", "TestZ covers FunctionW", "ClassA extends ClassB"
- **Metadata:** name, type, file path, line range per node
- **Privacy:** structural metadata only, NO source code content in the graph

### Supported Languages (19)

Python, TypeScript, JavaScript, Go, Rust, Java, C#, Ruby, Kotlin, Swift, PHP, C/C++, Vue SFC,
Solidity, Dart, R, Perl, Lua, Jupyter/Databricks notebooks.

## References

| Reference | When to read |
| --- | --- |
| [installation](references/installation.md) | The user agreed to install: setup, MCP client configuration, ignore file, multi-repo |
| [workflows](references/workflows.md) | Blast radius, risk scoring, dead code, rename preview, visualization, limits, alternatives |

## Integration with REDEVKIT

| Skill / phase | How the graph complements it |
| --- | --- |
| `{{SKILL:context-compression}}` | The graph reduces input context; compression reduces carried-over history |
| `{{SKILL:redevkit-orchestrate}}` | Workers can be dispatched with precise file lists |
| `{{CMD:redevkit-verify}}` | After a graph-informed review, verify the changes by running them |
| `{{SKILL:batch-operations}}` | The blast radius tells which files a batch must touch |

Recommended session shape:

```text
1. Start a fresh session for each distinct task
2. Graph pre-filters context → the agent reads only the blast radius
3. Context compression summarizes completed phases
4. Memory (.redevkit/memory/) keeps key decisions for the next session
5. Result: fewer tokens, sharper reviews
```

## Best Practices

1. **Run watch mode** in development: stale graphs produce stale context
2. **Exclude generated files**: they inflate the graph with noise
3. **Benchmark first**: measure token usage with and without the graph
4. **Combine with output constraints**: the graph reduces input, concise prompts reduce output
5. **Use `.code-review-graphignore`** for build artifacts, `node_modules`, `dist/`
6. **Keep sessions short**: fresh sessions + graph = best token efficiency
7. **Register multiple repos** for microservice architectures
