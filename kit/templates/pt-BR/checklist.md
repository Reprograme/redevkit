---
type: checklist
domain: "[DOMINIO]"
created: "[DATA]"
updated: "[DATA]"
---

# Checklist de [TIPO DE CHECKLIST]: [NOME DA FEATURE]

**Objetivo**: [O que este checklist cobre]

**Criado em**: [DATA]

**Feature**: `specs/[###-nome-da-feature]/spec.md`

**Responsável pela revisão**: este é um checklist de qualidade de requisitos que pertence ao
revisor. Marque um item `[x]` só quando um revisor julgar que o critério de qualidade do
requisito foi atendido.

**Significado da marcação**: `[x]` quer dizer que o requisito está bem escrito (completo,
claro, consistente, mensurável). Não quer dizer que a implementação está pronta.

<!--
  ============================================================================
  Os itens abaixo são EXEMPLOS. A fase checklist os substitui por itens construídos a partir
  da spec (e do plan.md e do tasks.md, quando existirem). Cada item pergunta sobre a
  qualidade do que está escrito, traz a dimensão e uma referência ([Spec §FR-001], [Gap],
  [Ambiguity], [Conflict], [Assumption]) e começa desmarcado.
  Não mantenha itens de exemplo no arquivo gerado.
  ============================================================================
-->

## Completude dos Requisitos

- [ ] CHK001 Os requisitos de tratamento de erro estão definidos para cada modo de falha? [Gap]
- [ ] CHK002 Os requisitos de acessibilidade estão especificados para todos os elementos interativos? [Completeness]

## Clareza dos Requisitos

- [ ] CHK003 "Carregamento rápido" está quantificado com um limite de tempo? [Clarity, Spec §SC-002]

## Consistência dos Requisitos

- [ ] CHK004 Os requisitos de navegação estão alinhados em todas as telas? [Consistency, Spec §FR-010]

## Cobertura de Cenários

- [ ] CHK005 Há requisitos para o estado vazio (ainda sem dados)? [Coverage, Gap]
- [ ] CHK006 Há requisitos de recuperação quando um salvamento falha no meio? [Coverage, Exception Flow]

## Notas

- Marque itens `[x]` só depois que a revisão confirmar que o critério foi atendido.
- Deixe os itens desmarcados enquanto precisarem de esclarecimento ou correção; anote os
  achados na própria linha.
- Este checklist é informativo, não é gate: a fase implement avisa uma vez sobre os itens
  abertos e o relatório do verify os lista em Não verificado. Nenhuma das duas altera as
  marcações.
- `checklists/requirements.md` é o checklist embutido de qualidade da spec e tem ciclo de
  vida próprio (fases specify e clarify).
