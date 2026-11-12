# Método: desenvolvimento orientado a especificação no REDEVKIT

Este documento descreve o método que os comandos do REDEVKIT seguem. Ele foi escrito a
partir dos templates que o kit realmente instala (`kit/templates/pt-BR/` e
`kit/templates/en/`, copiados para `.redevkit/templates/`) e das skills dos comandos. Todo
termo de processo citado aqui existe nesses arquivos. Um teste automático
(`test/docs.test.js`) confere uma lista de termos que os templates não têm, os gates G1–G7, a
linha do TDD e a gramática das tarefas.

Os nomes de seção aparecem em português, como nos templates pt-BR, com o equivalente dos
templates em inglês entre parênteses quando ajuda.

## Visão geral

O trabalho de cada feature passa por artefatos em `specs/NNN-nome/`, nesta ordem:

| Etapa | Pergunta | Artefato | Quem conduz |
| --- | --- | --- | --- |
| Constituição | Quais são as leis do projeto? | `.redevkit/memory/constitution.md` | `redevkit-new` (fase `redevkit-constitution`) |
| Spec | O QUE construir e POR QUÊ | `spec.md`, `checklists/requirements.md` | `redevkit-plan` (fase `redevkit-specify`) |
| Plano | COMO, com qual stack e estrutura | `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md` | `redevkit-plan` |
| Design | Qual linguagem visual | `DESIGN.md` na raiz | `redevkit-plan` (gate do `DESIGN.md`) |
| Tarefas | EM QUE ORDEM e QUEM faz | `tasks.md` | `redevkit-plan` (fase `redevkit-tasks`) |
| Análise | O conjunto é consistente? | relatório na resposta | `redevkit-plan` (fase `redevkit-analyze`) |
| Implementação | Construir, testes primeiro | código e testes | `redevkit-create` ou `redevkit-enhance` |
| Teste | A feature cumpre a spec? | `test-report.md` | `redevkit-test` |
| Verificação | O código converge com a spec e roda de verdade? | `verification.md` | `redevkit-verify` |

A spec diz o quê e por quê, nunca como: stack, APIs e estrutura de código ficam no plano.
Nenhum código de aplicação é escrito antes da aprovação do plano (gate G2).

## Constituição

A constituição fica dentro da memória, em `.redevkit/memory/constitution.md`. Ela é criada
pelo `redevkit-new` a partir do template `constitution.md` e só muda por emenda.

Estrutura do template:

- **Princípios Fundamentais** (Core Principles): princípios numerados em algarismos romanos.
  O princípio I vem preenchido; os slots II a V são guias, e você pode ter mais ou menos
  princípios. Cada princípio usa DEVE/DEVERIA (MUST/SHOULD) e traz o motivo.
- **Restrições Técnicas** (Technical Constraints): stack, plataformas, metas de desempenho e
  conformidade, vindas do `tech.md` e das skills de domínio.
- **Design e Interface** (Design and User Interface): o `DESIGN.md` como fonte única da
  verdade visual e o Purple Ban ligado por padrão. É removida quando o projeto não tem
  interface.
- **Fluxo de Desenvolvimento** (Development Workflow).
- **Governança** (Governance): precedência, conformidade, emendas e versionamento.
- Linha final: `**Versão**: … | **Ratificada em**: … | **Última emenda**: …`.

### Test-First por padrão

O princípio I é **Test-First (INEGOCIÁVEL)** e traz uma linha estrutural, que não é
traduzida:

```markdown
**TDD**: required
```

Enquanto essa linha disser `required`, toda história de usuário começa com testes que
expressam os cenários de aceite, e esses testes precisam ser executados e vistos falhando
antes da implementação (vermelho, verde, refatorar). Para dispensar o TDD, por exemplo num
protótipo, é preciso uma emenda aprovada por você que troca a linha para
`**TDD**: waived`, registra o motivo e o alcance e incrementa a versão MAJOR. As fases
`redevkit-tasks` e `redevkit-implement` leem essa linha.

### Emendas e versionamento

- Toda criação ou emenda é mostrada a você e só é gravada depois da confirmação (gate G1).
- A versão segue semver: **MAJOR** para remover ou redefinir um princípio de forma
  incompatível (inclusive dispensar o TDD); **MINOR** para um princípio ou seção novos, ou
  orientação ampliada de forma relevante; **PATCH** para redação e esclarecimentos. A criação
  gera a versão `1.0.0`.
- Cada emenda anexa um **Sync Impact Report** à seção de emendas da constituição em
  `.redevkit/memory/changelog.md`: mudança de versão, motivo, princípios e seções alterados,
  templates a revisar, artefatos ativos a revisar e pendências.
- A fase de constituição **não edita** templates, specs nem código: o Sync Impact Report só
  lista o que depende do princípio alterado, para você ou o próximo comando revisar.

### Precedência

Pedido do usuário > constituição > `AGENTS.md` > skill de comando > persona > skill de
conhecimento.

## Spec

O `redevkit-plan` cria a spec quando não há feature ativa ou quando o pedido descreve outra
feature.

### Numeração NNN

- O diretório é `specs/NNN-nome-curto/`. `NNN` é o **maior** prefixo numérico existente em
  `specs/` mais 1, com 3 dígitos (`001` quando `specs/` está vazio ou não existe). Lacunas
  nunca são reaproveitadas; depois de `999` vem `1000`.
- O nome curto tem de 2 a 4 palavras em kebab-case ASCII, sem acentos, com até 40
  caracteres (por exemplo `autenticacao-usuario`).
- Antes de criar o diretório, o agente lista `specs/` de novo. Se dois diretórios tiverem o
  mesmo número (por exemplo depois de juntar branches), ele relata e oferece renumerar o mais
  recente, com sua confirmação. O `redevkit doctor` também detecta números duplicados.

### Conteúdo

O template `spec.md` tem:

- **Cenários de Usuário e Testes** (User Scenarios & Testing): histórias de usuário com
  prioridade (P1 é a mais crítica), cada uma testável de forma independente, com
  **Teste independente** e **Cenários de aceite** no formato Dado/Quando/Então; e **Casos de
  Borda**.
- **Requisitos**: requisitos funcionais `FR-001…` e, quando há dados, **Entidades-Chave**.
- **Critérios de Sucesso**: resultados mensuráveis `SC-001…`, independentes de tecnologia.
- **Suposições** (Assumptions): os padrões escolhidos onde a descrição não disse nada e as
  recomendações adotadas sem resposta no `--auto`.
- **Esclarecimentos** (Clarifications): vazia na primeira versão; a fase de clarify acrescenta
  uma subseção por sessão (`### Sessão AAAA-MM-DD`).

Onde algo não está claro, o agente faz uma suposição informada e a registra em Suposições. O
marcador `[NEEDS CLARIFICATION: pergunta]` só é usado quando a escolha muda escopo,
segurança ou experiência, tem várias leituras razoáveis e nenhum padrão razoável. São **no
máximo 3 marcadores por spec**, resolvidos na hora pela fase de clarify, uma pergunta por
vez.

Depois de escrita, a spec passa pelo laço de qualidade de `checklists/requirements.md` (até
3 iterações). O checklist avalia a qualidade do que está escrito (completo, claro,
consistente, mensurável), não a implementação.

### Branch opcional

A spec **não depende de branch**. Dentro de um repositório git, o plan oferece criar a
branch `NNN-nome-curto`; a resposta fica salva em `.redevkit/memory/active.md` › Preferências
de fluxo (sempre, só desta vez não, ou nunca). Fora de um repositório git, a oferta é pulada.
O kit nunca roda `git init` e nunca faz commit sem você pedir. No template, a linha
`**Branch**` é marcada como opcional e é removida quando nenhuma branch é criada.

### Feature ativa

A feature em andamento é registrada em `.redevkit/memory/active.md`, na linha
`- Feature: specs/NNN-nome`, junto com a fase atual. Todos os comandos leem esse ponteiro.

## Plano

O `plan.md` é escrito pela persona `project-planner` a partir do template:

- **Resumo** (Summary).
- **Contexto Técnico** (Technical Context): linguagem, dependências, armazenamento, testes,
  plataforma, **Tipo de projeto** (Project Type), metas de desempenho, restrições e escala.
  Valores desconhecidos ficam como `NEEDS CLARIFICATION` até a Fase 0. O verify escolhe as
  auditorias pelo Tipo de projeto.
- **Roteamento por Domínio** (Domain Routing): área → persona → skills e referências →
  motivo. As tarefas tiram o `@persona` desta tabela. A escolha segue a fase
  `redevkit-route`.
- **Verificação da Constituição** (Constitution Check): uma linha por princípio, com o que ele
  exige aqui, status `PASS`, `VIOLATION` ou `N/A` e a evidência. O template marca a seção
  como GATE: ela precisa passar antes da pesquisa da Fase 0 e é repetida depois do design da
  Fase 1.
- **Estrutura do Projeto**: a árvore de documentação da feature e o layout real do código.
- **Design Source-of-Truth**: os deltas desta feature no `DESIGN.md` (ver abaixo).
- **Fases de Execução**: Fase 0 (Pesquisa), Fase 1 (Design e Contratos) e Fase 2
  (Planejamento de Tarefas).
- **Controle de Complexidade** (Complexity Tracking): preenchido só quando a Verificação da
  Constituição tem uma violação que precisa ser justificada.
- **Relatório do Plano**: artefatos, resultado da verificação, contagens da análise e o
  status da aprovação (gate G2).

As fases do plano:

1. **Fase 0, Pesquisa:** cada `NEEDS CLARIFICATION` vira um item de pesquisa, consolidado em
   `research.md` com **Decisão**, **Motivo** e **Alternativas consideradas**. Num app novo,
   a skill `app-builder` escolhe a stack e o template de scaffolding.
2. **Fase 1, Design e Contratos:** `data-model.md` (entidades, campos, validações, estados),
   `contracts/` (só quando a feature expõe interfaces) e `quickstart.md` (cenários de
   validação executáveis, que o test e o verify percorrem).
3. **Fase 2, Planejamento de Tarefas:** o `tasks.md`, descrito adiante.

Uma violação da constituição sem justificativa interrompe o plano (gate G3). Uma violação
justificada vai para o Controle de Complexidade e precisa ser aceita por você. Um princípio
nunca é enfraquecido no plano: mudá-lo é uma emenda separada.

Se o `plan.md` já existe, o plan pergunta se deve atualizar (recomendado) ou recriar.

### Gate do `DESIGN.md`

Quando a feature tem interface (telas, componentes, páginas, HUD, views mobile), o plan
segue a skill `design-spec`: cria o `DESIGN.md` na raiz a partir do template `design.md`, ou
o atualiza no lugar. Existe **um único** `DESIGN.md` por projeto, com tokens nomeados (cores,
tipografia, layout, elevação, formas, movimento, componentes) que o código de interface usa
no lugar de valores avulsos. O Purple Ban vale por padrão: roxo e violeta só quando a marca
ou o `DESIGN.md` pedirem.

O `plan.md` ganha a seção **Design Source-of-Truth** com os deltas da feature (tokens,
componentes, telas, estados) e as metas de acessibilidade. Sem interface, a seção diz que
não se aplica.

## Tarefas

O `tasks.md` organiza as tarefas em fases, nesta ordem:

| Fase (pt-BR) | Fase (en) | Conteúdo |
| --- | --- | --- |
| `## Fase 1: Setup` | `## Phase 1: Setup` | Estrutura do projeto e ferramentas; o scaffolding de um app novo |
| `## Fase 2: Fundação` | `## Phase 2: Foundational` | Pré-requisitos que bloqueiam todas as histórias |
| `## Fase 3: US1 - … (Prioridade: P1)` | `## Phase 3: US1 - … (Priority: P1)` | Uma fase por história, em ordem de prioridade |
| `## Fase N: Polimento` | `## Phase N: Polish` | Melhorias que afetam várias histórias |

Trabalho novo entra sempre como uma fase nova no fim (por exemplo `Fase N: Convergência`,
vinda do verify, ou a fase de Enhancement do enhance). Tarefas nunca são renumeradas nem
reordenadas.

Dentro de cada fase de história, com TDD ligado, a subseção **Testes (escrever primeiro,
devem falhar)** vem antes de **Implementação**: cada tarefa de teste tem um VERIFY que diz que
o teste falha antes da implementação, e a última tarefa de implementação tem um VERIFY que
diz que os testes da história passam. Com `**TDD**: waived`, a subseção de testes fica
opcional, mas toda tarefa continua com VERIFY.

### Gramática da linha de tarefa

```text
- [ ] T012 [P] [US1] descrição — caminho — @persona — VERIFY: critério
```

| Parte | Regra |
| --- | --- |
| `- [ ]` | Caixa de seleção. Concluída é `- [X]`, marcada só depois de observar o VERIFY |
| `T012` | ID sequencial com 3 dígitos, em ordem de execução; nunca reutilizado |
| `[P]` | Opcional: a tarefa mexe em arquivos disjuntos das outras tarefas da fase e não depende de tarefa inacabada da fase |
| `[US1]` | Obrigatório nas fases de história; ausente em Setup, Fundação e Polimento |
| descrição | Imperativa, específica, um resultado só |
| caminho | Arquivo ou diretório que a tarefa altera, relativo ao repositório |
| `@persona` | Quem executa, escolhida pelo roteamento |
| `VERIFY:` | Critério observável: um comando e o resultado esperado, ou uma checagem concreta |

Os separadores são ` — ` (espaço, travessão, espaço). `T001`, `[P]`, `[US1]`, `@persona` e
`VERIFY:` são tokens estruturais e ficam iguais em qualquer idioma; só a descrição e o
critério são escritos no idioma do projeto.

## Análise

Antes da aprovação, a fase `redevkit-analyze` lê `spec.md`, `plan.md` e `tasks.md` sem
alterar nada e procura duplicação, ambiguidade, lacunas de cobertura e conflitos com a
constituição. Os achados têm severidade `CRITICAL`, `HIGH`, `MEDIUM` ou `LOW`. Violar um
princípio DEVE (inclusive faltar o teste que falha primeiro com TDD ligado) é sempre
`CRITICAL`. O plan corrige os achados críticos e roda a análise de novo, até 3 rodadas.

Quando o risco pede (autenticação, pagamentos, dados pessoais, API pública, interface
pesada), o plan também gera um checklist de domínio em `checklists/<domínio>.md`.

O plan termina na **aprovação do plano** (gate G2): resumo da feature, stack e Tipo de
projeto, resultado da Verificação da Constituição, deltas de design, tarefas por fase,
resultado da análise e suposições.

## Implementação

O `redevkit-create` (feature nova) e o `redevkit-enhance` (mudança no que existe) usam o
mesmo motor:

- As fases rodam em ordem: Setup → Fundação → US1..n → Polimento; uma fase começa quando
  todas as tarefas da anterior estão `[X]` ou bloqueadas (`[!]`).
- Cada tarefa é delegada à persona do campo `@persona`: no Claude Code pela ferramenta Agent
  com o subagente da persona; no Codex por `spawn_agent` ou, se o projeto não for confiável,
  aplicando a persona inline a partir do TOML.
- Tarefas `[P]` com arquivos disjuntos rodam em paralelo; o resto roda em ordem.
- Com TDD ligado, os testes da história são escritos, executados e vistos falhando pelo motivo
  esperado antes da implementação.
- Trabalho de interface usa os tokens do `DESIGN.md`.
- Uma tarefa vira `[X]` só depois que o critério VERIFY foi observado.
- Uma tarefa que continua falhando depois do limite de tentativas vira `[!]` (bloqueada), com
  uma linha `BLOCKED AAAA-MM-DD: motivo; needs: o que a desbloqueia` logo abaixo. As tarefas
  que dependem dela são puladas. Nenhum comando tenta uma tarefa bloqueada de novo sozinho: ela
  só roda outra vez com `redevkit-create --retry-blocked` (ou quando você a nomeia), e a
  cadeia `--auto` para enquanto houver tarefa bloqueada.

O enhance registra a mudança como delta datado na spec (`## Enhancements` › `### AAAA-MM-DD —
título`) e anexa as tarefas numa fase nova; se não houver feature correspondente, cria uma
spec leve. Uma mudança grande (nova história de usuário, mudança de modelo de dados, de
arquitetura ou de contrato público, ou cerca de 10 tarefas ou mais) é redirecionada para o
plan.

Create, enhance e debug terminam com uma **verificação leve** nos arquivos alterados: build ou
checagem de tipos, os testes tocados e o lint. A verificação completa é o
`redevkit-verify`.

## Verificação por execução

Nenhum comando declara sucesso sem evidência: o comando que rodou e o resultado observado
(código de saída, contagens de teste, status HTTP). Uma checagem que não rodou aparece como
`SKIPPED (motivo)`, nunca como `PASS`.

- **Test** (`redevkit-test`): mapeia cada cenário de aceite da spec (e do `quickstart.md`)
  para um teste, gera os que faltam sem mexer no código da aplicação e roda a suíte completa,
  pelo `test_runner.py` quando há Python ou pelo comando de teste do projeto, sempre de forma
  não interativa e com limite de tempo. O veredito é
  `PASS` só quando todos os comandos saíram com 0, nenhum teste falhou e todo cenário
  automatizável mapeia para um teste que passa; qualquer outra coisa é `FAIL`. Um cenário
  que não dá para automatizar no ambiente fica `SKIPPED (motivo)` em **Não verificado**: não
  reprova a execução e nunca conta como `PASS`. Toda falha recebe uma classe, e o handoff
  segue a classe (ver [Classes de falha](#classes-de-falha)).
- **Debug** (`redevkit-debug`): reproduz o problema, testa hipóteses com evidência, escreve
  primeiro o teste de regressão que falha, aplica a menor correção e confirma. O resultado do
  bug é `verified`, `partial` ou `failed`. Qualquer que seja o resultado, o debug termina,
  marca `- Verify pending:` no `active.md` e segue para o verify, que é obrigatório depois de
  um debug. Quando a causa não é um bug do código (o teste está errado, o comportamento nunca
  foi construído, o ambiente não deixa a suíte rodar), o debug para sem corrigir e devolve ao
  test, ao create ou a você.
- **Verify** (`redevkit-verify`): começa pelos testes. Se a última execução da feature
  inteira (escopo `feature`) no `test-report.md` foi sobre o mesmo estado do código atual (o
  mesmo Tree fingerprint), ela é reaproveitada (um `PASS`
  segue, um `FAIL` encerra com `failed`); senão, o verify executa o procedimento do
  `redevkit-test` e grava a execução no `test-report.md`. Como o debug muda o
  código, depois dele os testes rodam de novo, inclusive quando a correção está num arquivo
  novo, ainda fora do git; se a correção não mudou nada, o `FAIL` é
  reaproveitado e conta como failed após debug (um debug que não reproduz o problema para e
  não segue para o verify). Com os testes
  verdes, a fase `redevkit-converge` compara o código com spec, plano e tarefas, e cada lacuna
  vira uma tarefa anexada na fase de Convergência; depois vêm a execução real (build e, quando
  o Tipo de projeto tem runtime, subir a aplicação e percorrer os fluxos críticos do
  `quickstart.md`, sem rodar a suíte de novo) e as auditorias (uma execução de
  `verify_all.py` ou `checklist.py`, ou `SKIPPED` sem Python). As auditorias julgam o código
  que a feature escreveu: só os achados em arquivos que ela criou ou alterou viram tarefa ou
  `failed`; achados no resto do projeto são **linha de base** (dívida que já existia) e achados
  em código de terceiros ou gerado ficam fora do escopo, e nenhum dos dois muda o veredito. O veredito é `converged+verified`, `gaps` ou
  `failed`. Uma spec leve do enhance (sem `plan.md`) também é verificada: o contexto técnico
  vem do `tech.md`.

### Classes de falha

Um teste vermelho tem mais de uma causa, e cada causa tem um dono. O `redevkit-test` dá uma
classe a cada falha e a registra no relatório (**Failure class**); o handoff segue a classe:

| Classe | Quando | Para onde vai |
| --- | --- | --- |
| `environment` | A suíte não rodou ou não terminou: dependência ou ferramenta ausente, quebra antes de qualquer teste, tempo esgotado (`[TIMEOUT]`), porta ocupada | Não é bug. Corrige-se o ambiente e roda-se o test de novo; nunca vai para o debug |
| `test-defect` | O teste está errado: contradiz a spec ou falha por erro próprio | O próprio test corrige o teste (nunca o código), citando o cenário da spec como evidência, e roda a suíte mais uma vez |
| `not-implemented` | O comportamento pertence a uma tarefa aberta `[ ]` ou bloqueada `[!]` | `redevkit-create` |
| `product-defect` | O teste bate com a spec e o código se comporta de outro jeito | `redevkit-debug` |

O veredito da execução continua sendo `PASS` ou `FAIL`: uma suíte que não rodou nunca é
verde. O que muda é o caminho de saída.

### Verify pendente

A linha `- Verify pending:` em `.redevkit/memory/active.md` › Últimos resultados diz que a
feature precisa de um verify que termine em `converged+verified` antes do deploy. É uma
bandeira, então nenhum comando compara datas para saber o que veio antes:

- o debug a liga (`debug <slug>`) quando muda código;
- o verify a liga quando termina em `gaps` ou `failed`;
- só um verify `converged+verified` a desliga (`no`).

Enquanto ela está ligada, um test `PASS` aponta para o verify (não para o deploy), o
`--auto` segue até ele e o deploy fica `BLOCKED`. Assim o laço
gaps → create → test → verify se fecha sozinho, limitado pelo ciclo de correção.

### Ciclo de correção e G5

Esta seção é a referência da documentação para o G5; a regra exata está no passo 6 do
`redevkit-verify`. O verify mantém dois contadores da feature ativa em
`.redevkit/memory/active.md` › Últimos resultados, na linha `- Correction cycle:`:

- **failed após debug:** soma 1 quando o veredito é `failed` e o verify começou com a
  bandeira `Verify pending` em `debug <slug>`, seja qual for o teste ou o bug; zera com
  `converged+verified` ou `gaps`.
- **rodadas sem convergir:** soma 1 a cada veredito diferente de `converged+verified`; só zera
  com `converged+verified`. Execuções de testes não mexem nele, então o ciclo
  gaps → create → test → verify também chega ao limite.

Um `failed` que só reaproveitou um `FAIL` sem debug no meio não altera os contadores, nem um
`failed` cuja única classe de falha é `environment` (o código não chegou a ser julgado). Os dois
zeram quando a feature ativa muda ou quando você escolhe continuar no G5. O G5 dispara com 2
failed após debug ou 3 rodadas sem convergir. A cadeia para, mesmo no `--auto`, e pergunta:

1. Revisar o plano (recomendado): zera os contadores e segue para o `redevkit-plan`.
2. Continuar: zera os contadores e segue o handoff normal.
3. Parar: o G5 fica pendente; o próximo verify ou debug pergunta de novo.

Assim, nenhum caminho do pipeline fica em loop.

### Estado do código

Os relatórios de test e verify registram o **estado do código** de cada execução: commit
(HEAD), branch, árvore de trabalho (clean ou dirty), arquivos alterados e o **Tree
fingerprint**, calculado por `.redevkit/audits/code_state.py`. O fingerprint é um hash do
conteúdo dos arquivos do projeto (sem `.redevkit/`, `specs/`, as pastas dos agentes,
dependências e saída de build): muda quando qualquer arquivo é criado, apagado ou editado,
rastreado pelo git ou não, e não depende do shell, do histórico de commits nem de existir
git. Dois estados são o mesmo quando o fingerprint é igual; um commit feito depois do teste
não o altera. O verify usa esse valor para decidir se reaproveita a última execução de
testes. Sem Python o fingerprint fica `n/a`, nada é reaproveitado e o deploy pede que você
instale o Python ou confirme por override. O deploy faz assim:

- **Verify pendente** (depois de um debug, ou de um verify que terminou em `gaps` ou
  `failed`): `BLOCKED` até um `redevkit-verify` terminar em `converged+verified`.
- Senão, a referência é a **última** execução da feature inteira no `test-report.md` (escopo
  `feature`, avulsa ou feita pelo passo 1 do verify), que precisa ser `PASS` e ter o mesmo
  estado do código atual. Execuções de um arquivo ou cenário isolado não valem como referência.

Qualquer outra situação deixa o deploy `BLOCKED`. A única saída é um override com o motivo
registrado no relatório (`OVERRIDDEN`), e mesmo assim a confirmação do gate G6 continua.

## Relatórios

| Relatório | Onde | Regra |
| --- | --- | --- |
| Testes | `specs/NNN-nome/test-report.md` | Somente acréscimo: uma seção datada por execução, com estado do código, comandos, resultados, cobertura dos cenários e veredito `PASS` ou `FAIL` |
| Verificação | `specs/NNN-nome/verification.md` | Somente acréscimo: estado do código, evidência de testes (execução usada e se foi reaproveitada), convergência, evidência de execução, auditorias, lista do que não foi verificado e veredito |
| Bug | `.redevkit/bugs/<slug>/assessment.md`, `fix.md`, `test.md` | Avaliação (reprodução, hipóteses, causa raiz), correção (teste de regressão escrito primeiro) e confirmação |
| Avaliação de ideia | `.redevkit/assessments/<slug>/intake.md`, `research.md`, `definition.md`, `shape.md`, `decision.md` | Decisão `go`, `needs-clarification` ou `kill` |
| Deploy | `.redevkit/deploys/AAAA-MM-DD-<ambiente>.md` | Pré-condições, plano de deploy, plano de rollback, confirmação de produção, execução, smoke test e desfecho `succeeded`, `failed`, `rolled-back` ou `aborted` |

Os vereditos e status (`PASS`, `FAIL`, `SKIPPED`, `converged+verified`, `gaps`, `failed`,
`verified`, `partial`, `go`, `kill` e os demais) ficam em inglês em qualquer idioma, para
que outros comandos consigam lê-los.

## Gates

Gate é um ponto onde a cadeia sempre para e espera você, inclusive com `--auto`:

| Gate | Quando |
| --- | --- |
| G1 | Criação ou emenda da constituição |
| G2 | Aprovação do plano (fim do `redevkit-plan`) |
| G3 | Violação da constituição detectada em qualquer fase |
| G4 | Ação destrutiva ou irreversível |
| G5 | Ciclo de correção sem convergir (ver [Ciclo de correção e G5](#ciclo-de-correção-e-g5)) |
| G6 | Deploy (só você dispara) |
| G7 | Escolha sobre memória legada |

Fora dos gates, as perguntas seguem uma política única: só o que muda escopo ou arquitetura,
uma pergunta por vez, no máximo 3 opções com a recomendada primeiro, no máximo 5 perguntas
por comando, e toda suposição registrada.

## Modo `--auto`

`redevkit-new`, `redevkit-brainstorm`, `redevkit-plan`, `redevkit-create`,
`redevkit-enhance`, `redevkit-test`, `redevkit-debug` e `redevkit-verify` aceitam `--auto`.
Com ele, a cadeia segue sozinha:

```text
new → plan → create | enhance → test
  tarefa bloqueada no create ou no enhance → para e lista o que cada uma precisa
  test PASS, sem verify pendente → para e sugere verify e deploy
  test PASS, com verify pendente → verify
  test FAIL, por classe de falha:
    product-defect  → debug → verify (que roda os testes de novo)
    not-implemented → create → test
    environment     → para e diz o que corrigir no ambiente
  verify converged+verified → para antes do deploy
  verify gaps → create → test → verify
  verify failed → debug de novo (ou create, ou para, conforme a classe)
  G5 (ciclo de correção sem convergir) → para e pergunta
```

No `--auto`, a descrição dada ao `redevkit-new` vira a primeira feature (MVP) do plan, e as
perguntas fora dos gates são respondidas com a recomendação e registradas como suposições
(na seção Suposições da spec ou no relatório). A cadeia para em todos os gates: o plano
precisa da sua aprovação (G2) mesmo no `--auto`. O deploy nunca faz parte da cadeia.

## Handoff

Todo comando termina com uma seção de handoff: o próximo comando e o motivo. Por exemplo, o
test verde aponta para o deploy (sugerindo o verify antes) ou, com um verify pendente, para o
verify; o test vermelho aponta para o comando que a classe da falha indica; e o debug sempre
aponta para o verify. O `redevkit-status` sugere o próximo comando a
partir dos fatos que leu.
