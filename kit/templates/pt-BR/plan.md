---
type: plan
feature: "[###-nome-da-feature]"
status: draft
created: "[DATA]"
updated: "[DATA]"
---

# Plano de Implementação: [FEATURE]

**Diretório da feature**: `specs/[###-nome-da-feature]/` | **Data**: [DATA]

**Spec**: `specs/[###-nome-da-feature]/spec.md` | **Branch**: `[###-nome-da-feature]` (opcional)

## Resumo

[Requisito principal da spec + abordagem técnica vinda da pesquisa, em 2 a 4 frases]

## Contexto Técnico

<!--
  Substitua pelos valores reais do projeto. Use NEEDS CLARIFICATION só para valores que
  bloqueiam o design; resolva-os na Fase 0.
-->

**Linguagem/Versão**: [ex.: TypeScript 5.6, Python 3.12, Rust 1.82 ou NEEDS CLARIFICATION]

**Dependências principais**: [ex.: FastAPI, React, Phaser ou NEEDS CLARIFICATION]

**Armazenamento**: [ex.: PostgreSQL, SQLite, arquivos locais, ou N/A]

**Testes**: [ex.: vitest, pytest, cargo test, Playwright ou NEEDS CLARIFICATION]

**Plataforma-alvo**: [ex.: navegadores modernos, servidor Linux, iOS 17+ ou NEEDS CLARIFICATION]

**Tipo de projeto**: [web | fullstack | api | mobile | game | cli | library | desktop | other]

**Metas de desempenho**: [do domínio, ex.: 60 fps, 1.000 req/s, p95 < 200 ms]

**Restrições**: [do domínio, ex.: funciona offline, < 100 MB de memória, bundle < 300 KB]

**Escala/Escopo**: [ex.: 10 mil usuários, 30 telas, 5 fases do jogo]

## Roteamento por Domínio

<!--
  Preenchido pela fase de roteamento: quem constrói cada parte e quais skills de
  conhecimento (e referências) se aplicam. As tarefas tiram o @persona desta tabela.
-->

| Área | Persona | Skills (referências) | Motivo |
| --- | --- | --- | --- |
| [ex.: loop do jogo e renderização] | @[persona] | [skill (referência, referência)] | [gatilho encontrado na spec] |
| [ex.: testes] | @test-engineer | [testing-patterns, tdd-workflow] | [princípio Test-First] |

## Verificação da Constituição

*GATE: precisa passar antes da pesquisa da Fase 0; repetir depois do design da Fase 1.*

**Fonte**: `.redevkit/memory/constitution.md`, versão [VERSÃO DA CONSTITUIÇÃO]

| Princípio | O que exige aqui | Status | Evidência ou justificativa |
| --- | --- | --- | --- |
| [I. Test-First] | [Testes que falham primeiro em cada história] | [PASS / VIOLATION / N/A] | [Onde o plano atende] |
| [Princípio] | [Exigência] | [Status] | [Evidência] |

<!--
  Uma VIOLATION para o plano (gate G3), a menos que seja justificada em Controle de
  Complexidade e aceita pelo usuário. Nunca enfraqueça um princípio aqui: emendá-lo é um
  passo separado.
-->

## Estrutura do Projeto

### Documentação (desta feature)

```text
specs/[###-nome-da-feature]/
├── spec.md              # fase specify
├── plan.md              # este arquivo
├── research.md          # Fase 0
├── data-model.md        # Fase 1
├── quickstart.md        # Fase 1
├── contracts/           # Fase 1
├── checklists/          # requirements.md (specify) + <domínio>.md (fase checklist)
└── tasks.md             # Fase 2 (fase tasks, não é escrito por este passo)
```

### Código-fonte (raiz do repositório)

<!--
  Substitua pelo layout concreto desta feature, com caminhos reais. Apague as opções que
  não se aplicam; o plano final não mantém rótulos de opção.
-->

```text
# [REMOVER SE NÃO USAR] Opção 1: projeto único (padrão)
src/
├── models/
├── services/
└── lib/
tests/
├── contract/
├── integration/
└── unit/

# [REMOVER SE NÃO USAR] Opção 2: aplicação web (frontend + backend)
backend/
├── src/
└── tests/
frontend/
├── src/
└── tests/

# [REMOVER SE NÃO USAR] Opção 3: mobile + API
api/
└── [mesma estrutura do backend acima]
[ios/ ou android/ ou app/]
└── [estrutura da plataforma]
```

**Decisão de estrutura**: [A estrutura escolhida e os diretórios reais acima]

## Design Source-of-Truth

<!--
  Obrigatória quando a feature tem interface. O DESIGN.md na raiz do projeto é a fonte única
  da verdade (um por projeto). Registre aqui só os deltas desta feature. Sem interface,
  escreva "N/A - sem interface de usuário" e apague as tabelas.
-->

**Status do DESIGN.md**: [criado | atualizado | sem mudança | N/A - sem interface de usuário]

**Tokens usados**: [ex.: colors.primary, colors.surface, typography.body-md, spacing.md]

| Delta | Token ou componente | Mudança | Motivo |
| --- | --- | --- | --- |
| [adicionado / alterado / removido] | [ex.: components.score-badge] | [o que muda no DESIGN.md] | [qual história precisa] |

**Metas de acessibilidade desta feature**: [ex.: contraste WCAG 2.2 AA, caminho por teclado para toda ação]

**Nota de cor**: o Purple Ban vale por padrão; roxo ou violeta só quando o DESIGN.md ou a
marca pedirem.

## Fases de Execução

### Fase 0: Pesquisa

- [ ] Resolver todo NEEDS CLARIFICATION do Contexto Técnico
- [ ] Registrar decisões, motivos e alternativas rejeitadas em `research.md`

### Fase 1: Design e Contratos

- [ ] Entidades, campos, regras de validação e estados em `data-model.md`
- [ ] Interfaces (API, CLI, eventos, formatos de arquivo) em `contracts/`
- [ ] Cenários de validação executáveis em `quickstart.md`
- [ ] Gate do DESIGN.md quando a feature tem interface (seção acima)
- [ ] Verificação da Constituição repetida depois do design

### Fase 2: Planejamento de Tarefas

- [ ] `tasks.md` gerado pela fase tasks (Setup, Fundação, US1..n, Polimento; testes que falham primeiro)
- [ ] Análise sem achados CRITICAL

## Controle de Complexidade

> Preencha SOMENTE quando a Verificação da Constituição tiver uma violação que precisa ser justificada.

| Violação | Por que é necessária | Alternativa mais simples rejeitada porque |
| --- | --- | --- |
| [ex.: um 4º projeto] | [necessidade atual] | [por que 3 projetos não bastam] |

## Relatório do Plano

<!-- Escrito por último, depois das fases acima. -->

- **Artefatos**: [research.md, data-model.md, contracts/, quickstart.md, mudanças no DESIGN.md]
- **Verificação da Constituição**: [resultado inicial] → [resultado pós-design]
- **Análise**: [contagens CRITICAL / HIGH / MEDIUM / LOW]
- **Aprovação (gate G2)**: [pendente | aprovado em DATA]
