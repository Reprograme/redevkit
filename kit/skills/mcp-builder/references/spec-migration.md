# MCP Spec Migration (to `2026-07-28`)

Changes since revision `2025-11-25`, as listed in the official changelog
(`https://modelcontextprotocol.io/specification/2026-07-28/changelog`). Re-check the changelog
before a migration: this summary is a starting point, not the normative text.

## Major Changes

| Area | Before | Now |
| --- | --- | --- |
| Handshake | `initialize` / `notifications/initialized` | Removed; protocol version and client capabilities in every request's `_meta` |
| Sessions | `Mcp-Session-Id` header on Streamable HTTP | Removed; cross-call state uses explicit server-minted handles |
| Discovery | Implicit in the handshake | `server/discover` (servers MUST implement it) |
| Change notifications | HTTP GET stream, `resources/subscribe` / `unsubscribe` | `subscriptions/listen`, a long-lived POST response stream with opt-in types |
| Server-initiated requests | `roots/list`, `sampling/createMessage`, `elicitation/create` sent by the server | Multi round-trip requests: the server returns `resultType: "input_required"` with `inputRequests`; the client retries with `inputResponses` |
| Result envelope | No result type | Every result carries `resultType` (`"complete"` or `"input_required"`) |
| Removed methods | `ping`, `logging/setLevel`, `notifications/roots/list_changed` | Log level per request via `_meta` (`io.modelcontextprotocol/logLevel`) |
| Tasks | Experimental core feature | Official extension `io.modelcontextprotocol/tasks` (polling via `tasks/get`, input via `tasks/update`) |
| Stream resumability | `Last-Event-ID` redelivery | Removed; a broken stream loses the in-flight request, which is re-issued with a new ID |

## Minor Changes Worth Checking

- Resource-not-found error code changed from `-32002` to `-32602` (Invalid Params).
- `inputSchema` / `outputSchema` accept any JSON Schema 2020-12 keyword; `structuredContent`
  may be any JSON value; `$ref` resolution requirements and composition bounds were added.
- List and read results carry `ttlMs` and `cacheScope` caching hints.
- Streamable HTTP POST requests carry `Mcp-Method` and `Mcp-Name` headers; tool parameters
  can be mirrored to headers with `x-mcp-header` (never for secrets).
- Error codes `-32020` to `-32099` are reserved for the spec; `-32000` to `-32019` stay
  implementation-defined.
- Servers SHOULD return `tools/list` in a deterministic order.

## Deprecated (still functional, scheduled for removal)

| Feature | Migration path |
| --- | --- |
| Roots | Pass directories or files via tool parameters, resource URIs or server configuration |
| Sampling | Integrate directly with LLM provider APIs |
| Logging | Log to stderr on stdio; use OpenTelemetry for observability |
| HTTP+SSE transport | Streamable HTTP |
| Dynamic Client Registration | Client ID Metadata Documents |
| `includeContext: "thisServer"` / `"allServers"` | Omit the field or use `"none"` |

## Migration Checklist

- [ ] Replace the `initialize` handshake and connection-scoped sessions with per-request `_meta`.
- [ ] Implement `server/discover`; handle `UnsupportedProtocolVersionError` on the client.
- [ ] Move durable state behind explicit handles passed as tool arguments.
- [ ] Replace server-initiated requests with the multi round-trip (`input_required`) pattern.
- [ ] Emit `resultType` on every result; treat a missing `resultType` from older servers as
      `"complete"`.
- [ ] Emit `-32602` for resource-not-found; tolerate `-32002` from older peers.
- [ ] Move Tasks usage to the negotiated Tasks extension.
- [ ] Plan the exit from roots, sampling, logging and HTTP+SSE.
- [ ] Bound schema validation and keep network `$ref` resolution off by default.
- [ ] Add interoperability tests against one older peer and one `2026-07-28` peer.
- [ ] To keep talking to handshake-based peers (`2025-11-25` and earlier), follow the spec's
      "Backward Compatibility" section in the versioning page.
