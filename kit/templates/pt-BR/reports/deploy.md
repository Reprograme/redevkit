---
type: deploy
---

# Deploy: [AMBIENTE] — [AAAA-MM-DD]

- **Ambiente**: [AMBIENTE]
- **Produção**: sim / não
- **Início**: [AAAA-MM-DD HH:MM]
- **Disparado por**: [USUÁRIO] (deploys só rodam quando o usuário os invoca)
- **Features**: `specs/[NNN-nome-curto]/`
- **Desfecho**: [succeeded | failed | rolled-back | aborted]

<!--
Nunca grave segredos (tokens, senhas, chaves, strings de conexão) neste arquivo.
Mantenha estes tokens em inglês: PASS, FAIL, SKIPPED, OK, BLOCKED, OVERRIDDEN, succeeded,
failed, rolled-back, aborted, clean, dirty.
-->

## Pré-condições

| Verificação | Referência (do relatório) | Atual | Resultado |
| --- | --- | --- | --- |
| Debug pendente | [não / sim: slug do bug, AAAA-MM-DD HH:MM] | — | OK / BLOCKED |
| Execução de referência | [test-report.md, execução AAAA-MM-DD HH:MM, executada por redevkit-test / redevkit-verify (passo 1)] | — | — |
| Veredito da referência | [PASS] | — | OK / BLOCKED |
| Commit (HEAD) | `[SHA]` | `[SHA]` | OK / BLOCKED |
| Árvore de trabalho | [clean / dirty] | [clean / dirty] | OK / BLOCKED |
| Impressão digital do status | `[HASH]` | `[HASH]` | OK / BLOCKED |
| Impressão digital do diff | `[HASH]` | `[HASH]` | OK / BLOCKED |

- **Status das pré-condições**: OK / BLOCKED / OVERRIDDEN
- **Verify sugerido**: [não necessário (há um verify converged+verified mais novo que a referência) / sugerido, o usuário escolheu: verify antes ou deploy agora / um verify mais novo é gaps ou failed, o usuário escolheu: corrigir antes ou fazer o deploy assim mesmo]
- **Motivo do override**: [obrigatório quando OVERRIDDEN, nas palavras do usuário; senão, nenhum]

<!--
Execução de referência e comparação: redevkit-test/references/code-state.md § Compare (a
definição única). BLOCKED quando há debug pendente, quando não há referência, quando a última
execução de testes não é PASS ou quando o código mudou depois dela.
-->

## Plano de deploy

| # | Etapa | Comando ou ação | Resultado esperado |
| --- | --- | --- | --- |
| 1 | [ETAPA] | `[COMANDO]` | [RESULTADO ESPERADO] |

- **Versão ou artefato**: [TAG, IMAGEM, ID DO BUILD]
- **Migrações**: [nenhuma, ou lista com a reversibilidade de cada uma]
- **Configuração e segredos**: [de onde vêm, nunca os valores]
- **Indisponibilidade prevista**: [nenhuma, ou estimativa]

## Plano de rollback

- **Gatilho**: [condições que disparam o rollback, ex.: smoke test com FAIL, taxa de erro acima de N%]
- **Cuidados com dados**: [backups feitos, migrações irreversíveis, ou nenhum]

| # | Etapa | Comando ou ação | Resultado esperado |
| --- | --- | --- | --- |
| 1 | [ETAPA] | `[COMANDO]` | [RESULTADO ESPERADO] |

## Confirmação de produção

- **Exigida**: sim / não
- **Confirmação**: [a confirmação explícita do usuário, entre aspas, com horário] / não se aplica
- **Plano de rollback revisado pelo usuário**: sim / não / não se aplica

## Registro de execução

| Hora | Etapa | Comando | Código de saída | Resultado observado |
| --- | --- | --- | --- | --- |
| [HH:MM] | [ETAPA] | `[COMANDO]` | [CÓDIGO DE SAÍDA] | [RESULTADO] |

```text
[TRECHOS CURTOS DE SAÍDA]
```

## Smoke test pós-deploy

| Verificação | Comando ou URL | Esperado | Observado | Resultado |
| --- | --- | --- | --- | --- |
| [VERIFICAÇÃO] | `[COMANDO OU URL]` | [ESPERADO] | [OBSERVADO] | PASS / FAIL / SKIPPED ([MOTIVO]) |

## Desfecho

[Uma ou duas frases: o que foi publicado, onde, e a evidência de que funciona. Se houve
rollback, o que o disparou e o estado depois dele.]

- **Pendências**: [monitoramento, limpeza, chamados, ou nenhuma]
