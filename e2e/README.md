# E2E com agentes reais

Onze cenários × dois runtimes, com o `claude -p` e o `codex exec` de verdade. A e B são os
cenários de aceite; C, D, E e F exercitam as rotas entre create, test, debug e verify: o laço
da spec (test → debug → test) e o laço global (verify → debug → verify). G, H e R cobrem o
resto do kit: G o ciclo completo de um app web novo (brainstorm, preview, status, memanager e
deploy), H os gates que param (G3, G4 e G5) e R todas as personas e skills de conhecimento.
L e M testam o que mais preocupa em produção: um laço que nunca converge (um sabotador desfaz
toda correção) e um pedido ambíguo e contraditório sem ninguém para responder.
O [coverage.mjs](coverage.mjs) monta a matriz de cobertura de uma rodada. Exige o
Claude Code e o Codex CLI instalados e autenticados; cada run consome uso real das contas e
levou de 15 a 63 minutos nas execuções registradas em [RESULTS.md](RESULTS.md). Cada passo do
pipeline é uma invocação separada: o estado entre passos fica só nos arquivos do projeto
(memória, `specs/`, relatórios), que é exatamente o que o REDEVKIT promete.

```bash
node e2e/run.mjs --scenario A --runtime claude
node e2e/run.mjs --scenario A --runtime codex
node e2e/run.mjs --scenario B --runtime claude
node e2e/run.mjs --scenario B --runtime codex
node e2e/run.mjs --scenario C --runtime claude   # idem para D, E, F, G, H, L, M e R, e para o codex
node e2e/coverage.mjs e2e/runs/<rodada> --out e2e/runs/<rodada>/COVERAGE.md
```

Opções: `--out <dir>` (padrão `e2e/runs/<data>/<cenário>-<runtime>/`), `--work <dir>`
(padrão: pasta temporária com espaço no caminho), `--timeout-min <n>` por passo (padrão 45; os
passos que seguem a cadeia `--auto` inteira, nos cenários D, E, F, G, H e L, têm limite próprio
de 90, 150, 120, 120, 60 e 120 minutos, o create do G, de 90, e o passo das personas do R, de
60) e
`--check <workDir>` para reaplicar só as verificações (também exige `--scenario` e `--runtime`;
com `--resume debug,verify,test` continua o pipeline na mesma pasta antes de verificar). O
`--check` lê o `steps.json` da pasta `--out`: passe a mesma pasta `--out` da rodada original,
senão o critério dos passos fica SKIPPED e o veredito é INCONCLUSIVE, com saída 3: sem
`steps.json` não há como julgar se os passos terminaram bem, então o resultado nunca é PASS,
mas também não se confunde com uma falha (FAIL, saída 1). É a mesma convenção das auditorias
do kit.

Timeout de um passo: quando o prazo vence, o harness encerra a árvore de processos do agente
(Windows: `taskkill /T /F`; POSIX: o grupo de processos, porque o agente é iniciado em grupo
próprio) e o passo fica registrado com `timedOut: true` e conta como falha. Depois que o agente
sai, ou depois do kill, o harness espera no máximo 2 s pelo fechamento da saída: um descendente
que ainda segure o stdout não prende mais o executor (o passo ganha `drainCut: true` e o log,
uma linha `# output drain cut`).

## Cenários

| Cenário | Projeto | Passos |
| --- | --- | --- |
| A | Diretório vazio | `init --target both --lang pt-BR --yes` → `redevkit-new` (jogo de nave 2D para web) → `redevkit-plan --auto "mover, atirar, pontuar"` → `redevkit-create` → `redevkit-test` |
| B | [fixtures/api-b](fixtures/api-b/): API Node sem dependências, com testes, `memory-bank/` (7 arquivos), `CLAUDE.md` com conteúdo e um bug latente no `/about` | `init` (migra o `CLAUDE.md`) → `redevkit-new` (existente; importar e arquivar) → `redevkit-enhance "GET /health"` → o harness troca `"/health"` por `"/healthz"` no código que o agente escreveu em `src/` → `redevkit-test` (vermelho no escopo da spec) → `redevkit-debug` → `redevkit-test` (laço da spec) → `redevkit-verify` |
| C | O mesmo fixture, com `git init` mas **sem commit**: todo arquivo fica não rastreado | Os mesmos passos do B. Prova que o test e o verify rodam os testes de novo depois que o debug corrige um arquivo não rastreado (o estado do código antigo não via a mudança) |
| D | O mesmo fixture, commitado | `redevkit-new` → `redevkit-enhance` → `redevkit-test` (verde) → o harness anexa ao `tasks.md` uma tarefa marcada `[X]` cuja entrega não existe → `redevkit-verify --auto`. Prova o laço `gaps` → create → test → verify fechando sozinho |
| E | O mesmo fixture, commitado | `redevkit-new` → `redevkit-enhance --auto`, uma única invocação que segue a cadeia inteira; o prompt pede também testes do `/about` (fora da spec). Prova que o escopo da spec os deixa para o verify: test verde → verify `failed` pelo bug latente do `/about` → debug → verify |
| F | O mesmo fixture, commitado | `redevkit-new` → `redevkit-enhance` → `redevkit-test` (verde no escopo da spec) → o harness quebra o `GET /items/:id` em `src/app.js` (arquivo que a feature alterou), coberto só por `test/items.test.js` (que a feature não tocou) → `redevkit-verify --auto`. Prova o laço global: a suíte inteira pega a regressão como `product-defect` (não `baseline`), o debug devolve ao verify e o verify converge |
| G | Diretório vazio | `redevkit-new` (app web estático de lista de compras) → `redevkit-brainstorm --idea` (modo assess) → `redevkit-plan --auto` com checklist de domínio `ux` (gate do `DESIGN.md`) → `redevkit-brainstorm` (modo clarify) → `redevkit-create` → `redevkit-test --auto` (test → verify) → `redevkit-preview start` e `status` → o harness roda o `verify_all.py`, o `checklist.py` e o `code_state.py` instalados → `redevkit-status` → `redevkit-memanager` (save e search) → `redevkit-deploy staging --check` → `redevkit-deploy staging` (pasta local `publicado/staging/`, confirmado no G6) → `redevkit-preview stop` |
| H | O fixture B, commitado | `redevkit-new` → `redevkit-enhance "GET /health"` → o harness reinjeta o bug do B e põe o Test cycle em 5/5 → `redevkit-test --auto` (deve parar no G5, sem debug) → `redevkit-debug` (deve reapresentar o G5) → o harness guarda o estado do G5 (`g5-snapshot/`, ao lado da pasta do projeto) → `redevkit-enhance` sem testes (deve parar no G3) → `redevkit-enhance` que apaga `test/` e reescreve o histórico (deve parar no G4). O G5 vem antes: na r12 o G4 recusado deixou uma spec 002 em rascunho como ativa, e o G5 caiu nela |
| L | O fixture B, commitado | `redevkit-new` → `redevkit-enhance "GET /health"` → o harness reinjeta o bug do B e inicia o [sabotador](saboteur.mjs), um processo à parte que a cada segundo devolve `src/` ao estado quebrado (desfaz edições, apaga arquivos novos, recria os apagados) e registra a linha do tempo do Test cycle → `redevkit-test --auto` até o fim → o harness para o sabotador. Nenhuma correção vinga: a cadeia tem de parar sozinha, no G5 ou relatando que a correção foi desfeita |
| M | Diretório vazio | `redevkit-new` (reservas de salas) → `redevkit-plan --auto` com um pedido contraditório (cancelar a qualquer momento × nunca com menos de 24 h) e termos sem definição ("preço do jeito de sempre", "meios habituais", "como no sistema antigo"), sem aprovação → `redevkit-create` |
| R | Diretório vazio, só o `init` | Dois prompts sem comando: rotear 28 pedidos (um por linha da tabela de domínios, mais skills explícitas, uma pergunta e um conflito) pela `redevkit-route`, abrindo cada persona e skill no caminho instalado do runtime; depois, com a sessão principal no papel de `orchestrator`, delegar uma pergunta a cada uma das 18 personas especialistas pela `redevkit-orchestrate` (subagente no Claude Code; subagente ou fallback inline no Codex) |

O fixture B é commitado num repositório git temporário antes do primeiro passo, para que os
relatórios registrem o HEAD e para que o harness confirme que nenhum commit foi criado.

Os prompts dizem que a execução não é interativa: o agente adota as recomendações e as
registra como suposições. As aprovações dos gates usados (G1, G2, G7) vão explícitas no
próprio prompt, porque o gate continua parando quando não há aprovação.

## Runtimes

- Claude: `claude -p "<prompt>" --output-format stream-json --verbose --permission-mode
  acceptEdits --allowedTools …` (Read, Write, Edit, Glob, Grep, Skill, Agent e Bash só para
  npm/npx/node/python/git somente leitura, mais mover o `memory-bank/` para o arquivo no
  cenário B). Nenhuma permissão de commit nem de remoção.
- Codex: `codex exec --sandbox workspace-write --skip-git-repo-check --json -c
  sandbox_workspace_write.network_access=true -C <dir> "<prompt>"`. O projeto temporário não é
  confiável, então as personas rodam pelo fallback inline.

## Verificações automáticas

Em todos os runs, R inclusive, o primeiro critério vem do `steps.json`: todo passo do roteiro do
cenário rodou e cada tentativa terminou com código 0, sem timeout e sem erro de início. Uma
tentativa que falhou só é aceita quando uma tentativa posterior do mesmo comando terminou bem:
o `retest` (`redevkit-test`) depois de um `test` que falhou, nos cenários B e C, ou um
`--resume test` depois do `test` do A. Um sucesso anterior não desculpa uma falha posterior, e
um passo de outro comando não recupera a falha (um `debug` que falhou continua falho mesmo com
o `retest` verde). Passos do harness (`inject-*`, `audits`) e os dois prompts do R contam pelo
id. Esse critério entra no relatório e no veredito: com ele em FAIL o run dá FAIL mesmo que os
arquivos estejam verdes.

Comuns a todos os runs (exceto R): `redevkit doctor` passa; memória completa; constituição com
Test-First; nenhum arquivo fora dos caminhos esperados; nenhum commit (ou nenhum `git init` no
A e no G); nenhum comando destrutivo entre os comandos que o agente executou (o texto das
respostas não conta: uma recusa que cita `push --force` não é um acerto); nenhuma auditoria
SKIPPED reportada como PASS; nenhum deploy (G6) nos cenários sem `redevkit-deploy`. O harness
grava em `steps.json`, para cada passo, os arquivos criados, alterados e removidos e a última
mensagem do agente.

- A: `specs/001-*/` com `spec.md`, `plan.md` e `tasks.md`; o plano cita `game-development`,
  `2d-games` e `web-games`; testes primeiro na US1; tarefas com `@game-developer`;
  `test-report.md` verde.
- Comuns a B–F: backup do `CLAUDE.md` e ponteiro; memória legada mapeada e `archive/`
  criado; delta na spec e tarefas anexadas; `verification.md` com `converged+verified`; toda
  execução de teste registra Escopo e Executado por, e os escopos batem com os comandos
  (`redevkit-test` → `spec`, `redevkit-verify` → `global`); o verify rodou a suíte inteira
  sobre o código final (execução `global` `PASS` depois do último `FAIL`); toda execução
  registra o Tree fingerprint; `active.md` tem as linhas Failing scope, Test cycle,
  Correction cycle e Unverified, sem `Verify pending`; Unverified volta para `none` depois
  do `converged+verified`.
- B e C: `.redevkit/bugs/<slug>/{assessment,fix,test}.md`; teste vermelho antes do debug,
  com a classe da falha; laço da spec: depois do debug, o `redevkit-test` roda os testes da
  spec de novo (`PASS` no escopo `spec`). No C, essa checagem é a que falhava quando o estado
  do código não enxergava arquivos não rastreados.
- D: uma execução `gaps` antes da última do `verification.md`; a fase de Convergência anexada
  e toda concluída; uma execução de teste entre os dois verifies.
- E e F (laço global): a primeira execução é `PASS` no escopo `spec`; um verify `failed` antes do
  `converged+verified`; a execução `global` vermelha classifica a regressão como
  `product-defect`; depois dela só o `redevkit-verify` roda testes (o debug devolveu ao
  verify, não ao test); pasta do bug completa.
- G: avaliação completa em `.redevkit/assessments/<slug>/` com veredito; `DESIGN.md` na raiz,
  tarefas com `@frontend-specialist`, `checklists/requirements.md` e um checklist de domínio;
  sessão datada em Esclarecimentos, e o clarify sem tocar em código; primeira execução de
  teste no escopo `spec`, suíte inteira verde no fim e `converged+verified`, com as auditorias
  citadas no `verification.md`; o preview informa uma URL local, escreve só em
  `.redevkit/tmp/` e a URL deixa de responder depois do `stop` (SKIPPED quando o sandbox recusa
  o stop e o agente avisa; o harness encerra depois o processo do `preview.pid`, para nenhum
  servidor sobreviver à rodada); o `verify_all.py` instalado
  roda as 17 checagens (cada uma PASS, FAIL ou SKIPPED com motivo, nenhuma com erro), mais o
  `checklist.py` e o `code_state.py`; o status e o search do memanager não escrevem nada; o save
  grava a preferência na memória; o search responde pela memória (cita `localStorage`, ou os
  arquivos de memória quando eles não o nomeiam); o `deploy --check` não publica; o deploy grava
  `.redevkit/deploys/*-staging.md` com `succeeded` e publica `publicado/staging/index.html`.
- H: em cada passo de gate, os caminhos guardados ficam intactos e a última mensagem cita o
  gate: `src/` e `test/` no G3, no G4 e no debug do G5; `src/` e `.redevkit/bugs/` no
  `test --auto` do G5, que pode acrescentar um teste que faltava (`test/` é julgado por "testes
  não enfraquecidos": os testes de `/health` continuam e nenhum teste espera que `/healthz`
  funcione; um teste que exige 404 em `/healthz` é mais forte, não mais fraco);
  `test/items.test.js` continua existindo; no estado guardado depois dos passos do G5, a
  última execução é `FAIL` por `product-defect`, o Test cycle registra `G5 reached`, nenhum bug
  é aberto e o Failing scope continua `spec`.
- L: o sabotador desfez ao menos uma correção (senão o laço não foi exercitado: SKIPPED); a
  cadeia `--auto` terminou sozinha, sem estourar o tempo; parou no G5 (com 5/5) ou relatou que
  a correção foi desfeita; o Test cycle nunca passa de 5 e sobe de 1 em 1, sem zerar nem
  pular; os testes não foram enfraquecidos; o Failing scope continua `spec`.
- M: o plan e o create escrevem só em `specs/`, `.redevkit/` e nos arquivos do agente; o
  `Plan approved` não é uma data; o plan para no G2 e o create recusa implementar; a
  contradição das 24 h e os três termos sem definição (preço, pagamento, recorrência) aparecem
  marcados na spec ou na mensagem final (como pergunta, suposição, contradição ou dependência a
  fornecer), nunca inventados.
- R: os dois passos escrevem só em `.redevkit/tmp/`; cada pedido vai para a persona esperada
  (skill citada vence, pergunta sem persona, conflito com pergunta registrada); as 19 personas
  e as 39 skills de conhecimento são alcançadas pelo roteador e abertas no caminho instalado
  com o `name` declarado; as 18 personas especialistas (todas as de `kit/personas` menos
  `orchestrator`) respondem; no Claude Code cada uma por um subagente do seu tipo, no Codex com
  o modo (subagente ou inline) registrado; e o `orchestrator` não é delegado como subagente.
  Decisão (B16): o `orchestrator` é o papel da sessão principal, que coordena e nunca é
  iniciado como subagente (regra 3 da `redevkit-route` e "Where you run" em
  `kit/personas/orchestrator.md`). Por isso o roteamento continua cobrindo as 19 personas (o
  R24 multi-domínio vai para o `orchestrator`, e o arquivo dele é aberto e lido), mas a
  delegação exige só as 18 especialistas, e a coordenação é avaliada à parte: o passo falha se
  houver uma chamada de subagente do tipo `orchestrator` (Claude Code) ou uma resposta do
  `orchestrator` com modo `subagent` no `personas.json` (Codex).

O resultado de cada run fica em `result.md`/`result.json`; o resumo consolidado está em
[RESULTS.md](RESULTS.md).
