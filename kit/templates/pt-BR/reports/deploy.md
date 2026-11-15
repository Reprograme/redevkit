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
| Execução de referência | [verification.md, execução AAAA-MM-DD HH:MM] | — | — |
| Veredito da referência | [converged+verified] | — | OK / BLOCKED |
| Features não verificadas | — | [none / specs/NNN-nome, …] | OK / BLOCKED |
| Tree fingerprint | `sha256:[HASH]` | `sha256:[HASH]` | OK / BLOCKED |
| Commit (HEAD) | `[SHA]` | `[SHA]` | — |
| Árvore de trabalho | [clean / dirty] | [clean / dirty] | — |

- **Status das pré-condições**: OK / BLOCKED / OVERRIDDEN
- **Motivo do override**: [obrigatório quando OVERRIDDEN, nas palavras do usuário; senão, nenhum]

<!--
Execução de referência e comparação: redevkit-test/references/code-state.md (a definição
única). A referência é o último verify da feature ativa, nunca uma execução de teste.
BLOCKED quando não há execução de verify, quando ela não é converged+verified, quando ainda há
feature não verificada (Unverified), quando o Tree fingerprint difere (o código mudou depois
dela) ou quando o estado do código não pode ser calculado. Commit e árvore de
trabalho são só contexto.
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
