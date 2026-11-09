---
name: context-compression
description: Compress long-session context: summarize finished phases, keep decisions and file refs.
---

# Context Compression — Long Session Management

> Keep sessions productive by compressing completed work while preserving key decisions.

## Overview

Long sessions (30+ turns) cause context degradation — the AI loses track of earlier work, repeats itself, or forgets decisions. Context compression proactively summarizes completed phases so the context window stays focused on active work.

**Token impact:** replacing verbose tool output with short semantic summaries can recover thousands of tokens in a long session (measure, do not assume).

---

## When to Compress

| Signal | Action |
|---|---|
| Session has 20+ turns | Consider proactive compression |
| Agent repeats earlier suggestions | Context is saturated — compress now |
| User says "we already discussed this" | Compress immediately |
| Switching to a new phase of work | Compress the completed phase |
| Large tool output (500+ lines) | Micro-compact the output |

---

## Compression Levels

### Level 1: Micro-Compact (Tool Output)

Compress individual tool outputs while retaining semantic content:

```text
❌ Before (raw grep output — 200 lines, ~4,000 tokens):
src/auth/jwt.ts:15: import { verify } from 'jsonwebtoken'
src/auth/jwt.ts:23: export function validateToken(token: string) {
src/auth/jwt.ts:24:   try {
src/auth/jwt.ts:25:     const decoded = verify(token, SECRET)
... (195 more lines)

✅ After (micro-compact — 5 lines, ~100 tokens):
Grep results for "jwt": Found 8 files, 42 matches.
Key files: src/auth/jwt.ts (main JWT logic), src/middleware/auth.ts (middleware),
src/api/login.ts (token creation). Token validation at jwt.ts:23-40.
Error handling at jwt.ts:42-55. Secret loaded from env at jwt.ts:8.
```

### Level 2: Phase Summary

Replace a completed work phase with a summary:

```text
❌ Before (full research transcript — ~3,000 tokens):
[turn 1] Read package.json...
[turn 2] Read src/index.ts...
[turn 3] Grep for "auth"...
[turn 4] Found 8 files related to auth...
[turn 5] Read src/auth/jwt.ts...
... (10 more turns of exploration)

✅ After (phase summary — ~200 tokens):
## Research Phase Complete
- Project: Next.js 15 app with JWT auth
- Auth files: 8 files in src/auth/, src/middleware/, src/api/
- Token flow: login → create JWT → store in httpOnly cookie → validate in middleware
- Bug location: src/auth/jwt.ts:45 — expiry check uses `<` instead of `<=`
- Decision: Fix the comparison operator, add edge case test
```

### Level 3: Session Checkpoint

Full session summary for long-running work:

```markdown
## Session Checkpoint (Turn 35)

### Completed
- [x] Researched auth system (8 files, JWT flow mapped)
- [x] Fixed token expiry bug in jwt.ts:45
- [x] Added edge case test in jwt.test.ts
- [x] Verified: `npm test -- auth` → exit 0, 42 passed, 0 failed (HEAD a1b2c3d, tree clean)

### In Progress
- [ ] Update API documentation
- [ ] Review related middleware

### Key Decisions
1. Keep httpOnly cookies (not localStorage) for token storage
2. Use `<=` for expiry check to include exact-moment expiry
3. Add 5-minute grace period for clock skew

### Files Modified
- src/auth/jwt.ts (line 45: comparison fix)
- tests/auth/jwt.test.ts (added 3 edge case tests)

### Open Problems (keep the evidence)
- Middleware test fails: `npm test -- middleware` → exit 1 at HEAD a1b2c3d; paste the full stack trace here, verbatim
```

Every checkpoint keeps the evidence: each verification claim records the command, the observed
result and HEAD (`git rev-parse --short HEAD`). Never compress away the failing stack trace of
a problem that is still open.

---

## Compression Protocol

### Step 1: Identify Completed Phases

```text
What work is DONE and won't be revisited?
→ Research findings already synthesized
→ Implementation already verified
→ Decisions already made and applied
```

### Step 2: Extract Key Information

```text
From the completed phase, preserve:
✅ Decisions made and WHY
✅ File paths and line numbers of changes
✅ Key findings that inform ongoing work
✅ Evidence: each command run, its observed result and HEAD
✅ The full failing stack trace of any problem still open

Discard:
❌ Step-by-step tool invocation details
❌ Full file contents that were read
❌ Exploratory dead-ends that didn't lead anywhere
❌ Stack traces of problems already fixed and verified (keep the message only)
```

### Step 3: Write Summary

```text
Use the Phase Summary format above.
Keep to 100-300 tokens per completed phase.
Include enough detail to resume work without re-reading.
```

---

## Best Practices

1. **Compress phases, not facts** — Individual decisions should stay, full transcripts should go
2. **Preserve "why" over "what"** — Why a decision was made matters more than the exact commands run
3. **Never auto-compress** — Always tell the user "I'm summarizing the completed research phase to keep context focused"
4. **Keep file references** — Always preserve file paths and line numbers in summaries
5. **Checkpoint on phase transitions** — Natural compression point when switching from research to implementation
6. **Persist what must survive the session** — Decisions and progress that matter beyond this
   session go to `.redevkit/memory/` through `{{SKILL:redevkit-memanager}}` (save), not only into a
   chat summary. Feature progress lives in `specs/NNN-short-name/tasks.md`.
