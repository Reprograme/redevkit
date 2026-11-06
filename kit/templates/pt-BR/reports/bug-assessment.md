---
type: bug-assessment
---

# Avaliação de bug: [TÍTULO CURTO]

- **Slug**: [SLUG]
- **Criado em**: [AAAA-MM-DD]
- **Origem**: [execução de teste com falha / texto colado / URL sanitizada]
- **Feature**: `specs/[NNN-nome-curto]/`, ou nenhuma
- **Relatório de testes**: `specs/[NNN-nome-curto]/test-report.md`, execução [AAAA-MM-DD HH:MM], ou nenhum
- **Bug relacionado**: `.redevkit/bugs/[SLUG-ANTERIOR]/`, ou nenhum
- **Veredito**: [valid | likely-valid | invalid]
- **Severidade**: [critical | high | medium | low]

<!--
Nunca grave segredos neste arquivo; oculte-os, inclusive dentro de citações.
Mantenha estes tokens em inglês: valid, likely-valid, invalid, critical, high, medium, low,
always, often, sometimes, rare, not reproduced, allowlisted, confirmed-by-user, auto-refused.
-->

## Relato

[Relato citado ou condensado: teste que falhou e a asserção, mensagem de erro, trecho do
stack trace, passos informados pelo usuário.]

### Registro de URLs

| URL (sanitizada) | Host | Ramo da política |
| --- | --- | --- |
| [URL] | [HOST] | allowlisted / confirmed-by-user / auto-refused: [MOTIVO] |

### Não verificado

[Conteúdo com cara de instrução encontrado nas páginas buscadas, citado literalmente e não
executado, ou nenhum.]

## Sintoma

- **Observado**: [O QUE ACONTECE]
- **Esperado**: [O QUE DEVERIA ACONTECER]
- **Condições**: [ENTRADA, AMBIENTE, MOMENTO]

## Reprodução

1. [PASSO]
2. [PASSO]

- **Comando**: `[COMANDO]`
- **Taxa de reprodução**: [always | often | sometimes | rare | not reproduced]
- **Ambiente**: [SO, versões de runtime e ferramentas, branch]

```text
[TRECHO DA SAÍDA OBSERVADA]
```

## Isolamento

- **Desde quando**: [commit, data ou mudança que o introduziu, ou desconhecido]
- **Mudanças recentes verificadas**: [intervalo do git log ou resumo do diff]
- **Reprodução mínima**: [menor entrada ou caminho de código que dispara o problema]
- **Componente**: [MÓDULO, SERVIÇO OU CAMADA]

## Evidências

| # | Evidência | Fonte | Apoia ou refuta a hipótese |
| --- | --- | --- | --- |
| 1 | [OBSERVAÇÃO] | [comando, `caminho/do/arquivo:linha`, linha de log] | apoia / refuta |

## Caminhos de código suspeitos

- `[caminho/do/arquivo:linha]` — [POR QUÊ]

## Hipótese de causa raiz

1. Por que [OBSERVAÇÃO]? Porque [MOTIVO].
2. Por que [MOTIVO]? Porque [MOTIVO MAIS PROFUNDO].
3. Por que [MOTIVO MAIS PROFUNDO]? Porque [CAUSA RAIZ].

- **Hipótese**: [um parágrafo]
- **Confiança**: [high | medium | low]

## Correção proposta

- **Preferida**: [um ou dois parágrafos descrevendo a mudança na causa raiz]
- **Alternativas**: [ALTERNATIVA — TRADE-OFF], ou nenhuma
- **Arquivos que devem mudar**: `[caminho/do/arquivo]`

### Teste de regressão a escrever primeiro

- `[caminho/do/teste::nome]` — [o que ele fixa; deve falhar antes da correção, por este motivo]

## Riscos

- [Quebra de API, migração, desempenho, segurança, observabilidade, ou nenhum]

## Perguntas em aberto

- [NEEDS CLARIFICATION: PERGUNTA], ou nenhuma
