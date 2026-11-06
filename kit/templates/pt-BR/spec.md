---
type: spec
feature: "[###-nome-da-feature]"
status: draft
created: "[DATA]"
updated: "[DATA]"
---

# Especificação da Feature: [NOME DA FEATURE]

**Diretório da feature**: `specs/[###-nome-da-feature]/`

**Branch**: `[###-nome-da-feature]` (opcional; remova esta linha quando nenhuma branch for criada)

**Status**: Rascunho

**Entrada**: descrição do usuário: "[DESCRIÇÃO DA FEATURE COMO O USUÁRIO ESCREVEU]"

## Cenários de Usuário e Testes *(obrigatório)*

<!--
  Histórias de usuário são jornadas ordenadas por importância (P1 = a mais crítica).
  Cada história deve ser TESTÁVEL DE FORMA INDEPENDENTE: implementar só essa história já
  entrega um incremento viável, que pode ser desenvolvido, testado, publicado e demonstrado
  sozinho. Cada cenário de aceite vira um teste que falha antes da implementação (Test-First).
-->

### História de Usuário 1 - [Título Curto] (Prioridade: P1)

[Descreva esta jornada em linguagem simples]

**Por que esta prioridade**: [O valor e por que tem esta prioridade]

**Teste independente**: [Como pode ser testada sozinha, ex.: "Pode ser testada por completo fazendo [ação] e entrega [valor]"]

**Cenários de aceite**:

1. **Dado** [estado inicial], **Quando** [ação], **Então** [resultado esperado]
2. **Dado** [estado inicial], **Quando** [ação], **Então** [resultado esperado]

---

### História de Usuário 2 - [Título Curto] (Prioridade: P2)

[Descreva esta jornada em linguagem simples]

**Por que esta prioridade**: [O valor e por que tem esta prioridade]

**Teste independente**: [Como pode ser testada sozinha]

**Cenários de aceite**:

1. **Dado** [estado inicial], **Quando** [ação], **Então** [resultado esperado]

---

### História de Usuário 3 - [Título Curto] (Prioridade: P3)

[Descreva esta jornada em linguagem simples]

**Por que esta prioridade**: [O valor e por que tem esta prioridade]

**Teste independente**: [Como pode ser testada sozinha]

**Cenários de aceite**:

1. **Dado** [estado inicial], **Quando** [ação], **Então** [resultado esperado]

---

[Acrescente mais histórias conforme necessário, cada uma com prioridade]

### Casos de Borda

- O que acontece quando [condição de limite]?
- Como o sistema trata [cenário de erro]?

## Requisitos *(obrigatório)*

### Requisitos Funcionais

- **FR-001**: O sistema DEVE [capacidade específica, ex.: "permitir que usuários criem contas"]
- **FR-002**: O sistema DEVE [capacidade específica, ex.: "validar endereços de e-mail"]
- **FR-003**: Os usuários DEVEM conseguir [interação principal, ex.: "redefinir a senha"]
- **FR-004**: O sistema DEVE [requisito de dados, ex.: "guardar as preferências do usuário"]

*Como marcar um requisito pouco claro (no máximo 3 marcadores por spec):*

- **FR-005**: O sistema DEVE autenticar usuários via [NEEDS CLARIFICATION: método de autenticação não definido - e-mail e senha, SSO, OAuth?]

### Entidades-Chave *(inclua se a feature envolve dados)*

- **[Entidade 1]**: [O que representa, atributos principais, sem implementação]
- **[Entidade 2]**: [O que representa, relações com outras entidades]

## Critérios de Sucesso *(obrigatório)*

<!--
  Mensuráveis e independentes de tecnologia: sem frameworks, linguagens, bancos ou APIs.
-->

### Resultados Mensuráveis

- **SC-001**: [Métrica mensurável, ex.: "Usuários criam a conta em menos de 2 minutos"]
- **SC-002**: [Métrica mensurável, ex.: "1.000 usuários simultâneos sem lentidão perceptível"]
- **SC-003**: [Métrica de satisfação, ex.: "90% dos usuários concluem a tarefa principal na primeira tentativa"]
- **SC-004**: [Métrica de negócio, ex.: "Chamados de suporte sobre [X] caem 50%"]

## Suposições

<!--
  Padrões razoáveis escolhidos onde a descrição não disse nada, e recomendações adotadas
  sem resposta (--auto). Uma linha cada.
-->

- [Suposição sobre os usuários, ex.: "Os usuários têm conexão estável com a internet"]
- [Suposição sobre o escopo, ex.: "Suporte a celular fica fora da v1"]
- [Dependência de sistema existente, ex.: "Reutiliza a API de perfil de usuário existente"]

## Esclarecimentos

<!--
  Preenchida pela fase de clarify. Uma subseção por sessão:
  ### Sessão AAAA-MM-DD
  - Q: <pergunta> → A: <resposta>
  Deixe esta seção vazia quando a spec for escrita pela primeira vez.
-->
