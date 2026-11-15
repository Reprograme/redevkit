---
type: test-report
---

# Relatório de testes: [NOME DA FEATURE]

- **Feature**: `specs/[NNN-nome-curto]/`
- **Spec**: `specs/[NNN-nome-curto]/spec.md`

<!--
Somente acréscimo (append-only). Adicione uma seção "Execução" no fim deste arquivo a cada
rodada. Nunca edite nem apague uma execução anterior. Escopo spec: o redevkit-test rodou só
os testes desta feature (spec (full suite) quando o comando de teste não seleciona arquivos).
Escopo global: o redevkit-verify (passo 1) rodou a suíte inteira. Só execuções da suíte
inteira podem ser reaproveitadas pelo redevkit-verify; o deploy nunca usa uma execução de
teste como referência (usa o último verify, redevkit-test/references/code-state.md).
Mantenha estes tokens em inglês: PASS, FAIL, SKIPPED, MISSING, clean, dirty, os escopos e as
classes de falha product-defect, not-implemented, test-defect, environment, baseline.
-->

## Execução [AAAA-MM-DD HH:MM] — [PASS | FAIL]

- **Executado por**: [redevkit-test | redevkit-verify (step 1)]
- **Escopo**: [spec | spec (full suite) | global]
- **Conjunto de testes da spec** (escopo spec): [arquivos de teste passados ao runner, ou o motivo de a suíte inteira ter rodado]

### Estado do código

| Campo | Valor |
| --- | --- |
| Commit (HEAD) | `[SHA]` ou `n/a (não é um repositório git)` |
| Branch | `[BRANCH]` |
| Árvore de trabalho | clean / dirty |
| Arquivos alterados | [nenhum, ou a lista do `git status --porcelain`] |
| Tree fingerprint | `sha256:[HASH]` ou `n/a (no Python interpreter)` |

<!--
Registre estes valores logo após a suíte com o `code_state.py`, como descreve
redevkit-test/references/code-state.md. Duas execuções rodaram sobre o mesmo código quando o
Tree fingerprint é igual.
-->

### Comandos executados

| # | Comando | Código de saída | Duração | Resumo |
| --- | --- | --- | --- | --- |
| 1 | `[COMANDO]` | [CÓDIGO DE SAÍDA] | [DURAÇÃO] | [N aprovados, N falharam, N ignorados] |

### Resultados

- **Total**: [N] · **Aprovados**: [N] · **Falharam**: [N] · **Ignorados**: [N]
- **Falhas** (uma linha cada, com a classe):
  - `[ID DO TESTE]` — [product-defect | not-implemented | test-defect | environment | baseline] — [trecho da asserção ou do erro]
- **Classe da falha** (todas as que restam numa execução FAIL; nenhuma em PASS): [product-defect | not-implemented | test-defect | environment | nenhuma]
- **Falhas de baseline** (escopo global, antes da primeira execução da suíte inteira toda verde do projeto; nunca tornam a execução FAIL): [teste — arquivo, ou nenhuma]
- **Fora da spec** (testes gerados a pedido para comportamento fora da spec e, no escopo spec (full suite), todo outro teste da suíte; nunca tornam a execução FAIL, o verify os julga): [teste — arquivo — resultado, ou nenhum]

```text
[TRECHO CURTO DA SAÍDA: linhas finais do resumo ou a asserção que falhou]
```

### Cobertura dos cenários de aceite

| Cenário da spec | Teste | Status |
| --- | --- | --- |
| [US1 / Cenário 1 — resumo do Dado, Quando, Então] | `[caminho/do/teste::nome]` | PASS / FAIL / SKIPPED ([MOTIVO]) / MISSING |

- **Testes gerados nesta execução**: [lista, ou nenhum]
- **Testes corrigidos nesta execução** (test-defect, com o cenário da spec ou o erro que comprova): [lista, ou nenhum]
- **Cenários ainda sem teste**: [lista, ou nenhum]
- **Não verificado** (não automatizável aqui; nunca conta como PASS): [cenário — checagem
  manual necessária, ou nenhum]

### Suposições

- [Suposição adotada nesta execução e o motivo, ou nenhuma]

### Veredito

**[PASS | FAIL]** — [uma frase com a evidência decisiva].

<!--
PASS somente quando todos os comandos saíram com 0 (escopo global: ou falharam só por falhas
de baseline), nenhum outro teste falhou e todo cenário de aceite automatizável tem um teste
aprovado. Qualquer outra situação é FAIL. Cenários que não
podem ser automatizados aqui vão para Não verificado: não tornam a execução FAIL e nunca são PASS.
-->

- **Próximo passo**: [PASS: redevkit-verify (o único caminho para o deploy), ou redevkit-plan para a próxima feature | FAIL, por classe: environment → corrigir o ambiente e rodar de novo; not-implemented → redevkit-create; product-defect → redevkit-debug (test cycle N/5) | dentro do redevkit-verify: a verificação continua (PASS) ou termina como failed (FAIL)]
