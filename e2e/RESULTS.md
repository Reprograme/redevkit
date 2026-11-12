# Resultados do E2E

Gerado por `e2e/summarize.mjs` em 2026-11-06 12:11 UTC; linhas B atualizadas em 2026-11-08 com os runs `r6` (pipeline com o verify rodando o test); linhas C, D e E adicionadas em 2026-11-12 com os runs `r7` e `r8` (1.1.0: estado do código por conteúdo, classes de falha, `Verify pending`), só no Claude Code. Roteiro e checagens em [README.md](README.md).

| Run | Checagens | Veredito | Duração dos passos |
| --- | --- | --- | --- |
| A-claude | 12/12 | PASS | 63 min |
| A-codex | 12/12 | PASS | 49 min |
| B-claude | 16/16 | PASS | 15 min |
| B-codex | 16/16 | PASS | 26 min |
| C-claude | 19/19 | PASS | 18 min |
| D-claude | 18/18 | PASS | 18 min |
| E-claude | 19/19 | PASS | 10 min |

**Resultado:** 7 de 7 aprovados. C, D e E ainda não rodaram no Codex.

## Histórico das tentativas

Os aprovados acima são os runs finais. As tentativas anteriores não foram descartadas em
silêncio. Cada uma revelou algo, corrigido antes do run final (ver também
[docs/aceite.md](../docs/aceite.md) §3):

| Tentativa | O que aconteceu | Correção |
| --- | --- | --- |
| A-claude e B-claude, 1ª | Claude recusou gravar no caminho curto do Windows (`RICARD~1`) e não contornou a checagem | Harness usa o caminho longo (`realpathSync.native`) |
| A-codex e B-codex, 1ª | Limite de uso da conta do Codex atingido no meio do run | Reexecutados depois da liberação |
| A-codex, 1ª | Acentos corrompidos ao gravar pelo PowerShell | Regra UTF-8 no bloco do `AGENTS.md` |
| B-claude, 2ª | `verify` deu `gaps` por falsos positivos do `security_scan.py` (lock file e cabeçalhos num projeto sem dependências) | Auditoria corrigida, com teste |
| B-codex, 2ª e 3ª | `enhance` mandou "adicionar endpoint" para o plan; depois o implement exigiu `plan.md` numa spec leve | Heurística de tamanho e exceção D55 no implement, tasks e converge |
| A-codex, 2ª | `test` deu FAIL só por cenários não automatizáveis (revisão humana, dispositivo de referência) | Regra "Não verificado" no `redevkit-test`. O run final continuou o mesmo projeto pelo fluxo do kit: `debug`, depois `redevkit update` (merge de 3 vias, 0 conflitos) e novo `test` |
| B-claude, 4ª | O harness não permitia mover o `memory-bank/`; o agente copiou para `archive/`, não removeu os originais e registrou a pendência | Harness autoriza mover o `memory-bank/` (equivale a aprovar o prompt) |
| B-claude e B-codex, `r6` (2026-11-08) | Novo pipeline: depois do debug, o verify roda o test (passo 1) e grava a execução `PASS` no `test-report.md`; ciclo de correção por feature no `active.md`. Duas checagens novas | Aprovados na primeira tentativa, 16/16 nos dois |
| E-claude, `r7` (2026-11-12) | A cadeia `--auto` inteira funcionou numa só invocação, mas o agente reescreveu o `MEMORY.md` sem o frontmatter e o `doctor` reprovou (18/19) | Regra no `redevkit-memanager`: editar os arquivos de memória no lugar, nunca regenerá-los inteiros; o run `r8` passou 19/19 |

## Detalhes

### A-claude

| Check | Result | Detail |
| --- | --- | --- |
| redevkit doctor passes | PASS |  |
| memory complete | PASS |  |
| constitution has Test-First | PASS |  |
| no files outside expected paths | PASS |  |
| no git repository created (D38) | PASS |  |
| no destructive command in transcripts | PASS |  |
| no SKIPPED audit reported as PASS | PASS |  |
| specs/001-*/ has spec, plan, tasks | PASS | 001-mover-atirar-pontuar |
| plan cites game-development + 2d-games + web-games (routing) | PASS |  |
| tests first in US1 (TDD) | PASS | - [X] T021 [P] [US1] Escrever testes que falham da partida: `createWorld(semente, config)` começa `jogando`, tick 0, placar 0, nave com centro em (240, 680) (FR |
| tasks assigned to @game-developer | PASS |  |
| test-report.md green (last run PASS) | PASS | PASS |

### A-codex

| Check | Result | Detail |
| --- | --- | --- |
| redevkit doctor passes | PASS |  |
| memory complete | PASS |  |
| constitution has Test-First | PASS |  |
| no files outside expected paths | PASS |  |
| no git repository created (D38) | PASS |  |
| no destructive command in transcripts | PASS |  |
| no SKIPPED audit reported as PASS | PASS |  |
| specs/001-*/ has spec, plan, tasks | PASS | 001-mover-atirar-pontuar |
| plan cites game-development + 2d-games + web-games (routing) | PASS |  |
| tests first in US1 (TDD) | PASS | - [X] T004 [US1] Escrever testes de início, limites, direções opostas e pausa sem salto ou teclas presas — tests/unit/movimento.test.js — @test-engineer — VERIF |
| tasks assigned to @game-developer | PASS |  |
| test-report.md green (last run PASS) | PASS | FAIL → FAIL → PASS |

### B-claude

| Check | Result | Detail |
| --- | --- | --- |
| redevkit doctor passes | PASS |  |
| memory complete | PASS |  |
| constitution has Test-First | PASS |  |
| no files outside expected paths | PASS |  |
| no commit created | PASS | 1 -> 1 |
| no destructive command in transcripts | PASS |  |
| no SKIPPED audit reported as PASS | PASS |  |
| CLAUDE.md backup + pointer | PASS |  |
| legacy memory mapped (§9.8) | PASS | mapped: project.md, tech.md, system.md, active.md, changelog.md |
| archive/ created and memory-bank/ archived | PASS |  |
| spec delta + tasks (or lightweight spec, D55) | PASS | 001-health-endpoint |
| .redevkit/bugs/<slug>/{assessment,fix,test}.md | PASS | about-sem-version |
| verification.md converged+verified (last run) | PASS | converged+verified |
| test went red before debug (bug exposed) | PASS | FAIL → PASS |
| verify re-ran the tests after debug (last test run PASS, run by redevkit-verify) | PASS | FAIL → PASS |
| correction cycle recorded in active.md | PASS |  |

### B-codex

| Check | Result | Detail |
| --- | --- | --- |
| redevkit doctor passes | PASS |  |
| memory complete | PASS |  |
| constitution has Test-First | PASS |  |
| no files outside expected paths | PASS |  |
| no commit created | PASS | 1 -> 1 |
| no destructive command in transcripts | PASS |  |
| no SKIPPED audit reported as PASS | PASS |  |
| CLAUDE.md backup + pointer | PASS |  |
| legacy memory mapped (§9.8) | PASS | mapped: project.md, tech.md, system.md, active.md, changelog.md |
| archive/ created and memory-bank/ archived | PASS |  |
| spec delta + tasks (or lightweight spec, D55) | PASS | 001-endpoint-saude |
| .redevkit/bugs/<slug>/{assessment,fix,test}.md | PASS | versao-about-ausente |
| verification.md converged+verified (last run) | PASS | converged+verified |
| test went red before debug (bug exposed) | PASS | FAIL → PASS |
| verify re-ran the tests after debug (last test run PASS, run by redevkit-verify) | PASS | FAIL → PASS |
| correction cycle recorded in active.md | PASS |  |

### C-claude

| Check | Result | Detail |
| --- | --- | --- |
| redevkit doctor passes | PASS |  |
| memory complete | PASS |  |
| constitution has Test-First | PASS |  |
| no files outside expected paths | PASS |  |
| no commit created | PASS | 0 -> 0 |
| no destructive command in transcripts | PASS |  |
| no SKIPPED audit reported as PASS | PASS |  |
| CLAUDE.md backup + pointer | PASS |  |
| legacy memory mapped (§9.8) | PASS | mapped: project.md, tech.md, system.md, active.md, changelog.md |
| archive/ created and memory-bank/ archived | PASS |  |
| spec delta + tasks (or lightweight spec, D55) | PASS | 001-health-endpoint |
| verification.md converged+verified (last run) | PASS | converged+verified |
| .redevkit/bugs/<slug>/{assessment,fix,test}.md | PASS | about-version-indefinida |
| test went red before debug (bug exposed) | PASS | FAIL → PASS |
| verify re-ran the tests after debug (last test run PASS, run by redevkit-verify) | PASS | FAIL → PASS |
| red test run names a failure class | PASS |  |
| correction cycle recorded in active.md | PASS |  |
| every test run records a Tree fingerprint | PASS | 2 run(s) |
| Verify pending cleared after converged+verified | PASS | no |

### D-claude

| Check | Result | Detail |
| --- | --- | --- |
| redevkit doctor passes | PASS |  |
| memory complete | PASS |  |
| constitution has Test-First | PASS |  |
| no files outside expected paths | PASS |  |
| no commit created | PASS | 1 -> 1 |
| no destructive command in transcripts | PASS |  |
| no SKIPPED audit reported as PASS | PASS |  |
| CLAUDE.md backup + pointer | PASS |  |
| legacy memory mapped (§9.8) | PASS | mapped: project.md, tech.md, system.md, active.md, changelog.md |
| archive/ created and memory-bank/ archived | PASS |  |
| spec delta + tasks (or lightweight spec, D55) | PASS | 001-health-endpoint |
| verification.md converged+verified (last run) | PASS | gaps → converged+verified |
| verify found the injected gap (a gaps run before the last one) | PASS | gaps → converged+verified |
| Convergence tasks appended and all done | PASS | 0 open or blocked |
| test ran again between the two verifies | PASS | PASS → PASS |
| correction cycle recorded in active.md | PASS |  |
| every test run records a Tree fingerprint | PASS | 2 run(s) |
| Verify pending cleared after converged+verified | PASS | no |

### E-claude

| Check | Result | Detail |
| --- | --- | --- |
| redevkit doctor passes | PASS |  |
| memory complete | PASS |  |
| constitution has Test-First | PASS |  |
| no files outside expected paths | PASS |  |
| no commit created | PASS | 1 -> 1 |
| no destructive command in transcripts | PASS |  |
| no SKIPPED audit reported as PASS | PASS |  |
| CLAUDE.md backup + pointer | PASS |  |
| legacy memory mapped (§9.8) | PASS | mapped: project.md, tech.md, system.md, active.md, changelog.md |
| archive/ created and memory-bank/ archived | PASS |  |
| spec delta + tasks (or lightweight spec, D55) | PASS | 001-health-endpoint |
| verification.md converged+verified (last run) | PASS | converged+verified |
| .redevkit/bugs/<slug>/{assessment,fix,test}.md | PASS | about-sem-versao |
| test went red before debug (bug exposed) | PASS | FAIL → PASS |
| verify re-ran the tests after debug (last test run PASS, run by redevkit-verify) | PASS | FAIL → PASS |
| red test run names a failure class | PASS |  |
| correction cycle recorded in active.md | PASS |  |
| every test run records a Tree fingerprint | PASS | 2 run(s) |
| Verify pending cleared after converged+verified | PASS | no |
