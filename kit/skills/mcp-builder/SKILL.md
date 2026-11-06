---
name: mcp-builder
description: Build and review MCP servers and clients against the current MCP spec; register MCP servers in Claude Code and Codex.
---

# MCP Builder

> Build interoperable Model Context Protocol (MCP) implementations against the current
> specification. Treat extensions as negotiated, opt-in capabilities, never as core guarantees.

## When to Read What

| Need | Read |
| --- | --- |
| Build or review an MCP server or client | This file |
| Upgrade an implementation from `2025-11-25` or earlier | [spec-migration](references/spec-migration.md) |
| Register an MCP server in Claude Code or Codex (e.g. context7) | [configure-mcp](references/configure-mcp.md) |

## 1. Baseline

- The specification lives at `https://modelcontextprotocol.io/specification`. At the time of
  writing the current revision is **`2026-07-28`**. Check the versioning page before relying on
  version-specific details, and say which revision your implementation targets.
- Protocol versions are `YYYY-MM-DD` strings. Peers MAY support several versions at once.
- Where this skill and the official spec disagree, the spec wins. Do not invent protocol
  methods, fields or error codes; look them up in the spec or the official `schema.ts`.

### Core versus extensions

| Layer | Status | Engineering rule |
| --- | --- | --- |
| Base protocol (JSON-RPC 2.0 messages, `_meta`, versioning, errors) | Core | Required for every implementation |
| Server features: tools, resources, prompts | Core, optional per server | Declare the capability; clients check it before use |
| Client feature: elicitation | Core, optional per client | Check the client capability before requesting input |
| Roots, sampling, logging | Deprecated in `2026-07-28` | Do not build new designs on them |
| Tasks, Skills over MCP, MCP Apps | Extensions | Opt-in; both peers must support and negotiate them |
| Draft or vendor extensions | Experimental | Isolate behind adapters and feature flags |

Never label an extension as stable because one SDK or host supports it. Check its own status.

## 2. Architecture

MCP uses JSON-RPC 2.0 messages between **hosts** (LLM applications), **clients** (connectors
inside the host) and **servers** (services that provide context and capabilities).

```text
host application
  └─ MCP client
       ├─ stdio transport            (local subprocess)
       └─ Streamable HTTP transport  (remote or shared service)
            └─ MCP server
                 ├─ tools      (functions the model can call)
                 ├─ resources  (context and data, addressed by URI)
                 └─ prompts    (user-facing message templates)
```

### Stateless request model (`2026-07-28`)

- There is no `initialize` handshake and no protocol-level session. Every request carries its
  protocol version and client capabilities in `_meta`
  (`io.modelcontextprotocol/protocolVersion`, `io.modelcontextprotocol/clientCapabilities`).
- A server rejects an unsupported version with `UnsupportedProtocolVersionError`, listing the
  versions it supports; the client may retry with a mutually supported one.
- Servers MUST implement `server/discover` (supported versions, capabilities, identity).
  Clients MAY call it first, or send requests directly and handle a version error.
- State that must span calls (a cart, a browser context, a transaction) uses an explicit,
  server-minted handle returned by one tool and passed as an argument to the next.

Do:

- validate every request on its own; tolerate interleaved requests from unrelated tasks;
- validate authorization against a handle on every call (a handle is a name, not a
  credential); make handles opaque, give them a stated lifetime and return a tool error
  when one has expired;
- return `tools/list` in a deterministic order.

Do not:

- treat a stdio process or HTTP connection as a session boundary;
- vary `tools/list` per connection (it MAY vary by the authorization on the request);
- use self-reported client or server info for authorization decisions.

## 3. Transports

| Transport | Typical use | Baseline |
| --- | --- | --- |
| stdio | Local subprocess launched by the host | stdout carries only MCP messages; log to stderr; read credentials from the environment |
| Streamable HTTP | Remote or shared service | Use the MCP HTTP authorization framework; validate `Origin`; enforce network boundaries |

- The older HTTP+SSE transport is deprecated; migrate to Streamable HTTP.
- WebSocket is not a standard MCP transport.
- Transport concerns must not leak into protocol semantics: a reconnect must not destroy
  state that lives behind an explicit handle.

## 4. Tools, Resources and Prompts

### Tools

- One responsibility per tool; clear action names. Names SHOULD be 1-128 characters from
  `A-Z a-z 0-9 _ - .`, case-sensitive and unique within the server.
- `inputSchema` is a JSON Schema object with `type: "object"` at the root. JSON Schema
  2020-12 is the default dialect when `$schema` is absent. For a tool without parameters use
  `{ "type": "object", "additionalProperties": false }`.
- Describe every property, declare `required`, and prefer enums, bounds and formats.
- Use `outputSchema` plus `structuredContent` when consumers need typed results; also return
  the serialized JSON in a text block for older clients.
- Errors: unknown tool or malformed request is a JSON-RPC protocol error; API failures,
  validation and business-rule errors are tool results with `isError: true` and an actionable
  message the model can use to retry.
- Annotations (read-only, destructive, idempotent, open-world) are hints. Clients MUST treat
  them as untrusted unless the server is trusted.
- Servers MUST validate inputs, enforce access control, rate-limit calls and sanitize outputs.

### Resources

- Stable URIs and correct MIME types; authorize per resource, not only per connection.
- Separate listing metadata from content; paginate large lists.
- Never forward resource data to another server or model without user consent.

### Prompts

- Prompts are user-visible templates, not hidden authority.
- Keep permissions and policy enforcement in code, never in prompt text.
- Validate prompt arguments and identify any data sources included in generated messages.

## 5. Schema and Validator Safety

- Follow the spec's `$ref` resolution requirements when validating against `inputSchema` and
  `outputSchema`.
- Engineering default: do not dereference network `$ref` values automatically. If remote
  resolution is ever enabled, use a host allowlist, reject loopback/link-local/private
  addresses, and apply timeouts and response-size limits.
- Reject schemas with unresolved references instead of treating them as permissive.
- Bound schema depth, subschema count and validation time (composition keywords and recursive
  references can be used for denial of service).

## 6. Security Requirements

1. **Consent:** hosts obtain explicit user consent before invoking a tool or exposing user data;
   keep a human able to deny tool calls.
2. **Untrusted metadata:** tool descriptions, annotations, client/server info and
   model-produced arguments are never authorization evidence.
3. **Validation:** validate schemas, arguments, structured results, URIs and content types at
   every trust boundary.
4. **Secrets:** load credentials from the environment or a secret manager; never put real keys
   in repository config, logs, prompts or error payloads.
5. **Network:** defend remote fetches against SSRF, redirect abuse, oversized and slow
   responses.
6. **Isolation:** sandbox subprocesses and filesystem access; reject archive and symlink
   escapes.
7. **Audit:** log security-relevant decisions and tool identity without storing sensitive
   payloads.

## 7. Testing Matrix

| Test | Expected evidence |
| --- | --- |
| Contract | Invalid JSON-RPC, missing `_meta`, unsupported version, unknown tool |
| Statelessness | Interleaved requests, reconnects, handle reuse and expiry |
| Schema safety | External `$ref`, deep or recursive schemas, size and time limits |
| Authorization | Denied tool/resource access, consent gates, credential isolation |
| Extensions | Extension absent, version mismatch, graceful fallback |
| Compatibility | Current peer plus each older revision you claim to support |
| Failure handling | Timeouts, cancellation, `isError` results, no secret leakage |

Write these tests first (TDD is the REDEVKIT default, see `{{SKILL:tdd-workflow}}`). The
official MCP Inspector is useful for manual checks; it does not replace automated tests.

## 8. Review Checklist

- [ ] Target protocol revision and the status of every extension used are documented.
- [ ] Requests are self-contained; cross-call state uses explicit handles.
- [ ] Capabilities are declared and checked before optional features.
- [ ] Tool names, schemas, `outputSchema` and error semantics follow the spec.
- [ ] Network `$ref` resolution is off by default and validation is bounded.
- [ ] Annotations are not trusted for authorization; consent happens outside prompts.
- [ ] Secrets come from the environment; nothing sensitive in config, logs or errors.
- [ ] No new design depends on roots, sampling, logging or HTTP+SSE.
- [ ] Contract, security, extension and cross-version tests pass (show the run).
