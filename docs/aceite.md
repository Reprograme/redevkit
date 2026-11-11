# Aceite da 1.0 — evidências

Checklist do PLANO §15.3. Cada decisão (D01–D56) e cada achado do relatório (§13, 143 IDs)
aponta para onde está implementado e como é verificado. Legenda dos achados: **C** corrigido
com teste · **R** resolvido por decisão · **E** eliminado (componente não portado) · **N/A**.

Comandos de verificação usados abaixo:

- `npm test` — testes da CLI e do kit (`test/*.test.js`).
- `node bin/redevkit.js validate-kit` — validação do kit nos dois alvos e nos dois idiomas.
- `python -m unittest discover -s test-audits -v` — auditorias Python.
- `npx markdownlint-cli2` — lint de Markdown.
- `node e2e/run.mjs` — E2E real (resultados em [e2e/RESULTS.md](../e2e/RESULTS.md)).

## 1. Decisões D01–D56

| ID | Evidência |
| --- | --- |
| D01 | CLI só instala, renderiza e atualiza: `src/commands/*`; conteúdo em `kit/` (MD). Sem catálogos/trust store/auth. Projeto novo e existente: `test/cli.test.js` (init vazio e com `CLAUDE.md`/`AGENTS.md`). |
| D02 | `src/core/targets/claude.js` e `codex.js`; `test/render.test.js` (snapshots por alvo). |
| D03 | Comandos, fases, conhecimento e personas são skills: `kit/{commands,phases,memory,skills}`; personas também viram skill fina no Claude. `test/kit.test.js` (88/69 entradas). |
| D04 | Caminhos de artefatos fixos em `docs/kit-authoring.md` §6 e no bloco do `AGENTS.md` (`kit/context/AGENTS.block.md`, seção Artifacts). |
| D05 | Regra "evidence before claims" no bloco do `AGENTS.md`; seção Evidence rule em cada comando (`kit/commands/*/SKILL.md`). |
| D06 | Nenhum arquivo do Antigravity/Gemini; validador falha em `antigravity`/`gemini` (`src/core/validate.js` `FORBIDDEN`); `test/render.test.js` "validator flags…". |
| D07 | `kit/context/CLAUDE.{pt-BR,en}.md` (só `@AGENTS.md` + instrução); `src/core/context-files.js`. |
| D08 | Sub-skills como `references/` acionáveis pela tabela de roteamento da mãe (ex.: `kit/skills/game-development/SKILL.md` → 10 referências). |
| D09 | Seção 2 deste documento. |
| D10 | Raiz `.redevkit/` (`src/core/manifest.js`, `render.js` `renderCommon`). |
| D11 | Kit em inglês (`docs/kit-authoring.md` §1); templates por idioma em `kit/templates/{pt-BR,en}`; `{{LANG}}` nos comandos. |
| D12 | Node ≥ 20, ESM, npm (`package.json`), base no `managed-tree` do AG Kit (`src/core/managed-tree.js`). |
| D13 | Prefixo `redevkit-` em comandos e fases; personas e conhecimento com nome original (`src/core/validate.js` `NAMES`). |
| D14 | Nenhum script auxiliar do Spec Kit; numeração e pré-requisitos descritos em `kit/phases/redevkit-specify/SKILL.md`. |
| D15 | 17 auditorias + 3 orquestradores em `kit/audits/` (mais o módulo compartilhado `audit_common.py`, desde a 1.0.2); fallback SKIPPED em `kit/audits/README.md`; `test-audits/test_skipped_contract.py`. |
| D16 | Sem hook e sem deny-list (nada em `kit/runtime/` além de allow); seção Safety do bloco do `AGENTS.md`. |
| D17 | `.claude/agents/<p>.md` + skill fina (`claude.js` `personaFile`/`personaSkill`); `test/render.test.js`. |
| D18 | `.codex/agents/<p>.toml` via `smol-toml`; fallback inline no `{{DELEGATE}}` do Codex; `test/render.test.js`. |
| D19 | 19 personas, `product-manager` fundido em `kit/personas/product-owner.md`; `test/kit.test.js` (inventário). |
| D20 | `kit/commands/redevkit-new/SKILL.md` (novo × existente, memória, constituição na memória, domínio). |
| D21 | `kit/commands/redevkit-brainstorm/SKILL.md` (assess sem feature ativa, clarify com feature ativa, `go` → plan). |
| D22 | `kit/commands/redevkit-plan/SKILL.md` + `references/plan-stage.md` (specify → route → plan → DESIGN.md → tasks → analyze → G2). |
| D23 | `redevkit-create` e `redevkit-enhance` usam `redevkit-implement` + `redevkit-orchestrate`; enhance redireciona mudança grande ao plan. |
| D24 | Fases com `user-invocable: false` no Claude e `[internal]` no Codex (`targets/*.js`); `test/render.test.js`. |
| D25 | Verificação leve em create/enhance/debug; completa em `redevkit-verify`. |
| D26 | Handoffs test → deploy (verde) / debug → verify (vermelho) nos `## Handoff` dos comandos. |
| D27 | `kit/commands/redevkit-deploy/SKILL.md` + `kit/commands/redevkit-test/references/code-state.md` (HEAD e impressões digitais; produção com confirmação; override com motivo). |
| D28 | `invocation: user-only` → `disable-model-invocation: true` e `agents/openai.yaml`; `test/kit.test.js`. |
| D29 | Handoff em todos os comandos; `--auto` e gates no bloco do `AGENTS.md` e nos comandos. |
| D30 | `kit/commands/redevkit-preview/SKILL.md` só MD; `auto_preview.py`/`session_manager.py` ausentes (`test_skipped_contract.py` checa os 20 scripts). |
| D31 | Estrutura da memória: `kit/memory/redevkit-memanager/SKILL.md` + `kit/templates/*/memory/`. |
| D32 | Tabela de política de escrita no memanager; confirmação para constituição, invariantes e exclusões. |
| D33 | Precedência sobre a memória nativa: `kit/memory/PROTOCOL.md` (incluído no bloco do `AGENTS.md`); nenhuma config de memória nativa é gravada (D51). |
| D34 | `kit/memory/redevkit-memanager/references/legacy-import.md` (3 opções, G7). |
| D35 | Nada da memória no `.redevkit/.gitignore` (só `backups/`, `tmp/`, `conflicts/`). |
| D36 | Protocolo `{{ASK}}` (`targets/*.js`) + seção Questions dos comandos. |
| D37 | Princípio Test-First padrão em `kit/templates/*/constitution.md`; `redevkit-tasks` com testes primeiro; E2E A verifica. |
| D38 | Oferta de branch em `redevkit-specify`/`redevkit-plan`; seção Git do bloco do `AGENTS.md` (sem `git init`, sem commit); E2E verifica "nenhum commit". |
| D39 | Gate do `DESIGN.md` no plan; template `kit/templates/*/design.md`; seção Design Source-of-Truth no `plan.md`. |
| D40 | Migração com diff, confirmação e backup: `src/core/install.js` + `context-files.js`; `test/cli.test.js` "init migrates an existing CLAUDE.md". |
| D41 | 8 comandos da CLI em `src/cli.js`. |
| D42 | `package.json` `name: redevkit`, `bin.redevkit`. |
| D43 | `LICENSE` (MIT) e `NOTICE` (AG Kit, Spec Kit). |
| D44 | `npm test` + `e2e/run.mjs` (2 cenários × 2 runtimes). |
| D45 | Repositório `REDEVKIT/redevkit/` com git próprio; fontes intocadas. |
| D46 | Sub-skills como referências; descrições ≤ 160; orçamento por alvo (`src/core/catalog-budget.js`, `test/kit.test.js`). |
| D47 | Absorções: memanager, orchestrate, route, plan/tasks, verify, brainstorm/clarify; `behavioral-modes` ausente. |
| D48 | Seção 2.3 (K2–K15). |
| D49 | `{{ASK}}`: AskUserQuestion no Claude; `request_user_input` ou texto no Codex (`targets/*.js`). |
| D50 | Protocolo de ~12 linhas em `kit/memory/PROTOCOL.md` + `@.redevkit/memory/MEMORY.md` só no Claude. |
| D51 | `kit/runtime/claude-allow.json` e `codex-config.toml`; `src/core/runtime-config.js`; `test/core.test.js` (ausente, existente, inválido, chave do usuário). |
| D52 | `--lang`; só o idioma escolhido é instalado (`render.js` `renderCommon`); `test/render.test.js` "common files". |
| D53 | NNN com 3 dígitos em `redevkit-specify`; duplicatas no `doctor` (`test/cli.test.js` "doctor…"). |
| D54 | Caminhos de relatórios nos comandos test/verify/deploy/debug e em `kit/templates/*/reports/`. |
| D55 | `- Feature: specs/NNN-name` no `active.md`; status só com fatos (`kit/commands/redevkit-status/SKILL.md`). |
| D56 | Seção 2 deste documento. |

## 2. Achados do relatório (143)

### 2.1 AG Kit — código executável (H, P, S, C, W: 26)

| ID | Destino | Evidência |
| --- | --- | --- |
| H1 | E | Os 4 `.mjs` não existem no produto. Lição: guard do `bin/redevkit.js`; `test/cli.test.js` "bin guard works through a path with spaces". |
| H2 | E | Nenhum hook (D16). |
| H3 | E | Sem `build-plugin`. |
| H4 | E | Lição: allowlist `files` + `test/pack-check.mjs` e `test/kit.test.js` "npm pack…" (sem `__pycache__`/`.pyc`). |
| H5 | C | `src/core/frontmatter.js` (CRLF/BOM) + `.gitattributes`; `test/core.test.js` "frontmatter: CRLF…". |
| H6 | E | Lição: TOML por biblioteca; `test/core.test.js` "persona TOML round-trips…". |
| P1, P2 | E | Preview só MD (D30). |
| P3 | C | `src/core/validate.js`: reporta UTF-8 inválido, links que saem do projeto, sem exceções além das legadas documentadas. |
| P4 | C | Flag única `--no-runtime`: `test-audits/test_p4_no_runtime_flag.py`. |
| S1 | C | `test-audits/test_s1_test_runner.py`. |
| S2 | C | `test-audits/test_s2_security_npm_audit.py`. |
| S3 | C | `test-audits/test_s3_security_sql.py`. |
| S4 | C | `test-audits/test_s4_i18n_flat_layout.py`. |
| S5 | C | `test-audits/test_s5_react_performance.py`. |
| S6 | E | `convert_rules.py` ausente (`test_skipped_contract.py` lista os 20 scripts). |
| S7 | C | `test-audits/test_s7_lint_runner.py`. |
| S8 | C | `test-audits/test_s8_type_coverage_timeout.py`. |
| S9 | C | `test-audits/test_s9_accessibility.py`. |
| S10 | C | `test-audits/test_s10_path_exclusions.py`. |
| C1 | C | `src/core/semver.js` + `redevkit version --check` honesto offline; `test/core.test.js` "semver compare", `test/cli.test.js` "status compares versions…". |
| C2 | C | Temporário ao lado do alvo e limpo no SIGINT (`fsutil.js` `atomicWrite`/`cleanupPendingTemps`, `cli.js`); `test/core.test.js` "atomic write…". |
| C3 | C | `test/core.test.js` "symlinks are never written or deleted through" com `t.skip()` sem privilégio. |
| C4 | C | `test/cli.test.js` "init without TTY and without --yes fails…" e uninstall sem `--yes`. |
| W1, W2 | E | CI novo (`.github/workflows/ci.yml`); `web/` não portado. |

### 2.2 AG Kit — camada Markdown (M: 14)

| ID | Destino | Evidência |
| --- | --- | --- |
| M1 | R | Memória única (D31–D34, D47): `kit/memory/`. |
| M2 | R | Versão só no `package.json`, injetada por `{{VERSION}}`; `test/render.test.js` "version comes from package.json only". |
| M3 | R | Contagens geradas pelo validador (`validate-kit` imprime totais); nenhuma contagem manual que possa divergir na documentação. |
| M4 | E | `CHANGELOG.md` novo a partir de 1.0.0. |
| M5, M6 | E | Documentos não portados; validador de links (`validate.js`, `test/docs.test.js`). |
| M7 | C | `kit/personas/project-planner.md` sem `CODEBASE.md`; `code-review-graph` opcional; validador proíbe `CODEBASE.md`. |
| M8 | R | Artefatos em `specs/NNN` (D22). |
| M9 | R | Catálogo gerado do frontmatter (`catalog-budget.js`). |
| M10, M11, M13 | E | Memória/documentos do AG Kit não portados; `intelligent-routing` absorvida em `redevkit-route`. |
| M12 | R | Sub-skills como referências; o validador cobre todo `.md` do kit. |
| M14 | C | `kit/skills/mcp-builder/` revisado contra a especificação oficial; `references/configure-mcp.md`. |

### 2.3 AG Kit — contradições (K: 15, todas R)

| ID | Evidência |
| --- | --- |
| K1 | D36: protocolo `{{ASK}}` e seção Questions. |
| K2 | `kit/phases/redevkit-orchestrate/SKILL.md` (menor conjunto coerente). |
| K3 | Paralelo só em `[P]` com arquivos disjuntos; síntese pelo coordenador (mesma fase). |
| K4 | Comandos deixam artefato em `specs/NNN`; edições pequenas permitidas (bloco do `AGENTS.md`). |
| K5 | Fases definidas pelo `redevkit-plan`. |
| K6 | Gate G2 entre plan e create. |
| K7 | Modelo único de tarefas (`kit/phases/redevkit-tasks/references/task-format.md`). |
| K8 | Sem `allowed-tools` (renderer descarta; teste de allowlist de frontmatter); `clean-code` sem scripts. |
| K9 | Sem `trigger`/`priority`; precedência no bloco do `AGENTS.md`. |
| K10 | Purple Ban padrão sobreponível: `frontend-design`, `frontend-specialist`, template `design.md`, bloco do `AGENTS.md`. |
| K11 | Leitura do `MEMORY.md` obrigatória (início de sessão no bloco); escrita pela D32. |
| K12 | `redevkit-status` só com fatos; SKIPPED nunca PASS (E2E verifica). |
| K13 | `behavioral-modes` e "Gemini Mode Mapping" ausentes (validador proíbe `gemini`). |
| K14 | `product-manager` fundido em `product-owner`. |
| K15 | Ferramentas por placeholders de alvo (`{{DELEGATE}}`, `{{ASK}}`); validador proíbe `ViewCodeItem`/`FindByName`/`run_command`. |

### 2.4 Spec Kit — scripts, templates e documentação (R: 12, T: 23, D: 11)

| ID | Destino | Evidência |
| --- | --- | --- |
| R1–R12 | E | Scripts não portados (D14). Lição: detecção de intérprete executando `--version` (`kit/audits/README.md`, `doctor` `detectPython`). |
| T1 | C | Fases e templates citam `.redevkit/memory/constitution.md`; validador proíbe `/memory/` solto. |
| T2 | C | `kit/phases/redevkit-checklist/SKILL.md`: só `spec.md` é pré-requisito. |
| T3 | C | `kit/phases/redevkit-clarify/SKILL.md`: passos 1–8 numerados de forma consistente. |
| T4 | C | `redevkit-implement` usa as fases do `task-format.md`; TDD padrão. |
| T5 | R | O agente numera (D14, D53); `doctor` detecta duplicatas. |
| T6 | C | `{{ARGS}}` exatamente uma vez por comando (validador). |
| T7 | C | Template `plan.md` com fases antes do relatório; plan detecta `plan.md` existente e exige `spec.md`. |
| T8 | C | Sync Impact Report no `changelog.md` (`redevkit-constitution`, passo 9). |
| T9 | C | Templates com frontmatter válido (`test/kit.test.js` renderiza e o `doctor` valida a memória). |
| T10 | C | Resolução única `overrides/` → core em todas as fases que usam template. |
| T11, T18 | E | Sem extensões nem hooks. |
| T12 | E | Template de extensão não portado; markdownlint no CI. |
| T13, T14, T16, T17, T20, T21, T23 | E | Componentes não portados (`vscode-settings.json` etc.). |
| T15 | C | Template `spec.md` sem `$ARGUMENTS` literal (validador: só `{{ARGS}}` e só em comandos). |
| T19 | R | D38: nunca `git init` (E2E A verifica). |
| T22 | E | Motor de workflows não portado; `--auto` em MD. |
| D1 | R | Branch opcional (D38), em `docs/metodo.md`. |
| D2, D3, D4, D6, D8 | C | `docs/metodo.md` reescrito a partir dos templates reais; `test/docs.test.js` (termos só se existirem nos templates). |
| D5 | R | D36. |
| D7 | R | D10. |
| D9 | R | Formato único `redevkit-<cmd>` (D13). |
| D10, D11 | E | Documentos não portados. |

### 2.5 Spec Kit — pacote Python e design (Y: 37, G: 5)

| ID | Destino | Evidência |
| --- | --- | --- |
| Y1–Y37 | E | `src/specify_cli` não portado. Lições aplicadas: sem `shell=True`/shell na CLI (Y1; `doctor.which` resolve executáveis); nenhum comando executado a partir de arquivos comitáveis (Y2); symlink/junction checados antes de gravar ou apagar (Y3, Y9; `fsutil.crossesLink`); arquivos estranhos tolerados (Y12; `test/cli.test.js` "junk files…"); saída UTF-8 (Y15); manifesto atômico (Y18; `manifest.js`). |
| G1–G4 | E | MCP e documentos de design não portados. |
| G5 | N/A | Verificação positiva (nenhum `os.chdir`). |

## 3. Correções encontradas pelo E2E real

Os runs reais com `claude -p` e `codex exec` expuseram defeitos que os testes unitários não
pegavam. Todos foram corrigidos com teste ou com texto de skill revisado:

| Achado no E2E | Correção |
| --- | --- |
| No Windows, o Codex gravou artefatos pelo PowerShell e perdeu os acentos | Regra "write every file as UTF-8" no bloco do `AGENTS.md` (o rerun saiu com acentos corretos) |
| `security_scan.py` acusava lock file ausente e rodava `npm audit` num projeto sem dependências | `_node_has_dependencies`; `test-audits/test_e2e_security_false_positives.py` |
| `security_scan.py` cobrava cabeçalhos de segurança de qualquer projeto com `package.json` (CLI, biblioteca, API JSON) | Detecção de projeto web por indicadores reais e frameworks; mesmo teste |
| `test_runner.py` contava arquivos de teste do Vitest/Jest como testes | Contagem pela linha `Tests`; `test-audits/test_e2e_test_runner_counts.py` |
| `doctor` lia o exemplo `→ arquivo.md` de dentro do comentário do índice e recusava alvos relativos à raiz (`.redevkit/bugs/…`) | Só entradas `- [tipo]`, comentários removidos, alvo resolvido na memória ou na raiz; `test/cli.test.js` |
| `redevkit-enhance` tratava "adicionar um endpoint" como mudança de contrato público e mandava para o plan | Heurística: só mudança que quebra contrato é grande; acréscimo compatível continua enhance |
| A spec leve do enhance (D55) não tem `plan.md`, mas implement, tasks e converge o exigiam | Exceção D55 explícita nas três fases |
| `redevkit-test` dava FAIL para cenário não automatizável (revisão humana, dispositivo de referência), levando a um laço de debug inútil | Cenário não automatizável vira "Não verificado" (nunca PASS, nunca FAIL) e o handoff aponta para o verify |
| Harness: caminho curto do Windows (`RICARD~1`) bloqueava escritas no Claude; vereditos lidos de qualquer ocorrência do token | `realpathSync.native`; veredito pelo cabeçalho da última execução |

## 4. Demais critérios do §15.3

| Critério | Evidência |
| --- | --- |
| CI verde em 3 SO | `.github/workflows/ci.yml`: GitHub Actions run 42220543579 (2026-11-06, commit `20d59e8`, repositório privado `Reprograme/redevkit`) com `success` em `windows-latest`, `macos-latest` e `ubuntu-latest`: testes Node, validação do kit, auditorias Python, markdownlint e allowlist do pacote. |
| E2E 4/4 | [e2e/RESULTS.md](../e2e/RESULTS.md). |
| Orçamento de catálogo | `validate-kit` e `test/kit.test.js` (abaixo de 12.000 e do fallback de 8.000 nos dois alvos). |
| `npm pack --dry-run` | `test/pack-check.mjs`. |
| Documentação sem links quebrados | `test/docs.test.js` + markdownlint. |

## 5. Mudança do pipeline e revisão do kit (2026-11-08)

Pedido do solicitante: o verify passa a rodar o test quando vem depois de um debug, e o test
verde segue para o deploy sugerindo o verify. Decisões tomadas com o solicitante:

| Decisão | Onde está |
| --- | --- |
| O verify decide pelo estado do código: reaproveita a última execução do `test-report.md` sobre o mesmo código (`PASS` segue, `FAIL` dá `failed`); senão executa o procedimento do test | `kit/commands/redevkit-verify/SKILL.md` passo 1 |
| Com o test verde, o verify continua (convergência, execução sem rodar a suíte de novo, auditorias); com o test vermelho, para e vai ao debug | Passos 1–4 do verify |
| Ciclo de correção: 2 `failed` após debug (qualquer causa) ou 3 verify sem `converged+verified` disparam o G5; execuções de testes não zeram o contador | Passo 6 do verify (definição única) |
| Deploy: com debug pendente, `BLOCKED` até o verify; senão, a última execução do `test-report.md` precisa ser `PASS` sobre o código atual | `kit/commands/redevkit-test/references/code-state.md` § Compare |
| Checklists de domínio são informativos (um aviso no implement, "Não verificado" no verify) | `phases/redevkit-implement`, `phases/redevkit-checklist` |
| `init --force` faz backup de todo arquivo que sobrescreve | `src/core/install.js`; `test/cli.test.js` |

Revisão do kit inteiro por quatro revisores independentes (comandos, fases e templates,
personas e skills, documentação), cerca de 60 achados conferidos e corrigidos. Os principais:
loop sem limite dentro do debug (bug-test `failed`), status mandando de volta ao plan depois do
create (marcador `- Plan approved:`), spec leve sem caminho no verify e no create, resync do
`redevkit-new` apagando a feature ativa, bug "aberto" sem definição, regra de referência do
deploy circular, rótulos de `active.md` diferentes entre en e pt-BR, skills que mandavam
corrigir bug sem teste de regressão ou reiniciar produção sem confirmação, escrita PowerShell
sem UTF-8, auditorias que davam `PASS` sem checar nada (Drizzle, tudo `SKIPPED`) e
`git hash-object --stdin` fora da allowlist. O harness E2E ganhou duas verificações no cenário
B: a última execução do `test-report.md` é `PASS` feita pelo verify, e o ciclo de correção está
no `active.md`.

Evidência de execução: E2E real do cenário B (`e2e/runs/r6`, 2026-11-08) aprovado com 16/16
checagens no Claude Code e no Codex, inclusive as duas novas; ver [e2e/RESULTS.md](../e2e/RESULTS.md).
Testes: 46 Node e 63 Python; `validate-kit` e markdownlint sem achados.

## 6. Revisão 1.0.2 (2026-11-10)

Origem: num projeto real (PHP/CodeIgniter com Playwright), todos os achados das auditorias
caíram em código de terceiros, arquivos gerados ou protótipos. As afirmações do relato foram
conferidas no código e corrigidas:

| Achado | Correção | Evidência |
| --- | --- | --- |
| Cada auditoria tinha sua própria lista de pastas ignoradas; `vendor/` só em parte delas; nenhuma lia o `.gitignore`; não havia como excluir caminhos | Política única em `kit/audits/audit_common.py`: padrões comuns, `.gitignore`, `.redevkit/audit-ignore` e `--exclude PATTERN` (`--no-gitignore` desliga o segundo) | `test-audits/test_s11_exclusions.py` |
| UX, acessibilidade, SEO e GEO não liam views `.php` | Views `.php`/`.phtml` com os blocos PHP mascarados; parciais não disparam checagens de documento | `test-audits/test_s12_php_views.py` |
| O passo 4 do verify rodava a suíte de testes de novo pelos orquestradores | `--no-tests` em `checklist.py` e `verify_all.py`; o verify sempre passa a opção | `test-audits/test_p4_no_runtime_flag.py`; `kit/commands/redevkit-verify/references/execution.md` |
| Quedas e falsos positivos nas auditorias (`onClick`, `regex.exec(`, `<Header>`, BOM, arquivos fora de UTF-8) | Corrigidos script a script | `test-audits/test_s13_audit_review.py` |
| Achados em código que o projeto não mantém viravam tarefas ou `failed` | Triagem no verify: ficam fora do escopo e vão para as Notas da auditoria | `execution.md` § Audits, passo 6 |
| `rollback` apagava os arquivos gerenciados que a execução desfeita não tinha tocado | Remove só o que a execução criou; o primeiro `init` faz backup da configuração do usuário que reescreve | `test/cli.test.js`, `test/core.test.js` |
| `doctor` não executava atalhos `.cmd` em caminho com espaço; erros de uso saíam com 1; Ctrl+C no prompt não saía com 130 | `src/commands/doctor.js`, `src/cli.js`, `src/core/prompt.js` | `test/cli.test.js` |
| Estado "sem tarefa aberta" indefinido no create; status e deploy comparavam com execução de escopo parcial | Texto dos comandos corrigido | `kit/commands/redevkit-create`, `redevkit-status`, `redevkit-deploy` |

Não refeito nesta revisão: o E2E real (`node e2e/run.mjs`) e a CI nos três sistemas.
