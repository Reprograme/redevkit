---
name: batch-operations
description: Apply one change across many files safely - preview, execute, verify. Use for renames, bulk edits and migrations.
---

# Batch Operations

> Apply consistent changes across many files at once. One pattern, many targets.

## When to Use

**Good for:**

- Renaming a function/component across all files that use it
- Adding an import to every file in a directory
- Updating version numbers across package files
- Applying the same code pattern to multiple similar files
- Migrating from one API to another across the codebase
- Adding/removing a field from all similar data structures

**Not for:**

- Single-file edits (edit directly)
- Unique changes per file (handle individually)
- Changes that need per-file judgment (split by domain and delegate, see below)

## Batch Operation Protocol

### Step 1: Define the Pattern

```text
What:     [exact text/pattern to find]
Replace:  [exact replacement text]
Scope:    [file glob pattern, e.g., "src/**/*.tsx"]
Exclude:  [files to skip, e.g., "**/*.test.tsx"]
```

### Step 2: Preview Before Executing

```bash
# Find all affected files FIRST
grep -rl "oldPattern" src/ --include="*.ts"

# Count matches
grep -rc "oldPattern" src/ --include="*.ts" | grep -v ":0$"

# Show context for each match
grep -rn "oldPattern" src/ --include="*.ts"
```

> **NEVER batch-modify without previewing first.** Show the user what will change. A batch
> that deletes code or touches many files outside the current feature is a destructive action
> (gate G4): stop and get explicit confirmation.

### Step 3: Execute the Batch

For text replacements:

```bash
# Linux/macOS (GNU sed; on macOS use: sed -i '' ...)
find src -name "*.ts" -exec sed -i 's/oldPattern/newPattern/g' {} +
```

```powershell
# Windows (PowerShell)
Get-ChildItem -Path src -Recurse -Filter *.ts |
  ForEach-Object { (Get-Content $_.FullName) -replace 'oldPattern','newPattern' | Set-Content $_.FullName }
```

For structural changes (adding imports, wrapping code):

- Use the editor tool on each file instead of regex
- Process files in a consistent order (alphabetical or by dependency)

### Step 4: Verify the Batch

```bash
# Confirm no missed instances (should return nothing)
grep -rl "oldPattern" src/ --include="*.ts"

# Confirm replacements are correct
grep -rn "newPattern" src/ --include="*.ts" | head -5

# Run tests and build to catch breakage
npm run test
npm run build
```

Report the commands you ran and their observed results. Never claim the batch is done without
that evidence.

## Splitting a Large Batch Across Subagents

Delegate only when the files split into **disjoint groups** (no file in two groups) and each
group needs judgment that a regex cannot provide. Otherwise run the batch yourself: one
mechanical pass is faster and easier to verify.

1. Run Step 1 and Step 2 yourself and list every affected file.
2. Partition the files into disjoint groups (by directory or domain). Never let two workers
   edit the same file.
3. Give each worker the exact pattern, its file list, the exclusions and the verify command.
4. Wait for every worker, then run Step 4 yourself over the whole scope. You own the synthesis
   and the final evidence.

{{#claude}}
Each group goes to a subagent through the Agent tool, one call per group, sent in the same
message so they run concurrently. Pick the persona that owns the domain, for example:
{{DELEGATE:frontend-specialist}}.
{{/claude}}
{{#codex}}
Each group goes to a subagent with `spawn_agent`, one per group, then wait for all of them
before verifying. Pick the persona that owns the domain, for example:
{{DELEGATE:frontend-specialist}}.
{{/codex}}

Subagents never ask the user: they return open questions to you, and you decide or ask.

## Common Batch Patterns

| Operation | Command pattern |
| --- | --- |
| **Rename import** | Find all `import { X }` → replace with `import { Y }` |
| **Update version** | Find `"version": "1.0"` → replace across all package.json |
| **Add export** | Append `export { X }` to all index files |
| **Remove deprecated** | Find `deprecatedFn()` → replace with `newFn()` |
| **Add header** | Prepend license header to all source files |
| **Type migration** | Find `interface X` → replace with `type X =` |

## Safety Rules

1. **Preview first** — always show affected files before modifying
2. **Git safety** — ensure a clean working tree (commit or stash first, with the user's consent)
3. **Exclude tests** — tests often need different treatment than source
4. **Verify after** — run build + tests after every batch operation
5. **Report changes** — list every file modified with a change summary

## Related Skills

| Need | Skill |
| --- | --- |
| Which files a change really affects (large repos, optional tool) | `{{SKILL:code-review-graph}}` |
| Multi-domain coordination | `{{SKILL:redevkit-orchestrate}}` |
