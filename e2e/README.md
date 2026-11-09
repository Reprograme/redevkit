# E2E real (PLANO §15.2)

Dois cenários × dois runtimes, com o `claude -p` e o `codex exec` de verdade. Cada passo do
pipeline é uma invocação separada: o estado entre passos fica só nos arquivos do projeto
(memória, `specs/`, relatórios), que é exatamente o que o REDEVKIT promete.

```bash
node e2e/run.mjs --scenario A --runtime claude
node e2e/run.mjs --scenario A --runtime codex
node e2e/run.mjs --scenario B --runtime claude
node e2e/run.mjs --scenario B --runtime codex
```

Opções: `--out <dir>` (padrão `e2e/runs/<data>/<cenário>-<runtime>/`), `--work <dir>`
(padrão: pasta temporária com espaço no caminho), `--timeout-min <n>` por passo (padrão 45) e
`--check <workDir>` para reaplicar só as verificações (também exige `--scenario` e `--runtime`;
com `--resume debug,verify,test` continua o pipeline na mesma pasta antes de verificar).

## Cenários

| Cenário | Projeto | Passos |
| --- | --- | --- |
| A | Diretório vazio | `init --target both --lang pt-BR --yes` → `redevkit-new` (jogo de nave 2D para web) → `redevkit-plan --auto "mover, atirar, pontuar"` → `redevkit-create` → `redevkit-test` |
| B | [fixtures/api-b](fixtures/api-b/): API Node sem dependências, com testes, `memory-bank/` (7 arquivos), `CLAUDE.md` com conteúdo e um bug latente no `/about` | `init` (migra o `CLAUDE.md`) → `redevkit-new` (existente; importar e arquivar) → `redevkit-enhance "GET /health"` → `redevkit-test` (vermelho) → `redevkit-debug` → `redevkit-verify` |

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

Comuns aos 4 runs: `redevkit doctor` passa; memória completa; constituição com Test-First;
nenhum arquivo fora dos caminhos esperados; nenhum commit (ou nenhum `git init` no A);
nenhum comando destrutivo nas transcrições; nenhuma auditoria SKIPPED reportada como PASS.

- A: `specs/001-*/` com `spec.md`, `plan.md` e `tasks.md`; o plano cita `game-development`,
  `2d-games` e `web-games`; testes primeiro na US1; tarefas com `@game-developer`;
  `test-report.md` verde.
- B: backup do `CLAUDE.md` e ponteiro; memória legada mapeada e `archive/` criado; delta na
  spec e tarefas anexadas; `.redevkit/bugs/<slug>/{assessment,fix,test}.md`; teste vermelho
  antes do debug; `verification.md` com `converged+verified`; o verify roda os testes de novo
  depois do debug (a última execução do `test-report.md` é `PASS`, executada pelo
  `redevkit-verify`); ciclo de correção registrado no `active.md`.

O resultado de cada run fica em `result.md`/`result.json`; o resumo consolidado está em
[RESULTS.md](RESULTS.md).
