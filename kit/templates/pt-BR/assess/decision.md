---
type: assess-decision
---

# Decisão: [TÍTULO CURTO]

- **Slug**: [SLUG]
- **Decidido em**: [AAAA-MM-DD]
- **Veredito**: [go | needs-clarification | kill]
- **Artefatos revisados**: [intake.md, research.md, definition.md, shape.md]

<!--
Mantenha estes tokens em inglês: go, needs-clarification, kill, strong, adequate, weak,
unknown. Um go exige validade do problema adequate ou melhor, força das evidências adequate
ou melhor (nunca weak nem unknown) e uma opção recomendada no shape.md. Caso contrário, o
veredito honesto é needs-clarification. Um kill é um desfecho válido.
-->

## Placar

| Critério | Nota | Justificativa |
| --- | --- | --- |
| Validade do problema | strong / adequate / weak / unknown | [DO definition.md E DO research.md] |
| Força das evidências | strong / adequate / weak / unknown | [DO research.md] |
| Valor vs. custo de não fazer nada | strong / adequate / weak / unknown | [DO definition.md] |
| Viabilidade e encaixe no apetite | strong / adequate / weak / unknown | [DO shape.md] |
| Alinhamento estratégico | strong / adequate / weak / unknown | [CONSTITUIÇÃO E OBJETIVOS DO PROJETO] |
| Postura de risco | strong / adequate / weak / unknown | [strong = riscos-chave conhecidos e mitigados] |

## Veredito e justificativa

[A decisão e o porquê, num parágrafo curto que cita o placar. Reconheça toda nota unknown.]

## Se needs-clarification

- **Perguntas bloqueantes**: [NEEDS CLARIFICATION: PERGUNTA]
- **Etapa a revisitar**: [intake | research | define | shape]

## Se kill

- **Motivo decisivo**: [problema fraco, alternativa melhor, custo acima do valor, fora do
  escopo, superado]

## Se go — brief para o redevkit-plan

```text
Feature: [TÍTULO CURTO]
Problema: [ENUNCIADO DO PROBLEMA EM UMA LINHA]
Usuários: [QUEM É AFETADO]
Abordagem: [OPÇÃO RECOMENDADA, NO NÍVEL DE CONCEITO]
No escopo: [RESUMO]
Fora do escopo: [RESUMO]
Métricas de sucesso: [MÉTRICA: LINHA DE BASE -> META]
Restrições e suposições: [RESUMO]
Perguntas em aberto: [LISTA, ou nenhuma]
Origem: .redevkit/assessments/[SLUG]/decision.md
```

## Revisões

<!--
Somente acréscimo (append-only). Quando a decisão for revisitada, adicione aqui uma entrada
datada com o novo placar e a justificativa, atualize a linha Veredito do cabeçalho e preencha
a seção do novo veredito. Nunca reescreva o conteúdo anterior.
-->

- [AAAA-MM-DD] — [veredito anterior -> novo veredito]: [o que mudou e por quê], ou nenhuma
