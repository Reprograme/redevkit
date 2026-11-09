---
type: verification
---

# Verificação: [NOME DA FEATURE]

- **Feature**: `specs/[NNN-nome-curto]/`
- **Entradas**: `spec.md`, `plan.md` (quando existe), `tasks.md`, `test-report.md` (mesmo diretório)

<!--
Somente acréscimo (append-only). Adicione uma seção "Execução" no fim deste arquivo a cada
rodada do verify. Nunca edite nem apague uma execução anterior. Mantenha estes tokens em
inglês: converged+verified, gaps, failed, PASS, FAIL, SKIPPED, clean, dirty.
-->

## Execução [AAAA-MM-DD HH:MM] — [converged+verified | gaps | failed]

### Estado do código

| Campo | Valor |
| --- | --- |
| Commit (HEAD) | `[SHA]` ou `n/a (não é um repositório git)` |
| Branch | `[BRANCH]` |
| Árvore de trabalho | clean / dirty |
| Arquivos alterados | [nenhum, ou a lista do `git status --porcelain`] |
| Impressão digital do status | `[HASH]` |
| Impressão digital do diff | `[HASH]` |

<!--
Mesmos comandos do relatório de testes: redevkit-test/references/code-state.md.
-->

### Evidência de testes

| Campo | Valor |
| --- | --- |
| Execução de testes | `test-report.md`, execução [AAAA-MM-DD HH:MM] — [PASS \| FAIL] |
| Origem | [executada no passo 1 \| reaproveitada: mesmo estado do código atual] |
| Debug desde o verify anterior | [slug do bug, AAAA-MM-DD HH:MM \| nenhum] |

<!--
Uma execução de testes FAIL encerra a verificação aqui: veredito failed, e as seções
Convergência, Evidência de execução e Auditorias ficam SKIPPED (test run FAIL).
-->

### Convergência

- **Resultado**: convergente / lacunas encontradas
- **Tarefas anexadas**: `Fase [N]: Convergência` no `tasks.md`, [T0NN–T0NN], ou nenhuma

| Lacuna | Origem (spec, plan ou tarefa) | Tarefa anexada |
| --- | --- | --- |
| [O QUE FALTA OU ESTÁ DIFERENTE] | [FR-00N, cenário 2 da US1, seção do plan, T0NN] | [T0NN] |

### Evidência de execução

| Etapa | Comando | Código de saída | Resultado observado |
| --- | --- | --- | --- |
| Build | `[COMANDO]` | [CÓDIGO DE SAÍDA] | [compilou sem erros, ou o erro] |
| Subida da aplicação | `[COMANDO]` | [CÓDIGO DE SAÍDA] | [ouvindo em URL, ou o erro], ou SKIPPED ([MOTIVO]) |

#### Fluxos críticos

| Fluxo | Passos | Esperado | Observado | Resultado |
| --- | --- | --- | --- | --- |
| [NOME DO FLUXO] | [requisição, caminho de cliques ou comando] | [ESPERADO] | [OBSERVADO] | PASS / FAIL / SKIPPED ([MOTIVO]) |

```text
[TRECHOS CURTOS DE SAÍDA QUE COMPROVAM OS RESULTADOS ACIMA]
```

### Auditorias

- **Executor**: `verify_all.py` / `checklist.py` / comandos do projeto (sem Python disponível)
- **Tipo de projeto**: [TIPO DE PROJETO]

| Auditoria | Comando | Resultado | Observações |
| --- | --- | --- | --- |
| [NOME DA AUDITORIA] | `[COMANDO]` | PASS / FAIL / SKIPPED ([MOTIVO]) | [RESUMO DOS ACHADOS] |

### Não verificado

- [O que não pôde ser exercitado e por quê, ou nada]

### Suposições

- [Suposição adotada nesta execução e o motivo, ou nenhuma]

### Veredito

**[converged+verified | gaps | failed]** — [uma ou duas frases com a evidência decisiva].

<!--
converged+verified: execução de testes PASS; nenhuma lacuna de convergência; build e fluxos
críticos passam; nenhuma auditoria com FAIL.
gaps: execução de testes PASS e a execução passa, mas a convergência ou auditorias não
críticas anexaram tarefas.
failed: a execução de testes é FAIL, ou o build, um fluxo crítico ou uma auditoria
bloqueante falha.
-->

- **Ciclo de correção** (depois desta execução): failed após debug [N]/2 · rodadas sem convergir [N]/3
- **Próximo passo**: [redevkit-deploy | redevkit-create ou redevkit-enhance (gaps) | redevkit-debug (failed) | G5 atingido: aguardando o usuário]
