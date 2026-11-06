# code-review-graph: Workflows and Limits

## Core Workflows

### 1. Blast Radius Analysis (Primary Use)

This is automatic when the MCP server is active. Your AI assistant queries the graph before reading files, getting only the impacted files instead of everything.

```text
Illustrative:
Without graph:  Changed auth/middleware.ts → AI reads 200+ files → 8,200 tokens
With graph:     Changed auth/middleware.ts → Graph returns 12 impacted files → 1,000 tokens
```

### 2. Risk-Scored Change Analysis

```bash
code-review-graph detect-changes
```

Scores each uncommitted change by risk level:

- Number of dependents
- Test coverage gaps
- Whether changed functions are on critical paths
- High-risk changes flagged **before** you ask for review

### 3. Dead Code Detection

The graph finds nodes with **no incoming edges** — no callers, no importers, no test coverage:

```bash
# Surfaces functions/classes that are candidates for removal
# Useful on mature codebases to reduce cruft
```

### 4. Refactoring Preview

```bash
code-review-graph rename preview --from OldClassName --to NewClassName
```

Shows every file affected by a rename, and flags edge cases (dynamic string references that static analysis can't catch).

### 5. Architecture Visualization

```bash
code-review-graph visualize
```

Generates interactive visualization showing module clusters using community detection (Leiden algorithm). Useful for:

- Onboarding new contributors
- Identifying architectural drift
- Spotting overly-coupled modules

### 6. Wiki Generation

```bash
code-review-graph wiki
```

Generates markdown wiki of codebase structure — every module, its public API, dependencies, and test coverage.

---

## Known Limitations

| Limitation | Impact | Mitigation |
|-----------|--------|------------|
| **Dynamic imports** (`require(variable)`, `import(buildPath())`) | Dependencies invisible to parser | Manually note in `.code-review-graphignore` or accept over-prediction |
| **Reflection-based calls** (Django signals, `getattr()`, Java reflection) | Missed edges in graph | Serena (LSP-based) is better for these codebases |
| **Runtime-generated code** (`eval`, template engines) | Not parseable at static time | Accept limitation or exclude from graph |
| **Cross-language boundaries** (Python calling TypeScript API) | No edges between language runtimes | Use multi-repo registration as partial workaround |
| **Stale graph** (without watch mode) | The agent queries outdated relationships | Always run `code-review-graph update` before tasks, or use watch mode |
| **TypeScript path aliases** (`@/components/...`) | May require tsconfig resolution config | Check that the tool's tsconfig path resolution handles your setup |

---

## Alternatives Comparison

| Tool | Approach | Pros | Cons | Best For |
|------|----------|------|------|----------|
| **code-review-graph** | Tree-sitter + SQLite | Fast, 19 languages, local, no deps | Static analysis only | General use, large codebases |
| **Claudette** | Go rewrite | Single binary, no Python | Fewer languages, simpler | Python-averse teams |
| **Serena** | LSP-based | Deep semantic precision, type resolution | Heavy setup, slower | Polymorphism-heavy codebases |
| **code-graph-rag** | RAG + vector search | Natural language queries | Complex setup | Codebase exploration |
| **Native IDE context** | Editor built-in | Zero setup | No explicit blast radius | Simple projects |
