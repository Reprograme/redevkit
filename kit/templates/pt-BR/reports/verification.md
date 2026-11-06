---
type: verification
---

# Verificação: [NOME DA FEATURE]

- **Feature**: `specs/[NNN-nome-curto]/`
- **Entradas**: `spec.md`, `plan.md`, `tasks.md`, `test-report.md` (mesmo diretório)

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
Mesmos comandos do relatório de testes:
  git rev-parse HEAD
  git status --porcelain -- . ':(exclude).redevkit' ':(exclude)specs'
  git status --porcelain -- . ':(exclude).redevkit' ':(exclude)specs' | git hash-object --stdin   (impressão digital do status)
  git diff HEAD -- . ':(exclude).redevkit' ':(exclude)specs' | git hash-object --stdin            (impressão digital do diff)
-->

### Convergência

- **Resultado**: convergente / lacunas encontradas
- **Tarefas anexadas**: `Phase [N]: Convergence` no `tasks.md`, [T0NN–T0NN], ou nenhuma

| Lacuna | Origem (spec, plan ou tarefa) | Tarefa anexada |
| --- | --- | --- |
| [O QUE FALTA OU ESTÁ DIFERENTE] | [FR-00N, cenário 2 da US1, seção do plan, T0NN] | [T0NN] |

### Evidência de execução

| Etapa | Comando | Código de saída | Resultado observado |
| --- | --- | --- | --- |
| Build | `[COMANDO]` | [CÓDIGO DE SAÍDA] | [compilou sem erros, ou o erro] |
| Suíte de testes completa | `[COMANDO]` | [CÓDIGO DE SAÍDA] | [N aprovados, N falharam, N ignorados] |
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

### Veredito

**[converged+verified | gaps | failed]** — [uma ou duas frases com a evidência decisiva].

<!--
converged+verified: nenhuma lacuna de convergência; build, suíte completa e fluxos críticos
passam; nenhuma auditoria com FAIL.
gaps: a execução passa, mas a convergência encontrou lacunas (tarefas foram anexadas).
failed: build, suíte, um fluxo crítico ou uma auditoria bloqueante falha.
-->

- **Próximo passo**: [redevkit-deploy | redevkit-create ou redevkit-enhance (gaps) | redevkit-debug (failed, ciclo [1 | 2] de 2)]
