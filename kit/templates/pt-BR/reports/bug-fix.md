---
type: bug-fix
---

# Correção de bug: [TÍTULO CURTO]

- **Slug**: [SLUG]
- **Corrigido em**: [AAAA-MM-DD]
- **Avaliação**: `assessment.md` (mesmo diretório)
- **Status**: [applied | partial | not-applied]

<!--
Mantenha estes tokens em inglês: applied, partial, not-applied, PASS, FAIL, SKIPPED,
clean, dirty.
-->

## Resumo

[Uma ou duas frases: o que mudou e por que isso elimina a causa raiz.]

## Teste de regressão (escrito primeiro)

- **Teste**: `[caminho/do/teste::nome]`
- **Comando**: `[COMANDO]`
- **Antes da correção**: FAIL
- **Falha pelo motivo certo**: [sim — a asserção corresponde ao sintoma / não — explique]
- **Depois da correção**: PASS
- **Dispensa do teste primeiro**: [nenhuma / emenda da constituição que o dispensa; teste adicionado depois da correção]

```text
[SAÍDA COM FALHA ANTES DA CORREÇÃO]
```

```text
[SAÍDA APROVADA DEPOIS DA CORREÇÃO]
```

## Mudanças

| Arquivo | Mudança | Observações |
| --- | --- | --- |
| `[caminho/do/arquivo]` | [adicionado / modificado / removido] | [OBSERVAÇÃO] |
| `[caminho/do/teste]` | teste adicionado | [OBSERVAÇÃO] |

## Verificação leve

| Verificação | Comando | Resultado | Observações |
| --- | --- | --- | --- |
| Teste de regressão | `[COMANDO]` | PASS / FAIL | [OBSERVAÇÃO] |
| Testes dos módulos alterados | `[COMANDO]` | PASS / FAIL / SKIPPED ([MOTIVO]) | [N aprovados, N falharam] |
| Lint / checagem de tipos | `[COMANDO]` | PASS / FAIL / SKIPPED ([MOTIVO]) | [OBSERVAÇÃO] |

## Estado do código

- **Commit (HEAD)**: `[SHA]` ou `n/a (não é um repositório git)`
- **Árvore de trabalho**: [clean / dirty — arquivos alterados]

## Desvios em relação à avaliação

[Ampliações de escopo, outra causa raiz, uma correção que não se sustentou; ou nenhum.]

## Pendências

- [Limpeza, monitoramento, documentação, código semelhante a revisar, ou nenhuma]
