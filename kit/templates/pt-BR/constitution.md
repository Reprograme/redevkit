---
type: constitution
created: "[DATA_DE_RATIFICACAO]"
updated: "[DATA_DA_ULTIMA_EMENDA]"
---

# Constituição de [NOME_DO_PROJETO]

<!--
  As leis do projeto. Todo plano faz uma Verificação da Constituição contra este arquivo; a
  análise e o converge tratam a violação de um DEVE (MUST) como CRITICAL. Mudanças só pelo
  procedimento de emenda em Governança (gate G1). Substitua todo [CAMPO]; apague estes
  comentários depois de preencher.
-->

## Princípios Fundamentais

### I. Test-First (INEGOCIÁVEL)

**TDD**: required

Toda história de usuário começa com testes que expressam os cenários de aceite. Os testes
DEVEM ser executados e vistos FALHANDO antes de a implementação ser escrita, e DEVEM passar
antes de a história ser concluída (vermelho, verde, refatorar). Uma tarefa só está pronta
quando o VERIFY dela foi observado.

*Motivo*: testes escritos primeiro fixam o comportamento esperado e provam que o código faz o
que a spec diz.

*Dispensa*: este princípio só pode ser relaxado por uma emenda aprovada pelo usuário, que
troca a linha acima para `**TDD**: waived` (marcador estrutural, não traduzir), registra o
motivo e o alcance, e incrementa a versão MAJOR.

### II. [NOME_DO_PRINCIPIO_2]

[DESCRICAO_DO_PRINCIPIO_2]
<!-- Exemplo: II. Verificação com evidência - nenhuma tarefa, execução de teste ou auditoria
é relatada como aprovada sem o comando que rodou e o resultado observado; checagens puladas
ficam SKIPPED. -->

### III. [NOME_DO_PRINCIPIO_3]

[DESCRICAO_DO_PRINCIPIO_3]
<!-- Exemplo vindo de uma skill de domínio: III. Orçamento de desempenho - o jogo DEVE
manter 60 FPS nos dispositivos-alvo; o tempo de quadro é medido em todo release candidate. -->

### IV. [NOME_DO_PRINCIPIO_4]

[DESCRICAO_DO_PRINCIPIO_4]
<!-- Exemplo: IV. Simplicidade - comece pelo design mais simples que atende a spec (YAGNI);
camadas ou projetos extras são justificados no Controle de Complexidade do plano. -->

### V. [NOME_DO_PRINCIPIO_5]

[DESCRICAO_DO_PRINCIPIO_5]
<!-- Exemplo: V. Segurança por padrão - segredos nunca entram no repositório, na memória ou
nos artefatos; entradas de usuários e de URLs são validadas. Acrescente ou remova princípios
conforme a necessidade. -->

## Restrições Técnicas

[RESTRICOES_TECNICAS]
<!-- Stack, plataformas, engine, metas de desempenho, conformidade. Vêm do tech.md e das
skills de domínio, ex.: "Engine: Phaser 3; alvo: navegadores de desktop e celular". -->

## Design e Interface

<!-- Remova esta seção quando o projeto não tiver interface de usuário. -->

- O `DESIGN.md` na raiz do projeto é a fonte única da verdade visual; trabalho de interface
  DEVE lê-lo primeiro e usar os tokens dele.
- Purple Ban: roxo e violeta não são usados por padrão. A marca ou o `DESIGN.md` podem
  suspender a proibição de forma explícita.
- [META_DE_ACESSIBILIDADE, ex.: "contraste WCAG 2.2 AA e acesso completo por teclado"]

## Fluxo de Desenvolvimento

[FLUXO_DE_DESENVOLVIMENTO]
<!-- Exemplo: features seguem spec → plano → tarefas → implementação → teste; o plano é
aprovado antes do código (gate G2); commits só quando o usuário pedir; ações destrutivas
exigem confirmação explícita. -->

## Governança

- Esta constituição prevalece sobre qualquer outra prática do projeto. Precedência: o pedido
  do usuário > esta constituição > `AGENTS.md` > skills de comando > personas > skills de
  conhecimento.
- **Conformidade**: todo plano tem uma Verificação da Constituição que cita este arquivo; a
  análise e o converge checam os princípios DEVE; uma violação para o trabalho (gate G3) até
  ser corrigida ou justificada no Controle de Complexidade do plano e aceita pelo usuário.
- **Emendas**: propostas de forma explícita, mostradas ao usuário e aplicadas só depois da
  confirmação (gate G1). Cada emenda atualiza a linha de versão abaixo e anexa um Sync Impact
  Report ao `.redevkit/memory/changelog.md` (mudança de versão, princípios e seções alterados,
  templates e artefatos a revisar, pendências).
- **Versionamento** (semver): MAJOR para remover ou redefinir um princípio de forma
  incompatível (inclusive a dispensa do TDD); MINOR para um princípio ou seção novos, ou
  orientação ampliada de forma relevante; PATCH para redação e esclarecimentos.
- [REGRAS_ADICIONAIS_DE_GOVERNANCA]

**Versão**: [VERSAO_DA_CONSTITUICAO] | **Ratificada em**: [DATA_DE_RATIFICACAO] | **Última emenda**: [DATA_DA_ULTIMA_EMENDA]
