# Referência dos comandos

Os 11 comandos do pipeline e a skill de memória. Cada seção resume a skill instalada (o
`SKILL.md` em `kit/commands/` e `kit/memory/`); em caso de dúvida, vale a skill.

Como invocar:

- **Claude Code:** `/redevkit-<nome>`, seguido do texto livre. Exemplo:
  `/redevkit-plan --auto login com e-mail e senha`.
- **Codex:** `$redevkit-<nome>`, seguido do texto livre. Exemplo:
  `$redevkit-plan --auto login com e-mail e senha`.

Regras comuns a todos os comandos:

- **Início:** fase 1 da memória (leitura de `MEMORY.md`, `active.md` e das invariantes do
  `system.md`; a constituição antes de plan, create, enhance, debug e deploy). Linha
  canônica: `📖 Memória carregada. Último registro: AAAA-MM-DD.`
- **Fim:** fase 3 da memória nos comandos que modificam algo (linha `💾 Memória atualizada
  (arquivos).`) e uma seção de **handoff** com o próximo comando e o motivo.
- **Perguntas:** só o que muda escopo ou arquitetura, uma por vez, no máximo 3 opções com a
  recomendada primeiro, no máximo 5 por comando. Subagentes nunca perguntam. No `--auto` ou
  em execução não interativa, a recomendação é adotada e registrada como suposição, exceto nos
  gates.
- **Evidência:** nada é declarado pronto, corrigido ou passando sem o comando executado e o
  resultado observado.
- **Templates:** `.redevkit/templates/overrides/<nome>` quando existe; senão
  `.redevkit/templates/<nome>`.
- **Idioma:** artefatos no idioma do projeto (gravado no manifesto); respostas no idioma do
  usuário.

Os gates G1–G7 estão descritos em [metodo.md](metodo.md#gates).

## redevkit-new

- **Propósito:** inicializar o projeto uma vez: decidir se é novo ou existente, criar ou
  carregar a memória, importar memória legada se você quiser, detectar o domínio e ratificar
  a constituição. Não escreve spec nem código, não roda `git init` e não faz commit.
- **Entrada:** `[--auto] [new|existing] [descrição do projeto]`.
- **Pré-condições:** `.redevkit/manifest.json` existe (gravado pelo `redevkit init`).
- **Passos principais:**
  1. Detecta código, manifestos, memória do REDEVKIT, memória legada e git (só leitura).
  2. Pergunta se o projeto é novo ou existente, com recomendação baseada no que encontrou.
  3. Se a memória já existe, oferece: ressincronizar (recomendado), emendar a constituição
     ou sair.
  4. Cria os arquivos de núcleo da memória a partir dos templates do idioma.
  5. Memória legada (`memory-bank/`, `.agents/memory/`, `.specify/memory/`): mostra o mapa
     e pergunta entre importar e arquivar, importar e manter os originais, ou não importar.
  6. Projeto existente: descoberta com `explorer-agent` e `code-archaeologist`, gravando só
     fatos explícitos e citando a fonte; o resto recebe `<PENDENTE DE ENTREVISTA — motivo>`.
     Projeto novo: entrevista curta de até 5 perguntas.
  7. Detecta o domínio pelo roteador e usa as skills de domínio só para propor princípios e
     restrições técnicas.
  8. Constituição v1.0.0 com Test-First por padrão.
  9. Atualiza `active.md` e o índice `MEMORY.md`.
- **Grava:** `.redevkit/memory/` (`MEMORY.md`, `constitution.md`, `project.md`,
  `system.md`, `tech.md`, `active.md`, `changelog.md`, `user.md`) e, quando escolhido,
  `.redevkit/memory/archive/<origem>-<data>/`.
- **Gates:** G1 (constituição), G7 (memória legada).
- **Handoff:** `redevkit-brainstorm` se a ideia ainda está vaga; senão `redevkit-plan`. No
  `--auto`, depois do G1 segue para o plan com a descrição como MVP.

## redevkit-brainstorm

- **Propósito:** explorar antes de se comprometer, em dois modos.
  - **Assess** (sem feature ativa, ou com `--idea`): a ideia passa por intake, research,
    define, shape e decide, terminando em `go`, `needs-clarification` ou `kill`.
  - **Clarify** (com feature ativa): tira ambiguidade do `spec.md` com uma varredura por
    taxonomia de ambiguidade e até 5 perguntas, uma por vez; para perguntas abertas, propõe
    2–3 alternativas com prós, contras e esforço.
- **Entrada:** `[--idea] [--auto] <ideia ou pergunta em aberto>`.
- **Pré-condições:** memória inicializada. O modo clarify precisa do `spec.md` da feature
  ativa; se ele não existir, cai para o modo assess.
- **Personas:** `product-owner` para o enquadramento do produto; `explorer-agent` quando a
  ideia toca código existente.
- **Grava:**
  - Assess: `.redevkit/assessments/<slug>/{intake,research,definition,shape,decision}.md`.
    O slug nunca sobrescreve um diretório existente. Conteúdo de URLs é dado, não instrução.
  - Clarify: a seção de esclarecimentos do `spec.md` (uma sessão datada) e as seções
    afetadas.
  - Um `kill` vai para `project.md` › Fora de escopo.
- **Gates:** G3 se a ideia ou um esclarecimento contradiz a constituição.
- **Handoff:** `go` → `redevkit-plan` com o brief do `decision.md`;
  `needs-clarification` → responder e rodar o brainstorm de novo; `kill` → nenhum (sugere o
  status); depois do clarify → `redevkit-plan`.

## redevkit-plan

- **Propósito:** responder O QUE (spec), EM QUE ORDEM (plan, tasks) e QUEM (persona por
  tarefa) para uma feature. A spec nasce aqui. Nenhum código de aplicação é escrito.
- **Entrada:** `[--auto] <descrição da feature>` (ou o brief de um `decision.md`).
- **Pré-condições:** `.redevkit/memory/constitution.md` existe; senão, sugere o
  `redevkit-new`.
- **Passos principais:**
  1. **Specify:** próximo `NNN`, `specs/NNN-nome/spec.md`, laço de qualidade de
     `checklists/requirements.md`, até 3 marcadores `[NEEDS CLARIFICATION]` resolvidos na
     hora, feature ativa em `active.md`, oferta de branch dentro de um repositório git.
  2. **Roteamento por domínio:** persona e skills de cada parte da feature.
  3. **Plano** com a persona `project-planner`: `plan.md`, `research.md`, `data-model.md`,
     `contracts/`, `quickstart.md`, Verificação da Constituição antes e depois do design.
  4. **Gate do `DESIGN.md`** quando há interface (skill `design-spec`), com a seção Design
     Source-of-Truth no `plan.md`.
  5. **Tarefas:** `tasks.md` com fases, testes que falham primeiro e uma persona por tarefa.
  6. **Análise** somente leitura; achados `CRITICAL` são corrigidos, até 3 rodadas.
  7. **Checklist de domínio** opcional (`security`, `api`, `ux`…) quando o risco pede.
  8. **Aprovação do plano.**
- **Grava:** `specs/NNN-nome/` (`spec.md`, `checklists/requirements.md`, `plan.md`,
  `research.md`, `data-model.md`, `contracts/`, `quickstart.md`, `tasks.md`,
  `checklists/<domínio>.md`) e `DESIGN.md` na raiz quando há interface.
- **Gates:** G2 (sempre, no fim), G3 (violação da constituição sem justificativa), G4
  (recriar um `plan.md` existente ou reescrever seções do `DESIGN.md` de outras features).
- **Handoff:** aprovado → `redevkit-create`; spec ainda ambígua → `redevkit-brainstorm` em
  modo clarify. No `--auto`, depois da aprovação segue para o create.

## redevkit-create

- **Propósito:** construir uma feature nova, inclusive o scaffolding, a partir do
  `tasks.md` aprovado. O orquestrador entrega cada tarefa à persona indicada nela, história
  por história, testes primeiro.
- **Entrada:** `[--auto] [--retry-blocked] [faixa de tarefas, por exemplo T001-T020]`. Sem
  faixa, todas as tarefas abertas; as bloqueadas (`[!]`) só rodam de novo com
  `--retry-blocked` ou quando você as nomeia.
- **Pré-condições:** feature ativa com o plano aprovado no G2; `spec.md`, `plan.md` e
  `tasks.md` existem; para tarefas de interface, o `DESIGN.md` existe.
- **Passos principais:** checa checklists abertos; scaffolding com o template do
  `app-builder` (só em pasta vazia ou nova); implementação fase por fase com
  `redevkit-implement` e `redevkit-orchestrate`; `[P]` em paralelo quando os arquivos são
  disjuntos; tarefa vira `[X]` só depois do VERIFY observado, e `[!]` (bloqueada, com o
  motivo e o que ela precisa) quando o limite de tentativas acaba; verificação leve (build ou
  checagem de tipos, testes tocados, lint dos arquivos alterados).
- **Grava:** código e testes nos caminhos das tarefas; `tasks.md` com as tarefas marcadas.
- **Gates:** G3 (tarefa que violaria a constituição), G4 (sobrescrever arquivos, apagar
  dados, ação irreversível).
- **Handoff:** tudo pronto → `redevkit-test`; tarefas abertas que ainda podem rodar →
  `redevkit-create` de novo; tarefas bloqueadas → pergunta: resolver o que elas precisam e
  rodar com `--retry-blocked`, revisar o plano ou seguir para o test. O comando nunca aponta
  para si mesmo sem que algo tenha mudado. No `--auto`, segue para o test; com tarefa
  bloqueada, a cadeia para.

## redevkit-enhance

- **Propósito:** mudar algo que já existe. Registra a mudança como delta datado na spec,
  anexa tarefas e as implementa com o mesmo motor do create.
- **Entrada:** `[--auto] <descrição da mudança>`.
- **Pré-condições:** memória inicializada; existe código para mudar (num projeto vazio,
  sugere o plan).
- **Passos principais:**
  1. `code-archaeologist` analisa a área afetada junto com a memória e aponta conflitos com
     a stack ou com invariantes.
  2. Localiza a feature em `specs/`. Se existe: seção `## Enhancements` datada na spec e uma
     fase nova de Enhancement no `tasks.md`. Se não existe: spec leve num novo
     `specs/NNN-nome/`, que vira a feature ativa.
  3. Mudança grande (nova história de usuário, modelo de dados, arquitetura, contrato
     público, ou cerca de 10 tarefas ou mais): recomenda o plan e pergunta.
  4. Apresenta o plano da mudança e pede aprovação.
  5. Implementa a fase anexada (persona por tarefa, testes primeiro) e faz a verificação
     leve.
- **Grava:** `spec.md` (seção de enhancements) e `tasks.md` (fase anexada), ou a spec leve;
  código e testes.
- **Gates:** G3 (mudança viola a constituição), G4 (apagar arquivos ou dados, migrations
  destrutivas).
- **Handoff:** pronto → `redevkit-test`; redirecionado → `redevkit-plan` com o delta
  rascunhado. No `--auto`, segue para o test (ou para o plan, quando a mudança é grande).

## redevkit-test

- **Propósito:** provar a feature contra a spec. Mapeia cada cenário de aceite para um teste,
  gera os que faltam, roda a suíte completa, classifica as falhas e anexa uma execução datada
  ao relatório. Não muda código da aplicação.
- **Entrada:** `[--auto] [feature, arquivo ou cenário]`. Padrão: a feature ativa.
- **Pré-condições:** memória inicializada; feature com `spec.md`. Sem nenhuma feature, roda só
  a suíte e sugere o plan.
- **Personas e skills:** `test-engineer` (unidade e integração), `qa-automation-engineer` com
  `webapp-testing` (fluxos end-to-end); `testing-patterns` e `tdd-workflow` para gerar
  testes.
- **Passos principais:** tabela cenário → teste (`covered` ou `missing`); gera os testes
  faltantes sem enfraquecer testes existentes; roda `.redevkit/audits/test_runner.py` quando
  há Python, senão o comando de teste do `tech.md` (detectado e registrado se faltar), sempre
  sem modo watch, com limite de tempo e com a saída completa em
  `.redevkit/tmp/test-output.log`; dá a cada falha uma
  [classe](metodo.md#classes-de-falha) (`environment`, `test-defect`, `not-implemented`,
  `product-defect`), corrigindo ali mesmo o que é do ambiente ou do próprio teste; grava o
  estado do código com o `code_state.py` (HEAD, branch, árvore, Tree fingerprint).
- **Grava:** novos testes e `specs/NNN-nome/test-report.md` (somente acréscimo).
- **Veredito:** `PASS` só quando todos os comandos saíram com 0, nenhum teste falhou e todo
  cenário automatizável mapeia para um teste que passa; senão `FAIL`. Cenários que não dá para
  automatizar ficam `SKIPPED (motivo)` em Não verificado e nunca contam como `PASS`.
- **Dentro do verify:** os passos acima também são o passo 1 do `redevkit-verify`, que os
  executa sem as fases de memória e o handoff próprios, marcando a execução com
  "Executado por: redevkit-verify (step 1)".
- **Gates:** G4 (testes que usam serviços externos reais, bancos reais ou apagam dados), G3
  (requisito só testável violando a constituição).
- **Handoff:** `PASS` com [verify pendente](metodo.md#verify-pendente) → `redevkit-verify`;
  `PASS` sem pendência → `redevkit-deploy` (por você), sugerindo o `redevkit-verify` antes
  (um verify logo em seguida, sobre o mesmo código, reaproveita esta execução). `FAIL` segue a
  classe da falha: `environment` → corrigir o ambiente e rodar o test de novo;
  `not-implemented` → `redevkit-create`; `product-defect` → `redevkit-debug`. No `--auto`, a
  cadeia segue esses mesmos caminhos e para no `PASS` sem pendência, na falha de ambiente e
  quando só restam tarefas bloqueadas.

## redevkit-debug

- **Propósito:** investigar e corrigir um problema com evidência: reproduzir, achar a causa
  raiz, escrever o teste de regressão que falha, corrigir e confirmar.
- **Entrada:** `[--auto] <sintoma, erro ou teste que falha>`. Sem entrada, usa os testes que
  falharam na última execução `FAIL` do `test-report.md`.
- **Pré-condições:** memória inicializada; um sintoma (a entrada ou uma execução `FAIL`). Se
  o `active.md` mostra o G5 atingido e ainda sem resposta, apresenta a pergunta do G5 antes
  de começar.
- **Passos principais:**
  1. Slug do sintoma. Um bug aberto equivalente só é continuado quando o debug anterior foi
     interrompido (falta `fix.md` ou `test.md`); se o `test.md` já existe, abre um bug novo
     ligado a ele.
  2. `redevkit-bug-assess` com a persona `debugger` e a skill `systematic-debugging`:
     reprodução por comando, hipóteses testadas, causa raiz explicada.
  3. `redevkit-bug-fix`: teste de regressão primeiro (visto falhando), menor correção que
     ataca a causa raiz, teste passando, prevenção quando a causa pode voltar.
  4. `redevkit-bug-test`: resultado `verified`, `partial` ou `failed`. Um `failed` não abre
     outra avaliação dentro do mesmo debug: o próximo debug, depois do verify, abre um bug
     novo ligado a este.
  5. Verificação leve.
- **Grava:** `.redevkit/bugs/<slug>/assessment.md`, `fix.md`, `test.md`; o teste de
  regressão e a correção; as linhas Debug e `Verify pending` de `active.md` › Últimos
  resultados (a segunda é como o verify sabe que veio depois de um debug e o que mantém o
  deploy bloqueado até lá).
- **Gates:** G3 (correção violaria a constituição), G4 (passos destrutivos ou irreversíveis),
  G5 (atingido e ainda sem resposta).
- **Handoff:** `redevkit-verify`, qualquer que seja o resultado do `test.md`. Quando a causa
  não é um bug do código, o debug para antes de corrigir: teste errado → `redevkit-test`;
  comportamento nunca construído → `redevkit-create`; ambiente → você.

## redevkit-verify

- **Propósito:** a verificação completa: testes sobre o código atual, convergência do código
  com spec, plano e tarefas, execução real e auditorias, com um veredito ligado ao estado do
  código. Obrigatório depois de um debug; sugerido depois de um test `PASS`, antes do deploy.
- **Entrada:** `[--auto] [feature ou escopo]`. Padrão: a feature ativa e o que mudou desde a
  última verificação.
- **Pré-condições:** memória inicializada; feature com `spec.md`, `plan.md` e `tasks.md` (uma
  spec leve do enhance não tem `plan.md`: o Tipo de projeto vem do `tech.md`). Sem feature, a
  convergência fica `SKIPPED (no feature spec)`, nada é gravado em relatório e o `--auto` não
  continua. G5 atingido para a feature ativa e sem resposta → apresenta a pergunta de novo.
- **Passos principais:**
  1. Testes: compara o Tree fingerprint do código atual com o da última execução da feature
     inteira (Escopo `feature`) do `test-report.md`.
     `PASS` sobre o mesmo código → reaproveita, sem rodar de novo. `FAIL` sobre o mesmo código
     → reaproveita e o veredito é `failed`. Qualquer outro caso (por exemplo, depois de um
     debug) → executa o procedimento do `redevkit-test` e grava a execução no
     `test-report.md`; um `FAIL` encerra a verificação com `failed`.
  2. `redevkit-converge`: cada lacuna vira uma tarefa anexada na fase de Convergência do
     `tasks.md` (somente acréscimo).
  3. Execução: build e, quando o Tipo de projeto tem runtime, subir a aplicação em segundo
     plano, percorrer os fluxos críticos do `quickstart.md` e parar; para correções de bug,
     reproduzir o cenário original. A suíte não roda de novo: a evidência é a do passo 1.
  4. Auditorias: uma execução de `verify_all.py` ou `checklist.py` conforme o Tipo de
     projeto (`--no-runtime` quando não há app rodando; sempre `--no-tests`, pois o passo 1
     já é a evidência dos testes). Caminhos fora do escopo vão em `.redevkit/audit-ignore`
     ou `--exclude`. Sem Python: `SKIPPED (no Python
     interpreter)` mais o lint e a checagem de tipos do projeto. Só os achados em arquivos
     que a feature criou ou alterou contam; achados no resto do projeto são linha de base e
     achados em código de terceiros ou gerado ficam fora do escopo: nenhum dos dois vira
     tarefa nem `failed`.
  5. Relatório com o veredito `converged+verified`, `gaps` ou `failed`.
  6. `Verify pending` e ciclo de correção em `active.md` (regras em
     [metodo.md](metodo.md#verify-pendente)).
- **Grava:** `specs/NNN-nome/verification.md` (somente acréscimo); `test-report.md` e testes
  novos quando o passo 1 executa o procedimento do test; havendo lacunas, a fase de
  Convergência no `tasks.md`. Não edita código da aplicação.
- **Gates:** G5 (ciclo de correção sem convergir), G4 (testes ou fluxos que escrevem em
  sistemas externos reais ou apagam dados), G3 (requisito só testável violando a
  constituição).
- **Handoff:** `converged+verified` → `redevkit-deploy` (por você); `gaps` →
  `redevkit-create`, ou `redevkit-enhance` quando a lacuna pede mudança na spec (o test que
  vem depois devolve ao verify); `failed` → `redevkit-debug`, ou `redevkit-create` quando a
  falha é `not-implemented`, ou corrigir o ambiente quando é `environment`; G5 atingido →
  para e espera a sua resposta.

## redevkit-preview

- **Propósito:** rodar a aplicação localmente para você ver, só com as ferramentas nativas do
  agente: detecta o comando de dev e a porta, sobe o servidor em segundo plano, faz um
  healthcheck HTTP e informa a URL.
- **Entrada:** `[start|stop|status|restart] [porta]`. Padrão: `status`.
- **Pré-condições:** o projeto tem algo executável (script de dev, ponto de entrada de
  framework ou um `index.html` estático).
- **Passos principais:** detecção pelo `tech.md`, pelos scripts do `package.json`, pelas
  convenções do framework ou perguntando; no Claude Code, Bash em segundo plano; no Codex, o
  comando de segundo plano do sistema operacional com o PID em `.redevkit/tmp/preview.pid`;
  saudável é qualquer status HTTP abaixo de 500. `status` só checa porta, processo e HTTP;
  `stop` encerra a árvore de processos; `restart` é stop e start.
- **Grava:** só `.redevkit/tmp/preview.log` e `.redevkit/tmp/preview.pid` (efêmeros, fora do
  git). Não grava memória nem relatório.
- **Gates:** G4 para encerrar um processo que este comando não iniciou.
- **Handoff:** preview saudável → você confere; para provar os fluxos, `redevkit-verify`.
  Falha ao subir → `redevkit-debug` com o trecho do log. Não faz parte do `--auto`.

## redevkit-deploy

- **Propósito:** levar o código testado a um ambiente, com plano de deploy, plano de
  rollback, confirmação explícita e smoke test. Só você inicia este comando: ele nunca é
  invocado pelo modelo, nunca entra no `--auto` e nunca é disparado pelo handoff de outro
  comando. No Claude Code, a skill tem `disable-model-invocation: true`; no Codex,
  `allow_implicit_invocation: false`.
- **Entrada:** `[staging|production|<ambiente>] [--check | --rollback]`. `--check` roda só as
  pré-condições e o pre-flight; `--rollback` executa o plano de rollback do último relatório
  daquele ambiente.
- **Pré-condições:**
  1. Invocado por você neste turno.
  2. Memória inicializada.
  3. Evidência verde sobre o código atual, pela regra de
     [Estado do código](metodo.md#estado-do-código): com verify pendente, `BLOCKED` até um
     verify `converged+verified`; senão, a última execução da feature inteira no
     `test-report.md` precisa ser `PASS` e ter o Tree fingerprint do código atual. A única
     saída é `OVERRIDDEN`, com o seu motivo registrado.
  4. Se o último verify não é `converged+verified` sobre este mesmo código, pergunta se você
     quer rodar o verify antes (recomendado).
- **Passos principais:** ambiente e plataforma (pelo `tech.md` ou pelos arquivos de deploy
  do projeto); plano com a persona `devops-engineer` e as skills `deployment-procedures` e
  `server-management` (pre-flight, plano de deploy, plano de rollback); rascunho do
  relatório; confirmação; execução passo a passo; smoke test; desfecho.
- **Produção:** exige uma confirmação que nomeie o ambiente ("deploy to production"); um
  "sim" genérico não basta.
- **Grava:** `.redevkit/deploys/AAAA-MM-DD-<ambiente>.md` (nunca sobrescreve: acrescenta
  `-2`, `-3`…). Nunca grava segredos.
- **Gates:** G6 (o comando todo e a confirmação), G4 (passos irreversíveis, rollback,
  migrations de dados), G3 (plano que viola a constituição).
- **Handoff:** `succeeded` → `redevkit-status` ou `redevkit-plan` para a próxima feature;
  `failed` ou `rolled-back` → `redevkit-debug`; `BLOCKED` → `redevkit-verify` quando há um
  verify pendente, senão `redevkit-test`; `aborted` →
  nada mudou.

## redevkit-status

- **Propósito:** mostrar onde o projeto está usando só fatos lidos de arquivos e de comandos
  somente leitura. Nunca inventa agentes rodando, percentuais ou resultados.
- **Entrada:** `[feature]` para reportar outra feature em vez da ativa.
- **Pré-condições:** nenhuma. Sem `.redevkit/memory/`, informa que a memória não foi
  inicializada.
- **Mostra:** último registro da memória; feature ativa e fase; progresso do `tasks.md` por
  fase, com as tarefas bloqueadas; aprovação do plano; último test (quem o executou e a
  classe da falha), último verify, último debug, o verify pendente e o ciclo de correção; se o código mudou desde o último test; bugs abertos; avaliações pendentes; marcadores de entrevista pendentes; último deploy;
  branch e mudanças não commitadas. O que não consegue ler aparece como `unknown (motivo)`.
  Inconsistências são listadas, não corrigidas.
- **Grava:** nada. Não pergunta nada.
- **Gates:** nenhum.
- **Handoff:** sugere um próximo comando a partir dos fatos, na ordem de uma tabela em que a
  primeira linha que se aplica vale (por exemplo: sem memória → `redevkit-new`; G5 sem
  resposta → responder ao G5; tarefas abertas → `redevkit-create`; só tarefas bloqueadas →
  resolver o que elas precisam; último test vermelho → o comando da classe da falha; verify
  pendente → `redevkit-verify`).

## redevkit-memanager

Skill de memória: chamada pelos comandos no início e no fim, e invocável por você
(`/redevkit-memanager` ou `$redevkit-memanager`) ou por frases como "lembre disso".

| Operação | Gatilho | Efeito |
| --- | --- | --- |
| bootstrap | chamada pelo `redevkit-new` | Cria a estrutura a partir dos templates do idioma |
| recall | início de cada comando | Fase 1: lê o índice, `active.md`, invariantes e o que for relevante |
| save | fim de comando; "lembre disso", "anote isso", "remember this" | Classifica o fato, grava no arquivo de destino e atualiza o índice |
| sync | "atualize a memória", "update memory", "UMB" | Revisa todos os arquivos contra o repositório e reconcilia |
| search | "o que sabemos sobre X?" | Busca em `.redevkit/memory/` (só leitura) |
| prune | dentro de save e sync | Índice de seções acima de 100 linhas; consolidação acima de 256; `MEMORY.md` até 256 linhas; o `changelog.md` não é consolidado: acima de 512 linhas, as entradas mais antigas vão para `archive/changelog-AAAA-MM.md` |
| import | `redevkit-new` com memória legada | Importa conforme o mapa da [migração](migracao.md) |
| report | chamada pelo `redevkit-status`; entrada vazia | Resumo factual da memória |

- **Grava automaticamente:** `active.md`, `changelog.md`, `MEMORY.md`; `tech.md` e
  `system.md` quando surge um padrão ou dependência; `project.md` quando muda o escopo
  visível; `user.md` (preferências e feedback).
- **Pede confirmação:** criação ou emenda da constituição (G1), qualquer mudança em
  invariantes e qualquer exclusão. No `--auto`, essas gravações viram propostas em
  `active.md` › Próximos passos.
- **Nunca grava:** segredos e credenciais, logs efêmeros, trechos de código, superfície de
  API, caminhos absolutos locais, o que o código já mostra e transcrições de conversa.
- **Memória nativa:** continua ligada; fatos do projeto precisam estar em
  `.redevkit/memory/`, que prevalece em caso de conflito.
- **Git:** toda a memória é versionada, inclusive `user.md`.
- **Handoff:** quando chamada por outro comando, devolve o controle sem handoff; quando
  invocada por você, sugere o comando que continua o trabalho registrado em `active.md`.
