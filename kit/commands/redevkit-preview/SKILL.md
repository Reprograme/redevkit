---
name: redevkit-preview
description: Start, stop, restart or check the local dev server in the background with an HTTP health check.
short-description: Manage the local preview server
argument-hint: "[start|stop|status|restart] [port]"
---

# redevkit-preview

**Input:** {{ARGS}}

Sub-command: `start`, `stop`, `status` or `restart`; default `status`. Optional port. Answer
the user in the user's language.

## Purpose

Run the application locally for the user to see (D30), using only the runtime's native
tools: detect the dev command and port, start the server in the background, check it over
HTTP and report the URL. The preview state is ephemeral: this command never writes memory.

## Preconditions

- The project has something runnable (a dev script, a framework entry point or a static
  `index.html`). If not, say so and stop.
- `.redevkit/tmp/` exists (create it if missing; it is ignored by git). Log:
  `.redevkit/tmp/preview.log`. Process id, when known: `.redevkit/tmp/preview.pid`.

## Memory phase 1

Recall per `{{SKILL:redevkit-memanager}}`: `MEMORY.md` and `tech.md` (dev command, preview
port). Print `📖 Memory loaded. Last entry: YYYY-MM-DD.` Read-only: no memory write follows.

## Questions

Ask only when something blocks the start, one question at a time, at most 3 options with the
recommended one first and marked "(Recommended)", at most 5 questions in this run. In
non-interactive runs adopt the recommendation and report it, except at gates.

{{ASK}}

## Steps

### 1. Detect the command and port

Follow [detection](references/detection.md): `tech.md`, then `package.json` scripts, then
framework conventions, then ask. A port given in the input wins.

### 2. start

#### Port check

If the port already answers and `.redevkit/tmp/preview.pid` points to a live process, the
preview is already running: report it (as in `status`) and stop. If another process holds the
port, ask: start on the next free port (Recommended), stop the other process (G4, it was not
started by this command) or give another port.

#### Start in the background

Output always goes to `.redevkit/tmp/preview.log`.

{{#claude}}
Run the dev command with the Bash tool and `run_in_background: true`, redirecting the output:
`<command> > .redevkit/tmp/preview.log 2>&1`. Keep the background task id for `stop` in this
session.
{{/claude}}

{{#codex}}
Use the background form of the current OS and write the process id to
`.redevkit/tmp/preview.pid`.

Windows (PowerShell):

```powershell
New-Item -ItemType Directory -Force .redevkit/tmp | Out-Null
$p = Start-Process -FilePath cmd.exe -ArgumentList '/c', '<command> > .redevkit\tmp\preview.log 2>&1' -WindowStyle Hidden -PassThru
$p.Id | Set-Content .redevkit/tmp/preview.pid
```

macOS and Linux:

```bash
mkdir -p .redevkit/tmp
nohup sh -c '<command>' > .redevkit/tmp/preview.log 2>&1 &
echo $! > .redevkit/tmp/preview.pid
```

If the sandbox blocks background processes or local network access, ask the user to approve
the command.
{{/codex}}

#### Health check and report

Poll every 2 seconds for up to 60 seconds:
`curl -s -o /dev/null -w "%{http_code}" http://localhost:<port>/` (on Windows PowerShell use
`curl.exe` and `-o NUL`). Healthy = any HTTP status below 500.

Report the URL (`http://localhost:<port>`), the framework, the log path and how to stop it.
Unhealthy: show the last 30 lines of the log and stop the process you started.

### 3. status (read-only)

Check, without starting or stopping anything:

- Port listening — Windows: `Get-NetTCPConnection -LocalPort <port> -State Listen`;
  macOS and Linux: `lsof -nP -iTCP:<port> -sTCP:LISTEN`.
- The process in `.redevkit/tmp/preview.pid` (or the background task of this session) alive.
- HTTP health as in start.

Report running/stopped, URL, health, process id. Never claim a server is running without
these checks.

### 4. stop

{{#claude}}
Stop the background task started in this session with the runtime's tool for stopping
background tasks. If no such task is known, stop by process id or port as below.
{{/claude}}

Stop the process tree recorded in `.redevkit/tmp/preview.pid` — Windows:
`taskkill /PID <pid> /T /F`; macOS and Linux: `pkill -TERM -P <pid>; kill <pid>`. Then
confirm the port is free and delete the pid file. Stopping a process this command did not
start (found only by port) needs explicit confirmation (G4).

### 5. restart

`stop`, then `start` with the same command and port.

## Gates that apply

| Gate | Where |
| --- | --- |
| G4 | Stopping a process that this command did not start |

## Artifacts

`.redevkit/tmp/preview.log` and `.redevkit/tmp/preview.pid` (ephemeral, ignored by git). No
report, no memory.

## Memory phase 3

None. The preview never writes memory. If the detected dev command or port is missing from
`tech.md`, suggest saving it with `{{SKILL:redevkit-memanager}}` (the user decides).

## Evidence rule

"Running" and "healthy" are claimed only after the port check and an HTTP status were
observed; quote the status code. A failed start shows the log lines that explain it.

## Handoff

- Preview healthy → the user checks the app; to prove the flows, `{{CMD:redevkit-verify}}`.
- Start failed → `{{CMD:redevkit-debug}}` with the log excerpt.
- The preview is not part of the `--auto` chain.
