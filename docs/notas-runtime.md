# Notas de runtime (reconfirmações RC1–RC5)

Itens que o PLANO (§16) mandou reconfirmar durante a implementação. Datas e versões são as
da verificação.

| ID | Item | Resultado (2026-11-06) | Efeito no REDEVKIT |
| --- | --- | --- | --- |
| RC1 | Orçamento total do catálogo de skills no Claude Code | A listagem de skills cabe em 1% da janela de contexto, com fallback de 8.000 caracteres (`SLASH_COMMAND_TOOL_CHAR_BUDGET` ou `skillListingBudgetFraction` mudam isso). Quando estoura, todos os nomes continuam listados e as descrições das skills menos usadas são descartadas. | O validador mantém o limite de 12.000 do plano e avisa acima de 8.000. As skills finas de persona usam uma descrição curta (o subagente já aparece na ferramenta Agent) e as fases têm descrições curtas. Total atual: abaixo de 8.000 nos dois alvos. |
| RC2 | Chaves TOML do Codex | Confirmadas no Codex CLI 0.162.1: a feature `default_mode_request_user_input` (estado "under development") e `SkillsConfig.max_context_tokens` (`[skills]`). | `kit/runtime/codex-config.toml` usa exatamente essas chaves. |
| RC3 | O Codex descobre `SKILL.md` aninhado? | Irrelevante depois da D46: o kit não tem `SKILL.md` aninhado. | O validador (e o `doctor`) falham se houver `SKILL.md` aninhado em `.claude/skills` ou `.agents/skills`. |
| RC4 | Subagente do Claude pré-carrega skill com `user-invocable: false`? | Não documentado. A documentação diz que só `disable-model-invocation: true` impede o pré-carregamento, porque o pré-carregamento usa o mesmo conjunto de skills que o modelo pode invocar; `user-invocable: false` só esconde do menu `/`. | Personas pré-carregam fases (`redevkit-orchestrate`, `redevkit-tasks` etc.). Nenhuma persona pré-carrega o `redevkit-deploy` (o validador impede). Os corpos das personas também citam o caminho da skill para leitura sob demanda, então o comportamento não depende só do pré-carregamento. |
| RC5 | O Codex substitui `$ARGUMENTS`? | Não há substituição documentada; o parser lê só `name`, `description` e `metadata.short-description`. | O render usa a frase "the request the user wrote alongside this skill invocation" no Codex. |

Outros fatos confirmados na mesma verificação (documentação do Claude Code):

- Regras de permissão: a forma atual é `Bash(npm test *)`; `Bash(npm test:*)` é equivalente. O
  REDEVKIT grava a forma com espaço.
- `skills` (subagente) e `paths` (skill) aceitam lista YAML; o render grava listas.
- `@imports` dentro do `AGENTS.md` importado pelo `CLAUDE.md` são expandidos (até 4 saltos).
- Comentários HTML de bloco são removidos antes de o conteúdo entrar no contexto, então os
  marcadores `<!-- REDEVKIT:BEGIN/END -->` não custam contexto.
