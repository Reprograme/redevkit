## Memory protocol

- Session start: read `.redevkit/memory/MEMORY.md`, then `constitution.md`, then `active.md`.
- Facts about this project must be written to `.redevkit/memory`, even if native memory has them.
- `active.md`: state, events, next steps, test results. `changelog.md`: releases, ADRs.
- `project.md`: scope, out of scope. `system.md`: architecture, conventions, invariants.
- `tech.md`: stack, commands, preview port. `user.md`: environment, style, feedback.
- Other themes: `topics/<topic>.md`, plus one `MEMORY.md` line `- [type] summary → file.md`.
- Ask first: constitution amendments, invariant changes, any deletion.
- Never write: secrets, ephemeral logs, code, API surface, absolute paths, derivable facts, transcripts.
- After writing, end with `💾 Memory updated (files).`
- Native memory stays on; on conflict `.redevkit/memory` wins. Details: `{{SKILL:redevkit-memanager}}`.
