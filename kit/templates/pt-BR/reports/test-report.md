---
type: test-report
---

# Relatório de testes: [NOME DA FEATURE]

- **Feature**: `specs/[NNN-nome-curto]/`
- **Spec**: `specs/[NNN-nome-curto]/spec.md`

<!--
Somente acréscimo (append-only). Adicione uma seção "Execução" no fim deste arquivo a cada
rodada. Nunca edite nem apague uma execução anterior. Só contam execuções da feature inteira
(Escopo: feature): a última delas é a que o redevkit-verify (passo 1) pode reaproveitar, e a
referência do redevkit-deploy é escolhida como redevkit-test/references/code-state.md § Compare
descreve; os dois comparam o estado do código ali.
Mantenha estes tokens em inglês: PASS, FAIL, SKIPPED, MISSING, clean, dirty.
-->

## Execução [AAAA-MM-DD HH:MM] — [PASS | FAIL]

- **Executado por**: [redevkit-test | redevkit-verify (step 1)]
- **Escopo**: [feature | arquivo ou cenário: …]

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
Registre estes valores logo após a suíte com os comandos de
redevkit-test/references/code-state.md (no mesmo tipo de shell que o deploy vai usar).
-->

### Comandos executados

| # | Comando | Código de saída | Duração | Resumo |
| --- | --- | --- | --- | --- |
| 1 | `[COMANDO]` | [CÓDIGO DE SAÍDA] | [DURAÇÃO] | [N aprovados, N falharam, N ignorados] |

### Resultados

- **Total**: [N] · **Aprovados**: [N] · **Falharam**: [N] · **Ignorados**: [N]
- **Falhas**:
  - `[ID DO TESTE]` — [trecho da asserção ou do erro]

```text
[TRECHO CURTO DA SAÍDA: linhas finais do resumo ou a asserção que falhou]
```

### Cobertura dos cenários de aceite

| Cenário da spec | Teste | Status |
| --- | --- | --- |
| [US1 / Cenário 1 — resumo do Dado, Quando, Então] | `[caminho/do/teste::nome]` | PASS / FAIL / SKIPPED ([MOTIVO]) / MISSING |

- **Testes gerados nesta execução**: [lista, ou nenhum]
- **Cenários ainda sem teste**: [lista, ou nenhum]
- **Não verificado** (não automatizável aqui; nunca conta como PASS): [cenário — checagem
  manual necessária, ou nenhum]

### Suposições

- [Suposição adotada nesta execução e o motivo, ou nenhuma]

### Veredito

**[PASS | FAIL]** — [uma frase com a evidência decisiva].

<!--
PASS somente quando todos os comandos saíram com 0, nenhum teste falhou e todo cenário de
aceite automatizável tem um teste aprovado. Qualquer outra situação é FAIL. Cenários que não
podem ser automatizados aqui vão para Não verificado: não tornam a execução FAIL e nunca são PASS.
-->

- **Próximo passo**: [redevkit-deploy, sugerindo redevkit-verify antes | redevkit-debug | dentro do redevkit-verify: a verificação continua (PASS) ou termina como failed (FAIL)]
