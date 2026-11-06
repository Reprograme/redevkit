---
type: tasks
feature: "[###-nome-da-feature]"
created: "[DATA]"
updated: "[DATA]"
---

# Tarefas: [NOME DA FEATURE]

**Entrada**: documentos de design em `specs/[###-nome-da-feature]/`

**Pré-requisitos**: plan.md (obrigatório), spec.md (obrigatório), research.md, data-model.md, contracts/, DESIGN.md (quando há interface)

**Testes**: Test-First é o padrão (constituição). Em cada história de usuário, os testes vêm
primeiro e precisam FALHAR antes da implementação. Tarefas de teste só são opcionais quando a
constituição diz `**TDD**: waived`.

**Organização**: as tarefas são agrupadas por história de usuário, para que cada história
possa ser construída, testada e entregue sozinha.

## Formato

`- [ ] T001 [P] [US1] descrição — caminho — @persona — VERIFY: critério`

- **[P]**: pode rodar em paralelo (arquivos disjuntos das outras tarefas da fase, sem
  depender de tarefa inacabada da fase)
- **[US1]**: a história de usuário à qual a tarefa pertence (só nas fases de história)
- **caminho**: o arquivo ou diretório que a tarefa altera
- **@persona**: quem executa a tarefa
- **VERIFY**: a checagem observável que prova que a tarefa está pronta
- Tarefas concluídas ficam `- [X]`

<!--
  ============================================================================
  As tarefas abaixo são EXEMPLOS. A fase tasks as substitui por tarefas reais tiradas de:
  - histórias de usuário e prioridades do spec.md
  - stack, estrutura e Roteamento por Domínio do plan.md
  - entidades do data-model.md e interfaces de contracts/
  Não mantenha tarefas de exemplo no arquivo gerado.
  ============================================================================
-->

## Fase 1: Setup

**Objetivo**: inicializar o projeto e as ferramentas compartilhadas

- [ ] T001 Criar a estrutura do projeto conforme o plano — src/, tests/ — @backend-specialist — VERIFY: os diretórios existem e o comando de teste roda com 0 testes
- [ ] T002 Inicializar o projeto [linguagem] com as dependências de [framework] — package.json — @backend-specialist — VERIFY: a instalação termina sem erros
- [ ] T003 [P] Configurar lint e formatação — eslint.config.js — @backend-specialist — VERIFY: o comando de lint sai com 0 no projeto vazio

---

## Fase 2: Fundação

**Objetivo**: pré-requisitos que bloqueiam todas as histórias de usuário

**Crítico**: nenhuma história começa antes de esta fase terminar.

- [ ] T004 Configurar o schema e o framework de migrations — src/db/ — @database-architect — VERIFY: o comando de migration aplica uma migration vazia
- [ ] T005 [P] Configurar tratamento de erros e logs — src/lib/errors.ts — @backend-specialist — VERIFY: o teste unitário do formatador de erros passa
- [ ] T006 [P] Configurar as variáveis de ambiente — src/config.ts — @backend-specialist — VERIFY: o app sobe com os valores de `.env.example`

**Checkpoint**: fundação pronta; as histórias de usuário podem começar.

---

## Fase 3: US1 - [Título] (Prioridade: P1) MVP

**Meta**: [o que esta história entrega]

**Teste independente**: [como verificar esta história sozinha]

### Testes (escrever primeiro, devem falhar)

- [ ] T007 [P] [US1] Escrever teste de contrato que falha para [endpoint] — tests/contract/[nome].test.ts — @test-engineer — VERIFY: `[comando de teste] tests/contract/[nome].test.ts` falha porque [endpoint] ainda não existe
- [ ] T008 [P] [US1] Escrever teste de integração que falha para [jornada do usuário] — tests/integration/[nome].test.ts — @test-engineer — VERIFY: `[comando de teste] tests/integration/[nome].test.ts` falha na primeira asserção

### Implementação

- [ ] T009 [P] [US1] Criar o modelo [Entidade1] — src/models/[entidade1].ts — @backend-specialist — VERIFY: a checagem de tipos passa
- [ ] T010 [US1] Implementar [Serviço] (depende de T009) — src/services/[servico].ts — @backend-specialist — VERIFY: os testes unitários de [Serviço] passam
- [ ] T011 [US1] Implementar [endpoint ou tela] — src/[local]/[arquivo].ts — @[persona] — VERIFY: os testes de T007 e T008 passam

**Checkpoint**: a US1 funciona e está testada sozinha.

---

## Fase 4: US2 - [Título] (Prioridade: P2)

**Meta**: [o que esta história entrega]

**Teste independente**: [como verificar esta história sozinha]

### Testes (escrever primeiro, devem falhar)

- [ ] T012 [P] [US2] Escrever teste de integração que falha para [jornada do usuário] — tests/integration/[nome].test.ts — @test-engineer — VERIFY: o teste falha antes da implementação

### Implementação

- [ ] T013 [P] [US2] Criar o modelo [Entidade] — src/models/[entidade].ts — @backend-specialist — VERIFY: a checagem de tipos passa
- [ ] T014 [US2] Implementar [funcionalidade] — src/[local]/[arquivo].ts — @[persona] — VERIFY: T012 passa

**Checkpoint**: US1 e US2 funcionam, cada uma sozinha.

---

[Acrescente uma fase por história restante, no mesmo padrão, em ordem de prioridade]

---

## Fase N: Polimento

**Objetivo**: melhorias que afetam várias histórias

- [ ] TXXX [P] Atualizar a documentação — docs/ — @documentation-writer — VERIFY: o README descreve o novo comportamento
- [ ] TXXX Limpar e refatorar o código alterado — src/ — @[persona] — VERIFY: a suíte completa passa e o lint sai com 0
- [ ] TXXX Validar os cenários do quickstart — specs/[###-nome-da-feature]/quickstart.md — @qa-automation-engineer — VERIFY: cada passo do quickstart roda como está escrito

---

## Dependências e Ordem de Execução

### Dependências entre fases

- **Setup**: sem dependências.
- **Fundação**: depois do Setup; bloqueia todas as histórias.
- **Histórias de usuário**: depois da Fundação; em paralelo ou em ordem de prioridade (P1 → P2 → P3).
- **Polimento**: depois das histórias desejadas.

### Dependências entre histórias

- **US1 (P1)**: começa depois da Fundação; não depende de outras histórias.
- **US2 (P2)**: começa depois da Fundação; pode integrar com a US1, mas continua testável sozinha.

### Dentro de cada história

- Testes primeiro, e eles FALHAM antes da implementação.
- Modelos antes de serviços, serviços antes de endpoints ou telas, núcleo antes da integração.
- A história fica completa antes de passar para a próxima prioridade.

### Oportunidades de paralelismo

- Tarefas `[P]` da mesma fase podem rodar juntas.
- Depois da Fundação, histórias diferentes podem rodar em paralelo.

## Exemplo de Paralelismo: US1

```text
Juntas (testes):   T007, T008
Juntas (modelos):  T009
Depois, em ordem:  T010 → T011
```

## Estratégia de Implementação

### MVP primeiro

1. Fase 1 Setup, depois Fase 2 Fundação.
2. US1: testes que falham, implementação, testes verdes.
3. Pare e valide a US1 sozinha; demonstre se estiver pronta.

### Entrega incremental

Acrescente uma história por vez: testes que falham, implementação, testes verdes, validação.
Cada história agrega valor sem quebrar as anteriores.

## Notas

- `[P]` = arquivos disjuntos e nenhuma dependência dentro da fase.
- Marque uma tarefa `[X]` só depois de observar o VERIFY dela.
- Nunca renumere tarefas; trabalho novo entra como uma nova fase no fim.
- Commits só quando o usuário pedir.
