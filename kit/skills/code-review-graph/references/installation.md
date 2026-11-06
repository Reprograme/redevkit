# code-review-graph: Installation and Configuration

> Optional external tool. Install only with the user's explicit consent.

## Installation

### Prerequisites

- Python 3.9+ (`python3 --version`)
- pip or pipx installed
- An MCP-capable client (Claude Code or Codex)
- Git-tracked codebase (for incremental updates)

### Step 1: Install the Package

```bash
# Recommended: isolated environment
pipx install code-review-graph

# Alternative: fastest, no permanent install
uvx code-review-graph install

# Alternative: global pip
pip install code-review-graph
```

### Step 2: Configure MCP Client

```bash
# Auto-detect supported clients
code-review-graph install

# Or target Claude Code explicitly
code-review-graph install --platform claude-code
```

For Codex, check the tool's documentation for a Codex option. If there is none, register its
MCP server under `[mcp_servers]` in the Codex `config.toml`, using the server command the
tool documents. Do not guess the command.

> **Restart the client session** after this step. The MCP server activates on restart.

### Step 3: Build the Initial Graph

```bash
cd /your/project
code-review-graph build
```

| Codebase Size | Expected Build Time |
|---------------|---------------------|
| 500 files | 10–30 seconds |
| 5,000 files | 2–5 minutes |
| 27,000 files | 5–10 minutes |

### Step 4: Enable Watch Mode (Recommended)

```bash
# Keep graph current as you work
code-review-graph watch
```

Incremental updates complete in **under 2 seconds**. If you prefer manual updates:

```bash
code-review-graph update
```

### Step 5: Verify Integration

Open a new session and check the MCP connection. In Claude Code, run `/mcp` and confirm
`code-review-graph` appears. In Codex, confirm the server is configured and its tools are
available in a new session.

---

## Configuration

### Ignore File

Create `.code-review-graphignore` at project root (uses `.gitignore` syntax):

```text
# Build artifacts
dist/**
.next/**
build/**

# Dependencies
node_modules/**
vendor/**

# Generated files
generated/**
*.generated.ts
*.min.js

# Test fixtures (if large)
__fixtures__/**
```

> Excluding generated files and build artifacts is critical — they inflate the graph with meaningless nodes.

### Multi-Repo Setup

For microservice architectures:

```bash
# Register additional repos
code-review-graph register /path/to/other/repo

# List all registered repos
code-review-graph repos
```

The MCP server serves context across all registered repositories.
