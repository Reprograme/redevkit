## Memory protocol

- Facts about this project must be written to `.redevkit/memory`, even if native memory has them.
- `active.md`: state, events, next steps, test results. `changelog.md`: releases, ADRs.
- Skills name `active.md` sections in English; pt-BR files use the translated headings: Active
  feature = Feature ativa, Where we are = Onde estamos, Recent events = Eventos recentes, What
  works = O que funciona, What's left = O que falta, Next steps = Próximos passos, Known issues
  = Problemas conhecidos, Last results = Últimos resultados, Workflow preferences =
  Preferências de fluxo. Line labels stay in English in every language: `- Feature:`,
  `- Plan approved:`, `- Test:`, `- Verify:`, `- Debug:`, `- Verify pending:`,
  `- Correction cycle:`, `- Bug <slug>:`.
- `project.md`: scope, out of scope. `system.md`: architecture, conventions, invariants.
- `tech.md`: stack, commands, preview port. `user.md`: environment, style, feedback.
- Other themes: `topics/<topic>.md`, plus one `MEMORY.md` line `- [type] summary → file.md`.
- Ask first: constitution amendments, invariant changes, any deletion.
- Never write: secrets, ephemeral logs, code, API surface, absolute paths, derivable facts, transcripts.
- After writing, end with `💾 Memory updated (files).`
- Native memory stays on; on conflict `.redevkit/memory` wins. Details: `{{SKILL:redevkit-memanager}}`.
