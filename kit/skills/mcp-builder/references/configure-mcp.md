# Configure MCP Servers in Claude Code and Codex

How to register an MCP server for a project in both targets. REDEVKIT does not ship or sync any
MCP configuration: each runtime keeps its own, and you add servers explicitly with the commands
below. Adding a server that runs code or reaches the network is a security decision; show the
user the exact entry before writing it.

## Rules for Both Targets

- Never commit real secrets. Reference environment variables instead of literal tokens.
- Prefer project scope only for servers the whole team needs; personal servers go in user scope.
- After adding a server, check that it starts (see "Verify" in each section) and report the
  observed result.
- Options of the CLI come **before** the server name; everything after `--` is the server's own
  command line, passed through untouched.

## Claude Code

### Scopes

| Scope | Loads in | Stored in |
| --- | --- | --- |
| `local` (default) | Current project, only you | `~/.claude.json` (under the project path) |
| `project` | Current project, shared through version control | `.mcp.json` at the project root |
| `user` | All your projects | `~/.claude.json` |

### CLI

```bash
# stdio server (local process)
claude mcp add --transport stdio <name> -- <command> [args...]

# stdio server with environment variables (keep another option between --env and the name)
claude mcp add --env API_KEY=value --transport stdio <name> -- npx -y <package>

# Streamable HTTP server
claude mcp add --transport http <name> <url>

# shared with the team: writes .mcp.json
claude mcp add --transport http <name> --scope project <url>

# manage
claude mcp list
claude mcp get <name>
claude mcp remove <name>
```

`claude mcp add-json <name> '<json>'` adds a server from a JSON definition.

### Project `.mcp.json`

```json
{
  "mcpServers": {
    "local-tool": {
      "command": "npx",
      "args": ["-y", "some-mcp-package"],
      "env": {
        "SOME_TOKEN": "${SOME_TOKEN}"
      }
    },
    "remote-tool": {
      "type": "http",
      "url": "https://example.com/mcp",
      "headers": {
        "Authorization": "Bearer ${REMOTE_TOOL_TOKEN}"
      }
    }
  }
}
```

- `${VAR}` expands an environment variable; `${VAR:-default}` supplies a fallback. Expansion
  works in `command`, `args`, `env`, `url` and `headers`.
- Claude Code asks for approval before using project-scoped servers from `.mcp.json`;
  `claude mcp reset-project-choices` resets those choices.

### Verify

Run `claude mcp list` or open `/mcp` inside a session to see the server status and tool count.

## Codex

### Location

| File | Applies to |
| --- | --- |
| `~/.codex/config.toml` | All projects for this user |
| `.codex/config.toml` in the project | This project, only when the project is trusted |

Each server is a table named `[mcp_servers.<name>]`.

### stdio server

```toml
[mcp_servers.local-tool]
command = "npx"                        # required
args = ["-y", "some-mcp-package"]
env_vars = ["SOME_TOKEN"]              # forward these variables from your environment
# cwd = "path/to/start/in"            # optional working directory

[mcp_servers.local-tool.env]           # literal values, never secrets
LOG_LEVEL = "info"
```

### Streamable HTTP server

```toml
[mcp_servers.remote-tool]
url = "https://example.com/mcp"                 # required
bearer_token_env_var = "REMOTE_TOOL_TOKEN"     # sent as the Authorization bearer token
```

`http_headers` (static values) and `env_http_headers` (header name to variable name) are also
available.

### Common options

| Key | Meaning |
| --- | --- |
| `startup_timeout_sec` | Seconds allowed for the server to start (default 10) |
| `tool_timeout_sec` | Seconds allowed for one tool call (default 60) |
| `enabled = false` | Turn the server off without deleting the entry |

### CLI

```bash
codex mcp add <name> --env VAR1=VALUE1 -- <stdio server command>
codex mcp list
```

### Verify

Run `codex mcp list`, then start a session and confirm the server's tools are available.

## Example: context7 (no API key)

context7 serves up-to-date library documentation. It works without an API key; a key only
raises rate limits and, if used, must come from an environment variable, never from a
committed file.

Claude Code:

```bash
claude mcp add --transport stdio context7 -- npx -y @upstash/context7-mcp
```

Or, shared with the team in `.mcp.json`:

```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp"]
    }
  }
}
```

Codex:

```bash
codex mcp add context7 -- npx -y @upstash/context7-mcp
```

Or in `~/.codex/config.toml` (or the trusted project's `.codex/config.toml`):

```toml
[mcp_servers.context7]
command = "npx"
args = ["-y", "@upstash/context7-mcp"]
```

Requires Node.js with `npx` on the `PATH`. If `npx` does not start on native Windows, try
wrapping the command as `cmd /c npx -y @upstash/context7-mcp`.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Server never starts | Run the command after `--` by hand in a terminal; read its stderr |
| Starts but no tools | Timeout too short (`startup_timeout_sec` in Codex); server crashed after start |
| Project server ignored in Codex | The project is not trusted, so `.codex/config.toml` is not applied |
| Project server ignored in Claude Code | Approval was declined; run `claude mcp reset-project-choices` |
| Auth errors on HTTP | Variable named in `bearer_token_env_var` or `${VAR}` is unset in the shell that launched the CLI |
