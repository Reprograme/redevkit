---
type: bug-test
---

# Verificação de bug: [TÍTULO CURTO]

- **Slug**: [SLUG]
- **Testado em**: [AAAA-MM-DD]
- **Avaliação**: `assessment.md` (mesmo diretório)
- **Correção**: `fix.md` (mesmo diretório)
- **Resultado**: [verified | partial | failed]

<!--
Mantenha estes tokens em inglês: verified, partial, failed, PASS, FAIL, SKIPPED, clean, dirty.
verified: a reprodução original foi exercitada e não falha mais, o teste de regressão passa
e a suíte relevante está verde.
partial: o sintoma sumiu, mas uma verificação é inconclusiva ou foi pulada (inclusive uma
reprodução que não pôde ser exercitada), ou surgiu uma regressão não relacionada.
failed: o sintoma ainda se reproduz, ou a correção quebra a suíte.
-->

## Resumo

[Uma ou duas frases: o bug ainda se reproduz, a correção se sustentou, houve regressões.]

## Verificações

| Verificação | Comando ou ação | Resultado | Observações |
| --- | --- | --- | --- |
| Reprodução original (após a correção) | `[COMANDO OU PASSOS]` | PASS / FAIL / SKIPPED ([MOTIVO]) | [PASS = o sintoma não ocorre mais] |
| Teste de regressão | `[COMANDO]` | PASS / FAIL | [OBSERVAÇÃO] |
| Suíte relevante | `[COMANDO]` | PASS / FAIL / SKIPPED ([MOTIVO]) | [N aprovados, N falharam, N ignorados] |
| Lint / checagem de tipos | `[COMANDO]` | PASS / FAIL / SKIPPED ([MOTIVO]) | [OBSERVAÇÃO] |

## Trechos de saída

```text
[LINHAS FINAIS DO RESUMO OU A ASSERÇÃO QUE FALHOU]
```

## Estado do código

- **Commit (HEAD)**: `[SHA]` ou `n/a (não é um repositório git)`
- **Árvore de trabalho**: [clean / dirty — arquivos alterados]

## Riscos residuais

- [Ambiente não coberto, comportamento intermitente, ou nenhum]

## Recomendação

[Encerrar o bug e seguir para o redevkit-verify / aguardar: reprodução inconclusiva /
reabrir: o sintoma ainda se reproduz, avaliar de novo com esta evidência.]
